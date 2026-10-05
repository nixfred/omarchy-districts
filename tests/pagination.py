"""Native screen-fit, complete pagination and live identity flows; async IPC steps allow polish."""
import json,time
from native_session import NativeSession,ROOT,clean_log
from fixtures import pagination_fixture
OUT=ROOT/'verification'
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtTest
ShellRoot{
 QA_GUARD
 DistrictsV2{id:d;testMode:true;settings:({motion:false})}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE);console.log("READY")}}
 TestCase{id:qa;parent:d.testBody;when:false;function press(item){mouseClick(item,item.width/2,item.height/2)}}
 function list(){return d.atlasOpen?d.testAtlas.testResults:d.moveDraft?d.testMove.testPages:d.testInspector.testPages}
 IpcHandler{target:"harness"
  function status():string{return d.status()}
  function size(w:string,h:string):void{d.testViewport=Qt.size(Number(w),Number(h))}
  function capture(path:string):void{d.capture(path,1)}
  function act(name:string,arg:string):void{
   switch(name){
    case "inspect":d.inspectBuilding(arg||"0x1");break
    case "district":d.focusDistrict(Number(arg));break
    case "style":d.testInspector.showStyle();break
    case "apps":d.testInspector.showList();break
    case "tools":d.testInspector.view="tools";break
    case "rename":d.beginRename();break
    case "text":d.testInspector.testName.text=arg;break
    case "error":d.message=arg;break
    case "cancelRename":qa.press(d.testInspector.testCancel);break
    case "atlas":d.openAtlas();break
    case "closeAtlas":d.closeAtlas();break
    case "move":d.beginMove();break
    case "destination":d.chooseDestination(Number(arg));break
    case "cancelMove":qa.press(d.testMove.testCancel);break
    case "next":qa.press(list().testNext);break
    case "back":qa.press(list().testPrevious);break
    case "row":qa.press(list().testRow(0));break
    case "key":d.testAtlas.testSearch.forceActiveFocus();qa.keyClick(Number(arg));break
    case "selectFirstApp":d.testAtlas.selectIndex(d.atlasResults.findIndex(function(e){return e.type==="building"&&e.key==="0x1"}));break
    case "insert":var v=JSON.parse(JSON.stringify(d.snapshot));v.windows.unshift({address:"0xffff",workspace:1,monitor:0,app:"New app",class:"org.fixture",icon:"application-x-executable",height:600,width:900});v.districts[0].count++;d.ingest(v);break
    case "removeApp":v=JSON.parse(JSON.stringify(d.snapshot));v.windows=v.windows.filter(function(w){return w.address!=="0x1"});d.ingest(v);break
    case "removeDestination":v=JSON.parse(JSON.stringify(d.snapshot));v.districts=v.districts.filter(function(e){return e.id!==d.moveDraft.destination});d.ingest(v);break
    case "inspectResult":d.testAtlas.inspect();break
    case "reset":d.ingest(FIXTURE);break
    case "close":d.close();break
   }
  }
  function report():string{var l=list(),rows=[];for(var i=0;i<l.shownEntries.length;i++){var r=l.testRow(i);if(r){var texts=r.children[0];rows.push({key:r.modelData.key,height:r.height,textHeight:texts.height})}}return JSON.stringify({view:d.testInspector.view,selected:d.selected,renaming:d.nameEditing,text:d.testInspector.testName.text,draft:d.renameDraft,nameContent:d.testInspector.testName.contentHeight,nameSpace:d.testInspector.testName.height-d.testInspector.testName.topPadding-d.testInspector.testName.bottomPadding,bodyHeight:d.testInspector.testBody.height,infoHeight:d.testInspector.testInfoContent.height,styleHeight:d.testInspector.testStyleContent.height,toolsHeight:d.testInspector.testToolsContent.height,page:l.page,capacity:l.capacity,pageCount:l.pageCount,rowHeight:l.rowHeight,rowsHeight:l.testRows.height,listHeight:l.height,keys:l.shownEntries.map(function(e){return e.key}),count:l.entries.length,rows:rows,resultKey:d.testAtlas.resultKey,resultIndex:d.testAtlas.resultIndex,atlasCount:d.atlasResults.length,move:d.moveDraft,confirm:d.testMove.testConfirm.enabled,moveFooterY:d.testMove.testFooter.y,moveListBottom:d.testMove.testPages.y+d.testMove.testPages.height,fixtureMoves:d.fixtureMoves})}
  function quit():void{Qt.callLater(Qt.quit)}
 }
}'''.replace('FIXTURE',json.dumps(pagination_fixture()))
records=[]
with NativeSession('pagination',qml)as session:
 session.marker('READY');time.sleep(.5)
 def act(name,arg=''):
  session.ipc('act',name,str(arg));time.sleep(.13)
 def report():return json.loads(session.ipc('report'))
 def pages(label):
  r=report();assert r['rowsHeight']<=r['listHeight']-46+.1,(label,r)
  assert all(row['textHeight']<=row['height']-12+.1 for row in r['rows']),(label,r)
  return r
 def capture(label):
  p=OUT/('fit-'+label+'.png');p.unlink(missing_ok=True);session.ipc('capture',str(p));session.marker('CAPTURE '+str(p)+' true',timeout=8)
 for w,h in [(1366,768),(1093,614),(912,512),(1280,720),(1920,1080),(2560,1440),(3840,2160),(3440,1440)]:
  session.ipc('size',str(w),str(h));act('inspect');r=report();assert r['infoHeight']<=r['bodyHeight'],r
  if (w,h)==(912,512):capture('small-app-info')
  act('style');r=report();assert r['styleHeight']<=r['bodyHeight'],r
  act('rename');act('text','W'*64);r=report();assert r['text']=='W'*48 and r['draft']=='W'*48,r
  assert r['styleHeight']<=r['bodyHeight'] and r['nameContent']<=r['nameSpace'],r
  if (w,h)==(912,512):capture('small-rename')
  act('cancelRename');assert not report()['renaming'];act('district',2);act('rename');r=report();assert r['text']=='W'*48,r
  act('cancelRename');assert not report()['renaming'];act('district',3);act('rename');r=report();assert r['text']=='District 3' and r['draft']=='District 3',r
  act('error','Use a name of up to 48 visible characters.');r=report();assert r['styleHeight']<=r['bodyHeight'],r;act('cancelRename');act('error','')
  act('inspect');act('tools');r=report();assert r['toolsHeight']<=r['bodyHeight'],r
  act('apps');r=pages('apps');assert r['count']==100,r
  if (w,h)==(912,512):capture('small-app-page')
  act('district',2);r=report();assert r['infoHeight']<=r['bodyHeight'],r
  act('atlas');r=pages('atlas');assert r['atlasCount']==179,r
  if (w,h)==(912,512):capture('small-atlas')
  act('closeAtlas');act('inspect');act('move');act('destination',2);r=pages('move');assert r['moveFooterY']>=r['moveListBottom'],r
  if (w,h)==(912,512):capture('small-move')
  act('cancelMove');records.append({'logical':[w,h],'full48Name64App':True,'viewsAndPagesFit':True})
 session.ipc('size','912','512');act('inspect');act('apps');act('next');assert report()['page']==1;act('back');assert report()['page']==0
 for _ in range(25):act('next')
 r=pages('repeated');first=r['keys'][0];act('insert');assert first in report()['keys'];act('row');r=report();assert r['selected'] and r['view']=='info',r
 act('atlas');act('next');r=pages('atlas page');assert r['page']*r['capacity']<=r['resultIndex']<(r['page']+1)*r['capacity'],r
 key=r['resultKey'];act('key',16777237);assert report()['resultKey']!=key # Qt.Key_Down
 act('key',16777239);pages('keyboard page') # Qt.Key_PageDown
 act('selectFirstApp');act('removeApp');assert report()['resultIndex']==-1;r=report();act('inspectResult');assert report()['selected']==r['selected'];act('closeAtlas')
 act('reset');act('inspect');act('move');act('next');assert report()['move']['destination']==-1;act('row');r=report();assert r['confirm'];target=r['move']['destination'];act('cancelMove');assert report()['fixtureMoves']==0 and report()['move'] is None
 act('move');act('destination',target);act('removeDestination');assert not report()['confirm'];act('cancelMove')
 act('reset');act('inspect');act('move');act('destination',2);act('removeApp');assert not report()['confirm'];act('cancelMove')
 act('reset');act('inspect');act('apps');act('next');act('removeApp');pages('live removal');act('close');assert not session.status()['opened'];session.quit();clean_log(session.log())
(OUT/'pagination.json').write_text(json.dumps({'viewports':records,'nativePageButtonsAndKeyboard':True,'all179AtlasResultsAccessible':True,'liveInsertPageAnchor':True,'removedResultCannotRetarget':True,'repeatRenameTruncationAndCrossDistrictReset':True,'cancelAndDisappearedSourceDestinationGuards':True,'closedNormalExit':True},indent=2))
print('PASS: 8 logical viewports; full labels; all data paged; native clicks/keys; live identity and cancel guards; repeated rename.')
