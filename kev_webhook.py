#!/usr/bin/env python3
"""KEV→busabase webhook bridge (activation-ready; SCALE-PLAN gap 5 closer).

Diffs the newest archived row's KEV section against the previous row. When the
count moved or new CVE ids entered the top-20, POSTs one alert payload to the
configured busabase webhook and records the alert locally in alerts.jsonl
(same spirit as frozen-delta rows: changes + sha256 + ts).

Doctrine: the lane never pages by itself — delivery happens only when the
webhook URL is configured (BUSABASE_WEBHOOK_URL env or --url). Without it, run
--dry-run to see exactly what would be delivered. busabase is currently
offline; this script is dormant until LANE-SOP R6 activation.

Safety (per security review): https only; the webhook host is DNS-resolved and
delivery is refused if it lands on private/loopback/link-local/reserved space;
redirects are not followed (a 3xx is reported, not chased).

Usage:
  kev_webhook.py --dry-run
  BUSABASE_WEBHOOK_URL=https://… kev_webhook.py
  kev_webhook.py --url https://…
"""
import argparse
import hashlib
import ipaddress
import json
import os
import socket
import sys
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(HERE, "pulse.jsonl")
ALERTS = os.path.join(HERE, "alerts.jsonl")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # report redirects, never chase them


def assert_public_https(url):
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname:
        raise ValueError("webhook URL must be https://<host> (no other scheme)")
    for info in socket.getaddrinfo(u.hostname, 443, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError(
                "webhook host %s resolves to a non-public address (%s) — refusing"
                % (u.hostname, ip))
    return u


def last_two_rows():
    rows = []
    with open(JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: r.get("ts") or "")
    return (rows[-2], rows[-1]) if len(rows) >= 2 else (None, rows[-1] if rows else None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default=os.environ.get("BUSABASE_WEBHOOK_URL"))
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    if not os.path.exists(JSONL):
        print("no pulse.jsonl")
        return 1
    prev, cur = last_two_rows()
    if not prev or not cur or not cur.get("kev"):
        print("not enough rows with a kev section")
        return 2

    k_new, k_old = cur["kev"], (prev.get("kev") or {})
    new_ids = [c for c in k_new.get("top20", [])
               if c not in (k_old.get("top20") or [])]
    gone_ids = [c for c in (k_old.get("top20") or [])
                if c not in k_new.get("top20", [])]
    delta = k_new.get("count", 0) - k_old.get("count", 0)
    if not new_ids and delta == 0:
        print("no KEV movement since %s" % prev.get("ts"))
        return 0

    alert = {
        "kind": "kev-webhook",
        "ts": cur.get("ts"),
        "prev_ts": prev.get("ts"),
        "changes": {"kev_count": [k_old.get("count"), k_new.get("count")],
                    "kev_new_ids": new_ids, "kev_gone_ids": gone_ids},
        "top5_enriched": k_new.get("top5", []),
        "epss_model": k_new.get("epss_model"),
    }
    alert["sha256"] = hashlib.sha256(
        json.dumps(alert, sort_keys=True).encode()).hexdigest()

    if a.dry_run or not a.url:
        print("DRY-RUN payload (no URL configured — LANE-SOP R6):")
        print(json.dumps(alert, indent=2))
        delivered = False
    else:
        try:
            assert_public_https(a.url)
            req = urllib.request.Request(
                a.url, data=json.dumps(alert).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            opener = urllib.request.build_opener(_NoRedirect)
            with opener.open(req, timeout=20) as r:
                print("webhook -> %s" % r.status)
            delivered = True
        except ValueError as e:
            print("REFUSED:", e)
            delivered = False
        except Exception as e:
            print("webhook delivery failed (recorded undelivered):", e)
            delivered = False

    alert["delivered"] = delivered
    with open(ALERTS, "a") as f:
        f.write(json.dumps(alert, sort_keys=True) + "\n")
    print("alert recorded to alerts.jsonl (%d new ids, count %+d)"
          % (len(new_ids), delta))
    return 0


if __name__ == "__main__":
    sys.exit(main())
