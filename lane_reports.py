#!/usr/bin/env python3
"""Lane reporting layer — alerts, report, evidence pack, validator.

Composes with archive_pulse (loads pulse.jsonl / row_from) without touching
that file, so both pulse runners and CI can call this safely:

    python3 lane_reports.py            # emit alerts + rebuild REPORT + pack
    python3 lane_reports.py --validate # quality gate; exit 3 on problems

Alert cards (alerts.jsonl): one append per pulse whose FROZEN/leader keys
moved — excludes churny numeric counters (downloads, trend score). Cards carry
a sha256 of their own content; self-consistent evidence, not a signature.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from archive_pulse import HERE as _HERE, JSONL, load_rows, row_from
except Exception:  # archive_pulse schema moves fast (multi-agent lane)
    _HERE = HERE
    JSONL = os.path.join(_HERE, "pulse.jsonl")

    def load_rows():
        rows = []
        if os.path.exists(JSONL):
            with open(JSONL) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except ValueError:
                            pass
        rows.sort(key=lambda r: r.get("ts") or "")
        return rows

    def row_from(snap):
        return snap

ALERTS = os.path.join(HERE, "alerts.jsonl")
REPORT = os.path.join(HERE, "REPORT.md")
PACK = os.path.join(HERE, "packs", "pack-latest.md")
VLOG = os.path.join(HERE, "verification-log.jsonl")
RECON = os.path.join(HERE, "RECONCILIATION.md")
DASH = os.path.join(HERE, "dashboard.html")
FEED = os.path.join(HERE, "feed.json")
CSVF = os.path.join(HERE, "timeseries.csv")
ROOT_URL = "https://councilof.ai/root.json"
UA = {"User-Agent": "gspc-pulse-lane-reports/0.1 (permissionless reproduction)"}

ALERT_KEYS = [
    "board_slots", "board_measured", "board_separated", "board_ties",
    "board_untested", "capsules_total", "capsules_as_of", "root_card_count",
    "root_as_of", "cards_declared", "cards_store", "cards_head",
    "hf_top_id", "hf_top_trending", "hf_top_new_30d",
    "kev_count", "kev_released",
]


def _append_jsonl(path, row):
    with open(path, "a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


def _read_jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        pass
    return out


def emit_alerts():
    rows = load_rows()
    if len(rows) < 2:
        return 0
    prev, cur = rows[-2], rows[-1]
    rp, rc = row_from(prev), row_from(cur)
    changes = {k: [rp.get(k), rc.get(k)] for k in ALERT_KEYS
               if rp.get(k) != rc.get(k)}
    p_anch = prev.get("anchors") or {}
    c_anch = cur.get("anchors") or {}
    for k in ("ots_state", "rekor_state", "xrpl_state"):
        if p_anch.get(k) != c_anch.get(k):
            changes["anchors." + k] = [p_anch.get(k), c_anch.get(k)]
    # Section-absence (UNREACHABLE) is never a change: compare only when BOTH
    # rows carry the section.
    p_did = (prev.get("did") or {}).get("key_ids")
    c_did = (cur.get("did") or {}).get("key_ids")
    if p_did is not None and c_did is not None and p_did != c_did:
        changes["did_key_ids"] = [p_did, c_did]
    kt_prev = (prev.get("kev") or {}).get("top20")
    kt_cur = (cur.get("kev") or {}).get("top20")
    if kt_prev is not None and kt_cur is not None:
        new_ids = [i for i in kt_cur if i not in kt_prev]
        if new_ids:
            changes["kev_new_ids"] = new_ids
    if not changes:
        return 0
    # One card per transition: dedupe on (prev_ts, ts) — reruns must not
    # re-emit for a transition already recorded.
    p_ts, c_ts = prev.get("ts"), cur.get("ts")
    for a in _read_jsonl(ALERTS):
        if a.get("prev_ts") == p_ts and a.get("ts") == c_ts:
            return 0
    alert = {"ts": c_ts, "kind": "frozen-delta",
             "prev_ts": p_ts, "changes": changes}
    alert["sha256"] = hashlib.sha256(
        json.dumps(alert, sort_keys=True).encode()).hexdigest()
    _append_jsonl(ALERTS, alert)
    print("alert card emitted (%d frozen changes)" % len(changes))
    return 0


def build_report():
    rows = load_rows()
    alerts = _read_jsonl(ALERTS)
    vlog = _read_jsonl(VLOG)
    runners = {}
    kinds = {}
    for r in rows:
        rid = (r.get("meta") or {}).get("runner") or r.get("writer") or "canonical"
        runners[rid] = runners.get(rid, 0) + 1
        if r.get("swan"):
            kinds["swan-scan"] = kinds.get("swan-scan", 0) + 1
        if r.get("interop"):
            kinds["interop-census"] = kinds.get("interop-census", 0) + 1
    latest = rows[-1] if rows else {}
    dom = (latest.get("domains") or {}).get("codes") or {}
    ok = sum(1 for v in dom.values() if v[0] == "2")
    lines = [
        "# GSPC Pulse — Evidence Report",
        "",
        "_Regenerated every pulse. Measurement, not endorsement; never a "
        "certification. License CC BY 4.0._",
        "",
        "- Rows: **%d** (runners: %s)" % (
            len(rows), ", ".join("%s×%d" % kv for kv in sorted(runners.items())) or "—"),
        "- Fluid layers carried: %s" % (", ".join(sorted(kinds)) or "—"),
        "- Latest: **%s**" % latest.get("ts"),
        "- Alert cards (frozen deltas): **%d**" % len(alerts),
        "- Verification log entries: **%d**" % len(vlog),
        "- Domains OK (2xx first-hop): **%d / %d**" % (ok, len(dom)),
    ]
    if alerts:
        lines += ["", "## Frozen-delta timeline (latest 12)", ""]
        for a in alerts[-12:]:
            for k, (a0, a1) in a.get("changes", {}).items():
                lines.append("- `%s` — %s: %s → **%s**" % (
                    a["ts"], k, json.dumps(a0)[:48], json.dumps(a1)[:48]))
    if vlog:
        lines += ["", "## Verification cadence (latest 6)", ""]
        for v in vlog[-6:]:
            lines.append("- `%s` — %s %s: **%s**" % (
                v.get("ts"), v.get("kind"), (v.get("subject") or "")[:16],
                v.get("verdict") or v.get("note", "")[:40]))
    with open(REPORT, "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(rows)


def build_pack():
    rows = load_rows()
    if not rows:
        return 0
    latest = rows[-1]
    os.makedirs(os.path.dirname(PACK), exist_ok=True)
    dom = (latest.get("domains") or {}).get("codes") or {}
    b = latest.get("board") or {}
    with open(PACK, "w") as f:
        f.write("""# Evidence Pack — GSPC Live Pulse (rolling latest)

