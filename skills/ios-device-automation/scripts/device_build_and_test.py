#!/usr/bin/env python3
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from device_selector import choose_device  # noqa: E402
from device_list import list_devices  # noqa: E402


def load_env(root: Path) -> dict:
    env_file = root / '.codex' / 'xcodebuild.env'
    values = {}
    if not env_file.exists():
        return values
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def pick_workspace(root: Path, env: dict) -> str | None:
    if env.get('XCODE_WORKSPACE'):
        return env['XCODE_WORKSPACE']
    candidates = [
        p for p in root.rglob('*.xcworkspace')
        if 'Pods' not in p.parts and 'project.xcworkspace' not in str(p)
    ]
    candidates = [p for p in candidates if len(p.relative_to(root).parts) <= 3]
    return str(sorted(candidates)[0].relative_to(root)) if candidates else None


def pick_project(root: Path, env: dict) -> str | None:
    if env.get('XCODE_PROJECT'):
        return env['XCODE_PROJECT']
    candidates = [p for p in root.rglob('*.xcodeproj') if 'Pods' not in p.parts]
    candidates = [p for p in candidates if len(p.relative_to(root).parts) <= 3]
    return str(sorted(candidates)[0].relative_to(root)) if candidates else None


def pick_scheme(root: Path, env: dict) -> str:
    if env.get('XCODE_SCHEME'):
        return env['XCODE_SCHEME']
    schemes = []
    for path in sorted(root.rglob('*.xcscheme')):
        if 'Pods' in path.parts:
            continue
        schemes.append(path.stem)
    if not schemes:
        raise RuntimeError('No shared scheme found')
    for scheme in schemes:
        if not re.search(r'(Tests|UITests)$', scheme) and not re.search(r'(^|[_-])(DEV|TEST|UAT|STAGING)$', scheme):
            return scheme
    for scheme in schemes:
        if not re.search(r'(Tests|UITests)$', scheme):
            return scheme
    return schemes[0]


def build_command(root: Path, args, env: dict, device_id: str):
    workspace = args.workspace or pick_workspace(root, env)
    project = args.project or pick_project(root, env)
    if not workspace and not project:
        raise RuntimeError(f'No .xcworkspace or .xcodeproj found in {root}')
    scheme = args.scheme or pick_scheme(root, env)
    configuration = args.configuration or env.get('XCODE_CONFIGURATION', 'Debug')
    action = args.action or env.get('XCODE_ACTION', 'build')

    command = ['xcodebuild']
    if workspace:
        command += ['-workspace', workspace]
    else:
        command += ['-project', project]
    command += [
        '-scheme', scheme,
        '-configuration', configuration,
        '-destination', f'id={device_id}',
    ]
    if args.test_suite:
        command += [f'-only-testing:{args.test_suite}']
    command.append(action)
    return {
        'workspace': workspace,
        'project': project,
        'scheme': scheme,
        'configuration': configuration,
        'action': action,
        'destination': f'id={device_id}',
        'command': command,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Build or test an Xcode project on a connected iOS device')
    parser.add_argument('root', nargs='?', default='.', help='Target repo root')
    parser.add_argument('--workspace')
    parser.add_argument('--project')
    parser.add_argument('--scheme')
    parser.add_argument('--configuration')
    parser.add_argument('--action', choices=['build', 'test'], default='build')
    parser.add_argument('--test-suite', help='Specific test suite, e.g. AppTests/LoginTests')
    parser.add_argument('--device-name')
    parser.add_argument('--device-id')
    parser.add_argument('--prefer-model')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    env = load_env(root)
    try:
        if args.device_id and not args.device_name and not args.prefer_model:
            selected = {
                'name': args.device_id,
                'identifier': args.device_id,
                'state': 'explicit',
                'model': 'unknown',
                'hostname': '',
            }
            reason = 'using explicit device identifier'
        else:
            devices = list_devices()
            selected, reason = choose_device(devices, name=args.device_name, identifier=args.device_id, prefer_model=args.prefer_model)
            if not selected:
                raise RuntimeError(reason)
        payload = build_command(root, args, env, selected['identifier'])
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

    result_payload = {
        'root': str(root),
        'device': selected,
        'reason': reason,
        **payload,
    }

    if args.json:
        result_payload['command_string'] = ' '.join(shlex.quote(part) for part in payload['command'])
    else:
        print(f"Device: {selected['name']} [{selected['identifier']}] ({selected['state']})")
        print(f"Reason: {reason}")
        print(f"Command: {' '.join(shlex.quote(part) for part in payload['command'])}")

    if args.dry_run:
        if args.json:
            print(json.dumps(result_payload, indent=2, ensure_ascii=False))
        return 0

    completed = subprocess.run(payload['command'], cwd=root)
    result_payload['exit_code'] = completed.returncode
    if args.json:
        print(json.dumps(result_payload, indent=2, ensure_ascii=False))
    return completed.returncode


if __name__ == '__main__':
    raise SystemExit(main())
