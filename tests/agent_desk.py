"""Hidden native Agent Desk fixture; no provider calls, no real session text."""
import json
import subprocess
from pathlib import Path
from native_session import NativeSession, ROOT, clean_log

qml='''import QtQuick
import Quickshell
import Quickshell.Io
import QtTest
import "SOURCE" as Source
ShellRoot {
 QtObject{id:theme;property color ink:"#eeeeee";property color accent:"#33ccdd";property color panelPaper:"#202025"}
 FloatingWindow{id:window;title:"Districts · Fixture";visible:true;implicitWidth:1600;implicitHeight:1000
  Item{id:body;anchors.fill:parent
   Source.AgentV2{id:pane;city:theme;width:912;height:512}
   TestCase{id:qa;parent:body;name:"AgentDeskNative";when:false
    property int reads:0
    property int choices:0
    property string lastProvider:""
    property string lastId:""
    function check(value,message){if(!value)throw new Error("DESK_CHECK_FAILED "+message)}
    function press(item){mouseClick(item,item.width/2,item.height/2);wait(25)}
    function agent(provider,id){return {provider:provider,id:id,label:provider+" synthetic session",availability:"live",status:{type:"idle",activeFlags:[]},statusSource:"Controlled metadata fixture",capabilities:{canReadReply:true,canSend:false,canOpen:false}}}
    function polish(item){for(var child of item.children)polish(child);if(typeof item.forceLayout==="function")item.forceLayout()}
    function test_desk(){
     check(pane.testTitle.text==="Agent Desk","Shared title");check(!pane.testRead.enabled,"No-session read blocked");press(pane.testNotices);check(pane.showNotices,"No-session adapters accessible");check(reads===0,"No automatic content read");press(pane.testNotices);
     var uuid="11111111-1111-4111-8111-111111111111",a=agent("codex",uuid),b=agent("claude",uuid);pane.availableAgents=[a,b];pane.availableAgents[1].availability="stored";press(pane.testSessionNext);check(choices===1&&pane.selectedAgent.provider==="codex","Desk chooses first exact metadata session");press(pane.testSessionNext);check(choices===2&&pane.selectedAgent.provider==="claude"&&pane.selectedAgent.availability==="stored","Desk includes stored metadata independently of city display");pane.selectedAgent=a;wait(25);check(reads===0,"Selection is metadata-only");press(pane.testRead);check(reads===1&&lastProvider==="codex"&&lastId===uuid,"Explicit exact read selection");
     pane.replyIdentity="codex:"+uuid;pane.reply={text:"Latest synthetic assistant reply.",source:"Sanitized fixture only",history:[{role:"assistant",itemId:"older",text:Array(151).join("Earlier assistant reply 🍀 with complete paragraphs and no private session content.\\n")},{role:"user",itemId:"not-an-assistant",text:"User text is excluded."},{role:"assistant",itemId:"latest",text:"Latest synthetic assistant reply."}]};wait(30);check(pane.replyMessages.length===2&&pane.replyMessageIndex===1,"Assistant-only bounded history starts latest");press(pane.testMessagePrevious);check(pane.replyMessageIndex===0,"Older response button");check(pane.replyPages.length>1,"Long response is paged");press(pane.testReplyNext);check(pane.replyPage===1&&pane.replyMessageIndex===0,"Text pages independent");press(pane.testMessageNext);check(pane.replyMessageIndex===1&&pane.replyPage===0,"Response change resets only text page");check(reads===1,"Browsing fetched history makes no provider requests");
     pane.selectedAgent=b;wait(25);check(pane.replyMessages.length===0,"Same UUID different provider hides old content");check(pane.testReply.text.indexOf("Latest synthetic")<0,"Stale text never relabeled");pane.replyIdentity="claude:"+uuid;wait(25);check(pane.replyMessages.length===0,"Retagging cannot expose retained reply");pane.reply={text:"Selected Claude synthetic response.",source:"Sanitized fixture only",history:[{role:"assistant",itemId:"claude-older",text:Array(101).join("Long Claude assistant fixture 🍀.\\n")},{role:"assistant",itemId:"claude-latest",text:"Selected Claude synthetic response."}]};wait(30);
     for(var size of [[912,512],[1600,1000],[880,480],[760,480]]){
      window.implicitWidth=size[0];window.implicitHeight=size[1];pane.width=size[0];pane.height=size[1];wait(100);pane.showReplyMessage(0);wait(30);polish(pane);
      for(var n=0;n<pane.replyPages.length;n++){pane.replyPage=n;wait(2);check(pane.testReply.paintedHeight<=pane.testReply.height+1,"Complete reply page fits "+size+" / "+n);check(pane.testReply.paintedWidth<=pane.testReply.width+1,"Complete reply width fits");}
      for(var item of [pane.testSessionPrevious,pane.testSessionNext,pane.testRead,pane.testMessagePrevious,pane.testMessageNext,pane.testReplyPrevious,pane.testReplyNext,pane.testClose]){var p=item.mapToItem(pane,0,0);check(p.x>=0&&p.y>=0&&p.x+item.width<=pane.width+1&&p.y+item.height<=pane.height+1,"All Desk controls in bounds "+size+" / "+item.text+" / "+JSON.stringify({x:p.x,y:p.y,w:item.width,h:item.height,paneWidth:pane.width,parent:item.parent.width,grandparent:item.parent.parent.width,column:item.parent.parent.parent.width}));}
      pane.showReplyMessage(1);pane.draft="Synthetic draft retained separately from history.";
     }
     check(reads===1,"Fit and resize never read chat");console.log("AGENT_DESK_PASS "+JSON.stringify({sharedDesk:true,exactProviderSession:true,allPassedStoredMetadataAvailable:true,noAutomaticRead:true,assistantMessages:2,independentMessageTextPages:true,staleProviderReplyHidden:true,retagAloneRejected:true,minimum:[912,512],normal:[1600,1000],modalMinimum:[880,480],modalWidth:[760,480],replyPagesFullyFit:true,positionersPolishedForHiddenWindow:true,realSessionIO:false,visibleLiveQA:false}));
    }
   }
   Connections{target:pane;function onRequestSelect(agent){qa.choices++;pane.selectedAgent=agent}function onRequestRead(agent){qa.reads++;qa.lastProvider=agent.provider;qa.lastId=agent.id}}
  }
 }
 Timer{interval:200;running:true;onTriggered:console.log("AGENT_DESK_READY")}
 IpcHandler{target:"harness";function run():void{Qt.callLater(function(){try{qa.test_desk()}catch(error){console.log("AGENT_DESK_FAILURE "+error+" "+error.stack);Qt.quit()}})}function quit():void{Qt.callLater(Qt.quit)}}
}'''.replace('SOURCE',ROOT.as_uri())
def focus():
 return json.loads(subprocess.check_output(['hyprctl','activewindow','-j'],text=True)).get('address')

before=focus()
with NativeSession('agent-desk',qml,guard=False,background=True) as session:
 session.marker('AGENT_DESK_READY');session.ipc('run');session.marker('AGENT_DESK_PASS',timeout=35);session.quit();clean_log(session.log());assert focus()==before,'Hidden fixture changed actual user focus'
 result=json.loads(next(line.split('AGENT_DESK_PASS ',1)[1]for line in session.log().splitlines()if 'AGENT_DESK_PASS 'in line));result.update(hiddenNativeFixture=True,focusPreserved=True)
 (ROOT/'verification/agent-desk.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
