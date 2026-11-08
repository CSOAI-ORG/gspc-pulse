#!/usr/bin/env python3
"""Independent public-surface pulse watcher (permissionless reproduction).

Runs anywhere (GitHub Actions, any machine, this repo's lane). Fetches ONLY
public HTTP surfaces, computes the frozen-layer delta vs the last archived row,
and appends a row to pulse.jsonl ONLY when the frozen layer moved. Fluid
measurements are printed to stdout (CI logs) without committing.

Frozen gate: board measured, capsules total, root card count, cards declared/
store, KEV count+release, DID key ids, domain status codes.
Fluid extras (swan outlier scan, interop censuses) ride along in rows but are
NEVER part of the frozen gate — fluid movement alone appends only with --fluid.
Exit 0 = frozen row appended (caller should commit);
exit 2 = no frozen change (caller should skip commit; --fluid appends anyway);
exit 1 = every fetch failed.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive_pulse import CSV_COLS, JSONL, build_feeds, row_from, write_csv  # noqa: E402
import swan_stats  # noqa: E402
import swan_watch  # noqa: E402

UA = {"User-Agent": "gspc-pulse-watcher/0.1 (permissionless reproduction)"}
DOMAINS = [
    "councilof.ai", "safetyof.ai", "muckaway.ai", "grabhire.ai",
    "templeman-opticians.com", "fishkeeper.ai", "csoai.org", "proofof.ai",
    "suicidestop.ai", "planthire.ai", "haulage.app", "koikeeper.ai",
    "diyhelp.ai", "loopfactory.ai", "pokerhud.ai", "industrial-hire-ai.com",
    "industrial-domains.com", "asisecurity-portal.com", "optomobile.ai",
]
FROZEN_ROW_KEYS = [
    "board_measured", "capsules_total", "root_card_count", "cards_declared",
    "cards_store", "kev_count", "kev_released", "hf_top_trending",
    "hf_top_new_30d",
]


def get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def try_json(url, timeout=15):
    try:
        return json.loads(get(url, timeout))
    except Exception:
        return None


def fetch_board():
    b = try_json("https://councilof.ai/api/gspc")
    if not isinstance(b, dict):
        return None
    t = b.get("totals") if isinstance(b.get("totals"), dict) else {}

    def num(*keys):
        for k in keys:
            v = t.get(k)
            if isinstance(v, (int, float)):
                return v
        return None

    out = {
        "slots": num("axes", "axis_slots", "slots"),
        "measured": num("measured_axes", "measured"),
        "unmeasured": num("unmeasured_axes", "unmeasured"),
        "separated_leads": num("separated_leads"),
        "ties": num("ties"),
        "untested": num("untested_separations", "untested"),
        "totals_keys": sorted(t.keys()),
    }
    if out["slots"] is None and out["measured"] is None:
        return None
    return out


def fetch_capsules():
    latest = try_json("https://councilof.ai/measurement-capsules/latest.json")
    idx = try_json("https://councilof.ai/measurement-capsules/v0.2/index.json",
                   timeout=30)
    if not isinstance(latest, dict) and not isinstance(idx, dict):
        return None
    return {
        "as_of": latest.get("as_of") if isinstance(latest, dict) else None,
        "total": idx.get("n_capsules_total") if isinstance(idx, dict) else None,
    }


def fetch_anchors():
    """Anchor states from the capsule anchors file — the freeze-event watch.
    OTS -> bitcoin-attested and XRPL -> submitted are the two pending
    transitions; either move is a frozen event."""
    a = try_json("https://councilof.ai/measurement-capsules/v0.2/anchors.json",
                 timeout=15)
    if not isinstance(a, dict):
        return None
    ots = a.get("opentimestamps") or {}
    rekor = a.get("rekor") or []
    rekor0 = rekor[0] if isinstance(rekor, list) and rekor else {}
    xrpl = a.get("xrpl") or {}
    return {"ots_state": ots.get("state"),
            "rekor_state": rekor0.get("state"),
            "xrpl_state": xrpl.get("state"),
            "as_of": a.get("as_of")}


def fetch_did():
    d = try_json("https://csoai.org/.well-known/did.json")
    if not isinstance(d, dict):
        return None
    methods = d.get("verificationMethod", [])
    return sorted(m.get("id") for m in methods if isinstance(m, dict) and m.get("id"))


def fetch_domain_codes():
    """First-hop status codes, redirects NOT followed — a 308 to councilof.ai
    records as 308, matching the topology table's semantics."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    def code(domain):
        opener = urllib.request.build_opener(NoRedirect)
        req = urllib.request.Request("https://" + domain + "/",
                                     headers=UA)
        try:
            with opener.open(req, timeout=8) as r:
                return str(r.status)
        except urllib.error.HTTPError as e:
            return str(e.code)
        except Exception:
            return "ERR"
    with ThreadPoolExecutor(max_workers=8) as ex:
        return dict(zip(DOMAINS, ex.map(code, DOMAINS)))


