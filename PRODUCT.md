# PRODUCT — from free evidence to value

The pulse series is free forever (CC BY 4.0, see [LICENSE-EVIDENCE.md](LICENSE-EVIDENCE.md)).
Value is built ON it, in layers that cost nothing to serve and get stronger
with every automated pulse.

## Layer 0 — free surfaces (the wedge, live now)

| Surface | Consumer | Endpoint |
|---|---|---|
| One-GET current state | agents, dashboards | `latest.json` |
| Full series | analysts, training pipelines | `feed.json` (schema `csoai.gspc-pulse-feed/0.1`) |
| Tabular counters | spreadsheets, pandas, R | `timeseries.csv` |
| Agent discovery | LLM agents | `llms.txt` |
| Human dashboard | end users | `index.html` (self-contained, no build) |
| Raw git history | auditors | the commit log itself — tamper-evident |

Raw consumption works today without any hosting:
`https://raw.githubusercontent.com/CSOAI-ORG/clawd-workspace/<branch>/m2/evidence/gspc-pulse/latest.json`
(switch `<branch>` to `main` after the protected-release merge).

## Layer 1 — agent reuse (compounding distribution)

- **MCP**: the GSPC MCP tools remain the canonical read/verify surface; the
  pulse feed is the *historical* complement the tools don't serve.
- **Agent conventions**: `llms.txt` at the lane root tells any agent what this
  is, how to fetch it, and the doctrine rules (UNREACHABLE ≠ 0; slots ≠
  measurements).
- Every downstream agent that builds on the feed becomes a distributor
  (attribution loop) and, if it runs `ci_pulse.py`, a **watcher node**.

## Layer 2 — paid derivatives (the checkout path)

Sold against the free wedge, priced per the estate checkout (£79 Pro /
£299 Enterprise at csoai.org/checkout):

1. **Evidence packs** — frozen-row bundles mapped to EU AI Act / ISO 42001
   style controls (board already carries `art5-safeguard`, `conformance`,
   `regulatory-framework` axes). Generated from the series, sold as documents.
2. **KEV exposure cards** — when a new CVE lands in KEV, a signed card mapping
   affected products to the measured estate. Security/insurance buyers.
3. **Anchored exports** — a series slice plus its Rekor/OTS/XRPL anchor
   receipts, for customers who need timestamped evidence for regulators or
   courts.
4. **Custom surface onboarding** — "we watch your surface on the same
   cadence, same doctrine" — the automation pattern replicated per client.

## Layer 3 — the IP core (what only we have)

- The **longest continuous, multi-runner, signature-anchored time series** of
  these surfaces — uncopyable retroactively.
- The **watcher network**: every fork of this repo that enables the workflow
  is an independent reproduction node feeding the same doctrine.
- **Priority and brand**: CC BY attribution puts the mark on every derivative;
  the doctrine ("measurement, not endorsement") is the trademark-able voice.

## Next build steps (in order)

1. Feeds → a hosted JSON endpoint (GitHub Pages or Cloudflare Worker, free)
   with a stable URL after the default-branch merge.
2. Evidence-pack generator: series slice → signed PDF/HTML bundle (P2 in
   SCALE-PLAN.md).
3. KEV→card webhook (busabase webhooks exist; wire delta → card append).
4. Mirror the lane to the `csoai/evidence-index` HF dataset per estate §10
   (needs HF write token — owner-gated).
