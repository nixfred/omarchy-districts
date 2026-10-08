import QtQuick
import QtTest
import "../.." as Districts
Item {
 width:912;height:512
 QtObject{
  id:city
  property color panelPaper:"#171717"
  property color ink:"#eeeeee"
  property color accent:"#80cfff"
  property var neons:["#80cfff"]
  property var district:({id:1,name:"Workspace",groupName:"System & Tools",count:1,pinned:false,nameSource:"number"})
  property var selectedBuilding:null
  property var scene:({districts:[]})
  property var currentBuildings:[]
  property var tracedBuildings:[]
  property string lens:""
  property string selected:""
  property int selectedDistrict:1
  property bool nameEditing:false
  property bool actionBusy:false
  property bool metadataBusy:false
  property bool replaying:false
  property string renameDraft:""
  property string message:""
  property int navigations:0
  property int resourceOpens:0
  property int agentOpens:0
  property var openedAgent:null
  function navigate(){navigations++}
  function openResources(){resourceOpens++}
  function openAgent(agent){agentOpens++;openedAgent=agent}
  function focusDistrict(id){}
  function inspectBuilding(key){}
  function beginRename(){}
  function customize(change){}
  function saveRename(){}
  function cancelRename(){}
  function traceApp(){}
  function beginMove(){}
  property var toggledFamily:""
  function toggleFamily(family){toggledFamily=family}
 }
 Districts.InspectorV2{id:pane;city:city;width:292;height:342}
 TestCase {
  name:"InspectorAgentAndResources";when:windowShown
  function real(){city.district={id:1,name:"Workspace",groupName:"System & Tools",count:1,pinned:false,nameSource:"number"};city.selectedBuilding={key:"0x1",app:"W".repeat(64),workspace:1,icon:"",width:900,windowHeight:600,ownerPid:42,ownerCpu:{state:"measured",percent:10}};city.currentBuildings=[city.selectedBuilding];pane.showInfo();wait(30)}
  function agent(){city.district={id:-1,name:"Agent court",virtualWorkspace:true,count:1,pinned:false};city.selectedBuilding={key:"agent:codex:12345678",kind:"agent",app:"Codex 12345678",agent:{id:"12345678",parentId:"abcdef01-2345",status:{type:"running"},statusSource:"codex app-server thread/read",observedAt:"2026-10-06T12:00:00Z",availability:"live"}};city.currentBuildings=[city.selectedBuilding];pane.showInfo();wait(30)}
  function test_agent_actions_and_labels(){agent();verify(!pane.testStyle.visible);verify(!pane.testTools.visible);verify(!pane.testDetails.visible);compare(pane.entries[0].subtitle,"Agent · live · running");verify(!pane.entries[0].subtitle.includes("D-"));verify(pane.testInfoContent.height<=pane.testBody.height);mouseClick(pane.testEnter,pane.testEnter.width/2,pane.testEnter.height/2);compare(city.agentOpens,1);compare(city.navigations,0);compare(city.openedAgent.id,"12345678");city.replaying=true;mouseClick(pane.testEnter,pane.testEnter.width/2,pane.testEnter.height/2);compare(city.agentOpens,1);city.replaying=false}
  function test_family_collapse_control(){city.selectedBuilding=null;city.currentBuildings=[];city.district={id:-900000,name:"Atlas:desk:herdr",kind:"agentFamily",virtualWorkspace:true,count:3,familyCount:3,collapsible:true,collapsed:false,hiddenCount:0,sessionFamily:"agent:claude:x",pinned:false};pane.showInfo();wait(20);verify(pane.testFamily.visible);compare(pane.testFamily.text,"Collapse family to root");pane.testFamily.clicked();compare(city.toggledFamily,"agent:claude:x");city.district=Object.assign({},city.district,{collapsed:true,hiddenCount:2,count:1});wait(10);compare(pane.testFamily.text,"Expand family  ·  2 hidden");verify(pane.testInfoContent.height<=pane.testBody.height,"Collapsed court info fits");city.district=Object.assign({},city.district,{collapsible:false});wait(10);verify(!pane.testFamily.visible)}
  function test_virtual_court_never_visits_workspace(){agent();city.selectedBuilding=null;city.currentBuildings=[];wait(30);verify(!pane.testEnter.visible);verify(!pane.testStyle.visible);verify(!pane.testTools.visible);pane.showStyle();wait(10);verify(!pane.testStyleContent.visible)}
  function test_real_window_fit_and_resource_details(){real();verify(pane.testInfoContent.height<=pane.testBody.height,"Real info fits minimum app inspector");verify(pane.testStyle.visible,"style visible for real");verify(pane.testTools.visible,"tools visible for real");verify(pane.testDetails.visible,"details visible for real");mouseClick(pane.testDetails,pane.testDetails.width/2,pane.testDetails.height/2);compare(city.resourceOpens,1);mouseClick(pane.testActivity,pane.testActivity.width/2,pane.testActivity.height/2);compare(city.resourceOpens,2);city.replaying=true;mouseClick(pane.testDetails,pane.testDetails.width/2,pane.testDetails.height/2);mouseClick(pane.testActivity,pane.testActivity.width/2,pane.testActivity.height/2);compare(city.resourceOpens,2);verify(!pane.testRelocate.enabled);city.replaying=false;mouseClick(pane.testEnter,pane.testEnter.width/2,pane.testEnter.height/2);compare(city.navigations,1);compare(pane.entries[0].subtitle,"D1 / Tiled window")}
 }
}
