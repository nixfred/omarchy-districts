import QtQuick
import QtTest
import ".."
Item {
 width:912;height:512
 QtObject{id:theme;property color accent:"#57dfff";property color ink:"#ffffff";property color panelPaper:"#10182c"}
 NavigationV2{id:n;anchors.fill:parent;city:theme;districts:[{id:1},{id:2},{id:3}];motion:false}
 TestCase{
  name:"NavigationContracts";when:windowShown
  property int tourId:-1
  property bool instant:false
  property int liveCount:0
  property int replayCount:0
  property var request:null
  Connections{target:n;function onTourDistrictRequested(id,jump){qa.tourId=id;qa.instant=jump}function onLiveRequested(){qa.liveCount++}function onReplayRequested(snapshot,timestamp){qa.replayCount++;qa.verify(snapshot.replay);qa.verify(snapshot.windows[0].ownerCpu.state==="unavailable")}function onPersistenceRequested(value){qa.request=value}}
  id:qa
  function source(w){return {schema:1,boroughs:[{id:0}],districts:[{id:1,seed:1},{id:2,seed:2}],windows:[{address:"0xa",class:"Code",workspace:w,monitor:0,height:600}]}}
  function test_01_tour_takeover(){n.startTour();compare(tourId,1);verify(instant);verify(n.touring);n.districts=[{id:1},{id:3}];n.advanceTour();compare(tourId,3);n.userTakeover();verify(!n.touring);n.advanceTour();compare(tourId,3);n.startTour();n.advanceTour();n.advanceTour();verify(!n.touring)}
  function test_02_replay_and_expiry(){n.observe(source(1),null,1000);n.observe(source(2),null,4000);compare(n.frameCount,2);n.seek(0);verify(n.replaying);compare(replayCount,1);n.observe(source(1),null,7000);compare(n.replayIndex,0);n.playReplay();verify(n.playing);n.advanceReplay();compare(n.replayIndex,1);n.returnLive();verify(!n.replaying);verify(!n.playing);compare(liveCount,1);n.seek(0);n.observe(source(2),null,2000000);verify(!n.replaying);compare(liveCount,2);n.clearHistory();compare(n.frameCount,0)}
  function test_03_views(){n.open("views");compare(request.operation,"list");n.testName.text="  East View  ";n.currentCamera={x:20,y:30,zoom:2,yaw:450,tilt:40};n.saveView();compare(request.name,"East View");compare(request.camera.yaw,90);n.acceptPersistence({ok:true,viewpoints:[{name:"East View",camera:request.camera}]});compare(n.savedViews.length,1);n.selectedView="East View";n.deleteView();compare(request.operation,"delete");n.selectView(n.savedViews[0]);verify(!n.panelOpen)}
  function test_04_layout(){n.savedViews=Array.from({length:12},function(_,i){return {name:"W".repeat(40)+i,camera:{yaw:360,tilt:75}}});n.observe(source(1),null,1000);n.observe(source(2),[{id:"agent-id",status:{type:"active",activeFlags:["waitingOnApproval"]},statusSource:"W".repeat(80)}],4000);n.persistenceMessage="W".repeat(160);for(var i=0;i<3;i++){n.open(["views","tour","replay"][i]);wait(50);verify(n.testPanel.height<=n.height-32);var pages=i===0?n.testPages:i===2?n.testEvents:null;if(pages){verify(pages.height>=pages.rowHeight+46-1,"One complete row + paging fits: "+i+" / "+pages.height+" / "+pages.rowHeight);verify(pages.testRows.height<=pages.height-46+1,"Rows fit");}grabImage(n).save("/tmp/districts-navigation-"+["views","tour","replay"][i]+".png")}n.suspend();verify(!n.panelOpen);verify(!n.touring);verify(!n.replaying)}
 }
}
