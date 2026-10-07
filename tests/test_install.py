"""Execute installer staging/activation against a private filesystem and mock IPC."""
import contextlib
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('districts_install',Path(__file__).resolve().parents[1]/'install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
ID=installer.ID

class Desktop:
 def __init__(self,home,config,modern=False):
  self.home=home;self.config=deepcopy(config);self.modern=modern;self.calls=[]
  self.state={'ready':True,'saving':False,'error':''};self.api_error=None
  self.on_stage=None;self.on_rescan=None;self.on_enable=None;self.pending_save=False
  self.now=0;self.write()
 def write(self):
  path=self.home/'.config/omarchy/shell.json';path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps(self.config,indent=2)+'\n')
 def tick(self):self.now+=.25;return self.now
 def sleep(self,seconds):
  self.now+=seconds
  if self.pending_save:self.write();self.pending_save=False
 def output(self,cmd,**kwargs):
  self.calls.append(list(cmd));method=cmd[2]
  if method=='configPersistenceState':
   if self.api_error:raise self.api_error
   if not self.modern:raise subprocess.CalledProcessError(1,cmd,stderr='Function not found.\n')
   return json.dumps(self.state)
  if method=='listShellConfig':return json.dumps(self.config)
  if method=='listPlugins':return json.dumps([{'id':ID,'enabled':bool(installer.placements(self.config))}])
  raise AssertionError('Unsupported test IPC: '+method)
 def run(self,cmd,**kwargs):
  self.calls.append(list(cmd))
  if cmd[:3]==['omarchy','plugin','validate']:
   if Path(cmd[3]).name.startswith('.districts-stage-') and self.on_stage:self.on_stage()
  elif cmd==['omarchy-shell','shell','rescanPlugins']:
   if self.on_rescan:self.on_rescan()
  elif cmd[:3]==['omarchy','plugin','enable']:
   if self.on_enable:self.on_enable(cmd)
   else:
    disabled=[p for p in self.config.get('disabledPlugins',[]) if p!=ID]
    if disabled:self.config['disabledPlugins']=disabled
    else:self.config.pop('disabledPlugins',None)
    if not installer.placements(self.config):
     section=cmd[cmd.index('--section')+1];index=int(cmd[cmd.index('--index')+1])
     self.config['bar']['layout'][section].insert(index,{'id':ID})
    if not self.pending_save:self.write()
  else:raise AssertionError('Unexpected subprocess: '+str(cmd))
  return subprocess.CompletedProcess(cmd,0)
 def enables(self):return [c for c in self.calls if c[:3]==['omarchy','plugin','enable']]

class InstallTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.base=Path(self.tmp.name);self.home=self.base/'home';self.source=self.base/'source';self.source.mkdir()
  (self.source/'manifest.json').write_text(json.dumps({'id':ID,'version':'fixture'}))
  (self.source/'runtime.qml').write_text('fixture-runtime\n')
  self.dest=self.home/'.config/omarchy/plugins'/ID
  self.receipt=self.base/'evidence/installation.json'
  self.config={'version':1,'bar':{'layout':{'left':['left-widget'],'center':[],'right':[{'id':'first','settings':{'keep':42}},'last']}},'plugins':[{'id':'service','settings':{'keep':True}}],'disabledPlugins':['other-disabled'],'idle':{'keep':13}}
 def desktop(self,placed=False,disabled=False,modern=False):
  config=deepcopy(self.config)
  if placed:config['bar']['layout']['center']=[{'id':ID,'zone':'outer','settings':{'motion':False,'custom':{'retain':1}}}]
  if disabled:config['disabledPlugins'].append(ID)
  return Desktop(self.home,config,modern)
 def previous(self):
  self.dest.mkdir(parents=True)
  (self.dest/'manifest.json').write_text(json.dumps({'id':ID,'version':'previous'}))
  (self.dest/'runtime.qml').write_text('previous-runtime\n')
 def invoke(self,desktop,enable=True):
  args=['install.py','--receipt',str(self.receipt)]
  if enable:args.append('--enable')
  with patch.object(installer,'ROOT',self.source),patch.object(installer,'RUNTIME',['manifest.json','runtime.qml']),patch.object(installer.Path,'home',return_value=self.home),patch.object(installer.subprocess,'check_output',side_effect=desktop.output),patch.object(installer.subprocess,'run',side_effect=desktop.run),patch.object(installer.time,'monotonic',side_effect=desktop.tick),patch.object(installer.time,'sleep',side_effect=desktop.sleep),patch('sys.argv',args),contextlib.redirect_stdout(io.StringIO()):
   return installer.main()
 def receipt_data(self):return json.loads(self.receipt.read_text())
 def test_older_shell_existing_entry_stages_backups_and_preserves_every_setting(self):
  desktop=self.desktop(placed=True);before=deepcopy(desktop.config);self.previous()
  self.assertEqual(self.invoke(desktop),0)
  result=self.receipt_data();self.assertTrue(result['enabled']);self.assertEqual(result['persistenceMode'],'live-saved-readback')
  self.assertEqual(desktop.config,before);self.assertEqual(desktop.enables(),[])
  self.assertEqual((self.dest/'runtime.qml').read_text(),'fixture-runtime\n')
  backup=Path(result['backup']);self.assertEqual((backup/'plugin/runtime.qml').read_text(),'previous-runtime\n')
  self.assertEqual(json.loads((backup/'shell-live.json').read_text()),before)
  self.assertEqual(json.loads((backup/'shell-saved.json').read_text()),before)
  self.assertEqual((backup/'shell-saved.json').stat().st_mode&0o777,0o600)
 def test_disabled_existing_entry_enabled_without_reposition_or_settings_loss(self):
  desktop=self.desktop(placed=True,disabled=True);before=deepcopy(desktop.config)
  self.assertEqual(self.invoke(desktop),0)
  self.assertEqual(desktop.enables(),[['omarchy','plugin','enable',ID]])
  self.assertEqual(installer.placements(desktop.config),installer.placements(before))
  self.assertEqual(desktop.config['disabledPlugins'],['other-disabled'])
 def test_modern_new_install_appends_right_and_verifies_enabled(self):
  desktop=self.desktop(modern=True);before=deepcopy(desktop.config)
  self.assertEqual(self.invoke(desktop),0)
  self.assertEqual(desktop.enables(),[['omarchy','plugin','enable',ID,'--section','right','--index','2']])
  self.assertEqual(installer.without_ours(desktop.config),installer.without_ours(before))
  self.assertEqual(self.receipt_data()['persistenceMode'],'state-api')
 def test_transport_failure_never_falls_back_or_replaces_runtime(self):
  desktop=self.desktop();desktop.api_error=subprocess.CalledProcessError(1,['ipc'],stderr='omarchy-shell is not running\n');self.previous()
  with self.assertRaises(subprocess.CalledProcessError):self.invoke(desktop)
  self.assertEqual((self.dest/'runtime.qml').read_text(),'previous-runtime\n');self.assertEqual(desktop.enables(),[])
 def test_invalid_persistence_response_never_falls_back(self):
  desktop=self.desktop(modern=True);desktop.state=['invalid'];self.previous()
  with self.assertRaisesRegex(RuntimeError,'Invalid desktop persistence'):self.invoke(desktop)
  self.assertEqual((self.dest/'runtime.qml').read_text(),'previous-runtime\n')
 def test_modern_busy_configuration_blocks_before_staging(self):
  desktop=self.desktop(modern=True);desktop.state['saving']=True;self.previous()
  with self.assertRaisesRegex(RuntimeError,'busy'):self.invoke(desktop)
  self.assertEqual((self.dest/'runtime.qml').read_text(),'previous-runtime\n')
 def test_saved_live_disagreement_blocks_before_staging(self):
  desktop=self.desktop();(self.home/'.config/omarchy/shell.json').write_text('{}');self.previous()
  with self.assertRaisesRegex(RuntimeError,'disagree'):self.invoke(desktop)
  self.assertEqual((self.dest/'runtime.qml').read_text(),'previous-runtime\n');self.assertEqual(desktop.enables(),[])
 def test_concurrent_staging_change_stops_before_rescan_without_restoration(self):
  desktop=self.desktop()
  def changed():desktop.config['idle']['keep']=99;desktop.write()
  desktop.on_stage=changed;self.previous()
  self.assertEqual(self.invoke(desktop),1)
  self.assertIn('during staging',self.receipt_data()['activationError'])
  self.assertNotIn(['omarchy-shell','shell','rescanPlugins'],desktop.calls)
  self.assertEqual(desktop.config['idle']['keep'],99);self.assertEqual(desktop.enables(),[])
 def test_concurrent_discovery_change_stops_before_enable(self):
  desktop=self.desktop()
  def changed():desktop.config['idle']['keep']=88;desktop.write()
  desktop.on_rescan=changed
  self.assertEqual(self.invoke(desktop),1)
  self.assertIn('during discovery',self.receipt_data()['activationError']);self.assertEqual(desktop.enables(),[])
 def test_modern_api_becoming_busy_during_staging_stops_before_rescan(self):
  desktop=self.desktop(modern=True)
  def changed():desktop.state['saving']=True
  desktop.on_stage=changed
  self.assertEqual(self.invoke(desktop),1)
  self.assertIn('busy',self.receipt_data()['activationError']);self.assertEqual(desktop.enables(),[])
  self.assertNotIn(['omarchy-shell','shell','rescanPlugins'],desktop.calls)
 def test_missing_function_mid_modern_activation_is_not_silent_fallback(self):
  desktop=self.desktop(modern=True)
  def changed():desktop.modern=False
  desktop.on_rescan=changed
  self.assertEqual(self.invoke(desktop),1)
  self.assertIn('API changed',self.receipt_data()['activationError']);self.assertEqual(desktop.enables(),[])
 def test_older_shell_waits_for_real_saved_readback_after_enable(self):
  desktop=self.desktop();desktop.pending_save=True
  self.assertEqual(self.invoke(desktop),0)
  self.assertFalse(desktop.pending_save);self.assertTrue(self.receipt_data()['enabled'])
 def test_enable_noop_is_not_reported_as_enabled(self):
  desktop=self.desktop();desktop.on_enable=lambda cmd:None
  self.assertEqual(self.invoke(desktop),1);self.assertFalse(self.receipt_data()['enabled'])
 def test_unrelated_post_enable_change_is_preserved_and_reported_failure(self):
  desktop=self.desktop()
  def changed(cmd):
   desktop.config['bar']['layout']['right'].append({'id':ID});desktop.config['idle']['keep']=77;desktop.write()
  desktop.on_enable=changed
  self.assertEqual(self.invoke(desktop),1)
  self.assertIn('Unrelated',self.receipt_data()['activationError']);self.assertEqual(desktop.config['idle']['keep'],77)
 def test_existing_entry_setting_change_is_reported_failure(self):
  desktop=self.desktop(placed=True,disabled=True)
  def changed(cmd):
   desktop.config['disabledPlugins'].remove(ID);desktop.config['bar']['layout']['center'][0]['zone']='inner';desktop.write()
  desktop.on_enable=changed
  self.assertEqual(self.invoke(desktop),1);self.assertIn('position or settings',self.receipt_data()['activationError'])
 def test_stage_only_never_queries_or_mutates_live_shell(self):
  desktop=self.desktop();before=deepcopy(desktop.config)
  self.assertEqual(self.invoke(desktop,enable=False),0)
  self.assertFalse(self.receipt_data()['enabled']);self.assertEqual(desktop.config,before)
  self.assertTrue(all(c[:3]==['omarchy','plugin','validate'] for c in desktop.calls))

if __name__=='__main__':unittest.main()
