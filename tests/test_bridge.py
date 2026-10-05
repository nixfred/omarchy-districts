import importlib.util
import json
import os
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('districts_bridge', ROOT/'districts.py')
bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)

def fixture():
    return ([{'id':0,'name':'DP-1','activeWorkspace':{'id':2},'width':1920,'height':1080,'scale':1}],
            [{'id':2,'monitorID':0},{'id':-2,'monitorID':0}],
            [{'address':'0x123','workspace':{'id':2},'monitor':0,'class':'kitty','title':'PRIVATE SECRET',
              'at':[3,5],'size':[800,600],'mapped':True,'hidden':False}], {'address':'0x123'})

class BridgeTests(unittest.TestCase):
    def test_titles_never_leave_bridge(self):
        data=bridge.normalize(*fixture(),{},{});self.assertNotIn('PRIVATE',json.dumps(data));self.assertNotIn('title',json.dumps(data))
        self.assertEqual(data['windows'][0]['app'],'kitty')
    def test_special_workspaces_excluded(self):
        m,w,c,a=fixture();c.append({**c[0],'address':'0x456','workspace':{'id':-2}})
        data=bridge.normalize(m,w,c,a,{},{});self.assertEqual(len(data['windows']),1);self.assertEqual(len(data['districts']),1)
    def test_hidden_and_unmapped_excluded(self):
        m,w,c,a=fixture();c += [{**c[0],'address':'0x45','hidden':True},{**c[0],'address':'0x46','mapped':False}]
        self.assertEqual(len(bridge.normalize(m,w,c,a,{}, {})['windows']),1)
    def test_missing_workspace_recovered_from_clients(self):
        m,w,c,a=fixture();data=bridge.normalize(m,[],c,a,{},{});self.assertEqual(data['districts'][0]['id'],2)
    def test_malformed_records_ignored(self):
        m,w,c,a=fixture();c.extend([{}, {'address':'x"})','workspace':{'id':2}}, {**c[0],'size':[]}])
        self.assertEqual(len(bridge.normalize(m,w,c,a,{}, {})['windows']),1)
    def test_monitor_bounds(self):
        m,w,c,a=fixture();m[0]['width']=999999
        self.assertEqual(bridge.normalize(m,w,c,a,{}, {})['boroughs'],[])
    def test_cap_and_truncation(self):
        m,w,c,a=fixture();clients=[{**c[0],'address':hex(i+1)} for i in range(600)]
        data=bridge.normalize(m,w,clients,a,{},{});self.assertTrue(data['truncated']);self.assertEqual(len(data['windows']),512)
    def test_public_icon_and_app_label(self):
        data=bridge.normalize(*fixture(),{}, {'kitty':{'app':'Kitty','icon':'kitty'}});self.assertEqual(data['windows'][0]['icon'],'kitty')
    def test_seed_roundtrip_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'city'/'architecture.json';bridge.save_architecture(p,{'2':123});self.assertEqual(bridge.load_architecture(p),{'2':123})
            self.assertEqual(p.stat().st_mode&0o777,0o600);self.assertEqual(set(json.loads(p.read_text())),{'schema','seeds','names','pins','tints','grouping'})
    def test_invalid_seed_file_resets(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'architecture.json';p.write_text('{bad');self.assertEqual(bridge.load_architecture(p),{})
    def test_renumber_preserves_identity(self):
        with tempfile.TemporaryDirectory() as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.save_architecture(bridge.state_path(),{'2':981,'3':123});bridge.renumber(2,7)
            self.assertEqual(bridge.load_architecture(bridge.state_path()),{'7':981,'3':123})
    def test_stale_address_refused(self):
        with patch.object(bridge,'query',return_value=[]),patch.object(bridge,'command') as cmd:
            with self.assertRaisesRegex(ValueError,'closed'):bridge.activate('0x123')
            cmd.assert_not_called()
    def test_injection_address_refused(self):
        with patch.object(bridge,'query') as query:
            with self.assertRaises(ValueError):bridge.activate('0x123"})')
            query.assert_not_called()
    def test_reused_address_class_refused(self):
        with patch.object(bridge,'query',return_value=fixture()[2]),patch.object(bridge,'command') as cmd:
            with self.assertRaisesRegex(ValueError,'changed'):bridge.activate('0x123',expected_app='browser')
            cmd.assert_not_called()
    def test_moved_window_refused(self):
        with patch.object(bridge,'query',return_value=fixture()[2]),patch.object(bridge,'command') as cmd:
            with self.assertRaisesRegex(ValueError,'moved'):bridge.activate('0x123',expected_workspace=3)
            cmd.assert_not_called()
    def test_lua_dispatch_validated(self):
        with patch.object(bridge,'query',return_value=fixture()[2]),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'command',return_value='ok') as cmd:
            self.assertTrue(bridge.activate('0x123',expected_workspace=2,expected_app='kitty')['ok'])
            cmd.assert_called_once_with(['dispatch','hl.dsp.focus({ window = "address:0x123" })'])
    def test_legacy_dispatch_validated(self):
        with patch.object(bridge,'query',return_value=fixture()[2]),patch.object(bridge,'lua_supported',return_value=False),patch.object(bridge,'command',return_value='ok') as cmd:
            bridge.activate('0x123');cmd.assert_called_once_with(['dispatch','focuswindow','address:0x123'])
    def test_disappeared_workspace_refused(self):
        with patch.object(bridge,'query',return_value=[]),patch.object(bridge,'command') as cmd:
            with self.assertRaisesRegex(ValueError,'no longer'):bridge.activate(workspace=2)
            cmd.assert_not_called()
    def test_positive_existing_workspace_only(self):
        with patch.object(bridge,'query',return_value=fixture()[1]),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'command',return_value='ok') as cmd:
            bridge.activate(workspace=2);cmd.assert_called_once_with(['dispatch','hl.dsp.focus({ workspace = "2" })'])
        with self.assertRaises(ValueError):bridge.activate(workspace=-2)
    def test_dispatch_failure_not_success(self):
        with patch.object(bridge,'query',return_value=fixture()[1]),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'command',return_value='error'):
            with self.assertRaises(RuntimeError):bridge.activate(workspace=2)
    def test_seed_transactions_preserve_concurrent_updates(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'architecture.json'
            bridge.save_architecture(path,{'1':9})
            code='''import importlib.util,sys,time,pathlib
s=importlib.util.spec_from_file_location('bridge',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p=pathlib.Path(sys.argv[2])
with m.architecture_lock(p):
 data=m.load_architecture(p);time.sleep(.05);data[sys.argv[3]]=int(sys.argv[3]);m.save_architecture(p,data)
'''
            children=[subprocess.Popen([sys.executable,'-B','-c',code,str(ROOT/'districts.py'),str(path),str(i)])for i in range(2,7)]
            for child in children:self.assertEqual(child.wait(timeout=4),0)
            self.assertEqual(bridge.load_architecture(path),{'1':9,**{str(i):i for i in range(2,7)}})
    def test_version_detection_does_not_trust_config_file(self):
        with patch.object(bridge,'command',return_value='{"tag":"v0.56.1"}'):self.assertTrue(bridge.lua_supported())
        with patch.object(bridge,'command',return_value='{"tag":"v0.55.0"}'):self.assertFalse(bridge.lua_supported())
    def test_watch_caches_public_apps_in_memory(self):
        import io
        selector=unittest.mock.MagicMock();selector.select.side_effect=[[True],[],[True]]
        input=unittest.mock.MagicMock();input.fileno.return_value=9
        with patch.object(bridge.selectors,'DefaultSelector',return_value=selector),patch.object(bridge,'app_directories_signature',return_value=('unchanged',)),patch.object(bridge,'desktop_apps',return_value={})as apps,patch.object(bridge,'snapshot',return_value={'schema':1})as snapshot,patch.object(bridge.sys,'stdin',input),patch.object(bridge.sys,'stdout',io.StringIO()),patch.object(bridge.os,'read',side_effect=[b'refresh\nrefresh\n',b'']):
            bridge.watch();self.assertEqual(apps.call_count,1);self.assertEqual(snapshot.call_count,2)
    def test_empty_app_class_revalidates_consistently(self):
        client={**fixture()[2][0],'class':''}
        with patch.object(bridge,'query',return_value=[client]),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'command',return_value='ok'):
            self.assertTrue(bridge.activate('0x123',expected_app='Application')['ok'])

    def test_schema1_migrates_without_losing_seed(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            p=bridge.state_path();p.write_text(json.dumps({'schema':1,'seeds':{'2':991}}))
            bridge.customize(2,name='Build / docs',pinned=True,tint=3)
            data=bridge.read_state(p)
            self.assertEqual(data['seeds']['2'],991);self.assertEqual(data['names']['2'],'Build / docs');self.assertEqual(data['pins'],['2']);self.assertEqual(data['tints']['2'],3)
            self.assertEqual(p.stat().st_mode&0o777,0o600)
    def test_clear_name_preserves_other_personalization(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,name='研究',pinned=True,tint=2);bridge.customize(2,name='')
            data=bridge.read_state(bridge.state_path());self.assertNotIn('2',data['names']);self.assertEqual(data['pins'],['2']);self.assertEqual(data['tints']['2'],2)
    def test_control_and_oversized_names_rejected_without_write(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            for name in ['bad\nname','x'*49,'bad\u202ename']:
                with self.assertRaises(ValueError):bridge.customize(2,name=name)
            self.assertFalse(bridge.state_path().exists())
    def test_renumber_carries_identity_and_user_labels(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,name='Build',pinned=True,tint=4);seed=bridge.load_architecture(bridge.state_path())['2'];bridge.renumber(2,9)
            data=bridge.read_state(bridge.state_path());self.assertEqual(data['names'],{'9':'Build'});self.assertEqual(data['pins'],['9']);self.assertEqual(data['tints'],{'9':4});self.assertEqual(data['seeds']['9'],seed)
    def test_grounded_labels_source_and_custom_priority(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'),patch.object(bridge,'query')as q:
            m,w,c,a=fixture();w[0]['name']='2';q.side_effect=[m,w,c,a]
            data=bridge.snapshot({'kitty':{'app':'Kitty','icon':'kitty'}});self.assertEqual(data['districts'][0]['name'],'Kitty');self.assertEqual(data['districts'][0]['nameSource'],'apps')
            w[0]['name']='Release';q.side_effect=[m,w,c,a];data=bridge.snapshot({});self.assertEqual(data['districts'][0]['name'],'Release');self.assertEqual(data['districts'][0]['nameSource'],'workspace')
            bridge.customize(2,name='Custom');q.side_effect=[m,w,c,a];data=bridge.snapshot({});self.assertEqual(data['districts'][0]['name'],'Custom');self.assertEqual(data['districts'][0]['nameSource'],'custom')
            self.assertNotIn('PRIVATE',json.dumps(data))
    def test_relocation_validates_all_targets_and_is_silent(self):
        m,w,c,a=fixture();w.append({'id':3,'monitorID':0})
        with patch.object(bridge,'query',side_effect=[c,w]),patch.object(bridge,'lua_supported',return_value=True),patch.object(bridge,'command',return_value='ok')as cmd:
            self.assertTrue(bridge.relocate('0x123',3,'kitty',2)['ok'])
            cmd.assert_called_once_with(['dispatch','hl.dsp.window.move({ workspace = "3", window = "address:0x123", follow = false })'])
        with patch.object(bridge,'query',side_effect=[c,w]),patch.object(bridge,'lua_supported',return_value=False),patch.object(bridge,'command',return_value='ok')as cmd:
            bridge.relocate('0x123',3,'kitty',2);cmd.assert_called_once_with(['dispatch','movetoworkspacesilent','3,address:0x123'])
    def test_relocation_stale_reused_missing_and_same_destination(self):
        m,w,c,a=fixture()
        cases=[([],w,'kitty',2,3), (c,w,'Code',2,3),(c,w,'kitty',4,3),(c,w,'kitty',2,3),(c,w,'kitty',2,2)]
        for clients,workspaces,app,source,dest in cases:
            with patch.object(bridge,'query',side_effect=[clients,workspaces]),patch.object(bridge,'command')as cmd:
                with self.assertRaises(ValueError):bridge.relocate('0x123',dest,app,source)
                cmd.assert_not_called()
        with self.assertRaises(ValueError):bridge.relocate('bad"})',3,'kitty',2)

    def test_renumber_collision_preserves_both_personal_identities(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,name='Build',pinned=True,tint=4);bridge.customize(9,name='Archive',tint=2)
            before=bridge.read_state(bridge.state_path());bridge.renumber(2,9);after=bridge.read_state(bridge.state_path())
            self.assertEqual(after['names'],{'9':'Build','2':'Archive'});self.assertEqual(after['pins'],['9'])
            self.assertEqual(after['tints'],{'9':4,'2':2});self.assertEqual(after['seeds']['9'],before['seeds']['2']);self.assertEqual(after['seeds']['2'],before['seeds']['9'])
    def test_personal_districts_survive_bounded_workspace_churn(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,name='Keep',pinned=True,tint=4);data=bridge.read_state(bridge.state_path())
            data['seeds'].update({str(i):i for i in range(3,800)});bridge.write_state(bridge.state_path(),data)
            saved=bridge.read_state(bridge.state_path());self.assertEqual(len(saved['seeds']),512);self.assertEqual(saved['names']['2'],'Keep');self.assertEqual(saved['pins'],['2']);self.assertEqual(saved['tints']['2'],4)
    def test_personal_limit_rejects_without_erasing_existing_data(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            data={'schema':2,'seeds':{str(i):i for i in range(1,513)},'names':{str(i):'Keep' for i in range(1,513)},'pins':[],'tints':{}}
            bridge.write_state(bridge.state_path(),data);before=bridge.state_path().read_bytes()
            with self.assertRaisesRegex(ValueError,'512 personalized'):bridge.customize(513,name='New')
            self.assertEqual(bridge.state_path().read_bytes(),before)

    def test_activity_hysteresis_resets_cleanly_after_custom_source(self):
        import io,copy
        values=[('Kitty','apps'),('Code','apps'),('Mine','custom'),('Code','apps'),('Brave','apps'),('Brave','apps')]
        frames=[{'schema':1,'districts':[{'id':2,'name':n,'nameSource':s}]}for n,s in values]
        selector=unittest.mock.MagicMock();selector.select.side_effect=[[],[],[],[],[],[True]]
        input=unittest.mock.MagicMock();input.fileno.return_value=9;output=io.StringIO()
        with patch.object(bridge.selectors,'DefaultSelector',return_value=selector),patch.object(bridge,'app_directories_signature',return_value=()),patch.object(bridge,'desktop_apps',return_value={}),patch.object(bridge,'snapshot',side_effect=copy.deepcopy(frames)),patch.object(bridge.time,'monotonic',side_effect=[0,2,4,6,8,15]),patch.object(bridge.sys,'stdin',input),patch.object(bridge.sys,'stdout',output),patch.object(bridge.os,'read',return_value=b''):
            bridge.watch()
        self.assertEqual([json.loads(line)['districts'][0]['name']for line in output.getvalue().splitlines()],['Kitty','Kitty','Mine','Code','Code','Brave'])

    def test_ordered_renumber_roundtrip_preserves_final_identity(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(3,name='Work',pinned=True,tint=4);bridge.customize(7,name='History',tint=2)
            before=bridge.read_state(bridge.state_path());bridge.renumber(3,7);bridge.renumber(7,3);after=bridge.read_state(bridge.state_path())
            for field in ['seeds','names','pins','tints']:self.assertEqual(after[field],before[field])
    def test_ordered_renumber_chain_keeps_current_and_historical_metadata(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,name='Current',pinned=True);bridge.customize(9,name='Historical9');bridge.customize(7,name='Historical7')
            bridge.renumber(2,9);bridge.renumber(9,7);after=bridge.read_state(bridge.state_path())
            self.assertEqual(after['names'],{'2':'Historical9','9':'Historical7','7':'Current'});self.assertEqual(after['pins'],['7'])
    def test_public_app_cache_detects_in_place_entry_edit(self):
        with tempfile.TemporaryDirectory()as d,patch.dict(os.environ,{'XDG_DATA_HOME':d,'XDG_DATA_DIRS':d}):
            directory=Path(d)/'applications';directory.mkdir();entry=directory/'fixture.desktop';entry.write_text('[Desktop Entry]\nName=Before\n')
            directory_time=directory.stat().st_mtime_ns;before=bridge.app_directories_signature();stamp=entry.stat().st_mtime_ns
            entry.write_text('[Desktop Entry]\nName=After\n');os.utime(entry,ns=(stamp+1000000,stamp+1000000));os.utime(directory,ns=(directory_time,directory_time))
            self.assertNotEqual(bridge.app_directories_signature(),before)

    def test_explicit_first_circuit_is_protected_through_churn(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,tint=0);data=bridge.read_state(bridge.state_path());data['seeds'].update({str(i):i for i in range(3,800)});bridge.write_state(bridge.state_path(),data)
            saved=bridge.read_state(bridge.state_path());self.assertIn('2',saved['seeds']);self.assertIn('2',saved['tints']);self.assertEqual(saved['tints']['2'],0)

    def test_group_settings_preserve_schema2_names_pins_and_circuits(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,name='Mine',pinned=True,tint=0);before=bridge.read_state(bridge.state_path())
            result=bridge.edit_group(group='development',color='#123456')
            bridge.edit_group(app='Code',rule='research');saved=bridge.read_state(bridge.state_path())
            for key in ['seeds','names','pins','tints']:self.assertEqual(saved[key],before[key])
            self.assertEqual(saved['grouping']['colors'],{'development':'#123456'});self.assertEqual(saved['grouping']['rules'],{'code':'research'})
            self.assertEqual(saved['grouping']['revision'],2);self.assertEqual(bridge.state_path().stat().st_mode&0o777,0o600)
            bridge.renumber(2,7);self.assertEqual(bridge.read_state(bridge.state_path())['grouping'],saved['grouping'])
            bridge.customize(7,name='New');self.assertEqual(bridge.read_state(bridge.state_path())['grouping'],saved['grouping'])
    def test_bad_or_duplicate_group_colors_and_rules_do_not_write(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.customize(2,name='Keep');before=bridge.state_path().read_bytes()
            for fields in [dict(group='development',color=bridge.GROUP_COLORS['system']),dict(group='missing',color='#123456'),dict(group='development',color='red'),dict(app='bad\nclass',rule='research'),dict(app='Code',rule='fake'),dict(app='Code'),dict(group='development',color='#123456',app='Code',rule='research')]:
                with self.assertRaises(ValueError):bridge.edit_group(**fields)
                self.assertEqual(bridge.state_path().read_bytes(),before)
    def test_group_rule_clear_default_and_limit(self):
        with tempfile.TemporaryDirectory()as d,patch.object(bridge,'state_path',return_value=Path(d)/'architecture.json'):
            bridge.edit_group(group='development',color='#123456');bridge.edit_group(app='Code',rule='research')
            bridge.edit_group(group='development',color='default');bridge.edit_group(app='Code',rule='auto')
            prefs=bridge.read_state(bridge.state_path())['grouping'];self.assertEqual(prefs['colors'],{});self.assertEqual(prefs['rules'],{})
            data=bridge.read_state(bridge.state_path());data['grouping']['rules']={str(i):'development'for i in range(128)};bridge.write_state(bridge.state_path(),data);before=bridge.state_path().read_bytes()
            with self.assertRaises(ValueError):bridge.edit_group(app='Code',rule='research')
            self.assertEqual(bridge.state_path().read_bytes(),before);bridge.edit_group(app='1',rule='research')
    def test_corrupt_group_preferences_never_erase_personal_metadata(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'architecture.json';p.write_text(json.dumps({'schema':2,'seeds':{'2':123},'names':{'2':'Keep'},'pins':['2'],'tints':{'2':0},'grouping':{'revision':'bad','colors':{'development':['bad']},'rules':{'kitty':['bad']}}}))
            data=bridge.read_state(p);self.assertEqual(data['names'],{'2':'Keep'});self.assertEqual(data['pins'],['2']);self.assertEqual(data['tints'],{'2':0});self.assertEqual(data['grouping']['rules'],{})
    def test_public_categories_are_allowlisted_not_exec_or_comment(self):
        with tempfile.TemporaryDirectory()as d,patch.dict(os.environ,{'XDG_DATA_HOME':d,'XDG_DATA_DIRS':d}):
            root=Path(d)/'applications';root.mkdir();(root/'fixture.desktop').write_text('[Desktop Entry]\nName=Fixture\nStartupWMClass=Fixture\nCategories=Development;UnknownPrivateCategory;Network;\nExec=PRIVATE COMMAND\nComment=PRIVATE COMMENT\n')
            apps=bridge.desktop_apps();self.assertEqual(apps['fixture']['categories'],['Development']);self.assertNotIn('PRIVATE',json.dumps(apps));self.assertNotIn('UnknownPrivateCategory',json.dumps(apps))
    def test_group_rule_and_metadata_concurrent_commits_merge(self):
        with tempfile.TemporaryDirectory()as d:
            code='''import importlib.util,sys,os
s=importlib.util.spec_from_file_location('bridge',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
os.environ['XDG_STATE_HOME']=sys.argv[2]
if sys.argv[3]=='group':m.edit_group(app='Code',rule='research')
else:m.customize(2,name='Keep',pinned=True,tint=0)
'''
            children=[subprocess.Popen([sys.executable,'-B','-c',code,str(ROOT/'districts.py'),d,kind])for kind in ['group','metadata']]
            for child in children:self.assertEqual(child.wait(timeout=4),0)
            data=bridge.read_state(Path(d)/'districts/architecture.json');self.assertEqual(data['names'],{'2':'Keep'});self.assertEqual(data['grouping']['rules'],{'code':'research'})

if __name__=='__main__':unittest.main()
