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

Item {
  id: root
  property QtObject bar: null
  property var shell: null
  property var settings: ({})
  property string moduleName: "nixfred.districts"
  property bool opened: false
  property bool testMode: false
  property bool testLiveBridge: false
  property bool testMetadataIO: false
  property size testViewport: Qt.size(0,0)
  property int fixtureMoves: 0
  property bool legendOpen: false
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
  readonly property var ui: Camera.metrics(body.width,body.height)
  readonly property var cameraView: Camera.view({x:panX,y:panY,zoom:zoom},stage.width,stage.height)
  readonly property bool metadataBusy: metadata.running
  readonly property bool actionBusy: action.running
  readonly property var neons: ["#57dfff","#fc69d5","#b99cff","#b0fca9","#ffcd78"]
  readonly property color panelPaper: night?"#10182c":"#e9f0f6"
  readonly property var tracedBuildings: scene.buildings.filter(function(b){return !b.dying&&(!lens||b.appClass===lens)})
  readonly property var pinnedDistricts: scene.districts.filter(function(d){return d.pinned})
  readonly property var atlasResults: {
    var q=queryText.trim().toLowerCase(),out=[]
    scene.districts.slice().sort(function(a,b){return Number(b.pinned)-Number(a.pinned)||a.id-b.id}).forEach(function(d){if(!q||(d.name+" district "+d.id).toLowerCase().indexOf(q)>=0)out.push({type:"district",key:d.id,label:d.name,subtitle:"D"+d.id+" · "+d.count+(d.count===1?" window":" windows")})})
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
  readonly property var currentBuildings: scene.buildings.filter(function(b){return !b.dying&&(selectedDistrict<0||b.workspace===selectedDistrict)})
  implicitWidth: 30
  implicitHeight: bar ? bar.barSize : 28

  function saveSetting(key,value) {
    var next=Object.assign({},settings);next[key]=value
    var api=bar&&bar.shell?bar.shell:shell
    if(!testMode && (!api || !api.updateEntryInline || !api.updateEntryInline(moduleName,next))){message="Setting could not be saved.";return false}
    settings=next;paint();return true
  }
  function open() {
    if(opened)return
    navigating=false
    var monitor=Hyprland.focusedMonitor,screens=Quickshell.screens
    selectedScreen=null
    for(var i=0;i<screens.length;i++)if(monitor&&screens[i].name===monitor.name)selectedScreen=screens[i]
    if(!selectedScreen&&screens.length)selectedScreen=screens[0]
    opened=true;failed=false;message="";hasFitted=false
    refresh();fitTimer.restart();Qt.callLater(function(){if(!testMode)body.forceActiveFocus()})
  }
  function close() {opened=false;legendOpen=false;showSettings=false;atlasOpen=false;nameEditing=false;moveDraft=null;cameraTimer.stop();pointer=Qt.point(-100,-100)}
  function toggle() {if(opened)close();else open()}
  function refresh() {
    if((testMode&&!testLiveBridge)||!opened)return
    if(collector.running){collector.write("refresh\n");return}
    collector.command=["python3","-B",helper,"watch"];collector.running=true
  }
  function ingest(value) {
    if(!value||value.schema!==1||!Array.isArray(value.windows)||!Array.isArray(value.districts)){failed=true;message="City data unavailable. Refresh to reconnect.";return}
    if(value.grouping&&Number(value.grouping.revision)>=groupingPreferences.revision)groupingPreferences=Groups.preferences(value.grouping)
    value=Groups.enrich(value,groupHistory,value.activityTime===undefined?Date.now():Number(value.activityTime),groupingPreferences)
    var signature=JSON.stringify([value.boroughs,value.districts,value.windows,value.focused])
    updateCount++;failed=false;message=""
    if(signature===sceneSignature){snapshot=value;if(!hasFitted&&opened)fitTimer.restart();return}
    sceneSignature=signature;sceneBuildCount++
    var next=City.layout(value)
    var old={};scene.buildings.forEach(function(b){old[b.key]=b})
    var changed=next.buildings.some(function(b){return !old[b.key]||old[b.key].targetX!==b.x||old[b.key].targetY!==b.y})||scene.buildings.some(function(b){return !next.buildings.some(function(n){return n.key===b.key})})
    snapshot=value;scene=City.transition(scene,next,motion,Date.now())
    if(changed)transitionsUntil=Date.now()+850
    if(selected&&!selectedBuilding)selected=""
    if(selectedDistrict>=0&&!district)selectedDistrict=-1
    if(!hasFitted&&opened)fitTimer.restart()
    failed=false;message="";paint()
  }
  function paint(){if(opened){cityCanvas.requestPaint();minimap.requestPaint()}}
  function cameraTo(value,duration) {
    cameraTimer.stop()
    if(!motion){panX=value.x;panY=value.y;zoom=value.zoom;paint();return}
    cameraFrom={x:panX,y:panY,zoom:zoom};cameraTarget=value;cameraAt=Date.now();cameraDuration=duration||420;cameraTimer.start()
  }
  function fit() {
    var bounds=Object.assign({},scene.bounds)
    scene.boroughs.forEach(function(b){var p=City.project(b.x,b.y);bounds.minX=Math.min(bounds.minX,p.x-110);bounds.maxX=Math.max(bounds.maxX,p.x+110);bounds.minY=Math.min(bounds.minY,p.y-35)})
    cameraTo(Camera.fit(bounds,stage.width,stage.height,0));hasFitted=true
  }
  function districtName(id){for(var i=0;i<scene.districts.length;i++)if(scene.districts[i].id===id)return scene.districts[i].name;return "District "+id}
  function focusDistrict(id) {
    nameEditing=false;selectedDistrict=id;selected="";inspector.showInfo()
    for(var i=0;i<scene.districts.length;i++)if(scene.districts[i].id===id){var p=City.project(scene.districts[i].x,scene.districts[i].y,20),z=City.clamp(Math.min(stage.width/440,stage.height/330),1.1,3.3);cameraTo({x:-p.x*z,y:-p.y*z+28,zoom:z});return}
  }
  function inspectBuilding(key) {
    nameEditing=false;selected=String(key);inspector.showInfo()
    if(selectedBuilding){if(lens&&lens!==selectedBuilding.appClass)lens="";selectedDistrict=selectedBuilding.workspace;var p=City.project(selectedBuilding.x,selectedBuilding.y,selectedBuilding.height/2),z=Math.max(zoom,Math.min(3.6,stage.height/210));cameraTo({x:-p.x*z,y:-p.y*z,zoom:z})}
    paint()
  }
  function inspectResult(result){closeAtlas();if(result.type==="district")focusDistrict(result.key);else inspectBuilding(result.key)}
  function openAtlas(){legendOpen=false;nameEditing=false;moveDraft=null;atlasOpen=true;queryText="";pointer=Qt.point(-100,-100)}
  function closeAtlas(){atlasOpen=false;body.forceActiveFocus()}
  function zoomAt(factor,x,y){var base=cameraTimer.running?cameraTarget:{x:panX,y:panY,zoom:zoom};cameraTo(Camera.anchored(base,factor,x,y,stage.width,stage.height),160)}
  function traceApp(){lens=selectedBuilding?(lens?"":selectedBuilding.appClass):"";inspector.showList();paint()}
  function beginRename(){if(!district||metadataBusy)return;renameWorkspace=district.id;renameDraft=district.customName||"";nameEditing=true;pointer=Qt.point(-100,-100)}
  function cancelRename(){if(metadataBusy)return;nameEditing=false;renameDraft="";body.forceActiveFocus()}
  function saveRename(){if(nameEditing&&renameWorkspace>0)customize({name:renameDraft},renameWorkspace)}
  function customize(fields,workspace) {
    if(metadataBusy)return false
    var wid=workspace||selectedDistrict;if(wid<1)return false
    metadataContext={workspace:wid,fields:fields};metadataResult=null
    var args=["python3","-B",helper,"customize",String(wid)]
    if(fields.name!==undefined)args=args.concat(["--name",String(fields.name)])
    if(fields.pinned!==undefined)args=args.concat(["--pinned",fields.pinned?"true":"false"])
    if(fields.tint!==undefined)args=args.concat(["--tint",String(fields.tint)])
    if(testMode&&!testMetadataIO){applyCustomization(metadataContext);return true}
    metadata.command=args;metadata.running=true;return true
  }
  function applyCustomization(context){var value=JSON.parse(JSON.stringify(snapshot));value.districts.forEach(function(d){if(d.id===context.workspace)Object.keys(context.fields).forEach(function(k){if(k==="name"){d.customName=context.fields[k];d.name=context.fields[k]||d.autoName||City.activityName(value,d.id);d.nameSource=context.fields[k]?"custom":d.autoSource||"apps"}else d[k]=context.fields[k]})});ingest(value);nameEditing=false;message="District saved";if(opened)body.forceActiveFocus()}
  function beginMove(){legendOpen=false;if(!selectedBuilding||actionBusy)return;var b=selectedBuilding;moveDraft={address:b.address,app:b.app,appClass:b.appClass,sourceWorkspace:b.workspace,destination:-1};pointer=Qt.point(-100,-100)}
  function chooseDestination(id){if(moveDraft)moveDraft=Object.assign({},moveDraft,{destination:id})}
  function cancelMove(){moveDraft=null;body.forceActiveFocus()}
  function validMove(){return !!moveDraft&&moveDraft.destination>0&&moveDraft.destination!==moveDraft.sourceWorkspace&&!actionBusy&&!failed&&scene.districts.some(function(d){return d.id===root.moveDraft.destination})}
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
  function openLegend(){if(metadataBusy)return;nameEditing=false;atlasOpen=false;moveDraft=null;showSettings=false;legendOpen=true;pointer=Qt.point(-100,-100)}
  function closeLegend(){legendOpen=false;body.forceActiveFocus()}
  function updateGrouping(fields){
    if(groupingBusy)return
    groupingMessage="";groupingResult=null
    var args=["python3","-B",helper,"group"]
    if(fields.group!==undefined)args=args.concat(["--group",fields.group,"--color",String(fields.color)])
    if(fields.app!==undefined)args=args.concat(["--app",String(fields.app),"--rule",fields.rule])
    groupingProcess.command=args;groupingProcess.running=true
  }
  function dismiss(){if(legendOpen)closeLegend();else if(moveDraft)cancelMove();else if(atlasOpen)closeAtlas();else if(nameEditing)cancelRename();else close()}
  function pick(x,y) {
    var hit=City.hit(scene,(x-stage.width/2-panX)/zoom,(y-stage.height/2-panY)/zoom,zoom)
    if(!hit){selected="";paint();return}
    if(hit.type==="group"){openLegend();legend.editColor(hit.key);return}
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
    return JSON.stringify({version:"2.2.0",opened:opened,districts:scene.districts.length,buildings:snapshot.windows.length,
      selected:!!selectedBuilding,selectedDistrict:selectedDistrict,motion:motion,night:night,frames:frameCount,updates:updateCount,
      zoom:zoom,failed:failed,collector:collector.running,navigating:navigating,standalone:true,sceneBuilds:sceneBuildCount,viewport:[body.width,body.height],mapped:window.backingWindowVisible,screen:selectedScreen?selectedScreen.name:"automatic",cameraRunning:cameraTimer.running,edgeRunning:edgeTimer.running,legend:legendOpen,groupingBusy:groupingBusy,groups:(scene.groups||[]).length,atlas:atlasOpen,renaming:nameEditing,moving:moveDraft!==null,metadataBusy:metadataBusy,fixtureMoves:fixtureMoves,viewportLogical:[body.width,body.height],mapViewport:[stage.width,stage.height],canvasPhysicalPixels:Math.round(cityCanvas.width*cityCanvas.height*Screen.devicePixelRatio*Screen.devicePixelRatio)})
  }
  function capture(path,scale) {var ok=body.grabToImage(function(result){console.log("CAPTURE "+path+" "+result.saveToFile(path))},Qt.size(body.width*(scale||1),body.height*(scale||1)));console.log("GRAB "+path+" "+ok);return ok}
  onOpenedChanged: {if(!opened){collector.running=false;eventTimer.stop();fitTimer.stop();cameraTimer.stop()}}
  onPanXChanged:paint()
  onPanYChanged:paint()
  onZoomChanged:paint()
  onMotionChanged: {if(!motion){if(cameraTimer.running){cameraTimer.stop();panX=cameraTarget.x;panY=cameraTarget.y;zoom=cameraTarget.zoom}City.advance(scene,Date.now(),false);scene=Object.assign({},scene)}paint()}
  onPaletteChanged:paint()

  Process {
    id:collector
    stdinEnabled:true
    stdout:SplitParser {onRead:function(line){try{var data=JSON.parse(line);if(data.error){root.failed=true;root.message=data.error}else if(root.opened)root.ingest(data)}catch(e){root.failed=true;root.message="Desktop did not answer. Refresh to reconnect."}}}
    onExited:function(code){if(code!==0&&root.opened){root.failed=true;if(!root.message)root.message="Desktop unavailable."}}
  }
  Process {
    id:action
    stdout:StdioCollector{onStreamFinished:{try{root.actionResult=JSON.parse(text)}catch(e){root.actionResult={ok:false,error:"Action could not complete."}}}}
    onExited:function(code){root.navigating=false;var result=root.actionResult;if(!result||!result.ok||code!==0){root.message=result&&result.error?result.error:"Action could not complete."}else if(root.actionKind==="relocate"){root.selectedDistrict=root.actionContext.destination;root.message="Building relocated";root.refresh()}}
  }
  Process{
    id:groupingProcess
    stdout:StdioCollector{onStreamFinished:{try{root.groupingResult=JSON.parse(text)}catch(e){root.groupingResult=null}}}
    onExited:function(code){if(code===0&&root.groupingResult&&root.groupingResult.ok){root.groupingPreferences=Groups.preferences(root.groupingResult.grouping);var value=Object.assign({},root.snapshot,{grouping:root.groupingPreferences});root.ingest(value);root.groupingMessage="Grouping saved";if(root.opened)root.refresh()}else root.groupingMessage=root.groupingResult&&root.groupingResult.error?root.groupingResult.error:"Grouping could not be saved."}
  }
  Process{
    id:metadata
    stdout:StdioCollector{onStreamFinished:{try{root.metadataResult=JSON.parse(text)}catch(e){root.metadataResult=null}}}
    onExited:function(code){if(code===0&&root.metadataResult&&root.metadataResult.ok){root.applyCustomization(root.metadataContext);root.refresh()}else root.message=root.metadataResult&&root.metadataResult.error?root.metadataResult.error:"District could not be saved."}
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
      if(root.opened&&["workspace","workspacev2","focusedmon","focusedmonv2","activewindow","activewindowv2","openwindow","closewindow","movewindow","movewindowv2","changeworkspaceid","renameworkspace","monitoradded","monitorremoved","fullscreen"].indexOf(name)>=0)eventTimer.restart()
    }
  }
  Timer{id:eventTimer;interval:180;onTriggered:root.refresh()}
  IdleMonitor{id:idle;timeout:60;respectInhibitors:false;onIsIdleChanged:{if(root.testMode)return;if(isIdle){collector.running=false;root.message="City paused while idle"}else if(root.opened)root.refresh()}}
  IdleInhibitor{window:window;enabled:root.testMode&&root.opened}
  Timer{id:fitTimer;interval:150;onTriggered:if(root.opened)root.fit()}
  Timer{id:cameraTimer;interval:33;repeat:true;running:false;onTriggered:{if(!root.opened){stop();return}var t=(Date.now()-root.cameraAt)/root.cameraDuration,c=Camera.interpolate(root.cameraFrom,root.cameraTarget,t);root.panX=c.x;root.panY=c.y;root.zoom=c.zoom;if(t>=1)stop()}}
  Timer{id:edgeTimer;interval:33;repeat:true;running:root.opened&&root.settings.edgePan!==false&&(root.testMode||!idle.isIdle)&&mapInput.containsMouse&&root.pointer.x>=0&&root.pointer.y>=0&&root.pointer.x<=stage.width&&root.pointer.y<=stage.height&&!mapInput.pressed&&!root.legendOpen&&!root.atlasOpen&&!root.nameEditing&&!root.moveDraft&&!root.showSettings&&!cameraTimer.running&&(root.pointer.x<48||root.pointer.x>stage.width-48||root.pointer.y<48||root.pointer.y>stage.height-48)
    onTriggered:{var p=root.pointer;if(p.x<0||p.y<0||p.x>stage.width||p.y>stage.height)return;cameraTimer.stop();var dx=p.x<48?(48-p.x)/48:p.x>stage.width-48?-(p.x-stage.width+48)/48:0,dy=p.y<48?(48-p.y)/48:p.y>stage.height-48?-(p.y-stage.height+48)/48:0;root.panX+=City.clamp(dx,-1,1)*11;root.panY+=City.clamp(dy,-1,1)*11}}

  Timer{id:animationTimer;interval:66;repeat:true;running:root.opened&&root.motion&&(!idle.isIdle||root.testMode);onTriggered:{root.clock+=.066;if(Date.now()<root.transitionsUntil){root.transitionClock=root.clock;var count=root.scene.buildings.length;City.advance(root.scene,Date.now(),true);if(count!==root.scene.buildings.length)root.scene=Object.assign({},root.scene);paint()}root.frameCount++}}
  IpcHandler {
    target:"nixfred.districts"
    function open():void {root.open()}
    function close():void {root.close()}
    function toggle():void {root.toggle()}
    function refresh():void {root.refresh()}
    function status():string {return root.status()}
  }

  WidgetButton {
    id:button;anchors.fill:parent;bar:root.bar;labelVisible:false;hasVisualContent:true;fixedWidth:32
    tooltipText:"Districts · Your desktop city\n"+(root.message&&!root.opened?root.message:"Click to explore")
    onPressed:function(b){if(b===Qt.LeftButton)root.toggle()}
    Canvas{id:skyline;anchors.centerIn:parent;width:25;height:23;onPaint:{var c=getContext("2d");c.reset();c.fillStyle=String(Color.accent);c.strokeStyle=String(Color.accent);c.lineWidth=1.1;City.polygon(c,[{x:1,y:21},{x:1,y:11},{x:4,y:8},{x:7,y:11},{x:7,y:21}],String(Color.accent));City.polygon(c,[{x:9,y:21},{x:9,y:5},{x:12,y:3},{x:15,y:5},{x:15,y:21}],String(Color.accent));City.polygon(c,[{x:17,y:21},{x:17,y:13},{x:21,y:11},{x:24,y:13},{x:24,y:21}],String(Color.accent));c.beginPath();c.moveTo(12,4);c.lineTo(12,0);c.stroke();c.clearRect(3,13,2,2);c.clearRect(11,8,2,2);c.clearRect(11,13,2,2);c.clearRect(19,15,2,2);c.beginPath();c.moveTo(0,22);c.lineTo(25,22);c.stroke()}}
    Connections{target:Color;function onAccentChanged(){skyline.requestPaint()}}
  }
  PanelWindow {
    id:window
    screen:root.selectedScreen
    anchors{top:true;bottom:true;left:true;right:true}
    color:"transparent";visible:root.opened;exclusionMode:ExclusionMode.Ignore
    WlrLayershell.namespace:"omarchy-districts";WlrLayershell.layer:WlrLayer.Overlay
    WlrLayershell.keyboardFocus:root.opened&&!root.testMode?WlrKeyboardFocus.Exclusive:WlrKeyboardFocus.None
    mask:Region {item:root.testMode?null:body}
    Item {
      id:body;width:root.testMode&&root.testViewport.width>0?root.testViewport.width:parent.width;height:root.testMode&&root.testViewport.height>0?root.testViewport.height:parent.height;focus:true
      Keys.onEscapePressed:root.dismiss()
      Keys.onPressed:function(event){
        if(root.nameEditing||root.legendOpen||root.atlasOpen||root.moveDraft)return
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
          onPaint:{var c=getContext("2d");c.reset();c.clearRect(0,0,width,height);c.save();c.scale(rasterScale,rasterScale);c.translate(stage.width/2+root.panX,stage.height/2+root.panY);c.scale(root.zoom,root.zoom);City.draw(c,root.scene,root.palette,root.selected,root.selectedDistrict,root.clock,false,root.zoom,root.cameraView,root.lens);c.restore()}
        }
        Repeater{model:root.opened?root.scene.buildings:[]
          Item{required property var modelData
            readonly property var pt:{var tick=root.transitionClock;return City.project(modelData.x,modelData.y,modelData.height*modelData.growth+3)}
            x:stage.width/2+root.panX+pt.x*root.zoom-10;y:stage.height/2+root.panY+pt.y*root.zoom-13
            width:20;height:20;visible:root.zoom>.7&&!modelData.dying&&x>-24&&y>-24&&x<stage.width&&y<stage.height
            opacity:{var tick=root.transitionClock;return modelData.growth*(root.lens&&root.lens!==modelData.appClass?.22:1)}
            Image{anchors.fill:parent;source:parent.visible?Quickshell.iconPath(parent.modelData.icon,true):"";sourceSize:Qt.size(40,40);fillMode:Image.PreserveAspectFit;asynchronous:true}
          }
        }
        Repeater{model:root.opened?root.scene.roads.slice(0,64):[]
          Rectangle{required property var modelData;readonly property real t:(root.clock*.07+(modelData.seed%100)/100)%1
            x:stage.width/2+root.panX+City.mix(modelData.a.x,modelData.b.x,t)*root.zoom-2;y:stage.height/2+root.panY+City.mix(modelData.a.y,modelData.b.y,t)*root.zoom-2
            width:4;height:4;radius:2;color:root.neons[1];opacity:.9;visible:root.motion&&x>=0&&y>=0&&x<stage.width&&y<stage.height
          }
        }
        MouseArea{id:mapInput;anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;hoverEnabled:true
          property real downX:0;property real downY:0;property real originalX:0;property real originalY:0;property bool dragged:false
          cursorShape:pressed?Qt.ClosedHandCursor:edgeTimer.running?Qt.SizeAllCursor:Qt.OpenHandCursor
          onPressed:function(mouse){cameraTimer.stop();downX=mouse.x;downY=mouse.y;originalX=root.panX;originalY=root.panY;dragged=false}
          onPositionChanged:function(mouse){root.pointer=Qt.point(mouse.x,mouse.y);if(pressed&&(Math.abs(mouse.x-downX)+Math.abs(mouse.y-downY)>5)){dragged=true;root.panX=originalX+mouse.x-downX;root.panY=originalY+mouse.y-downY}else if(Date.now()-root.hoverAt>70){root.hoverAt=Date.now();root.hoverTarget=City.hit(root.scene,(mouse.x-stage.width/2-root.panX)/root.zoom,(mouse.y-stage.height/2-root.panY)/root.zoom,root.zoom)}}
          onExited:{root.pointer=Qt.point(-100,-100);root.hoverTarget=null}
          onReleased:function(mouse){if(!dragged){if(mouse.button===Qt.RightButton){root.selected="";root.selectedDistrict=-1;root.fit()}else root.pick(mouse.x,mouse.y)}}
          onDoubleClicked:function(mouse){root.pick(mouse.x,mouse.y);if(root.legendOpen)return;if(root.selectedBuilding)root.inspectBuilding(root.selected);else if(root.district)root.focusDistrict(root.selectedDistrict)}
          onWheel:function(wheel){var delta=wheel.pixelDelta.y?wheel.pixelDelta.y*3:wheel.angleDelta.y;if(delta){root.zoomAt(Math.pow(1.14,City.clamp(delta/120,-4,4)),wheel.x,wheel.y);wheel.accepted=true}}
        }
        Row{x:12;y:12;spacing:8
          Repeater{model:root.pinnedDistricts.slice(0,Math.max(1,Math.min(4,Math.floor(stage.width/165))))
            NeonActionV2{required property var modelData;city:root;width:150;text:"★ "+modelData.name;onClicked:root.focusDistrict(modelData.id)}
          }
        }
        NeonActionV2{city:root;visible:!!root.lens;x:12;y:60;text:"Tracing "+root.lens+"  ·  "+root.tracedBuildings.length+(root.tracedBuildings.length===1?" window   ×":" windows   ×");onClicked:{root.lens="";root.paint()}}
        Rectangle{id:hoverCard;visible:root.hoverTarget!==null&&!mapInput.pressed&&!edgeTimer.running&&!root.legendOpen&&!root.atlasOpen&&!root.nameEditing&&!root.moveDraft
          x:City.clamp(root.pointer.x+16,8,stage.width-width-8);y:City.clamp(root.pointer.y-50,60,stage.height-height-8);width:Math.min(250,hoverText.implicitWidth+24);height:36;radius:6;color:root.panelPaper;border.color:Qt.alpha(root.accent,.55)
          Text{id:hoverText;anchors.centerIn:parent;width:parent.width-20;elide:Text.ElideRight;font.pixelSize:12;color:root.ink;textFormat:Text.PlainText;text:{if(!root.hoverTarget)return "";if(root.hoverTarget.type==="group")return Groups.info(root.hoverTarget.key).name+" / Group city";if(root.hoverTarget.type==="district")return root.districtName(root.hoverTarget.key);var b=root.scene.buildings.filter(function(b){return b.key===root.hoverTarget.key})[0];return b?b.app+" / "+root.districtName(b.workspace):""}}
        }
        Rectangle{id:mapPanel;x:12;y:stage.height-height-12;width:root.ui.compact?170:210;height:root.ui.compact?112:136;color:Qt.alpha(root.panelPaper,.95);border.color:Qt.alpha(root.accent,.3);radius:8
          Canvas{id:minimap;anchors.fill:parent;anchors.margins:8;onPaint:{var c=getContext("2d");c.reset();c.clearRect(0,0,width,height);var b=root.scene.bounds,s=Math.min(width/(b.maxX-b.minX+80),height/(b.maxY-b.minY+80)),cx=(b.minX+b.maxX)/2,cy=(b.minY+b.maxY)/2;c.save();c.translate(width/2,height/2);c.scale(s,s);root.scene.districts.forEach(function(d){var p=City.project(d.x,d.y);c.fillStyle=d.groupColor||root.neons[d.tint||0];c.globalAlpha=d.id===root.selectedDistrict?.9:.4;c.fillRect(p.x-cx-35,p.y-cy-16,70,32)});c.globalAlpha=1;c.strokeStyle=String(root.accent);c.lineWidth=1/s;var v=root.cameraView;c.strokeRect(v.minX-cx,v.minY-cy,v.maxX-v.minX,v.maxY-v.minY);c.restore()}}
          MouseArea{id:minimapInput;anchors.fill:parent;cursorShape:Qt.PointingHandCursor;function recenter(mouse){var b=root.scene.bounds,s=Math.min(minimap.width/(b.maxX-b.minX+80),minimap.height/(b.maxY-b.minY+80)),sx=(mouse.x-width/2)/s+(b.minX+b.maxX)/2,sy=(mouse.y-height/2)/s+(b.minY+b.maxY)/2;root.cameraTo({x:-sx*root.zoom,y:-sy*root.zoom,zoom:root.zoom},240)}onPressed:function(mouse){recenter(mouse)}onPositionChanged:function(mouse){if(pressed)recenter(mouse)}}
        }
        Row{x:mapPanel.x+mapPanel.width+12;y:stage.height-50;spacing:7
          NeonActionV2{city:root;text:"−";width:38;onClicked:root.zoomAt(1/1.25,stage.width/2,stage.height/2)}
          NeonActionV2{city:root;text:"+";width:38;onClicked:root.zoomAt(1.25,stage.width/2,stage.height/2)}
          NeonActionV2{id:fitButton;city:root;text:"Overview";onClicked:{root.selected="";root.selectedDistrict=-1;root.fit()}}
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
        NeonActionV2{city:root;text:"Leave  ×";onClicked:root.close()}
      }
      InspectorV2{id:inspector;city:root;x:body.width-width-root.ui.margin;y:root.ui.header;width:root.ui.sidebar;height:body.height-y-root.ui.footer}
      Rectangle{visible:root.showSettings;z:4;anchors.right:parent.right;anchors.rightMargin:root.ui.margin;y:78;width:270;height:218;radius:10;color:root.panelPaper;border.color:root.accent
        Column{anchors.fill:parent;anchors.margins:14;spacing:10
          NeonActionV2{id:nightButton;city:root;width:parent.width;text:root.night?"Night circuit  ✓":"Day city";onClicked:root.saveSetting("night",!root.night)}
          NeonActionV2{id:motionButton;city:root;width:parent.width;text:root.motion?"Living motion  ✓":"Reduced motion";onClicked:root.saveSetting("motion",!root.motion)}
          NeonActionV2{city:root;width:parent.width;text:root.settings.edgePan!==false?"Edge glide  ✓":"Edge glide off";onClicked:root.saveSetting("edgePan",root.settings.edgePan===false)}
          NeonActionV2{city:root;width:parent.width;text:"Refresh live city";onClicked:root.refresh()}
        }
      }
      Text{x:root.ui.margin;width:stage.width;wrapMode:Text.Wrap;anchors.bottom:parent.bottom;anchors.bottomMargin:24;text:root.ui.compact?"DRAG / EDGE  pan   •   WHEEL  zoom   •   F  overview   •   ESC  leave":"DRAG / EDGE  pan     WHEEL  zoom     MINIMAP  travel     TAB  buildings     N  name     ENTER  visit";color:Qt.alpha(root.ink,.55);font.pixelSize:12}
      Text{anchors.right:parent.right;anchors.rightMargin:root.ui.margin;anchors.bottom:parent.bottom;anchors.bottomMargin:24;width:Math.min(root.ui.sidebar,body.width/3);horizontalAlignment:Text.AlignRight;elide:Text.ElideRight;font.pixelSize:11;color:root.failed?Color.urgent:Qt.alpha(root.ink,.7);text:root.message||(root.motion?"LIVE CITY / 15 FPS":"REDUCED MOTION")}
      AtlasV2{id:atlas;city:root;anchors.fill:parent;z:6}
      LegendV2{id:legend;city:root;anchors.fill:parent;z:8}
      MoveV2{id:moveModal;city:root;anchors.fill:parent;z:7}
    }
  }
}
