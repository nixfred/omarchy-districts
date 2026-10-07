"""Verify installed/live runtime and cropped actual skyline without opening city."""
import collections,importlib.util,json,hashlib,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';DEST=Path.home()/'.config/omarchy/plugins/nixfred.districts'
os.environ['XDG_RUNTIME_DIR']='/run/user/1000';os.environ['WAYLAND_DISPLAY']='wayland-1'
def ipc(target,method):return json.loads(subprocess.check_output(['omarchy-shell',target,method],text=True,timeout=8))
receipt=json.loads((OUT/'installation.json').read_text());before=json.loads((Path(receipt['backup'])/'shell-live.json').read_text());current=ipc('shell','listShellConfig');saved=json.loads((Path.home()/'.config/omarchy/shell.json').read_text());assert current==before==saved,'Current state drifted: preserve freshest user state and inspect rather than restoring backup'
for name,expected in receipt['hashes'].items():assert hashlib.sha256((DEST/name).read_bytes()).hexdigest()==expected,name
assert set(p.relative_to(DEST).as_posix()for p in DEST.rglob('*')if p.is_file())==set(receipt['hashes'])
status=ipc('nixfred.districts','status');assert status['version']=='2.0.0'and not status['opened']and not status['collector']and not status['cameraRunning']and not status['edgeRunning'],status
time.sleep(.6);assert ipc('nixfred.districts','status')['frames']==status['frames']
geometry=ipc('shell','debugBarGeometry');slot=next(e for e in geometry if e['id']=='nixfred.districts');assert slot['visible']and slot['shown']and slot['itemVisible']and slot['width']>=25,slot
layout=current['bar']['layout'];positions=[{'section':s,'index':i}for s,entries in layout.items()for i,e in enumerate(entries)if e['id']=='nixfred.districts'];assert len(positions)==1
# The exact installed helper supplies real title-free labels; save only source counts.
spec=importlib.util.spec_from_file_location('installed_districts',DEST/'v2/districts.py');bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
# Bar geometry is local to its screen; grim needs compositor-global coordinates.
monitors=bridge.query('monitors');monitor=next((m for m in monitors if m.get('focused')),monitors[0])
path=OUT/'activation-launcher.png';crop=f"{slot['x']+monitor['x']},{slot['y']+monitor['y']} {slot['width']}x{slot['height']}"
subprocess.run(['grim','-g',crop,str(path)],check=True,timeout=5)
frame=bridge.snapshot();sources=collections.Counter();all_grounded=True
for d in frame['districts']:
 key=str(d['id']);mix=sorted({w['app']for w in frame['windows']if w['workspace']==d['id']},key=str.casefold);sources[d['nameSource']]+=1
 if d['nameSource']=='apps':assert d['name']==' + '.join(mix[:3])[:48],d['nameSource']
 elif d['nameSource']=='number':assert d['name']=='Workspace '+key
 elif d['nameSource']=='custom':assert d['name']==d['customName']
 elif d['nameSource']=='workspace':assert d['name']==d['autoName']
 else:raise AssertionError('Unknown source')
assert 'title'not in json.dumps(frame)
# Read only current process identity; no restart, signal or dispatch.
listing=subprocess.check_output(['quickshell','list','--all'],text=True)
import re
pids=[int(m.group(1))for m in re.finditer(r'Process ID: (\d+)\n.*?Config path: ([^\n]+)',listing,re.S)if m.group(2).endswith('/omarchy/shell/shell.qml')];assert len(pids)==1,pids
assert pids[0]==393276,'Shell PID changed; inspect independent user restart'
log=Path(f'/run/user/1000/quickshell/by-pid/{pids[0]}/log.log');tail=log.read_text(errors='replace').splitlines()[-100:];new_errors=[line for line in tail if ('/v2/'in line or 'DistrictsV2'in line)and any(t in line for t in ['ERROR','TypeError','ReferenceError','Unable to assign','case mismatch'])];assert not new_errors,new_errors
report={'installedVersion':'2.0.0','runtimeHashesMatch':True,'exact11Files':True,'currentAndSavedEqualFreshBaseline':True,'wholeShellRestarted':False,'shellPidPreserved':pids[0],'districtsPlacement':positions[0],'skylineSlot':slot,'actualSkylineCrop':str(path),'globalCrop':crop,'screen':monitor['name'],'opened':False,'closedFramesStable':True,'collectorAndCameraAndEdgeStopped':True,'liveGroundedNamesVerified':True,'nameSources':dict(sources),'liveDistrictCount':len(frame['districts']),'newDistrictErrors':new_errors,'noFocusOrWorkspaceDispatch':True,'layoutGap':'Inspector, Atlas and move destination lists currently scroll; require pagination/adaptive passport for Fred no-scroll preference. City pan/zoom remains intentional.'}
(OUT/'activation-health.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
