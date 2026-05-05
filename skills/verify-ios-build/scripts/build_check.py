#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VERIFY_SKILL_DIR = SCRIPT_DIR.parent

THIRD_PARTY_MARKERS = ("Pods", "Carthage", "SourcePackages")
SIMULATOR_DESTINATION_PATTERN = re.compile(r"simulator", re.IGNORECASE)
COMPILATION_ERROR_PATTERN = re.compile(
    r"^(?P<file>[^:\n]+):(?P<line>\d+):(?P<column>\d+):\s*error:\s*(?P<message>.+?)$"
)
FRAMEWORK_NOT_FOUND_PATTERN = re.compile(r"ld:\s+framework\s+'(?P<name>[^']+)'\s+not found")
LIBRARY_NOT_FOUND_PATTERN = re.compile(r"ld:\s+library\s+'(?P<name>[^']+)'\s+not found")
QUOTED_PATH_PATTERN = re.compile(r"""['"](?P<path>[^'"]+)['"]""")
UI_TEST_SCHEME_NAME_PATTERN = re.compile(r"(?:^|[_-])UITESTS?$", re.IGNORECASE)
UNIT_TEST_SCHEME_TOKEN_PATTERN = re.compile(r"(?:^|[_-])TESTS$", re.IGNORECASE)
GENERIC_TEST_SCHEME_NAME_PATTERN = re.compile(r"(?:^|[_-])TEST$", re.IGNORECASE)
NON_PRODUCTION_SCHEME_PATTERN = re.compile(r"(^|[_-])(DEV|TEST|UAT|STAGING)$", re.IGNORECASE)


@dataclass
class BuildIssue:
    order: int
    kind: str
    message: str
    file: str | None = None
    related_paths: list[str] = field(default_factory=list)
    third_party_evidence: bool = False

    @property
    def touches_file(self) -> bool:
        return bool(self.file or self.related_paths)


@dataclass
class BuildAttempt:
    label: str
    destination: str | None
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    issues: list[BuildIssue] = field(default_factory=list)

    @property
    def combined_output(self) -> str:
        parts = []
        if self.stdout:
            parts.append(self.stdout)
        if self.stderr:
            parts.append(self.stderr)
        return "\n".join(parts)

    @property
    def command_string(self) -> str:
        return " ".join(shlex.quote(part) for part in self.command)


@dataclass
class BuildConfig:
    root: Path
    workspace: str | None
    project: str | None
    scheme: str
    configuration: str
    action: str
    destination: str | None
    derived_data: str
    device_fallback_enabled: bool
    explicit_device_id: str | None
    explicit_device_name: str | None
    preferred_model: str | None
    validation_platform: str | None
    show_output: bool

    def command_for_destination(self, destination: str | None) -> list[str]:
        command = ["xcodebuild"]
        if self.workspace:
            command += ["-workspace", self.workspace]
        else:
            command += ["-project", self.project or ""]

        command += [
            "-scheme",
            self.scheme,
            "-configuration",
            self.configuration,
        ]

        if destination:
            command += ["-destination", destination]

        command += [
            "-derivedDataPath",
            self.derived_data,
        ]

        if is_simulator_destination(destination):
            command += ["CODE_SIGNING_ALLOWED=NO", "CODE_SIGNING_REQUIRED=NO"]

        command.append(self.action)
        return command


OVERRIDABLE_ENV_KEYS = (
    "XCODE_WORKSPACE",
    "XCODE_PROJECT",
    "XCODE_SCHEME",
    "XCODE_CONFIGURATION",
    "XCODE_ACTION",
    "XCODE_DESTINATION",
    "XCODE_DERIVED_DATA",
    "XCODE_DEVICE_FALLBACK",
    "XCODE_DEVICE_ID",
    "XCODE_DEVICE_NAME",
    "XCODE_PREFER_MODEL",
    "XCODEBUILD_SHOW_OUTPUT",
)


