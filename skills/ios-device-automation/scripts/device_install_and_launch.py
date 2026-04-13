#!/usr/bin/env python3
import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from device_selector import choose_device  # noqa: E402
from device_list import list_devices  # noqa: E402


def run_command(command, dry_run=False):
    if dry_run:
        return {'command': command, 'exit_code': 0, 'dry_run': True}
    completed = subprocess.run(command)
    return {'command': command, 'exit_code': completed.returncode}


def main() -> int:
    parser = argparse.ArgumentParser(description='Install and/or launch an app on a connected iOS device')
    parser.add_argument('--device-name')
    parser.add_argument('--device-id')
    parser.add_argument('--prefer-model')
    parser.add_argument('--app', help='Path to .app bundle for installation')
    parser.add_argument('--bundle-id', help='Bundle identifier to launch')
    parser.add_argument('--launch', action='store_true', help='Launch the bundle id after install or by itself')
    parser.add_argument('--terminate-pid', type=int, help='Terminate a running process by PID')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

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
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

    actions = []
    if args.app:
        actions.append(['xcrun', 'devicectl', 'device', 'install', 'app', '--device', selected['identifier'], args.app])
    if args.launch:
        if not args.bundle_id:
            print('Error: --launch requires --bundle-id', file=sys.stderr)
            return 1
        actions.append(['xcrun', 'devicectl', 'device', 'process', 'launch', '--device', selected['identifier'], args.bundle_id])
    if args.terminate_pid is not None:
        actions.append(['xcrun', 'devicectl', 'device', 'process', 'terminate', '--device', selected['identifier'], '--pid', str(args.terminate_pid)])

    if not actions:
        print('Error: specify at least one of --app, --launch, or --terminate-pid', file=sys.stderr)
        return 1

    results = []
    exit_code = 0
    for command in actions:
        result = run_command(command, dry_run=args.dry_run)
        results.append(result)
        exit_code = max(exit_code, result['exit_code'])
        if result['exit_code'] != 0 and not args.dry_run:
            break

    if args.json:
        payload = {
            'device': selected,
            'reason': reason,
            'results': [
                {**result, 'command_string': ' '.join(shlex.quote(part) for part in result['command'])}
                for result in results
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Device: {selected['name']} [{selected['identifier']}] ({selected['state']})")
        print(f"Reason: {reason}")
        for result in results:
            print(f"Command: {' '.join(shlex.quote(part) for part in result['command'])}")
            print(f"Exit: {result['exit_code']}")
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
