#!/usr/bin/env python3
"""Guard against unsafe CocoaPods commit states for private/local library workflows."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PODS_PATH_RE = re.compile(r"(?:^|/)Pods/([^/]+)(?:/|$)")
PODS_CONTAINER_DIRS = {
    "Headers",
    "Local Podspecs",
    "Manifest.lock",
    "Target Support Files",
    "Development Pods",
}
PODFILE_RE = re.compile(r"(?:^|/)Podfile$")
POD_LOCK_RE = re.compile(r"(?:^|/)Podfile\.lock$")
MANIFEST_LOCK_RE = re.compile(r"(?:^|/)Pods/Manifest\.lock$")
POD_NAME_RE = re.compile(r"pod\s+['\"]([^'\"]+)['\"]")
LOCAL_PATH_OPTION_RE = re.compile(r"(?:\:path\s*=>|\bpath:)")
LOCKFILE_POD_NAME_RE = re.compile(r"^\s{2}([^:\s][^:]*):\s*$")
LOCKFILE_PATH_RE = re.compile(r"^\s{4}:path:\s*(.+?)\s*$")


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def staged_files() -> list[str]:
    out = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def staged_file_content(path: str) -> str:
    return subprocess.check_output(["git", "show", f":{path}"], text=True)


def extract_real_pod_name(path: str) -> str | None:
    m = PODS_PATH_RE.search(path)
    if not m:
        return None
    first_segment = m.group(1)
    if first_segment in PODS_CONTAINER_DIRS:
        return None
    return first_segment


def extract_local_path_pods_from_podfile(text: str) -> set[str]:
    results: set[str] = set()
    current_pod: str | None = None
    current_has_path = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if match := POD_NAME_RE.search(line):
            if current_pod and current_has_path:
                results.add(current_pod)
            current_pod = match.group(1)
            current_has_path = bool(LOCAL_PATH_OPTION_RE.search(line))
            continue

        if current_pod and LOCAL_PATH_OPTION_RE.search(line):
            current_has_path = True

    if current_pod and current_has_path:
        results.add(current_pod)
    return results


def extract_local_path_pods_from_lockfile(text: str) -> set[str]:
    results: set[str] = set()
    current_section = ""
    current_pod: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        if not line.startswith(" "):
            current_section = line.strip()
            current_pod = None
            continue
        if current_section != "EXTERNAL SOURCES:":
            continue
        if match := LOCKFILE_POD_NAME_RE.match(line):
            current_pod = match.group(1).strip()
            continue
        if LOCKFILE_PATH_RE.match(line) and current_pod:
            results.add(current_pod)
    return results


def staged_local_path_refs(files: list[str]) -> dict[str, set[str]]:
    results: dict[str, set[str]] = {}
    for path in files:
        if PODFILE_RE.search(path):
            pods = extract_local_path_pods_from_podfile(staged_file_content(path))
        elif POD_LOCK_RE.search(path) or MANIFEST_LOCK_RE.search(path):
            pods = extract_local_path_pods_from_lockfile(staged_file_content(path))
        else:
            continue
        if pods:
            results[path] = pods
    return results


def main() -> int:
    files = staged_files()
    if not files:
        return 0

    allow_pods_cache_edit = os.getenv("ALLOW_PODS_CACHE_EDIT") == "1"
    pod_cache_touches = [f for f in files if "/Pods/" in f or f.startswith("Pods/")]
    touched_pods = {pod for path in pod_cache_touches if (pod := extract_real_pod_name(path))}
    local_path_ref_touches = staged_local_path_refs(files)

    if local_path_ref_touches:
        print("[pod-private-guard] ❌ 检测到本次提交包含本地 `:path` 私有库引用（严格禁止提交）：")
        for path, pods in sorted(local_path_ref_touches.items(), key=lambda item: item[0]):
            display_path = Path(path).as_posix()
            pod_list = ", ".join(sorted(pods))
            print(f"  - {display_path}: {pod_list}")
        print("\n请改为严格流程：")
        print("1) 本地联调时可临时把主工程私有库切为本地 :path 依赖")
        print("2) 使用本地 :path 依赖完成开发、验证与独立 review，但不要把该依赖形态提交到项目仓库")
        print("3) 验证通过后可继续保持当前本地 :path 状态，不需要为了收口自动回切线上")
        print("4) 只有用户明确要求回切线上，或准备提交主项目依赖文件时，才恢复 Podfile / Podfile.lock / Pods/Manifest.lock 到可提交状态")
        print("5) 如需保留本地联调配置，请仅保留在未提交工作区，不要进入 git commit")
        return 1

    if touched_pods:
        if allow_pods_cache_edit:
            return 0
        print("[pod-private-guard] ❌ 检测到直接修改 Pods 中的库副本（严格禁止）：")
        for pod in sorted(touched_pods):
            print(f"  - {pod}")
        print("\n请改为严格流程：")
        print("1) 在主工程 Podfile 将目标私有库切为本地 :path 依赖")
        print("2) pod install")
        print("3) 到本机私有库源码仓库修改并提交（不要改 Pods/ 副本）")
        print("4) 回主工程继续使用本地 :path 私有库依赖联调验证")
        print("5) 验证通过后默认保持当前本地 :path 状态；回线上版本化依赖仅在用户明确要求或提交主项目依赖文件时执行，并需单独验证/提交")
        print("\n如确认临时放行，可使用: ALLOW_PODS_CACHE_EDIT=1 git commit ...")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
