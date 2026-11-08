#!/usr/bin/env python3
"""Freeze the pulse series: hash-chain + Merkle root + Ed25519-signed manifest.

The GSPC capsule index freezes *its* measurements; this freezes ours, with the
same shape in miniature:
  - canonical row  -> sha256           (the leaves, sorted, like a batch rule)
  - chain head     -> sha256(prev + leaf)   (tamper-evident ordering)
  - merkle root    -> over sorted leaf shas (one root commits every row)
  - manifest       -> schema csoai.pulse-freeze-manifest/0.1, Ed25519-signed

Trust anchor: the lane's public key is committed to this repo; the private key
never is (it lives in the pulse state dir). This is signature-frozen, not
ledger-frozen — OTS/Rekor/XRPL anchoring remains owner-gated (SCALE-PLAN §3.1).

Usage:
  pulse_freeze.py freeze            # (re)build manifest+leaves+sig from pulse.jsonl
  pulse_freeze.py verify [--quiet]  # recompute everything, verify signature
  pulse_freeze.py prove --ts TS     # inclusion proof for one row against the root
  pulse_freeze.py self-test         # tamper a copy; verification must FAIL
Exit 0 verified / frozen; 1 failure; 2 nothing to verify yet.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
JSONL = os.path.join(HERE, "pulse.jsonl")
MANIFEST = os.path.join(HERE, "pulse-freeze-manifest.json")
LEAVES = os.path.join(HERE, "pulse-leaves.json")
SIG = os.path.join(HERE, "pulse-freeze-manifest.sig")
KEY = os.path.expanduser(
    "~/workspace_for_ai/plugins/gspc-live-state/keys/pulse-lane-key.pem")
SCHEMA = "csoai.pulse-freeze-manifest/0.1"
GENESIS = b"pulse-series-genesis-2026-11-04"

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey, Ed25519PublicKey)
    from cryptography.hazmat.primitives import serialization
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False


def canonical(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":")).encode()


def leaf_sha(row):
    return hashlib.sha256(canonical(row)).hexdigest()


def chain_head(shas):
    h = hashlib.sha256(GENESIS).hexdigest()
    for s in shas:
        h = hashlib.sha256((h + s).encode()).hexdigest()
    return h


def merkle_root(sorted_shas):
    if not sorted_shas:
        return hashlib.sha256(b"empty").hexdigest()
    level = [bytes.fromhex(s) for s in sorted_shas]
    if len(level) % 2:
        level.append(level[-1])
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            nxt.append(hashlib.sha256(level[i] + level[i + 1]).digest())
        level = nxt
        if len(level) % 2 and len(level) > 1:
            level.append(level[-1])
    return level[0].hex()


def load_rows():
    rows = []
    with open(JSONL) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    rows.sort(key=lambda r: r.get("ts") or "")
    return rows


def load_key():
    if not os.path.exists(KEY):
        os.makedirs(os.path.dirname(KEY), exist_ok=True)
        key = Ed25519PrivateKey.generate()
        pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption())
        fd = os.open(KEY, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(pem)
    with open(KEY, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def cmd_freeze(_):
    rows = load_rows()
    if not rows:
        print("no rows to freeze")
        return 2
    leaves = [{"ts": r.get("ts"), "sha": leaf_sha(r)} for r in rows]
    shas = sorted(l["sha"] for l in leaves)
    root = merkle_root(shas)
    head = chain_head([l["sha"] for l in leaves])
    key = load_key()
    pub = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    manifest = {
        "schema": SCHEMA,
        "produced_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_rows": len(rows),
        "first_ts": rows[0].get("ts"),
        "last_ts": rows[-1].get("ts"),
        "chain_head": head,
        "merkle_root": root,
        "leaf_count": len(shas),
        "pubkey": pub.hex(),
        "pubkey_fp": hashlib.sha256(pub).hexdigest(),
        "doctrine": "measurement, not endorsement; signature-frozen, "
                    "not ledger-frozen; trust anchor = this repo's git history",
    }
    payload = json.dumps(manifest, sort_keys=True,
                         separators=(",", ":")).encode()
    sig = key.sign(payload)
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)
    with open(LEAVES, "w") as f:
        json.dump(leaves, f, indent=2)
    with open(SIG, "w") as f:
        f.write(sig.hex())
    print("frozen %d rows | last_ts=%s | root=%s | head=%s | fp=%s"
          % (len(rows), manifest["last_ts"], root[:16], head[:16],
             manifest["pubkey_fp"][:16]))
    return 0


def verify(manifest, quiet=False):
    if not (os.path.exists(MANIFEST) and os.path.exists(LEAVES)
            and os.path.exists(SIG)):
        print("freeze artifacts missing — run freeze first")
        return 2
    manifest = json.load(open(MANIFEST))
    leaves = json.load(open(LEAVES))
    sig = bytes.fromhex(open(SIG).read().strip())
    rows = load_rows()
    ok = True
    # 1. rows vs leaves
    if [leaf_sha(r) for r in rows] != [l["sha"] for l in leaves]:
        print("FAIL: pulse.jsonl does not match leaves (rows moved since freeze)")
        ok = False
    # 2. counts and endpoints
    if manifest.get("n_rows") != len(rows):
        print("FAIL: manifest n_rows %s != %d" % (manifest.get("n_rows"), len(rows)))
        ok = False
    if manifest.get("last_ts") != (rows[-1].get("ts") if rows else None):
        print("FAIL: manifest last_ts stale")
        ok = False
    # 3. chain + merkle recomputation
    shas = sorted(l["sha"] for l in leaves)
    if manifest.get("chain_head") != chain_head([l["sha"] for l in leaves]):
        print("FAIL: chain head mismatch")
        ok = False
    if manifest.get("merkle_root") != merkle_root(shas):
        print("FAIL: merkle root mismatch")
        ok = False
    # 4. signature over canonical manifest bytes
    payload = json.dumps(manifest, sort_keys=True,
                         separators=(",", ":")).encode()
    try:
        pub = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(manifest["pubkey"]))
        pub.verify(sig, payload)
    except Exception as e:
        print("FAIL: signature invalid: %s" % e)
        ok = False
    if not quiet or not ok:
        print("%s: %d rows, chain %s, root %s, signature %s"
              % ("VERIFIED" if ok else "BROKEN", len(rows),
                 manifest.get("chain_head", "?")[:16],
                 manifest.get("merkle_root", "?")[:16],
                 "ok" if ok else "INVALID"))
    return 0 if ok else 1


def cmd_verify(a):
    return verify(json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {},
                  quiet=a.quiet)


def inclusion_proof(ts):
    """Sibling path for one leaf against the merkle root; verifies locally."""
    leaves = json.load(open(LEAVES))
    shas = sorted(l["sha"] for l in leaves)
    target = next((l["sha"] for l in leaves if l.get("ts") == ts), None)
    if not target:
        return None, "ts not in leaves"
    pos = shas.index(target)
    level = [bytes.fromhex(s) for s in shas]
    if len(level) % 2:
        level.append(level[-1])
    proof = []
    while len(level) > 1:
        if pos % 2 == 1:
            proof.append(("L", level[pos - 1].hex()))  # sibling is left
        else:
            proof.append(("R", level[pos + 1].hex()))  # sibling is right
        level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                 for i in range(0, len(level), 2)]
        pos //= 2
        if len(level) % 2 and len(level) > 1:
            level.append(level[-1])
    acc = bytes.fromhex(target)
    for side, sib in proof:
        acc = (hashlib.sha256(bytes.fromhex(sib) + acc) if side == "L"
               else hashlib.sha256(acc + bytes.fromhex(sib))).digest()
    root = json.load(open(MANIFEST)).get("merkle_root")
    return ("VALID" if acc.hex() == root else "INVALID"), root


def cmd_prove(a):
    verdict, root = inclusion_proof(a.ts)
    if verdict is None:
        print("FAIL: %s" % root)
        return 1
    print("%s: ts %s inclusion against root %s" % (verdict, a.ts, root[:16]))
    return 0 if verdict == "VALID" else 1


def cmd_self_test(_):
    """Tamper a copy of pulse.jsonl; verification must catch it."""
    import shutil, tempfile
    tmp = tempfile.mkdtemp()
    kept = (JSONL, MANIFEST, LEAVES, SIG)
    backups = [os.path.join(tmp, os.path.basename(p)) for p in kept]
    for src, dst in zip(kept, backups):
        if os.path.exists(src):
            shutil.copy2(src, dst)
    try:
        rows = load_rows()
        if rows:
            rows[-1]["kev"]["count"] += 1  # inject a lie
            shutil.copy2(JSONL, JSONL + ".bak")
            with open(JSONL, "w") as f:
                f.write("\n".join(json.dumps(r, sort_keys=True) for r in rows))
            rc = verify({}, quiet=True)
            print("self-test: tampered series detected -> %s"
                  % ("YES (correct)" if rc == 1 else "NO (BROKEN GUARD)"))
            return 0 if rc == 1 else 1
    finally:
        for src, dst in zip(kept, backups):
            if os.path.exists(dst):
                shutil.copy2(dst, src)
            elif os.path.exists(src + ".bak"):
                os.replace(src + ".bak", src)
        shutil.rmtree(tmp, ignore_errors=True)
    print("self-test: no rows to tamper")
    return 2


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("freeze")
    v = sub.add_parser("verify")
    v.add_argument("--quiet", action="store_true")
    pr = sub.add_parser("prove")
    pr.add_argument("--ts", required=True)
    sub.add_parser("self-test")
    a = p.parse_args()
    if not HAVE_CRYPTO:
        print("cryptography library unavailable — cannot freeze/verify")
        return 1
    return {"freeze": cmd_freeze, "verify": cmd_verify,
            "prove": cmd_prove, "self-test": cmd_self_test}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
