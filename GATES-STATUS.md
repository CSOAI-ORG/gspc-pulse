# GATES STATUS — every owner gate, worked to its real edge (2026-11-08)

Goal-mode pass: machine inspected, credentials hunted in standard locations,
agents kicked, levers pulled. What follows is the true state — nothing
overclaimed.

## CLOSED BY THE LANE (no owner action needed)

| Gate | Resolution |
|---|---|
| HF token | **VALID** (renewed OAuth on the desktop) — mirrors running |
| OTS anchor (index v0.2) | Bitcoin-attested (block 973564), verified vs public chain, mirrored |
| Series + curriculum freeze | LIVE, signed, hourly cycle re-kicked and healthy |
| Watcher schedule | ACTIVE on main (CI rows committing — confirmed 11-08T01:20Z row) |
| Release to main | Releases 1 + 2 merged (PRs #15, #20), build green |
| Busabase alerts | CR path live (crqmw1ojymmb5vymgb + stall claim 15fee533) |
| Daily intelligence | daily/YYYY-MM-DD.md auto-compiled by the 06:30 agent |
| Kaggle / Space / extension / skills / actions | all deployed and public |

## REQUIRES THE OWNER — exact effort per gate

1. **XRPL memo** — needs the estate wallet seed. Never store it here; run
   `XRPL-OWNER-ACTION.md`'s snippet from a machine holding the seed.
   *Effort: one command. Cost: a few drops.*
2. **PyPI publish** — `pip install twine && twine upload dist/*` with a token
   from pypi.org (account: create → project token). *Effort: ~5 min.*
3. **Zenodo DOI** — zenodo.org → token → upload `zenodo-deposit.json` set.
   *Effort: ~5 min.*
4. **Smithery** — `gh secret set SMITHERY_API_KEY` (key from smithery.ai
   account), then `gh release create v0.5.0` auto-publishes the MCP server.
   *Effort: ~5 min per the workflow already in-repo.*
5. **Pager URL** — provide any https webhook; a `webhooks_create` rule on
   busabase turns record.created into push delivery. *Effort: one URL.*
6. **6h canonical pulse restart** — the ZCode desktop automation that writes
   enriched 0.5.0 rows (with EPSS/ecosystem enrichment) stalled after
   2026-11-07T12:06Z; claim `15fee533` open. Restart the automation in the
   desktop composer; everything else (hourly freeze/audit/mirror cycle,
   CI watcher, daily batch) is confirmed running.
7. **Vercel** — account blocked (PR checks); unblock at vercel.com to restore
   site deploys. Unrelated to lane correctness.

## DOCTRINE-LOCKED (deliberately not automatable)

- **NEEDS-HUMAN-EYES approvals** (GitLab priority CR `crqmw1ojymmb5vymgb`,
  stall claim): the human decision IS the product. The BFT will escalate;
  it will not impersonate you.
- **Counsel gates** (`counsel_confirmed`): regulator-facing claims require
  counsel, by the estate's own rule.
