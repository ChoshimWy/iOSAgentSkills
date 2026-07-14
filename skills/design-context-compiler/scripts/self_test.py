#!/usr/bin/env python3
"""Run deterministic contract, adversarial and benchmark gate self-tests."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import zlib

from compile_agent_packet import compile_packet
import create_benchmark_run_plan as run_plan_module
from codex_benchmark_executor import ExecutorError, _canonical_events, _cli_identity
from index_swift_components import scan
from initialize_implementation_manifest import initialize
from run_benchmark import (
    RunnerError,
    _capture_patch,
    _create_checkout,
    _create_provider_worktree,
    _execute,
    _execute_with_isolation,
    _restore_executor_isolation,
    _restore_hidden_paths,
    _provider_git_metadata_sha256,
    _scope_allows_path,
    _shield_paths,
    _verify_provider_worktree_git,
    _verify_measured_repository_boundaries,
    run as run_benchmark,
)
from score_benchmark import _capture_checkout_patch, _replay_provider_stream, _score_added_swift_literals, _score_decode_png, _score_pixel_difference_ratio, _verify_symbol_declaration_location, score
from ios_semantic_visual_validator import added_swift_literals as validator_added_swift_literals
from ios_semantic_visual_validator import decode_png as validator_decode_png
from ios_semantic_visual_validator import declaration_location as validator_declaration_location
from ios_semantic_visual_validator import pixel_difference_ratio as validator_pixel_difference_ratio
from ios_semantic_visual_validator import ValidationError as SemanticValidationError
from prepare_benchmark_case import (
    PreparationError,
    _provider_source_manifest,
    _verify_provider_source_scope,
    _verify_required_registry_bindings,
)
from validate_contract import estimate_agent_packet_tokens, load_json, validate
import unityframework_simulator_stub as unity_stub


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "references"
VALIDATOR = ROOT / "scripts" / "validate_contract.py"
CODEX_EXECUTOR = ROOT / "scripts" / "codex_benchmark_executor.py"


def make_png(width: int, height: int) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    pixels = b"".join(b"\x00" + (b"\x00" * width) for _ in range(height))
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def make_rgba_png(red: int, green: int, blue: int, alpha: int) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    pixels = bytes([0, red, green, blue, alpha])
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


def test_evaluator_dependency_setup_restore() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        bad_cpu = root / "bad-cpu"
        bad_cpu.write_bytes(struct.pack("<IiiIIIII", 0xFEEDFACF, 0x01000007, 0, 6, 0, 0, 0, 0))
        try:
            unity_stub.verify_simulator_macho(bad_cpu)
        except unity_stub.StubError as exc:
            assert "arm64" in str(exc)
        else:
            raise AssertionError("evaluator dependency must reject a non-arm64 Mach-O")

        bad_filetype = root / "bad-filetype"
        bad_filetype.write_bytes(struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0, 2, 0, 0, 0, 0))
        try:
            unity_stub.verify_simulator_macho(bad_filetype)
        except unity_stub.StubError as exc:
            assert "dynamic library" in str(exc)
        else:
            raise AssertionError("evaluator dependency must reject a non-dylib Mach-O")

        missing_simulator_platform = root / "missing-simulator-platform"
        missing_simulator_platform.write_bytes(
            struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0, 6, 1, 24, 0, 0)
            + struct.pack("<II16s", 0x1B, 24, b"self-test-uuid!!")
        )
        try:
            unity_stub.verify_simulator_macho(missing_simulator_platform)
        except unity_stub.StubError as exc:
            assert "iOS Simulator" in str(exc)
        else:
            raise AssertionError("evaluator dependency must require the iOS Simulator platform")

        wrong_platform = root / "wrong-platform"
        wrong_platform.write_bytes(
            struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0, 6, 2, 48, 0, 0)
            + struct.pack("<IIIIII", 0x32, 24, 2, 0, 0, 0)
            + struct.pack("<II16s", 0x1B, 24, b"self-test-uuid!!")
        )
        try:
            unity_stub.verify_simulator_macho(wrong_platform)
        except unity_stub.StubError as exc:
            assert "iOS Simulator" in str(exc)
        else:
            raise AssertionError("evaluator dependency must reject a non-Simulator platform")

        missing_uuid = root / "missing-uuid"
        missing_uuid.write_bytes(
            struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0, 6, 1, 24, 0, 0)
            + struct.pack("<IIIIII", 0x32, 24, 7, 0, 0, 0)
        )
        try:
            unity_stub.verify_simulator_macho(missing_uuid)
        except unity_stub.StubError as exc:
            assert "LC_UUID" in str(exc)
        else:
            raise AssertionError("evaluator dependency must require LC_UUID")

        mismatched_command_bytes = root / "mismatched-sizeofcmds"
        mismatched_command_bytes.write_bytes(
            struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0, 6, 1, 32, 0, 0)
            + struct.pack("<II16s", 0x1B, 24, b"self-test-uuid!!")
            + (b"\x00" * 8)
        )
        try:
            unity_stub.verify_simulator_macho(mismatched_command_bytes)
        except unity_stub.StubError as exc:
            assert "sizeofcmds" in str(exc)
        else:
            raise AssertionError("evaluator dependency must enforce the declared load-command table size")

        xcframework = root / "Pods/UnityFramework.xcframework"
        xcframework.mkdir(parents=True)
        info = xcframework / "Info.plist"
        info.write_bytes(plistlib.dumps({
            "AvailableLibraries": [
                {"LibraryIdentifier": "ios-arm64", "SupportedArchitectures": ["arm64"], "SupportedPlatform": "ios"},
                {"LibraryIdentifier": "ios-x86_64-simulator", "SupportedArchitectures": ["x86_64"], "SupportedPlatform": "ios", "SupportedPlatformVariant": "simulator"},
            ]
        }))
        copy_script = root / "Pods/copy.sh"
        copy_script.write_text(
            'case "$1" in\n'
            '  "UnityFramework.xcframework/ios-x86_64-simulator")\n    echo "simulator"\n    ;;\n'
            'esac\ncase "$1" in\n'
            '  "UnityFramework.xcframework/ios-x86_64-simulator")\n    echo "x86_64"\n    ;;\n'
            'esac\ninstall "ios-arm64" "ios-x86_64-simulator"\n',
            encoding="utf-8",
        )
        original_info = hashlib.sha256(info.read_bytes()).hexdigest()
        original_script = hashlib.sha256(copy_script.read_bytes()).hexdigest()

        def fake_build(output: Path, _clang: Path, _sdk: Path) -> dict[str, str]:
            framework = output / unity_stub.FRAMEWORK_NAME
            (framework / "Headers").mkdir(parents=True)
            (framework / "Modules").mkdir(parents=True)
            files = {
                "binary_sha256": framework / "UnityFramework",
                "header_sha256": framework / "Headers/UnityFramework.h",
                "modulemap_sha256": framework / "Modules/module.modulemap",
                "framework_info_sha256": framework / "Info.plist",
            }
            for key, path in files.items():
                path.write_text(key, encoding="utf-8")
            return {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in files.items()}

        with TemporaryDirectory() as product_dir:
            product = fake_build(Path(product_dir), Path("clang"), Path("sdk"))
        contract = {
            "mode": "unityframework-arm64-simulator-stub-v1",
            "clang": {"path": "/clang", "sha256": "0" * 64},
            "sdk": {"path": "/sdk", "settings_sha256": "1" * 64},
            "xcframework_path": "Pods/UnityFramework.xcframework",
            "pod_copy_script_path": "Pods/copy.sh",
            "baseline": {"xcframework_info_sha256": original_info, "pod_copy_script_sha256": original_script},
            "product": product,
        }
        state = root / "state"
        with patch.object(unity_stub, "fingerprint", return_value=product), patch.object(unity_stub, "build_product", side_effect=fake_build):
            unity_stub.apply(contract, root, state)
            assert (xcframework / unity_stub.SLICE_IDENTIFIER / unity_stub.FRAMEWORK_NAME / "UnityFramework").is_file()
            unity_stub.restore(contract, root, state)
            assert hashlib.sha256(info.read_bytes()).hexdigest() == original_info
            assert hashlib.sha256(copy_script.read_bytes()).hexdigest() == original_script
            assert not (xcframework / unity_stub.SLICE_IDENTIFIER).exists()

            unity_stub.apply(contract, root, state)
            copy_script.write_text(copy_script.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
            try:
                unity_stub.restore(contract, root, state)
            except unity_stub.StubError as exc:
                assert "changed while capture" in str(exc)
            else:
                raise AssertionError("dependency setup restore must reject capture-time mutation")


def test_benchmark_required_binding_projection() -> None:
    registry = {
        "entries": [
            {
                "id": "component.alert",
                "status": "active",
                "reuse_policy": "required",
                "bindings": [
                    {
                        "id": "binding.alert.uikit",
                        "framework": "UIKit",
                        "symbol": "AlertView",
                        "source": "Sources/AlertView.swift",
                    }
                ],
            }
        ]
    }
    validation = {
        "required_bindings": [
            {
                "id": "binding.alert.uikit",
                "registry_entry_id": "component.alert",
                "code_symbol": "AlertView",
                "source": "Sources/AlertView.swift",
                "region_id": "alert",
                "runtime_type": "AlertView",
            }
        ]
    }
    _verify_required_registry_bindings(registry, validation, "UIKit")

    stale_source = deepcopy(validation)
    stale_source["required_bindings"][0]["source"] = "Sources/StaleAlertView.swift"
    try:
        _verify_required_registry_bindings(registry, stale_source, "UIKit")
    except PreparationError as exc:
        assert "differ from active required Registry bindings" in str(exc)
    else:
        raise AssertionError("benchmark preparation must reject Registry source drift")


def test_provider_source_scope_worktree() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        repository = root / "repository"
        repository.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        (repository / "Allowed").mkdir()
        (repository / "Allowed/A.swift").write_text("let value = 1\n", encoding="utf-8")
        (repository / "Allowed/B.json").write_text("{}\n", encoding="utf-8")
        (repository / "Secret").mkdir()
        (repository / "Secret/private.txt").write_text("must stay hidden\n", encoding="utf-8")
        (repository / "Unsupported").mkdir()
        (repository / "Unsupported/link.swift").symlink_to("../Allowed/A.swift")
        subprocess.run(["git", "add", "."], cwd=repository, check=True)
        subprocess.run(
            [
                "git", "-c", "user.name=Scope Test", "-c", "user.email=scope@example.invalid",
                "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                "commit", "-q", "-m", "scope baseline",
            ],
            cwd=repository,
            check=True,
        )
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
        scope = {"mode": "allowlist", "entries": [{"kind": "directory", "path": "Allowed"}]}
        manifest = _provider_source_manifest(repository, commit, scope)
        assert [item["path"] for item in manifest["files"]] == ["Allowed/A.swift", "Allowed/B.json"]
        _, manifest_diagnostics, manifest_blocking = validate(manifest, "provider-source-manifest")
        assert not manifest_diagnostics and not manifest_blocking
        invalid_manifest = deepcopy(manifest)
        invalid_manifest["files"][0]["bytes"] += 1
        expect_invalid(invalid_manifest, "provider-source-manifest", "artifact.manifest")
        overlapping_manifest = deepcopy(manifest)
        overlapping_manifest["scope_entries"].append({"kind": "file", "path": "Allowed/A.swift"})
        expect_invalid(overlapping_manifest, "provider-source-manifest", "artifact.manifest")
        unsorted_manifest = deepcopy(manifest)
        unsorted_manifest["files"].reverse()
        expect_invalid(unsorted_manifest, "provider-source-manifest", "artifact.manifest")
        frozen_scope = {
            **scope,
            "expected_file_count": manifest["file_count"],
            "expected_total_bytes": manifest["total_bytes"],
            "expected_content_sha256": manifest["content_sha256"],
        }
        assert _verify_provider_source_scope(repository, commit, frozen_scope) == manifest
        overlapping_scope = {
            "mode": "allowlist",
            "entries": [
                {"kind": "directory", "path": "Allowed"},
                {"kind": "file", "path": "Allowed/A.swift"},
            ],
        }
        try:
            _provider_source_manifest(repository, commit, overlapping_scope)
        except PreparationError as exc:
            assert "overlap" in str(exc)
        else:
            raise AssertionError("provider source scope must reject overlapping entries")
        try:
            _provider_source_manifest(
                repository,
                commit,
                {"mode": "allowlist", "entries": [{"kind": "file", "path": "Missing.swift"}]},
            )
        except PreparationError as exc:
            assert "matched no frozen files" in str(exc)
        else:
            raise AssertionError("provider source scope must reject empty matches")
        try:
            _provider_source_manifest(
                repository,
                commit,
                {"mode": "allowlist", "entries": [{"kind": "directory", "path": "Unsupported"}]},
            )
        except PreparationError as exc:
            assert "unsupported Git entry" in str(exc)
        else:
            raise AssertionError("provider source scope must reject symlink entries")
        drifted_scope = deepcopy(frozen_scope)
        drifted_scope["expected_file_count"] += 1
        try:
            _verify_provider_source_scope(repository, commit, drifted_scope)
        except PreparationError as exc:
            assert "identity mismatch" in str(exc)
        else:
            raise AssertionError("provider source scope must reject frozen identity drift")

        full_checkout = root / "full-checkout"
        _create_checkout(repository, commit, full_checkout, strategy="git-pinned-tree-slice")
        provider_worktree = root / "provider-worktree"
        baseline, objects, config_hash, metadata_hash = _create_provider_worktree(full_checkout, provider_worktree, manifest)
        assert (provider_worktree / "Allowed/A.swift").is_file()
        assert not (provider_worktree / "Secret/private.txt").exists()
        (provider_worktree / "Allowed/A.swift").write_text("let value = 2\n", encoding="utf-8")
        _verify_provider_worktree_git(provider_worktree, baseline, objects, config_hash, metadata_hash, manifest)
        patch_path = root / "implementation.patch"
        patch_hash, changed = _capture_patch(provider_worktree, baseline, patch_path)
        assert changed == ["Allowed/A.swift"]
        assert _scope_allows_path(changed[0], manifest["scope_entries"])
        index_line = next(line for line in patch_path.read_text(encoding="utf-8").splitlines() if line.startswith("index "))
        old_object, new_object = index_line.split()[1].split("..")
        assert len(old_object) == 40 and len(new_object) == 40
        applied = subprocess.run(
            ["git", "apply", "--binary", "--whitespace=nowarn", "--", str(patch_path)],
            cwd=full_checkout,
            capture_output=True,
            check=False,
        )
        assert applied.returncode == 0
        replay_path = root / "replayed.patch"
        replay_hash, replayed = _capture_patch(full_checkout, commit, replay_path)
        assert replay_hash == patch_hash and replay_path.read_bytes() == patch_path.read_bytes()
        assert replayed == changed
        scored_patch, scored_error = _capture_checkout_patch(full_checkout, commit)
        assert scored_error is None and scored_patch == patch_path.read_bytes()

        reset = subprocess.run(
            ["git", "checkout", "--", "Allowed/A.swift"],
            cwd=provider_worktree,
            capture_output=True,
            check=False,
        )
        assert reset.returncode == 0
        untracked_binary = provider_worktree / "Allowed/New.bin"
        untracked_binary.write_bytes(b"\x00canonical-provider-output\xff")
        untracked_patch = root / "untracked.patch"
        untracked_hash, untracked_changed = _capture_patch(provider_worktree, baseline, untracked_patch)
        assert untracked_changed == ["Allowed/New.bin"]
        assert _scope_allows_path(untracked_changed[0], manifest["scope_entries"])
        untracked_index = next(
            line for line in untracked_patch.read_text(encoding="utf-8").splitlines() if line.startswith("index ")
        )
        zero_object, binary_object = untracked_index.split()[1].split("..")
        assert zero_object == "0" * 40 and len(binary_object) == 40
        untracked_checkout = root / "untracked-full-checkout"
        _create_checkout(repository, commit, untracked_checkout, strategy="git-pinned-tree-slice")
        applied_untracked = subprocess.run(
            ["git", "apply", "--binary", "--whitespace=nowarn", "--", str(untracked_patch)],
            cwd=untracked_checkout,
            capture_output=True,
            check=False,
        )
        assert applied_untracked.returncode == 0
        replayed_untracked = root / "replayed-untracked.patch"
        replayed_untracked_hash, replayed_untracked_changed = _capture_patch(
            untracked_checkout, commit, replayed_untracked
        )
        assert replayed_untracked_hash == untracked_hash
        assert replayed_untracked.read_bytes() == untracked_patch.read_bytes()
        assert replayed_untracked_changed == untracked_changed
        scored_untracked, scored_untracked_error = _capture_checkout_patch(untracked_checkout, commit)
        assert scored_untracked_error is None and scored_untracked == untracked_patch.read_bytes()

        (provider_worktree / "Outside.swift").write_text("let leaked = true\n", encoding="utf-8")
        _, outside_changes = _capture_patch(provider_worktree, baseline, root / "outside.patch")
        assert "Outside.swift" in outside_changes
        assert not _scope_allows_path("Outside.swift", manifest["scope_entries"])


def sync_packet_budget(packet: dict) -> None:
    packet["context_budget"]["estimated_tokens"] = estimate_agent_packet_tokens(packet)
    packet["context_budget"]["within_budget"] = (
        packet["context_budget"]["estimated_tokens"] <= packet["context_budget"]["max_tokens"]
    )


def expect_valid(name: str, kind: str) -> dict:
    data = load_json(REFERENCES / name)
    base_dir = REFERENCES if kind == "implementation-manifest" else None
    _, diagnostics, blocking = validate(data, kind, base_dir=base_dir)
    assert not diagnostics, [item.as_dict() for item in diagnostics]
    assert not blocking, blocking
    return data


def expect_invalid(data: dict, kind: str, expected_code_prefix: str | None = None) -> None:
    _, diagnostics, _ = validate(data, kind)
    assert diagnostics, f"expected invalid {kind} contract"
    if expected_code_prefix:
        assert any(item.code.startswith(expected_code_prefix) for item in diagnostics), [item.as_dict() for item in diagnostics]


def test_codex_benchmark_executor() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        worktree = root / "checkout"
        worktree.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=worktree, check=True)
        input_dir = root / "input"
        input_dir.mkdir()
        reference = input_dir / "reference.png"
        reference.write_bytes(make_png(2, 2))
        prompt = input_dir / "shared-prompt.md"
        prompt.write_text("Implement the frozen alert slice.\n", encoding="utf-8")
        validator = input_dir / "validation-config.json"
        validator.write_text('{"secret_binding":"must-not-leak"}\n', encoding="utf-8")
        ui_ir = input_dir / "ui-ir.json"
        ui_ir.write_text('{"screen":"visible-ui-ir"}\n', encoding="utf-8")
        context = {
            "input_context_version": "1.2.0",
            "case_id": "executor-self-test",
            "variant": "ui-ir",
            "plan_sha256": "a" * 64,
            "run_plan": {"path": "run-plan.json", "sha256": "b" * 64},
            "benchmark_case": {"path": "benchmark-case.json", "sha256": "c" * 64},
            "executor_adapter": {"path": "executor-adapter", "sha256": hashlib.sha256(CODEX_EXECUTOR.read_bytes()).hexdigest()},
            "validator_adapter": {"path": "validator-adapter", "sha256": "d" * 64},
            "environment": {
                "task_mode": "reuse-conformance",
                "screen": "alert",
                "state": "default",
                "viewport": {"width": 2, "height": 2},
                "scale": 1,
                "appearance": "dark",
                "locale": "en_US",
                "ui_framework": "UIKit",
            },
            "inputs": [
                {"kind": "reference", "audience": "agent", "path": "input/reference.png", "sha256": hashlib.sha256(reference.read_bytes()).hexdigest()},
                {"kind": "shared-prompt", "audience": "agent", "path": "input/shared-prompt.md", "sha256": hashlib.sha256(prompt.read_bytes()).hexdigest()},
                {"kind": "validation-config", "audience": "validator", "path": "input/validation-config.json", "sha256": hashlib.sha256(validator.read_bytes()).hexdigest()},
                {"kind": "ui-ir", "audience": "agent", "path": "input/ui-ir.json", "sha256": hashlib.sha256(ui_ir.read_bytes()).hexdigest()},
            ],
        }
        context_path = root / "input-context.json"
        context_path.write_text(json.dumps(context), encoding="utf-8")
        capture = root / "provider-capture.json"
        fake = root / "codex"
        fake.write_text(
            """#!/usr/bin/env python3
