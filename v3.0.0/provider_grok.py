"""Read-only Grok stored-session metadata and explicitly selected assistant history.

Storage follows the installed Grok CLI's documented Session Persistence layout.
No CLI/API process, authentication, resume, prompt, or input injection is used.
"""
import json
import os
from pathlib import Path
import re
import stat
import time
from urllib.parse import unquote

NAME_LIMIT = 64
CONTROL = re.compile('[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069]')
UUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
LIMIT = 128
MAX_CANDIDATES = 512
MAX_DIRECTORY_ENTRIES = 256
MAX_CHILD_DIRECTORIES = 1024
MAX_CHILD_DEPTH = 8
MAX_METADATA_BYTES = 65536
MAX_HISTORY_BYTES = 8 * 1024 * 1024
MAX_HISTORY_LINE = 1024 * 1024
MAX_MESSAGES = 16
MAX_TEXT = 65536
SOURCE = 'Selected Grok chat_history.jsonl assistant text (stored; live completion unverified)'


def display_name(value):
    if not isinstance(value, str):
        return None
    text = ' '.join(CONTROL.sub(' ', value).split())
    return text[:NAME_LIMIT] or None


def ident(value):
    if not isinstance(value, str) or not UUID.fullmatch(value):
        raise ValueError('Select an exact Grok session UUID.')
    return value.lower()


def stamp():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def notice(notices, code, reason):
    value = {'provider': 'grok', 'code': code, 'reason': reason}
    if notices is not None and value not in notices:
        notices.append(value)


