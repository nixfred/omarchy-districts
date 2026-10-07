import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('sessions', Path(__file__).resolve().parents[1] / 'sessions.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
A='11111111-1111-4111-8111-111111111111'
B='22222222-2222-4222-8222-222222222222'
C='33333333-3333-4333-8333-333333333333'
M='44444444-4444-4444-8444-444444444444'
EMPTY_EXTRAS=(lambda **kw:[],lambda:{'sessions':[],'notices':[],'bounded':False,'provider':{'provider':'pi','canSend':False,'reason':'Stored only'}},lambda **kw:[])


def thread(sid=A, parent=None, status=None, direct=True):
    return {'id':sid,'parentThreadId':parent,'sessionId':A,'status':status or {'type':'idle'},
            'canAcceptDirectInput':direct,'preview':'PRIVATE PROMPT','name':'PRIVATE TITLE','cwd':'/private/path'}


def fixture_id(number):
    return '00000000-0000-4000-8000-%012d' % number


class InventoryConnection:
    def __init__(self, loaded=(), recent=(), cursor=None):
        self.loaded=list(loaded);self.recent=list(recent);self.cursor=cursor;self.calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def call(self,method,params):
        self.calls.append((method,params))
        if method=='thread/loaded/list':return {'data':self.loaded}
        if method=='thread/list':return {'data':[thread(sid)for sid in self.recent],'nextCursor':self.cursor}
        if method=='thread/read':return {'thread':thread(params['threadId'])}
        raise AssertionError(method)


class Connection:
    def __init__(self, status=None, direct=True, loaded=True):
        self.calls=[]; self.status=status;self.direct=direct;self.loaded=loaded
    def call(self, method, params):
        self.calls.append((method,params))
        if method=='thread/loaded/list':return {'data':[A]if self.loaded else[]}
        if method=='thread/read':return {'thread':thread(status=self.status,direct=self.direct)}
        if method=='thread/queue/add':return {'queuedSubmission':{'id':'submission-1'}}
        if method=='thread/items/list':return {'data':[{'type':'agentMessage','id':'c','phase':'commentary','text':'ongoing'},
            {'type':'reasoning','text':'PRIVATE REASONING'},{'type':'agentMessage','id':'final','phase':'final_answer','text':'Selected reply'}]}
        raise AssertionError(method)


class Sessions(unittest.TestCase):
    def test_loaded_inventory_reports_cap_without_cursor(self):
        for count in (s.LIMIT,s.LIMIT+1):
            c=InventoryConnection(loaded=[fixture_id(i)for i in range(count)])
            notices=[]
            with patch.object(s,'spawn_metadata',return_value=[]):
                rows,bounded=s.codex_inventory(c,notices)
            self.assertTrue(bounded);self.assertEqual(len(rows),s.LIMIT)
            self.assertTrue(any(n['code']=='inventory-bound-reached'and 'Loaded' in n['reason']for n in notices))
            self.assertFalse(any(p.get('includeTurns')for m,p in c.calls))

    def test_recent_inventory_reports_cap_and_combined_truncation(self):
        c=InventoryConnection(loaded=[fixture_id(i)for i in range(110)],recent=[fixture_id(i)for i in range(200,233)])
        notices=[]
        with patch.object(s,'spawn_metadata',return_value=[]):rows,bounded=s.codex_inventory(c,notices)
        self.assertTrue(bounded);self.assertEqual(len(rows),s.LIMIT)
        self.assertTrue(any(n['code']=='inventory-bound-reached'and 'Recent' in n['reason']for n in notices))
        self.assertTrue(any(n['code']=='inventory-truncated'for n in notices))

    def test_small_inventory_does_not_claim_truncation(self):
        notices=[]
        with patch.object(s,'spawn_metadata',return_value=[]):rows,bounded=s.codex_inventory(InventoryConnection([A],[B]),notices)
        self.assertFalse(bounded);self.assertEqual(len(rows),2);self.assertEqual(notices,[])

    def test_provider_cursor_reports_unseen_page_even_below_cap(self):
        notices=[]
        with patch.object(s,'spawn_metadata',return_value=[]):
            rows,bounded=s.codex_inventory(InventoryConnection([A],[B],cursor='additional-page'),notices)
        self.assertTrue(bounded);self.assertEqual(len(rows),2)
        self.assertTrue(any('one page' in n['reason']for n in notices))

    def test_parent_metadata_cap_is_reported_readonly(self):
        with tempfile.TemporaryDirectory()as home:
            path=Path(home)/'state_5.sqlite';db=sqlite3.connect(path)
            db.execute('CREATE TABLE thread_spawn_edges(parent_thread_id TEXT,child_thread_id TEXT)')
            db.execute('CREATE TABLE threads(id TEXT,source TEXT,updated_at INT)')
            db.executemany('INSERT INTO thread_spawn_edges VALUES(?,?)',[(A,fixture_id(i))for i in range(33)])
            db.commit();db.close();before=path.read_bytes();notices=[]
            edges=s.spawn_metadata(home,notices)
            self.assertEqual(len(edges),32);self.assertEqual(path.read_bytes(),before)
            self.assertTrue(any(n['code']=='ancestry-bound-reached'for n in notices))
            def bounded_edges(*args,**kwargs):
                kwargs['notices'].extend(notices);return edges
            with patch.object(s,'spawn_metadata',side_effect=bounded_edges):
                rows,bounded=s.codex_inventory(InventoryConnection(),[])
            self.assertTrue(bounded);self.assertEqual(len(rows),33)

    def test_claude_cap_reports_metadata_only_notice(self):
        class Result:returncode=0;stdout=json.dumps([{'sessionId':fixture_id(i),'state':'working','name':'PRIVATE','cwd':'/private'}for i in range(129)])
        notices=[];rows=s.claude_inventory(lambda *a,**k:Result(),notices)
        self.assertEqual(len(rows),s.LIMIT)
        self.assertEqual(notices[0]['provider'],'claude');self.assertIn('may be omitted',notices[0]['reason'])
        self.assertNotIn('PRIVATE',json.dumps([rows,notices]))

    def test_inventory_preserves_provider_reasons_and_bounds(self):
        def claude(*args,**kwargs):
            s.inventory_notice(kwargs['notices'],'claude','inventory-bound-reached','Claude metadata bound reached; additional sessions may be omitted.')
            return [s.codex_record(thread(B),False)|{'provider':'claude'}]
        with patch.object(s,'spawn_metadata',return_value=[]),patch.object(s,'claude_inventory',side_effect=claude):
            result=s.inventory(lambda:InventoryConnection([A]),extra_factories=EMPTY_EXTRAS)
        self.assertTrue(result['bounded']);self.assertEqual(len(result['sessions']),2)
        unsupported={p['provider']:p for p in result['unsupportedProviders']}
        self.assertEqual(set(unsupported),{'codex-desktop','herdr','kimi-native'})
        self.assertIn('separate namespace',unsupported['codex-desktop']['reason'])
        self.assertTrue(all(not p['canSend']for p in unsupported.values()))
        for p in result['providers']:
            if not p['canSend']:
                self.assertTrue(any(n['provider']==p['provider']and n['reason']==p['reason']for n in result['notices']))
        self.assertNotIn('PRIVATE',json.dumps(result))

    def test_inventory_omits_private_data(self):
        row=s.codex_record(thread(B,A),True)
        self.assertEqual(row['parentId'],A);self.assertEqual(row['familyId'],A)
        encoded=json.dumps(row)
        for private in ['PRIVATE','preview','name','cwd','pid','window']:
            self.assertNotIn(private,encoded)
        self.assertTrue(row['capabilities']['canSend'])

    def test_source_parent_is_declared_not_pid(self):
        t=thread(B);t['source']={'subAgent':{'thread_spawn':{'parent_thread_id':A,'depth':1}}}
        self.assertEqual(s.codex_record(t)['parentId'],A)
        t['source']={'subAgent':{'other':'guardian'}}
        self.assertIsNone(s.codex_record(t)['parentId'])

    def test_stored_not_live(self):
        row=s.codex_record(thread(status={'type':'notLoaded'}),False)
        self.assertEqual(row['availability'],'stored');self.assertFalse(row['capabilities']['canSend'])

    def test_waiting_flags_block_send(self):
        for flag in ['waitingOnApproval','waitingOnUserInput']:
            c=Connection(status={'type':'active','activeFlags':[flag]})
            with self.assertRaises(ValueError):s.send_codex(c,A,'Do work',M)
            self.assertNotIn('thread/queue/add',[m for m,p in c.calls])

    def test_exact_loaded_direct_guard(self):
        for c in [Connection(loaded=False),Connection(direct=False),Connection(status={'type':'systemError'}),Connection(status={'type':'active','activeFlags':['unknownFutureBlockingFlag']})]:
            with self.assertRaises(ValueError):s.send_codex(c,A,'Do work',M)
            self.assertNotIn('thread/queue/add',[m for m,p in c.calls])

    def test_send_queue_no_permissions_override(self):
        c=Connection();r=s.send_codex(c,A,'User instruction\nsecond line',M)
        self.assertEqual(r['state'],'queued')
        method,params=c.calls[-1]
        self.assertEqual(method,'thread/queue/add');self.assertEqual(params['threadId'],A)
        self.assertEqual(params['clientUserMessageId'],M)
        self.assertEqual(set(params),{'threadId','clientUserMessageId','input'})
        self.assertEqual(params['input'][0]['text'],'User instruction\nsecond line')
        self.assertNotIn('approval',json.dumps(params))
        self.assertEqual([m for m,p in c.calls],['thread/loaded/list','thread/read','thread/queue/add'])

    def test_missing_submission_identity_stays_uncertain_without_retry(self):
        for acknowledgement in (None, [], {}, {'id':None}, {'id':''}, {'id':'  \t'}, {'id':0}, {'id':True}, {'id':[]}):
            with self.subTest(acknowledgement=acknowledgement):
                c=Connection();original=c.call
                def call(method,params):
                    if method=='thread/queue/add':
                        c.calls.append((method,params))
                        return {'queuedSubmission':acknowledgement}
                    return original(method,params)
                c.call=call
                with self.assertRaisesRegex(RuntimeError,'delivery uncertain'):
                    s.send_codex(c,A,'Exact unchanged draft',M)
                self.assertEqual([m for m,p in c.calls],['thread/loaded/list','thread/read','thread/queue/add'])
                self.assertEqual(c.calls[-1][1]['clientUserMessageId'],M)

    def test_bad_identity_or_input_before_send(self):
        for sid in ['--last','../file','name;command',None,'123']:
            with self.assertRaises(ValueError):s.send_codex(Connection(),sid,'Hello',M)
        for text in ['', ' ', 'a'*8193,'a\x00b',None]:
            with self.assertRaises(ValueError):s.send_codex(Connection(),A,text,M)

    def test_selected_reply_only(self):
        c=Connection();r=s.latest_codex(c,A)
        self.assertEqual(r['text'],'Selected reply')
        self.assertEqual(c.calls,[('thread/items/list',{'threadId':A,'limit':64,'sortDirection':'desc'})])

    def test_reply_uses_supported_bounded_turns_fallback(self):
        calls=[]
        def call(method,params):
            calls.append((method,params))
            if method=='thread/items/list':raise s.CodexRpcError(-32601)
            return {'data':[{'id':'new','status':'completed','items':[{'id':'a','type':'agentMessage','text':'older same-turn'}, {'id':'b','type':'agentMessage','phase':'final_answer','text':'Latest selected reply'}]}, {'items':[{'type':'agentMessage','text':'Old turn'}]}]}
        c=Connection();c.call=call;r=s.latest_codex(c,A)
        self.assertEqual(r['text'],'Latest selected reply');self.assertIn('thread/turns/list',r['source'])
        self.assertEqual(calls[-1],('thread/turns/list',{'threadId':A,'limit':4,'itemsView':'full','sortDirection':'desc'}))

    def test_reply_full_read_fallback_only_if_methods_unavailable(self):
        calls=[]
        def call(method,params):
            calls.append((method,params))
            if method!='thread/read':raise s.CodexRpcError(-32601)
            return {'thread':{'id':A,'turns':[{'items':[{'type':'agentMessage','text':'Old reply'}]}, {'status':'completed','items':[{'type':'agentMessage','text':'Latest reply'}]}]}}
        c=Connection();c.call=call;r=s.latest_codex(c,A)
        self.assertEqual(r['text'],'Latest reply');self.assertIn('8MiB',r['source'])
        self.assertEqual(calls[-1],('thread/read',{'threadId':A,'includeTurns':True}))

    def test_invalid_thread_never_tries_other_read_routes(self):
        c=Connection();calls=[]
        def call(method,params):calls.append(method);raise s.CodexRpcError(-32600)
        c.call=call
        with self.assertRaises(s.CodexRpcError):s.latest_codex(c,A)
        self.assertEqual(calls,['thread/items/list'])

    def test_reply_fallback_identity_guard(self):
        c=Connection()
        def call(method,params):
            if method!='thread/read':raise s.CodexRpcError(-32601)
            return {'thread':{'id':B,'turns':[{'items':[{'type':'agentMessage','text':'Wrong session'}]}]}}
        c.call=call
        with self.assertRaises(ValueError):s.latest_codex(c,A)

    def test_rpc_error_never_exposes_provider_private_contents(self):
        error=s.CodexRpcError(-32600,'thread not found PRIVATE CONTENT')
        self.assertEqual(error.category,'session-unavailable');self.assertNotIn('PRIVATE',str(error))

    def test_reply_bound_is_explicit(self):
        c=Connection();c.call=lambda m,p:{'data':[{'type':'agentMessage','text':'x'*(s.MAX_REPLY+1)}]}
        r=s.latest_codex(c,A)
        self.assertTrue(r['truncated']);self.assertEqual(len(r['text']),s.MAX_REPLY)

    def test_spawns_readonly_and_family(self):
        with tempfile.TemporaryDirectory()as d:
            db=sqlite3.connect(Path(d)/'state_5.sqlite')
            db.execute('CREATE TABLE thread_spawn_edges(parent_thread_id TEXT,child_thread_id TEXT,status TEXT)')
            db.execute('CREATE TABLE threads(id TEXT,source TEXT,updated_at INT)')
            db.execute('INSERT INTO thread_spawn_edges VALUES(?,?,?)',(A,B,'open'))
            db.execute('INSERT INTO threads VALUES(?,?,1)',(C,json.dumps({'subagent':{'thread_spawn':{'parent_thread_id':B}}})))
            db.commit();db.close();edges=s.spawn_metadata(d)
            self.assertEqual({r['id']:r['parentId']for r in edges},{B:A,C:B})
            rows={i:s.codex_record(thread(i,p))for i,p in [(A,None),(B,A),(C,B)]}
            s.assign_families(rows);self.assertEqual(rows[C]['familyId'],A)
            db=sqlite3.connect(Path(d)/'state_5.sqlite');self.assertEqual(db.execute('select count(*)from thread_spawn_edges').fetchone()[0],1)

    def test_cyclic_ancestry_not_accepted(self):
        rows={i:s.codex_record(thread(i,p))for i,p in [(A,B),(B,A)]}
        s.assign_families(rows);self.assertTrue(any(r['parentId']is None for r in rows.values()))

    def test_claude_only_exact_selected_assistant_text(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'projects/example';p.mkdir(parents=True)
            rows=[{'type':'assistant','sessionId':B,'message':{'content':[{'type':'text','text':'Wrong session'}]}},
                  {'type':'assistant','sessionId':A,'message':{'content':[{'type':'thinking','thinking':'PRIVATE'}, {'type':'text','text':'Selected stored reply'}]}}]
            (p/(A+'.jsonl')).write_text('\n'.join(map(json.dumps,rows)))
            (p/(B+'.jsonl')).write_text('DO NOT READ ME')
            self.assertEqual(s.latest_claude(A,d)['text'],'Selected stored reply')

    def test_claude_transcript_escape_rejected(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'projects/example';p.mkdir(parents=True)
            external=Path(d)/'outside';external.write_text('secret')
            (p/(A+'.jsonl')).symlink_to(external)
            with self.assertRaises(ValueError):s.latest_claude(A,d)

    def test_claude_inventory_reports_actual_state_no_parent_guess(self):
        class Result:returncode=0;stdout=json.dumps([{'sessionId':A,'state':'working','name':'private','cwd':'/private'}])
        result=s.claude_inventory(lambda *a,**k:Result())
        self.assertEqual(result[0]['status']['type'],'working');self.assertIsNone(result[0]['parentId'])
        self.assertFalse(result[0]['capabilities']['canSend']);self.assertNotIn('private',json.dumps(result))

if __name__=='__main__':unittest.main()
