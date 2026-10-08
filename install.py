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
RUNTIME=['v3.0.0/AgentCityV2.js', 'v3.0.0/AgentV2.qml', 'v3.0.0/AtlasV2.qml', 'v3.0.0/CameraV2.js', 'v3.0.0/CityV2.js', 'v3.0.0/DistrictsV2.qml', 'v3.0.0/GroupsV2.js', 'v3.0.0/InspectorV2.qml', 'v3.0.0/LegendV2.qml', 'v3.0.0/LensV2.js', 'v3.0.0/LensV2.qml', 'v3.0.0/MoveV2.qml', 'v3.0.0/NavigationV2.js', 'v3.0.0/NavigationV2.qml', 'v3.0.0/NeonActionV2.qml', 'v3.0.0/OrganizeV2.qml', 'v3.0.0/PagedListV2.qml', 'v3.0.0/ResourcesV2.js', 'v3.0.0/ResourcesV2.qml', 'v3.0.0/districts.py', 'v3.0.0/history.py', 'v3.0.0/organize.py', 'v3.0.0/resources.py', 'v3.0.0/sessions.py', 'v3.0.0/provider_claude.py', 'v3.0.0/provider_grok.py', 'v3.0.0/provider_pi.py', 'v3.0.0/provider_metrics.py', 'v3.0.0/ProviderLegendV2.js', 'v3.0.0/ProviderLegendV2.qml', 'v3.0.0/PaceDockV2.qml', 'manifest.json', 'README.md', 'LICENSE']

def ipc(method, *args):
 return subprocess.check_output(['omarchy-shell', 'shell', method, *args],
                                text=True, stderr=subprocess.PIPE, timeout=8).strip()

def entry_id(entry):
 return entry.get('id') if isinstance(entry, dict) else entry

def placements(config):
 return [(section, index, entry) for section, entries in config.get('bar', {}).get('layout', {}).items()
         for index, entry in enumerate(entries) if entry_id(entry) == ID]

def without_ours(config):
 data=json.loads(json.dumps(config))
 for entries in data.get('bar',{}).get('layout',{}).values():
  entries[:]=[entry for entry in entries if entry_id(entry)!=ID]
 if 'plugins' in data:data['plugins']=[entry for entry in data['plugins'] if entry_id(entry)!=ID]
 # Enabling only our plugin may remove its explicit disabled marker. Do not
 # normalize unrelated empty fields or allow changes to other markers.
 if ID in data.get('disabledPlugins',[]):
  disabled=[entry for entry in data['disabledPlugins'] if entry!=ID]
  if disabled:data['disabledPlugins']=disabled
  else:data.pop('disabledPlugins',None)
 return data

def persistence_state():
 """Only a proven missing function permits the older-shell readback path."""
 try:
  raw=ipc('configPersistenceState')
 except subprocess.CalledProcessError as error:
  if (error.stderr or '').strip() == 'Function not found.':return None
  raise
 if raw == 'Function not found.':return None
 state=json.loads(raw)
 if not isinstance(state,dict):raise RuntimeError('Invalid desktop persistence response.')
 return state

def require_ready(state):
 if state is not None and (state.get('ready') is not True or state.get('saving') or state.get('error')):
  raise RuntimeError('Desktop configuration is busy or failed; inspect current state before retrying.')

def agreed_config():
 """Fresh live -> saved -> live read; no config mutation or defaults guess."""
 live=json.loads(ipc('listShellConfig'))
 if not isinstance(live,dict):raise RuntimeError('Invalid live desktop configuration.')
 saved=json.loads((Path.home()/'.config/omarchy/shell.json').read_text())
 if saved!=live or json.loads(ipc('listShellConfig'))!=live:
  raise RuntimeError('Live and saved desktop configuration disagree; inspect current state before retrying.')
 return live

def settled_config():
 # The runtime swap hot-reloads the plugin inside the shell; its IPC can refuse
 # one call mid-reload. Retry transport failures only; any disagreement or
 # change still stops activation.
 deadline=time.monotonic()+8
 while True:
  try:return agreed_config()
  except subprocess.SubprocessError:
   if time.monotonic()>=deadline:raise
   time.sleep(.25)

def unchanged_config(before, phase, has_state_api=False):
 if has_state_api:
  state=persistence_state()
  if state is None:raise RuntimeError('Desktop persistence API changed during activation.')
  require_ready(state)
 if settled_config()!=before:
  raise RuntimeError('Configuration changed '+phase+'; runtime staged but activation stopped. Inspect current state without restoring a backup.')

