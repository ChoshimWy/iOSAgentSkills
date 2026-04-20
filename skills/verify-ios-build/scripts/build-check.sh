#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVICE_HELPERS="$SCRIPT_DIR/../../ios-device-automation/scripts/device_helpers.sh"
# shellcheck source=/dev/null
source "$DEVICE_HELPERS"

ROOT="$PWD"
if [[ $# -gt 0 && "$1" != -* ]]; then
  ROOT="$1"
fi
ROOT="$(cd "$ROOT" && pwd)"

env_or_file_value() {
  local key="$1"
  if [[ ${!key+x} == x ]]; then
    printf '%s' "${!key}"
    return 0
  fi
  read_xcode_env_value "$ROOT" "$key" || true
}

XCODE_DESTINATION_VALUE="$(env_or_file_value XCODE_DESTINATION)"
XCODE_DEVICE_ID_VALUE="$(env_or_file_value XCODE_DEVICE_ID)"
XCODE_DEVICE_NAME_VALUE="$(env_or_file_value XCODE_DEVICE_NAME)"
XCODE_PREFER_MODEL_VALUE="$(env_or_file_value XCODE_PREFER_MODEL)"
XCODE_DEVICE_FALLBACK_VALUE="$(env_or_file_value XCODE_DEVICE_FALLBACK)"
XCODE_WORKSPACE_VALUE="$(env_or_file_value XCODE_WORKSPACE)"
XCODE_PROJECT_VALUE="$(env_or_file_value XCODE_PROJECT)"
XCODE_SCHEME_VALUE="$(env_or_file_value XCODE_SCHEME)"

XCODE_DEVICE_FALLBACK_VALUE="${XCODE_DEVICE_FALLBACK_VALUE:-1}"

set_selected_target_env() {
  export XCODE_SELECTED_DEVICE_NAME="$1"
  export XCODE_SELECTED_DEVICE_ID="$2"
  export XCODE_SELECTED_DEVICE_STATE="$3"
  export XCODE_SELECTED_DEVICE_MODEL="${4:-}"
  export XCODE_SELECTED_DEVICE_REASON="$5"
}

unset XCODE_SELECTED_DEVICE_NAME XCODE_SELECTED_DEVICE_ID XCODE_SELECTED_DEVICE_STATE XCODE_SELECTED_DEVICE_MODEL XCODE_SELECTED_DEVICE_REASON || true
unset XCODE_FALLBACK_DEVICE_NAME XCODE_FALLBACK_DEVICE_ID XCODE_FALLBACK_DEVICE_STATE XCODE_FALLBACK_DEVICE_MODEL XCODE_FALLBACK_DEVICE_REASON XCODE_FALLBACK_DEVICE_ERROR || true
unset XCODE_VALIDATION_PLATFORM || true

if [[ -z "$XCODE_DESTINATION_VALUE" ]]; then
  if [[ -n "$XCODE_DEVICE_ID_VALUE" && -z "$XCODE_DEVICE_NAME_VALUE" && -z "$XCODE_PREFER_MODEL_VALUE" ]]; then
    export XCODE_DEVICE_ID="$XCODE_DEVICE_ID_VALUE"
    export XCODE_DEVICE_NAME=""
    export XCODE_PREFER_MODEL=""
    export XCODE_VALIDATION_PLATFORM='ios-device'
    set_selected_target_env "$XCODE_DEVICE_ID_VALUE" "$XCODE_DEVICE_ID_VALUE" 'explicit' '' 'using explicit device identifier'
  else
    if select_xcode_destination "$ROOT" "$XCODE_WORKSPACE_VALUE" "$XCODE_PROJECT_VALUE" "$XCODE_SCHEME_VALUE" "$XCODE_DEVICE_NAME_VALUE" "$XCODE_DEVICE_ID_VALUE" "$XCODE_PREFER_MODEL_VALUE" 'connected-only'; then
      export XCODE_DEVICE_ID="$SELECTED_DEVICE_IDENTIFIER"
      export XCODE_DEVICE_NAME=""
      export XCODE_PREFER_MODEL=""
      export XCODE_VALIDATION_PLATFORM='ios-device'
      set_selected_target_env "$SELECTED_DEVICE_NAME" "$SELECTED_DEVICE_IDENTIFIER" "$SELECTED_DEVICE_STATE" "$SELECTED_DEVICE_MODEL" "$SELECTED_DEVICE_REASON"
    else
      case "$SELECT_DEVICE_ERROR" in
        "no connected physical iOS destinations available"*|"no physical iOS destinations available"*)
          if supports_xcode_platform "$ROOT" "$XCODE_WORKSPACE_VALUE" "$XCODE_PROJECT_VALUE" "$XCODE_SCHEME_VALUE" 'iOS Simulator'; then
            export XCODE_DESTINATION='generic/platform=iOS Simulator'
            export XCODE_VALIDATION_PLATFORM='ios-simulator'
            set_selected_target_env 'iOS Simulator' 'generic/platform=iOS Simulator' 'simulator' '' 'no connected physical iOS destination available; using simulator'
          elif supports_xcode_platform "$ROOT" "$XCODE_WORKSPACE_VALUE" "$XCODE_PROJECT_VALUE" "$XCODE_SCHEME_VALUE" 'macOS'; then
            export XCODE_VALIDATION_PLATFORM='macos'
            set_selected_target_env 'macOS Host' 'macOS' 'macos' '' 'no iOS destination available; using macOS host build'
          else
            echo "Initial validation blocked: no connected physical iOS destination, no iOS Simulator destination, and no macOS destination available" >&2
            exit 1
          fi
          ;;
        *)
          echo "Initial physical-device validation blocked: $SELECT_DEVICE_ERROR" >&2
          exit 1
          ;;
      esac
    fi
  fi