**Cite as:** GSPC live pulse — CSOAI / Council of AI (councilof.ai), CC BY 4.0.
**Snapshot:** {ts} UTC · series: {n} rows since 2026-11-03.

Measurement, not endorsement; never a certification. Every value below was
fetched LIVE at {ts} and is traceable to its source surface at that moment.

## Frozen layer
- GSPC board: {bm} measured of {bs} slots · separated leads {sl} · ties {t} · untested {u}
- Capsule index: {cap} capsules (as_of {capas})
- Public root: {root} cards (as_of {rootas})
- Signed cards: {decl} declared / {store} in store (two labelled numbers)
- CISA KEV: {kev} entries (released {kevrel})

## Estate liveness (first-hop status codes)
{dom}

## Full latest row
```json
{row}
```
""".format(ts=latest.get("ts"), n=len(rows),
           bm=b.get("measured"), bs=b.get("slots"),
           sl=b.get("separated_leads") if "separated_leads" in b else b.get("separated"),
           t=b.get("ties"), u=b.get("untested"),
           cap=(latest.get("capsules") or {}).get("total"),
           capas=(latest.get("capsules") or {}).get("as_of"),
           root=(latest.get("root") or {}).get("card_count"),
           rootas=(latest.get("root") or {}).get("as_of"),
           decl=(latest.get("cards") or {}).get("declared"),
           store=(latest.get("cards") or {}).get("store"),
           kev=(latest.get("kev") or {}).get("count"),
           kevrel=(latest.get("kev") or {}).get("released"),
           dom="\n".join("- %s: `%s`" % (k, v)
                         for k, v in sorted(dom.items())) or "—",
           row=json.dumps(latest, indent=2, sort_keys=True)))
    return 1


def vlog_record(event):
    """Append a verification-log entry; dedupes per day on
    (kind, subject, verdict)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = ts[:10]
    key = (event.get("kind"), event.get("subject"), event.get("verdict"))
    for r in _read_jsonl(VLOG):
        if r.get("ts", "").startswith(day) and \
                (r.get("kind"), r.get("subject"), r.get("verdict")) == key:
            return 2
    row = dict(event)
    row["ts"] = ts
    row["sha256"] = hashlib.sha256(
        json.dumps(row, sort_keys=True).encode()).hexdigest()
    _append_jsonl(VLOG, row)
    return 0


