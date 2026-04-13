#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from typing import List, Dict

WARNING_PREFIXES = (
    'Failed to load provisioning',
    '`devicectl',
    'ERROR:',
)


def rank_state(state: str) -> int:
    state = state.strip().lower()
    if state == 'connected':
        return 0
    if state == 'available (paired)':
        return 1
    if state.startswith('available'):
        return 2
    return 3


def parse_devices(text: str) -> List[Dict[str, str]]:
    devices: List[Dict[str, str]] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.startswith('Name') or set(line) == {'-'}:
            continue
        if any(line.startswith(prefix) for prefix in WARNING_PREFIXES):
            continue
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) < 5:
            continue
        name, hostname, identifier, state, model = parts[:5]
        devices.append({
            'name': name,
            'hostname': hostname,
            'identifier': identifier,
            'state': state,
            'model': model,
        })
    devices.sort(key=lambda item: (rank_state(item['state']), item['name'].lower()))
    return devices


def list_devices() -> List[Dict[str, str]]:
    last_error = 'Failed to list devices with devicectl'
    for _ in range(2):
        result = subprocess.run(
            ['xcrun', 'devicectl', '--timeout', '60', 'list', 'devices'],
            capture_output=True,
            text=True,
        )
        devices = parse_devices(result.stdout)
        if devices:
            return devices
        if result.stderr.strip():
            last_error = result.stderr.strip()
    raise RuntimeError(last_error)


def main() -> int:
    parser = argparse.ArgumentParser(description='List iOS physical devices visible to devicectl')
    parser.add_argument('--json', action='store_true', help='Output machine-readable JSON')
    parser.add_argument('--state', help='Optional exact state filter, e.g. connected')
    args = parser.parse_args()

    try:
        devices = list_devices()
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

    if args.state:
        devices = [device for device in devices if device['state'].lower() == args.state.lower()]

    if args.json:
        print(json.dumps(devices, indent=2, ensure_ascii=False))
        return 0

    if not devices:
        print('No devices found')
        return 0

    for device in devices:
        print(f"{device['state']:<18} {device['name']} [{device['identifier']}] {device['model']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
