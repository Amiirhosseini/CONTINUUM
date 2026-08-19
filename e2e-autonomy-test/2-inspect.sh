#!/usr/bin/env bash
# Step 2: inspect intermediate state while the agent is PAUSED after INV-003.
#
# Read-only. Run this in a separate terminal after PROMPT 1's agent tells you it
# has completed three of five. It answers: did the agent actually use the tooling,
# and does the ledger match the files on disk?
set -uo pipefail
cd "$(dirname "$0")"
. ./env.sh

echo "=================================================================="
echo " INTERMEDIATE INSPECTION (expected: 3 of 5 done)"
echo "=================================================================="

echo
echo "--- runs (is '$E2E_RUN_ID' registered at all?) ------------------"
cont runs

echo
echo "--- progress (inspect .progress.completed, expect 3) ------------"
completed=$(cont_json inspect "$E2E_RUN_ID" 2>/dev/null \
  | "$E2E_PY" -c "import sys,json; print(json.load(sys.stdin)['progress']['completed'])" 2>/dev/null \
  || echo "N/A")
echo "  completed = $completed  (expected 3)"

echo
echo "--- ledger actions (expect 3 completed, 0 unresolved) -----------"
cont actions "$E2E_RUN_ID"

echo
echo "--- outbox files (expect exactly INV-001..003, no duplicates) ---"
ls -1 "$E2E_OUTBOX"/ 2>/dev/null || echo "  (outbox empty)"

echo
echo "=================================================================="
echo " READING:"
echo "  - No run / empty ledger  => agent IGNORED the tooling (finding!)."
echo "  - 3 completed / 0 unresolved / 3 files => healthy, proceed."
echo
echo " NEXT: HARD-KILL the Claude Code session now (do not message it)."
echo "       Then open a BRAND-NEW session and paste PROMPT 2."
echo "=================================================================="
