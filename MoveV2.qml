import QtQuick
Item {
 id:modal
 required property var city
 property alias testConfirm:confirm
 property alias testCancel:cancel
 property alias testPages:list
 property alias testPanel:panel
 property alias testHeading:heading
 property alias testFooter:footer
 readonly property bool sourceCurrent:!!city.moveDraft&&city.snapshot.windows.some(function(w){var d=modal.city.moveDraft;return w.address===d.address&&w.class===d.appClass&&w.workspace===d.sourceWorkspace})
 readonly property var entries:city.scene.districts.filter(function(d){return modal.city.moveDraft&&d.id!==modal.city.moveDraft.sourceWorkspace}).map(function(d){return {key:String(d.id),label:d.name,subtitle:"D"+d.id+" / "+d.count+" windows",payload:d}})
 visible:city.moveDraft!==null
 Rectangle{anchors.fill:parent;color:"#b0020712"}
 MouseArea{anchors.fill:parent;onClicked:modal.city.cancelMove()}
 Rectangle {
  id:panel;anchors.centerIn:parent;width:Math.min(600,parent.width-32);height:Math.min(700,parent.height-32);color:modal.city.panelPaper;border.color:Qt.alpha(modal.city.accent,.5);radius:16
  MouseArea{anchors.fill:parent}
  Column{id:heading;x:16;y:16;width:parent.width-32;spacing:8
   Text{text:"MOVE / CHOOSE DISTRICT";color:modal.city.accent;font.pixelSize:13}
   Text{width:parent.width;text:modal.city.moveDraft?modal.city.moveDraft.app:"";color:modal.city.ink;font.pixelSize:18;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   Text{width:parent.width;text:"The window moves. Your current workspace stays.";color:Qt.alpha(modal.city.ink,.72);font.pixelSize:13;wrapMode:Text.Wrap}
  }
  Column{id:footer;x:16;width:parent.width-32;anchors.bottom:parent.bottom;anchors.bottomMargin:16;spacing:10
   Text{width:parent.width;text:!modal.sourceCurrent?"This window changed. Cancel and inspect it again.":modal.city.validMove()?"D"+modal.city.moveDraft.sourceWorkspace+" → "+modal.city.districtName(modal.city.moveDraft.destination):"Choose an existing destination.";color:modal.city.accent;font.pixelSize:14;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   Row{width:parent.width;spacing:10
    NeonActionV2{id:cancel;city:modal.city;width:(parent.width-10)/2;text:"Cancel";onClicked:modal.city.cancelMove()}
    NeonActionV2{id:confirm;city:modal.city;width:(parent.width-10)/2;text:"Confirm move";primary:true;enabled:modal.city.validMove()&&modal.sourceCurrent;onClicked:modal.city.confirmMove()}
   }
  }
  PagedListV2{id:list;city:modal.city;x:16;width:parent.width-32;anchors.top:heading.bottom;anchors.topMargin:12;anchors.bottom:footer.top;anchors.bottomMargin:12;entries:modal.entries;selectedKey:modal.city.moveDraft?String(modal.city.moveDraft.destination):""
   onActivated:function(entry){modal.city.chooseDestination(entry.payload.id)}
  }
 }
}
