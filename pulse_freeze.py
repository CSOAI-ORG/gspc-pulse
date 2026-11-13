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


def verify(manifest=None, quiet=False, require_full=False):
    """Verify the Ed25519-signed prefix, and report any later unsigned tail.

    The hourly public-HTTP watcher has no access to the private lane key. It may
    append observations after the last signed row. Those rows are deliberately
    not covered by the manifest and are never described as verified. Use
    ``require_full=True`` when a consumer requires every row to be signed.
    """
    if not (os.path.exists(MANIFEST) and os.path.exists(LEAVES)
            and os.path.exists(SIG)):
        print("freeze artifacts missing — run freeze first")
        return 2
    try:
        with open(MANIFEST, encoding="utf-8") as handle:
            manifest = json.load(handle)
        with open(LEAVES, encoding="utf-8") as handle:
            leaves = json.load(handle)
        with open(SIG, encoding="utf-8") as handle:
            sig = bytes.fromhex(handle.read().strip())
        rows = load_rows()
    except (OSError, ValueError, TypeError) as exc:
        print("FAIL: freeze artifacts unreadable: %s" % exc)
        return 1

    ok = True
    signature_ok = False
    signed_count = manifest.get("n_rows")
    if manifest.get("schema") != SCHEMA:
        print("FAIL: manifest schema mismatch")
        ok = False
    if type(signed_count) is not int or signed_count < 1:
        print("FAIL: manifest n_rows must be a positive integer")
        return 1
    if len(leaves) != signed_count:
        print("FAIL: manifest n_rows %d != %d signed leaves"
              % (signed_count, len(leaves)))
        ok = False
    if len(rows) < signed_count:
        print("FAIL: pulse.jsonl has %d rows but signed prefix requires %d"
              % (len(rows), signed_count))
        return 1

    signed_rows = rows[:signed_count]
    # The complete feed must remain well-formed and strictly time-ordered,
    # including unsigned observations. This is a structural check, not a
    # cryptographic claim about the tail.
    timestamps = [row.get("ts") if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(ts, str) or not ts for ts in timestamps):
        print("FAIL: every row must carry a non-empty timestamp")
        ok = False
    elif any(a >= b for a, b in zip(timestamps, timestamps[1:])):
        print("FAIL: pulse rows are not strictly time-ordered and unique")
        ok = False

    if signed_rows:
        if manifest.get("first_ts") != signed_rows[0].get("ts"):
            print("FAIL: manifest first_ts does not match signed prefix")
            ok = False
        if manifest.get("last_ts") != signed_rows[-1].get("ts"):
            print("FAIL: manifest last_ts does not match signed prefix")
            ok = False
    if manifest.get("leaf_count") != signed_count:
        print("FAIL: manifest leaf_count does not match n_rows")
        ok = False

    # 1. Signed prefix rows vs leaves. Later public-watcher rows are not in
    # this comparison: they are explicitly an unsigned observation tail.
    if len(leaves) == signed_count:
        for index, (row, leaf) in enumerate(zip(signed_rows, leaves)):
            if not isinstance(leaf, dict):
                print("FAIL: leaf %d is not an object" % index)
                ok = False
                break
            if leaf.get("ts") != row.get("ts") or leaf.get("sha") != leaf_sha(row):
                print("FAIL: signed row %d does not match its leaf" % index)
                ok = False
                break

    # 2. Chain + Merkle recomputation over the signed leaves only.
    try:
        leaf_shas = [leaf["sha"] for leaf in leaves]
        if manifest.get("chain_head") != chain_head(leaf_shas):
            print("FAIL: chain head mismatch")
            ok = False
        if manifest.get("merkle_root") != merkle_root(sorted(leaf_shas)):
            print("FAIL: Merkle root mismatch")
            ok = False
    except (KeyError, TypeError, ValueError):
        print("FAIL: malformed signed leaves")
        ok = False

    # 3. The manifest fingerprint and Ed25519 signature are checked separately.
    try:
        pub_bytes = bytes.fromhex(manifest["pubkey"])
        if hashlib.sha256(pub_bytes).hexdigest() != manifest.get("pubkey_fp"):
            print("FAIL: public-key fingerprint mismatch")
            ok = False
        pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
        payload = json.dumps(manifest, sort_keys=True,
                             separators=(",", ":")).encode()
        pub.verify(sig, payload)
        signature_ok = True
    except Exception as exc:
        print("FAIL: signature invalid: %s" % exc)
        ok = False

    tail = rows[signed_count:]
    if tail:
        first_tail = tail[0].get("ts")
        last_tail = tail[-1].get("ts")
        print("UNSIGNED TAIL: %d row(s), %s through %s; not covered by the Ed25519 signature"
              % (len(tail), first_tail, last_tail))
        if require_full:
            print("FAIL: --require-full requested a signature for every row")
            ok = False

    if not quiet or not ok:
        if ok and not tail:
            label = "VERIFIED FULL SERIES"
        elif ok:
            label = "VERIFIED SIGNED PREFIX"
        elif signature_ok and tail and require_full:
            label = "INCOMPLETE SIGNATURE COVERAGE"
        else:
            label = "BROKEN"
        print("%s: %d signed row(s) through %s; %d unsigned tail row(s); chain %s; root %s; signature %s"
              % (label, signed_count, manifest.get("last_ts"), len(tail),
                 str(manifest.get("chain_head", "?"))[:16],
                 str(manifest.get("merkle_root", "?"))[:16],
                 "ok" if signature_ok else "INVALID"))
    return 0 if ok else 1

