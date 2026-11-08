#!/usr/bin/env python3
"""council_bft.py — the Council votes; humans decide only what needs deciding.

BFT voting over INDEPENDENT instruments (they share no code paths — that is
the fault tolerance): the pulse snapshot, the claims ledger, the SOV model,
the crosswalk signals, and the auditor's digest each cast one verdict from
their own data. Quorum = 2/3 of responding voters. If the quorum agrees, the
decision is recorded and the human is INFORMED (not required). If voters
disagree beyond tolerance, or doctrine mandates it (NEEDS-HUMAN-EYES rules,
counsel gates, payments, XRPL), the decision escalates: awaiting_human in the
session ledger — the human is the final move only when the council cannot
self-resolve.

Routing: `route` breaks a big task into chunks and routes each chunk to the
right executor (deterministic engine / SOV model / open-weight model via
MEOK ONE / human gate), with chained continuity — every chunk carries the
session id and its receipt, so long tasks survive restarts.

Usage:
  council_bft.py vote --proposition "…" [--kind ops|doctrine|payment]
  council_bft.py route --task "…" [--session S1]
  council_bft.py decisions [-n 5]
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

# Explicit sibling imports also work under Python isolated mode (-I).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

LANE = pathlib.Path.home() / "workspace_for_ai/clawd-workspace/m2/evidence/gspc-pulse"
STATE = pathlib.Path.home() / "workspace_for_ai/plugins/gspc-live-state"
DECISIONS = STATE / "council-decisions.jsonl"
SESSION_LEDGER = STATE / "session-events.jsonl"
GENESIS = b"council-bft-genesis-2026-11-04"
DOCTRINE_ESCALATE = ("payment", "xrpl", "counsel", "legal", "needs-human-eyes",
                     "deploy", "delete")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_jsonl(p):
    rows = []
    if pathlib.Path(p).exists():
        for line in pathlib.Path(p).read_text().splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows


def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


# ---------- independent voters (no shared code paths) ----------
def v_pulse_snapshot(prop):
    p = LANE / "pulse-freeze-manifest.json"
    try:
        m = json.loads(p.read_text())
        return ("yes" if m.get("n_rows") else "abstain"), "pulse-runner: series frozen, %s rows" % m.get("n_rows")
    except Exception as e:
        return "abstain", "pulse-runner unreachable: %s" % str(e)[:60]


def v_claims(prop):
    rows = read_jsonl(LANE / "claims/claims-ledger.jsonl")
    open_claims = [r for r in rows if r.get("status") in ("open", "checked")]
    kw = [w for w in prop.lower().split() if len(w) > 5]
    touches = any(any(w in json.dumps(r.get("claim", "")).lower() for w in kw)
                  for r in open_claims)
    if touches:
        return "escalate", "claims-ledger: %d open claim(s) touch this proposition" % len(open_claims)
    return "no" if open_claims else "yes", "claims-ledger: %d open claims, none matching" % len(open_claims)


def v_sov(prop):
    p = LANE / "simulation/model.json"
    try:
        m = json.loads(p.read_text())
    except Exception as e:
        return "abstain", "sov-model unavailable: %s" % str(e)[:60]
    triggers = ("overdue", "act today", "urgent", "epss")
    if any(t in prop.lower() for t in triggers):
        return "escalate", "sov-model: act-today triggers present — severity path, prefer human sign-off"
    return "abstain", "sov-model: prose proposition outside its signal-vector input — abstains honestly"


def v_crosswalk(prop):
    p = LANE / "frameworks/obligation-index.json"
    try:
        idx = json.loads(p.read_text())
        gated = sum(1 for o in idx["obligations"] if o.get("access") == "x402")
        hit = any(w in prop.lower() for w in
                  (o["id"] for o in idx["obligations"]))
        if hit:
            return "escalate", "crosswalk: proposition touches a mapped obligation"
        return "yes", "crosswalk: %d obligations tracked, none touched" % len(idx["obligations"])
    except Exception as e:
        return "abstain", "crosswalk unavailable: %s" % str(e)[:60]


def v_audit(prop):
    d = STATE / "DIGEST.md"
    try:
        head = d.read_text()[:400]
        if "all hard checks passed" in head:
            return "yes", "auditor digest: all hard checks passed"
        return "escalate", "auditor digest: findings present — read DIGEST.md"
    except Exception as e:
        return "abstain", "digest unavailable: %s" % str(e)[:60]


VOTERS = {"pulse-runner": v_pulse_snapshot, "claims-ledger": v_claims,
          "sov-model": v_sov, "crosswalk": v_crosswalk, "auditor": v_audit}


def emit_session(kind, session, coverage, subject, detail):
    prev = hashlib.sha256(b"session-ledger-genesis-2026-11-04").hexdigest()
    if SESSION_LEDGER.exists():
        lines = [l for l in SESSION_LEDGER.read_text().splitlines() if l.strip()]
        if lines:
            prev = json.loads(lines[-1]).get("sha256", prev)
    entry = {"ts": now(), "kind": kind, "session_id": session,
             "host": "council-bft", "coverage": coverage,
             "subject": subject[:200], "detail": detail[:300],
             "prev_sha256": prev}
    entry["sha256"] = hashlib.sha256(
        prev.encode() + canonical(entry)).hexdigest()
    with open(SESSION_LEDGER, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def canonical(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def cmd_vote(a):
    voters = {name: fn(a.proposition) for name, fn in VOTERS.items()}
    counts = {"yes": 0, "no": 0, "escalate": 0, "abstain": 0}
    for name, (verdict, reason) in voters.items():
        counts[verdict] += 1
        print("  %-14s %-8s %s" % (name, verdict, reason))
    # Fixed-roster advisory triage; never an execution or publication approval.
    from assurance_core import assess_votes
    assessment = assess_votes(voters, a.proposition, a.kind, len(VOTERS))
    decision = assessment["decision"]
    why = assessment["why"]
    rec = {"ts": now(), "kind": "council-bft-decision",
           "proposition": a.proposition[:300], "votes": {k: v[0] for k, v in voters.items()},
           "decision": decision, "why": why,
           "session_id": a.session or "unbound"}
    rec.update(assessment)
    rec["sha256"] = hashlib.sha256(canonical(rec)).hexdigest()
    with open(DECISIONS, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")
    coverage = "observing" if decision == "TRIAGE_CLEAR" else "gated"
    event_kind = {"HUMAN_DECIDES": "awaiting_human",
                  "INSUFFICIENT_EVIDENCE": "check_uncheckable",
                  "TRIAGE_CLEAR": "plan_reported"}[decision]
    emit_session(event_kind, a.session or "unbound", coverage,
                 "council-triage", decision + ": " + why)
    print("\nDECISION: %s — %s (recorded %s, coverage %s)"
          % (decision, why, rec["sha256"][:16], coverage))
    return 0


ROUTES = [
    ("verify|proof|frozen|merkle|sign", "deterministic-engine",
     "pulse_freeze.py verify / verify_remote.py — no LLM, no hallucination surface"),
    ("kev|cve|vulner|epss|patch", "sov-model + engine",
     "claims ledger for the finding; SOV model for severity; human if EPSS >= 0.1"),
    ("measure|pulse|board|capsule", "deterministic-engine",
     "engine.py build/freeze/verify — instruments over opinions"),
    ("teach|explain|lesson|learn", "him-surface",
     "academy lessons (Space Learn tab / busabase docs) rendered against live data"),
    ("draft|write|post|paper|message", "open-weight-model (MEOK ONE / OWM)",
     "GSPC-analyst persona; every factual claim must carry a pulse row ts"),
    ("pay|deploy|xrpl|delete|legal|contract", "human-gate",
     "DOCTRINE_ESCALATE class — the council votes to involve the human, never to replace them"),
]


def cmd_route(a):
    from assurance_core import route_task
    if not a.session:
        print("explicit --session is required for a content-bound task plan", file=sys.stderr)
        return 2
    plan = route_task(a.task, a.session)
    for s in plan:
        emit_session("plan_reported", s["session_id"],
                     "gated" if s["route"] in ("human-gate", "review-required") else "observing",
                     "planned chunk %d" % s["chunk"], s["route"])
    print(json.dumps({"task_chunks": len(plan), "plan": plan,
                      "execution_authorized": False,
                      "continuity": "content-bound plan identities; no execution, "
                                    "automatic resume or completed outcome is established"}, indent=2))
    return 0


def cmd_decisions(a):
    for r in read_jsonl(DECISIONS)[-a.n:]:
        print(r.get("ts"), r.get("decision"), "—", r.get("proposition", "")[:80])
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("vote")
    v.add_argument("--proposition", required=True)
    v.add_argument("--kind", default="ops", choices=["ops", "doctrine", "payment"])
    v.add_argument("--session")
    r = sub.add_parser("route")
    r.add_argument("--task", required=True)
    r.add_argument("--session")
    d = sub.add_parser("decisions")
    d.add_argument("-n", type=int, default=5)
    a = p.parse_args()
    sys.exit({"vote": cmd_vote, "route": cmd_route,
              "decisions": cmd_decisions}[a.cmd](a))
