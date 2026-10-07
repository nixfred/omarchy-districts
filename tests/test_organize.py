"""Behavior checks with a mutable mock compositor; never dispatch to the host."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import os
import tempfile
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('organizer', ROOT/'organize.py')
organize = importlib.util.module_from_spec(spec)
spec.loader.exec_module(organize)


def fixture():
    return {'truncated': False, 'focused': '0xff', 'grouping': {},
            'districts': [{'id': i, 'monitor': 0, 'count': 1, 'name': 'District '+str(i)} for i in (1, 2, 3)],
            'windows': [{'address': hex(i + 16), 'class': 'code', 'app': 'Code', 'pid': 100 + i, 'workspace': i, 'monitor': 0,
                         'desktopCategories': ['Development'], 'title': 'PRIVATE CONTENT'} for i in (1, 2, 3)]}


class Desktop:
    def __init__(self, snapshot):
        self.workspaces = [{'id': d['id'], 'monitorID': d['monitor']} for d in snapshot['districts']]
        self.clients = [{'address': w['address'], 'class': w['class'], 'pid': w['pid'], 'workspace': {'id': w['workspace']},
                         'mapped': True, 'hidden': False, 'title': 'PRIVATE CONTENT'} for w in snapshot['windows']]
        self.active = {'address': snapshot['focused']}
        self.commands = []
        self.queries = []
        self.before = None
        self.state = {'grouping': {}, 'names': {}, 'pins': []}
        self.response = 'ok'
        self.confirm = True

    def query(self, name):
        self.queries.append(name)
        return deepcopy({'clients': self.clients, 'workspaces': self.workspaces, 'activewindow': self.active}[name])

    def command(self, arguments):
        self.commands.append(arguments)
        # Use the emitted intentional Lua interface, not source-text assertions.
        import re
        match = re.fullmatch(r'hl\.dsp\.window\.move\(\{ workspace = "(\d+)", window = "address:(0x[0-9a-fA-F]+)", follow = false \}\)', arguments[1])
        if arguments[0] != 'dispatch' or not match:
            raise AssertionError('Only the supported scoped non-following move is allowed.')
        if self.confirm and self.response == 'ok':
            for client in self.clients:
                if client['address'] == match[2]:
                    client['workspace']['id'] = int(match[1])
        if self.before:
            self.before(self)
        return self.response

    def apply(self, plan, prefs=None, **kwargs):
        with patch.object(organize.bridge, 'query', side_effect=self.query), patch.object(organize.bridge, 'command', side_effect=self.command), patch.object(organize.bridge, 'lua_supported', return_value=True), patch.object(organize.bridge, 'read_state', side_effect=lambda unused: deepcopy({**self.state, 'grouping': prefs if prefs is not None else self.state['grouping']})):
            return organize.apply(plan, plan['planId'], now=101, **kwargs)


class OrganizerTests(unittest.TestCase):
    def plan(self, snapshot=None):
        return organize.preview(snapshot or fixture(), now=100)['plan']

    def test_preview_is_pure_and_title_free(self):
        original = fixture()
        before = deepcopy(original)
        with patch.object(organize.bridge, 'query') as query, patch.object(organize.bridge, 'command') as command:
            plan = self.plan(original)
        query.assert_not_called()
        command.assert_not_called()
        self.assertEqual(original, before)
        self.assertNotIn('PRIVATE', json.dumps(plan))
        self.assertNotIn('title', json.dumps(plan))
        self.assertEqual([m['sourceWorkspace'] for m in plan['moves']], [2, 3])
        self.assertEqual([m['destinationWorkspace'] for m in plan['moves']], [1, 1])
        self.assertEqual(plan['summaries'], [{'workspace': 1, 'before': 1, 'after': 3}, {'workspace': 2, 'before': 1, 'after': 0}, {'workspace': 3, 'before': 1, 'after': 0}])

    def test_busiest_anchor_then_lowest_id(self):
        snapshot = fixture()
        snapshot['windows'].append({**snapshot['windows'][1], 'address': '0x25', 'pid': 999})
        plan = self.plan(snapshot)
        self.assertEqual({m['destinationWorkspace'] for m in plan['moves']}, {2})

    def test_custom_rule_overrides_unknown_app(self):
        snapshot = fixture()
        for window in snapshot['windows']:
            window.update({'class': 'custom-app', 'app': 'Custom App', 'desktopCategories': []})
        self.assertEqual(self.plan(snapshot)['moves'], [])
        snapshot['grouping'] = {'revision': 4, 'rules': {'custom-app': 'development'}}
        self.assertEqual(len(self.plan(snapshot)['moves']), 2)

    def test_unknown_and_browser_content_not_classified(self):
        for app in ('brave', 'unknown'):
            snapshot = fixture()
            for window in snapshot['windows']:
                window.update({'class': app, 'desktopCategories': ['Development', 'WebBrowser'] if app == 'brave' else []})
            self.assertEqual(self.plan(snapshot)['moves'], [])

    def test_named_and_pinned_districts_protected(self):
        for key, value in [('pinned', True), ('customName', 'My coding'), ('autoSource', 'workspace')]:
            snapshot = fixture()
            snapshot['districts'][0][key] = value
            plan = self.plan(snapshot)
            self.assertEqual(plan['protectedDistricts'], 1)
            self.assertEqual(len(plan['moves']), 1)
            self.assertEqual(plan['moves'][0]['sourceWorkspace'], 3)
            self.assertEqual(plan['moves'][0]['destinationWorkspace'], 2)

    def test_focused_window_excluded(self):
        snapshot = fixture()
        snapshot['focused'] = '0x12'
        self.assertEqual([m['address'] for m in self.plan(snapshot)['moves']], ['0x13'])

    def test_different_category_destination_not_suggested(self):
        snapshot = fixture()
        for i, app in enumerate(('spotify', 'slack'), 50):
            snapshot['windows'].append({'address': hex(i), 'class': app, 'app': app, 'pid': i, 'workspace': 1})
        plan = self.plan(snapshot)
        self.assertEqual({m['destinationWorkspace'] for m in plan['moves']}, {2})

    def test_unsupported_hidden_special_and_injection_excluded(self):
        snapshot = fixture()
        snapshot['districts'].append({'id': -99, 'monitor': 0})
        for update in ({'address': '0x99', 'workspace': -99}, {'address': '0x88', 'hidden': True}, {'address': '0x1"})'}, {'address': '0x77', 'class': 'evil"'}) :
            snapshot['windows'].append({**snapshot['windows'][0], **update})
        plan = self.plan(snapshot)
        self.assertEqual(len(plan['moves']), 2)
        self.assertEqual(plan['omitted'], 5)

    def test_truncated_snapshot_refused(self):
        snapshot = fixture(); snapshot['truncated'] = True
        with self.assertRaisesRegex(ValueError, 'complete'):
            self.plan(snapshot)

    def test_cap_is_explicit(self):
        snapshot = fixture()
        snapshot['windows'] += [{**snapshot['windows'][0], 'address': hex(i + 1000), 'pid': i + 2000} for i in range(60)]
        snapshot['windows'] += [{**snapshot['windows'][1], 'address': hex(i + 300), 'pid': i + 1000} for i in range(40)]
        plan = self.plan(snapshot)
        self.assertEqual(len(plan['moves']), organize.MAX_MOVES)
        self.assertGreater(plan['deferred'], 0)

    def test_explicit_exact_acceptance_required(self):
        plan = self.plan()
        with patch.object(organize.bridge, 'query') as query, patch.object(organize.bridge, 'command') as cmd:
            with self.assertRaisesRegex(ValueError, 'exact'):
                organize.apply(plan, 'wrong', now=101)
            changed = deepcopy(plan); changed['moves'][0]['destinationWorkspace'] = 3
            with self.assertRaisesRegex(ValueError, 'exact'):
                organize.apply(changed, plan['planId'], now=101)
        query.assert_not_called(); cmd.assert_not_called()

    def test_expired_plan_never_queries_or_moves(self):
        plan = self.plan()
        with patch.object(organize.bridge, 'query') as query, patch.object(organize.bridge, 'command') as cmd:
            with self.assertRaisesRegex(ValueError, 'expired'):
                organize.apply(plan, plan['planId'], now=220)
        query.assert_not_called(); cmd.assert_not_called()

    def test_apply_scoped_moves_and_checks_each_move(self):
        desktop = Desktop(fixture())
        receipt = desktop.apply(self.plan())
        self.assertTrue(receipt['ok'])
        self.assertEqual(receipt['applied'], 2)
        self.assertEqual([c['workspace']['id'] for c in desktop.clients], [1, 1, 1])
        self.assertEqual(desktop.active, {'address': '0xff'})
        self.assertEqual(desktop.queries, ['workspaces', 'clients', 'activewindow', 'clients'] * 2)

    def test_reused_address_pid_class_or_source_aborts(self):
        for field, value in [('pid', 9999), ('class', 'slack'), ('workspace', {'id': 3}), ('hidden', True)]:
            desktop = Desktop(fixture()); desktop.clients[1][field] = value
            receipt = desktop.apply(self.plan())
            self.assertFalse(receipt['ok']); self.assertEqual(receipt['applied'], 0)
            self.assertEqual(len(receipt['items']), 2); self.assertEqual(receipt['items'][0]['status'], 'blocked')
            self.assertEqual(desktop.commands, [])

    def test_disappeared_or_changed_monitor_source_destination_aborts(self):
        for wid in (1, 2):
            desktop = Desktop(fixture())
            desktop.workspaces = [w for w in desktop.workspaces if w['id'] != wid]
            self.assertEqual(desktop.apply(self.plan())['applied'], 0)
            self.assertEqual(desktop.commands, [])
        desktop = Desktop(fixture()); desktop.workspaces[0]['monitorID'] = 1
        self.assertEqual(desktop.apply(self.plan())['applied'], 0)
        self.assertEqual(desktop.commands, [])

    def test_any_affected_membership_change_aborts(self):
        desktop = Desktop(fixture())
        desktop.clients.append({**desktop.clients[0], 'address': '0xaa', 'pid': 456})
        self.assertEqual(desktop.apply(self.plan())['applied'], 0)
        self.assertEqual(desktop.commands, [])

    def test_workspace_emptied_by_confirmed_move_can_retire(self):
        desktop = Desktop(fixture())
        desktop.before = lambda d: setattr(d, 'workspaces', [w for w in d.workspaces if any(c['workspace']['id'] == w['id'] for c in d.clients)])
        result = desktop.apply(self.plan())
        self.assertTrue(result['ok']); self.assertEqual(result['applied'], 2)

    def test_expiry_during_apply_stops_next_move(self):
        desktop = Desktop(fixture())
        with patch.object(organize.time, 'monotonic', side_effect=[0, 0, 121]):
            result = desktop.apply(self.plan())
        self.assertFalse(result['ok']); self.assertEqual(result['applied'], 1)
        self.assertIn('expired', result['message']); self.assertEqual(len(desktop.commands), 1)

    def test_changed_preferences_aborts_before_queries(self):
        desktop = Desktop(fixture())
        result = desktop.apply(self.plan(), prefs={'revision': 1, 'rules': {'code': 'mixed'}})
        self.assertEqual(result['applied'], 0)
        self.assertEqual(desktop.queries, [])
        self.assertEqual(desktop.commands, [])

    def test_protection_anchor_records_exact_unprotected_metadata(self):
        for anchor in self.plan()['districts']:
            self.assertEqual(anchor['protection'], {'customName': '', 'pinned': False, 'workspaceNamed': False, 'workspaceName': str(anchor['id'])})

    def test_new_name_pin_or_workspace_label_blocks_source_and_destination(self):
        for wid in (1, 2):
            for kind in ('customName', 'pin', 'workspaceName'):
                with self.subTest(workspace=wid, protection=kind):
                    desktop = Desktop(fixture())
                    if kind == 'customName': desktop.state['names'][str(wid)] = 'Personal coding'
                    elif kind == 'pin': desktop.state['pins'].append(str(wid))
                    else: next(w for w in desktop.workspaces if w['id'] == wid)['name'] = 'Personal coding'
                    result = desktop.apply(self.plan())
                    self.assertEqual(result['applied'], 0); self.assertIn('name or pin changed', result['message'])
                    self.assertEqual(desktop.commands, [])

    def test_protection_changes_between_moves_stop_with_partial_receipt(self):
        for wid in (1, 3):
            for kind in ('customName', 'pin', 'workspaceName'):
                with self.subTest(workspace=wid, protection=kind):
                    desktop = Desktop(fixture())
                    def mutate(d):
                        if kind == 'customName': d.state['names'][str(wid)] = 'Protected after first move'
                        elif kind == 'pin': d.state['pins'].append(str(wid))
                        else: next(w for w in d.workspaces if w['id'] == wid)['name'] = 'Protected after first move'
                    desktop.before = mutate
                    result = desktop.apply(self.plan())
                    self.assertEqual(result['applied'], 1); self.assertEqual(len(desktop.commands), 1)
                    self.assertEqual([r['status'] for r in result['items']], ['applied', 'blocked'])
                    self.assertIn('name or pin changed', result['message'])

    def test_architecture_rechecked_after_compositor_queries(self):
        desktop = Desktop(fixture()); query = desktop.query
        def mutate_last_query(name):
            result = query(name)
            if name == 'activewindow': desktop.state['pins'].append('1')
            return result
        desktop.query = mutate_last_query
        result = desktop.apply(self.plan())
        self.assertEqual(result['applied'], 0); self.assertEqual(desktop.commands, [])

    def test_missing_or_protected_anchor_refused_even_with_matching_digest(self):
        for value in (None, {'customName': 'My coding', 'pinned': False, 'workspaceNamed': False, 'workspaceName': '1'}):
            plan = self.plan()
            if value is None: del plan['districts'][0]['protection']
            else: plan['districts'][0]['protection'] = value
            plan['planId'] = organize.digest({k:v for k,v in plan.items() if k != 'planId'})
            with self.assertRaisesRegex(ValueError, 'protected or unknown'):
                organize.validate_plan(plan, plan['planId'], 101)

    def test_becomes_focused_aborts_before_move(self):
        desktop = Desktop(fixture()); desktop.active = {'address': '0x12'}
        result = desktop.apply(self.plan())
        self.assertEqual(result['applied'], 0)
        self.assertEqual(desktop.commands, [])

    def test_change_between_moves_keeps_honest_partial_receipt(self):
        desktop = Desktop(fixture())
        desktop.before = lambda d: d.clients[2].update({'pid': 555})
        result = desktop.apply(self.plan())
        self.assertFalse(result['ok']); self.assertEqual(result['applied'], 1)
        self.assertEqual([r['status'] for r in result['items']], ['applied', 'blocked'])
        self.assertEqual(len(desktop.commands), 1)

    def test_failed_or_unconfirmed_dispatch_stops(self):
        for response, confirm in [('error', True), ('ok', False)]:
            desktop = Desktop(fixture()); desktop.response = response; desktop.confirm = confirm
            result = desktop.apply(self.plan())
            self.assertFalse(result['ok']); self.assertEqual(result['applied'], 0)
            self.assertEqual([r['status'] for r in result['items']], ['unconfirmed', 'not-attempted'])
            self.assertEqual(len(desktop.commands), 1)

    def test_no_lua_means_no_legacy_or_unscoped_fallback(self):
        with patch.object(organize.bridge, 'lua_supported', return_value=False), patch.object(organize.bridge, 'command') as cmd:
            result = organize.apply(self.plan(), self.plan()['planId'], now=101)
        self.assertFalse(result['ok']); self.assertIn('scoped', result['message']); cmd.assert_not_called()

    def test_cli_preview_and_oversize_failure(self):
        run = subprocess.run([sys.executable, str(ROOT/'organize.py'), 'preview'], input=json.dumps(fixture()), text=True, capture_output=True)
        self.assertEqual(run.returncode, 0); self.assertEqual(len(json.loads(run.stdout)['plan']['moves']), 2)
        run = subprocess.run([sys.executable, str(ROOT/'organize.py'), 'preview'], input=' ' * (organize.MAX_INPUT + 1), text=True, capture_output=True)
        self.assertEqual(run.returncode, 1); self.assertIn('too large', json.loads(run.stdout)['error'])


QML_FIXTURE = r'''import QtQuick
import QtTest
import "__ROOT_URI__" as Districts
Item {
 id:host;width:912;height:512
 QtObject{id:city;property color panelPaper:"#f8f8f8";property color accent:"#005faa";property color ink:"#101010"}
 Districts.OrganizeV2{id:modal;anchors.fill:parent;city:city}
 SignalSpy{id:applySpy;target:modal;signalName:"applyRequested"}
 SignalSpy{id:cancelSpy;target:modal;signalName:"cancelRequested"}
 function plan(){var moves=[];for(var i=0;i<32;i++)moves.push({app:"W".repeat(64),sourceWorkspace:100000,destinationWorkspace:99999,sourceCount:512,destinationCount:512,sourceAfter:480,destinationAfter:544,reason:"Consolidate this public app with 512 matching window(s) in an existing communication district."});return {planId:"exact-plan",expiresAt:Math.floor(Date.now()/1000)+120,moves:moves,omitted:5,protectedDistricts:20,deferred:50}}
 TestCase{
  name:"OrganizerOffscreen";when:windowShown
  function init(){modal.plan=host.plan();modal.receipt=null;modal.error="";modal.busy=false;modal.nowSeconds=Math.floor(Date.now()/1000);modal.testPages.page=0;host.width=912;host.height=512;applySpy.clear();cancelSpy.clear();wait(60)}
  function fits(){var l=modal.testPages;verify(l.height>46);verify(l.testRows.height<=l.height-46+0.1);verify(modal.testHeading.y+modal.testHeading.height<=l.y);verify(l.y+l.height<=modal.testFooter.y);verify(modal.testFooter.y+modal.testFooter.height<=modal.testPanel.height-10);for(var i=0;i<l.shownEntries.length;i++){var r=l.testRow(i),col=r.children[1];verify(col.height<=r.height-12)}}
  function test_small_and_large_fit(){for(var size of [[912,512],[1280,720],[1600,1000],[3840,2160]]){host.width=size[0];host.height=size[1];wait(60);fits()}}
  function test_all_proposals_paged(){var keys=[],l=modal.testPages;for(var page=0;page<l.pageCount;page++){fits();keys=keys.concat(l.shownEntries.map(function(e){return e.key}));if(page+1<l.pageCount){mouseClick(l.testNext,l.testNext.width/2,19);wait(30)}}compare(keys.length,32);compare(new Set(keys).size,32)}
  function test_exact_explicit_apply_and_cancel(){compare(applySpy.count,0);mouseClick(modal.testApply,modal.testApply.width/2,19);compare(applySpy.count,1);compare(applySpy.signalArguments[0][0],"exact-plan");mouseClick(modal.testCancel,modal.testCancel.width/2,19);compare(cancelSpy.count,1);compare(modal.plan.moves.length,32)}
  function test_expiry_busy_receipt_guards(){modal.nowSeconds=modal.plan.expiresAt;compare(modal.testApply.enabled,false);modal.nowSeconds=modal.plan.expiresAt-1;compare(modal.testApply.enabled,true);modal.busy=true;compare(modal.testApply.enabled,false);compare(modal.testCancel.enabled,false);modal.busy=false;modal.receipt={applied:1,total:32,message:"An affected district changed after preview. Preview again.",items:modal.plan.moves.map(function(m){return {app:m.app,sourceWorkspace:m.sourceWorkspace,destinationWorkspace:m.destinationWorkspace,status:"not-attempted",message:"Stopped after the preceding result."}})};wait(60);compare(modal.testApply.enabled,false);fits();verify(modal.testCancel.enabled)}
 }
}
'''


class OrganizerUiTests(unittest.TestCase):
    @unittest.skipUnless(Path('/usr/lib/qt6/bin/qmltestrunner').exists(), 'Qt Quick Test unavailable')
    def test_plan_digest_survives_real_qt_json_transport(self):
        snapshot = fixture()
        snapshot['windows'][0]['app'] = '研究'
        plans = [organize.preview(snapshot, now=epoch)['plan'] for epoch in (100.0, 100.25, 1700000000.0, 1791316800.1234567, 1791316800.9999998)]
        plans.append(organize.preview(snapshot)['plan'])
        qml = """import QtQuick
