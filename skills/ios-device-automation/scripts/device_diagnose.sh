#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEVICE_ID="${1:-}"
RUN_SYSDIAGNOSE="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)
      DEVICE_ID="$2"
      shift 2
      ;;
    --sysdiagnose)
      RUN_SYSDIAGNOSE="1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

if [[ -z "$DEVICE_ID" ]]; then
  DEVICE_ID="$(python3 "$SCRIPT_DIR/device_selector.py" --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["selected"]["identifier"])')"
fi

echo "Device: $DEVICE_ID"
echo

echo "== Details =="
xcrun devicectl device info details --device "$DEVICE_ID" || true

echo
echo "== Lock State =="
xcrun devicectl device info lockState --device "$DEVICE_ID" || true

echo
echo "== DDI Services =="
xcrun devicectl device info ddiServices --device "$DEVICE_ID" || true

echo
echo "== Processes =="
xcrun devicectl device info processes --device "$DEVICE_ID" || true

if [[ "$RUN_SYSDIAGNOSE" == "1" ]]; then
  echo
  echo "== Sysdiagnose =="
  xcrun devicectl device sysdiagnose --device "$DEVICE_ID" || true
fi
