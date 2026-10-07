import QtQuick
Item {
 id:modal
 required property var city
 property var plan:null
 property var receipt:null
 property bool busy:false
 property string error:""
 property int nowSeconds:Math.floor(Date.now()/1000)
 readonly property bool expired:!!plan&&nowSeconds>=plan.expiresAt
 readonly property var entries:receipt?(receipt.items||[]).map(function(row,index){return {key:String(index),label:row.app+" / D"+row.sourceWorkspace+" → D"+row.destinationWorkspace,subtitle:row.status.toUpperCase()+" / "+row.message}}):plan?(plan.moves||[]).map(function(row,index){return {key:String(index),label:row.app+" / D"+row.sourceWorkspace+" → D"+row.destinationWorkspace,subtitle:"Source "+row.sourceCount+" → "+row.sourceAfter+" · destination "+row.destinationCount+" → "+row.destinationAfter+" windows after this plan / "+row.reason}}):[]
 signal applyRequested(string planId)
 signal cancelRequested()
 signal refreshRequested()
 property alias testApply:confirm
 property alias testCancel:cancel
 property alias testRefresh:refresh
 property alias testPages:list
 property alias testPanel:panel
 property alias testHeading:heading
 property alias testFooter:footer
 visible:plan!==null||receipt!==null||error!==""||busy
 Timer{interval:1000;repeat:true;running:modal.visible&&!modal.receipt;onTriggered:modal.nowSeconds=Math.floor(Date.now()/1000)}
 Rectangle{anchors.fill:parent;color:"#b0020712"}
 MouseArea{anchors.fill:parent;onClicked:if(!modal.busy)modal.cancelRequested()}
 Rectangle{
  id:panel;anchors.centerIn:parent;width:Math.min(860,parent.width-32);height:Math.min(720,parent.height-32);color:modal.city.panelPaper;border.color:Qt.alpha(modal.city.accent,.5);radius:16
  MouseArea{anchors.fill:parent}
  Column{id:heading;x:16;y:14;width:parent.width-32;spacing:5
   Text{text:modal.receipt?"ORGANIZE / RESULT":"ORGANIZE / EXACT PREVIEW";color:modal.city.accent;font.pixelSize:13}
   Text{width:parent.width;text:modal.receipt?modal.receipt.applied+" / "+modal.receipt.total+" moves confirmed":modal.busy&&!modal.plan?"Preparing current-window preview…":modal.plan?(modal.plan.moves.length?modal.plan.moves.length+" proposed moves":"No safe consolidation suggested"):"Preview unavailable";color:modal.city.ink;font.pixelSize:18;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   Text{width:parent.width;text:modal.receipt?"Each result below is confirmed, blocked, unconfirmed or not attempted. No automatic undo.":"Review each public app and exact D-number route. Nothing moves until Apply. Named/pinned districts and focused windows stay.";color:Qt.alpha(modal.city.ink,.72);font.pixelSize:13;wrapMode:Text.Wrap;textFormat:Text.PlainText}
  }
  Column{id:footer;x:16;width:parent.width-32;anchors.bottom:parent.bottom;anchors.bottomMargin:14;spacing:7
   Text{width:parent.width;text:modal.error|| (modal.receipt?modal.receipt.message:modal.busy?"Applying approved moves; checking the desktop before each move…":modal.expired?"This preview expired. Preview again before applying.":modal.plan?(modal.plan.omitted+" unsupported entries excluded · "+modal.plan.protectedDistricts+" protected districts · "+modal.plan.deferred+" proposals deferred. Any affected-district change stops Apply."):"Prepare a fresh preview.");color:modal.city.accent;font.pixelSize:13;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   Row{width:parent.width;spacing:10
    NeonActionV2{id:cancel;city:modal.city;width:(parent.width-20)/3;text:modal.receipt?"Done":"Cancel";enabled:!modal.busy;onClicked:modal.cancelRequested()}
    NeonActionV2{id:refresh;city:modal.city;width:(parent.width-20)/3;text:"Preview again";enabled:!modal.busy;onClicked:modal.refreshRequested()}
    NeonActionV2{id:confirm;city:modal.city;width:(parent.width-20)/3;text:modal.busy?"Applying…":"Apply "+(modal.plan?modal.plan.moves.length:0)+" moves";primary:true;enabled:!modal.busy&&!modal.receipt&&!!modal.plan&&modal.plan.moves.length>0&&!modal.expired&&!modal.error;onClicked:modal.applyRequested(modal.plan.planId)}
   }
  }
  PagedListV2{id:list;city:modal.city;x:16;width:parent.width-32;anchors.top:heading.bottom;anchors.topMargin:12;anchors.bottom:footer.top;anchors.bottomMargin:12;entries:modal.entries}
 }
}
