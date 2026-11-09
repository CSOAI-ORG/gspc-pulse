---
title: "AI Compliance Evidence: How to Prove What Your AI Actually Does (EU AI Act & ISO 42001)"
description: "Regulators and enterprise buyers now ask for evidence, not promises. Here is what AI-governance evidence means, why self-attestation fails audits, and how verifiable public measurement — signed cards, Merkle proofs, public timestamps — closes the gap. Free checklists included."
keywords: [EU AI Act evidence requirements, ISO 42001 audit evidence, AI governance, AI vendor due diligence, verifiable AI measurement, AI compliance checklist]
date: 2026-11-04
license: CC-BY-4.0
---

**TL;DR:** Under the EU AI Act and ISO 42001, "trust us" is no longer an
answer — conformity depends on evidence that a third party can re-check. The
fix is measurement whose proof travels with it: signed measurement cards,
Merkle commitments, and public timestamps anyone can verify without asking
the vendor for permission.

## What counts as "evidence" under the EU AI Act and ISO 42001?

Both frameworks ask the same practical question: *can you show* the system
behaves as declared — logging, oversight, accuracy, incident handling? What
fails in practice: a PDF policy. What passes: measurements tied to a method,
a date, and a party — re-checkable by an auditor without trusting the
subject.

## Why self-attested AI benchmarks keep failing

Vendor benchmarks are re-run by nobody and drift silently. The pattern that
holds up under diligence has three properties, borrowed from how the web
secures certificates:

1. **Signed measurement cards** — every result is a small, canonical,
   Ed25519-signed object; the signature is checked against a pinned public
   key, so tampering breaks it.
2. **Merkle commitments** — thousands of results compress into one root
   hash; any single result can be proven included without revealing the
   rest.
3. **Public timestamps** — the root is anchored in independent ledgers and
   transparency logs (Rekor, OpenTimestamps), so nobody can quietly rewrite
   history.

Anyone can verify all three in a browser — no account, no vendor API:
see [HOW-TO-VERIFY](https://councilof.ai/signed/HOW-TO-VERIFY.md).

## What this means for buyers and vendors

- **Buyers:** add one line to vendor questionnaires — *"show a signed,
  timestamped measurement, or say 'none'."* The answers sort the market
  fast.
- **Vendors:** publish one verifiable measurement per claim you make. It is
  cheaper than one diligence escalation.
- **Everyone:** run the free readiness checklists (EU AI Act, DORA, NIS2,
  GDPR, ISO 27001, NIST CSF, SOC 2, PCI DSS, CRA) to see exactly which
  evidence a control would demand — via the GSPC tools or
  [councilof.ai](https://councilof.ai).

## FAQ

**Is a signed benchmark a certification?** No — it proves the bytes are
authentic and dated, not that the product is good. Verification and
certification are different acts. **Does this satisfy notified bodies?** It
gives them re-checkable inputs; conformity assessment remains its own
process. **What does it cost?** The evidence series and checklists are free
and open-licensed.

## Free, verifiable starting points

Live AI-measurement time series (one GET): [latest.json](../latest.json) ·
full open series: [feed.json](../feed.json) · verification guide:
[HOW-TO-VERIFY](https://councilof.ai/signed/HOW-TO-VERIFY.md) · readiness
checklists and paid evidence packs:
[councilof.ai](https://councilof.ai).

## Related — the free stack

- [Free tools & features](../tools.html) — feeds, daily KEV watch, interop censuses, verification
- [Live dashboard](../index.html) — the evidence series, updated automatically
- [Free data, one GET](../latest.json) · [full series](../feed.json) · [councilof.ai](https://councilof.ai)
