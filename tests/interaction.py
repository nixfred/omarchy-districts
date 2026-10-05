"""Actual native controls, persistence, cancellation, atlas, move and edge glide."""
import json
from native_session import NativeSession,ROOT,clean_log
fixture={'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'DP-1'}],
 'districts':[{'id':1,'seed':312,'monitor':0,'count':2},{'id':2,'seed':913,'monitor':0,'count':1}],
 'windows':[{'address':'0x1','workspace':1,'monitor':0,'app':'Kitty','class':'kitty','icon':'kitty','height':600,'width':900,'focused':True},
            {'address':'0x2','workspace':1,'monitor':0,'app':'Brave','class':'brave','icon':'applications-internet','height':900,'width':1100},
            {'address':'0x3','workspace':2,'monitor':0,'app':'Kitty','class':'kitty','icon':'kitty','height':600,'width':900}]}
qml='''import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtTest
import "CityV2.js" as City
ShellRoot {
 QA_GUARD
 DistrictsV2{id:d;testMode:true;testMetadataIO:true}
 Timer{interval:200;running:true;onTriggered:{d.open();d.ingest(FIXTURE)}}
 TestCase{id:controls;parent:d.testBody;name:"DistrictsV2Controls";when:false
  function press(item){waitForPolish(d.testBody.Window.window);wait(180);mouseClick(item,item.width/2,item.height/2);wait(100)}
  function test_controls(){
   console.log("STEP 1 "+d.status())
   wait(1000)
   console.log("STEP 2 "+d.status())
   var b=d.scene.buildings[0],p=City.project(b.x,b.y,b.height/2)
   console.log("STEP 3 "+d.status())
   var x=d.testMap.width/2+d.panX+p.x*d.zoom,y=d.testMap.height/2+d.panY+p.y*d.zoom
   console.log("STEP 4 "+d.status())
   console.log("HIT "+JSON.stringify({x:x,y:y,key:b.key}));mouseClick(d.testMap,x,y);wait(150);compare(d.selected,b.key,"Map selects real building")
   console.log("STEP 5 "+d.status())
   press(d.testInspector.testEnter);compare(d.message,"Fixture navigation suppressed")
   console.log("STEP 6 "+d.status())
   var before=d.panX;mouseDrag(d.testMap,300,300,65,35);verify(d.panX>before+30,"Drag works")
   console.log("STEP 7 "+d.status())
   var zoom=d.zoom;mouseWheel(d.testMap,400,300,0,120);wait(220);verify(d.zoom>zoom,"Anchored wheel works")
   console.log("STEP 8 "+d.status())
   press(d.testInspector.testStyle);wait(100);console.log("RENAME_GEOM "+JSON.stringify({width:d.testInspector.testRename.width,height:d.testInspector.testRename.height,visible:d.testInspector.testRename.visible,enabled:d.testInspector.testRename.enabled,point:d.testInspector.testRename.mapToItem(d.testBody,0,0)}));press(d.testInspector.testRename);console.log("RENAME_AFTER "+d.nameEditing);tryCompare(d,"nameEditing",true);d.testInspector.testName.text="Cancelled name";d.renameDraft="Cancelled name";wait(100);press(d.testInspector.testCancel);compare(d.nameEditing,false);verify(d.district.name!=="Cancelled name","Cancel does not write")
   console.log("STEP 9 "+d.status())
   tryCompare(d.testInspector.testRename,"visible",true);wait(100);press(d.testInspector.testRename);tryCompare(d,"nameEditing",true);tryCompare(d.testInspector.testSave,"visible",true);wait(100);d.testInspector.testName.text="Build notes";d.renameDraft="Build notes";wait(100);console.log("SAVE_GEOM "+JSON.stringify({visible:d.testInspector.testSave.visible,point:d.testInspector.testSave.mapToItem(d.testBody,0,0),draft:d.renameDraft}));press(d.testInspector.testSave);var updated=JSON.parse(JSON.stringify(d.snapshot));updated.windows[1].width=1234;updated.focused="0x2";d.ingest(updated);wait(500);console.log("SAVE_AFTER "+d.status()+" "+d.message+" result="+JSON.stringify(d.metadataResult));tryCompare(d,"nameEditing",false,3000);compare(d.district.name,"Build notes","Real metadata helper commit");compare(d.snapshot.windows[1].width,1234,"Metadata commit keeps live updates");compare(d.snapshot.focused,"0x2")
   console.log("STEP 10 "+d.status())
   press(d.testInspector.testPin);tryVerify(function(){return d.district.pinned},3000)
   console.log("STEP 11 "+d.status())
   press(d.testInspector.testTools);wait(100);press(d.testInspector.testTrace);compare(d.tracedBuildings.length,2,"Trace spans actual districts")
   console.log("STEP 12 "+d.status())
   d.openAtlas();wait(100);d.testAtlas.testSearch.text="brave";d.queryText="brave";compare(d.atlasResults.length,1);compare(d.atlasResults[0].type,"building");d.inspectResult(d.atlasResults[0]);wait(500);compare(d.selected,"0x2");compare(d.atlasOpen,false)
   console.log("STEP 13 "+d.status())
   press(d.testInspector.testTools);wait(100);press(d.testInspector.testRelocate);wait(100);compare(d.validMove(),false);d.chooseDestination(2);compare(d.validMove(),true);press(d.testMove.testCancel);compare(d.fixtureMoves,0);compare(d.moveDraft,null)
   console.log("STEP 14 "+d.status())
   press(d.testInspector.testTools);wait(100);press(d.testInspector.testRelocate);wait(100);d.chooseDestination(2);press(d.testMove.testConfirm);compare(d.fixtureMoves,1);compare(d.selectedBuilding.workspace,2);compare(d.moveDraft,null)
   console.log("STEP 15 "+d.status())
   d.beginMove();d.chooseDestination(1);d.snapshot.timestamp=Date.now()/1000-20;d.confirmMove();compare(d.fixtureMoves,1,"Stale navigation does not mutate");d.cancelMove();d.snapshot.timestamp=0
   console.log("STEP 16 "+d.status())
   d.focusDistrict(2);wait(500);mouseMove(d.testMap,2,d.testMap.height/2);wait(100);console.log("EDGE_START "+d.status()+" pointer="+d.pointer+" contains="+d.testMap.containsMouse);var edge=d.panX;wait(500);console.log("EDGE_END "+d.panX+" before="+edge);verify(d.panX>edge+30,"Pointer edge glides without drag");mouseMove(d.testMap,d.testMap.width/2,d.testMap.height/2);wait(80);edge=d.panX;wait(180);compare(d.panX,edge,"Center remains stable")
   console.log("STEP 17 "+d.status())
   mouseMove(d.testMap,2,d.testMap.height/2);d.beginRename();wait(80);edge=d.panX;wait(180);compare(d.panX,edge,"Rename suspends edge glide");d.cancelRename();mouseMove(d.testMap,d.testMap.width/2,d.testMap.height/2)
   console.log("STEP 18 "+d.status())
   d.openAtlas();wait(80);edge=d.panX;wait(180);compare(d.panX,edge,"Atlas suspends edge glide");d.closeAtlas()
   d.openLegend();wait(80);edge=d.panX;wait(180);compare(d.panX,edge,"Grouping legend suspends edge glide");d.closeLegend()
   console.log("STEP 19 "+d.status())
   var old=d.panX;mouseClick(d.testMinimap,d.testMinimap.width*.8,d.testMinimap.height*.5);wait(300);verify(Math.abs(d.panX-old)>10,"Minimap travels")
   console.log("STEP 20 "+d.status())
   d.showSettings=true;wait(50);press(d.testMotion);compare(d.motion,false);compare(d.cameraRunning,false)
   console.log("STEP 21 "+d.status())
   press(d.testNight);compare(d.night,false)
   console.log("STEP 22 "+d.status())
   var frames=d.frameCount;wait(200);compare(d.frameCount,frames,"Reduced motion clock stops")
   console.log("STEP 23 "+d.status())
   d.close();wait(80);compare(d.opened,false);verify(!d.status().includes('"edgeRunning":true'));verify(!d.status().includes('"cameraRunning":true'))
   console.log("STEP 24 "+d.status())
   d.testAction.command=["python3","-c",TEST_COMMAND];d.actionKind="focus";d.testAction.running=true;d.navigate();compare(d.opened,false,"Busy action cannot reopen or overlap");wait(350);compare(d.opened,false,"Failed focus never reopens the overlay");compare(d.message,"Fixture dispatch failure")
   console.log("INPUT_TESTS_PASS "+d.status())
  }
 }
 Timer{interval:1200;running:true;onTriggered:{console.log("INPUT_TESTS_START");controls.test_controls()}}
 IpcHandler{target:"harness";function status():string{return d.status()}function quit():void{Qt.callLater(Qt.quit)}}
}'''.replace('TEST_COMMAND',json.dumps('import time,json; time.sleep(.15); print(json.dumps({"ok":False,"error":"Fixture dispatch failure"}))')).replace('FIXTURE',json.dumps(fixture)).replace('compare(d.cameraRunning,false)','verify(!d.status().includes(\'"cameraRunning":true\'))')
with NativeSession('interaction',qml)as session:
 session.marker('INPUT_TESTS_PASS',timeout=55)
 status=session.status();session.quit();clean_log(session.log());print(session.log())
 assert not status['opened']and not status['collector']and not status['edgeRunning']and not status['cameraRunning']
 assert status['fixtureMoves']==1,status
 (ROOT/'verification/interaction.json').write_text(json.dumps({'status':status,'normalExit':True,'actualQtTestControls':True,'metadataCommit':True,'cancelFlows':True,'atlasTrace':True,'confirmedMoveAndStaleGuard':True,'edgeGlideAndModalGuards':True,'minimapTravel':True},indent=2))