def fetch_hf():
    """0.3.4 methodology — trending leader + new-with-traction (30d cohort).
    A downloads leaderboard is ubiquity, not news: never record one (owner rule)."""
    trend = try_json(
        "https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=1"
    )
    if not (isinstance(trend, list) and trend):
        return None
    pool = try_json(
        "https://huggingface.co/api/models?sort=downloads&direction=-1"
        "&limit=400&filter=text-generation&filter=conversational"
    )
    hf = {
        "method": "trending + new-with-traction (30d cohort) — no downloads leaderboard ever",
        "top_trending": trend[0].get("id"),
        "trend_score": trend[0].get("trendingScore"),
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    }
    if isinstance(pool, list) and pool:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).date()
        young = []
        for m in pool:
            created = str(m.get("createdAt") or "")[:10]
            try:
                if datetime.fromisoformat(created).date() >= cutoff:
                    young.append(m)
            except ValueError:
                continue
        if young:
            best = max(young, key=lambda m: m.get("downloads") or 0)
            hf["top_new_30d"] = best.get("id")
            hf["new_30d_downloads"] = best.get("downloads")
    return hf


def fetch_kev(url="https://www.cisa.gov/sites/default/files/feeds/"
                  "known_exploited_vulnerabilities.json"):
    k = try_json(url, timeout=30)
    if not isinstance(k, dict):
        return None
    vs = sorted(k.get("vulnerabilities", []),
                key=lambda v: v.get("dateAdded", ""), reverse=True)
    return {
        "count": k.get("count"),
        "released": k.get("dateReleased"),
        "top20": [v.get("cveID") for v in vs[:20]],
    }


def fetch_kev_and_swan():
    """One KEV fetch feeding both the frozen kev section and the fluid swan
    outlier scan, EPSS-enriched, plus a ransomware.live leak-site sample.
    Returns (kev_dict_or_None, swan_dict_or_None)."""
    try:
        vulns, released, count = swan_stats.fetch_vulns()
    except Exception:
        return fetch_kev(), None
    vs = sorted(vulns, key=lambda v: v.get("dateAdded", ""), reverse=True)
    kev = {"count": count, "released": released,
           "top20": [v.get("cveID") for v in vs[:20]]}
    swan = swan_stats.compute(vulns)
    try:
        swan_watch.epss_enrich(swan.get("perimeter_recent", []))
        swan_watch.ssvc_enrich(swan.get("perimeter_recent", []))
    except Exception:
        pass
    rw = swan_watch.ransomware_victims()
    if rw:
        swan["ransomware_sample"] = rw
    return kev, swan


def fetch_interop():
    """Interop census snapshots — public JSON, counts only by doctrine."""
    interop = {}
    mcp = try_json("https://councilof.ai/interop/mcp-trust/latest.json",
                   timeout=15)
    if isinstance(mcp, dict):
        en, ct = mcp.get("enumeration") or {}, mcp.get("counts") or {}
        interop["mcp_trust"] = {
            "as_of": mcp.get("as_of"), "partial": mcp.get("partial"),
            "unique_hosts": en.get("unique_hosts"),
            "registry_rows_seen": en.get("registry_rows_seen"),
            "initialize_ok_open": ct.get("initialize_ok_open"),
            "initialize_ok_tools_listed": ct.get("initialize_ok_tools_listed"),
            "auth_challenged_401_403": ct.get("auth_challenged_401_403"),
            "dead_404_or_unreachable": ct.get("dead_404_or_unreachable"),
        }
    x402 = try_json("https://councilof.ai/interop/x402-trust/latest.json",
                    timeout=15)
    if isinstance(x402, dict):
        ct = x402.get("counts") or {}
        interop["x402_trust"] = {
            "as_of": x402.get("as_of"),
            "challenge_402": ct.get("challenge_402"),
            "total": ct.get("total"),
            "dead_404_or_unreachable": ct.get("dead_404_or_unreachable"),
        }
    return interop or None


SECTION_OF = {
    "board_measured": "board",
    "capsules_total": "capsules",
    "root_card_count": "root",
    "cards_declared": "cards",
    "cards_store": "cards",
    "kev_count": "kev",
    "kev_released": "kev",
    "hf_top_trending": "hf",
    "hf_top_new_30d": "hf",
}


