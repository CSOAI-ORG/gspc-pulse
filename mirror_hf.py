#!/usr/bin/env python3
"""mirror_hf.py — push the full public surface set to the HF dataset + Space.

Idempotent (HF skips unchanged files). Run via: engine.py mirror
(venv: ~/workspace_for_ai/plugins/gspc-live-state/venv-ots — has huggingface_hub
+ the local token). Private-repo raw URLs are auth-only; THIS mirror is the
public surface (LANE-SOP §5 lists the exact set).
"""
import os
import sys

from huggingface_hub import HfApi

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "csoai/evidence-index"
BASE = "gspc-pulse/2026-11-04"
SPACE = "csoai/gspc-council-os"

FILES = [
    "index.html", "llms.txt", "latest.json", "feed.json", "timeseries.csv",
    "README.md", "JOURNEYS.md", "RECONCILIATION.md", "PULSE-NODE.md",
    "LANE-SOP.md", "REPORT.md", "SCALE-PLAN.md", "XRPL-OWNER-ACTION.md",
    "PRODUCT.md", "LICENSE-EVIDENCE.md", "verification-log.jsonl",
    "alerts.jsonl", "pulse_freeze.py", "verify_remote.py", "engine.py",
    "kev_webhook.py", "surface-index.json", "tools.html", "dashboard.html",
    "pulse-freeze-manifest.json", "pulse-freeze-manifest.sig",
    "pulse-leaves.json", "rss.xml", "pyproject.toml", "council_bft.py",
    "SCALE-OUT.md", "session-events.schema.json",
    "assurance_core.py",  # required by the council advisory-triage source
]
EXTRA = [("/Users/iokfarm/workspace_for_ai/plugins/gspc-live-state/session-events.jsonl",
          BASE + "/session-events.jsonl")]
DIRS = ["watch", "posts", "ots-upgrades", "packs", "discovery", "inside",
        "space", "kaggle", "academy", "frameworks", "daily", "moat-v2",
        "variations", "claims", "evaluation", "cards", "deep-board"]
SPACE_FILES = [("space/app.py", "app.py"), ("space/README.md", "README.md")]


def main():
    api = HfApi()
    n = 0
    for name in FILES:
        p = os.path.join(HERE, name)
        if os.path.exists(p):
            api.upload_file(path_or_fileobj=p, path_in_repo=BASE + "/" + name,
                            repo_id=REPO, repo_type="dataset",
                            commit_message="mirror: public surface set")
            n += 1
    for d in DIRS:
        p = os.path.join(HERE, d)
        if os.path.isdir(p):
            api.upload_folder(folder_path=p, path_in_repo=BASE + "/" + d,
                              repo_id=REPO, repo_type="dataset",
                              commit_message="mirror: " + d + "/ complete")
            n += 1
    for local, remote in EXTRA:
        if os.path.exists(local):
            api.upload_file(path_or_fileobj=local, path_in_repo=remote,
                            repo_id=REPO, repo_type="dataset",
                            commit_message="mirror: session event continuity")
            n += 1
    for local, remote in SPACE_FILES:
        p = os.path.join(HERE, local)
        if os.path.exists(p):
            try:
                api.create_repo(SPACE, repo_type="space", space_sdk="gradio",
                                private=False, exist_ok=True)
            except Exception as e:
                print("space create:", e)
            api.upload_file(path_or_fileobj=p, path_in_repo=remote,
                            repo_id=SPACE, repo_type="space",
                            commit_message="GSPC Council OS — living measurement engine")
            n += 1
    print("mirror: %d items processed (%s + space)" % (n, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