def load_env(root: Path) -> dict[str, str]:
    env_file = root / ".codex" / "xcodebuild.env"
    values: dict[str, str] = {}
    if env_file.exists():
        for raw in env_file.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")

    for key in OVERRIDABLE_ENV_KEYS:
        if key in os.environ:
            values[key] = os.environ[key]
    return values


def truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def pick_workspace(root: Path, env: dict[str, str]) -> str | None:
    if env.get("XCODE_WORKSPACE"):
        return env["XCODE_WORKSPACE"]

    candidates = [
        path
        for path in root.rglob("*.xcworkspace")
        if "Pods" not in path.parts and "project.xcworkspace" not in str(path)
    ]
    candidates = [path for path in candidates if len(path.relative_to(root).parts) <= 3]
    return str(sorted(candidates)[0].relative_to(root)) if candidates else None


def pick_project(root: Path, env: dict[str, str]) -> str | None:
    if env.get("XCODE_PROJECT"):
        return env["XCODE_PROJECT"]

    candidates = [path for path in root.rglob("*.xcodeproj") if "Pods" not in path.parts]
    candidates = [path for path in candidates if len(path.relative_to(root).parts) <= 3]
    return str(sorted(candidates)[0].relative_to(root)) if candidates else None


def is_ui_test_preferred_scheme(name: str) -> bool:
    return bool(
        UI_TEST_SCHEME_NAME_PATTERN.search(name)
        or re.search(r"UITests?$", name, re.IGNORECASE)
    )


def is_unit_test_preferred_scheme(name: str) -> bool:
    return bool(
        (
            UNIT_TEST_SCHEME_TOKEN_PATTERN.search(name)
            or re.search(r"(?<!UI)Tests$", name, re.IGNORECASE)
        )
        and not is_ui_test_preferred_scheme(name)
    )


def is_generic_test_scheme(name: str) -> bool:
    return bool(
        GENERIC_TEST_SCHEME_NAME_PATTERN.search(name)
        and not is_ui_test_preferred_scheme(name)
    )


def iter_scheme_testable_names(path: Path | None) -> list[str]:
    if path is None:
        return []

    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []

    names: list[str] = []
    for reference in root.findall(".//TestAction//TestableReference//BuildableReference"):
        for key in ("BuildableName", "BlueprintName"):
            value = reference.get(key)
            if value:
                names.append(Path(value).stem)
    return names


def scheme_has_unit_test_binding(path: Path | None) -> bool:
    return any(is_unit_test_preferred_scheme(name) for name in iter_scheme_testable_names(path))


def scheme_has_ui_test_binding(path: Path | None) -> bool:
    return any(is_ui_test_preferred_scheme(name) for name in iter_scheme_testable_names(path))


def scheme_sort_key(name: str, path: Path | None) -> tuple[int, str]:
    if scheme_has_unit_test_binding(path):
        return (0, name.lower())
    if is_unit_test_preferred_scheme(name):
        return (1, name.lower())
    if is_generic_test_scheme(name):
        return (2, name.lower())
    if scheme_has_ui_test_binding(path):
        return (3, name.lower())
    if is_ui_test_preferred_scheme(name):
        return (4, name.lower())
    if not NON_PRODUCTION_SCHEME_PATTERN.search(name):
        return (5, name.lower())
    if not is_ui_test_preferred_scheme(name):
        return (6, name.lower())
    return (7, name.lower())


def pick_scheme(root: Path, env: dict[str, str]) -> str:
    if env.get("XCODE_SCHEME"):
        return env["XCODE_SCHEME"]

    scheme_paths: dict[str, Path] = {}
    for path in sorted(root.rglob("*.xcscheme")):
        if "Pods" in path.parts:
            continue
        scheme_paths.setdefault(path.stem, path)

    schemes = list(scheme_paths.keys())
    if not schemes:
        raise RuntimeError("No shared scheme found")

    return sorted(schemes, key=lambda name: scheme_sort_key(name, scheme_paths.get(name)))[0]


