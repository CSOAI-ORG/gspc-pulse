# gspc-pulse — standalone public mirror

This repository is the **standalone public mirror** of the GSPC live pulse
evidence lane (canonical source: CSOAI-ORG/clawd-workspace,
`m2/evidence/gspc-pulse/`). It exists so that:

1. **Raw URLs are stable and public**: `raw.githubusercontent.com/CSOAI-ORG/gspc-pulse/main/latest.json`
2. **Fork = watcher node** works for everyone (PULSE-NODE.md) — forks of this
   public repo get the hourly CI workflow immediately.
3. The series is independently discoverable in GitHub search/topic indexes.

Start here: `latest.json` (one GET) → `feed.json` (full series) →
`llms.txt` (agent rules) → `JOURNEYS.md` (six end-user journeys) →
`index.html` / `dashboard.html` (dashboards).

Doctrine: measurement, not endorsement; never a certification;
UNREACHABLE is never zero; slots are not measurements. CC BY 4.0.
