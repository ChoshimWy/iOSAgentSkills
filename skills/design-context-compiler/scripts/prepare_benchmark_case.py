#!/usr/bin/env python3
"""Materialize and verify a real pre-run Design Context benchmark case."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from typing import Any

from compile_agent_packet import compile_packet
from validate_contract import load_json, validate, validate_against_schema


EXPECTED_INPUTS = {
    "screenshot-only": {"reference", "shared-prompt", "validation-config"},
    "ui-ir": {"reference", "shared-prompt", "validation-config", "ui-ir"},
    "ui-ir-with-binding": {"reference", "shared-prompt", "validation-config", "agent-packet"},
}
INPUT_AUDIENCE = {
    "reference": "agent",
    "shared-prompt": "agent",
    "validation-config": "validator",
    "ui-ir": "agent",
    "agent-packet": "agent",
}
DEFAULT_SKETCHTOOL = Path("/Applications/Sketch.app/Contents/Resources/sketchtool/bin/sketchtool")


class PreparationError(ValueError):
    """A deterministic readiness or integrity gate failed."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_required_registry_bindings(
    registry: dict[str, Any],
    validation_config: dict[str, Any],
    ui_framework: str,
) -> None:
    """Verify Registry-owned binding identity without discarding validator-only observation fields."""
    expected = [
        {
            "id": binding["id"],
            "registry_entry_id": entry["id"],
            "code_symbol": binding["symbol"],
            "source": binding["source"],
        }
        for entry in registry["entries"]
        if entry["status"] == "active" and entry["reuse_policy"] == "required"
        for binding in entry["bindings"]
        if binding["framework"] == ui_framework
        or (ui_framework == "mixed-ui" and binding["framework"] in {"UIKit", "SwiftUI"})
    ]
    actual = [
        {
            "id": binding["id"],
            "registry_entry_id": binding["registry_entry_id"],
            "code_symbol": binding["code_symbol"],
            "source": binding["source"],
        }
        for binding in validation_config["required_bindings"]
    ]
    if actual != expected:
        raise PreparationError("validation config required_bindings differ from active required Registry bindings")


def _provider_source_manifest(code_root: Path, commit: str, scope: dict[str, Any]) -> dict[str, Any]:
    """Resolve an allowlisted provider view from the frozen Git tree without reading the worktree."""
    if scope.get("mode") != "allowlist":
        raise PreparationError("unsupported provider source scope mode")
    normalized: list[tuple[str, str]] = []
    for item in scope.get("entries", []):
        kind = item.get("kind")
        raw = item.get("path")
        if kind not in {"file", "directory"} or not isinstance(raw, str):
            raise PreparationError("provider source scope entry is invalid")
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts or raw != path.as_posix() or not raw:
            raise PreparationError(f"provider source scope path is not normalized: {raw!r}")
        value = raw.rstrip("/")
        normalized.append((kind, value))
    if not normalized or len(normalized) != len(set(normalized)):
        raise PreparationError("provider source scope entries must be non-empty and unique")

    result = subprocess.run(
        ["git", "-C", str(code_root), "ls-tree", "-r", "-l", "-z", commit],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise PreparationError(f"unable to enumerate provider source scope: {result.stderr.decode(errors='replace').strip()}")
    matched = {entry: 0 for entry in normalized}
    files: list[dict[str, Any]] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        header, raw_path = record.split(b"\t", 1)
        mode, object_type, object_id, raw_size = header.decode("ascii").split()
        path = raw_path.decode("utf-8", errors="strict")
        selected_entries: list[tuple[str, str]] = []
        for entry in normalized:
            kind, value = entry
            if (kind == "file" and path == value) or (kind == "directory" and path.startswith(value + "/")):
                matched[entry] += 1
                selected_entries.append(entry)
        if len(selected_entries) > 1:
            rendered = [f"{kind}:{value}" for kind, value in selected_entries]
            raise PreparationError(f"provider source scope entries overlap for {path}: {rendered}")
        if not selected_entries:
            continue
        if object_type != "blob" or mode not in {"100644", "100755"} or raw_size == "-":
            raise PreparationError(f"provider source scope contains unsupported Git entry: {path}")
        files.append({"path": path, "git_mode": mode, "blob_sha1": object_id, "bytes": int(raw_size)})
    missing = [f"{kind}:{path}" for (kind, path), count in matched.items() if count == 0]
    if missing:
        raise PreparationError(f"provider source scope entries matched no frozen files: {missing}")
    files.sort(key=lambda item: item["path"])
    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest = {
        "provider_source_manifest_version": "1.0.0",
        "mode": "allowlist",
        "code_baseline_commit": commit,
        "scope_entries": [{"kind": kind, "path": path} for kind, path in normalized],
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "content_sha256": hashlib.sha256(canonical).hexdigest(),
        "files": files,
    }
    _, diagnostics, blocking = validate(manifest, "provider-source-manifest")
    if diagnostics or blocking:
        raise PreparationError(
            f"generated provider source manifest is invalid: {[item.as_dict() for item in diagnostics]} {blocking}"
        )
    return manifest


def _verify_provider_source_scope(code_root: Path, commit: str, scope: dict[str, Any]) -> dict[str, Any]:
    manifest = _provider_source_manifest(code_root, commit, scope)
    expected = {
        "file_count": scope["expected_file_count"],
        "total_bytes": scope["expected_total_bytes"],
        "content_sha256": scope["expected_content_sha256"],
    }
    actual = {key: manifest[key] for key in expected}
    if actual != expected:
        raise PreparationError(f"provider source scope identity mismatch: expected {expected}, got {actual}")
    return manifest


def _within(base: Path, candidate: Path) -> Path:
    resolved_base = base.resolve()
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_base)
    except ValueError as exc:
        raise PreparationError(f"artifact escapes its declared root: {candidate}") from exc
    return resolved