def resolve_build_config(root: Path) -> BuildConfig:
    env = load_env(root)
    workspace = pick_workspace(root, env)
    project = pick_project(root, env)

    if not workspace and not project:
        raise RuntimeError(f"No .xcworkspace or .xcodeproj found in {root}")

    return BuildConfig(
        root=root,
        workspace=workspace,
        project=project,
        scheme=pick_scheme(root, env),
        configuration=env.get("XCODE_CONFIGURATION", "Debug"),
        action=env.get("XCODE_ACTION", "build"),
        destination=env.get("XCODE_DESTINATION"),
        derived_data=env.get("XCODE_DERIVED_DATA", str(root / ".codex-derived-data")),
        device_fallback_enabled=truthy(env.get("XCODE_DEVICE_FALLBACK"), default=True),
        explicit_device_id=env.get("XCODE_DEVICE_ID"),
        explicit_device_name=env.get("XCODE_DEVICE_NAME"),
        preferred_model=env.get("XCODE_PREFER_MODEL"),
        validation_platform=os.environ.get("XCODE_VALIDATION_PLATFORM"),
        show_output=truthy(env.get("XCODEBUILD_SHOW_OUTPUT"), default=False),
    )


def is_simulator_destination(destination: str | None) -> bool:
    return bool(destination and SIMULATOR_DESTINATION_PATTERN.search(destination))


def load_selected_device_from_env(prefix: str) -> tuple[dict[str, str] | None, str | None]:
    identifier = os.environ.get(f"{prefix}ID")
    name = os.environ.get(f"{prefix}NAME") or identifier
    reason = os.environ.get(f"{prefix}REASON")
    state = os.environ.get(f"{prefix}STATE", "selected")
    model = os.environ.get(f"{prefix}MODEL", "")
    if not any((identifier, name, reason)):
        return None, None

    return (
        {
            "name": name or "selected-device",
            "identifier": identifier or "",
            "state": state,
            "model": model,
            "hostname": "",
        },
        reason or "selected by shell wrapper",
    )


def explicit_selected_device(config: BuildConfig) -> tuple[dict[str, str] | None, str | None]:
    if config.explicit_device_id and not config.explicit_device_name and not config.preferred_model:
        return (
            {
                "name": config.explicit_device_id,
                "identifier": config.explicit_device_id,
                "state": "explicit",
                "model": "unknown",
                "hostname": "",
            },
            "using explicit device identifier",
        )
    return None, None


