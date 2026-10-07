"""Own-surface logical viewport / output scale captures, no compositor changes."""
import json,time
from native_session import NativeSession,ROOT,clean_log
from fixtures import city_fixture
OUT=ROOT/'verification'
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot {
 QA_GUARD
 DistrictsV2{id:d;testMode:true;settings:({motion:false})}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);console.log("READY")}}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function size(w:string,h:string):void{d.testViewport=Qt.size(Number(w),Number(h));d.fit()}
  function capture(path:string,scale:string):void{d.capture(path,Number(scale))}
  function rename():void{d.focusDistrict(1);d.beginRename()}
  function atlas():void{d.cancelRename();d.openAtlas()}
  function close():void{d.close()}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(city_fixture()))
cases=[('laptop',1366,768,1),('fractional',1600,900,1.25),('native',1920,1080,1),('1440p',2560,1440,1),('4k',3840,2160,1),('ultrawide',3440,1440,1),('wide4k',5120,1440,1)]
records={}
with NativeSession('resolutions',qml)as session:
 session.marker('READY');time.sleep(.8)
 for name,w,h,scale in cases:
  session.ipc('size',str(w),str(h));time.sleep(.25);status=session.status()
  assert status['viewportLogical']==[w,h],status
  assert status['canvasPhysicalPixels']<=6000001,status
  path=OUT/('viewport-'+name+'.png');path.unlink(missing_ok=True)
  session.ipc('capture',str(path),str(scale));session.marker('CAPTURE '+str(path)+' true',timeout=8)
  from PIL import Image
  with Image.open(path)as im:assert im.size==(int(w*scale),int(h*scale)),im.size
  records[name]={'logical':[w,h],'outputScale':scale,'outputPixels':[int(w*scale),int(h*scale)],'status':status}
 session.ipc('size','1366','768');session.ipc('rename');time.sleep(.2)
 for mode in ['rename','atlas']:
  if mode=='atlas':session.ipc('atlas');time.sleep(.2)
  path=OUT/('viewport-laptop-'+mode+'.png');path.unlink(missing_ok=True);session.ipc('capture',str(path),'1');session.marker('CAPTURE '+str(path)+' true',timeout=5)
 session.ipc('close');time.sleep(.1);assert not session.status()['opened'];session.quit();clean_log(session.log())
records['limits']='Synthetic logical viewport and own-surface output scaling; this fixture does not configure or verify a physical 4K or fractional-scale monitor.'
(OUT/'resolutions.json').write_text(json.dumps(records,indent=2));print('PASS: seven native own-surface viewport captures, raster bound, laptop dialogs and cleanup.')