def _verify_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise PreparationError(f"{label} is missing: {path}")
    actual = sha256(path)
    if actual != expected:
        raise PreparationError(f"{label} hash mismatch: expected {expected}, got {actual}: {path}")


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise PreparationError(f"reference export is not a valid PNG: {path}")
    return struct.unpack(">II", header[16:24])


def _local_artifact(case_dir: Path, ref: dict[str, Any], label: str) -> Path:
    path = _within(case_dir, case_dir / ref["path"])
    _verify_hash(path, ref["sha256"], label)
    return path


def _rooted_artifact(roots: dict[str, Path], ref: dict[str, Any], label: str) -> Path:
    root_id = ref["root"]
    if root_id not in roots:
        raise PreparationError(f"{label} references unknown root: {root_id}")
    path = _within(roots[root_id], roots[root_id] / ref["path"])
    _verify_hash(path, ref["sha256"], label)
    return path


def _validate_contract(path: Path, kind: str) -> dict[str, Any]:
    data = load_json(path)
    _, diagnostics, blocking = validate(data, kind)
    if diagnostics:
        raise PreparationError(f"invalid {kind}: {[item.as_dict() for item in diagnostics]}")
    if blocking:
        raise PreparationError(f"blocked {kind}: {blocking}")
    return data


def _resolve_sketchtool(explicit: Path | None) -> Path:
    if explicit is not None:
        candidate = explicit.expanduser().resolve()
    elif DEFAULT_SKETCHTOOL.is_file():
        candidate = DEFAULT_SKETCHTOOL
    else:
        found = shutil.which("sketchtool")
        if not found:
            raise PreparationError("sketchtool was not found; install Sketch or pass --sketchtool")
        candidate = Path(found).resolve()
    if not candidate.is_file():
        raise PreparationError(f"sketchtool is missing: {candidate}")
    return candidate


