"""Native group legend, global color/app-rule persistence, no-scroll viewport and topology checks."""
import json,time
from native_session import NativeSession,ROOT,clean_log
OUT=ROOT/'verification'
classes=['Code','Spotify','Discord','Obsidian','kitty','Brave']
fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'DP-1'}],
'districts':[{'id':i+1,'seed':100+i,'monitor':0,'count':1,'name':classes[i%6],'nameSource':'apps','autoName':classes[i%6],'autoSource':'apps','customName':'','tint':0,'circuitOverride':i==0}for i in range(12)],
'windows':[{'address':hex(i+1),'workspace':i+1,'monitor':0,'app':classes[i%6],'class':classes[i%6],'icon':'application-x-executable','height':600,'width':900}for i in range(12)]}
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtTest
import "CityV2.js" as City
ShellRoot{
 QA_GUARD
 DistrictsV2{id:d;testMode:true;settings:({motion:false})}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);console.log("READY")}}
 TestCase{id:qa;parent:d.testBody;when:false;function press(item){mouseClick(item,item.width/2,item.height/2)}}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function size(w:string,h:string):void{d.testViewport=Qt.size(Number(w),Number(h));d.fit()}
  function capture(path:string):void{d.capture(path,1)}
  function act(name:string,arg:string):void{switch(name){
   case "groupHeader":d.fit();var g=d.scene.groups[0],p=City.project(g.x,g.y);qa.mouseClick(d.testMap,d.testMap.width/2+d.panX+p.x*d.zoom,d.testMap.height/2+d.panY+p.y*d.zoom-8);break
   case "escape":d.testBody.forceActiveFocus();qa.keyClick(Qt.Key_Escape);break
   case "legend":d.openLegend();break
   case "closeLegend":d.closeLegend();break
   case "row":qa.press(d.testLegend.testPages.testRow(0));break
   case "next":qa.press(d.testLegend.testPages.testNext);break
   case "backPage":qa.press(d.testLegend.testPages.testPrevious);break
   case "back":qa.press(d.testLegend.testBack);break
   case "rules":qa.press(d.testLegend.testRules);break
   case "color":d.testLegend.testColor.text=arg;break
   case "saveColor":qa.press(d.testLegend.testColorSave);break
   case "defaultColor":qa.press(d.testLegend.testReset);break
   case "editDev":d.testLegend.editColor('development');break
   case "editCode":d.testLegend.editRule(d.snapshot.windows[0]);break
   case "rule":qa.press(d.testLegend.testRule(Number(arg)));break
   case "longRule":d.testLegend.editRule({app:'W'.repeat(64),class:'W'.repeat(96)});break
   case "inspect":d.inspectBuilding('0x1');break
   case "removeCode":var gone=JSON.parse(JSON.stringify(d.snapshot));gone.windows=gone.windows.filter(function(w){return w.class!=='Code'});gone.districts.forEach(function(e){e.count=gone.windows.filter(function(w){return w.workspace===e.id}).length});d.ingest(gone);break
   case "savedCode":d.testLegend.editRule({class:'code',app:'Code'});break
   case "reset":d.ingest(FIXTURE);break
   case "focusChange":var v=JSON.parse(JSON.stringify(d.snapshot));v.windows.forEach(function(w){w.focused=w.address==='0x2'});d.ingest(v);break
   case "close":d.close();break
  }}
  function report():string{var l=d.testLegend.testPages;return JSON.stringify({view:d.testLegend.view,prefs:d.groupingPreferences,message:d.groupingMessage,busy:d.groupingBusy,groups:d.scene.groups,districts:d.scene.districts.map(function(e){return {id:e.id,x:e.x,y:e.y,group:e.group,color:e.groupColor,tint:e.tint,circuitOverride:e.circuitOverride}}),topology:d.snapshot.windows.map(function(w){return [w.address,w.workspace]}),rowsHeight:l.testRows.height,listHeight:l.height,page:l.page,count:l.entries.length,body:d.testLegend.testBody.height,colorHeight:d.testLegend.testColorContent.height,ruleHeight:d.testLegend.testRuleContent.height,legend:d.legendOpen})}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(fixture))
