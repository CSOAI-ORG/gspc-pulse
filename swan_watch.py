#!/usr/bin/env python3
"""Swan-watch v2 engine for the gspc-pulse lane.

All remote fetching goes through fetch_guard (https-only, host allowlist,
private-IP refusal, redirects disabled). Local writes go only to
watch/watch_state.json inside this lane directory.

Rule engine v2 fires on CHANGES only — new perimeter entrants, fresh (≤3d)
due windows on CVEs added ≤30d, ransomware-flag flips, 2× cadence surge,
catalog release — so carried perimeter entries are observations, not
escalations. This kills the daily re-fire noise of v1. State persists
per-CVE (first_seen / last_seen) in watch/watch_state.json.

Usage:
  python3 swan_watch.py --rules     # evaluate rules on last two pulse rows
  python3 swan_watch.py --enrich    # live KEV scan + EPSS + ransomware sample
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_guard  # noqa: E402
import swan_stats   # noqa: E402

EPSS_URL = "https://api.first.org/data/v1/epss"
RW_VICTIMS_URL = "https://api.ransomware.live/v2/recentvictims"
LANE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(LANE, "watch", "watch_state.json")
JSONL_PATH = os.path.join(LANE, "pulse.jsonl")


def epss_enrich(entries, timeout=15):
    """Attach FIRST.org EPSS score+percentile to entries with a well-formed
    'cve'. Unscored CVEs get unscored=True — absent is not zero. Query values
    are allowlisted CVE tokens only; the URL is an https module constant."""
    cves = sorted({c for c in (e.get("cve") for e in entries)
                   if c and swan_stats._CVE_RE.match(c)})[:100]
    if not cves:
        return entries
    d = fetch_guard.get_json(EPSS_URL + "?cve=" + ",".join(cves), timeout)
    scores = {x["cve"]: x for x in d.get("data", [])}
    for e in entries:
        s = scores.get(e.get("cve"))
        if s:
            e["epss"] = float(s["epss"])
            e["epss_percentile"] = float(s["percentile"])
            e["epss_date"] = s["date"]
        else:
            e["unscored"] = True
    return entries


VULNRICHMENT_URL = ("https://raw.githubusercontent.com/cisagov/vulnrichment"
                    "/develop/{year}/{bucket}/{cve}.json")


def ssvc_enrich(entries, timeout=10):
    """Attach CISA Vulnrichment SSVC decision outcome to entries with a
    well-formed 'cve'. Vulnrichment covers CVEs CISA has enriched — fresh
    entries are often absent, so a miss records nothing (absent ≠ zero).
    Mutates in place; URL is an https constant with validated path parts."""
    for e in entries:
        cve = e.get("cve") or ""
        year = cve[4:8]
        bucket = (cve[9:10] or "") + "xxx"
        if not (swan_stats._CVE_RE.match(cve)
                and re.fullmatch(r"\d{4}", year)
                and re.fullmatch(r"\dxxx", bucket)):
            continue
        url = ("https://raw.githubusercontent.com/cisagov/vulnrichment"
               "/develop/" + year + "/" + bucket + "/" + cve + ".json")
        try:
            d = fetch_guard.get_json(url, timeout)
            sels = (d.get("containers", {}).get("cna", {})
                    .get("ssvc", {}).get("selections") or [])
            decision = next((s.get("selections") for s in sels
                             if s.get("name") == "decision"), None)
            if decision:
                e["ssvc"] = decision
        except Exception:
            continue  # 404 / unreachable: enriched later by CISA
    return entries


def ransomware_victims(timeout=20):
    """Recent leak-site victims via ransomware.live — a recent-100 SAMPLE of
    leak-site posts, not a census; states only. Turns the 'slow-motion swan'
    (record ransomware year) from news-scavenging into a measured series."""
    try:
        d = fetch_guard.get_json(RW_VICTIMS_URL, timeout)
    except Exception:
        return None
    if not isinstance(d, list) or not d:
        return None
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    days = sorted(x.get("attackdate", "")[:10]
                  for x in d if x.get("attackdate"))
    groups = Counter(x.get("group") for x in d if x.get("group"))
    return {
        "sample_size": len(d),
        "window_first": days[0] if days else None,
        "window_last": days[-1] if days else None,
        "claimed_today": sum(1 for x in d
                             if x.get("attackdate", "")[:10] == today),
        "top_groups_sample": dict(groups.most_common(5)),
        "source_kind": "recent-100 leak-site sample, not a census",
    }


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {"cves": {}}


def save_state(st):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(st, f, indent=2, sort_keys=True)


def evaluate_rules(cur, prev, now=None):
    """Rule engine v2. cur/prev are swan dicts with a rules_context key
    carrying kev_count/kev_released. Returns (fires, observations). Updates
    watch_state.json: first_seen/last_seen per perimeter CVE."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    fires, obs = [], []
    st = load_state()
    seen = st.setdefault("cves", {})
    ts_now = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    prev_cves = ({x.get("cve") for x in prev.get("perimeter_recent", [])}
                 if prev else set())
    cur_per = {e.get("cve"): e for e in cur.get("perimeter_recent", [])}
    new_per = sorted(c for c in cur_per
                     if c not in seen and c not in prev_cves)
    for cve in cur_per:
        rec = seen.setdefault(cve, {"first_seen": ts_now})
        rec["last_seen"] = ts_now
    if new_per:
        fires.append({"rule": "a-new-perimeter", "cves": new_per,
                      "detail": {c: cur_per[c].get("vendor", "")
                                 for c in new_per}})
    carried = sorted(c for c in cur_per if c not in new_per)
    if carried:
        obs.append({"rule": "a-carried", "cves": carried})

    # rule-b v3: fresh ≤3d due windows on ANY perimeter entry (not just the
    # historical top-5), once per CVE — fixes the miss where new urgent
    # windows were outranked by old 1d entries.
    for e in cur.get("perimeter_recent", []):
        cve = e.get("cve")
        a, du = swan_stats._dt(e.get("added", "") or ""), swan_stats._dt(e.get("due", "") or "")
        if (cve and a and du and (du - a).days <= 3
                and not seen.get(cve, {}).get("b_noted")):
            seen.setdefault(cve, {})["b_noted"] = ts_now
            fires.append({"rule": "b-fresh-due-window", "cve": cve,
                          "days": (du - a).days, "added": e.get("added")})

    for w in cur.get("shortest_due_windows", []):
        added = swan_stats._dt(w.get("added", "") or "")
        if (w.get("days") is not None and w["days"] <= 3 and added
                and (now - added).days <= 30):
            fires.append({"rule": "b-fresh-due-window", "cve": w.get("cve"),
                          "days": w["days"], "added": w.get("added")})

    if prev:
        cc, pc = (cur.get("rules_context") or {}), (prev.get("rules_context") or {})
        if (cc.get("kev_count") != pc.get("kev_count")
                or cc.get("kev_released") != pc.get("kev_released")):
            fires.append({"rule": "e-catalog-release",
                          "count": cc.get("kev_count"),
                          "released": cc.get("kev_released")})
        if ((cur.get("ransomware_flagged_recent") or 0)
                > (prev.get("ransomware_flagged_recent") or 0)):
            fires.append({"rule": "c-ransomware-flip",
                          "prev": prev.get("ransomware_flagged_recent"),
                          "cur": cur.get("ransomware_flagged_recent"),
                          "cves": cur.get("ransomware_flagged_recent_cves")})
        if ((cur.get("cadence_last14") or 0) > 2 * (cur.get("cadence_prior14") or 0)
                and (cur.get("cadence_prior14") or 0) >= 1):
            fires.append({"rule": "d-cadence-surge",
                          "last14": cur.get("cadence_last14"),
                          "prior14": cur.get("cadence_prior14")})
    st["last_run"] = ts_now
    save_state(st)
    return fires, obs


