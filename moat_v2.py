#!/usr/bin/env python3
"""moat_v2.py — the deep ecosystem matrix: endpoints × industries × regulators
× obligations × axes × demographics.

Joins what the estate MEASURES (domain endpoints in every pulse row) with
what the estate IS (its vertical portfolio) and what GOVERNS each vertical
(real UK/EU regulators). Output:
  moat-v2/ecosystem-matrix.json — the full join, with live endpoint state
  signals.jsonl                 — one DIRECT signal per domain×regulator pair

Classification is a documented heuristic mapping (industry/regulator/demographic
per domain) — counsel/trade-body verifiable, upgradeable. Licenses and
regulator applicability depend on each business's actual activities; the
matrix states APPLICABILITY CANDIDATES, never determinations.
"""
import json
import pathlib
from datetime import datetime, timezone

LANE = pathlib.Path(__file__).resolve().parent
PULSE = LANE / "pulse.jsonl"
OUT = LANE / "moat-v2" / "ecosystem-matrix.json"
SIGNALS = LANE / "signals.jsonl"

# domain -> industry -> regulators -> demographics -> obligations -> axes
# regulators: real UK/EU bodies applicable to the vertical (candidates)
PORTFOLIO = {
    "councilof.ai": {"industry": "ai-governance", "regulators": ["ico", "uk-aisi", "eu-ai-act-office"],
                     "demographics": ["ai-developers", "enterprises", "policy"],
                     "obligations": ["eu-ai-act", "iso-42001", "gdpr"], "axes": ["governance", "regulatory-framework", "openness", "conformance"]},
    "csoai.org": {"industry": "standards-body", "regulators": ["ico", "uk-dsit"],
                  "demographics": ["enterprises", "regulators", "academia"],
                  "obligations": ["iso-42001", "eu-ai-act"], "axes": ["governance", "measurer-integrity", "conformance"]},
    "proofof.ai": {"industry": "deepfake-detection", "regulators": ["ofcom-osa", "ico", "eu-ai-act-office"],
                   "demographics": ["media", "platforms", "elections"],
                   "obligations": ["eu-ai-act", "gdpr"], "axes": ["detector-interop", "provenance", "safety"]},
    "safetyof.ai": {"industry": "safety-posture", "regulators": ["ico", "hse"],
                    "demographics": ["enterprises", "safety-officers"],
                    "obligations": ["iso-42001", "gdpr"], "axes": ["safety", "watchdog-ingest", "company-practice"]},
    "suicidestop.ai": {"industry": "crisis-intervention", "regulators": ["cqc", "charity-commission", "ico"],
                       "demographics": ["at-risk-individuals", "carers", "nhs"],
                       "obligations": ["gdpr"], "axes": ["care", "affect", "safety"],
                       "sensitive": True},
    "templeman-opticians.com": {"industry": "optical-retail", "regulators": ["goc"],
                                "demographics": ["patients"],
                                "obligations": ["gdpr"], "axes": ["company-practice", "serving-fidelity"]},
    "optomobile.ai": {"industry": "mobile-optical", "regulators": ["goc"],
                      "demographics": ["patients"],
                      "obligations": ["gdpr"], "axes": ["company-practice", "serving-fidelity"]},
    "planthire.ai": {"industry": "construction-plant-hire", "regulators": ["hse", "dvsa"],
                     "demographics": ["construction-smes", "site-managers"],
                     "obligations": ["cra"], "axes": ["machinery-conformity", "lab-practice", "safety"]},
    "grabhire.ai": {"industry": "waste-hire", "regulators": ["environment-agency", "hse"],
                    "demographics": ["construction-smes"],
                    "obligations": ["cra"], "axes": ["machinery-conformity", "distribution-integrity"]},
    "muckaway.ai": {"industry": "waste-removal", "regulators": ["environment-agency"],
                    "demographics": ["construction-smes", "homeowners"],
                    "obligations": ["cra"], "axes": ["distribution-integrity", "lab-practice"]},
    "haulage.app": {"industry": "haulage-logistics", "regulators": ["traffic-commissioner", "dvsa"],
                    "demographics": ["hgv-operators", "shippers"],
                    "obligations": ["cra", "dora"], "axes": ["continuity", "company-practice", "lab-practice"]},
    "industrial-hire-ai.com": {"industry": "industrial-hire", "regulators": ["hse", "puwer"],
                               "demographics": ["industrial-smes"],
                               "obligations": ["cra"], "axes": ["machinery-conformity", "safety"]},
    "industrial-domains.com": {"industry": "industrial-portfolio", "regulators": ["hse"],
                               "demographics": ["industrial-smes"],
                               "obligations": ["cra"], "axes": ["machinery-conformity"]},
    "asisecurity-portal.com": {"industry": "security-services", "regulators": ["sia", "ico"],
                               "demographics": ["security-firms", "venues"],
                               "obligations": ["gdpr", "soc2"], "axes": ["company-practice", "safety"]},
    "pokerhud.ai": {"industry": "poker-tooling", "regulators": ["gambling-commission", "ico"],
                    "demographics": ["players"],
                    "obligations": ["gdpr"], "axes": ["company-practice", "serving-fidelity"],
                    "sensitive": True},
    "fishkeeper.ai": {"industry": "aquatics-pet", "regulators": ["animal-welfare", "ico"],
                      "demographics": ["hobbyists", "retailers"],
                      "obligations": ["gdpr"], "axes": ["company-practice"]},
    "koikeeper.ai": {"industry": "koi-aquaculture", "regulators": ["animal-welfare", "environment-agency"],
                     "demographics": ["hobbyists", "breeders"],
                     "obligations": ["gdpr"], "axes": ["company-practice"]},
    "diyhelp.ai": {"industry": "diy-guidance", "regulators": ["hse"],
                   "demographics": ["homeowners"],
                   "obligations": [], "axes": ["lab-practice", "safety"]},
    "loopfactory.ai": {"industry": "ai-tooling", "regulators": ["ico"],
                       "demographics": ["ai-developers"],
                       "obligations": ["eu-ai-act"], "axes": ["ai-adoption-components", "harness-fidelity"]},
    "meok.ai": {"industry": "personal-ai", "regulators": ["ico", "eu-ai-act-office"],
                "demographics": ["consumers"],
                "obligations": ["eu-ai-act", "gdpr"], "axes": ["affect", "care", "interpretability-reproducibility"],
                "sensitive": True},
}

