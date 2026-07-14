#!/usr/bin/env python3
"""Create a blocked draft Implementation Manifest from a validated Agent Packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from validate_contract import load_json, validate, validate_packet_ui_ir_linkage


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def initialize(
    packet: dict,
    packet_path: Path,
    ui_ir_path: Path,
    manifest_dir: Path | None = None,
) -> dict:
    _, diagnostics, blocking = validate(packet, "agent-packet")
    if diagnostics or blocking:
        raise ValueError(
            f"Agent Packet is not handoff-ready: diagnostics={[item.as_dict() for item in diagnostics]}, blocking={blocking}"
        )
    ui_ir = load_json(ui_ir_path)
    _, ui_diagnostics, ui_blocking = validate(ui_ir, "ui-ir")
    if ui_diagnostics or ui_blocking:
        raise ValueError(
            f"UI IR is not handoff-ready: diagnostics={[item.as_dict() for item in ui_diagnostics]}, blocking={ui_blocking}"
        )
    linkage = validate_packet_ui_ir_linkage(ui_ir, packet)
    if linkage:
        raise ValueError(f"UI IR and Agent Packet linkage is invalid: {[item.as_dict() for item in linkage]}")
    bindings = {item["id"]: item for item in packet["bindings"]}
    mappings = []
    for node in packet["nodes"]:
        for binding_id in node.get("binding_refs", []):
            binding = bindings[binding_id]
            mappings.append(
                {
                    "design_node_id": node["id"],
                    "semantic_role": node.get("role", "unknown"),
                    "binding_id": binding_id,
                    "framework": binding["framework"],
                    "code_symbol": binding["symbol"],
                    "source_file": binding["source"],
                    "preview_scene": "",
                    "validation_region": "",
                }
            )
    if not mappings:
        raise ValueError("Agent Packet contains no resolved component bindings")
    def artifact_path(path: Path) -> str:
        resolved = path.resolve()
        if manifest_dir is None:
            return str(resolved)
        return Path(os.path.relpath(resolved, manifest_dir.resolve())).as_posix()

    return {
        "manifest_version": "1.0.0",
        "status": "draft",
        "screen": packet["task"]["screen"],
        "source": {
            "ui_ir": {"path": artifact_path(ui_ir_path), "sha256": _sha256(ui_ir_path)},
            "agent_packet": {"path": artifact_path(packet_path), "sha256": _sha256(packet_path)},
        },
        "mappings": mappings,
        "validation": {"status": "pending", "evidence": []},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-packet", required=True, type=Path)
    parser.add_argument("--ui-ir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = initialize(load_json(args.agent_packet), args.agent_packet, args.ui_ir, args.output.parent)
        _, diagnostics, blocking = validate(manifest, "implementation-manifest")
    except ValueError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "draft",
                "handoff_ready": False,
                "output": str(args.output),
                "diagnostics": [item.as_dict() for item in diagnostics],
                "blocking_unknowns": blocking,
                "next_action": "fill preview_scene and validation_region, attach validation evidence, then set complete",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1 if diagnostics else 0


if __name__ == "__main__":
    sys.exit(main())
