# LAYER-0 HARNESS — consume · connect · join · harness everything we measure

**The gap being closed:** until now every lane polished its own slice. Layer 0
already holds an entire measurement estate — but nothing JOINS it. This is the
connective-tissue plan: one harness that consumes all of it and emits the
matrices every ecosystem surface (domains, MCP tools, HF, checkout, content)
then serves.

## 1 · What Layer 0 already holds (the raw material)

| Estate | Contents | Source |
|---|---|---|
| **34 board axes** | governance · care · safety · jail · swarm · provenance · provenance-controls · custody-disclosure · distribution-integrity · serving-fidelity · harness-fidelity · measurer-integrity · interpretability-reproducibility · detector-interop · cross-reality · effect-binding · claim-maintenance · company-practice · conformance · continuity · interop-conformance · machinery-conformity · lab-practice · openness · regulator-transparency · regulatory-framework · reserve-attestation · watchdog-ingest · art50-marking · ai-adoption-components · labour-components · humanoid-deployment · humanoid-labour-index · axis_A_conformance | `/api/gspc` + signed cards |
| **11,529 capsules / 12 adapters** | contract_parity, self_parity, tool_drift, cross_ledger, operations, public_signals, a2a_card, mill_cross_runtime, busabase, meok, claim_watch | capsule index |
| **428 public-root cards / 335 signed cards** | per-axis measurement cards | root.json + card_index |
| **9 readiness frameworks** | eu-ai-act · dora · nis2 · gdpr · iso-27001 · nist-csf · soc2 · pci-dss · cra — each keyed to published provisions, sector-aware | framework_readiness tool (deterministic, free) |
| **Pulse series (fluid)** | KEV + EPSS + SSVC, leak-site sample, MCP/x402 censuses, domain liveness, HF ecosystem | this lane |
| **Interop censuses** | 2,459 MCP hosts, x402 catalog | interop latest.json |

## 2 · The join model (what "connect" means concretely)

**Matrix:** `axis × framework × provision × industry × regulator × endpoint`

- Each **axis** carries evidence types that satisfy framework **provisions**
  (e.g. `art50-marking` → EU-AI-Act Art. 50 transparency; `watchdog-ingest` →
  NIS2 incident reporting; `reserve-attestation` → DORA operational resilience).
- Each **industry** (finance · healthcare · energy · transport · gambling ·
  education · public-sector · retail · telecoms · legal · media · HR/labour)
  selects a framework subset (sector pointer already in the tool) → a
  **sector slice** of the matrix.
- Each **regulator** gets the provisions THEY enforce, with the axis evidence
  that would satisfy each — the regulator-transparency axis applies to us too:
  we publish our own measurement basis.
- Each **endpoint** (MCP tool, feed, checklist, card verify, HF dataset) is the
  delivery surface for a matrix cell — every cell names its endpoints.

Emitted as: **`matrix.json`** (the whole crosswalk, versioned) + per-slice
static pages (sector × regulator landing pages — the SEO/AEO surface area
multiplies by hundreds: "EU AI Act evidence for finance", "NIS2 reporting
evidence for energy"…).

## 3 · Build order

- **H0 (seed, next lane session):** `harness.py` — consumes board + capsule
  index + frameworks; emits `matrix.json` with the axis↔provision crosswalk
  seeded from the 34 axes × 9 frameworks. Every cell links its evidence
  endpoints (cards, capsules, feed).
- **H1 (slices):** 12 industry slices × 9 regulator pages generated from the
  matrix — static, free-hosted, each with checklist CTAs → checkout. This is
  the "thousands of endpoints" surface-area unlock, ~100+ landing pages from
  one generator.
- **H2 (demographics/endpoints):** practitioner personas (compliance officer,
  model provider, deployer, auditor, journalist, agent developer) each get a
  journey page selecting their matrix slice; MCP tools gain `matrix`/`slice`
  tools so agents consume the join natively.
- **H3 (compounding):** every new capsule/card auto-lands in matrix cells via
  the same verify-on-ingest gate; per-cell "evidence freshness" from the pulse
  series; sector slices become the evidence-pack SKUs (checkout tiers).

## 4 · Doctrine constraints (unchanged)

Cells state evidence and freshness — never scores, never conformity verdicts.
Two-number discipline holds per cell. Sector slices describe what evidence
*would* be measured; they are not legal advice and not conformity assessment.
