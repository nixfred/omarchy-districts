#!/usr/bin/env python3
"""Explicit, bounded, title-free window organization. No automatic actions.

preview consumes the displayed normalized snapshot on stdin. apply consumes the
unchanged preview plan on stdin and requires --accept <planId>. Plans expire in
120 seconds; the UI must retain the exact plan, never reconstruct its moves.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
import re
import sys
import subprocess
import time

import districts as bridge

MAX_MOVES = 32
TTL = 120
MAX_INPUT = 262144
ROLES = frozenset(bridge.GROUP_COLORS)
KNOWN = {
    'development': 'code code-oss vscodium codium zed dev.zed.zed sublime_text sublime-text jetbrains-idea jetbrains-pycharm jetbrains-webstorm jetbrains-clion jetbrains-rustrover dbeaver postman gitkraken'.split(),
    'entertainment': 'spotify com.spotify.client vlc org.videolan.vlc mpv steam lutris com.valvesoftware.steam'.split(),
    'communication': 'slack com.slack.slack discord com.discordapp.discord signal org.signal.signal telegramdesktop org.telegram.desktop teams zoom thunderbird org.mozilla.thunderbird'.split(),
    'research': 'obsidian md.obsidian.obsidian zotero org.zotero.zotero libreoffice libreoffice-writer libreoffice-calc libreoffice-impress org.gnome.evince okular org.kde.okular calibre'.split(),
    'system': 'kitty foot alacritty wezterm org.wezfurlong.wezterm org.gnome.terminal konsole org.kde.konsole org.gnome.nautilus dolphin org.kde.dolphin thunar pavucontrol org.gnome.settings gparted'.split(),
}
CATEGORIES = {'Development': 'development', 'Game': 'entertainment', 'AudioVideo': 'entertainment', 'Audio': 'entertainment', 'Video': 'entertainment', 'Chat': 'communication', 'InstantMessaging': 'communication', 'Email': 'communication', 'Office': 'research', 'Education': 'research', 'Science': 'research', 'Graphics': 'research', 'System': 'system', 'Utility': 'system'}
BROWSER = re.compile(r'^(brave(?:-browser)?|firefox|org\.mozilla\.firefox|chromium|google-chrome|chrome|microsoft-edge|vivaldi|librewolf|zen|zen-browser)$')


def canonical_json(value):
    # Qt's JSON.stringify turns 1.0 into 1 and -0.0 into 0. Normalize numeric
    # identities before hashing, while retaining fractional epoch timestamps.
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Preview numbers must be finite.')
        if value.is_integer():
            value = int(value)
    if type(value) is int and abs(value) > 9007199254740991:
        raise ValueError('Preview integer exceeds the Qt JSON safe range.')
    if isinstance(value, list):
        return [canonical_json(item) for item in value]
    if isinstance(value, dict):
        return {key: canonical_json(item) for key, item in value.items()}
    return value


def digest(value):
    return hashlib.sha256(json.dumps(canonical_json(value), sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def positive(value, high=100000):
    if type(value) is not int or not 0 < value <= high:
        raise ValueError('Expected a positive integer.')
    return value


def public(value, limit):
    if not isinstance(value, str) or not value or len(value) > limit or bridge.APP.sub('', value) != value:
        raise ValueError('Expected a public app identity.')
    return value


def app_role(window, prefs):
    key = window['class'].lower()
    if key in prefs['rules']:
        return prefs['rules'][key]
    for role, identities in KNOWN.items():
        if key in identities:
            return role
    categories = window.get('desktopCategories', [])
    if 'WebBrowser' in categories or BROWSER.fullmatch(key):
        return 'mixed'
    roles = {CATEGORIES[c] for c in categories if c in CATEGORIES}
    return next(iter(roles)) if len(roles) == 1 else 'mixed'


def district_role(windows, prefs):
    distinct = {w['class'].lower(): w for w in windows}
    votes = Counter(app_role(w, prefs) for w in distinct.values())
    strong = Counter()
    for key, window in distinct.items():
        role = app_role(window, prefs)
        if role not in ('mixed', 'system') or key in prefs['rules']:
            strong[role] += 1
    if strong:
        best, count = strong.most_common(1)[0]
        return best if count > sum(strong.values()) / 2 else 'mixed'
    return 'system' if votes['system'] else 'mixed'


def window_identity(window):
    pid = window.get('pid')
    if pid is not None:
        positive(pid, 2147483647)
    return {'address': window['address'], 'class': window['class'], 'pid': pid}


def canonical_windows(windows):
    return sorted([window_identity(w) for w in windows], key=lambda w: w['address'])



def preview_protection(district):
    wid = district['id']
    custom = district.get('customName', '')
    if not isinstance(custom, str):
        raise ValueError('Invalid district name metadata.')
    custom = bridge.label(custom)
    named = district.get('autoSource') == 'workspace'
    workspace_name = district.get('autoName', '') if named else str(wid)
    if not isinstance(workspace_name, str):
        raise ValueError('Invalid workspace name metadata.')
    return {'customName': custom, 'pinned': bool(district.get('pinned')),
            'workspaceNamed': named, 'workspaceName': workspace_name}


def current_protection(workspace, state):
    wid = workspace['id']
    key = str(wid)
    name = str(workspace.get('name', key)).strip()
    # Missing/empty or ordinary numeric labels are the same unprotected identity.
    name = name or key
    return {'customName': state.get('names', {}).get(key, ''),
            'pinned': key in state.get('pins', []),
            'workspaceNamed': name != key, 'workspaceName': name}


def preview(snapshot, now=None):
    """Pure function: generates a plan, without querying or changing the desktop."""
    now = time.time() if now is None else now
    if not isinstance(snapshot, dict) or snapshot.get('truncated'):
        raise ValueError('A complete current city snapshot is required.')
    raw_districts, raw_windows = snapshot.get('districts'), snapshot.get('windows')
    if not isinstance(raw_districts, list) or not isinstance(raw_windows, list) or len(raw_districts) > bridge.LIMIT or len(raw_windows) > bridge.LIMIT:
        raise ValueError('A bounded city snapshot is required.')
    prefs = bridge.grouping(snapshot.get('grouping'))
    districts, windows, omitted = {}, [], 0
    for district in raw_districts:
        try:
            wid = positive(district['id'])
            monitor = district['monitor']
            if type(monitor) is not int or not 0 <= monitor < 32 or wid in districts:
                raise ValueError('Unsupported district.')
            districts[wid] = {**district, 'monitor': monitor}
        except (KeyError, TypeError, ValueError):
            omitted += 1
    addresses = set()
    for window in raw_windows:
        try:
            address = window['address']
            if not isinstance(address, str) or not bridge.ADDRESS.fullmatch(address) or address in addresses:
                raise ValueError('Invalid or duplicate window.')
            wid = positive(window['workspace'])
            if wid not in districts or window.get('mapped') is False or window.get('hidden') is True:
                raise ValueError('Unsupported window.')
            app_class = public(window['class'], 96)
            # Public desktop names are bounded; no client titles enter this contract.
            app = public(window.get('app', app_class), 64)
            categories = window.get('desktopCategories', [])
            if not isinstance(categories, list):
                categories = []
            safe = {'address': address, 'workspace': wid, 'class': app_class, 'app': app,
                    'pid': window.get('pid'), 'focused': bool(window.get('focused')) or address == snapshot.get('focused'),
                    'desktopCategories': [c for c in categories if isinstance(c, str) and c in CATEGORIES or c == 'WebBrowser']}
            window_identity(safe)
            addresses.add(address)
            windows.append(safe)
        except (KeyError, TypeError, ValueError):
            omitted += 1
    by_workspace = defaultdict(list)
    by_app = defaultdict(list)
    for window in windows:
        by_workspace[window['workspace']].append(window)
        by_app[window['class'].lower()].append(window)
    protected = {wid for wid, d in districts.items() if d.get('pinned') or d.get('customName') or d.get('nameSource') == 'custom' or d.get('autoSource') == 'workspace'}
    roles = {wid: district_role(ws, prefs) for wid, ws in by_workspace.items()}
    moves = []
    deferred = 0
    for app_class in sorted(by_app):
        app_windows = by_app[app_class]
        role = app_role(app_windows[0], prefs)
        if role == 'mixed':
            continue
        counts = Counter(w['workspace'] for w in app_windows if w['workspace'] not in protected and roles.get(w['workspace']) == role)
        if not counts:
            continue
        destination = min(counts, key=lambda wid: (-counts[wid], wid))
        for window in sorted(app_windows, key=lambda w: (w['workspace'], w['address'])):
            source = window['workspace']
            if source == destination or source in protected or window['focused']:
                continue
            if len(moves) >= MAX_MOVES:
                deferred += 1
                continue
            moves.append({'address': window['address'], 'app': window['app'], 'appClass': window['class'], 'pid': window['pid'],
                          'sourceWorkspace': source, 'destinationWorkspace': destination,
                          'sourceMonitor': districts[source]['monitor'], 'destinationMonitor': districts[destination]['monitor'],
                          'sourceName': 'D' + str(source), 'destinationName': 'D' + str(destination),
                          'sourceCount': len(by_workspace[source]), 'destinationCount': len(by_workspace[destination]),
                          'category': role, 'reason': 'Consolidate this public app with ' + str(counts[destination]) + ' matching window(s) in an existing ' + role + ' district.'})
    affected = sorted({m[key] for m in moves for key in ('sourceWorkspace', 'destinationWorkspace')})
    anchors = [{'id': wid, 'monitor': districts[wid]['monitor'], 'windows': canonical_windows(by_workspace[wid]), 'protection': preview_protection(districts[wid])} for wid in affected]
    deltas = Counter()
    for move in moves:
        deltas[move['sourceWorkspace']] -= 1
        deltas[move['destinationWorkspace']] += 1
    summaries = [{'workspace': wid, 'before': len(by_workspace[wid]), 'after': len(by_workspace[wid]) + deltas[wid]} for wid in affected]
    for move in moves:
        move['sourceAfter'] = len(by_workspace[move['sourceWorkspace']]) + deltas[move['sourceWorkspace']]
        move['destinationAfter'] = len(by_workspace[move['destinationWorkspace']]) + deltas[move['destinationWorkspace']]
    plan = {'schema': 1, 'createdAt': now, 'expiresAt': now + TTL, 'groupingDigest': digest(prefs),
            'moves': moves, 'districts': anchors, 'summaries': summaries, 'omitted': omitted, 'deferred': deferred,
            'protectedDistricts': len(protected), 'policy': 'Existing districts only. Named/pinned districts, mixed/unknown apps and focused windows stay. Every affected district is checked before each move. No automatic undo.'}
    plan['planId'] = digest(plan)
    return {'ok': True, 'plan': plan}


def validate_plan(plan, accepted, now):
    if not isinstance(plan, dict) or plan.get('schema') != 1 or not isinstance(plan.get('planId'), str):
        raise ValueError('Invalid organization preview.')
    plan_id = plan['planId']
    if accepted != plan_id or digest({k: v for k, v in plan.items() if k != 'planId'}) != plan_id:
        raise ValueError('Apply requires the exact accepted preview. Preview again.')
    created, expires = plan.get('createdAt'), plan.get('expiresAt')
    if type(created) not in (int, float) or type(expires) not in (int, float) or not math.isfinite(created) or not math.isfinite(expires) or expires - created != TTL or now < created - 5 or now >= expires:
        raise ValueError('The preview expired. Preview again.')
    moves, anchors = plan.get('moves'), plan.get('districts')
    if not isinstance(moves, list) or len(moves) > MAX_MOVES or not isinstance(anchors, list) or len(anchors) > MAX_MOVES * 2:
        raise ValueError('The preview is out of bounds.')
    seen = set()
    expected = {}
    for anchor in anchors:
        wid = positive(anchor['id'])
        monitor = anchor['monitor']
        identities = anchor['windows']
        if wid in expected or type(monitor) is not int or not 0 <= monitor < 32 or not isinstance(identities, list) or len(identities) > bridge.LIMIT:
            raise ValueError('Invalid preview district.')
        for identity in identities:
            if not bridge.ADDRESS.fullmatch(identity['address']):
                raise ValueError('Invalid preview address.')
            public(identity['class'], 96)
            window_identity(identity)
        if len({w['address'] for w in identities}) != len(identities):
            raise ValueError('Duplicate preview identity.')
        protection = anchor.get('protection')
        unprotected = {'customName': '', 'pinned': False, 'workspaceNamed': False, 'workspaceName': str(wid)}
        if protection != unprotected or type(protection.get('pinned')) is not bool or type(protection.get('workspaceNamed')) is not bool:
            raise ValueError('A protected or unknown district cannot be organized. Preview again.')
        expected[wid] = {'monitor': monitor, 'windows': canonical_windows(identities), 'protection': dict(protection)}
    for move in moves:
        address = move['address']
        if not isinstance(address, str) or not bridge.ADDRESS.fullmatch(address) or address in seen:
            raise ValueError('Invalid or duplicate preview address.')
        seen.add(address)
        public(move['appClass'], 96)
        public(move['app'], 64)
        window_identity({'address': address, 'class': move['appClass'], 'pid': move['pid']})
        source, destination = positive(move['sourceWorkspace']), positive(move['destinationWorkspace'])
        if source == destination or source not in expected or destination not in expected or expected[source]['monitor'] != move['sourceMonitor'] or expected[destination]['monitor'] != move['destinationMonitor']:
            raise ValueError('Invalid preview route.')
        identity = {'address': address, 'class': move['appClass'], 'pid': move['pid']}
        if identity not in expected[source]['windows']:
            raise ValueError('Preview target is not in its original district.')
    return expected


def live_identity(client):
    return {'address': client.get('address'), 'class': bridge.APP.sub('', str(client.get('class', '')))[:96] or 'Application',
            'pid': client.get('pid') if type(client.get('pid')) is int and 0 < client['pid'] <= 2147483647 else None}


def check_current(expected, move, grouping_digest):
    """Queries are deliberately fresh for each explicitly approved move."""
    workspaces = bridge.query('workspaces')
    clients = bridge.query('clients')
    if not isinstance(workspaces, list) or not isinstance(clients, list) or len(clients) > bridge.LIMIT:
        raise ValueError('The current desktop snapshot is incomplete.')
    active = bridge.query('activewindow')
    # Read architecture metadata after compositor queries, immediately before dispatch.
    state = bridge.read_state(bridge.state_path())
    if digest(bridge.grouping(state.get('grouping'))) != grouping_digest:
        raise ValueError('Your grouping preferences changed. Preview again.')
    for wid, anchor in expected.items():
        matching = [w for w in workspaces if w.get('id') == wid]
        if len(matching) != 1 or matching[0].get('monitorID') != anchor['monitor']:
            raise ValueError('An affected district disappeared or changed monitor. Preview again.')
        if current_protection(matching[0], state) != anchor['protection']:
            raise ValueError('An affected district name or pin changed after preview. Preview again.')
        current = [live_identity(c) for c in clients if c.get('workspace', {}).get('id') == wid and c.get('mapped') is not False and c.get('hidden') is not True]
        if sorted(current, key=lambda c: str(c['address'])) != anchor['windows']:
            raise ValueError('An affected district changed after preview. Preview again.')
    matches = [c for c in clients if c.get('address') == move['address'] and c.get('mapped') is not False and c.get('hidden') is not True]
    if len(matches) != 1 or live_identity(matches[0]) != {'address': move['address'], 'class': move['appClass'], 'pid': move['pid']} or matches[0].get('workspace', {}).get('id') != move['sourceWorkspace']:
        raise ValueError('The approved window changed. Preview again.')
    if not isinstance(active, dict) or active.get('address') == move['address']:
        raise ValueError('A focused window is protected. Preview again after switching focus.')


def apply(plan, accepted, now=None):
    """Apply only the exact accepted plan; stop on the first stale/error result."""
    now = time.time() if now is None else now
    started = time.monotonic()
    expected = validate_plan(plan, accepted, now)
    receipt = {'schema': 1, 'planId': plan['planId'], 'ok': False, 'applied': 0, 'total': len(plan['moves']),
               'stopped': False, 'items': [], 'message': '', 'completedAt': None}
    moves = plan['moves']
    try:
        if not bridge.lua_supported():
            raise ValueError('Organization requires the supported scoped Lua move API.')
        if digest(bridge.grouping(bridge.read_state(bridge.state_path()).get('grouping'))) != plan['groupingDigest']:
            raise ValueError('Your grouping preferences changed. Preview again.')
        for index, move in enumerate(moves):
            dispatched = False
            try:
                if now + time.monotonic() - started >= plan['expiresAt']:
                    raise ValueError('The preview expired before this move. Preview again.')
                # Re-read preferences too: apply never silently ignores a custom rule edit.
                if digest(bridge.grouping(bridge.read_state(bridge.state_path()).get('grouping'))) != plan['groupingDigest']:
                    raise ValueError('Your grouping preferences changed. Preview again.')
                check_current(expected, move, plan['groupingDigest'])
                lua = 'hl.dsp.window.move({ workspace = "' + str(move['destinationWorkspace']) + '", window = "address:' + move['address'] + '", follow = false })'
                dispatched = True
                if bridge.command(['dispatch', lua]).strip() != 'ok':
                    raise RuntimeError('The compositor did not confirm this move; refresh before further actions.')
                after = [c for c in bridge.query('clients') if c.get('address') == move['address']]
                if len(after) != 1 or live_identity(after[0]) != {'address': move['address'], 'class': move['appClass'], 'pid': move['pid']} or after[0].get('workspace', {}).get('id') != move['destinationWorkspace']:
                    raise RuntimeError('Move outcome is unconfirmed; refresh before further actions.')
                identity = {'address': move['address'], 'class': move['appClass'], 'pid': move['pid']}
                expected[move['sourceWorkspace']]['windows'].remove(identity)
                expected[move['destinationWorkspace']]['windows'].append(identity)
                expected[move['destinationWorkspace']]['windows'].sort(key=lambda w: w['address'])
                # Hyprland may retire a workspace emptied by this approved move.
                # Only retire its guard after all of its planned routes are done.
                source = move['sourceWorkspace']
                if not expected[source]['windows'] and not any(source in (later['sourceWorkspace'], later['destinationWorkspace']) for later in moves[index + 1:]):
                    del expected[source]
                receipt['applied'] += 1
                receipt['items'].append({'app': move['app'], 'sourceWorkspace': move['sourceWorkspace'], 'destinationWorkspace': move['destinationWorkspace'], 'status': 'applied', 'message': 'Move confirmed.'})
            except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                receipt['stopped'] = True
                receipt['items'].append({'app': move['app'], 'sourceWorkspace': move['sourceWorkspace'], 'destinationWorkspace': move['destinationWorkspace'], 'status': 'unconfirmed' if dispatched else 'blocked', 'message': str(error)})
                for rest in moves[index + 1:]:
                    receipt['items'].append({'app': rest['app'], 'sourceWorkspace': rest['sourceWorkspace'], 'destinationWorkspace': rest['destinationWorkspace'], 'status': 'not-attempted', 'message': 'Stopped after the preceding result.'})
                receipt['message'] = str(error)
                break
        else:
            receipt['ok'] = True
            receipt['message'] = str(receipt['applied']) + ' move(s) confirmed. Your focus was not requested to change.'
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        receipt['stopped'] = True
        receipt['message'] = str(error)
        receipt['items'] = [{'app': m['app'], 'sourceWorkspace': m['sourceWorkspace'], 'destinationWorkspace': m['destinationWorkspace'], 'status': 'not-attempted', 'message': str(error)} for m in moves]
    receipt['completedAt'] = time.time()
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('preview')
    action = sub.add_parser('apply')
    action.add_argument('--accept', required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.readline(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError('Organization input is too large.')
        payload = json.loads(raw)
        result = preview(payload) if args.action == 'preview' else apply(payload, args.accept)
        print(json.dumps(result, separators=(',', ':')))
        return 0 if result.get('ok') else 1
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