import json, os, pathlib, sys
if sys.argv[1:] == [\"--version\"]:
    print(\"codex-cli 0.test\")
    raise SystemExit(0)
args = sys.argv[1:]
prompt = args[-1]
capture = {
    \"has_dcc_environment\": any(key.startswith(\"DCC_\") for key in os.environ),
    \"has_validator_secret\": \"VALIDATOR_SECRET\" in os.environ,
    \"pwd\": os.environ.get(\"PWD\"),
    \"prompt\": prompt,
    \"args\": args[:-1],
}
pathlib.Path(os.environ[\"FAKE_CAPTURE\"]).write_text(json.dumps(capture))
print(json.dumps({\"type\":\"thread.started\",\"thread_id\":\"provider-self-test\"}))
print(json.dumps({\"type\":\"turn.started\"}))
print(json.dumps({\"type\":\"item.completed\",\"item\":{\"id\":\"item_0\",\"type\":\"agent_message\",\"text\":\"{}\"}}))
print(json.dumps({\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":123,\"cached_input_tokens\":23,\"output_tokens\":7,\"reasoning_output_tokens\":2}}))
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        observation = root / "run-observation.json"
        environment = os.environ.copy()
        environment.update(
            {
                "DCC_EVIDENCE_STATUS": "synthetic-adapter-test",
                "DCC_VARIANT": "ui-ir",
                "DCC_MODEL": "gpt-self-test",
                "DCC_REASONING": "low",
                "DCC_WORKTREE": str(worktree),
                "DCC_INPUT_CONTEXT": str(context_path),
                "DCC_CASE_ID": "executor-self-test",
                "DCC_EXECUTOR_ADAPTER_SHA256": hashlib.sha256(CODEX_EXECUTOR.read_bytes()).hexdigest(),
                "DCC_RUN_OBSERVATION": str(observation),
                "DCC_EXPECTED_PROVIDER_CLI_VERSION": "unused-test-version",
                "DCC_EXPECTED_PROVIDER_LAUNCHER_PATH": str(fake),
                "DCC_EXPECTED_PROVIDER_NATIVE_PATH": str(fake),
                "DCC_EXPECTED_PROVIDER_LAUNCHER_SHA256": "0" * 64,
                "DCC_EXPECTED_PROVIDER_NATIVE_SHA256": "0" * 64,
                "DCC_EXPECTED_PROVIDER_PACKAGE_JSON_SHA256": "0" * 64,
                "DCC_CODEX_BIN": str(fake),
                "FAKE_CAPTURE": str(capture),
                "VALIDATOR_SECRET": "must-not-reach-provider",
            }
        )
        result = subprocess.run(
            [sys.executable, str(CODEX_EXECUTOR)],
            cwd=worktree,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        receipt = load_json(observation)
        _, diagnostics, blocking = validate(receipt, "benchmark-run-observation")
        assert not diagnostics and not blocking, [item.as_dict() for item in diagnostics]
        assert receipt["provider_runs"] == [
            {
                "id": "provider-self-test",
                "input_tokens": 123,
                "cached_input_tokens": 23,
                "output_tokens": 7,
                "reasoning_output_tokens": 2,
            }
        ]
        assert receipt["provider_event_stream_sha256"] == hashlib.sha256(result.stdout.encode()).hexdigest()
        provider_capture = load_json(capture)
        assert provider_capture["has_dcc_environment"] is False
        assert provider_capture["has_validator_secret"] is False
        assert Path(provider_capture["pwd"]).resolve() == worktree.resolve()
        assert "visible-ui-ir" in provider_capture["prompt"]
        assert "must-not-leak" not in provider_capture["prompt"]
        assert "validation-config" not in provider_capture["prompt"]
        assert "--ignore-user-config" in provider_capture["args"]
        assert "--ignore-rules" in provider_capture["args"]
        observation.unlink()
        measured_override_environment = environment.copy()
        measured_override_environment["DCC_EVIDENCE_STATUS"] = "measured"
        blocked = subprocess.run(
            [sys.executable, str(CODEX_EXECUTOR)],
            cwd=worktree,
            env=measured_override_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert blocked.returncode == 2 and "forbids Codex binary override" in blocked.stderr
        assert not observation.exists()
        path_override_environment = measured_override_environment.copy()
        path_override_environment.pop("DCC_CODEX_BIN")
        path_override_environment["PATH"] = f"{root}:{path_override_environment.get('PATH', '')}"
        path_override_environment["DCC_EXPECTED_PROVIDER_LAUNCHER_PATH"] = str(root / "missing-codex.js")
        path_blocked = subprocess.run(
            [sys.executable, str(CODEX_EXECUTOR)],
            cwd=worktree,
            env=path_override_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert path_blocked.returncode == 2
        assert "frozen measured Codex launcher path" in path_blocked.stderr
        assert not observation.exists()


def test_measured_executor_shield() -> None:
    with TemporaryDirectory() as raw:
        run_dir = Path(raw)
        (run_dir / "input").mkdir()
        protected = [
            run_dir / "run-plan.json",
            run_dir / "benchmark-case.json",
            run_dir / "validator-adapter",
            run_dir / "input" / "validation-config.json",
        ]
        for path in protected:
            path.write_text("protected\n", encoding="utf-8")
        agent_input = run_dir / "input" / "reference.png"
        agent_input.write_bytes(make_png(1, 1))
        context = {
            "inputs": [
                {"kind": "reference", "audience": "agent", "path": "input/reference.png"},
                {"kind": "validation-config", "audience": "validator", "path": "input/validation-config.json"},
            ]
        }
        hidden = [
            run_dir / "run-plan.json",
            run_dir / "benchmark-case.json",
            run_dir / "validator-adapter",
            run_dir / "input" / "validation-config.json",
        ]
        modes = _shield_paths(hidden)
        try:
            assert set(modes) == {path.resolve() for path in protected}
            assert all(path.stat().st_mode & 0o777 == 0 for path in protected)
            assert agent_input.stat().st_mode & 0o400
        finally:
            _restore_hidden_paths(modes)
        assert all(path.stat().st_mode & 0o400 for path in protected)
        rollback_target = run_dir / "rollback-target"
        rollback_target.write_text("rollback\n", encoding="utf-8")
        original_mode = rollback_target.stat().st_mode & 0o777
        try:
            _shield_paths([rollback_target, run_dir / "missing-hidden-path"])
        except RunnerError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError("shield must reject missing hidden paths")
        assert rollback_target.stat().st_mode & 0o777 == original_mode
        partial_first = run_dir / "partial-first"
        partial_second = run_dir / "partial-second"
        partial_first.write_text("first\n", encoding="utf-8")
        partial_second.write_text("second\n", encoding="utf-8")
        partial_modes = {
            partial_first: partial_first.stat().st_mode & 0o777,
            partial_second: partial_second.stat().st_mode & 0o777,
        }
        original_chmod = Path.chmod

        def fail_second_zero(path: Path, mode: int, *args, **kwargs):
            if path.resolve() == partial_second.resolve() and mode == 0:
                raise OSError("injected partial shield failure")
            return original_chmod(path, mode, *args, **kwargs)

        with patch.object(Path, "chmod", fail_second_zero):
            try:
                _shield_paths([partial_first, partial_second])
            except OSError as exc:
                assert "injected partial" in str(exc)
            else:
                raise AssertionError("shield must rollback after a real partial chmod failure")
        assert all(path.stat().st_mode & 0o777 == mode for path, mode in partial_modes.items())

        restore_first = run_dir / "restore-first"
        restore_second = run_dir / "restore-second"
        restore_first.write_text("first\n", encoding="utf-8")
        restore_second.write_text("second\n", encoding="utf-8")
        restore_modes = _shield_paths([restore_first, restore_second])
        failed_restore = restore_second.resolve()

        def fail_one_restore(path: Path, mode: int, *args, **kwargs):
            if path.resolve() == failed_restore and mode != 0:
                raise OSError("injected restore failure")
            return original_chmod(path, mode, *args, **kwargs)

        with patch.object(Path, "chmod", fail_one_restore):
            try:
                _restore_hidden_paths(restore_modes)
            except RunnerError as exc:
                assert "injected restore failure" in str(exc)
            else:
                raise AssertionError("restore must report an injected per-path failure")
        assert restore_first.stat().st_mode & 0o400
        assert restore_second.stat().st_mode & 0o777 == 0
        original_chmod(restore_second, restore_modes[restore_second.resolve()])
        emergency_context = run_dir / "input-context.json"
        emergency_context.write_text("{}\n", encoding="utf-8")
        context_mode = emergency_context.stat().st_mode & 0o777
        emergency_hidden = run_dir / "emergency-hidden"
        emergency_hidden.write_text("hidden\n", encoding="utf-8")
        emergency_modes = _shield_paths([emergency_hidden])
        emergency_context.chmod(0)
        _restore_executor_isolation(emergency_modes, emergency_context, context_mode)
        assert emergency_context.stat().st_mode & 0o777 == context_mode
        assert emergency_hidden.stat().st_mode & 0o400

        pre_execute_hidden = run_dir / "pre-execute-hidden"
        pre_execute_hidden.write_text("hidden\n", encoding="utf-8")
        try:
            _execute_with_isolation(
                [str(run_dir / "missing-executable")],
                run_dir,
                os.environ.copy(),
                1,
                run_dir / "pre-execute.stdout",
                run_dir / "pre-execute.stderr",
                [pre_execute_hidden],
                emergency_context,
            )
        except OSError:
            pass
        else:
            raise AssertionError("pre-execute failure fixture must fail")
        assert pre_execute_hidden.stat().st_mode & 0o400
        assert emergency_context.stat().st_mode & 0o777 == context_mode


def test_measured_identity_ignores_fake_node_path() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        package = root / "node_modules" / "@openai" / "codex"
        launcher = package / "bin" / "codex.js"
        platform_package, vendor_platform = {
            ("Darwin", "arm64"): ("codex-darwin-arm64", "aarch64-apple-darwin"),
            ("Darwin", "x86_64"): ("codex-darwin-x64", "x86_64-apple-darwin"),
        }[(platform.system(), platform.machine())]
        native = (
            package
            / "node_modules"
            / "@openai"
            / platform_package
            / "vendor"
            / vendor_platform
            / "bin"
            / "codex"
        )
        launcher.parent.mkdir(parents=True)
        native.parent.mkdir(parents=True)
        launcher.write_text("#!/usr/bin/env node\nthrow new Error('launcher must not execute');\n", encoding="utf-8")
        (package / "package.json").write_text(
            json.dumps({"name": "@openai/codex", "version": "9.9.9"}),
            encoding="utf-8",
        )
        native.write_text(
            "#!/bin/sh\n[ \"$1\" = \"--version\" ] && echo 'codex-cli 9.9.9' && exit 0\nexit 9\n",
            encoding="utf-8",
        )
        native.chmod(0o755)
        fake_bin = root / "fake-bin"
        fake_bin.mkdir()
        node_marker = root / "fake-node-ran"
        fake_node = fake_bin / "node"
        fake_node.write_text(f"#!/bin/sh\necho ran > '{node_marker}'\nexit 0\n", encoding="utf-8")
        fake_node.chmod(0o755)
        with patch.dict(os.environ, {"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}):
            identity = _cli_identity(launcher, root)
        assert identity[0] == "codex-cli 9.9.9"
        assert identity[2] == str(native.resolve())
        assert not node_marker.exists(), "measured identity must not execute launcher via PATH-resolved node"


def test_provider_receipt_parser_adversarial() -> None:
    valid_events = [
        {"type": "thread.started", "thread_id": "provider-parser-test"},
        {"type": "turn.started"},
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": 10,
                "cached_input_tokens": 2,
                "output_tokens": 3,
                "reasoning_output_tokens": 1,
            },
        },
    ]
    raw = "".join(json.dumps(event) + "\n" for event in valid_events)
    canonical, thread_id, usage = _canonical_events(raw)
    assert thread_id == "provider-parser-test" and usage["input_tokens"] == 10
    replay_id, replay_usage, replay_error = _replay_provider_stream(canonical)
    assert replay_error is None and replay_id == thread_id and replay_usage == usage
    duplicate_turn = deepcopy(valid_events)
    duplicate_turn.insert(2, {"type": "turn.started"})
    try:
        _canonical_events("".join(json.dumps(event) + "\n" for event in duplicate_turn))
    except ExecutorError as exc:
        assert "one ordered" in str(exc)
    else:
        raise AssertionError("executor parser must reject multiple turn.started events")
    malformed_usage = deepcopy(valid_events)
    del malformed_usage[-1]["usage"]["cached_input_tokens"]
    try:
        _canonical_events("".join(json.dumps(event) + "\n" for event in malformed_usage))
    except ExecutorError as exc:
        assert "usage" in str(exc)
    else:
        raise AssertionError("executor parser must reject missing provider usage")
    _, _, replay_error = _replay_provider_stream(b"not-json\n")
    assert replay_error is not None


def test_executor_timeout_kills_process_group() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        child_pid = root / "child.pid"
        driver = root / "driver.py"
        driver.write_text(
            """import pathlib, subprocess, sys, time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
pathlib.Path(sys.argv[1]).write_text(str(child.pid))
time.sleep(60)
""",
            encoding="utf-8",
        )
        try:
            _execute(
                [sys.executable, str(driver), str(child_pid)],
                root,
                os.environ.copy(),
                1,
                root / "stdout.log",
                root / "stderr.log",
            )
        except RunnerError as exc:
            assert "timed out" in str(exc)
        else:
            raise AssertionError("timeout test driver must be terminated")
        pid = int(child_pid.read_text())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("executor timeout must kill provider descendants")


def test_isolated_timeout_restores_after_descendants_exit() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        hidden = root / "hidden"
        hidden.write_text("secret\n", encoding="utf-8")
        hidden_mode = hidden.stat().st_mode & 0o777
        context = root / "input-context.json"
        context.write_text("{}\n", encoding="utf-8")
        context_mode = context.stat().st_mode & 0o777
        child_pid = root / "child.pid"
        ready = root / "ready"
        leaked = root / "restored-too-early"
        driver = root / "isolated-timeout.py"
        driver.write_text(
            """import os, pathlib, subprocess, sys, time
hidden, context, child_pid, ready, leaked = map(pathlib.Path, sys.argv[1:])
monitor = subprocess.Popen([
    sys.executable, '-c',
    'import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); leak=pathlib.Path(sys.argv[2]); '
    '[(leak.write_text("early") if (p.stat().st_mode & 0o777) else time.sleep(0.01)) for _ in range(10000)]',
    str(hidden), str(leaked),
])
child_pid.write_text(str(monitor.pid))
if hidden.stat().st_mode & 0o777:
    raise SystemExit('hidden path was readable during provider execution')
context.chmod(0)
ready.write_text('ready')
time.sleep(60)
""",
            encoding="utf-8",
        )
        try:
            _execute_with_isolation(
                [sys.executable, str(driver), str(hidden), str(context), str(child_pid), str(ready), str(leaked)],
                root,
                os.environ.copy(),
                1,
                root / "isolated.stdout",
                root / "isolated.stderr",
                [hidden],
                context,
            )
        except RunnerError as exc:
            assert "timed out" in str(exc)
        else:
            raise AssertionError("isolated timeout fixture must time out")
        assert ready.is_file()
        assert not leaked.exists()
        assert hidden.stat().st_mode & 0o777 == hidden_mode
        assert context.stat().st_mode & 0o777 == context_mode
        pid = int(child_pid.read_text())
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("isolated timeout must reap provider descendants before restoring paths")


def test_pinned_tree_slice_rejects_history() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        source = root / "source"
        source.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=source, check=True)
        secret = source / "validator-secret.txt"
        secret.write_text("historical validator secret\n", encoding="utf-8")
        subprocess.run(["git", "add", "validator-secret.txt"], cwd=source, check=True)
        commit_args = [
            "git", "-c", "user.name=Benchmark Test", "-c", "user.email=test@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q",
        ]
        subprocess.run([*commit_args, "-m", "secret"], cwd=source, check=True)
        secret_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        secret.unlink()
        (source / "App.swift").write_text("// safe baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=source, check=True)
        subprocess.run([*commit_args, "-m", "safe baseline"], cwd=source, check=True)
        baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        checkout = root / "checkout"
        _create_checkout(source, baseline, checkout, strategy="git-pinned-tree-slice")
        recovered = subprocess.run(
            ["git", "show", f"{secret_commit}:validator-secret.txt"],
            cwd=checkout,
            text=True,
            capture_output=True,
            check=False,
        )
        assert recovered.returncode != 0 and "historical validator secret" not in recovered.stdout
        assert subprocess.run(["git", "cat-file", "-e", secret_commit], cwd=checkout, check=False).returncode != 0


def test_measured_repository_boundaries() -> None:
    with TemporaryDirectory() as raw:
        root = Path(raw)
        source = root / "source"
        evaluator = root / "evaluator"
        other = root / "other"
        for repository in (source, evaluator, other):
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
        plan = evaluator / "run-plan.json"
        case = evaluator / "case.json"
        adapter = evaluator / "executor.py"
        outsider = other / "validator.py"
        for path in (plan, case, adapter, outsider):
            path.write_text("fixture\n", encoding="utf-8")
        assert _verify_measured_repository_boundaries(source, plan, [plan, case, adapter]) == evaluator.resolve()
        try:
            _verify_measured_repository_boundaries(source, plan, [plan, case, outsider])
        except RunnerError as exc:
            assert "same reviewed plan repository" in str(exc)
        else:
            raise AssertionError("measured evaluator artifacts must share one reviewed repository")
        nested_source = evaluator / "code"
        nested_source.mkdir()
        try:
            _verify_measured_repository_boundaries(nested_source, plan, [plan, case, adapter])
        except RunnerError as exc:
            assert "must not overlap" in str(exc)
        else:
            raise AssertionError("measured evaluator and code repositories must not overlap")


def test_ui_ir_adversarial(ui_ir: dict) -> None:
    mutations = []
    for path, value in (
        (("source", "kind"), "web"),
        (("reference", "scale"), -3),
        (("reference", "appearance"), "sepia"),
        (("environment", "platform"), "web"),
        (("tree", "type"), "layer"),
        (("tree", "provenance", "source"), "design_variable"),
        (("unknowns", 0, "severity"), "maybe"),
        (("reference", "viewport", "width"), True),
        (("reference", "scale"), float("nan")),
    ):
        candidate = deepcopy(ui_ir)
        target = candidate
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        mutations.append(candidate)
    extra = deepcopy(ui_ir)
    extra["unexpected"] = True
    mutations.append(extra)
    fixed_without_value = deepcopy(ui_ir)
    del fixed_without_value["tree"]["children"][0]["layout"]["height"]["value"]
    mutations.append(fixed_without_value)
    for candidate in mutations:
        expect_invalid(candidate, "ui-ir")

    duplicate_node = deepcopy(ui_ir)
    duplicate_node["tree"]["children"].append(deepcopy(duplicate_node["tree"]["children"][0]))
    expect_invalid(duplicate_node, "ui-ir", "duplicate")

    broken_transition = deepcopy(ui_ir)
    broken_transition["state"]["transitions"][0]["to"] = "missing-scene"
    expect_invalid(broken_transition, "ui-ir", "reference")

    broken_region = deepcopy(ui_ir)
    broken_region["validation"]["required_regions"] = ["missing-region"]
    expect_invalid(broken_region, "ui-ir", "reference")


def test_evidence_adversarial(evidence: dict) -> None:
    for path, value in (
        (("source", "kind"), "web"),
        (("snapshot", "scale"), 0),
        (("snapshot", "appearance"), "sepia"),
        (("unknowns", 0, "severity"), "maybe"),
    ):
        candidate = deepcopy(evidence)
        target = candidate
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        expect_invalid(candidate, "design-evidence")
    duplicate_layer = deepcopy(evidence)
    duplicate_layer["extracted"]["layers"].append(deepcopy(duplicate_layer["extracted"]["layers"][0]))
    expect_invalid(duplicate_layer, "design-evidence", "duplicate")


def test_packet_adversarial(packet: dict) -> None:
    mutations = []
    for path, value in (
        (("task", "target_kind"), "vector"),
        (("reference", "image"), ""),
        (("tokens",), {}),
        (("nodes", 0, "id"), 42),
        (("bindings", 0, "framework"), "Web"),
    ):
        candidate = deepcopy(packet)
        target = candidate
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = value
        mutations.append(candidate)
    for candidate in mutations:
        expect_invalid(candidate, "agent-packet")

    for field, missing in (
        ("target_id", "missing-target"),
        ("parent", "missing-parent"),
        ("token_refs", ["missing-token"]),
        ("binding_refs", ["missing-binding"]),
    ):
        candidate = deepcopy(packet)
        if field == "target_id":
            candidate["task"][field] = missing
        else:
            candidate["nodes"][1][field] = missing
        expect_invalid(candidate, "agent-packet", "reference")

    target_type_mismatch = deepcopy(packet)
    target_type_mismatch["task"]["target_id"] = "root"
    expect_invalid(target_type_mismatch, "agent-packet", "target.type")

    self_cycle = deepcopy(packet)
    self_cycle["nodes"][0]["parent"] = "root"
    expect_invalid(self_cycle, "agent-packet", "tree.")

    two_node_cycle = deepcopy(packet)
    two_node_cycle["nodes"][0]["parent"] = "intensity"
    expect_invalid(two_node_cycle, "agent-packet", "tree.")

    over_budget = deepcopy(packet)
    over_budget["context_budget"] = {
        "estimated_tokens": 0,
        "max_tokens": 1,
        "within_budget": False,
    }
    sync_packet_budget(over_budget)
    _, diagnostics, blocking = validate(over_budget, "agent-packet")
    assert not diagnostics, [item.as_dict() for item in diagnostics]
    assert blocking
    with TemporaryDirectory() as directory:
        path = Path(directory) / "over-budget.json"
        path.write_text(json.dumps(over_budget), encoding="utf-8")
        process = subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert process.returncode == 2, process.stdout + process.stderr

    forged_budget = deepcopy(packet)
    forged_budget["context_budget"] = {"estimated_tokens": 0, "max_tokens": 1, "within_budget": True}
    expect_invalid(forged_budget, "agent-packet", "consistency")


def test_registry_adversarial(registry: dict) -> None:
    duplicate = deepcopy(registry)
    duplicate["entries"].append(deepcopy(duplicate["entries"][0]))
    expect_invalid(duplicate, "component-registry", "duplicate")

    missing_required_binding = deepcopy(registry)
    missing_required_binding["entries"][0]["bindings"] = []
    expect_invalid(missing_required_binding, "component-registry", "binding")

    invalid_status = deepcopy(registry)
    invalid_status["entries"][0]["status"] = "guessed"
    expect_invalid(invalid_status, "component-registry", "schema.")

    unreviewed_active = deepcopy(registry)
    unreviewed_active["entries"][0]["provenance"] = {"source": "source-index", "confidence": "heuristic"}
    expect_invalid(unreviewed_active, "component-registry", "schema.")


def test_swift_component_index() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "Components.swift"
        source.write_text(
            """
import SwiftUI
import UIKit
@MainActor public struct FixtureCard: View { var body: some View { EmptyView() } }
final class IntensitySlider: UIControl {}
final class DetailController: UIViewController {}
struct FixtureModel: Codable {}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        entries = scan([root], "LightingUI", root)
        assert [item["bindings"][0]["symbol"] for item in entries] == [
            "DetailController",
            "FixtureCard",
            "IntensitySlider",
        ]
        assert all(item["status"] == "pending-review" for item in entries)
        assert all(item["provenance"]["confidence"] == "heuristic" for item in entries)
        assert all("availability" not in item["bindings"][0] for item in entries)
        assert all(item["bindings"][0]["declaration_line"] > 0 for item in entries)


def test_context_compiler(ui_ir: dict, registry: dict) -> dict:
    packet = compile_packet(ui_ir, registry, "intensity", "component", [], 6000)
    _, diagnostics, blocking = validate(packet, "agent-packet")
    assert not diagnostics, [item.as_dict() for item in diagnostics]
    assert not blocking, blocking
    assert [item["id"] for item in packet["nodes"]] == ["root", "intensity"]
    assert packet["nodes"][1]["binding_refs"] == ["binding.intensity.uikit"]
    assert packet["tokens"] == [{"id": "spacing.page.horizontal", "value": 24}]
    assert packet["nodes"][1]["style"] == ui_ir["tree"]["children"][0]["style"]
    assert packet["nodes"][1]["node_state"] == ui_ir["tree"]["children"][0]["state"]
    assert packet["nodes"][1]["component"]["design_id"] == "Control/Slider/Intensity"
    assert packet["environment"] == ui_ir["environment"]
    assert packet["reference"]["viewport"] == ui_ir["reference"]["viewport"]
    assert packet["responsive"] == ui_ir["responsive"]
    assert packet["accessibility"] == ui_ir["accessibility"]
    assert [item["id"] for item in packet["states"]] == ["default", "ota-available"]
    assert [item["id"] for item in packet["interactions"]] == ["transition.0"]
    assert packet["interactions"][0]["presentation"] == "confirmation-sheet"

    responsive_ir = deepcopy(ui_ir)
    responsive_ir["tokens"]["spacing"]["regular"] = deepcopy(responsive_ir["tokens"]["spacing"]["page.horizontal"])
    responsive_ir["responsive"][0]["layout"]["horizontal_margin_token"] = "spacing.regular"
    responsive_packet = compile_packet(responsive_ir, registry, "intensity", "component", [], 6000)
    assert "spacing.regular" in {item["id"] for item in responsive_packet["tokens"]}

    dependency_ir = deepcopy(ui_ir)
    label = deepcopy(dependency_ir["tree"]["children"][0])
    label.update({"id": "intensity-label", "type": "primitive", "role": "label"})
    label.pop("component")
    label.pop("state")
    dependency_ir["tree"]["children"].insert(0, label)
    dependency_ir["tree"]["children"][1]["layout"]["top"] = {"relative_to": "intensity-label", "value": 8}
    dependency_packet = compile_packet(dependency_ir, registry, "intensity", "component", [], 6000)
    assert {item["id"] for item in dependency_packet["nodes"]} == {"root", "intensity-label", "intensity"}

    unrelated_ir = deepcopy(ui_ir)
    unrelated_ir["tokens"]["spacing"]["unrelated"] = deepcopy(unrelated_ir["tokens"]["spacing"]["page.horizontal"])
    unrelated = deepcopy(unrelated_ir["tree"]["children"][0])
    unrelated.update({"id": "unrelated", "type": "primitive", "role": "unrelated"})
    unrelated.pop("component")
    unrelated["style"] = {"padding_token": "spacing.unrelated"}
    unrelated_ir["tree"]["children"].append(unrelated)
    scoped = compile_packet(unrelated_ir, registry, "intensity", "component", [], 6000)
    assert "unrelated" not in {item["id"] for item in scoped["nodes"]}
    assert "spacing.unrelated" not in {item["id"] for item in scoped["tokens"]}

    stale = deepcopy(registry)
    stale["entries"][0]["status"] = "stale"
    blocked_packet = compile_packet(ui_ir, stale, "intensity", "component", [], 6000)
    _, diagnostics, blocking = validate(blocked_packet, "agent-packet")
    assert not diagnostics
    assert any(item["source"] == "component-registry" for item in blocking)

    framework_mismatch = deepcopy(registry)
    framework_mismatch["entries"][0]["bindings"][0]["framework"] = "SwiftUI"
    mismatched_packet = compile_packet(ui_ir, framework_mismatch, "intensity", "component", [], 6000)
    _, diagnostics, blocking = validate(mismatched_packet, "agent-packet")
    assert not diagnostics
    assert any("framework intent" in item["reason"] for item in blocking)

    ambiguous_ir = deepcopy(ui_ir)
    ambiguous_ir["tree"]["children"][0]["component"]["reuse_policy"] = "preferred"
    ambiguous_registry = deepcopy(registry)
    ambiguous_registry["entries"][0]["reuse_policy"] = "preferred"
    second_binding = deepcopy(ambiguous_registry["entries"][0]["bindings"][0])
    second_binding["id"] = "binding.intensity.uikit.alternate"
    ambiguous_registry["entries"][0]["bindings"].append(second_binding)
    ambiguous_packet = compile_packet(ambiguous_ir, ambiguous_registry, "intensity", "component", [], 6000)
    _, diagnostics, blocking = validate(ambiguous_packet, "agent-packet")
    assert not diagnostics
    assert any("ambiguous" in item["reason"] and item["severity"] == "blocking" for item in blocking)

    over_budget = compile_packet(ui_ir, registry, "intensity", "component", [], 1)
    _, diagnostics, blocking = validate(over_budget, "agent-packet")
    assert not diagnostics
    assert blocking

    blocked_ir = deepcopy(ui_ir)
    blocked_ir["unknowns"][0]["severity"] = "blocking"
    preserved = compile_packet(blocked_ir, registry, "intensity", "component", [], 6000)
    _, diagnostics, blocking = validate(preserved, "agent-packet")
    assert not diagnostics
    assert any(item["path"] == "tree.intensity.motion.duration" for item in blocking)
    return packet


def test_implementation_manifest(packet: dict, ui_ir: dict, complete_manifest: dict) -> None:
    _, diagnostics, blocking = validate(complete_manifest, "implementation-manifest", base_dir=REFERENCES)
    assert not diagnostics
    assert not blocking

    incomplete = deepcopy(complete_manifest)
    incomplete["mappings"][0]["preview_scene"] = ""
    expect_invalid(incomplete, "implementation-manifest", "completion")

    _, diagnostics, blocking = validate(complete_manifest, "implementation-manifest")
    assert not diagnostics
    assert blocking and blocking[0]["path"] == "source"

    mismatched_mapping = deepcopy(complete_manifest)
    mismatched_mapping["mappings"][0]["code_symbol"] = "InventedSlider"
    _, diagnostics, _ = validate(mismatched_mapping, "implementation-manifest", base_dir=REFERENCES)
    assert any(item.code == "artifact.mapping" for item in diagnostics)

    mismatched_hash = deepcopy(complete_manifest)
    mismatched_hash["source"]["agent_packet"]["sha256"] = f"sha256:{'0' * 64}"
    _, diagnostics, _ = validate(mismatched_hash, "implementation-manifest", base_dir=REFERENCES)
    assert any(item.code == "artifact.hash" for item in diagnostics)

    mismatched_evidence = deepcopy(complete_manifest)
    mismatched_evidence["validation"]["evidence"][0]["sha256"] = f"sha256:{'0' * 64}"
    _, diagnostics, _ = validate(mismatched_evidence, "implementation-manifest", base_dir=REFERENCES)
    assert any(item.code == "artifact.hash" for item in diagnostics)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        expanded_packet = deepcopy(packet)
        expanded_packet["acceptance"]["required_regions"] = ["root", "intensity"]
        sync_packet_budget(expanded_packet)
        packet_path = root / "agent-packet.json"
        ui_ir_path = root / "ui-ir.json"
        evidence_path = root / "validation.json"
        packet_path.write_text(json.dumps(expanded_packet), encoding="utf-8")
        ui_ir_path.write_text(json.dumps(ui_ir), encoding="utf-8")
        evidence_path.write_bytes((REFERENCES / "implementation-validation-example.json").read_bytes())
        incomplete_coverage = deepcopy(complete_manifest)
        incomplete_coverage["source"] = {
            "ui_ir": {"path": ui_ir_path.name, "sha256": f"sha256:{hashlib.sha256(ui_ir_path.read_bytes()).hexdigest()}"},
            "agent_packet": {"path": packet_path.name, "sha256": f"sha256:{hashlib.sha256(packet_path.read_bytes()).hexdigest()}"},
        }
        incomplete_coverage["validation"]["evidence"][0] = {
            "kind": "semantic-visual-validation",
            "path": evidence_path.name,
            "sha256": f"sha256:{hashlib.sha256(evidence_path.read_bytes()).hexdigest()}",
        }
        _, diagnostics, _ = validate(incomplete_coverage, "implementation-manifest", base_dir=root)
        assert any(item.code == "artifact.coverage" and "root" in item.message for item in diagnostics)

    with TemporaryDirectory() as directory:
        root = Path(directory)
        packet_path = root / "packet.json"
        ui_ir_path = root / "ui-ir.json"
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        ui_ir_path.write_text(json.dumps(ui_ir), encoding="utf-8")
        draft = initialize(packet, packet_path, ui_ir_path)
        _, diagnostics, blocking = validate(draft, "implementation-manifest")
        assert not diagnostics
        assert blocking and blocking[0]["path"] == "status"

        missing_token_packet = deepcopy(packet)
        missing_token_packet["tokens"] = []
        for node in missing_token_packet["nodes"]:
            node["token_refs"] = []
        sync_packet_budget(missing_token_packet)
        packet_path.write_text(json.dumps(missing_token_packet), encoding="utf-8")
        try:
            initialize(missing_token_packet, packet_path, ui_ir_path)
        except ValueError as exc:
            assert "token" in str(exc)
        else:
            raise AssertionError("initializer must reject incomplete token closure")

        missing_state_packet = deepcopy(packet)
        missing_state_packet["states"] = [missing_state_packet["states"][0]]
        missing_state_packet["interactions"] = []
        for node in missing_state_packet["nodes"]:
            node["state_refs"] = ["default"]
            node["interaction_refs"] = []
        sync_packet_budget(missing_state_packet)
        packet_path.write_text(json.dumps(missing_state_packet), encoding="utf-8")
        try:
            initialize(missing_state_packet, packet_path, ui_ir_path)
        except ValueError as exc:
            assert "state" in str(exc) or "interaction" in str(exc)
        else:
            raise AssertionError("initializer must reject incomplete state closure")

        invented_binding_packet = deepcopy(packet)
        binding = invented_binding_packet["bindings"][0]
        binding.update({"framework": "SwiftUI", "symbol": "InventedSlider", "source": "Invented.swift"})
        invented_binding_packet["code_anchors"][0].update({"symbol": "InventedSlider", "source": "Invented.swift"})
        sync_packet_budget(invented_binding_packet)
        packet_path.write_text(json.dumps(invented_binding_packet), encoding="utf-8")
        try:
            initialize(invented_binding_packet, packet_path, ui_ir_path)
        except ValueError as exc:
            assert "binding" in str(exc)
        else:
            raise AssertionError("initializer must reject invented binding")

        downgraded_acceptance = deepcopy(packet)
        downgraded_acceptance["acceptance"]["required_regions"] = ["root"]
        sync_packet_budget(downgraded_acceptance)
        packet_path.write_text(json.dumps(downgraded_acceptance), encoding="utf-8")
        try:
            initialize(downgraded_acceptance, packet_path, ui_ir_path)
        except ValueError as exc:
            assert "acceptance" in str(exc)
        else:
            raise AssertionError("initializer must reject downgraded acceptance regions")

        packet_path.write_text(json.dumps(packet), encoding="utf-8")

        mismatched_ui_ir = deepcopy(ui_ir)
        mismatched_ui_ir["source"]["evidence_hash"] = "sha256:different-evidence"
        ui_ir_path.write_text(json.dumps(mismatched_ui_ir), encoding="utf-8")
        try:
            initialize(packet, packet_path, ui_ir_path)
        except ValueError as exc:
            assert "evidence hash" in str(exc)
        else:
            raise AssertionError("initializer must reject mismatched UI IR")

        mismatched_ui_ir = deepcopy(ui_ir)
        mismatched_ui_ir["environment"]["device"] = "DifferentDevice"
        ui_ir_path.write_text(json.dumps(mismatched_ui_ir), encoding="utf-8")
        try:
            initialize(packet, packet_path, ui_ir_path)
        except ValueError as exc:
            assert "environment" in str(exc)
        else:
            raise AssertionError("initializer must reject mismatched environment")


def _measured_benchmark(benchmark: dict, directory: Path) -> dict:
    measured = deepcopy(benchmark)
    measured["evidence_status"] = "measured"
    baseline_repo = directory / "baseline-repo"
    baseline_repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=baseline_repo, check=True)
    (baseline_repo / "Generated.swift").write_text("// benchmark baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "Generated.swift"], cwd=baseline_repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=Benchmark Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "benchmark baseline"],
        cwd=baseline_repo,
        check=True,
    )
    baseline_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=baseline_repo, text=True).strip()
    commit_object = subprocess.check_output(["git", "cat-file", "commit", baseline_commit], cwd=baseline_repo)
    provider_scope = {"mode": "allowlist", "entries": [{"kind": "file", "path": "Generated.swift"}]}
    provider_source_manifest = _provider_source_manifest(baseline_repo, baseline_commit, provider_scope)
    provider_source_manifest_path = directory / "provider-source-manifest.json"
    provider_source_manifest_path.write_text(json.dumps(provider_source_manifest), encoding="utf-8")
    provider_source_manifest_hash = hashlib.sha256(provider_source_manifest_path.read_bytes()).hexdigest()
    measured["environment"]["code_baseline"] = baseline_commit
    measured["environment"]["code_baseline_hash"] = hashlib.sha256(commit_object).hexdigest()
    viewport_parts = measured["environment"]["viewport"].split("@", 1)[0].split("x", 1)
    viewport = {"width": int(viewport_parts[0]), "height": int(viewport_parts[1])}
    adapter = directory / "measured-adapter"
    adapter.write_text("measured adapter fixture\n", encoding="utf-8")
    capture_adapter = directory / "measured-capture"
    capture_adapter.write_text("measured capture fixture\n", encoding="utf-8")
    capture_overlay = directory / "capture-overlay.patch"
    capture_overlay.write_text(
        "diff --git a/Generated.swift b/Generated.swift\n--- a/Generated.swift\n+++ b/Generated.swift\n@@ -1 +1 @@\n-// benchmark baseline\n+// evaluator capture overlay\n",
        encoding="utf-8",
    )
    capture_overlay_hash = hashlib.sha256(capture_overlay.read_bytes()).hexdigest()
    validator_adapter = directory / "measured-validator"
    validator_adapter.write_text("measured validator fixture\n", encoding="utf-8")
    verification_wrapper = directory / "verification-wrapper"
    verification_wrapper.write_text("measured verification wrapper fixture\n", encoding="utf-8")
    simctl = directory / "simctl"
    simctl.write_text("measured simctl fixture\n", encoding="utf-8")
    dependency_generator = directory / "evaluator-dependency-generator"
    dependency_generator.write_text("measured evaluator dependency generator fixture\n", encoding="utf-8")
    clang = directory / "clang"
    clang.write_text("measured clang fixture\n", encoding="utf-8")
    sdk = directory / "iPhoneSimulator26.5.sdk"
    sdk.mkdir()
    sdk_settings = sdk / "SDKSettings.plist"
    sdk_settings.write_text("measured SDK settings fixture\n", encoding="utf-8")
    dependency_generator_hash = hashlib.sha256(dependency_generator.read_bytes()).hexdigest()
    capture_runtime = {
        "mode": "ios-simulator",
        "verification_wrapper": {
            "path": str(verification_wrapper.resolve()),
            "sha256": hashlib.sha256(verification_wrapper.read_bytes()).hexdigest(),
        },
        "simctl": {
            "path": str(simctl.resolve()),
            "sha256": hashlib.sha256(simctl.read_bytes()).hexdigest(),
        },
        "workspace": "Acrux/Acrux.xcworkspace",
        "scheme": "Acrux_DEV",
        "destination": {
            "udid": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
            "runtime": "com.apple.CoreSimulator.SimRuntime.iOS-26-5",
            "runtime_version": "26.5",
            "runtime_build_version": "23F77",
            "device_name": "iPad Pro 13-inch (M5)",
            "device_type_identifier": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-12GB",
        },
        "test_selector": "AcruxUITests/Test/testCapture",
        "app_bundle_id": "com.example.capture",
        "artifacts": {"screenshot": "actual.png", "raw_probe": "raw.json"},
        "evaluator_dependency_setup": {
            "mode": "unityframework-arm64-simulator-stub-v1",
            "generator": {
                "path": str(dependency_generator.resolve()),
                "sha256": dependency_generator_hash,
            },
            "clang": {
                "path": str(clang.resolve()),
                "sha256": hashlib.sha256(clang.read_bytes()).hexdigest(),
            },
            "sdk": {
                "path": str(sdk.resolve()),
                "version": "26.5",
                "build_version": "23F73",
                "settings_sha256": hashlib.sha256(sdk_settings.read_bytes()).hexdigest(),
            },
            "xcframework_path": "Acrux/Pods/UnityFramework.xcframework",
            "pod_copy_script_path": "Acrux/Pods/copy.sh",
            "baseline": {
                "xcframework_info_sha256": "a" * 64,
                "pod_copy_script_sha256": "b" * 64,
            },
            "product": {
                "binary_sha256": "c" * 64,
                "header_sha256": "d" * 64,
                "modulemap_sha256": "e" * 64,
                "framework_info_sha256": "f" * 64,
            },
        },
    }
    capture_runtime_hash = hashlib.sha256(
        json.dumps(capture_runtime, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    run_plan = {
        "run_plan_version": "1.2.0",
        "plan_id": "measured.self-test",
        "evidence_status": "measured",
        "case": {"path": "case.json", "sha256": "8" * 64},
        "executor": {
            "model": measured["environment"]["model"],
            "reasoning": measured["environment"]["reasoning"],
            "synthetic": False,
            "provider_cli": {
                "name": "openai-codex-cli",
                "version": "codex-cli 0.0.0",
                "launcher_path": str(adapter.resolve()),
                "native_path": str(adapter.resolve()),
                "launcher_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
                "native_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
                "package_json_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            },
            "adapter": {"path": adapter.name, "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest()},
            "implementation_command": ["{adapter}", "implementation"],
            "timeout_seconds": 60,
            "environment": {},
        },
        "validator": {
            "id": "measured-self-test-validator",
            "synthetic": False,
            "capture_adapter": {"path": capture_adapter.name, "sha256": hashlib.sha256(capture_adapter.read_bytes()).hexdigest()},
            "capture_overlay": {
                "mode": "git-patch",
                "artifact": {"path": capture_overlay.name, "sha256": capture_overlay_hash},
            },
            "capture_runtime": capture_runtime,
            "capture_command": ["{capture}", "capture"],
            "adapter": {"path": validator_adapter.name, "sha256": hashlib.sha256(validator_adapter.read_bytes()).hexdigest()},
            "command": ["{validator}", "validation"],
            "timeout_seconds": 60,
            "environment": {},
        },
        "isolation": {
            "strategy": "git-pinned-tree-slice",
            "run_order": ["screenshot-only", "ui-ir", "ui-ir-with-binding"],
            "clean_checkout": True,
        },
    }
    run_plan_path = directory / "run-plan.json"
    run_plan_path.write_text(json.dumps(run_plan), encoding="utf-8")
    run_plan_hash = hashlib.sha256(run_plan_path.read_bytes()).hexdigest()
    benchmark_case_data = deepcopy(load_json(REFERENCES / "benchmark-cases" / "au-create-project-alert" / "benchmark-case.json"))
    benchmark_case_data["case_id"] = measured["case_id"]
    benchmark_case_data["source"]["code"] = {
        "root": "repository",
        "git_commit": baseline_commit,
        "provider_source_scope": {
            **provider_scope,
            "expected_file_count": provider_source_manifest["file_count"],
            "expected_total_bytes": provider_source_manifest["total_bytes"],
            "expected_content_sha256": provider_source_manifest["content_sha256"],
        },
        "files": [
            {
                "root": "repository",
                "path": "Generated.swift",
                "sha256": hashlib.sha256(b"// benchmark baseline\n").hexdigest(),
            }
        ],
    }
    benchmark_case = directory / "benchmark-case.json"
    benchmark_case.write_text(json.dumps(benchmark_case_data), encoding="utf-8")
    benchmark_case_hash = hashlib.sha256(benchmark_case.read_bytes()).hexdigest()
    run_plan["case"] = {"path": benchmark_case.name, "sha256": benchmark_case_hash}
    run_plan_path.write_text(json.dumps(run_plan), encoding="utf-8")
    run_plan_hash = hashlib.sha256(run_plan_path.read_bytes()).hexdigest()
    measured["environment"].update(
        {
            "run_plan_hash": run_plan_hash,
            "benchmark_case_hash": benchmark_case_hash,
            "executor_adapter_hash": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            "validator_id": run_plan["validator"]["id"],
            "capture_adapter_hash": hashlib.sha256(capture_adapter.read_bytes()).hexdigest(),
            "capture_overlay_mode": "git-patch",
            "capture_overlay_hash": capture_overlay_hash,
            "capture_runtime_hash": capture_runtime_hash,
            "validator_adapter_hash": hashlib.sha256(validator_adapter.read_bytes()).hexdigest(),
            "adapter_runtime": measured["environment"].get("adapter_runtime", "/usr/bin/python3"),
            "adapter_runtime_version": measured["environment"].get("adapter_runtime_version", "3.x"),
            "provider_cli_name": "openai-codex-cli",
            "provider_cli_version": "codex-cli 0.0.0",
            "provider_cli_launcher_path": str(adapter.resolve()),
            "provider_cli_native_path": str(adapter.resolve()),
            "provider_cli_launcher_hash": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            "provider_cli_native_hash": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            "provider_cli_package_json_hash": hashlib.sha256(adapter.read_bytes()).hexdigest(),
        }
    )
    for candidate in measured["candidates"]:
        run_dir = directory / candidate["variant"]
        input_dir = run_dir / "input"
        input_dir.mkdir(parents=True)
        checkout = run_dir / "checkout"
        _create_checkout(baseline_repo, baseline_commit, checkout, strategy="git-pinned-tree-slice")
        provider_worktree = run_dir / "provider-worktree"
        (
            provider_baseline,
            provider_objects,
            _,
            provider_metadata_hash,
        ) = _create_provider_worktree(checkout, provider_worktree, provider_source_manifest)
        png_header = make_png(viewport["width"], viewport["height"])
        reference = input_dir / "reference.png"
        reference.write_bytes(png_header)
        prompt = input_dir / "shared-prompt.md"
        prompt.write_text("measured test prompt\n", encoding="utf-8")
        validation = {
            "config_version": "1.1.0",
            "reference_viewport": viewport,
            "reference_scale": 3,
            "appearance": "dark",
            "locale": measured["environment"]["locale"],
            "required_regions": ["root"],
            "reference_regions": [
                {
                    "id": "root",
                    "frame": {"x": 0, "y": 0, "width": viewport["width"], "height": viewport["height"]},
                    "runtime_type": "RootView",
                    "accessibility_identifier": "benchmark.root",
                    "parent_id": None,
                    "child_ids": [],
                }
            ],
            "required_bindings": [
                {
                    "id": f"binding-{index}",
                    "registry_entry_id": f"component-{index}",
                    "code_symbol": f"Binding{index}",
                    "source": "Generated.swift",
                    "region_id": "root",
                    "runtime_type": f"Binding{index}",
                }
                for index in range(10)
            ],
            "required_anchors": [
                {"region_id": "root", "anchors": [{"id": "max-anchor", "metric": "position"}]}
            ],
            "ignore_regions": [],
            "pixel_diff": {"max_channel_delta": 0, "max_different_pixel_ratio": 0},
            "metrics": {
                "layout_deviation": "max-anchor-deviation-pt",
                "component_reuse": "required-binding-coverage",
                "magic_numbers": "unmapped-layout-literal-count",
                "repair_iterations": "accepted-repair-rounds",
                "input_tokens": "actual-model-input-tokens",
                "manual_minutes": "human-intervention-minutes",
            },
            "thresholds": measured["thresholds"],
        }
        validation_path = input_dir / "validation-config.json"
        validation_path.write_text(json.dumps(validation), encoding="utf-8")
        measured["environment"]["shared_prompt_hash"] = hashlib.sha256(prompt.read_bytes()).hexdigest()
        measured["environment"]["validation_config_hash"] = hashlib.sha256(validation_path.read_bytes()).hexdigest()
        inputs = [
            {"kind": "reference", "audience": "agent", "path": "input/reference.png", "sha256": hashlib.sha256(reference.read_bytes()).hexdigest()},
            {"kind": "shared-prompt", "audience": "agent", "path": "input/shared-prompt.md", "sha256": measured["environment"]["shared_prompt_hash"]},
            {"kind": "validation-config", "audience": "validator", "path": "input/validation-config.json", "sha256": measured["environment"]["validation_config_hash"]},
        ]
        context_kind = "ui-ir" if candidate["variant"] == "ui-ir" else ("agent-packet" if candidate["variant"] == "ui-ir-with-binding" else None)
        if context_kind:
            context_path = input_dir / ("ui-ir.json" if context_kind == "ui-ir" else "agent-packet.json")
            context_path.write_text("{}\n", encoding="utf-8")
            inputs.append(
                {
                    "kind": context_kind,
                    "audience": "agent",
                    "path": f"input/{context_path.name}",
                    "sha256": hashlib.sha256(context_path.read_bytes()).hexdigest(),
                }
            )
        input_context = {
            "input_context_version": "1.2.0",
            "case_id": measured["case_id"],
            "variant": candidate["variant"],
            "plan_sha256": run_plan_hash,
            "run_plan": {"path": "run-plan.json", "sha256": run_plan_hash},
            "benchmark_case": {"path": "benchmark-case.json", "sha256": benchmark_case_hash},
            "executor_adapter": {"path": "executor-adapter", "sha256": hashlib.sha256(adapter.read_bytes()).hexdigest()},
            "capture_adapter": {"path": "capture-adapter", "sha256": hashlib.sha256(capture_adapter.read_bytes()).hexdigest()},
            "capture_overlay": {
                "mode": "git-patch",
                "artifact": {"path": "capture-overlay.patch", "sha256": capture_overlay_hash},
            },
            "provider_source_scope": {
                "mode": "allowlist",
                "artifact": {
                    "path": "provider-source-manifest.json",
                    "sha256": provider_source_manifest_hash,
                },
                "file_count": provider_source_manifest["file_count"],
                "total_bytes": provider_source_manifest["total_bytes"],
                "content_sha256": provider_source_manifest["content_sha256"],
                "worktree": {
                    "path": "provider-worktree",
                    "baseline_commit": provider_baseline,
                    "object_set_sha256": hashlib.sha256(
                        json.dumps(sorted(provider_objects), separators=(",", ":")).encode("utf-8")
                    ).hexdigest(),
                    "git_metadata_sha256": provider_metadata_hash,
                },
            },
            "evaluator_dependency_setup": {
                "mode": "unityframework-arm64-simulator-stub-v1",
                "artifact": {
                    "path": "evaluator-dependency-generator",
                    "sha256": dependency_generator_hash,
                },
            },
            "validator_adapter": {"path": "validator-adapter", "sha256": hashlib.sha256(validator_adapter.read_bytes()).hexdigest()},
            "environment": {
                "task_mode": "reuse-conformance",
                "screen": measured["environment"]["screen"],
                "state": measured["environment"]["state"],
                "viewport": viewport,
                "scale": 3,
                "appearance": "dark",
                "locale": measured["environment"]["locale"],
                "ui_framework": "UIKit",
            },
            "inputs": inputs,
        }
        input_context_path = run_dir / "input-context.json"
        shutil.copyfile(run_plan_path, run_dir / "run-plan.json")
        shutil.copyfile(benchmark_case, run_dir / "benchmark-case.json")
        shutil.copyfile(adapter, run_dir / "executor-adapter")
        shutil.copyfile(capture_adapter, run_dir / "capture-adapter")
        shutil.copyfile(capture_overlay, run_dir / "capture-overlay.patch")
        shutil.copyfile(provider_source_manifest_path, run_dir / "provider-source-manifest.json")
        shutil.copyfile(dependency_generator, run_dir / "evaluator-dependency-generator")
        shutil.copyfile(validator_adapter, run_dir / "validator-adapter")
        input_context_path.write_text(json.dumps(input_context), encoding="utf-8")
        provider_id = f"provider-{candidate['variant']}"
        provider_events = [
            {"type": "thread.started", "thread_id": provider_id},
            {"type": "turn.started"},
            {"item": {"id": "item_0", "type": "agent_message"}, "type": "item.completed"},
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": candidate["input_tokens"],
                    "cached_input_tokens": 0,
                    "output_tokens": 100,
                    "reasoning_output_tokens": 0,
                },
            },
        ]
        (run_dir / "implementation.stdout.log").write_text(
            "".join(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n" for event in provider_events),
            encoding="utf-8",
        )
        for log_name in ("implementation.stderr.log", "capture.stdout.log", "capture.stderr.log", "validation.stdout.log", "validation.stderr.log"):
            (run_dir / log_name).write_text(f"self-test {log_name}\n", encoding="utf-8")
        actual = run_dir / "actual.png"
        actual.write_bytes(png_header)
        binding_count = 10
        reused_count = round(candidate["component_reuse_rate"] * binding_count)
        actual_root_frame = {
            "x": candidate["layout_deviation_pt"],
            "y": 0,
            "width": viewport["width"] - candidate["layout_deviation_pt"],
            "height": viewport["height"],
        }
        probe = run_dir / "validator-probe.json"
        probe_payload = {
            "validator_probe_version": "1.0.0",
            "case_id": measured["case_id"],
            "variant": candidate["variant"],
            "validator_id": run_plan["validator"]["id"],
            "capture_adapter_sha256": hashlib.sha256(capture_adapter.read_bytes()).hexdigest(),
            "environment": {
                "viewport": viewport,
                "scale": 3,
                "appearance": "dark",
                "locale": measured["environment"]["locale"],
            },
            "actual_screenshot": {"path": actual.name, "sha256": hashlib.sha256(actual.read_bytes()).hexdigest()},
            "regions": [
                {
                    "id": "root",
                    "frame": actual_root_frame,
                    "runtime_type": "RootView",
                    "accessibility_identifier": "benchmark.root",
                    "visible": True,
                    "parent_id": None,
                    "child_ids": [],
                }
            ],
            "bindings": [
                {"id": f"binding-{index}", "region_id": "root", "runtime_type": f"Binding{index}"}
                for index in range(reused_count)
            ],
        }
        probe.write_text(json.dumps(probe_payload), encoding="utf-8")
        probe_hash = hashlib.sha256(probe.read_bytes()).hexdigest()
        source_lines = [f"final class Binding{index} {{}} // reused={index < reused_count}" for index in range(binding_count)]
        source_lines.extend(f"view.frame.origin.x = CGFloat({index})" for index in range(candidate["magic_numbers"]))
        (checkout / "Generated.swift").write_text("\n".join(source_lines) + "\n", encoding="utf-8")
        (provider_worktree / "Generated.swift").write_text("\n".join(source_lines) + "\n", encoding="utf-8")
        implementation_output = run_dir / "implementation-output.patch"
        implementation_output.write_bytes(
            subprocess.check_output(
                [
                    "git",
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
            )
        )
        semantic = run_dir / "semantic.json"
        semantic_payload = {
            "semantic_evidence_version": "1.1.0",
            "case_id": measured["case_id"],
            "variant": candidate["variant"],
            "validator_id": run_plan["validator"]["id"],
            "validator_adapter_sha256": hashlib.sha256(validator_adapter.read_bytes()).hexdigest(),
            "validator_probe_sha256": probe_hash,
            "capture_adapter_sha256": hashlib.sha256(capture_adapter.read_bytes()).hexdigest(),
            "regions": [
                {
                    "id": "root",
                    "frame": actual_root_frame,
                    "structure": "passed",
                    "semantic": "passed",
                }
            ],
            "required_bindings": [
                {
                    "id": f"binding-{index}",
                    "registry_entry_id": f"component-{index}",
                    "code_symbol": f"Binding{index}",
                    "source": "Generated.swift",
                    "region_id": "root",
                    "runtime_type": f"Binding{index}",
                    "runtime_observed": index < reused_count,
                    "reused": index < reused_count,
                    "locations": ([{"path": "Generated.swift", "line": index + 1}] if index < reused_count else []),
                }
                for index in range(binding_count)
            ],
            "unmapped_literals": [
                {
                    "kind": "layout",
                    "value": str(index),
                    "location": {"path": "Generated.swift", "line": binding_count + index + 1},
                }
                for index in range(candidate["magic_numbers"])
            ],
        }
        semantic.write_text(json.dumps(semantic_payload), encoding="utf-8")
        diff = run_dir / "diff.json"
        diff_payload = {
            "visual_diff_version": "1.1.0",
            "case_id": measured["case_id"],
            "variant": candidate["variant"],
            "validator_id": run_plan["validator"]["id"],
            "validator_adapter_sha256": hashlib.sha256(validator_adapter.read_bytes()).hexdigest(),
            "validator_probe_sha256": probe_hash,
            "capture_adapter_sha256": hashlib.sha256(capture_adapter.read_bytes()).hexdigest(),
            "reference_sha256": inputs[0]["sha256"],
            "actual_sha256": hashlib.sha256(actual.read_bytes()).hexdigest(),
            "regions": [
                {
                    "id": "root",
                    "visual": "passed",
                    "layout_deviation_pt": candidate["layout_deviation_pt"],
                    "pixel_difference_ratio": 0,
                    "anchors": [
                        {
                            "id": "max-anchor",
                            "metric": "position",
                            "reference_value": [0, 0],
                            "actual_value": [candidate["layout_deviation_pt"], 0],
                            "deviation_pt": candidate["layout_deviation_pt"],
                        }
                    ],
                }
            ],
        }
        diff.write_text(json.dumps(diff_payload), encoding="utf-8")
        observation = run_dir / "run-observation.json"
        observation_payload = {
            "run_observation_version": "1.1.0",
            "case_id": measured["case_id"],
            "variant": candidate["variant"],
            "executor_adapter_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            "model": measured["environment"]["model"],
            "reasoning": measured["environment"]["reasoning"],
            "provider_cli": {
                "name": "openai-codex-cli",
                "version": "codex-cli 0.0.0",
                "launcher_path": str(adapter.resolve()),
                "native_path": str(adapter.resolve()),
                "launcher_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
                "native_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
                "package_json_sha256": hashlib.sha256(adapter.read_bytes()).hexdigest(),
            },
            "provider_event_stream_sha256": hashlib.sha256((run_dir / "implementation.stdout.log").read_bytes()).hexdigest(),
            "provider_runs": [
                {
                    "id": provider_id,
                    "input_tokens": candidate["input_tokens"],
                    "cached_input_tokens": 0,
                    "output_tokens": 100,
                    "reasoning_output_tokens": 0,
                }
            ],
            "repair_events": [
                {"id": f"repair-{index}", "provider_run_id": provider_id, "reason": "self-test repair"}
                for index in range(candidate["repair_iterations"])
            ],
            "manual_interventions": ([{"id": "manual-0", "duration_seconds": candidate["manual_minutes"] * 60, "reason": "self-test timing"}] if candidate["manual_minutes"] else []),
        }
        observation.write_text(json.dumps(observation_payload), encoding="utf-8")
        thresholds = measured["thresholds"]
        candidate_passed = all(
            (
                candidate["layout_deviation_pt"] <= thresholds["max_layout_deviation_pt"],
                candidate["component_reuse_rate"] >= thresholds["min_component_reuse_rate"],
                candidate["magic_numbers"] <= thresholds["max_magic_numbers"],
                candidate["repair_iterations"] <= thresholds["max_repair_iterations"],
                candidate["input_tokens"] <= thresholds["max_input_tokens"],
                candidate["manual_minutes"] <= thresholds["max_manual_minutes"],
            )
        )
        run_result = {
            "run_result_version": "1.1.0",
            "status": "passed" if candidate_passed else "failed",
            "variant": candidate["variant"],
            "model": measured["environment"]["model"],
            "reasoning": measured["environment"]["reasoning"],
            "code_baseline_commit": measured["environment"]["code_baseline"],
            "reference_sha256": inputs[0]["sha256"],
            "provider_run_id": provider_id,
            "model_usage": {"input_tokens": candidate["input_tokens"], "output_tokens": 100},
            "metrics": {
                key: candidate[key]
                for key in ("layout_deviation_pt", "component_reuse_rate", "magic_numbers", "repair_iterations", "manual_minutes")
            },
            "regions": [
                {
                    "id": "root",
                    "structure": "passed",
                    "semantic": "passed",
                    "visual": "passed",
                    "layout_deviation_pt": candidate["layout_deviation_pt"],
                }
            ],
            "evidence": {
                "actual_screenshot": {"path": actual.name, "sha256": hashlib.sha256(actual.read_bytes()).hexdigest()},
                "validator_probe": {"path": probe.name, "sha256": probe_hash},
                "semantic_snapshot": {"path": semantic.name, "sha256": hashlib.sha256(semantic.read_bytes()).hexdigest()},
                "visual_diff": {"path": diff.name, "sha256": hashlib.sha256(diff.read_bytes()).hexdigest()},
                "run_observation": {"path": observation.name, "sha256": hashlib.sha256(observation.read_bytes()).hexdigest()},
            },
        }
        run_result_path = run_dir / "benchmark-run-result.json"
        run_result_path.write_text(json.dumps(run_result), encoding="utf-8")
        evidence = {
            "input_context": {"path": input_context_path.name, "sha256": hashlib.sha256(input_context_path.read_bytes()).hexdigest()},
            "implementation_output": {"path": implementation_output.name, "sha256": hashlib.sha256(implementation_output.read_bytes()).hexdigest()},
            "implementation_stdout": {"path": "implementation.stdout.log", "sha256": hashlib.sha256((run_dir / "implementation.stdout.log").read_bytes()).hexdigest()},
            "implementation_stderr": {"path": "implementation.stderr.log", "sha256": hashlib.sha256((run_dir / "implementation.stderr.log").read_bytes()).hexdigest()},
            "capture_stdout": {"path": "capture.stdout.log", "sha256": hashlib.sha256((run_dir / "capture.stdout.log").read_bytes()).hexdigest()},
            "capture_stderr": {"path": "capture.stderr.log", "sha256": hashlib.sha256((run_dir / "capture.stderr.log").read_bytes()).hexdigest()},
            "validation_stdout": {"path": "validation.stdout.log", "sha256": hashlib.sha256((run_dir / "validation.stdout.log").read_bytes()).hexdigest()},
            "validation_stderr": {"path": "validation.stderr.log", "sha256": hashlib.sha256((run_dir / "validation.stderr.log").read_bytes()).hexdigest()},
            "validation_report": {"path": run_result_path.name, "sha256": hashlib.sha256(run_result_path.read_bytes()).hexdigest()},
        }
        artifact = {
            "artifact_version": "1.2.0",
            "run_id": candidate["run"]["id"],
            "variant": candidate["variant"],
            "validation_status": run_result["status"],
            "capture_overlay": {
                "mode": "git-patch",
                "artifact": {"path": "capture-overlay.patch", "sha256": capture_overlay_hash},
            },
            "environment": {
                key: measured["environment"][key]
                for key in (
                    "model",
                    "reasoning",
                    "appearance",
                    "ui_framework",
                    "adapter_runtime",
                    "adapter_runtime_version",
                    "provider_cli_name",
                    "provider_cli_version",
                    "provider_cli_launcher_path",
                    "provider_cli_native_path",
                    "provider_cli_launcher_hash",
                    "provider_cli_native_hash",
                    "provider_cli_package_json_hash",
                    "code_baseline_hash",
                    "shared_prompt_hash",
                    "design_source_hash",
                    "validation_config_hash",
                    "run_plan_hash",
                    "benchmark_case_hash",
                    "executor_adapter_hash",
                    "validator_id",
                    "capture_adapter_hash",
                    "capture_overlay_mode",
                    "capture_overlay_hash",
                    "capture_runtime_hash",
                    "validator_adapter_hash",
                )
            },
            "metrics": {
                key: candidate[key]
                for key in (
                    "layout_deviation_pt",
                    "component_reuse_rate",
                    "magic_numbers",
                    "repair_iterations",
                    "input_tokens",
                    "manual_minutes",
                )
            },
            "evidence": evidence,
        }
        artifact_path = run_dir / "run-artifact.json"
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_path"] = artifact_path.relative_to(directory).as_posix()
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    return measured


def test_benchmark_gates(benchmark: dict) -> None:
    synthetic = score(benchmark, allow_synthetic=True)
    assert synthetic["status"] == "scored"
    assert synthetic["recommendation"] == "go"
    assert score(benchmark, allow_synthetic=False)["status"] == "blocked"
    mixed_ui = deepcopy(benchmark)
    mixed_ui["environment"]["ui_framework"] = "mixed-ui"
    assert score(mixed_ui, allow_synthetic=True)["status"] == "scored"

    relabeled = deepcopy(benchmark)
    relabeled["evidence_status"] = "measured"
    assert score(relabeled, base_dir=REFERENCES)["status"] == "blocked"

    with TemporaryDirectory() as directory:
        base = Path(directory)
        dummy = deepcopy(benchmark)
        dummy["evidence_status"] = "measured"
        for candidate in dummy["candidates"]:
            path = base / f"{candidate['variant']}.json"
            path.write_text(json.dumps({"variant": candidate["variant"]}), encoding="utf-8")
            candidate["run"]["artifact_path"] = path.name
            candidate["run"]["artifact_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        assert score(dummy, base_dir=base)["status"] == "blocked"

    malformed = deepcopy(benchmark)
    malformed["thresholds"]["max_input_tokens"] = "lots"
    assert score(malformed, allow_synthetic=True)["status"] == "invalid"

    no_ui_ir_gain = deepcopy(benchmark)
    no_ui_ir_gain["candidates"][1]["layout_deviation_pt"] = no_ui_ir_gain["candidates"][0]["layout_deviation_pt"]
    assert score(no_ui_ir_gain, allow_synthetic=True)["recommendation"] == "revise"

    no_binding_gain = deepcopy(benchmark)
    no_binding_gain["candidates"][2]["component_reuse_rate"] = no_binding_gain["candidates"][1]["component_reuse_rate"]
    assert score(no_binding_gain, allow_synthetic=True)["recommendation"] == "revise"

    no_compaction = deepcopy(benchmark)
    no_compaction["candidates"][2]["input_tokens"] = no_compaction["candidates"][1]["input_tokens"] + 1
    assert score(no_compaction, allow_synthetic=True)["recommendation"] == "revise"

    failed_final_validation = deepcopy(benchmark)
    failed_final_validation["candidates"][2]["validation_status"] = "failed"
    failed_final_score = score(failed_final_validation, allow_synthetic=True)
    assert failed_final_score["recommendation"] == "revise"
    assert failed_final_score["gates"]["final_semantic_visual_validation"] is False

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        result = score(measured, base_dir=base)
        assert result["status"] == "scored"
        assert result["recommendation"] == "go"
        (base / "ui-ir" / "input-context.json").write_text("tampered", encoding="utf-8")
        assert score(measured, base_dir=base)["status"] == "blocked"

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        (base / "ui-ir" / "provider-source-manifest.json").write_text("{}\n", encoding="utf-8")
        tampered_provider_scope = score(measured, base_dir=base)
        assert tampered_provider_scope["status"] == "blocked"
        assert any(item["code"] == "artifact.hash" for item in tampered_provider_scope["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        for candidate in measured["candidates"]:
            run_dir = base / candidate["variant"]
            manifest_path = run_dir / "provider-source-manifest.json"
            manifest = load_json(manifest_path)
            manifest["files"][0]["bytes"] += 1
            # Preserve the self-reported top-level identity to exercise independent recomputation.
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            context_path = run_dir / "input-context.json"
            context = load_json(context_path)
            context["provider_source_scope"]["artifact"]["sha256"] = manifest_hash
            context_path.write_text(json.dumps(context), encoding="utf-8")
            artifact_path = run_dir / "run-artifact.json"
            artifact = load_json(artifact_path)
            artifact["evidence"]["input_context"]["sha256"] = hashlib.sha256(context_path.read_bytes()).hexdigest()
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        coherent_manifest_tamper = score(measured, base_dir=base)
        assert coherent_manifest_tamper["status"] == "blocked"
        assert any(
            item["code"] == "artifact.manifest" and "canonical" in item["message"]
            for item in coherent_manifest_tamper["diagnostics"]
        )

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][1]
        run_dir = base / candidate["variant"]
        provider_worktree = run_dir / "provider-worktree"
        subprocess.run(
            ["git", "update-index", "--assume-unchanged", "Generated.swift"],
            cwd=provider_worktree,
            check=True,
        )
        (provider_worktree / "Generated.swift").write_text("// hidden provider mutation\n", encoding="utf-8")
        context_path = run_dir / "input-context.json"
        context = load_json(context_path)
        context["provider_source_scope"]["worktree"]["git_metadata_sha256"] = _provider_git_metadata_sha256(
            provider_worktree
        )
        context_path.write_text(json.dumps(context), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["evidence"]["input_context"]["sha256"] = hashlib.sha256(context_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        hidden_index_mutation = score(measured, base_dir=base)
        assert hidden_index_mutation["status"] == "blocked"
        assert any(
            item["code"] == "artifact.patch" and "filesystem snapshots differ" in item["message"]
            for item in hidden_index_mutation["diagnostics"]
        )

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][1]
        run_dir = base / candidate["variant"]

        manifest_path = run_dir / "provider-source-manifest.json"
        manifest = load_json(manifest_path)
        manifest["files"][0]["bytes"] += 1
        manifest["total_bytes"] += 1
        manifest["content_sha256"] = hashlib.sha256(
            json.dumps(manifest["files"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()

        case_path = run_dir / "benchmark-case.json"
        case = load_json(case_path)
        case_scope = case["source"]["code"]["provider_source_scope"]
        case_scope["expected_total_bytes"] = manifest["total_bytes"]
        case_scope["expected_content_sha256"] = manifest["content_sha256"]
        case_path.write_text(json.dumps(case), encoding="utf-8")
        case_hash = hashlib.sha256(case_path.read_bytes()).hexdigest()

        plan_path = run_dir / "run-plan.json"
        plan = load_json(plan_path)
        plan["case"]["sha256"] = case_hash
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()

        context_path = run_dir / "input-context.json"
        context = load_json(context_path)
        context["plan_sha256"] = plan_hash
        context["run_plan"]["sha256"] = plan_hash
        context["benchmark_case"]["sha256"] = case_hash
        context_scope = context["provider_source_scope"]
        context_scope["artifact"]["sha256"] = manifest_hash
        context_scope["total_bytes"] = manifest["total_bytes"]
        context_scope["content_sha256"] = manifest["content_sha256"]
        context_path.write_text(json.dumps(context), encoding="utf-8")

        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["environment"]["run_plan_hash"] = plan_hash
        artifact["environment"]["benchmark_case_hash"] = case_hash
        artifact["evidence"]["input_context"]["sha256"] = hashlib.sha256(context_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

        drifted_provider_scope = score(measured, base_dir=base)
        assert drifted_provider_scope["status"] == "blocked"
        assert any(
            item["code"] == "artifact.cross-run" and "provider_source_scope_identity" in item["message"]
            for item in drifted_provider_scope["diagnostics"]
        )

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        (base / "ui-ir" / "capture-overlay.patch").write_text("tampered evaluator overlay\n", encoding="utf-8")
        tampered_overlay = score(measured, base_dir=base)
        assert tampered_overlay["status"] == "blocked"
        assert any(item["code"] == "artifact.hash" for item in tampered_overlay["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        (base / "ui-ir" / "evaluator-dependency-generator").write_text(
            "tampered evaluator dependency generator\n",
            encoding="utf-8",
        )
        tampered_dependency_generator = score(measured, base_dir=base)
        assert tampered_dependency_generator["status"] == "blocked"
        assert any(item["code"] == "artifact.hash" for item in tampered_dependency_generator["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][1]
        artifact_path = base / candidate["variant"] / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["capture_overlay"]["artifact"]["sha256"] = "f" * 64
        artifact["environment"]["capture_overlay_hash"] = "f" * 64
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        mismatched_overlay_linkage = score(measured, base_dir=base)
        assert mismatched_overlay_linkage["status"] == "blocked"
        assert any(item["code"] == "artifact.linkage" for item in mismatched_overlay_linkage["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][1]
        run_dir = base / candidate["variant"]
        overlay_path = run_dir / "capture-overlay.patch"
        overlay_path.write_text("different candidate evaluator overlay\n", encoding="utf-8")
        overlay_hash = hashlib.sha256(overlay_path.read_bytes()).hexdigest()
        plan_path = run_dir / "run-plan.json"
        plan = load_json(plan_path)
        plan["validator"]["capture_overlay"]["artifact"]["sha256"] = overlay_hash
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        context_path = run_dir / "input-context.json"
        context = load_json(context_path)
        context["plan_sha256"] = plan_hash
        context["run_plan"]["sha256"] = plan_hash
        context["capture_overlay"]["artifact"]["sha256"] = overlay_hash
        context_path.write_text(json.dumps(context), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["capture_overlay"]["artifact"]["sha256"] = overlay_hash
        artifact["environment"]["run_plan_hash"] = plan_hash
        artifact["environment"]["capture_overlay_hash"] = overlay_hash
        artifact["evidence"]["input_context"]["sha256"] = hashlib.sha256(context_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        drifted_overlay_identity = score(measured, base_dir=base)
        assert drifted_overlay_identity["status"] == "blocked"
        assert any(item["code"] == "artifact.cross-run" and "capture_overlay_identity" in item["message"] for item in drifted_overlay_identity["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][1]
        run_dir = base / candidate["variant"]
        generator_path = run_dir / "evaluator-dependency-generator"
        generator_path.write_text("different candidate evaluator dependency generator\n", encoding="utf-8")
        generator_hash = hashlib.sha256(generator_path.read_bytes()).hexdigest()
        plan_path = run_dir / "run-plan.json"
        plan = load_json(plan_path)
        plan["validator"]["capture_runtime"]["evaluator_dependency_setup"]["generator"]["sha256"] = generator_hash
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        runtime_hash = hashlib.sha256(
            json.dumps(plan["validator"]["capture_runtime"], sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        context_path = run_dir / "input-context.json"
        context = load_json(context_path)
        context["plan_sha256"] = plan_hash
        context["run_plan"]["sha256"] = plan_hash
        context["evaluator_dependency_setup"]["artifact"]["sha256"] = generator_hash
        context_path.write_text(json.dumps(context), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["environment"]["run_plan_hash"] = plan_hash
        artifact["environment"]["capture_runtime_hash"] = runtime_hash
        artifact["evidence"]["input_context"]["sha256"] = hashlib.sha256(context_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        drifted_dependency_identity = score(measured, base_dir=base)
        assert drifted_dependency_identity["status"] == "blocked"
        assert any(
            item["code"] == "artifact.cross-run" and "evaluator_dependency_identity" in item["message"]
            for item in drifted_dependency_identity["diagnostics"]
        )

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        measured["candidates"][2]["validation_status"] = "failed"
        forged_aggregate_status = score(measured, base_dir=base)
        assert forged_aggregate_status["status"] == "blocked"
        assert any(item["code"] == "artifact.validation-status" for item in forged_aggregate_status["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        checkout = base / "screenshot-only" / "checkout"
        injected = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=checkout,
            input="validator-secret",
            text=True,
            capture_output=True,
            check=True,
        )
        assert injected.stdout.strip()
        extra_object = score(measured, base_dir=base)
        assert extra_object["status"] == "blocked"
        assert any(item["code"] == "artifact.isolation" for item in extra_object["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        (base / "screenshot-only" / "executor-adapter").write_text("tampered adapter\n", encoding="utf-8")
        assert score(measured, base_dir=base)["status"] == "blocked"

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][0]
        run_dir = base / candidate["variant"]
        semantic_path = run_dir / "semantic.json"
        semantic_path.write_text(json.dumps({"region": "root"}), encoding="utf-8")
        run_result_path = run_dir / "benchmark-run-result.json"
        run_result = load_json(run_result_path)
        run_result["evidence"]["semantic_snapshot"]["sha256"] = hashlib.sha256(semantic_path.read_bytes()).hexdigest()
        run_result_path.write_text(json.dumps(run_result), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["evidence"]["validation_report"]["sha256"] = hashlib.sha256(run_result_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        placeholder_semantic = score(measured, base_dir=base)
        assert placeholder_semantic["status"] == "blocked"
        assert any(item["code"].startswith("schema.") for item in placeholder_semantic["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][0]
        run_dir = base / candidate["variant"]
        screenshot = run_dir / "actual.png"
        screenshot.write_bytes(b"not a complete png")
        run_result_path = run_dir / "benchmark-run-result.json"
        run_result = load_json(run_result_path)
        run_result["evidence"]["actual_screenshot"]["sha256"] = hashlib.sha256(screenshot.read_bytes()).hexdigest()
        run_result_path.write_text(json.dumps(run_result), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["evidence"]["validation_report"]["sha256"] = hashlib.sha256(run_result_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        invalid_png = score(measured, base_dir=base)
        assert invalid_png["status"] == "blocked"
        assert any(item["code"] == "artifact.png" for item in invalid_png["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][1]
        run_dir = base / candidate["variant"]
        run_result_path = run_dir / "benchmark-run-result.json"
        run_result = load_json(run_result_path)
        run_result["metrics"]["layout_deviation_pt"] = 0
        run_result_path.write_text(json.dumps(run_result), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["metrics"]["layout_deviation_pt"] = 0
        artifact["evidence"]["validation_report"]["sha256"] = hashlib.sha256(run_result_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["layout_deviation_pt"] = 0
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        self_reported = score(measured, base_dir=base)
        assert self_reported["status"] == "blocked"
        assert any(item["code"] == "artifact.derived" for item in self_reported["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][0]
        run_dir = base / candidate["variant"]
        diff_path = run_dir / "diff.json"
        diff = load_json(diff_path)
        diff["regions"][0]["pixel_difference_ratio"] = 0.5
        diff_path.write_text(json.dumps(diff), encoding="utf-8")
        run_result_path = run_dir / "benchmark-run-result.json"
        run_result = load_json(run_result_path)
        run_result["evidence"]["visual_diff"]["sha256"] = hashlib.sha256(diff_path.read_bytes()).hexdigest()
        run_result_path.write_text(json.dumps(run_result), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["evidence"]["validation_report"]["sha256"] = hashlib.sha256(run_result_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        forged_pixel_ratio = score(measured, base_dir=base)
        assert forged_pixel_ratio["status"] == "blocked"
        assert any(item["code"] == "artifact.derived" and "pixel difference ratio" in item["message"] for item in forged_pixel_ratio["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        first_id = load_json(base / "screenshot-only" / "run-observation.json")["provider_runs"][0]["id"]
        candidate = measured["candidates"][1]
        run_dir = base / candidate["variant"]
        observation_path = run_dir / "run-observation.json"
        observation = load_json(observation_path)
        old_id = observation["provider_runs"][0]["id"]
        observation["provider_runs"][0]["id"] = first_id
        for event in observation["repair_events"]:
            if event["provider_run_id"] == old_id:
                event["provider_run_id"] = first_id
        observation_path.write_text(json.dumps(observation), encoding="utf-8")
        run_result_path = run_dir / "benchmark-run-result.json"
        run_result = load_json(run_result_path)
        run_result["provider_run_id"] = first_id
        run_result["evidence"]["run_observation"]["sha256"] = hashlib.sha256(observation_path.read_bytes()).hexdigest()
        run_result_path.write_text(json.dumps(run_result), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["evidence"]["validation_report"]["sha256"] = hashlib.sha256(run_result_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        duplicate_provider = score(measured, base_dir=base)
        assert duplicate_provider["status"] == "blocked"
        assert any(item["code"] == "artifact.provider" for item in duplicate_provider["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        (base / "screenshot-only" / "input" / "agent-packet.json").write_text("{}\n", encoding="utf-8")
        injected_input = score(measured, base_dir=base)
        assert injected_input["status"] == "blocked"
        assert any(item["code"] == "artifact.coverage" for item in injected_input["diagnostics"])

    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][1]
        run_dir = base / candidate["variant"]
        plan_path = run_dir / "run-plan.json"
        plan = load_json(plan_path)
        plan["plan_id"] = "measured.self-test.different-plan"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        context_path = run_dir / "input-context.json"
        context = load_json(context_path)
        context["plan_sha256"] = plan_hash
        context["run_plan"]["sha256"] = plan_hash
        context_path.write_text(json.dumps(context), encoding="utf-8")
        artifact_path = run_dir / "run-artifact.json"
        artifact = load_json(artifact_path)
        artifact["environment"]["run_plan_hash"] = plan_hash
        artifact["evidence"]["input_context"]["sha256"] = hashlib.sha256(context_path.read_bytes()).hexdigest()
        artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        candidate["run"]["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        different_plan = score(measured, base_dir=base)
        assert different_plan["status"] == "blocked"
        assert any(item["code"] in {"artifact.environment", "artifact.cross-run"} for item in different_plan["diagnostics"])


def test_ios_semantic_visual_validator(benchmark: dict) -> None:
    with TemporaryDirectory() as directory:
        base = Path(directory)
        measured = _measured_benchmark(benchmark, base)
        candidate = measured["candidates"][2]
        run_dir = base / candidate["variant"]
        validator = ROOT / "scripts" / "ios_semantic_visual_validator.py"
        result_path = run_dir / "validator-adapter-result.json"
        environment = {
            **os.environ,
            "DCC_RUN_DIR": str(run_dir),
            "DCC_WORKTREE": str(run_dir / "checkout"),
            "DCC_INPUT_CONTEXT": str(run_dir / "input-context.json"),
            "DCC_VALIDATOR_PROBE": str(run_dir / "validator-probe.json"),
            "DCC_ACTUAL_SCREENSHOT": str(run_dir / "actual.png"),
            "DCC_RUN_OBSERVATION": str(run_dir / "run-observation.json"),
            "DCC_RUN_RESULT": str(result_path),
            "DCC_VALIDATOR_ID": "measured-self-test-validator",
            "DCC_VALIDATOR_ADAPTER_SHA256": hashlib.sha256(validator.read_bytes()).hexdigest(),
            "DCC_CODE_BASELINE_COMMIT": measured["environment"]["code_baseline"],
            "DCC_MODEL": measured["environment"]["model"],
            "DCC_REASONING": measured["environment"]["reasoning"],
        }
        completed = subprocess.run([sys.executable, str(validator)], env=environment, capture_output=True, text=True, check=False)
        assert completed.returncode == 0, completed.stderr
        result = load_json(result_path)
        _, diagnostics, blocking = validate(result, "benchmark-run-result")
        assert not diagnostics and not blocking, ([item.as_dict() for item in diagnostics], blocking)
        assert result["metrics"]["layout_deviation_pt"] == candidate["layout_deviation_pt"]
        assert result["metrics"]["component_reuse_rate"] == candidate["component_reuse_rate"]
        assert load_json(run_dir / "visual-diff.json")["regions"][0]["pixel_difference_ratio"] == 0


def test_independent_png_alpha_diff() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        opaque = root / "opaque.png"
        transparent = root / "transparent.png"
        opaque.write_bytes(make_rgba_png(20, 40, 60, 255))
        transparent.write_bytes(make_rgba_png(20, 40, 60, 0))
        frame = {"x": 0, "y": 0, "width": 1, "height": 1}
        validator_ratio = validator_pixel_difference_ratio(
            validator_decode_png(opaque), validator_decode_png(transparent), frame, [], 0
        )
        scorer_ratio = _score_pixel_difference_ratio(
            _score_decode_png(opaque), _score_decode_png(transparent), frame, [], 0
        )
        assert validator_ratio == 1 and scorer_ratio == 1


def test_binding_declaration_rejects_bait() -> None:
    binding = {"source": "Owner.swift", "code_symbol": "FakeOwner"}
    for content in ('let bait = "class FakeOwner"\n', 'let x = 1 /* class FakeOwner */\n'):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Owner.swift").write_text(content, encoding="utf-8")
            try:
                validator_declaration_location(root, binding)
            except SemanticValidationError:
                pass
            else:
                raise AssertionError("validator must reject declaration bait in strings/comments")
            diagnostics = _verify_symbol_declaration_location(
                root,
                {"path": "Owner.swift", "line": 1},
                "FakeOwner",
                "binding",
            )
            assert diagnostics and diagnostics[0].code == "artifact.location"


def test_magic_number_semantic_filter() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        source = root / "Layout.swift"
        source.write_text("// baseline\n", encoding="utf-8")
        subprocess.run(["git", "add", "Layout.swift"], cwd=root, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Benchmark Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "baseline"],
            cwd=root,
            check=True,
        )
        baseline = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        source.write_text(
            'let semanticSpacing = 24\nlet label = "2026"\nview.frame.origin.x = CGFloat(17)\n',
            encoding="utf-8",
        )
        expected = [{"kind": "layout", "value": "17", "location": {"path": "Layout.swift", "line": 3}}]
        assert validator_added_swift_literals(root, baseline) == expected
        assert _score_added_swift_literals(root, baseline) == expected


def test_measured_run_plan_freezer() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        case_path = root / "benchmark-case.json"
        shutil.copyfile(REFERENCES / "benchmark-cases" / "au-create-project-alert" / "benchmark-case.json", case_path)
        executor = root / "executor.py"
        capture = root / "capture.py"
        validator = root / "validator.py"
        launcher = root / "codex.js"
        for path, content in (
            (executor, "executor\n"),
            (capture, "capture\n"),
            (validator, "validator\n"),
            (launcher, "launcher\n"),
        ):
            path.write_text(content, encoding="utf-8")
        identity = (
            "codex-cli 1.2.3",
            str(launcher.resolve()),
            str(launcher.resolve()),
            hashlib.sha256(launcher.read_bytes()).hexdigest(),
            hashlib.sha256(launcher.read_bytes()).hexdigest(),
            "9" * 64,
        )
        output = root / "measured-run-plan.json"
        with patch.object(run_plan_module, "EXECUTOR", executor), patch.object(run_plan_module, "VALIDATOR", validator), patch.object(run_plan_module, "_cli_identity", return_value=identity):
            plan = run_plan_module.create_plan(case_path, capture, launcher, "frozen-model", "high", output)
        _, diagnostics, blocking = validate(plan, "benchmark-run-plan")
        assert not diagnostics and not blocking
        assert output.is_file() and plan["validator"]["capture_adapter"]["sha256"] == hashlib.sha256(capture.read_bytes()).hexdigest()


def test_benchmark_case_contract() -> None:
    path = REFERENCES / "benchmark-cases" / "au-create-project-alert" / "benchmark-case.json"
    case = load_json(path)
    _, diagnostics, blocking = validate(case, "benchmark-case")
    assert not diagnostics, [item.as_dict() for item in diagnostics]
    assert not blocking, blocking

    duplicate_variant = deepcopy(case)
    duplicate_variant["benchmark"]["variants"][1]["variant"] = "screenshot-only"
    expect_invalid(duplicate_variant, "benchmark-case", "duplicate")

    missing_packet = deepcopy(case)
    missing_packet["benchmark"]["variants"][2]["inputs"] = missing_packet["benchmark"]["variants"][2]["inputs"][:-1]
    expect_invalid(missing_packet, "benchmark-case", "variants.inputs")

    forged_ready = deepcopy(case)
    forged_ready["readiness"]["blocking_unknowns"] = ["missing runner"]
    expect_invalid(forged_ready, "benchmark-case", "consistency")

    blocked_case = deepcopy(case)
    blocked_case["readiness_status"] = "blocked"
    blocked_case["readiness"]["ready"] = False
    blocked_case["readiness"]["blocking_unknowns"] = ["missing source"]
    _, diagnostics, blocking = validate(blocked_case, "benchmark-case")
    assert not diagnostics and blocking

    path_escape = deepcopy(case)
    path_escape["source"]["design"]["node_id"] = "../outside"
    expect_invalid(path_escape, "benchmark-case", "schema.pattern")

    cross_root_code = deepcopy(case)
    cross_root_code["source"]["code"]["files"][0]["root"] = "repository"
    expect_invalid(cross_root_code, "benchmark-case", "reference")

    validation_path = path.parent / case["benchmark"]["validation_config"]["path"]
    validation_config = load_json(validation_path)
    _, diagnostics, blocking = validate(validation_config, "benchmark-validation-config")
    assert not diagnostics and not blocking
    invalid_threshold = deepcopy(validation_config)
    invalid_threshold["thresholds"]["max_input_tokens"] = True
    expect_invalid(invalid_threshold, "benchmark-validation-config")
    overlapping_region = deepcopy(validation_config)
    overlapping_region["ignore_regions"] = [deepcopy(overlapping_region["reference_regions"][0])]
    expect_invalid(overlapping_region, "benchmark-validation-config", "overlap")
    incomplete_reference = deepcopy(validation_config)
    incomplete_reference["reference_regions"] = incomplete_reference["reference_regions"][:-1]
    expect_invalid(incomplete_reference, "benchmark-validation-config", "coverage")
    incomplete_spacing = deepcopy(validation_config)
    del incomplete_spacing["required_anchors"][1]["anchors"][0]["reference_value"]
    expect_invalid(incomplete_spacing, "benchmark-validation-config", "anchor")
    polluted_position = deepcopy(validation_config)
    polluted_position["required_anchors"][0]["anchors"][0]["reference_value"] = 0
    expect_invalid(polluted_position, "benchmark-validation-config", "anchor")


def test_benchmark_runner() -> None:
    plan_example = expect_valid("benchmark-run-plan-example.json", "benchmark-run-plan")
    input_example = expect_valid("benchmark-input-context-example.json", "benchmark-input-context")
    result_example = expect_valid("benchmark-run-result-example.json", "benchmark-run-result")
    missing_probe_result = deepcopy(result_example)
    del missing_probe_result["evidence"]["validator_probe"]
    expect_invalid(missing_probe_result, "benchmark-run-result", "schema.required")
    expect_valid("benchmark-semantic-evidence-example.json", "benchmark-semantic-evidence")
    expect_valid("benchmark-visual-diff-example.json", "benchmark-visual-diff")
    probe = expect_valid("benchmark-validator-probe-example.json", "benchmark-validator-probe")
    escaped_probe = deepcopy(probe)
    escaped_probe["actual_screenshot"]["path"] = "../actual.png"
    expect_invalid(escaped_probe, "benchmark-validator-probe", "artifact.path")
    escaped_frame = deepcopy(probe)
    escaped_frame["regions"][0]["frame"]["width"] = 394
    expect_invalid(escaped_frame, "benchmark-validator-probe", "geometry")
    semantic = expect_valid("benchmark-semantic-evidence-example.json", "benchmark-semantic-evidence")
    forged_source = deepcopy(semantic)
    forged_source["required_bindings"][0]["locations"][0]["path"] = "Sources/Invented.swift"
    expect_invalid(forged_source, "benchmark-semantic-evidence", "evidence")
    visual = expect_valid("benchmark-visual-diff-example.json", "benchmark-visual-diff")
    forged_deviation = deepcopy(visual)
    forged_deviation["regions"][0]["anchors"][0]["deviation_pt"] = 0
    expect_invalid(forged_deviation, "benchmark-visual-diff", "consistency")
    expect_valid("benchmark-run-observation-example.json", "benchmark-run-observation")
    measured_fake = deepcopy(plan_example)
    measured_fake["evidence_status"] = "measured"
    expect_invalid(measured_fake, "benchmark-run-plan", "evidence")
    embedded_adapter = deepcopy(plan_example)
    embedded_adapter["executor"]["implementation_command"] = ["runner", "{adapter}"]
    expect_invalid(embedded_adapter, "benchmark-run-plan", "adapter")
    duplicate_input = deepcopy(input_example)
    duplicate_input["inputs"].append(deepcopy(duplicate_input["inputs"][0]))
    expect_invalid(duplicate_input, "benchmark-input-context", "duplicate")
    inconsistent_result = deepcopy(result_example)
    inconsistent_result["metrics"]["layout_deviation_pt"] = 0.1
    expect_invalid(inconsistent_result, "benchmark-run-result", "consistency")
    failed_result = deepcopy(result_example)
    failed_result["status"] = "failed"
    _, diagnostics, blocking = validate(failed_result, "benchmark-run-result")
    assert not diagnostics and not blocking

    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "source"
        source.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=source, check=True)
        subprocess.run(["git", "config", "user.email", "benchmark@example.invalid"], cwd=source, check=True)
        subprocess.run(["git", "config", "user.name", "Benchmark Test"], cwd=source, check=True)
        baseline = source / "baseline.txt"
        baseline.write_text("baseline\n", encoding="utf-8")
        generated_baseline = source / "BenchmarkGenerated.swift"
        generated_baseline.write_text("// provider baseline\n", encoding="utf-8")
        (source / "secret.txt").write_text("must not enter provider worktree\n", encoding="utf-8")
        subprocess.run(["git", "add", "baseline.txt", "BenchmarkGenerated.swift", "secret.txt"], cwd=source, check=True)
        subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "test(Runner): [HUMAN] 创建临时基线"],
            cwd=source,
            check=True,
        )
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
        design = source / "design.sketch"
        design.write_text("synthetic design\n", encoding="utf-8")

        case_dir = root / "case"
        case_dir.mkdir()
        artifact_refs = {}
        for name in ("design-evidence.json", "ui-ir.json", "component-registry.json", "agent-packet.json"):
            path = case_dir / name
            path.write_text("{}\n", encoding="utf-8")
            artifact_refs[name] = {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        prompt = case_dir / "shared-prompt.md"
        prompt.write_text("synthetic shared prompt\n", encoding="utf-8")
        validation = {
            "config_version": "1.1.0",
            "reference_viewport": {"width": 8, "height": 8},
            "reference_scale": 1,
            "appearance": "dark",
            "locale": "en_US",
            "required_regions": ["root"],
            "reference_regions": [
                {
                    "id": "root",
                    "frame": {"x": 0, "y": 0, "width": 8, "height": 8},
                    "runtime_type": "RootView",
                    "accessibility_identifier": "benchmark.root",
                    "parent_id": None,
                    "child_ids": [],
                }
            ],
            "required_bindings": [
                {
                    "id": f"binding-{index}",
                    "registry_entry_id": f"component-{index}",
                    "code_symbol": f"Binding{index}",
                    "source": "BenchmarkGenerated.swift",
                    "region_id": "root",
                    "runtime_type": f"Binding{index}",
                }
                for index in range(10)
            ],
            "required_anchors": [
                {"region_id": "root", "anchors": [{"id": "max-anchor", "metric": "position"}]}
            ],
            "ignore_regions": [],
            "pixel_diff": {"max_channel_delta": 0, "max_different_pixel_ratio": 0},
            "metrics": {
                "layout_deviation": "max-anchor-deviation-pt",
                "component_reuse": "required-binding-coverage",
                "magic_numbers": "unmapped-layout-literal-count",
                "repair_iterations": "accepted-repair-rounds",
                "input_tokens": "actual-model-input-tokens",
                "manual_minutes": "human-intervention-minutes",
            },
            "thresholds": {
                "max_layout_deviation_pt": 1,
                "min_component_reuse_rate": 0.8,
                "max_repair_iterations": 2,
                "max_input_tokens": 10000,
                "max_magic_numbers": 3,
                "max_manual_minutes": 30,
                "min_ui_ir_layout_improvement_pt": 1,
                "min_binding_reuse_gain": 0.3,
            },
        }
        validation_path = case_dir / "validation-config.json"
        validation_path.write_text(json.dumps(validation), encoding="utf-8")
        reference = root / "reference.png"
        reference.write_bytes(make_png(8, 8))
        reference_hash = hashlib.sha256(reference.read_bytes()).hexdigest()
        environment = {
            "task_mode": "reuse-conformance",
            "screen": "synthetic-screen",
            "state": "default",
            "viewport": {"width": 8, "height": 8},
            "scale": 1,
            "appearance": "dark",
            "locale": "en_US",
            "ui_framework": "UIKit",
        }
        case = {
            "case_version": "1.0.0",
            "case_id": "synthetic.runner.case",
            "readiness_status": "ready",
            "workspace_roots": [{"id": "source", "path": "source"}],
            "source": {
                "design": {
                    "file": {"root": "source", "path": "design.sketch", "sha256": hashlib.sha256(design.read_bytes()).hexdigest()},
                    "node_id": "11111111-1111-1111-1111-111111111111",
                    "document_version": "synthetic-version",
                    "reference_export": {
                        "tool": "sketchtool",
                        "format": "png",
                        "scale": 1,
                        "expected_output": "reference.png",
                        "expected_sha256": reference_hash,
                        "expected_viewport": {"width": 8, "height": 8},
                    },
                },
                "code": {
                    "root": "source",
                    "git_commit": commit,
                    "provider_source_scope": {},
                    "files": [
                        {
                            "root": "source",
                            "path": "baseline.txt",
                            "sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                        }
                    ],
                },
            },
            "contracts": {
                "design_evidence": artifact_refs["design-evidence.json"],
                "ui_ir": artifact_refs["ui-ir.json"],
                "ui_ir_unbound": {"projection": "strip-component-bindings", "sha256": "1" * 64},
                "component_registry": artifact_refs["component-registry.json"],
                "agent_packet": artifact_refs["agent-packet.json"],
            },
            "benchmark": {
                "shared_prompt": {"path": prompt.name, "sha256": hashlib.sha256(prompt.read_bytes()).hexdigest()},
                "validation_config": {
                    "path": validation_path.name,
                    "sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
                },
                "environment": environment,
                "variants": [],
            },
            "readiness": {"ready": True, "blocking_unknowns": [], "measured_results": False},
        }
        synthetic_scope = {
            "mode": "allowlist",
            "entries": [
                {"kind": "file", "path": "baseline.txt"},
                {"kind": "file", "path": "BenchmarkGenerated.swift"},
            ],
        }
        synthetic_provider_manifest = _provider_source_manifest(source, commit, synthetic_scope)
        case["source"]["code"]["provider_source_scope"] = {
            **synthetic_scope,
            "expected_file_count": synthetic_provider_manifest["file_count"],
            "expected_total_bytes": synthetic_provider_manifest["total_bytes"],
            "expected_content_sha256": synthetic_provider_manifest["content_sha256"],
        }
        input_kinds = {
            "screenshot-only": ["reference", "shared-prompt", "validation-config"],
            "ui-ir": ["reference", "shared-prompt", "validation-config", "ui-ir"],
            "ui-ir-with-binding": ["reference", "shared-prompt", "validation-config", "agent-packet"],
        }
        source_names = {
            "reference": "generated-reference",
            "shared-prompt": "shared_prompt",
            "validation-config": "validation_config",
            "ui-ir": "generated-ui-ir-unbound",
            "agent-packet": "agent_packet",
        }
        case["benchmark"]["variants"] = [
            {
                "variant": variant,
                "inputs": [{"kind": kind, "artifact": {"source": source_names[kind]}} for kind in input_kinds[variant]],
            }
            for variant in ("screenshot-only", "ui-ir", "ui-ir-with-binding")
        ]
        case_path = case_dir / "benchmark-case.json"
        case_path.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _, diagnostics, blocking = validate(case, "benchmark-case")
        assert not diagnostics and not blocking

        prepared = root / "prepared"
        prepared.mkdir()
        provider_manifest_path = prepared / "provider-source-manifest.json"
        provider_manifest_path.write_text(json.dumps(synthetic_provider_manifest), encoding="utf-8")
        files = {
            "reference": reference,
            "shared-prompt": prompt,
            "validation-config": validation_path,
        }
        extra = root / "ui-ir-unbound.json"
        extra.write_text("{}\n", encoding="utf-8")
        packet = root / "agent-packet.json"
        packet.write_text("{}\n", encoding="utf-8")
        files.update({"ui-ir": extra, "agent-packet": packet})
        for variant, kinds in input_kinds.items():
            variant_dir = prepared / "variants" / variant
            variant_dir.mkdir(parents=True)
            inputs = []
            names = {
                "reference": "reference.png",
                "shared-prompt": "shared-prompt.md",
                "validation-config": "validation-config.json",
                "ui-ir": "ui-ir.json",
                "agent-packet": "agent-packet.json",
            }
            for kind in kinds:
                destination = variant_dir / names[kind]
                shutil.copyfile(files[kind], destination)
                inputs.append(
                    {
                        "kind": kind,
                        "audience": "validator" if kind == "validation-config" else "agent",
                        "path": destination.name,
                        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                    }
                )
            manifest = {
                "case_id": case["case_id"],
                "variant": variant,
                "environment": environment,
                "inputs": inputs,
                "measured_result": None,
            }
            (variant_dir / "input-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        report = {
            "status": "ready",
            "case_id": case["case_id"],
            "case_sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(),
            "provider_source_scope": {
                "mode": "allowlist",
                "manifest_path": str(provider_manifest_path),
                "manifest_sha256": hashlib.sha256(provider_manifest_path.read_bytes()).hexdigest(),
                "file_count": synthetic_provider_manifest["file_count"],
                "total_bytes": synthetic_provider_manifest["total_bytes"],
                "content_sha256": synthetic_provider_manifest["content_sha256"],
            },
        }
        (prepared / "preparation-report.json").write_text(json.dumps(report), encoding="utf-8")

        fake = ROOT / "scripts" / "fake_benchmark_executor.py"
        fake_capture = ROOT / "scripts" / "fake_benchmark_capture.py"
        plan = {
            "run_plan_version": "1.2.0",
            "plan_id": "synthetic.runner.e2e",
            "evidence_status": "synthetic-example",
            "case": {
                "path": str(case_path.relative_to(root)),
                "sha256": hashlib.sha256(case_path.read_bytes()).hexdigest(),
            },
            "executor": {
                "model": "synthetic-model",
                "reasoning": "synthetic",
                "synthetic": True,
                "provider_cli": {
                    "name": "synthetic-test-adapter",
                    "version": "1.0.0",
                    "launcher_path": str(fake.resolve()),
                    "native_path": str(fake.resolve()),
                    "launcher_sha256": hashlib.sha256(fake.read_bytes()).hexdigest(),
                    "native_sha256": hashlib.sha256(fake.read_bytes()).hexdigest(),
                    "package_json_sha256": hashlib.sha256(fake.read_bytes()).hexdigest(),
                },
                "adapter": {"path": str(fake), "sha256": hashlib.sha256(fake.read_bytes()).hexdigest()},
                "implementation_command": ["{adapter}", "--phase", "implementation"],
                "timeout_seconds": 60,
                "environment": {"DCC_FAKE_REQUIRE_MINIMAL_SCOPE": "1"},
            },
            "validator": {
                "id": "synthetic-validator",
            "synthetic": True,
            "capture_adapter": {"path": str(fake_capture), "sha256": hashlib.sha256(fake_capture.read_bytes()).hexdigest()},
            "capture_overlay": {"mode": "none"},
            "capture_runtime": {"mode": "none"},
            "capture_command": ["{capture}"],
                "adapter": {"path": str(fake), "sha256": hashlib.sha256(fake.read_bytes()).hexdigest()},
                "command": ["{validator}", "--phase", "validation"],
                "timeout_seconds": 60,
                "environment": {},
            },
            "isolation": {
                "strategy": "git-shared-clone",
                "run_order": ["screenshot-only", "ui-ir", "ui-ir-with-binding"],
                "clean_checkout": True,
            },
        }
        plan_path = root / "run-plan.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output = root / "output"
        result = run_benchmark(plan_path, root, output, prepared, True)
        assert result["status"] == "completed"
        assert result["evidence_status"] == "synthetic-example"
        assert result["score"]["status"] == "scored" and result["score"]["recommendation"] == "go"
        for variant in input_kinds:
            patch = output / "runs" / variant / "implementation-output.patch"
            assert "BenchmarkGenerated.swift" in patch.read_text(encoding="utf-8")
        try:
            run_benchmark(plan_path, root, root / "denied", prepared, False)
        except RunnerError as exc:
            assert "--allow-synthetic" in str(exc)
        else:
            raise AssertionError("synthetic runner must require explicit opt-in")

        outside_scope_plan = deepcopy(plan)
        outside_scope_plan["plan_id"] = "synthetic.runner.provider-outside-scope"
        outside_scope_plan["executor"]["environment"]["DCC_FAKE_WRITE_OUTSIDE_SCOPE"] = "1"
        outside_scope_plan_path = root / "provider-outside-scope-plan.json"
        outside_scope_plan_path.write_text(json.dumps(outside_scope_plan), encoding="utf-8")
        try:
            run_benchmark(outside_scope_plan_path, root, root / "provider-outside-scope-output", prepared, True)
        except RunnerError as exc:
            assert "outside frozen source scope" in str(exc)
        else:
            raise AssertionError("runner must reject provider changes outside the frozen source scope")

        hidden_outside_scope_plan = deepcopy(plan)
        hidden_outside_scope_plan["plan_id"] = "synthetic.runner.provider-hidden-outside-scope"
        hidden_outside_scope_plan["executor"]["environment"]["DCC_FAKE_HIDE_OUTSIDE_SCOPE"] = "1"
        hidden_outside_scope_plan_path = root / "provider-hidden-outside-scope-plan.json"
        hidden_outside_scope_plan_path.write_text(json.dumps(hidden_outside_scope_plan), encoding="utf-8")
        try:
            run_benchmark(
                hidden_outside_scope_plan_path,
                root,
                root / "provider-hidden-outside-scope-output",
                prepared,
                True,
            )
        except RunnerError as exc:
            assert "Git metadata" in str(exc) or "outside frozen source scope" in str(exc)
        else:
            raise AssertionError("runner must reject Git-ignored provider writes outside the frozen source scope")

        no_overlay_timeout_plan = deepcopy(plan)
        no_overlay_timeout_plan["plan_id"] = "synthetic.runner.capture-timeout-mutation"
        no_overlay_timeout_plan["validator"]["environment"] = {"DCC_FAKE_CAPTURE_TIMEOUT_AFTER_MUTATION": "1"}
        no_overlay_timeout_plan["validator"]["timeout_seconds"] = 1
        no_overlay_timeout_plan_path = root / "capture-timeout-mutation-plan.json"
        no_overlay_timeout_plan_path.write_text(json.dumps(no_overlay_timeout_plan), encoding="utf-8")
        no_overlay_timeout_output = root / "capture-timeout-mutation-output"
        try:
            run_benchmark(no_overlay_timeout_plan_path, root, no_overlay_timeout_output, prepared, True)
        except RunnerError as exc:
            assert "fallback restored the isolated checkout" in str(exc)
            checkout = no_overlay_timeout_output / "runs" / "screenshot-only" / "checkout"
            assert (checkout / "baseline.txt").read_text(encoding="utf-8") == "baseline\n"
            assert not (checkout / "capture-mutation.txt").exists()
            assert (checkout / "BenchmarkGenerated.swift").is_file()
        else:
            raise AssertionError("runner must recover no-overlay capture timeout mutations")

        overlay_path = root / "capture-overlay.patch"
        overlay_path.write_text(
            """diff --git a/baseline.txt b/baseline.txt
--- a/baseline.txt
+++ b/baseline.txt
@@ -1 +1 @@
-baseline
+capture overlay
diff --git a/capture-only.txt b/capture-only.txt
new file mode 100644
--- /dev/null
+++ b/capture-only.txt
@@ -0,0 +1 @@
+evaluator capture only
""",
            encoding="utf-8",
        )
        overlay_plan = deepcopy(plan)
        overlay_plan["plan_id"] = "synthetic.runner.capture-overlay"
        overlay_plan["executor"]["environment"] = {"DCC_FAKE_PROVIDER_FORBID_OVERLAY": "1"}
        overlay_plan["validator"]["capture_overlay"] = {
            "mode": "git-patch",
            "artifact": {
                "path": overlay_path.name,
                "sha256": hashlib.sha256(overlay_path.read_bytes()).hexdigest(),
            },
        }
        overlay_plan["validator"]["environment"] = {
            "DCC_FAKE_CAPTURE_REQUIRE_OVERLAY": "1",
            "DCC_FAKE_VALIDATOR_FORBID_OVERLAY": "1",
        }
        overlay_plan_path = root / "capture-overlay-plan.json"
        overlay_plan_path.write_text(json.dumps(overlay_plan), encoding="utf-8")
        overlay_output = root / "capture-overlay-output"
        overlay_result = run_benchmark(overlay_plan_path, root, overlay_output, prepared, True)
        assert overlay_result["status"] == "completed"
        for variant in input_kinds:
            checkout = overlay_output / "runs" / variant / "checkout"
            assert (checkout / "baseline.txt").read_text(encoding="utf-8") == "baseline\n"
            assert not (checkout / "capture-only.txt").exists()
            assert (checkout / "BenchmarkGenerated.swift").is_file()
            artifact = json.loads((overlay_output / "runs" / variant / "run-artifact.json").read_text(encoding="utf-8"))
            assert artifact["capture_overlay"]["artifact"]["sha256"] == hashlib.sha256(overlay_path.read_bytes()).hexdigest()
            assert artifact["environment"]["capture_overlay_mode"] == "git-patch"

        capture_failure_plan = deepcopy(overlay_plan)
        capture_failure_plan["plan_id"] = "synthetic.runner.capture-overlay-failure"
        capture_failure_plan["validator"]["environment"]["DCC_FAKE_CAPTURE_FAIL"] = "1"
        capture_failure_plan_path = root / "capture-overlay-failure-plan.json"
        capture_failure_plan_path.write_text(json.dumps(capture_failure_plan), encoding="utf-8")
        capture_failure_output = root / "capture-overlay-failure-output"
        try:
            run_benchmark(capture_failure_plan_path, root, capture_failure_output, prepared, True)
        except RunnerError as exc:
            assert "executor failed" in str(exc)
            checkout = capture_failure_output / "runs" / "screenshot-only" / "checkout"
            assert (checkout / "baseline.txt").read_text(encoding="utf-8") == "baseline\n"
            assert not (checkout / "capture-only.txt").exists()
            assert (checkout / "BenchmarkGenerated.swift").is_file()
        else:
            raise AssertionError("runner must restore capture overlay after capture failure")

        capture_overlay_mutation_plan = deepcopy(overlay_plan)
        capture_overlay_mutation_plan["plan_id"] = "synthetic.runner.capture-overlay-mutation"
        capture_overlay_mutation_plan["validator"]["environment"]["DCC_FAKE_CAPTURE_MUTATE_OVERLAY"] = "1"
        capture_overlay_mutation_plan_path = root / "capture-overlay-mutation-plan.json"
        capture_overlay_mutation_plan_path.write_text(json.dumps(capture_overlay_mutation_plan), encoding="utf-8")
        capture_overlay_mutation_output = root / "capture-overlay-mutation-output"
        try:
            run_benchmark(capture_overlay_mutation_plan_path, root, capture_overlay_mutation_output, prepared, True)
        except RunnerError as exc:
            assert "fallback restored the isolated checkout" in str(exc)
            checkout = capture_overlay_mutation_output / "runs" / "screenshot-only" / "checkout"
            assert (checkout / "baseline.txt").read_text(encoding="utf-8") == "baseline\n"
            assert not (checkout / "capture-only.txt").exists()
            assert (checkout / "BenchmarkGenerated.swift").is_file()
        else:
            raise AssertionError("runner must reject and restore capture-time overlay mutation")

        capture_overlay_reverse_conflict_plan = deepcopy(overlay_plan)
        capture_overlay_reverse_conflict_plan["plan_id"] = "synthetic.runner.capture-overlay-reverse-conflict"
        capture_overlay_reverse_conflict_plan["validator"]["environment"]["DCC_FAKE_CAPTURE_BREAK_OVERLAY"] = "1"
        capture_overlay_reverse_conflict_plan_path = root / "capture-overlay-reverse-conflict-plan.json"
        capture_overlay_reverse_conflict_plan_path.write_text(json.dumps(capture_overlay_reverse_conflict_plan), encoding="utf-8")
        capture_overlay_reverse_conflict_output = root / "capture-overlay-reverse-conflict-output"
        try:
            run_benchmark(capture_overlay_reverse_conflict_plan_path, root, capture_overlay_reverse_conflict_output, prepared, True)
        except RunnerError as exc:
            assert "fallback restored the isolated checkout" in str(exc)
            checkout = capture_overlay_reverse_conflict_output / "runs" / "screenshot-only" / "checkout"
            assert (checkout / "baseline.txt").read_text(encoding="utf-8") == "baseline\n"
            assert not (checkout / "capture-only.txt").exists()
            assert (checkout / "BenchmarkGenerated.swift").is_file()
        else:
            raise AssertionError("runner must reject and restore capture overlay reverse conflicts")

        conflicting_overlay = root / "conflicting-capture-overlay.patch"
        conflicting_overlay.write_text(overlay_path.read_text(encoding="utf-8").replace("-baseline\n", "-not-the-baseline\n", 1), encoding="utf-8")
        conflicting_overlay_plan = deepcopy(overlay_plan)
        conflicting_overlay_plan["plan_id"] = "synthetic.runner.capture-overlay-conflict"
        conflicting_overlay_plan["validator"]["capture_overlay"]["artifact"] = {
            "path": conflicting_overlay.name,
            "sha256": hashlib.sha256(conflicting_overlay.read_bytes()).hexdigest(),
        }
        conflicting_overlay_plan_path = root / "conflicting-capture-overlay-plan.json"
        conflicting_overlay_plan_path.write_text(json.dumps(conflicting_overlay_plan), encoding="utf-8")
        conflicting_overlay_output = root / "conflicting-capture-overlay-output"
        try:
            run_benchmark(conflicting_overlay_plan_path, root, conflicting_overlay_output, prepared, True)
        except RunnerError as exc:
            assert "unable to apply capture overlay" in str(exc)
            checkout = conflicting_overlay_output / "runs" / "screenshot-only" / "checkout"
            assert (checkout / "baseline.txt").read_text(encoding="utf-8") == "baseline\n"
            assert not (checkout / "capture-only.txt").exists()
            assert (checkout / "BenchmarkGenerated.swift").is_file()
        else:
            raise AssertionError("runner must reject a conflicting capture overlay")
        mutating_plan = deepcopy(plan)
        mutating_plan["plan_id"] = "synthetic.runner.mutating-input"
        mutating_plan["executor"]["environment"] = {"DCC_FAKE_MUTATE_INPUT": "1"}
        mutating_plan_path = root / "mutating-plan.json"
        mutating_plan_path.write_text(json.dumps(mutating_plan), encoding="utf-8")
        try:
            run_benchmark(mutating_plan_path, root, root / "mutating-output", prepared, True)
        except RunnerError as exc:
            assert "hash mismatch" in str(exc)
        else:
            raise AssertionError("runner must reject executor mutation of frozen inputs")
        mismatched_stream_plan = deepcopy(plan)
        mismatched_stream_plan["plan_id"] = "synthetic.runner.mismatched-event-stream"
        mismatched_stream_plan["executor"]["environment"] = {"DCC_FAKE_EVENT_STREAM_MISMATCH": "1"}
        mismatched_stream_plan_path = root / "mismatched-event-stream-plan.json"
        mismatched_stream_plan_path.write_text(json.dumps(mismatched_stream_plan), encoding="utf-8")
        try:
            run_benchmark(mismatched_stream_plan_path, root, root / "mismatched-event-stream-output", prepared, True)
        except RunnerError as exc:
            assert "provider event stream hash mismatch" in str(exc)
        else:
            raise AssertionError("runner must reject unreceipted provider event streams")
        adding_input_plan = deepcopy(plan)
        adding_input_plan["plan_id"] = "synthetic.runner.adding-input"
        adding_input_plan["executor"]["environment"] = {"DCC_FAKE_ADD_INPUT": "1"}
        adding_input_plan_path = root / "adding-input-plan.json"
        adding_input_plan_path.write_text(json.dumps(adding_input_plan), encoding="utf-8")
        try:
            run_benchmark(adding_input_plan_path, root, root / "adding-input-output", prepared, True)
        except RunnerError as exc:
            assert "input file set changed" in str(exc)
        else:
            raise AssertionError("runner must reject cross-variant input injection")
        prewrite_plan = deepcopy(plan)
        prewrite_plan["plan_id"] = "synthetic.runner.prewrite-validation"
        prewrite_plan["executor"]["environment"] = {"DCC_FAKE_PREWRITE_VALIDATION": "1"}
        prewrite_plan_path = root / "prewrite-plan.json"
        prewrite_plan_path.write_text(json.dumps(prewrite_plan), encoding="utf-8")
        try:
            run_benchmark(prewrite_plan_path, root, root / "prewrite-output", prepared, True)
        except RunnerError as exc:
            assert "unexpected run files" in str(exc)
        else:
            raise AssertionError("runner must reject executor-owned validation outputs")
        moving_head_plan = deepcopy(plan)
        moving_head_plan["plan_id"] = "synthetic.runner.moving-head"
        moving_head_plan["executor"]["environment"] = {"DCC_FAKE_MOVE_HEAD": "1"}
        moving_head_plan_path = root / "moving-head-plan.json"
        moving_head_plan_path.write_text(json.dumps(moving_head_plan), encoding="utf-8")
        try:
            run_benchmark(moving_head_plan_path, root, root / "moving-head-output", prepared, True)
        except RunnerError as exc:
            assert "changed minimal worktree HEAD" in str(exc)
        else:
            raise AssertionError("runner must reject executor movement of pinned HEAD")
        absolute_plan = deepcopy(plan)
        absolute_plan["plan_id"] = "synthetic.runner.absolute-evidence"
        absolute_plan["validator"]["environment"] = {"DCC_FAKE_ABSOLUTE_EVIDENCE": "1"}
        absolute_plan_path = root / "absolute-plan.json"
        absolute_plan_path.write_text(json.dumps(absolute_plan), encoding="utf-8")
        try:
            run_benchmark(absolute_plan_path, root, root / "absolute-output", prepared, True)
        except RunnerError as exc:
            assert "relative evidence path" in str(exc)
        else:
            raise AssertionError("runner must reject absolute run-result evidence")
        capture_mutation_plan = deepcopy(plan)
        capture_mutation_plan["plan_id"] = "synthetic.runner.capture-mutates-patch"
        capture_mutation_plan["validator"]["environment"] = {"DCC_FAKE_CAPTURE_MUTATE_PATCH": "1"}
        capture_mutation_plan_path = root / "capture-mutation-plan.json"
        capture_mutation_plan_path.write_text(json.dumps(capture_mutation_plan), encoding="utf-8")
        try:
            run_benchmark(capture_mutation_plan_path, root, root / "capture-mutation-output", prepared, True)
        except RunnerError as exc:
            assert "capture command modified frozen implementation patch" in str(exc)
        else:
            raise AssertionError("runner must reject capture mutation of the implementation patch")
        validator_capture_mutation_plan = deepcopy(plan)
        validator_capture_mutation_plan["plan_id"] = "synthetic.runner.validator-mutates-capture"
        validator_capture_mutation_plan["validator"]["environment"] = {"DCC_FAKE_VALIDATOR_MUTATE_CAPTURE": "1"}
        validator_capture_mutation_plan_path = root / "validator-capture-mutation-plan.json"
        validator_capture_mutation_plan_path.write_text(json.dumps(validator_capture_mutation_plan), encoding="utf-8")
        try:
            run_benchmark(validator_capture_mutation_plan_path, root, root / "validator-capture-mutation-output", prepared, True)
        except RunnerError as exc:
            assert "validation command modified capture-owned evidence" in str(exc)
        else:
            raise AssertionError("runner must reject validator mutation of capture evidence")
        stale = prepared / "variants" / "screenshot-only" / "agent-packet.json"
        stale.write_text("stale", encoding="utf-8")
        try:
            run_benchmark(plan_path, root, root / "stale-output", prepared, True)
        except RunnerError as exc:
            assert "unexpected files" in str(exc)
        else:
            raise AssertionError("runner must reject cross-variant stale input")
        stale.unlink()

        tampered_prepared = root / "tampered-provider-scope-prepared"
        shutil.copytree(prepared, tampered_prepared)
        (tampered_prepared / "provider-source-manifest.json").write_text("{}\n", encoding="utf-8")
        tampered_report_path = tampered_prepared / "preparation-report.json"
        tampered_report = load_json(tampered_report_path)
        tampered_report["provider_source_scope"]["manifest_path"] = str(
            tampered_prepared / "provider-source-manifest.json"
        )
        tampered_report_path.write_text(json.dumps(tampered_report), encoding="utf-8")
        try:
            run_benchmark(plan_path, root, root / "tampered-provider-scope-output", tampered_prepared, True)
        except RunnerError as exc:
            assert "provider source manifest hash mismatch" in str(exc)
        else:
            raise AssertionError("runner must reject a tampered provider source manifest")


def main() -> int:
    evidence = expect_valid("design-evidence-example.json", "design-evidence")
    ui_ir = expect_valid("ui-ir-example.json", "ui-ir")
    packet = expect_valid("agent-packet-example.json", "agent-packet")
    benchmark = expect_valid("benchmark-example.json", "benchmark")
    input_context = expect_valid("benchmark-input-context-example.json", "benchmark-input-context")
    missing_provider_scope = deepcopy(input_context)
    del missing_provider_scope["provider_source_scope"]
    expect_invalid(missing_provider_scope, "benchmark-input-context", "schema.required")
    leaked_environment = deepcopy(input_context)
    leaked_environment["environment"]["validator_answers"] = {"binding": "secret"}
    expect_invalid(leaked_environment, "benchmark-input-context", "schema.additionalProperties")
    registry = expect_valid("component-registry-example.json", "component-registry")
    complete_manifest = expect_valid("implementation-manifest-example.json", "implementation-manifest")
    validation_artifact = expect_valid("implementation-validation-example.json", "implementation-validation")
    failed_validation = deepcopy(validation_artifact)
    failed_validation["checks"]["visual"] = "failed"
    _, diagnostics, blocking = validate(failed_validation, "implementation-validation")
    assert not diagnostics and blocking

    test_ui_ir_adversarial(ui_ir)
    test_evidence_adversarial(evidence)
    test_packet_adversarial(packet)
    test_registry_adversarial(registry)
    test_swift_component_index()
    compiled_packet = test_context_compiler(ui_ir, registry)
    test_implementation_manifest(compiled_packet, ui_ir, complete_manifest)
    test_codex_benchmark_executor()
    test_evaluator_dependency_setup_restore()
    test_benchmark_required_binding_projection()
    test_provider_source_scope_worktree()
    test_measured_identity_ignores_fake_node_path()
    test_measured_executor_shield()
    test_provider_receipt_parser_adversarial()
    test_executor_timeout_kills_process_group()
    test_isolated_timeout_restores_after_descendants_exit()
    test_pinned_tree_slice_rejects_history()
    test_measured_repository_boundaries()
    test_benchmark_gates(benchmark)
    test_ios_semantic_visual_validator(benchmark)
    test_independent_png_alpha_diff()
    test_binding_declaration_rejects_bait()
    test_magic_number_semantic_filter()
    test_measured_run_plan_freezer()
    test_benchmark_case_contract()
    test_benchmark_runner()

    print("PASS design-context-compiler self-test: schemas, Registry index, dependency closure, Agent Packet budget, Manifest handoff gate, isolated prepared real benchmark case, Codex provider receipt, pinned-checkout runner, validation config linkage, structured artifact chain, staged benchmark gains")
    return 0


if __name__ == "__main__":
    sys.exit(main())
