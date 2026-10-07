"""Native Wayland TextArea boundary regressions; no real session I/O or global keys."""
import json
import subprocess
from native_session import NativeSession, ROOT, clean_log

qml='''import QtQuick
import Quickshell
import Quickshell.Io
import QtTest
import "SOURCE" as Source
ShellRoot {
 QtObject{id:theme;property color ink:"#eeeeee";property color accent:"#33ccdd";property color panelPaper:"#202025"}
 FloatingWindow{id:window;title:"Districts · Fixture";visible:true;implicitWidth:1100;implicitHeight:700
  Item{id:body;anchors.fill:parent
   Source.AgentV2{id:pane;city:theme;width:912;height:512
    property bool tinyPages:true
    function paginate(value,columns,rows){return splitPages(value,tinyPages?2:columns,tinyPages?1:rows)}
    selectedAgent:({id:"11111111-1111-4111-8111-111111111111",provider:"codex",label:"Codex CLI fixture",availability:"live",status:{type:"idle",activeFlags:[]},statusSource:"Controlled fixture metadata",capabilities:{canReadReply:true,canSend:true,canOpen:false,reason:"Exact fixture queue."}})
   }
   TestCase{id:qa;parent:body;name:"AgentNativeBoundaries";when:false
    property string sentText:""
    property string closedText:""
    property bool staleCallbackIsolated:false
    function check(a,b,label){if(a!==b){console.log("MISMATCH "+label+" actual="+JSON.stringify(a)+" expected="+JSON.stringify(b));throw new Error("CHECKFAILED "+label)}}
    function assert(a,label){if(!a){console.log("ASSERTFAIL "+label);throw new Error("ASSERTFAILED "+label)}}
    function press(item){mouseClick(item,item.width/2,item.height/2);wait(30)}
    function prepare(value){pane.editScheduled=false;pane.draft=value;pane.view="draft";pane.showNotices=false;wait(30);pane.syncDraftAtCursor(value.length);pane.testDraft.forceActiveFocus();wait(20)}
    function queueValue(value){pane.syncingEditor=true;pane.testDraft.text=value;pane.syncingEditor=false;pane.queueEditorChange();assert(pane.editScheduled,"Native editor edit is queued before boundary");}
    function type(key){keyClick(key);wait(30)}
    function test_editor(){
     var original=JSON.parse(JSON.stringify(pane.selectedAgent)),other=JSON.parse(JSON.stringify(original));other.id="33333333-3333-4333-8333-333333333333";
     prepare("ab");queueValue("xy");pane.selectedAgent=other;pane.draft="SECOND";wait(30);check(pane.draft,"SECOND","Queued edit cannot mutate a newly selected session");
     // A cancelled old callback must not flush a new edit with an unsettled cursor.
     pane.selectedAgent=original;prepare("ab");queueValue("xy");Qt.callLater(function(){qa.staleCallbackIsolated=pane.editScheduled&&pane.draft==="SECOND"});pane.selectedAgent=other;pane.draft="SECOND";pane.syncDraftAtCursor(2);pane.view="draft";pane.testDraft.forceActiveFocus();queueValue("ZZ");assert(pane.editScheduled);wait(30);check(pane.draft,"SEZZND","New generation applies only its own immutable range");assert(staleCallbackIsolated,"Old deferred callback cannot consume the newer generation edit");
     pane.selectedAgent=original;prepare("ab");queueValue("xy");pane.selectedAgent=null;pane.draft="";wait(30);check(pane.draft,"","Replay/close clearing target cancels the queued edit");
     pane.selectedAgent=original;prepare("ab");queueValue("xy");pane.visible=false;wait(30);check(pane.draft,"ab","Hidden pane cancels deferred editing");pane.visible=true;
     prepare("ab");queueValue("xy");pane.enabled=false;wait(30);check(pane.draft,"ab","Disabled pane cancels deferred editing");pane.enabled=true;
     prepare("ab");queueValue("xy");pane.draft="RESTORED";wait(30);check(pane.draft,"RESTORED","External same-session draft restoration cancels old edit");
     prepare("ab");queueValue("xy");pane.selectedAgent=JSON.parse(JSON.stringify(original));wait(30);check(pane.draft,"xy","Metadata refresh with same exact identity preserves pending edit");
     prepare("ab");queueValue("xy");pane.testClose.clicked();check(closedText,"xy","Close action flushes while original session is still selected");wait(30);check(pane.draft,"xy");
     prepare("ab");queueValue("xy");pane.flushEditor();check(pane.draft,"xy","Root can flush old draft before remembering or switching");pane.selectedAgent=other;pane.draft="SECOND";wait(30);check(pane.draft,"SECOND");pane.selectedAgent=original;
     prepare("ab");check(pane.testDraft.text,"ab");type(Qt.Key_C);check(pane.draft,"abc");check(pane.draftPage,1);check(pane.testDraft.text,"c");type(Qt.Key_D);check(pane.draft,"abcd","Boundary typing keeps exact instruction order");
     press(pane.testSend);assert(pane.confirming);press(pane.testConfirm);check(sentText,"abcd","Confirmed payload has exact canonical instruction");
     // A replaced inventory object for the same UUID must retain the nonce.
     var nonce=pane.pendingMessageId;pane.selectedAgent=JSON.parse(JSON.stringify(pane.selectedAgent));wait(20);check(pane.pendingMessageId,nonce);
     prepare("abcd");pane.showDraftPage(0);pane.testDraft.forceActiveFocus();pane.testDraft.cursorPosition=2;type(Qt.Key_X);type(Qt.Key_Y);check(pane.draft,"abxycd","Insertion in a full nonfinal page preserves suffix order");
     prepare("ab😀cd");pane.showDraftPage(1);pane.testDraft.forceActiveFocus();pane.testDraft.cursorPosition=0;type(Qt.Key_Backspace);check(pane.draft,"a😀cd","Backspace crosses page boundary without losing suffix");
     pane.showDraftPage(0);pane.testDraft.forceActiveFocus();pane.testDraft.cursorPosition=pane.testDraft.text.length;type(Qt.Key_Delete);check(pane.draft,"a😀d","Delete at page boundary preserves complete surrogate pair");
     prepare("ab");pane.testDraft.insert(pane.testDraft.cursorPosition,"cdefghij");wait(40);check(pane.draft,"abcdefghij","Paste follows canonical cursor");type(Qt.Key_K);check(pane.draft,"abcdefghijk");
     prepare("abcdef");pane.showDraftPage(1);pane.testDraft.forceActiveFocus();pane.testDraft.select(0,2);type(Qt.Key_X);type(Qt.Key_Y);check(pane.draft,"abxyef","Selection replacement preserves page suffix");
     prepare("ab\\nc");type(Qt.Key_D);check(pane.draft,"ab\\ncd","Newline boundaries preserve text");
     pane.tinyPages=false;wait(30);var capacity=pane.pageColumns*pane.pageRows,prefix=Array(capacity+1).join("a");prepare(prefix);type(Qt.Key_C);type(Qt.Key_D);check(pane.draft,prefix+"cd","Actual viewport page capacity preserves order");assert(pane.testDraft.contentHeight<=pane.testDraft.height+1,"Editor remains fully paged");
     pane.width=1600;pane.height=900;wait(30);type(Qt.Key_E);check(pane.draft,prefix+"cde","Resize keeps absolute insertion cursor");
     pane.width=912;pane.height=512;pane.selectedAgent={id:"22222222-2222-4222-8222-222222222222",provider:"claude",label:"Claude fixture",availability:"live",status:{type:"idle",activeFlags:[]},statusSource:"fixture",capabilities:{canReadReply:true,canSend:false,canOpen:false,reason:"No supported same-process instruction API."}};wait(30);assert(pane.sendReason.indexOf("Read-only session:")===0);assert(!pane.testSend.enabled);
     pane.inventoryNotices=[{provider:"grok",code:"unsupported",reason:Array(101).join("Long metadata-only adapter reason WWW 🍀. ")},{provider:"codex-desktop",reason:"Desktop task namespace unavailable to external plugin."}];press(pane.testNotices);assert(pane.showNotices);assert(pane.noticePages.length>1);
     for(var n=0;n<pane.noticePages.length;n++){pane.noticePage=n;wait(5);assert(pane.testNoticeText.paintedHeight<=pane.testNoticeText.height+1,"Adapter notice page fully fits "+n);}
     check(pane.noticePages.join(""),pane.noticeText,"All adapter notice text is accessible by pages");
     console.log("AGENT_PANE_PASS "+JSON.stringify({boundaryText:"abcd",nativeTextAreaKeys:true,unicodeBoundary:true,midPageInsertion:true,pasteAndSelection:true,actualViewportBoundary:true,resizeCursor:true,nonceRetained:true,sessionSwitchRace:true,nullTargetRace:true,hiddenPaneRace:true,disabledPaneRace:true,externalDraftRace:true,sameIdentityRefresh:true,preSwitchFlush:true,staleCallbackIsolated:staleCallbackIsolated,closeFlush:true,noticePages:pane.noticePages.length,readOnlyReason:true}));
    }
   }
   Connections{target:pane;function onRequestSend(agent,text,messageId){qa.sentText=text}function onClosed(){qa.closedText=pane.draft}}
  }
 }
 Timer{interval:500;running:true;onTriggered:{try{qa.test_editor()}catch(error){console.log("AGENT_PANE_FAILURE "+error);Qt.quit()}}}
 IpcHandler{target:"harness";function status():string{return JSON.stringify({done:true})}function quit():void{Qt.callLater(Qt.quit)}}
}'''.replace('SOURCE', ROOT.as_uri())

def focused():
 return json.loads(subprocess.check_output(['hyprctl','activewindow','-j'],text=True)).get('address')

before=focused()
with NativeSession('agent-pane',qml,guard=False,background=True) as session:
 session.marker('AGENT_PANE_PASS',timeout=35)
 assert focused()==before,'Fixture changed user focus'
 session.quit();clean_log(session.log())
 result=json.loads(next(line.split('AGENT_PANE_PASS ',1)[1]for line in session.log().splitlines()if 'AGENT_PANE_PASS 'in line))
 result.update(focusRetained=True,realSessionIO=False,globalKeyInjection=False,hiddenNativeFixture=True)
 (ROOT/'verification/agent-pane.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result))
