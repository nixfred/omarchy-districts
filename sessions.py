#!/usr/bin/env python3
"""Exact local agent sessions. Inventory is metadata-only; reply reads are opt-in.

Codex transport is the documented Unix WebSocket app-server API. No daemon is
started, thread resumed, terminal input injected, or permission policy changed.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import stat
import struct
import subprocess
import time
import uuid

UUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
MAX_FRAME = 8 * 1024 * 1024
MAX_REPLY = 65536
LIMIT = 128


def ident(value):
    if not isinstance(value, str) or not UUID.fullmatch(value):
        raise ValueError('Select an exact session UUID.')
    return value.lower()


def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


class CodexRpcError(RuntimeError):
    """Expose only numeric protocol code, never provider response contents."""
    def __init__(self, code, message=""):
        low = message.lower() if isinstance(message, str) else ""
        self.category = ("method-unavailable" if code == -32601 else
            "session-unavailable" if any(word in low for word in ("not found", "notfound", "unknown thread", "no such", "does not exist")) else
            "validation-or-provider-error")
        self.code = code if type(code) is int else None
        super().__init__('Codex CLI rejected this request (code %s).' % (self.code if self.code is not None else '?'))


class CodexConnection:
    """Bounded RFC6455 local client, owner-only socket; never handles approvals."""
    def __init__(self, home=None, timeout=4):
        self.path = Path(home or Path.home() / '.codex') / 'app-server-control/app-server-control.sock'
        self.timeout = timeout
        self.socket = None
        self.serial = 0

    def __enter__(self):
        info = self.path.stat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise RuntimeError('Codex control socket must be an existing owner-only local socket.')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(self.timeout)
        try:
            self.socket.connect(str(self.path))
            key = base64.b64encode(os.urandom(16)).decode()
            request = ('GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n'
                       'Connection: Upgrade\r\nSec-WebSocket-Key: ' + key + '\r\n'
                       'Sec-WebSocket-Version: 13\r\n\r\n')
            self.socket.sendall(request.encode())
            headers = bytearray()
            while not headers.endswith(b'\r\n\r\n'):
                headers.extend(self._read(1))
                if len(headers) > 16384:
                    raise RuntimeError('Invalid Codex handshake.')
            lines = headers.decode('ascii').split('\r\n')
            fields = {k.lower(): v.strip() for k, v in (line.split(':', 1) for line in lines[1:] if ':' in line)}
            accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
            if ' 101 ' not in lines[0] or fields.get('sec-websocket-accept') != accept:
                raise RuntimeError('Codex rejected the local connection; no authentication fallback attempted.')
            self.call('initialize', {'clientInfo': {'name': 'districts', 'title': 'Districts', 'version': '1'},
                                     'capabilities': {'experimentalApi': True}})
            self._send({'method': 'initialized', 'params': {}})
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.socket:
            self.socket.close()
            self.socket = None

    def _read(self, count):
        result = bytearray()
        while len(result) < count:
            chunk = self.socket.recv(count - len(result))
            if not chunk:
                raise RuntimeError('Codex disconnected. Do not retry an uncertain send automatically.')
            result.extend(chunk)
        return bytes(result)

    def _frame(self, payload, opcode=1):
        if len(payload) > MAX_FRAME:
            raise ValueError('Message exceeds the local transport limit.')
        mask = os.urandom(4)
        n = len(payload)
        header = bytes([0x80 | opcode, 0x80 | n]) if n < 126 else (
            bytes([0x80 | opcode, 254]) + struct.pack('!H', n) if n <= 65535 else
            bytes([0x80 | opcode, 255]) + struct.pack('!Q', n))
        self.socket.sendall(header + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(payload)))

    def _send(self, message):
        self._frame(json.dumps(message, separators=(',', ':'), ensure_ascii=False).encode())

    def _receive(self):
        payload = bytearray()
        started = False
        while True:
            a, b = self._read(2)
            opcode = a & 15
            size = b & 127
            if a & 0x70 or b & 0x80:
                raise RuntimeError('Unsupported Codex WebSocket frame.')
            if size == 126:
                size = struct.unpack('!H', self._read(2))[0]
            elif size == 127:
                size = struct.unpack('!Q', self._read(8))[0]
            if size > MAX_FRAME or len(payload) + size > MAX_FRAME:
                raise RuntimeError('Codex response exceeds the local read limit.')
            data = self._read(size)
            if opcode == 8:
                raise RuntimeError('Codex closed this connection.')
            if opcode == 9:
                if size > 125:
                    raise RuntimeError('Invalid Codex ping.')
                self._frame(data, 10)
                continue
            if opcode == 10:
                continue
            if opcode == 1 and not started:
                started = True
            elif opcode != 0 or not started:
                raise RuntimeError('Unexpected Codex response frame.')
            payload.extend(data)
            if a & 0x80:
                result = json.loads(payload)
                if not isinstance(result, dict):
                    raise RuntimeError('Invalid Codex response.')
                return result

    def call(self, method, params):
        self.serial += 1
        request_id = self.serial
        self._send({'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + self.timeout
        for _ in range(512):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Codex response timed out; no automatic resend.')
            self.socket.settimeout(remaining)
            response = self._receive()
            # Never answer server requests: existing client owns approval UI.
            if response.get('id') == request_id and 'method' not in response:
                if 'error' in response:
                    raise CodexRpcError(response['error'].get('code'), response['error'].get('message'))
                return response.get('result', {})
        raise RuntimeError('Codex sent too many notifications for this bounded read.')


def codex_record(thread, loaded=False):
    sid = ident(thread.get('id'))
    parent = thread.get('parentThreadId')
    source = thread.get('source')
    if not parent and isinstance(source, dict):
        sub = source.get('subAgent', source.get('subagent', {}))
        if isinstance(sub, dict) and isinstance(sub.get('thread_spawn'), dict):
            parent = sub['thread_spawn'].get('parent_thread_id')
    parent = ident(parent) if parent else None
    status = thread.get('status') if isinstance(thread.get('status'), dict) else {'type': 'unknown'}
    status = {'type': str(status.get('type', 'unknown'))[:32],
              'activeFlags': [s for s in status.get('activeFlags', []) if s in ('waitingOnApproval', 'waitingOnUserInput')]}
    pending = bool((thread.get('status') or {}).get('activeFlags')) if isinstance(thread.get('status'), dict) else True
    live = loaded and status['type'] != 'notLoaded'
    direct = live and status['type'] in ('idle', 'active') and thread.get('canAcceptDirectInput') is True
    return {'id': sid, 'provider': 'codex', 'key': 'agent:codex:' + sid,
            'parentId': parent, 'familyId': ident(thread.get('sessionId', sid)),
            'label': 'Codex CLI ' + sid[:8], 'status': status,
            'statusSource': 'Codex CLI daemon thread/read', 'observedAt': stamp(),
            'availability': 'live' if live else 'stored', 'sessionScope': 'local-cli-daemon',
            'capabilities': {'canReadReply': True, 'canReadHistory': True, 'canSend': direct and not pending,
                             'canOpen': False, 'approvalPolicy': 'existing-session-unchanged',
                             'approvalPending': 'waitingOnApproval' in status['activeFlags'],
                             'reason': 'Answer approval/question in the native client.' if pending else
                             'Exact existing CLI queue; queued does not mean completed. Approvals stay in its CLI client.' if direct else 'Only a loaded thread accepting direct input can receive instructions.'}}


def inventory_notice(notices, provider, code, reason):
    if notices is not None:
        notice = {'provider': provider, 'code': code, 'reason': reason}
        if notice not in notices:
            notices.append(notice)


def codex_inventory(connection, notices=None):
    result = connection.call('thread/loaded/list', {'limit': LIMIT})
    loaded_data = result.get('data', [])
    bounded = len(loaded_data) >= LIMIT or bool(result.get('nextCursor'))
    if bounded:
        inventory_notice(notices, 'codex', 'inventory-bound-reached',
                         'Loaded CLI session inventory is limited to 128 records or one page; additional sessions may be omitted.')
    loaded = [ident(v) for v in loaded_data[:LIMIT]]
    rows = {}
    for sid in loaded:
        thread = connection.call('thread/read', {'threadId': sid, 'includeTurns': False}).get('thread', {})
        rows[sid] = codex_record(thread, True)
    # Recent interactive metadata plus authoritative recorded spawn edges. Generic
    # guardian/compaction helpers are not invented into semantic child agents.
    result = connection.call('thread/list', {'limit': 32, 'sortKey': 'updated_at',
        'sourceKinds': ['cli', 'vscode', 'exec', 'appServer'], 'useStateDbOnly': True})
    if len(result.get('data', [])) >= 32 or result.get('nextCursor'):
        bounded = True
        inventory_notice(notices, 'codex', 'inventory-bound-reached',
                         'Recent CLI session inventory is limited to 32 records or one page; additional stored sessions may be omitted.')
    for thread in result.get('data', [])[:32]:
        try:
            row = codex_record(thread, thread.get('id') in loaded)
            rows.setdefault(row['id'], row)
        except (ValueError, TypeError):
            continue
    ancestry_notices = []
    for item in spawn_metadata(notices=ancestry_notices):
        for sid in (item['id'], item['parentId']):
            if sid in rows:
                continue
            try:
                thread = connection.call('thread/read', {'threadId': sid, 'includeTurns': False}).get('thread', {})
                rows[sid] = codex_record(thread, sid in loaded)
            except (RuntimeError, ValueError):
                rows[sid] = {'id': sid, 'provider': 'codex', 'key': 'agent:codex:' + sid,
                    'parentId': None, 'familyId': sid, 'label': 'Codex CLI ' + sid[:8],
                    'status': {'type': 'notLoaded', 'activeFlags': []},
                    'statusSource': 'Codex CLI stored spawn record; live status unavailable',
                    'observedAt': stamp(), 'availability': 'stored',
                    'capabilities': {'canReadReply': False, 'canSend': False, 'canOpen': False,
                        'approvalPolicy': 'existing-session-unchanged', 'approvalPending': False,
                        'reason': 'Stored spawn record; no loaded session status.'}}
        rows[item['id']]['parentId'] = item['parentId']
        rows[item['id']]['parentSource'] = item['source']
    assign_families(rows)
    for notice in ancestry_notices:
        inventory_notice(notices, notice['provider'], notice['code'], notice['reason'])
    if len(rows) > LIMIT:
        inventory_notice(notices, 'codex', 'inventory-truncated',
                         'Combined CLI session inventory exceeds 128 records; some session or parent records were omitted.')
    return list(rows.values())[:LIMIT], bounded or bool(ancestry_notices) or len(rows) > LIMIT


def spawn_metadata(home=None, notices=None):
    """Read only explicit session edges; never transcripts or process ancestry."""
    path = Path(home or Path.home() / '.codex') / 'state_5.sqlite'
    rows = {}
    try:
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=.3) as db:
            edges = db.execute('SELECT parent_thread_id,child_thread_id FROM thread_spawn_edges LIMIT 33').fetchall()
            sources = db.execute("SELECT id,source FROM threads WHERE source LIKE '%thread_spawn%' ORDER BY updated_at DESC LIMIT 33").fetchall()
            if len(edges) >= 32 or len(sources) >= 32:
                inventory_notice(notices, 'codex', 'ancestry-bound-reached',
                                 'Stored CLI parent metadata reached its 32-record source bound; family relationships may be incomplete.')
            for parent, child in edges[:32]:
                rows[ident(child)] = {'id': ident(child), 'parentId': ident(parent), 'source': 'Codex state DB thread_spawn_edges'}
            for sid, source in sources[:32]:
                try:
                    sub = json.loads(source).get('subagent', {})
                    parent = sub.get('thread_spawn', {}).get('parent_thread_id')
                    if parent:
                        rows.setdefault(ident(sid), {'id': ident(sid), 'parentId': ident(parent),
                            'source': 'Codex stored SessionSource.thread_spawn'})
                except (ValueError, TypeError, AttributeError):
                    continue
    except (OSError, sqlite3.Error, ValueError):
        return []
    if len(rows) > 32:
        inventory_notice(notices, 'codex', 'ancestry-truncated',
                         'Combined CLI parent metadata exceeds 32 records; some verified relationships were omitted.')
    return list(rows.values())[:32]


def assign_families(rows):
    for sid, record in rows.items():
        current = sid; seen = set()
        for _ in range(32):
            if current in seen:
                record['familyId'] = sid
                record['parentId'] = None
                record['parentSource'] = 'Invalid cyclic provider ancestry omitted'
                break
            seen.add(current)
            parent = rows.get(current, {}).get('parentId')
            if not parent:
                record['familyId'] = current
                break
            current = parent
        else:
            record['familyId'] = sid


def provider_status(provider, reason):
    return {'provider': provider, 'canSend': False, 'reason': reason}


def claude_inventory(runner=subprocess.run, notices=None):
    result = runner(['claude', 'agents', '--json'], capture_output=True, text=True, timeout=5, check=False)
    if result.returncode or len(result.stdout) > MAX_FRAME:
        raise RuntimeError('Claude read-only inventory unavailable.')
    records = json.loads(result.stdout)
    if not isinstance(records, list):
        raise ValueError('Invalid Claude inventory.')
    if len(records) >= LIMIT:
        inventory_notice(notices, 'claude', 'inventory-bound-reached',
                         'Claude session inventory reached its 128-record bound; additional sessions may be omitted.')
    rows = []
    for item in records[:LIMIT]:
        try:
            sid = ident(item.get('sessionId'))
        except ValueError:
            continue
        rows.append({'id': sid, 'provider': 'claude', 'key': 'agent:claude:' + sid,
                     'parentId': None, 'familyId': sid, 'label': 'Claude ' + sid[:8],
                     'status': {'type': str(item.get('state', 'unknown'))[:32], 'activeFlags': []},
                     'statusSource': 'Claude agents --json', 'observedAt': stamp(), 'availability': 'live',
                     'capabilities': {'canReadReply': True, 'canReadHistory': True, 'canSend': False, 'canOpen': False,
                                      'approvalPolicy': 'existing-session-unchanged', 'approvalPending': None,
                                      'reason': 'Existing Claude sessions are read-only here; no supported same-process instruction API verified. Parentage unavailable.'}})
    return rows


def provider_groups(extra_factories=None):
    if extra_factories is not None:
        return extra_factories
    from provider_claude import subagent_inventory
    from provider_pi import inventory_pi
    from provider_grok import inventory as grok_inventory
    return extra_factories or (subagent_inventory, inventory_pi, grok_inventory)


def fair_sessions(groups, limit=LIMIT):
    """Preserve representation for each observed provider under aggregate cap."""
    pending = [sorted(group, key=lambda r: (r.get('availability') != 'live', bool(r.get('parentId')))) for group in groups]
    rows = []; seen = set()
    while any(pending) and len(rows) < limit:
        for group in pending:
            if not group or len(rows) >= limit:
                continue
            row = group.pop(0); key = (row.get('provider'), row.get('id'))
            if key not in seen:
                seen.add(key); rows.append(row)
    return rows, any(pending)


def inventory(connection_factory=CodexConnection, extra_factories=None):
    groups = []; providers = []; notices = []; bounded = False
    try:
        with connection_factory() as connection:
            found, bounded = codex_inventory(connection, notices=notices)
            groups.append(found)
            providers.append({'provider': 'codex', 'canSend': any(r['capabilities']['canSend'] for r in found),
                'canMonitorLive': True, 'canReadReply': True, 'canReadHistory': True, 'canReadParent': True,
                'reason': 'Codex CLI exact loaded-thread queue where available; existing approvals stay in its CLI client.'})
    except (OSError, RuntimeError, TimeoutError, ValueError):
        groups.append([])
        providers.append(provider_status('codex', 'Existing local daemon unavailable. Districts does not start or resume it.'))
    claude_rows = []
    try:
        claude_rows = claude_inventory(notices=notices)
        providers.append({'provider': 'claude', 'canSend': False, 'canMonitorLive': True,
            'canReadReply': True, 'canReadHistory': True, 'canReadParent': False,
            'reason': 'Native live main-session inventory and stored assistant/subagent history; immediate child parentage and same-process instruction API are unavailable.'})
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        providers.append(provider_status('claude', 'Live inventory unavailable. Stored history may remain available; no resume or terminal injection fallback.'))
    children_factory, pi_factory, grok_factory = provider_groups(extra_factories)
    try:
        claude_rows.extend(children_factory(existing=claude_rows, notices=notices))
    except (OSError, RuntimeError, ValueError):
        inventory_notice(notices, 'claude', 'metadata-unavailable', 'Stored Claude subagent metadata is unavailable within its safe read bounds.')
    groups.append(claude_rows)
    try:
        pi_result = pi_factory()
        groups.append(pi_result['sessions']); notices.extend(pi_result['notices'])
        bounded = bounded or pi_result['bounded']; providers.append(pi_result['provider'])
        kimi_rows = [r for r in pi_result['sessions'] if r.get('isKimi3')]
        providers.append({'provider': 'kimi', 'canSend': False, 'canMonitorLive': False,
            'canReadReply': bool(kimi_rows), 'canReadHistory': bool(kimi_rows), 'canReadParent': False,
            'reason': 'Kimi3 via Pi saved-session history where explicitly recorded; no live attach transport. No matching saved session was found.' if not kimi_rows else 'Kimi3 via Pi saved-session history; no verified live attach transport or semantic subagent parentage.'})
    except (OSError, RuntimeError, ValueError):
        groups.append([])
        providers.append(provider_status('pi', 'Pi saved-session metadata unavailable; no process is started.'))
        providers.append(provider_status('kimi', 'Kimi3 via Pi saved-session metadata unavailable; no process is started.'))
    try:
        grok_rows = grok_factory(notices=notices); groups.append(grok_rows)
        providers.append({'provider': 'grok', 'canSend': False, 'canMonitorLive': False,
            'canReadReply': any(r.get('capabilities', {}).get('canReadReply') for r in grok_rows), 'canReadHistory': any(r.get('capabilities', {}).get('canReadHistory') for r in grok_rows), 'canReadParent': True,
            'reason': 'Stored Grok metadata, explicit child records and selected assistant history. Live ownership/state and existing-process instructions are unavailable; no resume fallback.'})
    except (OSError, RuntimeError, ValueError):
        groups.append([])
        providers.append(provider_status('grok', 'Stored Grok metadata unavailable within its read bounds; no process is started.'))
    unsupported = [provider_status('codex-desktop', 'Desktop app task inventory, replies and instructions are unavailable to this external plugin: no published supported runtime interface verified. CLI sessions are a separate namespace.'),
        provider_status('herdr', 'This application is outside a Herdr-managed pane; installed Herdr skill prohibits external session control.'),
        provider_status('kimi-native', 'Native Kimi ACP starts its own protocol process. Kimi3 via Pi is separately recognized from actual saved model metadata; neither is silently resumed.')]
    providers.extend(unsupported)
    for provider in providers:
        if not provider['canSend']:
            inventory_notice(notices, provider['provider'], 'provider-limit', provider['reason'])
    rows, aggregate_bound = fair_sessions(groups)
    if aggregate_bound:
        inventory_notice(notices, 'all', 'inventory-truncated',
                         'Combined provider inventory exceeds 128 records; each observed provider is represented but additional sessions or parents were omitted.')
    return {'ok': True, 'sessions': rows, 'providers': providers,
            'unsupportedProviders': unsupported, 'notices': notices,
            'bounded': bounded or aggregate_bound or any('bound' in n['code'] or 'truncated' in n['code'] for n in notices),
            'observedAt': stamp(), 'scope': 'local-provider-session-records',
            'privacy': 'Metadata inventory omits titles, prompts, replies, paths, and PID guesses.'}


def metrics(connection_factory=CodexConnection, collector=None, now_ms=None):
    from provider_metrics import collect, record, number, normalize_window
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    result = (collector or collect)(now_ms=now_ms)
    # Existing daemon owns authentication. Never read tokens or send account,
    # reset-credit, permission, model or approval mutation methods.
    try:
        with connection_factory() as connection:
            response = connection.call('account/rateLimits/read', {})
        if not isinstance(response, dict):
            raise ValueError('Invalid quota metadata response.')
        groups = response.get('rateLimitsByLimitId')
        groups = groups.values() if isinstance(groups, dict) and groups else [response.get('rateLimits', {})]
        rows = []; seen = set()
        for group in groups:
            if not isinstance(group, dict):
                continue
            for key in ('primary', 'secondary'):
                window = group.get(key)
                if not isinstance(window, dict):
                    continue
                used, minutes, reset = (number(window.get(k)) for k in ('usedPercent', 'windowDurationMins', 'resetsAt'))
                if used is None or not 0 <= used <= 100:
                    continue
                signature = (used, minutes, reset)
                if signature in seen:
                    continue
                seen.add(signature)
                row = {'label': 'Codex quota window ' + str(len(rows) + 1), 'percent': used / 100}
                if reset is not None and reset > 0:
                    row['resetsAt'] = reset * 1000
                if minutes is not None and minutes > 0:
                    row['durationMs'] = minutes * 60000
                rows.append(row)
        # The transport already bounds the whole response to 8 MiB. Consider every
        # valid unique window before the eight-row display cap, so later buckets
        # cannot hide the most-behind pace or the number of omitted windows.
        def urgency(row):
            window = normalize_window(row, measured_at=now_ms, source='Codex quota observation', now_ms=now_ms)
            credit = number(window['pace'].get('signedSeconds'))
            return (0, credit) if credit is not None else (1, 0 if window['state'] == 'measured' else 1)
        rows.sort(key=urgency)
        fresh = record('codex', {'limits': rows}, source='Codex existing daemon account/rateLimits/read quota observation', now_ms=now_ms, measured_at=now_ms)
        fresh['quotaScope'] = 'Provider account quota; separate from session CPU or progress'
        fresh['ordinaryUsageAllowed'] = response.get('ordinaryUsageAllowed') if type(response.get('ordinaryUsageAllowed')) is bool else None
        result['providers'] = [fresh if r.get('provider') == 'codex' else r for r in result['providers']]
    except (OSError, RuntimeError, TimeoutError, ValueError):
        # An existing supported cache may remain useful; its own measurement stamp
        # controls freshness. Do not restamp it after an unsuccessful provider read.
        for row in result['providers']:
            if row.get('provider') == 'codex':
                row['liveReadUnavailable'] = True
    result['ok'] = True
    return result


def reply_result(sid, item, source, turn_status=None):
    text = item.get('text', '')
    if not isinstance(text, str):
        return None
    return {'ok': True, 'provider': 'codex', 'id': sid, 'text': text[:MAX_REPLY],
            'source': source, 'truncated': len(text) > MAX_REPLY,
            'observedAt': stamp(), 'itemId': item.get('id'), 'phase': item.get('phase'),
            'turnStatus': turn_status, 'sessionScope': 'local-cli-daemon'}


def with_history(sid, items, source, more=False):
    """Assistant-only recent history, newest-first input; bounded shared text RAM."""
    entries = []; budget = MAX_REPLY; truncated = bool(more)
    for item, turn_status in items:
        if not isinstance(item, dict) or item.get('type') != 'agentMessage' or item.get('phase') == 'commentary' or not isinstance(item.get('text'), str) or not item['text']:
            continue
        if len(entries) >= 16 or budget <= 0:
            truncated = True
            break
        text = item['text'][:budget]; budget -= len(text)
        truncated = truncated or len(text) < len(item['text'])
        entries.append({'text': text, 'itemId': str(item.get('id', ''))[:128], 'role': 'assistant', 'turnStatus': turn_status})
    if not entries:
        return None
    reply = reply_result(sid, {'text': entries[0]['text'], 'id': entries[0]['itemId']}, source, entries[0]['turnStatus'])
    reply.update(history=list(reversed(entries)), truncated=truncated)
    return reply


def reply_from_turns(sid, turns, source, more=False):
    return with_history(sid, ((item, turn.get('status')) for turn in turns if isinstance(turn, dict)
        for item in reversed(turn.get('items', [])) if isinstance(turn.get('items'), list)), source, more)


def latest_codex(connection, sid):
    """Read only selected session, adapting to the actual daemon method set."""
    sid = ident(sid)
    source = 'Selected Codex CLI thread/items/list assistant message'
    try:
        result = connection.call('thread/items/list', {'threadId': sid, 'limit': 64, 'sortDirection': 'desc'})
        reply = with_history(sid, ((wrapper.get('item', wrapper), None) for wrapper in result.get('data', []) if isinstance(wrapper, dict)), source, bool(result.get('nextCursor')))
        if reply:
            return reply
        message = 'No assistant reply in the latest 64 available items.'
    except CodexRpcError as error:
        if error.code != -32601:
            raise
        source = 'Selected Codex CLI thread/turns/list assistant message'
        try:
            result = connection.call('thread/turns/list', {'threadId': sid, 'limit': 4,
                                      'itemsView': 'full', 'sortDirection': 'desc'})
            reply = reply_from_turns(sid, result.get('data', []), source, bool(result.get('nextCursor')))
            if reply:
                return reply
            message = 'No assistant reply in the latest 4 available turns.'
        except CodexRpcError as fallback:
            if fallback.code != -32601:
                raise
            # Older daemons expose full-history read only. The transport rejects
            # any frame/history over 8MiB; no unbounded transcript is retained.
            source = 'Selected Codex CLI thread/read assistant message (8MiB history bound)'
            result = connection.call('thread/read', {'threadId': sid, 'includeTurns': True})
            thread = result.get('thread', {})
            if ident(thread.get('id')) != sid:
                raise ValueError('Codex CLI returned a different reply session identity.')
            reply = reply_from_turns(sid, reversed(thread.get('turns', [])), source)
            if reply:
                return reply
            message = 'No assistant reply in this selected session’s bounded history.'
    return {'ok': True, 'provider': 'codex', 'id': sid, 'text': '', 'truncated': False,
            'source': source, 'observedAt': stamp(), 'message': message,
            'sessionScope': 'local-cli-daemon'}


def latest_claude(sid, home=None):
    from provider_claude import reply
    return reply(sid, home)


def send_codex(connection, sid, text, message_id):
    sid = ident(sid); message_id = ident(message_id)
    if not isinstance(text, str) or not text.strip() or len(text) > 8192 or '\x00' in text:
        raise ValueError('Write an instruction of 1–8192 characters without NUL bytes.')
    loaded = connection.call('thread/loaded/list', {'limit': LIMIT}).get('data', [])
    if sid not in loaded:
        raise ValueError('This exact session is not loaded. Open its native client; no resume fallback.')
    thread = connection.call('thread/read', {'threadId': sid, 'includeTurns': False}).get('thread', {})
    if ident(thread.get('id')) != sid:
        raise ValueError('Codex returned a different session identity.')
    row = codex_record(thread, True)
    if not row['capabilities']['canSend']:
        raise ValueError(row['capabilities']['reason'])
    result = connection.call('thread/queue/add', {'threadId': sid, 'clientUserMessageId': message_id,
                                               'input': [{'type': 'text', 'text': text, 'text_elements': []}]})
    submission = result.get('queuedSubmission')
    submission_id = submission.get('id') if isinstance(submission, dict) else None
    if not isinstance(submission_id, str) or not submission_id.strip():
        raise RuntimeError('Queue acknowledgement unavailable; delivery uncertain. Do not resend automatically.')
    return {'ok': True, 'id': sid, 'provider': 'codex', 'messageId': message_id,
            'queuedSubmissionId': submission_id, 'state': 'queued',
            'message': 'Queued for this exact session; execution/completion is not yet confirmed. Existing approval policy is unchanged.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inventory', 'metrics', 'reply', 'send', 'open'])
    parser.add_argument('--provider', choices=['codex', 'claude', 'grok', 'pi'], default='codex')
    parser.add_argument('--id'); parser.add_argument('--message-id')
    args = parser.parse_args()
    try:
        if args.action == 'inventory':
            result = inventory()
        elif args.action == 'metrics':
            result = metrics()
        elif args.action == 'reply':
            if args.provider == 'claude':
                result = latest_claude(args.id)
            elif args.provider == 'grok':
                from provider_grok import reply
                result = reply(args.id)
            elif args.provider == 'pi':
                from provider_pi import latest_pi
                result = latest_pi(args.id)
            else:
                sid = ident(args.id)
                with CodexConnection() as connection:
                    result = latest_codex(connection, sid)
        elif args.action == 'send':
            if args.provider != 'codex':
                raise ValueError('This provider has no verified exact-session instruction transport.')
            # Request via stdin, never message contents in argv/process listings.
            request = json.loads(__import__('sys').stdin.readline(65536))
            if not isinstance(request, dict):
                raise ValueError('Provide one JSON instruction object.')
            with CodexConnection() as connection:
                result = send_codex(connection, args.id, request.get('text'), args.message_id)
        else:
            sid = ident(args.id)
            if args.provider != 'codex':
                raise ValueError('No exact native-app route verified for this provider.')
            raise ValueError('Exact native-client open route for CLI sessions has not been verified. Use the displayed provider session UUID in its owning client.')
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, TypeError, OSError, RuntimeError, TimeoutError, subprocess.SubprocessError) as error:
        # Content-free diagnostics; never echo protocol bodies, messages or private paths.
        print(json.dumps({'ok': False, 'message': str(error) if isinstance(error, (ValueError, RuntimeError)) else
                          'Local session service unavailable; no automatic retry or fallback.'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
