# DISTRIBUTION — end-user journeys on HF, Kaggle, packages (ready-to-paste)

Every card below is aligned to the current system (live feeds, swan watch,
EPSS/SSVC, doctrine). Copy the blocks to the token-holder; pushes need HF/
Kaggle/PyPI credentials, which this lane does not hold.

## 1 · HuggingFace Space `csoai/gspc-auto-measure` — replace README body with

```
Continuous measurement pipeline for the GSPC governance benchmark estate.
Rotates open-source models against frozen banks, grades deterministically,
returns per-item results — and every public counter it feeds is verifiable
for free.

**Free, no-signup companions**
- Live evidence series (one GET): https://councilof.ai/pulse/latest.json
  (or raw.githubusercontent.com/CSOAI-ORG/clawd-workspace/<branch>/m2/evidence/gspc-pulse/latest.json)
- Full append-only series: feed.json · tabular: timeseries.csv
- Daily KEV watch (EPSS + SSVC + leak-site sample): watch/ reports
- Human dashboard: index.html · agent guide: llms.txt

**Doctrine:** measurement, not endorsement — states only, never a
certification; UNREACHABLE is never read as zero. CC BY 4.0.
Learn: the KEV patch-priority, AI-compliance-evidence and ransomware-2026
explainers live in the pulse `posts/` directory.
```

## 2 · HF dataset `csoai/evidence-index` — append this dataset-card section

```
## Companion: gspc-pulse evidence series
A machine-readable, append-only time series of LIVE public-surface
measurements (GSPC board, capsules, signed cards, CISA KEV + EPSS + SSVC,
HF ecosystem, MCP/x402 censuses, leak-site ransomware sample).
Rows carry meta.runner (independent runners cross-check each other) and each
source's own as_of timestamp. Tamper-evident via git commit log.
Fetch first: latest.json (one GET) → feed.json (schema
csoai.gspc-pulse-feed/0.1) → timeseries.csv (pandas/R ready).
Rules for agents (UNREACHABLE ≠ 0; slots ≠ measurements; never a raw
downloads leaderboard): llms.txt in the same tree.
```

## 3 · Kaggle dataset `gspc-pulse-timeseries` — create with description

```
Daily-updated CSV of LIVE security/AI-ecosystem counters: CISA KEV catalog
size, perimeter-vendor entries, EPSS scores, leak-site ransomware sample,
MCP handshake census, x402 trust probes, GSPC board measurements.
19+ columns, one row per automated pulse, multi-runner cross-checked.
Kernel-ready: load timeseries.csv directly; license CC BY 4.0 (attribute
"CSOAI / Council of AI — councilof.ai"). Updates: replace file on each run.
```

## 4 · Package listings (@csoai/lib2b npm / PyPI MCPs) — one-line blurb

> Includes GSPC measurement/verification clients: verify signed cards and
> Merkle inclusion permissionlessly; consume the free gspc-pulse evidence
> feed (latest.json/feed.json/timeseries.csv). States only — never a
> certification. Docs: councilof.ai · guide: /signed/HOW-TO-VERIFY.md

## Push commands (token-holder runs)

- HF Space: edit README via web UI or `huggingface-cli upload` ; dataset card
  = append section to `README.md` in `csoai/evidence-index` main branch.
- Kaggle: `kaggle datasets create -dir` with the CSV + dataset-metadata JSON
  (description above), then `kaggle datasets version` per update.
- After pushes: add the HF dataset URL as a `copies` entry alongside the
  existing measurement-index copies.
