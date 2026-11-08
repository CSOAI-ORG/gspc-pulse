# License — the GSPC pulse evidence series (data)

**The data in this lane** (`pulse.jsonl`, `timeseries.csv`, `feed.json`,
`latest.json`, and every feed built from them) is **dual-licensed**:

> **CC BY 4.0 OR CC0-1.0** — you choose. CC0 waives all rights for maximal,
> friction-free reuse (public-domain dedication); CC BY 4.0 keeps attribution
> flowing. SPDX: `CC-BY-4.0 OR CC0-1.0`.

Under **Creative Commons Attribution 4.0 International (CC BY 4.0)**:

- You may share and adapt the data for any purpose, including commercially.
- You must give appropriate credit, link the license, and indicate if changes
  were made: *“GSPC live pulse — CSOAI / Council of AI (councilof.ai),
  CC BY 4.0”*.
- No warranty. The data is measurement, not endorsement, and never a
  certification; each value carries its source URL and the `ts` at which it
  was observed.

**Code in this lane** (`archive_pulse.py`, `ci_pulse.py`) follows the
repository's existing LICENSE.

## Why attribution (the IP mechanics)

1. **Attribution compounds the brand.** Every reuse — a paper, a dashboard, an
   agent, a training set — carries the source forward. Openness is the moat;
   the requirement is credit, not permission.
2. **First-party provenance cannot be copied.** Anyone can copy today's row;
   nobody can reconstruct the series that was observed live and kept
   append-only since 2026-11-03. The IP is the *series and its continuity*,
   and every derivative that cites it increases its authority.
3. **Anchored priority.** Rows tie to surfaces whose bytes are
   signature-frozen and (per the capsule index) Rekor-included — so the series
   doubles as timestamped evidence of what a public surface said at a moment.

## What is NOT licensed away

Derivative *products* (evidence packs, API access, anchored exports, support)
are separate commercial offerings — see [PRODUCT.md](PRODUCT.md). The
measurements themselves stay free forever, per the estate's own doctrine
(root.json: "Free; not paywalled").
