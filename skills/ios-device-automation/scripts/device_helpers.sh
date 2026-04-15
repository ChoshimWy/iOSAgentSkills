#!/usr/bin/env bash

SELECTED_DEVICE_NAME=""
SELECTED_DEVICE_IDENTIFIER=""
SELECTED_DEVICE_STATE=""
SELECTED_DEVICE_MODEL=""
SELECTED_DEVICE_REASON=""
SELECT_DEVICE_ERROR=""

trim_device_value() {
  local value="$*"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

read_xcode_env_value() {
  local root="$1"
  local key="$2"
  local env_file="$root/.codex/xcodebuild.env"
  [[ -f "$env_file" ]] || return 1

  awk -F= -v target="$key" '
    /^[[:space:]]*#/ || !/=/{next}
    {
      key=$1
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", key)
      if (key != target) {
        next
      }
      value=substr($0, index($0, "=") + 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      if ((value ~ /^".*"$/) || (value ~ /^\047.*\047$/)) {
        value=substr(value, 2, length(value) - 2)
      }
      print value
      exit
    }
  ' "$env_file"
}

path_depth_le() {
  local rel="$1"
  local max_depth="$2"
  local path_parts=()
  IFS='/' read -r -a path_parts <<< "$rel"
  [[ ${#path_parts[@]} -le $max_depth ]]
}

pick_workspace() {
  local root="$1"
  local explicit_workspace
  explicit_workspace="$(read_xcode_env_value "$root" XCODE_WORKSPACE || true)"
  if [[ -n "$explicit_workspace" ]]; then
    printf '%s\n' "$explicit_workspace"
    return 0
  fi

  while IFS= read -r path; do
    local rel="${path#"$root"/}"
    path_depth_le "$rel" 3 || continue
    printf '%s\n' "$rel"
    return 0
  done < <(find "$root" -name '*.xcworkspace' ! -path '*/Pods/*' ! -path '*/project.xcworkspace' ! -path '*/project.xcworkspace/*' | sort)

  return 1
}

pick_project() {
  local root="$1"
  local explicit_project
  explicit_project="$(read_xcode_env_value "$root" XCODE_PROJECT || true)"
  if [[ -n "$explicit_project" ]]; then
    printf '%s\n' "$explicit_project"
    return 0
  fi

  while IFS= read -r path; do
    local rel="${path#"$root"/}"
    path_depth_le "$rel" 3 || continue
    printf '%s\n' "$rel"
    return 0
  done < <(find "$root" -name '*.xcodeproj' ! -path '*/Pods/*' | sort)

  return 1
}

pick_scheme() {
  local root="$1"
  local explicit_scheme
  explicit_scheme="$(read_xcode_env_value "$root" XCODE_SCHEME || true)"
  if [[ -n "$explicit_scheme" ]]; then
    printf '%s\n' "$explicit_scheme"
    return 0
  fi

  local schemes=()
  while IFS= read -r path; do
    schemes+=("$(basename "$path" .xcscheme)")
  done < <(find "$root" -name '*.xcscheme' ! -path '*/Pods/*' | sort)

  if [[ ${#schemes[@]} -eq 0 ]]; then
    return 1
  fi

  local scheme
  for scheme in "${schemes[@]}"; do
    if [[ ! "$scheme" =~ (Tests|UITests)$ ]] && [[ ! "$scheme" =~ (^|[_-])(DEV|TEST|UAT|STAGING)$ ]]; then
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

destination_to_device_id() {
  local destination="$1"
  [[ "$destination" == id=* ]] || return 1
  printf '%s\n' "${destination#id=}"
}

is_simulator_destination_text() {
  printf '%s' "$1" | grep -qi 'simulator'
}

list_xcode_physical_destinations_tsv() {
  local root="$1"
  local workspace="$2"
  local project="$3"
  local scheme="$4"
  local command=(xcodebuild)

  if [[ -n "$workspace" ]]; then
    command+=( -workspace "$workspace" )
  else
    command+=( -project "$project" )
  fi
  command+=( -scheme "$scheme" -showdestinations )

  "${command[@]}" | sed -nE 's/.*\{ platform:iOS,([^}]*) id:([^,]+), name:([^}]+) \}.*/\3\t\2/p' | while IFS=$'\t' read -r name identifier; do
    name="$(trim_device_value "$name")"
    identifier="$(trim_device_value "$identifier")"
    [[ -n "$name" && -n "$identifier" ]] || continue
    [[ "$identifier" == dvtdevice-* || "$identifier" == *placeholder* ]] && continue
    printf '%s\t%s\n' "$name" "$identifier"
  done
}

list_devicectl_devices_tsv() {
  xcrun devicectl list devices | awk -F '  +' '
    BEGIN { started = 0 }
    /^-+[[:space:]]+-+/ { started = 1; next }
    started && NF >= 5 {
      printf "%s\t%s\t%s\t%s\t%s\n", $1, $2, $3, $4, $5
    }
  '
}

clear_selected_device() {
  SELECTED_DEVICE_NAME=""
  SELECTED_DEVICE_IDENTIFIER=""
  SELECTED_DEVICE_STATE=""
  SELECTED_DEVICE_MODEL=""
  SELECTED_DEVICE_REASON=""
  SELECT_DEVICE_ERROR=""
}

set_selected_device() {
  SELECTED_DEVICE_NAME="$1"
  SELECTED_DEVICE_IDENTIFIER="$2"
  SELECTED_DEVICE_STATE="$3"
  SELECTED_DEVICE_MODEL="$4"
  SELECTED_DEVICE_REASON="$5"
  SELECT_DEVICE_ERROR=""
}

rank_device_state() {
  case "$1" in
    connected)
      printf '0\n'
      ;;
    'available (paired)')
      printf '1\n'
      ;;
    available*)
      printf '2\n'
      ;;
    *)
      printf '3\n'
      ;;
  esac
}

select_xcode_destination() {
  local root="$1"
  local workspace="$2"
  local project="$3"
  local scheme="$4"
  local explicit_name="$5"
  local explicit_id="$6"
  local prefer_model="$7"
  clear_selected_device

  if [[ -n "$explicit_id" && -z "$explicit_name" && -z "$prefer_model" ]]; then
    set_selected_device "$explicit_id" "$explicit_id" 'explicit' '' 'using explicit device identifier'
    return 0
  fi

  if [[ -z "$workspace" ]]; then
    workspace="$(pick_workspace "$root" || true)"
  fi
  if [[ -z "$project" ]]; then
    project="$(pick_project "$root" || true)"
  fi
  if [[ -z "$workspace" && -z "$project" ]]; then
    SELECT_DEVICE_ERROR="No .xcworkspace or .xcodeproj found in $root"
    return 1
  fi
  if [[ -z "$scheme" ]]; then
    scheme="$(pick_scheme "$root" || true)"
  fi
  if [[ -z "$scheme" ]]; then
    SELECT_DEVICE_ERROR='No shared scheme found'
    return 1
  fi

  local temp_file
  temp_file="$(mktemp)"
  if ! list_xcode_physical_destinations_tsv "$root" "$workspace" "$project" "$scheme" > "$temp_file"; then
    rm -f "$temp_file"
    SELECT_DEVICE_ERROR="xcodebuild -showdestinations failed for scheme '$scheme'"
    return 1
  fi

  if [[ ! -s "$temp_file" ]]; then
    rm -f "$temp_file"
    SELECT_DEVICE_ERROR="no physical iOS destinations available for scheme '$scheme'"
    return 1
  fi

  if [[ -n "$explicit_name" ]]; then
    local current_name current_id
    while IFS=$'\t' read -r current_name current_id; do
      current_name="$(trim_device_value "$current_name")"
      current_id="$(trim_device_value "$current_id")"
      if [[ "$current_name" == "$explicit_name" ]]; then
        rm -f "$temp_file"
        set_selected_device "$current_name" "$current_id" 'destination' '' 'matched explicit name'
        return 0
      fi
    done < "$temp_file"

    rm -f "$temp_file"
    SELECT_DEVICE_ERROR="name not found: $explicit_name"
    return 1
  fi

  local first_name=""
  local first_id=""
  local preferred_name=""
  local preferred_id=""
  local prefer_lower="$(to_lower "$prefer_model")"
  local current_name current_id current_haystack
  while IFS=$'\t' read -r current_name current_id; do
    current_name="$(trim_device_value "$current_name")"
    current_id="$(trim_device_value "$current_id")"
    [[ -n "$first_id" ]] || {
      first_name="$current_name"
      first_id="$current_id"
    }
    if [[ -n "$prefer_lower" ]]; then
      current_haystack="$(to_lower "$current_name")"
      if [[ "$current_haystack" == *"$prefer_lower"* ]]; then
        preferred_name="$current_name"
        preferred_id="$current_id"
        break
      fi
    fi
  done < "$temp_file"
  rm -f "$temp_file"

  if [[ -n "$preferred_id" ]]; then
    set_selected_device "$preferred_name" "$preferred_id" 'destination' '' 'selected first matching xcodebuild destination'
    return 0
  fi

  if [[ -n "$first_id" ]]; then
    set_selected_device "$first_name" "$first_id" 'destination' '' 'selected first physical xcodebuild destination'
    return 0
  fi

  SELECT_DEVICE_ERROR="no physical iOS destinations available for scheme '$scheme'"
  return 1
}

select_devicectl_device() {
  local explicit_name="$1"
  local explicit_id="$2"
  local prefer_model="$3"
  clear_selected_device

  if [[ -n "$explicit_id" && -z "$explicit_name" && -z "$prefer_model" ]]; then
    set_selected_device "$explicit_id" "$explicit_id" 'explicit' '' 'using explicit device identifier'
    return 0
  fi

  local temp_file
  temp_file="$(mktemp)"
  if ! list_devicectl_devices_tsv > "$temp_file"; then
    rm -f "$temp_file"
    SELECT_DEVICE_ERROR='xcrun devicectl list devices failed'
    return 1
  fi

  local explicit_best_name=""
  local explicit_best_host=""
  local explicit_best_id=""
  local explicit_best_state=""
  local explicit_best_model=""
  local explicit_best_rank=99

  local preferred_name=""
  local preferred_host=""
  local preferred_id=""
  local preferred_state=""
  local preferred_model_value=""
  local preferred_rank=99

  local best_name=""
  local best_host=""
  local best_id=""
  local best_state=""
  local best_model_value=""
  local best_rank=99

  local prefer_lower="$(to_lower "$prefer_model")"
  local current_name current_host current_id current_state current_model current_rank current_haystack
  while IFS=$'\t' read -r current_name current_host current_id current_state current_model; do
    current_name="$(trim_device_value "$current_name")"
    current_host="$(trim_device_value "$current_host")"
    current_id="$(trim_device_value "$current_id")"
    current_state="$(trim_device_value "$current_state")"
    current_model="$(trim_device_value "$current_model")"
    [[ -n "$current_id" ]] || continue

    current_rank="$(rank_device_state "$current_state")"

    if [[ -n "$explicit_name" && "$current_name" == "$explicit_name" ]]; then
      if (( current_rank < explicit_best_rank )) || { (( current_rank == explicit_best_rank )) && [[ -z "$explicit_best_name" || "$current_name" < "$explicit_best_name" ]]; }; then
        explicit_best_name="$current_name"
        explicit_best_host="$current_host"
        explicit_best_id="$current_id"
        explicit_best_state="$current_state"
        explicit_best_model="$current_model"
        explicit_best_rank="$current_rank"
      fi
    fi

    if [[ -n "$prefer_lower" ]]; then
      current_haystack="$(to_lower "$current_name $current_model")"
      if [[ "$current_haystack" == *"$prefer_lower"* ]]; then
        if (( current_rank < preferred_rank )) || { (( current_rank == preferred_rank )) && [[ -z "$preferred_name" || "$current_name" < "$preferred_name" ]]; }; then
          preferred_name="$current_name"
          preferred_host="$current_host"
          preferred_id="$current_id"
          preferred_state="$current_state"
          preferred_model_value="$current_model"
          preferred_rank="$current_rank"
        fi
      fi
    fi

    if (( current_rank < best_rank )) || { (( current_rank == best_rank )) && [[ -z "$best_name" || "$current_name" < "$best_name" ]]; }; then
      best_name="$current_name"
      best_host="$current_host"
      best_id="$current_id"
      best_state="$current_state"
      best_model_value="$current_model"
      best_rank="$current_rank"
    fi
  done < "$temp_file"
  rm -f "$temp_file"

  if [[ -n "$explicit_name" ]]; then
    if [[ -n "$explicit_best_id" ]]; then
      set_selected_device "$explicit_best_name" "$explicit_best_id" "$explicit_best_state" "$explicit_best_model" 'matched explicit name'
      return 0
    fi
    SELECT_DEVICE_ERROR="name not found: $explicit_name"
    return 1
  fi

  if [[ -n "$preferred_id" ]]; then
    set_selected_device "$preferred_name" "$preferred_id" "$preferred_state" "$preferred_model_value" 'selected best preferred device'
    return 0
  fi

  if [[ -n "$best_id" ]]; then
    local best_reason='selected fallback device'
    case "$best_state" in
      connected)
        best_reason='selected best connected device'
        ;;
      'available (paired)')
        best_reason='selected best available (paired) device'
        ;;
    esac
    set_selected_device "$best_name" "$best_id" "$best_state" "$best_model_value" "$best_reason"
    return 0
  fi

  SELECT_DEVICE_ERROR='no devices available'
  return 1
}
