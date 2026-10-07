"""Claude stored subagent metadata and exact opt-in assistant history.

Native subagent paths are documented by Claude Code. No TUI input, attach,
resume, model call, approval response, or transcript body inventory is used.
"""
import json
import os
from pathlib import Path
import re
import stat
import time

UUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
AGENT = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')
LIMIT = 128
TAIL_BYTES = 2 * 1024 * 1024
TEXT_LIMIT = 65536
HISTORY_LIMIT = 16


def identity(value):
    if not isinstance(value, str):
        raise ValueError('Select an exact Claude session or recorded subagent identity.')
    parts = value.split(':')
    if len(parts) not in (1, 2) or not UUID.fullmatch(parts[0]) or (len(parts) == 2 and not AGENT.fullmatch(parts[1])):
        raise ValueError('Select an exact Claude session or recorded subagent identity.')
    return parts[0].lower(), parts[1] if len(parts) == 2 else None


def safe_descriptor(path, root):
    """Traverse absolute components without following symlinks; validate data scope."""
    path, root = Path(os.path.abspath(path)), Path(os.path.abspath(root))
    path.relative_to(root)
    data_home = root.parent
    directory_fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    current = Path('/')
    try:
        for part in path.parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
            current = current / part
            info = os.fstat(directory_fd)
            if current == data_home or current.is_relative_to(data_home):
                if info.st_uid != os.getuid() or info.st_mode & 0o022:
                    raise ValueError('Claude data directories must be owner-held and not writable by other users.')
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022 or info.st_nlink != 1:
            raise ValueError('Claude data must be an owner-held regular file without shared writes or hard links.')
        return fd
    except BaseException:
        os.close(fd)
        raise


def safe_file(path, root):
    try:
        fd = safe_descriptor(path, root)
        os.close(fd)
        return True
    except (OSError, ValueError):
        return False


def selected_path(value, home=None):
    sid, agent = identity(value)
    root = Path(home or Path.home() / '.claude') / 'projects'
    suffix = sid + '/subagents/agent-' + agent + '.jsonl' if agent else sid + '.jsonl'
    candidates = []
    try:
        for index, project in enumerate(root.iterdir()):
            if index >= 256:
                raise ValueError('Selected Claude lookup exceeds its directory bound; identity uniqueness is unverified.')
            if project.is_symlink() or not project.is_dir():
                continue
            candidate = project / suffix
            if safe_file(candidate, root):
                candidates.append(candidate)
    except OSError:
        raise ValueError('Selected Claude transcript is unavailable or unsafe.') from None
    if len(candidates) != 1:
        raise ValueError('Selected Claude transcript is unavailable, unsafe or ambiguous.')
    return candidates[0], sid, agent


def subagent_inventory(existing=(), home=None, notices=None):
    root = Path(home or Path.home() / '.claude') / 'projects'
    if root.is_symlink() or not root.is_dir():
        return []
    live = {r['id']: r for r in existing if r.get('provider') == 'claude'}
    # Directory traversal is bounded separately; no body, name, prompt or role
    # is loaded for automatic inventory. Sidecar presence confirms native records.
    candidates = []
    scanned = 0
    scan_bound = False
    for project in root.iterdir():
        scanned += 1
        if scanned > 2048:
            scan_bound = True
            break
        if project.is_symlink() or not project.is_dir():
            continue
        for session in project.iterdir():
            scanned += 1
            if scanned > 2048:
                scan_bound = True
                break
            if session.is_symlink() or not session.is_dir() or not UUID.fullmatch(session.name):
                continue
            child_dir = session / 'subagents'
            if child_dir.is_symlink() or not child_dir.is_dir():
                continue
            for sidecar in child_dir.glob('agent-*.meta.json'):
                scanned += 1
                if scanned > 2048:
                    scan_bound = True
                    break
                agent = sidecar.name[len('agent-'):-len('.meta.json')]
                transcript = child_dir / ('agent-' + agent + '.jsonl')
                if not AGENT.fullmatch(agent) or not safe_file(sidecar, root) or not safe_file(transcript, root):
                    continue
                if len(candidates) >= 512:
                    scan_bound = True
                    break
                # Known compaction helpers are not semantic user subagents.
                try:
                    if sidecar.stat().st_size > 32768:
                        continue
                    with safe_open(sidecar, root) as stream:
                        raw = stream.read(32769)
                    if len(raw) > 32768:
                        continue
                    meta = json.loads(raw)
                    if meta.get('agentType', '').lower() in ('compact', 'compaction'):
                        continue
                except (OSError, ValueError, AttributeError, RecursionError):
                    continue
                candidates.append((session.name.lower() in live, sidecar.stat().st_mtime, session.name.lower(), agent, project))
            if scan_bound:
                break
        if scan_bound:
            break
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    rows = {}
    for _, _, sid, agent, project in candidates:
        if len(rows) >= LIMIT - 1:
            scan_bound = True
            break
        if sid not in live and sid not in rows:
            rows[sid] = record(sid, sid, None, safe_file(project / (sid + '.jsonl'), root))
        child = sid + ':' + agent
        rows[child] = record(child, sid, None, True)
    if scan_bound and notices is not None:
        notices.append({'provider': 'claude', 'code': 'inventory-bound-reached', 'reason': 'Stored Claude subagent metadata reached its scan or 128-record bound; some recorded children or parents may be omitted.'})
    return list(rows.values())


