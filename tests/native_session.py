"""Bounded native QA session with readiness/IPC phases and unconditional cleanup."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
PASSIVE_GUARD='''
 PanelWindow {
  id:qaSurface;visible:true;implicitWidth:1;implicitHeight:1;color:"transparent"
  exclusionMode:ExclusionMode.Ignore
  WlrLayershell.namespace:"districts-qa-guard"
  WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
  mask:Region {item:null}
 }
 IdleInhibitor {window:qaSurface;enabled:true}
'''

class NativeSession:
 def __init__(self,name,qml,*,live=False,guard=True):
  self.name=name;self.qml=qml;self.live=live;self.guard=guard;self.process=None
 def __enter__(self):
  self.temporary=tempfile.TemporaryDirectory(prefix='districts-'+self.name+'-',dir='/tmp')
  self.work=Path(self.temporary.name)
  for name in ('Commons','Ui','services'):
   (self.work/name).symlink_to(Path(os.environ['OMARCHY_PATH'])/'shell'/name,target_is_directory=True)
  runtime=Path(os.environ.get('DISTRICTS_RUNTIME',str(ROOT)))
  for name in ('DistrictsV2.qml','CityV2.js','CameraV2.js','NeonActionV2.qml','InspectorV2.qml','AtlasV2.qml','MoveV2.qml','PagedListV2.qml','GroupsV2.js','LegendV2.qml','districts.py','manifest.json'):shutil.copy2(runtime/'v2.2'/name if os.environ.get('DISTRICTS_RUNTIME')and(runtime/'v2.2'/name).exists()else runtime/name,self.work/name)
  self.config=self.work/'shell.qml'
  self.config.write_text(self.qml.replace('QA_GUARD',PASSIVE_GUARD if self.guard else ''))
  self.env={**os.environ,'QT_QPA_PLATFORM':'wayland','XDG_RUNTIME_DIR':f'/run/user/{os.getuid()}',
            'WAYLAND_DISPLAY':os.environ.get('WAYLAND_DISPLAY')or'wayland-1','XDG_STATE_HOME':str(self.work/'state')}
  if self.live and not self.env.get('HYPRLAND_INSTANCE_SIGNATURE'):
   candidates=[p for p in (Path(self.env['XDG_RUNTIME_DIR'])/'hypr').glob('*')if(p/'hyprland.lock').exists()]
   if candidates:self.env['HYPRLAND_INSTANCE_SIGNATURE']=max(candidates,key=lambda p:p.stat().st_mtime).name
  self.path=ROOT/'verification'/(self.name+'.log');self.path.parent.mkdir(exist_ok=True)
  self.logfile=self.path.open('w');self.started=time.monotonic()
  self.process=subprocess.Popen(['quickshell','--no-color','--path',str(self.config)],env=self.env,stdout=self.logfile,stderr=self.logfile)
  return self
 def log(self):return self.path.read_text()
 def marker(self,value,timeout=10):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   if value in self.log():return
   if self.process.poll()is not None:raise AssertionError('Native session exited before '+value+'\n'+self.log())
   time.sleep(.05)
  raise AssertionError('Native marker timed out: '+value+'\n'+self.log())
 def ipc(self,method,*args):
  r=subprocess.run(['quickshell','ipc','--pid',str(self.process.pid),'call','harness',method,*args],env=self.env,capture_output=True,text=True,timeout=5)
  if r.returncode:raise AssertionError('Native IPC failed: '+method+'\n'+r.stderr)
  return r.stdout.strip()
 def status(self):return json.loads(self.ipc('status'))
 def quit(self):
  self.ipc('quit');self.process.wait(timeout=5)
  assert self.process.returncode==0,self.log()
 def readings(self):
  data=Path(f'/proc/{self.process.pid}/stat').read_text().rsplit(')',1)[1].split()
  cpu=(int(data[11])+int(data[12]))/os.sysconf('SC_CLK_TCK')
  text=Path(f'/proc/{self.process.pid}/status').read_text()
  rss=int(next(line.split()[1]for line in text.splitlines()if line.startswith('VmRSS:')))
  return time.monotonic(),cpu,rss
 def __exit__(self,*unused):
  if self.process and self.process.poll()is None:
   self.process.terminate()
   try:self.process.wait(timeout=3)
   except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=3)
  self.logfile.close();self.temporary.cleanup()
  (ROOT/'verification'/(self.name+'-lifecycle.json')).write_text(json.dumps({
   'pid':self.process.pid,'exitCode':self.process.returncode,'elapsedSeconds':round(time.monotonic()-self.started,2),
   'reaped':self.process.poll()is not None,'passiveGuard':self.guard},indent=2))

def clean_log(log):
 for bad in ('ERROR:','ReferenceError','TypeError','Unable to assign','is not a type','FAIL!','Cannot specify','Binding loop'):
  assert bad not in log,log
