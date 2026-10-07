"""Read-only Pi saved-session adapter. No process launch, resume, or transport writes.

Inventory parses only the session header and native model_change records; message
bodies are not decoded. Replies/history are read only for an explicitly selected
opaque session ID. Entry parentId describes the conversation tree, never agents.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_FILES = 256
MAX_BYTES = 8 * 1024 * 1024
MAX_INVENTORY_BYTES = 16 * 1024 * 1024
MAX_LINE = 1024 * 1024
MAX_ENTRIES = 20000
MAX_TEXT = 65536
ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
MODEL_LINE = re.compile(rb'^\s*\{\s*"type"\s*:\s*"model_change"\s*[,}]')
KIMI_MODELS = frozenset(('k3', 'k3-256k', 'kimi-for-coding'))
SEND_REASON = ('Pi RPC belongs to its owning stdin/stdout subprocess. No supported '
               'attach transport to this existing session is verified. An in-process '
               'extension bridge would require separate explicit setup; none is installed by Districts.')
SOURCE = ('Selected Pi saved JSONL path ending at its last persisted entry; '
          'not live process state or a verified current in-memory branch')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def ident(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('Invalid Pi session identifier.')
    return value


def root_path(home=None):
    return Path(home) if home is not None else Path.home() / '.pi' / 'agent' / 'sessions'


def notice(notices, code, reason):
    if not any(n['code'] == code for n in notices):
        notices.append({'provider': 'pi', 'code': code, 'reason': reason})


def paths(root):
    """At most 256 native depth-two files; never follow symlink directories."""
    if not root.exists():
        return [], False
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Pi session root must be a local directory, not a symlink.')
    candidates = []
    # scandir iteration itself is bounded, including unrelated entries.
    examined = 0
    with os.scandir(root) as directories:
        for directory in directories:
            examined += 1
            if examined > MAX_FILES:
                return candidates, True
            if not directory.is_dir(follow_symlinks=False):
                continue
            with os.scandir(directory.path) as files:
                for file in files:
                    examined += 1
                    if examined > MAX_FILES:
                        return candidates, True
                    if file.name.endswith('.jsonl') and file.is_file(follow_symlinks=False):
                        candidates.append(Path(file.path))
    return candidates, False


def safe_open(path, root, header_only=False):
    if path.parent.is_symlink() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Pi transcript must remain inside its local session root.')
    if path.parent.parent != root:
        raise ValueError('Pi transcript must use the native depth-two session layout.')
    # Directory descriptors prevent a changed parent symlink from redirecting the
    # final open after the path check. No path or credential is returned to UI.
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        directory_fd = os.open(path.parent.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        os.close(root_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('Pi transcript must be a regular file owned by the current user.')
        if not header_only and info.st_size > MAX_BYTES:
            raise ValueError('Selected Pi transcript exceeds the 8MiB read bound.')
        return os.fdopen(fd, 'rb'), info
    except BaseException:
        os.close(fd)
        raise


def header_read(stream):
    line = stream.readline(65537)
    if len(line) > 65536:
        raise ValueError('Pi session header exceeds its bound.')
    item = json.loads(line)
    if not isinstance(item, dict) or item.get('type') != 'session' or item.get('version') not in (2, 3):
        raise ValueError('Unsupported Pi saved-session format; no migration is performed.')
    return {'id': ident(item.get('id')), 'version': item['version'],
            'forkAncestryRecorded': bool(item.get('parentSession'))}


def lines(stream):
    total = stream.tell()
    for _ in range(MAX_ENTRIES):
        line = stream.readline(MAX_LINE + 1)
        if not line:
            return
        total += len(line)
        if total > MAX_BYTES or len(line) > MAX_LINE:
            raise ValueError('Pi transcript entry or scan exceeds its read bound.')
        # Live writers may leave one incomplete last record. Ignore it, explicitly
        # report via the caller, and never join it to a later record.
        if not line.endswith(b'\n'):
            raise ValueError('Pi transcript has an incomplete final record; retry after its writer settles.')
        yield line
    if stream.read(1):
        raise ValueError('Pi transcript exceeds its 20000-entry bound.')


def metadata(path, root):
    stream, _ = safe_open(path, root)
    with stream:
        header = header_read(stream)
        model_provider = model_id = None
        for line in lines(stream):
            if not MODEL_LINE.match(line):
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or item.get('type') != 'model_change':
                continue
            provider, model = item.get('provider'), item.get('modelId')
            if isinstance(provider, str) and isinstance(model, str):
                model_provider, model_id = provider[:128], model[:128]
        header.update(modelProvider=model_provider, modelId=model_id,
                      isKimi3=model_provider == 'kimi-coding' and model_id in KIMI_MODELS)
        return header


def inventory_pi(home=None):
    root = root_path(home)
    notices = []
    records = []
    candidates, bounded = paths(root)
    if bounded:
        notice(notices, 'inventory-bound', 'Pi filesystem inventory reached its 256-entry scan bound; saved sessions may be omitted.')
    headers = []
    scanned_bytes = 0
    for path in candidates:
        try:
            scanned_bytes += path.stat().st_size
            if scanned_bytes > MAX_INVENTORY_BYTES:
                bounded = True
                notice(notices, 'metadata-budget', 'Pi inventory reached its aggregate 16MiB metadata scan budget; additional sessions were omitted.')
                break
            headers.append(metadata(path, root))
        except (OSError, ValueError, UnicodeError):
            notice(notices, 'metadata-unavailable', 'A saved Pi session could not be safely read within the format and size bounds.')
    counts = {}
    for header in headers:
        counts[header['id']] = counts.get(header['id'], 0) + 1
    for header in headers:
        sid = header['id']
        if counts[sid] != 1:
            if not any(n['code'] == 'ambiguous-id' for n in notices):
                notice(notices, 'ambiguous-id', 'Duplicate Pi session IDs are omitted; selected reads require exactly one local file.')
            continue
        prefix = 'Kimi3 via Pi' if header['isKimi3'] else 'Pi'
        records.append({'id': sid, 'provider': 'pi', 'key': 'agent:pi:' + sid,
                        'parentId': None, 'familyId': sid, 'label': prefix + ' ' + sid[:8],
                        'modelProvider': header['modelProvider'], 'modelId': header['modelId'],
                        'isKimi3': header['isKimi3'], 'forkAncestryRecorded': header['forkAncestryRecorded'],
                        'modelSource': 'Last saved model_change record; not verified live model selection',
                        'parentSource': 'Pi parentSession records fork/clone ancestry, not semantic subagent parentage',
                        'status': {'type': 'unknown', 'activeFlags': []},
                        'statusSource': 'Pi saved JSONL header; live activity and approvals unavailable',
                        'observedAt': stamp(), 'availability': 'stored', 'sessionScope': 'pi-saved-session',
                        'capabilities': {'canReadReply': True, 'canReadHistory': True,
                                         'canSend': False, 'canOpen': False, 'canMonitorLive': False,
                                         'canReadParent': False, 'approvalPolicy': 'existing-session-unchanged',
                                         'approvalPending': None, 'reason': SEND_REASON}})
    return {'sessions': records, 'notices': notices, 'bounded': bounded or bool(notices),
            'provider': {'provider': 'pi', 'availability': 'stored',
                         'statusSource': 'Saved session records; live process monitoring unavailable',
                         'canReadReply': True, 'canReadHistory': True,
                         'canSend': False, 'canMonitorLive': False, 'canReadParent': False,
                         'reason': SEND_REASON}}


def selected_path(sid, root):
    ident(sid)
    candidates, bounded = paths(root)
    if bounded:
        raise ValueError('Pi inventory is bounded; exact selected session cannot be established.')
    matches = []
    for path in candidates:
        try:
            stream, _ = safe_open(path, root, header_only=True)
            with stream:
                if header_read(stream)['id'] == sid:
                    matches.append(path)
        except (OSError, ValueError, UnicodeError):
            raise ValueError('Pi inventory contains an unreadable header; exact selected identity cannot be established.') from None
    if len(matches) != 1:
        raise ValueError('Selected Pi transcript is unavailable or ambiguous.')
    return matches[0]


def selected_entries(sid, home=None):
    root = root_path(home)
    path = selected_path(sid, root)
    stream, info = safe_open(path, root)
    with stream:
        if header_read(stream)['id'] != sid:
            raise ValueError('Selected Pi file identity changed.')
        entries = {}
        leaf = None
        incomplete = False
        try:
            for line in lines(stream):
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError('Invalid Pi entry object.')
                eid = ident(item.get('id'))
                parent = item.get('parentId')
                if parent is not None:
                    ident(parent)
                if eid in entries:
                    raise ValueError('Duplicate Pi conversation entry identifier.')
                # Never retain system/tool/thinking bodies or extension state.
                saved = {'parentId': parent}
                if item.get('type') == 'message':
                    message = item.get('message')
                    if isinstance(message, dict) and message.get('role') in ('user', 'assistant'):
                        content = message.get('content')
                        text = content if isinstance(content, str) else '\n'.join(
                            c['text'] for c in content if isinstance(c, dict) and c.get('type') == 'text' and isinstance(c.get('text'), str)
                        ) if isinstance(content, list) else ''
                        saved.update(id=eid, role=message['role'], text=text[:MAX_TEXT],
                                     truncated=len(text) > MAX_TEXT,
                                     timestamp=item.get('timestamp') if isinstance(item.get('timestamp'), str) else None)
                entries[eid] = saved
                leaf = eid
        except ValueError as error:
            if str(error).startswith('Pi transcript has an incomplete final record'):
                incomplete = True
            else:
                raise
        current = os.fstat(stream.fileno())
        if (info.st_ino, info.st_size, info.st_mtime_ns) != (current.st_ino, current.st_size, current.st_mtime_ns):
            raise ValueError('Pi transcript changed during selected reading; restart history.')
    messages, seen = [], set()
    while leaf is not None:
        if leaf in seen or leaf not in entries:
            raise ValueError('Pi saved entry path has a cycle or missing ancestor.')
        seen.add(leaf)
        item = entries[leaf]
        if item.get('text'):
            messages.append({k: item[k] for k in ('id', 'role', 'text', 'timestamp', 'truncated')})
        leaf = item['parentId']
    snapshot = hashlib.sha256(f'{sid}:{info.st_ino}:{info.st_size}:{info.st_mtime_ns}'.encode()).hexdigest()[:24]
    return messages, snapshot, incomplete


def history_pi(sid, cursor=None, limit=8, home=None):
    sid = ident(sid)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 16:
        raise ValueError('Pi history page size must be between 1 and 16 messages.')
    messages, snapshot, incomplete = selected_entries(sid, home)
    offset = 0
    if cursor is not None:
        try:
            if not isinstance(cursor, str) or len(cursor) > 512 or not re.fullmatch(r'[A-Za-z0-9_-]+', cursor):
                raise ValueError()
            token = json.loads(base64.urlsafe_b64decode(cursor + '=' * (-len(cursor) % 4)))
            if (not isinstance(token, dict) or token.get('id') != sid or token.get('snapshot') != snapshot
                    or type(token.get('offset')) is not int or not 0 <= token['offset'] <= len(messages)):
                raise ValueError()
            offset = token['offset']
        except (ValueError, UnicodeError, TypeError):
            raise ValueError('Pi history cursor is invalid or stale; restart selected history.') from None
    chosen = []
    size = 0
    for message in messages[offset:offset + limit]:
        if chosen and size + len(message['text']) > MAX_TEXT:
            break
        chosen.append(message)
        size += len(message['text'])
    next_offset = offset + len(chosen)
    next_cursor = None
    if next_offset < len(messages):
        token = {'id': sid, 'snapshot': snapshot, 'offset': next_offset}
        next_cursor = base64.urlsafe_b64encode(json.dumps(token, separators=(',', ':')).encode()).decode().rstrip('=')
    return {'ok': True, 'provider': 'pi', 'id': sid, 'messages': chosen,
            'nextCursor': next_cursor, 'hasMore': next_cursor is not None, 'order': 'newest-first',
            'truncated': incomplete or any(m['truncated'] for m in chosen),
            'source': SOURCE, 'observedAt': stamp(),
            'message': 'Incomplete last record excluded; retry after the writer settles.' if incomplete else ''}


def latest_pi(sid, home=None):
    """Explicit Read reply: latest assistant plus bounded assistant-only history.

    This does not automatically expose user text. The separate explicit history
    action may call history_pi() for user/assistant transcript pages.
    """
    sid = ident(sid)
    messages, _, incomplete = selected_entries(sid, home)
    assistants = [m for m in messages if m['role'] == 'assistant']
    latest = assistants[0] if assistants else None
    history = []
    size = 0
    for message in assistants[:16]:
        if history and size + len(message['text']) > MAX_TEXT:
            break
        history.append({'text': message['text'], 'itemId': message['id'], 'role': 'assistant'})
        size += len(message['text'])
    history.reverse()
    return {'ok': True, 'provider': 'pi', 'id': sid, 'text': latest['text'] if latest else '',
            'history': history, 'historySource': SOURCE,
            'historyTruncated': incomplete or len(history) < len(assistants) or any(m['truncated'] for m in assistants[:len(history)]),
            'truncated': incomplete or bool(latest and latest['truncated']),
            'source': SOURCE + ' / latest stored assistant text', 'observedAt': stamp(),
            'message': '' if latest else 'No assistant text on this selected saved entry path.'}
