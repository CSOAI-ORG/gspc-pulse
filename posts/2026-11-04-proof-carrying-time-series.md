# Proof-carrying time series: the pulse as public infrastructure

*CSOAI / Council of AI — 2026-11-04 · CC BY 4.0 OR CC0-1.0*

## The claim

A time series nobody can verify is an opinion with a database. A time series
anyone can verify **from anywhere, with no credentials** is infrastructure.
The GSPC live pulse is the second kind: an append-only, multi-runner,
hash-chained, Merkle-rooted, Ed25519-signed record of global AI-safety,
security and model-ecosystem state — verifiable in one command against a
public mirror.

## The design, in seven properties

1. **Layer-0 free forever.** The measurements are CC BY 4.0 OR CC0-1.0. No
   registration, no key, one GET: `latest.json`.
2. **Independent reproduction.** Two runners (a 6-hourly canonical agent, an
   hourly public-HTTP watcher on the default branch) measure the same public
   surfaces. Rows carry their runner. Disagreement is a finding, not a bug.
3. **Frozen, not remembered.** Every append ends frozen: canonical row
   sha256s, hash-chained from a genesis constant, Merkle-rooted over sorted
   leaves, the manifest Ed25519-signed. `verify` in one command;
   `prove --ts` for any single row; a self-test injects a lie and must catch it.
4. **Verify from anywhere.** Three files from a public mirror (manifest,
   signature, leaves) let anyone on the internet recompute chain, root and
   signature — no repo, no keys. `REMOTE SERIES VERIFIED` is a property, not
   a promise.
5. **Enriched, honestly.** KEV = confirmed exploitation; EPSS = predicted
   30-day probability (model-dated); a challenge is a term sheet, not
   delivery; unreachable is never zero. Every enrichment names its instrument.
6. **Measuring the measurer.** A reconciliation report tracks declared vs
   carried vs store counts, frozen-vs-live framings, identity layers and
   anchoring gaps — including our own. Trustworthy systems publish their own
   gaps.
7. **Discovery-complete.** The series is listed where its subjects live: MCP
   registry, A2A cards, x402 manifests, GitHub topics, HF datasets — so the
   ecosystems we measure can find, consume, and re-verify us. A
   self-measuring distribution loop.

## Why this shape

Certificate Transparency normalized "publicly auditable TLS". Signal
normalized "verifiable messaging". We apply the same discipline to
*AI-safety state*: a signed, append-only, publicly auditable log of what the
world's safety surfaces looked like, over time, from independent runners.
The moat is not the dashboard — it is the **longest densest independently
verifiable series**, which cannot be reconstructed retroactively.

## The proof you can run today

```
python3 pulse_freeze.py verify          # local series: chain+merkle+signature
python3 verify_remote.py                # public mirror: same, without the repo
```

Verification is free forever. So is the data. What is sold (later, as an
x402-listed resource) is *anchored, control-mapped evidence packs* — the
free wedge stays free; the packaging carries the price.

*Repository: github.com/CSOAI-ORG/clawd-workspace (`m2/evidence/gspc-pulse/`).
Public mirror + frozen manifest: huggingface.co/datasets/csoai/evidence-index
(`gspc-pulse/2026-11-04/`). Measurement, not endorsement.*
