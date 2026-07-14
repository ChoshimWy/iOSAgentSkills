#!/usr/bin/env python3
"""Index UIKit and SwiftUI type declarations into reviewable Registry candidates."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


DECLARATION = re.compile(
    r"^\s*(?:@[A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?\s+)*"
    r"(?:(?:public|open|internal|private|fileprivate|final|indirect)\s+)*"
    r"(class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*([^\{]+))?"
)
UIKIT_BASES = {
    "UIView",
    "UIViewController",
    "UIControl",
    "UITableViewCell",
    "UICollectionViewCell",
    "UITableViewHeaderFooterView",
}


def _source_path(path: Path, cwd: Path) -> str:
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def scan(roots: list[Path], module: str, cwd: Path) -> list[dict]:
    entries: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for root in sorted((item.resolve() for item in roots), key=lambda item: item.as_posix()):
        paths = [root] if root.is_file() else sorted(root.rglob("*.swift"))
        for path in paths:
            if path.suffix != ".swift" or not path.is_file():
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                match = DECLARATION.match(line)
                if not match:
                    continue
                kind, symbol, inheritance = match.groups()
                inherited = {
                    part.strip().split("<", 1)[0].strip()
                    for part in (inheritance or "").split(",")
                    if part.strip()
                }
                framework = None
                if kind == "struct" and "View" in inherited:
                    framework = "SwiftUI"
                elif kind == "class" and inherited & UIKIT_BASES:
                    framework = "UIKit"
                if framework is None or (module, symbol) in seen:
                    continue
                seen.add((module, symbol))
                source = _source_path(path, cwd)
                declaration_hash = hashlib.sha256(line.strip().encode("utf-8")).hexdigest()
                stable = _identifier(f"{module}-{symbol}")
                entries.append(
                    {
                        "id": f"candidate.{stable}",
                        "design_id": f"unmapped:{module}.{symbol}",
                        "semantic_role": "unmapped",
                        "reuse_policy": "preferred",
                        "status": "pending-review",
                        "bindings": [
                            {
                                "id": f"binding.{stable}",
                                "framework": framework,
                                "symbol": symbol,
                                "module": module,
                                "source": source,
                                "declaration_line": line_number,
                                "declaration_hash": f"sha256:{declaration_hash}",
                            }
                        ],
                        "provenance": {"source": "source-index", "confidence": "heuristic"},
                    }
                )
    return sorted(entries, key=lambda item: (item["design_id"], item["id"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", required=True, type=Path, help="Swift file or source root; repeatable")
    parser.add_argument("--module", required=True, help="Owning Swift module")
    parser.add_argument("--generated-at", help="RFC 3339 timestamp; defaults to current UTC")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    missing = [str(root) for root in args.root if not root.exists()]
    if missing:
        print(json.dumps({"status": "invalid", "error": f"source roots not found: {missing}"}, indent=2))
        return 1
    generated_at = args.generated_at or datetime.now(timezone.utc).isoformat()
    registry = {
        "registry_version": "1.0.0",
        "generated_at": generated_at,
        "source_roots": [_source_path(root, Path.cwd()) for root in args.root],
        "entries": scan(args.root, args.module, Path.cwd()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "output": str(args.output), "candidates": len(registry["entries"])}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