def cmd_verify(a):
    return verify({}, quiet=a.quiet, require_full=a.require_full)


def inclusion_proof(ts):
    """Sibling path for a timestamp in the signed prefix, never the unsigned tail."""
    with open(LEAVES, encoding="utf-8") as handle:
        leaves = json.load(handle)
    with open(MANIFEST, encoding="utf-8") as handle:
        manifest = json.load(handle)
    signed_count = manifest.get("n_rows")
    if type(signed_count) is not int or signed_count != len(leaves):
        return None, "signed-prefix manifest/leaf count mismatch"
    target_leaf = next((l for l in leaves if l.get("ts") == ts), None)
    if not target_leaf:
        return None, "timestamp is not in the signed prefix (unsigned tail cannot be proved)"
    rows = load_rows()
    signed_rows = rows[:signed_count]
    row = next((r for r in signed_rows if r.get("ts") == ts), None)
    if row is None or target_leaf.get("sha") != leaf_sha(row):
        return None, "signed row does not match its committed leaf"
    shas = [l["sha"] for l in leaves]
    level = [bytes.fromhex(s) for s in sorted(shas)]
    # Merkle leaves are sorted by digest; map the selected digest to its position.
    pos = sorted(shas).index(target_leaf["sha"])
    if len(level) % 2:
        level.append(level[-1])
    proof = []
    while len(level) > 1:
        if pos % 2 == 1:
            proof.append(("L", level[pos - 1].hex()))
        else:
            proof.append(("R", level[pos + 1].hex()))
        level = [hashlib.sha256(level[i] + level[i + 1]).digest()
                 for i in range(0, len(level), 2)]
        pos //= 2
        if len(level) % 2 and len(level) > 1:
            level.append(level[-1])
    acc = bytes.fromhex(target_leaf["sha"])
    for side, sibling in proof:
        acc = (hashlib.sha256(bytes.fromhex(sibling) + acc) if side == "L"
               else hashlib.sha256(acc + bytes.fromhex(sibling))).digest()
    root = manifest.get("merkle_root")
    return ("VALID" if acc.hex() == root else "INVALID"), root


def cmd_prove(a):
    if verify({}, quiet=True) != 0:
        print("FAIL: signed prefix does not verify")
        return 1
    verdict, root = inclusion_proof(a.ts)
    if verdict is None:
        print("FAIL: %s" % root)
        return 1
    print("%s: ts %s inclusion against signed-prefix root %s"
          % (verdict, a.ts, root[:16]))
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
            rows[0]["kev"]["count"] += 1  # tamper a row that is covered by the signed prefix
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
        # Never leave a scratch backup beside the public series.
        if os.path.exists(JSONL + ".bak"):
            os.remove(JSONL + ".bak")
        shutil.rmtree(tmp, ignore_errors=True)
    print("self-test: no rows to tamper")
    return 2


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("freeze")
    v = sub.add_parser("verify")
    v.add_argument("--quiet", action="store_true")
    v.add_argument("--require-full", action="store_true",
                   help="fail if any rows follow the signed prefix")
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
