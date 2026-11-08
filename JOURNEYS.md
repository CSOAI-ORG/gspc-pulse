# JOURNEYS — what each end user does with the pulse

Every journey works on public data with zero hosting, today. Start at
`latest.json`; everything links from there.

> **Public path note (2026-11-04):** the release to `main` activated the hourly
> watcher; the repo itself is private, so `raw.githubusercontent.com/.../main/...`
> works for **authed** users only. The fully-public mirror of this lane lives at
> `https://huggingface.co/datasets/csoai/evidence-index/tree/main/gspc-pulse/2026-11-04`
> (frozen manifest + sig + leaves included) — prefer it for public consumers.

## 1. Security analyst — "what just became exploitable?"

```bash
curl -s https://raw.githubusercontent.com/CSOAI-ORG/clawd-workspace/main/m2/evidence/gspc-pulse/alerts.jsonl | grep kev_new_ids
```
- `alerts.jsonl` emits `kev_new_ids` the moment a CVE enters the KEV top-20.
- `REPORT.md` shows the frozen-delta timeline; `dashboard.html` renders it.
- Swan watch adds the fluid layer (ransomware flags, perimeter vendors, due
  windows) with `⚠️ NEEDS HUMAN EYES` stamps — nothing auto-sends anywhere.
- Depth: KEV `top20` in every row since 2026-11-03 = reconstructable
  exposure timeline.

## 2. Compliance officer — "prove the state of these systems on a date"

1. Open `packs/pack-latest.md` (rolling) or `packs/pack-YYYY-WNN.md` (week slice).
2. Every value carries its source URL + `as_of` — cite directly.
3. Need it anchored? The capsule index ties to Rekor (INCLUDED, proof
   verifies); OTS/XRPL state per `latest.json` `anchors`.
4. Full audit trail: `verification-log.jsonl` (card/inclusion/root verdicts
   over time) + git history (tamper-evident).

## 3. Agent developer — "give my agent trustworthy current state"

```bash
curl -s .../latest.json   # one GET; schema, license, doctrine included
```
- Point your agent at `llms.txt` first — it encodes the rules (UNREACHABLE ≠
  0; slots ≠ measurements) so downstream agents don't misuse the data.
- Full history: `feed.json` (schema `csoai.gspc-pulse-feed/0.1`).
- Become a node: see PULSE-NODE.md — 60 seconds, stdlib only.

## 4. Auditor / skeptic — "why should I trust this?"

You shouldn't — you should **verify**:
1. `python3 lane_reports.py` recomputes the entire 428-leaf public root from
   the published leaves under the published rule (first run: **VALID**,
   recorded `2026-11-04`). Independent of any tool.
2. `RECONCILIATION.md` lists every place runners disagree (335 vs 336;
   frozen "13 of 14" framing vs live 34/34). Disagreement is shown, never
   hidden.
3. Every row carries its runner; every alert card carries its own sha256;
   git history is the tamper-evident log.

## 5. Researcher / data engineer — "give me the series"

```python
import pandas as pd, urllib.request, io
u = "https://raw.githubusercontent.com/CSOAI-ORG/clawd-workspace/main/m2/evidence/gspc-pulse/timeseries.csv"
df = pd.read_csv(io.BytesIO(urllib.request.urlopen(u).read()))
```
- CC BY 4.0: reuse commercially, attribute *“GSPC live pulse — CSOAI /
  Council of AI (councilof.ai)”* (LICENSE-EVIDENCE.md).
- JSONL is the superset (fluid layers included); CSV is the counters.

## 6. The owner of any measured surface — "you're measuring me; what now?"

The doctrine protects you too: we measure states, we never grade. If your
surface moved and the alert timeline recorded it, that record is
timestamped, source-linked and honest — including the pulses where your
site was down (UNREACHABLE is recorded as absent, never as zero).
Corrections welcome via PR; erratums are data, not embarrassments.