def _last_two_swans():
    rows = []
    with open(JSONL_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    rows.sort(key=lambda r: r.get("ts") or "")

    def with_ctx(r):
        s = dict(r.get("swan") or {})
        k = r.get("kev") or {}
        s["rules_context"] = {"kev_count": k.get("count"),
                              "kev_released": k.get("released")}
        return s

    if len(rows) < 2:
        return None, None
    return with_ctx(rows[-1]), with_ctx(rows[-2])


def rollup(days=7):
    """Summarize the last `days` of pulse.jsonl as markdown on stdout —
    states only, no file writes (the caller archives it)."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    cut = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    with open(JSONL_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    if (r.get("ts") or "") >= cut:
                        rows.append(r)
                except ValueError:
                    pass
    if not rows:
        print("no rows in window")
        return 1
    first, last = rows[0], rows[-1]
    wk = now.isocalendar()
    counters = [
        ("KEV count", lambda r: (r.get("kev") or {}).get("count")),
        ("KEV perimeter entries", lambda r: len(
            (r.get("swan") or {}).get("perimeter_recent") or [])),
        ("Ransomware share %", lambda r: (r.get("swan") or {})
         .get("ransomware_share_pct")),
        ("Leak-site claims (sample)", lambda r: ((r.get("swan") or {})
         .get("ransomware_sample") or {}).get("claimed_today")),
        ("MCP hosts probed", lambda r: ((r.get("interop") or {})
         .get("mcp_trust") or {}).get("unique_hosts")),
        ("x402 correct-402", lambda r: ((r.get("interop") or {})
         .get("x402_trust") or {}).get("challenge_402")),
    ]
    lines = ["# Weekly rollup — %04d-W%02d (%d rows, %s → %s)" % (
        wk[0], wk[1], len(rows), first.get("ts"), last.get("ts")), "",
        "| Counter | first | last | Δ |", "|---|---|---|---|"]
    for name, get in counters:
        a, b = get(first), get(last)
        lines.append("| %s | %s | %s | %s |" % (
            name, a, b, "changed" if a != b else "flat"))
    lines += ["", "Runners: " + ", ".join(sorted(
        {(r.get("meta") or {}).get("runner", "canonical") for r in rows})),
        "", "measurement, not endorsement — states only; sources in feed.json."]
    print("\n".join(lines))
    return 0


def main():
    args = sys.argv[1:]
    if "--rollup" in args:
        days = 7
        if "--days" in args:
            days = int(args[args.index("--days") + 1])
        return rollup(days)
    if "--rules" in args:
        cur, prev = _last_two_swans()
        if not cur:
            print(json.dumps({"fires": [], "observations": [],
                              "note": "fewer than two rows with swan data"}))
            return 0
        fires, obs = evaluate_rules(cur, prev)
        print(json.dumps({"fires": fires, "observations": obs}, indent=2))
        return 0
    if "--enrich" in args:
        try:
            vulns, released, count = swan_stats.fetch_vulns()
        except Exception as e:
            print("UNREACHABLE: %s" % e, file=sys.stderr)
            return 1
        stats = swan_stats.compute(vulns)
        try:
            epss_enrich(stats.get("perimeter_recent", []))
        except Exception:
            pass
        rw = ransomware_victims()
        if rw:
            stats["ransomware_sample"] = rw
        stats["kev_released"] = released
        print(json.dumps(stats, indent=2))
        return 0
    print("usage: swan_watch.py --rules | --enrich", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
