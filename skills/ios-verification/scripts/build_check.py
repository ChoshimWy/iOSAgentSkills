#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
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
UI_SENSITIVE_FILE_PATTERNS = (
    re.compile(r".*ViewController.*\.swift$", re.IGNORECASE),
    re.compile(r".*View.*\.swift$", re.IGNORECASE),
    re.compile(r".*Router.*\.swift$", re.IGNORECASE),
    re.compile(r".*Coordinator.*\.swift$", re.IGNORECASE),
    re.compile(r".*\.storyboard$", re.IGNORECASE),
    re.compile(r".*\.xib$", re.IGNORECASE),
)
UI_SENSITIVE_PATH_PREFIXES = ("Assets.xcassets/",)
UI_SMOKE_MODE_VALUES = {"off", "auto", "required"}
CURRENT_BUILD_CONFIG: "BuildConfig" | None = None
DEFAULT_ARTIFACT_SUBDIR = ".codex/build-results/latest"
DEFAULT_FORMATTER_CANDIDATES = ("xcbeautify", "xcpretty", "xcprint")
FORMATTER_VALUES = {"auto", "none", *DEFAULT_FORMATTER_CANDIDATES}
TOOL_INSTALL_POLICY_VALUES = {"auto", "off", "required"}
SECRET_PATTERNS = (
    re.compile(r"(?i)(Authorization:\s*Bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)((?:token|api[_-]?key|secret|password|passwd)\s*[:=]\s*)[^\s]+"),
    re.compile(r"(?i)(PROVISIONING_PROFILE(?:_SPECIFIER)?\s*=\s*)[^\s]+"),
)
SENSITIVE_ARG_NAMES = {
    "authorization",
    "authorization:",
    "bearer",
    "--token",
    "--api-key",
    "--apikey",
    "--secret",
    "--password",
    "--passwd",
}
SENSITIVE_ARG_PREFIXES = (
    "--token=",
    "--api-key=",
    "--apikey=",
    "--github-token=",
    "--auth-token=",
    "--secret=",
    "--password=",
    "--passwd=",
)


@dataclass
class BuildIssue:
    order: int
    kind: str
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    severity: str = "error"
    target: str | None = None
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
    formatted_output: str = ""

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
    device_fallback_enabled: bool
    explicit_device_id: str | None
    explicit_device_name: str | None
    preferred_model: str | None
    validation_platform: str | None
    show_output: bool
    ui_smoke_mode: str
    ui_smoke_spec: str
    derived_data_path: str | None
    derived_data_mode: str | None
    artifacts_dir: Path
    formatter_preference: str
    tool_install_policy: str
    tool_install_overrides: dict[str, str]

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

        if self.derived_data_path:
            command += ["-derivedDataPath", self.derived_data_path]

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
    "XCODE_UI_SMOKE_MODE",
    "XCODE_UI_SMOKE_SPEC",
    "CODEX_VERIFY_ARTIFACT_DIR",
    "CODEX_VERIFY_FORMATTER",
    "CODEX_VERIFY_TOOL_INSTALL",
    "CODEX_VERIFY_INSTALL_XCBEAUTIFY",
    "CODEX_VERIFY_INSTALL_XCPRETTY",
    "CODEX_VERIFY_INSTALL_XCPRINT",
)


@dataclass
class ToolBootstrapResult:
    formatter: str | None
    command: list[str]
    install_attempted: bool
    install_succeeded: bool
    install_command: list[str] | None = None
    status: str = "not_needed"
    message: str = ""


@dataclass
class VerificationArtifacts:
    agent_summary: Path
    verification_report: Path
    diagnostics_json: Path
    build_summary: Path
    test_summary: Path
    xcresult_summary: Path
    raw_log: Path
    formatted_log: Path
    source_context: Path


@dataclass
class UISmokeResult:
    should_run: bool
    success: bool
    message: str


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


def normalize_ui_smoke_mode(value: str | None) -> str:
    if value is None:
        return "auto"
    mode = value.strip().lower()
    if mode in UI_SMOKE_MODE_VALUES:
        return mode
    return "auto"


def normalize_formatter_preference(value: str | None) -> str:
    if value is None:
        return "auto"
    formatter = value.strip().lower()
    if formatter in FORMATTER_VALUES:
        return formatter
    return "auto"


def normalize_tool_install_policy(value: str | None) -> str:
    if value is None:
        return "auto"
    policy = value.strip().lower()
    if policy in TOOL_INSTALL_POLICY_VALUES:
        return policy
    return "auto"


def resolve_artifacts_dir(root: Path, env: dict[str, str]) -> Path:
    configured = env.get("CODEX_VERIFY_ARTIFACT_DIR")
    if configured:
        candidate = Path(configured).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate.resolve()
    return (root / DEFAULT_ARTIFACT_SUBDIR).resolve()


def pick_workspace(root: Path, env: dict[str, str]) -> str | None:
    if env.get("XCODE_WORKSPACE"):
        return env["XCODE_WORKSPACE"]

    candidates = workspace_candidates(root)
    return str(candidates[0].relative_to(root)) if candidates else None


def workspace_candidates(root: Path) -> list[Path]:
    candidates = [
        path
        for path in root.rglob("*.xcworkspace")
        if "Pods" not in path.parts and "project.xcworkspace" not in str(path)
    ]
    return sorted(path for path in candidates if len(path.relative_to(root).parts) <= 3)


def pick_project(root: Path, env: dict[str, str]) -> str | None:
    if env.get("XCODE_PROJECT"):
        return env["XCODE_PROJECT"]

    candidates = project_candidates(root)
    return str(candidates[0].relative_to(root)) if candidates else None


