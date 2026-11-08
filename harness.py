#!/usr/bin/env python3
"""LAYER-0 HARNESS (H0) — consume, connect, join the measurement estate.

Consumes live Layer-0 surfaces (board totals, capsule index, MCP census),
joins them with the seeded axis→framework→provision crosswalk, and emits
two documents: matrix.json (the full join) and slices.json (industry
slices). Cells state evidence and freshness — never scores, never conformity
verdicts. Provision mappings carry maturity:"seed" until each key is
verified against framework_readiness output.
All fetching via fetch_guard (https-only, host allowlist); all writes to
module-constant paths inside this lane.
Usage: python3 harness.py
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_guard  # noqa: E402

LANE = os.path.dirname(os.path.abspath(__file__))
MATRIX_PATH = os.path.join(LANE, "matrix.json")
SLICES_PATH = os.path.join(LANE, "slices.json")

AXES = [
    "governance", "care", "safety", "jail", "swarm", "provenance",
    "provenance-controls", "custody-disclosure", "distribution-integrity",
    "serving-fidelity", "harness-fidelity", "measurer-integrity",
    "interpretability-reproducibility", "detector-interop", "cross-reality",
    "effect-binding", "claim-maintenance", "company-practice", "conformance",
    "continuity", "interop-conformance", "machinery-conformity",
    "lab-practice", "openness", "regulator-transparency",
    "regulatory-framework", "reserve-attestation", "watchdog-ingest",
    "art50-marking", "art5-safeguard", "ai-adoption-components",
    "labour-components", "humanoid-deployment", "humanoid-labour-index",
]

CROSSWALK = {
    "art50-marking": (["eu-ai-act"], ["EU AI Act Art. 50 (transparency/marking)"]),
    "art5-safeguard": (["eu-ai-act"], ["EU AI Act Art. 5 (safeguards)"]),
    "watchdog-ingest": (["nis2", "dora"], ["NIS2 Art. 23 (incident reporting)", "DORA Art. 19 (ICT incident management)"]),
    "reserve-attestation": (["dora"], ["DORA Art. 11 (backup/restore resilience)"]),
    "continuity": (["dora", "iso-27001", "nist-csf"], ["DORA Art. 12 (business continuity)", "ISO 27001 A.17", "NIST CSF RC"]),
    "conformance": (["cra", "iso-27001"], ["CRA Annex I (essential requirements)"]),
    "company-practice": (["soc2", "gdpr"], ["SOC 2 CC-series (governance)", "GDPR Art. 24 (accountability)"]),
    "custody-disclosure": (["gdpr", "iso-27001"], ["GDPR Art. 13/14 (disclosure)"]),
    "distribution-integrity": (["cra", "nist-csf"], ["CRA secure update/distribution", "NIST CSF PR"]),
    "serving-fidelity": (["iso-27001", "soc2"], ["ISO 27001 A.7 (operations)"]),
    "harness-fidelity": (["nist-csf"], ["NIST CSF PR/DE"]),
    "measurer-integrity": (["iso-27001", "soc2"], ["ISO 27001 A.8"]),
    "interpretability-reproducibility": (["cra"], ["CRA Annex I (documentation)"]),
    "detector-interop": (["nist-csf"], ["NIST CSF DE"]),
    "interop-conformance": (["cra", "nist-csf"], ["CRA interoperability", "NIST CSF ID"]),
    "machinery-conformity": (["cra"], ["CRA (products with digital elements)"]),
    "lab-practice": (["iso-27001"], ["ISO 27001 A.6"]),
    "openness": (["eu-ai-act"], ["EU AI Act Art. 10/11"]),
    "regulator-transparency": (["eu-ai-act", "nis2"], ["EU AI Act Art. 13", "NIS2 supervision"]),
    "regulatory-framework": (["eu-ai-act", "dora", "nis2", "gdpr", "cra"], ["framework-level applicability"]),
    "provenance": (["cra", "eu-ai-act"], ["CRA provenance/SBOM", "EU AI Act Art. 12"]),
    "provenance-controls": (["gdpr", "iso-27001"], ["GDPR Art. 32"]),
    "claim-maintenance": (["soc2", "cra"], ["SOC 2 claim upkeep", "CRA vulnerability handling"]),
    "governance": (["soc2", "iso-27001", "nist-csf", "gdpr"], ["SOC 2 CC1", "ISO 27001 A.5", "NIST CSF GV", "GDPR Art. 5"]),
    "care": (["gdpr"], ["GDPR Art. 25"]),
    "safety": (["cra", "eu-ai-act"], ["CRA Annex I safety", "EU AI Act Art. 15"]),
    "jail": (["eu-ai-act"], ["EU AI Act Art. 15 (robustness)"]),
    "swarm": (["nis2"], ["NIS2 Art. 20"]),
    "cross-reality": (["cra"], ["CRA emerging device classes"]),
    "effect-binding": (["nist-csf"], ["NIST CSF DE/RS"]),
    "ai-adoption-components": (["eu-ai-act", "soc2"], ["EU AI Act Art. 26 (deployer duties)", "SOC 2 processing integrity"]),
    "labour-components": (["gdpr"], ["GDPR Art. 22"]),
    "humanoid-deployment": (["cra"], ["CRA / Machinery Regulation 2023/1230 (robotics)"]),
    "humanoid-labour-index": (["gdpr"], ["GDPR Art. 22 + labour law pointers"]),
}

FRAMEWORKS = ["eu-ai-act", "dora", "nis2", "gdpr", "iso-27001",
              "nist-csf", "soc2", "pci-dss", "cra"]
REGULATOR_OF = {
    "eu-ai-act": "EU AI Office / national market surveillance authorities",
    "dora": "European Supervisory Authorities (ESAs)",
    "nis2": "National CSIRTs / NIS2 competent authorities",
    "gdpr": "DPAs / EDPB",
    "iso-27001": "Accredited certification bodies (voluntary)",
    "nist-csf": "Voluntary (US NIST)",
    "soc2": "AICPA-licensed CPA firms (attestation)",
    "pci-dss": "PCI SSC / card brands",
    "cra": "EU national market surveillance authorities (from 2027)",
}
INDUSTRIES = {
    "finance": ["eu-ai-act", "dora", "nis2", "gdpr", "iso-27001"],
    "healthcare": ["eu-ai-act", "gdpr", "iso-27001", "nist-csf"],
    "energy": ["nis2", "iso-27001", "nist-csf"],
    "transport": ["nis2", "cra", "iso-27001"],
    "public-sector": ["eu-ai-act", "nis2", "gdpr"],
    "telecoms": ["nis2", "gdpr", "iso-27001"],
    "retail": ["gdpr", "pci-dss", "cra"],
    "legal": ["gdpr", "eu-ai-act", "iso-27001"],
    "media": ["eu-ai-act", "gdpr"],
    "education": ["gdpr", "eu-ai-act", "nist-csf"],
    "hr-labour": ["eu-ai-act", "gdpr"],
    "agent-developers": ["cra", "nist-csf", "eu-ai-act"],
}
ENDPOINTS = {
    "board": "GET https://councilof.ai/api/gspc (or gspc board MCP tool)",
    "axis_cards": "gspc signed cards — verify per HOW-TO-VERIFY.md",
    "capsules": "GET https://councilof.ai/measurement-capsules/latest.json",
    "checklists": "gspc framework_readiness MCP tool (deterministic, free)",
    "pulse": "gspc-pulse feed.json / latest.json (this lane)",
    "verify": "https://councilof.ai/signed/HOW-TO-VERIFY.md",
}


def _fetch(url):
    try:
        return fetch_guard.get_json(url, 20)
    except Exception:
        return None  # absent is not zero


def build():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    board = _fetch("https://councilof.ai/api/gspc") or {}
    caps = _fetch("https://councilof.ai/measurement-capsules/latest.json") or {}
    mcp = _fetch("https://councilof.ai/interop/mcp-trust/latest.json")
    axes_out = []
    for ax in AXES:
        fws, provs = CROSSWALK.get(
            ax, (["eu-ai-act"], ["(unmapped — seed pending)"]))
        axes_out.append({
            "axis": ax,
            "frameworks": fws,
            "provisions": [{"framework": f, "provision": p, "maturity": "seed"}
                           for f, p in zip(fws, provs)],
            "evidence_endpoints": ["board", "axis_cards", "capsules", "verify"],
        })
    return {
        "schema": "csoai.layer0-matrix/0.1",
        "generated": now,
        "doctrine": ("measurement, not endorsement — cells state evidence and "
                     "freshness, never scores or conformity verdicts; provision "
                     "mappings maturity:seed until verified against "
                     "framework_readiness"),
        "live_layer0": {
            "board": {"public_count": board.get("public_count"),
                      "as_of": (board.get("as_of") or {}).get("fetched_at")},
            "capsules": {"as_of": caps.get("as_of"),
                         "n_batches": len(caps.get("batches") or [])},
            "mcp_census_hosts": ((mcp or {}).get("enumeration") or {}).get("unique_hosts"),
        },
        "frameworks": [{"id": f, "regulator": REGULATOR_OF[f]} for f in FRAMEWORKS],
        "axes": axes_out,
        "industries": {k: {"frameworks": v} for k, v in INDUSTRIES.items()},
        "endpoints": ENDPOINTS,
    }


def write_outputs(m):
    slices = []
    for ind, spec in sorted(m["industries"].items()):
        cells = [a["axis"] for a in m["axes"]
                 if set(a["frameworks"]) & set(spec["frameworks"])]
        slices.append({"schema": "csoai.layer0-slice/0.1", "industry": ind,
                       "frameworks": spec["frameworks"],
                       "regulators": [REGULATOR_OF[f] for f in spec["frameworks"]],
                       "axes_in_scope": cells,
                       "endpoints": ENDPOINTS,
                       "note": ("evidence would be measured here; not a "
                                "conformity assessment; not legal advice")})
    with open(MATRIX_PATH, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    with open(SLICES_PATH, "w") as f:
        json.dump({"schema": "csoai.layer0-slices/0.1",
                   "generated": m["generated"], "slices": slices},
                  f, indent=1, sort_keys=True)
    print("matrix.json: %d axes, %d frameworks | slices: %d" % (
        len(m["axes"]), len(m["frameworks"]), len(slices)))
    return 0


if __name__ == "__main__":
    sys.exit(write_outputs(build()))