# estate-critical obligations dimension (from the live engine's catalogue)
OBLIGATION_NOTE = ("full obligation catalogue lives in frameworks/obligation-index.json "
                   "(live engine); this matrix maps each vertical to its candidate set")


def newest_domain_states():
    latest = {}
    p = LANE / "pulse.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                    codes = (r.get("domains") or {}).get("codes")
                    if codes:
                        latest = codes
                except ValueError:
                    pass
    return latest


def main():
    live = newest_domain_states()
    matrix = {
        "schema": "csoai.gspc-ecosystem-matrix/0.1",
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "APPLICABILITY CANDIDATES per vertical — counsel/trade-body "
                "verifiable, never a determination. Endpoint state joined from "
                "the newest measured pulse row.",
        "domains": {},
    }
    pairs = 0
    for domain, spec in PORTFOLIO.items():
        state = live.get(domain, "unmeasured-this-row")
        entry = dict(spec)
        entry["endpoint_state"] = state
        entry["industry_regulator_pairs"] = [
            {"industry": spec["industry"], "regulator": reg}
            for reg in spec["regulators"]]
        matrix["domains"][domain] = entry
        for reg in spec["regulators"]:
            signals_entry = {"kind": "ecosystem-signal", "domain": domain,
                             "industry": spec["industry"], "regulator": reg,
                             "endpoint_state": state,
                             "obligations": spec["obligations"],
                             "axes": spec["axes"], "relevance": "direct"}
            with open(SIGNALS, "a") as f:
                f.write(json.dumps(signals_entry, sort_keys=True) + "\n")
            pairs += 1
    matrix["totals"] = {"domains": len(PORTFOLIO), "domain_regulator_pairs": pairs,
                        "sensitive_verticals": sum(1 for s in PORTFOLIO.values()
                                                   if s.get("sensitive"))}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(matrix, indent=2, sort_keys=True))
    print("moat-v2: %d domains | %d domain×regulator pairs emitted | live states joined: %d"
          % (len(PORTFOLIO), pairs, len(live)))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