def catalog_entry():
 entries=json.loads(ipc('listPlugins'))
 if not isinstance(entries,list):raise RuntimeError('Invalid plugin discovery response.')
 found=[entry for entry in entries if isinstance(entry,dict) and entry.get('id')==ID]
 if len(found)>1:raise RuntimeError('Plugin discovery is ambiguous; activation stopped.')
 return found[0] if found else None

def persisted_after(has_state_api):
 deadline=time.monotonic()+8
 last_error=None
 while time.monotonic()<deadline:
  try:
   if has_state_api:
    state=persistence_state()
    if state is None:raise RuntimeError('Desktop persistence API changed during activation.')
    require_ready(state)
   return agreed_config()
  except (OSError,ValueError,RuntimeError) as error:
   last_error=error
   time.sleep(.15)
 raise RuntimeError('Activation persistence could not be verified; inspect newest live/saved state without restoring a backup.') from last_error

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
 before=None;has_state_api=False
 if args.enable:
  state=persistence_state();has_state_api=state is not None;require_ready(state)
  before=agreed_config()
  if len(placements(before))>1:raise RuntimeError('Districts has multiple bar placements; resolve the ambiguity before installing.')
  p=backup/'shell-live.json';p.write_text(json.dumps(before,indent=2));p.chmod(0o600)
  p=backup/'shell-saved.json';p.write_text((Path.home()/'.config/omarchy/shell.json').read_text());p.chmod(0o600)
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
 receipt={'id':ID,'version':'3.0.0','installed':str(dest),'backup':str(backup),'enabled':False,
          'hashes':{name:hashlib.sha256((dest/name).read_bytes()).hexdigest()for name in RUNTIME}}
 try:
  if args.enable:
   unchanged_config(before,'during staging',has_state_api)
   subprocess.run(['omarchy-shell','shell','rescanPlugins'],check=True)
   # Registry rescans finish asynchronously; do not restart the shell.
   deadline=time.monotonic()+8;entry=None
   while time.monotonic()<deadline:
    entry=catalog_entry()
    if entry is not None:break
    time.sleep(.15)
   else:raise RuntimeError('Plugin discovery did not complete; runtime is installed but not enabled.')
   unchanged_config(before,'during discovery',has_state_api)
   prior_placements=placements(before)
   if prior_placements:
    # Empty placement preserves section, index, entry settings and zone. The
    # catalog's bar-widget enabled bit reflects placement, so also inspect
    # the explicit disabled marker before deciding activation is complete.
    if not entry.get('enabled') or ID in before.get('disabledPlugins',[]):
     subprocess.run(['omarchy','plugin','enable',ID],check=True)
   else:
    append_index=len(before.get('bar',{}).get('layout',{}).get('right',[]))
    subprocess.run(['omarchy','plugin','enable',ID,'--section','right','--index',str(append_index)],check=True)
   after=persisted_after(has_state_api)
   if prior_placements and placements(after)!=prior_placements:
    raise RuntimeError('Existing Districts bar position or settings changed; inspect current state without restoring a backup.')
   if not prior_placements and [(section,index) for section,index,_ in placements(after)]!=[('right',append_index)]:
    raise RuntimeError('New Districts placement differs from the requested append position; inspect current state.')
   if without_ours(before)!=without_ours(after):
    raise RuntimeError('Unrelated configuration changed; inspect newest live state without restoring a backup.')
   active=catalog_entry()
   if active is None or active.get('enabled') is not True or ID in after.get('disabledPlugins',[]) or len(placements(after))!=1:
    raise RuntimeError('Districts enablement could not be verified; inspect current plugin state.')
   if agreed_config()!=after:raise RuntimeError('Configuration changed during final enablement readback; inspect current state.')
   receipt['persistenceMode']='state-api' if has_state_api else 'live-saved-readback'
   receipt['enabled']=True;receipt['preservation']='PASS: unrelated live fields/order/settings preserved'
 except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
  receipt['activationError']=str(error)
 receipt_path.write_text(json.dumps(receipt,indent=2)+'\n');receipt_path.chmod(0o600)
 print(json.dumps(receipt,indent=2));return 1 if receipt.get('activationError')else 0

if __name__=='__main__':raise SystemExit(main())
