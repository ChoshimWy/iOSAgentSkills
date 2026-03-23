#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$PWD}"
cd "$ROOT"

if [[ -f ".codex/xcodebuild.env" ]]; then
  # shellcheck disable=SC1091
  source ".codex/xcodebuild.env"
fi

pick_workspace() {
  if [[ -n "${XCODE_WORKSPACE:-}" ]]; then
    printf '%s\n' "$XCODE_WORKSPACE"
    return 0
  fi

  find . -maxdepth 3 -name '*.xcworkspace' \
    -not -path '*/Pods/*' \
    -not -path '*/project.xcworkspace' \
    | sort | head -n 1
}

pick_project() {
  if [[ -n "${XCODE_PROJECT:-}" ]]; then
    printf '%s\n' "$XCODE_PROJECT"
    return 0
  fi

  find . -maxdepth 3 -name '*.xcodeproj' \
    -not -path '*/Pods/*' \
    | sort | head -n 1
}

pick_scheme() {
  if [[ -n "${XCODE_SCHEME:-}" ]]; then
    printf '%s\n' "$XCODE_SCHEME"
    return 0
  fi

  schemes=()
  while IFS= read -r path; do
    schemes+=("$(basename "$path" .xcscheme)")
  done < <(
    find . -path '*/xcshareddata/xcschemes/*.xcscheme' \
      -not -path '*/Pods/*' \
      | sort
  )

  if [[ "${#schemes[@]}" -eq 0 ]]; then
    echo "No shared scheme found" >&2
    exit 1
  fi

  for scheme in "${schemes[@]}"; do
    if [[ ! "$scheme" =~ (Tests|UITests)$ ]] &&
       [[ ! "$scheme" =~ (^|[_-])(DEV|TEST|UAT|STAGING)$ ]]; then
      printf '%s\n' "$scheme"
      return 0
    fi
  done

  for scheme in "${schemes[@]}"; do
    if [[ ! "$scheme" =~ (Tests|UITests)$ ]]; then
      printf '%s\n' "$scheme"
      return 0
    fi
  done

  printf '%s\n' "${schemes[0]}"
}

WORKSPACE="$(pick_workspace || true)"
PROJECT="$(pick_project || true)"

if [[ -z "$WORKSPACE" && -z "$PROJECT" ]]; then
  echo "No .xcworkspace or .xcodeproj found in $ROOT" >&2
  exit 1
fi

SCHEME="$(pick_scheme)"
CONFIGURATION="${XCODE_CONFIGURATION:-Debug}"
DESTINATION="${XCODE_DESTINATION:-generic/platform=iOS Simulator}"
ACTION="${XCODE_ACTION:-build}"
DERIVED_DATA="${XCODE_DERIVED_DATA:-$ROOT/.codex-derived-data}"

build_cmd=(xcodebuild)

if [[ -n "$WORKSPACE" ]]; then
  build_cmd+=(-workspace "$WORKSPACE")
else
  build_cmd+=(-project "$PROJECT")
fi

build_cmd+=(
  -scheme "$SCHEME"
  -configuration "$CONFIGURATION"
  -destination "$DESTINATION"
  -derivedDataPath "$DERIVED_DATA"
  CODE_SIGNING_ALLOWED=NO
  CODE_SIGNING_REQUIRED=NO
  "$ACTION"
)

echo "Root: $ROOT"
if [[ -n "$WORKSPACE" ]]; then
  echo "Workspace: $WORKSPACE"
else
  echo "Project: $PROJECT"
fi
echo "Scheme: $SCHEME"
echo "Configuration: $CONFIGURATION"
echo "Destination: $DESTINATION"
printf 'Command:'
printf ' %q' "${build_cmd[@]}"
printf '\n'

if [[ "${XCODEBUILD_DRY_RUN:-0}" == "1" ]]; then
  exit 0
fi

"${build_cmd[@]}"
