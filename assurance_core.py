"""Deterministic evidence/triage helpers. No execution, signing or legal authority.

This is NOT a Byzantine consensus implementation. Instruments can share authors,
inputs and hosts; quorum is an advisory aggregation rule over a fixed roster.
Only the existing independently verified MEOK authorization gate can authorize effects.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import pathlib
import re
from contextlib import contextmanager
from datetime import datetime, timezone

MAX_BYTES = 8 * 1024 * 1024
AUTHORITY = re.compile(r"\b(pay\w*|deploy\w*|publish\w*|releas\w*|delet\w*|remov\w*|"
                       r"legal|counsel|contract\w*|xrpl|sign\w*|transfer\w*|send\w*|"
                       r"execut\w*|resum\w*|restart\w*|train\w*|approv\w*|authori[sz]\w*|"
                       r"credential\w*|secret\w*|grant\w*|revoke\w*)\b|needs-human-eyes", re.I)
GENESIS = b"session-ledger-genesis-2026-11-04"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def requires_human(text, kind="ops"):
    if kind not in ("ops", "doctrine", "payment"):
        return True
    return kind != "ops" or bool(AUTHORITY.search(text))


def assess_votes(votes, proposition, kind="ops", roster_size=None):
    """Strict >2/3 of the configured roster, not just available responders.

    A clear triage result never grants approval. Any explicit dissent or escalation
    remains a human referral. Missing/invalid data cannot become a positive vote.
    """
    if not isinstance(votes, dict):
        raise ValueError("votes must be an instrument-id mapping")
    roster = len(votes) if roster_size is None else roster_size
    if type(roster) is not int or roster < len(votes) or roster < 0:
        raise ValueError("invalid configured roster")
    counts = {v: 0 for v in ("yes", "no", "escalate", "abstain")}
    for value in votes.values():
        verdict = value[0] if isinstance(value, (list, tuple)) and value else value
        counts[verdict if isinstance(verdict, str) and verdict in counts else "abstain"] += 1
    counts["abstain"] += roster - len(votes)
    responding = roster - counts["abstain"]
    threshold = math.floor(2 * roster / 3) + 1 if roster else 1
    if requires_human(proposition, kind):
        decision, why = "HUMAN_DECIDES", "consequential or explicitly human-gated task class"
    elif not responding or responding < threshold:
        decision, why = "INSUFFICIENT_EVIDENCE", "fixed-roster quorum unavailable; abstention is not approval"
    elif counts["no"] or counts["escalate"]:
        decision, why = "HUMAN_DECIDES", "instrument dissent or escalation requires review"
    elif counts["yes"] >= threshold:
        decision, why = "TRIAGE_CLEAR", "advisory quorum only; proposition correctness is not established"
    else:
        decision, why = "INSUFFICIENT_EVIDENCE", "insufficient affirmative evidence"
    return {"decision": decision, "why": why, "counts": counts,
            "roster_size": roster, "responding": responding, "quorum": threshold,
            "bft_verified": False, "independent_voters_verified": False,
            "execution_authorized": False, "publication_authorized": False,
            "human_approval_verified": False}


def route_task(task, session):
    """Produce a plan only; no runner or model call is started."""
    if not isinstance(task, str) or not task.strip() or len(task) > 16000:
        raise ValueError("task must contain 1..16000 characters")
    if not isinstance(session, str) or not session.strip() or len(session) > 200:
        raise ValueError("explicit task session is required")
    chunks = [c.strip() for c in task.split(" and then ") if c.strip()]
    if len(chunks) > 100:
        raise ValueError("too many chunks")
    plan = []
    for i, chunk in enumerate(chunks):
        if requires_human(chunk):
            route = "human-gate"
        elif re.search(r"\b(verify|proof|frozen|merkle|measure|pulse|board|capsule)\b", chunk, re.I):
            route = "deterministic-engine"
        elif re.search(r"\b(kev|cve|vulnerability|epss|patch)\b", chunk, re.I):
            route = "evidence-review"
        elif re.search(r"\b(teach|explain|lesson)\b", chunk, re.I):
            route = "academy-read-only"
        else:
            route = "review-required"
        sid = digest({"parent": session, "task": task, "index": i, "chunk": chunk})[:24]
        plan.append({"chunk": i + 1, "parent_session_id": session,
                     "session_id": "c-" + sid, "task": chunk,
                     "route": route, "state": "PLANNED", "execution_authorized": False})
    return plan


def parse_jsonl(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError("ledger exceeds bounded read size")
    rows = []
    for i, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("malformed ledger row %d" % i) from exc
        if not isinstance(row, dict):
            raise ValueError("ledger row must be an object")
        rows.append(row)
    return rows


def read_jsonl(path):
    path = pathlib.Path(path)
    if path.is_symlink():
        raise ValueError("symlink ledger refused")
    if not path.exists():
        return []
    with path.open("rb") as f:
        return parse_jsonl(f.read(MAX_BYTES + 1))


def verify_chain(rows, genesis=GENESIS):
    previous = hashlib.sha256(genesis).hexdigest()
    for i, row in enumerate(rows, 1):
        item = dict(row)
        claimed = item.pop("sha256", None)
        if item.get("prev_sha256") != previous:
            raise ValueError("previous-hash mismatch at row %d" % i)
        actual = hashlib.sha256(previous.encode() + canonical(item)).hexdigest()
        if claimed != actual:
            raise ValueError("hash mismatch at row %d" % i)
        previous = claimed
    return previous


@contextmanager
def locked_file(path):
    """Local POSIX lock; all writers must use this helper to serialize appends."""
    import fcntl
    path = pathlib.Path(path)
    if not path.parent.is_dir():
        raise ValueError("ledger directory must already exist")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+b") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield f
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def append_event(path, event, genesis=GENESIS):
    """Verify existing bytes before append; never repair/re-hash corrupt history."""
    if any(k in event for k in ("sha256", "prev_sha256")):
        raise ValueError("caller cannot supply chain fields")
    if event.get("kind") == "human_decided":
        raise ValueError("generic writer cannot attest human approval; use verified authority adapter")
    with locked_file(path) as f:
        raw = f.read(MAX_BYTES + 1)
        rows = parse_jsonl(raw)
        previous = verify_chain(rows, genesis)
        entry = dict(event, prev_sha256=previous)
        entry["sha256"] = hashlib.sha256(previous.encode() + canonical(entry)).hexdigest()
        encoded = canonical(entry) + b"\n"
        if len(raw) + len(encoded) > MAX_BYTES:
            raise ValueError("ledger size limit reached; owner rotation required")
        f.seek(0, os.SEEK_END)
        if raw and not raw.endswith(b"\n"):
            f.write(b"\n")
        f.write(encoded)
        f.flush()
        os.fsync(f.fileno())
    return entry


def access_state(status):
    """A timeout, 403 or server failure is not a payment challenge."""
    if type(status) is not int:
        return "unreachable"
    return {200: "reachable-unvalidated", 401: "authentication-required",
            402: "payment-required", 403: "access-denied", 404: "not-found"}.get(status, "http-error")