def record(value, sid, parent, readable):
    return {'id': value, 'provider': 'claude', 'key': 'agent:claude:' + value,
            'parentId': parent, 'parentSource': 'Native owning-main-session family; immediate spawning parent unavailable' if ':' in value else None,
            'isSubagent': ':' in value,
            'familyId': sid, 'label': 'Claude subagent ' + value.split(':')[-1][:8] if ':' in value else 'Claude stored ' + sid[:8],
            'status': {'type': 'unknown', 'activeFlags': []},
            'statusSource': 'Stored Claude subagent record; running state and completion unverified' if ':' in value else 'Stored Claude parent identity; running state unverified',
            'observedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'availability': 'stored',
            'sessionScope': 'claude-local-transcript',
            'capabilities': {'canReadReply': readable, 'canReadHistory': readable,
                'canSend': False, 'canOpen': False, 'approvalPending': None,
                'approvalPolicy': 'existing-session-unchanged',
                'reason': 'Stored assistant history only. No supported existing-process instruction transport verified; no resume or terminal input fallback.'}}


def safe_open(path, root):
    return os.fdopen(safe_descriptor(path, root), 'rb')


def reply(value, home=None):
    path, sid, agent = selected_path(value, home)
    with safe_open(path, Path(home or Path.home() / '.claude') / 'projects') as stream:
        size = os.fstat(stream.fileno()).st_size
        start = max(0, size - TAIL_BYTES)
        stream.seek(start)
        if start:
            stream.readline(TAIL_BYTES)
        data = stream.read(TAIL_BYTES)
    entries = []
    budget = TEXT_LIMIT
    truncated = start > 0
    for line in reversed(data.split(b'\n')):
        try:
            item = json.loads(line)
        except (ValueError, UnicodeError, RecursionError):
            continue
        if not isinstance(item, dict) or item.get('type') != 'assistant' or item.get('sessionId') != sid:
            continue
        if agent and (item.get('agentId') != agent or item.get('isSidechain') is not True):
            continue
        if not agent and item.get('isSidechain') is True:
            continue
        message = item.get('message')
        content = message.get('content', []) if isinstance(message, dict) else []
        if not isinstance(content, list):
            continue
        text = '\n'.join(c['text'] for c in content if isinstance(c, dict) and c.get('type') == 'text' and isinstance(c.get('text'), str))
        if not text:
            continue
        if len(entries) >= HISTORY_LIMIT or budget <= 0:
            truncated = True
            break
        excerpt = text[:budget]
        budget -= len(excerpt)
        truncated = truncated or len(excerpt) < len(text)
        entries.append({'text': excerpt, 'itemId': str(item.get('uuid', ''))[:128], 'role': 'assistant'})
    latest = entries[0]['text'] if entries else ''
    return {'ok': True, 'provider': 'claude', 'id': value, 'text': latest,
            'history': list(reversed(entries)), 'truncated': truncated,
            'source': 'Selected Claude stored assistant history; not live completion telemetry',
            'observedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'sessionScope': 'claude-local-transcript', 'message': '' if entries else 'No assistant text in the bounded selected transcript tail.'}
