#!/usr/bin/env python3
"""Validate and publish the GSPC pulse to its Hugging Face dataset mirror.

The Hub card declares explicit JSONL and CSV configurations so Dataset Viewer
can build both tables. The signed manifest covers only its declared prefix;
any later public-watcher observations are reported as an unsigned tail.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "csoai/gspc-pulse"
DATA_FILES = [
    "pulse.jsonl", "timeseries.csv", "feed.json", "latest.json", "llms.txt",
    "index.html", "pulse-freeze-manifest.json", "pulse-freeze-manifest.sig",
    "pulse-leaves.json", "REPORT.md", "RECONCILIATION.md", "alerts.jsonl",
    "verification-log.jsonl", "dashboard.html", "PULSE-NODE.md",
]


def _read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _verify_signed_prefix(root):
    sys.path.insert(0, str(root))
    import pulse_freeze
    names = ("JSONL", "MANIFEST", "LEAVES", "SIG")
    previous = {name: getattr(pulse_freeze, name) for name in names}
    try:
        pulse_freeze.JSONL = str(root / "pulse.jsonl")
        pulse_freeze.MANIFEST = str(root / "pulse-freeze-manifest.json")
        pulse_freeze.LEAVES = str(root / "pulse-leaves.json")
        pulse_freeze.SIG = str(root / "pulse-freeze-manifest.sig")
        return pulse_freeze.verify({}, quiet=True)
    finally:
        for name, value in previous.items():
            setattr(pulse_freeze, name, value)


def validate(root=ROOT):
    root = Path(root)
    rows = [json.loads(line) for line in (root / "pulse.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("pulse.jsonl is empty")
    timestamps = [row.get("ts") for row in rows]
    if any(not isinstance(ts, str) or not ts for ts in timestamps):
        raise ValueError("every pulse row must have a timestamp")
    if any(a >= b for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError("pulse rows must be strictly time-ordered and unique")

    feed = _read_json(root / "feed.json")
    latest = _read_json(root / "latest.json")
    if feed.get("row_count") != len(rows) or feed.get("rows") != rows:
        raise ValueError("feed.json does not exactly match pulse.jsonl")
    if latest.get("latest") != rows[-1]:
        raise ValueError("latest.json does not match the final pulse row")
    with (root / "timeseries.csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    if len(csv_rows) != len(rows):
        raise ValueError("timeseries.csv row count does not match pulse.jsonl")

    manifest = _read_json(root / "pulse-freeze-manifest.json")
    leaves = _read_json(root / "pulse-leaves.json")
    signed_count = manifest.get("n_rows")
    if type(signed_count) is not int or signed_count != len(leaves) or signed_count > len(rows):
        raise ValueError("manifest/leaf count is not a valid signed prefix")
    if _verify_signed_prefix(root) != 0:
        raise ValueError("Ed25519 signed prefix failed verification")

    card_path = root / "hf" / "README.md"
    card = card_path.read_text(encoding="utf-8")
    if not card.startswith("---\n"):
        raise ValueError("Hugging Face dataset card is missing YAML front matter")
    import yaml
    try:
        _, frontmatter, _ = card.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
    except Exception as exc:
        raise ValueError("dataset card front matter is invalid: %s" % exc)
    configs = {item.get("config_name"): item.get("data_files", [])
               for item in metadata.get("configs", [])}
    expected = {
        "pulse-jsonl": [{"split": "train", "path": "pulse.jsonl"}],
        "pulse-timeseries": [{"split": "train", "path": "timeseries.csv"}],
    }
    if configs != expected:
        raise ValueError("dataset card configs must explicitly expose pulse.jsonl and timeseries.csv")

    return {
        "rows": len(rows),
        "latest_ts": timestamps[-1],
        "signed_prefix_rows": signed_count,
        "signed_prefix_last_ts": manifest.get("last_ts"),
        "unsigned_tail_rows": len(rows) - signed_count,
        "signature_state": "SIGNED_PREFIX_ONLY" if len(rows) > signed_count else "FULLY_SIGNED",
    }


def _stage(root, directory, summary):
    directory = Path(directory)
    for name in DATA_FILES:
        source = root / name
        if not source.is_file():
            raise FileNotFoundError("required mirror file missing: %s" % name)
        shutil.copy2(source, directory / name)
    shutil.copy2(root / "hf" / "README.md", directory / "README.md")

    hashes = {}
    for name in DATA_FILES + ["README.md"]:
        data = (directory / name).read_bytes()
        hashes[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    receipt = {
        "schema": "csoai.gspc-pulse-hf-mirror-receipt/0.1",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_repository": "CSOAI-ORG/gspc-pulse",
        "source_revision": os.environ.get("GITHUB_SHA"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        **summary,
        "authority": "unsigned publication receipt; file hashes aid reproduction but are not a signature",
        "files": hashes,
    }
    (directory / "mirror-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    digest = [
        "# GSPC Pulse — current mirror digest", "",
        "- Latest observation: `%s`" % summary["latest_ts"],
        "- Rows in feed: **%d**" % summary["rows"],
        "- Ed25519-signed prefix: **%d rows**, through `%s`" % (summary["signed_prefix_rows"], summary["signed_prefix_last_ts"]),
        "- Unsigned public-watcher tail: **%d rows**" % summary["unsigned_tail_rows"],
        "- Signature state: `%s`" % summary["signature_state"], "",
        "The signature does not cover the unsigned tail. Run `pulse_freeze.py verify` to verify the prefix; use `--require-full` to reject a tail.",
        "The publication receipt is unsigned and does not extend the signing authority.", "",
        "Source: https://github.com/CSOAI-ORG/gspc-pulse",
    ]
    (directory / "DIGEST.md").write_text("\n".join(digest) + "\n", encoding="utf-8")
    (directory / "mirror-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="validate local files without publishing")
    group.add_argument("--publish", action="store_true", help="publish the validated mirror to Hugging Face")
    args = parser.parse_args()
    summary = validate(ROOT)
    print(json.dumps(summary, indent=2))
    if args.check:
        return 0
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("HF_TOKEN is required for --publish")
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.repo_info(DATASET_ID, repo_type="dataset")  # fail closed if the target repo is absent
    with tempfile.TemporaryDirectory(prefix="gspc-hf-mirror-") as tmp:
        _stage(ROOT, tmp, summary)
        commit = api.upload_folder(
            folder_path=tmp,
            repo_id=DATASET_ID,
            repo_type="dataset",
            commit_message="Sync verified GSPC pulse data and Dataset Viewer configs",
        )
    print("PUBLISHED Hugging Face dataset %s commit=%s" % (DATASET_ID, getattr(commit, "oid", "accepted")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
