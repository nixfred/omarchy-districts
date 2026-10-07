import QtQuick
import QtTest
import "../.."
TestCase {
 id:qa;name:"GlobalAgentDesk";visible:true;when:windowShown;width:1600;height:1000
 QtObject{id:theme;property color ink:"#eeeeee";property color accent:"#33ccdd";property color panelPaper:"#202025"}
 AgentV2{id:pane;city:theme;width:912;height:512}
 SignalSpy{id:choices;target:pane;signalName:"requestSelect"}
 SignalSpy{id:reads;target:pane;signalName:"requestRead"}
 SignalSpy{id:sends;target:pane;signalName:"requestSend"}
 function agent(provider,id){return {provider:provider,id:id,label:provider+" fixture",availability:"live",status:{type:"idle",activeFlags:[]},statusSource:"Synthetic metadata",capabilities:{canReadReply:true,canSend:true,canOpen:false}}}
 function init(){pane.selectedAgent=null;pane.replyIdentity="";pane.reply={text:"",source:"Synthetic metadata"};pane.width=912;pane.height=512;pane.availableAgents=[];pane.providerFilter="";pane.draft="";pane.message="";pane.busy=false;pane.showNotices=false;reads.clear();sends.clear();choices.clear();wait(20)}
 function test_desk_without_selection(){compare(pane.testTitle.text,"Agent Desk");verify(!pane.testRead.enabled);verify(!pane.testSend.enabled);verify(!pane.testDraft.enabled);compare(pane.replyMessages.length,0);mouseClick(pane.testNotices);verify(pane.showNotices);compare(reads.count,0)}
 function test_metadata_selector_includes_passed_stored_records(){
  var uuid="11111111-1111-4111-8111-111111111111",a=agent("codex",uuid),b=agent("claude",uuid);b.availability="stored";pane.availableAgents=[a,b,a];wait(20);compare(pane.selectorAgents.length,2);compare(pane.selectorIndex,-1);verify(pane.testSessionNext.enabled);mouseClick(pane.testSessionNext);compare(choices.count,1);compare(choices.signalArguments[0][0].provider,"codex");compare(reads.count,0);pane.selectedAgent=a;wait(20);compare(pane.selectorIndex,0);mouseClick(pane.testSessionNext);compare(choices.count,2);compare(choices.signalArguments[1][0].provider,"claude");compare(choices.signalArguments[1][0].availability,"stored");compare(reads.count,0,"Choosing stored metadata never fetches chat");
  pane.providerFilter="kimi";pane.availableAgents=[Object.assign(agent("pi","22222222-2222-4222-8222-222222222222"),{isKimi3:true})];pane.selectedAgent=null;wait(20);verify(pane.testSessionLabel.text.indexOf("Kimi3")>=0);mouseClick(pane.testSessionNext);compare(choices.signalArguments[2][0].provider,"pi","Display family never rewrites exact provider");compare(reads.count,0);pane.availableAgents=[];wait(20);verify(!pane.testSessionNext.enabled);verify(pane.testSessionLabel.text.indexOf("No matching")>=0);
 }
 function test_explicit_read_exact_provider_identity(){
  var uuid="11111111-1111-4111-8111-111111111111",a=agent("codex",uuid),b=agent("claude",uuid);
  pane.selectedAgent=a;wait(20);compare(reads.count,0,"Selection never reads chat");mouseClick(pane.testRead);compare(reads.count,1);compare(reads.signalArguments[0][0].provider,"codex");compare(reads.signalArguments[0][0].id,uuid);
  pane.replyIdentity="codex:"+uuid;pane.reply={text:"Codex private fixture text",history:[{role:"assistant",itemId:"c1",text:"Codex private fixture text"}]};wait(20);compare(pane.replyMessages.length,1);
  pane.selectedAgent=b;wait(20);compare(pane.replyMessages.length,0,"Namespace switch cannot expose retained reply");verify(pane.testReply.text.indexOf("Codex private")<0);compare(reads.count,1);
  pane.replyIdentity="claude:"+uuid;wait(20);compare(pane.replyMessages.length,0,"Retagging alone cannot expose old accepted content");
  pane.reply={text:"Claude fixture reply",history:[{role:"assistant",itemId:"a1",text:"Claude fixture reply"}]};wait(20);compare(pane.currentReply.text,"Claude fixture reply");
  pane.replyIdentity="codex:"+uuid;wait(20);compare(pane.replyMessages.length,0,"Tagged wrong-provider result stays hidden");
  pane.selectedAgent=null;wait(20);compare(pane.replyMessages.length,0);verify(!pane.testRead.enabled);
 }
 function test_message_and_text_pages_independent(){
  pane.selectedAgent=agent("kimi","22222222-2222-4222-8222-222222222222");pane.reply={text:"Latest fixture reply",history:[{role:"assistant",itemId:"old",text:Array(2001).join("Old reply 🍀 with wide WWW.\n")},{role:"user",itemId:"u",text:"User content must not enter assistant history"},{role:"assistant",itemId:"latest",text:"Latest fixture reply"}]};wait(30);
  compare(pane.replyMessages.length,2);compare(pane.replyMessageIndex,1);compare(pane.currentReply.itemId,"latest");mouseClick(pane.testMessagePrevious);compare(pane.replyMessageIndex,0);verify(pane.replyPages.length>1);compare(pane.replyPage,0);
  mouseClick(pane.testReplyNext);compare(pane.replyPage,1);compare(pane.replyMessageIndex,0);mouseClick(pane.testMessageNext);compare(pane.replyMessageIndex,1);compare(pane.replyPage,0);compare(reads.count,0,"Browsing fetched content never starts reads");
 }
 function test_bounded_history_and_same_identity_metadata(){
  pane.selectedAgent=agent("gemini","33333333-3333-4333-8333-333333333333");var rows=[];for(var i=0;i<100;i++)rows.push({role:"assistant",itemId:"item"+i,text:"Synthetic response "+i});pane.reply={text:"Synthetic response99",history:rows};wait(20);compare(pane.replyMessages.length,16);compare(pane.replyMessages[0].itemId,"item84");compare(pane.currentReply.itemId,"item99");verify(pane.historyBounded);
  pane.showReplyMessage(7);pane.selectedAgent=agent("gemini","33333333-3333-4333-8333-333333333333");wait(20);compare(pane.replyMessageIndex,7,"Same identity metadata refresh keeps navigation");compare(pane.replyMessages.length,16);
 }
 function test_same_identity_metadata_keeps_both_reply_pages(){
  var id="66666666-6666-4666-8666-666666666666";pane.selectedAgent=agent("codex",id);pane.reply={history:[{role:"assistant",itemId:"older",text:Array(2001).join("Older response preserved 🍀.\n")},{role:"assistant",itemId:"latest",text:"Latest"}]};wait(20);pane.showReplyMessage(0);verify(pane.replyPages.length>1);pane.replyPage=1;pane.selectedAgent=Object.assign(agent("codex",id),{status:{type:"active"}});wait(20);compare(pane.replyMessageIndex,0);compare(pane.replyPage,1);
 }
 function test_backend_bounded_history_label(){
  pane.selectedAgent=agent("pi","55555555-5555-4555-8555-555555555555");pane.reply={text:"Latest",historyTruncated:true,history:[{role:"assistant",text:"Latest"}]};wait(20);verify(pane.historyBounded,"Backend omitted older entries are disclosed even below UI cap");
 }
 function test_reply_and_draft_fit_data(){return [{tag:"minimum",w:912,h:512},{tag:"normal",w:1600,h:1000},{tag:"modalMinimum",w:880,h:480},{tag:"modalWidth",w:760,h:480}]}
 function test_reply_and_draft_fit(data){
  pane.width=data.w;pane.height=data.h;pane.selectedAgent=agent("codex","44444444-4444-4444-8444-444444444444");pane.reply={text:"Latest",history:[{role:"assistant",itemId:"old",text:Array(301).join("Long reply plain text 🍀 WWW / narrow iii.\n")},{role:"assistant",itemId:"latest",text:"Latest"}]};pane.draft=Array(90).join("Complete draft 🏘️ preserved.\n");wait(30);pane.showReplyMessage(0);
  for(var page=0;page<pane.replyPages.length;page++){pane.replyPage=page;wait(1);verify(pane.testReply.paintedHeight<=pane.testReply.height+1,"Every reply text page fits");verify(pane.testReply.paintedWidth<=pane.testReply.width+1)}
  for(var item of [pane.testTitle,pane.testSessionPrevious,pane.testSessionNext,pane.testRead,pane.testMessagePrevious,pane.testMessageNext,pane.testReplyPrevious,pane.testReplyNext,pane.testClose]){var p=item.mapToItem(pane,0,0);verify(p.x>=0&&p.y>=0&&p.x+item.width<=pane.width+1&&p.y+item.height<=pane.height+1,"Desk control fits "+data.tag)}
  pane.view="draft";wait(20);for(var page=0;page<pane.draftPages.length;page++){pane.showDraftPage(page);wait(1);verify(pane.testDraft.contentHeight<=pane.testDraft.height+1,"Every draft text page fits")}
 }
}
