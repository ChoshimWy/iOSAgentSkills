#!/usr/bin/env python3
"""Lint SKILL.md files against the repository Skill Schema v1.

This linter intentionally separates hard failures from migration warnings:

- FAIL: missing YAML frontmatter or mandatory sections required by Skill Schema v1.
- WARN: missing recommended sections or weak output contract fields.

Usage:
    python scripts/lint_skill_schema.py
    python scripts/lint_skill_schema.py --strict
    python scripts/lint_skill_schema.py --include-system

In normal mode, warnings do not fail the command. In strict mode, warnings fail.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

REQUIRED_FRONTMATTER_FIELDS = [
    "name",
    "description",
]

REQUIRED_SECTIONS = [
    "## Purpose",
    "## Agent Rules",
    "## Outputs",
    "## Exit Conditions",
]

RECOMMENDED_SECTIONS = [
    "## Inputs",
    "## Escalation Rules",
    "## Relationship to Other Skills",
]

RECOMMENDED_KEYWORDS = [
    "status",
    "next_action",
    "Token Budget",
]

# Some non-primary or legacy skills may be intentionally short while being migrated.
# Keep this list small; prefer fixing skills instead of expanding exemptions.
LEGACY_WARNING_ONLY = {
    "app-store-changelog",
    "app-store-opportunity-research",
    "apple-docs",
    "open-design",
    "ui-ux-design-system",
    "git-workflow",
    "gh-pr-flow",
    "macos-menubar-tuist-app",
    "macos-spm-app-packaging",
}


@dataclass(frozen=True)
class LintResult:
    file: Path
    name: str
    missing_frontmatter: list[str]
    missing_required: list[str]
    missing_recommended: list[str]
    missing_keywords: list[str]

    @property
    def has_failures(self) -> bool:
        return bool(self.missing_frontmatter or self.missing_required)

    @property
    def has_warnings(self) -> bool:
        return bool(self.missing_recommended or self.missing_keywords)


def read_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    if not text.startswith("---\n"):
        return {}, ["frontmatter delimited by ---"]

    lines = text.splitlines()
    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, ["frontmatter closing ---"]

    frontmatter: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    missing = [
        field
        for field in REQUIRED_FRONTMATTER_FIELDS
        if not frontmatter.get(field)
    ]
    return frontmatter, missing


def read_skill_name(frontmatter: dict[str, str], skill_file: Path) -> str:
    name = frontmatter.get("name")
    if name:
        return name
    return skill_file.parent.name


def lint_file(skill_file: Path) -> LintResult:
    text = skill_file.read_text(encoding="utf-8", errors="ignore")
    frontmatter, missing_frontmatter = read_frontmatter(text)
    name = read_skill_name(frontmatter, skill_file)

    missing_required = [section for section in REQUIRED_SECTIONS if section not in text]
    missing_recommended = [section for section in RECOMMENDED_SECTIONS if section not in text]
    missing_keywords = [keyword for keyword in RECOMMENDED_KEYWORDS if keyword not in text]

    return LintResult(
        file=skill_file,
        name=name,
        missing_frontmatter=missing_frontmatter,
        missing_required=missing_required,
        missing_recommended=missing_recommended,
        missing_keywords=missing_keywords,
    )


def print_result(prefix: str, result: LintResult) -> None:
    print(f"{prefix:<5} {result.file}")
    if result.missing_frontmatter:
        print("      missing frontmatter:")
        for item in result.missing_frontmatter:
            print(f"        - {item}")
    if result.missing_required:
        print("      missing required:")
        for item in result.missing_required:
            print(f"        - {item}")
    if result.missing_recommended:
        print("      missing recommended:")
        for item in result.missing_recommended:
            print(f"        - {item}")
    if result.missing_keywords:
        print("      missing contract keywords:")
        for item in result.missing_keywords:
            print(f"        - {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint skills against Skill Schema v1")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument(
        "--include-system",
        action="store_true",
        help="also lint vendored/system skills under skills/.system",
    )
    parser.add_argument("--skills-dir", default="skills", help="skills directory path")
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists():
        print(f"FAIL  skills directory not found: {skills_dir}")
        return 1

    results = [
        lint_file(path)
        for path in sorted(skills_dir.rglob("SKILL.md"))
        if args.include_system or ".system" not in path.relative_to(skills_dir).parts
    ]

    failures: list[LintResult] = []
    warnings: list[LintResult] = []
    passes: list[LintResult] = []

    for result in results:
        if result.missing_frontmatter:
            failures.append(result)
        elif result.has_failures and result.name not in LEGACY_WARNING_ONLY:
            failures.append(result)
        elif result.has_failures or result.has_warnings:
            warnings.append(result)
        else:
            passes.append(result)

    for result in passes:
        print_result("PASS", result)

    for result in warnings:
        print_result("WARN", result)

    for result in failures:
        print_result("FAIL", result)

    print()
    print(f"Summary: {len(passes)} passed, {len(warnings)} warnings, {len(failures)} failures")

    if failures:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
