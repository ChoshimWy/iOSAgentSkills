#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent

MANDATORY_VERIFY_SKILLS = [
    "ios-feature-implementation",
    "swiftui-feature-implementation",
    "uikit-feature-implementation",
    "swift-expert",
    "swiftui-ui-patterns",
    "swiftui-view-refactor",
    "swiftui-liquid-glass",
    "refactoring",
    "sdk-architecture",
    "debugging",
    "testing",
    "ios-performance",
    "swiftui-performance-audit",
    "xcode-build",
    "ios-device-automation",
    "ios-simulator-automation",
    "macos-menubar-tuist-app",
]


def require_contains(path: Path, snippets: list[str], failures: list[str]) -> None:
    text = path.read_text()
    missing = [snippet for snippet in snippets if snippet not in text]
    if missing:
        failures.append(f"{path.relative_to(ROOT)} missing: {', '.join(missing)}")


def main() -> int:
    failures: list[str] = []

    require_contains(
        ROOT / "AGENTS.md",
        [
            "强制 `verify-ios-build` 门禁",
            "目标项目环境",
            "如果同时存在 `.xcworkspace` 和 `.xcodeproj`，验证必须使用 `.xcworkspace`。",
            "已连接真机",
            "在 `verify-ios-build` 成功之前，任务都不算完成",
        ],
        failures,
    )
    require_contains(
        ROOT / "README.md",
        [
            "强制 `verify-ios-build` 收尾门禁",
            "目标项目根目录的项目环境",
            "优先 `.xcworkspace`",
            "已连接真机",
            "python3 scripts/lint_verify_ios_build_policy.py",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "TAXONOMY.md",
        [
            "最终都必须切到 `verify-ios-build` 做收尾门禁",
            "目标项目根目录的项目环境",
            "优先 `.xcworkspace`",
            "已连接真机",
            "不能把任务表述为“已完成”",
        ],
        failures,
    )

    for skill in MANDATORY_VERIFY_SKILLS:
        skill_md = ROOT / "skills" / skill / "SKILL.md"
        require_contains(
            skill_md,
            [
                "## 强制收尾验证",
                "`verify-ios-build`",
                "项目环境",
                ".xcworkspace",
                "已连接真机",
                "任务未完成",
            ],
            failures,
        )

        openai_yaml = ROOT / "skills" / skill / "agents" / "openai.yaml"
        if not openai_yaml.exists():
            failures.append(f"{openai_yaml.relative_to(ROOT)} missing")
        else:
            require_contains(
                openai_yaml,
                [
                    "$verify-ios-build",
                    "项目环境",
                    ".xcworkspace",
                    "已连接真机",
                ],
                failures,
            )

    require_contains(
        ROOT / "skills" / "verify-ios-build" / "SKILL.md",
        [
            "强制收尾验证技能",
            "项目环境",
            "sandbox_permissions=\\\"require_escalated\\\"",
            ".xcworkspace",
            "已连接真机",
            "任务未完成",
            "macOS Xcode 工程",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "references" / "override-config.md",
        [
            "项目环境",
            "已连接真机",
            "generic/platform=iOS Simulator",
            "宿主机 `xcodebuild build`",
            "`.xcworkspace` 优先于 `.xcodeproj`",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "scripts" / "build-check.sh",
        [
            "generic/platform=iOS Simulator",
            "connected-only",
            "XCODE_VALIDATION_PLATFORM='macos'",
            "no connected physical iOS destination available; using simulator",
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "verify-ios-build" / "scripts" / "build_check.py",
        [
            'validation_platform=os.environ.get("XCODE_VALIDATION_PLATFORM")',
            'if config.validation_platform == "macos":',
            'default host build (no explicit destination)',
        ],
        failures,
    )
    require_contains(
        ROOT / "skills" / "ios-device-automation" / "scripts" / "device_helpers.sh",
        [
            "select_connected_xcode_destination",
            "connected-only",
            "selected first connected xcodebuild destination",
        ],
        failures,
    )

    verify_openai = ROOT / "skills" / "verify-ios-build" / "agents" / "openai.yaml"
    if not verify_openai.exists():
        failures.append(f"{verify_openai.relative_to(ROOT)} missing")
    else:
        require_contains(
            verify_openai,
            [
                "项目环境",
                ".xcworkspace",
                "已连接真机",
                "simulator",
            ],
            failures,
        )

    if failures:
        print("verify-ios-build policy lint failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("verify-ios-build policy lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
