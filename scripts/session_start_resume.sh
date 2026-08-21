#!/bin/sh
# SessionStart hook that runs continuum resume out of band without a model turn.
# Install as a Claude Code SessionStart hook to make detection instant.
set -e
if command -v continuum >/dev/null 2>&1; then
  continuum resume --json 2>/dev/null | head -c 2000
fi