class Store:
    """Descriptor-relative, owner-checked reads; never follow directory/file links."""
    def __init__(self, home=None):
        # ``home`` is the Grok data directory (normally ~/.grok), not $HOME.
        self.root = Path(home if home is not None else Path.home() / '.grok').absolute()

    def directory(self, relative=()):
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        try:
            parts = self.root.parts[1:] + tuple(relative)
            root_depth = len(self.root.parts) - 1
            for index, part in enumerate(parts, 1):
                if part in ('', '.', '..') or '/' in part:
                    raise ValueError('Invalid Grok storage path.')
                following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd); fd = following
                info = os.fstat(fd)
                # Only the provider data root and its descendants must belong to
                # this user. System ancestors may be root/mapped-system owned;
                # opening each component without links anchors the safe root.
                if index >= root_depth and (info.st_uid != os.getuid() or info.st_mode & 0o022):
                    raise ValueError('Grok storage ownership is unsafe.')
            return fd
        except BaseException:
            os.close(fd)
            raise

    def file(self, relative, directory_fd=None):
        if relative[-1] in ('', '.', '..') or '/' in relative[-1]:
            raise ValueError('Invalid Grok storage filename.')
        directory = self.directory(relative[:-1]) if directory_fd is None else directory_fd
        try:
            fd = os.open(relative[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        finally:
            if directory_fd is None:
                os.close(directory)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022 or info.st_nlink != 1:
                raise ValueError('Selected Grok file ownership or type is unsafe.')
        except BaseException:
            os.close(fd)
            raise
        return fd

    def metadata(self, relative, directory_fd=None):
        fd = self.file(relative, directory_fd)
        with os.fdopen(fd, 'rb') as stream:
            if os.fstat(stream.fileno()).st_size > MAX_METADATA_BYTES:
                raise ValueError('Grok metadata exceeds its safety bound.')
            raw = stream.read(MAX_METADATA_BYTES + 1)
        if len(raw) > MAX_METADATA_BYTES:
            raise ValueError('Grok metadata exceeds its safety bound.')
        try:
            value = json.loads(raw)
        except RecursionError:
            raise ValueError('Grok metadata nesting exceeds its safety bound.') from None
        if not isinstance(value, dict):
            raise ValueError('Invalid Grok metadata.')
        return value

    def directories(self, relative, notices):
        fd = self.directory(relative)
        try:
            with os.scandir(fd) as entries:
                names = []
                for index, entry in enumerate(entries):
                    if index >= MAX_DIRECTORY_ENTRIES:
                        notice(notices, 'inventory-bound-reached', 'Grok storage directory scan reached its bound; additional records may be omitted.')
                        break
                    if entry.is_dir(follow_symlinks=False):
                        names.append(entry.name)
            return sorted(names)
        finally:
            os.close(fd)


def summary(store, directory, directory_fd=None):
    value = store.metadata(directory + ('summary.json',), directory_fd)
    info = value.get('info')
    if not isinstance(info, dict) or ident(info.get('id')) != ident(directory[-1]):
        raise ValueError('Grok summary identity does not match its directory.')
    # Restored-session parent, model prompts and message counts are ignored:
    # restoring a session does not prove subagent ancestry. Explicit title and
    # agent-name metadata supply the real session name; cwd only its basename.
    name, source = None, None
    for field, label in (('generated_title', 'Grok generated session title'), ('agent_name', 'Grok agent name')):
        name = display_name(value.get(field))
        if name:
            source = label
            break
    cwd = directory[1] if len(directory) > 1 else None
    project = None
    if isinstance(cwd, str):
        try:
            project = display_name(os.path.basename(unquote(cwd).rstrip('/')))
        except (ValueError, UnicodeError):
            project = None
    return {'id': ident(info['id']), 'directory': directory, 'name': name, 'nameSource': source, 'project': project}


def scan(home=None, notices=None):
    store = Store(home); candidates = []; roots = []; edges = []
    try:
        encoded = store.directories(('sessions',), notices)
    except (OSError, ValueError):
        notice(notices, 'inventory-unavailable', 'Owner-safe Grok stored metadata is unavailable.')
        return store, {}, set(), []
    attempts = 0
    root_bound = False
    for cwd in encoded:
        try:
            sessions = store.directories(('sessions', cwd), notices)
        except (OSError, ValueError):
            continue
        for sid in sessions:
            if not UUID.fullmatch(sid):
                continue
            if attempts >= MAX_CANDIDATES:
                notice(notices, 'inventory-bound-reached', 'Grok metadata candidate scan reached its bound; additional records may be omitted.')
                root_bound = True
                break
            attempts += 1
            try:
                item = summary(store, ('sessions', cwd, sid))
            except (OSError, ValueError):
                notice(notices, 'metadata-omitted', 'An unsafe, invalid or unreadable Grok metadata record was omitted.')
                continue
            candidates.append(item); roots.append(item)
        if root_bound:
            break
    # Only the documented subagents subtree establishes child relationships.
    # meta.json explicitly identifies parent_session_id and child_session_id;
    # the latter may reference a separately indexed root summary for that child.
    budget = MAX_CHILD_DIRECTORIES
    child_budget = MAX_CHILD_DIRECTORIES
    for root in roots:
        pending = [(root['directory'] + ('subagents',), root['id'], 0)]
        while pending:
            directory, parent, depth = pending.pop()
            if budget <= 0:
                notice(notices, 'ancestry-bound-reached', 'Grok subagent metadata scan reached its bound; relationships may be incomplete.')
                break
            budget -= 1
            try:
                children = store.directories(directory, notices)
            except (OSError, ValueError):
                continue
            for name in children:
                if child_budget <= 0:
                    notice(notices, 'ancestry-bound-reached', 'Grok subagent entry scan reached its bound; relationships may be incomplete.')
                    budget = 0
                    break
                child_budget -= 1
                child_dir = directory + (name,)
                child_parent = parent
                if UUID.fullmatch(name):
                    try:
                        item = summary(store, child_dir)
                        if len(candidates) < MAX_CANDIDATES:
                            candidates.append(item)
                        else:
                            notice(notices, 'inventory-bound-reached', 'Grok metadata candidate scan reached its bound; additional records may be omitted.')
                        edges.append((item['id'], parent, 'Grok documented subagents directory and matching summary.info.id'))
                        child_parent = item['id']
                    except (OSError, ValueError):
                        pass
                    try:
                        meta = store.metadata(child_dir + ('meta.json',))
                        child = ident(meta.get('child_session_id')); declared_parent = ident(meta.get('parent_session_id'))
                        if child == ident(name) and declared_parent == parent:
                            edges.append((child, parent, 'Grok subagents/meta.json exact parent_session_id and child_session_id'))
                            child_parent = child
                    except (OSError, ValueError):
                        pass
                if depth < MAX_CHILD_DEPTH:
                    pending.append((child_dir, child_parent, depth + 1))
                else:
                    notice(notices, 'ancestry-bound-reached', 'Grok subagent metadata depth reached its bound; relationships may be incomplete.')
        if budget <= 0:
            break
    grouped = {}
    for item in candidates:
        grouped.setdefault(item['id'], {})[item['directory']] = item
    ambiguous = {sid for sid, paths in grouped.items() if len(paths) != 1}
    if ambiguous:
        notice(notices, 'ambiguous-session', 'Duplicate Grok session identities were omitted; selected reads require one exact stored path.')
    indexed = {sid: next(iter(paths.values())) for sid, paths in grouped.items() if sid not in ambiguous}
    return store, indexed, ambiguous, edges


def inventory(home=None, notices=None):
    scan_notices = notices if notices is not None else []
    store, indexed, _, edges = scan(home, scan_notices)
    scan_bounded = any(n['code'] in ('inventory-bound-reached', 'ancestry-bound-reached') for n in scan_notices)
    parents = {}
    for child, parent, source in edges:
        if child in indexed and parent in indexed and child != parent:
            parents.setdefault(child, {})[parent] = source
    records = []
    for sid, item in sorted(indexed.items()):
        relation = parents.get(sid, {})
        parent = next(iter(relation)) if len(relation) == 1 else None
        if len(relation) > 1:
            notice(notices, 'ambiguous-parent', 'Conflicting Grok subagent parent records were omitted.')
        seen = {sid}; ancestor = parent
        while ancestor:
            if ancestor in seen:
                parent = None
                notice(notices, 'invalid-parent', 'Cyclic Grok subagent relationships were omitted.')
                break
            seen.add(ancestor)
            links = parents.get(ancestor, {})
            ancestor = next(iter(links)) if len(links) == 1 else None
        readable = False
        try:
            fd = store.file(item['directory'] + ('chat_history.jsonl',)); os.close(fd)
            readable = not scan_bounded
        except (OSError, ValueError):
            pass
        row = {'id': sid, 'provider': 'grok', 'key': 'agent:grok:' + sid,
               'parentId': parent, 'familyId': sid, 'isSubagent': bool(parent), 'label': item.get('name') or 'Grok ' + sid[:8],
               'name': item.get('name'), 'nameSource': item.get('nameSource'), 'project': item.get('project'),
               'status': {'type': 'unknown', 'activeFlags': []}, 'availability': 'stored',
               'statusSource': 'Grok summary metadata; live process ownership unverified',
               'sessionScope': 'grok-local-stored', 'observedAt': stamp(),
               'capabilities': {'canReadReply': readable, 'canReadHistory': readable,
                                'canMonitorLive': False, 'canSend': False, 'canOpen': False,
                                'approvalPolicy': 'existing-session-unchanged', 'approvalPending': None,
                                'reason': ('Metadata scan is incomplete; selected reads are disabled. ' if scan_bounded else '') +
                                          'Stored assistant history only. No documented exact existing Grok session attach/send API verified.'}}
        if parent:
            row['parentSource'] = relation[parent]
        records.append(row)
    by_id = {row['id']: row for row in records}
    for row in records:
        ancestor = row
        while ancestor.get('parentId') in by_id:
            ancestor = by_id[ancestor['parentId']]
        row['familyId'] = ancestor['id']
    if len(records) > LIMIT:
        notice(notices, 'inventory-bound-reached', 'Stored Grok inventory reached its 128-record bound; additional sessions or parent records may be omitted.')
    return records[:LIMIT]


def assistant_text(item):
    if not isinstance(item, dict):
        return ''
    # Native Grok history is tagged with ``type``. Also accept raw role-tagged
    # model messages, but never let one discriminator override a conflicting one.
    tags = [item[key] for key in ('type', 'role') if key in item]
    if not tags or any(tag != 'assistant' for tag in tags):
        return ''
    content = item.get('content')
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(part['text'] for part in content if isinstance(part, dict)
                         and part.get('type') == 'text' and isinstance(part.get('text'), str))
    return ''


def reply(sid, home=None):
    sid = ident(sid)
    notices = []
    store, indexed, ambiguous, _ = scan(home, notices)
    if any(n['code'] in ('inventory-bound-reached', 'ancestry-bound-reached') for n in notices):
        raise ValueError('Bounded Grok metadata scan cannot verify a unique selected stored path.')
    if sid in ambiguous or sid not in indexed:
        raise ValueError('Selected Grok stored session is unavailable or ambiguous.')
    directory = indexed[sid]['directory']
    selected_directory = store.directory(directory)
    try:
        if summary(store, directory, selected_directory)['id'] != sid:
            raise ValueError('Selected Grok session identity changed.')
        fd = store.file(directory + ('chat_history.jsonl',), selected_directory)
    finally:
        os.close(selected_directory)
    with os.fdopen(fd, 'rb') as stream:
        size = os.fstat(stream.fileno()).st_size
        start = max(0, size - MAX_HISTORY_BYTES); stream.seek(start)
        raw = stream.read(min(size - start, MAX_HISTORY_BYTES))
    truncated = start > 0
    if start:
        first = raw.find(b'\n')
        start += first + 1 if first >= 0 else len(raw)
        raw = raw[first + 1:] if first >= 0 else b''
    retained = []; offset = start
    for line in raw.splitlines(keepends=True):
        offset += len(line)
        if len(line) > MAX_HISTORY_LINE:
            truncated = True; continue
        try:
            item = json.loads(line)
        except (ValueError, UnicodeError, RecursionError):
            truncated = True; continue
        text = assistant_text(item)
        if not text:
            continue
        item_id = item.get('id')
        if not isinstance(item_id, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,128}', item_id):
            item_id = 'grok-history:' + str(offset)
        retained.append({'text': text, 'itemId': item_id, 'role': 'assistant'})
        if len(retained) > MAX_MESSAGES:
            retained.pop(0); truncated = True
    remaining = MAX_TEXT; history = []
    for message in reversed(retained):
        if remaining <= 0:
            truncated = True; break
        text = message['text']
        if len(text) > remaining:
            text = text[-remaining:]; truncated = True
        history.append({**message, 'text': text}); remaining -= len(text)
    history.reverse()
    return {'ok': True, 'provider': 'grok', 'id': sid,
            'text': history[-1]['text'] if history else '', 'history': history,
            'truncated': truncated, 'source': SOURCE, 'observedAt': stamp(),
            'availability': 'stored', 'completionUnverified': True,
            'message': '' if history else 'No assistant text in the bounded selected stored history.'}
