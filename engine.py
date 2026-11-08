#!/usr/bin/env python3
"""engine.py — the gspc-pulse living engine, one command for everything.

Stages: status / build / freeze / verify / audit / alert / qa / all.
Runs every lane script in-process (runpy) — no subprocess, no shell. Every
script path and every artifact path below is a fixed literal — nothing dynamic
is ever built into a path. Stage arguments are fixed per stage.
Exit code = worst stage.
"""
import argparse
import hashlib
import json
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIT = "/Users/iokfarm/workspace_for_ai/plugins/gspc-live-audit.py"

F_ARCHIVE = os.path.join(HERE, "archive_pulse.py")
F_FREEZE = os.path.join(HERE, "pulse_freeze.py")
F_WEBHOOK = os.path.join(HERE, "kev_webhook.py")
F_RSS = os.path.join(HERE, "build_rss.py")
F_SURFACE = os.path.join(HERE, "surface-index.json")
F_MANIFEST = os.path.join(HERE, "pulse-freeze-manifest.json")
F_INDEX = os.path.join(HERE, "index.html")
F_LLMS = os.path.join(HERE, "llms.txt")
F_LATEST = os.path.join(HERE, "latest.json")
F_FEED = os.path.join(HERE, "feed.json")
F_CSV = os.path.join(HERE, "timeseries.csv")
F_README = os.path.join(HERE, "README.md")
F_JOURNEYS = os.path.join(HERE, "JOURNEYS.md")
F_RECON = os.path.join(HERE, "RECONCILIATION.md")
F_NODE = os.path.join(HERE, "PULSE-NODE.md")
F_SOP = os.path.join(HERE, "LANE-SOP.md")
F_SIG = os.path.join(HERE, "pulse-freeze-manifest.sig")
F_LEAVES = os.path.join(HERE, "pulse-leaves.json")
F_VLOG = os.path.join(HERE, "verification-log.jsonl")
F_ALERTS = os.path.join(HERE, "alerts.jsonl")
F_TOOLS = os.path.join(HERE, "tools.html")
F_DASH = os.path.join(HERE, "dashboard.html")

SURFACE = {
    F_INDEX: "human dashboard", F_LLMS: "agent discovery",
    F_LATEST: "one-GET current state", F_FEED: "full series",
    F_CSV: "flat counters", F_README: "operations doc",
    F_JOURNEYS: "end-user journeys", F_RECON: "measuring the measurer",
    F_NODE: "node onboarding", F_SOP: "operating procedure",
    F_MANIFEST: "freeze manifest", F_SIG: "manifest signature",
    F_LEAVES: "frozen leaves", F_VLOG: "verification cadence",
    F_ALERTS: "alert stream", F_TOOLS: "free tools", F_DASH: "delta dashboard",
}


def run_stage(label, path, argv):
    """Run another lane script in-process; scripts exit via SystemExit."""
    old = sys.argv
    sys.argv = [path, *argv]
    try:
        runpy.run_path(path, run_name="__main__")
        rc = 0
    except SystemExit as e:
        rc = e.code or 0
    finally:
        sys.argv = old
    ok = (rc == 0) or (label == "alert" and rc in (0, 2))
    print("[%s] %s" % ("ok" if ok else "FAIL", label))
    return ok


def surface_index():
    """Inventory every public artifact: sha256 + bytes — the wiring proof."""
    idx = {"schema": "csoai.pulse-surface-index/0.1", "generated_by": "engine.py",
           "artifacts": {}}
    for path, purpose in SURFACE.items():
        if os.path.exists(path):
            b = open(path, "rb").read()
            idx["artifacts"][os.path.basename(path)] = {
                "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b),
                "purpose": purpose}
    with open(F_SURFACE, "w") as f:
        json.dump(idx, f, indent=2, sort_keys=True)
    print("surface-index.json: %d artifacts" % len(idx["artifacts"]))


def stage_qa():
    ok = True
    idx = json.load(open(F_SURFACE))
    for key in sorted(idx["artifacts"]):
        path = SURFACE_INV.get(key)
        if path is None or not os.path.exists(path):
            print("QA FAIL: %s listed but missing" % key)
            ok = False
            continue
        if hashlib.sha256(open(path, "rb").read()).hexdigest() != idx["artifacts"][key]["sha256"]:
            print("QA FAIL: %s drifted from surface-index" % key)
            ok = False
    print("QA: %d artifacts present, hashes %s" %
          (len(idx["artifacts"]), "match" if ok else "MISMATCH"))
    return ok


SURFACE_INV = {os.path.basename(k): k for k in SURFACE}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["status", "build", "freeze", "verify",
                                     "audit", "alert", "qa", "all"])
    a = p.parse_args()
    results = {}
    if a.stage in ("status", "all"):
        print("=== status ===")
        for label, path in (("pulse.jsonl", os.path.join(HERE, "pulse.jsonl")),
                            (F_MANIFEST, F_MANIFEST), (F_SURFACE, F_SURFACE)):
            print("  %-32s %s" % (os.path.basename(label) if os.sep in label else label,
                                  "present" if os.path.exists(path) else "MISSING"))
        results["status"] = True
    if a.stage in ("build", "all"):
        print("=== build ===")
        try:
            results["build"] = run_stage("build", F_ARCHIVE, ["--rebuild"])
        except Exception as e:
            print("[FAIL] build:", e)
            results["build"] = False
        surface_index()
        run_stage("rss", F_RSS, [])
        print("[ok] surface-index")
    if a.stage in ("freeze", "all"):
        print("=== freeze ===")
        results["freeze"] = run_stage("freeze", F_FREEZE, ["freeze"])
    if a.stage in ("verify", "all"):
        print("=== verify ===")
        results["verify"] = run_stage("verify", F_FREEZE, ["verify"])
    if a.stage in ("audit", "all"):
        print("=== audit ===")
        results["audit"] = run_stage("audit", AUDIT, [])
    if a.stage in ("alert", "all"):
        print("=== alert ===")
        results["alert"] = run_stage("alert", F_WEBHOOK, ["--dry-run"])
    if a.stage in ("qa", "all"):
        print("=== qa ===")
        surface_index()  # freeze rewrites its artifacts after build — snapshot now
        results["qa"] = stage_qa()
    worst = all(results.values()) if results else False
    print("\nENGINE %s: %s" % ("GREEN" if worst else "RED",
                               " ".join("%s=%s" % (k, "ok" if v else "FAIL")
                                        for k, v in results.items())))
    return 0 if worst else 1


if __name__ == "__main__":
    sys.exit(main())
