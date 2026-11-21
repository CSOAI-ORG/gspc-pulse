# YEAR-PLAN — the evidence estate, Dec 2026 → Nov 2027

**Operating rhythm (already live, never stops):** M2 canonical pulse 6h ·
public-repo watcher hourly · m4-node hourly (MacBook; micro2 offline since
2026-11-14, rejoin pending) · swan watch daily · lane_reports hourly
(REPORT/dashboards/packs) · weekly reconciliation · weekly pack.

**Doctrine (unchanged all year):** measurement, not endorsement; never a
certification; UNREACHABLE is never zero; slots are not measurements.
**Every item below is an execution target, not a wish** — each maps to a
file, workflow, or automation that already exists.

---

## Q1 — FREEZE EVERYTHING (Dec · Jan · Feb)

**December 2026 — consolidation**
- W1: anchor sweep — every daily index since 2026-10-28 fetched, `ots upgrade`
  run, Bitcoin blocks recorded in verification-log (start: block 973564/973528 done).
- W2: `councilof.ai/pulse/latest.json` route decision — either owner deploys or
  every doc/gist re-points to the public raw URL (audit + fix all references).
- W3: PR-merge CI on clawd-workspace main verified firing; raw/main URLs canonical.
- W4: year-pack v1 — first annual evidence pack (packs/pack-2026.md), Zenodo
  draft finalized awaiting token.

**January 2027 — verification depth**
- W1-2: inclusion-proof rotation — verify a different public-root leaf every
  day (442+ leaves → full coverage cycle every ~15 months), logged per day.
- W3: reconciliation report #13-#17 published weekly (disputes trend chart in
  dashboard.html).
- W4: M4 MacBook + micro2 node health audit; micro2 rejoin or replacement node
  spec (any estate box, 60-second bootstrap per PULSE-NODE.md).

**February 2027 — surface expansion I**
- Weekly +1 frozen surface (candidate list: certificate-transparency logs,
  npm/PyPI package censuses for the estate's own 264+50 packages, HF model-card
  drift, DID rotation watch on all estate domains).
- Q1 GATE: anchor loop fully closed (OTS Bitcoin ✓, XRPL mainnet memo = the
  one owner command; escalate weekly until done).

## Q2 — DISTRIBUTION (Mar · Apr · May)

**March 2027 — registry + packages**
- Week 1: MCP registry publish (needs owner DNS TXT on councilof.ai → then
  `mcp-publisher`, payload ready at discovery/mcp-server.json).
- Week 2: PyPI `gspc-pulse` feed-client package (needs owner PYPI token).
- Week 3: npm `@csoai/gspc-pulse` (needs fresh npm token; current E401).
- Week 4: Smithery listing (needs SMITHERY_API_KEY) → release v0.5.0 auto-published.

**April 2027 — content flywheel**
- Weekly: one posts/ article published to HF community + linked from RSS.
- Daily KEV watch reports (swan) compiled into monthly security digest.
- Kaggle kernel v2 push (needs fresh kaggle.json — current key 401).

**May 2027 — federation scale**
- Target: 5 independent nodes (recruit via PULSE-NODE.md; forks already work).
- Node admission automation: PR template + auto-validation workflow for
  nodes/<name>/ submissions.
- Q2 GATE: series mirrored to ≥4 indexes (GitHub, HF, Kaggle, Zenodo-when-token).

## Q3 — DEPTH (Jun · Jul · Aug)

**June 2027 — measurement freshness**
- Drive measurement_age: 14 axes at 91+ days → re-measure the oldest block
  (owner-gated: requires live runs on the estate).
- Weekly: measurement_age distribution tracked in the series (board schema
  already carries it).

**July 2027 — evidence packs as product**
- AI-Act / ISO-42001 evidence pack generator v2 (from frozen rows → signed
  bundles via csoai_sign when backend returns; else hash-chained).
- KEV→exposure-card automation v2 (kev_webhook.py wired to a live endpoint).

**August 2027 — annual freeze**
- Q3 GATE: 365-day continuous series anniversary — annual pack, annual
  reconciliation report, annual root recompute marathon (every leaf).

## Q4 — COMPOUND (Sep · Oct · Nov)

**September–November 2027**
- Third-party node recruitment round 2 (target: 10 nodes).
- Cross-estate: extend the same pulse grammar to every councilof.ai surface.
- Year-2 plan drafted from the year-1 evidence (the series decides the plan).

---

## STANDING RULES

1. Every automated fire already does: fetch LIVE → delta → append → verify →
   validate gate → narrow commit. Never back-fill; never cache-forward.
2. Credential-gated items escalate WEEKLY in the fire report until the owner
   drops the token — one line, no nagging beyond that.
3. Anything unfinished goes into the next fire's prompt, not a private list.
4. The series itself is the source of truth for what happened. Plans are
   data; evidence is proof.
