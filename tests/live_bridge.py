"""Verify the real native stream, refresh coalescing, close and process cleanup."""
import json,time
from pathlib import Path
from native_session import NativeSession,ROOT,clean_log

qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot {
 QA_GUARD
 DistrictsV2{id:d;testMode:true;testLiveBridge:true;onUpdateCountChanged:console.log("UPDATE "+updateCount)}
 Timer{interval:200;running:true;onTriggered:{d.open();console.log("READY")}}
 IpcHandler{
  target:"harness"
  function status():string{return d.status()}
  function burstRefresh():void{for(var i=0;i<8;i++)d.refresh()}
  function close():string{d.close();return d.status()}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''
with NativeSession('live-bridge',qml,live=True)as session:
 session.marker('READY');session.marker('UPDATE 2',timeout=12)
 live=session.status()
 assert live['updates']>=2 and live['collector']and not live['failed'],live
 before=live['updates'];session.ipc('burstRefresh')
 session.marker('UPDATE '+str(before+1),timeout=8)
 refreshed=session.status();assert refreshed['updates']>before and not refreshed['failed'],refreshed
 requested=json.loads(session.ipc('close'))
 assert not requested['opened'],requested
 deadline=time.monotonic()+3
 children=Path(f'/proc/{session.process.pid}/task/{session.process.pid}/children')
 while time.monotonic()<deadline and children.read_text().strip():time.sleep(.05)
 assert not children.read_text().strip(),'Collector child remained after close'
 closed=session.status()
 assert not closed['collector']and not closed['opened'],closed
 session.quit();clean_log(session.log())
 records={'LIVE':live,'REFRESHED':refreshed,'CLOSED':closed,'normalExit':session.process.returncode==0,'collectorReapedAfterClose':True,'burstRefreshCount':8}
 (ROOT/'verification/live-bridge.json').write_text(json.dumps(records,indent=2));print(json.dumps(records,indent=2))
 print('PASS: native streamed recovery updates, refresh burst, stop/reap on close, normal IPC exit; only status counts saved.')
