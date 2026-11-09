---
title: "CISA KEV Catalog Explained: How to Prioritize Patching When 1,766 Flaws Are Already Being Exploited"
description: "What the CISA KEV catalog is, how its patch deadlines work, and a practical method to decide what to patch first — using KEV status, EPSS scores and exposure, with the current Ivanti VPN case as a worked example."
keywords: [CISA KEV, KEV catalog, patch prioritization, EPSS vs CVSS, Ivanti Connect Secure CVE-2026-111357, BOD 26-04, vulnerability management]
date: 2026-11-04
license: CC-BY-4.0
---

**TL;DR:** The CISA KEV catalog lists 1,766 security flaws that attackers are
*already using* — it is evidence of exploitation, not a prediction. Patch
order should start there, tighten with EPSS scores and exposure, and treat
Ivanti VPN gateways as the current priority case: two brand-new KEV entries
(CVE-2026-111357, CVE-2026-118527) with federal deadlines that have already
passed.

## What is the CISA KEV catalog?

KEV (Known Exploited Vulnerabilities) is the U.S. cybersecurity agency's
official list of flaws with **confirmed exploitation in the wild**. Unlike a
CVSS score (theoretical severity) or EPSS (predicted probability), a KEV
entry means someone is exploiting it today. Under Binding Operational
Directive 22-01, U.S. federal agencies must patch KEV entries by a fixed
deadline; private organizations should treat those deadlines as a free
expert triage.

## A 4-step patch-priority method that works

1. **KEV first.** Anything you run that appears in KEV jumps the queue —
   exploitation is proven, so theoretical severity stops mattering.
2. **Exposure second.** Internet-facing edge devices (VPNs, firewalls, file
   transfer, SSO) outrank internal software. Almost every worst breach of the
   last three years started at an edge appliance, not a workstation app.
3. **EPSS third.** For KEV entries you cannot patch immediately, EPSS
   (Exploit Prediction Scoring System, free from FIRST.org) ranks what
   attackers are most likely to pick up next. Low EPSS never means safe.
4. **Deadline pressure last.** KEV due dates of 1–3 days signal CISA sees an
   active campaign; two Ivanti Connect Secure flaws added 30 October carried
   deadlines of 2–13 November.

## Worked example: the Ivanti VPN chain (October–November 2026)

Three chained Ivanti Connect Secure flaws — CVE-2026-104935,
CVE-2026-111357 (missing authentication), CVE-2026-118527 — give an
unauthenticated attacker root on fully patched VPN gateways, per Volexity
and Rapid7. If you operate ICS or Pulse Secure: patch to 25.1.1.3 /
22.8R2.6 **and assume prior compromise** — an authentication bypass means
attackers may have been inside before the patch. Factory-reset and rotate
credentials where feasible. One of the two, CVE-2026-111357, had a federal
remediation deadline of 2 November 2026 — already passed.

## FAQ

**Is CVSS useless?** No — it ranks severity within a group you already need
to fix. It just can't tell you what attackers actually use. KEV does.
**Where do I get EPSS?** api.first.org, free, no account; batch queries by
CVE. **How often does KEV update?** Every few days, ~5–15 new entries per
week. **Do deadlines apply to me if I'm not a federal agency?** Not legally —
but they tell you how urgent CISA believes it is.

## Free daily KEV tracking (no signup)

We publish an automated daily scan — new KEV entries, patch-deadline
windows, exploit-probability scores, and leak-site ransomware counts — as
open data: [latest.json](../latest.json) (one GET), full series
[feed.json](../feed.json), human dashboard [index.html](../index.html).
Teams that want the same evidence mapped to EU AI Act / ISO 42001 controls
can start at [councilof.ai](https://councilof.ai).

## Related — the free stack

- [Free tools & features](../tools.html) — feeds, daily KEV watch, interop censuses, verification
- [Live dashboard](../index.html) — the evidence series, updated automatically
- [Free data, one GET](../latest.json) · [full series](../feed.json) · [councilof.ai](https://councilof.ai)
