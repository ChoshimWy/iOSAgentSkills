#!/usr/bin/env python3
"""Run three isolated Design Context benchmark variants from one pinned Git commit."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
from typing import Any
import zlib

from prepare_benchmark_case import PreparationError, prepare
from score_benchmark import score
from validate_contract import load_json, validate


VARIANTS = {"screenshot-only", "ui-ir", "ui-ir-with-binding"}
INPUT_AUDIENCE = {
    "reference": "agent",
    "shared-prompt": "agent",
    "validation-config": "validator",
    "ui-ir": "agent",
    "agent-packet": "agent",
}
INHERITED_ENV = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "SSH_AUTH_SOCK", "CODEX_HOME")


class RunnerError(ValueError):
    """The benchmark runner cannot produce trustworthy evidence."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _within(base: Path, candidate: Path) -> Path:
    root = base.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RunnerError(f"path escapes its declared root: {candidate}") from exc
    return resolved


def _resolve_evidence(base: Path, evidence: dict[str, Any], label: str) -> Path:
    value = Path(evidence["path"])
    path = value.resolve() if value.is_absolute() else _within(base, base / value)
    if not path.is_file():
        raise RunnerError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual != evidence["sha256"]:
        raise RunnerError(f"{label} hash mismatch: expected {evidence['sha256']}, got {actual}")
    return path


def _validate_json(path: Path, kind: str) -> dict[str, Any]:
    data = load_json(path)
    _, diagnostics, blocking = validate(data, kind)
    if diagnostics:
        raise RunnerError(f"invalid {kind}: {[item.as_dict() for item in diagnostics]}")
    if blocking:
        raise RunnerError(f"blocked {kind}: {blocking}")
    return data


def _run_git(args: list[str], cwd: Path | None = None, *, text: bool = True) -> subprocess.CompletedProcess:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(["git", *args], cwd=cwd, env=environment, capture_output=True, text=text, check=False)


def _create_checkout(source_root: Path, commit: str, destination: Path, *, strategy: str) -> None:
    if destination.exists():
        raise RunnerError(f"checkout destination already exists: {destination}")
    if strategy == "git-shared-clone":
        clone = _run_git(["clone", "--shared", "--no-checkout", "--quiet", str(source_root), str(destination)])
        if clone.returncode != 0:
            raise RunnerError(f"git clone failed: {clone.stderr.strip()}")
    elif strategy == "git-pinned-tree-slice":
        destination.mkdir()
        initialized = _run_git(["init", "--quiet"], cwd=destination)
        if initialized.returncode != 0:
            raise RunnerError(f"git init failed: {initialized.stderr.strip()}")
        with tempfile.TemporaryFile() as pack_file:
            packed = subprocess.run(
                ["git", "pack-objects", "--stdout", "--revs"],
                cwd=source_root,
                input=f"{commit}^{{tree}}\n".encode("utf-8"),
                stdout=pack_file,
                stderr=subprocess.PIPE,
                check=False,
            )
            if packed.returncode != 0:
                raise RunnerError(f"unable to pack pinned tree closure: {packed.stderr.decode(errors='replace').strip()}")
            pack_file.seek(0)
            indexed = subprocess.run(
                ["git", "index-pack", "--stdin"],
                cwd=destination,
                stdin=pack_file,
                capture_output=True,
                check=False,
            )
            if indexed.returncode != 0:
                raise RunnerError(f"unable to import pinned tree closure: {indexed.stderr.decode(errors='replace').strip()}")
        commit_object = _run_git(["cat-file", "commit", commit], cwd=source_root, text=False)
        if commit_object.returncode != 0:
            raise RunnerError(f"unable to read pinned commit object: {commit}")
        imported_commit = subprocess.run(
            ["git", "hash-object", "-w", "-t", "commit", "--stdin"],
            cwd=destination,
            input=commit_object.stdout,
            capture_output=True,
            check=False,
        )
        if imported_commit.returncode != 0 or imported_commit.stdout.decode().strip() != commit:
            raise RunnerError("unable to import the exact pinned commit object")
    else:
        raise RunnerError(f"unsupported checkout isolation strategy: {strategy}")
    checkout = _run_git(["checkout", "--detach", "--quiet", commit], cwd=destination)
    if checkout.returncode != 0:
        raise RunnerError(f"git checkout failed: {checkout.stderr.strip()}")
    head = _run_git(["rev-parse", "HEAD"], cwd=destination)
    if head.returncode != 0 or head.stdout.strip() != commit:
        raise RunnerError(f"isolated checkout did not resolve pinned commit: {destination}")
    status = _run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=destination)
    if status.returncode != 0 or status.stdout:
        raise RunnerError(f"isolated checkout is not clean: {destination}: {status.stdout.strip()}")
    if strategy == "git-pinned-tree-slice":
        _verify_pinned_tree_slice(destination, commit)


