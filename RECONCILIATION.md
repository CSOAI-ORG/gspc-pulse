# Reconciliation — measured the measurer

_Where two independent runners read the same field on the same day and
_disagreed, plus standing framing/live divergences. Disagreement is the
_finding: shown, never silently reconciled. Measurement, not endorsement._

- Disputed field-days: **6**
- `2026-11-03` — cards_store = 335 (manual-reproduction); cards_store = 336 (canonical, gspc-live-zcode)
- `2026-11-04` — cards_store = 335 (manual-reproduction); cards_store = 336 (gspc-live-zcode, gspc-live@0.3.4, gspc-live@0.5.0)
- `2026-11-07` — cards_store = 335 (manual-reproduction); cards_store = 336 (gspc-live-zcode)
- `2026-11-09` — kev_count = 1769 (m4-node); kev_count = 1773 (m4-node)
- `2026-11-13` — kev_count = 1779 (github-actions); kev_count = 1781 (github-actions)
- `2026-11-13` — root_card_count = 442 (github-actions); root_card_count = 452 (github-actions); root_card_count = 458 (github-actions)

## Known standing divergences (two/three labelled numbers)

- Signed card **index declares 335**; **/api/cards count endpoint
  reports 336** (includes the separate-schema cross-border East-West
  card); **/api/state card_chain.bodies_verified_valid reads 335**.
  Three surfaces, three labelled numbers, all honest.
- The head card's **frozen framing says “13 measured of 14
  quotable”**; the live count is **34/34**. Cards cannot be
  re-signed — the live count comes from GET /api/gspc, never from
  inside a card.

## Public-root verification (independent, full recompute)

- Latest: **VALID** at `2026-11-14T02:26:11Z` · {"leaves": 452, "levels": 9, "published": "00985d9a6ec3193f18242b15e8db9d075fd74b77459f4d17f04669fd692ff7e0", "recomputed": "00985d9a6ec3193f18242b15e8db9d075fd74b77459f4d17f04669f
