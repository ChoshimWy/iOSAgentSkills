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
COMMIT_SOURCE_TAGS = ("[Codex-GENERATED]", "[Codex-ASSIST]", "[HUMAN]")
HEADER_PATTERN = re.compile(r"^(?P<type>[a-z]+)\((?P<scope>[^():]+)\): (?P<subject>.+)$")
CHINESE_CHARACTER_PATTERN = re.compile(r"[㐀-䶿一-鿿豈-﫿]")
CO_AUTHORED_PATTERN = re.compile(r"Co-Authored-By:", re.IGNORECASE)


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
    scope = match.group("scope").strip()
    subject = match.group("subject").strip()

    if commit_type not in ALLOWED_TYPES:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        errors.append(f"type 不合法：{commit_type}；允许值：{allowed}")

    if not scope:
        errors.append("scope 不能为空")

    if not subject:
        errors.append("subject 不能为空")
        return errors

    matched_tag = next((tag for tag in COMMIT_SOURCE_TAGS if subject.startswith(f"{tag} ")), None)
    if not matched_tag:
        allowed_tags = ", ".join(COMMIT_SOURCE_TAGS)
        errors.append(f"subject 必须以提交来源标记开头：{allowed_tags}")
        return errors

    body_subject = subject[len(matched_tag) :].strip()
    if not body_subject:
        errors.append("提交来源标记后必须填写 subject")
        return errors

    if body_subject.endswith((".", "。")):
        errors.append("subject 不能以句号结尾")

    if not CHINESE_CHARACTER_PATTERN.search(body_subject):
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

    if header and not header.startswith(SPECIAL_PREFIXES):
        non_empty_after_first = [ln for ln in lines[1:] if ln.strip()]
        if non_empty_after_first:
            errors.append("commit 只能单行，不允许正文或脚注")
            if any(CO_AUTHORED_PATTERN.search(ln) for ln in non_empty_after_first):
                errors.append("禁止添加 Co-Authored-By 尾注")
    if not errors:
        return 0

    print("❌ Commit message 不符合仓库规范：", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    print("", file=sys.stderr)
    print("要求：", file=sys.stderr)
    print("  - 使用 Conventional Commits：<type>(<scope>): [TAG] <subject>", file=sys.stderr)
    print("  - TAG 只允许 [Codex-GENERATED]、[Codex-ASSIST]、[HUMAN]", file=sys.stderr)
    print("  - subject 使用中文，不加句号，首行不超过 72 字符", file=sys.stderr)
    print("", file=sys.stderr)
    print("示例：", file=sys.stderr)
    print("  feat(Action Panel): [Codex-GENERATED] 增加Action Panel主页面UI", file=sys.stderr)
    print("  refactor(Cue): [Codex-ASSIST] Cue增量更新重构", file=sys.stderr)
    print("  fix(bug): [HUMAN] 修复ONES bug #xxxxx", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
