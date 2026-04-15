#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/device_helpers.sh"

DEVICE_NAME=''
DEVICE_ID=''
PREFER_MODEL=''
APP_PATH=''
BUNDLE_ID=''
SHOULD_LAUNCH='0'
TERMINATE_PID=''
DRY_RUN='0'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --device-name)
      DEVICE_NAME="$2"
      shift 2
      ;;
    --device-id)
      DEVICE_ID="$2"
      shift 2
      ;;
    --prefer-model)
      PREFER_MODEL="$2"
      shift 2
      ;;
    --app)
      APP_PATH="$2"
      shift 2
      ;;
    --bundle-id)
      BUNDLE_ID="$2"
      shift 2
      ;;
    --launch)
      SHOULD_LAUNCH='1'
      shift
      ;;
    --terminate-pid)
      TERMINATE_PID="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN='1'
      shift
      ;;
    --help|-h)
      echo 'Usage: bash scripts/device_install_and_launch.sh [--device-name <name>] [--device-id <devicectl-id>] [--prefer-model <text>] [--app <path>] [--bundle-id <bundle-id>] [--launch] [--terminate-pid <pid>] [--dry-run]'
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

if [[ "$SHOULD_LAUNCH" == '1' && -z "$BUNDLE_ID" ]]; then
  echo 'Error: --launch requires --bundle-id' >&2
  exit 1
fi

if [[ -z "$APP_PATH" && "$SHOULD_LAUNCH" != '1' && -z "$TERMINATE_PID" ]]; then
  echo 'Error: specify at least one of --app, --launch, or --terminate-pid' >&2
  exit 1
fi

if ! select_devicectl_device "$DEVICE_NAME" "$DEVICE_ID" "$PREFER_MODEL"; then
  echo "Error: $SELECT_DEVICE_ERROR" >&2
  exit 1
fi

printf 'Device: %s [%s] (%s)\n' "$SELECTED_DEVICE_NAME" "$SELECTED_DEVICE_IDENTIFIER" "$SELECTED_DEVICE_STATE"
printf 'Reason: %s\n' "$SELECTED_DEVICE_REASON"

run_command() {
  local command=("$@")
  printf 'Command: '
  printf '%q ' "${command[@]}"
  printf '\n'
  if [[ "$DRY_RUN" == '1' ]]; then
    return 0
  fi
  "${command[@]}"
}

if [[ -n "$APP_PATH" ]]; then
  run_command xcrun devicectl device install app --device "$SELECTED_DEVICE_IDENTIFIER" "$APP_PATH"
fi

if [[ "$SHOULD_LAUNCH" == '1' ]]; then
  run_command xcrun devicectl device process launch --device "$SELECTED_DEVICE_IDENTIFIER" "$BUNDLE_ID"
fi

if [[ -n "$TERMINATE_PID" ]]; then
  run_command xcrun devicectl device process terminate --device "$SELECTED_DEVICE_IDENTIFIER" --pid "$TERMINATE_PID"
fi
