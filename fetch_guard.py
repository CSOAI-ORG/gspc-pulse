#!/usr/bin/env python3
"""Egress guard for gspc-pulse fetches.

Every remote fetch from this lane goes through get_json():
- https only (no cleartext, no file://)
- destination host must be on a fixed allowlist
- the host's DNS answer is resolved and any private / loopback / link-local /
  reserved / multicast answer is refused (DNS-rebinding and SSRF defense)
- redirects are disabled (a 3xx cannot hop to another host)
- only well-formed CVE ids are ever put into a query string (caller's duty,
  enforced by swan_stats._CVE_RE)
"""
import ipaddress
import json
import socket
import urllib.request
from urllib.parse import urlsplit

UA = {"User-Agent": "gspc-pulse/0.2 (measurement, not endorsement)"}

ALLOWED_HOSTS = {
    "www.cisa.gov",
    "api.first.org",
    "api.ransomware.live",
    "raw.githubusercontent.com",
    "councilof.ai",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _guard(url):
    sp = urlsplit(url)
    if sp.scheme != "https":
        raise ValueError("fetch_guard: https only, got %r" % sp.scheme)
    host = sp.hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError("fetch_guard: host not allowlisted: %r" % host)
    for _fam, _typ, _proto, _canon, sa in socket.getaddrinfo(host, 443):
        ip = ipaddress.ip_address(sa[0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            raise ValueError(
                "fetch_guard: %s resolves to non-public IP %s" % (host, ip))
    return url


def get_json(url, timeout=30):
    req = urllib.request.Request(_guard(url), headers=UA)
    with _OPENER.open(req, timeout=timeout) as r:
        return json.loads(r.read())
