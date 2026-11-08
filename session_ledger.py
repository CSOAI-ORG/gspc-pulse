#!/usr/bin/env python3
"""session_ledger.py — the session event ledger (Sentinel-ARCHITECTURE §8).

Append-only, hash-chained ledger of session events (schema
csoai.gspc-session-event/0.1). One file per day in the state dir; the newest
snapshot of active sessions can be mirrored for panels. No PII: session ids
are opaque; conversation content never enters the ledger — only facts.

Usage:
  session_ledger.py emit --kind check_failed --session S1 --host sentinel-browser \
      --coverage observing --subject "example claim" --detail "…"
  session_ledger.py tail [-n 5]
  session_ledger.py verify
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

STATE = "/Users/iokfarm/workspace_for_ai/plugins/gspc-live-state"
LEDGER = os.path.join(STATE, "session-events.jsonl")
GENESIS = b"session-ledger-genesis-2026-11-04"
KINDS = ("run_started", "plan_reported", "tool_called", "check_passed",
         "check_failed", "check_uncheckable", "awaiting_human",
         "human_decided", "outcome_verified", "run_completed",
         "observation_interrupted")


def canonical(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":")).encode()


def tail_entries(n):
    if not os.path.exists(LEDGER):
        return []
    rows = []
    with open(LEDGER) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    return rows[-n:]


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("emit")
    e.add_argument("--kind", required=True, choices=KINDS)
    e.add_argument("--session", required=True)
    e.add_argument("--host", default="sentinel-browser")
    e.add_argument("--coverage", default="observing",
                   choices=["observing", "gated", "not_connected", "stale"])
    e.add_argument("--actor")
    e.add_argument("--subject")
    e.add_argument("--detail")
    t = sub.add_parser("tail")
    t.add_argument("-n", type=int, default=5)
    sub.add_parser("verify")
    a = p.parse_args()
    os.makedirs(STATE, exist_ok=True)

    if a.cmd == "emit":
        prev_rows = tail_entries(10 ** 9)
        prev_sha = prev_rows[-1]["sha256"] if prev_rows else hashlib.sha256(GENESIS).hexdigest()
        entry = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "kind": a.kind, "session_id": a.session, "host": a.host,
                 "coverage": a.coverage, "actor": a.actor, "subject": a.subject,
                 "detail": a.detail,
                 "prev_sha256": prev_sha}
        entry["sha256"] = hashlib.sha256(
            prev_sha.encode() + canonical(entry)).hexdigest()
        with open(LEDGER, "a") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        print("emitted %s [%s] session=%s" % (a.kind, a.coverage, a.session))
        return 0

    if a.cmd == "tail":
        for r in tail_entries(a.n):
            print(r.get("ts"), r.get("kind"), r.get("coverage"), r.get("session_id"))
        return 0

    if a.cmd == "verify":
        rows = tail_entries(10 ** 9)
        prev = hashlib.sha256(GENESIS).hexdigest()
        ok = True
        for r in rows:
            claimed = r.pop("sha256", None)
            calc = hashlib.sha256(prev.encode() + canonical(r)).hexdigest()
            if claimed != calc:
                print("FAIL at", r.get("ts"))
                ok = False
                break
            prev = claimed
        print("%s: %d entries" % ("LEDGER VERIFIED" if ok else "LEDGER BROKEN", len(rows)))
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
