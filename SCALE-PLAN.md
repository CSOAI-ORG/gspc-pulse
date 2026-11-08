# GSPC Pulse — Relentless Scale Plan
**Mission: measure all frozen, operate on fluid. Compounding public evidence, permissionlessly.**
Written 2026-11-03 from the live state of the estate (34-axis board, 11,529 capsules,
428 root cards, pulse lane compounding every 6h).

---

## STATUS UPDATE — 2026-11-04 (lane execution; gates worked, not bypassed)

- **Gap 1 (anchor loop)**: OTS → **Bitcoin-attested** — the pending calendar proof
  for the 2026-10-28 index was upgraded via public OTS calendars and the attestation
  verified against public blockchain data (block **973564**, merkle root match);
  upgraded proof at `ots-upgrades/` + HF dataset `measurement-index/2026-10-28/gspc-lane-upgraded-proof.ots`.
  XRPL remains **owner-only** (funded estate seed — see `XRPL-OWNER-ACTION.md` one-liner).
- **Gap 4 (reconciliation)**: **DONE** — `RECONCILIATION.md` (capsule arithmetic PASSES;
  2-corpus anchoring gap tracked; three identity layers documented).
- **Gap 5 (feeds)**: feeds + enrichment live; KEV→webhook still open (busabase wiring).
- **Gap 6 (public API)**: **DONE for public consumers** — frozen evidence set mirrored
  to the public HF dataset `csoai/evidence-index` at `gspc-pulse/2026-11-04/`
  (one-GET `latest.json`, full `feed.json`, frozen manifest+sig+leaves, journeys docs).
  The narrow release also merged to main (PR #15 content, build passed), which
  **activates the hourly watcher schedule**; note the repo is private, so its
  `raw.githubusercontent` URLs work only for authed users — HF is the public surface
  until the repo goes public or a Pages/Worker host is added (PRODUCT next-steps).
- **Gap 7 (verification cadence)**: **DONE** — `verify` pulse focus, inclusion sweeps
  (2-corpus finding), head-card verdicts, all logged in `verification-log.jsonl`.
- **P0 schedule**: **ACTIVE** — `gspc-pulse-watcher.yml` now on the default branch (hourly).
- **NEW (this lane)**: the series itself is frozen — `pulse_freeze.py` (hash-chain +
  Merkle + Ed25519 manifest, self-tested tamper guard); lane key, trust anchor = this
  repo's git history; ledger anchoring of our manifest is one owner command away.

---

## 0. The two-layer thesis

- **FROZEN** = anything positioned in time by a signature, Merkle root, anchor, or
  catalog release: signed cards, capsule batches, root.json, DID keys, KEV releases,
  OTS/Rekor/XRPL anchors, model card publication. Frozen facts are **checkable forever**.
- **FLUID** = the delta stream between freezes: new KEV entries, key rotations, capsule
  index root changes, drift, card-count moves. Fluid is where **value is created**
  (alerts, feeds, evidence packs) — but only if the frozen baseline is measured
  relentlessly.

Whoever holds the longest, densest, independently-verifiable time series of frozen
global state holds a dataset **nobody can reconstruct retroactively**. That is the moat.

## 1. Where we are (asset inventory, verified live 2026-11-03)

| Asset | State | Scale value |
|---|---|---|
| Capsule index v0.2 | 11,529 capsules, 12 batches, all signatures VERIFY | the dataset |
| Anchors | Rekor INCLUDED (verifies) · OTS PENDING · XRPL prepared-not-submitted | weak link (§3) |
| verify stack | Ed25519 pinned keys + live DID cross-check (verify_card) | trust root |
| GSPC MCP tools | ~60 public read/verify tools already exposed | distribution |
| Pulse lane | 6 surfaces × every 6h → git (tamper-evident) | seed of the series |
| Free compute | ZeroGPU Space, HF Jobs cpu-basic, Kaggle, M2 Ollama | measurement muscle |
| Distribution | 264 PyPI MCPs, 50 npm pkgs, lib2b, 9 MCP servers/52 tools | channels |
| Estate | councilof.ai live + 15 more domains (several 402/404/no-DNS) | measured surface AND ops backlog |

## 2. The 1,000,000× math (honest version)

A single watcher can never 1,000,000× itself. The multiplier is **permissionless
reproduction + federation**:

```
value ≈ nodes × surfaces × cadence × verifiability
today:  1 node  × 6 surfaces   × 4/day  ≈ 24 frozen measurements/day
P0:     2 nodes × 12 surfaces  × 24/day ≈ 576/day        (×24)
P1:     forks   × 12 surfaces  × 24/day ≈ per-fork 576, n forks ×n (×n·24)
P2:     agent swarm on free GPU + external leaf admission ≈ 10⁴–10⁶/day
```

1,000,000× = from one machine's 24/day to a million measurements/day. The
architecture already admits this: per-batch Merkle roots + `leaves_url` + record
signatures mean **anyone's leaf can be verified inside the index without trusting
them**. Missing piece: a documented admission route (§5 P1).

## 3. What's missing (the honest gap list)

1. **Anchor loop is open** — OTS is PENDING_CALENDAR_COMMITMENT (dates nothing),
   XRPL is PREPARED_NOT_SUBMITTED. Until Bitcoin confirms and XRPL lands, "frozen"
   is only signature-frozen, not ledger-frozen. *Owner-gated: keys/fees (drops are
   pennies; OTS upgrade is free via calendar→bitcoin upgrade).*
2. **Single-machine dependency** — the 6h pulse lives in one ZCode automation on M2.
   *Fixed today: public CI watcher (§5 P0).*
3. **Coverage** — 6 surfaces measured; DID-document key rotation, domain liveness,
   marketplace inventory drift, PyPI/npm drift, A2A card census, safetyof.ai posture
   unmeasured. *DID + estate liveness added today.*
4. **Reconciliation is shown, never tracked** — 335 vs 336 cards; card framing
   "13 of 14" frozen vs 34/34 live. A tracked reconciliation axis would be the first
   "measured-the-measurer" series. *Open wedge.*
5. **No alerting / feeds** — deltas land in git only. No webhook on KEV delta, index
   root change, or key rotation. busabase webhooks already exist to wire this.
6. **No public API** — the lane is a git repo; a JSON feed (GitHub Pages / Cloudflare
   Worker, both free) would make it consumable by agents at scale.
7. **Verification cadence** — verify_card runs on the head card only; no scheduled
   inclusion-proof sweep (verify_inclusion) across random capsules/batches.

## 4. Crown jewels (protect these first)

1. **Pinned-key verify stack** (`#card-attestation-1/2`, `#board-attestation-1` +
   live DID cross-check) — everything else borrows trust from it.
2. **The capsule index + its per-batch Merkle/record signatures.**
3. **The anchor pipeline** (once closed: Rekor + Bitcoin + XRPL = triple-frozen).
4. **The autonomous pattern**: agent + cron + narrow git lane — replicates to all
   15 domains and every future surface at zero marginal cost.
5. **csoai HF org** (`evidence-index` dataset mirror + `gspc-auto-measure` Space) —
   public artifact store per the estate's own §10 policy.

## 5. Roadmap

**P0 — permissionless, $0, done today**
- ✅ Public CI watcher (`ci_pulse.py` + `.github/workflows/gspc-pulse-watcher.yml`):
  hourly, public-HTTP-only, independent reproduction cross-check of the board,
  frozen-gated commits (commits only when frozen layer moves; fluid logged).
- ✅ Estate surfaces added to the pulse: DID key ids, 19-domain liveness sweep,
  reconciliation counts (already), KEV.
- □ Activate schedule: workflows only *schedule* from the default branch — merge
  lane → main via the repo's protected release process (owner/narrow PR), or any
  fork gets the schedule automatically (**fork = watcher node** — the federation
  wedge in one move).

**P1 — this week**
- `PULSE-NODE.md` spec: how any agent/human runs a node and submits Merkle leaves
  (PR or busabase form → daily batch → index inclusion).
- Close the anchor loop: upgrade OTS to Bitcoin-attested; submit the prepared XRPL
  memo (owner-gated).
- Wire KEV-delta → busabase webhook → alert card appended to the lane.
- Public JSON feed of `timeseries.csv` (GitHub Pages).

**P2 — this month**
- Agent-swarm measurement on free compute (HF Jobs cpu-basic, ZeroGPU): run the
  mill adapter itemwise-reproduction at scale; every result = a capsule.
- Inclusion-proof sweep: verify_inclusion over a random sample each pulse.
- Evidence packs: auto-generate EU AI Act / ISO 42001-style measurement bundles
  from frozen rows (the board already has art5-safeguard, conformance,
  regulatory-framework axes to hang them on).

**P3 — compounding**
- External nodes submit leaves; daily index inclusion becomes a public event stream.
- The only long-running, signed, anchored, independently-verifiable time series of
  global AI-safety + security + model-ecosystem state. Pricing rides on top; the
  moat is the series itself.

## 6. Hunt / Learn / Reach / Enhance / Optimise — standing loop (every pulse)

- **Hunt**: each pulse diffs frozen surfaces; any new key id, card count, index
  root, KEV id, or domain status change = an event worth an evidence card.
- **Learn**: weekly reconciliation report (declared vs carried vs store; framing vs
  live; inclusion spot-checks) — publish it; measuring the measurer is credibility.
- **Reach**: every artifact ships through channels already owned: MCP tool, PyPI/npm
  package, HF dataset row, git commit — zero new infrastructure.
- **Enhance**: extend surfaces (A2A census, safetyof.ai posture, npm/PyPI drift);
  one new frozen surface per week is the pace.
- **Optimise**: frozen-gate commits (noise ↓), dedupe by ts, regenerate CSV
  deterministically, anchors before volume (freeze the baseline first).

## 7. Doctrine guardrails (non-negotiable)

Measurement, not endorsement. Never a certification. `UNREACHABLE` ≠ zero — a
failed fetch is recorded as absent, and a cached number is never presented as live.
Slots ≠ measurements — never summed. Every row carries each source's own `as_of`.
Narrow lane commits only; other agents' lanes are never staged.