def _git_blob_sha1(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()


def _scope_allows_path(relative: str, scope_entries: list[dict[str, str]]) -> bool:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or relative != path.as_posix():
        return False
    for entry in scope_entries:
        value = entry["path"].rstrip("/")
        if (entry["kind"] == "file" and relative == value) or (
            entry["kind"] == "directory" and relative.startswith(value + "/")
        ):
            return True
    return False


def _scope_allows_directory(relative: str, scope_entries: list[dict[str, str]]) -> bool:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or relative != path.as_posix():
        return False
    for entry in scope_entries:
        value = entry["path"].rstrip("/")
        if value.startswith(relative + "/"):
            return True
        if entry["kind"] == "directory" and (relative == value or relative.startswith(value + "/")):
            return True
    return False


def _canonical_string_set_sha256(values: set[str]) -> str:
    canonical = json.dumps(sorted(values), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _provider_git_metadata_sha256(worktree: Path) -> str:
    git_dir = worktree / ".git"
    if not git_dir.is_dir() or git_dir.is_symlink():
        raise RunnerError("provider worktree .git metadata is missing or invalid")
    entries: list[dict[str, Any]] = []
    for path in sorted(git_dir.rglob("*")):
        if path.is_symlink():
            raise RunnerError(f"provider worktree Git metadata contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(git_dir).as_posix()
        entries.append(
            {
                "path": relative,
                "mode": stat.S_IMODE(path.stat().st_mode),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    canonical = json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _verify_provider_worktree_files(worktree: Path, scope_entries: list[dict[str, str]]) -> None:
    root = worktree.resolve()
    invalid: list[str] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        if current_path == root and ".git" in directories:
            directories.remove(".git")
        for name in list(directories):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or not _scope_allows_directory(relative, scope_entries):
                invalid.append(relative + "/")
                directories.remove(name)
        for name in files:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode) or not _scope_allows_path(relative, scope_entries):
                invalid.append(relative)
    if invalid:
        raise RunnerError(f"provider worktree contains paths outside frozen source scope: {sorted(invalid)}")


def _git_tree_manifest(worktree: Path, commit: str) -> list[dict[str, Any]]:
    result = _run_git(["ls-tree", "-r", "-l", "-z", commit], cwd=worktree, text=False)
    if result.returncode != 0:
        raise RunnerError("unable to enumerate provider worktree baseline tree")
    files: list[dict[str, Any]] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, object_type, object_id, raw_size = header.decode("ascii").split()
        if object_type != "blob" or mode not in {"100644", "100755"} or raw_size == "-":
            raise RunnerError("provider worktree baseline contains unsupported Git entries")
        files.append(
            {
                "path": raw_path.decode("utf-8", errors="strict"),
                "git_mode": mode,
                "blob_sha1": object_id,
                "bytes": int(raw_size),
            }
        )
    return sorted(files, key=lambda item: item["path"])


def _create_provider_worktree(
    checkout: Path,
    destination: Path,
    manifest: dict[str, Any],
) -> tuple[str, set[str], str, str]:
    if destination.exists():
        raise RunnerError(f"provider worktree already exists: {destination}")
    destination.mkdir()
    expected_paths: set[str] = set()
    for item in manifest["files"]:
        relative = item["path"]
        if relative in expected_paths or not _scope_allows_path(relative, manifest["scope_entries"]):
            raise RunnerError(f"provider source manifest contains an invalid path: {relative}")
        source = _within(checkout, checkout / relative)
        if not source.is_file() or source.stat().st_size != item["bytes"] or _git_blob_sha1(source) != item["blob_sha1"]:
            raise RunnerError(f"provider source manifest does not match pinned checkout: {relative}")
        target = _within(destination, destination / relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        target.chmod(0o755 if item["git_mode"] == "100755" else 0o644)
        expected_paths.add(relative)
    actual_paths = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise RunnerError("provider worktree file set does not match frozen source manifest")
    initialized = _run_git(["init", "--quiet"], cwd=destination)
    added = _run_git(["add", "--all"], cwd=destination)
    if initialized.returncode != 0 or added.returncode != 0:
        raise RunnerError("unable to initialize provider source worktree")
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Design Context Benchmark",
            "GIT_AUTHOR_EMAIL": "benchmark@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_NAME": "Design Context Benchmark",
            "GIT_COMMITTER_EMAIL": "benchmark@example.invalid",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
    )
    committed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "--quiet", "-m", "provider source baseline"],
        cwd=destination,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if committed.returncode != 0:
        raise RunnerError(f"unable to commit provider source baseline: {committed.stderr.strip()}")
    baseline = _run_git(["rev-parse", "HEAD"], cwd=destination)
    if baseline.returncode != 0:
        raise RunnerError("unable to resolve provider source baseline")
    baseline_commit = baseline.stdout.strip()
    detached = _run_git(["checkout", "--detach", "--quiet", baseline_commit], cwd=destination)
    branch = _run_git(["symbolic-ref", "--short", "-q", "HEAD"], cwd=destination)
    if detached.returncode != 0 or branch.stdout.strip():
        raise RunnerError("provider source baseline must use detached HEAD")
    for ref in _run_git(["for-each-ref", "--format=%(refname)"], cwd=destination).stdout.splitlines():
        deleted = _run_git(["update-ref", "-d", ref], cwd=destination)
        if deleted.returncode != 0:
            raise RunnerError(f"unable to remove provider source ref: {ref}")
    config_hash = sha256(destination / ".git/config")
    metadata_hash = _provider_git_metadata_sha256(destination)
    baseline_objects = _git_object_ids(destination)
    if _git_tree_manifest(destination, baseline_commit) != manifest["files"]:
        raise RunnerError("provider source baseline tree does not match frozen manifest")
    _verify_provider_worktree_files(destination, manifest["scope_entries"])
    return baseline_commit, baseline_objects, config_hash, metadata_hash


def _verify_provider_worktree_git(
    worktree: Path,
    baseline_commit: str,
    baseline_objects: set[str],
    config_hash: str,
    metadata_hash: str,
    manifest: dict[str, Any],
) -> None:
    head = _run_git(["rev-parse", "HEAD"], cwd=worktree)
    refs = _run_git(["for-each-ref", "--format=%(refname)"], cwd=worktree)
    remotes = _run_git(["remote"], cwd=worktree)
    if head.returncode != 0 or head.stdout.strip() != baseline_commit:
        raise RunnerError("provider changed minimal worktree HEAD")
    if refs.returncode != 0 or refs.stdout.strip() or remotes.returncode != 0 or remotes.stdout.strip():
        raise RunnerError("provider changed minimal worktree refs or remotes")
    if (worktree / ".git/objects/info/alternates").exists() or _git_object_ids(worktree) != baseline_objects:
        raise RunnerError("provider changed minimal worktree Git object boundary")
    if sha256(worktree / ".git/config") != config_hash:
        raise RunnerError("provider changed minimal worktree Git configuration")
    if _provider_git_metadata_sha256(worktree) != metadata_hash:
        raise RunnerError("provider changed minimal worktree Git metadata")
    if _git_tree_manifest(worktree, baseline_commit) != manifest["files"]:
        raise RunnerError("provider changed minimal worktree baseline tree")
    _verify_provider_worktree_files(worktree, manifest["scope_entries"])


def _git_object_ids(checkout: Path) -> set[str]:
    result = _run_git(["cat-file", "--batch-all-objects", "--batch-check=%(objectname)"], cwd=checkout)
    if result.returncode != 0:
        raise RunnerError(f"unable to enumerate checkout objects: {checkout}")
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _pinned_tree_object_ids(checkout: Path, commit: str) -> set[str]:
    result = _run_git(["rev-list", "--objects", "--no-object-names", f"{commit}^{{tree}}"], cwd=checkout)
    if result.returncode != 0:
        raise RunnerError(f"unable to enumerate pinned tree closure: {checkout}")
    return {commit, *[line.strip() for line in result.stdout.splitlines() if line.strip()]}


def _verify_pinned_tree_slice(checkout: Path, commit: str) -> None:
    if (checkout / ".git" / "objects" / "info" / "alternates").exists():
        raise RunnerError(f"pinned tree slice unexpectedly depends on alternate objects: {checkout}")
    refs = _run_git(["for-each-ref", "--format=%(refname)"], cwd=checkout)
    remotes = _run_git(["remote"], cwd=checkout)
    if refs.returncode != 0 or refs.stdout.strip() or remotes.returncode != 0 or remotes.stdout.strip():
        raise RunnerError(f"pinned tree slice contains refs or remotes: {checkout}")
    actual = _git_object_ids(checkout)
    expected = _pinned_tree_object_ids(checkout, commit)
    if actual != expected:
        raise RunnerError(f"pinned tree slice object set mismatch: {sorted(actual ^ expected)[:20]}")


def _expand_command(command: list[str], values: dict[str, str]) -> list[str]:
    expanded: list[str] = []
    for argument in command:
        value = argument
        for key, replacement in values.items():
            value = value.replace("{" + key + "}", replacement)
        if "{" in value or "}" in value:
            raise RunnerError(f"unknown or unmatched command placeholder: {argument}")
        expanded.append(value)
    return expanded


def _command_environment(
    plan: dict[str, Any],
    configuration: dict[str, Any],
    values: dict[str, str],
    role: str,
) -> dict[str, str]:
    environment = {key: os.environ[key] for key in INHERITED_ENV if key in os.environ}
    environment.update(configuration["environment"])
    environment.update(
        {
            "GIT_OPTIONAL_LOCKS": "0",
            "DCC_EVIDENCE_STATUS": plan["evidence_status"],
            "DCC_VARIANT": values["variant"],
            "DCC_MODEL": values["model"],
            "DCC_REASONING": values["reasoning"],
            "DCC_WORKTREE": values["worktree"],
            "DCC_INPUT_DIR": values["input_dir"],
            "DCC_INPUT_CONTEXT": values["input_context"],
            "DCC_CODE_BASELINE_COMMIT": values["code_baseline_commit"],
            "DCC_REFERENCE_SHA256": values["reference_sha256"],
            "DCC_CASE_ID": values["case_id"],
            "DCC_EXECUTOR_ADAPTER_SHA256": values["executor_adapter_sha256"],
            "DCC_RUN_OBSERVATION": values["run_observation"],
            "DCC_EXPECTED_PROVIDER_CLI_VERSION": plan["executor"]["provider_cli"]["version"],
            "DCC_EXPECTED_PROVIDER_LAUNCHER_PATH": plan["executor"]["provider_cli"]["launcher_path"],
            "DCC_EXPECTED_PROVIDER_NATIVE_PATH": plan["executor"]["provider_cli"]["native_path"],
            "DCC_EXPECTED_PROVIDER_LAUNCHER_SHA256": plan["executor"]["provider_cli"]["launcher_sha256"],
            "DCC_EXPECTED_PROVIDER_NATIVE_SHA256": plan["executor"]["provider_cli"]["native_sha256"],
            "DCC_EXPECTED_PROVIDER_PACKAGE_JSON_SHA256": plan["executor"]["provider_cli"]["package_json_sha256"],
        }
    )
    if role in {"capture", "validator"}:
        environment.update(
            {
                "DCC_RUN_DIR": values["run_dir"],
                "DCC_RUN_RESULT": values["run_result"],
                "DCC_VALIDATOR_ID": values["validator_id"],
                "DCC_CAPTURE_ADAPTER_SHA256": values["capture_adapter_sha256"],
                "DCC_VALIDATOR_ADAPTER_SHA256": values["validator_adapter_sha256"],
                "DCC_ACTUAL_SCREENSHOT": values["actual_screenshot"],
                "DCC_VALIDATOR_PROBE": values["validator_probe"],
                "DCC_CAPTURE_RUNTIME_JSON": values["capture_runtime_json"],
            }
        )
    return environment


def _phase_files(run_dir: Path) -> set[str]:
    files: set[str] = set()
    for path in run_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(run_dir)
        if relative.parts[0] in {"checkout", "provider-worktree", "input"}:
            continue
        files.add(relative.as_posix())
    return files


def _require_exact_phase_files(run_dir: Path, expected: set[str], phase: str) -> None:
    actual = _phase_files(run_dir)
    if actual != expected:
        raise RunnerError(f"{phase} produced unexpected run files: {sorted(actual ^ expected)}")


def _restore_hidden_paths(modes: dict[Path, int]) -> None:
    errors: list[str] = []
    for path, mode in reversed(list(modes.items())):
        try:
            path.chmod(mode)
            if stat.S_IMODE(path.stat().st_mode) != mode:
                errors.append(f"mode verification failed: {path}")
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        raise RunnerError(f"unable to restore executor-hidden paths: {errors}")


def _restore_executor_isolation(
    hidden_modes: dict[Path, int],
    input_context_path: Path,
    input_context_mode: int,
) -> None:
    errors: list[str] = []
    try:
        if stat.S_IMODE(input_context_path.stat().st_mode) != input_context_mode:
            input_context_path.chmod(input_context_mode)
        if stat.S_IMODE(input_context_path.stat().st_mode) != input_context_mode:
            errors.append(f"input context mode verification failed: {input_context_path}")
    except OSError as exc:
        errors.append(f"{input_context_path}: {exc}")
    try:
        _restore_hidden_paths(hidden_modes)
    except RunnerError as exc:
        errors.append(str(exc))
    if errors:
        raise RunnerError(f"unable to restore measured executor isolation: {errors}")


def _shield_paths(paths: list[Path]) -> dict[Path, int]:
    resolved_paths: list[Path] = []
    for raw_path in paths:
        path = raw_path.resolve()
        if not path.exists():
            raise RunnerError(f"executor-hidden path is missing: {path}")
        resolved_paths.append(path)
    minimal_paths: list[Path] = []
    for path in sorted(set(resolved_paths), key=lambda item: (len(item.parts), str(item))):
        if any(parent.is_dir() and _is_within(path, parent) for parent in minimal_paths):
            continue
        minimal_paths.append(path)
    modes: dict[Path, int] = {}
    try:
        for path in minimal_paths:
            modes[path] = stat.S_IMODE(path.stat().st_mode)
            path.chmod(0)
            if stat.S_IMODE(path.stat().st_mode) != 0:
                raise RunnerError(f"executor-hidden path did not become unreadable: {path}")
    except Exception:
        _restore_hidden_paths(modes)
        raise
    return modes


def _shield_current_run(run_dir: Path, input_context: dict[str, Any]) -> list[Path]:
    """Return current-run evaluator paths that must be unreadable to the model."""
    paths = [
        run_dir / "run-plan.json",
        run_dir / "benchmark-case.json",
        run_dir / "capture-adapter",
        run_dir / "validator-adapter",
    ]
    dependency_setup = input_context.get("evaluator_dependency_setup")
    if isinstance(dependency_setup, dict) and dependency_setup.get("mode") != "none":
        paths.append(run_dir / dependency_setup["artifact"]["path"])
    provider_scope = input_context.get("provider_source_scope")
    if isinstance(provider_scope, dict) and provider_scope.get("mode") == "allowlist":
        paths.append(run_dir / provider_scope["artifact"]["path"])
    paths.extend(
        _within(run_dir, run_dir / item["path"])
        for item in input_context["inputs"]
        if item.get("audience") == "validator"
    )
    return paths


def _verify_provider_event_stream(observation: dict[str, Any], stdout_path: Path) -> None:
    expected = observation.get("provider_event_stream_sha256")
    actual = sha256(stdout_path)
    if expected != actual:
        raise RunnerError(
            f"provider event stream hash mismatch: observation has {expected}, implementation stdout has {actual}"
        )


def _execute(
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: int,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    started = datetime.now(timezone.utc)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        stdout_path.write_text(stdout or "", encoding="utf-8")
        stderr_path.write_text(stderr or "", encoding="utf-8")
        raise RunnerError(f"executor timed out after {timeout_seconds}s: {command[0]}") from exc
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    if process.returncode != 0:
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        raise RunnerError(f"executor failed with exit {process.returncode} after {elapsed:.3f}s: {command[0]}")


def _execute_with_isolation(
    command: list[str],
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: int,
    stdout_path: Path,
    stderr_path: Path,
    hidden_paths: list[Path],
    input_context_path: Path,
) -> None:
    """Execute one provider process while guaranteeing all chmod guards are restored."""
    input_context_mode = stat.S_IMODE(input_context_path.stat().st_mode)
    shielded_modes: dict[Path, int] = {}
    try:
        shielded_modes = _shield_paths(hidden_paths) if hidden_paths else {}
        _execute(command, cwd, environment, timeout_seconds, stdout_path, stderr_path)
    finally:
        _restore_executor_isolation(shielded_modes, input_context_path, input_context_mode)


def _verify_pinned_head(checkout: Path, commit: str, phase: str) -> None:
    head = _run_git(["rev-parse", "HEAD"], cwd=checkout)
    if head.returncode != 0 or head.stdout.strip() != commit:
        raise RunnerError(f"{phase} changed checkout HEAD away from pinned commit: {checkout}")


def _capture_patch(checkout: Path, baseline_commit: str, output: Path) -> tuple[str, list[str]]:
    # Full object IDs keep the evidence byte-stable across the minimal provider
    # repository and the complete evaluator checkout. Git otherwise chooses an
    # abbreviation length from each repository's object population.
    tracked = _run_git(
        [
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--full-index",
            "--binary",
            baseline_commit,
            "--",
        ],
        cwd=checkout,
        text=False,
    )
    if tracked.returncode != 0:
        raise RunnerError(f"unable to capture tracked diff: {tracked.stderr.decode(errors='replace').strip()}")
    untracked_result = _run_git(["ls-files", "--others", "--exclude-standard", "-z"], cwd=checkout, text=False)
    if untracked_result.returncode != 0:
        raise RunnerError("unable to enumerate untracked implementation files")
    untracked = sorted(item.decode("utf-8") for item in untracked_result.stdout.split(b"\0") if item)
    content = bytearray(tracked.stdout)
    for relative in untracked:
        path = _within(checkout, checkout / relative)
        if not path.is_file():
            raise RunnerError(f"untracked implementation output is not a regular file: {relative}")
        diff = _run_git(
            [
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--no-renames",
                "--full-index",
                "--no-index",
                "--binary",
                "--",
                "/dev/null",
                relative,
            ],
            cwd=checkout,
            text=False,
        )
        if diff.returncode not in (0, 1):
            raise RunnerError(f"unable to capture untracked file: {relative}")
        content.extend(diff.stdout)
    output.write_bytes(bytes(content))
    status = _run_git(["status", "--porcelain=v1", "--untracked-files=all"], cwd=checkout)
    if status.returncode != 0:
        raise RunnerError("unable to capture implementation status")
    changed = [line[3:] for line in status.stdout.splitlines() if len(line) >= 4]
    return sha256(output), changed


def _apply_capture_overlay(checkout: Path, overlay: Path, reverse: bool = False) -> None:
    action = "remove" if reverse else "apply"
    arguments = ["apply", "--check", "--binary", "--whitespace=nowarn"]
    if reverse:
        arguments.append("--reverse")
    arguments.extend(["--", str(overlay)])
    check = _run_git(arguments, cwd=checkout)
    if check.returncode != 0:
        raise RunnerError(f"unable to {action} capture overlay: {check.stderr.strip()}")
    arguments.remove("--check")
    applied = _run_git(arguments, cwd=checkout)
    if applied.returncode != 0:
        raise RunnerError(f"unable to {action} capture overlay: {applied.stderr.strip()}")


def _force_restore_implementation_checkout(
    checkout: Path,
    baseline_commit: str,
    implementation_patch: Path,
) -> None:
    reset = _run_git(["reset", "--hard", baseline_commit], cwd=checkout)
    clean = _run_git(["clean", "-fdx"], cwd=checkout)
    if reset.returncode != 0 or clean.returncode != 0:
        raise RunnerError(
            "capture overlay fallback could not reset the isolated checkout: "
            f"{reset.stderr.strip()} {clean.stderr.strip()}"
        )
    if implementation_patch.stat().st_size == 0:
        return
    restored = _run_git(
        ["apply", "--binary", "--whitespace=nowarn", "--", str(implementation_patch)],
        cwd=checkout,
    )
    if restored.returncode != 0:
        raise RunnerError(
            "capture overlay fallback could not restore implementation patch: "
            f"{restored.stderr.strip()}"
        )


def _verify_prepared_variant(
    prepared_dir: Path,
    case: dict[str, Any],
    case_path: Path,
    plan_path: Path,
    adapter_path: Path,
    capture_path: Path,
    overlay_path: Path | None,
    overlay_hash: str | None,
    dependency_generator_path: Path | None,
    dependency_generator_hash: str | None,
    dependency_setup_mode: str,
    validator_path: Path,
    provider_source_manifest_path: Path | None,
    provider_source_scope: dict[str, Any],
    provider_baseline_commit: str | None,
    provider_baseline_objects: set[str] | None,
    provider_git_metadata_hash: str | None,
    plan_hash: str,
    variant: str,
    run_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    source_dir = _within(prepared_dir, prepared_dir / "variants" / variant)
    source_manifest = source_dir / "input-manifest.json"
    if not source_manifest.is_file():
        raise RunnerError(f"prepared input manifest is missing: {source_manifest}")
    manifest = load_json(source_manifest)
    if manifest.get("case_id") != case["case_id"] or manifest.get("variant") != variant:
        raise RunnerError(f"prepared input manifest linkage mismatch: {variant}")
    expected_files = {"input-manifest.json", *[item["path"] for item in manifest.get("inputs", [])]}
    actual_files = {path.name for path in source_dir.iterdir() if path.is_file()}
    if actual_files != expected_files or any(path.is_dir() for path in source_dir.iterdir()):
        raise RunnerError(f"prepared variant contains unexpected files: {variant}: {sorted(actual_files ^ expected_files)}")
    input_dir = run_dir / "input"
    input_dir.mkdir()
    copied_inputs = []
    for item in manifest["inputs"]:
        source = _within(source_dir, source_dir / item["path"])
        if not source.is_file() or sha256(source) != item["sha256"]:
            raise RunnerError(f"prepared input hash mismatch: {variant}/{item['path']}")
        destination = _within(input_dir, input_dir / Path(item["path"]).name)
        shutil.copyfile(source, destination)
        expected_audience = INPUT_AUDIENCE[item["kind"]]
        if item.get("audience") != expected_audience:
            raise RunnerError(
                f"prepared input audience mismatch: {variant}/{item['kind']}: "
                f"expected {expected_audience}, got {item.get('audience')}"
            )
        copied_inputs.append(
            {
                "kind": item["kind"],
                "audience": expected_audience,
                "path": f"input/{destination.name}",
                "sha256": sha256(destination),
            }
        )
    input_context = {
        "input_context_version": "1.2.0",
        "case_id": case["case_id"],
        "variant": variant,
        "plan_sha256": plan_hash,
        "run_plan": {"path": "run-plan.json", "sha256": plan_hash},
        "benchmark_case": {"path": "benchmark-case.json", "sha256": sha256(case_path)},
        "executor_adapter": {"path": "executor-adapter", "sha256": sha256(adapter_path)},
        "capture_adapter": {"path": "capture-adapter", "sha256": sha256(capture_path)},
        "capture_overlay": {"mode": "none"},
        "provider_source_scope": {"mode": "full-tree"},
        "evaluator_dependency_setup": {"mode": "none"},
        "validator_adapter": {"path": "validator-adapter", "sha256": sha256(validator_path)},
        "environment": manifest["environment"],
        "inputs": copied_inputs,
    }
    shutil.copyfile(plan_path, run_dir / "run-plan.json")
    shutil.copyfile(case_path, run_dir / "benchmark-case.json")
    shutil.copyfile(adapter_path, run_dir / "executor-adapter")
    shutil.copyfile(capture_path, run_dir / "capture-adapter")
    if provider_source_manifest_path is not None:
        if provider_baseline_commit is None or provider_baseline_objects is None or provider_git_metadata_hash is None:
            raise RunnerError("provider source allowlist is missing its frozen worktree identity")
        archived_scope = run_dir / "provider-source-manifest.json"
        shutil.copyfile(provider_source_manifest_path, archived_scope)
        input_context["provider_source_scope"] = {
            "mode": "allowlist",
            "artifact": {"path": archived_scope.name, "sha256": sha256(archived_scope)},
            "file_count": provider_source_scope["file_count"],
            "total_bytes": provider_source_scope["total_bytes"],
            "content_sha256": provider_source_scope["content_sha256"],
            "worktree": {
                "path": "provider-worktree",
                "baseline_commit": provider_baseline_commit,
                "object_set_sha256": _canonical_string_set_sha256(provider_baseline_objects),
                "git_metadata_sha256": provider_git_metadata_hash,
            },
        }
    if dependency_generator_path is not None:
        archived_generator = run_dir / "evaluator-dependency-generator"
        shutil.copyfile(dependency_generator_path, archived_generator)
        if sha256(archived_generator) != dependency_generator_hash:
            raise RunnerError("archived evaluator dependency generator hash mismatch")
        input_context["evaluator_dependency_setup"] = {
            "mode": dependency_setup_mode,
            "artifact": {"path": archived_generator.name, "sha256": dependency_generator_hash},
        }
    if overlay_path is not None:
        input_context["capture_overlay"] = {
            "mode": "git-patch",
            "artifact": {
                "path": "capture-overlay.patch",
                "sha256": overlay_hash,
            },
        }
    shutil.copyfile(validator_path, run_dir / "validator-adapter")
    input_context_path = run_dir / "input-context.json"
    input_context_path.write_text(json.dumps(input_context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _validate_json(input_context_path, "benchmark-input-context")
    return input_context_path, input_context


def _verify_frozen_inputs(
    run_dir: Path,
    input_context_path: Path,
    expected_context_hash: str,
    input_context: dict[str, Any],
    include_capture_overlay: bool = True,
) -> None:
    if sha256(input_context_path) != expected_context_hash:
        raise RunnerError("input context changed during benchmark execution")
    evidence_items = [
        ("run plan", input_context["run_plan"]),
        ("benchmark case", input_context["benchmark_case"]),
        ("executor adapter", input_context["executor_adapter"]),
        ("capture adapter", input_context["capture_adapter"]),
        ("validator adapter", input_context["validator_adapter"]),
        *((f"variant input {item['kind']}", item) for item in input_context["inputs"]),
    ]
    dependency_setup = input_context.get("evaluator_dependency_setup")
    if isinstance(dependency_setup, dict) and dependency_setup.get("mode") != "none":
        evidence_items.append(("evaluator dependency generator", dependency_setup["artifact"]))
    provider_scope = input_context.get("provider_source_scope")
    if isinstance(provider_scope, dict) and provider_scope.get("mode") == "allowlist":
        evidence_items.append(("provider source manifest", provider_scope["artifact"]))
    capture_overlay = input_context.get("capture_overlay")
    if include_capture_overlay and isinstance(capture_overlay, dict) and capture_overlay.get("mode") == "git-patch":
        evidence_items.append(("capture overlay", capture_overlay["artifact"]))
    expected_input_files = {item["path"] for item in input_context["inputs"]}
    actual_input_files = {
        path.relative_to(run_dir).as_posix()
        for path in (run_dir / "input").rglob("*")
        if path.is_file()
    }
    if actual_input_files != expected_input_files:
        raise RunnerError(f"variant input file set changed during benchmark execution: {sorted(actual_input_files ^ expected_input_files)}")
    if any(path.is_dir() for path in (run_dir / "input").iterdir()):
        raise RunnerError("variant input directory contains unexpected nested directories")
    for label, evidence in evidence_items:
        if Path(evidence["path"]).is_absolute():
            raise RunnerError(f"{label} must use a relative evidence path")
        _resolve_evidence(run_dir, evidence, label)


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RunnerError(f"measured screenshot is not a valid PNG: {path}")
    offset = 8
    size: tuple[int, int] | None = None
    has_idat = False
    has_iend = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise RunnerError(f"measured screenshot contains a truncated PNG chunk: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise RunnerError(f"measured screenshot contains a truncated PNG chunk: {path}")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise RunnerError(f"measured screenshot contains an invalid PNG CRC: {path}")
        if chunk_type == b"IHDR":
            if offset != 8 or length != 13:
                raise RunnerError(f"measured screenshot contains an invalid PNG IHDR: {path}")
            size = struct.unpack(">II", chunk_data[:8])
        elif chunk_type == b"IDAT":
            has_idat = True
        elif chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                raise RunnerError(f"measured screenshot contains an invalid PNG IEND: {path}")
            has_iend = True
            break
        offset = chunk_end
    if size is None or not has_idat or not has_iend:
        raise RunnerError(f"measured screenshot is not a complete PNG: {path}")
    return size


def _verify_capture_outputs(
    run_dir: Path,
    probe: dict[str, Any],
    plan: dict[str, Any],
    input_context: dict[str, Any],
) -> None:
    actual_path = run_dir / "actual.png"
    probe_path = run_dir / "validator-probe.json"
    if not actual_path.is_file() or not probe_path.is_file():
        raise RunnerError("capture adapter must produce actual.png and validator-probe.json")
    environment = input_context["environment"]
    if _png_size(actual_path) != (
        environment["viewport"]["width"],
        environment["viewport"]["height"],
    ):
        raise RunnerError("capture screenshot viewport does not match the frozen input context")
    expected = {
        "case_id": input_context["case_id"],
        "variant": input_context["variant"],
        "validator_id": plan["validator"]["id"],
        "capture_adapter_sha256": input_context["capture_adapter"]["sha256"],
        "environment": {
            "viewport": environment["viewport"],
            "scale": environment["scale"],
            "appearance": environment["appearance"],
            "locale": environment["locale"],
        },
        "actual_screenshot": {"path": "actual.png", "sha256": sha256(actual_path)},
    }
    for key, value in expected.items():
        if probe.get(key) != value:
            raise RunnerError(f"validator probe linkage mismatch: {key}")
    validation_item = next(item for item in input_context["inputs"] if item["kind"] == "validation-config")
    validation = _validate_json(run_dir / validation_item["path"], "benchmark-validation-config")
    if [item["id"] for item in probe["regions"]] != validation["required_regions"]:
        raise RunnerError("validator probe region coverage does not match the frozen validation config")
    required_bindings = {
        item["id"]: {
            "id": item["id"],
            "region_id": item["region_id"],
            "runtime_type": item["runtime_type"],
        }
        for item in validation["required_bindings"]
    }
    for binding in probe["bindings"]:
        if required_bindings.get(binding["id"]) != binding:
            raise RunnerError(f"validator probe contains an unfrozen runtime binding: {binding['id']}")


def _verify_run_result(
    result_path: Path,
    result: dict[str, Any],
    plan: dict[str, Any],
    case: dict[str, Any],
    input_context: dict[str, Any],
) -> None:
    environment = case["benchmark"]["environment"]
    reference = next(item for item in input_context["inputs"] if item["kind"] == "reference")
    expected = {
        "variant": input_context["variant"],
        "model": plan["executor"]["model"],
        "reasoning": plan["executor"]["reasoning"],
        "code_baseline_commit": case["source"]["code"]["git_commit"],
        "reference_sha256": reference["sha256"],
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise RunnerError(f"run result linkage mismatch: {key}")
    observation = result["evidence"]["run_observation"]
    if observation["path"] != "run-observation.json":
        raise RunnerError("run result must reference the frozen executor-owned run-observation.json")
    region_ids = [item["id"] for item in result["regions"]]
    validation_input = next(item for item in input_context["inputs"] if item["kind"] == "validation-config")
    validation_path = _within(result_path.parent, result_path.parent / validation_input["path"])
    validation = _validate_json(validation_path, "benchmark-validation-config")
    if region_ids != validation["required_regions"]:
        raise RunnerError(f"run result region coverage mismatch: {region_ids}")
    for label, evidence in result["evidence"].items():
        if Path(evidence["path"]).is_absolute():
            raise RunnerError(f"run result {label} must use a relative evidence path")
        if label != "run_observation" and len(Path(evidence["path"]).parts) != 1:
            raise RunnerError(f"validator-owned {label} must be a direct child of the run directory")
        evidence_path = _resolve_evidence(result_path.parent, evidence, f"run result {label}")
        _within(result_path.parent, evidence_path)
        if plan["evidence_status"] == "measured":
            if label == "actual_screenshot":
                if _png_size(evidence_path) != (environment["viewport"]["width"], environment["viewport"]["height"]):
                    raise RunnerError("measured screenshot viewport does not match the benchmark case")
            else:
                try:
                    json.loads(evidence_path.read_text(encoding="utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise RunnerError(f"measured {label} evidence must be valid JSON") from exc


def _commit_object_sha256(source_root: Path, commit: str) -> str:
    result = _run_git(["cat-file", "commit", commit], cwd=source_root, text=False)
    if result.returncode != 0:
        raise RunnerError(f"unable to read pinned commit object: {commit}")
    return hashlib.sha256(result.stdout).hexdigest()


def _git_toplevel(path: Path) -> Path | None:
    result = _run_git(["rev-parse", "--show-toplevel"], cwd=path if path.is_dir() else path.parent)
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _case_evaluator_paths(case: dict[str, Any], case_path: Path) -> list[Path]:
    paths = [case_path]
    for label, evidence in (
        ("shared prompt", case["benchmark"]["shared_prompt"]),
        ("validation config", case["benchmark"]["validation_config"]),
    ):
        paths.append(_resolve_evidence(case_path.parent, evidence, label))
    for key, contract in case.get("contracts", {}).items():
        if isinstance(contract, dict) and "path" in contract:
            paths.append(_resolve_evidence(case_path.parent, contract, f"case contract {key}"))
    return paths


def _verify_measured_repository_boundaries(
    source_root: Path,
    plan_path: Path,
    evaluator_paths: list[Path],
) -> Path:
    plan_repository = _git_toplevel(plan_path)
    if plan_repository is None:
        raise RunnerError("measured plan and evaluator artifacts must belong to one reviewed Git repository")
    mismatched_repositories = [
        path for path in evaluator_paths if _git_toplevel(path) != plan_repository
    ]
    if mismatched_repositories:
        raise RunnerError(
            "measured case, contracts and adapters must belong to the same reviewed plan repository: "
            f"{mismatched_repositories}"
        )
    if _is_within(plan_repository, source_root) or _is_within(source_root, plan_repository):
        raise RunnerError(
            "measured plan/evaluator repository must not overlap the pinned code source repository"
        )
    return plan_repository


def run(
    plan_path: Path,
    workspace_root: Path,
    output_dir: Path,
    prepared_dir: Path | None,
    allow_synthetic: bool,
) -> dict[str, Any]:
    plan_path = plan_path.resolve()
    plan = _validate_json(plan_path, "benchmark-run-plan")
    if plan["evidence_status"] != "measured" and not allow_synthetic:
        raise RunnerError("synthetic run requires --allow-synthetic and cannot become measured evidence")
    if plan["evidence_status"] == "measured" and prepared_dir is not None:
        raise RunnerError("measured run must re-prepare the case; --prepared-dir is synthetic-only")
    plan_hash = sha256(plan_path)
    adapter_path = _resolve_evidence(plan_path.parent, plan["executor"]["adapter"], "executor adapter")
    capture_path = _resolve_evidence(plan_path.parent, plan["validator"]["capture_adapter"], "capture adapter")
    overlay_config = plan["validator"]["capture_overlay"]
    capture_runtime = plan["validator"]["capture_runtime"]
    capture_runtime_execution = json.loads(json.dumps(capture_runtime))
    dependency_setup = capture_runtime.get("evaluator_dependency_setup", {"mode": "none"})
    dependency_setup_mode = dependency_setup.get("mode", "none")
    dependency_generator_path: Path | None = None
    dependency_generator_hash: str | None = None
    if capture_runtime["mode"] == "ios-simulator":
        for key in ("verification_wrapper", "simctl"):
            resolved_tool = _resolve_evidence(plan_path.parent, capture_runtime[key], f"capture runtime {key}")
            capture_runtime_execution[key]["path"] = str(resolved_tool)
        if dependency_setup_mode != "none":
            dependency_generator_path = _resolve_evidence(
                plan_path.parent,
                dependency_setup["generator"],
                "evaluator dependency generator",
            )
            dependency_generator_hash = dependency_setup["generator"]["sha256"]
    capture_runtime_hash = hashlib.sha256(
        json.dumps(capture_runtime, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    overlay_path = (
        _resolve_evidence(plan_path.parent, overlay_config["artifact"], "capture overlay")
        if overlay_config["mode"] == "git-patch"
        else None
    )
    overlay_bytes = overlay_path.read_bytes() if overlay_path is not None else None
    overlay_hash = hashlib.sha256(overlay_bytes).hexdigest() if overlay_bytes is not None else None
    if overlay_path is not None and overlay_hash != overlay_config["artifact"]["sha256"]:
        raise RunnerError("capture overlay changed while freezing evaluator bytes")
    validator_path = _resolve_evidence(plan_path.parent, plan["validator"]["adapter"], "validator adapter")
    case_path = _resolve_evidence(plan_path.parent, plan["case"], "benchmark case")
    case = _validate_json(case_path, "benchmark-case")

    output_dir = output_dir.resolve()
    if output_dir.exists():
        if any(output_dir.iterdir()):
            raise RunnerError(f"output directory must be absent or empty: {output_dir}")
    else:
        output_dir.mkdir(parents=True)
    workspace_root = workspace_root.resolve()

    if prepared_dir is None:
        prepared = output_dir / "prepared"
        try:
            prepare(case_path, workspace_root, prepared, None)
        except PreparationError as exc:
            raise RunnerError(f"benchmark case preparation failed: {exc}") from exc
    else:
        prepared = prepared_dir.resolve()
    report_path = prepared / "preparation-report.json"
    report = load_json(report_path)
    if report.get("status") != "ready" or report.get("case_id") != case["case_id"] or report.get("case_sha256") != sha256(case_path):
        raise RunnerError("preparation report does not match the ready benchmark case")
    code = case["source"]["code"]
    case_provider_scope = code.get("provider_source_scope")
    report_provider_scope = report.get("provider_source_scope", {"mode": "full-tree"})
    provider_source_manifest_path: Path | None = None
    provider_source_manifest: dict[str, Any] | None = None
    if isinstance(case_provider_scope, dict):
        if report_provider_scope.get("mode") != "allowlist":
            raise RunnerError("preparation report omitted the case provider source allowlist")
        provider_source_manifest_path = _within(
            prepared,
            Path(report_provider_scope["manifest_path"]),
        )
        if not provider_source_manifest_path.is_file() or sha256(provider_source_manifest_path) != report_provider_scope.get("manifest_sha256"):
            raise RunnerError("prepared provider source manifest hash mismatch")
        provider_source_manifest = _validate_json(provider_source_manifest_path, "provider-source-manifest")
        expected_scope = {
            "file_count": case_provider_scope["expected_file_count"],
            "total_bytes": case_provider_scope["expected_total_bytes"],
            "content_sha256": case_provider_scope["expected_content_sha256"],
        }
        actual_scope = {key: provider_source_manifest.get(key) for key in expected_scope}
        if actual_scope != expected_scope or any(report_provider_scope.get(key) != value for key, value in expected_scope.items()):
            raise RunnerError("prepared provider source scope identity does not match benchmark case")
    elif report_provider_scope != {"mode": "full-tree"}:
        raise RunnerError("preparation report introduced an undeclared provider source scope")

    roots = {item["id"]: (workspace_root / item["path"]).resolve() for item in case["workspace_roots"]}
    source_root = roots[code["root"]]
    if not source_root.is_dir():
        raise RunnerError(f"code source root is missing: {source_root}")
    code_baseline_hash = _commit_object_sha256(source_root, code["git_commit"])
    evaluator_paths = [
        plan_path,
        adapter_path,
        capture_path,
        *([overlay_path] if overlay_path is not None else []),
        *([dependency_generator_path] if dependency_generator_path is not None else []),
        validator_path,
        *_case_evaluator_paths(case, case_path),
    ]
    plan_repository = _git_toplevel(plan_path)
    if plan["evidence_status"] == "measured":
        plan_repository = _verify_measured_repository_boundaries(
            source_root,
            plan_path,
            evaluator_paths,
        )
    persistent_sensitive_roots = [*roots.values()]
    if plan_repository is not None:
        persistent_sensitive_roots.append(plan_repository)
    if plan["evidence_status"] == "measured":
        for sensitive_root in persistent_sensitive_roots:
            if _is_within(output_dir, sensitive_root):
                raise RunnerError(
                    f"measured output must be outside every source/plan repository so it can be isolated: {sensitive_root}"
                )
    runner_root = Path(__file__).resolve().parents[3]
    runs: list[dict[str, Any]] = []
    common_environment = {
        "model": plan["executor"]["model"],
        "reasoning": plan["executor"]["reasoning"],
        "code_baseline_hash": code_baseline_hash,
        "shared_prompt_hash": case["benchmark"]["shared_prompt"]["sha256"],
        "design_source_hash": case["source"]["design"]["file"]["sha256"],
        "validation_config_hash": case["benchmark"]["validation_config"]["sha256"],
        "appearance": case["benchmark"]["environment"]["appearance"],
        "ui_framework": case["benchmark"]["environment"]["ui_framework"],
        "adapter_runtime": sys.executable,
        "adapter_runtime_version": sys.version.split()[0],
        "run_plan_hash": plan_hash,
        "benchmark_case_hash": sha256(case_path),
        "executor_adapter_hash": sha256(adapter_path),
        "validator_id": plan["validator"]["id"],
        "capture_adapter_hash": sha256(capture_path),
        "capture_overlay_mode": overlay_config["mode"],
        "capture_overlay_hash": overlay_hash,
        "capture_runtime_hash": capture_runtime_hash,
        "validator_adapter_hash": sha256(validator_path),
    }
    provider_identity: dict[str, str] | None = None

    for variant in plan["isolation"]["run_order"]:
        run_dir = output_dir / "runs" / variant
        run_dir.mkdir(parents=True)
        checkout = run_dir / "checkout"
        _create_checkout(
            source_root,
            code["git_commit"],
            checkout,
            strategy=plan["isolation"]["strategy"],
        )
        provider_worktree = checkout
        provider_baseline_commit: str | None = None
        provider_baseline_objects: set[str] | None = None
        provider_config_hash: str | None = None
        provider_git_metadata_hash: str | None = None
        if provider_source_manifest is not None:
            provider_worktree = run_dir / "provider-worktree"
            (
                provider_baseline_commit,
                provider_baseline_objects,
                provider_config_hash,
                provider_git_metadata_hash,
            ) = _create_provider_worktree(checkout, provider_worktree, provider_source_manifest)
        input_context_path, input_context = _verify_prepared_variant(
            prepared,
            case,
            case_path,
            plan_path,
            adapter_path,
            capture_path,
            overlay_path,
            overlay_hash,
            dependency_generator_path,
            dependency_generator_hash,
            dependency_setup_mode,
            validator_path,
            provider_source_manifest_path,
            report_provider_scope,
            provider_baseline_commit,
            provider_baseline_objects,
            provider_git_metadata_hash,
            plan_hash,
            variant,
            run_dir,
        )
        input_context_hash = sha256(input_context_path)
        current_capture_runtime = json.loads(json.dumps(capture_runtime_execution))
        if dependency_generator_path is not None:
            current_capture_runtime["evaluator_dependency_setup"]["generator"]["path"] = str(
                run_dir / "evaluator-dependency-generator"
            )
        result_path = run_dir / "benchmark-run-result.json"
        observation_path = run_dir / "run-observation.json"
        reference = next(item for item in input_context["inputs"] if item["kind"] == "reference")
        values = {
            "variant": variant,
            "model": plan["executor"]["model"],
            "reasoning": plan["executor"]["reasoning"],
            "worktree": str(provider_worktree),
            "run_dir": str(run_dir),
            "input_dir": str(run_dir / "input"),
            "input_context": str(input_context_path),
            "run_result": str(result_path),
            "run_observation": str(observation_path),
            "runner_root": str(runner_root),
            "code_baseline_commit": code["git_commit"],
            "reference_sha256": reference["sha256"],
            "adapter": str(run_dir / "executor-adapter"),
            "capture": str(run_dir / "capture-adapter"),
            "validator": str(run_dir / "validator-adapter"),
            "case_id": case["case_id"],
            "executor_adapter_sha256": sha256(adapter_path),
            "validator_id": plan["validator"]["id"],
            "capture_adapter_sha256": sha256(capture_path),
            "validator_adapter_sha256": sha256(validator_path),
            "actual_screenshot": str(run_dir / "actual.png"),
            "validator_probe": str(run_dir / "validator-probe.json"),
            "capture_runtime_json": json.dumps(current_capture_runtime, sort_keys=True, separators=(",", ":")),
        }
        setup_files = {
            "run-plan.json",
            "benchmark-case.json",
            "executor-adapter",
            "capture-adapter",
            "validator-adapter",
            "input-context.json",
        }
        if provider_source_manifest_path is not None:
            setup_files.add("provider-source-manifest.json")
        if dependency_generator_path is not None:
            setup_files.add("evaluator-dependency-generator")
        _require_exact_phase_files(run_dir, setup_files, "setup")
        implementation_environment = _command_environment(plan, plan["executor"], values, "executor")
        started_at = datetime.now(timezone.utc)
        implementation_command = _expand_command(plan["executor"]["implementation_command"], values)
        if not implementation_command or implementation_command[0] != str(run_dir / "executor-adapter"):
            raise RunnerError("implementation command must start with the archived adapter")
        implementation_command = [sys.executable, *implementation_command]
        implementation_stdout = run_dir / "implementation.stdout.log"
        implementation_stderr = run_dir / "implementation.stderr.log"
        hidden_paths: list[Path] = []
        if plan["evidence_status"] == "measured":
            hidden_paths.extend(_shield_current_run(run_dir, input_context))
            hidden_paths.append(prepared)
            hidden_paths.extend(persistent_sensitive_roots)
            hidden_paths.extend(item["run_dir"] for item in runs)
            hidden_paths.extend([plan_path, case_path, adapter_path, capture_path, validator_path])
            if dependency_generator_path is not None:
                hidden_paths.append(dependency_generator_path)
            if overlay_path is not None:
                hidden_paths.append(overlay_path)
            if provider_worktree != checkout:
                hidden_paths.append(checkout)
            for hidden in hidden_paths:
                if _is_within(provider_worktree, hidden):
                    raise RunnerError(f"executor-hidden path contains the active provider worktree: {hidden}")
        _execute_with_isolation(
            implementation_command,
            provider_worktree,
            implementation_environment,
            plan["executor"]["timeout_seconds"],
            implementation_stdout,
            implementation_stderr,
            hidden_paths,
            input_context_path,
        )
        implementation_phase_files = setup_files | {
            "implementation.stdout.log",
            "implementation.stderr.log",
            "run-observation.json",
        }
        _require_exact_phase_files(run_dir, implementation_phase_files, "implementation command")
        observation = _validate_json(observation_path, "benchmark-run-observation")
        _verify_provider_event_stream(observation, implementation_stdout)
        current_provider_identity = {
            "provider_cli_name": observation["provider_cli"]["name"],
            "provider_cli_version": observation["provider_cli"]["version"],
            "provider_cli_launcher_path": observation["provider_cli"]["launcher_path"],
            "provider_cli_native_path": observation["provider_cli"]["native_path"],
            "provider_cli_launcher_hash": observation["provider_cli"]["launcher_sha256"],
            "provider_cli_native_hash": observation["provider_cli"]["native_sha256"],
            "provider_cli_package_json_hash": observation["provider_cli"]["package_json_sha256"],
        }
        expected_provider_identity = {
            "provider_cli_name": plan["executor"]["provider_cli"]["name"],
            "provider_cli_version": plan["executor"]["provider_cli"]["version"],
            "provider_cli_launcher_path": plan["executor"]["provider_cli"]["launcher_path"],
            "provider_cli_native_path": plan["executor"]["provider_cli"]["native_path"],
            "provider_cli_launcher_hash": plan["executor"]["provider_cli"]["launcher_sha256"],
            "provider_cli_native_hash": plan["executor"]["provider_cli"]["native_sha256"],
            "provider_cli_package_json_hash": plan["executor"]["provider_cli"]["package_json_sha256"],
        }
        if current_provider_identity != expected_provider_identity:
            raise RunnerError("observed provider CLI identity does not match the frozen run plan")
        if provider_identity is None:
            provider_identity = current_provider_identity
        elif provider_identity != current_provider_identity:
            raise RunnerError("provider CLI identity changed across benchmark variants")
        observation_expected = {
            "case_id": case["case_id"],
            "variant": variant,
            "executor_adapter_sha256": sha256(adapter_path),
            "model": plan["executor"]["model"],
            "reasoning": plan["executor"]["reasoning"],
        }
        for key, value in observation_expected.items():
            if observation.get(key) != value:
                raise RunnerError(f"run observation linkage mismatch: {key}")
        observation_hash = sha256(observation_path)
        implementation_stdout_hash = sha256(implementation_stdout)
        implementation_stderr_hash = sha256(implementation_stderr)
        implementation_output = run_dir / "implementation-output.patch"
        if provider_worktree != checkout:
            assert provider_baseline_commit is not None
            assert provider_baseline_objects is not None
            assert provider_config_hash is not None
            assert provider_git_metadata_hash is not None
            _verify_provider_worktree_git(
                provider_worktree,
                provider_baseline_commit,
                provider_baseline_objects,
                provider_config_hash,
                provider_git_metadata_hash,
                provider_source_manifest,
            )
            implementation_hash, provider_changed_files = _capture_patch(
                provider_worktree,
                provider_baseline_commit,
                implementation_output,
            )
            invalid_changes = [
                path
                for path in provider_changed_files
                if not _scope_allows_path(path, provider_source_manifest["scope_entries"])
            ]
            if invalid_changes:
                raise RunnerError(f"provider modified paths outside frozen source scope: {invalid_changes}")
            if implementation_output.stat().st_size:
                applied = _run_git(
                    ["apply", "--binary", "--whitespace=nowarn", "--", str(implementation_output)],
                    cwd=checkout,
                )
                if applied.returncode != 0:
                    raise RunnerError(f"provider implementation patch does not apply to full checkout: {applied.stderr.strip()}")
            with tempfile.NamedTemporaryFile(prefix="dcc-full-checkout-patch-", suffix=".patch", dir=run_dir, delete=False) as handle:
                full_patch_path = Path(handle.name)
            try:
                full_hash, changed_files = _capture_patch(checkout, code["git_commit"], full_patch_path)
                if full_hash != implementation_hash or full_patch_path.read_bytes() != implementation_output.read_bytes():
                    raise RunnerError("provider patch changed while replaying into the full capture checkout")
                if changed_files != provider_changed_files:
                    raise RunnerError("provider/full checkout changed-file sets differ after patch replay")
            finally:
                full_patch_path.unlink(missing_ok=True)
        else:
            implementation_hash, changed_files = _capture_patch(checkout, code["git_commit"], implementation_output)
        values["worktree"] = str(checkout)
        _verify_pinned_head(checkout, code["git_commit"], "implementation command")
        if plan["isolation"]["strategy"] == "git-pinned-tree-slice":
            _verify_pinned_tree_slice(checkout, code["git_commit"])
        _verify_frozen_inputs(
            run_dir,
            input_context_path,
            input_context_hash,
            input_context,
            include_capture_overlay=False,
        )
        if overlay_bytes is not None:
            archived_overlay = run_dir / "capture-overlay.patch"
            if archived_overlay.exists():
                raise RunnerError("implementation command created evaluator capture overlay path")
            archived_overlay.write_bytes(overlay_bytes)
            if sha256(archived_overlay) != overlay_hash:
                raise RunnerError("archived capture overlay hash mismatch after late materialization")
        _verify_frozen_inputs(run_dir, input_context_path, input_context_hash, input_context)
        capture_command = _expand_command(plan["validator"]["capture_command"], values)
        if not capture_command or capture_command[0] != str(run_dir / "capture-adapter"):
            raise RunnerError("capture command must start with the archived capture adapter")
        capture_command = [sys.executable, *capture_command]
        capture_environment = _command_environment(plan, plan["validator"], values, "capture")
        overlay_applied = False
        overlay_state_hash: str | None = None
        try:
            if overlay_path is not None:
                _verify_frozen_inputs(run_dir, input_context_path, input_context_hash, input_context)
                _apply_capture_overlay(checkout, run_dir / "capture-overlay.patch")
                overlay_applied = True
                overlay_state_path = run_dir / ".capture-overlay-state.patch"
                overlay_state_hash, _ = _capture_patch(checkout, code["git_commit"], overlay_state_path)
                overlay_state_path.unlink()
            _execute(
                capture_command,
                checkout,
                capture_environment,
                plan["validator"]["timeout_seconds"],
                run_dir / "capture.stdout.log",
                run_dir / "capture.stderr.log",
            )
            if overlay_state_hash is not None:
                post_capture_overlay = run_dir / ".post-capture-overlay.patch"
                post_capture_overlay_hash, _ = _capture_patch(checkout, code["git_commit"], post_capture_overlay)
                post_capture_overlay.unlink()
                if post_capture_overlay_hash != overlay_state_hash:
                    raise RunnerError(f"capture command modified evaluator overlay checkout: {variant}")
        finally:
            restore_reason: str | None = None
            if overlay_applied:
                try:
                    _apply_capture_overlay(checkout, run_dir / "capture-overlay.patch", reverse=True)
                except RunnerError as exc:
                    restore_reason = str(exc)
            if restore_reason is None:
                restored_path = run_dir / ".post-capture-restore.patch"
                restored_hash, _ = _capture_patch(checkout, code["git_commit"], restored_path)
                restored_path.unlink()
                if restored_hash != implementation_hash:
                    restore_reason = f"capture phase left checkout mutations: {variant}"
            if restore_reason is not None:
                _force_restore_implementation_checkout(
                    checkout,
                    code["git_commit"],
                    implementation_output,
                )
                fallback_path = run_dir / ".post-capture-fallback.patch"
                fallback_hash, _ = _capture_patch(checkout, code["git_commit"], fallback_path)
                fallback_path.unlink()
                if fallback_hash != implementation_hash:
                    raise RunnerError(f"capture fallback did not recover implementation checkout: {variant}")
                raise RunnerError(
                    f"{restore_reason}; fallback restored the isolated checkout but the run is invalid"
                )
        capture_phase_files = implementation_phase_files | {
            "implementation-output.patch",
            "capture.stdout.log",
            "capture.stderr.log",
            "actual.png",
            "validator-probe.json",
        }
        if overlay_path is not None:
            capture_phase_files.add("capture-overlay.patch")
        _require_exact_phase_files(run_dir, capture_phase_files, "capture command")
        probe_path = run_dir / "validator-probe.json"
        probe = _validate_json(probe_path, "benchmark-validator-probe")
        _verify_capture_outputs(run_dir, probe, plan, input_context)
        actual_hash = sha256(run_dir / "actual.png")
        probe_hash = sha256(probe_path)
        _verify_pinned_head(checkout, code["git_commit"], "capture command")
        if plan["isolation"]["strategy"] == "git-pinned-tree-slice":
            _verify_pinned_tree_slice(checkout, code["git_commit"])
        _verify_frozen_inputs(run_dir, input_context_path, input_context_hash, input_context)
        if sha256(observation_path) != observation_hash:
            raise RunnerError("capture command modified executor-owned run observation")
        if sha256(implementation_stdout) != implementation_stdout_hash or sha256(implementation_stderr) != implementation_stderr_hash:
            raise RunnerError("capture command modified executor-owned command logs")
        if sha256(implementation_output) != implementation_hash:
            raise RunnerError("capture command modified frozen implementation patch")
        capture_stdout_hash = sha256(run_dir / "capture.stdout.log")
        capture_stderr_hash = sha256(run_dir / "capture.stderr.log")
        post_capture_patch = run_dir / "post-capture.patch"
        post_capture_hash, _ = _capture_patch(checkout, code["git_commit"], post_capture_patch)
        if post_capture_hash != implementation_hash:
            raise RunnerError(f"capture command modified implementation checkout: {variant}")
        post_capture_patch.unlink()
        validation_command = _expand_command(plan["validator"]["command"], values)
        if not validation_command or validation_command[0] != str(run_dir / "validator-adapter"):
            raise RunnerError("validation command must start with the archived validator adapter")
        validation_command = [sys.executable, *validation_command]
        validation_environment = _command_environment(plan, plan["validator"], values, "validator")
        _execute(
            validation_command,
            checkout,
            validation_environment,
            plan["validator"]["timeout_seconds"],
            run_dir / "validation.stdout.log",
            run_dir / "validation.stderr.log",
        )
        _verify_pinned_head(checkout, code["git_commit"], "validation command")
        if plan["isolation"]["strategy"] == "git-pinned-tree-slice":
            _verify_pinned_tree_slice(checkout, code["git_commit"])
        _verify_frozen_inputs(run_dir, input_context_path, input_context_hash, input_context)
        if sha256(observation_path) != observation_hash:
            raise RunnerError("validation command modified executor-owned run observation")
        if sha256(implementation_stdout) != implementation_stdout_hash or sha256(implementation_stderr) != implementation_stderr_hash:
            raise RunnerError("validation command modified executor-owned command logs")
        if sha256(run_dir / "capture.stdout.log") != capture_stdout_hash or sha256(run_dir / "capture.stderr.log") != capture_stderr_hash:
            raise RunnerError("validation command modified capture-owned command logs")
        if sha256(implementation_output) != implementation_hash:
            raise RunnerError("validation command modified frozen implementation patch")
        if sha256(run_dir / "actual.png") != actual_hash or sha256(probe_path) != probe_hash:
            raise RunnerError("validation command modified capture-owned evidence")
        post_validation_patch = run_dir / "post-validation.patch"
        post_validation_hash, _ = _capture_patch(checkout, code["git_commit"], post_validation_patch)
        if post_validation_hash != implementation_hash:
            raise RunnerError(f"validation command modified implementation checkout: {variant}")
        post_validation_patch.unlink()
        result = _validate_json(result_path, "benchmark-run-result")
        _verify_run_result(result_path, result, plan, case, input_context)
        if result["evidence"]["run_observation"]["sha256"] != observation_hash:
            raise RunnerError("run result observation hash does not match frozen executor output")
        allowed_validation_evidence = {
            Path(item["path"]).as_posix()
            for item in result["evidence"].values()
        }
        final_phase_files = capture_phase_files | {
            "validation.stdout.log",
            "validation.stderr.log",
            "benchmark-run-result.json",
            *allowed_validation_evidence,
        }
        _require_exact_phase_files(run_dir, final_phase_files, "validation command")
        completed_at = datetime.now(timezone.utc)
        metrics = {
            **result["metrics"],
            "input_tokens": result["model_usage"]["input_tokens"],
        }
        artifact = {
            "artifact_version": "1.2.0",
            "run_id": f"{plan['plan_id']}.{variant}.{started_at.strftime('%Y%m%dT%H%M%S%fZ')}",
            "variant": variant,
            "validation_status": result["status"],
            "capture_overlay": input_context["capture_overlay"],
            "environment": {**common_environment, **current_provider_identity},
            "metrics": metrics,
            "evidence": {
                "input_context": {"path": input_context_path.name, "sha256": sha256(input_context_path)},
                "implementation_output": {"path": implementation_output.name, "sha256": implementation_hash},
                "implementation_stdout": {"path": "implementation.stdout.log", "sha256": sha256(run_dir / "implementation.stdout.log")},
                "implementation_stderr": {"path": "implementation.stderr.log", "sha256": sha256(run_dir / "implementation.stderr.log")},
                "capture_stdout": {"path": "capture.stdout.log", "sha256": sha256(run_dir / "capture.stdout.log")},
                "capture_stderr": {"path": "capture.stderr.log", "sha256": sha256(run_dir / "capture.stderr.log")},
                "validation_stdout": {"path": "validation.stdout.log", "sha256": sha256(run_dir / "validation.stdout.log")},
                "validation_stderr": {"path": "validation.stderr.log", "sha256": sha256(run_dir / "validation.stderr.log")},
                "validation_report": {"path": result_path.name, "sha256": sha256(result_path)},
            },
        }
        artifact_path = run_dir / "run-artifact.json"
        artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _validate_json(artifact_path, "benchmark-artifact")
        runs.append(
            {
                "variant": variant,
                "validation_status": result["status"],
                "metrics": metrics,
                "run_id": artifact["run_id"],
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "artifact_path": artifact_path,
                "artifact_sha256": sha256(artifact_path),
                "changed_files": changed_files,
                "run_dir": run_dir,
            }
        )

    validation_config = _validate_json(
        prepared / "variants" / "screenshot-only" / "validation-config.json",
        "benchmark-validation-config",
    )
    case_environment = case["benchmark"]["environment"]
    benchmark = {
        "benchmark_version": "1.2.0",
        "case_id": case["case_id"],
        "evidence_status": plan["evidence_status"],
        "environment": {
            "task_mode": case_environment["task_mode"],
            "screen": case_environment["screen"],
            "state": case_environment["state"],
            "viewport": f"{case_environment['viewport']['width']}x{case_environment['viewport']['height']}@{case_environment['scale']}x",
            "locale": case_environment["locale"],
            "appearance": case_environment["appearance"],
            "ui_framework": case_environment["ui_framework"],
            "code_baseline": code["git_commit"],
            **common_environment,
            **(provider_identity or {}),
        },
        "thresholds": validation_config["thresholds"],
        "candidates": [
            {
                "variant": item["variant"],
                "validation_status": item["validation_status"],
                **item["metrics"],
                "run": {
                    "id": item["run_id"],
                    "started_at": item["started_at"],
                    "completed_at": item["completed_at"],
                    "artifact_path": item["artifact_path"].relative_to(output_dir).as_posix(),
                    "artifact_sha256": item["artifact_sha256"],
                },
            }
            for item in runs
        ],
    }
    benchmark_name = "benchmark-measured.json" if plan["evidence_status"] == "measured" else "benchmark-synthetic.json"
    benchmark_path = output_dir / benchmark_name
    benchmark_path.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _validate_json(benchmark_path, "benchmark")
    result = score(
        benchmark,
        allow_synthetic=plan["evidence_status"] != "measured",
        base_dir=output_dir,
    )
    if result.get("status") != "scored":
        raise RunnerError(f"benchmark evidence failed scorer verification: {result}")
    summary = {
        "status": "completed",
        "evidence_status": plan["evidence_status"],
        "plan_id": plan["plan_id"],
        "case_id": case["case_id"],
        "benchmark": str(benchmark_path),
        "score": result,
        "runs": [
            {"variant": item["variant"], "artifact": str(item["artifact_path"]), "changed_files": item["changed_files"]}
            for item in runs
        ],
    }
    summary_path = output_dir / "runner-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**summary, "summary_path": str(summary_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--prepared-dir", type=Path, help="synthetic tests only; measured runs always re-prepare")
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.plan, args.workspace_root, args.output_dir, args.prepared_dir, args.allow_synthetic)
    except (RunnerError, PreparationError, ValueError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
