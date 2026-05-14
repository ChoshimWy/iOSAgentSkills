#!/usr/bin/env python3
"""Block committing Pod cache edits unless Podfile uses local :path dependencies."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PODS_PATH_RE = re.compile(r"(?:^|/)Pods/([^/]+)/")
POD_DECL_RE = re.compile(
    r"^\s*pod\s+['\"](?P<name>[^'\"]+)['\"](?P<rest>.*)$", re.MULTILINE
)
PATH_ARG_RE = re.compile(r"(?::path\s*=>\s*['\"][^'\"]+['\"]|path:\s*['\"][^'\"]+['\"])")


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def staged_files() -> list[str]:
    out = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def find_podfile(repo_root: Path) -> Path | None:
    root_podfile = repo_root / "Podfile"
    if root_podfile.exists():
        return root_podfile

    try:
        podfiles = run(["git", "ls-files", "*Podfile"]).splitlines()
    except Exception:
        return None

    for entry in podfiles:
        p = repo_root / entry
        if p.name == "Podfile" and p.exists():
            return p
    return None


def pods_with_local_path(podfile: Path) -> set[str]:
    text = podfile.read_text(encoding="utf-8", errors="ignore")
    local = set()
    for match in POD_DECL_RE.finditer(text):
        name = match.group("name")
        rest = match.group("rest")
        if PATH_ARG_RE.search(rest):
            local.add(name)
    return local


def main() -> int:
    if os.getenv("ALLOW_PODS_CACHE_EDIT") == "1":
        return 0

    files = staged_files()
    pod_cache_touches = [f for f in files if "/Pods/" in f or f.startswith("Pods/")]
    if not pod_cache_touches:
        return 0

    touched_pods = set()
    for path in pod_cache_touches:
        m = PODS_PATH_RE.search(path)
        if m:
            touched_pods.add(m.group(1))

    repo_root = Path(run(["git", "rev-parse", "--show-toplevel"]))
    podfile = find_podfile(repo_root)
    if podfile is None:
        print("[pod-private-guard] ❌ 检测到 staged Pods 缓存改动，但仓库未找到 Podfile。")
        print("请先把私有库切到本地 :path 依赖，再在私有库源码仓库里修改并提交。")
        print("如确认临时放行，可使用: ALLOW_PODS_CACHE_EDIT=1 git commit ...")
        return 1

    local_path_pods = pods_with_local_path(podfile)

    violating = sorted(p for p in touched_pods if p and p not in local_path_pods)
    if violating:
        print("[pod-private-guard] ❌ 检测到 Pods 缓存改动，且以下 Pod 未在 Podfile 使用本地 :path 依赖：")
        for pod in violating:
            print(f"  - {pod}")
        print("\n请按流程操作：")
        print("1) 在主工程 Podfile 将目标私有库切为 :path 本地依赖")
        print("2) pod install")
        print("3) 在私有库源码目录完成修改并提交")
        print("4) 回主工程联调验证后，再切回版本化依赖")
        print("\n如确认临时放行，可使用: ALLOW_PODS_CACHE_EDIT=1 git commit ...")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
