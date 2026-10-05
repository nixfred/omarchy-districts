#!/usr/bin/env python3
"""Districts' bounded, title-free compositor bridge. Python standard library only."""
import argparse
import configparser
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time
import unicodedata

VERSION = "2.2.0"
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{1,16}$")
APP = re.compile(r"[^\w .+@()-]", re.UNICODE)
LIMIT = 512
GROUP_COLORS = {'development':'#57dfff','entertainment':'#b99cff','communication':'#fc69d5','research':'#b0fca9','system':'#ffcd78','mixed':'#aebbd0'}
DESKTOP_CATEGORIES = {'Development','Game','AudioVideo','Audio','Video','Chat','InstantMessaging','Email','Office','Education','Science','Graphics','System','Utility','WebBrowser'}


def grouping(value=None):
    value=value if isinstance(value,dict)else {}
    colors={};rules={}
    for key,color in (value.get('colors',{}).items()if isinstance(value.get('colors'),dict)else []):
        if key in GROUP_COLORS and isinstance(color,str)and re.fullmatch(r'#[0-9a-fA-F]{6}',color):colors[key]=color.lower()
    resolved={k:colors.get(k,v)for k,v in GROUP_COLORS.items()}
    if len(set(resolved.values()))!=len(resolved):colors={}
    for key,role in list(value.get('rules',{}).items())[:128]if isinstance(value.get('rules'),dict)else []:
        if isinstance(key,str)and key and len(key)<=96 and APP.sub('',key)==key and isinstance(role,str)and role in GROUP_COLORS:rules[key.lower()]=role
    try:revision=integer(value.get('revision',0),0,1000000000)
    except (ValueError,TypeError):revision=0
    return {'revision':revision,'colors':colors,'rules':rules}


def edit_group(group=None,color=None,app=None,rule=None):
    if group is not None and group not in GROUP_COLORS:raise ValueError('Choose a known group.')
    if color is not None and(group is None or(color!='default'and not re.fullmatch(r'#[0-9a-fA-F]{6}',color))):raise ValueError('Use a six-digit hex color, such as #57dfff.')
    if app is not None and(not app or len(app)>96 or APP.sub('',app)!=app):raise ValueError('Choose a current public app identity.')
    if rule is not None and(rule not in GROUP_COLORS and rule!='auto'):raise ValueError('Choose a known app group or Automatic.')
    if (app is None)!=(rule is None)or(color is None and app is None):raise ValueError('Choose a group color or an app rule.')
    if color is not None and app is not None:raise ValueError('Choose one grouping edit per call.')
    path=state_path()
    with architecture_lock(path):
        state=read_state(path);prefs=grouping(state.get('grouping'))
        if color is not None:
            if color=='default':prefs['colors'].pop(group,None)
            else:prefs['colors'][group]=color.lower()
            resolved=[prefs['colors'].get(k,v)for k,v in GROUP_COLORS.items()]
            if len(set(resolved))!=len(resolved):raise ValueError('Each group needs a different color.')
        if app is not None:
            key=app.lower()
            if rule=='auto':prefs['rules'].pop(key,None)
            else:
                if key not in prefs['rules']and len(prefs['rules'])>=128:raise ValueError('Clear an unused app rule before adding another.')
                prefs['rules'][key]=rule
        prefs['revision']=min(1000000000,prefs['revision']+1);state['grouping']=prefs;write_state(path,state)
    return {'ok':True,'grouping':prefs}



def environment():
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    if not env.get("HYPRLAND_INSTANCE_SIGNATURE"):
        base = Path(env["XDG_RUNTIME_DIR"]) / "hypr"
        candidates = [p for p in base.glob("*") if p.is_dir() and (p / "hyprland.lock").exists()]
        if candidates:
            env["HYPRLAND_INSTANCE_SIGNATURE"] = max(candidates, key=lambda p: p.stat().st_mtime).name
    return env


def command(args):
    result = subprocess.run(["hyprctl", *args], env=environment(), capture_output=True,
                            text=True, timeout=3, check=False)
    if result.returncode:
        raise RuntimeError("Compositor did not answer. Refresh when the desktop is available.")
    return result.stdout


def query(name):
    data = json.loads(command(["-j", name]))
    if not isinstance(data, (list, dict)):
        raise ValueError("Invalid compositor response")
    return data


def integer(value, low=-100000, high=100000):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a coordinate")
    result = int(value)
    if not low <= result <= high:
        raise ValueError("Coordinate out of range")
    return result


