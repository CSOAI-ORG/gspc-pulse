#!/usr/bin/env python3
"""mass_cards.py — mass-emit the card lattice from deep data:
34 axis cards + 20 domain cards + regulator cards. Each an indexable,
E-A-T public page with live values and verify links."""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
DOCTR = ("\n\n*Measurement, not endorsement — never a certification. "
         "Data: GSPC live pulse (CC BY 4.0 OR CC0-1.0). Verify: pulse_freeze.py verify.*")


def main():
    deep = json.loads((HERE / "deep-board" / "gspc-deep-2026-11-08.json").read_text())
    moat = json.loads((HERE / "moat-v2" / "ecosystem-matrix.json").read_text())
    n = 0

    apath = HERE / "cards" / "axis"
    apath.mkdir(parents=True, exist_ok=True)
    for a in deep.get("axes") or []:
        ax = a.get("axis", "axis")
        md = (
            f"# Axis: {ax} — {a.get('bench', '')}\n\n"
            f"**Task**: {a.get('task', '')} · **Family**: {a.get('family')} · "
            f"**Kind**: {a.get('kind')}\n\n"
            f"**Items tested (n)**: {a.get('n')} · **Fleet mean**: {a.get('fleet_mean')} · "
            f"**Mean harm**: {a.get('mean_harm')} · **CVaR05 harm**: {a.get('cvar05_harm')} · "
            f"**MDE**: {a.get('mde')}\n\n"
            f"**Separation**: {a.get('separation')} — {a.get('separation_sentence', '')} "
            f"(method: {a.get('separation_method')}, p: {a.get('separation_p')})\n\n"
            f"**Leader**: {a.get('leader', '—')} "
            f"(card state: {a.get('leader_card_state', '—')}, {a.get('leader_card_url', '')})\n\n"
            f"**Dataset**: {a.get('dataset', '')} ({a.get('dataset_url', '')})\n"
            f"**Per-item sha**: {a.get('peritem_file_sha256', '')}\n"
            f"**Interval**: {a.get('interval', '')} · "
            f"**Measurement time**: {a.get('measurement_time', '')}\n"
            f"**Historical record**: {str(a.get('historical_measurement_record', ''))[:200]}"
            + DOCTR)
        (apath / (ax + ".md")).write_text(md)
        n += 1

    dpath = HERE / "cards" / "domain"
    dpath.mkdir(parents=True, exist_ok=True)
    for dom, spec in (moat.get("domains") or {}).items():
        regs = ", ".join(p["regulator"] for p in spec.get("industry_regulator_pairs", []))
        md = (
            f"# Vertical: {dom}\n\n"
            f"**Industry**: {spec.get('industry')} · "
            f"**Endpoint state**: {spec.get('endpoint_state')}\n"
            f"**Regulators (candidates)**: {regs}\n"
            f"**Demographics**: {', '.join(spec.get('demographics', []))}\n"
            f"**Obligations**: {', '.join(spec.get('obligations', []))}\n"
            f"**Axes**: {', '.join(spec.get('axes', []))}\n"
            f"**Sensitive**: {spec.get('sensitive', False)}\n\n"
            "*APPLICABILITY CANDIDATES — counsel/trade-body verifiable, "
            "never a determination.*" + DOCTR)
        (dpath / (dom + ".md")).write_text(md)
        n += 1

    rpath = HERE / "cards" / "regulator"
    rpath.mkdir(parents=True, exist_ok=True)
    regs = {}
    for dom, spec in (moat.get("domains") or {}).items():
        for p in spec.get("industry_regulator_pairs", []):
            regs.setdefault(p["regulator"], []).append(dom)
    for reg, doms in sorted(regs.items()):
        lines = [f"# Regulator: {reg}",
                 f"\n**Verticals in scope (candidates)**: {len(doms)}\n"]
        for d in doms:
            lines.append(f"- {d} ({moat['domains'][d]['industry']}) — "
                         f"endpoint {moat['domains'][d]['endpoint_state']}")
        lines.append(DOCTR)
        (rpath / (reg + ".md")).write_text("\n".join(lines))
        n += 1

    print("cards generated:", n,
          "(axis %d + domain %d + regulator %d)"
          % (len(list(apath.glob('*.md'))), len(list(dpath.glob('*.md'))),
             len(list(rpath.glob('*.md')))))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