records=[]
with NativeSession('grouping',qml)as session:
 session.marker('READY');time.sleep(.6)
 def act(name,arg=''):
  session.ipc('act',name,str(arg));time.sleep(.14)
 def report():return json.loads(session.ipc('report'))
 def settled():
  stop=time.monotonic()+4
  while time.monotonic()<stop:
   r=report()
   if not r['busy']:return r
   time.sleep(.08)
  raise AssertionError('Group helper did not exit')
 def capture(label):
  p=OUT/('groups-'+label+'.png');p.unlink(missing_ok=True);session.ipc('capture',str(p));session.marker('CAPTURE '+str(p)+' true',timeout=8)
 def pagefit():
  r=report();assert r['rowsHeight']<=r['listHeight']-46+.1,r;return r
 r=report();topology=r['topology'];assert len(r['groups'])==6 and all(g['count']==2 for g in r['groups']),r
 pos=[(d['id'],d['x'],d['y'])for d in r['districts']];act('focusChange');assert pos==[(d['id'],d['x'],d['y'])for d in report()['districts']]
 capture('overview-native');act('groupHeader');assert report()['legend']and report()['view']=='color';act('escape');assert not report()['legend']
 for width,height in [(912,512),(1093,614),(1366,768),(1920,1080),(3840,2160)]:
  session.ipc('size',str(width),str(height));act('legend');r=pagefit();assert r['count']==6
  if width==912:capture('small-legend')
  act('row');r=report();assert r['view']=='color';assert r['colorHeight']<=r['body'],r
  if width==912:capture('small-color')
  act('back');act('rules');r=pagefit();assert r['count']==6
  act('row');r=report();assert r['view']=='rule' and r['ruleHeight']<=r['body'],r
  act('longRule');r=report();assert r['ruleHeight']<=r['body'],r
  if width==912:capture('small-rule')
  act('closeLegend');records.append({'logical':[width,height],'groupsColorsRulesFullLabelsFit':True})
 session.ipc('size','912','512');act('legend');act('next');assert report()['page']>0;act('backPage');assert report()['page']==0
 act('inspect');act('legend');act('editDev');act('color','#123456');act('saveColor');r=settled();assert r['prefs']['colors']=={'development':'#123456'},r
 assert all(d['color']=='#123456'for d in r['districts']if d['group']=='development');assert r['districts'][0]['circuitOverride'] and r['districts'][0]['tint']==0
 before=r['prefs'];act('color','#b99cff');act('saveColor');r=settled();assert r['prefs']==before and 'different color' in r['message'],r
 act('defaultColor');r=settled();assert not r['prefs']['colors'],r
 act('editCode');act('rule',2);r=settled();assert r['prefs']['rules']=={'code':'entertainment'},r
 assert all(d['group']=='entertainment'for d in r['districts']if d['id']in(1,7));assert r['topology']==topology
 act('removeCode');act('closeLegend');act('legend');act('rules');assert report()['count']==6,'saved Code rule remains listed after app closes';act('savedCode');act('rule',0);r=settled();assert not r['prefs']['rules'];act('reset');time.sleep(6.2);act('reset');r=report();assert all(d['group']=='development'for d in r['districts']if d['id']in(1,7));assert r['topology']==topology
 act('closeLegend');act('close');r=session.status();assert not r['opened']and not r['collector']and not r['groupingBusy'];session.quit();clean_log(session.log())
 saved=json.loads((session.work/'state/districts/architecture.json').read_text());assert not saved['grouping']['colors']and not saved['grouping']['rules']
(OUT/'grouping.json').write_text(json.dumps({'viewports':records,'sixLabeledDistinctColorCities':True,'focusStableLayout':True,'nativeLegendButtons':True,'groupColorInheritedEveryDistrict':True,'circuitOverridePreserved':True,'duplicateColorRejectedWithoutWrite':True,'globalAppRuleAffectsEveryMatchingDistrict':True,'automaticRestoresDetection':True,'workspaceWindowTopologyUnchanged':True,'isolatedRealAtomicHelperPersistence':True,'closedNormalExit':True},indent=2))
print('PASS: native grouping legend; five viewport sizes; color/global-rule edits; actual helper persistence; unchanged topology; close and cleanup.')
