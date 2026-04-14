#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_TYPES = {
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
}
SPECIAL_PREFIXES = ("Merge ", "Revert ", "fixup! ", "squash! ")
HEADER_PATTERN = re.compile(r"^(?P<type>[a-z]+)\((?P<scope>[^()\s:]+)\): (?P<subject>.+)$")
CHINESE_CHARACTER_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uf900-\ufaff]")


def validate_header(header: str) -> list[str]:
    errors: list[str] = []

    if not header:
        return ["首行不能为空"]

    if header.startswith(SPECIAL_PREFIXES):
        return []

    if len(header) > 72:
        errors.append(f"首行长度为 {len(header)}，超过 72 字符")

    match = HEADER_PATTERN.fullmatch(header)
    if not match:
        errors.append("格式必须为 <type>(<scope>): <subject>")
        return errors

    commit_type = match.group("type")
    subject = match.group("subject").strip()

    if commit_type not in ALLOWED_TYPES:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        errors.append(f"type 不合法：{commit_type}；允许值：{allowed}")

    if not subject:
        errors.append("subject 不能为空")
        return errors

    if subject.endswith((".", "。")):
        errors.append("subject 不能以句号结尾")

    if not CHINESE_CHARACTER_PATTERN.search(subject):
        errors.append("subject 必须包含中文")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: commitlint.py <commit-message-file>", file=sys.stderr)
        return 2

    message_path = Path(sys.argv[1])
    content = message_path.read_text(encoding="utf-8")
    lines = [line.rstrip("\n") for line in content.splitlines()]
    header = lines[0].strip() if lines else ""

    errors = validate_header(header)
    if not errors:
        return 0

    print("❌ Commit message 不符合仓库规范：", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    print("", file=sys.stderr)
    print("要求：", file=sys.stderr)
    print("  - 使用 Conventional Commits：<type>(<scope>): <subject>", file=sys.stderr)
    print("  - subject 使用中文，不加句号，首行不超过 72 字符", file=sys.stderr)
    print("", file=sys.stderr)
    print("示例：", file=sys.stderr)
    print("  feat(skills): 新增提交信息门禁", file=sys.stderr)
    print("  fix(git-workflow): 修复提交规范校验缺失", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
