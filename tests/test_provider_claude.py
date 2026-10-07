import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('provider_claude',Path(__file__).resolve().parents[1]/'provider_claude.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
A='11111111-1111-4111-8111-111111111111';B='22222222-2222-4222-8222-222222222222';CH='a123456789abcdef0'

def row(text,sid=A,agent=None):
 r={'type':'assistant','sessionId':sid,'uuid':'reply','message':{'content':[{'type':'thinking','thinking':'PRIVATE'}, {'type':'text','text':text}]}}
 if agent:r.update(agentId=agent,isSidechain=True)
 return r

class Claude(unittest.TestCase):
 def fixture(self,home,child=False):
  root=Path(home)/'projects'/'project';root.mkdir(parents=True,exist_ok=True)
  if child:
   root=root/A/'subagents';root.mkdir(parents=True,exist_ok=True)
   path=root/('agent-'+CH+'.jsonl');path.with_suffix('.meta.json').write_text(json.dumps({'agentType':'Engineer','description':'PRIVATE','spawnDepth':2,'toolUseId':'private'}))
  else:path=root/(A+'.jsonl')
  return path
 def test_history_is_selected_assistant_only(self):
  with tempfile.TemporaryDirectory()as h:
   path=self.fixture(h);path.write_text('\n'.join(map(json.dumps,[row('old'),{'type':'user','sessionId':A,'message':{'content':'PRIVATE'}},row('wrong',B),row('latest')]))+'\n')
   r=p.reply(A,h);self.assertEqual(r['text'],'latest');self.assertEqual([x['text']for x in r['history']],['old','latest']);self.assertNotIn('PRIVATE',json.dumps(r))
 def test_subagent_exact_identity_not_root_or_sibling(self):
  with tempfile.TemporaryDirectory()as h:
   f=self.fixture(h,True);f.write_text('\n'.join(map(json.dumps,[row('wrong'),row('wrong-child',agent='sibling'),row('selected',agent=CH)])))
   r=p.reply(A+':'+CH,h);self.assertEqual(r['text'],'selected');self.assertEqual(len(r['history']),1)
 def test_metadata_never_reads_transcript_body_or_invents_nested_parent(self):
  with tempfile.TemporaryDirectory()as h:
   f=self.fixture(h,True);f.write_text('DO NOT DECODE THIS PRIVATE CHAT')
   real=p.safe_open
   def metadata_only(path,root):
    self.assertEqual(path.suffix,'.json');return real(path,root)
   with patch.object(p,'safe_open',metadata_only):r=p.subagent_inventory(home=h)
   child=next(x for x in r if x['isSubagent']);self.assertIsNone(child['parentId']);self.assertEqual(child['familyId'],A);self.assertEqual(child['availability'],'stored');self.assertEqual(child['status']['type'],'unknown');self.assertFalse(child['capabilities']['canSend']);self.assertNotIn('PRIVATE',json.dumps(r))
 def test_compaction_is_omitted(self):
  with tempfile.TemporaryDirectory()as h:
   f=self.fixture(h,True);f.write_text('');f.with_suffix('.meta.json').write_text('{"agentType":"compaction"}')
   self.assertEqual(p.subagent_inventory(home=h),[])
 def test_bounds_keep_latest_without_overflow(self):
  with tempfile.TemporaryDirectory()as h:
   f=self.fixture(h);f.write_text('\n'.join(json.dumps(row(str(i)))for i in range(20)))
   r=p.reply(A,h);self.assertEqual(len(r['history']),16);self.assertEqual(r['text'],'19');self.assertTrue(r['truncated'])
   f.write_text(json.dumps(row('x'*70000)));r=p.reply(A,h);self.assertEqual(sum(len(x['text'])for x in r['history']),65536);self.assertTrue(r['truncated'])
 def test_duplicate_and_symlink_paths_fail(self):
  with tempfile.TemporaryDirectory()as h:
   f=self.fixture(h);f.write_text(json.dumps(row('valid')));other=Path(h)/'projects'/'other';other.mkdir();(other/f.name).write_text(f.read_text())
   with self.assertRaises(ValueError):p.reply(A,h)
   (other/f.name).unlink();f.unlink();outside=Path(h)/'outside';outside.write_text(json.dumps(row('PRIVATE')));f.symlink_to(outside)
   with self.assertRaises(ValueError):p.reply(A,h)
 def test_parent_directory_symlink_is_rejected(self):
  with tempfile.TemporaryDirectory()as h:
   root=Path(h)/'projects';root.mkdir();outside=Path(h)/'outside';outside.mkdir();(outside/(A+'.jsonl')).write_text(json.dumps(row('PRIVATE')));(root/'project').symlink_to(outside)
   with self.assertRaises(ValueError):p.reply(A,h)
 def test_provider_home_symlink_rejected(self):
  with tempfile.TemporaryDirectory()as h:
   actual=Path(h)/'actual';actual.mkdir();f=self.fixture(actual);f.write_text(json.dumps(row('PRIVATE')));link=Path(h)/'link';link.symlink_to(actual)
   with self.assertRaises(ValueError):p.reply(A,link)
 def test_shared_write_and_hardlink_rejected(self):
  with tempfile.TemporaryDirectory()as h:
   f=self.fixture(h);f.write_text(json.dumps(row('PRIVATE')));f.chmod(0o666)
   with self.assertRaises(ValueError):p.reply(A,h)
   f.chmod(0o600);__import__('os').link(f,Path(h)/'hardlink')
   with self.assertRaises(ValueError):p.reply(A,h)
 def test_selected_lookup_incomplete_fails_closed(self):
  with tempfile.TemporaryDirectory()as h:
   f=self.fixture(h);f.write_text(json.dumps(row('valid')))
   for index in range(256):(Path(h)/'projects'/str(index)).mkdir()
   with self.assertRaises(ValueError):p.reply(A,h)
 def test_identity_injection_rejected(self):
  for bad in ['../file',A+':../child',A+':x:y',None,A+':',A+':child;cmd']:
   with self.assertRaises(ValueError):p.identity(bad)

if __name__=='__main__':unittest.main()
