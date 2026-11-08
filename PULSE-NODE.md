# PULSE-NODE — run an independent reproduction node

Anyone — human or agent — can run a pulse node against the same public surfaces
and feed the same doctrine. Permissionless, $0, no keys, no registration.
Attribution: CC BY 4.0 — cite "GSPC live pulse — CSOAI / Council of AI".

## What a node does

1. **Fetch** the public surfaces (HTTP GET, no auth):
   - `https://councilof.ai/api/gspc` (board totals)
   - `https://councilof.ai/measurement-capsules/latest.json` (capsule index)
   - `https://councilof.ai/root.json` (public root)
   - `https://councilof.ai/signed/card_index.json` (signed cards)
   - `https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=10`
     (+ the 30-day conversational cohort — never a downloads leaderboard)
   - `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`
2. **Record** one row per pulse: every value carries its source's own `as_of`;
   a failed fetch is **absent (UNREACHABLE)**, never zero.
3. **Append** to your own `pulse.jsonl` (append-only, dedupe on `ts`) and commit
   to git — the commit log is your tamper-evidence.
4. **Diff** the frozen layer vs your previous row; speak up only when it moves.

## Doctrine (non-negotiable)

- Measurement, not endorsement; never a certification.
- Slots ≠ measurements — never summed or swapped.
- `UNREACHABLE` ≠ 0. A cached number is never presented as live.
- Two labelled numbers from two surfaces are shown side by side, never reconciled.
- Never a raw downloads leaderboard for models — trending + new-with-traction only.

## Submit leaves back (optional, permissionless wedge)

Per-batch Merkle leaves + `leaves_url` + record signatures mean **your row's
checkable facts can be verified inside the index without trusting you**. Current
admission route: open a PR adding your node's row file under `m2/evidence/gspc-pulse/nodes/<your-node>/`
(rows only, same schema, `meta.runner` = your node name) — a daily consolidation
batch carries accepted rows toward index inclusion. Overage: a busabase form
route is planned; until it ships, PRs are the only admission path.

## Verify anything

- Signed cards: `verify_card` / https://councilof.ai/gspc-verify (free, pinned keys)
- Public-root inclusion: `GET /api/proof?sha=<leaf-sha>` (INVALID = not a leaf of
  that root, never "forged")
- Anchors: Rekor log entries + OTS files beside each daily index (PENDING ≠ attested)
- **Full-root recompute** (no MCP needed): `python3 m2/evidence/gspc-pulse/lane_reports.py`
  recomputes the ENTIRE Merkle tree from `root.json`'s published `card_sha256`
  leaves under the published node rule (raw 32-byte digests, Bitcoin-style
  odd-node duplication, count-mismatch rejection per the CVE-2012-2459 closure)
  and compares to the published root. First independent run: **VALID** —
  428 leaves, 9 levels, recorded in `verification-log.jsonl` 2026-11-04.
  Every node can and should run this every pass.

## Node operations (lane tooling)

- `ci_pulse.py` — fetch + frozen gate (call with `--fluid` for scan-only rows)
- `lane_reports.py` — verify_root + alerts + REPORT + packs (rolling + ISO-week)
  + RECONCILIATION.md + dashboard.html
- `lane_reports.py --validate` — quality gate (ts order/uniqueness, JSONL
  parseability, feed↔row consistency); exit 3 must block commits
- `record_verification.py` — append verdicts to `verification-log.jsonl`
  (per-day dedupe; INVALID entries are findings, not failures — log them)
- Additional node surfaces: `…/v0.2/anchors.json` (freeze-event watch:
  OTS→Bitcoin and XRPL→submitted), `https://csoai.org/.well-known/did.json`
  (key-rotation watch), `/api/state` store counter, 19-domain first-hop sweep

## Minimal node (60 seconds)

```bash
git clone https://github.com/CSOAI-ORG/clawd-workspace && cd clawd-workspace
python3 m2/evidence/gspc-pulse/ci_pulse.py        # public-HTTP-only reproduction row
git checkout -b pulse-node-$(hostname) && git add m2/evidence/gspc-pulse/pulse.jsonl
git commit -m "pulse-node: <name> <ts>"            # your fork = your node
```

Enable the workflow on your fork and GitHub Actions runs it hourly — your fork is
a federation node (SCALE-PLAN §5 P0).
