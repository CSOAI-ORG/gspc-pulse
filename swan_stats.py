#!/usr/bin/env python3
"""KEV black-swan outlier scan for the gspc-pulse lane.

Computes fat-tail signals from a parsed CISA KEV feed and returns them as a
compact, JSON-serialisable dict — states only, never a verdict. Signals:

- ransomware_share: share of catalog flagged knownRansomwareCampaignUse=Known
- ransomware_flagged_recent: flagged entries added within `recent_days`
  (a count of 0 is attribution lag, not safety — flags land 2-6 weeks late)
- shortest_due_windows_days: N most urgent dateAdded->dueDate windows ever
- cadence_weekly: additions per ISO week for the last `weeks`
- cadence_last14 vs cadence_prior14: simple surge comparison
- cwe_top_recent: most-added CWE classes within `recent_days`

Usage:
  python3 swan_stats.py --url <kev-url>            # fetch + scan
  python3 swan_stats.py --file /tmp/kev.json       # scan a local feed
  python3 -c "import swan_stats; ..."              # compute(vulns) from code

Exit 0 on success, 1 when the feed could not be fetched/parsed.
"""
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

UA = {"User-Agent": "gspc-pulse-swan-watch/0.1 (measurement, not endorsement)"}
KEV_URL = ("https://www.cisa.gov/sites/default/files/feeds/"
           "known_exploited_vulnerabilities.json")
EPSS_URL = "https://api.first.org/data/v1/epss"
RW_VICTIMS_URL = "https://api.ransomware.live/v2/recentvictims"
LANE = os.path.expanduser(
    "~/workspace_for_ai/clawd-workspace/m2/evidence/gspc-pulse")
STATE_PATH = os.path.join(LANE, "watch", "watch_state.json")

PERIMETER_KEYWORDS = (
    "vpn", "firewall", "gateway", "connect secure", "netscaler",
    "big-ip", "f5", "pulse", "ivanti", "forti", "asa", "ftd", "edge",
    "sftp", "file transfer", "citrix", "palo", "sonicwall", "sslvpn",
)

# Query-parameter allowlist: only well-formed CVE ids from the KEV feed ever
# reach a query string, and every URL is an https module constant.
_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")


def _dt(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def compute(vulns, now=None, weeks=10, recent_days=21, due_top=5, cwe_top=6):
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    out = {}
    total = len(vulns)
    rw = [v for v in vulns
          if v.get("knownRansomwareCampaignUse") == "Known"]
    out["catalog_total"] = total
    out["ransomware_share_pct"] = round(100 * len(rw) / total, 1) if total else None
    recent_rw = [v for v in rw
                 if (d := _dt(v.get("dateAdded", "")))
                 and (now - d).days <= recent_days]
    out["ransomware_flagged_recent"] = len(recent_rw)
    out["ransomware_flagged_recent_cves"] = sorted(
        (v.get("cveID") for v in recent_rw), reverse=True)

    gaps = []
    for v in vulns:
        a, du = _dt(v.get("dateAdded", "")), _dt(v.get("dueDate", ""))
        if a and du:
            gaps.append(((du - a).days, v))
    gaps.sort(key=lambda g: g[0])
    out["shortest_due_windows"] = [
        {"days": g, "cve": v.get("cveID"), "vendor": v.get("vendorProject", ""),
         "product": v.get("product", ""),
         "ransomware": v.get("knownRansomwareCampaignUse"),
         "added": v.get("dateAdded", "")[:10]}
        for g, v in gaps[:due_top]]

    weekly = Counter()
    for v in vulns:
        a = _dt(v.get("dateAdded", ""))
        if a and (now - a).days <= weeks * 7:
            iso = a.isocalendar()
            weekly["%04d-W%02d" % (iso[0], iso[1])] += 1
    out["cadence_weekly"] = dict(sorted(weekly.items()))
    d14 = sum(1 for v in vulns
              if (a := _dt(v.get("dateAdded", "")))
              and (now - a).days <= 14)
    d28 = sum(1 for v in vulns
              if (a := _dt(v.get("dateAdded", "")))
              and 14 < (now - a).days <= 28)
    out["cadence_last14"] = d14
    out["cadence_prior14"] = d28

    cwes = Counter()
    for v in vulns:
        a = _dt(v.get("dateAdded", ""))
        if a and (now - a).days <= recent_days:
            for w in v.get("cwes", []) or ["(none listed)"]:
                cwes[w.get("cweID", str(w)) if isinstance(w, dict) else str(w)] += 1
    out["cwe_top_recent"] = dict(cwes.most_common(cwe_top))

    recent_all = sorted(
        (v for v in vulns
         if (a := _dt(v.get("dateAdded", "")))
         and (now - a).days <= recent_days),
        key=lambda v: v.get("dateAdded", ""), reverse=True)
    out["perimeter_recent"] = [
        {"cve": v.get("cveID"), "added": v.get("dateAdded", "")[:10],
         "due": v.get("dueDate", "")[:10],
         "vendor": v.get("vendorProject", ""), "product": v.get("product", "")}
        for v in recent_all
        if any(k in (v.get("product", "") + " " +
                     v.get("vendorProject", "")).lower()
               for k in PERIMETER_KEYWORDS)]
    return out


def fetch_vulns(url=KEV_URL, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    return d.get("vulnerabilities", []), d.get("dateReleased"), d.get("count")


def main():
    args = sys.argv[1:]
    if "--url" in args:
        url = args[args.index("--url") + 1]
    else:
        url = KEV_URL
    try:
        if "--file" in args:
            with open(args[args.index("--file") + 1]) as f:
                d = json.load(f)
            vulns = d.get("vulnerabilities", [])
            released, count = d.get("dateReleased"), d.get("count")
        else:
            vulns, released, count = fetch_vulns(url)
    except Exception as e:
        print("UNREACHABLE: could not fetch/parse KEV feed: %s" % e,
              file=sys.stderr)
        return 1
    stats = compute(vulns)
    stats["kev_released"] = released
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
