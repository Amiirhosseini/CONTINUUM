#!/usr/bin/env bash
# Step 1: reset the world to a clean slate before the test.
#
# Wipes the test DB, the outbox, and recreates the 5-invoice work list. Run this
# once before you start the FIRST Claude Code session (PROMPT 1).
set -euo pipefail
cd "$(dirname "$0")"
. ./env.sh

echo "Resetting CONTINUUM autonomous e2e test..."

rm -f "$E2E_DB" "$E2E_DB"-wal "$E2E_DB"-shm
rm -rf "$E2E_OUTBOX"
mkdir -p "$E2E_OUTBOX"

printf 'INV-001\nINV-002\nINV-003\nINV-004\nINV-005\n' > "$E2E_INVOICES"

echo
echo "  DB       : $E2E_DB   (empty)"
echo "  outbox   : $E2E_OUTBOX/   (empty)"
echo "  invoices : $E2E_INVOICES"
cat "$E2E_INVOICES" | sed 's/^/             /'
echo "  run id   : $E2E_RUN_ID"
echo

# The MCP server (not the CLI) reads $CONTINUUM_DB. Remind the operator to point
# it at the same file, or the agent will write to a DB these scripts do not read.
echo "IMPORTANT: your Claude Code MCP server config for 'continuum' must set"
echo "  CONTINUUM_DB=$E2E_DB"
echo "  CONTINUUM_MCP_MUTATING_CLIENTS=claude-code claude"
echo "Then confirm it is live:  claude mcp list   ->   continuum ... Connected"
echo
echo "Next: paste PROMPT 1 (see README.md) into a fresh Claude Code session."
