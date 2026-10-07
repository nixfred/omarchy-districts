import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('sessions',Path(__file__).resolve().parents[1]/'sessions.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
A='11111111-1111-4111-8111-111111111111'

class Providers(unittest.TestCase):
 def test_fair_cap_preserves_every_provider(self):
  groups=[[{'id':str(i),'provider':p,'availability':'stored'}for i in range(128)]for p in ['codex','claude','grok','pi']]
  rows,bounded=s.fair_sessions(groups);self.assertTrue(bounded);self.assertEqual(len(rows),128);self.assertEqual({p:sum(r['provider']==p for r in rows)for p in ['codex','claude','grok','pi']},{p:32 for p in ['codex','claude','grok','pi']})
 def test_provider_ids_are_namespaced(self):
  rows,bounded=s.fair_sessions([[{'id':A,'provider':'codex'},{'id':A,'provider':'codex'}],[{'id':A,'provider':'claude'}]])
  self.assertFalse(bounded);self.assertEqual(len(rows),2)
 def test_live_records_before_stored_within_provider(self):
  rows,bounded=s.fair_sessions([[{'id':'stored','provider':'p','availability':'stored'},{'id':'live','provider':'p','availability':'live'}]],limit=1)
  self.assertEqual(rows[0]['id'],'live');self.assertTrue(bounded)
 def test_bounded_history_latest_and_budget(self):
  items=[({'type':'agentMessage','text':'latest','id':'a'},'completed'),({'type':'reasoning','text':'PRIVATE'},None),({'type':'agentMessage','phase':'commentary','text':'PRIVATE'},None),({'type':'agentMessage','text':'old','id':'b'},'completed')]
  r=s.with_history(A,items,'fixture');self.assertEqual(r['text'],'latest');self.assertEqual([m['text']for m in r['history']],['old','latest']);self.assertNotIn('PRIVATE',str(r))
  r=s.with_history(A,[(dict(type='agentMessage',text='x'*70000),None)],'fixture');self.assertEqual(sum(len(m['text'])for m in r['history']),65536);self.assertTrue(r['truncated'])
 def test_metrics_exact_read_only_method_and_units(self):
  class C:
   calls=[]
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def call(self,method,params):
    self.calls.append((method,params));return {'accountId':'PRIVATE','ordinaryUsageAllowed':None,'rateLimits':{'primary':{'usedPercent':50,'windowDurationMins':300,'resetsAt':1900000000}},'rateLimitUpsell':{'private':'PRIVATE'}}
  now=1900000000000-2*3600000
  collector=lambda **kw:{'providers':[{'provider':p,'metric':{}}for p in ['grok','claude','codex','kimi']]}
  r=s.metrics(C,collector,now);codex=next(x for x in r['providers']if x['provider']=='codex')
  self.assertEqual(C.calls,[('account/rateLimits/read',{})]);self.assertEqual(codex['metric']['allowanceUsed'],.5);self.assertEqual(codex['metric']['resetAt'],1900000000000);self.assertEqual(codex['metric']['pace']['signedSeconds'],1800);self.assertIsNone(codex['ordinaryUsageAllowed']);self.assertNotIn('PRIVATE',str(r))
 def test_failed_live_read_preserves_cache_stamp(self):
  class C:
   def __enter__(self):raise RuntimeError('offline')
   def __exit__(self,*a):pass
  saved={'provider':'codex','metric':{'state':'stale','observedAt':123}}
  r=s.metrics(C,lambda **kw:{'providers':[saved]},1900000000000)
  self.assertEqual(r['providers'][0]['metric']['observedAt'],123);self.assertTrue(r['providers'][0]['liveReadUnavailable'])
 def test_late_worst_bucket_kept_and_overflow_disclosed(self):
  class C:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def call(self,*a):return {'rateLimitsByLimitId':{str(i):{'primary':{'usedPercent':100 if i==8 else (i+1)*5,'windowDurationMins':300,'resetsAt':1900000000}}for i in range(9)}}
  r=s.metrics(C,lambda **kw:{'providers':[{'provider':'codex'}]},1900000000000-7200000)['providers'][0]
  self.assertEqual(len(r['windows']),8);self.assertEqual(r['overflowCount'],1);self.assertEqual(r['metric']['allowanceUsed'],1);self.assertEqual(r['metric']['pace']['state'],'behind')
 def test_multiple_buckets_deduplicated_and_invalid_units_unknown(self):
  class C:
   def __enter__(self):return self
   def __exit__(self,*a):pass
   def call(self,*a):return {'rateLimitsByLimitId':{'a':{'primary':{'usedPercent':20,'windowDurationMins':300,'resetsAt':1900000000}},'b':{'primary':{'usedPercent':20,'windowDurationMins':300,'resetsAt':1900000000},'secondary':{'usedPercent':float('nan'),'windowDurationMins':300,'resetsAt':1900000000}}}}
  r=s.metrics(C,lambda **kw:{'providers':[{'provider':'codex'}]},1899990000000)
  self.assertEqual(len(r['providers'][0]['windows']),1)

if __name__=='__main__':unittest.main()
