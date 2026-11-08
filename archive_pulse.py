#!/usr/bin/env python3
"""Append the latest gspc-live pulse snapshot to the public evidence series.

Reads the pulse state file, dedupes by ts, appends one JSONL row,
regenerates timeseries.csv, prints a delta line vs the previous row.
Exit 0 = row appended; 1 = state file missing/unreadable; 2 = ts already recorded.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.expanduser("~/workspace_for_ai/plugins/gspc-live-state/last-pulse.json")
JSONL = os.path.join(HERE, "pulse.jsonl")
CSVF = os.path.join(HERE, "timeseries.csv")
FEED = os.path.join(HERE, "feed.json")
LATEST = os.path.join(HERE, "latest.json")
LLMS = os.path.join(HERE, "llms.txt")
INDEX_HTML = os.path.join(HERE, "index.html")

FEED_SCHEMA = "csoai.gspc-pulse-feed/0.1"
LICENSE = "CC-BY-4.0"
ATTRIBUTION = "GSPC live pulse — CSOAI / Council of AI (councilof.ai) · MEOK AI LABS"

CSV_COLS = [
    "ts", "writer", "board_slots", "board_measured", "board_separated", "board_ties",
    "board_untested", "capsules_total", "capsules_as_of", "root_card_count",
    "root_as_of", "cards_declared", "cards_store", "cards_head",
    "hf_method", "hf_top_trending", "hf_trend_score", "hf_top_new_30d",
    "hf_new_30d_downloads", "hf_top_id", "hf_top_downloads",
    "kev_count", "kev_released",
    "kev_perimeter", "kev_rw_share_pct", "rw_claimed_today",
    "mcp_hosts", "x402_ok",
]


def row_from(snap):
    return {
        "ts": snap.get("ts"),
        "writer": snap.get("writer"),
        "board_slots": snap.get("board", {}).get("slots"),
        "board_measured": snap.get("board", {}).get("measured"),
        "board_separated": snap.get("board", {}).get("separated"),
        "board_ties": snap.get("board", {}).get("ties"),
        "board_untested": snap.get("board", {}).get("untested"),
        "capsules_total": snap.get("capsules", {}).get("total"),
        "capsules_as_of": snap.get("capsules", {}).get("as_of"),
        "root_card_count": snap.get("root", {}).get("card_count"),
        "root_as_of": snap.get("root", {}).get("as_of"),
        "cards_declared": snap.get("cards", {}).get("declared"),
        "cards_store": snap.get("cards", {}).get("store"),
        "cards_head": snap.get("cards", {}).get("head"),
        "hf_method": snap.get("hf", {}).get("method"),
        "hf_top_trending": snap.get("hf", {}).get("top_trending"),
        "hf_trend_score": snap.get("hf", {}).get("trend_score"),
        "hf_top_new_30d": snap.get("hf", {}).get("top_new_30d"),
        "hf_new_30d_downloads": snap.get("hf", {}).get("new_30d_downloads"),
        "hf_top_id": snap.get("hf", {}).get("top_id"),
        "hf_top_downloads": snap.get("hf", {}).get("top_downloads"),
        "kev_count": snap.get("kev", {}).get("count"),
        "kev_released": snap.get("kev", {}).get("released"),
        # fluid swan/interop columns (absent when the section didn't run)
        "kev_perimeter": len(snap.get("swan", {}).get("perimeter_recent") or []),
        "kev_rw_share_pct": snap.get("swan", {}).get("ransomware_share_pct"),
        "rw_claimed_today": (snap.get("swan", {}).get("ransomware_sample")
                             or {}).get("claimed_today"),
        "mcp_hosts": (snap.get("interop", {}).get("mcp_trust")
                      or {}).get("unique_hosts"),
        "x402_ok": (snap.get("interop", {}).get("x402_trust")
                    or {}).get("challenge_402"),
    }


def write_csv(raw_rows):
    """Flatten jsonl rows to the canonical counter columns and write timeseries.csv."""
    flat = [row_from(r) for r in raw_rows]
    flat.sort(key=lambda r: r["ts"] or "")
    with open(CSVF, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        w.writerows(flat)


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


def build_feeds():
    """Regenerate every consumable surface from pulse.jsonl: feed.json (full
    series), latest.json (one-GET current state), llms.txt (agent discovery),
    index.html (self-contained human dashboard)."""
    rows = load_rows()
    write_csv(rows)
    sources = {
        "gspc_board": "https://councilof.ai/api/gspc",
        "capsule_index": "https://councilof.ai/measurement-capsules/latest.json",
        "public_root": "https://councilof.ai/root.json",
        "signed_cards": "https://councilof.ai/signed/card_index.json",
        "huggingface": "https://huggingface.co/api/models?sort=trendingScore",
        "cisa_kev": "https://www.cisa.gov/sites/default/files/feeds/"
                    "known_exploited_vulnerabilities.json",
        "did": "https://csoai.org/.well-known/did.json",
    }
    feed = {
        "schema": FEED_SCHEMA,
        "doctrine": "measurement, not endorsement — never a certification; "
                    "a failed fetch is absent, never zero",
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "updated": rows[-1].get("ts") if rows else None,
        "row_count": len(rows),
        "runners": sorted({(r.get("meta") or {}).get("runner", "canonical")
                           for r in rows}),
        "sources": sources,
        "rows": rows,
    }
    with open(FEED, "w") as f:
        json.dump(feed, f, indent=2)
    with open(LATEST, "w") as f:
        json.dump({"schema": "csoai.gspc-pulse-latest/0.1",
                   "license": LICENSE,
                   "attribution": ATTRIBUTION,
                   "feed": "feed.json",
                   "latest": rows[-1] if rows else None}, f, indent=2)
    with open(LLMS, "w") as f:
        f.write("""# GSPC Live Pulse — compounding public measurement evidence

