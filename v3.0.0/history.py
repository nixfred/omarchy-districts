#!/usr/bin/env python3
"""Private named camera bookmarks. Observation replay never persists here."""
import argparse
import contextlib
import fcntl
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time

MAX_VIEWS = 12
MAX_BYTES = 32768


def state_path():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'districts' / 'camera.json'


def number(value, fallback, low, high):
    try:
        n = float(value)
        return max(low, min(high, n)) if math.isfinite(n) else fallback
    except (ValueError, TypeError, OverflowError):
        return fallback


def camera(value):
    value = value if isinstance(value, dict) else {}
    return { 'x': number(value.get('x'), 0, -1000000, 1000000),
             'y': number(value.get('y'), 0, -1000000, 1000000),
             'zoom': number(value.get('zoom'), 1, .08, 6),
             'yaw': number(value.get('yaw'), 45, -1e9, 1e9) % 360,
             'tilt': number(value.get('tilt'), 35.26438968, 20, 75) }


def name(value):
    return re.sub(r'\s+', ' ', re.sub(r'[\x00-\x1f\x7f]', '', str(value or ''))).strip()[:40]


def target(value):
    try:
        n = int(value)
        return n if float(value) == n and 0 < n <= 100000 else None
    except (ValueError, TypeError, OverflowError):
        return None


def normalize(value):
    records, seen = [], set()
    for entry in (value.get('viewpoints', []) if isinstance(value, dict) else [])[:MAX_VIEWS]:
        if not isinstance(entry, dict):
            continue
        label = name(entry.get('name'))
        if not label or label.casefold() in seen:
            continue
        seen.add(label.casefold())
        records.append({'name': label, 'camera': camera(entry.get('camera')), 'targetDistrict': target(entry.get('targetDistrict')), 'savedAt': number(entry.get('savedAt'), 0, 0, 1e12)})
    return {'schema': 1, 'viewpoints': records}


def read(path):
    try:
        with open(path, 'rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return normalize({})
        return normalize(json.loads(raw))
    except (OSError, ValueError, TypeError, AttributeError):
        return normalize({})


@contextlib.contextmanager
def locked(path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path.parent / '.camera.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def write(path, value):
    raw = (json.dumps(normalize(value), ensure_ascii=False, allow_nan=False) + '\n').encode()
    if len(raw) > MAX_BYTES:
        raise ValueError('Camera bookmarks exceed the private state size limit.')
    fd, temporary = tempfile.mkstemp(prefix='.camera-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def update(path, operation, label='', value=None, district=None):
    if operation == 'list':
        return read(path)
    label = name(label)
    if not label:
        raise ValueError('Give the viewpoint a name (up to 40 characters).')
    with locked(path):
        data = read(path)
        index = next((i for i, entry in enumerate(data['viewpoints']) if entry['name'].casefold() == label.casefold()), None)
        if operation == 'delete':
            if index is not None:
                data['viewpoints'].pop(index)
        elif operation == 'save':
            entry = {'name': label, 'camera': camera(value), 'targetDistrict': target(district), 'savedAt': time.time()}
            if index is not None:
                data['viewpoints'][index] = entry
            elif len(data['viewpoints']) < MAX_VIEWS:
                data['viewpoints'].append(entry)
            else:
                raise ValueError('Twelve viewpoints are saved. Delete one before saving another.')
        else:
            raise ValueError('Unknown camera operation.')
        write(path, data)
        return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['list', 'save', 'delete'])
    parser.add_argument('--name', default='')
    parser.add_argument('--camera', default='{}')
    parser.add_argument('--target-district', type=int)
    args = parser.parse_args()
    try:
        if len(args.camera) > 4096:
            raise ValueError('Invalid camera data.')
        value = json.loads(args.camera)
        result = update(state_path(), args.operation, args.name, value, args.target_district)
        print(json.dumps({'ok': True, **result}, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
