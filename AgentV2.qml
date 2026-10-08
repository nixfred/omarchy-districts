import QtQuick
import QtQuick.Controls as Controls
import "AgentCityV2.js" as Agents
Item {
 id:pane
 required property var city
 property var selectedAgent:null
 property var availableAgents:[]
 property string providerFilter:""
 readonly property var selectorAgents:metadataChoices()
 readonly property int selectorIndex:selectorAgents.findIndex(function(agent){return selectedAgent&&agent.provider===selectedAgent.provider&&String(agent.id)===String(selectedAgent.id)})
 property var reply:({text:"",source:"Select Read replies to fetch this session only."})
 // Root supplies the identity captured when accepting a read result, never the current
 // selection as a substitute. Local acceptance also blocks legacy untagged stale text.
 property string replyIdentity:""
 property string acceptedReplyIdentity:""
 property int replyMessageIndex:0
 readonly property int historyLimit:16
 readonly property bool replyMatchesSelection:!!selectedAgent&&acceptedReplyIdentity===agentIdentity()&&(!replyIdentity||replyIdentity===agentIdentity())
 readonly property var replyMessages:messageHistory()
 readonly property var currentReply:replyMessages.length?replyMessages[Math.max(0,Math.min(replyMessageIndex,replyMessages.length-1))]:null
 readonly property bool historyBounded:replyMatchesSelection&&reply&&Array.isArray(reply.history)&&(reply.historyTruncated===true||reply.truncated===true||reply.history.filter(function(m){return m&&m.role==="assistant"&&typeof m.text==="string"}).length>historyLimit)
 property string draft:""
 property bool busy:false
 property bool submissionAvailable:true
 property string message:""
 property string view:"reply"
 property var inventoryNotices:[]
 property int noticePage:0
 property bool showNotices:false
 readonly property string noticeText:inventoryNotices.length?inventoryNotices.map(function(n){return String(n.provider||"Adapter")+(n.code?" / "+String(n.code):"")+"\n"+String(n.reason||"No reason supplied.")}).join("\n\n"):"No adapter notices supplied."
 readonly property var noticePages:paginate(noticeText,Math.max(8,Math.floor((noticesContent.width-20)/metrics.maximumCharacterWidth)),Math.max(2,Math.floor((noticesContent.height-80)/(metrics.height+2))))
 property int replyPage:0
 property int draftPage:0
 property bool confirming:false
 property string pendingMessageId:""
 property string previousIdentity:""
 property int draftCursor:0
 property int editorPageStart:0
 property int editorPageEnd:0
 property bool syncingEditor:false
 property bool editingDraft:false
 property bool editScheduled:false
 property string pendingEditorValue:""
 property string pendingEditorIdentity:""
 property string pendingEditorBase:""
 property int editorGeneration:0
 readonly property string sendReason:capabilities.canSend?(capabilities.reason||"Queue keeps this session’s permissions. Approvals and questions stay in its native client."):("Read-only session: "+(capabilities.reason||"This provider has no supported instruction transport here."))
 readonly property var capabilities:selectedAgent&&selectedAgent.capabilities||({})
 readonly property bool wide:width>=960
 readonly property int pageColumns:Math.max(8,Math.floor((Math.min(replyBox.width,draftBox.width)-20)/metrics.maximumCharacterWidth))
 readonly property int pageRows:Math.max(1,Math.floor((Math.min(replyBox.height,draftBox.height)-24)/(metrics.height+2)))
 readonly property var replyPages:paginate(currentReply?currentReply.text:"",pageColumns,pageRows)
 readonly property var draftPages:paginate(draft,pageColumns,pageRows)
 signal requestSelect(var agent)
 signal requestRead(var agent)
 signal requestSend(var agent,string text,string messageId)
 signal requestOpen(var agent)
 signal draftEdited(string text)
 signal closed()
 property alias testReply:replyText
 property alias testDraft:editor
 property alias testRead:readButton
 property alias testTitle:deskTitle
 property alias testSessionPrevious:sessionPrevious
 property alias testSessionNext:sessionNext
 property alias testSessionLabel:sessionLabel
 property alias testMessagePrevious:messagePrevious
 property alias testMessageNext:messageNext
 property alias testReplyPrevious:replyPrevious
 property alias testReplyNext:replyNext
 property alias testMessageLabel:messageLabel
 property alias testSend:sendButton
 property alias testConfirm:confirmButton
 property alias testClose:closeButton
 property alias testNotices:noticeButton
 property alias testNoticeText:noticeTextItem
 FontMetrics{id:metrics;font.pixelSize:14;font.family:"monospace"}
 function metadataChoices(){
  var seen={},out=[];
  (Array.isArray(availableAgents)?availableAgents:[]).forEach(function(agent){if(!agent||!agent.provider||!agent.id)return;var key=String(agent.provider)+":"+String(agent.id);if(!seen[key]){seen[key]=true;out.push(agent)}});
  return out;
 }
 function chooseSession(index){
  if(busy||index<0||index>=selectorAgents.length)return;
  flushEditor();requestSelect(selectorAgents[index]);
 }
 function messageHistory(){
  if(!replyMatchesSelection||!reply)return [];
  var messages=Array.isArray(reply.history)?reply.history.filter(function(m){return m&&m.role==="assistant"&&typeof m.text==="string"}).slice(-historyLimit).map(function(m){return {text:m.text,itemId:String(m.itemId||""),role:"assistant"}}):[];
  if(!messages.length&&typeof reply.text==="string"&&reply.text)messages.push({text:reply.text,itemId:String(reply.itemId||""),role:"assistant"});
  return messages;
 }
 function showReplyMessage(index){replyMessageIndex=Math.max(0,Math.min(replyMessages.length-1,index));replyPage=0}
 onReplyChanged:{acceptedReplyIdentity=agentIdentity();replyMessageIndex=Math.max(0,replyMessages.length-1);replyPage=0}
 onReplyMessagesChanged:{replyMessageIndex=Math.max(0,replyMessages.length-1);replyPage=0}
 function codePoints(value){
  var text=String(value),result=[];
  for(var i=0;i<text.length;i++){var c=text.charCodeAt(i);if(c>=0xd800&&c<=0xdbff&&i+1<text.length){var next=text.charCodeAt(i+1);if(next>=0xdc00&&next<=0xdfff){result.push(text.slice(i,i+2));i++;continue;}}result.push(text.charAt(i));}
  return result;
 }
 function paginate(value,columns,rows){return splitPages(value,columns,rows)}
 function splitPages(value,columns,rows){
  var chars=codePoints(value),pages=[],chunk="",line=0,col=0;
  for(var i=0;i<chars.length;i++){
   var c=chars[i];
   if(col>=columns&&c!=="\n"){line++;col=0}
   if(line>=rows){pages.push(chunk);chunk="";line=0;col=0}
   chunk+=c;
   if(c==="\n"){line++;col=0}else col++;
  }
  if(chunk||!pages.length)pages.push(chunk);return pages;
 }
 function draftRange(page){
  var start=0,pages=draftPages;
  for(var i=0;i<page;i++)start+=pages[i].length;
  return {start:start,end:start+pages[page].length,text:pages[page]};
 }
 function syncDraftAtCursor(position){
  if(syncingEditor||editingDraft||editScheduled)return;
  var pages=draftPages,pos=Math.max(0,Math.min(draft.length,position)),start=0,page=0;
  for(var i=0;i<pages.length;i++){
   if(pos<start+pages[i].length||i===pages.length-1){page=i;break;}
   start+=pages[i].length;
  }
  syncingEditor=true;
  draftCursor=pos;draftPage=page;
  editorPageStart=start;editorPageEnd=start+pages[page].length;
  if(editor.text!==pages[page])editor.text=pages[page];
  editor.cursorPosition=Math.max(0,Math.min(editor.text.length,pos-start));
  syncingEditor=false;
 }
 function showDraftPage(page){
  flushEditor();
  var chosen=Math.max(0,Math.min(draftPages.length-1,page));
  syncDraftAtCursor(draftRange(chosen).start);
 }
 function applyEditorChange(value,cursor){
  if(syncingEditor||editingDraft)return;
  // The editor owns one immutable UTF-16 range of the canonical string.
  // Capture its range before changing pagination, then follow the absolute
  // cursor into the continuation page instead of putting the old page back.
  var full=draft.slice(0,editorPageStart)+value+draft.slice(editorPageEnd);
  if(codePoints(full).length>8192){
   message="Instruction limit is 8192 characters. The previous draft is preserved.";
   syncDraftAtCursor(draftCursor);return;
  }
  var absolute=editorPageStart+Math.max(0,Math.min(value.length,cursor));
  editingDraft=true;draft=full;draftEdited(full);confirming=false;pendingMessageId="";editingDraft=false;
  syncDraftAtCursor(absolute);
 }
 function replacePage(value){var page=Math.max(0,Math.min(draftPage,draftPages.length-1)),range=draftRange(page);editorPageStart=range.start;editorPageEnd=range.end;applyEditorChange(value,value.length)}
 function agentIdentity(){return selectedAgent?selectedAgent.provider+":"+selectedAgent.id:""}
 function cancelEditorEdit(){
  editScheduled=false;pendingEditorValue="";pendingEditorIdentity="";pendingEditorBase="";editorGeneration++;
 }
 function queueEditorChange(){
  if(syncingEditor||editingDraft||!visible||!enabled||!selectedAgent||!editor.activeFocus||editor.text===draft.slice(editorPageStart,editorPageEnd))return;
  pendingEditorValue=editor.text;
  if(editScheduled)return;
  editScheduled=true;pendingEditorIdentity=agentIdentity();pendingEditorBase=draft;
  var generation=editorGeneration;
  Qt.callLater(function(){if(editScheduled&&generation===editorGeneration)flushEditor()});
 }
 function flushEditor(){
  if(!editScheduled)return;
  if(!visible||!enabled||pendingEditorIdentity!==agentIdentity()||pendingEditorBase!==draft){cancelEditorEdit();return;}
  var value=pendingEditorValue,cursor=editor.cursorPosition;
  cancelEditorEdit();
  applyEditorChange(value,cursor);
 }
 function removeBoundary(backwards){
  flushEditor();
  var pos=editorPageStart+editor.cursorPosition,start=pos,end=pos;
  if(backwards&&pos>0){start=pos-1;var code=draft.charCodeAt(start);if(code>=0xdc00&&code<=0xdfff&&start>0)start--;}
  else if(!backwards&&pos<draft.length){end=pos+1;var code=draft.charCodeAt(pos);if(code>=0xd800&&code<=0xdbff&&end<draft.length)end++;}
  else return;
  editingDraft=true;draft=draft.slice(0,start)+draft.slice(end);draftEdited(draft);confirming=false;pendingMessageId="";editingDraft=false;
  syncDraftAtCursor(start);
 }
 function reviewDraft(){
  flushEditor();
  if(busy||!capabilities.canSend||!draft.trim()||!submissionAvailable)return false;
  if(!pendingMessageId&&typeof city.canReserveSubmission==="function"&&!city.canReserveSubmission(selectedAgent)){message="Submission identity capacity reached. Edit a retained draft before preparing another instruction.";return false;}
  confirming=true;if(!pendingMessageId)pendingMessageId=newId();return true;
 }
 function queueInstruction(){flushEditor();if(busy||!capabilities.canSend||!submissionAvailable||!pendingMessageId)return;confirming=false;requestSend(selectedAgent,draft,pendingMessageId)}
 function newId(){
  if(!submissionAvailable||(typeof city.canReserveSubmission==="function"&&!city.canReserveSubmission(selectedAgent)))return "";
  // Client submission identity is retained across an uncertain outcome.
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g,function(c){var r=Math.floor(Math.random()*16);return(c==="x"?r:(r&3|8)).toString(16)})
 }
 onSelectedAgentChanged:{var identity=agentIdentity();if(identity!==previousIdentity){cancelEditorEdit();acceptedReplyIdentity="";replyMessageIndex=0;draftCursor=0;replyPage=0;draftPage=0;confirming=false;pendingMessageId="";view="reply";showNotices=false;previousIdentity=identity}}
 onVisibleChanged:if(!visible)cancelEditorEdit()
 onEnabledChanged:if(!enabled)cancelEditorEdit()
 onNoticePagesChanged:noticePage=Math.min(noticePage,noticePages.length-1)
 onReplyPagesChanged:replyPage=Math.min(replyPage,replyPages.length-1)
 onDraftChanged:{if(!editingDraft)cancelEditorEdit();Qt.callLater(function(){if(!editingDraft&&!editScheduled)syncDraftAtCursor(draftCursor)})}
 onPageColumnsChanged:Qt.callLater(function(){if(!editingDraft&&!editScheduled)syncDraftAtCursor(draftCursor)})
 onPageRowsChanged:Qt.callLater(function(){if(!editingDraft&&!editScheduled)syncDraftAtCursor(draftCursor)})
 onDraftPageChanged:{if(!syncingEditor&&!editingDraft&&!editScheduled)showDraftPage(draftPage)}
 Rectangle{anchors.fill:parent;color:pane.city.panelPaper;border.color:Qt.alpha(pane.city.accent,.35);radius:14}
 Column{id:header;x:20;y:16;width:parent.width-40;spacing:6
  Row{width:parent.width;spacing:8
   Text{id:deskTitle;width:parent.width-258;text:"Agent Desk";color:pane.city.ink;font.pixelSize:20;elide:Text.ElideRight;textFormat:Text.PlainText}
   NeonActionV2{id:noticeButton;city:pane.city;width:130;text:pane.showNotices?"Back to Desk":"Adapter status";onClicked:{pane.flushEditor();pane.showNotices=!pane.showNotices}}
   NeonActionV2{id:closeButton;city:pane.city;width:112;text:"Close ×";onClicked:{pane.flushEditor();pane.closed()}}
  }
  Row{width:parent.width;spacing:8
   NeonActionV2{id:sessionPrevious;city:pane.city;width:64;text:"←";enabled:!pane.busy&&pane.selectorIndex>0;onClicked:pane.chooseSession(pane.selectorIndex-1)}
   Text{id:sessionLabel;width:parent.width-144;height:38;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;font.pixelSize:12;color:pane.city.ink;text:(!pane.providerFilter?"All providers":pane.providerFilter==="kimi"?"Kimi3":pane.providerFilter)+" · "+(pane.selectorAgents.length?(pane.selectorIndex>=0?"Session "+(pane.selectorIndex+1)+" / "+pane.selectorAgents.length:"Choose session · "+pane.selectorAgents.length+" available"):"No matching sessions")}
   NeonActionV2{id:sessionNext;city:pane.city;width:64;text:"→";enabled:!pane.busy&&pane.selectorIndex+1<pane.selectorAgents.length;onClicked:pane.chooseSession(pane.selectorIndex+1)}
  }
  Text{width:parent.width;text:pane.selectedAgent?Agents.displayName(pane.selectedAgent)+"  ·  "+Agents.subtitle(pane.selectedAgent)+"  ·  "+Agents.glow(pane.selectedAgent).label:"Select any agent building to use this shared Desk. Adapter status is available below.";font.pixelSize:12;color:Qt.alpha(pane.city.ink,.72);wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Text{width:parent.width;text:pane.selectedAgent?(pane.selectedAgent.provider+" / "+pane.selectedAgent.id):"No session selected · No chat content has been requested.";font.pixelSize:12;color:pane.city.accent;wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Text{width:parent.width;text:{var a=pane.selectedAgent;if(!a)return "";var s=a.status||{};return a.availability+" · Reported "+s.type+((s.activeFlags||[]).length?" / "+s.activeFlags.join(", "):"")+" · "+a.statusSource}font.pixelSize:12;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
 }
 Row{id:tabs;x:20;y:header.y+header.height+10;width:parent.width-40;spacing:8;visible:!pane.wide&&!pane.showNotices
  NeonActionV2{city:pane.city;width:(parent.width-8)/2;text:"Replies";checked:pane.view==="reply";onClicked:pane.view="reply"}
  NeonActionV2{city:pane.city;width:(parent.width-8)/2;text:"Instruction";checked:pane.view==="draft";onClicked:pane.view="draft"}
 }
 Item{id:columns;visible:!pane.showNotices;x:20;y:tabs.visible?tabs.y+tabs.height+10:header.y+header.height+10;width:parent.width-40;height:Math.max(0,footer.y-y-12)
  Item{id:left;width:pane.wide?(parent.width-18)/2:parent.width;height:parent.height;visible:pane.wide||pane.view==="reply"
   Row{id:replyControls;width:parent.width;spacing:8
    NeonActionV2{id:readButton;city:pane.city;width:(parent.width-8)/2;text:pane.busy?"Working…":"Read replies";enabled:!pane.busy&&!!pane.selectedAgent&&!!pane.capabilities.canReadReply;onClicked:pane.requestRead(pane.selectedAgent)}
    NeonActionV2{city:pane.city;width:(parent.width-8)/2;text:"Open native client ↗";enabled:!pane.busy&&!!pane.capabilities.canOpen;onClicked:pane.requestOpen(pane.selectedAgent)}
   }
   Row{id:messageControls;x:0;y:replyControls.height+8;width:parent.width;spacing:8
    NeonActionV2{id:messagePrevious;city:pane.city;width:64;text:"Older";enabled:pane.replyMessageIndex>0;onClicked:pane.showReplyMessage(pane.replyMessageIndex-1)}
    Text{id:messageLabel;width:parent.width-144;height:38;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;font.pixelSize:12;color:pane.city.ink;text:pane.replyMessages.length?"Response "+(pane.replyMessageIndex+1)+" / "+pane.replyMessages.length+(pane.historyBounded?" · newest "+pane.historyLimit:""):"No replies read"}
    NeonActionV2{id:messageNext;city:pane.city;width:64;text:"Newer";enabled:pane.replyMessageIndex+1<pane.replyMessages.length;onClicked:pane.showReplyMessage(pane.replyMessageIndex+1)}
   }
   Rectangle{id:replyBox;x:0;y:messageControls.y+messageControls.height+8;width:parent.width;height:Math.max(40,parent.height-y-58);radius:6;color:Qt.alpha(pane.city.ink,.035);border.color:Qt.alpha(pane.city.accent,.25)
    Text{id:replyText;anchors.fill:parent;anchors.margins:10;font.pixelSize:14;font.family:"monospace";color:pane.city.ink;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText;text:pane.replyPages[pane.replyPage]||(pane.replyMatchesSelection&&pane.reply&&pane.reply.message)||(!pane.selectedAgent?"Select an agent building or inspect Adapter status. No session content is read automatically.":"No reply fetched. Read replies requests only this exact session.")}
   }
   Row{anchors.bottom:parent.bottom;width:parent.width;spacing:8
    NeonActionV2{id:replyPrevious;city:pane.city;width:64;text:"←";enabled:pane.replyPage>0;onClicked:pane.replyPage--}
    Text{width:parent.width-144;height:34;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;font.pixelSize:12;color:pane.city.ink;text:"Text page "+(pane.replyPage+1)+" / "+pane.replyPages.length+(pane.reply&&pane.reply.truncated?" · bounded excerpt":"")}
    NeonActionV2{id:replyNext;city:pane.city;width:64;text:"→";enabled:pane.replyPage+1<pane.replyPages.length;onClicked:pane.replyPage++}
   }
  }
  Item{id:right;x:pane.wide?left.width+18:0;width:left.width;height:parent.height;visible:pane.wide||pane.view==="draft"
   Text{id:draftHeading;width:parent.width;height:34;verticalAlignment:Text.AlignVCenter;text:pane.capabilities.canSend?"INSTRUCTION / EXACT SESSION":"DRAFT / READ-ONLY SESSION";font.pixelSize:12;color:pane.city.accent}
   Rectangle{id:draftBox;x:0;y:draftHeading.height+8;width:parent.width;height:Math.max(40,parent.height-y-98);radius:6;color:Qt.alpha(pane.city.ink,.04);border.color:pane.city.accent
    Controls.TextArea{id:editor;anchors.fill:parent;anchors.margins:10;text:"";font.pixelSize:14;font.family:"monospace";color:pane.city.ink;wrapMode:TextEdit.WrapAnywhere;selectByMouse:true;placeholderText:"Enter an instruction for this selected session.";placeholderTextColor:Qt.alpha(pane.city.ink,.55);enabled:!pane.busy&&!!pane.selectedAgent; background:Item{}
     onTextChanged:pane.queueEditorChange()
     onCursorPositionChanged:{if(pane.editScheduled)pane.flushEditor();else if(!pane.syncingEditor&&!pane.editingDraft)pane.draftCursor=pane.editorPageStart+cursorPosition}
     Keys.onPressed:function(event){
      if(selectionStart!==selectionEnd)return;
      if(event.key===Qt.Key_Backspace&&cursorPosition===0&&pane.editorPageStart>0){pane.removeBoundary(true);event.accepted=true;}
      else if(event.key===Qt.Key_Delete&&cursorPosition===text.length&&pane.editorPageEnd<pane.draft.length){pane.removeBoundary(false);event.accepted=true;}
      else if(event.key===Qt.Key_Left&&cursorPosition===0&&pane.editorPageStart>0){pane.syncDraftAtCursor(pane.editorPageStart-1);event.accepted=true;}
      else if(event.key===Qt.Key_Right&&cursorPosition===text.length&&pane.editorPageEnd<pane.draft.length){pane.syncDraftAtCursor(pane.editorPageEnd+1);event.accepted=true;}
     }
    }
   }
   Row{anchors.bottom:sendButton.top;anchors.bottomMargin:8;width:parent.width;spacing:8
    NeonActionV2{city:pane.city;width:64;text:"←";enabled:!pane.busy&&pane.draftPage>0;onClicked:pane.showDraftPage(pane.draftPage-1)}
    Text{width:parent.width-144;height:34;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;font.pixelSize:12;color:pane.city.ink;text:"Draft "+(pane.draftPage+1)+" / "+pane.draftPages.length+" · "+pane.codePoints(pane.draft).length+"/8192"}
    NeonActionV2{city:pane.city;width:64;text:"→";enabled:!pane.busy&&pane.draftPage+1<pane.draftPages.length;onClicked:pane.showDraftPage(pane.draftPage+1)}
   }
   NeonActionV2{id:sendButton;anchors.bottom:parent.bottom;width:parent.width;city:pane.city;text:pane.capabilities.canSend?"Review instruction…":"Sending unavailable";primary:true;enabled:!pane.busy&&pane.submissionAvailable&&!!pane.capabilities.canSend&&!!pane.draft.trim();onClicked:pane.reviewDraft()}
  }
 }
 Item{id:noticesContent;visible:pane.showNotices;x:20;y:header.y+header.height+10;width:parent.width-40;height:Math.max(0,footer.y-y-12)
  Rectangle{anchors.fill:parent;radius:6;color:Qt.alpha(pane.city.ink,.035);border.color:Qt.alpha(pane.city.accent,.25)}
  Text{id:noticeTextItem;x:10;y:10;width:parent.width-20;height:Math.max(0,parent.height-76);font.pixelSize:14;font.family:"monospace";color:pane.city.ink;wrapMode:Text.WrapAnywhere;textFormat:Text.PlainText;text:pane.noticePages[pane.noticePage]||""}
  Row{anchors.bottom:parent.bottom;anchors.bottomMargin:10;x:10;width:parent.width-20;spacing:8
   NeonActionV2{city:pane.city;width:64;text:"←";enabled:pane.noticePage>0;onClicked:pane.noticePage--}
   Text{width:parent.width-144;height:38;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;font.pixelSize:12;color:pane.city.ink;text:"Adapter status "+(pane.noticePage+1)+" / "+pane.noticePages.length}
   NeonActionV2{city:pane.city;width:64;text:"→";enabled:pane.noticePage+1<pane.noticePages.length;onClicked:pane.noticePage++}
  }
 }
 Column{id:footer;x:20;y:parent.height-height-16;width:parent.width-40;spacing:5
  Text{width:parent.width;font.pixelSize:12;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText;text:pane.message||(pane.capabilities.reason||"Queue keeps this session’s permissions. Approvals and questions stay in its native client.")}
  Text{width:parent.width;font.pixelSize:12;color:Qt.alpha(pane.city.ink,.65);wrapMode:Text.Wrap;textFormat:Text.PlainText;text:(pane.replyMatchesSelection&&pane.reply&&pane.reply.source)||"Metadata inventory contains no chat text. Read replies is an explicit session-only request."}
 }
 Rectangle{anchors.fill:parent;visible:pane.confirming;color:pane.city.panelPaper;border.color:pane.city.accent;radius:14
  Column{anchors.centerIn:parent;width:Math.min(parent.width-40,650);spacing:14
   Text{width:parent.width;text:"Send this instruction to the exact selected session?";font.pixelSize:20;color:pane.city.ink;wrapMode:Text.Wrap}
   Text{width:parent.width;text:pane.selectedAgent?pane.selectedAgent.provider+" / "+pane.selectedAgent.id:"";font.pixelSize:14;color:pane.city.accent;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   Text{width:parent.width;text:pane.codePoints(pane.draft).length+" characters · "+pane.draftPages.length+" draft pages. Review every page before sending. Existing permissions and approval prompts remain in the native client. Queued does not mean completed.";font.pixelSize:14;color:pane.city.ink;wrapMode:Text.Wrap}
   Row{width:parent.width;spacing:10
    NeonActionV2{id:confirmButton;city:pane.city;width:(parent.width-10)/2;text:"Queue instruction";primary:true;enabled:!pane.busy&&pane.submissionAvailable&&!!pane.capabilities.canSend;onClicked:pane.queueInstruction()}
    NeonActionV2{city:pane.city;width:(parent.width-10)/2;text:"Back to draft";onClicked:pane.confirming=false}
   }
  }
 }
}
