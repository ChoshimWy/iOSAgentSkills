#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/device_helpers.sh"

DEVICE_ID=""
DEVICE_NAME=""
PREFER_MODEL=""
RUN_SYSDIAGNOSE='0'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device)
      DEVICE_ID="$2"
      shift 2
      ;;
    --device-name)
      DEVICE_NAME="$2"
      shift 2
      ;;
    --prefer-model)
      PREFER_MODEL="$2"
      shift 2
      ;;
    --sysdiagnose)
      RUN_SYSDIAGNOSE='1'
      shift
      ;;
    --help|-h)
      echo 'Usage: bash scripts/device_diagnose.sh [--device <devicectl-id>] [--device-name <name>] [--prefer-model <text>] [--sysdiagnose]'
      exit 0
      ;;
    --*)
      echo "Error: unknown option $1" >&2
      exit 1
      ;;
    *)
      echo "Error: unexpected argument $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$DEVICE_ID" ]]; then
  if ! select_devicectl_device "$DEVICE_NAME" "$DEVICE_ID" "$PREFER_MODEL"; then
    echo "Error: $SELECT_DEVICE_ERROR" >&2
    exit 1
  fi
  DEVICE_ID="$SELECTED_DEVICE_IDENTIFIER"
  printf 'Selected device: %s [%s] (%s)\n' "$SELECTED_DEVICE_NAME" "$SELECTED_DEVICE_IDENTIFIER" "$SELECTED_DEVICE_STATE"
  printf 'Reason: %s\n\n' "$SELECTED_DEVICE_REASON"
fi

echo "Device: $DEVICE_ID"
echo

echo '== Details =='
xcrun devicectl device info details --device "$DEVICE_ID" || true

echo
echo '== Lock State =='
xcrun devicectl device info lockState --device "$DEVICE_ID" || true

echo
echo '== DDI Services =='
xcrun devicectl device info ddiServices --device "$DEVICE_ID" || true

echo
echo '== Processes =='
xcrun devicectl device info processes --device "$DEVICE_ID" || true

if [[ "$RUN_SYSDIAGNOSE" == '1' ]]; then
  echo
  echo '== Sysdiagnose =='
  xcrun devicectl device sysdiagnose --device "$DEVICE_ID" || true
fi
