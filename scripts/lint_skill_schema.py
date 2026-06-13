#!/usr/bin/env python3
"""Lint SKILL.md files against the repository Skill Schema v1.

This linter intentionally separates hard failures from migration warnings:

- FAIL: missing mandatory sections required by Skill Schema v1.
- WARN: missing recommended sections or weak output contract fields.

Usage:
    python scripts/lint_skill_schema.py
    python scripts/lint_skill_schema.py --strict

In normal mode, warnings do not fail the command. In strict mode, warnings fail.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

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
    missing_required: list[str]
    missing_recommended: list[str]
    missing_keywords: list[str]

    @property
    def has_failures(self) -> bool:
        return bool(self.missing_required)

    @property
    def has_warnings(self) -> bool:
        return bool(self.missing_recommended or self.missing_keywords)


def read_skill_name(text: str, skill_file: Path) -> str:
    for line in text.splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return skill_file.parent.name


def lint_file(skill_file: Path) -> LintResult:
    text = skill_file.read_text(encoding="utf-8", errors="ignore")
    name = read_skill_name(text, skill_file)

    missing_required = [section for section in REQUIRED_SECTIONS if section not in text]
    missing_recommended = [section for section in RECOMMENDED_SECTIONS if section not in text]
    missing_keywords = [keyword for keyword in RECOMMENDED_KEYWORDS if keyword not in text]

    return LintResult(
        file=skill_file,
        name=name,
        missing_required=missing_required,
        missing_recommended=missing_recommended,
        missing_keywords=missing_keywords,
    )


def print_result(prefix: str, result: LintResult) -> None:
    print(f"{prefix:<5} {result.file}")
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
    parser.add_argument("--skills-dir", default="skills", help="skills directory path")
    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    if not skills_dir.exists():
        print(f"FAIL  skills directory not found: {skills_dir}")
        return 1

    results = [lint_file(path) for path in sorted(skills_dir.rglob("SKILL.md"))]

    failures: list[LintResult] = []
    warnings: list[LintResult] = []
    passes: list[LintResult] = []

    for result in results:
        if result.has_failures and result.name not in LEGACY_WARNING_ONLY:
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
