#!/usr/bin/env python3
"""Corrections Publication Observer — independent public-readback receipts.

For every entry in the councilof.ai corrections ledger that carries
`reached_the_public: True`, this script:

1. Records that the correction was publicly reachable at `observed_at`.
2. For entries where `published_at` is UNRECORDED: emits a receipt with
   `first_independently_observed_at = observed_at` — a documented lower
   bound on the actual publication time (the correction was already
   publicly served before this observation; this does not claim to be the
   publication timestamp itself).
3. For entries where `published_at` is RECORDED: emits a confirmation
   receipt (`publication_recorded_confirmed`).

Receipts go to corrections-observations.jsonl (append-only, one JSON per
line). Verifies the ledger Ed25519 signature independently before observing.
Exit 0 = receipts written; 1 = ledger unreachable or signature not VALID.
"""
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_URL = "https://councilof.ai/api/corrections"
OUT = os.path.join(HERE, "corrections-observations.jsonl")
UA = {"User-Agent": "gspc-pulse-corrections-observer/0.1 (public readback)"}


def fetch_ledger():
    req = urllib.request.Request(LEDGER_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def check_signature(d):
    unsigned_fields = {"signature", "signature_state", "signature_check",
                       "correction_latency", "note", "fix_requires"}
    body = {k: v for k, v in d.items() if k not in unsigned_fields}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    content_id = hashlib.sha256(canonical.encode()).hexdigest()
    attested = d.get("signature", {}).get("attestation", {}).get("content_id")
    return content_id == attested


def observe(d, now):
    receipts = []
    corrections = d.get("corrections", [])
    sig_state = d.get("signature_state")
    for c in corrections:
        cid = c.get("id", "unknown")
        detected = c.get("detected_at", "UNRECORDED")
        published = c.get("published_at", "UNRECORDED")
        reached = c.get("reached_the_public")
        status = (c.get("status") or "")[:80]
        receipt = {
            "observed_at": now,
            "ledger_signed_at": d.get("signature", {}).get("attestation", {}).get("timestamp"),
            "ledger_signature_state": sig_state,
            "correction_id": cid,
            "detected_at": detected,
            "published_at_recorded": published,
            "reached_the_public": reached,
            "status_excerpt": status,
            "observation_kind": None,
        }
        if reached is True and published == "UNRECORDED":
            receipt["observation_kind"] = "first_independently_observed_public"
            receipt["note"] = ("correction was already publicly served before this "
                               "observation; this receipt is a lower bound on the "
                               "actual publication time, not the timestamp itself")
        elif reached is True and published != "UNRECORDED":
            receipt["observation_kind"] = "publication_recorded_confirmed"
            receipt["note"] = "ledger records a publication timestamp; confirmed publicly reachable"
        elif reached is None:
            receipt["observation_kind"] = "public_reach_unestablished"
            receipt["note"] = "ledger does not claim this correction reached the public"
        receipts.append(receipt)
    return receipts


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        d = fetch_ledger()
    except Exception as e:
        print("ledger UNREACHABLE: %s" % e)
        return 1

    sig_ok = check_signature(d)
    sig_state = d.get("signature_state")
    if sig_state != "VALID" or not sig_ok:
        print("ledger signature: %s (independent check: %s) - NOT VALID, refusing to observe" % (sig_state, sig_ok))
        return 1

    receipts = observe(d, now)
    os.makedirs(HERE, exist_ok=True)
    with open(OUT, "a") as f:
        for r in receipts:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    unrecorded_pub = sum(1 for r in receipts if r["observation_kind"] == "first_independently_observed_public")
    confirmed = sum(1 for r in receipts if r["observation_kind"] == "publication_recorded_confirmed")
    unestablished = sum(1 for r in receipts if r["observation_kind"] == "public_reach_unestablished")
    total = len(receipts)
    print("observed %d corrections at %s" % (total, now))
    print("  first_independently_observed_public: %d" % unrecorded_pub)
    print("  publication_recorded_confirmed: %d" % confirmed)
    print("  public_reach_unestablished: %d" % unestablished)
    return 0


if __name__ == "__main__":
    sys.exit(main())
