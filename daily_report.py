#!/usr/bin/env python3
"""daily_report.py — the auto-compiled DAILY FINDINGS report for humans in the loop.

Compiles every layer's output into one dated, readable, E-A-T report:
  Today in numbers (newest pulse row) · Findings (alerts + overdue KEV with
  reasoning) · Claims (open/corrected, from the maintenance ledger) · Council
  decisions (BFT) · Verifications (cadence log of the day) · Regulation
  signals (direct crosswalk pairs touched) · Learned (curriculum freeze
  state) · Evidence links. Written to daily/YYYY-MM-DD.md + daily/LATEST.md
  and mirrored. No LLM — compiled from signed artifacts.
"""
import hashlib
import json
import pathlib
from datetime import datetime, timezone

LANE = pathlib.Path(__file__).resolve().parent
HOME_LANE = pathlib.Path.home() / "workspace_for_ai/clawd-workspace/m2/evidence/gspc-pulse"
STATE = pathlib.Path.home() / "workspace_for_ai/plugins/gspc-live-state"
DAILY = LANE / "daily"
LATEST_ROW = LANE / "latest.json"
ALERTS = LANE / "alerts.jsonl"
CLAIMS = HOME_LANE / "claims/claims-ledger.jsonl"
DECISIONS = STATE / "council-decisions.jsonl"
VLOG = LANE / "verification-log.jsonl"
SIGNALS = LANE / "signals.jsonl"
CURR_MANIFEST = LANE / "academy/curriculum-manifest.json"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def main():
    L = (json.loads(LATEST_ROW.read_text()).get("latest") or {}) if LATEST_ROW.exists() else {}
    k, b, h = L.get("kev") or {}, L.get("board") or {}, L.get("hf") or {}
    alerts = [a for a in read_jsonl(ALERTS) if a.get("ts", "").startswith(TODAY)]
    claims = [c for c in read_jsonl(CLAIMS) if c.get("ts", "").startswith(TODAY)]
    decisions = [d for d in read_jsonl(DECISIONS) if d.get("ts", "").startswith(TODAY)]
    verdicts = [v for v in read_jsonl(VLOG) if v.get("ts", "").startswith(TODAY)]
    signals = read_jsonl(SIGNALS)
    direct = [s for s in signals if s.get("relevance") == "direct"]
    curr = json.loads(CURR_MANIFEST.read_text()) if CURR_MANIFEST.exists() else {}

    top5 = k.get("top5") or []
    overdue = [t for t in top5 if isinstance(t.get("due_days_left"), int)
               and t["due_days_left"] < 0]
    pri = next((t for t in top5 if (t.get("epss") or 0) >= 0.1), None)

    md = ["# GSPC DAILY FINDINGS — %s" % TODAY,
          "",
          "*Auto-compiled from signed artifacts by the gspc-pulse lane. "
          "Measurement, not endorsement — never a certification. "
          "UNREACHABLE is never zero. Verify: `pulse_freeze.py verify`.*",
          "",
          "## Today in numbers",
          "- Row `%s` (writer %s)" % (L.get("ts", "—"), L.get("writer", "—")),
          "- Board: **%s/%s** measured · separation **%s of 14** · ties %s · untested %s"
          % (b.get("measured", "—"), b.get("slots", "—"), b.get("separated", "—"),
             b.get("ties", "—"), b.get("untested", "—")),
          "- KEV: **%s** · HF trending: **%s** · new-30d cohort: %s models led by %s"
          % (k.get("count", "—"), h.get("top_trending", "—"),
             h.get("cohort_count", "—"), h.get("top_new_30d", "—")),
          "",
          "## Findings — exploited vulnerabilities (KEV newest 5)"]
    if not top5:
        md.append("- *no enriched row today — watcher rows only; priorities land on the next canonical pulse*")
    for t in top5:
        dd = t.get("due_days_left")
        due = ("**%d days OVERDUE**" % -dd if isinstance(dd, int) and dd < 0
               else "%d days left" % dd if isinstance(dd, int) else "no date")
        epss = ("EPSS %.3f (p%d)" % (t["epss"], round(t["percentile"] * 100))
                if t.get("epss") is not None else "unscored")
        md.append("- **%s** — %s · %s · %s" % (t.get("cve"), epss, due,
                                               ",".join(t.get("cwes") or [])))
    if overdue:
        md.append("- ⚠️ **%d of the newest 5 are past the federal deadline**" % len(overdue))
    if pri:
        md.append("- → **Priority: %s** — KEV-confirmed with EPSS ≥ 0.1; patch first." % pri.get("cve"))
    md += ["", "## Claims in maintenance"]
    if not claims:
        md.append("- none filed today")
    for c in claims:
        md.append("- %s — **%s** — %s" % (c.get("ts"), c.get("status"),
                                          c.get("claim", c.get("note", ""))[:140]))
    md += ["", "## Council decisions (BFT)"]
    if not decisions:
        md.append("- none today")
    for d in decisions:
        md.append("- %s — **%s** — %s" % (d.get("ts"), d.get("decision"),
                                          d.get("proposition", "")[:130]))
    md += ["", "## Verifications (cadence log)"]
    if not verdicts:
        md.append("- none today")
    for v in verdicts[-8:]:
        md.append("- %s — %s %s → **%s**" % (v.get("ts"), v.get("kind"),
                                             str(v.get("subject"))[:28], v.get("verdict")))
    md += ["", "## Regulation signals (direct crosswalk pairs: %d tracked)" % len(direct)]
    for s in direct[:7]:
        md.append("- %s → **%s** (tier: %s)" % (s.get("axis"), s.get("obligation"),
                                                s.get("tier")))
    md += ["", "## Curriculum (learned layer)"]
    if curr:
        md.append("- frozen %s — %s sources (%s unreachable) · root `%s`"
                  % (curr.get("produced_at"), curr.get("n_sources"),
                     len(curr.get("unreachable", [])),
                     str(curr.get("merkle_root"))[:16]))
    else:
        md.append("- curriculum freeze not run yet today")
    md += ["", "## Portfolio & regulators (moat-v2)"]
    mv = LANE / "moat-v2" / "ecosystem-matrix.json"
    if mv.exists():
        mx = json.loads(mv.read_text())
        failing = [d for d, v in mx["domains"].items()
                   if not str(v.get("endpoint_state", "")).startswith(("2", "3"))]
        md.append("- Verticals tracked: **%d** · domain×regulator pairs: **%d** · "
                  "sensitive verticals flagged: %d"
                  % (mx["totals"]["domains"], mx["totals"]["domain_regulator_pairs"],
                     mx["totals"]["sensitive_verticals"]))
        if failing:
            md.append("- ⚠️ **endpoint failures in verticals under active regulators**: "
                      + ", ".join("%s (%s)" % (d, mx["domains"][d]["industry"])
                                  for d in failing))
        regs = sorted({p["regulator"] for v in mx["domains"].values()
                       for p in v["industry_regulator_pairs"]})
        md.append("- Regulators in scope (candidates): %s" % ", ".join(regs))
    else:
        md.append("- moat-v2 matrix not built yet — run moat_v2.py")
    md += ["", "## Evidence",
           "- Feed: `feed.json` · counters: `timeseries.csv` · freeze manifest: "
           "`pulse-freeze-manifest.json` + `.sig` (same directory, public mirror)",
           "- Verify from anywhere: `verify_remote.py` — no repo, no keys"]

    DAILY.mkdir(exist_ok=True)
    (DAILY / ("%s.md" % TODAY)).write_text("\n".join(md))
    (DAILY / "LATEST.md").write_text("\n".join(md))
    print("daily findings compiled: daily/%s.md (%d claims, %d decisions, "
          "%d verdicts, %d direct signals)" % (TODAY, len(claims), len(decisions),
                                               len(verdicts), len(direct)))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
