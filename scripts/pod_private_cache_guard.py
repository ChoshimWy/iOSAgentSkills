#!/usr/bin/env python3
"""Guard against editing vendored Pod copies instead of local private library sources."""

from __future__ import annotations

import os
import re
import subprocess
import sys

PODS_PATH_RE = re.compile(r"(?:^|/)Pods/([^/]+)(?:/|$)")
PODS_CONTAINER_DIRS = {
    "Headers",
    "Local Podspecs",
    "Target Support Files",
    "Development Pods",
}


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def staged_files() -> list[str]:
    out = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def extract_real_pod_name(path: str) -> str | None:
    m = PODS_PATH_RE.search(path)
    if not m:
        return None
    first_segment = m.group(1)
    if first_segment in PODS_CONTAINER_DIRS:
        return None
    return first_segment


def main() -> int:
    if os.getenv("ALLOW_PODS_CACHE_EDIT") == "1":
        return 0

    files = staged_files()
    pod_cache_touches = [f for f in files if "/Pods/" in f or f.startswith("Pods/")]
    if not pod_cache_touches:
        return 0

    touched_pods = {pod for path in pod_cache_touches if (pod := extract_real_pod_name(path))}

    if touched_pods:
        print("[pod-private-guard] ❌ 检测到直接修改 Pods 中的库副本（严格禁止）：")
        for pod in sorted(touched_pods):
            print(f"  - {pod}")
        print("\n请改为严格流程：")
        print("1) 在主工程 Podfile 将目标私有库切为本地 :path 依赖")
        print("2) pod install")
        print("3) 到本机私有库源码仓库修改并提交（不要改 Pods/ 副本）")
        print("4) 回主工程联调验证")
        print("5) 切回 Podfile 声明的线上版本化依赖后再提交主工程")
        print("\n如确认临时放行，可使用: ALLOW_PODS_CACHE_EDIT=1 git commit ...")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