def project_candidates(root: Path) -> list[Path]:
    candidates = [path for path in root.rglob("*.xcodeproj") if "Pods" not in path.parts]
    return sorted(path for path in candidates if len(path.relative_to(root).parts) <= 3)


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
                name = Path(value).stem
                if name not in names:
                    names.append(name)
    return names


def scheme_paths(root: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for path in sorted(root.rglob("*.xcscheme")):
        if "Pods" in path.parts:
            continue
        paths.setdefault(path.stem, path)
    return paths


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

    paths = scheme_paths(root)

    schemes = list(paths.keys())
    if not schemes:
        raise RuntimeError("No shared scheme found")

    return sorted(schemes, key=lambda name: scheme_sort_key(name, paths.get(name)))[0]


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
        device_fallback_enabled=truthy(env.get("XCODE_DEVICE_FALLBACK"), default=True),
        explicit_device_id=env.get("XCODE_DEVICE_ID"),
        explicit_device_name=env.get("XCODE_DEVICE_NAME"),
        preferred_model=env.get("XCODE_PREFER_MODEL"),
        validation_platform=os.environ.get("XCODE_VALIDATION_PLATFORM"),
        show_output=truthy(env.get("XCODEBUILD_SHOW_OUTPUT"), default=False),
        ui_smoke_mode=normalize_ui_smoke_mode(env.get("XCODE_UI_SMOKE_MODE")),
        ui_smoke_spec=env.get("XCODE_UI_SMOKE_SPEC", ".codex/ui-smoke.yml"),
        derived_data_path=env.get("XCODE_DERIVED_DATA"),
        derived_data_mode=os.environ.get("CODEX_EFFECTIVE_DERIVED_DATA_MODE"),
        artifacts_dir=resolve_artifacts_dir(root, env),
        formatter_preference=normalize_formatter_preference(env.get("CODEX_VERIFY_FORMATTER")),
        tool_install_policy=normalize_tool_install_policy(env.get("CODEX_VERIFY_TOOL_INSTALL")),
        tool_install_overrides={
            "xcbeautify": env.get("CODEX_VERIFY_INSTALL_XCBEAUTIFY", ""),
            "xcpretty": env.get("CODEX_VERIFY_INSTALL_XCPRETTY", ""),
            "xcprint": env.get("CODEX_VERIFY_INSTALL_XCPRINT", ""),
        },
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


def run_git_text(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        errors="replace",
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout or ""


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def install_command_for_tool(tool: str, config: BuildConfig) -> list[str] | None:
    override = config.tool_install_overrides.get(tool) or ""
    if override:
        return shlex.split(override)

    if tool == "xcbeautify":
        if command_exists("brew"):
            return ["brew", "install", "xcbeautify"]
        if command_exists("mint"):
            return ["mint", "install", "thii/xcbeautify"]
    if tool == "xcpretty" and command_exists("gem"):
        return ["gem", "install", "xcpretty"]
    if tool == "xcprint" and command_exists("brew"):
        return ["brew", "install", "xcprint"]
    return None


def install_tool(tool: str, config: BuildConfig) -> ToolBootstrapResult:
    install_command = install_command_for_tool(tool, config)
    if install_command is None:
        return ToolBootstrapResult(
            formatter=None,
            command=[],
            install_attempted=False,
            install_succeeded=False,
            status="unavailable",
            message=f"{tool} is not installed and no supported installer is available",
        )

    print(f"[build_check] installing missing formatter: {redact_command_string(install_command)}")
    completed = subprocess.run(
        install_command,
        cwd=config.root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    installed = completed.returncode == 0 and command_exists(tool)
    message = (
        f"{tool} installed"
        if installed
        else f"{tool} install failed with exit code {completed.returncode}"
    )
    return ToolBootstrapResult(
        formatter=tool if installed else None,
        command=[tool] if installed else [],
        install_attempted=True,
        install_succeeded=installed,
        install_command=install_command,
        status="installed" if installed else "install_failed",
        message=redact_sensitive(message),
    )


def ensure_formatter(config: BuildConfig) -> ToolBootstrapResult:
    preference = config.formatter_preference
    if preference == "none":
        return ToolBootstrapResult(
            formatter=None,
            command=[],
            install_attempted=False,
            install_succeeded=False,
            status="disabled",
            message="external formatter disabled; using built-in digest parser",
        )

    candidates = list(DEFAULT_FORMATTER_CANDIDATES) if preference == "auto" else [preference]
    for tool in candidates:
        if command_exists(tool):
            return ToolBootstrapResult(
                formatter=tool,
                command=[tool],
                install_attempted=False,
                install_succeeded=False,
                status="available",
                message=f"{tool} is available",
            )

    if config.tool_install_policy == "off":
        return ToolBootstrapResult(
            formatter=None,
            command=[],
            install_attempted=False,
            install_succeeded=False,
            status="missing_install_disabled",
            message="formatter missing and CODEX_VERIFY_TOOL_INSTALL=off; using built-in digest parser",
        )

    install_results: list[ToolBootstrapResult] = []
    for tool in candidates:
        result = install_tool(tool, config)
        install_results.append(result)
        if result.formatter:
            return result

    message = "; ".join(result.message for result in install_results if result.message)
    if config.tool_install_policy == "required":
        return ToolBootstrapResult(
            formatter=None,
            command=[],
            install_attempted=any(result.install_attempted for result in install_results),
            install_succeeded=False,
            install_command=next((result.install_command for result in install_results if result.install_command), None),
            status="required_formatter_unavailable",
            message=message or "required formatter unavailable",
        )

    return ToolBootstrapResult(
        formatter=None,
        command=[],
        install_attempted=any(result.install_attempted for result in install_results),
        install_succeeded=False,
        install_command=next((result.install_command for result in install_results if result.install_command), None),
        status="fallback_builtin_parser",
        message=(message or "formatter unavailable") + "; using built-in digest parser",
    )


def format_output(raw_output: str, tool_bootstrap: ToolBootstrapResult, cwd: Path) -> str:
    if not tool_bootstrap.command:
        return ""
    completed = subprocess.run(
        tool_bootstrap.command,
        input=raw_output,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if completed.returncode != 0:
        return f"formatter failed with exit code {completed.returncode}\n{completed.stdout or ''}".strip()
    return completed.stdout or ""


def redact_sensitive(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}<redacted>", redacted)
    return redacted


def is_sensitive_arg_name(value: str) -> bool:
    normalized = value.strip().lower().rstrip(":")
    if normalized in SENSITIVE_ARG_NAMES:
        return True
    if not normalized.startswith("-"):
        return False
    sensitive_tokens = (
        "authorization",
        "auth",
        "token",
        "api-key",
        "apikey",
        "secret",
        "password",
        "passwd",
    )
    return any(token in normalized for token in sensitive_tokens)


def redact_command(command: list[str] | None) -> list[str] | None:
    if command is None:
        return None

    redacted: list[str] = []
    redact_next = False
    for part in command:
        lower = part.strip().lower()
        if redact_next:
            redacted.append("<redacted>")
            redact_next = lower in {"bearer", "authorization", "authorization:"}
            continue

        if "authorization" in lower:
            cleaned = redact_sensitive(part)
            if cleaned == part:
                cleaned = re.sub(r"(?i)(Authorization:\s*).*", r"\1<redacted>", part)
            redacted.append(cleaned)
            redact_next = True
            continue

        prefix = next((item for item in SENSITIVE_ARG_PREFIXES if lower.startswith(item)), None)
        if prefix or (lower.startswith("--") and "=" in lower and is_sensitive_arg_name(lower.split("=", 1)[0])):
            key_prefix = part.split("=", 1)[0] + "="
            redacted.append(key_prefix + "<redacted>")
            continue

        cleaned = redact_sensitive(part)
        if lower in SENSITIVE_ARG_NAMES or is_sensitive_arg_name(lower):
            redacted.append(cleaned)
            redact_next = True
            continue
        redacted.append(cleaned)
    return redacted


def redact_command_string(command: list[str] | None) -> str:
    redacted = redact_command(command) or []
    return " ".join(shlex.quote(part) for part in redacted)


def short_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


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


def is_ui_sensitive_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if any(
        normalized.startswith(prefix) or f"/{prefix}" in normalized
        for prefix in UI_SENSITIVE_PATH_PREFIXES
    ):
        return True
    return any(pattern.match(normalized) for pattern in UI_SENSITIVE_FILE_PATTERNS)


def has_ui_sensitive_changes(changed_files: set[str]) -> bool:
    return any(is_ui_sensitive_path(path) for path in changed_files)


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


def compile_issue_kind(file_path: str) -> str:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".swift":
        return "swift_compile_error"
    if suffix in {".m", ".mm", ".h"}:
        return "objc_compile_error"
    return "compilation_error"


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
                    kind=compile_issue_kind(file_path),
                    message=match.group("message").strip(),
                    file=file_path,
                    line=int(match.group("line")),
                    column=int(match.group("column")),
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


def failure_domain_for_issue(issue: BuildIssue) -> str:
    if issue.kind == "xcodebuild_error":
        message = issue.message.lower()
        if "destination" in message or "device" in message:
            return "destination"
        if "provision" in message or "signing" in message or "certificate" in message:
            return "signing"
        if "workspace" in message or "project" in message or "scheme" in message:
            return "project_config"
        return "infra"
    if issue.kind in {"framework_not_found", "library_not_found"}:
        return "dependency"
    if issue.kind in {
        "simulator_linker_incompatible",
        "undefined_symbols",
        "linker_symbols_not_found",
    }:
        return "dependency" if issue.third_party_evidence else "code"
    if issue.kind in {"swift_compile_error", "objc_compile_error", "compilation_error"}:
        return "code"
    if issue.kind == "ui_smoke_failure":
        return "test"
    if issue.kind == "destination_unavailable":
        return "destination"
    return "code"


def issue_priority(issue: BuildIssue) -> tuple[int, int]:
    priority_by_domain = {
        "project_config": 0,
        "dependency": 1,
        "code": 2,
        "signing": 3,
        "destination": 4,
        "test": 5,
        "infra": 6,
    }
    return (priority_by_domain.get(failure_domain_for_issue(issue), 10), issue.order)


def select_primary_issue(issues: list[BuildIssue]) -> BuildIssue | None:
    return sorted(issues, key=issue_priority)[0] if issues else None


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


def acquire_directory_lock(lock_dir: Path, label: str) -> None:
    poll_seconds = max(1, int(os.environ.get("CODEX_VERIFY_LOCK_POLL_SECONDS", "5")))
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    wait_started = time.time()

    while True:
        try:
            lock_dir.mkdir()
            owner_file = lock_dir / "owner.txt"
            owner_file.write_text(
                "\n".join(
                    [
                        f"pid={os.getpid()}",
                        f"label={label}",
                        f"started_at={time.strftime('%Y-%m-%d %H:%M:%S %z')}",
                    ]
                )
                + "\n"
            )
            return
        except FileExistsError:
            waited = int(time.time() - wait_started)
            owner_file = lock_dir / "owner.txt"
            owner_summary = owner_file.read_text().strip().replace("\n", "; ") if owner_file.exists() else ""
            if owner_summary:
                print(f"[build_check] waiting {waited}s for {label}: {owner_summary}")
            else:
                print(f"[build_check] waiting {waited}s for {label}: lock_dir={lock_dir}")
            time.sleep(poll_seconds)


def release_directory_lock(lock_dir: Path) -> None:
    owner_file = lock_dir / "owner.txt"
    if owner_file.exists():
        owner_file.unlink()
    try:
        lock_dir.rmdir()
    except OSError:
        pass


def destination_lock_path(config: BuildConfig | None, destination: str | None) -> Path | None:
    if config is None:
        return None
    if config.action not in {"test", "test-without-building"}:
        return None

    lock_root = os.environ.get("CODEX_VERIFY_DESTINATION_LOCK_ROOT")
    if not lock_root or not destination:
        return None

    destination_hash = hashlib.sha256(destination.encode("utf-8")).hexdigest()
    return Path(lock_root) / f"destination-{destination_hash}.lockdir"


def run_build(command: list[str], cwd: Path, label: str, destination: str | None) -> BuildAttempt:
    config = CURRENT_BUILD_CONFIG
    destination_lock = destination_lock_path(config, destination) if config is not None else None
    if destination_lock is not None:
        acquire_directory_lock(destination_lock, "destination validation lock")

    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
    finally:
        if destination_lock is not None:
            release_directory_lock(destination_lock)
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
    derived_data_home = str(Path.home() / "Library/Developer/Xcode/DerivedData")
    print(f"=== {label} ===")
    print(f"Root: {config.root}")
    if config.workspace:
        print(f"Workspace: {config.workspace}")
    else:
        print(f"Project: {config.project}")
    print(f"Scheme: {config.scheme}")
    print(f"Configuration: {config.configuration}")
    print(f"Action: {config.action}")
    if config.derived_data_path:
        mode = config.derived_data_mode or "isolated"
        print(f"DerivedData: {mode} ({config.derived_data_path})")
    else:
        print(f"DerivedData: Xcode default ({derived_data_home})")
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


def artifact_paths(artifacts_dir: Path) -> VerificationArtifacts:
    return VerificationArtifacts(
        agent_summary=artifacts_dir / "agent-summary.json",
        verification_report=artifacts_dir / "verification-report.json",
        diagnostics_json=artifacts_dir / "diagnostics.json",
        build_summary=artifacts_dir / "build-summary.txt",
        test_summary=artifacts_dir / "test-summary.json",
        xcresult_summary=artifacts_dir / "xcresult-summary.json",
        raw_log=artifacts_dir / "build.log",
        formatted_log=artifacts_dir / "formatted-build.log",
        source_context=artifacts_dir / "source-context.txt",
    )


def issue_to_dict(issue: BuildIssue | None, config: BuildConfig) -> dict[str, object] | None:
    if issue is None:
        return None
    payload: dict[str, object] = {
        "kind": issue.kind,
        "severity": issue.severity,
        "message": redact_sensitive(issue.message),
        "failure_domain": failure_domain_for_issue(issue),
        "retryable": failure_domain_for_issue(issue) in {"destination", "infra"},
    }
    if issue.file:
        relative = relative_to_root(issue.file, config.root)
        payload["file"] = relative or issue.file
    if issue.line is not None:
        payload["line"] = issue.line
    if issue.column is not None:
        payload["column"] = issue.column
    if issue.target:
        payload["target"] = issue.target
    if issue.related_paths:
        payload["related_paths"] = [redact_sensitive(path) for path in issue.related_paths[:3]]
    return payload


def warning_count(output: str) -> int:
    return sum(1 for line in output.splitlines() if ": warning:" in line or line.strip().startswith("warning:"))


def extract_failed_tests(output: str, limit: int = 5) -> list[dict[str, str]]:
    failed_tests: list[dict[str, str]] = []
    seen: set[str] = set()
    patterns = (
        re.compile(r"Test Case '([^']+)' failed"),
        re.compile(r"Failing tests:\s*(.+)$"),
    )
    for line in output.splitlines():
        for pattern in patterns:
            match = pattern.search(line)
            if not match:
                continue
            name = match.group(1).strip()
            if name and name not in seen:
                failed_tests.append({"name": name})
                seen.add(name)
            if len(failed_tests) >= limit:
                return failed_tests
    return failed_tests


def write_source_context(issue: BuildIssue | None, config: BuildConfig, path: Path) -> str | None:
    if not issue or not issue.file or issue.line is None:
        return None

    source_path = normalize_path(issue.file, config.root)
    try:
        relative = source_path.relative_to(config.root.resolve()).as_posix()
    except ValueError:
        return None

    if not source_path.exists() or not source_path.is_file():
        return None

    try:
        lines = source_path.read_text(errors="replace").splitlines()
    except OSError:
        return None

    start = max(issue.line - 6, 0)
    end = min(issue.line + 5, len(lines))
    snippet_lines = [
        f"{line_number + 1}: {lines[line_number]}"
        for line_number in range(start, end)
    ]
    path.write_text(
        f"{relative}:{issue.line}\n" + "\n".join(snippet_lines) + "\n",
        encoding="utf-8",
    )
    return str(path)


def compute_verification_fingerprint(
    config: BuildConfig,
    attempts: list[BuildAttempt],
    changed_files: set[str],
) -> str:
    baseline = {
        "workspace": config.workspace,
        "project": config.project,
        "scheme": config.scheme,
        "configuration": config.configuration,
        "action": config.action,
        "destinations": [attempt.destination for attempt in attempts],
        "commands": [attempt.command_string for attempt in attempts],
        "changed_files": sorted(changed_files),
        "git_diff": run_git_text(config.root, ["diff", "--cached"]) + run_git_text(config.root, ["diff"]),
    }
    return short_sha(json.dumps(baseline, sort_keys=True, ensure_ascii=False))


def extract_only_testing(command: list[str]) -> list[str]:
    selectors: list[str] = []
    index = 0
    while index < len(command):
        part = command[index]
        if part.startswith("-only-testing:"):
            selector = part.split(":", 1)[1]
            if selector:
                selectors.append(selector)
        elif part == "-only-testing" and index + 1 < len(command):
            selectors.append(command[index + 1])
            index += 1
        index += 1
    return selectors


def destination_type(destination: str | None, config: BuildConfig) -> str:
    if config.validation_platform == "macos":
        return "macos"
    if not destination:
        return "macos" if config.validation_platform == "macos" else "unknown"
    normalized = destination.lower()
    if "simulator" in normalized:
        return "simulator"
    if "generic/platform=ios" in normalized:
        return "generic_ios"
    if normalized.startswith("id="):
        return "physical_device"
    return "unknown"


def verification_level(
    config: BuildConfig,
    only_testing: list[str],
    ui_smoke_result: UISmokeResult | None = None,
) -> str:
    if ui_smoke_result and ui_smoke_result.should_run:
        return "ui"
    if only_testing:
        return "unit"
    action = config.action.lower()
    if action in {"test", "test-without-building"}:
        return "unit"
    if action in {"archive", "exportarchive"}:
        return "full"
    return "build"


def project_selection_payload(config: BuildConfig, env: dict[str, str]) -> dict[str, object]:
    workspace = config.workspace
    project = config.project
    if workspace:
        source = ".codex/xcodebuild.env" if env.get("XCODE_WORKSPACE") else "auto_discovered"
        reason = (
            "XCODE_WORKSPACE explicitly configured"
            if env.get("XCODE_WORKSPACE")
            else ".xcworkspace preferred over .xcodeproj"
            if project
            else ".xcworkspace auto discovered"
        )
        return {
            "type": "workspace",
            "value": workspace,
            "source": source,
            "reason": reason,
            "workspace_candidates": [str(path.relative_to(config.root)) for path in workspace_candidates(config.root)],
            "project_candidates": [str(path.relative_to(config.root)) for path in project_candidates(config.root)],
        }

    return {
        "type": "project",
        "value": project,
        "source": ".codex/xcodebuild.env" if env.get("XCODE_PROJECT") else "auto_discovered",
        "reason": (
            "XCODE_PROJECT explicitly configured"
            if env.get("XCODE_PROJECT")
            else "no .xcworkspace found; using .xcodeproj"
        ),
        "workspace_candidates": [],
        "project_candidates": [str(path.relative_to(config.root)) for path in project_candidates(config.root)],
    }


def scheme_selection_reason(name: str, path: Path | None, source: str) -> str:
    if source == ".codex/xcodebuild.env":
        return "XCODE_SCHEME explicitly configured"
    if scheme_has_unit_test_binding(path):
        return "scheme has unit test binding"
    if is_unit_test_preferred_scheme(name):
        return "scheme name matches unit test pattern"
    if is_generic_test_scheme(name):
        return "scheme name matches generic test pattern"
    if scheme_has_ui_test_binding(path):
        return "scheme has UI test binding"
    if is_ui_test_preferred_scheme(name):
        return "scheme name matches UI test pattern"
    if not NON_PRODUCTION_SCHEME_PATTERN.search(name):
        return "non-production scheme suffix not detected"
    return "fallback shared scheme"


def scheme_selection_payload(config: BuildConfig, env: dict[str, str]) -> dict[str, object]:
    paths = scheme_paths(config.root)
    selected_path = paths.get(config.scheme)
    source = ".codex/xcodebuild.env" if env.get("XCODE_SCHEME") else "auto_discovered"
    testables = iter_scheme_testable_names(selected_path)
    return {
        "scheme": config.scheme,
        "source": source,
        "reason": scheme_selection_reason(config.scheme, selected_path, source),
        "testables": testables,
        "has_unit_tests": any(is_unit_test_preferred_scheme(name) for name in testables),
        "has_ui_tests": any(is_ui_test_preferred_scheme(name) for name in testables),
        "scheme_path": str(selected_path.relative_to(config.root)) if selected_path else None,
        "candidate_schemes": sorted(paths.keys()),
    }


def write_verification_artifacts(
    config: BuildConfig,
    attempts: list[BuildAttempt],
    final_status: str,
    final_exit_code: int,
    changed_files: set[str],
    tool_bootstrap: ToolBootstrapResult,
    ui_smoke_result: UISmokeResult | None = None,
    selected_device_reason: str | None = None,
) -> None:
    paths = artifact_paths(config.artifacts_dir)
    config.artifacts_dir.mkdir(parents=True, exist_ok=True)

    raw_output = "\n\n".join(
        f"=== {attempt.label} ===\nCommand: {attempt.command_string}\nExit code: {attempt.exit_code}\n{attempt.combined_output}"
        for attempt in attempts
    )
    formatted_output = "\n\n".join(
        f"=== {attempt.label} ===\n{attempt.formatted_output}"
        for attempt in attempts
        if attempt.formatted_output.strip()
    )
    paths.raw_log.write_text(raw_output, encoding="utf-8")
    paths.formatted_log.write_text(formatted_output, encoding="utf-8")

    all_issues = [issue for attempt in attempts for issue in attempt.issues]
    primary_issue = select_primary_issue(all_issues)
    if final_status == "blocked":
        primary_issue = next(
            (
                issue
                for issue in reversed(all_issues)
                if issue.kind in {"destination_unavailable", "formatter_unavailable"}
                or issue.message.startswith("Device fallback blocked")
            ),
            primary_issue,
        )
    source_context_path = write_source_context(primary_issue, config, paths.source_context)
    combined_output = "\n".join(attempt.combined_output for attempt in attempts)
    failed_tests = extract_failed_tests(combined_output)
    diagnostics = [issue_to_dict(issue, config) for issue in sorted(all_issues, key=issue_priority)[:5]]
    diagnostics = [item for item in diagnostics if item is not None]
    fingerprint = compute_verification_fingerprint(config, attempts, changed_files)

    workspace_or_project = config.workspace or config.project
    first_error = issue_to_dict(primary_issue, config)
    formatter_blocked = (
        final_status == "blocked"
        and tool_bootstrap.status == "required_formatter_unavailable"
    )
    if formatter_blocked:
        first_error = {
            "kind": "formatter_unavailable",
            "severity": "error",
            "message": tool_bootstrap.message or "required formatter unavailable",
            "failure_domain": "infra",
            "retryable": True,
        }

    summary = "verification passed" if final_status == "passed" else "verification failed"
    suggested_next_action = "none" if final_status == "passed" else "fix_first_error"
    needs_raw_log = False
    if final_status == "blocked":
        suggested_next_action = "blocked"
        needs_raw_log = False
    if formatter_blocked:
        summary = f"formatter bootstrap blocked: {first_error['message']}"
    elif final_status != "passed" and first_error is None:
        summary = "verification failed; digest could not classify the first blocking error"
        suggested_next_action = "inspect_environment"
        needs_raw_log = True
    elif first_error:
        location = first_error.get("file", "")
        line = first_error.get("line")
        where = f"{location}:{line}" if location and line else location
        summary = f"{first_error.get('kind')}: {where} {first_error.get('message')}".strip()

    artifact_payload = {
        "agent_summary": str(paths.agent_summary),
        "verification_report": str(paths.verification_report),
        "diagnostics_json": str(paths.diagnostics_json),
        "build_summary": str(paths.build_summary),
        "test_summary": str(paths.test_summary),
        "xcresult_summary": str(paths.xcresult_summary),
        "raw_log": str(paths.raw_log),
        "formatted_log": str(paths.formatted_log),
    }
    if source_context_path:
        artifact_payload["source_context"] = source_context_path

    executed_commands = [attempt.command_string for attempt in attempts]
    only_testing: list[str] = []
    for attempt in attempts:
        only_testing.extend(extract_only_testing(attempt.command))
    final_destination = attempts[-1].destination if attempts else config.destination
    env = load_env(config.root)
    project_selection = project_selection_payload(config, env)
    scheme_selection = scheme_selection_payload(config, env)

    report = {
        "schema_version": 1,
        "producer": "codex_verify",
        "parser": "builtin-digest-parser",
        "formatter": tool_bootstrap.formatter,
        "status": final_status,
        "mode": config.action,
        "fingerprint": fingerprint,
        "cached": False,
        "summary": redact_sensitive(summary),
        "first_blocking_error": first_error,
        "failed_tests": failed_tests,
        "warnings_count": warning_count(combined_output),
        "artifact_paths": artifact_payload,
        "tool_bootstrap": {
            "formatter": tool_bootstrap.formatter,
            "status": tool_bootstrap.status,
            "install_attempted": tool_bootstrap.install_attempted,
            "install_succeeded": tool_bootstrap.install_succeeded,
            "install_command": redact_command(tool_bootstrap.install_command),
            "message": tool_bootstrap.message,
        },
        "baseline": {
            "workspace_or_project": workspace_or_project,
            "scheme": config.scheme,
            "configuration": config.configuration,
            "action": config.action,
            "destination": final_destination,
            "destination_type": destination_type(final_destination, config),
            "selected_device_reason": selected_device_reason,
            "derived_data": config.derived_data_path or "Xcode default",
        },
        "project_selection": project_selection,
        "scheme_selection": scheme_selection,
        "only_testing": only_testing,
        "executed_commands": executed_commands,
        "ui_smoke": {
            "executed": bool(ui_smoke_result and ui_smoke_result.should_run),
            "result": (
                "passed"
                if ui_smoke_result and ui_smoke_result.success
                else "failed"
                if ui_smoke_result and ui_smoke_result.should_run
                else "skipped"
            ),
            "message": ui_smoke_result.message if ui_smoke_result else "not evaluated",
        },
        "suggested_next_action": suggested_next_action,
        "raw_log_policy": "forbidden_by_default",
        "needs_raw_log": needs_raw_log,
    }
    agent_summary = {
        "schema_version": 1,
        "producer": "codex_verify_agent_summary",
        "status": final_status,
        "verification_level": verification_level(config, only_testing, ui_smoke_result),
        "route": "codex_verify -> build-queue daemon -> xcodebuild"
        if os.environ.get("CODEX_VERIFY_QUEUE_ROOT")
        else "build-check.py -> xcodebuild",
        "repo_root": str(config.root),
        "workspace_or_project": workspace_or_project,
        "project_selection": project_selection,
        "scheme": config.scheme,
        "scheme_selection": scheme_selection,
        "configuration": config.configuration,
        "action": config.action,
        "destination": {
            "type": destination_type(final_destination, config),
            "value": final_destination,
            "selected_device_reason": selected_device_reason,
        },
        "only_testing": only_testing,
        "executed_command": executed_commands[-1] if executed_commands else None,
        "executed_commands": executed_commands,
        "queue_job_id": os.environ.get("CODEX_VERIFY_JOB_ID"),
        "queue_job_dir": os.environ.get("CODEX_VERIFY_JOB_DIR"),
        "fingerprint": fingerprint,
        "cached": False,
        "summary": report["summary"],
        "first_blocking_error": first_error,
        "failed_tests": failed_tests,
        "warnings_count": report["warnings_count"],
        "ui_smoke": report["ui_smoke"],
        "artifact_paths": artifact_payload,
        "raw_log_policy": "forbidden_by_default",
        "needs_raw_log": needs_raw_log,
        "next_action": suggested_next_action,
    }

    diagnostics_payload = {
        "schema_version": 1,
        "status": final_status,
        "mode": config.action,
        "fingerprint": fingerprint,
        "cached": False,
        "summary": report["summary"],
        "diagnostics": diagnostics or ([first_error] if first_error else []),
        "next_action": suggested_next_action,
    }
    test_payload = {
        "schema_version": 1,
        "status": final_status,
        "failed_tests": failed_tests,
    }
    xcresult_payload = {
        "schema_version": 1,
        "status": "skipped",
        "summary": "No compact xcresult summary generated by build_check.py",
    }
    summary_lines = [
        f"status: {final_status}",
        f"exit_code: {final_exit_code}",
        f"workspace_or_project: {workspace_or_project}",
        f"scheme: {config.scheme}",
        f"configuration: {config.configuration}",
        f"action: {config.action}",
        f"destination: {attempts[-1].destination if attempts else config.destination}",
        f"destination_type: {destination_type(final_destination, config)}",
        f"only_testing: {', '.join(only_testing) if only_testing else 'none'}",
        f"fingerprint: {fingerprint}",
        f"formatter: {tool_bootstrap.formatter or 'builtin-digest-parser'} ({tool_bootstrap.status})",
        f"summary: {report['summary']}",
        f"agent_summary: {paths.agent_summary}",
        f"raw_log_policy: forbidden_by_default",
    ]

    paths.verification_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths.agent_summary.write_text(json.dumps(agent_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths.diagnostics_json.write_text(json.dumps(diagnostics_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths.test_summary.write_text(json.dumps(test_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths.xcresult_summary.write_text(json.dumps(xcresult_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths.build_summary.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Agent summary: {paths.agent_summary}")
    print(f"Evidence: {paths.verification_report}")
    print(f"Diagnostics: {paths.diagnostics_json}")
    print("Raw log: skipped by policy")


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
    issue = select_primary_issue(simulator_attempt.issues)
    if config.action != "build":
        return False, f"device fallback is disabled for action '{config.action}'", issue

    if not is_simulator_destination(config.destination):
        return False, "initial destination is not an iOS Simulator target", issue

    if not config.device_fallback_enabled:
        return False, "XCODE_DEVICE_FALLBACK=0", issue

    if not issue:
        return False, "unable to classify the first real simulator failure", None

    if issue_touches_changed_files(issue, changed_files, config.root):
        return False, "the first real simulator failure is inside changed files", issue

    if not issue_matches_device_fallback_whitelist(issue):
        return False, "the first real simulator failure is not in the device-fallback whitelist", issue

    return True, "third-party simulator-only linker failure", issue


def run_ui_smoke_if_needed(
    config: BuildConfig,
    changed_files: set[str],
    initial_destination: str | None,
) -> UISmokeResult:
    mode = config.ui_smoke_mode
    if mode == "off":
        return UISmokeResult(False, True, "UI smoke skipped: XCODE_UI_SMOKE_MODE=off")

    ui_sensitive = has_ui_sensitive_changes(changed_files)
    if not ui_sensitive:
        return UISmokeResult(False, True, "UI smoke skipped: no UI-sensitive file changes detected")

    if not is_simulator_destination(initial_destination):
        message = "UI smoke skipped: initial destination is not iOS Simulator"
        if mode == "required":
            message = (
                "UI smoke required but initial destination is not iOS Simulator. "
                "Set XCODE_DESTINATION to a simulator destination."
            )
            return UISmokeResult(True, False, message)
        return UISmokeResult(False, True, message)

    spec_path = (config.root / config.ui_smoke_spec).resolve()
    if not spec_path.exists():
        if mode == "required":
            return UISmokeResult(
                True,
                False,
                f"UI smoke required but spec not found: {spec_path}",
            )
        return UISmokeResult(
            False,
            True,
            f"UI smoke skipped: spec not found ({spec_path})",
        )

    runner = VERIFY_SKILL_DIR.parent / "ios-automation" / "scripts" / "simulator" / "ui_smoke_runner.py"
    if not runner.exists():
        return UISmokeResult(True, False, f"UI smoke runner missing: {runner}")

    artifacts_dir = config.root / ".codex" / "ui-smoke-artifacts"
    command = [
        "python3",
        str(runner),
        "--spec",
        str(spec_path),
        "--output-dir",
        str(artifacts_dir),
    ]

    print("=== UI smoke validation ===")
    print(f"Spec: {spec_path}")
    print(f"Runner: {runner}")
    print(f"Command: {' '.join(shlex.quote(part) for part in command)}")

    completed = subprocess.run(
        command,
        cwd=config.root,
        capture_output=True,
        text=True,
        errors="replace",
    )

    if completed.stdout.strip():
        print("--- ui smoke stdout ---")
        print(completed.stdout.rstrip())
    if completed.stderr.strip():
        print("--- ui smoke stderr ---")
        print(completed.stderr.rstrip())

    if completed.returncode != 0:
        return UISmokeResult(
            True,
            False,
            f"UI smoke failed with exit code {completed.returncode}",
        )

    return UISmokeResult(True, True, "UI smoke passed")


def main() -> int:
    global CURRENT_BUILD_CONFIG
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
    CURRENT_BUILD_CONFIG = config

    try:
        initial_destination, initial_device, initial_device_reason = resolve_initial_destination(config)
    except Exception as exc:
        print(f"Initial physical-device validation blocked: {exc}", file=sys.stderr)
        return 1

    tool_bootstrap = (
        ToolBootstrapResult(
            formatter=None,
            command=[],
            install_attempted=False,
            install_succeeded=False,
            status="dry_run",
            message="dry run; formatter bootstrap skipped",
        )
        if dry_run
        else ensure_formatter(config)
    )
    print(f"Formatter: {tool_bootstrap.formatter or 'builtin-digest-parser'} ({tool_bootstrap.status})")
    if tool_bootstrap.message:
        print(f"Formatter bootstrap: {tool_bootstrap.message}")
    if tool_bootstrap.status == "required_formatter_unavailable":
        write_verification_artifacts(
            config,
            [],
            final_status="blocked",
            final_exit_code=1,
            changed_files=collect_changed_files(root),
            tool_bootstrap=tool_bootstrap,
            selected_device_reason=initial_device_reason,
        )
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
    initial_attempt.formatted_output = format_output(initial_attempt.combined_output, tool_bootstrap, root)
    initial_attempt.issues = parse_build_issues(initial_attempt.combined_output, root)

    print(f"Result: {'SUCCESS' if initial_attempt.exit_code == 0 else 'FAILED'}")
    maybe_print_output(initial_attempt, config.show_output)

    if initial_attempt.exit_code == 0:
        ui_smoke_result = run_ui_smoke_if_needed(config, changed_files, initial_destination)
        print(ui_smoke_result.message)
        if not ui_smoke_result.success:
            initial_attempt.issues.append(
                BuildIssue(
                    order=len(initial_attempt.combined_output.splitlines()) + 1,
                    kind="ui_smoke_failure",
                    message=ui_smoke_result.message,
                )
            )
            write_verification_artifacts(
                config,
                [initial_attempt],
                final_status="failed",
                final_exit_code=1,
                changed_files=changed_files,
                tool_bootstrap=tool_bootstrap,
                ui_smoke_result=ui_smoke_result,
                selected_device_reason=initial_device_reason,
            )
            return 1
        write_verification_artifacts(
            config,
            [initial_attempt],
            final_status="passed",
            final_exit_code=0,
            changed_files=changed_files,
            tool_bootstrap=tool_bootstrap,
            ui_smoke_result=ui_smoke_result,
            selected_device_reason=initial_device_reason,
        )
        return 0

    primary_issue = select_primary_issue(initial_attempt.issues)

    if config.validation_platform == "macos":
        describe_issue(primary_issue, config, changed_files)
        write_verification_artifacts(
            config,
            [initial_attempt],
            final_status="failed",
            final_exit_code=initial_attempt.exit_code,
            changed_files=changed_files,
            tool_bootstrap=tool_bootstrap,
            selected_device_reason=initial_device_reason,
        )
        return initial_attempt.exit_code

    if not is_simulator_destination(initial_destination):
        describe_issue(primary_issue, config, changed_files)
        write_verification_artifacts(
            config,
            [initial_attempt],
            final_status="failed",
            final_exit_code=initial_attempt.exit_code,
            changed_files=changed_files,
            tool_bootstrap=tool_bootstrap,
            selected_device_reason=initial_device_reason,
        )
        return initial_attempt.exit_code

    should_fallback, fallback_reason, primary_issue = should_attempt_device_fallback(
        config,
        initial_attempt,
        changed_files,
    )
    describe_issue(primary_issue, config, changed_files)
    print(f"Device fallback decision: {'run' if should_fallback else 'skip'} ({fallback_reason})")

    if not should_fallback:
        write_verification_artifacts(
            config,
            [initial_attempt],
            final_status="failed",
            final_exit_code=initial_attempt.exit_code,
            changed_files=changed_files,
            tool_bootstrap=tool_bootstrap,
            selected_device_reason=initial_device_reason,
        )
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
            message = f"Device fallback blocked: {fallback_error}"
        else:
            message = "Device fallback blocked: no physical device destination resolved; set XCODE_DEVICE_ID or run via build-check.sh"
            print(
                message,
                file=sys.stderr,
            )
        initial_attempt.issues.append(
            BuildIssue(
                order=len(initial_attempt.combined_output.splitlines()) + 1,
                kind="destination_unavailable",
                message=message,
            )
        )
        write_verification_artifacts(
            config,
            [initial_attempt],
            final_status="blocked",
            final_exit_code=1,
            changed_files=changed_files,
            tool_bootstrap=tool_bootstrap,
            selected_device_reason=initial_device_reason,
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
    device_attempt.formatted_output = format_output(device_attempt.combined_output, tool_bootstrap, root)
    device_attempt.issues = parse_build_issues(device_attempt.combined_output, root)
    print(f"Result: {'SUCCESS' if device_attempt.exit_code == 0 else 'FAILED'}")
    maybe_print_output(device_attempt, config.show_output)
    write_verification_artifacts(
        config,
        [initial_attempt, device_attempt],
        final_status="passed" if device_attempt.exit_code == 0 else "failed",
        final_exit_code=device_attempt.exit_code,
        changed_files=changed_files,
        tool_bootstrap=tool_bootstrap,
        selected_device_reason=device_reason,
    )
    return device_attempt.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
