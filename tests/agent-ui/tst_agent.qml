import QtQuick
import QtTest
import "../.."
TestCase {
 id:test
 name:"AgentSessionPanel"
 visible:true
 when:windowShown
 width:1200;height:700
 QtObject{id:theme;property color ink:"#eeeeee";property color accent:"#33ccdd";property color panelPaper:"#202025"}
 AgentV2{id:pane;city:theme;width:912;height:512;selectedAgent:({id:"11111111-1111-4111-8111-111111111111",provider:"codex",label:"Codex fixture",availability:"live",status:{type:"idle",activeFlags:[]},statusSource:"Controlled fixture metadata",capabilities:{canReadReply:true,canSend:true,canOpen:true,reason:"Existing approval prompts remain in the native client."}})}
 SignalSpy{id:sent;target:pane;signalName:"requestSend"}
 function test_paged_fit(){
  for(var size of [[912,512],[1600,900],[2560,1440]]){
   pane.width=size[0];pane.height=size[1];pane.reply={text:Array(301).join("A long selected reply with unicode 🍀 and narrow / wide WWW characters.\n"),source:"Selected fixture only"};
   pane.draft=Array(100).join("A draft instruction with lines and Unicode 🏘️.\n");wait(80);
   verify(pane.replyPages.length>1);verify(pane.draftPages.length>1);
   for(var n=0;n<pane.replyPages.length;n++){
    pane.replyPage=n;wait(1);verify(pane.testReply.paintedHeight<=pane.testReply.height+1,"Reply page fits "+size+" / "+n)
   }
   pane.view="draft";wait(20);
   for(var m=0;m<pane.draftPages.length;m++){
    pane.draftPage=m;wait(1);verify(pane.testDraft.contentHeight<=pane.testDraft.height+1,"Draft page fits "+size+" / "+m)
   }
  }
 }
 function test_draft_complete_and_review(){
  pane.width=912;pane.height=512;pane.draft="before";pane.draftPage=0;pane.replacePage("complete draft");compare(pane.draft,"complete draft");
  pane.view="draft";wait(50);pane.testSend.clicked();verify(pane.confirming);pane.testConfirm.clicked();compare(sent.count,1);compare(sent.signalArguments[0][0].id,pane.selectedAgent.id);compare(sent.signalArguments[0][1],"complete draft");verify(/^[0-9a-f-]{36}$/.test(sent.signalArguments[0][2]));
 }
 function test_long_paste_reflows_without_hidden_overflow(){
  pane.width=912;pane.height=512;pane.view="draft";pane.draft="";pane.draftPage=0;wait(20);
  pane.testDraft.forceActiveFocus();pane.testDraft.text=Array(4001).join("x");wait(40);
  compare(pane.draft.length,4000);verify(pane.draftPages.length>1);verify(pane.testDraft.contentHeight<=pane.testDraft.height+1);
  var old=pane.draft;pane.testDraft.text=Array(8194).join("x");wait(30);compare(pane.draft,old);verify(pane.message.indexOf("8192")>=0);verify(pane.testDraft.contentHeight<=pane.testDraft.height+1);
 }
 function test_permission_pending_disables_send(){
  pane.selectedAgent={id:"22222222-2222-4222-8222-222222222222",provider:"codex",label:"Blocked fixture",availability:"live",status:{type:"active",activeFlags:["waitingOnApproval"]},statusSource:"fixture",capabilities:{canReadReply:true,canSend:false,canOpen:true,reason:"Answer approval in native client."}};
  pane.draft="instruction";wait(10);verify(!pane.testSend.enabled)
 }
}
