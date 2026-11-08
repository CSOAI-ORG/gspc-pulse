# LANE-SOP — gspc-pulse standard operating procedure

The operating contract for this lane. Follow it exactly; deviations are
recorded in `verification-log.jsonl` with a note, never silent. Doctrine is
binding: **measurement, not endorsement; never a certification; UNREACHABLE ≠ 0;
slots ≠ measurements; never a downloads leaderboard; narrow lane commits only.**

## 1. Cadence map (what runs when)

| Cadence | Runner | Does | Evidence |
|---|---|---|---|
| hourly | GitHub Actions `gspc-pulse-watcher.yml` (on main — active 2026-11-04) | public-HTTP reproduction row, frozen-gated commit | `pulse.jsonl` `meta.runner` |
| 6-hourly | M2 ZCode automation | full canonical pulse (sections 0–5 + snapshot) + archive + freeze | `writer: gspc-live@…` rows |
| on append | `archive_pulse.py` | CSV + feeds + surfaces regenerate + **auto-freeze** (`pulse_freeze.py freeze`) | manifest `produced_at` |
| every audit run | `gspc-live-audit.py` | schema, drift, archive health, **freeze integrity (hard-fail on tampering)**, anchor monitor, ecosystem drift, digest | `DIGEST.md`, exit code |
| weekly | reconciliation report | declared vs carried vs store; identity layers; anchoring gaps | `RECONCILIATION.md` |
| per event | `record_verification.py` | verdicts: cards, inclusion, anchors, freezes, upgrades | `verification-log.jsonl` |

## 2. Runbooks

**R1 — full pulse.** Plugin `/gspc-live` (sections 0–5) → write snapshot (only
fetched keys + `ts` + `writer`; preserve foreign keys) → `archive_pulse.py`
(dedupe by ts; exit 2 = already recorded, do not force) → audit green → commit
narrowly (pulse files only; never other lanes) → push.

**R2 — release lane → main.** `git worktree add /tmp/rel -b release/<name> origin/main`
→ extract ONLY lane files into it → commit → push branch → `gh pr create` → wait
for build check → merge (API merge if scope allows; otherwise fast-forward push of
the same reviewed commit from the main checkout). Never merge other lanes' work.

**R3 — freeze & verify.** `pulse_freeze.py freeze` (auto after archive) →
`verify` → spot `prove --ts` → quarterly `self-test`. Tamper alarm (verify exit 1
on same row count): treat as incident I-2.

**R4 — mirror to HF (public surface).** `venv-ots/bin/python` with
`huggingface_hub` + the local token: upload the full public set (see §5) to
`csoai/evidence-index` `gspc-pulse/<UTC-date>/`. HF token expires
2026-11-04T09:57Z — re-auth before mirrors after that.

**R5 — verification cadence.** Every verdict (card, inclusion, anchor, freeze,
upgrade) goes through `record_verification.py --file` (dedupes daily). Nothing
verbal. `INVALID` inclusion results are recorded as tracked facts, not failures.

**R6 — KEV→busabase integration (LIVE 2026-11-04).** Busabase is back online
and the human-eyes path is proven end-to-end: KEV alerts are filed as change
requests in the `csoai` base (`bsemv62m5zc99gcv7f`, "Agents propose; Nick
approves") with `autoMerge: false` so the human decision is structural —
first filed CR: `crqmw1ojymmb5vymgb` (GitLab CVE-2026-97229 priority, 3 of
newest-5 past due). Remaining optional config: a `webhooks_create` rule
(`eventType: record.created`, action `notify_agent`/`webhook`) once the owner
provides a pager URL — that turns approval events into push delivery. The
`kev_webhook.py` HTTP bridge stays available for any external sink
(SSRF-hardened: https-only, public-IP resolution check, no redirects).

## 3. E-A-T checklist (every public surface, every change)

- [ ] Every number carries its source + `as_of` (or the row `ts` that fetched it)
- [ ] Doctrine line present (measurement-not-endorsement / UNREACHABLE ≠ 0 / slots ≠ measurements)
- [ ] Verify links live: HOW-TO-VERIFY.md, gspc-verify, `pulse_freeze.py verify`
- [ ] No downloads leaderboards; trending + new-with-traction only
- [ ] Instruments named (which tool produced which counter)
- [ ] Dates on every claim; version stamps (`writer`) on every row/artifact
- [ ] Journey links resolve **inside the public mirror** too (HF tree = same relative layout)
- [ ] Honest limits stated (private-repo raw URLs; XRPL owner-only; token expiry)

## 4. Journeys QA (run before declaring any release complete)

| Journey | Happy path check |
|---|---|
| Human | `index.html` renders from `feed.json` embedded rows; header links resolve |
| Agent | `llms.txt` → `latest.json` (one GET) → doctrine rules understood |
| Analyst | `timeseries.csv` loads; header covers all canonical counters |
| Verifier | `pulse_freeze.py verify` == 0; `prove --ts <latest>` VALID; `verification-log.jsonl` parses |
| Auditor | `RECONCILIATION.md` claims recompute from public surfaces |
| Compliance | `feed.json` `evidence` block present with `as_of`; `counsel_confirmed` verbatim |
| Responder | `alerts.jsonl` + `kev.top5` EPSS/due joins present on newest row |
| Node | `PULSE-NODE.md` clone-to-commit path runs stdlib-only |

## 5. Public mirror set (HF = the public surface; keep 100% in sync)

`index.html`, `llms.txt`, `latest.json`, `feed.json`, `timeseries.csv`,
`README.md`, `JOURNEYS.md`, `RECONCILIATION.md`, `PULSE-NODE.md`, `LANE-SOP.md`,
`REPORT.md`, `SCALE-PLAN.md`, `XRPL-OWNER-ACTION.md`, `PRODUCT.md`,
`LICENSE-EVIDENCE.md`, `verification-log.jsonl`, `alerts.jsonl`, `pulse-freeze-manifest.json/.sig`,
`pulse-leaves.json`, `ots-upgrades/`, `watch/`, `posts/`, `tools.html`, `dashboard.html`, `packs/`.

## 6. Incidents

- **I-1 UNREACHABLE source**: render absent, never zero; note in footer; retry next cadence.
- **I-2 tamper alarm**: freeze `verify` fails on unchanged row count → stop, do NOT
  refreeze; diff vs git history; record finding + `⚠️ NEEDS HUMAN EYES` in `watch/`;
  repair only from git, then refreeze with a log note.
- **I-3 key compromise**: delete `state/keys/pulse-lane-key.pem` → freeze regenerates
  a new key → manifest `pubkey_fp` changes → log rotation event; old signatures
  remain verifiable against their own manifest.
- **I-4 busabase offline**: webhook path stays dormant (`kev_webhook.py --dry-run`
  only); alerts still land in `alerts.jsonl`; no pager — by design nothing auto-sends.

## 7. Owner-gated register (the only human steps left)

1. XRPL memo submit — `XRPL-OWNER-ACTION.md` one-liner (estate seed).
2. HF OAuth token renewal after 2026-11-04T09:57Z (or a fine-grained lane token).
3. Repo visibility / Pages-Worker hosting if raw URLs must become public.
