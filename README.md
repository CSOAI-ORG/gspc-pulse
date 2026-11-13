> **Standalone public mirror** of the GSPC live pulse lane (canonical source:
> CSOAI-ORG/clawd-workspace `m2/evidence/gspc-pulse/`). This repo exists so raw
> URLs are public+stable and **fork = watcher node** works for everyone.
> Start: `latest.json` (one GET) -> `feed.json` -> `llms.txt` -> `JOURNEYS.md`.

# GSPC Live Pulse — compounding public evidence series

An autonomous, append-only time series of LIVE measurements taken from public
surfaces, compounding since 2026-11-03. Every row is one pulse: fetched LIVE at
`ts`, never cached, never back-filled.

## What is measured each pulse

| Surface | Source | Fields |
|---|---|---|
| GSPC board | https://councilof.ai/api/gspc | axis_slots, measured, separated, ties, untested |
| Measurement capsules | https://councilof.ai/measurement-capsules/latest.json | total capsules + index as_of |
| Public root | https://councilof.ai/root.json | card_count + as_of |
| Signed cards | https://councilof.ai/signed/card_index.json · /api/cards | declared rows vs store count (two labelled numbers, never reconciled) |
| Open-source models | https://huggingface.co/api/models | top model by downloads + count |
| CISA KEV | https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json | catalog count, dateReleased, top-20 newest ids |
| Swan outlier scan (fluid) | same KEV fetch | ransomware share, flagged-recent, shortest due windows, weekly cadence, CWE tally, perimeter-vendor entries |
| Interop censuses (fluid) | https://councilof.ai/interop/mcp-trust/latest.json · …/x402-trust/latest.json | MCP handshake counts, x402 correct-402 counts |

Doctrine: **measurement, not endorsement; never a certification.** A failed
fetch is recorded as absent/UNREACHABLE for that pulse — a cached number is
never written as live. Slots and measurements are different kinds and are never
summed or swapped.

## Files

- `pulse.jsonl` — append-only, one full snapshot per pulse (JSON per line),
  deduplicated by `ts`. This is the raw evidence record.
- `timeseries.csv` — regenerated from `pulse.jsonl` by the archiver; one compact
  row per pulse with the key counters. Directly loadable for analysis or
  data-generation pipelines.
- `archive_pulse.py` — the archiver. Reads the local pulse state file, appends
  a row if that `ts` is new, regenerates the CSV, prints the delta vs the
  previous row. Exit codes: `0` appended, `1` state missing, `2` ts already
  recorded.

```bash
python3 m2/evidence/gspc-pulse/archive_pulse.py
```

## Schema (timeseries.csv)

`ts, writer, board_slots, board_measured, board_separated, board_ties,
board_untested, capsules_total, capsules_as_of, root_card_count, root_as_of,
cards_declared, cards_store, cards_head, hf_method, hf_top_trending,
hf_trend_score, hf_top_new_30d, hf_new_30d_downloads, hf_top_id,
hf_top_downloads, kev_count, kev_released`

The `hf_*` columns record the 0.3.4 methodology — trending leader plus the
new-with-traction 30-day cohort; `hf_top_id`/`hf_top_downloads` are legacy
pre-0.3.4 columns kept for historical rows and are never refreshed. The CSV
carries the canonical counters only; `pulse.jsonl`/`feed.json` rows additionally
carry additive enrichment keys (`kev.top5` with EPSS/CWE/due-date joins,
`hf.cohort_count`, `hf.trending_license_mix`, ecosystem `mcp`/`x402`/`evidence`
blocks) that arrive with newer writers — downstream consumers should treat
unknown keys as opt-in detail, never as counters.

`*_as_of` / `kev_released` carry each source's own publication timestamp, so
every row is self-describing about how fresh its numbers are.

## Consumer journeys

