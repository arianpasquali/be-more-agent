#!/usr/bin/env bash
# Dispatcher: routes to setup-pi.sh on Linux, setup-mac.sh on macOS.
# You can also call the platform script directly.
set -euo pipefail

case "$(uname -s)" in
  Linux)
    exec "$(dirname "$0")/setup-pi.sh" "$@"
    ;;
  Darwin)
    exec "$(dirname "$0")/setup-mac.sh" "$@"
    ;;
  *)
    echo "[bmo-orq] unsupported platform: $(uname -s). Supported: Linux (Pi), Darwin (macOS)." >&2
    exit 1
    ;;
esac
