#!/bin/bash
# CONTINUUM - one-command demo. Run:  ./try-it.sh
cd "$(dirname "$0")" || exit 1

# macOS re-hides uv's .pth files, which makes Python 3.14 skip them.
# A symlink into site-packages is immune to that.
SP=".venv/lib/python3.14/site-packages"
[ -d "$SP" ] && [ ! -e "$SP/continuum" ] && ln -sfn "$PWD/src/continuum" "$SP/continuum"
chflags nohidden "$SP"/*.pth 2>/dev/null

export PATH="$PWD/.venv/bin:$PATH"
export PYTHONPATH="$PWD/src"

case "${1:-demo}" in
  demo)  python examples/crash_recovery_agent.py ;;
  test)  python -m pytest ;;
  cli)   shift; continuum "$@" ;;
  shell) echo "PATH and PYTHONPATH set. Try: continuum --help"; exec "$SHELL" ;;
  *)     echo "usage: ./try-it.sh [demo|test|cli ...|shell]" ;;
esac
