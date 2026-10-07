import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('provider_metrics',Path(__file__).resolve().parents[1]/'provider_metrics.py')
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
NOW=1791328800000
HOUR=3600000


class MetricsTests(unittest.TestCase):
 def window(self, used=.2, **kwargs):
  row={'label':'Session (5-hour)','percent':used,'resetsAt':NOW+2.5*HOUR}
  row.update(kwargs)
  return metrics.normalize_window(row,measured_at=NOW,source='Verified quota source',now_ms=NOW)
 def test_signed_time_banked_behind_and_exact_on_pace(self):
  self.assertEqual(self.window(.2)['pace']['signedSeconds'],5400)
  behind=self.window(.8);self.assertEqual(behind['pace']['signedSeconds'],-5400)
  self.assertEqual(behind['pace']['waitSeconds'],5400)
  self.assertEqual(behind['pace']['assumption'],'No additional usage since the quota observation')
  self.assertEqual(self.window(.5)['pace']['signedSeconds'],0)
  self.assertEqual(self.window(.5)['pace']['state'],'on-pace')
 def test_real_measured_zero_is_valid_missing_is_not_zero(self):
  self.assertEqual(self.window(0)['allowanceUsed'],0)
  for value in [None,True,'0',float('nan'),float('inf'),-1,1.1]:
   result=self.window(value);self.assertEqual(result['state'],'unavailable');self.assertIsNone(result['allowanceUsed']);self.assertIsNone(result['pace']['signedSeconds'])
 def test_percent_is_fraction_no_absolute_compute_credit(self):
  value=self.window(.4);self.assertEqual(value['unit'],'fraction');self.assertEqual(value['allowanceRemaining'],.6)
  self.assertEqual(value['pace']['meaning'],'pace-equivalent allowance credit')
 def test_reset_boundary_withholds_old_quota_and_pace(self):
  for end in [NOW,NOW-1]:
   result=self.window(.4,resetsAt=end);self.assertEqual(result['state'],'stale');self.assertIsNone(result['pace']['signedSeconds'])
 def test_at_limit_wait_is_conditional_until_reset_not_claim_unblock(self):
  value=self.window(1);self.assertTrue(value['pace']['allowanceExhausted']);self.assertEqual(value['pace']['waitSeconds'],9000)
  self.assertEqual(value['pace']['recoveryAt'],value['resetAt'])
 def test_rolling_monthly_or_unknown_window_has_no_time_invention(self):
  for patch in [{'windowKind':'rolling'},{'label':'Monthly (total)'},{'label':'Quota'},{'resetsAt':None}]:
   value=self.window(**patch);self.assertEqual(value['state'],'measured');self.assertIsNone(value['pace']['signedSeconds'])
 def test_provider_declared_start_can_support_calendar_window(self):
  value=self.window(.2,label='Monthly (total)',startsAt=NOW-2.5*HOUR)
  self.assertEqual(value['pace']['signedSeconds'],5400)
 def test_explicit_api_duration_is_model_not_declared_start(self):
  value=self.window(.2,label='Account API window',durationMs=5*HOUR)
  self.assertEqual(value['pace']['signedSeconds'],5400)
  self.assertEqual(value['pace']['windowBasis'],'provider-declared duration/reset; even-pace model')
  for duration in [0,-1,True,'18000000',367*24*HOUR]:
   value=self.window(.2,label='Account API window',durationMs=duration)
   self.assertIsNone(value['pace']['signedSeconds'])
 def test_usage_permission_is_explicit_boolean_not_inferred(self):
  for allowed in [True,False,None,'true',1]:
   value=metrics.record('codex',{'ordinaryUsageAllowed':allowed},source='Verified quota source',now_ms=NOW)
   self.assertIs(value['ordinaryUsageAllowed'],allowed if type(allowed) is bool else None)
 def test_observed_credit_frozen_wait_projection_explicit(self):
  row={'label':'Session (5-hour)','percent':.8,'resetsAt':NOW+2.5*HOUR}
  later=metrics.normalize_window(row,measured_at=NOW,source='Verified quota source',now_ms=NOW+10*60000)
  self.assertEqual(later['pace']['signedSeconds'],-5400);self.assertEqual(later['pace']['waitSeconds'],4800)
 def test_stale_and_unstamped_usage_are_not_healthy(self):
  row={'label':'Weekly (7-day)','percent':.4,'resetsAt':NOW+HOUR}
  for stamp,state in [(None,'unavailable'),(NOW-900001,'stale'),(NOW+60001,'unavailable')]:
   result=metrics.normalize_window(row,measured_at=stamp,source='Verified quota source',now_ms=NOW)
   self.assertEqual(result['state'],state);self.assertIsNone(result['pace']['signedSeconds'])
 def test_multiple_windows_keep_all_and_select_most_behind(self):
  rows=[{'label':'Session (5-hour)','percent':.3,'resetsAt':NOW+2.5*HOUR},{'label':'Weekly (7-day)','percent':.8,'resetsAt':NOW+3.5*24*HOUR}]
  value=metrics.record('claude',{'limits':rows,'measuredAt':NOW},source='Verified quota source',now_ms=NOW)
  self.assertEqual(len(value['windows']),2);self.assertEqual(value['metric']['label'],'Weekly (7-day)')
 def test_restamped_file_updated_at_is_not_quota_measurement(self):
  value=metrics.record('codex',{'updatedAt':NOW,'limits':[{'label':'Weekly (7-day)','percent':.4,'resetsAt':NOW+HOUR}]},source='Canonical shared quota record',now_ms=NOW)
  self.assertEqual(value['metric']['state'],'unavailable')
 def test_window_display_bounded(self):
  rows=[{'label':'Session (5-hour)','percent':.2,'resetsAt':NOW+HOUR}]*10
  value=metrics.record('claude',{'limits':rows,'measuredAt':NOW},source='Verified quota source',now_ms=NOW)
  self.assertEqual(len(value['windows']),8);self.assertEqual(value['overflowCount'],2)
 def test_default_collector_has_no_reference_dependency_and_uses_probe_stamp(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);state=root/'state';cache=root/'cache'
   canonical=state/'omarchy/agents/usage';canonical.mkdir(parents=True)
   probe=cache/'omarchy/agent-usage';probe.mkdir(parents=True)
   doc={'limits':[{'label':'Session (5-hour)','percent':.2,'resetsAt':NOW+2.5*HOUR}]}
   (canonical/'claude.json').write_text(json.dumps(dict(doc,updatedAt=NOW)))
   (probe/'claude-limits.json').write_text(json.dumps(dict(doc,fetchedAtMs=NOW)))
   reference=state/'omarchy/burnbar';reference.mkdir(parents=True)
   (reference/'kimi-usage.json').write_text(json.dumps(dict(doc,measuredAt=NOW)))
   values=metrics.collect(state_root=state,cache_root=cache,now_ms=NOW)['providers']
   self.assertEqual(values[1]['metric']['state'],'measured');self.assertEqual(values[3]['metric']['state'],'unavailable')
   imported=metrics.collect(state_root=state,cache_root=cache,now_ms=NOW,reference_kimi=True)['providers']
   self.assertEqual(imported[3]['metric']['state'],'measured')
 def test_metadata_byte_depth_type_and_symlink_limits(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);valid=root/'valid.json';valid.write_text('{"limits":[]}')
   link=root/'linked.json';link.symlink_to(valid);self.assertIsNone(metrics.read_metadata(link))
   huge=root/'huge.json';huge.write_text('x'*65537);self.assertIsNone(metrics.read_metadata(huge))
   deep=root/'deep.json';deep.write_text('{"deep":'+('[ '*10)+'0'+('] '*10)+'}');self.assertIsNone(metrics.read_metadata(deep))
   self.assertEqual(metrics.read_metadata(valid),{'limits':[]})
 def test_timestamp_requires_zone_and_boolean_is_not_measurement(self):
  self.assertIsNone(metrics.timestamp('2026-10-06T12:00:00'));self.assertIsNone(metrics.timestamp(True))
  self.assertIsNotNone(metrics.timestamp('2026-10-06T12:00:00Z'))


if __name__=='__main__':unittest.main()