def seed_for(identity):
    return int.from_bytes(hashlib.sha256(str(identity).encode()).digest()[:4], "big") % 1000000


def state_path():
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "districts" / "architecture.json"


def label(value):
    value=str(value).strip()
    if len(value)>48 or any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError("Use a name of up to 48 visible characters.")
    return value


def read_state(path):
    empty={"schema":2,"seeds":{},"names":{},"pins":[],"tints":{},"grouping":grouping()}
    try:
        if path.stat().st_size>128000:return empty
        data=json.loads(path.read_text())
        if data.get('schema')not in (1,2):return empty
        seeds={str(integer(k,1,100000)):integer(v,0,999999)for k,v in list(data.get('seeds',{}).items())[-LIMIT:]}
        names={};tints={}
        for key in seeds:
            try:
                name=label(data.get('names',{}).get(key,''))
                if name:names[key]=name
                if key in data.get('tints',{}):tints[key]=integer(data['tints'][key],0,4)
            except (ValueError,TypeError):pass
        pins=[str(integer(k,1,100000))for k in data.get('pins',[])[:LIMIT]if str(k)in seeds]
        return {"schema":2,"seeds":seeds,"names":names,"pins":list(dict.fromkeys(pins)),"tints":tints,"grouping":grouping(data.get("grouping"))}
    except (OSError,ValueError,TypeError,AttributeError):return empty


def write_state(path,data):
    protected={k for k in data['seeds'] if data.get('names',{}).get(k) or k in data.get('pins',[]) or k in data.get('tints',{})}
    if len(protected)>LIMIT:raise ValueError('The city already has 512 personalized districts. Clear an unused label, pin or circuit before adding another.')
    ordinary=[k for k in data['seeds'] if k not in protected]
    keys=ordinary[-(LIMIT-len(protected)):]if len(protected)<LIMIT else []
    keys += [k for k in data['seeds']if k in protected]
    data={**data,'schema':2,'seeds':{k:data['seeds'][k]for k in keys},
      'names':{k:v for k,v in data.get('names',{}).items()if k in keys},
      'pins':[k for k in data.get('pins',[])if k in keys],
      'tints':{k:v for k,v in data.get('tints',{}).items()if k in keys},'grouping':grouping(data.get('grouping'))}
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.architecture-',dir=path.parent)
    try:
        with os.fdopen(fd,'w')as handle:
            json.dump(data,handle,ensure_ascii=False);handle.write('\n');handle.flush();os.fsync(handle.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)


def load_architecture(path):return read_state(path)['seeds']


def save_architecture(path,seeds):
    data=read_state(path);data['seeds']=seeds;write_state(path,data)


def customize(workspace,name=None,pinned=None,tint=None):
    wid=integer(workspace,1);key=str(wid);path=state_path()
    if name is not None:name=label(name)
    if tint is not None:tint=integer(tint,0,4)
    with architecture_lock(path):
        data=read_state(path);data['seeds'].setdefault(key,seed_for('district-'+key))
        if name is not None:
            if name:data['names'][key]=name
            else:data['names'].pop(key,None)
        if pinned is not None:
            data['pins']=[k for k in data['pins']if k!=key]
            if pinned:data['pins'].append(key)
        if tint is not None:data['tints'][key]=tint
        write_state(path,data)
    return {'ok':True,'workspace':wid}


@contextmanager
def architecture_lock(path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor = os.open(path.parent / '.architecture.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def desktop_apps():
    """Read public desktop entry labels/icons. Never execute Exec fields."""
    roots = [Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))]
    roots += [Path(p) for p in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if p]
    result = {}
    count = 0
    for root in roots:
        for file in sorted((root / "applications").glob("*.desktop")):
            count += 1
            if count > 2048:
                return result
            try:
                if file.stat().st_size > 65536:
                    continue
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read(file, encoding="utf-8")
                entry = parser["Desktop Entry"]
                icon = entry.get("Icon", "application-x-executable").strip()[:256]
                # Local absolute icon paths or ordinary icon-theme identifiers only.
                if not re.fullmatch(r"[A-Za-z0-9_./+@ -]{1,256}", icon) or ".." in icon:
                    icon = "application-x-executable"
                label = APP.sub("", entry.get("Name", file.stem))[:64] or "Application"
                for key in [file.stem, entry.get("StartupWMClass", "")]:
                    if key:
                        result.setdefault(key.casefold(), {"app": label, "icon": icon,"categories":sorted(set(entry.get("Categories","").split(";"))&DESKTOP_CATEGORIES)})
            except (OSError, UnicodeError, configparser.Error, KeyError):
                continue
    return result


