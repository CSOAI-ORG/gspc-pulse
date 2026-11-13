# GSPC in plain English — read this if nothing else

**The problem.** AI systems are being deployed everywhere, and nobody can
*prove* anything about how safe they are. Vendors make claims. Regulators
ask for evidence. Users get marketing.

**The idea.** Measure public facts about AI safety and security **on a
schedule, from public sources, with no special access** — publish a signed
prefix anyone can verify, and label later observations that have not yet been
signed. Like flight recorders and Certificate Transparency for websites — but
for AI safety.

**What we measure.** The GSPC board (34 axes: how model fleets handle
safety, care, governance, jailbreaks…), the measurement-capsule index
(11,529 frozen results), who is exploiting which software right now (CISA
KEV) with the odds it spreads (EPSS), the open-source model ecosystem
(trending + brand-new releases), the health of the MCP/x402/A2A agent
ecosystems, and 20 estate verticals' live endpoints.

**The trick that makes it verifiable.** The canonical runner hashes and
chains each row, Merkle-roots the series and signs a precise prefix with
Ed25519. The hourly public watcher has no signing key, so later observations
are explicitly an unsigned tail. The verifier reports the signed-prefix
boundary; it never calls the tail signed. Change a signed row and verification
fails. Anyone can check the signed prefix from the public mirror.

**The humans.** Every alert that matters becomes a **change request a human
must approve** (in the estate's busabase workspace). Five independent
instruments **vote** on decisions; if they disagree, it escalates. AI
reviewers are labelled AI. Counsel confirms legal claims, not the engine.

**What it is NOT.** Not a certification. Not a safety guarantee. Not a
score that says "92% safe". A failed check is shown as *absent*, never as
zero. Numbers without a timestamp are not ours.

**For you, specifically:**
- *Curious?* Read the daily findings (daily/LATEST.md) — plain language.
- *An engineer?* `latest.json` → `feed.json`; run `pulse_freeze.py verify` to check the signed prefix and identify any unsigned tail.
- *A regulator?* The obligation index maps measurements to DORA/CRA/ISO/EU
  AI Act articles, with `counsel_confirmed` reported honestly.
- *A gamer?* The games ARE the instruments — see games.md.
- *Sceptical?* Good. RECONCILIATION.md publishes our own gaps first.

Data: CC BY 4.0 OR CC0-1.0. Measurement, not endorsement — never a
certification.
