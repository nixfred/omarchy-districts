"""Synthetic Pi records only: never read real user messages or prompt a model."""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import provider_pi as pi

SID = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


def entry(eid, parent, role='assistant', text='answer'):
    return {'type': 'message', 'id': eid, 'parentId': parent,
            'timestamp': '2026-10-06T12:00:00Z',
            'message': {'role': role, 'content': [{'type': 'thinking', 'thinking': 'NEVER DISPLAY'},
                                               {'type': 'text', 'text': text},
                                               {'type': 'image', 'data': 'NEVER DISPLAY'}]}}


class PiAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.directory = self.root / '--fixture--'
        self.directory.mkdir()
        self.path = self.directory / ('stamp_' + SID + '.jsonl')

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, rows=(), sid=SID, extra=None, path=None):
        header = dict(type='session', version=3, id=sid, timestamp='2026-10-06T12:00:00Z',
                      cwd='/PRIVATE/PATH', **(extra or {}))
        (path or self.path).write_text(''.join(json.dumps(r) + '\n' for r in [header, *rows]))

    def history(self, **kwargs):
        return pi.history_pi(SID, home=self.root, **kwargs)

    def test_metadata_decodes_only_header_and_model_records(self):
        model = dict(type='model_change', id='model', parentId=None, provider='kimi-coding', modelId='k3')
        self.write([model, entry('reply', 'model', text='PRIVATE BODY'),
                    dict(type='session_info', id='name', parentId='reply', name='Named session')])
        decoder = json.loads
        decoded_types = []
        def decode(value):
            item = decoder(value)
            decoded_types.append(item['type'])
            return item
        with patch.object(pi.json, 'loads', side_effect=decode):
            result = pi.inventory_pi(self.root)
        # Only the header, model and explicit `/name` records are decoded.
        self.assertEqual(decoded_types, ['session', 'model_change', 'session_info'])
        record = result['sessions'][0]
        self.assertEqual(record['name'], 'Named session')
        self.assertEqual(record['label'], 'Named session')
        self.assertTrue(record['isKimi3'])
        self.assertEqual(record['modelId'], 'k3')
        self.assertEqual(record['modelProvider'], 'kimi-coding')
        self.assertFalse(record['capabilities']['canSend'])
        self.assertFalse(record['capabilities']['canMonitorLive'])
        self.assertIsNone(record['capabilities']['approvalPending'])
        self.assertEqual(record['status']['type'], 'unknown')
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_all_kimi_models_and_no_inferred_kimi_from_configuration(self):
        for model in ('k3', 'k3-256k', 'kimi-for-coding'):
            self.write([dict(type='model_change', id='m', parentId=None, provider='kimi-coding', modelId=model)])
            self.assertTrue(pi.inventory_pi(self.root)['sessions'][0]['isKimi3'])
        self.write([dict(type='model_change', id='m', parentId=None, provider='openai', modelId='gpt-5.5')])
        self.assertFalse(pi.inventory_pi(self.root)['sessions'][0]['isKimi3'])
        self.write()
        self.assertIsNone(pi.inventory_pi(self.root)['sessions'][0]['modelId'])

    def test_fork_and_entry_ancestry_never_become_agent_parentage(self):
        self.write([entry('parent-entry', None), entry('child-entry', 'parent-entry')],
                   extra={'parentSession': '/PRIVATE/PARENT/SESSION.jsonl'})
        record = pi.inventory_pi(self.root)['sessions'][0]
        self.assertTrue(record['forkAncestryRecorded'])
        self.assertIsNone(record['parentId'])
        self.assertEqual(record['familyId'], SID)
        self.assertFalse(record['capabilities']['canReadParent'])
        self.assertNotIn('/PRIVATE', json.dumps(record))

    def test_selected_stored_branch_and_text_roles_only(self):
        self.write([entry('a', None, 'user', 'question'), entry('b', 'a', text='abandoned'),
                    entry('system', 'b', 'system', 'SYSTEM SECRET'),
                    entry('new', 'a', text='selected'), entry('tool', 'new', 'toolResult', 'TOOL SECRET')])
        result = self.history()
        self.assertEqual([m['text'] for m in result['messages']], ['selected', 'question'])
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('NEVER DISPLAY', json.dumps(result))
        self.assertEqual(pi.latest_pi(SID, self.root)['text'], 'selected')
        self.assertIn('not live', result['source'])

    def test_reply_history_is_assistant_only_oldest_first_and_bounded(self):
        rows = [entry(str(i), str(i-1) if i else None, text=str(i)) for i in range(25)]
        rows.append(entry('private-user', '24', 'user', 'PRIVATE USER INPUT'))
        self.write(rows)
        result = pi.latest_pi(SID, self.root)
        self.assertEqual(result['text'], '24')
        self.assertEqual([h['text'] for h in result['history']], [str(i) for i in range(9, 25)])
        self.assertTrue(all(h['role'] == 'assistant' for h in result['history']))
        self.assertNotIn('PRIVATE USER INPUT', json.dumps(result))
        self.assertTrue(result['historyTruncated'])
        self.write([entry('a', None, text='a' * 40000), entry('b', 'a', text='b' * 40000)])
        result = pi.latest_pi(SID, self.root)
        self.assertEqual(len(result['history']), 1)
        self.assertLessEqual(sum(len(h['text']) for h in result['history']), pi.MAX_TEXT)
        self.assertTrue(result['historyTruncated'])

    def test_pages_are_bounded_and_snapshot_cursors_stale_on_append(self):
        rows = [entry(str(i), str(i-1) if i else None, 'assistant' if i % 2 else 'user', str(i)) for i in range(23)]
        self.write(rows)
        result = self.history(limit=8)
        seen = list(result['messages'])
        while result['hasMore']:
            self.assertLessEqual(len(result['messages']), 8)
            result = self.history(cursor=result['nextCursor'], limit=8)
            seen += result['messages']
        self.assertEqual([m['text'] for m in seen], [str(i) for i in range(22, -1, -1)])
        cursor = self.history(limit=1)['nextCursor']
        with self.path.open('a') as f:
            f.write(json.dumps(entry('appended', '22')) + '\n')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.history(cursor=cursor)

    def test_wrong_session_malformed_and_forged_cursor_rejected(self):
        self.write([entry('a', None), entry('b', 'a')])
        for cursor in ('../private', 'x' * 513, 'not_json',
                       base64.urlsafe_b64encode(json.dumps({'id': OTHER, 'snapshot': 'x', 'offset': 1}).encode()).decode().rstrip('=')):
            with self.assertRaises(ValueError):
                self.history(cursor=cursor)
        for limit in (True, 0, 17, '8'):
            with self.assertRaises(ValueError):
                self.history(limit=limit)
        for sid in ('../escape', '/tmp/private', '', 'a'*129):
            with self.assertRaises(ValueError):
                pi.latest_pi(sid, self.root)

    def test_total_page_text_and_individual_message_bounds(self):
        self.write([entry('a', None, text='a' * 40000), entry('b', 'a', text='b' * 40000)])
        result = self.history()
        self.assertEqual(len(result['messages']), 1)
        self.assertTrue(result['hasMore'])
        self.write([entry('a', None, text='a' * 80000)])
        result = self.history()
        self.assertEqual(len(result['messages'][0]['text']), pi.MAX_TEXT)
        self.assertTrue(result['truncated'])

    def test_incomplete_tail_is_excluded_from_selected_reply(self):
        self.write([entry('a', None, text='completed')])
        with self.path.open('ab') as f:
            f.write(b'{"type":"message","id":"partial"')
        result = pi.latest_pi(SID, self.root)
        self.assertEqual(result['text'], 'completed')
        self.assertTrue(result['truncated'])
        self.assertTrue(self.history()['message'])
        self.assertTrue(pi.inventory_pi(self.root)['notices'])

    def test_cycles_missing_ancestors_duplicates_and_malformed_rows(self):
        for rows in ([entry('a', 'a')], [entry('a', 'missing')], [entry('a', None), entry('a', None)],
                     [dict(type='message', id='a', parentId='../escape')], ['not-an-object']):
            self.write(rows)
            with self.assertRaises(ValueError):
                self.history()

    def test_duplicate_session_id_is_omitted_and_selected_read_rejected(self):
        self.write([entry('a', None)])
        self.write([entry('a', None)], path=self.directory / 'duplicate.jsonl')
        result = pi.inventory_pi(self.root)
        self.assertEqual(result['sessions'], [])
        self.assertIn('ambiguous-id', [n['code'] for n in result['notices']])
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            self.history()

    def test_unreadable_header_and_oversized_duplicate_do_not_hide_ambiguity(self):
        self.write([entry('a', None)])
        broken = self.directory / 'broken.jsonl'
        broken.write_text('not-json\n')
        with self.assertRaisesRegex(ValueError, 'exact selected identity'):
            self.history()
        broken.unlink()
        duplicate = self.directory / 'duplicate.jsonl'
        self.write(path=duplicate)
        with duplicate.open('a') as f:
            f.write('x' * 10000)
        with patch.object(pi, 'MAX_BYTES', self.path.stat().st_size + 10):
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                self.history()

    def test_symlink_file_directory_and_root_never_followed(self):
        self.write([entry('a', None)])
        other = self.root / 'outside.jsonl'
        self.path.rename(other)
        self.path.symlink_to(other)
        self.assertEqual(pi.inventory_pi(self.root)['sessions'], [])
        self.path.unlink()
        self.directory.rmdir()
        self.directory.symlink_to(self.root, target_is_directory=True)
        self.assertEqual(pi.inventory_pi(self.root)['sessions'], [])
        linked_root = self.root / 'linked'
        linked_root.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            pi.inventory_pi(linked_root)

    def test_format_size_entry_and_inventory_limits_report_bound(self):
        self.write(extra={'parentSession': None})
        with patch.object(pi, 'MAX_BYTES', 1):
            self.assertTrue(pi.inventory_pi(self.root)['notices'])
            with self.assertRaises(ValueError):
                self.history()
        self.write([entry('a', None), entry('b', 'a')])
        with patch.object(pi, 'MAX_ENTRIES', 1):
            with self.assertRaisesRegex(ValueError, 'entry bound'):
                self.history()
        with patch.object(pi, 'MAX_FILES', 1):
            self.assertTrue(pi.inventory_pi(self.root)['bounded'])
            with self.assertRaisesRegex(ValueError, 'bounded'):
                self.history()
        with patch.object(pi, 'MAX_INVENTORY_BYTES', 1):
            result = pi.inventory_pi(self.root)
            self.assertTrue(result['bounded'])
            self.assertIn('metadata-budget', [n['code'] for n in result['notices']])
        self.path.write_text(json.dumps({'type':'session','version':1,'id':SID})+'\n')
        self.assertEqual(pi.inventory_pi(self.root)['sessions'], [])


if __name__ == '__main__':
    unittest.main()