def run_git_lines(root: Path, args: list[str]) -> list[str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def collect_changed_files(root: Path) -> set[str]:
    changed: set[str] = set()
    commands = [
        ["diff", "--name-only", "--cached"],
        ["diff", "--name-only"],
        ["ls-files", "--others", "--exclude-standard"],
    ]
    for command in commands:
        changed.update(run_git_lines(root, command))
    return changed


def normalize_path(path: str, root: Path) -> Path:
    stripped = path.strip().strip('"').strip("'")
    if stripped.startswith("file://"):
        stripped = stripped.removeprefix("file://")

    candidate = Path(stripped)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def relative_to_root(path: str, root: Path) -> str | None:
    try:
        return normalize_path(path, root).relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    except OSError:
        return None


def path_has_third_party_marker(path: str) -> bool:
    text = path.replace("\\", "/")
    return any(f"/{marker}/" in text or text.startswith(f"{marker}/") for marker in THIRD_PARTY_MARKERS)


def text_has_third_party_marker(text: str) -> bool:
    normalized = text.replace("\\", "/")
    return any(f"/{marker}/" in normalized or f"{marker}/" in normalized for marker in THIRD_PARTY_MARKERS)


def extract_related_paths(text: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    for match in QUOTED_PATH_PATTERN.finditer(text):
        candidate = match.group("path")
        if path_has_third_party_marker(candidate) and candidate not in seen:
            paths.append(candidate)
            seen.add(candidate)

    if not paths:
        for token in re.split(r"\s+", text):
            if path_has_third_party_marker(token):
                cleaned = token.strip(",.()[]")
                if cleaned and cleaned not in seen:
                    paths.append(cleaned)
                    seen.add(cleaned)

    return paths


def third_party_name_exists(root: Path, name: str) -> bool:
    needle = name.lower()
    for marker in THIRD_PARTY_MARKERS:
        base = root / marker
        if not base.exists():
            continue
        for current_root, dirs, files in os.walk(base):
            if needle in Path(current_root).name.lower():
                return True
            for item in dirs:
                if needle in item.lower():
                    return True
            for item in files:
                if needle in item.lower():
                    return True
    return False


def collect_window(lines: list[str], index: int, radius: int = 4) -> str:
    start = max(index - radius, 0)
    end = min(index + radius + 1, len(lines))
    return "\n".join(lines[start:end])


def parse_build_issues(output: str, root: Path) -> list[BuildIssue]:
    issues: list[BuildIssue] = []
    lines = output.splitlines()

    for index, raw_line in enumerate(lines):
        line = raw_line.rstrip()
        if not line:
            continue

        if match := COMPILATION_ERROR_PATTERN.match(line):
            file_path = match.group("file")
            issues.append(
                BuildIssue(
                    order=index,
                    kind="compilation_error",
                    message=match.group("message").strip(),
                    file=file_path,
                    related_paths=[file_path],
                    third_party_evidence=path_has_third_party_marker(file_path),
                )
            )
            continue

        window = collect_window(lines, index)
        related_paths = extract_related_paths(window)
        third_party_evidence = bool(related_paths) or text_has_third_party_marker(window)

        if (
            line.startswith("ld:")
            and "building for iOS Simulator" in line
            and "built for iOS" in line
            and "linking in" in line
        ):
            issues.append(
                BuildIssue(
                    order=index,
                    kind="simulator_linker_incompatible",
                    message=line.strip(),
                    related_paths=related_paths,
                    third_party_evidence=third_party_evidence,
                )
            )
            continue

        if framework_match := FRAMEWORK_NOT_FOUND_PATTERN.search(line):
            framework_name = framework_match.group("name")
            issues.append(
                BuildIssue(
                    order=index,
                    kind="framework_not_found",
                    message=line.strip(),
                    related_paths=related_paths,
                    third_party_evidence=third_party_evidence
                    or third_party_name_exists(root, framework_name),
                )
            )
            continue

        if library_match := LIBRARY_NOT_FOUND_PATTERN.search(line):
            library_name = library_match.group("name")
            issues.append(
                BuildIssue(
                    order=index,
                    kind="library_not_found",
                    message=line.strip(),
                    related_paths=related_paths,
                    third_party_evidence=third_party_evidence
                    or third_party_name_exists(root, library_name),
                )
            )
            continue

        if line.startswith("Undefined symbols for architecture"):
            issues.append(
                BuildIssue(
                    order=index,
                    kind="undefined_symbols",
                    message=line.strip(),
                    related_paths=related_paths,
                    third_party_evidence=third_party_evidence,
                )
            )
            continue

        if line.startswith("ld: symbol(s) not found for architecture"):
            issues.append(
                BuildIssue(
                    order=index,
                    kind="linker_symbols_not_found",
                    message=line.strip(),
                    related_paths=related_paths,
                    third_party_evidence=third_party_evidence,
                )
            )
            continue

        if line.startswith("xcodebuild: error:"):
            issues.append(
                BuildIssue(
                    order=index,
                    kind="xcodebuild_error",
                    message=line.strip(),
                    related_paths=related_paths,
                    third_party_evidence=third_party_evidence,
                )
            )

    return issues


def select_primary_issue(issues: list[BuildIssue]) -> BuildIssue | None:
    return issues[0] if issues else None


def issue_touches_changed_files(issue: BuildIssue, changed_files: set[str], root: Path) -> bool:
    if not changed_files:
        return False

    candidates = []
    if issue.file:
        candidates.append(issue.file)
    candidates.extend(issue.related_paths)

    for candidate in candidates:
        relative = relative_to_root(candidate, root)
        if relative and relative in changed_files:
            return True
    return False


def issue_matches_device_fallback_whitelist(issue: BuildIssue) -> bool:
    if issue.kind == "simulator_linker_incompatible":
        return issue.third_party_evidence

    if issue.kind in {
        "framework_not_found",
        "library_not_found",
        "undefined_symbols",
        "linker_symbols_not_found",
    }:
        return issue.third_party_evidence

    return False


def run_build(command: list[str], cwd: Path, label: str, destination: str) -> BuildAttempt:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    return BuildAttempt(
        label=label,
        destination=destination,
        command=command,
        exit_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr="",
    )


def maybe_print_output(attempt: BuildAttempt, show_output: bool) -> None:
    if not show_output and attempt.exit_code == 0:
        return

    if attempt.stdout.strip():
        print(f"--- {attempt.label} stdout ---")
        print(attempt.stdout.rstrip())
    if attempt.stderr.strip():
        print(f"--- {attempt.label} stderr ---")
        print(attempt.stderr.rstrip())


def print_attempt_header(
    config: BuildConfig,
    label: str,
    destination: str | None,
    command: list[str],
) -> None:
    print(f"=== {label} ===")
    print(f"Root: {config.root}")
    if config.workspace:
        print(f"Workspace: {config.workspace}")
    else:
        print(f"Project: {config.project}")
    print(f"Scheme: {config.scheme}")
    print(f"Configuration: {config.configuration}")
    print(f"Action: {config.action}")
    print(f"Destination: {destination or 'default host build (no explicit destination)'}")
    print(f"Command: {' '.join(shlex.quote(part) for part in command)}")


def describe_issue(issue: BuildIssue | None, config: BuildConfig, changed_files: set[str]) -> None:
    if not issue:
        print("Primary failure: unable to classify the first real error")
        return

    print(f"Primary failure kind: {issue.kind}")
    print(f"Primary failure message: {issue.message}")
    if issue.file:
        print(f"Primary failure file: {issue.file}")
    elif issue.related_paths:
        print(f"Primary failure evidence: {issue.related_paths[0]}")
    print(
        "Primary failure hits changed files: "
        + ("yes" if issue_touches_changed_files(issue, changed_files, config.root) else "no")
    )
    print(
        "Primary failure matches device fallback whitelist: "
        + ("yes" if issue_matches_device_fallback_whitelist(issue) else "no")
    )


def resolve_initial_destination(config: BuildConfig) -> tuple[str | None, dict[str, str] | None, str | None]:
    if config.destination:
        selected_device, selection_reason = load_selected_device_from_env("XCODE_SELECTED_DEVICE_")
        return config.destination, selected_device, selection_reason

    if config.validation_platform == "macos":
        selected_device, selection_reason = load_selected_device_from_env("XCODE_SELECTED_DEVICE_")
        return None, selected_device, selection_reason

    selected_device, selection_reason = explicit_selected_device(config)
    if selected_device:
        shell_selected_device, shell_selection_reason = load_selected_device_from_env("XCODE_SELECTED_DEVICE_")
        return (
            f"id={selected_device['identifier']}",
            shell_selected_device or selected_device,
            shell_selection_reason or selection_reason,
        )

    raise RuntimeError(
        "no physical device destination resolved; run via build-check.sh or set XCODE_DESTINATION / XCODE_DEVICE_ID"
    )


def should_attempt_device_fallback(
    config: BuildConfig,
    simulator_attempt: BuildAttempt,
    changed_files: set[str],
) -> tuple[bool, str, BuildIssue | None]:
    if config.action != "build":
        return False, f"device fallback is disabled for action '{config.action}'", None

    if not is_simulator_destination(config.destination):
        return False, "initial destination is not an iOS Simulator target", None

    if not config.device_fallback_enabled:
        return False, "XCODE_DEVICE_FALLBACK=0", None

    issue = select_primary_issue(simulator_attempt.issues)
    if not issue:
        return False, "unable to classify the first real simulator failure", None

    if issue_touches_changed_files(issue, changed_files, config.root):
        return False, "the first real simulator failure is inside changed files", issue

    if not issue_matches_device_fallback_whitelist(issue):
        return False, "the first real simulator failure is not in the device-fallback whitelist", issue

    return True, "third-party simulator-only linker failure", issue


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run physical-device-first xcodebuild verification with optional simulator override"
    )
    parser.add_argument("root", nargs="?", default=".", help="Target repo root")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved commands without invoking xcodebuild",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    dry_run = args.dry_run or truthy(os.environ.get("XCODEBUILD_DRY_RUN"), default=False)

    try:
        config = resolve_build_config(root)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        initial_destination, initial_device, initial_device_reason = resolve_initial_destination(config)
    except Exception as exc:
        print(f"Initial physical-device validation blocked: {exc}", file=sys.stderr)
        return 1

    changed_files = collect_changed_files(root)
    initial_label = "Physical device build validation"
    if config.validation_platform == "macos":
        initial_label = "macOS host build validation"
    elif is_simulator_destination(initial_destination):
        initial_label = "Simulator build validation"
    initial_command = config.command_for_destination(initial_destination)
    print_attempt_header(config, initial_label, initial_destination, initial_command)
    if initial_device:
        print(
            "Selected device: "
            f"{initial_device['name']} [{initial_device['identifier']}] ({initial_device['state']})"
        )
        print(f"Selection reason: {initial_device_reason}")
    if changed_files:
        print(f"Changed files detected: {len(changed_files)}")
    else:
        print("Changed files detected: 0")

    if dry_run:
        print("Dry run: xcodebuild was not executed")
        if is_simulator_destination(initial_destination):
            print(
                "Device fallback enabled: "
                + ("yes" if config.device_fallback_enabled else "no")
            )
        return 0

    initial_attempt = run_build(
        initial_command,
        cwd=root,
        label=initial_label,
        destination=initial_destination,
    )
    initial_attempt.issues = parse_build_issues(initial_attempt.combined_output, root)

    print(f"Result: {'SUCCESS' if initial_attempt.exit_code == 0 else 'FAILED'}")
    maybe_print_output(initial_attempt, config.show_output)

    if initial_attempt.exit_code == 0:
        return 0

    primary_issue = select_primary_issue(initial_attempt.issues)

    if config.validation_platform == "macos":
        describe_issue(primary_issue, config, changed_files)
        return initial_attempt.exit_code

    if not is_simulator_destination(initial_destination):
        describe_issue(primary_issue, config, changed_files)
        return initial_attempt.exit_code

    should_fallback, fallback_reason, primary_issue = should_attempt_device_fallback(
        config,
        initial_attempt,
        changed_files,
    )
    describe_issue(primary_issue, config, changed_files)
    print(f"Device fallback decision: {'run' if should_fallback else 'skip'} ({fallback_reason})")

    if not should_fallback:
        return initial_attempt.exit_code

    selected_device, device_reason = explicit_selected_device(config)
    fallback_device, fallback_reason = load_selected_device_from_env("XCODE_FALLBACK_DEVICE_")
    if fallback_device:
        selected_device = fallback_device
        device_reason = fallback_reason or device_reason

    if not selected_device:
        fallback_error = os.environ.get("XCODE_FALLBACK_DEVICE_ERROR")
        if fallback_error:
            print(f"Device fallback blocked: {fallback_error}", file=sys.stderr)
        else:
            print(
                "Device fallback blocked: no physical device destination resolved; set XCODE_DEVICE_ID or run via build-check.sh",
                file=sys.stderr,
            )
        return 1

    device_destination = f"id={selected_device['identifier']}"
    device_command = config.command_for_destination(device_destination)
    print()
    print_attempt_header(config, "Physical device fallback validation", device_destination, device_command)
    print(
        "Selected device: "
        f"{selected_device['name']} [{selected_device['identifier']}] ({selected_device['state']})"
    )
    print(f"Selection reason: {device_reason}")

    device_attempt = run_build(
        device_command,
        cwd=root,
        label="Physical device fallback validation",
        destination=device_destination,
    )
    print(f"Result: {'SUCCESS' if device_attempt.exit_code == 0 else 'FAILED'}")
    maybe_print_output(device_attempt, config.show_output)
    return device_attempt.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
