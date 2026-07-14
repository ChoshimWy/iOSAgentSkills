#!/usr/bin/env python3
"""Execute one measured Design Context benchmark turn through Codex CLI.

The adapter exposes only inputs marked for the agent, emits the canonical Codex
JSONL event stream on stdout, and derives the executor-owned observation from
provider events. It deliberately performs exactly one provider turn so usage
and repair accounting cannot be estimated or merged implicitly.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


AGENT_KINDS = {"reference", "shared-prompt", "ui-ir", "agent-packet"}
VALIDATOR_KINDS = {"validation-config"}
REASONING_LEVELS = {"low", "medium", "high", "xhigh"}
PROMPT_ENVIRONMENT_KEYS = (
    "task_mode",
    "screen",
    "state",
    "viewport",
    "scale",
    "appearance",
    "locale",
    "ui_framework",
)
PROVIDER_ENVIRONMENT_KEYS = {
    "PATH",
    "HOME",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "SSH_AUTH_SOCK",
    "CODEX_HOME",
    "OPENAI_API_KEY",
    "CODEX_API_KEY",
    "CODEX_ACCESS_TOKEN",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
}


class ExecutorError(ValueError):
    """The provider execution cannot produce auditable measured evidence."""


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _within(base: Path, candidate: Path) -> Path:
    root = base.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ExecutorError(f"input escapes run directory: {candidate}") from exc
    return resolved


def _required_environment() -> dict[str, str]:
    names = (
        "DCC_EVIDENCE_STATUS",
        "DCC_VARIANT",
        "DCC_MODEL",
        "DCC_REASONING",
        "DCC_WORKTREE",
        "DCC_INPUT_CONTEXT",
        "DCC_CASE_ID",
        "DCC_EXECUTOR_ADAPTER_SHA256",
        "DCC_RUN_OBSERVATION",
        "DCC_EXPECTED_PROVIDER_CLI_VERSION",
        "DCC_EXPECTED_PROVIDER_LAUNCHER_PATH",
        "DCC_EXPECTED_PROVIDER_NATIVE_PATH",
        "DCC_EXPECTED_PROVIDER_LAUNCHER_SHA256",
        "DCC_EXPECTED_PROVIDER_NATIVE_SHA256",
        "DCC_EXPECTED_PROVIDER_PACKAGE_JSON_SHA256",
    )
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        raise ExecutorError(f"missing executor environment: {missing}")
    return {name: os.environ[name] for name in names}


def _load_agent_inputs(context_path: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    context = json.loads(context_path.read_text(encoding="utf-8"))
    if context.get("input_context_version") != "1.2.0":
        raise ExecutorError("unsupported benchmark input context version")
    run_dir = context_path.parent.resolve()
    inputs: dict[str, Path] = {}
    seen_paths: set[str] = set()
    for item in context.get("inputs", []):
        kind = item.get("kind")
        audience = item.get("audience")
        expected_audience = "validator" if kind in VALIDATOR_KINDS else "agent"
        if kind not in AGENT_KINDS | VALIDATOR_KINDS or audience != expected_audience:
            raise ExecutorError(f"invalid input audience: {kind}/{audience}")
        relative = item.get("path")
        if not isinstance(relative, str) or relative in seen_paths:
            raise ExecutorError(f"invalid or duplicate input path: {relative!r}")
        seen_paths.add(relative)
        path = _within(run_dir, run_dir / relative)
        if audience == "agent":
            if not path.is_file() or sha256(path) != item.get("sha256"):
                raise ExecutorError(f"input hash mismatch: {kind}")
            if kind in inputs:
                raise ExecutorError(f"duplicate agent input kind: {kind}")
            inputs[kind] = path
    required = {"reference", "shared-prompt"}
    if not required.issubset(inputs):
        raise ExecutorError(f"missing agent inputs: {sorted(required - set(inputs))}")
    if "ui-ir" in inputs and "agent-packet" in inputs:
        raise ExecutorError("a benchmark variant cannot expose both UI IR and Agent Packet")
    return context, inputs


def _prompt(context: dict[str, Any], inputs: dict[str, Path]) -> str:
    shared = inputs["shared-prompt"].read_text(encoding="utf-8").strip()
    if not shared:
        raise ExecutorError("shared prompt is empty")
    raw_environment = context.get("environment")
    if not isinstance(raw_environment, dict) or set(raw_environment) != set(PROMPT_ENVIRONMENT_KEYS):
        raise ExecutorError("input context environment must use the exact agent-visible key set")
    projected_environment = {key: raw_environment[key] for key in PROMPT_ENVIRONMENT_KEYS}
    environment = json.dumps(projected_environment, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sections = [
        shared,
        "",
        "## Frozen benchmark execution contract",
        f"Case: {context['case_id']}",
        f"Environment: `{environment}`",
        "The visual reference is attached as the initial image.",
        "Only the evidence included below is agent-visible. Do not inspect parent directories, "
        "benchmark metadata, validator configuration, validator code, or hidden comparison inputs.",
        "Work only inside the current Git checkout. Do not commit, move HEAD, modify Git metadata, "
        "or use network access. Implement the task directly, then return the required JSON summary.",
    ]
    if "ui-ir" in inputs:
        sections.extend(
            [
                "",
                "## Agent-visible Canonical UI IR",
                "```json",
                inputs["ui-ir"].read_text(encoding="utf-8").strip(),
                "```",
            ]
        )
    if "agent-packet" in inputs:
        sections.extend(
            [
                "",
                "## Agent-visible UI IR + Binding Agent Packet",
                "```json",
                inputs["agent-packet"].read_text(encoding="utf-8").strip(),
                "```",
            ]
        )
    return "\n".join(sections) + "\n"


def _output_schema() -> dict[str, Any]:
    string_array = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["summary", "changed_files", "reused_components", "unknowns", "validation"],
        "properties": {
            "summary": {"type": "string"},
            "changed_files": string_array,
            "reused_components": string_array,
            "unknowns": string_array,
            "validation": string_array,
        },
    }


def _provider_environment(worktree: Path, *, test_mode: bool = False) -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in PROVIDER_ENVIRONMENT_KEYS
        if key in os.environ
    }
    environment["PWD"] = str(worktree)
    # Prevent read-only Git commands from refreshing the frozen provider index.
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    if test_mode and "FAKE_CAPTURE" in os.environ:
        environment["FAKE_CAPTURE"] = os.environ["FAKE_CAPTURE"]
    return environment


def _canonical_events(stdout: str) -> tuple[bytes, str, dict[str, int]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(stdout.splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ExecutorError(f"Codex emitted non-JSON output at line {line_number}") from exc
        if not isinstance(value, dict):
            raise ExecutorError(f"Codex emitted a non-object event at line {line_number}")
        events.append(value)
    thread_started = [index for index, event in enumerate(events) if event.get("type") == "thread.started"]
    turn_started = [index for index, event in enumerate(events) if event.get("type") == "turn.started"]
    turn_completed = [index for index, event in enumerate(events) if event.get("type") == "turn.completed"]
    completed = [event for event in events if event.get("type") == "turn.completed"]
    failed = [event for event in events if event.get("type") in {"turn.failed", "error"}]
    if (
        failed
        or len(thread_started) != 1
        or len(turn_started) != 1
        or len(turn_completed) != 1
        or not (thread_started[0] < turn_started[0] < turn_completed[0])
        or turn_completed[0] != len(events) - 1
    ):
        raise ExecutorError(
            "Codex event stream must contain one ordered thread.started/turn.started/turn.completed sequence with no failure"
        )
    thread_id = events[thread_started[0]].get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        raise ExecutorError("Codex thread.started is missing thread_id")
    usage = completed[0].get("usage")
    required_usage = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
    if not isinstance(usage, dict) or any(
        not isinstance(usage.get(key), int) or isinstance(usage.get(key), bool) or usage[key] < 0
        for key in required_usage
    ):
        raise ExecutorError("Codex turn.completed is missing non-negative integer usage fields")
    canonical = b"".join(
        (json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for event in events
    )
    return canonical, thread_id, {key: usage[key] for key in required_usage}


def _native_executable(launcher: Path) -> Path:
    resolved = launcher.resolve()
    if resolved.suffix != ".js":
        return resolved
    platform_package = {
        ("Darwin", "arm64"): "codex-darwin-arm64",
        ("Darwin", "x86_64"): "codex-darwin-x64",
    }.get((platform.system(), platform.machine()))
    if platform_package is None:
        raise ExecutorError("unsupported Codex launcher platform for native identity")
    package_root = resolved.parent.parent / "node_modules" / "@openai" / platform_package
    candidates = sorted(package_root.glob("vendor/*/bin/codex"))
    if len(candidates) != 1 or not candidates[0].is_file():
        raise ExecutorError("unable to resolve the unique Codex native executable")
    return candidates[0].resolve()


def _cli_identity(
    executable: Path,
    worktree: Path,
    *,
    test_mode: bool = False,
) -> tuple[str, str, str, str, str, str]:
    launcher = executable.resolve()
    native = _native_executable(launcher)
    if test_mode:
        package_hash = sha256(launcher)
    else:
        if launcher.name != "codex.js" or launcher.parent.name != "bin":
            raise ExecutorError("measured Codex launcher must be the @openai/codex bin/codex.js entrypoint")
        package_json = launcher.parent.parent / "package.json"
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExecutorError("unable to read the @openai/codex package identity") from exc
        if package.get("name") != "@openai/codex" or not isinstance(package.get("version"), str):
            raise ExecutorError("Codex launcher does not belong to an @openai/codex package")
        package_hash = sha256(package_json)
    # The npm launcher uses `#!/usr/bin/env node`; executing it would make PATH
    # an unreceipted interpreter-selection boundary. Invoke the frozen native
    # binary directly for both identity and the measured provider turn.
    identity_executable = launcher if test_mode else native
    result = subprocess.run(
        [str(identity_executable), "--version"],
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
        env=_provider_environment(worktree, test_mode=test_mode),
    )
    version = (result.stdout or result.stderr).strip()
    if result.returncode != 0 or not version:
        raise ExecutorError("unable to capture Codex CLI version")
    if not test_mode and not re.fullmatch(r"codex-cli [0-9]+(?:\.[0-9]+){2}(?:[-+][A-Za-z0-9.-]+)?", version):
        raise ExecutorError(f"unexpected Codex CLI version string: {version}")
    if not test_mode and version != f"codex-cli {package['version']}":
        raise ExecutorError("Codex CLI version does not match its @openai/codex package.json")
    return version, str(launcher), str(native), sha256(launcher), sha256(native), package_hash


def execute() -> dict[str, Any]:
    env = _required_environment()
    test_mode = env["DCC_EVIDENCE_STATUS"] == "synthetic-adapter-test"
    if env["DCC_EVIDENCE_STATUS"] not in {"measured", "synthetic-adapter-test"}:
        raise ExecutorError("Codex executor only accepts measured plans or its isolated synthetic adapter test")
    if env["DCC_REASONING"] not in REASONING_LEVELS:
        raise ExecutorError(f"unsupported Codex reasoning level: {env['DCC_REASONING']}")
    context_path = Path(env["DCC_INPUT_CONTEXT"]).resolve()
    context, inputs = _load_agent_inputs(context_path)
    if context.get("case_id") != env["DCC_CASE_ID"] or context.get("variant") != env["DCC_VARIANT"]:
        raise ExecutorError("input context linkage does not match executor environment")
    worktree = Path(env["DCC_WORKTREE"]).resolve()
    if not (worktree / ".git").exists():
        raise ExecutorError("benchmark worktree is not a Git checkout")
    if not test_mode and "DCC_CODEX_BIN" in os.environ:
        raise ExecutorError("measured execution forbids Codex binary override")
    if test_mode:
        executable_name = os.environ.get("DCC_CODEX_BIN", "codex")
        resolved = shutil.which(executable_name)
        if not resolved:
            raise ExecutorError(f"Codex CLI not found: {executable_name}")
        executable = Path(resolved)
    else:
        expected_launcher = Path(env["DCC_EXPECTED_PROVIDER_LAUNCHER_PATH"])
        if not expected_launcher.is_absolute() or not expected_launcher.is_file():
            raise ExecutorError("frozen measured Codex launcher path must be an existing absolute file")
        executable = expected_launcher
    (
        cli_version,
        launcher_path,
        native_path,
        launcher_hash,
        native_hash,
        package_json_hash,
    ) = _cli_identity(executable, worktree, test_mode=test_mode)
    if not test_mode:
        expected_identity = (
            env["DCC_EXPECTED_PROVIDER_CLI_VERSION"],
            str(Path(env["DCC_EXPECTED_PROVIDER_LAUNCHER_PATH"]).resolve()),
            str(Path(env["DCC_EXPECTED_PROVIDER_NATIVE_PATH"]).resolve()),
            env["DCC_EXPECTED_PROVIDER_LAUNCHER_SHA256"],
            env["DCC_EXPECTED_PROVIDER_NATIVE_SHA256"],
            env["DCC_EXPECTED_PROVIDER_PACKAGE_JSON_SHA256"],
        )
        if (
            cli_version,
            launcher_path,
            native_path,
            launcher_hash,
            native_hash,
            package_json_hash,
        ) != expected_identity:
            raise ExecutorError("actual Codex CLI identity does not match the frozen measured run plan")
    provider_executable = executable.resolve() if test_mode else Path(native_path)

    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(_output_schema(), handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        schema_path = Path(handle.name)
    try:
        command = [
            str(provider_executable),
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--color",
            "never",
            "--sandbox",
            "workspace-write",
            "--cd",
            str(worktree),
            "--model",
            env["DCC_MODEL"],
            "--config",
            f'model_reasoning_effort="{env["DCC_REASONING"]}"',
            "--config",
            'approval_policy="never"',
            "--image",
            str(inputs["reference"]),
            "--output-schema",
            str(schema_path),
            _prompt(context, inputs),
        ]
        context_mode = context_path.stat().st_mode & 0o777
        context_path.chmod(0)
        if context_path.stat().st_mode & 0o777:
            raise ExecutorError("input context did not become unreadable before provider execution")
        try:
            result = subprocess.run(
                command,
                cwd=worktree,
                env=_provider_environment(worktree, test_mode=test_mode),
                stdin=subprocess.DEVNULL,
                text=True,
                capture_output=True,
                timeout=None,
                check=False,
            )
        finally:
            context_path.chmod(context_mode)
            if (context_path.stat().st_mode & 0o777) != context_mode:
                raise ExecutorError("input context mode was not restored after provider execution")
    finally:
        schema_path.unlink(missing_ok=True)
    if result.returncode != 0:
        detail = result.stderr.strip()[-2000:]
        raise ExecutorError(f"Codex CLI failed with exit {result.returncode}: {detail}")
    canonical, thread_id, usage = _canonical_events(result.stdout)
    sys.stdout.buffer.write(canonical)
    sys.stdout.buffer.flush()
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    observation = {
        "run_observation_version": "1.1.0",
        "case_id": env["DCC_CASE_ID"],
        "variant": env["DCC_VARIANT"],
        "executor_adapter_sha256": env["DCC_EXECUTOR_ADAPTER_SHA256"],
        "model": env["DCC_MODEL"],
        "reasoning": env["DCC_REASONING"],
        "provider_cli": {
            "name": "synthetic-test-adapter" if test_mode else "openai-codex-cli",
            "version": cli_version,
            "launcher_path": launcher_path,
            "native_path": native_path,
            "launcher_sha256": launcher_hash,
            "native_sha256": native_hash,
            "package_json_sha256": package_json_hash,
        },
        "provider_event_stream_sha256": sha256_bytes(canonical),
        "provider_runs": [{"id": thread_id, **usage}],
        "repair_events": [],
        "manual_interventions": [],
    }
    observation_path = Path(env["DCC_RUN_OBSERVATION"])
    observation_path.write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return observation


def main() -> int:
    try:
        execute()
    except (ExecutorError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
