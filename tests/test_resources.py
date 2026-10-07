import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('resources', Path(__file__).resolve().parents[1] / 'resources.py')
resources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resources)


class ResourceTests(unittest.TestCase):
 def setUp(self):
  self.temp = tempfile.TemporaryDirectory()
  self.root = Path(self.temp.name)
  self.proc = self.root / '42'
  self.proc.mkdir()
  self.write_stat()
  (self.proc / 'status').write_text('Name:\tPRIVATE\nVmRSS:\t2048 kB\nVmSize:\t8192 kB\nThreads:\t4\n')
  (self.proc / 'fd').mkdir()
  for number in range(3): (self.proc / 'fd' / str(number)).symlink_to('/private/never/read')
  self.clients = [{'pid':42, 'address':'0xabc', 'class':'Code', 'mapped':True}]
  self.queries = 0
 def tearDown(self): self.temp.cleanup()
 def write_stat(self, start=100):
  fields=['0']*50;fields[0]='R';fields[11]='123';fields[12]='45';fields[19]=str(start)
  (self.proc/'stat').write_text('42 (PRIVATE (owner) name ) '+' '.join(fields))
 def query(self, name):
  self.assertEqual(name, 'clients');self.queries+=1;return self.clients
 def inspect(self, **kwargs):
  return resources.inspect(42, '0xabc', query=self.query, proc_root=self.root, now=lambda:1234, **kwargs)
 def test_exact_owner_counters_and_no_private_names(self):
  result=self.inspect(expected_start=100,app='Code')
  self.assertEqual(self.queries,2)
  self.assertEqual(result['residentBytes'],2097152);self.assertEqual(result['virtualBytes'],8388608)
  self.assertEqual(result['threads'],4);self.assertEqual(result['fileDescriptors'],3)
  self.assertEqual(result['startTime'],100);self.assertEqual(result['observedAt'],1234000)
  self.assertEqual(result['userTicks'],123);self.assertEqual(result['systemTicks'],45)
  self.assertEqual(result['scope'],'window-owner-process')
  self.assertNotIn('PRIVATE',str(result));self.assertNotIn('command',result)
 def test_reject_invalid_pid_and_address_before_query(self):
  for pid in [True,-1,0,2147483648,'42']:
   with self.assertRaises(ValueError): resources.inspect(pid,'0xabc',query=self.query,proc_root=self.root)
  for address in ['abc','0xabc;exec','0x'+'a'*17,None]:
   with self.assertRaises(ValueError): resources.inspect(42,address,query=self.query,proc_root=self.root)
  self.assertEqual(self.queries,0)
 def test_reject_stale_window_owner_and_app(self):
  for patch in [{'pid':43},{'pid':True},{'mapped':False},{'hidden':True},{'class':'Other'}]:
   self.clients=[dict(pid=42,address='0xabc',mapped=True,**{k:v for k,v in patch.items() if k not in ('pid','mapped')})]
   self.clients[0].update(patch)
   with self.assertRaises(ValueError): self.inspect(app='Code')
 def test_reject_duplicate_owners(self):
  self.clients*=2
  with self.assertRaises(ValueError): self.inspect()
 def test_reject_previous_process_identity(self):
  with self.assertRaises(ValueError): self.inspect(expected_start=99)
 def test_reject_pid_reuse_during_observation(self):
  original=resources.stat_counters
  calls=[]
  def stat(path,pid):
   value=original(path,pid);calls.append(value)
   if len(calls)==2:value['startTime']=999
   return value
  from unittest.mock import patch
  with patch.object(resources,'stat_counters',stat):
   with self.assertRaisesRegex(ValueError,'during observation'):self.inspect()
 def test_reject_compositor_owner_change_during_observation(self):
  def query(name):
   self.queries+=1
   return self.clients if self.queries==1 else [dict(self.clients[0],pid=43)]
  with self.assertRaises(ValueError):resources.inspect(42,'0xabc',query=query,proc_root=self.root)
 def test_optional_counters_unavailable(self):
  (self.proc/'status').unlink()
  for p in (self.proc/'fd').iterdir():p.unlink()
  (self.proc/'fd').rmdir()
  result=self.inspect()
  self.assertIsNone(result['residentBytes']);self.assertIsNone(result['threads']);self.assertIsNone(result['fileDescriptors'])
 def test_bounded_file_descriptor_count(self):
  from unittest.mock import patch
  with patch.object(resources,'FD_LIMIT',2):result=self.inspect()
  self.assertEqual(result['fileDescriptors'],2);self.assertTrue(result['fileDescriptorsCapped'])
 def test_bound_core_and_optional_read(self):
  (self.proc/'status').write_text('x'*(resources.READ_LIMIT+1))
  self.assertIsNone(self.inspect()['residentBytes'])
  (self.proc/'stat').write_text('x'*(resources.READ_LIMIT+1))
  with self.assertRaises(ValueError):self.inspect()
 def test_other_user_rejected(self):
  with self.assertRaises(ValueError):self.inspect(uid=-1)
 def test_cli_invalid_input_is_json_error_no_query(self):
  result=subprocess.run([sys.executable,str(Path(resources.__file__)), '-1','0xabc'],capture_output=True,text=True)
  import json
  self.assertEqual(result.returncode,1);self.assertFalse(json.loads(result.stdout)['ok'])
  self.assertEqual(result.stderr,'')


if __name__=='__main__':unittest.main()