def _export_reference(
    sketchtool: Path,
    design_file: Path,
    node_id: str,
    scale: float,
    output_dir: Path,
) -> Path:
    export_dir = output_dir / "_export"
    export_dir.mkdir(parents=True, exist_ok=True)
    exported = _within(export_dir, export_dir / f"{node_id}.png")
    exported.unlink(missing_ok=True)
    command = [
        str(sketchtool),
        "export",
        "layers",
        str(design_file),
        f"--output={export_dir}",
        "--formats=png",
        f"--item={node_id}",
        f"--scales={scale:g}",
        "--overwriting=YES",
        "--use-id-for-name=YES",
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise PreparationError(f"sketchtool export failed ({result.returncode}): {detail}")
    if not exported.is_file():
        raise PreparationError(f"sketchtool did not create the expected layer export: {exported}")
    return exported


def _verify_links(
    case: dict[str, Any],
    design_file: Path,
    evidence: dict[str, Any],
    ui_ir: dict[str, Any],
    registry: dict[str, Any],
    stored_packet: dict[str, Any],
    validation_config: dict[str, Any],
    roots: dict[str, Path],
    reference: Path,
) -> None:
    design = case["source"]["design"]
    design_file_ref = design["file"]
    expected_document_id = Path(design_file_ref["path"]).name
    expected_evidence_hash = f"sha256:{design['reference_export']['expected_sha256']}"
    if evidence["source"].get("kind") != "sketch" or ui_ir["source"].get("kind") != "sketch":
        raise PreparationError("Design Evidence and UI IR must preserve the Sketch source kind")
    if evidence["source"].get("document_id") != expected_document_id or ui_ir["source"].get("document_id") != expected_document_id:
        raise PreparationError("Design Evidence/UI IR document_id does not match the benchmark design file")
    if evidence["source"].get("document_sha256") != design_file_ref["sha256"] or sha256(design_file) != design_file_ref["sha256"]:
        raise PreparationError("Design Evidence document hash does not match the frozen design file")
    if evidence["source"]["node_id"] != design["node_id"] or ui_ir["source"]["node_id"] != design["node_id"]:
        raise PreparationError("Design Evidence/UI IR node_id does not match the benchmark design node")
    if evidence["source"]["version"] != design["document_version"] or ui_ir["source"]["version"] != design["document_version"]:
        raise PreparationError("Design Evidence/UI IR version does not match the benchmark design version")
    if evidence["snapshot"]["evidence_hash"] != expected_evidence_hash or ui_ir["source"]["evidence_hash"] != expected_evidence_hash:
        raise PreparationError("Design Evidence/UI IR reference hash is not linked to the exported reference")
    expected_export = design["reference_export"]
    expected_viewport = expected_export["expected_viewport"]
    viewport = {"width": _png_size(reference)[0], "height": _png_size(reference)[1]}
    environment = case["benchmark"]["environment"]
    packet_reference = stored_packet["reference"]
    if not all(
        candidate == expected_viewport
        for candidate in (
            viewport,
            environment["viewport"],
            evidence["snapshot"]["viewport"],
            ui_ir["reference"]["viewport"],
            packet_reference["viewport"],
            validation_config["reference_viewport"],
        )
    ):
        raise PreparationError("reference viewport differs across export, case, Evidence, UI IR, Packet, or validation config")
    if evidence["snapshot"].get("reference_image") != expected_export["expected_output"]:
        raise PreparationError("Design Evidence reference image name differs from the generated reference")
    if ui_ir["reference"].get("image") != expected_export["expected_output"] or packet_reference.get("image") != expected_export["expected_output"]:
        raise PreparationError("UI IR/Agent Packet reference image name differs from the generated reference")
    if packet_reference.get("source_hash") != expected_evidence_hash:
        raise PreparationError("Agent Packet reference hash is not linked to the exported reference")

    reference_fields = {
        "scale": (expected_export["scale"], environment["scale"], evidence["snapshot"]["scale"], ui_ir["reference"]["scale"], packet_reference["scale"], validation_config["reference_scale"]),
        "appearance": (environment["appearance"], evidence["snapshot"]["appearance"], ui_ir["reference"]["appearance"], packet_reference["appearance"], validation_config["appearance"]),
        "locale": (environment["locale"], evidence["snapshot"]["locale"], ui_ir["reference"]["locale"], packet_reference["locale"], validation_config["locale"]),
    }
    for field, values in reference_fields.items():
        if len(set(values)) != 1:
            raise PreparationError(f"reference {field} differs across case, Evidence, UI IR, Packet, or validation config")

    scene_ids = {scene["id"] for scene in ui_ir["state"]["scenes"]}
    if environment["screen"] != ui_ir["screen"]["id"] or stored_packet["task"]["screen"] != environment["screen"]:
        raise PreparationError("benchmark screen differs from UI IR or Agent Packet task screen")
    if environment["state"] not in scene_ids or stored_packet["task"]["requested_states"] != [environment["state"]]:
        raise PreparationError("benchmark state is missing or differs from Agent Packet requested state")
    if environment["ui_framework"] != ui_ir["environment"]["ui_framework"] or stored_packet["environment"]["ui_framework"] != environment["ui_framework"]:
        raise PreparationError("benchmark ui_framework differs from UI IR or Agent Packet environment")
    if stored_packet["environment"] != ui_ir["environment"]:
        raise PreparationError("Agent Packet environment differs from UI IR environment")

    required_regions = ui_ir["validation"]["required_regions"]
    if stored_packet["acceptance"]["required_regions"] != required_regions:
        raise PreparationError("Agent Packet acceptance regions differ from UI IR validation regions")
    if validation_config["required_regions"] != required_regions:
        raise PreparationError("validation config required_regions differ from UI IR/Agent Packet")
    if validation_config["ignore_regions"] != ui_ir["validation"]["ignore_regions"]:
        raise PreparationError("validation config ignore_regions differ from UI IR validation regions")

    _verify_required_registry_bindings(registry, validation_config, environment["ui_framework"])

    code_root_id = case["source"]["code"]["root"]
    code_root = roots[code_root_id]
    frozen_code_paths = {item["path"] for item in case["source"]["code"]["files"]}
    for entry in registry["entries"]:
        for binding in entry["bindings"]:
            if binding["source"] not in frozen_code_paths:
                raise PreparationError(f"Registry binding source is not frozen in the code baseline: {binding['source']}")
            source = _within(code_root, code_root / binding["source"])
            if not source.is_file():
                raise PreparationError(f"Registry binding source is missing: {source}")
            line_number = binding.get("declaration_line")
            if line_number is not None:
                lines = source.read_text(encoding="utf-8").splitlines()
                if line_number > len(lines):
                    raise PreparationError(f"Registry declaration line is outside source: {binding['id']}")
                actual = hashlib.sha256(lines[line_number - 1].strip().encode("utf-8")).hexdigest()
                if binding["declaration_hash"] != f"sha256:{actual}":
                    raise PreparationError(f"Registry declaration hash is stale: {binding['id']}")

    compiled = compile_packet(
        ui_ir,
        registry,
        stored_packet["task"]["target_id"],
        stored_packet["task"]["target_kind"],
        stored_packet["task"]["requested_states"],
        stored_packet["context_budget"]["max_tokens"],
    )
    if compiled != stored_packet:
        raise PreparationError("stored Agent Packet is stale; recompile it from the frozen UI IR and Registry")


def _materialize_variants(
    case: dict[str, Any],
    output_dir: Path,
    sources: dict[str, Path],
) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    file_names = {
        "reference": "reference.png",
        "shared-prompt": "shared-prompt.md",
        "validation-config": "validation-config.json",
        "ui-ir": "ui-ir.json",
        "agent-packet": "agent-packet.json",
    }
    variants_root = _within(output_dir, output_dir / "variants")
    if variants_root.exists():
        shutil.rmtree(variants_root)
    variants_root.mkdir(parents=True)
    for variant in case["benchmark"]["variants"]:
        name = variant["variant"]
        kinds = {item["kind"] for item in variant["inputs"]}
        if kinds != EXPECTED_INPUTS[name]:
            raise PreparationError(f"variant {name} has an invalid input set: {sorted(kinds)}")
        variant_dir = _within(variants_root, variants_root / name)
        variant_dir.mkdir()
        inputs = []
        for item in variant["inputs"]:
            kind = item["kind"]
            source_key = item["artifact"]["source"]
            source = sources[source_key]
            destination = variant_dir / file_names[kind]
            shutil.copyfile(source, destination)
            inputs.append(
                {
                    "kind": kind,
                    "audience": INPUT_AUDIENCE[kind],
                    "path": destination.name,
                    "sha256": sha256(destination),
                }
            )
        manifest = {
            "case_id": case["case_id"],
            "variant": name,
            "environment": case["benchmark"]["environment"],
            "inputs": inputs,
            "measured_result": None,
        }
        manifest_path = variant_dir / "input-manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        materialized.append({"variant": name, "input_manifest": str(manifest_path), "sha256": sha256(manifest_path)})
    return materialized


def _write_unbound_ui_ir(
    ui_ir: dict[str, Any],
    registry: dict[str, Any],
    output_dir: Path,
    expected_sha256: str,
) -> Path:
    """Create the UI-IR-only control input without leaking code bindings."""
    projected = deepcopy(ui_ir)

    def strip(node: dict[str, Any]) -> None:
        component = node.get("component")
        if isinstance(component, dict):
            component["bindings"] = []
        for child in node.get("children", []):
            strip(child)

    strip(projected["tree"])
    # 生产级 UI IR 会刻意拒绝缺少 binding 的 required 组件；该投影仅用于 benchmark 对照，
    # 不能用于实施 handoff，因此这里只校验未改变的 UI IR 结构，不降低生产语义门禁。
    diagnostics = validate_against_schema(projected, "ui-ir")
    if diagnostics:
        raise PreparationError(
            f"unbound UI IR projection is structurally invalid: {[item.as_dict() for item in diagnostics]}"
        )
    serialized = json.dumps(projected, ensure_ascii=False, indent=2) + "\n"
    for entry in registry["entries"]:
        for binding in entry["bindings"]:
            for leaked in (binding["id"], binding["symbol"], binding["source"]):
                if leaked in serialized:
                    raise PreparationError(f"unbound UI IR projection leaks code binding data: {leaked}")
    path = _within(output_dir, output_dir / "ui-ir-unbound.json")
    path.write_text(serialized, encoding="utf-8")
    _verify_hash(path, expected_sha256, "unbound UI IR projection")
    return path


def prepare(case_path: Path, workspace_root: Path, output_dir: Path, sketchtool_path: Path | None) -> dict[str, Any]:
    case_path = case_path.resolve()
    case_dir = case_path.parent
    case = _validate_contract(case_path, "benchmark-case")
    if case["readiness_status"] != "ready" or not case["readiness"]["ready"]:
        raise PreparationError("benchmark case is not marked ready")
    if case["readiness"]["measured_results"]:
        raise PreparationError("pre-run benchmark case must not claim measured results")

    workspace_root = workspace_root.resolve()
    roots: dict[str, Path] = {}
    for item in case["workspace_roots"]:
        root = (workspace_root / item["path"]).resolve()
        if not root.is_dir():
            raise PreparationError(f"workspace root is missing: {item['id']} -> {root}")
        roots[item["id"]] = root

    design_file = _rooted_artifact(roots, case["source"]["design"]["file"], "design source")
    code = case["source"]["code"]
    code_root = roots[code["root"]]
    worktree_head = subprocess.run(
        ["git", "-C", str(code_root), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if worktree_head.returncode != 0:
        raise PreparationError(f"unable to read code repository HEAD: {worktree_head.stderr.strip()}")
    commit_exists = subprocess.run(
        ["git", "-C", str(code_root), "cat-file", "-e", f"{code['git_commit']}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    if commit_exists.returncode != 0:
        raise PreparationError(f"declared code baseline commit does not exist: {code['git_commit']}")
    for index, file_ref in enumerate(code["files"]):
        path = _rooted_artifact(roots, file_ref, f"code baseline file {index}")
        committed = subprocess.run(
            ["git", "-C", str(code_root), "show", f"{code['git_commit']}:{file_ref['path']}"],
            capture_output=True,
            check=False,
        )
        if committed.returncode != 0:
            detail = committed.stderr.decode("utf-8", errors="replace").strip()
            raise PreparationError(f"code baseline file is not present in the declared commit: {file_ref['path']}: {detail}")
        committed_hash = hashlib.sha256(committed.stdout).hexdigest()
        if committed_hash != file_ref["sha256"]:
            raise PreparationError(
                f"code baseline file does not match declared commit content: {file_ref['path']}: "
                f"expected {file_ref['sha256']}, commit has {committed_hash}, worktree has {sha256(path)}"
            )
    provider_source_manifest = None
    if isinstance(code.get("provider_source_scope"), dict):
        provider_source_manifest = _verify_provider_source_scope(
            code_root,
            code["git_commit"],
            code["provider_source_scope"],
        )

    contracts = case["contracts"]
    evidence_path = _local_artifact(case_dir, contracts["design_evidence"], "Design Evidence")
    ui_ir_path = _local_artifact(case_dir, contracts["ui_ir"], "UI IR")
    registry_path = _local_artifact(case_dir, contracts["component_registry"], "Component Registry")
    packet_path = _local_artifact(case_dir, contracts["agent_packet"], "Agent Packet")
    prompt_path = _local_artifact(case_dir, case["benchmark"]["shared_prompt"], "shared prompt")
    validation_path = _local_artifact(case_dir, case["benchmark"]["validation_config"], "validation config")

    evidence = _validate_contract(evidence_path, "design-evidence")
    ui_ir = _validate_contract(ui_ir_path, "ui-ir")
    registry = _validate_contract(registry_path, "component-registry")
    stored_packet = _validate_contract(packet_path, "agent-packet")
    validation_config = _validate_contract(validation_path, "benchmark-validation-config")
    if not prompt_path.read_text(encoding="utf-8").strip():
        raise PreparationError("shared prompt must not be empty")

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    provider_source_manifest_path = None
    if provider_source_manifest is not None:
        provider_source_manifest_path = _within(output_dir, output_dir / "provider-source-manifest.json")
        provider_source_manifest_path.write_text(
            json.dumps(provider_source_manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    sketchtool = _resolve_sketchtool(sketchtool_path)
    exported = _export_reference(
        sketchtool,
        design_file,
        case["source"]["design"]["node_id"],
        case["source"]["design"]["reference_export"]["scale"],
        output_dir,
    )
    reference = _within(
        output_dir,
        output_dir / case["source"]["design"]["reference_export"]["expected_output"],
    )
    shutil.copyfile(exported, reference)
    _verify_hash(reference, case["source"]["design"]["reference_export"]["expected_sha256"], "reference export")
    _verify_links(case, design_file, evidence, ui_ir, registry, stored_packet, validation_config, roots, reference)
    unbound_ui_ir = _write_unbound_ui_ir(ui_ir, registry, output_dir, contracts["ui_ir_unbound"]["sha256"])

    sources = {
        "generated-reference": reference,
        "generated-ui-ir-unbound": unbound_ui_ir,
        "shared_prompt": prompt_path,
        "validation_config": validation_path,
        "agent_packet": packet_path,
    }
    variants = _materialize_variants(case, output_dir, sources)
    report = {
        "preparation_version": "1.0.0",
        "status": "ready",
        "case_id": case["case_id"],
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "case_path": str(case_path),
        "case_sha256": sha256(case_path),
        "design_source_sha256": sha256(design_file),
        "code_baseline_commit": code["git_commit"],
        "source_worktree_head": worktree_head.stdout.strip(),
        "source_worktree_at_baseline": worktree_head.stdout.strip() == code["git_commit"],
        "provider_source_scope": (
            {
                "mode": provider_source_manifest["mode"],
                "manifest_path": str(provider_source_manifest_path),
                "manifest_sha256": sha256(provider_source_manifest_path),
                "file_count": provider_source_manifest["file_count"],
                "total_bytes": provider_source_manifest["total_bytes"],
                "content_sha256": provider_source_manifest["content_sha256"],
            }
            if provider_source_manifest is not None and provider_source_manifest_path is not None
            else {"mode": "full-tree"}
        ),
        "reference": {
            "path": str(reference),
            "sha256": sha256(reference),
            "viewport": {"width": _png_size(reference)[0], "height": _png_size(reference)[1]},
        },
        "ui_ir_control_projection": {
            "path": str(unbound_ui_ir),
            "projection": contracts["ui_ir_unbound"]["projection"],
            "sha256": sha256(unbound_ui_ir),
            "handoff_allowed": False,
        },
        "variants": variants,
        "measured_results": False,
        "next_action": "run the three variants with the same model/reasoning baseline, then create benchmark-v1 measured artifacts",
    }
    report_path = output_dir / "preparation-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**report, "report_path": str(report_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, help="benchmark-case-v1 JSON")
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd(), help="root used to resolve workspace_roots")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sketchtool", type=Path)
    args = parser.parse_args()
    try:
        report = prepare(args.case, args.workspace_root, args.output_dir, args.sketchtool)
    except (PreparationError, ValueError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
