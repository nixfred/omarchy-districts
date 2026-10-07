"""Native CPU lamp captures, geometry stability, reduced motion and compact fit."""
import json,time
from native_session import NativeSession,ROOT,clean_log
fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'eDP-2'}],
 'districts':[{'id':1,'seed':311,'monitor':0,'count':1}],
 'windows':[{'address':'0x1','workspace':1,'monitor':0,'pid':42,'app':'Development editor application with a deliberately long name here','class':'Code','height':600,'width':900,'ownerCpu':{'state':'measured','percent':0,'level':0}}]}
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot {
 QA_GUARD
 DistrictsV2{id:d;testMode:true;settings:({motion:false})}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);d.inspectBuilding("0x1");console.log("READY")}}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function report():string{return JSON.stringify({status:JSON.parse(d.status()),lamp:d.selectedBuilding.illumination,cpu:d.selectedBuilding.ownerCpu,geometry:d.scene.buildings.map(function(b){return [b.key,b.x,b.y,b.height,b.size]}),content:d.testInspector.testInfoContent.height,available:d.testInspector.testBody.height})}
  function size(w:string,h:string):void{d.testViewport=Qt.size(Number(w),Number(h))}
  function load(state:string,value:string):void{var s=JSON.parse(JSON.stringify(d.snapshot));s.windows[0].ownerCpu={state:state,percent:Number(value),level:Math.min(1,Number(value)/100)};d.ingest(s)}
  function capture(path:string):void{d.capture(path,1)}
  function close():void{d.close()}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(fixture))
out=ROOT/'verification';records={}
with NativeSession('activity',qml)as s:
 s.marker('READY');time.sleep(.5)
 def report():return json.loads(s.ipc('report'))
 base=report();geometry=base['geometry'];builds=base['status']['sceneBuilds']
 for mode,state,load in [('idle','measured',0),('busy','measured',100),('sampling','sampling',0),('unknown','unavailable',0)]:
  s.ipc('load',state,str(load));time.sleep(.2);r=report()
  assert r['geometry']==geometry and r['status']['sceneBuilds']==builds,r
  assert r['content']<=r['available'],r
  p=out/('activity-'+mode+'.png');s.ipc('capture',str(p));s.marker('CAPTURE '+str(p)+' true')
  records[mode]=r
 assert records['busy']['lamp']>records['idle']['lamp']>records['unknown']['lamp']
 frames=s.status()['frames'];time.sleep(.2);assert s.status()['frames']==frames
 for w,h in [(912,512),(1093,614),(1600,1000)]:
  s.ipc('size',str(w),str(h));s.ipc('load','measured','99');time.sleep(.2);r=report();assert r['content']<=r['available'],r
  records[str(w)+'x'+str(h)]=r
 s.ipc('close');closed=s.status();assert not closed['opened']and not closed['collector'];s.quit();clean_log(s.log())
(out/'activity.json').write_text(json.dumps(records,indent=2))
print('PASS native CPU facade illumination, sampling/unavailable labels, no geometry rebuild, reduced motion and compact inspector fit.')
