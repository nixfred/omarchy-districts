"""Sanitized native screenshot assets for the public README; small synthetic public-app fixture; stress labels belong only in private QA."""
import json,time
from native_session import NativeSession,ROOT,clean_log
names=['Code','Spotify','Discord','Obsidian','kitty','Brave']
labels=['Coding','Music','Messages','Notes','Terminal','Browsing']
icons=['code','spotify','discord','obsidian','kitty','brave-browser']
fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'DP-1'}],
'districts':[{'id':i+1,'seed':100+i,'monitor':0,'count':1,'name':labels[i],'nameSource':'custom','customName':labels[i],'autoName':names[i],'autoSource':'apps'}for i in range(6)],
'windows':[{'address':hex(i+1),'workspace':i+1,'monitor':0,'app':names[i%6],'class':names[i%6],'icon':icons[i%6],'height':600,'width':900}for i in range(6)]}
OUT=ROOT/'docs/images';OUT.mkdir(parents=True,exist_ok=True)
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot{QA_GUARD
 DistrictsV2{id:d;testMode:true;preferMaximized:false;settings:({motion:false,storedAgents:true})}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);console.log("READY")}}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function size(w:string,h:string):void{d.testViewport=Qt.size(Number(w),Number(h));d.fit()}
  function mode(name:string):void{if(name==='legend')d.openLegend();else if(name==='rules'){d.openLegend();d.testLegend.editRule(d.snapshot.windows[0])}else if(name==='passport'){d.closeLegend();d.inspectBuilding('0x1')}else if(name==='orbit'){d.closeLegend();d.selected='';d.selectedDistrict=-1;d.yaw=215;d.tilt=52;d.fit()}else if(name==='tour'){d.closeLegend();d.openNavigation('tour')}else if(name==='city'){d.closeLegend();d.selected='';d.selectedDistrict=-1;d.fit()}}
  function capture(name:string,path:string):void{var item=name==='passport'?d.testInspector:d.testLegend.testPanel;if(['city','orbit','tour'].indexOf(name)>=0){d.capture(path,1);return}item.grabToImage(function(r){console.log("CAPTURE "+path+" "+r.saveToFile(path))})}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(fixture))
with NativeSession('docs-capture',qml)as s:
 s.marker('READY');time.sleep(.6);s.ipc('size','1920','1080');time.sleep(.2)
 for mode in ['city','orbit','legend','rules','passport','tour']:
  if mode in ['passport','tour']:s.ipc('size','1366','512');time.sleep(.2)
  s.ipc('mode',mode);time.sleep(.25);p=OUT/(mode+'-native.png');p.unlink(missing_ok=True);s.ipc('capture',mode,str(p));s.marker('CAPTURE '+str(p)+' true',timeout=8)
 s.quit();clean_log(s.log())
print('PASS six native own-surface documentation captures; synthetic public-app fixture only.')