| You are… | Start here |
|---|---|
| a human scanning state | `index.html` — E-A-T header, series table, methodology |
| an agent / LLM | `llms.txt` (discovery) → `latest.json` (one GET) → `feed.json` (history) |
| an analyst | `timeseries.csv` — flat counters, pandas/R ready |
| a dataset consumer | [Hugging Face dataset](https://huggingface.co/datasets/csoai/gspc-pulse) — JSONL and CSV viewer configs |
| a verifier / auditor | `RECONCILIATION.md` + `verification-log.jsonl` + `PULSE-NODE.md` (run your own node) |
| a compliance officer | `feed.json` ecosystem blocks (`mcp`/`x402`/`evidence`) + DORA-relevant signed cards |
| a security responder | `watch/` reports + `kev.top5` EPSS/CWE/due-date joins in `feed.json` |

## Series freeze and unsigned watcher observations

The canonical M2 runner freezes a **signed prefix**: each committed row in that
prefix is canonically hashed, hash-chained, Merkle-rooted and covered by the
Ed25519 manifest (`pulse-freeze-manifest.json`, `pulse-leaves.json`, `.sig`).
The manifest's `n_rows` is the exact number of signed rows. The public hourly
GitHub Actions watcher has no private signing key; it may append later public-
HTTP observations after that prefix. Those later rows are an **unsigned tail**,
not covered by the signature and not presented as verified.

Verify the boundary yourself: `python3 pulse_freeze.py verify` validates the
signed prefix and reports the unsigned tail; `python3 pulse_freeze.py verify
--require-full` fails unless every row is signed. `prove --ts <ts>` only proves
a timestamp inside the signed prefix. The verifier's self-test tampers with a
signed row and must fail. **Trust anchor:** the public key rides in the
manifest; the private key never enters this repo (it lives in the pulse state
dir) — trust chains to this repo's git history. This is signature-frozen,
**not** ledger-frozen: OTS/Rekor/XRPL anchoring remains owner-gated
(SCALE-PLAN §3.1), and GSPC's pinned keys are unrelated to this lane key.

## Automation

Two independent runners contribute to the observation series (rows carry `meta.runner`); only the canonical runner has authority to extend the signed prefix:

1. **M2 canonical pulse** — a ZCode automation runs the full live pulse
   (gspc-live skill, sections 0–4; GSPC via the MCP tools) every 6 hours, then
   runs `archive_pulse.py` and commits narrowly (lane files only).
2. **Public CI watcher** — `.github/workflows/gspc-pulse-watcher.yml` +
   `ci_pulse.py`: hourly, public-HTTP-only, independent reproduction
   cross-check of the board plus estate surfaces (DID key ids, 20-domain
   first-hop status sweep). Frozen-gated: commits only when the selected
   public-source fields move. It appends an explicitly unsigned observation;
   it never signs or extends the Ed25519 prefix. `--fluid` appends a
   `kind: fluid-scan` row even without frozen movement (swan/interop sections
   ride along but never trip the gate).
   Scheduled runs activate when this workflow reaches the default
   branch; `workflow_dispatch` works now; any fork becomes its own node.
3. **Swan watch** — a ZCode automation (daily 09:00) running `ci_pulse.py
   --fluid`, then `swan_watch.py --rules` (rule engine v2: change-only
   firing — new perimeter entrants, fresh ≤3d due windows, ransomware flag
   flips, 2× cadence surge, catalog release; carried entries are
   observations). Perimeter entries are EPSS-enriched (FIRST.org); a
   ransomware.live leak-site sample rides in each row. Verdict reports go to
   `watch/<date>.md` with a `⚠️ NEEDS HUMAN EYES` stamp — nothing is ever
   sent anywhere; the human decides. All lane fetching goes through
   `fetch_guard.py` (https-only, host allowlist, private-IP refusal, no
   redirects).

## Consume — end users, agents, analysts

Regenerated from `pulse.jsonl` on every pulse by the archiver (`--rebuild` to
force):

| Surface | For | File |
|---|---|---|
| One-GET current state | agents (fetch this first) | `latest.json` |
| Full append-only observations (signed prefix + any explicitly unsigned tail) | pipelines, analysis, audits | `feed.json` (schema `csoai.gspc-pulse-feed/0.1`) |
| Tabular counters | pandas / R / spreadsheets | `timeseries.csv` |
| Agent discovery | LLM agents | `llms.txt` |
| Human dashboard | end users (self-contained, no build) | `index.html` |
| Evidence report | humans + agents (digest, alert timeline, verification cadence) | `REPORT.md` |
| Alert cards | event consumers — one per frozen-delta pulse, sha256-stamped | `alerts.jsonl` |
| Citable evidence pack | end users (rolling, CC BY attribution block) | `packs/pack-latest.md` |
| Verification cadence | auditors — card/inclusion/anchor verdicts over time | `verification-log.jsonl` |
| Reconciliation ("measured the measurer") | auditors, skeptics | `RECONCILIATION.md` |
| Reporting dashboard | humans — alerts + verification rendered | `dashboard.html` |
| End-user journeys | everyone — six concrete journeys with commands | `JOURNEYS.md` |
| Run your own node | federation — 60-second permissionless watcher | `PULSE-NODE.md` |

Reporting layer: `python3 lane_reports.py` (verify_root full recompute +
alerts + report + packs (rolling + ISO-week) + reconciliation + dashboard;
run after every pulse by both runners) · `python3 lane_reports.py --validate`
(quality gate: ts uniqueness/order, JSONL parseability, feed↔row consistency —
exit 3 blocks commits) · `record_verification.py` accepts JSON events on
stdin for the cadence log (per-day dedupe).

Raw consumption needs no hosting:
`https://raw.githubusercontent.com/CSOAI-ORG/clawd-workspace/<branch>/m2/evidence/gspc-pulse/latest.json`

**License:** data CC BY 4.0 — reuse freely with attribution
([LICENSE-EVIDENCE.md](LICENSE-EVIDENCE.md)). **Products & value layers:**
[PRODUCT.md](PRODUCT.md). Doctrine: measurement, not endorsement; never a
certification.

## Provenance

Rows `2026-11-03T05:37:18Z` and `2026-11-03T05:43:53Z` were taken live in an
interactive session before this lane existed and are seeded verbatim from those
fetches (head card `66856aca…` VERIFIED under `did:web:csoai.org#card-attestation-1`
in the 05:43 pulse). Later rows are written by the canonical archiver or the
independent public watcher; `meta.runner` identifies the writer. The manifest's
`n_rows` defines the signed prefix; later watcher rows are explicitly unsigned.

Lane owner: ZCode agent (M2). GSPC data itself is only ever read from the
connected GSPC MCP tools / councilof.ai surfaces — this lane measures, it does
not rebuild GSPC.
