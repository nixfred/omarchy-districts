"""Measure native rendering from readiness, with explicit reduced/closed phases."""
import json,time
from native_session import NativeSession,ROOT,clean_log
fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'DP-1'}],
 'districts':[{'id':i,'seed':i*3100,'monitor':0,'count':5}for i in range(1,7)],
 'windows':[{'address':hex(i*10+j),'workspace':i,'monitor':0,'app':'Application','class':'org.fixture','icon':'application-x-executable','height':600+j*90,'focused':i==1 and j==0}for i in range(1,7)for j in range(5)]}
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot {
 QA_GUARD
 DistrictsV2{id:d;testMode:true}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);console.log("READY")}}
 IpcHandler{
  target:"harness"
  function status():string{return d.status()}
  function reduce():string{d.saveSetting("motion",false);return d.status()}
  function close():string{d.close();return d.status()}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(fixture))
with NativeSession('performance',qml)as session:
 session.marker('READY');time.sleep(2)
 records={};rss={};durations={}
 def sample(name,duration):
  a=session.readings();time.sleep(duration);b=session.readings()
  records[name]=round((b[1]-a[1])/(b[0]-a[0])*100,2)
  rss[name]=[a[2],b[2]];durations[name]=round(b[0]-a[0],3)
 sample('animatedCpuPercentOfOneCore',4)
 reduced=json.loads(session.ipc('reduce'));time.sleep(1)
 sample('reducedCpuPercentOfOneCore',3)
 assert session.status()['frames']==reduced['frames'],'Reduced motion clock advanced'
 closed=json.loads(session.ipc('close'));time.sleep(1)
 sample('closedCpuPercentOfOneCore',3)
 done=session.status()
 assert not done['opened']and not done['collector']and done['frames']==closed['frames'],'Closed lifecycle advanced'
 session.quit();clean_log(session.log())
 records.update({'fixtureWindows':30,'resolution':reduced['viewportLogical'],'fpsCap':15,'rssKiB':rss,'sampleSeconds':durations,
                 'standalone':True,'normalExit':session.process.returncode==0,'animationStops':'PASS: frames unchanged reduced and closed','phaseStart':'Native READY marker; explicit scoped IPC phase changes'})
 (ROOT/'verification/performance.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2))
