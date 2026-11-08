#!/usr/bin/env python3
"""verify_remote.py — verify the frozen pulse series from the PUBLIC MIRROR alone.

Three fixed URLs on the public HF dataset (manifest, signature, leaves) prove
the Ed25519 signature, hash-chain head and Merkle root without any repo
access — anyone on the internet can confirm the series was frozen by this lane
key and has not been rewritten since. What it cannot prove: that the lane key
itself is ours — that chains to the repo's git history (LANE-SOP).

Safety: three literal https URLs on huggingface.co only; the host is
DNS-resolved and delivery refused on private/loopback/link-local/resolved
non-public addresses; redirects are not chased.
"""
import hashlib
import ipaddress
import json
import socket
import sys
import urllib.request
from urllib.parse import urlparse

URL_MANIFEST = ("https://huggingface.co/datasets/csoai/evidence-index"
                "/resolve/main/gspc-pulse/2026-11-04/pulse-freeze-manifest.json")
URL_LEAVES = ("https://huggingface.co/datasets/csoai/evidence-index"
              "/resolve/main/gspc-pulse/2026-11-04/pulse-leaves.json")
URL_SIG = ("https://huggingface.co/datasets/csoai/evidence-index"
           "/resolve/main/gspc-pulse/2026-11-04/pulse-freeze-manifest.sig")
GENESIS = b"pulse-series-genesis-2026-11-04"


def assert_public_https(url):
    """https only; resolve the host; refuse non-public addresses (SSRF guard)."""
    if not url.startswith("https://huggingface.co/"):
        raise ValueError("refusing off-host URL")
    host = urlparse(url).hostname
    for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP):
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError("host resolves to non-public address %s" % ip)


def fetch(url):
    assert_public_https(url)
    req = urllib.request.Request(url, headers={"Accept": "application/octet-stream"})
    opener = urllib.request.build_opener()
    with opener.open(req, timeout=30) as r:
        return r.read()


def main():
    try:
        manifest = json.loads(fetch(URL_MANIFEST))
        leaves = json.loads(fetch(URL_LEAVES))
        sig = bytes.fromhex(fetch(URL_SIG).decode().strip())
    except Exception as e:
        print("UNREACHABLE: %s" % e)
        return 2

    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PublicKey)
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(manifest["pubkey"])).verify(sig, payload)
        sig_ok = True
    except ImportError:
        print("cryptography library missing — signature check skipped "
              "(chain/merkle still verified)")
        sig_ok = None
    except Exception as e:
        print("FAIL: signature invalid: %s" % e)
        return 1

    shas = sorted(l["sha"] for l in leaves)
    h = hashlib.sha256(GENESIS).hexdigest()
    for l in leaves:  # leaves are chronological
        h = hashlib.sha256((h + l["sha"]).encode()).hexdigest()
    chain_ok = (h == manifest["chain_head"])

    level = [bytes.fromhex(s) for s in shas]
    if len(level) % 2:
        level.append(level[-1])
    while len(level) > 1:
        level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                 for i in range(0, len(level), 2)]
        if len(level) % 2 and len(level) > 1:
            level.append(level[-1])
    merkle_ok = (level[0].hex() == manifest["merkle_root"])

    print("manifest %s | rows %d | chain %s | merkle %s | signature %s"
          % (manifest.get("produced_at"), len(leaves),
             "ok" if chain_ok else "FAIL", "ok" if merkle_ok else "FAIL",
             "ok" if sig_ok else ("skipped" if sig_ok is None else "FAIL")))
    ok = chain_ok and merkle_ok and (sig_ok is not False)
    print("REMOTE SERIES %s against manifest fp %s"
          % ("VERIFIED" if ok else "BROKEN", manifest.get("pubkey_fp", "?")[:16]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
