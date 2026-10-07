"""Native xdg-toplevel lifecycle; only the isolated fixture window is manipulated."""
import json, subprocess, time
from native_session import NativeSession, ROOT, clean_log

fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'eDP-2'}],
 'districts':[{'id':1,'seed':311,'monitor':0,'count':1}],
 'windows':[{'address':'0x1','workspace':1,'monitor':0,'pid':42,'app':'Code','class':'Code','height':600,'width':900}]}
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtTest
ShellRoot {
 QA_GUARD
 DistrictsV2{id:d;testMode:true;preferMaximized:false;settings:({motion:false})}
 Timer{interval:200;running:true;onTriggered:{console.log("READY")}}
 TestCase{id:qa;parent:d.testBody;when:false;function press(item){mouseClick(item,item.width/2,item.height/2)}}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function debug():string{return JSON.stringify({frame:d.frameResult,message:d.message})}
  function open():void{d.open();d.ingest(FIXTURE)}
  function minimize():void{d.minimize()}
  function maximize():void{d.maximize()}
  function close():void{d.close()}
  function capture(path:string):void{d.capture(path,1)}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(fixture))
def read(command):return json.loads(subprocess.check_output(['hyprctl',command,'-j'],text=True))
records=[]
before=read('activewindow').get('address')
with NativeSession('application',qml,background=True)as s:
 s.marker('READY')
 def clients():return [c for c in read('clients')if c['pid']==s.process.pid]
 def settled(opened):
  for _ in range(60):
   state=s.status();cs=clients()
   if state['opened']==opened and len(cs)==int(opened)and state['mapped']==opened and not state['frameBusy']:
    assert read('activewindow').get('address')==before,'Fixture changed focus'
    return state,cs
   time.sleep(.05)
  raise AssertionError((state,cs,s.log()))
 def dispatch(expr):subprocess.run(['hyprctl','dispatch',expr],check=True,capture_output=True,text=True)
 s.ipc('open');state,cs=settled(True);c=cs[0]
 assert c['class']=='org.quickshell'and c['title']=='Districts · Fixture',c
 records.append({'phase':'open','status':state,'client':c,'focusRetained':read('activewindow').get('address')==before});print('Fixture focus retained:',records[-1]['focusRetained'],flush=True)
 s.ipc('open');time.sleep(.15);assert len(clients())==1
 address=c['address']
 for w,h in [(912,512),(1280,800),(1500,900)]:
  dispatch('hl.dsp.window.resize({x='+str(w)+',y='+str(h)+',relative=false,window="address:'+address+'"})')
  time.sleep(.4);state=s.status();c=clients()[0]
  assert abs(state['viewport'][0]-w)<=1 and abs(state['viewport'][1]-h)<=1,(state,c)
  records.append({'phase':'resize','logical':state['viewport'],'clientSize':c['size']})
 s.ipc('maximize');time.sleep(1);state=s.status();assert state['maximized'],(state,clients(),s.ipc('debug'),s.log())
 assert read('activewindow').get('address')==before,('Maximize changed focus',before,read('activewindow').get('address'),clients()[0]['address'])
 records.append({'phase':'maximized','status':state,'client':clients()[0]})
 s.ipc('maximize');time.sleep(.2)
 s.ipc('minimize');state,cs=settled(False);assert state['minimized']and not state['collector'],state
 records.append({'phase':'minimized','status':state})
 s.ipc('open');state,cs=settled(True);assert not state['minimized'];assert cs[0]['stableId']!=c['stableId']
 records.append({'phase':'reopen','status':state})
 dispatch('hl.dsp.window.close({window="address:'+cs[0]['address']+'"})')
 state,cs=settled(False);assert not state['collector']and not state['minimized'],state
 s.ipc('open');state,cs=settled(True);assert len(cs)==1
 s.ipc('close');state,cs=settled(False);assert not state['collector']and not state['cameraRunning']and not state['edgeRunning'],state
 records.append({'phase':'closed','status':state})
 s.quit();clean_log(s.log())
(ROOT/'verification/application.json').write_text(json.dumps({'nativeToplevel':True,'singleton':True,'nativeResize':True,'maximizeRestore':True,'hideMinimizeReopen':True,'compositorCloseReopen':True,'records':records},indent=2))
print('PASS native application singleton, three real resize sizes, maximize/restore, minimize/reopen and compositor close/reopen; all fixture processes reaped.')
