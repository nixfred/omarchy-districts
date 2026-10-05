"""Capture native fixtures with readiness and completion gates, then verify exit."""
import json,time
from native_session import NativeSession,ROOT,clean_log
OUT=ROOT/'verification'
from fixtures import city_fixture
snapshot=city_fixture()
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
  function captureCity():string{d.capture(OUT+"/native-city.png");return d.status()}
  function selectDistrict():void{d.focusDistrict(2);d.selectNext(1)}
  function captureDistrict():string{d.capture(OUT+"/native-district.png");d.navigate();return d.status()}
  function day():void{d.saveSetting("motion",false);d.saveSetting("night",false)}
  function captureDay():string{d.capture(OUT+"/native-day.png");return d.status()}
  function reduceBuildings():string{var v=FIXTURE;v.windows=v.windows.slice(0,6);d.ingest(v);return d.status()}
  function close():string{d.close();return d.status()}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(snapshot)).replace('OUT',json.dumps(str(OUT)))
for name in ('native-city.png','native-district.png','native-day.png'):(OUT/name).unlink(missing_ok=True)
with NativeSession('native',qml)as session:
 session.marker('READY');time.sleep(1)
 records={}
 for label,method,name in [('CITY','captureCity','native-city.png'),('DISTRICT','captureDistrict','native-district.png'),('DAY','captureDay','native-day.png')]:
  if label=='DISTRICT':session.ipc('selectDistrict');time.sleep(.6)
  if label=='DAY':session.ipc('day');time.sleep(.2)
  records[label]=json.loads(session.ipc(method))
  session.marker('CAPTURE '+str(OUT/name)+' true',timeout=4)
  assert(OUT/name).stat().st_size>10000
 records['REDUCED']=json.loads(session.ipc('reduceBuildings'))
 records['CLOSED']=json.loads(session.ipc('close'));time.sleep(.2)
 assert session.status()['frames']==records['CLOSED']['frames']
 assert records['CITY']['buildings']==8 and records['CITY']['standalone']
 assert records['DISTRICT']['selected']and records['DISTRICT']['selectedDistrict']==2
 assert not records['DAY']['motion']and not records['DAY']['night']
 assert not records['CLOSED']['opened']and not records['CLOSED']['collector']
 session.quit();clean_log(session.log());records['normalExit']=session.process.returncode==0
 (OUT/'native.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2))
 print('PASS: final native captures, district entry guard, day/night, reduced/closed lifecycle and normal exit.')
