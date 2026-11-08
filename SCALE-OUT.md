# SCALE-OUT — the permissionless distribution playbook

How this lane compounds outward without permission, capital, or waiting.
Every row is either DONE (today) or ONE-STEP (a single owner token/command).

## The three multiplier rules (from SCALE-PLAN §2, honestly applied)

1. **Fork = node.** Anyone who clones, enables the watcher workflow, and
   commits rows is an independent reproduction node. `PULSE-NODE.md` is the
   60-second onboarding. Each fork multiplies surfaces × cadence.
2. **PR = leaf admission.** Node rows enter the lane via PR → daily
   consolidation → the frozen series. Per-batch Merkle leaves mean foreign
   rows verify inside the index without trusting the foreigner.
3. **Payloads, not promises.** Every index gets a ready-to-submit artifact in
   `discovery/` — never a description of what we'd submit.

## Channels — state as of 2026-11-04

| Channel | Lever | State |
|---|---|---|
| GitHub (topics, releases) | topics set (20); release → Smithery auto-publish | DONE / one `gh release create` + SMITHERY_API_KEY |
| HuggingFace (dataset + Space + cards) | public mirror 40+ items; council-OS Space live; tagged card | **DONE** |
| Kaggle | measurement-engine kernel | **DONE** (v1 live, forks = nodes) |
| MCP Registry / PulseMCP / Glama / mcp.so | `discovery/mcp-server.json` | payload ready → registry PR / forms |
| A2A registry / cards | `discovery/a2a-agent-card.json` | payload ready → estate `.well-known` (owner) |
| x402 bazaar | `discovery/x402-resource.manifest.json` + engine already 402-live on 5 obligations | payload ready → owner deploys endpoint |
| Anthropic Agent Skills | `anthropic-skill/SKILL.md` | **DONE** (importable) |
| ChatGPT Actions / Apps | `chatgpt-action-openapi.json` | Action importable; Apps = owner dev account |
| Browser stores (Sentinel) | `extension/` MV3 | unpacked install today; store listing = owner account |
| PyPI | `pyproject.toml` + dist | owner token → `twine upload dist/*` |
| Zenodo (DOI) | `zenodo-deposit.json` | owner token → 5 minutes |
| RSS readers | rss.xml | **DONE** |
| TV / web embeds | council-OS Space iframe (`inside/embed.html`) | **DONE** |

## The compounding loop (what makes scale exponential, not linear)

Every node's rows are **frozen by the same grammar** → verifiable by the same
three-file check → crosswalked into the same obligations → taught by the same
academy → alerted into the same human loop. New nodes increase surface ×
cadence; new indexes increase distribution; new obligations increase the
moat matrix; and every one of them is measured by the very instruments we
publish. The engine eats its own frontend.

## Cadence ownership (who runs what — currently self-running)

- hourly CI watcher (GitHub, on main) — running
- 6-hourly canonical pulse (M2 automation) — running
- daily 06:30 batch (`com.csoai.gspc-daily`): rss → curriculum freeze →
  verify_remote → audit → mirror — running
- weekly reconciliation (RECONCILIATION.md refresh) — manual trigger today
- per-event verification + claims + BFT — on demand, ledgered