def normalize(monitors, workspaces, clients, active, seeds, apps):
    if not all(isinstance(value, list) for value in [monitors, workspaces, clients]):
        raise ValueError("Expected compositor lists")
    boroughs = []
    for monitor in monitors[:32]:
        try:
            boroughs.append({"id": integer(monitor["id"], 0), "name": APP.sub("", str(monitor.get("name", "Display")))[:40],
                             "focused": monitor.get("focused") is True,
                             "workspace": integer(monitor.get("activeWorkspace", {}).get("id", 0)),
                             "x": integer(monitor.get("x", 0)), "y": integer(monitor.get("y", 0)),
                             "width": integer(monitor.get("width", 1920), 1, 32768),
                             "height": integer(monitor.get("height", 1080), 1, 32768),
                             "scale": max(.25, min(8, float(monitor.get("scale", 1))))})
        except (ValueError, TypeError, KeyError):
            continue
    district_map = {}
    for workspace in workspaces[:LIMIT]:
        try:
            wid = integer(workspace["id"], 1)
            key = str(wid)
            seeds.setdefault(key, seed_for("district-" + key))
            district_map[wid] = {"id": wid, "seed": seeds[key], "monitor": integer(workspace.get("monitorID", -1)), "count": 0}
        except (ValueError, TypeError, KeyError):
            continue  # Scratchpads/special workspaces never become switchable city districts.
    windows = []
    focus = str(active.get("address", "")) if isinstance(active, dict) else ""
    for client in clients[:LIMIT]:
        try:
            address = str(client["address"])
            wid = integer(client["workspace"]["id"], 1)
            if not ADDRESS.fullmatch(address) or client.get("mapped") is False or client.get("hidden") is True:
                continue
            if wid not in district_map:
                key = str(wid)
                seeds.setdefault(key, seed_for("district-" + key))
                district_map[wid] = {"id": wid, "seed": seeds[key], "monitor": integer(client.get("monitor", -1)), "count": 0}
            app_class = APP.sub("", str(client.get("class", "")))[:96] or "Application"
            public = apps.get(app_class.casefold(), apps.get(app_class.casefold().removesuffix(".exe"), {}))
            windows.append({"address": address, "workspace": wid, "monitor": integer(client.get("monitor", -1)),
                            "app": public.get("app", app_class[:64]), "class": app_class,
                            "icon": public.get("icon", "application-x-executable"),"desktopCategories":public.get("categories",[]), "focused": address == focus,
                            "urgent": client.get("urgent") is True, "floating": client.get("floating") is True,
                            "width": integer(client.get("size", [400, 300])[0], 0, 32768),
                            "height": integer(client.get("size", [400, 300])[1], 0, 32768)})
            district_map[wid]["count"] += 1
        except (ValueError, TypeError, KeyError, IndexError):
            continue
    return {"schema": 1, "version": VERSION, "timestamp": time.time(),"activityTime":time.monotonic()*1000, "boroughs": boroughs,
            "districts": sorted(district_map.values(), key=lambda d: (d["monitor"], d["id"])), "windows": windows,
            "focused": focus if ADDRESS.fullmatch(focus) else "", "truncated": len(clients) > LIMIT}


def snapshot(apps=None):
    path = state_path()
    # Compositor queries stay outside the short state transaction.
    monitors, workspaces, clients, active = query("monitors"), query("workspaces"), query("clients"), query("activewindow")
    if apps is None:
        apps = desktop_apps()
    with architecture_lock(path):
        state=read_state(path);seeds=state["seeds"]
        previous = dict(seeds)
        data = normalize(monitors, workspaces, clients, active, seeds, apps)
        for district in data["districts"]:
            key=str(district["id"]);configured=next((w.get('name','')for w in workspaces if w.get('id')==district['id']),"")
            try:configured=label(configured)
            except ValueError:configured=""
            app_mix=sorted(set(w['app']for w in data['windows']if w['workspace']==district['id']),key=str.casefold)
            automatic=configured if configured and configured!=key else (" + ".join(app_mix[:3])[:48]if app_mix else 'Workspace '+key)
            source='workspace'if configured and configured!=key else 'apps'if app_mix else 'number'
            custom=state['names'].get(key,'')
            district.update({'name':custom or automatic,'nameSource':'custom'if custom else source,'customName':custom,'autoName':automatic,'autoSource':source,'pinned':key in state['pins'],'tint':state['tints'].get(key,seeds[key]%5),'circuitOverride':key in state['tints']})
        if seeds != previous:
            write_state(path,state)
    data['grouping']=state['grouping']
    return data


