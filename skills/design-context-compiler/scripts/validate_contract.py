#!/usr/bin/env python3
"""Validate Design Context Compiler JSON contracts without third-party packages."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable


UI_IR_REQUIRED = {
    "schema_version",
    "source",
    "reference",
    "environment",
    "screen",
    "state",
    "tokens",
    "tree",
    "responsive",
    "accessibility",
    "validation",
    "unknowns",
}
EVIDENCE_REQUIRED = {"evidence_version", "source", "snapshot", "extracted", "unknowns"}
PACKET_REQUIRED = {
    "packet_version",
    "task",
    "reference",
    "environment",
    "nodes",
    "tokens",
    "bindings",
    "states",
    "interactions",
    "responsive",
    "accessibility",
    "code_anchors",
    "unknowns",
    "acceptance",
    "context_budget",
}
BENCHMARK_REQUIRED = {
    "benchmark_version",
    "case_id",
    "evidence_status",
    "environment",
    "thresholds",
    "candidates",
}
BENCHMARK_CASE_REQUIRED = {
    "case_version",
    "case_id",
    "readiness_status",
    "workspace_roots",
    "source",
    "contracts",
    "benchmark",
    "readiness",
}
REGISTRY_REQUIRED = {"registry_version", "generated_at", "source_roots", "entries"}
MANIFEST_REQUIRED = {"manifest_version", "status", "screen", "source", "mappings", "validation"}
EXPECTED_VARIANTS = {"screenshot-only", "ui-ir", "ui-ir-with-binding"}
DIMENSION_MODES = {"fill", "fixed", "intrinsic", "hug", "min", "max"}
POSITION_MODES = {"flow", "overlay", "absolute", "sticky"}
REFERENCES = Path(__file__).resolve().parents[1] / "references"
SCHEMA_FILES = {
    "design-evidence": REFERENCES / "design-evidence-v1.schema.json",
    "ui-ir": REFERENCES / "ui-ir-v1.1.schema.json",
    "agent-packet": REFERENCES / "agent-packet-v1.schema.json",
    "benchmark": REFERENCES / "benchmark-v1.schema.json",
    "benchmark-case": REFERENCES / "benchmark-case-v1.schema.json",
    "benchmark-validation-config": REFERENCES / "benchmark-validation-config-v1.schema.json",
    "benchmark-validator-probe": REFERENCES / "benchmark-validator-probe-v1.schema.json",
    "benchmark-run-plan": REFERENCES / "benchmark-run-plan-v1.schema.json",
    "benchmark-input-context": REFERENCES / "benchmark-input-context-v1.schema.json",
    "provider-source-manifest": REFERENCES / "provider-source-manifest-v1.schema.json",
    "benchmark-run-result": REFERENCES / "benchmark-run-result-v1.schema.json",
    "benchmark-semantic-evidence": REFERENCES / "benchmark-semantic-evidence-v1.schema.json",
    "benchmark-visual-diff": REFERENCES / "benchmark-visual-diff-v1.schema.json",
    "benchmark-run-observation": REFERENCES / "benchmark-run-observation-v1.schema.json",
    "benchmark-artifact": REFERENCES / "benchmark-run-artifact-v1.schema.json",
    "component-registry": REFERENCES / "component-registry-v1.schema.json",
    "implementation-manifest": REFERENCES / "implementation-manifest-v1.schema.json",
    "implementation-validation": REFERENCES / "implementation-validation-v1.schema.json",
}


@dataclass(frozen=True)
class Diagnostic:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


def load_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant is not allowed: {value}")

    try:
        return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def _require_keys(value: Any, required: Iterable[str], path: str, out: list[Diagnostic]) -> dict[str, Any]:
    if not isinstance(value, dict):
        out.append(Diagnostic(path, "type", "expected object"))
        return {}
    for key in sorted(set(required) - set(value)):
        out.append(Diagnostic(f"{path}.{key}", "required", "missing required field"))
    return value


def _require_list(value: Any, path: str, out: list[Diagnostic]) -> list[Any]:
    if not isinstance(value, list):
        out.append(Diagnostic(path, "type", "expected array"))
        return []
    return value


def _require_non_empty_string(value: Any, path: str, out: list[Diagnostic]) -> None:
    if not isinstance(value, str) or not value.strip():
        out.append(Diagnostic(path, "value", "expected non-empty string"))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _json_equal(lhs: Any, rhs: Any) -> bool:
    return type(lhs) is type(rhs) and lhs == rhs


def estimate_agent_packet_tokens(packet: dict[str, Any]) -> int:
    """Return a deterministic estimate independent of self-referential budget fields."""
    normalized = deepcopy(packet)
    budget = normalized.get("context_budget")
    if isinstance(budget, dict):
        budget["estimated_tokens"] = 0
        budget["within_budget"] = True
    return math.ceil(len(json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))) / 4)


def _matches_type(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": _is_number(value),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def _resolve_local_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"only local schema refs are supported: {ref}")
    current: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"unresolved schema ref: {ref}")
        current = current[part]
    if not isinstance(current, dict):
        raise ValueError(f"schema ref does not resolve to object: {ref}")
    return current


def _schema_errors(value: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return _schema_errors(value, _resolve_local_ref(root_schema, ref), root_schema, path)

    for child_schema in schema.get("allOf", []):
        if isinstance(child_schema, dict):
            out.extend(_schema_errors(value, child_schema, root_schema, path))
    condition = schema.get("if")
    if isinstance(condition, dict):
        condition_matches = not _schema_errors(value, condition, root_schema, path)
        branch = schema.get("then") if condition_matches else schema.get("else")
        if isinstance(branch, dict):
            out.extend(_schema_errors(value, branch, root_schema, path))

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = [expected_type] if isinstance(expected_type, str) else expected_type
        if not isinstance(expected_types, list) or not any(
            isinstance(item, str) and _matches_type(value, item) for item in expected_types
        ):
            out.append(Diagnostic(path, "schema.type", f"expected type {expected_type}"))
            return out

    if "const" in schema and not _json_equal(value, schema["const"]):
        out.append(Diagnostic(path, "schema.const", f"expected constant {schema['const']!r}"))
    enum = schema.get("enum")
    if isinstance(enum, list) and not any(_json_equal(value, item) for item in enum):
        out.append(Diagnostic(path, "schema.enum", f"expected one of {enum}"))

    if isinstance(value, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if isinstance(key, str) and key not in value:
                    out.append(Diagnostic(f"{path}.{key}", "schema.required", "missing required field"))
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}
        additional = schema.get("additionalProperties", True)
        for key, child in value.items():
            child_path = f"{path}.{key}"
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                out.extend(_schema_errors(child, child_schema, root_schema, child_path))
            elif additional is False:
                out.append(Diagnostic(child_path, "schema.additionalProperties", "unexpected field"))
            elif isinstance(additional, dict):
                out.extend(_schema_errors(child, additional, root_schema, child_path))

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            out.append(Diagnostic(path, "schema.minItems", f"expected at least {min_items} items"))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                out.extend(_schema_errors(item, item_schema, root_schema, f"{path}[{index}]"))

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            out.append(Diagnostic(path, "schema.minLength", f"expected length >= {min_length}"))
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, value) is None:
            out.append(Diagnostic(path, "schema.pattern", f"value does not match {pattern}"))
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError("timezone required")
            except ValueError:
                out.append(Diagnostic(path, "schema.format", "expected RFC 3339 date-time with timezone"))

    if _is_number(value):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        exclusive_minimum = schema.get("exclusiveMinimum")
        exclusive_maximum = schema.get("exclusiveMaximum")
        if _is_number(minimum) and value < minimum:
            out.append(Diagnostic(path, "schema.minimum", f"expected value >= {minimum}"))
        if _is_number(maximum) and value > maximum:
            out.append(Diagnostic(path, "schema.maximum", f"expected value <= {maximum}"))
        if _is_number(exclusive_minimum) and value <= exclusive_minimum:
            out.append(Diagnostic(path, "schema.exclusiveMinimum", f"expected value > {exclusive_minimum}"))
        if _is_number(exclusive_maximum) and value >= exclusive_maximum:
            out.append(Diagnostic(path, "schema.exclusiveMaximum", f"expected value < {exclusive_maximum}"))
    return out


def validate_against_schema(data: Any, kind: str) -> list[Diagnostic]:
    schema_path = SCHEMA_FILES[kind]
    schema = load_json(schema_path)
    if not isinstance(schema, dict):
        raise ValueError(f"schema root must be object: {schema_path}")
    return _schema_errors(data, schema, schema, "$")


def _deduplicate(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    seen: set[tuple[str, str, str]] = set()
    result: list[Diagnostic] = []
    for item in diagnostics:
        key = (item.path, item.code, item.message)
        if key not in seen:
            result.append(item)
            seen.add(key)
    return result


def _validate_node(node: Any, path: str, node_ids: set[str], out: list[Diagnostic]) -> None:
    obj = _require_keys(node, {"id", "type", "role", "layout", "children"}, path, out)
    node_id = obj.get("id")
    _require_non_empty_string(node_id, f"{path}.id", out)
    if isinstance(node_id, str):
        if node_id in node_ids:
            out.append(Diagnostic(f"{path}.id", "duplicate", f"duplicate node id: {node_id}"))
        node_ids.add(node_id)

    layout = _require_keys(obj.get("layout"), {"position", "width", "height"}, f"{path}.layout", out)
    position = layout.get("position")
    if position not in POSITION_MODES:
        out.append(Diagnostic(f"{path}.layout.position", "enum", f"expected one of {sorted(POSITION_MODES)}"))
    if position == "absolute" and not layout.get("reason"):
        out.append(Diagnostic(f"{path}.layout.reason", "required", "absolute layout requires a reason"))

    for name in ("width", "height"):
        dimension = _require_keys(layout.get(name), {"mode"}, f"{path}.layout.{name}", out)
        mode = dimension.get("mode")
        if mode not in DIMENSION_MODES:
            out.append(Diagnostic(f"{path}.layout.{name}.mode", "enum", f"expected one of {sorted(DIMENSION_MODES)}"))
        if mode == "fixed" and not isinstance(dimension.get("value"), (int, float)):
            out.append(Diagnostic(f"{path}.layout.{name}.value", "required", "fixed dimension requires numeric value"))

    component = obj.get("component")
    if component is not None:
        component_obj = _require_keys(
            component,
            {"design_id", "semantic_role", "reuse_policy", "bindings"},
            f"{path}.component",
            out,
        )
        bindings = _require_list(component_obj.get("bindings"), f"{path}.component.bindings", out)
        if component_obj.get("reuse_policy") == "required" and not bindings:
            out.append(Diagnostic(f"{path}.component.bindings", "binding", "required component must have at least one binding"))

    for index, child in enumerate(_require_list(obj.get("children"), f"{path}.children", out)):
        _validate_node(child, f"{path}.children[{index}]", node_ids, out)


def _collect_relative_refs(value: Any, path: str = "$.tree") -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "relative_to" and isinstance(child, str):
                refs.append((child_path, child))
            else:
                refs.extend(_collect_relative_refs(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            refs.extend(_collect_relative_refs(child, f"{path}[{index}]"))
    return refs


def _collect_ids(items: Any, path: str, out: list[Diagnostic]) -> set[str]:
    result: set[str] = set()
    for index, item in enumerate(_require_list(items, path, out)):
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if isinstance(item_id, str):
            if item_id in result:
                out.append(Diagnostic(f"{path}[{index}].id", "duplicate", f"duplicate id: {item_id}"))
            result.add(item_id)
    return result


def _validate_refs(
    refs: Any,
    allowed: set[str],
    path: str,
    out: list[Diagnostic],
) -> None:
    for index, ref in enumerate(_require_list(refs, path, out)):
        if isinstance(ref, str) and ref not in allowed:
            out.append(Diagnostic(f"{path}[{index}]", "reference", f"unknown id: {ref}"))


def validate_ui_ir(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "ui-ir")
    root = _require_keys(data, UI_IR_REQUIRED, "$", out)
    if root.get("schema_version") != "1.1.0":
        out.append(Diagnostic("$.schema_version", "version", "expected 1.1.0"))

    source = _require_keys(
        root.get("source"),
        {"kind", "document_id", "node_id", "version", "captured_at", "parser_version", "evidence_hash"},
        "$.source",
        out,
    )
    for key in ("kind", "document_id", "node_id", "version", "captured_at", "parser_version", "evidence_hash"):
        _require_non_empty_string(source.get(key), f"$.source.{key}", out)

    reference = _require_keys(root.get("reference"), {"image", "viewport", "scale", "appearance", "locale"}, "$.reference", out)
    _require_non_empty_string(reference.get("image"), "$.reference.image", out)
    viewport = _require_keys(reference.get("viewport"), {"width", "height"}, "$.reference.viewport", out)
    for key in ("width", "height"):
        if not _is_number(viewport.get(key)) or viewport.get(key, 0) <= 0:
            out.append(Diagnostic(f"$.reference.viewport.{key}", "range", "expected positive number"))

    environment = _require_keys(root.get("environment"), {"platform", "ui_framework", "minimum_os", "device"}, "$.environment", out)
    for key in ("platform", "ui_framework", "minimum_os", "device"):
        _require_non_empty_string(environment.get(key), f"$.environment.{key}", out)

    screen = _require_keys(root.get("screen"), {"id", "name"}, "$.screen", out)
    _require_non_empty_string(screen.get("id"), "$.screen.id", out)
    _require_non_empty_string(screen.get("name"), "$.screen.name", out)

    state = _require_keys(root.get("state"), {"scenes", "transitions"}, "$.state", out)
    scenes = _require_list(state.get("scenes"), "$.state.scenes", out)
    if not scenes:
        out.append(Diagnostic("$.state.scenes", "minItems", "at least one scene is required"))
    scene_ids: set[str] = set()
    for index, scene in enumerate(scenes):
        scene_obj = _require_keys(scene, {"id", "data"}, f"$.state.scenes[{index}]", out)
        scene_id = scene_obj.get("id")
        _require_non_empty_string(scene_id, f"$.state.scenes[{index}].id", out)
        if isinstance(scene_id, str):
            if scene_id in scene_ids:
                out.append(Diagnostic(f"$.state.scenes[{index}].id", "duplicate", f"duplicate scene id: {scene_id}"))
            scene_ids.add(scene_id)
    for index, transition in enumerate(_require_list(state.get("transitions"), "$.state.transitions", out)):
        transition_obj = _require_keys(transition, {"event", "from", "to"}, f"$.state.transitions[{index}]", out)
        for endpoint in ("from", "to"):
            scene_id = transition_obj.get(endpoint)
            if scene_id not in scene_ids:
                out.append(Diagnostic(f"$.state.transitions[{index}].{endpoint}", "reference", f"unknown scene id: {scene_id}"))

    node_ids: set[str] = set()
    _validate_node(root.get("tree"), "$.tree", node_ids, out)
    for ref_path, ref in _collect_relative_refs(root.get("tree")):
        if ref not in node_ids:
            out.append(Diagnostic(ref_path, "reference", f"unknown node id: {ref}"))

    accessibility = _require_keys(root.get("accessibility"), {"dynamic_type", "voice_over", "reduce_motion"}, "$.accessibility", out)
    for key in ("dynamic_type", "voice_over", "reduce_motion"):
        if not isinstance(accessibility.get(key), bool):
            out.append(Diagnostic(f"$.accessibility.{key}", "type", "expected boolean"))

    validation = _require_keys(root.get("validation"), {"similarity_threshold", "required_regions", "ignore_regions"}, "$.validation", out)
    threshold = validation.get("similarity_threshold")
    if not _is_number(threshold) or not 0 <= threshold <= 1:
        out.append(Diagnostic("$.validation.similarity_threshold", "range", "expected number between 0 and 1"))
    _validate_refs(validation.get("required_regions"), node_ids, "$.validation.required_regions", out)

    unknowns = _require_list(root.get("unknowns"), "$.unknowns", out)
    blocking_unknowns: list[dict[str, Any]] = []
    for index, unknown in enumerate(unknowns):
        unknown_obj = _require_keys(unknown, {"path", "reason", "severity", "source"}, f"$.unknowns[{index}]", out)
        if unknown_obj.get("severity") == "blocking":
            blocking_unknowns.append(unknown_obj)
    return out, blocking_unknowns


def validate_design_evidence(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "design-evidence")
    root = _require_keys(data, EVIDENCE_REQUIRED, "$", out)
    if root.get("evidence_version") != "1.0.0":
        out.append(Diagnostic("$.evidence_version", "version", "expected 1.0.0"))
    source = _require_keys(
        root.get("source"),
        {"kind", "document_id", "node_id", "version", "captured_at", "adapter", "adapter_version"},
        "$.source",
        out,
    )
    for key in ("kind", "document_id", "node_id", "version", "captured_at", "adapter", "adapter_version"):
        _require_non_empty_string(source.get(key), f"$.source.{key}", out)
    snapshot = _require_keys(
        root.get("snapshot"),
        {"reference_image", "viewport", "scale", "appearance", "locale", "evidence_hash"},
        "$.snapshot",
        out,
    )
    _require_non_empty_string(snapshot.get("reference_image"), "$.snapshot.reference_image", out)
    _require_non_empty_string(snapshot.get("evidence_hash"), "$.snapshot.evidence_hash", out)
    viewport = _require_keys(snapshot.get("viewport"), {"width", "height"}, "$.snapshot.viewport", out)
    for key in ("width", "height"):
        if not _is_number(viewport.get(key)) or viewport.get(key, 0) <= 0:
            out.append(Diagnostic(f"$.snapshot.viewport.{key}", "range", "expected positive number"))
    extracted = _require_keys(
        root.get("extracted"),
        {"layers", "variables", "styles", "components", "assets", "interactions"},
        "$.extracted",
        out,
    )
    layer_ids: set[str] = set()
    for index, layer in enumerate(_require_list(extracted.get("layers"), "$.extracted.layers", out)):
        layer_obj = _require_keys(layer, {"id", "type", "name"}, f"$.extracted.layers[{index}]", out)
        layer_id = layer_obj.get("id")
        _require_non_empty_string(layer_id, f"$.extracted.layers[{index}].id", out)
        if isinstance(layer_id, str):
            if layer_id in layer_ids:
                out.append(Diagnostic(f"$.extracted.layers[{index}].id", "duplicate", f"duplicate layer id: {layer_id}"))
            layer_ids.add(layer_id)
    unknowns = _require_list(root.get("unknowns"), "$.unknowns", out)
    blocking_unknowns = [item for item in unknowns if isinstance(item, dict) and item.get("severity") == "blocking"]
    return out, blocking_unknowns


def validate_agent_packet(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "agent-packet")
    root = _require_keys(data, PACKET_REQUIRED, "$", out)
    if root.get("packet_version") != "1.0.0":
        out.append(Diagnostic("$.packet_version", "version", "expected 1.0.0"))
    task = _require_keys(root.get("task"), {"screen", "target_kind", "target_id", "requested_states"}, "$.task", out)
    for key in ("screen", "target_kind", "target_id"):
        _require_non_empty_string(task.get(key), f"$.task.{key}", out)
    nodes = _require_list(root.get("nodes"), "$.nodes", out)
    if not nodes:
        out.append(Diagnostic("$.nodes", "minItems", "at least one node is required"))
    node_ids = _collect_ids(nodes, "$.nodes", out)
    node_types = {
        item.get("id"): item.get("type")
        for item in nodes
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    token_ids = _collect_ids(root.get("tokens"), "$.tokens", out)
    binding_ids = _collect_ids(root.get("bindings"), "$.bindings", out)
    state_ids = _collect_ids(root.get("states"), "$.states", out)
    interaction_ids = _collect_ids(root.get("interactions"), "$.interactions", out)
    _collect_ids(root.get("code_anchors"), "$.code_anchors", out)
    binding_map = {
        item.get("id"): item
        for item in _require_list(root.get("bindings"), "$.bindings", out)
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    anchor_pairs = {
        (item.get("symbol"), item.get("source"))
        for item in _require_list(root.get("code_anchors"), "$.code_anchors", out)
        if isinstance(item, dict)
    }
    for binding_id, binding in binding_map.items():
        if (binding.get("symbol"), binding.get("source")) not in anchor_pairs:
            out.append(
                Diagnostic(
                    "$.code_anchors",
                    "binding.anchor",
                    f"missing code anchor for binding: {binding_id}",
                )
            )

    _validate_refs(task.get("requested_states", []), state_ids, "$.task.requested_states", out)
    if task.get("target_kind") == "state" and task.get("target_id") not in task.get("requested_states", []):
        out.append(Diagnostic("$.task.requested_states", "state.seed", "state target must be included in requested_states"))

    target_id = task.get("target_id")
    target_ids = state_ids if task.get("target_kind") == "state" else node_ids
    if isinstance(target_id, str) and target_id not in target_ids:
        out.append(Diagnostic("$.task.target_id", "reference", f"target id not present in packet closure: {target_id}"))
    elif isinstance(target_id, str) and task.get("target_kind") != "state":
        target_kind = task.get("target_kind")
        if node_types.get(target_id) != target_kind:
            out.append(
                Diagnostic(
                    "$.task.target_kind",
                    "target.type",
                    f"target_kind {target_kind!r} does not match node type {node_types.get(target_id)!r}",
                )
            )

    parents: dict[str, str] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        parent = node.get("parent")
        if isinstance(parent, str) and parent not in node_ids:
            out.append(Diagnostic(f"$.nodes[{index}].parent", "reference", f"unknown parent node id: {parent}"))
        elif isinstance(parent, str) and isinstance(node.get("id"), str):
            parents[node["id"]] = parent
        _validate_refs(node.get("token_refs", []), token_ids, f"$.nodes[{index}].token_refs", out)
        _validate_refs(node.get("binding_refs", []), binding_ids, f"$.nodes[{index}].binding_refs", out)
        _validate_refs(node.get("state_refs", []), state_ids, f"$.nodes[{index}].state_refs", out)
        _validate_refs(node.get("interaction_refs", []), interaction_ids, f"$.nodes[{index}].interaction_refs", out)
        component = node.get("component") if isinstance(node.get("component"), dict) else None
        for binding_id in node.get("binding_refs", []):
            binding = binding_map.get(binding_id)
            if component and binding:
                if binding.get("design_id") != component.get("design_id"):
                    out.append(
                        Diagnostic(
                            f"$.nodes[{index}].binding_refs",
                            "binding.component",
                            f"binding {binding_id} design_id does not match node component",
                        )
                    )
                if binding.get("reuse_policy") != component.get("reuse_policy"):
                    out.append(
                        Diagnostic(
                            f"$.nodes[{index}].binding_refs",
                            "binding.component",
                            f"binding {binding_id} reuse_policy does not match node component",
                        )
                    )

    root_ids = node_ids - set(parents)
    if len(root_ids) != 1:
        out.append(Diagnostic("$.nodes", "tree.roots", f"expected exactly one root node, got {sorted(root_ids)}"))
    for node_id in sorted(node_ids):
        visited: set[str] = set()
        current = node_id
        while current in parents:
            if current in visited:
                out.append(Diagnostic("$.nodes", "tree.cycle", f"parent cycle detected from node: {node_id}"))
                break
            visited.add(current)
            current = parents[current]

    for index, interaction in enumerate(_require_list(root.get("interactions"), "$.interactions", out)):
        if not isinstance(interaction, dict):
            continue
        for endpoint in ("from", "to"):
            ref = interaction.get(endpoint)
            if isinstance(ref, str) and ref not in state_ids:
                out.append(Diagnostic(f"$.interactions[{index}].{endpoint}", "reference", f"unknown state id: {ref}"))

    acceptance = root.get("acceptance") if isinstance(root.get("acceptance"), dict) else {}
    _validate_refs(acceptance.get("required_regions", []), node_ids, "$.acceptance.required_regions", out)

    budget = _require_keys(root.get("context_budget"), {"estimated_tokens", "max_tokens", "within_budget"}, "$.context_budget", out)
    estimated = budget.get("estimated_tokens")
    maximum = budget.get("max_tokens")
    within = budget.get("within_budget")
    if not isinstance(estimated, int) or estimated < 0:
        out.append(Diagnostic("$.context_budget.estimated_tokens", "range", "expected non-negative integer"))
    if not isinstance(maximum, int) or maximum <= 0:
        out.append(Diagnostic("$.context_budget.max_tokens", "range", "expected positive integer"))
    if isinstance(estimated, int) and isinstance(maximum, int) and isinstance(within, bool):
        actual_estimate = estimate_agent_packet_tokens(root)
        if estimated != actual_estimate:
            out.append(
                Diagnostic(
                    "$.context_budget.estimated_tokens",
                    "consistency",
                    f"must equal independently computed estimate: {actual_estimate}",
                )
            )
        if within != (estimated <= maximum):
            out.append(Diagnostic("$.context_budget.within_budget", "consistency", "must equal estimated_tokens <= max_tokens"))

    unknowns = _require_list(root.get("unknowns"), "$.unknowns", out)
    blocking_unknowns = [item for item in unknowns if isinstance(item, dict) and item.get("severity") == "blocking"]
    if within is False:
        blocking_unknowns.append(
            {
                "path": "context_budget",
                "reason": "Agent Packet exceeds its context budget.",
                "severity": "blocking",
                "source": "validator",
            }
        )
    return out, blocking_unknowns


def validate_benchmark(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark")
    root = _require_keys(data, BENCHMARK_REQUIRED, "$", out)
    if root.get("benchmark_version") != "1.2.0":
        out.append(Diagnostic("$.benchmark_version", "version", "expected 1.2.0"))
    environment = _require_keys(root.get("environment"), {"screen", "state", "viewport", "locale", "code_baseline"}, "$.environment", out)
    for key in ("screen", "state", "viewport", "locale", "code_baseline"):
        _require_non_empty_string(environment.get(key), f"$.environment.{key}", out)
    overlay_mode = environment.get("capture_overlay_mode")
    overlay_hash = environment.get("capture_overlay_hash")
    if overlay_mode == "none" and overlay_hash is not None:
        out.append(Diagnostic("$.environment.capture_overlay_hash", "consistency", "none capture overlay requires a null hash"))
    if overlay_mode == "git-patch" and not isinstance(overlay_hash, str):
        out.append(Diagnostic("$.environment.capture_overlay_hash", "consistency", "git-patch capture overlay requires a hash"))
    thresholds = _require_keys(
        root.get("thresholds"),
        {"max_layout_deviation_pt", "min_component_reuse_rate", "max_repair_iterations", "max_input_tokens"},
        "$.thresholds",
        out,
    )
    if thresholds.get("min_component_reuse_rate") is not None:
        value = thresholds.get("min_component_reuse_rate")
        if not _is_number(value) or not 0 <= value <= 1:
            out.append(Diagnostic("$.thresholds.min_component_reuse_rate", "range", "expected number between 0 and 1"))

    candidates = _require_list(root.get("candidates"), "$.candidates", out)
    variants: set[str] = set()
    run_ids: set[str] = set()
    metric_names = (
        "layout_deviation_pt",
        "component_reuse_rate",
        "magic_numbers",
        "repair_iterations",
        "input_tokens",
        "manual_minutes",
    )
    for index, candidate in enumerate(candidates):
        candidate_obj = _require_keys(candidate, {"variant", "validation_status", *metric_names}, f"$.candidates[{index}]", out)
        variant = candidate_obj.get("variant")
        if isinstance(variant, str):
            if variant in variants:
                out.append(Diagnostic(f"$.candidates[{index}].variant", "duplicate", f"duplicate variant: {variant}"))
            variants.add(variant)
        if candidate_obj.get("validation_status") not in {"passed", "failed"}:
            out.append(Diagnostic(f"$.candidates[{index}].validation_status", "enum", "expected passed or failed"))
        for metric in metric_names:
            value = candidate_obj.get(metric)
            if not _is_number(value) or value < 0:
                out.append(Diagnostic(f"$.candidates[{index}].{metric}", "range", "expected non-negative number"))
        reuse = candidate_obj.get("component_reuse_rate")
        if _is_number(reuse) and not 0 <= reuse <= 1:
            out.append(Diagnostic(f"$.candidates[{index}].component_reuse_rate", "range", "expected number between 0 and 1"))
        run = candidate_obj.get("run")
        if isinstance(run, dict):
            run_id = run.get("id")
            if isinstance(run_id, str):
                if run_id in run_ids:
                    out.append(Diagnostic(f"$.candidates[{index}].run.id", "duplicate", f"duplicate run id: {run_id}"))
                run_ids.add(run_id)
            started_at = run.get("started_at")
            completed_at = run.get("completed_at")
            if isinstance(started_at, str) and isinstance(completed_at, str):
                try:
                    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    completed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                    if completed < started:
                        out.append(Diagnostic(f"$.candidates[{index}].run.completed_at", "order", "completed_at must not precede started_at"))
                except ValueError:
                    pass
    if variants != EXPECTED_VARIANTS:
        out.append(Diagnostic("$.candidates", "variants", f"expected exactly {sorted(EXPECTED_VARIANTS)}, got {sorted(variants)}"))
    return out, []


def validate_benchmark_case(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    """Validate a pre-run benchmark case without treating it as measured evidence."""
    out = validate_against_schema(data, "benchmark-case")
    blocking_unknowns: list[dict[str, Any]] = []
    root = _require_keys(data, BENCHMARK_CASE_REQUIRED, "$", out)
    if root.get("case_version") != "1.0.0":
        out.append(Diagnostic("$.case_version", "version", "expected 1.0.0"))

    root_ids: set[str] = set()
    for index, workspace_root in enumerate(_require_list(root.get("workspace_roots"), "$.workspace_roots", out)):
        if not isinstance(workspace_root, dict):
            continue
        root_id = workspace_root.get("id")
        if isinstance(root_id, str):
            if root_id in root_ids:
                out.append(
                    Diagnostic(
                        f"$.workspace_roots[{index}].id",
                        "duplicate",
                        f"duplicate workspace root id: {root_id}",
                    )
                )
            root_ids.add(root_id)

    source = root.get("source") if isinstance(root.get("source"), dict) else {}
    rooted_references: list[tuple[str, Any]] = []
    design = source.get("design") if isinstance(source.get("design"), dict) else {}
    rooted_references.append(("$.source.design.file.root", (design.get("file") or {}).get("root") if isinstance(design.get("file"), dict) else None))
    code = source.get("code") if isinstance(source.get("code"), dict) else {}
    rooted_references.append(("$.source.code.root", code.get("root")))
    for index, file_ref in enumerate(_require_list(code.get("files"), "$.source.code.files", out)):
        if isinstance(file_ref, dict):
            rooted_references.append((f"$.source.code.files[{index}].root", file_ref.get("root")))
            if isinstance(code.get("root"), str) and file_ref.get("root") != code.get("root"):
                out.append(
                    Diagnostic(
                        f"$.source.code.files[{index}].root",
                        "reference",
                        "code baseline files must use source.code.root",
                    )
                )
    for path, root_id in rooted_references:
        if isinstance(root_id, str) and root_id not in root_ids:
            out.append(Diagnostic(path, "reference", f"unknown workspace root: {root_id}"))

    benchmark = root.get("benchmark") if isinstance(root.get("benchmark"), dict) else {}
    variants = _require_list(benchmark.get("variants"), "$.benchmark.variants", out)
    seen_variants: set[str] = set()
    expected_inputs = {
        "screenshot-only": {"reference", "shared-prompt", "validation-config"},
        "ui-ir": {"reference", "shared-prompt", "validation-config", "ui-ir"},
        "ui-ir-with-binding": {"reference", "shared-prompt", "validation-config", "agent-packet"},
    }
    expected_sources = {
        "reference": "generated-reference",
        "shared-prompt": "shared_prompt",
        "validation-config": "validation_config",
        "ui-ir": "generated-ui-ir-unbound",
        "agent-packet": "agent_packet",
    }
    for index, variant in enumerate(variants):
        if not isinstance(variant, dict):
            continue
        variant_name = variant.get("variant")
        if isinstance(variant_name, str):
            if variant_name in seen_variants:
                out.append(Diagnostic(f"$.benchmark.variants[{index}].variant", "duplicate", f"duplicate variant: {variant_name}"))
            seen_variants.add(variant_name)
        input_kinds: set[str] = set()
        for input_index, input_ref in enumerate(_require_list(variant.get("inputs"), f"$.benchmark.variants[{index}].inputs", out)):
            if not isinstance(input_ref, dict):
                continue
            kind = input_ref.get("kind")
            if isinstance(kind, str):
                if kind in input_kinds:
                    out.append(
                        Diagnostic(
                            f"$.benchmark.variants[{index}].inputs[{input_index}].kind",
                            "duplicate",
                            f"duplicate input kind: {kind}",
                        )
                    )
                input_kinds.add(kind)
                artifact = input_ref.get("artifact") if isinstance(input_ref.get("artifact"), dict) else {}
                if artifact.get("source") != expected_sources.get(kind):
                    out.append(
                        Diagnostic(
                            f"$.benchmark.variants[{index}].inputs[{input_index}].artifact.source",
                            "reference",
                            f"input kind {kind!r} must reference {expected_sources.get(kind)!r}",
                        )
                    )
        if isinstance(variant_name, str) and variant_name in expected_inputs and input_kinds != expected_inputs[variant_name]:
            out.append(
                Diagnostic(
                    f"$.benchmark.variants[{index}].inputs",
                    "variants.inputs",
                    f"expected exactly {sorted(expected_inputs[variant_name])}, got {sorted(input_kinds)}",
                )
            )
    if seen_variants != EXPECTED_VARIANTS:
        out.append(
            Diagnostic(
                "$.benchmark.variants",
                "variants",
                f"expected exactly {sorted(EXPECTED_VARIANTS)}, got {sorted(seen_variants)}",
            )
        )

    readiness = root.get("readiness") if isinstance(root.get("readiness"), dict) else {}
    ready = readiness.get("ready")
    blocking = readiness.get("blocking_unknowns") if isinstance(readiness.get("blocking_unknowns"), list) else []
    readiness_status = root.get("readiness_status")
    if readiness_status == "ready" and (ready is not True or blocking):
        out.append(Diagnostic("$.readiness", "consistency", "ready case must set ready=true and have no blocking_unknowns"))
    if readiness_status == "blocked" and (ready is not False or not blocking):
        out.append(Diagnostic("$.readiness", "consistency", "blocked case must set ready=false and explain blocking_unknowns"))
    if readiness_status != "ready" or ready is not True or blocking:
        reasons = [item for item in blocking if isinstance(item, str) and item.strip()]
        blocking_unknowns.append(
            {
                "path": "readiness",
                "reason": "; ".join(reasons) if reasons else f"benchmark case is {readiness_status or 'not ready'}",
                "severity": "blocking",
                "source": "benchmark-case",
            }
        )
    return out, blocking_unknowns


def validate_benchmark_artifact(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-artifact")
    if not isinstance(data, dict):
        return out, []
    overlay = data.get("capture_overlay") if isinstance(data.get("capture_overlay"), dict) else {}
    environment = data.get("environment") if isinstance(data.get("environment"), dict) else {}
    mode = overlay.get("mode")
    if environment.get("capture_overlay_mode") != mode:
        out.append(Diagnostic("$.environment.capture_overlay_mode", "consistency", "must match capture_overlay.mode"))
    if mode == "git-patch":
        artifact = overlay.get("artifact") if isinstance(overlay.get("artifact"), dict) else {}
        if artifact.get("path") != "capture-overlay.patch":
            out.append(Diagnostic("$.capture_overlay.artifact.path", "ownership", "archived capture overlay path must be capture-overlay.patch"))
        if artifact.get("sha256") != environment.get("capture_overlay_hash"):
            out.append(Diagnostic("$.environment.capture_overlay_hash", "consistency", "must match capture overlay artifact hash"))
    elif mode == "none" and environment.get("capture_overlay_hash") is not None:
        out.append(Diagnostic("$.environment.capture_overlay_hash", "consistency", "none capture overlay requires a null hash"))
    return out, []


def validate_benchmark_validation_config(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-validation-config")
    if isinstance(data, dict):
        required_regions = data.get("required_regions")
        required_region_set = set(required_regions or [])
        if isinstance(required_regions, list) and len(required_regions) != len(set(required_regions)):
            out.append(Diagnostic("$.required_regions", "duplicate", "required_regions must be unique"))
        ignore_regions = data.get("ignore_regions")
        ignore_ids = [item.get("id") for item in ignore_regions if isinstance(item, dict)] if isinstance(ignore_regions, list) else []
        if len(ignore_ids) != len(set(ignore_ids)):
            out.append(Diagnostic("$.ignore_regions", "duplicate", "ignore region ids must be unique"))
        if isinstance(required_regions, list):
            overlap = sorted(set(required_regions) & set(ignore_ids))
            if overlap:
                out.append(Diagnostic("$.ignore_regions", "overlap", f"required and ignored regions overlap: {overlap}"))
        reference_ids: list[str] = []
        reference_regions_by_id: dict[str, dict[str, Any]] = {}
        reference_viewport = data.get("reference_viewport") if isinstance(data.get("reference_viewport"), dict) else {}
        for index, region in enumerate(data.get("reference_regions") if isinstance(data.get("reference_regions"), list) else []):
            region_id = region.get("id") if isinstance(region, dict) else None
            if isinstance(region_id, str):
                if region_id in reference_ids:
                    out.append(Diagnostic(f"$.reference_regions[{index}].id", "duplicate", f"duplicate reference region: {region_id}"))
                reference_ids.append(region_id)
                if isinstance(region, dict):
                    reference_regions_by_id[region_id] = region
            frame = region.get("frame") if isinstance(region, dict) and isinstance(region.get("frame"), dict) else {}
            if all(_is_number(frame.get(key)) for key in ("x", "y", "width", "height")) and all(_is_number(reference_viewport.get(key)) for key in ("width", "height")):
                if frame["x"] < 0 or frame["y"] < 0 or frame["width"] <= 0 or frame["height"] <= 0 or frame["x"] + frame["width"] > reference_viewport["width"] or frame["y"] + frame["height"] > reference_viewport["height"]:
                    out.append(Diagnostic(f"$.reference_regions[{index}].frame", "geometry", "reference region frame must have positive size and stay inside reference_viewport"))
        if reference_ids != list(required_regions or []):
            out.append(Diagnostic("$.reference_regions", "coverage", "reference_regions must exactly cover required_regions in order"))
        for index, region_id in enumerate(reference_ids):
            region = reference_regions_by_id[region_id]
            parent_id = region.get("parent_id")
            child_ids = region.get("child_ids") if isinstance(region.get("child_ids"), list) else []
            if parent_id is not None and parent_id not in required_region_set:
                out.append(Diagnostic(f"$.reference_regions[{index}].parent_id", "reference", "reference parent must be a required region or null"))
            for child_index, child_id in enumerate(child_ids):
                if child_id not in required_region_set:
                    out.append(Diagnostic(f"$.reference_regions[{index}].child_ids[{child_index}]", "reference", "reference child must be a required region"))
                elif reference_regions_by_id.get(child_id, {}).get("parent_id") != region_id:
                    out.append(Diagnostic(f"$.reference_regions[{index}].child_ids[{child_index}]", "consistency", "reference child parent_id does not point back to this region"))
            if parent_id in reference_regions_by_id and region_id not in reference_regions_by_id[parent_id].get("child_ids", []):
                out.append(Diagnostic(f"$.reference_regions[{index}].parent_id", "consistency", "reference parent child_ids does not contain this region"))
        for index, region in enumerate(ignore_regions if isinstance(ignore_regions, list) else []):
            frame = region.get("frame") if isinstance(region, dict) and isinstance(region.get("frame"), dict) else {}
            if all(_is_number(frame.get(key)) for key in ("x", "y", "width", "height")) and all(_is_number(reference_viewport.get(key)) for key in ("width", "height")):
                if frame["x"] < 0 or frame["y"] < 0 or frame["width"] <= 0 or frame["height"] <= 0 or frame["x"] + frame["width"] > reference_viewport["width"] or frame["y"] + frame["height"] > reference_viewport["height"]:
                    out.append(Diagnostic(f"$.ignore_regions[{index}].frame", "geometry", "ignore region frame must have positive size and stay inside reference_viewport"))
        seen_bindings: set[str] = set()
        seen_symbols: set[str] = set()
        for index, binding in enumerate(data.get("required_bindings") if isinstance(data.get("required_bindings"), list) else []):
            if not isinstance(binding, dict):
                continue
            for field, seen in (("id", seen_bindings), ("code_symbol", seen_symbols)):
                value = binding.get(field)
                if isinstance(value, str):
                    if value in seen:
                        out.append(Diagnostic(f"$.required_bindings[{index}].{field}", "duplicate", f"duplicate required binding {field}: {value}"))
                    seen.add(value)
            source = binding.get("source")
            if isinstance(source, str):
                source_path = Path(source)
                if source_path.is_absolute() or ".." in source_path.parts or source_path.suffix != ".swift":
                    out.append(Diagnostic(f"$.required_bindings[{index}].source", "path", "required binding source must be a normalized relative Swift path"))
            if binding.get("region_id") not in required_region_set:
                out.append(Diagnostic(f"$.required_bindings[{index}].region_id", "reference", "required binding must target a required region"))
        anchor_regions: set[str] = set()
        for index, region in enumerate(data.get("required_anchors") if isinstance(data.get("required_anchors"), list) else []):
            if not isinstance(region, dict):
                continue
            region_id = region.get("region_id")
            if isinstance(region_id, str):
                if region_id in anchor_regions:
                    out.append(Diagnostic(f"$.required_anchors[{index}].region_id", "duplicate", f"duplicate anchor region: {region_id}"))
                anchor_regions.add(region_id)
            anchor_ids: set[str] = set()
            for anchor_index, anchor in enumerate(region.get("anchors") if isinstance(region.get("anchors"), list) else []):
                anchor_id = anchor.get("id") if isinstance(anchor, dict) else None
                if isinstance(anchor_id, str):
                    if anchor_id in anchor_ids:
                        out.append(Diagnostic(f"$.required_anchors[{index}].anchors[{anchor_index}].id", "duplicate", f"duplicate anchor id: {anchor_id}"))
                    anchor_ids.add(anchor_id)
                if not isinstance(anchor, dict):
                    continue
                spacing_fields = {"relative_to_region_id", "region_edge", "relative_edge", "reference_value"}
                present = spacing_fields & set(anchor)
                if anchor.get("metric") == "spacing":
                    missing = spacing_fields - set(anchor)
                    if missing:
                        out.append(Diagnostic(f"$.required_anchors[{index}].anchors[{anchor_index}]", "anchor", f"spacing anchor is missing fields: {sorted(missing)}"))
                    relative_id = anchor.get("relative_to_region_id")
                    if isinstance(relative_id, str) and relative_id not in required_region_set:
                        out.append(Diagnostic(f"$.required_anchors[{index}].anchors[{anchor_index}].relative_to_region_id", "anchor", "spacing anchor must reference a required region"))
                    if isinstance(relative_id, str) and relative_id == region_id:
                        out.append(Diagnostic(f"$.required_anchors[{index}].anchors[{anchor_index}].relative_to_region_id", "anchor", "spacing anchor must reference a different required region"))
                elif present:
                    out.append(Diagnostic(f"$.required_anchors[{index}].anchors[{anchor_index}]", "anchor", "position/size anchors must derive only from the region reference frame"))
        ordered_anchor_regions = [item.get("region_id") for item in data.get("required_anchors", []) if isinstance(item, dict)]
        if ordered_anchor_regions != list(required_regions or []):
            out.append(Diagnostic("$.required_anchors", "coverage", "required_anchors must exactly cover required_regions in order"))
    return out, []


def validate_benchmark_validator_probe(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-validator-probe")
    if not isinstance(data, dict):
        return out, []
    screenshot = data.get("actual_screenshot") if isinstance(data.get("actual_screenshot"), dict) else {}
    screenshot_path = screenshot.get("path")
    if screenshot_path != "actual.png":
        out.append(Diagnostic("$.actual_screenshot.path", "artifact.path", "validator probe screenshot must be the direct run artifact actual.png"))
    viewport = (data.get("environment") or {}).get("viewport") if isinstance(data.get("environment"), dict) else {}
    width = viewport.get("width") if isinstance(viewport, dict) else None
    height = viewport.get("height") if isinstance(viewport, dict) else None
    seen: set[str] = set()
    regions_by_id: dict[str, dict[str, Any]] = {}
    for index, region in enumerate(data.get("regions") if isinstance(data.get("regions"), list) else []):
        if not isinstance(region, dict):
            continue
        region_id = region.get("id")
        if isinstance(region_id, str):
            if region_id in seen:
                out.append(Diagnostic(f"$.regions[{index}].id", "duplicate", f"duplicate probe region: {region_id}"))
            seen.add(region_id)
            regions_by_id[region_id] = region
        frame = region.get("frame") if isinstance(region.get("frame"), dict) else {}
        if all(_is_number(frame.get(key)) for key in ("x", "y", "width", "height")) and _is_number(width) and _is_number(height):
            if frame["x"] < 0 or frame["y"] < 0 or frame["x"] + frame["width"] > width or frame["y"] + frame["height"] > height:
                out.append(Diagnostic(f"$.regions[{index}].frame", "geometry", "probe region frame must stay inside the frozen viewport"))
    for index, region_id in enumerate(item.get("id") for item in data.get("regions", []) if isinstance(item, dict) and isinstance(item.get("id"), str)):
        region = regions_by_id[region_id]
        parent_id = region.get("parent_id")
        if parent_id is not None and parent_id not in seen:
            out.append(Diagnostic(f"$.regions[{index}].parent_id", "reference", "probe parent must reference an observed region or null"))
        for child_index, child_id in enumerate(region.get("child_ids") if isinstance(region.get("child_ids"), list) else []):
            if child_id not in seen:
                out.append(Diagnostic(f"$.regions[{index}].child_ids[{child_index}]", "reference", "probe child must reference an observed region"))
    seen_bindings: set[str] = set()
    for index, binding in enumerate(data.get("bindings") if isinstance(data.get("bindings"), list) else []):
        if not isinstance(binding, dict):
            continue
        binding_id = binding.get("id")
        if isinstance(binding_id, str):
            if binding_id in seen_bindings:
                out.append(Diagnostic(f"$.bindings[{index}].id", "duplicate", f"duplicate runtime binding: {binding_id}"))
            seen_bindings.add(binding_id)
        if binding.get("region_id") not in seen:
            out.append(Diagnostic(f"$.bindings[{index}].region_id", "reference", "runtime binding must reference an observed probe region"))
    return out, []


def validate_benchmark_run_plan(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-run-plan")
    if not isinstance(data, dict):
        return out, []
    executor = data.get("executor") if isinstance(data.get("executor"), dict) else {}
    validator = data.get("validator") if isinstance(data.get("validator"), dict) else {}
    if data.get("evidence_status") == "measured" and executor.get("synthetic") is not False:
        out.append(Diagnostic("$.executor.synthetic", "evidence", "measured plan must use a non-synthetic executor"))
    if data.get("evidence_status") == "measured" and validator.get("synthetic") is not False:
        out.append(Diagnostic("$.validator.synthetic", "evidence", "measured plan must use a non-synthetic validator"))
    provider_cli = executor.get("provider_cli") if isinstance(executor.get("provider_cli"), dict) else {}
    if data.get("evidence_status") == "measured" and provider_cli.get("name") != "openai-codex-cli":
        out.append(Diagnostic("$.executor.provider_cli.name", "provider", "measured Codex plan must freeze openai-codex-cli identity"))
    if data.get("evidence_status") == "measured" and not re.fullmatch(
        r"codex-cli [0-9]+(?:\.[0-9]+){2}(?:[-+][A-Za-z0-9.-]+)?",
        provider_cli.get("version") if isinstance(provider_cli.get("version"), str) else "",
    ):
        out.append(Diagnostic("$.executor.provider_cli.version", "provider", "measured Codex plan must freeze an exact codex-cli semantic version"))
    if data.get("evidence_status") == "measured":
        for key in ("launcher_path", "native_path"):
            value = provider_cli.get(key)
            if (
                not isinstance(value, str)
                or not Path(value).is_absolute()
                or str(Path(value).resolve()) != value
            ):
                out.append(
                    Diagnostic(
                        f"$.executor.provider_cli.{key}",
                        "provider",
                        "measured Codex plan must freeze a canonical absolute provider executable path",
                    )
                )
    if data.get("evidence_status") == "measured" and executor.get("environment") != {}:
        out.append(Diagnostic("$.executor.environment", "isolation", "measured executor environment must be empty"))
    if data.get("evidence_status") == "measured" and validator.get("environment") != {}:
        out.append(Diagnostic("$.validator.environment", "isolation", "measured capture and validator environment must be empty"))
    executor_adapter = executor.get("adapter") if isinstance(executor.get("adapter"), dict) else {}
    capture_adapter = validator.get("capture_adapter") if isinstance(validator.get("capture_adapter"), dict) else {}
    capture_overlay = validator.get("capture_overlay") if isinstance(validator.get("capture_overlay"), dict) else {}
    validator_adapter = validator.get("adapter") if isinstance(validator.get("adapter"), dict) else {}
    if capture_overlay.get("mode") == "git-patch":
        overlay_artifact = capture_overlay.get("artifact") if isinstance(capture_overlay.get("artifact"), dict) else {}
        overlay_path = overlay_artifact.get("path")
        if not isinstance(overlay_path, str) or Path(overlay_path).suffix != ".patch":
            out.append(Diagnostic("$.validator.capture_overlay.artifact.path", "path", "capture overlay must be a .patch artifact"))
    if data.get("evidence_status") == "measured":
        adapter_hashes = [
            executor_adapter.get("sha256"),
            capture_adapter.get("sha256"),
            validator_adapter.get("sha256"),
        ]
        if len({value for value in adapter_hashes if isinstance(value, str)}) != 3:
            out.append(
                Diagnostic(
                    "$.validator.capture_adapter.sha256",
                    "separation",
                    "measured implementation, capture and validation adapters must be three distinct hash-frozen programs",
                )
            )
    implementation_command = executor.get("implementation_command") if isinstance(executor.get("implementation_command"), list) else []
    if not implementation_command or implementation_command[0] != "{adapter}":
        out.append(Diagnostic("$.executor.implementation_command", "adapter", "command must start with the hash-frozen {adapter}; the runner supplies the Python runtime"))
    capture_command = validator.get("capture_command") if isinstance(validator.get("capture_command"), list) else []
    if not capture_command or capture_command[0] != "{capture}":
        out.append(Diagnostic("$.validator.capture_command", "adapter", "capture command must start with the hash-frozen {capture}; the runner supplies the Python runtime"))
    validation_command = validator.get("command") if isinstance(validator.get("command"), list) else []
    if not validation_command or validation_command[0] != "{validator}":
        out.append(Diagnostic("$.validator.command", "adapter", "command must start with the hash-frozen {validator}; the runner supplies the Python runtime"))
    isolation = data.get("isolation") if isinstance(data.get("isolation"), dict) else {}
    if data.get("evidence_status") == "measured" and isolation.get("strategy") != "git-pinned-tree-slice":
        out.append(Diagnostic("$.isolation.strategy", "isolation", "measured plan must use git-pinned-tree-slice"))
    order = isolation.get("run_order") if isinstance(isolation.get("run_order"), list) else []
    if len(order) != len(EXPECTED_VARIANTS) or set(order) != EXPECTED_VARIANTS:
        out.append(Diagnostic("$.isolation.run_order", "variants", f"expected exactly {sorted(EXPECTED_VARIANTS)}"))
    return out, []


def validate_benchmark_input_context(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-input-context")
    if not isinstance(data, dict):
        return out, []
    expected = {
        "screenshot-only": {"reference", "shared-prompt", "validation-config"},
        "ui-ir": {"reference", "shared-prompt", "validation-config", "ui-ir"},
        "ui-ir-with-binding": {"reference", "shared-prompt", "validation-config", "agent-packet"},
    }
    expected_audience = {
        "reference": "agent",
        "shared-prompt": "agent",
        "validation-config": "validator",
        "ui-ir": "agent",
        "agent-packet": "agent",
    }
    capture_overlay = data.get("capture_overlay") if isinstance(data.get("capture_overlay"), dict) else {}
    if capture_overlay.get("mode") == "git-patch":
        artifact = capture_overlay.get("artifact") if isinstance(capture_overlay.get("artifact"), dict) else {}
        if artifact.get("path") != "capture-overlay.patch":
            out.append(Diagnostic("$.capture_overlay.artifact.path", "ownership", "archived capture overlay path must be capture-overlay.patch"))
    provider_scope = data.get("provider_source_scope") if isinstance(data.get("provider_source_scope"), dict) else {}
    if provider_scope.get("mode") == "allowlist":
        worktree = provider_scope.get("worktree") if isinstance(provider_scope.get("worktree"), dict) else {}
        if worktree.get("path") != "provider-worktree":
            out.append(Diagnostic("$.provider_source_scope.worktree.path", "ownership", "provider worktree path must be provider-worktree"))
    kinds: set[str] = set()
    paths: set[str] = set()
    for index, item in enumerate(data.get("inputs") if isinstance(data.get("inputs"), list) else []):
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        audience = item.get("audience")
        path = item.get("path")
        if isinstance(kind, str):
            if kind in kinds:
                out.append(Diagnostic(f"$.inputs[{index}].kind", "duplicate", f"duplicate input kind: {kind}"))
            kinds.add(kind)
            if audience != expected_audience.get(kind):
                out.append(
                    Diagnostic(
                        f"$.inputs[{index}].audience",
                        "audience",
                        f"{kind} must be {expected_audience.get(kind)}-visible",
                    )
                )
        if isinstance(path, str):
            if path in paths:
                out.append(Diagnostic(f"$.inputs[{index}].path", "duplicate", f"duplicate input path: {path}"))
            paths.add(path)
    variant = data.get("variant")
    if isinstance(variant, str) and variant in expected and kinds != expected[variant]:
        out.append(
            Diagnostic(
                "$.inputs",
                "variants.inputs",
                f"expected exactly {sorted(expected[variant])}, got {sorted(kinds)}",
            )
        )
    return out, []


def validate_provider_source_manifest(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "provider-source-manifest")
    if not isinstance(data, dict) or out:
        return out, []
    scope_entries = data["scope_entries"]
    files = data["files"]
    normalized_entries: list[tuple[str, str]] = []
    for index, entry in enumerate(scope_entries):
        raw = entry["path"]
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts or raw != path.as_posix() or raw.endswith("/"):
            out.append(Diagnostic(f"$.scope_entries[{index}].path", "artifact.path", "scope entry path must be normalized and relative"))
        normalized_entries.append((entry["kind"], raw))

    paths = [item["path"] for item in files]
    if paths != sorted(paths):
        out.append(Diagnostic("$.files", "artifact.manifest", "provider source files must be sorted by path"))
    if len(paths) != len(set(paths)):
        out.append(Diagnostic("$.files", "artifact.manifest", "provider source file paths must be unique"))

    matched = [0] * len(normalized_entries)
    for index, item in enumerate(files):
        raw = item["path"]
        path = Path(raw)
        if path.is_absolute() or ".." in path.parts or raw != path.as_posix() or raw.endswith("/"):
            out.append(Diagnostic(f"$.files[{index}].path", "artifact.path", "provider source file path must be normalized and relative"))
        matches: list[int] = []
        for entry_index, (kind, value) in enumerate(normalized_entries):
            if (kind == "file" and raw == value) or (kind == "directory" and raw.startswith(value + "/")):
                matches.append(entry_index)
                matched[entry_index] += 1
        if len(matches) != 1:
            out.append(
                Diagnostic(
                    f"$.files[{index}].path",
                    "artifact.manifest",
                    "provider source file must match exactly one scope entry",
                )
            )
    for index, count in enumerate(matched):
        if count == 0:
            out.append(Diagnostic(f"$.scope_entries[{index}]", "artifact.manifest", "provider source scope entry matched no files"))

    canonical = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = {
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "content_sha256": hashlib.sha256(canonical).hexdigest(),
    }
    for key, value in expected.items():
        if data.get(key) != value:
            out.append(Diagnostic(f"$.{key}", "artifact.manifest", f"provider source canonical {key} is invalid"))
    return out, []


def validate_benchmark_run_result(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-run-result")
    if not isinstance(data, dict):
        return out, []
    region_ids: set[str] = set()
    region_deviations: list[float] = []
    failed_regions: list[str] = []
    for index, region in enumerate(data.get("regions") if isinstance(data.get("regions"), list) else []):
        if not isinstance(region, dict):
            continue
        region_id = region.get("id")
        if isinstance(region_id, str):
            if region_id in region_ids:
                out.append(Diagnostic(f"$.regions[{index}].id", "duplicate", f"duplicate region: {region_id}"))
            region_ids.add(region_id)
        deviation = region.get("layout_deviation_pt")
        if _is_number(deviation):
            region_deviations.append(float(deviation))
        if any(region.get(check) != "passed" for check in ("structure", "semantic", "visual")):
            failed_regions.append(str(region_id or index))
    metric_deviation = (data.get("metrics") or {}).get("layout_deviation_pt") if isinstance(data.get("metrics"), dict) else None
    if region_deviations and _is_number(metric_deviation) and not math.isclose(float(metric_deviation), max(region_deviations), abs_tol=1e-9):
        out.append(Diagnostic("$.metrics.layout_deviation_pt", "consistency", "must equal the maximum region deviation"))
    if failed_regions and data.get("status") == "passed":
        out.append(Diagnostic("$.status", "consistency", f"passed result contains failed regions: {failed_regions}"))
    # A failed candidate is valid measured evidence and must reach the aggregate
    # scorer; `failed` describes quality, not evidence-chain trustworthiness.
    return out, []


def validate_benchmark_semantic_evidence(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-semantic-evidence")
    if not isinstance(data, dict):
        return out, []
    for field in ("regions", "required_bindings"):
        seen: set[str] = set()
        for index, item in enumerate(data.get(field) if isinstance(data.get(field), list) else []):
            item_id = item.get("id") if isinstance(item, dict) else None
            if isinstance(item_id, str):
                if item_id in seen:
                    out.append(Diagnostic(f"$.{field}[{index}].id", "duplicate", f"duplicate {field} id: {item_id}"))
                seen.add(item_id)
            if field == "required_bindings" and isinstance(item, dict) and item.get("reused") is True and not item.get("locations"):
                out.append(Diagnostic(f"$.{field}[{index}].locations", "evidence", "reused binding requires at least one source location"))
            if field == "required_bindings" and isinstance(item, dict) and item.get("reused") is True:
                source = item.get("source")
                if not any(isinstance(location, dict) and location.get("path") == source for location in item.get("locations", [])):
                    out.append(Diagnostic(f"$.{field}[{index}].locations", "evidence", "reused binding requires a source location in the frozen owner file"))
            if field == "required_bindings" and isinstance(item, dict):
                if item.get("reused") is not item.get("runtime_observed"):
                    out.append(Diagnostic(f"$.{field}[{index}].reused", "consistency", "reused must equal runtime_observed; declaration presence alone is insufficient"))
    return out, []


def validate_benchmark_visual_diff(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-visual-diff")
    if not isinstance(data, dict):
        return out, []
    seen: set[str] = set()
    for index, region in enumerate(data.get("regions") if isinstance(data.get("regions"), list) else []):
        if not isinstance(region, dict):
            continue
        region_id = region.get("id")
        if isinstance(region_id, str):
            if region_id in seen:
                out.append(Diagnostic(f"$.regions[{index}].id", "duplicate", f"duplicate visual region: {region_id}"))
            seen.add(region_id)
        deviations = [item.get("deviation_pt") for item in region.get("anchors", []) if isinstance(item, dict) and _is_number(item.get("deviation_pt"))]
        for anchor_index, anchor in enumerate(region.get("anchors") if isinstance(region.get("anchors"), list) else []):
            if not isinstance(anchor, dict):
                continue
            metric = anchor.get("metric")
            reference = anchor.get("reference_value")
            actual = anchor.get("actual_value")
            expected_length = 1 if metric == "spacing" else 2
            if isinstance(reference, list) and isinstance(actual, list):
                if len(reference) != expected_length or len(actual) != expected_length:
                    out.append(Diagnostic(f"$.regions[{index}].anchors[{anchor_index}]", "anchor", f"{metric} anchor requires {expected_length} values"))
                elif all(_is_number(value) for value in reference + actual):
                    derived = max(abs(float(left) - float(right)) for left, right in zip(reference, actual))
                    if _is_number(anchor.get("deviation_pt")) and not math.isclose(float(anchor["deviation_pt"]), derived, abs_tol=1e-9):
                        out.append(Diagnostic(f"$.regions[{index}].anchors[{anchor_index}].deviation_pt", "consistency", "must equal the maximum absolute reference/actual delta"))
        if deviations and _is_number(region.get("layout_deviation_pt")) and not math.isclose(float(region["layout_deviation_pt"]), max(float(value) for value in deviations), abs_tol=1e-9):
            out.append(Diagnostic(f"$.regions[{index}].layout_deviation_pt", "consistency", "must equal maximum anchor deviation"))
    return out, []


def validate_benchmark_run_observation(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "benchmark-run-observation")
    if not isinstance(data, dict):
        return out, []
    provider_ids: set[str] = set()
    for index, item in enumerate(data.get("provider_runs") if isinstance(data.get("provider_runs"), list) else []):
        run_id = item.get("id") if isinstance(item, dict) else None
        if isinstance(run_id, str):
            if run_id in provider_ids:
                out.append(Diagnostic(f"$.provider_runs[{index}].id", "duplicate", f"duplicate provider run id: {run_id}"))
            provider_ids.add(run_id)
        if isinstance(item, dict):
            cached = item.get("cached_input_tokens")
            total = item.get("input_tokens")
            if _is_number(cached) and _is_number(total) and cached > total:
                out.append(
                    Diagnostic(
                        f"$.provider_runs[{index}].cached_input_tokens",
                        "usage",
                        "cached_input_tokens cannot exceed input_tokens",
                    )
                )
    for index, item in enumerate(data.get("repair_events") if isinstance(data.get("repair_events"), list) else []):
        provider_id = item.get("provider_run_id") if isinstance(item, dict) else None
        if isinstance(provider_id, str) and provider_id not in provider_ids:
            out.append(Diagnostic(f"$.repair_events[{index}].provider_run_id", "reference", "repair event must reference provider_runs"))
    return out, []


def validate_implementation_validation(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "implementation-validation")
    blocking: list[dict[str, Any]] = []
    if isinstance(data, dict) and data.get("status") != "passed":
        blocking.append(
            {
                "path": "status",
                "reason": "Semantic visual validation did not pass.",
                "severity": "blocking",
                "source": "validator",
            }
        )
    if isinstance(data, dict):
        checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
        failed = sorted(name for name in ("structure", "semantic", "visual") if checks.get(name) != "passed")
        if failed:
            blocking.append(
                {
                    "path": "checks",
                    "reason": f"Validation checks did not pass: {failed}.",
                    "severity": "blocking",
                    "source": "validator",
                }
            )
    return out, blocking


def validate_component_registry(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "component-registry")
    root = _require_keys(data, REGISTRY_REQUIRED, "$", out)
    if root.get("registry_version") != "1.0.0":
        out.append(Diagnostic("$.registry_version", "version", "expected 1.0.0"))

    entry_ids: set[str] = set()
    design_ids: set[str] = set()
    binding_ids: set[str] = set()
    for index, entry in enumerate(_require_list(root.get("entries"), "$.entries", out)):
        path = f"$.entries[{index}]"
        entry_obj = _require_keys(
            entry,
            {"id", "design_id", "semantic_role", "reuse_policy", "status", "bindings", "provenance"},
            path,
            out,
        )
        entry_id = entry_obj.get("id")
        design_id = entry_obj.get("design_id")
        if isinstance(entry_id, str):
            if entry_id in entry_ids:
                out.append(Diagnostic(f"{path}.id", "duplicate", f"duplicate registry entry id: {entry_id}"))
            entry_ids.add(entry_id)
        if isinstance(design_id, str):
            if design_id in design_ids:
                out.append(Diagnostic(f"{path}.design_id", "duplicate", f"duplicate design id: {design_id}"))
            design_ids.add(design_id)
        bindings = _require_list(entry_obj.get("bindings"), f"{path}.bindings", out)
        if entry_obj.get("status") == "active" and entry_obj.get("reuse_policy") == "required" and not bindings:
            out.append(Diagnostic(f"{path}.bindings", "binding", "active required component must have a binding"))
        for binding_index, binding in enumerate(bindings):
            if not isinstance(binding, dict):
                continue
            binding_id = binding.get("id")
            if isinstance(binding_id, str):
                if binding_id in binding_ids:
                    out.append(
                        Diagnostic(
                            f"{path}.bindings[{binding_index}].id",
                            "duplicate",
                            f"duplicate registry binding id: {binding_id}",
                        )
                    )
                binding_ids.add(binding_id)
    return out, []


def validate_implementation_manifest(data: Any) -> tuple[list[Diagnostic], list[dict[str, Any]]]:
    out = validate_against_schema(data, "implementation-manifest")
    root = _require_keys(data, MANIFEST_REQUIRED, "$", out)
    if root.get("manifest_version") != "1.0.0":
        out.append(Diagnostic("$.manifest_version", "version", "expected 1.0.0"))

    node_ids: set[str] = set()
    for index, mapping in enumerate(_require_list(root.get("mappings"), "$.mappings", out)):
        if not isinstance(mapping, dict):
            continue
        path = f"$.mappings[{index}]"
        node_id = mapping.get("design_node_id")
        if isinstance(node_id, str):
            if node_id in node_ids:
                out.append(Diagnostic(f"{path}.design_node_id", "duplicate", f"duplicate design node: {node_id}"))
            node_ids.add(node_id)
    blocking: list[dict[str, Any]] = []
    if root.get("status") != "complete":
        blocking.append(
            {
                "path": "status",
                "reason": "Implementation Manifest is still a draft.",
                "severity": "blocking",
                "source": "validator",
            }
        )
    else:
        for index, mapping in enumerate(_require_list(root.get("mappings"), "$.mappings", out)):
            if not isinstance(mapping, dict):
                continue
            for field in ("preview_scene", "validation_region"):
                if not isinstance(mapping.get(field), str) or not mapping[field].strip():
                    out.append(
                        Diagnostic(
                            f"$.mappings[{index}].{field}",
                            "completion",
                            f"complete manifest requires non-empty {field}",
                        )
                    )
        validation = root.get("validation") if isinstance(root.get("validation"), dict) else {}
        if validation.get("status") != "passed":
            out.append(Diagnostic("$.validation.status", "completion", "complete manifest requires passed validation"))
        if not validation.get("evidence"):
            out.append(Diagnostic("$.validation.evidence", "completion", "complete manifest requires validation evidence"))
    return out, blocking


def validate_packet_ui_ir_linkage(
    ui_ir: dict[str, Any],
    packet: dict[str, Any],
    path_prefix: str = "$.agent_packet",
) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    if packet.get("task", {}).get("screen") != ui_ir.get("screen", {}).get("id"):
        out.append(Diagnostic(path_prefix, "artifact.linkage", "Agent Packet screen does not match UI IR"))
    if packet.get("reference", {}).get("source_hash") != ui_ir.get("source", {}).get("evidence_hash"):
        out.append(Diagnostic(path_prefix, "artifact.linkage", "Agent Packet source hash does not match UI IR evidence hash"))
    if packet.get("environment") != ui_ir.get("environment"):
        out.append(Diagnostic(path_prefix, "artifact.linkage", "Agent Packet environment does not match UI IR"))
    for field in ("viewport", "scale", "appearance", "locale", "image"):
        if packet.get("reference", {}).get(field) != ui_ir.get("reference", {}).get(field):
            out.append(Diagnostic(path_prefix, "artifact.linkage", f"Agent Packet reference {field} does not match UI IR"))

    ui_nodes: dict[str, tuple[dict[str, Any], str | None]] = {}

    def collect_ui_node(node: dict[str, Any], parent: str | None = None) -> None:
        ui_nodes[node["id"]] = (node, parent)
        for child in node.get("children", []):
            collect_ui_node(child, node["id"])

    collect_ui_node(ui_ir["tree"])

    def subtree_ids(node: dict[str, Any]) -> set[str]:
        result = {node["id"]}
        for child in node.get("children", []):
            result.update(subtree_ids(child))
        return result

    def relative_refs(value: Any) -> set[str]:
        result: set[str] = set()
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "children":
                    continue
                if key == "relative_to" and isinstance(child, str):
                    result.add(child)
                else:
                    result.update(relative_refs(child))
        elif isinstance(value, list):
            for child in value:
                result.update(relative_refs(child))
        return result

    target_id = packet.get("task", {}).get("target_id")
    target_kind = packet.get("task", {}).get("target_kind")
    if target_kind == "state":
        expected_node_ids = set(ui_nodes)
    elif target_id in ui_nodes:
        expected_node_ids = subtree_ids(ui_nodes[target_id][0])

        def add_ancestors(node_id: str) -> None:
            current = node_id
            while ui_nodes[current][1] is not None:
                parent = ui_nodes[current][1]
                assert parent is not None
                expected_node_ids.add(parent)
                current = parent

        for node_id in list(expected_node_ids):
            add_ancestors(node_id)
        changed = True
        while changed:
            changed = False
            dependencies = relative_refs(ui_ir.get("responsive", []))
            for node_id in expected_node_ids:
                dependencies.update(relative_refs(ui_nodes[node_id][0]))
            for dependency in dependencies:
                if dependency not in ui_nodes:
                    continue
                before = len(expected_node_ids)
                expected_node_ids.add(dependency)
                add_ancestors(dependency)
                changed = changed or len(expected_node_ids) != before
    else:
        expected_node_ids = set()
    packet_node_ids = {
        node.get("id")
        for node in packet.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    if packet_node_ids != expected_node_ids:
        out.append(
            Diagnostic(
                f"{path_prefix}.nodes",
                "artifact.linkage",
                f"Packet node closure differs from UI IR; missing={sorted(expected_node_ids - packet_node_ids)}, "
                f"extra={sorted(packet_node_ids - expected_node_ids)}",
            )
        )
    expected_required_regions = [
        region
        for region in ui_ir.get("validation", {}).get("required_regions", [])
        if region in expected_node_ids
    ]
    if not expected_required_regions and target_kind != "state":
        expected_required_regions = [target_id]
    elif not expected_required_regions:
        expected_required_regions = [ui_ir["tree"]["id"]]
    if packet.get("acceptance", {}).get("required_regions") != expected_required_regions:
        out.append(
            Diagnostic(
                f"{path_prefix}.acceptance.required_regions",
                "artifact.linkage",
                "Packet acceptance regions do not match UI IR target closure",
            )
        )
    packet_state_ids = {
        state.get("id")
        for state in packet.get("states", [])
        if isinstance(state, dict) and isinstance(state.get("id"), str)
    }
    packet_binding_map = {
        binding.get("id"): binding
        for binding in packet.get("bindings", [])
        if isinstance(binding, dict) and isinstance(binding.get("id"), str)
    }
    for index, packet_node in enumerate(packet.get("nodes", [])):
        if not isinstance(packet_node, dict):
            continue
        node_id = packet_node.get("id")
        expected_pair = ui_nodes.get(node_id)
        path = f"{path_prefix}.nodes[{index}]"
        if not expected_pair:
            out.append(Diagnostic(path, "artifact.linkage", f"Packet node is absent from UI IR: {node_id}"))
            continue
        expected, expected_parent = expected_pair
        expected_component = None
        if isinstance(expected.get("component"), dict):
            expected_component = {
                key: expected["component"][key]
                for key in ("design_id", "semantic_role", "reuse_policy")
            }
        for field, expected_value in (
            ("type", expected.get("type")),
            ("role", expected.get("role")),
            ("parent", expected_parent),
            ("layout", expected.get("layout")),
            ("style", expected.get("style")),
            ("node_state", expected.get("state")),
            ("component", expected_component),
        ):
            if packet_node.get(field) != expected_value:
                out.append(Diagnostic(f"{path}.{field}", "artifact.linkage", f"Packet node {field} does not match UI IR"))
        if set(packet_node.get("state_refs", [])) != packet_state_ids:
            out.append(Diagnostic(f"{path}.state_refs", "artifact.linkage", "Packet node state references are incomplete"))
        expected_inline_bindings = {
            (binding.get("framework"), binding.get("symbol"), binding.get("source"))
            for binding in expected.get("component", {}).get("bindings", [])
            if isinstance(binding, dict)
        }
        for binding_id in packet_node.get("binding_refs", []):
            binding = packet_binding_map.get(binding_id)
            if not binding:
                continue
            actual_binding = (binding.get("framework"), binding.get("symbol"), binding.get("source"))
            if actual_binding not in expected_inline_bindings:
                out.append(
                    Diagnostic(
                        f"{path}.binding_refs",
                        "artifact.linkage",
                        f"Packet binding {binding_id} does not match UI IR inline binding",
                    )
                )

    ui_tokens: dict[str, Any] = {}
    for namespace, values in ui_ir.get("tokens", {}).items():
        if isinstance(values, dict):
            for name, token in values.items():
                if isinstance(token, dict) and "value" in token:
                    ui_tokens[f"{namespace}.{name}"] = token["value"]

    def token_refs(value: Any) -> set[str]:
        result: set[str] = set()
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "children":
                    continue
                result.update(token_refs(child))
        elif isinstance(value, list):
            for child in value:
                result.update(token_refs(child))
        elif isinstance(value, str) and value in ui_tokens:
            result.add(value)
        return result

    expected_token_ids = token_refs(ui_ir.get("responsive", []))
    for index, packet_node in enumerate(packet.get("nodes", [])):
        if not isinstance(packet_node, dict) or packet_node.get("id") not in ui_nodes:
            continue
        expected_refs = token_refs(ui_nodes[packet_node["id"]][0])
        if set(packet_node.get("token_refs", [])) != expected_refs:
            out.append(
                Diagnostic(
                    f"{path_prefix}.nodes[{index}].token_refs",
                    "artifact.linkage",
                    "Packet node token references do not match UI IR",
                )
            )
        expected_token_ids.update(expected_refs)
    packet_token_map = {
        token.get("id"): token.get("value")
        for token in packet.get("tokens", [])
        if isinstance(token, dict) and isinstance(token.get("id"), str)
    }
    for index, token in enumerate(packet.get("tokens", [])):
        if isinstance(token, dict) and ui_tokens.get(token.get("id")) != token.get("value"):
            out.append(Diagnostic(f"{path_prefix}.tokens[{index}]", "artifact.linkage", "Packet token does not match UI IR"))

    ui_scenes = {
        scene["id"]: scene["data"]
        for scene in ui_ir.get("state", {}).get("scenes", [])
        if isinstance(scene, dict) and "id" in scene and "data" in scene
    }
    for index, state in enumerate(packet.get("states", [])):
        if isinstance(state, dict) and ui_scenes.get(state.get("id")) != state.get("data"):
            out.append(Diagnostic(f"{path_prefix}.states[{index}]", "artifact.linkage", "Packet state does not match UI IR"))
    requested_states = set(packet.get("task", {}).get("requested_states", []))
    expected_state_ids = set(requested_states)
    changed = True
    while changed:
        changed = False
        for transition in ui_ir.get("state", {}).get("transitions", []):
            if not isinstance(transition, dict):
                continue
            if transition.get("from") in expected_state_ids or transition.get("to") in expected_state_ids:
                before = len(expected_state_ids)
                expected_state_ids.update((transition.get("from"), transition.get("to")))
                changed = changed or len(expected_state_ids) != before
    if packet_state_ids != expected_state_ids:
        out.append(
            Diagnostic(
                f"{path_prefix}.states",
                "artifact.linkage",
                f"Packet state closure differs from requested seeds; missing={sorted(expected_state_ids - packet_state_ids)}, "
                f"extra={sorted(packet_state_ids - expected_state_ids)}",
            )
        )
    for transition in ui_ir.get("state", {}).get("transitions", []):
        if not isinstance(transition, dict):
            continue
        endpoints = {transition.get("from"), transition.get("to")}
        if endpoints & packet_state_ids and not endpoints.issubset(packet_state_ids):
            out.append(Diagnostic(f"{path_prefix}.states", "artifact.linkage", "Packet state set is not closed over UI IR transitions"))
    for state_id in packet_state_ids:
        if state_id in ui_scenes:
            expected_token_ids.update(token_refs(ui_scenes[state_id]))
    ui_transitions = {
        tuple(item.get(field) for field in ("event", "from", "to", "side_effect", "presentation", "animation"))
        for item in ui_ir.get("state", {}).get("transitions", [])
        if isinstance(item, dict)
    }
    packet_transition_tuples: set[tuple[Any, ...]] = set()
    for index, interaction in enumerate(packet.get("interactions", [])):
        if isinstance(interaction, dict) and tuple(
            interaction.get(field)
            for field in ("event", "from", "to", "side_effect", "presentation", "animation")
        ) not in ui_transitions:
            out.append(Diagnostic(f"{path_prefix}.interactions[{index}]", "artifact.linkage", "Packet interaction does not match UI IR"))
        if isinstance(interaction, dict):
            packet_transition_tuples.add(
                tuple(interaction.get(field) for field in ("event", "from", "to", "side_effect", "presentation", "animation"))
            )
            expected_token_ids.update(token_refs(interaction))
    expected_transition_tuples = {
        tuple(item.get(field) for field in ("event", "from", "to", "side_effect", "presentation", "animation"))
        for item in ui_ir.get("state", {}).get("transitions", [])
        if isinstance(item, dict) and item.get("from") in packet_state_ids and item.get("to") in packet_state_ids
    }
    if packet_transition_tuples != expected_transition_tuples:
        out.append(Diagnostic(f"{path_prefix}.interactions", "artifact.linkage", "Packet interaction closure does not match UI IR"))
    packet_interaction_ids = {
        interaction.get("id")
        for interaction in packet.get("interactions", [])
        if isinstance(interaction, dict) and isinstance(interaction.get("id"), str)
    }
    for index, packet_node in enumerate(packet.get("nodes", [])):
        if isinstance(packet_node, dict) and set(packet_node.get("interaction_refs", [])) != packet_interaction_ids:
            out.append(
                Diagnostic(
                    f"{path_prefix}.nodes[{index}].interaction_refs",
                    "artifact.linkage",
                    "Packet node interaction references are incomplete",
                )
            )
    if set(packet_token_map) != expected_token_ids:
        out.append(
            Diagnostic(
                f"{path_prefix}.tokens",
                "artifact.linkage",
                f"Packet token closure differs from UI IR; missing={sorted(expected_token_ids - set(packet_token_map))}, "
                f"extra={sorted(set(packet_token_map) - expected_token_ids)}",
            )
        )
    if packet.get("responsive") != ui_ir.get("responsive"):
        out.append(Diagnostic(path_prefix, "artifact.linkage", "Agent Packet responsive rules do not match UI IR"))
    if packet.get("accessibility") != ui_ir.get("accessibility"):
        out.append(Diagnostic(path_prefix, "artifact.linkage", "Agent Packet accessibility rules do not match UI IR"))

    ui_blocking_unknowns = {
        (item.get("path"), item.get("reason"), item.get("source"))
        for item in ui_ir.get("unknowns", [])
        if isinstance(item, dict) and item.get("severity") == "blocking"
    }
    packet_blocking_unknowns = {
        (item.get("path"), item.get("reason"), item.get("source"))
        for item in packet.get("unknowns", [])
        if isinstance(item, dict) and item.get("severity") == "blocking"
    }
    if not ui_blocking_unknowns.issubset(packet_blocking_unknowns):
        out.append(Diagnostic(path_prefix, "artifact.linkage", "Agent Packet dropped UI IR blocking unknowns"))
    return out


def _validate_manifest_artifacts(data: dict[str, Any], base_dir: Path) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    loaded: dict[str, dict[str, Any]] = {}
    for name, kind in (("ui_ir", "ui-ir"), ("agent_packet", "agent-packet")):
        artifact = source.get(name) if isinstance(source.get(name), dict) else {}
        raw_path = artifact.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            continue
        path = Path(raw_path)
        if not path.is_absolute():
            path = base_dir / path
        if not path.is_file():
            out.append(Diagnostic(f"$.source.{name}.path", "artifact.missing", f"source artifact not found: {path}"))
            continue
        actual_hash = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        if actual_hash != artifact.get("sha256"):
            out.append(Diagnostic(f"$.source.{name}.sha256", "artifact.hash", "source artifact SHA-256 mismatch"))
            continue
        try:
            contract = load_json(path)
            _, diagnostics, blocking = validate(contract, kind, base_dir=path.parent)
        except ValueError as exc:
            out.append(Diagnostic(f"$.source.{name}.path", "artifact.invalid", str(exc)))
            continue
        if diagnostics or blocking:
            out.append(
                Diagnostic(
                    f"$.source.{name}.path",
                    "artifact.contract",
                    f"referenced {kind} is not handoff-ready",
                )
            )
            continue
        loaded[name] = contract

    ui_ir = loaded.get("ui_ir")
    packet = loaded.get("agent_packet")
    if ui_ir and ui_ir.get("screen", {}).get("id") != data.get("screen"):
        out.append(Diagnostic("$.screen", "artifact.screen", "screen does not match referenced UI IR"))
    if packet and packet.get("task", {}).get("screen") != data.get("screen"):
        out.append(Diagnostic("$.screen", "artifact.screen", "screen does not match referenced Agent Packet"))
    if ui_ir and packet:
        out.extend(validate_packet_ui_ir_linkage(ui_ir, packet, "$.source.agent_packet"))
    if not packet:
        return out

    packet_nodes = {item["id"]: item for item in packet.get("nodes", []) if isinstance(item, dict) and "id" in item}
    packet_bindings = {
        item["id"]: item for item in packet.get("bindings", []) if isinstance(item, dict) and "id" in item
    }
    actual_pairs: set[tuple[str, str]] = set()
    for index, mapping in enumerate(data.get("mappings", [])):
        if not isinstance(mapping, dict):
            continue
        path = f"$.mappings[{index}]"
        node_id = mapping.get("design_node_id")
        binding_id = mapping.get("binding_id")
        node = packet_nodes.get(node_id)
        binding = packet_bindings.get(binding_id)
        if not node or binding_id not in node.get("binding_refs", []):
            out.append(Diagnostic(f"{path}.binding_id", "artifact.mapping", "mapping is not present in Agent Packet node closure"))
            continue
        actual_pairs.add((node_id, binding_id))
        if mapping.get("semantic_role") != node.get("role"):
            out.append(Diagnostic(f"{path}.semantic_role", "artifact.mapping", "semantic role does not match Agent Packet node"))
        if not binding:
            out.append(Diagnostic(f"{path}.binding_id", "artifact.mapping", "binding is absent from Agent Packet"))
            continue
        for manifest_field, packet_field in (
            ("framework", "framework"),
            ("code_symbol", "symbol"),
            ("source_file", "source"),
        ):
            if mapping.get(manifest_field) != binding.get(packet_field):
                out.append(
                    Diagnostic(
                        f"{path}.{manifest_field}",
                        "artifact.mapping",
                        f"value does not match Agent Packet binding {binding_id}",
                    )
                )
        if mapping.get("validation_region") not in packet.get("acceptance", {}).get("required_regions", []):
            out.append(
                Diagnostic(
                    f"{path}.validation_region",
                    "artifact.mapping",
                    "validation region is not an Agent Packet required region",
                )
            )

    expected_pairs = {
        (node["id"], binding_id)
        for node in packet.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
        for binding_id in node.get("binding_refs", [])
    }
    if actual_pairs != expected_pairs:
        missing = sorted(expected_pairs - actual_pairs)
        extra = sorted(actual_pairs - expected_pairs)
        out.append(
            Diagnostic(
                "$.mappings",
                "artifact.coverage",
                f"Manifest mappings must exactly cover Packet bindings; missing={missing}, extra={extra}",
            )
        )

    validated_regions: set[str] = set()
    for index, evidence in enumerate(data.get("validation", {}).get("evidence", [])):
        if not isinstance(evidence, dict):
            continue
        path_value = evidence.get("path")
        if not isinstance(path_value, str):
            continue
        evidence_path = Path(path_value)
        if not evidence_path.is_absolute():
            evidence_path = base_dir / evidence_path
        path = f"$.validation.evidence[{index}]"
        if not evidence_path.is_file():
            out.append(Diagnostic(f"{path}.path", "artifact.missing", f"validation evidence not found: {evidence_path}"))
            continue
        actual_hash = f"sha256:{hashlib.sha256(evidence_path.read_bytes()).hexdigest()}"
        if actual_hash != evidence.get("sha256"):
            out.append(Diagnostic(f"{path}.sha256", "artifact.hash", "validation evidence SHA-256 mismatch"))
            continue
        if evidence.get("kind") != "semantic-visual-validation":
            continue
        try:
            payload = load_json(evidence_path)
        except ValueError as exc:
            out.append(Diagnostic(f"{path}.path", "artifact.invalid", str(exc)))
            continue
        if not isinstance(payload, dict) or payload.get("kind") != "semantic-visual-validation":
            out.append(Diagnostic(f"{path}.path", "artifact.invalid", "invalid semantic visual validation payload"))
            continue
        _, evidence_diagnostics, evidence_blocking = validate(
            payload,
            "implementation-validation",
            base_dir=evidence_path.parent,
        )
        if evidence_diagnostics or evidence_blocking:
            out.append(Diagnostic(f"{path}.path", "artifact.contract", "semantic visual validation is not handoff-ready"))
            continue
        if payload.get("status") != "passed" or payload.get("screen") != data.get("screen"):
            out.append(Diagnostic(f"{path}.path", "artifact.result", "semantic visual validation did not pass for this screen"))
            continue
        expected_environment = {
            "platform": packet.get("environment", {}).get("platform"),
            "device": packet.get("environment", {}).get("device"),
            "viewport": packet.get("reference", {}).get("viewport"),
            "scale": packet.get("reference", {}).get("scale"),
            "appearance": packet.get("reference", {}).get("appearance"),
            "locale": packet.get("reference", {}).get("locale"),
        }
        if payload.get("source_hash") != packet.get("reference", {}).get("source_hash"):
            out.append(Diagnostic(f"{path}.path", "artifact.linkage", "validation evidence source hash does not match Packet"))
            continue
        if payload.get("environment") != expected_environment:
            out.append(Diagnostic(f"{path}.path", "artifact.linkage", "validation evidence environment does not match Packet"))
            continue
        region = payload.get("region")
        if isinstance(region, str):
            validated_regions.add(region)

    required_validation_regions = set(packet.get("acceptance", {}).get("required_regions", []))
    missing_validation = sorted(required_validation_regions - validated_regions)
    if missing_validation:
        out.append(
            Diagnostic(
                "$.validation.evidence",
                "artifact.coverage",
                f"missing passed semantic visual evidence for regions: {missing_validation}",
            )
        )
    return out


VALIDATORS = {
    "design-evidence": validate_design_evidence,
    "ui-ir": validate_ui_ir,
    "agent-packet": validate_agent_packet,
    "benchmark": validate_benchmark,
    "benchmark-case": validate_benchmark_case,
    "benchmark-validation-config": validate_benchmark_validation_config,
    "benchmark-validator-probe": validate_benchmark_validator_probe,
    "benchmark-run-plan": validate_benchmark_run_plan,
    "benchmark-input-context": validate_benchmark_input_context,
    "provider-source-manifest": validate_provider_source_manifest,
    "benchmark-run-result": validate_benchmark_run_result,
    "benchmark-semantic-evidence": validate_benchmark_semantic_evidence,
    "benchmark-visual-diff": validate_benchmark_visual_diff,
    "benchmark-run-observation": validate_benchmark_run_observation,
    "benchmark-artifact": validate_benchmark_artifact,
    "component-registry": validate_component_registry,
    "implementation-manifest": validate_implementation_manifest,
    "implementation-validation": validate_implementation_validation,
}


def detect_kind(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    if "evidence_version" in data:
        return "design-evidence"
    if "schema_version" in data:
        return "ui-ir"
    if "packet_version" in data:
        return "agent-packet"
    if "benchmark_version" in data:
        return "benchmark"
    if "case_version" in data:
        return "benchmark-case"
    if "config_version" in data:
        return "benchmark-validation-config"
    if "validator_probe_version" in data:
        return "benchmark-validator-probe"
    if "run_plan_version" in data:
        return "benchmark-run-plan"
    if "input_context_version" in data:
        return "benchmark-input-context"
    if "provider_source_manifest_version" in data:
        return "provider-source-manifest"
    if "run_result_version" in data:
        return "benchmark-run-result"
    if "semantic_evidence_version" in data:
        return "benchmark-semantic-evidence"
    if "visual_diff_version" in data:
        return "benchmark-visual-diff"
    if "run_observation_version" in data:
        return "benchmark-run-observation"
    if "artifact_version" in data:
        return "benchmark-artifact"
    if "registry_version" in data:
        return "component-registry"
    if "manifest_version" in data:
        return "implementation-manifest"
    if "validation_artifact_version" in data:
        return "implementation-validation"
    return None


def validate(
    data: Any,
    kind: str | None = None,
    base_dir: Path | None = None,
) -> tuple[str, list[Diagnostic], list[dict[str, Any]]]:
    resolved = kind or detect_kind(data)
    if resolved not in VALIDATORS:
        raise ValueError("unable to detect contract kind; pass --kind")
    diagnostics, blocking_unknowns = VALIDATORS[resolved](data)
    if resolved == "implementation-manifest" and isinstance(data, dict) and data.get("status") == "complete":
        if base_dir is None:
            blocking_unknowns.append(
                {
                    "path": "source",
                    "reason": "Complete Manifest source integrity has not been verified without a base directory.",
                    "severity": "blocking",
                    "source": "validator",
                }
            )
        else:
            diagnostics.extend(_validate_manifest_artifacts(data, base_dir))
    return resolved, _deduplicate(diagnostics), blocking_unknowns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="JSON contract to validate")
    parser.add_argument("--kind", choices=sorted(VALIDATORS), help="contract kind; auto-detected by default")
    parser.add_argument("--allow-blocking-unknowns", action="store_true", help="inspection only; normal handoff must block")
    args = parser.parse_args()

    try:
        data = load_json(args.path)
        kind, diagnostics, blocking_unknowns = validate(data, args.kind, base_dir=args.path.parent)
    except ValueError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    status = "invalid" if diagnostics else ("blocked" if blocking_unknowns else "valid")
    payload = {
        "status": status,
        "handoff_ready": not diagnostics and not blocking_unknowns,
        "kind": kind,
        "path": str(args.path),
        "diagnostics": [item.as_dict() for item in diagnostics],
        "blocking_unknowns": blocking_unknowns,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if diagnostics:
        return 1
    if blocking_unknowns and not args.allow_blocking_unknowns:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
