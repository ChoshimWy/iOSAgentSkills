#!/usr/bin/env python3
"""Compile a task-scoped Agent Packet from Canonical UI IR and Component Registry."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

from validate_contract import estimate_agent_packet_tokens, load_json, validate


def _flatten(node: dict[str, Any], parent: str | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    nodes: dict[str, dict[str, Any]] = {}
    parents: dict[str, str] = {}

    def visit(current: dict[str, Any], owner: str | None) -> None:
        node_id = current["id"]
        nodes[node_id] = current
        if owner is not None:
            parents[node_id] = owner
        for child in current.get("children", []):
            visit(child, node_id)

    visit(node, parent)
    return nodes, parents


def _relative_refs(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "children":
                continue
            if key == "relative_to" and isinstance(child, str):
                result.add(child)
            else:
                result.update(_relative_refs(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_relative_refs(child))
    return result


def _subtree_ids(node: dict[str, Any]) -> set[str]:
    result = {node["id"]}
    for child in node.get("children", []):
        result.update(_subtree_ids(child))
    return result


def _add_ancestors(node_id: str, selected: set[str], parents: dict[str, str]) -> None:
    current = node_id
    selected.add(current)
    while current in parents:
        current = parents[current]
        selected.add(current)


def _flatten_tokens(tokens: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for namespace, values in tokens.items():
        if not isinstance(values, dict):
            continue
        for name, token in values.items():
            if isinstance(token, dict) and "value" in token:
                result[f"{namespace}.{name}"] = token
    return result


def _token_refs(value: Any, known: set[str], key: str = "") -> set[str]:
    result: set[str] = set()
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key == "children":
                continue
            result.update(_token_refs(child, known, child_key))
    elif isinstance(value, list):
        for child in value:
            result.update(_token_refs(child, known, key))
    elif isinstance(value, str) and (value in known or key.endswith("_token")) and value in known:
        result.add(value)
    return result


def _select_binding(
    component: dict[str, Any],
    entry: dict[str, Any],
    environment_framework: str,
) -> tuple[dict[str, Any] | None, str | None, bool]:
    candidates = list(entry.get("bindings", []))
    if environment_framework in {"UIKit", "SwiftUI"}:
        candidates = [item for item in candidates if item.get("framework") == environment_framework]
    inline = component.get("bindings", [])
    if inline:
        candidates = [
            candidate
            for candidate in candidates
            if any(
                candidate.get("framework") == expected.get("framework")
                and candidate.get("symbol") == expected.get("symbol")
                and candidate.get("source") == expected.get("source")
                for expected in inline
                if isinstance(expected, dict)
            )
        ]
    if len(candidates) == 1:
        return candidates[0], None, False
    if not candidates:
        return None, "no Registry binding matches the UI IR binding and framework intent", False
    return None, "multiple Registry bindings match; the framework intent is ambiguous", True


def compile_packet(
    ui_ir: dict[str, Any],
    registry: dict[str, Any],
    target_id: str,
    target_kind: str,
    state_ids: list[str],
    max_tokens: int,
) -> dict[str, Any]:
    _, ui_diagnostics, _ = validate(ui_ir, "ui-ir")
    _, registry_diagnostics, _ = validate(registry, "component-registry")
    if ui_diagnostics or registry_diagnostics:
        details = [item.as_dict() for item in ui_diagnostics + registry_diagnostics]
        raise ValueError(f"input contract is invalid: {details}")
    nodes, parents = _flatten(ui_ir["tree"])
    scenes = {scene["id"]: scene for scene in ui_ir["state"]["scenes"]}
    if target_kind == "state":
        if target_id not in scenes:
            raise ValueError(f"unknown state target: {target_id}")
        selected = set(nodes)
        requested_states = [target_id]
    else:
        if target_id not in nodes:
            raise ValueError(f"unknown node target: {target_id}")
        if nodes[target_id].get("type") != target_kind:
            raise ValueError(f"target kind {target_kind!r} does not match node type {nodes[target_id].get('type')!r}")
        selected = _subtree_ids(nodes[target_id])
        for node_id in list(selected):
            _add_ancestors(node_id, selected, parents)
        requested_states = list(dict.fromkeys(state_ids or [next(iter(scenes))]))

    unknown_states = sorted(set(requested_states) - set(scenes))
    if unknown_states:
        raise ValueError(f"unknown state ids: {unknown_states}")

    state_closure = set(requested_states)
    changed = True
    while changed:
        changed = False
        for transition in ui_ir["state"]["transitions"]:
            if transition["from"] in state_closure or transition["to"] in state_closure:
                before = len(state_closure)
                state_closure.update((transition["from"], transition["to"]))
                changed = changed or len(state_closure) != before
    selected_states = [scene_id for scene_id in scenes if scene_id in state_closure]

    changed = True
    while changed:
        changed = False
        dependencies: set[str] = _relative_refs(ui_ir["responsive"])
        for node_id in selected:
            dependencies.update(_relative_refs(nodes[node_id]))
        for dependency in dependencies:
            if dependency not in nodes:
                raise ValueError(f"relative layout dependency is missing: {dependency}")
            before = len(selected)
            _add_ancestors(dependency, selected, parents)
            changed = changed or len(selected) != before

    token_map = _flatten_tokens(ui_ir["tokens"])
    registry_by_design = {entry["design_id"]: entry for entry in registry["entries"]}
    bindings: dict[str, dict[str, Any]] = {}
    binding_refs: dict[str, list[str]] = {node_id: [] for node_id in selected}
    unknowns = [deepcopy(item) for item in ui_ir.get("unknowns", [])]
    desired_framework = ui_ir["environment"]["ui_framework"]

    for node_id in sorted(selected):
        component = nodes[node_id].get("component")
        if not isinstance(component, dict):
            continue
        design_id = component["design_id"]
        entry = registry_by_design.get(design_id)
        severity = "blocking" if component["reuse_policy"] == "required" else "non-blocking"
        provenance = entry.get("provenance", {}) if entry else {}
        active_confirmed = bool(
            entry
            and entry.get("status") == "active"
            and provenance.get("source") == "manual-contract"
            and provenance.get("confidence") == "exact"
        )
        if not active_confirmed or not entry.get("bindings"):
            status = "missing" if entry is None else entry.get("status")
            unknowns.append(
                {
                    "path": f"tree.{node_id}.component",
                    "reason": f"Component Registry binding for {design_id!r} is {status}.",
                    "severity": severity,
                    "source": "component-registry",
                }
            )
            continue
        contract_conflict = False
        for field in ("semantic_role", "reuse_policy"):
            if entry.get(field) != component.get(field):
                contract_conflict = True
                unknowns.append(
                    {
                        "path": f"tree.{node_id}.component.{field}",
                        "reason": (
                            f"UI IR value {component.get(field)!r} conflicts with Component Registry value "
                            f"{entry.get(field)!r}."
                        ),
                        "severity": "blocking",
                        "source": "component-registry",
                    }
                )
        if contract_conflict:
            continue
        chosen, binding_error, ambiguous = _select_binding(component, entry, desired_framework)
        if chosen is None:
            unknowns.append(
                {
                    "path": f"tree.{node_id}.component.bindings",
                    "reason": f"Unable to resolve {design_id!r}: {binding_error}.",
                    "severity": "blocking" if ambiguous else severity,
                    "source": "component-registry",
                }
            )
            continue
        packet_binding = {
            "id": chosen["id"],
            "design_id": design_id,
            "reuse_policy": component["reuse_policy"],
            "framework": chosen["framework"],
            "symbol": chosen["symbol"],
            "source": chosen["source"],
        }
        bindings[chosen["id"]] = packet_binding
        binding_refs[node_id].append(chosen["id"])

    referenced_tokens: set[str] = _token_refs(ui_ir["responsive"], set(token_map))
    for state_id in selected_states:
        referenced_tokens.update(_token_refs(scenes[state_id]["data"], set(token_map)))
    packet_nodes: list[dict[str, Any]] = []
    for node_id, node in nodes.items():
        if node_id not in selected:
            continue
        refs = sorted(_token_refs(node, set(token_map)))
        referenced_tokens.update(refs)
        packet_node: dict[str, Any] = {
            "id": node_id,
            "type": node["type"],
            "role": node["role"],
            "layout": deepcopy(node["layout"]),
            "token_refs": refs,
            "binding_refs": binding_refs[node_id],
            "state_refs": list(selected_states),
            "interaction_refs": [],
        }
        if isinstance(node.get("style"), dict):
            packet_node["style"] = deepcopy(node["style"])
        if isinstance(node.get("state"), dict):
            packet_node["node_state"] = deepcopy(node["state"])
        if isinstance(node.get("component"), dict):
            component = node["component"]
            packet_node["component"] = {
                "design_id": component["design_id"],
                "semantic_role": component["semantic_role"],
                "reuse_policy": component["reuse_policy"],
            }
        if node_id in parents:
            packet_node["parent"] = parents[node_id]
        packet_nodes.append(packet_node)

    interactions = []
    for index, transition in enumerate(ui_ir["state"]["transitions"]):
        if transition["from"] in selected_states and transition["to"] in selected_states:
            interaction_id = f"transition.{index}"
            interactions.append(
                {
                    "id": interaction_id,
                    "event": transition["event"],
                    "from": transition["from"],
                    "to": transition["to"],
                    **{
                        field: transition[field]
                        for field in ("side_effect", "presentation", "animation")
                        if field in transition
                    },
                }
            )
            referenced_tokens.update(_token_refs(transition, set(token_map)))
            for packet_node in packet_nodes:
                packet_node["interaction_refs"].append(interaction_id)

    required_regions = [item for item in ui_ir["validation"]["required_regions"] if item in selected]
    if not required_regions and target_kind != "state":
        required_regions = [target_id]
    elif not required_regions:
        required_regions = [ui_ir["tree"]["id"]]

    packet = {
        "packet_version": "1.0.0",
        "task": {
            "screen": ui_ir["screen"]["id"],
            "target_kind": target_kind,
            "target_id": target_id,
            "requested_states": requested_states,
        },
        "reference": {
            "image": ui_ir["reference"]["image"],
            "source_hash": ui_ir["source"]["evidence_hash"],
            "viewport": deepcopy(ui_ir["reference"]["viewport"]),
            "scale": ui_ir["reference"]["scale"],
            "appearance": ui_ir["reference"]["appearance"],
            "locale": ui_ir["reference"]["locale"],
        },
        "environment": deepcopy(ui_ir["environment"]),
        "nodes": packet_nodes,
        "tokens": [{"id": item, "value": token_map[item]["value"]} for item in sorted(referenced_tokens)],
        "bindings": [bindings[item] for item in sorted(bindings)],
        "states": [{"id": item, "data": deepcopy(scenes[item]["data"])} for item in selected_states],
        "interactions": interactions,
        "responsive": deepcopy(ui_ir["responsive"]),
        "accessibility": deepcopy(ui_ir["accessibility"]),
        "code_anchors": [
            {"id": f"anchor.{binding_id}", "symbol": binding["symbol"], "source": binding["source"]}
            for binding_id, binding in sorted(bindings.items())
        ],
        "unknowns": unknowns,
        "acceptance": {
            "required_regions": required_regions,
            "max_geometry_deviation_pt": 1,
        },
        "context_budget": {"estimated_tokens": 0, "max_tokens": max_tokens, "within_budget": True},
    }
    estimate = estimate_agent_packet_tokens(packet)
    packet["context_budget"]["estimated_tokens"] = estimate
    packet["context_budget"]["within_budget"] = estimate <= max_tokens
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-ir", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--target-kind", required=True, choices=["screen", "region", "component", "state"])
    parser.add_argument("--state", action="append", default=[])
    parser.add_argument("--max-tokens", type=int, default=6000)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.max_tokens <= 0:
        print(json.dumps({"status": "invalid", "error": "--max-tokens must be positive"}, indent=2))
        return 1
    try:
        packet = compile_packet(
            load_json(args.ui_ir),
            load_json(args.registry),
            args.target_id,
            args.target_kind,
            args.state,
            args.max_tokens,
        )
        _, diagnostics, blocking = validate(packet, "agent-packet")
    except ValueError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    status = "invalid" if diagnostics else ("blocked" if blocking else "completed")
    print(
        json.dumps(
            {
                "status": status,
                "handoff_ready": not diagnostics and not blocking,
                "output": str(args.output),
                "diagnostics": [item.as_dict() for item in diagnostics],
                "blocking_unknowns": blocking,
                "context_budget": packet["context_budget"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if diagnostics else (2 if blocking else 0)


if __name__ == "__main__":
    sys.exit(main())