def renumber(old,new):
    old=integer(old,1);new=integer(new,1);path=state_path();a=str(old);b=str(new)
    with architecture_lock(path):
        data=read_state(path)
        if a in data['seeds']:
            # The compositor ID is vacant, but it may own historical personal data.
            # Swap identities instead of discarding the historical destination.
            collision=b in data['seeds']
            for field in ['seeds','names','tints']:
                old_value=data[field].pop(a,None);new_value=data[field].pop(b,None)
                if old_value is not None:data[field][b]=old_value
                if collision and new_value is not None:data[field][a]=new_value
            data['pins']=[b if k==a else a if collision and k==b else k for k in data['pins']]
            data['pins']=list(dict.fromkeys(data['pins']))
            write_state(path,data)
    return {'ok':True}


def lua_supported():
    data = json.loads(command(["-j", "version"]))
    match = re.search(r'(\d+)\.(\d+)', data.get('tag', data.get('version', '')))
    return bool(match and (int(match[1]), int(match[2])) >= (0, 56))


def app_directories_signature():
    roots=[Path(os.environ.get('XDG_DATA_HOME',str(Path.home()/'.local/share')))]
    roots += [Path(p)for p in os.environ.get('XDG_DATA_DIRS','/usr/local/share:/usr/share').split(':')if p]
    signature=[];count=0
    for root in roots:
        directory=root/'applications'
        try:signature.append((str(directory),directory.stat().st_mtime_ns))
        except OSError:signature.append((str(directory),None));continue
        # In-place public desktop-entry edits do not change directory mtime.
        for file in sorted(directory.glob('*.desktop')):
            count+=1
            if count>2048:return tuple(signature)
            try:signature.append((str(file),file.stat().st_mtime_ns))
            except OSError:signature.append((str(file),None))
    return tuple(signature)


def watch():
    """One visible-city process caches only public app icons/labels in RAM."""
    selector = selectors.DefaultSelector()
    selector.register(sys.stdin, selectors.EVENT_READ)
    signature = None
    apps = {}
    stable_names = {}
    try:
        while True:
            current = app_directories_signature()
            if signature != current:
                apps = desktop_apps()
                signature = current
            try:
                result = snapshot(apps)
            except (OSError, ValueError, TypeError, subprocess.SubprocessError, RuntimeError):
                result = {"ok": False, "error": "Desktop bridge unavailable. Refresh to reconnect."}
            if result.get('schema')==1:
                now=time.monotonic();present=set()
                for district in result.get('districts',[]):
                    key=district['id'];present.add(key);entry=stable_names.get(key)
                    if district['nameSource']!='apps':stable_names.pop(key,None);continue
                    candidate=district['name']
                    if entry is None:entry={'shown':candidate,'candidate':candidate,'since':now};stable_names[key]=entry
                    elif entry['candidate']!=candidate:entry['candidate']=candidate;entry['since']=now
                    elif now-entry['since']>=6:entry['shown']=candidate
                    district['name']=entry['shown']
                stable_names={k:v for k,v in stable_names.items()if k in present}
            print(json.dumps(result, ensure_ascii=False), flush=True)
            events = selector.select(timeout=2.5)
            # Coalesce an entire burst of refresh requests into one snapshot.
            # Read the descriptor directly: TextIO buffering can hide queued lines from select.
            if events:
                if not os.read(sys.stdin.fileno(), 4096):
                    return
                while selector.select(timeout=0):
                    if not os.read(sys.stdin.fileno(), 4096):
                        return
    finally:
        selector.close()


