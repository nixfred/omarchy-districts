"""Bounded maximum topology, native camera workload and closed lifecycle."""
import json,time
from native_session import NativeSession,ROOT,clean_log
fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'DP-1'}], 'districts':[{'id':i,'seed':i*1031,'monitor':0,'count':1}for i in range(1,513)],'windows':[{'address':hex(i),'workspace':i,'monitor':0,'app':'Kitty','class':'kitty','icon':'kitty','height':600,'width':900}for i in range(1,513)]}
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot{
 QA_GUARD
 DistrictsV2{id:d;testMode:true;settings:({motion:false});testViewport:Qt.size(3840,2160)}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);console.log("READY")}}
 Timer{id:camera;interval:33;repeat:true;running:false;property int tick:0;onTriggered:{tick++;d.panX+=tick%2?7:-7;d.paint()}}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function travel():void{d.focusDistrict(250);camera.start()}
  function stop():void{camera.stop()}
  function close():void{camera.stop();d.close()}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(fixture))
with NativeSession('stress',qml)as session:
 session.marker('READY',timeout=15);time.sleep(1);status=session.status();assert status['buildings']==512 and status['districts']==512 and status['canvasPhysicalPixels']<=6000001,status
 session.ipc('travel');time.sleep(.5);a=session.readings();time.sleep(3);b=session.readings();camera=round((b[1]-a[1])/(b[0]-a[0])*100,2)
 session.ipc('close');time.sleep(.3);a=session.readings();time.sleep(2);b=session.readings();closed=round((b[1]-a[1])/(b[0]-a[0])*100,2);assert not session.status()['opened'];session.quit();clean_log(session.log())
result={'maximumWindows':512,'maximumWorkspaces':512,'logicalViewport':[3840,2160],'canvasPhysicalPixels':status['canvasPhysicalPixels'],'camera30fpsCpuPercentOneCore':camera,'closedCpuPercentOneCore':closed,'rssKiB':b[2],'normalExit':True,'limits':'Synthetic maximum topology; external collector and real hardware DPI not part of this render workload.'}
(ROOT/'verification/stress.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
