# Shared configuration for the CONTINUUM autonomous end-to-end test.
# Source this from the other scripts: `. ./env.sh`
#
# This file is the single source of truth for the DB path, run id, and the
# python/CLI invocations, so every script and both prompts agree on them.

# Absolute paths so the scripts work regardless of the caller's cwd.
export E2E_DB="/tmp/continuum-e2e-test.db"
export E2E_OUTBOX="/tmp/e2e-outbox"
export E2E_INVOICES="/tmp/e2e-invoices.txt"
export E2E_RUN_ID="invoice-batch-e2e"

# The interpreter that has continuum + the mcp extra installed. Adjust if your
# environment differs (the MCP server is registered against this same python).
export E2E_PY="/opt/miniconda3/bin/python"

# The CLI honours --db but NOT $CONTINUUM_DB, so every call passes --db E2E_DB.
# Warnings from an unrelated urllib3/requests mismatch are filtered for signal.
cont() {
  "$E2E_PY" -m continuum.cli --db "$E2E_DB" "$@" 2>&1 \
    | grep -v RequestsDependencyWarning | grep -v "warnings.warn"
}

# JSON variant: --json is a GLOBAL flag and must precede the subcommand.
cont_json() {
  "$E2E_PY" -m continuum.cli --db "$E2E_DB" --json "$@" 2>&1 \
    | grep -v RequestsDependencyWarning | grep -v "warnings.warn"
}
