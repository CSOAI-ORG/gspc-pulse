# MANIFEST — lane ownership & open-gap ledger

## File ownership (multi-agent convention, agreed format)

| Files | Owner lane | Notes |
|---|---|---|
| `swan_stats.py`, `swan_watch.py`, `fetch_guard.py`, `ci_pulse.py` (watch parts), `watch/`, `posts/`, `tools.html`, `DISTRIBUTION.md`, `MANIFEST.md` | CLAUDE/ZCode | change-only rule engine, egress guard, EPSS/SSVC enrichment |
| `archive_pulse.py` (shared generator), `index.html`, `llms.txt`, `feed.json`, `latest.json`, `timeseries.csv` | shared | generated surfaces — edit the generator, never the output |
| `PULSE-NODE.md`, `RECONCILIATION.md`, `verification-log.jsonl`, `lane_reports.py`, `engine.py`, `verify_remote.py` | other lanes | do not modify without coordinating |

Rule: commit only your owned files; if you must touch a shared file, do it additively and say so in the commit message.

## Open gaps (found 2026-11-03/04, with owners)

**Owner-gated (human/keys/server):**
1. Merge lane branch → `main` — activates raw URLs, CI watcher, search-visible hosting
2. Host lane at a councilof.ai subdomain + Stripe £499–4,990 tiers + evidence packs
3. XRPL anchor submit · OTS calendar commitment (server pipeline)
4. MCP census cap 500 → 2,459 (server config)
5. Record-or-mark the 980 unrecorded operations SHA256s (server data)
6. Bring M4 back online (SSH 192.168.50.105 timing out 2026-11-03/04)
7. ~~HF dataset card + series push~~ **DONE 2026-11-08**: card section added and latest.json/timeseries.csv/llms.txt/index.html live at hf.co/datasets/csoai/evidence-index/gspc-pulse/ (authed Nicholastempleman). REMAINING: HF Space README body swap; Kaggle dataset (stored key is read-only — 401, needs fresh token from kaggle.com/settings); package-listing blurbs

**In-lane (any lane, coordinate via this manifest):**
8. Rule-b refinement: fresh ≤3d due windows outside the historical top-5 are missed — evaluate perimeter entries' own dueDates (needs `compute()` to carry `dueDate` on perimeter entries)
9. Add `swan_watch.py --rollup` to the daily watch automation prompt (Monday runs)
10. Cross-runner reconciliation automation — coordinate with the lanes owning `RECONCILIATION.md` before building
11. JSONL sharding past ~5k rows; witness cosigning of the series root (P2 bridge)

**Done this session (for the record):** swan watch v2 (change-only rules, per-CVE state), EPSS + SSVC + leak-site enrichment, egress guard, 3 SEO posts, tools page, dashboard/tools/posts interlink mesh, CSV fluid columns, weekly rollup, distribution cards, first NEEDS-HUMAN-EYES escalations (Ivanti UTA0576 chain; CVE-2026-111357 BOD due passed 2026-11-02).
