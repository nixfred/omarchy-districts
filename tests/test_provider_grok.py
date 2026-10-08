import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('provider_grok', Path(__file__).resolve().parents[1] / 'provider_grok.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
A = '11111111-1111-4111-8111-111111111111'
B = '22222222-2222-4222-8222-222222222222'
C = '33333333-3333-4333-8333-333333333333'


class GrokProvider(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / '.grok'
        self.home.mkdir()

    def session(self, sid=A, cwd='%2Ffixture', **extra):
        directory = self.home / 'sessions' / cwd / sid
        directory.mkdir(parents=True, exist_ok=True)
        data = {'info': {'id': sid, 'cwd': 'PRIVATE CWD'}, 'title': 'PRIVATE TITLE', **extra}
        (directory / 'summary.json').write_text(json.dumps(data))
        return directory

    def chat(self, directory, items):
        (directory / 'chat_history.jsonl').write_text(''.join(json.dumps(i) + '\n' for i in items))

    def child(self, parent, child, declared_parent=None, declared_child=None):
        directory = parent / 'subagents' / child
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'meta.json').write_text(json.dumps({
            'parent_session_id': declared_parent or parent.name,
            'child_session_id': declared_child or child,
            'status': 'completed', 'prompt': 'PRIVATE CHILD PROMPT',
            'description': 'PRIVATE CHILD DESCRIPTION', 'tool_calls': 99,
            'started_at': '2000-01-01', 'completed_at': '2000-01-02', 'pid': os.getpid()}))
        (directory / 'output.json').write_text('PRIVATE OUTPUT MUST NOT BE READ')
        return directory

    def test_real_names_from_title_metadata_and_cwd_basename_only(self):
        self.session(A, cwd='%2Fhome%2Fuser%2FProjects%2Fplonk', generated_title='Plonk\u202e compact\nbugs', agent_name='ignored')
        self.session(B, cwd='%2Fsecret', agent_name='grok-build-plan')
        self.session(C)
        rows = {r["id"]: r for r in g.inventory(self.home)}
        self.assertEqual(rows[A]['name'], 'Plonk compact bugs')
        self.assertEqual(rows[A]['label'], 'Plonk compact bugs')
        self.assertEqual(rows[A]['nameSource'], 'Grok generated session title')
        self.assertEqual(rows[A]['project'], 'plonk')
        self.assertEqual(rows[B]['name'], 'grok-build-plan')
        self.assertIsNone(rows[C]['name'])
        self.assertEqual(rows[C]['label'], 'Grok ' + C[:8])
        encoded = json.dumps(list(rows.values()))
        self.assertNotIn('PRIVATE', encoded)
        self.assertNotIn('/home/user', encoded)

    def test_inventory_metadata_only_without_any_automatic_chat_read(self):
        root = self.session(parentSessionId=B, pid=os.getpid(), status='working')
        self.chat(root, [{'role': 'user', 'content': 'PRIVATE USER'},
                         {'role': 'assistant', 'content': 'PRIVATE ASSISTANT'}])
        (root / 'updates.jsonl').write_text('PRIVATE UPDATES')
        (root / 'signals.json').write_text('PRIVATE SIGNALS')
        self.session(B)
        child = self.child(root, B)
        original_metadata = g.Store.metadata
        reads = []
        def metadata(store, relative, directory_fd=None):
            reads.append(relative[-1])
            self.assertIn(relative[-1], ('summary.json', 'meta.json'))
            return original_metadata(store, relative, directory_fd)
        original_fdopen = os.fdopen
        def fdopen(fd, *args, **kwargs):
            target = os.readlink('/proc/self/fd/' + str(fd))
            self.assertIn(Path(target).name, ('summary.json', 'meta.json'))
            return original_fdopen(fd, *args, **kwargs)
        with patch.object(g.Store, 'metadata', metadata), patch.object(g.os, 'fdopen', fdopen), \
             patch.object(g, 'reply', side_effect=AssertionError('automatic reply forbidden')):
            rows = g.inventory(self.home)
        self.assertTrue(reads)
        self.assertEqual(len(rows), 2)
        by_id = {r['id']: r for r in rows}
        self.assertEqual(by_id[B]['parentId'], A)
        self.assertEqual(by_id[B]['familyId'], A)
        self.assertIsNone(by_id[A]['parentId'])  # restored reference was ignored
        self.assertIn('meta.json', by_id[B]['parentSource'])
        for row in rows:
            self.assertEqual(row['availability'], 'stored')
            self.assertEqual(row['status'], {'type': 'unknown', 'activeFlags': []})
            self.assertFalse(row['capabilities']['canSend'])
            self.assertFalse(row['capabilities']['canOpen'])
        self.assertTrue(by_id[A]['capabilities']['canReadReply'])
        self.assertTrue(by_id[A]['capabilities']['canReadHistory'])
        self.assertFalse(by_id[A]['capabilities']['canMonitorLive'])
        self.assertIsNone(by_id[A]['capabilities']['approvalPending'])
        self.assertFalse(by_id[A]['isSubagent'])
        self.assertTrue(by_id[B]['isSubagent'])
        self.assertFalse(by_id[B]['capabilities']['canReadReply'])
        self.assertNotIn('PRIVATE', json.dumps(rows))
        self.assertNotIn('tool_calls', json.dumps(rows))
        self.assertTrue((child / 'output.json').exists())

    def test_assistant_history_only_chronological_latest_text(self):
        root = self.session()
        self.chat(root, [
            {'role': 'system', 'content': 'PRIVATE SYSTEM'},
            {'role': 'user', 'content': 'PRIVATE USER'},
            {'role': 'assistant', 'id': 'm1', 'content': 'First answer', 'reasoning_content': 'PRIVATE THOUGHT'},
            {'role': 'tool', 'content': 'PRIVATE TOOL'},
            {'role': 'assistant', 'id': 'm2', 'content': [
                {'type': 'thinking', 'text': 'PRIVATE THINKING'}, {'type': 'text', 'text': 'Second'},
                {'type': 'tool_use', 'text': 'PRIVATE TOOL'}, {'type': 'text', 'text': 'answer'}]},
            {'role': 'assistant', 'tool_calls': [{'arguments': 'PRIVATE ARGUMENTS'}], 'content': None}])
        value = g.reply(A, self.home)
        self.assertEqual([m['text'] for m in value['history']], ['First answer', 'Second\nanswer'])
        self.assertEqual([m['itemId'] for m in value['history']], ['m1', 'm2'])
        self.assertTrue(all(m['role'] == 'assistant' for m in value['history']))
        self.assertEqual(value['text'], 'Second\nanswer')
        self.assertNotIn('PRIVATE', json.dumps(value))
        self.assertNotIn('messages', value)
        self.assertTrue(value['completionUnverified'])
        self.assertEqual(value['availability'], 'stored')
        self.assertFalse(value['truncated'])

    def test_keeps_latest_sixteen_messages_in_order(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'content': str(i), 'id': 'm' + str(i)} for i in range(25)])
        result = g.reply(A, self.home)
        self.assertEqual([m['text'] for m in result['history']], list(map(str, range(9, 25))))
        self.assertEqual(result['text'], '24')
        self.assertTrue(result['truncated'])

    def test_native_grok_type_tagged_model_history(self):
        root = self.session()
        self.chat(root, [
            {'type': 'user', 'content': 'PRIVATE USER', 'model_id': 'private-model', 'tool_calls': []},
            {'type': 'assistant', 'content': 'Native first', 'model_id': 'private-model',
             'tool_calls': [{'arguments': 'PRIVATE TOOL INPUT'}]},
            {'type': 'tool', 'content': 'PRIVATE TOOL RESULT'},
            {'type': 'thinking', 'content': 'PRIVATE THOUGHT'},
            {'type': 'assistant', 'content': 'Native latest', 'model_id': 'private-model', 'tool_calls': []}])
        result = g.reply(A, self.home)
        self.assertEqual([m['text'] for m in result['history']], ['Native first', 'Native latest'])
        self.assertEqual(result['text'], 'Native latest')
        self.assertTrue(all(m['role'] == 'assistant' for m in result['history']))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('private-model', json.dumps(result))

    def test_native_legacy_conflicting_and_missing_tags_are_fail_closed(self):
        root = self.session()
        self.chat(root, [
            {'type': 'assistant', 'role': 'assistant', 'content': 'Both consistent'},
            {'role': 'assistant', 'content': 'Legacy raw role'},
            {'type': 'assistant', 'role': 'user', 'content': 'PRIVATE CONFLICT'},
            {'type': 'user', 'role': 'assistant', 'content': 'PRIVATE CONFLICT'},
            {'type': 'tool', 'role': 'assistant', 'content': 'PRIVATE TOOL'},
            {'type': None, 'role': 'assistant', 'content': 'PRIVATE UNKNOWN'},
            {'type': 'assistant', 'role': None, 'content': 'PRIVATE UNKNOWN'},
            {'content': 'PRIVATE UNTAGGED'},
            {'type': 'assistant', 'content': [{'type': 'text', 'text': 'Native structured text'},
                                             {'type': 'thinking', 'text': 'PRIVATE THOUGHT'}]}])
        result = g.reply(A, self.home)
        self.assertEqual([m['text'] for m in result['history']],
                         ['Both consistent', 'Legacy raw role', 'Native structured text'])
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_shared_text_budget_prefers_latest_not_per_message_budget(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'id': 'old', 'content': 'a' * 40000},
                         {'role': 'assistant', 'id': 'new', 'content': 'b' * 40000}])
        result = g.reply(A, self.home)
        self.assertEqual(sum(len(m['text']) for m in result['history']), 65536)
        self.assertEqual([len(m['text']) for m in result['history']], [25536, 40000])
        self.assertEqual(result['text'], 'b' * 40000)
        self.assertTrue(result['truncated'])

    def test_single_large_answer_has_explicit_truncation(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'content': 'begin' + 'x' * 70000 + 'end'}])
        result = g.reply(A, self.home)
        self.assertEqual(len(result['text']), 65536)
        self.assertTrue(result['text'].endswith('end'))
        self.assertTrue(result['truncated'])
        self.assertTrue(result['completionUnverified'])

    def test_reply_reads_only_selected_uuid(self):
        first = self.session(A); second = self.session(B)
        self.chat(first, [{'role': 'assistant', 'content': 'Selected A'}])
        self.chat(second, [{'role': 'assistant', 'content': 'PRIVATE B'}])
        original = os.fdopen
        def guarded(fd, *args, **kwargs):
            target = os.readlink('/proc/self/fd/' + str(fd))
            self.assertFalse(target.endswith(B + '/chat_history.jsonl'))
            return original(fd, *args, **kwargs)
        with patch.object(g.os, 'fdopen', guarded):
            self.assertEqual(g.reply(A, self.home)['text'], 'Selected A')

    def test_invalid_uuid_and_missing_summary_cannot_read(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'content': 'Selected'}])
        for sid in ('../' + A, A + '/other', '', None, 'new-session'):
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                g.reply(sid, self.home)
        (root / 'summary.json').write_text(json.dumps({'info': {'id': B}}))
        self.assertEqual(g.inventory(self.home), [])
        with self.assertRaises(ValueError):
            g.reply(A, self.home)

    def test_same_uuid_two_valid_paths_is_ambiguous(self):
        first = self.session(); self.session(cwd='%2Fother')
        self.chat(first, [{'role': 'assistant', 'content': 'Selected'}])
        notices = []
        self.assertEqual(g.inventory(self.home, notices), [])
        self.assertTrue(any(n['code'] == 'ambiguous-session' for n in notices))
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            g.reply(A, self.home)

    def test_explicit_child_id_parent_id_must_match_path_and_owner(self):
        root = self.session(A); self.session(B); self.session(C)
        self.child(root, B, declared_parent=C)
        self.child(root, C, declared_child=B)
        rows = g.inventory(self.home)
        self.assertTrue(all(r['parentId'] is None for r in rows))

    def test_nested_matching_summary_and_explicit_grandchild(self):
        root = self.session(A)
        nested = root / 'subagents' / B
        nested.mkdir(parents=True)
        (nested / 'summary.json').write_text(json.dumps({'info': {'id': B}}))
        self.session(C)
        self.child(nested, C)
        rows = {r['id']: r for r in g.inventory(self.home)}
        self.assertEqual(rows[B]['parentId'], A)
        self.assertEqual(rows[C]['parentId'], B)
        self.assertEqual(rows[C]['familyId'], A)

    def test_explicit_child_metadata_establishes_nested_parent(self):
        root = self.session(A); self.session(B); self.session(C)
        child = self.child(root, B)
        self.child(child, C)
        rows = {r['id']: r for r in g.inventory(self.home)}
        self.assertEqual(rows[B]['parentId'], A)
        self.assertEqual(rows[C]['parentId'], B)
        self.assertEqual(rows[C]['familyId'], A)

    def test_restored_parent_and_arbitrary_neighbor_meta_never_prove_ancestry(self):
        root = self.session(A, parent_session_id=B, parentSessionId=B)
        self.session(B)
        (root / 'meta.json').write_text(json.dumps({'parent_session_id': B, 'child_session_id': A}))
        rows = g.inventory(self.home)
        self.assertTrue(all(r['parentId'] is None for r in rows))

    def test_conflicting_parents_and_cycles_do_not_make_invented_family(self):
        first = self.session(A); second = self.session(B); self.session(C)
        self.child(first, C); self.child(second, C)
        self.child(first, B); self.child(second, A)
        notices = []
        rows = g.inventory(self.home, notices)
        self.assertTrue(all(r['parentId'] is None and r['familyId'] == r['id'] for r in rows))
        self.assertTrue({'ambiguous-parent', 'invalid-parent'}.issubset({n['code'] for n in notices}))

    def test_symlinked_session_and_data_root_are_rejected(self):
        root = self.session()
        linked = self.home / 'sessions' / '%2Fother'
        linked.mkdir()
        (linked / B).symlink_to(root, target_is_directory=True)
        self.assertEqual([r['id'] for r in g.inventory(self.home)], [A])
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(self.home, target_is_directory=True)
        self.assertEqual(g.inventory(alias), [])

    def test_symlinked_metadata_history_and_child_meta_are_rejected(self):
        root = self.session(A); second = self.session(B)
        self.chat(second, [{'role': 'assistant', 'content': 'PRIVATE B'}])
        (root / 'chat_history.jsonl').symlink_to(second / 'chat_history.jsonl')
        child = self.child(root, B)
        valid = child / 'saved-meta.json'
        (child / 'meta.json').rename(valid)
        (child / 'meta.json').symlink_to(valid)
        rows = {r['id']: r for r in g.inventory(self.home)}
        self.assertFalse(rows[A]['capabilities']['canReadReply'])
        self.assertIsNone(rows[B]['parentId'])
        with self.assertRaises(OSError):
            g.reply(A, self.home)
        (root / 'summary.json').unlink()
        (root / 'summary.json').symlink_to(second / 'summary.json')
        self.assertNotIn(A, [r['id'] for r in g.inventory(self.home)])

    def test_hardlinked_world_writable_and_fifo_history_are_rejected(self):
        root = self.session()
        history = root / 'chat_history.jsonl'
        self.chat(root, [{'role': 'assistant', 'content': 'Answer'}])
        os.link(history, root / 'hardlink')
        self.assertFalse(g.inventory(self.home)[0]['capabilities']['canReadReply'])
        with self.assertRaises(ValueError):
            g.reply(A, self.home)
        (root / 'hardlink').unlink(); history.chmod(0o666)
        with self.assertRaises(ValueError):
            g.reply(A, self.home)
        history.unlink(); os.mkfifo(history)
        self.assertFalse(g.inventory(self.home)[0]['capabilities']['canReadReply'])
        with self.assertRaises(ValueError):
            g.reply(A, self.home)

    def test_world_writable_directory_and_foreign_owner_rejected(self):
        root = self.session()
        root.chmod(0o777)
        self.assertEqual(g.inventory(self.home), [])
        root.chmod(0o755)
        original = os.fstat
        def foreign(fd):
            value = original(fd)
            return os.stat_result(tuple(value)[:4] + (os.getuid() + 1,) + tuple(value)[5:])
        with patch.object(g.os, 'fstat', foreign):
            self.assertEqual(g.inventory(self.home), [])

    def test_missing_history_does_not_use_acp_or_child_output_fallback(self):
        root = self.session()
        (root / 'updates.jsonl').write_text(json.dumps({'sessionUpdate': 'agent_message_chunk', 'content': {'text': 'UNVERIFIED CHUNK'}}))
        (root / 'output.json').write_text('PRIVATE OUTPUT')
        self.assertFalse(g.inventory(self.home)[0]['capabilities']['canReadReply'])
        with self.assertRaises(FileNotFoundError):
            g.reply(A, self.home)

    def test_malformed_oversized_and_nested_metadata_are_bounded(self):
        root = self.session()
        for raw in ('{', 'x' * (g.MAX_METADATA_BYTES + 1), '[' * 2000 + ']' * 2000):
            (root / 'summary.json').write_text(raw)
            notices = []
            self.assertEqual(g.inventory(self.home, notices), [])
            self.assertTrue(any(n['code'] == 'metadata-omitted' for n in notices))

    def test_root_scan_attempt_bound_includes_invalid_records(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'content': 'Answer'}])
        bad = self.session(B)
        (bad / 'summary.json').write_text('{')
        self.session(C)
        notices = []
        with patch.object(g, 'MAX_CANDIDATES', 2):
            rows = g.inventory(self.home, notices)
            self.assertEqual([r['id'] for r in rows], [A])
            self.assertFalse(rows[0]['capabilities']['canReadReply'])
            with self.assertRaisesRegex(ValueError, 'cannot verify'):
                g.reply(A, self.home)
        self.assertTrue(any(n['code'] == 'inventory-bound-reached' for n in notices))

    def test_directory_and_child_bounds_refuse_unproven_unique_reads(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'content': 'Answer'}])
        self.session(B); self.session(C)
        with patch.object(g, 'MAX_DIRECTORY_ENTRIES', 2):
            notices = []
            g.inventory(self.home, notices)
            self.assertTrue(any(n['code'] == 'inventory-bound-reached' for n in notices))
            with self.assertRaisesRegex(ValueError, 'cannot verify'):
                g.reply(A, self.home)
        self.child(root, B); self.child(root, C)
        with patch.object(g, 'MAX_CHILD_DIRECTORIES', 1):
            notices = []
            g.inventory(self.home, notices)
            self.assertTrue(any(n['code'] == 'ancestry-bound-reached' for n in notices))
            with self.assertRaisesRegex(ValueError, 'cannot verify'):
                g.reply(A, self.home)

    def test_exact_inventory_limit_does_not_claim_unseen_records(self):
        self.session(A); self.session(B)
        with patch.object(g, 'LIMIT', 2):
            notices = []
            self.assertEqual(len(g.inventory(self.home, notices)), 2)
            self.assertFalse(any(n['code'] == 'inventory-bound-reached' for n in notices))
        self.session(C)
        with patch.object(g, 'LIMIT', 2):
            notices = []
            self.assertEqual(len(g.inventory(self.home, notices)), 2)
            self.assertTrue(any(n['code'] == 'inventory-bound-reached' for n in notices))

    def test_malformed_oversized_and_partial_lines_mark_selected_history_truncated(self):
        root = self.session()
        raw = json.dumps({'role': 'assistant', 'content': 'Prior answer'}) + '\n'
        raw += '[' * 2000 + ']' * 2000 + '\n'
        raw += 'x' * (g.MAX_HISTORY_LINE + 1) + '\n'
        raw += '{"role":"assistant","content":"partial'
        (root / 'chat_history.jsonl').write_text(raw)
        result = g.reply(A, self.home)
        self.assertEqual(result['text'], 'Prior answer')
        self.assertTrue(result['truncated'])
        self.assertTrue(result['completionUnverified'])

    def test_tail_read_is_bounded_and_fallback_item_id_uses_stable_byte_offset(self):
        root = self.session()
        raw = ('x' * 200 + '\n' + json.dumps({'role': 'assistant', 'content': 'Latest 🧪'}, ensure_ascii=False) + '\n').encode()
        (root / 'chat_history.jsonl').write_bytes(raw)
        with patch.object(g, 'MAX_HISTORY_BYTES', 100):
            result = g.reply(A, self.home)
        self.assertEqual(result['text'], 'Latest 🧪')
        self.assertEqual(result['history'][0]['itemId'], 'grok-history:' + str(len(raw)))
        self.assertTrue(result['truncated'])

    def test_opaque_message_id_never_exposes_arbitrary_private_metadata(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'id': 'PRIVATE USER NAME / path', 'content': 'Answer'}])
        result = g.reply(A, self.home)
        self.assertTrue(result['history'][0]['itemId'].startswith('grok-history:'))
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_selected_summary_and_history_share_one_directory_descriptor(self):
        root = self.session()
        self.chat(root, [{'role': 'assistant', 'content': 'Exact A'}])
        original = g.Store.metadata
        captured = []
        def swap(store, relative, directory_fd=None):
            value = original(store, relative, directory_fd)
            if directory_fd is not None:
                captured.append(directory_fd)
                root.rename(root.parent / 'saved-original')
                root.mkdir()
                (root / 'summary.json').write_text(json.dumps({'info': {'id': B}}))
                self.chat(root, [{'role': 'assistant', 'content': 'WRONG ID'}])
            return value
        with patch.object(g.Store, 'metadata', swap):
            self.assertEqual(g.reply(A, self.home)['text'], 'Exact A')
        self.assertEqual(len(captured), 1)


if __name__ == '__main__':
    unittest.main()
