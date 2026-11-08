# ALIGNMENT — gspc-pulse lane ↔ M2/M4 ecosystem

Aligned to `m2/docs/ECOSYSTEM-ALIGNMENT.md` (machine roles, boundary rule)
and `m2/docs/MASTER-PLAN-ALL-DOMAINS.md` (domain status). Checked live
2026-11-08.

## 1. Machine-role alignment (boundary rule compliance)

- **This lane runs on M2** (safety/AI domain controller) — correct placement:
  it measures AI-safety surfaces (GSPC board, capsules, KEV, MCP/x402
  censuses) and produces governance/compliance evidence (DORA/CRA/AI-Act
  obligation bundles) — squarely M2's charter.
- **M4 (meok-only)** consumes, never produces, this lane's evidence: via
  Ollama (M4 :11434) + `inside/Modelfile.gspc-analyst` (GSPC-analyst
  persona), via the MCP endpoint for sov3/council deliberation, and via the
  public mirror (no cross-machine coupling required).

## 2. Domain alignment

The lane's `domains` block measures the estate's own surfaces (councilof.ai,
csoai.org, the trade/vertical domains, safetyof.ai) — MASTER-PLAN's LIVE/DEAD
domain table is independently reproduced by every pulse row. Domain state
changes (200→ERR) are frozen-delta events and claim-ledger candidates.

## 3. Integration routes (declared, per boundary)

| Direction | Route | Status |
|---|---|---|
| M2 lane → public | HF mirror + raw main + Space + Kaggle + discovery payloads | LIVE |
| M4 council/sov3 → lane evidence | `councilof.ai/mcp` instruments + latest.json | LIVE (verify in M4 = owner step) |
| M4 Ollama → GSPC-analyst | Modelfile + dated snapshot | LIVE (build: `ollama create gspc-analyst`) |
| M4 MCP marketplace publishing | Smithery release lever | owner key pending |
| lane → busabase academy/alerts | CRs + docs (busabase MCP when connected) | LIVE (proven 11-04) |
| Desktop Commander fleet | `com.csoai.gspc-daily` LaunchAgent + dc-bridge agents | LIVE (batches ran 11-05→11-07 autonomously) |

## 4. Observed drift (filed to claims ledger, 2026-11-08)

- Canonical 6h pulse automation stalled after 2026-11-07T12:06Z — hourly CI
  + daily batch continued; automation-lane restart required. Filed as an
  open claim: the measurer measures its own maintenance gaps too.

## 5. Doctrine

Aligned with the estate's single source of truth: measurement, not
endorsement; UNREACHABLE ≠ 0; slots ≠ measurements; narrow lane commits;
M4 = meok, M2 = safety. This lane never crosses the boundary — it publishes
evidence and personas that the other side consumes on its own schedule.