def verify_root(timeout=25):
    """Independent FULL verification of the public root: recompute the entire
    Merkle tree from the published leaf list under the published node rule
    (parent = sha256(left||right) over raw 32-byte digests, Bitcoin-style
    odd-node duplication, no domain separation) and compare to the published
    merkle_root. Rejects leaf-count mismatches (the CVE-2012-2459 closure).
    This needs no MCP tools — anyone on the public internet can run it."""
    import urllib.request
    verdict, detail = "FETCH_FAILED", None
    try:
        req = urllib.request.Request(ROOT_URL, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        leaves = [bytes.fromhex(h) for h in d.get("card_sha256") or []]
        root = bytes.fromhex(d.get("merkle_root"))
        if not leaves or len(leaves) != d.get("card_count"):
            return "INVALID", "leaf count %s != card_count %s" % (
                len(leaves), d.get("card_count"))
        level = list(leaves)
        levels = 0
        while len(level) > 1:
            if len(level) % 2:
                level.append(level[-1])
            level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                     for i in range(0, len(level), 2)]
            levels += 1
        verdict = "VALID" if level[0] == root else "MISMATCH"
        detail = {"leaves": len(leaves), "levels": levels,
                  "recomputed": level[0].hex(), "published": root.hex(),
                  "root_as_of": d.get("as_of")}
    except Exception as e:
        detail = str(e)[:200]
    vlog_record({"kind": "verify_root_full", "subject": "public-root.json",
                 "verdict": verdict, "detail": detail})
    return verdict, detail


