#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from device_list import list_devices, rank_state  # noqa: E402


def choose_device(devices, name=None, identifier=None, prefer_model=None):
    if identifier:
        for device in devices:
            if device['identifier'] == identifier:
                return device, 'matched explicit identifier'
        return None, f'identifier not found: {identifier}'

    if name:
        for device in devices:
            if device['name'] == name:
                return device, 'matched explicit name'
        return None, f'name not found: {name}'

    preferred = devices
    if prefer_model:
        preferred = [d for d in devices if prefer_model.lower() in d['model'].lower() or prefer_model.lower() in d['name'].lower()] or devices

    preferred = sorted(preferred, key=lambda item: (rank_state(item['state']), item['name'].lower()))
    for wanted in ('connected', 'available (paired)'):
        for device in preferred:
            if device['state'].lower() == wanted:
                return device, f'selected best {wanted} device'
    if preferred:
        return preferred[0], 'selected fallback device'
    return None, 'no devices available'


def main() -> int:
    parser = argparse.ArgumentParser(description='Select the best available iOS physical device')
    parser.add_argument('--name', help='Explicit device name')
    parser.add_argument('--identifier', '--udid', dest='identifier', help='Explicit device identifier')
    parser.add_argument('--prefer-model', help='Prefer a device model/name containing this text')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    args = parser.parse_args()

    try:
        devices = list_devices()
        selected, reason = choose_device(devices, name=args.name, identifier=args.identifier, prefer_model=args.prefer_model)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1

    if not selected:
        print(reason, file=sys.stderr)
        return 1

    payload = {'selected': selected, 'reason': reason, 'candidates': devices}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"Selected: {selected['name']} [{selected['identifier']}] ({selected['state']})")
        print(f"Reason: {reason}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
