#!/usr/bin/env python3
"""
Quick validation script for skills - minimal version
"""

import re
import sys
from pathlib import Path

MAX_SKILL_NAME_LENGTH = 64


def parse_frontmatter(frontmatter_text):
    top_level = {}
    current_multiline_key = None
    multiline_indent = None
    multiline_lines = []

    def flush_multiline():
        nonlocal current_multiline_key, multiline_indent, multiline_lines
        if current_multiline_key is None:
            return
        top_level[current_multiline_key] = "\n".join(multiline_lines).rstrip()
        current_multiline_key = None
        multiline_indent = None
        multiline_lines = []

    for raw_line in frontmatter_text.splitlines():
        if current_multiline_key is not None:
            if raw_line.strip() and (len(raw_line) - len(raw_line.lstrip(" "))) >= multiline_indent:
                multiline_lines.append(raw_line[multiline_indent:])
                continue
            flush_multiline()

        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if raw_line.startswith((" ", "\t", "-")):
            # Nested / list content belongs to the last parsed top-level key.
            continue

        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw_line)
        if not match:
            continue

        key = match.group(1)
        value = match.group(2).strip()
        if value in {"|", ">"}:
            current_multiline_key = key
            multiline_indent = 2
            multiline_lines = []
            continue

        if not value:
            top_level[key] = {}
            continue

        top_level[key] = value.strip().strip('"').strip("'")

    flush_multiline()
    return top_level


def validate_skill(skill_path):
    """Basic validation of a skill"""
    skill_path = Path(skill_path)

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, "SKILL.md not found"

    content = skill_md.read_text()
    if not content.startswith("---"):
        return False, "No YAML frontmatter found"

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return False, "Invalid frontmatter format"

    frontmatter_text = match.group(1)

    frontmatter = parse_frontmatter(frontmatter_text)
    if not isinstance(frontmatter, dict):
        return False, "Frontmatter must be a YAML dictionary"

    allowed_properties = {"name", "description", "license", "allowed-tools", "metadata"}

    unexpected_keys = set(frontmatter.keys()) - allowed_properties
    if unexpected_keys:
        allowed = ", ".join(sorted(allowed_properties))
        unexpected = ", ".join(sorted(unexpected_keys))
        return (
            False,
            f"Unexpected key(s) in SKILL.md frontmatter: {unexpected}. Allowed properties are: {allowed}",
        )

    if "name" not in frontmatter:
        return False, "Missing 'name' in frontmatter"
    if "description" not in frontmatter:
        return False, "Missing 'description' in frontmatter"

    name = frontmatter.get("name", "")
    if not isinstance(name, str):
        return False, f"Name must be a string, got {type(name).__name__}"
    name = name.strip()
    if name:
        if not re.match(r"^[a-z0-9-]+$", name):
            return (
                False,
                f"Name '{name}' should be hyphen-case (lowercase letters, digits, and hyphens only)",
            )
        if name.startswith("-") or name.endswith("-") or "--" in name:
            return (
                False,
                f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens",
            )
        if len(name) > MAX_SKILL_NAME_LENGTH:
            return (
                False,
                f"Name is too long ({len(name)} characters). "
                f"Maximum is {MAX_SKILL_NAME_LENGTH} characters.",
            )

    description = frontmatter.get("description", "")
    if not isinstance(description, str):
        return False, f"Description must be a string, got {type(description).__name__}"
    description = description.strip()
    if description:
        if "<" in description or ">" in description:
            return False, "Description cannot contain angle brackets (< or >)"
        if len(description) > 1024:
            return (
                False,
                f"Description is too long ({len(description)} characters). Maximum is 1024 characters.",
            )

    return True, "Skill is valid!"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python quick_validate.py <skill_directory>")
        sys.exit(1)

    valid, message = validate_skill(sys.argv[1])
    print(message)
    sys.exit(0 if valid else 1)
