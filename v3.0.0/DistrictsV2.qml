import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland
import Quickshell.Wayland
import qs.Commons
import qs.Ui
import "CityV2.js" as City
import "CameraV2.js" as Camera
import "GroupsV2.js" as Groups
import "AgentCityV2.js" as Agents
import "LensV2.js" as FocusLens

Item {
  id: root
  property QtObject bar: null
  property var shell: null
  property var settings: ({})
  property string moduleName: "nixfred.districts"
  property bool opened: false
  property bool appMinimized: false
  property bool preferMaximized: !testMode
  property bool appMaximized:false
  property var frameResult:null
  property size rememberedSize: Qt.size(0,0)
  readonly property var window: applicationLoader.item
  property bool testMode: false
  property bool testLiveBridge: false
  property bool testMetadataIO: false
  property size testViewport: Qt.size(0,0)
  property int fixtureMoves: 0
  property bool legendOpen: false
  property real yaw:45
  property real tilt:35.26438968
  property bool orbitDragging:false
  readonly property var orbitCamera:({yaw:yaw,tilt:tilt,interactive:orbitDragging||cameraTimer.running})
  readonly property var currentCamera:({x:panX,y:panY,zoom:zoom,yaw:yaw,tilt:tilt})
  readonly property var projectedBounds:City.bounds(scene,orbitCamera,zoom)
  property var liveSnapshot:({schema:1,boroughs:[],districts:[],windows:[]})
  property var agentRecords:[]
  property var collapsedFamilies:({})
  // The persistent quota pace dock sits on the city's right edge; framing leaves room for it.
  readonly property bool paceDockVisible:opened&&settings.paceDock!==false&&!replaying
  readonly property real paceReserve:paceDockVisible?paceDock.width+24:0
  property string providerFilter:""
  property var providerMetrics:[]
  property var metricsContext:null
  property var metricsResult:null
  property string metricsMessage:""
  readonly property var deskAgents:(replaying?(viewSource.agents||[]):agentRecords).filter(function(a){return !providerFilter||providerFamily(a)===providerFilter})
  property var focusLens:null
  property string panel:""
  readonly property bool replaying:navigation.replaying
  readonly property var viewSource:replaying&&navigation.replayFrame?navigation.replayFrame.snapshot:awaitingLive?({schema:1,boroughs:[],districts:[],windows:[],agents:[]}):liveSnapshot
  readonly property bool anyModal:legendOpen||atlasOpen||nameEditing||!!moveDraft||panel!==""||navigation.panelOpen
  property var resourcesResult:null
  property var resourcesTarget:null
  property var resourcesContext:null
  property string resourcesError:""
  property var organizePlan:null
  property var organizeReceipt:null
  property var organizeResult:null
  property string organizeError:""
  property string organizeInput:""
  property string organizeOperation:"preview"
  property var agentTarget:null
  property var sessionReply:null
  property string sessionReplyIdentity:""
  property string sessionDraft:""
  property var sessionDrafts:({})
  property bool switchingAgent:false
  property bool flushingDraft:false
  readonly property int retainedSubmissions:pendingSubmissionCount()
  readonly property bool submissionCapacity:retainedSubmissions>=16&&!agentPane.pendingMessageId
  property string sessionMessage:""
  property string sessionInput:""
  property string sessionOperation:""
  property int uiGeneration:0
  property var organizeContext:null
  property string inventoryMessage:""
  property var inventoryNotices:[]
  property bool awaitingLive:false
  property int agentSelectionGeneration:0
  property var sessionContext:null
  onPanelChanged:uiGeneration++
  onReplayingChanged:uiGeneration++
  property var sessionResult:null
  property var bookmarkResult:null
  property bool intentionallyPaused:false
  property alias testNavigation:navigation
  property alias testResources:resourcesPane
  property alias testSessionsProcess:sessions
  property alias testResourcesProcess:resources
  property alias testOrganizationProcess:organization
  property alias testLens:lensPane
  property alias testOrganize:organizer
  property alias testAgent:agentPane
  property alias testDeskButton:deskButton
  property alias testProvidersButton:providersButton
  property alias testPaceDock:paceDock
  property alias testProviderPane:providerPane
  property alias testStoredAgents:storedAgentsAction

  property var groupingPreferences: ({revision:0,colors:{},rules:{}})
  property var groupHistory: ({})
  property var groupingResult: null
  property string groupingMessage: ""
  readonly property bool groupingBusy: groupingProcess.running
  property bool atlasOpen: false
  property string queryText: ""
  property string lens: ""
  property bool nameEditing: false
  property string renameDraft: ""
  property int renameWorkspace: -1
  property var moveDraft: null
  property var metadataContext: null
  property var metadataResult: null
  property string actionKind: "focus"
  property var actionResult: null
  property var actionContext: null
  property var hoverTarget: null
  property real hoverAt: 0
  property point pointer: Qt.point(-100,-100)
  property var cameraFrom: null
  property var cameraTarget: null
  property real cameraAt: 0
  property real cameraDuration: 420
  readonly property var ui: Object.assign({},Camera.metrics(body.width,body.height),{header:Math.max(126,Camera.metrics(body.width,body.height).header)})
  readonly property var cameraView: Camera.view({x:panX,y:panY,zoom:zoom},stage.width,stage.height)
  readonly property bool metadataBusy: metadata.running
  readonly property bool actionBusy: action.running
  readonly property var neons: ["#57dfff","#fc69d5","#b99cff","#b0fca9","#ffcd78"]
  readonly property color panelPaper: night?"#10182c":"#e9f0f6"
  readonly property var tracedBuildings: scene.buildings.filter(function(b){return !b.dying&&(!lens||b.appClass===lens)})
  readonly property var pinnedDistricts: scene.districts.filter(function(d){return d.pinned})
  readonly property var atlasResults: {
    var q=queryText.trim().toLowerCase(),out=[]
    scene.buildings.filter(function(b){return b.kind==="agent"&&!b.dying}).forEach(function(b){if(!q||(b.app+" "+(b.agent.project||"")+" "+b.agent.provider+" "+b.agent.id).toLowerCase().indexOf(q)>=0)out.push({type:"building",key:b.key,label:b.app,subtitle:Agents.subtitle(b.agent)+(b.agentGlow?" · "+b.agentGlow.label:"")})})
    scene.districts.slice().sort(function(a,b){return Number(b.pinned)-Number(a.pinned)||a.id-b.id}).forEach(function(d){if(!q||(d.name+" district "+d.id).toLowerCase().indexOf(q)>=0)out.push({type:"district",key:d.id,label:d.name,subtitle:d.virtualWorkspace?d.count+" agent sessions":"D"+d.id+" · "+d.count+(d.count===1?" window":" windows")})})
    snapshot.windows.forEach(function(w){if(!q||(w.app+" "+w.class+" "+root.districtName(w.workspace)).toLowerCase().indexOf(q)>=0)out.push({type:"building",key:w.address,label:w.app,subtitle:root.districtName(w.workspace)})})
    return out
  }
  property var snapshot: ({boroughs:[],districts:[],windows:[]})
  property var scene: ({districts:[],buildings:[],roads:[],boroughs:[],bounds:{minX:0,maxX:1,minY:0,maxY:1}})
  property string selected: ""
  property int selectedDistrict: -1
  property int borough: -1
  property string message: ""
  property bool failed: false
  property bool showSettings: false
  property real zoom: 1
  property real panX: 0
  property real panY: 0
  property real clock: 0
  property int frameCount: 0
  property int updateCount: 0
  property int sceneBuildCount: 0
  property int metricUpdates: 0
  property string sceneSignature: ""
  property bool hasFitted: false
  property bool navigating: false
  property alias testMap:mapInput
  property alias testBody:body
  property alias testFit:fitButton
  property alias testEnter:inspector.testEnter
  property alias testNight:nightButton
  property alias testInspector:inspector
  property alias testLegend:legend
  property alias testGrouping:groupingProcess
  property alias testAtlas:atlas
  property alias testMove:moveModal
  property alias testMinimap:minimapInput
  property alias testStage:stage
  property alias testAction:action
  property alias testMotion:motionButton
  property alias testMinimize:minimizeButton
  property alias testMaximize:maximizeButton
  property alias testClose:closeButton
  property var selectedScreen: null
  property var renumberQueue: []
  property real transitionsUntil: 0
  property real transitionClock: 0
  readonly property bool motion: settings.motion !== false
  readonly property bool night: settings.night !== false
  readonly property bool stale: !!snapshot.timestamp && Date.now()/1000-snapshot.timestamp>8
  readonly property string helper: decodeURIComponent(String(Qt.resolvedUrl("districts.py")).replace(/^file:\/\//,""))
  readonly property color accent: night?neons[0]:"#05647d"
  readonly property bool lightTheme: Color.background.r*.2126+Color.background.g*.7152+Color.background.b*.0722>.55
  readonly property color ink: night?"#dceaff":"#18384b"
  readonly property color paper: night?"#060c19":"#e8eff3"
  readonly property var palette: ({accent:String(accent),ink:String(ink),neons:neons,
    ground:String(night?Qt.darker(paper,1.05):Qt.lighter(paper,1.45)),
    foundation:String(Qt.darker(paper,1.5)),left:String(night?Qt.lighter(paper,1.65):Qt.lighter(paper,1.25)),
    right:String(night?Qt.lighter(paper,1.25):Qt.darker(paper,1.05)),
    roof:String(night?Qt.lighter(paper,2.1):Qt.lighter(paper,1.9)),roofActive:String(Qt.tint(paper,Qt.alpha(accent,.25)))})
  readonly property var selectedBuilding: {
    for(var i=0;i<scene.buildings.length;i++)if(scene.buildings[i].key===selected&&!scene.buildings[i].dying)return scene.buildings[i]
    return null
  }
  readonly property var district: {
    for(var i=0;i<scene.districts.length;i++)if(scene.districts[i].id===selectedDistrict)return scene.districts[i]
    return null
  }
  readonly property var currentBuildings: scene.buildings.filter(function(b){return !b.dying&&(selectedDistrict===-1||b.workspace===selectedDistrict)})
  implicitWidth: 30
  implicitHeight: bar ? bar.barSize : 28

  function saveSetting(key,value) {
    var next=Object.assign({},settings);next[key]=value
    var api=bar&&bar.shell?bar.shell:shell
    if(!testMode && (!api || !api.updateEntryInline || !api.updateEntryInline(moduleName,next))){message="Setting could not be saved.";return false}
    settings=next;paint();return true
  }
  function open() {
    if(opened){if(!testMode)frame("raise");body.forceActiveFocus();return}
    appMinimized=false;appMaximized=false
    navigating=false
    var monitor=Hyprland.focusedMonitor,screens=Quickshell.screens
    selectedScreen=null
    for(var i=0;i<screens.length;i++)if(monitor&&screens[i].name===monitor.name)selectedScreen=screens[i]
    if(!selectedScreen&&screens.length)selectedScreen=screens[0]
    opened=true;failed=false;message="";hasFitted=false
    refresh();refreshAgents();refreshProviderMetrics();fitTimer.restart();Qt.callLater(function(){if(!testMode)body.forceActiveFocus()})
  }
  function rememberSize(){if(window){preferMaximized=appMaximized;if(!appMaximized&&window.width>=912&&window.height>=512)rememberedSize=Qt.size(window.width,window.height)}}
  function minimize(){rememberSize();close();appMinimized=true}
  function frame(operation){if(!opened||!window||appFrame.running)return;var args=["python3","-B",helper,"application-frame",operation];if(operation==="configure"&&preferMaximized)args.push("--maximized");if(testMode)args.push("--fixture");frameResult=null;appFrame.command=args;appFrame.running=true}
  function maximize(){frame("toggle")}
  function close() {rememberAgentDraft();switchingAgent=true;if(sessionOperation!=="send")sessions.running=false;resources.running=false;quotaMetrics.running=false;if(organizeOperation!=="apply")organization.running=false;navigation.suspend();panel="";agentTarget=null;sessionReply=null;sessionReplyIdentity="";sessionDraft="";switchingAgent=false;rememberSize();appMinimized=false;opened=false;legendOpen=false;showSettings=false;atlasOpen=false;nameEditing=false;moveDraft=null;cameraTimer.stop();pointer=Qt.point(-100,-100)}
  function toggle() {if(opened)close();else open()}
  function refresh() {
    if((testMode&&!testLiveBridge)||!opened)return
    intentionallyPaused=false
    if(collector.running){collector.write("refresh\n");return}
    collector.command=["python3","-B",helper,"watch"];collector.running=true
  }
  function ingest(value) {
    if(!value||value.schema!==1||!Array.isArray(value.windows)||!Array.isArray(value.districts)){failed=true;message="City data unavailable. Refresh to reconnect.";return}
    if(value.grouping&&Number(value.grouping.revision)>=groupingPreferences.revision)groupingPreferences=Groups.preferences(value.grouping)
    value=Groups.enrich(value,groupHistory,value.activityTime===undefined?Date.now():Number(value.activityTime),groupingPreferences)
    liveSnapshot=value
    if(awaitingLive)message=""
    awaitingLive=false
    if(opened)navigation.observe(value,agentRecords,Date.now())
    if(replaying)return
    renderSnapshot(value,agentRecords)
  }
  function providerFamily(agent){return agent&&agent.provider==="pi"&&agent.isKimi3===true?"kimi":agent&&agent.provider||""}
  function filterProvider(provider){providerFilter=providerFilter===provider?"":provider;renderCurrentSnapshot();fit();if(agentTarget&&providerFilter&&providerFamily(agentTarget)!==providerFilter)selectAgent(null)}
  function visibleAgents(input){input=input.filter(function(a){return !providerFilter||providerFamily(a)===providerFilter});if(settings.storedAgents===true||replaying||providerFilter)return input;var found={},out=input.filter(function(a){return a.availability==="live"});out.forEach(function(a){found[Agents.key(a)]=true});for(var n=0;n<16;n++){var changed=false;out.slice().forEach(function(a){var p=Agents.parent(a,input);if(p&&!found[Agents.key(p)]){found[Agents.key(p)]=true;out.push(p);changed=true}});if(!changed)break}return out}

  function toggleFamily(family){if(!family)return;var next=Object.assign({},collapsedFamilies);if(next[family])delete next[family];else next[family]=true;collapsedFamilies=next;renderCurrentSnapshot()}
  function renderCurrentSnapshot(){var value=viewSource;renderSnapshot(value,replaying?(value.agents||[]):agentRecords)}
  function renderSnapshot(value,agents) {
    value=FocusLens.apply(Object.assign({},value,{agents:visibleAgents(agents||[])}),focusLens)
    // CPU changes update facade lights and the inspector, never city geometry.
    var topology=value.windows.map(function(w){var row=Object.assign({},w);delete row.ownerCpu;delete row.pid;return row})
    var signature=JSON.stringify([value.boroughs,value.districts,topology,value.focused,(value.agents||[]).map(function(a){return [a.provider,a.id,a.parentId,a.familyId]}),focusLens,Object.keys(collapsedFamilies).sort()])
    updateCount++;failed=false;message=""
    if(signature===sceneSignature){snapshot=value;City.updateActivity(scene,value.windows);scene.buildings.forEach(function(b){if(b.kind==="agent"){var a=(value.agents||[]).find(function(a){return Agents.key(a)===b.key});if(a)Agents.applyState(b,a)}});scene=Object.assign({},scene);metricUpdates++;paint();if(!hasFitted&&opened)fitTimer.restart();return}
    sceneSignature=signature;sceneBuildCount++
    var next=Agents.decorate(City.layout(value),value.agents||[],{collapsed:collapsedFamilies})
    var old={};scene.buildings.forEach(function(b){old[b.key]=b})
    var changed=next.buildings.some(function(b){return !old[b.key]||old[b.key].targetX!==b.x||old[b.key].targetY!==b.y})||scene.buildings.some(function(b){return !next.buildings.some(function(n){return n.key===b.key})})
    snapshot=value;scene=City.transition(scene,next,motion,Date.now())
    if(changed)transitionsUntil=Date.now()+850
    if(selected&&!selectedBuilding)selected=""
    if(selectedDistrict!==-1&&!district)selectedDistrict=-1
    if(!hasFitted&&opened)fitTimer.restart()
    failed=false;message="";paint()
  }
  function paint(){if(opened){cityCanvas.requestPaint();minimap.requestPaint()}}
  function cameraTo(value,duration) {
    cameraTimer.stop()
    value=Camera.orbit(value,value.yaw===undefined?yaw:value.yaw,value.tilt===undefined?tilt:value.tilt)
    if(!motion||duration===0){panX=value.x;panY=value.y;zoom=value.zoom;yaw=value.yaw;tilt=value.tilt;paint();return}
    cameraFrom=currentCamera;cameraTarget=value;cameraAt=Date.now();cameraDuration=duration||420;cameraTimer.start()
  }
  function fit() {
    cameraTo(Camera.fit(projectedBounds,stage.width,stage.height,paceReserve,orbitCamera));hasFitted=true
  }
  function resetCamera(){navigation.userTakeover();var c=Camera.reset(currentCamera);yaw=c.yaw;tilt=c.tilt;selected="";selectedDistrict=-1;fit()}
  function restoreCamera(value,target){navigation.userTakeover();var c=Camera.orbit(value,value.yaw,value.tilt);yaw=c.yaw;tilt=c.tilt;var bounds=City.bounds(scene,c,c.zoom),r=Camera.range(stage.width,stage.height);c.zoom=City.clamp(c.zoom,r.min,r.max);c.x=City.clamp(c.x,-bounds.maxX*c.zoom-stage.width/3,-bounds.minX*c.zoom+stage.width/3);c.y=City.clamp(c.y,-bounds.maxY*c.zoom-stage.height/3,-bounds.minY*c.zoom+stage.height/3);cameraTo(c);if(target>0&&scene.districts.some(function(d){return d.id===target}))selectedDistrict=target;else selectedDistrict=-1;selected=""}
  function districtName(id){for(var i=0;i<scene.districts.length;i++)if(scene.districts[i].id===id)return scene.districts[i].name;return "District "+id}
  function focusDistrict(id,fromTour,instant) {
    if(!fromTour)navigation.userTakeover()
    nameEditing=false;selectedDistrict=id;selected="";inspector.showInfo()
    for(var i=0;i<scene.districts.length;i++)if(scene.districts[i].id===id){var p=City.project(scene.districts[i].x,scene.districts[i].y,20,orbitCamera),b=City.districtBounds(scene.districts[i],orbitCamera),c=Camera.fit(b,stage.width,stage.height,paceReserve,orbitCamera);cameraTo(c,instant?0:420);return}
  }
  function inspectBuilding(key) {
    navigation.userTakeover()
    nameEditing=false;selected=String(key);inspector.showInfo()
    if(selectedBuilding){if(lens&&lens!==selectedBuilding.appClass)lens="";selectedDistrict=selectedBuilding.workspace;var p=City.project(selectedBuilding.x,selectedBuilding.y,selectedBuilding.height/2,orbitCamera),z=Math.max(zoom,Math.min(3.6,stage.height/210));cameraTo({x:-p.x*z,y:-p.y*z,zoom:z})}
    paint()
  }
  function inspectResult(result){closeAtlas();if(result.type==="district")focusDistrict(result.key);else inspectBuilding(result.key)}
  function openAtlas(){navigation.userTakeover();panel="";navigation.close();legendOpen=false;nameEditing=false;moveDraft=null;atlasOpen=true;queryText="";pointer=Qt.point(-100,-100)}
  function closeAtlas(){atlasOpen=false;body.forceActiveFocus()}
  function zoomAt(factor,x,y){navigation.userTakeover();var base=cameraTimer.running?cameraTarget:currentCamera;cameraTo(Camera.anchored(base,factor,x,y,stage.width,stage.height),160)}
  function traceApp(){lens=selectedBuilding?(lens?"":selectedBuilding.appClass):"";inspector.showList();paint()}
  function beginRename(){if(replaying||!district||district.virtualWorkspace||metadataBusy)return;renameWorkspace=district.id;renameDraft=district.customName||"";nameEditing=true;pointer=Qt.point(-100,-100)}
  function cancelRename(){if(metadataBusy)return;nameEditing=false;renameDraft="";body.forceActiveFocus()}
  function saveRename(){if(nameEditing&&renameWorkspace>0)customize({name:renameDraft},renameWorkspace)}
  function customize(fields,workspace) {
    if(replaying||metadataBusy)return false
    var wid=workspace||selectedDistrict;if(wid<1)return false
    metadataContext={workspace:wid,fields:fields};metadataResult=null
    var args=["python3","-B",helper,"customize",String(wid)]
    if(fields.name!==undefined)args=args.concat(["--name",String(fields.name)])
    if(fields.pinned!==undefined)args=args.concat(["--pinned",fields.pinned?"true":"false"])
    if(fields.tint!==undefined)args=args.concat(["--tint",String(fields.tint)])
    if(testMode&&!testMetadataIO){applyCustomization(metadataContext);return true}
    metadata.command=args;metadata.running=true;return true
  }
  function applyCustomization(context){var value=JSON.parse(JSON.stringify(liveSnapshot));value.districts.forEach(function(d){if(d.id===context.workspace)Object.keys(context.fields).forEach(function(k){if(k==="name"){d.customName=context.fields[k];d.name=context.fields[k]||d.autoName||City.activityName(value,d.id);d.nameSource=context.fields[k]?"custom":d.autoSource||"apps"}else d[k]=context.fields[k]})});ingest(value);nameEditing=false;message="District saved";if(opened)body.forceActiveFocus()}
  function beginMove(){legendOpen=false;if(replaying||!selectedBuilding||selectedBuilding.kind==="agent"||actionBusy)return;var b=selectedBuilding;moveDraft={address:b.address,app:b.app,appClass:b.appClass,sourceWorkspace:b.workspace,destination:-1};pointer=Qt.point(-100,-100)}
  function chooseDestination(id){if(moveDraft)moveDraft=Object.assign({},moveDraft,{destination:id})}
  function cancelMove(){moveDraft=null;body.forceActiveFocus()}
  function validMove(){return !replaying&&!!moveDraft&&moveDraft.destination>0&&moveDraft.destination!==moveDraft.sourceWorkspace&&!actionBusy&&!failed&&scene.districts.some(function(d){return d.id===root.moveDraft.destination})}
  function confirmMove(){
    if(!validMove())return
    if(snapshot.timestamp&&Date.now()/1000-snapshot.timestamp>8){message="Refresh before moving this building.";refresh();return}
    var t=Object.assign({},moveDraft)
    if(!snapshot.windows.some(function(w){return w.address===t.address&&w.class===t.appClass&&w.workspace===t.sourceWorkspace})){message="That building changed. Refresh and choose it again.";moveDraft=null;return}
    moveDraft=null
    if(testMode){fixtureMoves++;var v=JSON.parse(JSON.stringify(snapshot));v.windows.forEach(function(w){if(w.address===t.address){w.workspace=t.destination;var d=v.districts.filter(function(d){return d.id===t.destination})[0];if(d)w.monitor=d.monitor}});v.districts.forEach(function(d){d.count=v.windows.filter(function(w){return w.workspace===d.id}).length});ingest(v);selectedDistrict=t.destination;message="Fixture relocation only";return}
    actionKind="relocate";actionContext=t;actionResult=null
    action.command=["python3","-B",helper,"relocate",t.address,String(t.destination),"--app",t.appClass,"--workspace",String(t.sourceWorkspace)];action.running=true
  }
  function openLegend(){navigation.userTakeover();panel="";navigation.close();if(metadataBusy)return;nameEditing=false;atlasOpen=false;moveDraft=null;showSettings=false;legendOpen=true;pointer=Qt.point(-100,-100)}
  function closeLegend(){legendOpen=false;body.forceActiveFocus()}
  function updateGrouping(fields){
    if(replaying||groupingBusy)return
    groupingMessage="";groupingResult=null
    var args=["python3","-B",helper,"group"]
    if(fields.group!==undefined)args=args.concat(["--group",fields.group,"--color",String(fields.color)])
    if(fields.app!==undefined)args=args.concat(["--app",String(fields.app),"--rule",fields.rule])
    groupingProcess.command=args;groupingProcess.running=true
  }
  function dismiss(){if(navigation.panelOpen)navigation.close();else if(panel!=="")panel="";else if(legendOpen)closeLegend();else if(moveDraft)cancelMove();else if(atlasOpen)closeAtlas();else if(nameEditing)cancelRename();else close()}
  function pick(x,y) {
    navigation.userTakeover()
    var hit=City.hit(scene,(x-stage.width/2-panX)/zoom,(y-stage.height/2-panY)/zoom,zoom,orbitCamera)
    if(!hit){selected="";paint();return}
    if(hit.type==="group"){if(hit.key==="agent-sessions"){openPanel("agents");return}openLegend();legend.editColor(hit.key);return}
    if(hit.type==="building"){selected=hit.key;selectedDistrict=selectedBuilding?selectedBuilding.workspace:-1}
    else {selected="";selectedDistrict=hit.key}
    inspector.showInfo();paint()
  }
  function selectNext(direction) {
    var list=currentBuildings;if(!list.length)return
    var index=list.map(function(b){return b.key}).indexOf(selected)
    inspectBuilding(list[(index+direction+list.length)%list.length].key)
  }
  function navigate() {
    if(replaying){message="Return live and select again before acting.";return}
    if(selectedBuilding&&selectedBuilding.kind==="agent"){openAgent(selectedBuilding.agent);return}
    if(district&&district.virtualWorkspace)return
    if(navigating||actionBusy||metadataBusy)return
    if(testMode){message="Fixture navigation suppressed";return}
    if((snapshot.timestamp&&Date.now()/1000-snapshot.timestamp>8)||failed){message="Refresh the city before entering.";refresh();return}
    var target=selectedBuilding,command
    if(target)command=["python3","-B",helper,"focus",target.address,"--app",target.appClass,"--workspace",String(target.workspace)]
    else if(district)command=["python3","-B",helper,"visit",String(district.id)]
    else return
    navigating=true;actionKind="focus";actionResult=null;action.command=command
    // Release the city layer's keyboard ownership before the compositor focuses an app.
    close();action.running=true
  }
  function status() {
    return JSON.stringify({version:"3.0.0",opened:opened,yaw:yaw,tilt:tilt,agentCount:agentRecords.length,sessionBusy:sessions.running,metricsBusy:quotaMetrics.running,resourcesBusy:resources.running,replaying:replaying,touring:navigation.touring,lens:focusLens,panel:panel,districts:scene.districts.length,buildings:snapshot.windows.length,
      selected:!!selectedBuilding,selectedDistrict:selectedDistrict,motion:motion,night:night,frames:frameCount,updates:updateCount,
      zoom:zoom,failed:failed,collector:collector.running,navigating:navigating,standalone:true,sceneBuilds:sceneBuildCount,metricUpdates:metricUpdates,ownerCpuMeasured:snapshot.windows.filter(function(w){return w.ownerCpu&&w.ownerCpu.state==='measured'}).length,ownerCpuSampling:snapshot.windows.filter(function(w){return w.ownerCpu&&w.ownerCpu.state==='sampling'}).length,ownerCpuUnavailable:snapshot.windows.filter(function(w){return !w.ownerCpu||w.ownerCpu.state==='unavailable'}).length,viewport:[body.width,body.height],applicationWindow:true,frameBusy:appFrame.running,minimized:appMinimized,maximized:!!window&&appMaximized,mapped:!!window&&window.backingWindowVisible,screen:selectedScreen?selectedScreen.name:"automatic",cameraRunning:cameraTimer.running,edgeRunning:edgeTimer.running,legend:legendOpen,groupingBusy:groupingBusy,groups:(scene.groups||[]).length,atlas:atlasOpen,renaming:nameEditing,moving:moveDraft!==null,metadataBusy:metadataBusy,fixtureMoves:fixtureMoves,viewportLogical:[body.width,body.height],mapViewport:[stage.width,stage.height],canvasPhysicalPixels:Math.round(cityCanvas.width*cityCanvas.height*Screen.devicePixelRatio*Screen.devicePixelRatio)})
  }
  function capture(path,scale) {var ok=body.grabToImage(function(result){console.log("CAPTURE "+path+" "+result.saveToFile(path))},Qt.size(body.width*(scale||1),body.height*(scale||1)));console.log("GRAB "+path+" "+ok);return ok}
  onOpenedChanged: {uiGeneration++;if(!opened){collector.running=false;eventTimer.stop();fitTimer.stop();cameraTimer.stop()}}
  onYawChanged:paint()
  onTiltChanged:paint()
  onOrbitDraggingChanged:paint()
  onPanXChanged:paint()
  onPanYChanged:paint()
  onZoomChanged:paint()
  onMotionChanged: {if(!motion){if(cameraTimer.running){cameraTimer.stop();panX=cameraTarget.x;panY=cameraTarget.y;zoom=cameraTarget.zoom;yaw=cameraTarget.yaw;tilt=cameraTarget.tilt}City.advance(scene,Date.now(),false);scene=Object.assign({},scene)}paint()}
  onPaletteChanged:paint()

  function moduleHelper(name){return decodeURIComponent(String(Qt.resolvedUrl(name)).replace(/^file:\/\//,""))}
  function openPanel(value){if(panel==="agents"&&value!=="agents")rememberAgentDraft();navigation.userTakeover();navigation.close();showSettings=false;legendOpen=false;atlasOpen=false;nameEditing=false;moveDraft=null;panel=value;pointer=Qt.point(-100,-100);if(value==="agents"&&!agentTarget&&deskAgents.length)selectAgent(deskAgents[0]);if(value==="providers")refreshProviderMetrics()}
  function openNavigation(value){panel="";showSettings=false;navigation.userTakeover();navigation.open(value)}
  function refreshAgents(){if(!opened||(testMode&&!testLiveBridge)||sessions.running)return;sessionOperation="inventory";sessionContext={generation:uiGeneration};sessionResult=null;sessions.command=["python3","-B",moduleHelper("sessions.py"),"inventory"];sessions.running=true}
  function acceptAgents(rows){if(agentTarget)rememberAgentDraft();agentRecords=Agents.records(rows);if(agentTarget){var current=agentRecords.find(function(a){return a.provider===agentTarget.provider&&a.id===agentTarget.id});agentTarget=current||null;if(!current){sessionReply=null;sessionReplyIdentity="";sessionDraft=""}}if(opened){navigation.observe(liveSnapshot,agentRecords,Date.now());if(!replaying&&!awaitingLive)renderSnapshot(liveSnapshot,agentRecords)}}
  function rememberAgentDraft(){if(switchingAgent||!agentTarget||flushingDraft)return;flushingDraft=true;try{agentPane.flushEditor()}finally{flushingDraft=false}var entries=Object.assign({},sessionDrafts),key=agentTarget.provider+":"+agentTarget.id;entries[key]={draft:sessionDraft,messageId:agentPane.pendingMessageId,touched:Date.now()};var keys=Object.keys(entries).sort(function(a,b){return entries[b].touched-entries[a].touched});keys.filter(function(k){return !entries[k].messageId}).slice(16).forEach(function(k){delete entries[k]});sessionDrafts=entries}
  function pendingSubmissionCount(){var entries=sessionDrafts,keys=Object.keys(entries).filter(function(k){return !!entries[k].messageId}),key=agentTarget?agentTarget.provider+":"+agentTarget.id:"";if(key&&agentPane.pendingMessageId&&keys.indexOf(key)<0)keys.push(key);return keys.length}
  function canReserveSubmission(agent){if(!agent)return false;var key=agent.provider+":"+agent.id,saved=sessionDrafts[key];return !!(saved&&saved.messageId)||pendingSubmissionCount()<16}
  function selectAgent(agent){var changed=(!agentTarget)!==(!agent)||agent&&agentTarget&&(agent.provider!==agentTarget.provider||String(agent.id)!==String(agentTarget.id));rememberAgentDraft();switchingAgent=true;if(changed){agentSelectionGeneration++;sessionReply=null;sessionReplyIdentity="";sessionMessage=""}agentTarget=agent;var saved=agent?sessionDrafts[agent.provider+":"+agent.id]:null;sessionDraft=saved?saved.draft:"";agentPane.draft=sessionDraft;agentPane.pendingMessageId=saved?saved.messageId:"";switchingAgent=false}
  function openAgent(agent){openPanel("agents");selectAgent(agent);sessionReply=null;sessionReplyIdentity="";sessionMessage="";}
  function sessionCommand(operation,agent){if(!agent||sessions.running)return false;if(!agentTarget||agentTarget.provider!==agent.provider||String(agentTarget.id)!==String(agent.id)){sessionMessage="Select this exact session again before the action.";return false}sessionOperation=operation;sessionContext={provider:agent.provider,id:String(agent.id||agent.sessionId),generation:uiGeneration,selectionGeneration:agentSelectionGeneration};sessionResult=null;sessionMessage="";sessions.command=["python3","-B",moduleHelper("sessions.py"),operation,"--provider",agent.provider,"--id",String(agent.id||agent.sessionId)];return true}
  function readAgent(agent){if(!opened||panel!=="agents"||replaying){sessionMessage="Return live and select again before reading.";return}if(!agent||!agentTarget||agentTarget.provider!==agent.provider||String(agentTarget.id)!==String(agent.id)){sessionMessage="Select this exact session again before reading.";return}agent=agentRecords.find(function(r){return r.provider===agent.provider&&String(r.id)===String(agent.id)});if(!agent||!agent.capabilities||agent.capabilities.canReadReply!==true){sessionMessage="Reply reading is unavailable for this session.";return}if(testMode&&!testLiveBridge){agentTarget=agent;sessionReply={ok:true,text:"Synthetic reply fixture. No live session content was read.",source:"Protocol fixture"};sessionMessage="Fixture reply only";return}if(sessionCommand("reply",agent))sessions.running=true}
  function sendAgent(agent,text,messageId){var saved=agent?sessionDrafts[agent.provider+":"+agent.id]:null;if(!messageId||!saved||saved.messageId!==messageId||saved.draft!==text||!canReserveSubmission(agent)){sessionMessage="Retained submission identity does not match this draft. Select and review the retained draft.";return}if(testMode){sessionMessage="Fixture sending is suppressed.";return}if(replaying){sessionMessage="Return live and select again before sending.";return}if(!agent||!agentRecords.some(function(r){return r.provider===agent.provider&&String(r.id)===String(agent.id)})){sessionMessage="Session changed. Refresh and select again.";return}if(!sessionCommand("send",agent))return;sessionInput=JSON.stringify({text:text});sessions.command=sessions.command.concat(["--message-id",messageId]);sessions.running=true}
  function openAgentNative(agent){if(testMode)return;if(!replaying&&sessionCommand("open",agent))sessions.running=true}
  function openResources(){resourcesTarget=selectedBuilding;resourcesResult=null;resourcesError="";openPanel("resources");readResources()}
  function readResources(){if(resources.running)return;resourcesResult=null;if(testMode&&!testLiveBridge){resourcesError="Synthetic fixture; no live owner counters read.";return}var b=resourcesTarget;if(!b||b.kind==="agent"||replaying){resourcesError=replaying?"Historical owner counters are unavailable.":b&&b.kind==="agent"?"No verified process owner for this session. Adapter state is reported below.":"Select a real app building first.";return}resourcesError="";resourcesContext={generation:uiGeneration,key:b.key,address:b.address,pid:b.ownerPid,startTime:b.ownerCpu?b.ownerCpu.startTime:null};resources.command=["python3","-B",moduleHelper("resources.py"),String(b.ownerPid),b.address,"--app",b.appClass];if(b.ownerCpu&&b.ownerCpu.startTime)resources.command=resources.command.concat(["--start-time",String(b.ownerCpu.startTime)]);resources.running=true}
  function previewOrganization(){if(replaying||organization.running)return;openPanel("organize");organizeOperation="preview";organizeContext={generation:uiGeneration};organizePlan=null;organizeReceipt=null;organizeError="";organizeResult=null;organizeInput=JSON.stringify(liveSnapshot);organization.command=["python3","-B",moduleHelper("organize.py"),"preview"];if(testMode&&!testLiveBridge){organizePlan={schema:1,planId:"fixture-preview",moves:[],expiresAt:Date.now()/1000+120,omitted:0,protectedDistricts:0,deferred:0};return}organization.running=true}
  function applyOrganization(planId){if(replaying||organization.running||!organizePlan||organizePlan.planId!==planId)return;organizeOperation="apply";organizeContext={generation:uiGeneration,planId:planId};organizeInput=JSON.stringify(organizePlan);organizeResult=null;organization.command=["python3","-B",moduleHelper("organize.py"),"apply","--accept",planId];if(testMode){organizeError="Fixture organization never moves host windows.";return}organization.running=true}
  function persistView(request){if(bookmarks.running)return;if(testMode&&!testMetadataIO){navigation.acceptPersistence({ok:true,viewpoints:navigation.savedViews});return}var args=["python3","-B",moduleHelper("history.py"),request.operation];if(request.name)args=args.concat(["--name",request.name]);if(request.operation==="save"){args=args.concat(["--camera",JSON.stringify(request.camera)]);if(request.targetDistrict>0)args=args.concat(["--target-district",String(request.targetDistrict)])}bookmarkResult=null;bookmarks.command=args;bookmarks.running=true}
  Timer{interval:10000;repeat:true;running:root.opened&&(root.testMode||!idle.isIdle);onTriggered:root.refreshAgents()}
  Process{id:bookmarks;stdout:StdioCollector{onStreamFinished:{try{root.bookmarkResult=JSON.parse(text)}catch(e){root.bookmarkResult={ok:false,error:"Viewpoints unavailable."}}}}
    onExited:navigation.acceptPersistence(root.bookmarkResult)}
  Process{id:sessions;stdinEnabled:true;onStarted:if(root.sessionOperation==="send")write(root.sessionInput+"\n");stdout:StdioCollector{onStreamFinished:{try{root.sessionResult=JSON.parse(text)}catch(e){root.sessionResult={ok:false,message:"Session service unavailable."}}}}
    onExited:function(code){var r=root.sessionResult;if(!root.opened||root.replaying||!root.sessionContext||root.sessionContext.generation!==root.uiGeneration)return;if(root.sessionOperation!=="inventory"&&root.sessionContext.selectionGeneration!==root.agentSelectionGeneration)return;if(root.sessionOperation!=="inventory"&&(!root.agentTarget||!root.sessionContext||root.agentTarget.provider!==root.sessionContext.provider||String(root.agentTarget.id)!==root.sessionContext.id))return;if(!r||!r.ok||code!==0){root.sessionMessage=r&&r.message?r.message:"Session service unavailable.";return}if(root.sessionOperation==="inventory"){root.inventoryNotices=(r.notices||[]).concat(r.providers||r.unsupportedProviders||[]);root.inventoryMessage=(r.bounded?"Bounded inventory · ":"")+root.inventoryNotices.length+" adapter notices. Select Adapter status to inspect.";root.acceptAgents(r.agents||r.sessions||[]);} else if(root.sessionOperation==="reply"){if(r.provider!==root.sessionContext.provider||String(r.id)!==root.sessionContext.id){root.sessionMessage="Provider returned a different session identity; reply withheld.";return}root.sessionReply=r;root.sessionReplyIdentity=r.provider+":"+r.id;}else root.sessionMessage=r.message||"Exact session instruction queued."}}
  function refreshProviderMetrics(){if(!opened||replaying||(testMode&&!testLiveBridge)||quotaMetrics.running)return;metricsContext={generation:uiGeneration};metricsResult=null;quotaMetrics.command=["python3","-B",moduleHelper("sessions.py"),"metrics"];quotaMetrics.running=true}
  Timer{interval:60000;repeat:true;running:root.opened&&!root.replaying&&!idle.isIdle;onTriggered:root.refreshProviderMetrics()}
  Process{id:quotaMetrics;stdout:StdioCollector{onStreamFinished:{try{root.metricsResult=JSON.parse(text)}catch(e){root.metricsResult=null}}}
    onExited:function(code){if(!root.opened||root.replaying||!root.metricsContext||root.metricsContext.generation!==root.uiGeneration)return;var r=root.metricsResult;if(code!==0||!r||!r.ok){root.providerMetrics=[];root.metricsMessage="Provider quota metadata unavailable.";return}root.providerMetrics=r.providers||[];root.metricsMessage=""}}
  Process{id:resources;stdout:StdioCollector{onStreamFinished:{var b=root.resourcesTarget,c=root.resourcesContext;if(!root.opened||root.replaying||root.panel!=="resources"||!b||!c||c.generation!==root.uiGeneration||b.key!==c.key||b.address!==c.address||b.ownerPid!==c.pid)return;try{var r=JSON.parse(text);if(r.ok&&(r.address!==c.address||Number(r.pid)!==Number(c.pid)||(c.startTime&&Number(r.startTime)!==Number(c.startTime)))){root.resourcesError="Owner identity changed. Select again.";return}root.resourcesResult=r.ok?r:null;root.resourcesError=r.ok?"":r.error||"Owner details unavailable."}catch(e){root.resourcesError="Owner details unavailable."}}}}
  Process{id:organization;stdinEnabled:true;onStarted:write(root.organizeInput+"\n");stdout:StdioCollector{onStreamFinished:{try{root.organizeResult=JSON.parse(text)}catch(e){root.organizeResult={ok:false,error:"Organization unavailable."}}}}
    onExited:function(code){var r=root.organizeResult,c=root.organizeContext;if(!root.opened||root.replaying||root.panel!=="organize"||!c||c.generation!==root.uiGeneration)return;if(root.organizeOperation==="apply"&&r&&r.schema===1&&root.organizePlan&&r.planId===root.organizePlan.planId&&Array.isArray(r.items)){root.organizeReceipt=r;root.organizeError="";root.refresh()}else if(!r||!r.ok||code!==0)root.organizeError=r&&(r.error||r.message)?r.error||r.message:"Organization unavailable.";else if(root.organizeOperation==="preview")root.organizePlan=r.plan}}
  Process {
    id:collector
    stdinEnabled:true
    stdout:SplitParser {onRead:function(line){try{var data=JSON.parse(line);if(data.error){root.failed=true;root.message=data.error}else if(root.opened)root.ingest(data)}catch(e){root.failed=true;root.message="Desktop did not answer. Refresh to reconnect."}}}
    onExited:function(code){if(code!==0&&root.opened&&!root.intentionallyPaused){root.failed=true;if(!root.message)root.message="Desktop unavailable."}}
  }
  Process {
    id:action
    stdout:StdioCollector{onStreamFinished:{try{root.actionResult=JSON.parse(text)}catch(e){root.actionResult={ok:false,error:"Action could not complete."}}}}
    onExited:function(code){root.navigating=false;var result=root.actionResult;if(!result||!result.ok||code!==0){root.message=result&&result.error?result.error:"Action could not complete."}else if(root.actionKind==="relocate"){root.selectedDistrict=root.actionContext.destination;root.message="Building relocated";root.refresh()}}
  }
  Process{
    id:groupingProcess
    stdout:StdioCollector{onStreamFinished:{try{root.groupingResult=JSON.parse(text)}catch(e){root.groupingResult=null}}}
    onExited:function(code){if(code===0&&root.groupingResult&&root.groupingResult.ok){root.groupingPreferences=Groups.preferences(root.groupingResult.grouping);var value=Object.assign({},root.liveSnapshot,{grouping:root.groupingPreferences});root.ingest(value);root.groupingMessage="Grouping saved";if(root.opened)root.refresh()}else root.groupingMessage=root.groupingResult&&root.groupingResult.error?root.groupingResult.error:"Grouping could not be saved."}
  }
  Process{
    id:metadata
    stdout:StdioCollector{onStreamFinished:{try{root.metadataResult=JSON.parse(text)}catch(e){root.metadataResult=null}}}
    onExited:function(code){if(code===0&&root.metadataResult&&root.metadataResult.ok){root.applyCustomization(root.metadataContext);root.refresh()}else root.message=root.metadataResult&&root.metadataResult.error?root.metadataResult.error:"District could not be saved."}
  }
  Process {
    id:appFrame
    stdout:StdioCollector{onStreamFinished:{try{root.frameResult=JSON.parse(text)}catch(e){root.frameResult=null}}}
    onExited:function(code){if(root.opened&&code===0&&root.frameResult&&root.frameResult.ok){root.appMaximized=root.frameResult.maximized;root.preferMaximized=root.appMaximized;fitTimer.restart()}else if(root.opened)root.message=root.frameResult&&root.frameResult.error?root.frameResult.error:"Application window action failed."}
  }
  Process {
    id:renumber
    stdout:StdioCollector {}
    onExited:{root.refresh();root.drainRenumber()}
  }
  function drainRenumber() {
    if(testMode||renumber.running||!renumberQueue.length)return
    var q=renumberQueue.slice(),pair=q.shift();renumberQueue=q
    renumber.command=["python3","-B",helper,"renumber",String(pair[0]),String(pair[1])];renumber.running=true
  }
  Connections {
    target:Hyprland
    function onRawEvent(event) {
      var name=String(event.name||"")
      if(name==="changeworkspaceid") {
        var parts=event.parse?event.parse(2):String(event.data||"").split(","),a=Number(parts[0]),b=Number(parts[1])
        if(/^[1-9][0-9]*$/.test(String(parts[0]))&&/^[1-9][0-9]*$/.test(String(parts[1]))&&a<=100000&&b<=100000){root.renumberQueue=root.renumberQueue.concat([[a,b]]);root.drainRenumber()}
      }
      if(root.opened&&name==="fullscreen")root.frame("state")
      if(root.opened&&["workspace","workspacev2","focusedmon","focusedmonv2","activewindow","activewindowv2","openwindow","closewindow","movewindow","movewindowv2","changeworkspaceid","renameworkspace","monitoradded","monitorremoved","fullscreen"].indexOf(name)>=0)eventTimer.restart()
    }
  }
  Timer{id:eventTimer;interval:180;onTriggered:root.refresh()}
  IdleMonitor{id:idle;timeout:60;respectInhibitors:false;onIsIdleChanged:{if(root.testMode)return;if(isIdle){root.intentionallyPaused=true;navigation.stopTour("City paused while idle");navigation.playing=false;navigation.pauseTracking();if(root.sessionOperation!=="send")sessions.running=false;quotaMetrics.running=false;collector.running=false;root.message="City paused while idle"}else if(root.opened){root.refresh();root.refreshAgents();root.refreshProviderMetrics()}}}
  IdleInhibitor{window:window;enabled:root.testMode&&root.opened}
  Timer{id:fitTimer;interval:150;onTriggered:if(root.opened)root.fit()}
  Timer{id:cameraTimer;interval:33;repeat:true;running:false;onTriggered:{if(!root.opened){stop();return}var t=(Date.now()-root.cameraAt)/root.cameraDuration,c=Camera.interpolate(root.cameraFrom,root.cameraTarget,t);root.panX=c.x;root.panY=c.y;root.zoom=c.zoom;root.yaw=c.yaw;root.tilt=c.tilt;if(t>=1){stop();root.paint()}}}
  Timer{id:edgeTimer;interval:33;repeat:true;running:root.opened&&root.settings.edgePan!==false&&(root.testMode||!idle.isIdle)&&mapInput.containsMouse&&root.pointer.x>=0&&root.pointer.y>=0&&root.pointer.x<=stage.width&&root.pointer.y<=stage.height&&!mapInput.pressed&&!root.anyModal&&!root.showSettings&&!navigation.touring&&!cameraTimer.running&&(root.pointer.x<48||root.pointer.x>stage.width-48||root.pointer.y<48||root.pointer.y>stage.height-48)
    onTriggered:{var p=root.pointer;if(p.x<0||p.y<0||p.x>stage.width||p.y>stage.height)return;navigation.userTakeover();cameraTimer.stop();var dx=p.x<48?(48-p.x)/48:p.x>stage.width-48?-(p.x-stage.width+48)/48:0,dy=p.y<48?(48-p.y)/48:p.y>stage.height-48?-(p.y-stage.height+48)/48:0;root.panX+=City.clamp(dx,-1,1)*11;root.panY+=City.clamp(dy,-1,1)*11}}

  Timer{id:animationTimer;interval:66;repeat:true;running:root.opened&&root.motion&&(!idle.isIdle||root.testMode);onTriggered:{root.clock+=.066;if(Date.now()<root.transitionsUntil){root.transitionClock=root.clock;var count=root.scene.buildings.length;City.advance(root.scene,Date.now(),true);if(count!==root.scene.buildings.length)root.scene=Object.assign({},root.scene);paint()}root.frameCount++}}
  IpcHandler {
    target:"nixfred.districts"
    function open():void {root.open()}
    function close():void {root.close()}
    function minimize():void {root.minimize()}
    function maximize():void {root.maximize()}
    function toggle():void {root.toggle()}
    function refresh():void {root.refresh()}
    function status():string {return root.status()}
  }

  WidgetButton {
    id:button;anchors.fill:parent;bar:root.bar;labelVisible:false;hasVisualContent:true;fixedWidth:32
    tooltipText:"Districts · Your desktop city\n"+(root.message&&!root.opened?root.message:"Click to explore")
    onPressed:function(b){if(b===Qt.LeftButton)root.open()}
    Canvas{id:skyline;anchors.centerIn:parent;width:25;height:23;onPaint:{var c=getContext("2d");c.reset();c.fillStyle=String(Color.accent);c.strokeStyle=String(Color.accent);c.lineWidth=1.1;City.polygon(c,[{x:1,y:21},{x:1,y:11},{x:4,y:8},{x:7,y:11},{x:7,y:21}],String(Color.accent));City.polygon(c,[{x:9,y:21},{x:9,y:5},{x:12,y:3},{x:15,y:5},{x:15,y:21}],String(Color.accent));City.polygon(c,[{x:17,y:21},{x:17,y:13},{x:21,y:11},{x:24,y:13},{x:24,y:21}],String(Color.accent));c.beginPath();c.moveTo(12,4);c.lineTo(12,0);c.stroke();c.clearRect(3,13,2,2);c.clearRect(11,8,2,2);c.clearRect(11,13,2,2);c.clearRect(19,15,2,2);c.beginPath();c.moveTo(0,22);c.lineTo(25,22);c.stroke()}}
    Connections{target:Color;function onAccentChanged(){skyline.requestPaint()}}
  }
  Loader {
    id:applicationLoader
    active:root.opened
    sourceComponent:FloatingWindow {
      id:application
      title:root.testMode?"Districts · Fixture":"Districts"
      screen:root.selectedScreen
      color:root.paper
      minimumSize:Qt.size(912,512)
      implicitWidth:Math.max(912,Math.min(root.rememberedSize.width||1440,(root.selectedScreen?root.selectedScreen.width:1600)-96))
      implicitHeight:Math.max(512,Math.min(root.rememberedSize.height||900,(root.selectedScreen?root.selectedScreen.height:1000)-100))
      maximized:false
      visible:true
      mask:Region{item:root.testMode?null:body}
      onWindowConnected:{if(root.testMode&&application._backingWindow)application._backingWindow.flags|=Qt.WindowDoesNotAcceptFocus;Qt.callLater(function(){root.frame("configure")})}
      onClosed:root.close()
      onWidthChanged:if(root.opened)fitTimer.restart()
      onHeightChanged:if(root.opened)fitTimer.restart()
    }
  }
  Item {
      id:body
      parent:root.window?root.window.contentItem:null
      visible:root.opened
      width:root.testMode&&root.testViewport.width>0?root.testViewport.width:(parent?parent.width:0)
      height:root.testMode&&root.testViewport.height>0?root.testViewport.height:(parent?parent.height:0)
      focus:true
      Keys.onEscapePressed:root.dismiss()
      Keys.onPressed:function(event){
        if(root.anyModal)return
        navigation.userTakeover()
        if(event.key===Qt.Key_K&&(event.modifiers&Qt.ControlModifier)||event.key===Qt.Key_Slash){root.openAtlas();event.accepted=true}
        else if(event.key===Qt.Key_N){root.beginRename();event.accepted=true}
        else if(event.key===Qt.Key_Return||event.key===Qt.Key_Enter){root.navigate();event.accepted=true}
        else if(event.key===Qt.Key_Tab){root.selectNext(event.modifiers&Qt.ShiftModifier?-1:1);event.accepted=true}
        else if(event.key===Qt.Key_Home||event.key===Qt.Key_F){root.selectedDistrict=-1;root.selected="";root.fit();event.accepted=true}
        else if(event.key===Qt.Key_R){root.refresh();event.accepted=true}
        else if(event.key===Qt.Key_Left){cameraTimer.stop();root.panX+=65;event.accepted=true}
        else if(event.key===Qt.Key_Right){cameraTimer.stop();root.panX-=65;event.accepted=true}
        else if(event.key===Qt.Key_Up){cameraTimer.stop();root.panY+=50;event.accepted=true}
        else if(event.key===Qt.Key_Down){cameraTimer.stop();root.panY-=50;event.accepted=true}
        else if(event.key===Qt.Key_Plus||event.key===Qt.Key_Equal){root.zoomAt(1.2,stage.width/2,stage.height/2);event.accepted=true}
        else if(event.key===Qt.Key_Minus){root.zoomAt(1/1.2,stage.width/2,stage.height/2);event.accepted=true}
      }
      Rectangle{anchors.fill:parent;color:root.paper;gradient:Gradient{GradientStop{position:0;color:root.night?"#10132c":"#fafcff"}GradientStop{position:1;color:root.paper}}}
      Repeater{model:42;Rectangle{required property int index;x:(index*347%1901)/1901*body.width;y:(index*191%991)/991*body.height;width:index%5===0?2:1;height:width;radius:width;color:root.neons[index%5];opacity:root.night?.14:.1}}
      Item {
        id:stage;x:root.ui.margin;y:root.ui.header;width:Math.max(260,body.width-root.ui.sidebar-3*root.ui.margin);height:Math.max(220,body.height-root.ui.header-root.ui.footer)
        clip:true
        onWidthChanged:{root.pointer=Qt.point(-100,-100);if(root.opened&&root.hasFitted)root.fit()}
        onHeightChanged:{root.pointer=Qt.point(-100,-100);if(root.opened&&root.hasFitted)root.fit()}
        Canvas{id:cityCanvas;readonly property real rasterScale:Math.min(1,Math.sqrt(6000000/(stage.width*stage.height*Screen.devicePixelRatio*Screen.devicePixelRatio)));width:stage.width*rasterScale;height:stage.height*rasterScale;scale:1/rasterScale;transformOrigin:Item.TopLeft;renderStrategy:Canvas.Cooperative
          onPaint:{var c=getContext("2d");c.reset();c.clearRect(0,0,width,height);c.save();c.scale(rasterScale,rasterScale);c.translate(stage.width/2+root.panX,stage.height/2+root.panY);c.scale(root.zoom,root.zoom);City.draw(c,root.scene,root.palette,root.selected,root.selectedDistrict,root.clock,false,root.zoom,root.cameraView,root.lens,root.orbitCamera);c.restore()}
        }
        Repeater{model:root.opened?root.scene.buildings:[]
          Item{required property var modelData
            readonly property var pt:{var tick=root.transitionClock;return City.project(modelData.x,modelData.y,modelData.height*modelData.growth+3,root.orbitCamera)}
            x:stage.width/2+root.panX+pt.x*root.zoom-10;y:stage.height/2+root.panY+pt.y*root.zoom-13
            width:20;height:20;visible:root.zoom>.7&&!modelData.dying&&x>-24&&y>-24&&x<stage.width&&y<stage.height
            opacity:{var tick=root.transitionClock;return modelData.growth*(root.lens&&root.lens!==modelData.appClass?.22:1)}
            Image{anchors.fill:parent;source:parent.visible?Quickshell.iconPath(parent.modelData.icon,true):"";sourceSize:Qt.size(40,40);fillMode:Image.PreserveAspectFit;asynchronous:true}
          }
        }
        // Working / needs-attention agent buildings carry a roof beacon. It pulses
        // with QML opacity animation (no canvas repaint) and holds still under
        // reduced motion. The state comes only from the adapter's live report.
        Repeater{model:root.opened?root.scene.buildings.filter(function(b){return b.kind==="agent"&&!b.dying&&b.agentGlow&&b.agentGlow.pulse}).slice(0,48):[]
          Item{id:beacon;required property var modelData
            readonly property var pt:{var tick=root.transitionClock;return City.project(modelData.x,modelData.y,modelData.height+24,root.orbitCamera)}
            x:stage.width/2+root.panX+pt.x*root.zoom-width/2;y:stage.height/2+root.panY+pt.y*root.zoom-height/2
            width:Math.max(10,22*Math.min(1.4,root.zoom));height:width
            visible:root.zoom>.28&&x>-width&&y>-height&&x<stage.width&&y<stage.height&&!(root.lens&&root.lens!==modelData.appClass)
            Rectangle{anchors.fill:parent;radius:width/2;color:"transparent";border.width:2;border.color:beacon.modelData.agentGlow.color
              opacity:.85;SequentialAnimation on opacity{running:root.motion&&beacon.visible&&(root.testMode||!idle.isIdle);loops:Animation.Infinite;NumberAnimation{from:.95;to:.2;duration:beacon.modelData.agentGlow.state==="waiting"?520:1100;easing.type:Easing.InOutSine}NumberAnimation{from:.2;to:.95;duration:beacon.modelData.agentGlow.state==="waiting"?520:1100;easing.type:Easing.InOutSine}}}
            Rectangle{anchors.centerIn:parent;width:parent.width*.36;height:width;radius:width/2;color:beacon.modelData.agentGlow.color}
          }
        }
        Repeater{model:root.opened?root.scene.roads.filter(function(r){return r.kind!=="agent-link"}).slice(0,64):[]
          Rectangle{required property var modelData;readonly property var points:City.roadPoints(modelData,root.orbitCamera)
            readonly property real t:(root.clock*.07+(modelData.seed%100)/100)%1
            x:stage.width/2+root.panX+City.mix(points.a.x,points.b.x,t)*root.zoom-2;y:stage.height/2+root.panY+City.mix(points.a.y,points.b.y,t)*root.zoom-2
            width:4;height:4;radius:2;color:root.neons[1];opacity:.9;visible:root.motion&&x>=0&&y>=0&&x<stage.width&&y<stage.height
          }
        }
        MouseArea{id:mapInput;anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;hoverEnabled:true
          property real downX:0;property real downY:0;property real originalX:0;property real originalY:0;property bool dragged:false;property bool orbiting:false;property real originalYaw:45;property real originalTilt:35
          cursorShape:pressed?Qt.ClosedHandCursor:edgeTimer.running?Qt.SizeAllCursor:Qt.OpenHandCursor
          enabled:!root.anyModal
          onPressed:function(mouse){navigation.userTakeover();cameraTimer.stop();orbiting=mouse.button===Qt.RightButton||!!(mouse.modifiers&Qt.ShiftModifier);root.orbitDragging=orbiting;originalYaw=root.yaw;originalTilt=root.tilt;downX=mouse.x;downY=mouse.y;originalX=root.panX;originalY=root.panY;dragged=false}
          onPositionChanged:function(mouse){root.pointer=Qt.point(mouse.x,mouse.y);if(pressed&&(Math.abs(mouse.x-downX)+Math.abs(mouse.y-downY)>5)){dragged=true;if(orbiting){var c=Camera.orbit(root.currentCamera,originalYaw+(mouse.x-downX)*.35,originalTilt-(mouse.y-downY)*.22);root.yaw=c.yaw;root.tilt=c.tilt}else{root.panX=originalX+mouse.x-downX;root.panY=originalY+mouse.y-downY}}else if(Date.now()-root.hoverAt>70){root.hoverAt=Date.now();root.hoverTarget=City.hit(root.scene,(mouse.x-stage.width/2-root.panX)/root.zoom,(mouse.y-stage.height/2-root.panY)/root.zoom,root.zoom,root.orbitCamera)}}
          onExited:{root.pointer=Qt.point(-100,-100);root.hoverTarget=null}
          onReleased:function(mouse){root.orbitDragging=false;root.paint();if(!dragged){if(mouse.button===Qt.RightButton){root.resetCamera()}else root.pick(mouse.x,mouse.y)}}
          onDoubleClicked:function(mouse){root.pick(mouse.x,mouse.y);if(root.legendOpen)return;if(root.selectedBuilding)root.inspectBuilding(root.selected);else if(root.district)root.focusDistrict(root.selectedDistrict)}
          onWheel:function(wheel){var delta=wheel.pixelDelta.y?wheel.pixelDelta.y*3:wheel.angleDelta.y;if(delta){root.zoomAt(Math.pow(1.14,City.clamp(delta/120,-4,4)),wheel.x,wheel.y);wheel.accepted=true}}
        }
        Row{x:12;y:12;spacing:8
          Repeater{model:root.pinnedDistricts.slice(0,Math.max(1,Math.min(4,Math.floor(stage.width/165))))
            NeonActionV2{required property var modelData;city:root;width:150;text:"★ "+modelData.name;onClicked:root.focusDistrict(modelData.id)}
          }
        }
        NeonActionV2{city:root;visible:!!root.lens;x:12;y:60;text:"Tracing "+root.lens+"  ·  "+root.tracedBuildings.length+(root.tracedBuildings.length===1?" window   ×":" windows   ×");onClicked:{root.lens="";root.paint()}}
        Rectangle{id:hoverCard;visible:root.hoverTarget!==null&&!mapInput.pressed&&!edgeTimer.running&&!root.anyModal
          x:City.clamp(root.pointer.x+16,8,stage.width-width-8);y:City.clamp(root.pointer.y-50,60,stage.height-height-8);width:Math.min(250,hoverText.implicitWidth+24);height:36;radius:6;color:root.panelPaper;border.color:Qt.alpha(root.accent,.55)
          Text{id:hoverText;anchors.centerIn:parent;width:parent.width-20;elide:Text.ElideRight;font.pixelSize:12;color:root.ink;textFormat:Text.PlainText;text:{if(!root.hoverTarget)return "";if(root.hoverTarget.type==="group")return Groups.info(root.hoverTarget.key).name+" / Group city";if(root.hoverTarget.type==="district")return root.districtName(root.hoverTarget.key);var b=root.scene.buildings.filter(function(b){return b.key===root.hoverTarget.key})[0];return b?b.app+" / "+root.districtName(b.workspace):""}}
        }
        PaceDockV2{id:paceDock;city:root;visible:root.paceDockVisible;z:3;x:stage.width-width-12;y:12;maxHeight:stage.height-24;mini:stage.width<700
          records:root.providerMetrics;agents:root.agentRecords;activeProvider:root.providerFilter
          onProviderSelected:function(provider){root.filterProvider(provider)}
          onDetailsRequested:root.openPanel("providers")
          onHideRequested:root.saveSetting("paceDock",false)
        }
        Rectangle{id:mapPanel;x:12;y:stage.height-height-12;width:root.ui.compact?170:210;height:root.ui.compact?112:136;color:Qt.alpha(root.panelPaper,.95);border.color:Qt.alpha(root.accent,.3);radius:8
          Canvas{id:minimap;anchors.fill:parent;anchors.margins:8;onPaint:{var c=getContext("2d");c.reset();c.clearRect(0,0,width,height);var b=root.projectedBounds,s=Math.min(width/(b.maxX-b.minX+80),height/(b.maxY-b.minY+80)),cx=(b.minX+b.maxX)/2,cy=(b.minY+b.maxY)/2;c.save();c.translate(width/2,height/2);c.scale(s,s);root.scene.districts.forEach(function(d){var p=City.project(d.x,d.y,0,root.orbitCamera);c.fillStyle=d.groupColor||root.neons[d.tint||0];c.globalAlpha=d.id===root.selectedDistrict?.9:.4;c.fillRect(p.x-cx-35,p.y-cy-16,70,32)});c.globalAlpha=1;c.strokeStyle=String(root.accent);c.lineWidth=1/s;var v=root.cameraView;c.strokeRect(v.minX-cx,v.minY-cy,v.maxX-v.minX,v.maxY-v.minY);c.restore()}}
          MouseArea{id:minimapInput;anchors.fill:parent;cursorShape:Qt.PointingHandCursor;function recenter(mouse){navigation.userTakeover();var b=root.projectedBounds,s=Math.min(minimap.width/(b.maxX-b.minX+80),minimap.height/(b.maxY-b.minY+80)),sx=(mouse.x-width/2)/s+(b.minX+b.maxX)/2,sy=(mouse.y-height/2)/s+(b.minY+b.maxY)/2;root.cameraTo({x:-sx*root.zoom,y:-sy*root.zoom,zoom:root.zoom},240)}onPressed:function(mouse){recenter(mouse)}onPositionChanged:function(mouse){if(pressed)recenter(mouse)}}
        }
        Row{x:mapPanel.x+mapPanel.width+12;y:stage.height-50;spacing:7
          NeonActionV2{city:root;text:"−";width:38;onClicked:root.zoomAt(1/1.25,stage.width/2,stage.height/2)}
          NeonActionV2{city:root;text:"+";width:38;onClicked:root.zoomAt(1.25,stage.width/2,stage.height/2)}
          NeonActionV2{id:fitButton;city:root;text:"Overview";onClicked:{navigation.userTakeover();root.selected="";root.selectedDistrict=-1;root.fit()}}
          Text{anchors.verticalCenter:parent.verticalCenter;text:Math.round(root.zoom*100)+"%";font.pixelSize:12;color:Qt.alpha(root.ink,.6)}
        }
      }
      Column{x:root.ui.margin;y:25;spacing:6
        Text{text:"D I S T R I C T S";color:root.ink;font.pixelSize:root.ui.compact?27:32;font.weight:Font.Light}
        Text{text:(root.testMode&&!root.testLiveBridge?"VALIDATION FIXTURE / ":"")+City.count(root.snapshot.districts.length,"NEIGHBORHOOD","NEIGHBORHOODS")+"   /   "+City.count(root.snapshot.windows.length,"APP WINDOW","APP WINDOWS");color:Qt.alpha(root.ink,.6);font.pixelSize:11;font.letterSpacing:1}
      }
      Row{anchors.right:parent.right;anchors.rightMargin:root.ui.margin;y:28;spacing:8
        NeonActionV2{city:root;text:"Groups";onClicked:root.openLegend()}
        NeonActionV2{city:root;text:"Atlas   Ctrl K";onClicked:root.openAtlas()}
        NeonActionV2{city:root;text:"•••";onClicked:root.showSettings=!root.showSettings}
        NeonActionV2{id:minimizeButton;city:root;text:"−";width:38;onClicked:root.minimize()}
        NeonActionV2{id:maximizeButton;city:root;text:root.appMaximized?"❐":"□";width:38;onClicked:root.maximize()}
        NeonActionV2{id:closeButton;city:root;text:"Close ×";onClicked:root.close()}
      }
      Row{x:root.ui.margin;y:84;spacing:8
        NeonActionV2{id:deskButton;city:root;text:"Agent Desk";onClicked:root.openPanel("agents")}
        NeonActionV2{id:providersButton;city:root;text:"Providers";onClicked:root.openPanel("providers")}
        NeonActionV2{id:paceButton;city:root;text:root.settings.paceDock!==false?"Pace dock ✓":"Pace dock";checked:root.settings.paceDock!==false;onClicked:{root.saveSetting("paceDock",root.settings.paceDock===false);fitTimer.restart()}}
        Text{anchors.verticalCenter:parent.verticalCenter;text:root.providerFilter?"Filter: "+root.providerFilter:"";color:root.ink;font.pixelSize:12}
      }
      InspectorV2{id:inspector;city:root;x:body.width-width-root.ui.margin;y:root.ui.header;width:root.ui.sidebar;height:body.height-y-root.ui.footer}
      Rectangle{visible:root.showSettings;z:4;anchors.right:parent.right;anchors.rightMargin:root.ui.margin;y:78;width:460;height:364;radius:10;color:root.panelPaper;border.color:root.accent
        Grid{anchors.fill:parent;anchors.margins:14;columns:2;spacing:8
          NeonActionV2{id:nightButton;city:root;width:212;text:root.night?"Night circuit ✓":"Day city";onClicked:root.saveSetting("night",!root.night)}
          NeonActionV2{id:motionButton;city:root;width:212;text:root.motion?"Living motion ✓":"Reduced motion";onClicked:root.saveSetting("motion",!root.motion)}
          NeonActionV2{city:root;width:212;text:root.settings.edgePan!==false?"Edge glide ✓":"Edge glide off";onClicked:root.saveSetting("edgePan",root.settings.edgePan===false)}
          NeonActionV2{city:root;width:212;text:"Refresh live city";onClicked:{root.refresh();root.refreshAgents()}}
          NeonActionV2{city:root;width:212;text:"Reset orbit";onClicked:root.resetCamera()}
          NeonActionV2{city:root;width:212;text:"Named viewpoints";onClicked:root.openNavigation("views")}
          NeonActionV2{city:root;width:212;text:"Guided tour";onClicked:root.openNavigation("tour")}
          NeonActionV2{city:root;width:212;text:"Agent Desk";onClicked:root.openPanel("agents")}
          NeonActionV2{city:root;width:212;text:"Preview organization";enabled:!root.replaying;onClicked:root.previewOrganization()}
          NeonActionV2{city:root;width:212;text:"Owner / reported details";onClicked:root.openResources()}
          NeonActionV2{city:root;width:212;text:"Focus lens";onClicked:root.openPanel("lens")}
          NeonActionV2{city:root;width:212;text:"Activity replay";onClicked:root.openNavigation("replay")}
          NeonActionV2{id:storedAgentsAction;city:root;width:212;text:root.settings.storedAgents===true?"Stored agents visible ✓":"Show stored agents";onClicked:{if(root.saveSetting("storedAgents",root.settings.storedAgents!==true)){root.renderCurrentSnapshot();root.fit()}}}
          NeonActionV2{city:root;width:212;text:"Clear selection";onClicked:{navigation.userTakeover();root.selected="";root.selectedDistrict=-1;inspector.showInfo()}}
        }
      }
      Text{x:root.ui.margin;width:stage.width;wrapMode:Text.Wrap;anchors.bottom:parent.bottom;anchors.bottomMargin:24;text:root.ui.compact?"DRAG pan  •  RIGHT DRAG orbit / tilt  •  WHEEL zoom  •  F overview":"DRAG pan   RIGHT / SHIFT DRAG orbit + tilt   WHEEL zoom   MINIMAP travel   TAB buildings   ENTER visit";color:Qt.alpha(root.ink,.55);font.pixelSize:12}
      Text{anchors.right:parent.right;anchors.rightMargin:root.ui.margin;anchors.bottom:parent.bottom;anchors.bottomMargin:24;width:Math.min(root.ui.sidebar,body.width/3);horizontalAlignment:Text.AlignRight;elide:Text.ElideRight;font.pixelSize:11;color:root.failed?Color.urgent:Qt.alpha(root.ink,.7);text:root.message||(root.motion?"LIVE CITY / 15 FPS":"REDUCED MOTION")}
      NavigationV2{id:navigation;city:root;anchors.fill:parent;z:20;currentCamera:root.currentCamera;targetDistrict:root.selectedDistrict;districts:root.liveSnapshot.districts||[];motion:root.motion;persistenceBusy:bookmarks.running
        onCameraRequested:function(camera,target){root.restoreCamera(camera,target)}
        onTourDistrictRequested:function(id,instant){root.focusDistrict(id,true,instant)}
        onTourStopped:cameraTimer.stop()
        onReplayRequested:function(value,timestamp){root.rememberAgentDraft();root.switchingAgent=true;root.agentTarget=null;root.resourcesTarget=null;root.resourcesResult=null;root.resourcesError="";root.sessionReply=null;sessionReplyIdentity="";root.sessionMessage="";root.sessionDraft="";root.switchingAgent=false;root.panel="";root.organizePlan=null;root.organizeReceipt=null;root.selected="";root.selectedDistrict=-1;root.renderSnapshot(value,value.agents||[])}
        onLiveRequested:{root.selected="";root.selectedDistrict=-1;root.rememberAgentDraft();root.switchingAgent=true;root.agentTarget=null;root.resourcesTarget=null;root.sessionReply=null;sessionReplyIdentity="";root.sessionDraft="";root.switchingAgent=false;if(root.testMode&&!root.testLiveBridge)root.renderSnapshot(root.liveSnapshot,root.agentRecords);else{root.awaitingLive=true;root.message="Refreshing current desktop metadata…";root.renderSnapshot({schema:1,boroughs:[],districts:[],windows:[]},[])}root.refresh();root.refreshAgents()}
        onPersistenceRequested:function(request){root.persistView(request)}
      }
      Row{visible:navigation.touring||root.replaying||!!root.focusLens;width:stage.width-24;x:root.ui.margin;y:root.ui.header+58;spacing:8;z:5
        Text{width:parent.width-120;wrapMode:Text.Wrap;anchors.verticalCenter:parent.verticalCenter;color:root.accent;font.pixelSize:12;text:root.replaying?"HISTORY / "+navigation.timeLabel(navigation.replayFrame?navigation.replayFrame.timestamp:0):navigation.touring?"TOUR / "+navigation.tourMessage:"LENS / "+(root.focusLens?root.focusLens.label:"")}
        NeonActionV2{city:root;text:root.replaying?"Return live":navigation.touring?"Stop tour":"Clear lens";onClicked:{if(root.replaying)navigation.returnLive();else if(navigation.touring)navigation.stopTour("Tour stopped");else{root.focusLens=null;root.renderCurrentSnapshot();root.fit()}}}
      }
      Item{anchors.fill:parent;visible:root.panel==="lens"||root.panel==="resources"||root.panel==="agents"||root.panel==="providers";z:18
        Rectangle{anchors.fill:parent;color:"#ac020712"}
        MouseArea{anchors.fill:parent;onClicked:{if(root.panel==="agents")root.rememberAgentDraft();root.panel=""}}
        Rectangle{anchors.centerIn:parent;width:Math.min(root.panel==="providers"?1200:760,parent.width-32);height:Math.min(root.panel==="providers"?820:610,parent.height-32);color:root.panelPaper;radius:14;MouseArea{anchors.fill:parent}
          LensV2{id:lensPane;anchors.fill:parent;visible:root.panel==="lens";city:root;snapshot:Object.assign({},root.viewSource,{agents:root.replaying?(root.viewSource.agents||[]):root.agentRecords});selectedWindow:root.selectedBuilding;selectedDistrict:root.district;lens:root.focusLens
            onSelected:function(value){root.focusLens=FocusLens.normalize(value);root.panel="";root.renderCurrentSnapshot();root.fit()}
            onCleared:{root.focusLens=null;root.panel="";root.renderCurrentSnapshot();root.fit()}
            onClosed:root.panel=""
          }
          ResourcesV2{id:resourcesPane;anchors.fill:parent;visible:root.panel==="resources";city:root;details:root.resourcesResult;reported:root.resourcesTarget&&root.resourcesTarget.agent?root.resourcesTarget.agent:null;cpu:root.resourcesTarget?root.resourcesTarget.ownerCpu:null;targetLabel:root.resourcesTarget?root.resourcesTarget.app:"Select a building";busy:resources.running;error:root.resourcesError;onRefreshRequested:root.readResources();onClosed:root.panel=""}
          ProviderLegendV2{id:providerPane;anchors.fill:parent;visible:root.panel==="providers";city:root;records:root.replaying?[]:root.providerMetrics;agents:root.replaying?[]:root.agentRecords;onRefreshRequested:root.refreshProviderMetrics();activeProvider:root.providerFilter;onProviderSelected:function(provider){root.filterProvider(provider)};onClosed:root.panel=""}
          AgentV2{id:agentPane;anchors.fill:parent;availableAgents:root.deskAgents;providerFilter:root.providerFilter;replyIdentity:root.sessionReplyIdentity;visible:root.panel==="agents";city:root;selectedAgent:root.agentTarget;reply:root.sessionReply||({text:"",source:"Select Read latest reply to fetch this session only."});draft:root.sessionDraft;busy:sessions.running;message:root.submissionCapacity?"16 submission identities retained. Select a retained draft and edit it to release its previous identity.":root.sessionMessage||root.inventoryMessage;submissionAvailable:!root.submissionCapacity;inventoryNotices:root.inventoryNotices
            onDraftEdited:function(text){root.sessionDraft=text;root.rememberAgentDraft()}
            onPendingMessageIdChanged:root.rememberAgentDraft()
            onRequestSelect:function(agent){root.selectAgent(agent)}
            onRequestRead:function(agent){root.readAgent(agent)}
            onRequestSend:function(agent,text,messageId){root.sendAgent(agent,text,messageId)}
            onRequestOpen:function(agent){root.openAgentNative(agent)}
            onClosed:root.panel=""
          }
        }
      }
      OrganizeV2{id:organizer;city:root;anchors.fill:parent;z:19;plan:root.organizePlan;receipt:root.organizeReceipt;busy:organization.running;error:root.organizeError;visible:root.panel==="organize";onApplyRequested:function(planId){root.applyOrganization(planId)}
        onCancelRequested:if(!organization.running)root.panel=""
        onRefreshRequested:root.previewOrganization()}
      AtlasV2{id:atlas;city:root;anchors.fill:parent;z:6}
      LegendV2{id:legend;city:root;anchors.fill:parent;z:8}
      MoveV2{id:moveModal;city:root;anchors.fill:parent;z:7}
  }
}