def activate(address=None, workspace=None, expected_app=None, expected_workspace=None):
    """Revalidate the current target immediately before an explicit user action."""
    if address is not None:
        if not ADDRESS.fullmatch(address):
            raise ValueError("Invalid window address")
        matches = [c for c in query("clients") if c.get("address") == address and c.get("mapped") is not False and c.get("hidden") is not True]
        if len(matches) != 1:
            raise ValueError("That building has closed. Refresh the city.")
        client = matches[0]
        if expected_app is not None and (APP.sub("", str(client.get("class", "")))[:96] or "Application") != expected_app:
            raise ValueError("That building changed. Refresh the city.")
        if expected_workspace is not None and integer(client.get("workspace", {}).get("id", -1)) != expected_workspace:
            raise ValueError("That building moved. Refresh the city.")
        wid = integer(client.get("workspace", {}).get("id", -1), 1)
        # Address and integer are validated before interpolation into the Lua expression.
        args = [f'hl.dsp.focus({{ window = "address:{address}" }})'] if lua_supported() else ["focuswindow", "address:" + address]
    else:
        wid = integer(workspace, 1)
        if not any(w.get("id") == wid for w in query("workspaces")):
            raise ValueError("That district is no longer present. Refresh the city.")
        args = [f'hl.dsp.focus({{ workspace = "{wid}" }})'] if lua_supported() else ["workspace", str(wid)]
    response = command(["dispatch", *args]).strip()
    if response != "ok":
        raise RuntimeError("Compositor did not accept navigation.")
    return {"ok": True, "workspace": wid}


def relocate(address,destination,expected_app,expected_workspace):
    destination=integer(destination,1);expected_workspace=integer(expected_workspace,1)
    if not ADDRESS.fullmatch(address):raise ValueError('Invalid window address')
    clients=query('clients');matches=[c for c in clients if c.get('address')==address and c.get('mapped')is not False and c.get('hidden')is not True]
    if len(matches)!=1:raise ValueError('That building has closed. Refresh the city.')
    client=matches[0]
    if (APP.sub('',str(client.get('class','')))[:96]or'Application')!=expected_app:raise ValueError('That building changed. Refresh the city.')
    if integer(client.get('workspace',{}).get('id',-1),1)!=expected_workspace:raise ValueError('That building moved. Refresh the city.')
    if not any(w.get('id')==destination for w in query('workspaces')):raise ValueError('That destination no longer exists. Refresh the city.')
    if destination==expected_workspace:raise ValueError('Choose another district.')
    args=[f'hl.dsp.window.move({{ workspace = "{destination}", window = "address:{address}", follow = false }})']if lua_supported()else['movetoworkspacesilent',f'{destination},address:{address}']
    if command(['dispatch',*args]).strip()!='ok':raise RuntimeError('Compositor did not accept relocation.')
    return {'ok':True,'workspace':destination}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("snapshot")
    sub.add_parser("watch")
    focus = sub.add_parser("focus"); focus.add_argument("address"); focus.add_argument("--app"); focus.add_argument("--workspace", type=int)
    visit = sub.add_parser("visit"); visit.add_argument("workspace", type=int)
    rename = sub.add_parser("renumber"); rename.add_argument("old", type=int); rename.add_argument("new", type=int)
    meta=sub.add_parser("customize");meta.add_argument("workspace",type=int);meta.add_argument("--name");meta.add_argument("--pinned",choices=["true","false"]);meta.add_argument("--tint",type=int)
    move=sub.add_parser("relocate");move.add_argument("address");move.add_argument("destination",type=int);move.add_argument("--app",required=True);move.add_argument("--workspace",required=True,type=int)
    group=sub.add_parser('group');group.add_argument('--group',choices=list(GROUP_COLORS));group.add_argument('--color');group.add_argument('--app');group.add_argument('--rule',choices=[*GROUP_COLORS,'auto'])
    args = parser.parse_args()
    try:
        if args.action == 'watch':
            watch(); return 0
        if args.action == "snapshot": result = snapshot()
        elif args.action == "group":result=edit_group(args.group,args.color,args.app,args.rule)
        elif args.action == "focus": result = activate(args.address, expected_app=args.app, expected_workspace=args.workspace)
        elif args.action == "visit": result = activate(workspace=args.workspace)
        elif args.action=="customize":result=customize(args.workspace,args.name,None if args.pinned is None else args.pinned=="true",args.tint)
        elif args.action=="relocate":result=relocate(args.address,args.destination,args.app,args.workspace)
        else: result = renumber(args.old, args.new)
        print(json.dumps(result, ensure_ascii=False)); return 0
    except (OSError, ValueError, TypeError, subprocess.SubprocessError, RuntimeError) as error:
        # Error text is our own exception label, never raw compositor output or private data.
        message = str(error) if isinstance(error, (ValueError, RuntimeError)) else "Desktop bridge unavailable. Try refreshing."
        print(json.dumps({"ok": False, "error": message[:160]})); return 1


if __name__ == "__main__":
    sys.exit(main())
