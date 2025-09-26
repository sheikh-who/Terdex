#!/bin/sh
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
PYTHON=${PYTHON:-python3}

WITH_OLLAMA=0
WITH_COLOR=0
PASS_ARGS=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --with-ollama)
      WITH_OLLAMA=1
      ;;
    --with-color)
      WITH_COLOR=1
      ;;
    --python)
      if [ "$#" -lt 2 ]; then
        echo "--python requires an interpreter path" >&2
        exit 1
      fi
      PYTHON="$2"
      shift
      ;;
    --help|-h)
      cat <<'USAGE'
Usage: installer.sh [options]

Options:
  --with-ollama   Install the Ollama extra
  --with-color    Install the colorized confetti extra
  --python PATH   Use a specific Python interpreter
  -h, --help      Show this message

Any additional arguments are forwarded to the underlying Python installer.
USAGE
      exit 0
      ;;
    --)
      shift
      PASS_ARGS="$PASS_ARGS $*"
      break
      ;;
    *)
      PASS_ARGS="$PASS_ARGS $1"
      ;;
  esac
  shift
done

EXTRA_FLAGS=""
if [ "$WITH_OLLAMA" -eq 1 ]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --with-ollama"
fi
if [ "$WITH_COLOR" -eq 1 ]; then
  EXTRA_FLAGS="$EXTRA_FLAGS --with-color"
fi

set -x
"$PYTHON" "$SCRIPT_DIR/install_terdex.py" $EXTRA_FLAGS $PASS_ARGS