def build_reconciliation():
    """Measured-the-measurer: where independent runners read the same field
    and disagreed, plus standing framing/live divergences. Disagreement is
    the finding — shown, never silently reconciled."""
    rows = load_rows()
    fields = ["board_measured", "capsules_total", "root_card_count",
              "cards_declared", "cards_store", "kev_count"]
    by_day = {}
    for r in rows:
        day = (r.get("ts") or "")[:10]
        rid = (r.get("meta") or {}).get("runner") or r.get("writer") or "canonical"
        proj = row_from(r)
        for f in fields:
            v = proj.get(f)
            if v is not None:
                by_day.setdefault(day, {}).setdefault(f, {}) \
                      .setdefault(json.dumps(v), set()).add(rid)
    disputes = []
    for day in sorted(by_day):
        for f in sorted(by_day[day]):
            vals = by_day[day][f]
            if len(vals) > 1:
                disputes.append((day, f, vals))
    vr = [v for v in _read_jsonl(VLOG) if v.get("kind") == "verify_root_full"]
    lines = [
        "# Reconciliation — measured the measurer",
        "",
        "_Where two independent runners read the same field on the same day and",
        "_disagreed, plus standing framing/live divergences. Disagreement is the",
        "_finding: shown, never silently reconciled. Measurement, not endorsement._",
        "",
        "- Disputed field-days: **%d**" % len(disputes),
    ]
    for day, f, vals in disputes:
        detail = "; ".join("%s = %s (%s)" % (f, v, ", ".join(sorted(rs)))
                           for v, rs in sorted(vals.items()))
        lines.append("- `%s` — %s" % (day, detail))
    lines += [
        "",
        "## Known standing divergences (two/three labelled numbers)",
        "",
        "- Signed card **index declares 335**; **/api/cards count endpoint",
        "  reports 336** (includes the separate-schema cross-border East-West",
        "  card); **/api/state card_chain.bodies_verified_valid reads 335**.",
        "  Three surfaces, three labelled numbers, all honest.",
        "- The head card's **frozen framing says \u201c13 measured of 14",
        "  quotable\u201d**; the live count is **34/34**. Cards cannot be",
        "  re-signed — the live count comes from GET /api/gspc, never from",
        "  inside a card.",
        "",
        "## Public-root verification (independent, full recompute)",
        "",
    ]
    if vr:
        last = vr[-1]
        lines.append("- Latest: **%s** at `%s` · %s" % (
            last.get("verdict"), last.get("ts"),
            json.dumps(last.get("detail"))[:180]))
    else:
        lines.append("- Not yet run (runs with every lane_reports pass).")
    with open(RECON, "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(disputes)


def build_dashboard():
    """Self-contained reporting-layer HTML: alert cards + verification
    cadence. Complements index.html (the raw series) without touching it."""
    alerts = _read_jsonl(ALERTS)
    vlog = _read_jsonl(VLOG)
    data = json.dumps({"alerts": alerts, "vlog": vlog}).replace("</", "<\\/")
    with open(DASH, "w") as f:
        f.write("""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GSPC Pulse — Alerts, Verification</title>
<style>
 body{font-family:-apple-system,system-ui,sans-serif;margin:2rem auto;max-width:960px;
      padding:0 1rem;color:#1a1a2e;background:#f7f7fb}
 h1{margin-bottom:.2rem} .sub{color:#555}
 h2{margin-top:2rem;border-bottom:2px solid #dcd;font-size:1.1rem}
 table{border-collapse:collapse;width:100%;font-size:.85rem;background:#fff}
 th,td{border:1px solid #ddd;padding:.35rem .5rem;text-align:left;vertical-align:top}
 .ok{color:#0a7d32;font-weight:600} .warn{color:#b06000;font-weight:600}
 footer{margin-top:2rem;font-size:.8rem;color:#666}
</style></head><body>
<h1>GSPC Pulse — reporting layer</h1>
<p class="sub">Alert cards and verification cadence. Companion to
<a href="index.html">index.html</a> · reconciliation:
<a href="RECONCILIATION.md">RECONCILIATION.md</a> · series:
<a href="feed.json">feed.json</a> · current: <a href="latest.json">latest.json</a>.
Measurement, not endorsement; never a certification. CC BY 4.0.</p>
<h2>Alert cards (frozen deltas)</h2>
<table id="alerts"><thead><tr><th>ts</th><th>changes (prev → new)</th></tr></thead><tbody></tbody></table>
<h2>Verification cadence</h2>
<table id="vlog"><thead><tr><th>ts</th><th>kind</th><th>subject</th><th>verdict</th></tr></thead><tbody></tbody></table>
<footer>Regenerated every pulse by lane_reports.py · CC BY 4.0 · CSOAI / Council of AI (councilof.ai).</footer>
<script id="data" type="application/json">__DATA__</script>
<script>
const d=JSON.parse(document.getElementById('data').textContent);
const fa=document.querySelector('#alerts tbody');
for(const a of d.alerts){
  const ch=Object.entries(a.changes||{}).map(([k,pn])=>
    k+': '+JSON.stringify(pn[0])+' → <b>'+JSON.stringify(pn[1])+'</b>').join('<br>');
  const tr=document.createElement('tr');
  tr.innerHTML='<td>'+a.ts+'</td><td>'+ch+'</td>'; fa.appendChild(tr);
}
const fv=document.querySelector('#vlog tbody');
for(const v of d.vlog){
  const tr=document.createElement('tr');
  const cls=(v.verdict==='VALID')?'ok':((v.verdict&&v.verdict!=='VALID')?'warn':'');
  tr.innerHTML='<td>'+v.ts+'</td><td>'+(v.kind||'')+'</td><td>'+((v.subject||'')+'').slice(0,40)+'</td><td class="'+cls+'">'+(v.verdict||'—')+'</td>';
  fv.appendChild(tr);
}
</script></body></html>""".replace("__DATA__", data))
    return len(alerts)


def build_weekly_pack():
    """ISO-week evidence pack slice: packs/pack-<YYYY>-W<NN>.md."""
    rows = load_rows()
    if not rows:
        return None
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    tag = "%d-W%02d" % (iso[0], iso[1])
    monday = (now - timedelta(days=iso[2] - 1)).strftime("%Y-%m-%d")
    week_rows = [r for r in rows if (r.get("ts") or "")[:10] >= monday]
    week_alerts = [a for a in _read_jsonl(ALERTS)
                   if (a.get("ts") or "")[:10] >= monday]
    path = os.path.join(HERE, "packs", "pack-%s.md" % tag)
    with open(path, "w") as f:
        f.write("""# Evidence Pack — week %s slice

**Cite as:** GSPC live pulse — CSOAI / Council of AI (councilof.ai), CC BY 4.0.
Week window: %s → · rows in window: **%d** of %d total · frozen-delta alerts: **%d**.

Measurement, not endorsement; never a certification.

## Frozen moves this week
%s

## Latest row in window (%s)
```json
%s
```
""" % (tag, monday, len(week_rows), len(rows), len(week_alerts),
       ("\n".join("- `%s` — %s" % (a["ts"], ", ".join(
           "%s → %s" % (k, json.dumps(v[1])[:40])
           for k, v in a.get("changes", {}).items()))
           for a in week_alerts) or "— none —"),
       (week_rows[-1].get("ts") if week_rows else "—"),
       json.dumps(week_rows[-1] if week_rows else {}, indent=2, sort_keys=True)))
    return path


def validate_lane():
    problems = []
    rows = load_rows()
    if not rows:
        problems.append("pulse.jsonl has no rows")
    tss = [r.get("ts") for r in rows]
    if len(set(tss)) != len(tss):
        problems.append("duplicate ts in pulse.jsonl")
    if tss != sorted(tss):
        problems.append("pulse.jsonl not ts-sorted")
    for name, path in (("alerts", ALERTS), ("verification-log", VLOG)):
        for i, line in enumerate(_read_jsonl(path) and
                                  open(path).read().splitlines()):
            if line.strip():
                try:
                    json.loads(line)
                except ValueError:
                    problems.append("%s line %d unparseable" % (name, i + 1))
    if os.path.exists(FEED):
        with open(FEED) as f:
            feed = json.load(f)
        if feed.get("row_count") != len(rows):
            problems.append("feed.json row_count %s != %d"
                            % (feed.get("row_count"), len(rows)))
        if feed.get("updated") != (rows[-1].get("ts") if rows else None):
            problems.append("feed.json updated != last row ts")
    else:
        problems.append("feed.json missing")
    if not os.path.exists(CSVF):
        problems.append("timeseries.csv missing")
    return problems


def main():
    if "--validate" in sys.argv:
        problems = validate_lane()
        if problems:
            print("LANE INVALID:")
            for p in problems:
                print(" -", p)
            return 3
        print("lane valid: %d rows" % len(load_rows()))
        return 0
    v, detail = verify_root()
    print("verify_root: %s" % (json.dumps(detail)[:120] if detail else v))
    emit_alerts()
    build_report()
    build_pack()
    build_weekly_pack()
    nd = build_reconciliation()
    build_dashboard()
    print("report + packs + reconciliation (%d disputes) + dashboard rebuilt; rows=%d"
          % (nd, len(load_rows())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
