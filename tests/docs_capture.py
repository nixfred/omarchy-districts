"""Sanitized native screenshot assets for the public README; small synthetic public-app fixture; stress labels belong only in private QA."""
import json,time
from native_session import NativeSession,ROOT,clean_log
names=['Code','Spotify','Discord','Obsidian','kitty','Brave']
labels=['Coding','Music','Messages','Notes','Terminal','Browsing']
icons=['code','spotify','discord','obsidian','kitty','brave-browser']
fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'DP-1'}],
'districts':[{'id':i+1,'seed':100+i,'monitor':0,'count':1,'name':labels[i],'nameSource':'custom','customName':labels[i],'autoName':names[i],'autoSource':'apps'}for i in range(6)],
'windows':[{'address':hex(i+1),'workspace':i+1,'monitor':0,'app':names[i%6],'class':names[i%6],'icon':icons[i%6],'height':600,'width':900}for i in range(6)]}
# Generic public-style agent sessions and quota observations; never a real user's.
U=lambda n:'%08d-0000-4000-8000-000000000000'%n
def agent(n,provider,name,status,availability='live',parent=None,family=None,project=None,sub=False):
 return {'id':U(n),'provider':provider,'name':name,'project':project,'familyId':family or U(n),'parentId':parent,'isSubagent':sub,'status':{'type':status,'activeFlags':['waitingOnApproval']if status=='approval'else[]},
  'statusSource':'Synthetic documentation fixture','observedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'availability':availability,'capabilities':{'canSend':False}}
agents=[agent(1,'claude','Refactor parser','busy',project='parser'),agent(2,'claude','Explore: find config loader','unknown','stored',family=U(1),sub=True),
 agent(3,'claude','Test: cover edge cases','unknown','stored',family=U(1),sub=True),agent(4,'codex','Review pull request','approval',project='docs-site'),
 agent(5,'codex','Spawned reviewer','active',parent=U(4),family=U(4)),agent(6,'codex','Write release notes','idle',project='app'),
 agent(7,'claude','Migrate database','blocked',project='api'),agent(8,'grok','Benchmark summary','unknown','stored',project='bench')]
NOW=int(time.time()*1000)
def metric(provider,label,seconds):
 m={'label':label,'state':'measured','freshness':'fresh','unit':'fraction','allowanceUsed':.6,'allowanceRemaining':.4,'source':'Synthetic documentation fixture','observedAt':NOW,'resetAt':NOW+4*3600000,
    'pace':{'state':'banked'if seconds>0 else'behind'if seconds<0 else'on-pace','signedSeconds':seconds,'source':'Synthetic','formula':'documentation fixture','meaning':'pace-equivalent allowance credit','fixedWindow':True}}
 if seconds<0:m['pace']['recoveryAt']=NOW-seconds*1000
 return {'provider':provider,'metric':m,'windows':[m]}
metrics=[metric('claude','Session (5-hour)',-2580),metric('codex','Weekly',13500)]
OUT=ROOT/'docs/images';OUT.mkdir(parents=True,exist_ok=True)
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
ShellRoot{QA_GUARD
 DistrictsV2{id:d;testMode:true;preferMaximized:false;settings:({motion:false,storedAgents:true})}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);d.providerMetrics=METRICS;console.log("READY")}}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function size(w:string,h:string):void{d.testViewport=Qt.size(Number(w),Number(h));d.fit()}
  function mode(name:string):void{if(name==='legend')d.openLegend();else if(name==='rules'){d.openLegend();d.testLegend.editRule(d.snapshot.windows[0])}else if(name==='passport'){d.closeLegend();d.inspectBuilding('0x1')}else if(name==='orbit'){d.closeLegend();d.selected='';d.selectedDistrict=-1;d.yaw=215;d.tilt=52;d.fit()}else if(name==='tour'){d.closeLegend();d.openNavigation('tour')}else if(name==='city'){d.closeLegend();d.selected='';d.selectedDistrict=-1;d.fit()}else if(name==='agents'){d.testNavigation.close();d.panel='';d.acceptAgents(AGENTS);var b=d.scene.buildings.find(function(x){return x.kind==='agent'&&x.agent.name==='Refactor parser'});d.selected='';d.selectedDistrict=b.workspace;d.focusDistrict(b.workspace,true,true)}}
  function capture(name:string,path:string):void{var item=name==='passport'?d.testInspector:name==='pace'?d.testPaceDock:d.testLegend.testPanel;if(['city','orbit','tour','agents'].indexOf(name)>=0){d.capture(path,1);return}item.grabToImage(function(r){console.log("CAPTURE "+path+" "+r.saveToFile(path))})}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(fixture)).replace('METRICS',json.dumps(metrics)).replace('AGENTS',json.dumps(agents))
with NativeSession('docs-capture',qml)as s:
 s.marker('READY');time.sleep(.6);s.ipc('size','1920','1080');time.sleep(.2)
 for mode in ['city','orbit','legend','rules','passport','tour','agents','pace']:
  if mode in ['passport','tour']:s.ipc('size','1366','512');time.sleep(.2)
  if mode=='agents':s.ipc('size','1600','1000');time.sleep(.2)
  s.ipc('mode',mode);time.sleep(1.4 if mode=='agents' else .25);p=OUT/(mode+'-native.png');p.unlink(missing_ok=True);s.ipc('capture',mode,str(p));s.marker('CAPTURE '+str(p)+' true',timeout=8)
 s.quit();clean_log(s.log())
print('PASS eight native own-surface documentation captures; synthetic public-app, agent and quota fixtures only.')
