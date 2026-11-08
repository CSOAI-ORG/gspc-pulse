#!/usr/bin/env python3
"""Append a verification-cadence entry to verification-log.jsonl.

Reads a JSON event from stdin (or --file PATH) and appends it with a ts and a
content sha256. Typical events: verify_card head-card verdicts, verify_inclusion
leaf checks, capsule-index signature states, anchor states.

Usage: echo '{"kind":"verify_card","verdict":"VALID",...}' | record_verification.py
Dedupes on (kind, subject, verdict) within the same UTC day.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
VLOG = os.path.join(HERE, "verification-log.jsonl")


def main():
    raw = sys.stdin.read() if not sys.argv[1:] else open(sys.argv[2]).read()
    try:
        event = json.loads(raw)
    except ValueError as e:
        print("invalid JSON event:", e)
        return 1
    if not isinstance(event, dict) or "kind" not in event:
        print("event needs at least a 'kind' field")
        return 1
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    day = ts[:10]
    seen = set()
    if os.path.exists(VLOG):
        with open(VLOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        if r.get("ts", "").startswith(day):
                            seen.add((r.get("kind"), r.get("subject"),
                                      r.get("verdict")))
                    except ValueError:
                        pass
    key = (event.get("kind"), event.get("subject"), event.get("verdict"))
    if key in seen:
        print("already recorded today:", key)
        return 2
    row = dict(event)
    row["ts"] = ts
    body = json.dumps(row, sort_keys=True).encode()
    row["sha256"] = hashlib.sha256(body).hexdigest()
    with open(VLOG, "a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print("recorded:", event.get("kind"), event.get("verdict"), ts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
