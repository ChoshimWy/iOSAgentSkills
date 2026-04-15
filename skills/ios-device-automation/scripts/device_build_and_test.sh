#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/device_helpers.sh"

ROOT='.'
WORKSPACE=''
PROJECT=''
SCHEME=''
CONFIGURATION=''
ACTION=''
TEST_SUITE=''
DEVICE_NAME=''
DEVICE_ID=''
PREFER_MODEL=''
DRY_RUN='0'

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace)
      WORKSPACE="$2"
      shift 2
      ;;
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --scheme)
      SCHEME="$2"
      shift 2
      ;;
    --configuration)
      CONFIGURATION="$2"
      shift 2
      ;;
    --action)
      ACTION="$2"
      shift 2
      ;;
    --test-suite)
      TEST_SUITE="$2"
      shift 2
      ;;
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
    --dry-run)
      DRY_RUN='1'
      shift
      ;;
    --help|-h)
      echo 'Usage: bash scripts/device_build_and_test.sh <repo-root> [--workspace <path>] [--project <path>] [--scheme <name>] [--configuration <name>] [--action build|test] [--test-suite <suite>] [--device-name <name>] [--device-id <destination-id>] [--prefer-model <text>] [--dry-run]'
      exit 0
      ;;
    --*)
      echo "Error: unknown option $1" >&2
      exit 1
      ;;
    *)
      ROOT="$1"
      shift
      ;;
  esac
done

ROOT="$(cd "$ROOT" && pwd)"
WORKSPACE="${WORKSPACE:-$(read_xcode_env_value "$ROOT" XCODE_WORKSPACE || true)}"
PROJECT="${PROJECT:-$(read_xcode_env_value "$ROOT" XCODE_PROJECT || true)}"
SCHEME="${SCHEME:-$(read_xcode_env_value "$ROOT" XCODE_SCHEME || true)}"
CONFIGURATION="${CONFIGURATION:-$(read_xcode_env_value "$ROOT" XCODE_CONFIGURATION || true)}"
ACTION="${ACTION:-$(read_xcode_env_value "$ROOT" XCODE_ACTION || true)}"
DEVICE_NAME="${DEVICE_NAME:-$(read_xcode_env_value "$ROOT" XCODE_DEVICE_NAME || true)}"
PREFER_MODEL="${PREFER_MODEL:-$(read_xcode_env_value "$ROOT" XCODE_PREFER_MODEL || true)}"

ENV_DESTINATION="${XCODE_DESTINATION:-$(read_xcode_env_value "$ROOT" XCODE_DESTINATION || true)}"
if [[ -z "$DEVICE_ID" ]]; then
  DEVICE_ID="${XCODE_DEVICE_ID:-$(read_xcode_env_value "$ROOT" XCODE_DEVICE_ID || true)}"
fi
if [[ -z "$DEVICE_ID" ]]; then
  DEVICE_ID="$(destination_to_device_id "$ENV_DESTINATION" 2>/dev/null || true)"
fi

CONFIGURATION="${CONFIGURATION:-Debug}"
ACTION="${ACTION:-build}"

if [[ "$ACTION" != 'build' && "$ACTION" != 'test' ]]; then
  echo "Error: --action must be build or test" >&2
  exit 1
fi

if ! select_xcode_destination "$ROOT" "$WORKSPACE" "$PROJECT" "$SCHEME" "$DEVICE_NAME" "$DEVICE_ID" "$PREFER_MODEL"; then
  echo "Error: $SELECT_DEVICE_ERROR" >&2
  exit 1
fi

if [[ -z "$WORKSPACE" ]]; then
  WORKSPACE="$(pick_workspace "$ROOT" || true)"
fi
if [[ -z "$PROJECT" ]]; then
  PROJECT="$(pick_project "$ROOT" || true)"
fi
if [[ -z "$SCHEME" ]]; then
  SCHEME="$(pick_scheme "$ROOT" || true)"
fi

if [[ -z "$WORKSPACE" && -z "$PROJECT" ]]; then
  echo "Error: No .xcworkspace or .xcodeproj found in $ROOT" >&2
  exit 1
fi
if [[ -z "$SCHEME" ]]; then
  echo 'Error: No shared scheme found' >&2
  exit 1
fi

command=(xcodebuild)
if [[ -n "$WORKSPACE" ]]; then
  command+=( -workspace "$WORKSPACE" )
else
  command+=( -project "$PROJECT" )
fi
command+=(
  -scheme "$SCHEME"
  -configuration "$CONFIGURATION"
  -destination "id=$SELECTED_DEVICE_IDENTIFIER"
)
if [[ -n "$TEST_SUITE" ]]; then
  command+=( "-only-testing:$TEST_SUITE" )
fi
command+=( "$ACTION" )

printf 'Device: %s [%s] (%s)\n' "$SELECTED_DEVICE_NAME" "$SELECTED_DEVICE_IDENTIFIER" "$SELECTED_DEVICE_STATE"
printf 'Reason: %s\n' "$SELECTED_DEVICE_REASON"
printf 'Command: '
printf '%q ' "${command[@]}"
printf '\n'

if [[ "$DRY_RUN" == '1' ]]; then
  exit 0
fi

cd "$ROOT"
"${command[@]}"