else
  export XCODE_DESTINATION="$XCODE_DESTINATION_VALUE"
  if is_simulator_destination_text "$XCODE_DESTINATION_VALUE"; then
    export XCODE_VALIDATION_PLATFORM='ios-simulator'
  fi
fi

if [[ -n "$XCODE_DESTINATION_VALUE" ]] && is_simulator_destination_text "$XCODE_DESTINATION_VALUE" && [[ "$XCODE_DEVICE_FALLBACK_VALUE" != '0' ]]; then
  if [[ -n "$XCODE_DEVICE_ID_VALUE" && -z "$XCODE_DEVICE_NAME_VALUE" && -z "$XCODE_PREFER_MODEL_VALUE" ]]; then
    export XCODE_DEVICE_ID="$XCODE_DEVICE_ID_VALUE"
    export XCODE_DEVICE_NAME=""
    export XCODE_PREFER_MODEL=""
    export XCODE_FALLBACK_DEVICE_NAME="$XCODE_DEVICE_ID_VALUE"
    export XCODE_FALLBACK_DEVICE_ID="$XCODE_DEVICE_ID_VALUE"
    export XCODE_FALLBACK_DEVICE_STATE='explicit'
    export XCODE_FALLBACK_DEVICE_REASON='using explicit device identifier'
  else
    if select_xcode_destination "$ROOT" "$XCODE_WORKSPACE_VALUE" "$XCODE_PROJECT_VALUE" "$XCODE_SCHEME_VALUE" "$XCODE_DEVICE_NAME_VALUE" "$XCODE_DEVICE_ID_VALUE" "$XCODE_PREFER_MODEL_VALUE" 'connected-only'; then
      export XCODE_DEVICE_ID="$SELECTED_DEVICE_IDENTIFIER"
      export XCODE_DEVICE_NAME=""
      export XCODE_PREFER_MODEL=""
      export XCODE_FALLBACK_DEVICE_NAME="$SELECTED_DEVICE_NAME"
      export XCODE_FALLBACK_DEVICE_ID="$SELECTED_DEVICE_IDENTIFIER"
      export XCODE_FALLBACK_DEVICE_STATE="$SELECTED_DEVICE_STATE"
      export XCODE_FALLBACK_DEVICE_MODEL="$SELECTED_DEVICE_MODEL"
      export XCODE_FALLBACK_DEVICE_REASON="$SELECTED_DEVICE_REASON"
    else
      export XCODE_FALLBACK_DEVICE_ERROR="$SELECT_DEVICE_ERROR"
    fi
  fi
fi

exec python3 "$SCRIPT_DIR/build_check.py" "$@"