def frozen_signature(snap):
    """Frozen-layer signature. Sections absent from this snapshot (failed
    fetches) are excluded from the gate — UNREACHABLE must never look like a
    frozen change."""
    row = row_from(snap)
    sig = {k: row.get(k) for k, sec in SECTION_OF.items() if sec in snap}
    sig["did_key_ids"] = snap.get("did", {}).get("key_ids") if "did" in snap else None
    sig["domain_codes"] = snap.get("domains", {}).get("codes") if "domains" in snap else None
    if "anchors" in snap:
        a = snap["anchors"]
        sig["ots_state"] = a.get("ots_state")
        sig["rekor_state"] = a.get("rekor_state")
        sig["xrpl_state"] = a.get("xrpl_state")
    return sig


def load_rows():
    rows = []
    if os.path.exists(JSONL):
        with open(JSONL) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        pass
    rows.sort(key=lambda r: r.get("ts") or "")
    return rows


def main():
    fluid_only = "--fluid" in sys.argv
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    runner = "github-actions" if os.environ.get("GITHUB_ACTIONS") else "manual-reproduction"
    kind = "fluid-scan" if fluid_only else "public-surface-reproduction"
    snap = {"ts": ts, "meta": {"runner": runner, "kind": kind}}

    board = fetch_board()
    if board:
        snap["board"] = board
    root = try_json("https://councilof.ai/root.json")
    if isinstance(root, dict):
        snap["root"] = {"card_count": root.get("card_count"),
                        "as_of": root.get("as_of")}
    caps = fetch_capsules()
    if caps:
        snap["capsules"] = caps
    anchors = fetch_anchors()
    if anchors:
        snap["anchors"] = anchors
    idx = try_json("https://councilof.ai/signed/card_index.json")
    # store-side count: the published counter at /api/state
    # card_chain.bodies_verified_valid.value (kind: measured). Two labelled
    # numbers with the index's declared count — never reconciled here.
    state = try_json("https://councilof.ai/api/state", timeout=20)
    store_count = None
    chain = state.get("card_chain") if isinstance(state, dict) else None
    bvv = chain.get("bodies_verified_valid") if isinstance(chain, dict) else None
    if isinstance(bvv, dict) and isinstance(bvv.get("value"), int):
        store_count = bvv["value"]
        cards = {"store_source": "api_state.card_chain.bodies_verified_valid"}
    if store_count is None:
        legacy = try_json("https://councilof.ai/api/cards")
        if isinstance(legacy, list):
            store_count = len(legacy)
    cards = cards if store_count is not None else {}
    if isinstance(idx, dict):
        cards["declared"] = idx.get("n_cards")
        cards["head"] = idx.get("head")
    if store_count is not None:
        cards["store"] = store_count
    if cards:
        snap["cards"] = cards
    did = fetch_did()
    if did is not None:
        snap["did"] = {"key_ids": did}
    snap["domains"] = {"codes": fetch_domain_codes()}
    hf = fetch_hf()
    if hf:
        snap["hf"] = hf
    kev, swan = fetch_kev_and_swan()
    if kev:
        snap["kev"] = kev
    if swan:
        snap["swan"] = swan
    interop = fetch_interop()
    if interop:
        snap["interop"] = interop

    rows = load_rows()
    if "board" not in snap and "kev" not in snap:
        print("all primary fetches failed — recording nothing (UNREACHABLE != 0)")
        return 1
    prev = rows[-1] if rows else None
    sig = frozen_signature(snap)
    if not fluid_only and prev is not None and frozen_signature(prev) == sig:
        print("no frozen change since %s — fluid row logged only:" % prev.get("ts"))
        print(json.dumps(snap, sort_keys=True)[:400])
        return 2

    with open(JSONL, "a") as f:
        f.write(json.dumps(snap, sort_keys=True) + "\n")
    rows = load_rows()
    write_csv(rows)
    build_feeds()
    changed = {k: [ (prev_f := row_from(prev)).get(k), row_from(snap).get(k)]
               for k in FROZEN_ROW_KEYS
               if prev and row_from(prev).get(k) != row_from(snap).get(k)}
    if prev is None or (snap.get("did") and not prev.get("did")) or \
       (snap.get("domains") and not prev.get("domains")):
        changed["baseline"] = "first frozen snapshot for new surfaces"
    print("frozen row appended %s; rows=%d; changed=%s"
          % (ts, len(rows), json.dumps(changed, default=str)[:600]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