import QtTest
Item{
 property string payload: PAYLOAD
 TestCase{name: "OrganizerJsonTransport";when:windowShown
  function test_roundtrip(){var plans=JSON.parse(parent.payload);for(var i=0;i<plans.length;i++)console.log("ORGANIZER_JSON "+i+" "+JSON.stringify(JSON.parse(JSON.stringify(plans[i]))))}
 }
}""".replace('PAYLOAD', json.dumps(json.dumps(plans)))
        with tempfile.TemporaryDirectory(prefix='districts-organize-json-qa-') as directory:
            fixture_path = Path(directory)/'tst_transport.qml'; fixture_path.write_text(qml)
            environment = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software', 'QT_QPA_PLATFORMTHEME': '', 'QT_STYLE_OVERRIDE': 'Basic'}
            run = subprocess.run(['/usr/lib/qt6/bin/qmltestrunner', '-input', str(fixture_path), '-o', '-,txt'], env=environment, text=True, capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        lines = [line.split('ORGANIZER_JSON ',1)[1].split(' ',1)[1] for line in run.stdout.splitlines() if 'ORGANIZER_JSON ' in line]
        self.assertEqual(len(lines), len(plans), run.stdout)
        converted = [json.loads(line) for line in lines]
        self.assertIs(type(plans[0]['createdAt']), float)
        self.assertIs(type(converted[0]['createdAt']), int)
        # This is the pre-fix bug: Python's raw 100.0 JSON differs from Qt's 100.
        legacy = lambda plan: json.dumps({k:v for k,v in plan.items() if k != 'planId'}, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        self.assertNotEqual(legacy(plans[0]), legacy(converted[0]))
        for original, transported in zip(plans, converted):
            expected = organize.validate_plan(transported, original['planId'], original['createdAt'] + 1)
            self.assertEqual(len(expected), 3)
            self.assertEqual(organize.digest(original), organize.digest(transported))

    def test_digest_rejects_nonfinite_or_unsafe_json_numbers(self):
        for value in (float('nan'), float('inf'), 9007199254740992):
            with self.assertRaises(ValueError): organize.digest({'value':value})
        self.assertEqual(organize.digest({'value':-0.0}), organize.digest({'value':0}))

    @unittest.skipUnless(Path('/usr/lib/qt6/bin/qmltestrunner').exists(), 'Qt Quick Test unavailable')
    def test_offscreen_fit_pagination_and_explicit_controls(self):
        with tempfile.TemporaryDirectory(prefix='districts-organize-qa-') as directory:
            fixture_path = Path(directory)/'tst_organize.qml'
            fixture_path.write_text(QML_FIXTURE.replace('__ROOT_URI__', ROOT.as_uri()))
            environment = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software', 'QT_QPA_PLATFORMTHEME': '', 'QT_STYLE_OVERRIDE': 'Basic'}
            run = subprocess.run(['/usr/lib/qt6/bin/qmltestrunner', '-input', str(fixture_path), '-o', '-,txt'], env=environment, text=True, capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertNotIn('QWARN', run.stdout, run.stdout)


if __name__ == '__main__':
    unittest.main()
