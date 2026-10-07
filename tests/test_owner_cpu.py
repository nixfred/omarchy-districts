import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('owner_cpu',Path(__file__).resolve().parents[1]/'districts.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)

class CpuTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.sampler=bridge.OwnerCpuSampler(self.root)
  self.windows=[{'pid':42},{'pid':42},{'pid':None},{'pid':-1}]
 def tearDown(self):self.temp.cleanup()
 def stat(self,ticks,start=100):
  p=self.root/'42';p.mkdir(exist_ok=True);fields=['0']*50;fields[0]='R';fields[11]=str(ticks);fields[12]='0';fields[19]=str(start)
  (p/'stat').write_text('42 (owner name with ) spaces) '+' '.join(fields))
 def test_deduplicated_cadence_and_owner_scope(self):
  self.stat(0);self.sampler.sample(self.windows,0);self.assertEqual(self.sampler.reads,1)
  self.assertEqual(self.windows[0]['ownerCpu']['state'],'sampling');self.assertEqual(self.windows[2]['ownerCpu']['state'],'unavailable')
  self.stat(os.sysconf('SC_CLK_TCK')*10);self.sampler.sample(self.windows,1);self.assertEqual(self.sampler.reads,1)
  self.sampler.sample(self.windows,2.5);cpu=self.windows[0]['ownerCpu'];self.assertEqual(cpu['state'],'measured');self.assertEqual(cpu['percent'],400)
  self.assertEqual(cpu['level'],1);self.assertEqual(self.windows[1]['ownerCpu'],cpu);self.assertEqual(cpu['scope'],'window-owner-process');self.assertEqual(cpu['startTime'],100)
 def test_smoothing_idle_and_pid_reuse(self):
  self.stat(0);self.sampler.sample(self.windows,0)
  self.stat(int(os.sysconf('SC_CLK_TCK')*2.5));self.sampler.sample(self.windows,2.5)
  cpu=self.windows[0]['ownerCpu'];self.assertEqual(cpu['percent'],100);self.assertGreater(cpu['level'],.3);self.assertLess(cpu['level'],.4)
  old=cpu['smoothedPercent'];self.sampler.sample(self.windows,5);self.assertEqual(self.windows[0]['ownerCpu']['percent'],0);self.assertLess(self.windows[0]['ownerCpu']['smoothedPercent'],old)
  self.stat(0,start=200);self.sampler.sample(self.windows,7.5);self.assertEqual(self.windows[0]['ownerCpu']['state'],'sampling');self.assertEqual(self.windows[0]['ownerCpu']['startTime'],200)
 def test_unavailable_and_pruned_owners(self):
  self.sampler.sample(self.windows,0);self.assertEqual(self.windows[0]['ownerCpu']['state'],'unavailable')
  self.stat(0);self.sampler.sample(self.windows,2.5);self.assertEqual(self.windows[0]['ownerCpu']['state'],'sampling')
  self.sampler.sample([],5);self.assertEqual(self.sampler.history,{})
 def test_malformed_counters_and_invalid_pid(self):
  (self.root/'42').mkdir();(self.root/'42/stat').write_text('invalid')
  self.sampler.sample(self.windows+ [{'pid':True},{'pid':2147483648},{'pid':'42'}],0)
  self.assertEqual(self.windows[0]['ownerCpu']['state'],'unavailable')

if __name__=='__main__':unittest.main()
