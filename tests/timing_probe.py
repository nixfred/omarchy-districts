"""Compare native QtQuick timer progression after closing the only test surface."""
import json,time
from native_session import NativeSession,ROOT,clean_log
QML='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot {
 property int beats:0
 QA_GUARD
 PanelWindow {id:surface;visible:true;implicitWidth:1;implicitHeight:1;color:"transparent";exclusionMode:ExclusionMode.Ignore;WlrLayershell.keyboardFocus:WlrKeyboardFocus.None;mask:Region{item:null}}
 IdleInhibitor{window:surface;enabled:surface.visible}
 Timer{interval:250;repeat:true;running:true;onTriggered:{beats++;console.log("BEAT "+beats)}}
 Timer{interval:1500;running:true;onTriggered:{surface.visible=false;console.log("CLOSED "+beats)}}
 IpcHandler{target:"harness";function status():string{return JSON.stringify({beats:beats,visible:surface.visible})}function quit():void{Qt.callLater(Qt.quit)}}
 Component.onCompleted:console.log("READY")
}'''
records={}
for guard in (False,True):
 name='timing-probe-'+str(guard).lower()
 with NativeSession(name,QML,guard=guard)as session:
  session.marker('READY');session.marker('CLOSED',timeout=4)
  closed=int(next(line.split('CLOSED ',1)[1]for line in session.log().splitlines()if'CLOSED 'in line))
  time.sleep(2)
  before=session.log().count('BEAT ')
  status=session.status();session.quit();clean_log(session.log())
  records[name]={'closedBeat':closed,'beatsInLogBeforeIpc':before,'status':status,'normalExit':session.process.returncode==0}
(ROOT/'verification/timing-probe.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2))
