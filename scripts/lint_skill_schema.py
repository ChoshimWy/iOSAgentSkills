#!/usr/bin/env python3
from pathlib import Path
import sys

REQUIRED_SECTIONS = [
    '## Purpose',
    '## Agent Rules',
    '## Outputs',
    '## Exit Conditions'
]

skills_dir = Path('skills')
failed = []

for skill_file in skills_dir.rglob('SKILL.md'):
    text = skill_file.read_text(encoding='utf-8', errors='ignore')

    missing = [s for s in REQUIRED_SECTIONS if s not in text]

    if missing:
        failed.append((skill_file, missing))

if failed:
    print('发现不符合 Skill 规范的文件:\n')

    for file, missing in failed:
        print(f'- {file}')
        for item in missing:
            print(f'  缺少: {item}')

    sys.exit(1)

print('所有 Skill 结构检查通过')
