#!/bin/zsh
# daily_batch.sh — the autonomous day-cycle for the gspc-pulse lane.
# Loaded as a LaunchAgent (com.csoai.gspc-daily) so completion continues
# for days without anyone at the keyboard. Logs to the state dir.
set -u
LANE=/Users/iokfarm/workspace_for_ai/clawd-workspace/m2/evidence/gspc-pulse
VENV=/Users/iokfarm/workspace_for_ai/plugins/gspc-live-state/venv-ots/bin
LOG=/Users/iokfarm/workspace_for_ai/plugins/gspc-live-state/daily-batch.log
cd "$LANE" || exit 1
{
  echo "=== daily batch $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  python3 -I daily_report.py
  python3 -I build_rss.py
  python3 freeze_curriculum.py freeze && python3 freeze_curriculum.py verify --quiet
  python3 session_ledger.py verify
  "$VENV/python" -I verify_remote.py
  python3 -I gspc-live-audit.py 2>/dev/null || true
  "$VENV/python" -I mirror_hf.py
  echo "=== done $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
} >> "$LOG" 2>&1
