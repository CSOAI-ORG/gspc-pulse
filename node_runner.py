#!/usr/bin/env python3
"""GSPC pulse node runner - self-contained, stdlib only. Doctrine: measurement not endorsement; UNREACHABLE is absent, never zero; slots are not measurements. Rows carry meta.runner = m4-node."""
import json, os, sys, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(HERE, "pulse.jsonl")
UA = {"User-Agent": "gspc-pulse-node/m4 (permissionless reproduction)"}
DOMAINS = ["councilof.ai","safetyof.ai","muckaway.ai","grabhire.ai","templeman-opticians.com","fishkeeper.ai","csoai.org","proofof.ai","suicidestop.ai","planthire.ai","haulage.app","koikeeper.ai","diyhelp.ai","loopfactory.ai","pokerhud.ai","industrial-hire-ai.com","industrial-domains.com","asisecurity-portal.com","optomobile.ai"]

def get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def tj(url, timeout=15):
    try:
        return json.loads(get(url, timeout))
    except Exception:
        return None

def fetch_board():
    b = tj("https://councilof.ai/api/gspc")
    t = b.get("totals") if isinstance(b, dict) else None
    if not isinstance(t, dict):
        return None
    def num(*ks):
        for k in ks:
            v = t.get(k)
            if isinstance(v, (int, float)):
                return v
        return None
    out = {"slots": num("axes","axis_slots"), "measured": num("measured_axes","measured"),
           "unmeasured": num("unmeasured_axes"), "separated_leads": num("separated_leads"),
           "ties": num("ties"), "untested": num("untested_separations")}
    return out if out["slots"] is not None or out["measured"] is not None else None

def fetch_capsules():
    latest = tj("https://councilof.ai/measurement-capsules/latest.json")
    idx = tj("https://councilof.ai/measurement-capsules/v0.2/index.json", 30)
    if not isinstance(latest, dict) and not isinstance(idx, dict):
        return None
    return {"as_of": latest.get("as_of") if isinstance(latest, dict) else None,
            "total": idx.get("n_capsules_total") if isinstance(idx, dict) else None}

def fetch_root():
    r = tj("https://councilof.ai/root.json")
    return {"card_count": r.get("card_count"), "as_of": r.get("as_of"),
            "merkle_root": r.get("merkle_root")} if isinstance(r, dict) else None

def fetch_cards():
    idx = tj("https://councilof.ai/signed/card_index.json")
    out = {}
    if isinstance(idx, dict):
        out["declared"] = idx.get("n_cards"); out["head"] = idx.get("head")
    st = tj("https://councilof.ai/api/state", 20)
    ch = st.get("card_chain") if isinstance(st, dict) else None
    bvv = ch.get("bodies_verified_valid") if isinstance(ch, dict) else None
    if isinstance(bvv, dict) and isinstance(bvv.get("value"), int):
        out["store"] = bvv["value"]
    return out or None

def fetch_did():
    d = tj("https://csoai.org/.well-known/did.json")
    if not isinstance(d, dict):
        return None
    return sorted(m.get("id") for m in d.get("verificationMethod", []) if isinstance(m, dict) and m.get("id"))

def fetch_domains():
    class NR(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    def code(d):
        op = urllib.request.build_opener(NR)
        try:
            with op.open(urllib.request.Request("https://" + d + "/", headers=UA), timeout=8) as r:
                return str(r.status)
        except urllib.error.HTTPError as e:
            return str(e.code)
        except Exception:
            return "ERR"
    with ThreadPoolExecutor(max_workers=8) as ex:
        return dict(zip(DOMAINS, ex.map(code, DOMAINS)))

def fetch_hf():
    out = {}
    m = tj("https://huggingface.co/api/models?sort=trendingScore&direction=-1&limit=1")
    if isinstance(m, list) and m:
        out["top_trending"] = m[0].get("id"); out["trend_score"] = m[0].get("trendingScore")
    d = tj("https://huggingface.co/api/models?sort=downloads&direction=-1&limit=1")
    if isinstance(d, list) and d:
        out["top_id"] = d[0].get("id"); out["top_downloads"] = d[0].get("downloads")
    return out or None

def fetch_kev():
    k = tj("https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", 30)
    if not isinstance(k, dict):
        return None
    vs = sorted(k.get("vulnerabilities", []), key=lambda v: v.get("dateAdded",""), reverse=True)
    total = len(vs) or 1
    rw = [v for v in vs if v.get("knownRansomwareCampaignUse") == "Known"]
    per = [v for v in vs if any(w in (v.get("product","")+ ""+v.get("vendorProject","")).lower()
           for w in ("vpn","firewall","gateway","connect secure","netscaler","big-ip","ivanti","forti","asa","ftd","citrix","sonicwall","sslvpn"))]
    return {"count": k.get("count"), "released": k.get("dateReleased"),
            "top20": [v.get("cveID") for v in vs[:20]],
            "rw_share_pct": round(100*len(rw)/total, 1),
            "perimeter_recent": [v.get("cveID") for v in per[:10]]}

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
    return sorted(rows, key=lambda r: r.get("ts") or "")

def sig(r):
    s = {}
    for sec, keys in (("board",["measured"]),("capsules",["total"]),("root",["card_count"]),
                      ("cards",["declared","store"]),("kev",["count","released"])):
        if sec in r:
            for k in keys:
                s[sec+"."+k] = (r.get(sec) or {}).get(k)
    if "did" in r:
        s["did"] = r["did"].get("key_ids")
    if "domains" in r:
        s["domains"] = r["domains"].get("codes")
    return s

def main():
    fluid = "--fluid" in sys.argv
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap = {"ts": ts, "meta": {"runner": "m4-node", "kind": "public-surface-reproduction"}}
    b = fetch_board()
    if b: snap["board"] = b
    c = fetch_capsules()
    if c: snap["capsules"] = c
    r = fetch_root()
    if r: snap["root"] = r
    ca = fetch_cards()
    if ca: snap["cards"] = ca
    did = fetch_did()
    if did is not None: snap["did"] = {"key_ids": did}
    snap["domains"] = {"codes": fetch_domains()}
    hf = fetch_hf()
    if hf: snap["hf"] = hf
    k = fetch_kev()
    if k: snap["kev"] = k
    rows = load_rows()
    if "board" not in snap and "kev" not in snap:
        print("all primary fetches failed - recording nothing (UNREACHABLE != 0)")
        return 1
    prev = rows[-1] if rows else None
    if prev is not None and not fluid and sig(prev) == sig(snap):
        print("no frozen change since %s" % prev.get("ts"))
        return 2
    with open(JSONL, "a") as f:
        f.write(json.dumps(snap, sort_keys=True) + "\n")
    print("appended %s; node rows=%d" % (ts, len(rows)+1))
    return 0

if __name__ == "__main__":
    sys.exit(main())
