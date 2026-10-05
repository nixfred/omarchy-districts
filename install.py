#!/usr/bin/env python3
"""Stage Districts, validate it, and optionally enable via the public scoped API."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parent
ID='nixfred.districts'
RUNTIME=['v2.2/DistrictsV2.qml', 'v2.2/CityV2.js', 'v2.2/CameraV2.js', 'v2.2/NeonActionV2.qml', 'v2.2/InspectorV2.qml', 'v2.2/AtlasV2.qml', 'v2.2/MoveV2.qml', 'v2.2/districts.py', 'v2.2/PagedListV2.qml','v2.2/GroupsV2.js','v2.2/LegendV2.qml', 'manifest.json', 'README.md', 'LICENSE']

def ipc(method,*args):
 return subprocess.check_output(['omarchy-shell','shell',method,*args],text=True,timeout=8).strip()

def without_ours(config):
 data=json.loads(json.dumps(config))
 for entries in data.get('bar',{}).get('layout',{}).values():entries[:]=[e for e in entries if (e.get('id')if isinstance(e,dict)else e)!=ID]
 data['plugins']=[e for e in data.get('plugins',[])if (e.get('id')if isinstance(e,dict)else e)!=ID]
 return data

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--destination',type=Path,default=Path.home()/'.config/omarchy/plugins'/ID)
 parser.add_argument('--receipt',type=Path)
 parser.add_argument('--enable',action='store_true')
 args=parser.parse_args();dest=args.destination.expanduser().absolute()
 if dest==ROOT or ROOT in dest.parents or dest in ROOT.parents or dest.is_symlink():parser.error('Destination must be separate from source and not a symlink.')
 if dest.exists()and not dest.is_dir():parser.error('Destination must be a directory.')
 if args.enable and dest!=Path.home()/'.config/omarchy/plugins'/ID:parser.error('Enable requires the standard plugin destination.')
 if dest.exists() and any(dest.iterdir()):
  try:existing=json.loads((dest/'manifest.json').read_text())
  except (OSError,ValueError):parser.error('Refusing to replace an unrelated directory.')
  if existing.get('id')!=ID:parser.error('Destination belongs to another plugin.')
 subprocess.run(['omarchy','plugin','validate',str(ROOT)],check=True)
 receipt_path=args.receipt or Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'districts/installation.json'
 receipt_path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 backup=receipt_path.parent/'backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(mode=0o700,parents=True)
 before=None
 if args.enable:
  state=json.loads(ipc('configPersistenceState'))
  if not state.get('ready')or state.get('saving')or state.get('error'):raise RuntimeError('Desktop config is busy; retry when ready.')
  before=json.loads(ipc('listShellConfig'));p=backup/'shell-live.json';p.write_text(json.dumps(before,indent=2));p.chmod(0o600)
 if dest.exists():shutil.copytree(dest,backup/'plugin',symlinks=True)
 dest.parent.mkdir(parents=True,exist_ok=True)
 stage=Path(tempfile.mkdtemp(prefix='.districts-stage-',dir=dest.parent));displaced=backup/'displaced'
 try:
  for name in RUNTIME:
   (stage/name).parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,stage/name)
  subprocess.run(['omarchy','plugin','validate',str(stage)],check=True)
  if dest.exists():dest.rename(displaced)
  try:stage.rename(dest)
  except OSError:
   if displaced.exists():displaced.rename(dest)
   raise
 finally:
  if stage.exists():shutil.rmtree(stage)
 receipt={'id':ID,'version':'2.2.0','installed':str(dest),'backup':str(backup),'enabled':False,
          'hashes':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest()for name in RUNTIME}}
 try:
  if args.enable:
   if json.loads(ipc('listShellConfig'))!=before:raise RuntimeError('Configuration changed during staging; plugin installed but not enabled. Retry activation against current state.')
   subprocess.run(['omarchy-shell','shell','rescanPlugins'],check=True)
   # Registry rescans complete asynchronously after the IPC call returns.
   deadline=time.monotonic()+8
   while time.monotonic()<deadline:
    if any(entry.get('id')==ID for entry in json.loads(ipc('listPlugins'))):break
    time.sleep(.15)
   else:raise RuntimeError('Plugin discovery did not complete; runtime is installed but not enabled.')
   if json.loads(ipc('listShellConfig'))!=before:raise RuntimeError('Configuration changed during discovery; retry activation against current state.')
   already_placed=any((entry.get('id')if isinstance(entry,dict)else entry)==ID for entries in before.get('bar',{}).get('layout',{}).values()for entry in entries)
   if not already_placed:
    append_index=len(before.get('bar',{}).get('layout',{}).get('right',[]))
    subprocess.run(['omarchy','plugin','enable',ID,'--section','right','--index',str(append_index)],check=True)
   for attempt in range(20):
    state=json.loads(ipc('configPersistenceState'))
    if state.get('ready')and not state.get('saving')and not state.get('error'):break
    time.sleep(.15)
   else:raise RuntimeError('Activation persistence is busy; inspect newest live state without restoring a backup.')
   after=json.loads(ipc('listShellConfig'));saved=json.loads((Path.home()/'.config/omarchy/shell.json').read_text())
   if already_placed and before!=after:raise RuntimeError('Existing plugin configuration changed during code-only update; inspect current state without restoring a backup.')
   if without_ours(before)!=without_ours(after):raise RuntimeError('Unrelated configuration changed; inspect newest live state without restoring a backup.')
   if saved!=after:raise RuntimeError('Activation is not yet persisted; inspect configPersistenceState.')
   receipt['enabled']=True;receipt['preservation']='PASS: unrelated live fields/order/settings preserved'
 except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
  receipt['activationError']=str(error)
 receipt_path.write_text(json.dumps(receipt,indent=2)+'\n');receipt_path.chmod(0o600)
 print(json.dumps(receipt,indent=2));return 1 if receipt.get('activationError')else 0

if __name__=='__main__':raise SystemExit(main())
