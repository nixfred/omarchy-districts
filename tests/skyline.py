"""Capture actual native skyline WidgetButton in passive dedicated bar fixture."""
import json,time
from native_session import NativeSession,ROOT,clean_log
OUT=ROOT/'verification'
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons
ShellRoot{
 QA_GUARD
 PanelWindow{id:barWindow;visible:true;implicitWidth:32;implicitHeight:40;exclusionMode:ExclusionMode.Ignore;color:"transparent";WlrLayershell.namespace:"districts-skyline-qa";WlrLayershell.keyboardFocus:WlrKeyboardFocus.None;mask:Region{item:null}
  Rectangle{id:sample;width:32;height:barWindow.height;color:Color.background
   DistrictsV2{id:d;anchors.fill:parent;testMode:true}
  }
 }
 Timer{interval:300;running:true;onTriggered:console.log("READY")}
 IpcHandler{target:"harness"
  function height(h:string):void{barWindow.implicitHeight=Number(h)}
  function capture(path:string,scale:string):void{sample.grabToImage(function(result){console.log("CAPTURE "+path+" "+result.saveToFile(path))},Qt.size(32*Number(scale),sample.height*Number(scale)))}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''
with NativeSession('skyline',qml)as session:
 session.marker('READY')
 for height,scale in [(28,1),(32,1.25),(40,2)]:
  session.ipc('height',str(height));time.sleep(.15);path=OUT/('skyline-'+str(height)+'-'+str(scale)+'.png');path.unlink(missing_ok=True)
  session.ipc('capture',str(path),str(scale));session.marker('CAPTURE '+str(path)+' true',timeout=3)
 session.quit();clean_log(session.log())
print('PASS: native32px skyline slot at28/32/40px bar height,1/1.25/2 output scale, passive cleanup.')