> Autonomous, append-only, multi-runner time series of LIVE measurements from
> public surfaces (GSPC board, measurement capsules, signed cards, public root,
> HuggingFace, CISA KEV + EPSS, DID keys, domain liveness, MCP/x402/ecosystem
> censuses). {n} rows since 2026-11-03, committed to git (tamper-evident).
> {lic} — reuse freely with attribution. Measurement, not endorsement; never a
> certification.

## Feeds (machine-readable; fetch latest.json first)
- [latest.json](latest.json): one-GET current state, schema csoai.gspc-pulse-latest/0.1
- [feed.json](feed.json): full append-only series, schema csoai.gspc-pulse-feed/0.1, with per-row source URLs
- [timeseries.csv](timeseries.csv): flat canonical counters, one row per pulse (pandas/R ready)
- [index.html](index.html): self-contained human dashboard (no build, no JS deps)

## Verify (free, permissionless)
- [HOW-TO-VERIFY.md](https://councilof.ai/signed/HOW-TO-VERIFY.md): pinned-key Ed25519 card verification
- [gspc-verify](https://councilof.ai/gspc-verify): verify any signed card in the browser
- [verification-log.jsonl](verification-log.jsonl): our verification cadence — head-card verdicts, inclusion sweeps, anchor states, each with ts + content sha256
- pulse_freeze.py: the series itself is frozen — canonical row shas, hash-chain, Merkle root, Ed25519-signed manifest (`verify` / `prove --ts` / `self-test`); lane key, trust anchor = this repo's git history
- [RECONCILIATION.md](RECONCILIATION.md): declared vs carried vs store, frozen-framing vs live, anchoring gaps — measuring the measurer

## Reproduce (be a node)
- [PULSE-NODE.md](PULSE-NODE.md): run an independent reproduction node in 60 seconds — same surfaces, same doctrine, your fork = a federation node
- [ci_pulse.py](ci_pulse.py): hourly public-HTTP-only watcher (frozen-gated commits)

## Reports
- [watch/](watch/): security watch reports (swan outlier scan, NEEDS-HUMAN-EYES rules)
- Audit digest: regenerated on every audit run beside the pulse state; feed.json `updated` + the index.html table are the hosted equivalents
- [tools.html](tools.html): free tools & features — feeds, swan watch, interop censuses, verification
- [posts/](posts/): published write-ups (swan watch launch, scaling, doctrine)

## Layer-0 matrix (the join)
- [matrix.json](matrix.json): 34 axes × 9 frameworks × 48 provision seed mappings × industries × regulators × evidence endpoints — schema csoai.layer0-matrix/0.1
- [slices.json](slices.json): 12 industry slices (finance, healthcare, energy…) with regulators + in-scope axes — schema csoai.layer0-slices/0.1
- Cells state evidence and freshness; provision mappings maturity:seed; never conformity verdicts
- [sitemap.txt](sitemap.txt): every public surface in this lane, one URL per line — the self-serve index

## Doctrine (binding on every consumer)
- Every value is traceable to the source URL in feed.json `sources` at row `ts`.
- Absent sections mean the fetch failed (UNREACHABLE) — never read them as zero.
- Slots and measurements are different kinds; never sum or swap them.
- KEV = confirmed exploitation; EPSS = predicted 30-day probability (model-dated; young CVEs lag; absent score = unscored, not zero).
- A 402 or auth challenge is a term sheet, not delivery; unreachable is never FAIL.
- Never a raw downloads leaderboard for models: trending + new-with-traction (30-day cohort) only.

## Sources
- GSPC instruments: https://councilof.ai/api/gspc · capsule index https://councilof.ai/measurement-capsules/latest.json · public root https://councilof.ai/root.json · signed cards https://councilof.ai/signed/card_index.json
- Models: HuggingFace trendingScore + conversational cohort · KEV: CISA feed · EPSS: FIRST/Empirical Security daily bulk file (model-dated)
""".format(n=len(rows), lic=LICENSE))
    data = json.dumps(rows).replace("</", "<\\/")
    with open(INDEX_HTML, "w") as f:
        f.write("""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GSPC Live Pulse — evidence series</title>
<style>
 body{font-family:-apple-system,system-ui,sans-serif;margin:2rem auto;max-width:960px;
      padding:0 1rem;color:#1a1a2e;background:#f7f7fb}
 h1{margin-bottom:.2rem} .sub{color:#555;margin-top:0}
 table{border-collapse:collapse;width:100%;font-size:.85rem;margin-top:1rem;background:#fff}
 th,td{border:1px solid #ddd;padding:.35rem .5rem;text-align:left}
 th{background:#eef;background-position:sticky}
 .tag{display:inline-block;background:#e8e8ff;border-radius:.4rem;padding:.05rem .5rem;
      font-size:.75rem;margin-right:.4rem}
 footer{margin-top:2rem;font-size:.8rem;color:#666}
</style></head><body>
<h1>GSPC Live Pulse</h1>
<p class="sub">An autonomous, append-only, independently-verifiable time series of global
AI-safety, security and model-ecosystem state — measurement, not endorsement; never a
certification.</p>
<p>
 <span class="tag">CC BY 4.0</span><span class="tag">append-only</span>
 <span class="tag">multi-runner</span><span class="tag">tamper-evident git</span>
 <a class="tag" href="https://councilof.ai/gspc-verify">verify cards free</a>
 <a class="tag" href="https://councilof.ai/signed/HOW-TO-VERIFY.md">how to verify</a>
</p>
<p class="sub"><b>Experience:</b> measured continuously since 2026-11-03 by an autonomous
agent lane (6-hourly canonical pulse), cross-checked hourly by an independent public-HTTP
watcher. <b>Expertise:</b> every counter names its instrument and every row carries each
source's own timestamp. <b>Trustworthiness:</b> deltas land in git — the commit log is the
tamper evidence — and <a href="RECONCILIATION.md">RECONCILIATION.md</a> measures the
measurer itself.</p>
<nav style="margin:1rem 0;font-size:.85rem"><b>Jump to your journey:</b>
 agents: <a href="llms.txt">llms.txt</a> ·
 analysts: <a href="timeseries.csv">timeseries.csv</a> ·
 node-operators: <a href="PULSE-NODE.md">PULSE-NODE.md</a> ·
 auditors: <a href="RECONCILIATION.md">RECONCILIATION.md</a> ·
 <a href="watch/">security watch</a> ·
 readers: <a href="posts/2026-11-04-swan-watch-launch.md">CISA KEV explainer</a> ·
 <a href="posts/2026-11-04-one-million-x.md">AI compliance evidence</a> ·
 <a href="posts/2026-11-04-measurement-not-endorsement.md">ransomware 2026</a> ·
 <a href="tools.html">free tools</a></nav>
<div id="stats"></div>
<table id="t"><thead><tr>
<th>ts (UTC)</th><th>runner</th><th>board measured</th><th>capsules</th>
<th>root cards</th><th>cards decl/store</th><th>HF trending / new-30d</th>
<th>KEV · EPSS-top</th><th>domains ok</th></tr></thead><tbody></tbody></table>
<h2>Methodology — measurement, not endorsement</h2>
<ul style="font-size:.85rem">
 <li><b>Models:</b> HuggingFace trending leader + new-with-traction 30-day cohort.
 Never a downloads leaderboard — download rank is ubiquity, not news.</li>
 <li><b>Security:</b> CISA KEV = <i>confirmed</i> exploitation; EPSS = <i>predicted</i>
 30-day probability (model-dated daily file). EPSS ≥ 0.1 on a KEV entry is the priority
 item; young entries score low by model lag; absent score = unscored.</li>
 <li><b>Ecosystem:</b> an auth challenge or 402 is a term sheet, not delivery;
 unreachable is never FAIL; partial rounds are disclosed.</li>
 <li><b>Provenance:</b> per-row source URLs live in <a href="feed.json">feed.json</a>;
 signed artifacts verify under pinned keys — <a href="https://councilof.ai/signed/HOW-TO-VERIFY.md">HOW-TO-VERIFY.md</a>.</li>
</ul>
<footer>Raw git history is the tamper evidence. Machine feeds:
<a href="latest.json">latest.json</a> ·
<a href="feed.json">feed.json</a> · <a href="timeseries.csv">timeseries.csv</a> ·
<a href="llms.txt">llms.txt</a> — every value traceable to its source at ts.
Tools: <a href="tools.html">tools.html</a> · Posts: <a href="posts/">posts/</a> ·
Watch: <a href="watch/">watch/</a>.
License CC BY 4.0 · CSOAI / Council of AI (councilof.ai).</footer>
<script id="data" type="application/json">__DATA__</script>
<script>
const rows=JSON.parse(document.getElementById('data').textContent);
const tb=document.querySelector('#t tbody');
for(const r of rows){
  const b=r.board||{},c=r.cards||{},h=r.hf||{},k=r.kev||{},dm=r.domains||{};
  const ok=Object.values(dm.codes||{}).filter(v=>v[0]==='2').length,
        tot=Object.keys(dm.codes||{}).length;
  const tr=document.createElement('tr');
  tr.innerHTML='<td>'+r.ts+'</td><td>'+((r.meta||{}).runner||'canonical')+'</td>'
   +'<td>'+(b.measured??'—')+(b.slots?' / '+b.slots:'')+'</td>'
   +'<td>'+(r.capsules?r.capsules.total:'—')+'</td>'
   +'<td>'+(r.root?r.root.card_count:'—')+'</td>'
   +'<td>'+((c.declared??'—')+' / '+(c.store??'—'))+'</td>'
   +'<td>'+((h.top_trending||h.top_id)?(h.top_trending||h.top_id)+(h.top_new_30d?' · new30d: '+h.top_new_30d:''):'—')+'</td>'
   +'<td>'+(k.count??'—')+(k.top5&&k.top5.length?' · EPSS-top '+Math.max(...k.top5.map(x=>x.epss||0)).toFixed(2):'')+'</td>'
   +'<td>'+(tot?ok+' / '+tot:'—')+'</td>';
  tb.appendChild(tr);
}
document.getElementById('stats').innerHTML=
 '<p>'+rows.length+' rows · updated '+(rows[rows.length-1]||{}).ts+' UTC</p>';
</script></body></html>""".replace("__DATA__", data))
    return len(rows)


def main():
    if "--rebuild" in sys.argv:
        print("rebuilt feeds; rows=%d" % build_feeds())
        return 0
    try:
        with open(STATE) as f:
            snap = json.load(f)
    except (OSError, ValueError) as e:
        print("state file missing/unreadable:", e)
        return 1
    ts = snap.get("ts")
    if not ts:
        print("state file has no ts")
        return 1

    existing_ts = set()
    if os.path.exists(JSONL):
        with open(JSONL) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing_ts.add(json.loads(line).get("ts"))
                    except ValueError:
                        pass
    if ts in existing_ts:
        print("already recorded:", ts)
        return 2

    with open(JSONL, "a") as f:
        f.write(json.dumps(snap, sort_keys=True) + "\n")

    rows = []
    with open(JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: r.get("ts") or "")
    write_csv(rows)
    build_feeds()
    # freeze the series (chain + merkle + signature) so every append ends frozen
    import subprocess
    try:
        rf = subprocess.run(
            [sys.executable, "-I",
             os.path.join(HERE, "pulse_freeze.py"), "freeze"],
            capture_output=True, text=True, timeout=60)
        print((rf.stdout or rf.stderr).strip() or "freeze: no output")
    except Exception as e:
        print("freeze skipped:", e)

    flat = [row_from(r) for r in rows]
    cur = flat[-1]
    prev = flat[-2] if len(flat) >= 2 else None
    if prev:
        changed = {k: [prev[k], cur[k]] for k in CSV_COLS
                   if k != "ts" and prev[k] != cur[k]}
        print("appended %s; rows=%d; changed=%s"
              % (cur["ts"], len(rows), changed or "none"))
    else:
        print("appended %s; rows=%d; first row" % (cur["ts"], len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
