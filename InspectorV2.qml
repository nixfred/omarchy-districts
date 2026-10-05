import QtQuick
import QtQuick.Controls as Controls
import Quickshell
Item {
 id:pane
 required property var city
 property string view:"info"
 property alias testRename:renameButton
 property alias testName:nameInput
 property alias testSave:saveButton
 property alias testCancel:cancelButton
 property alias testPin:pinButton
 property alias testTrace:traceButton
 property alias testRelocate:relocateButton
 property alias testEnter:enterButton
 property alias testPages:pages
 property alias testInfo:infoTab
 property alias testStyle:styleTab
 property alias testApps:appsTab
 property alias testTools:toolsTab
 property alias testBody:body
 property alias testToolsContent:tools
 property alias testInfoContent:info
 property alias testStyleContent:style
 function showInfo(){view="info"}
 function showStyle(){view="style"}
 function showList(){view="list"}
 readonly property var entries:(city.district?(city.lens?city.tracedBuildings:city.currentBuildings):city.scene.districts).map(function(d){return {key:d.key?"window:"+d.key:"district:"+d.id,label:d.app||d.name,subtitle:d.app?"D"+d.workspace+" / "+(d.floating?"Floating window":"Tiled window"):"D"+d.id+" / "+d.count+" windows",payload:d}})
 Rectangle{anchors.fill:parent;color:city.panelPaper;border.color:Qt.alpha(city.accent,.22);radius:14}
 Item{id:content;anchors.fill:parent;anchors.margins:16
  Row{id:tabs;visible:!!pane.city.district&&!pane.city.nameEditing;width:parent.width;spacing:4
   NeonActionV2{id:infoTab;city:pane.city;width:(parent.width-(toolsTab.visible?12:8))/(toolsTab.visible?4:3);text:"Info";checked:pane.view==="info";onClicked:pane.showInfo()}
   NeonActionV2{id:styleTab;city:pane.city;width:infoTab.width;text:"Style";checked:pane.view==="style";onClicked:pane.showStyle()}
   NeonActionV2{id:appsTab;city:pane.city;width:infoTab.width;text:"Apps";checked:pane.view==="list";onClicked:pane.showList()}
   NeonActionV2{id:toolsTab;city:pane.city;visible:!!pane.city.selectedBuilding;width:infoTab.width;text:"Tools";checked:pane.view==="tools";onClicked:pane.view="tools"}
  }
  Item{id:body;anchors.top:tabs.visible?tabs.bottom:parent.top;anchors.topMargin:tabs.visible?12:0;anchors.bottom:parent.bottom;width:parent.width
   Column{id:info;visible:pane.view==="info"&&!!pane.city.district&&!pane.city.nameEditing;width:parent.width;spacing:10
    Text{width:parent.width;wrapMode:Text.Wrap;text:pane.city.district?"D"+pane.city.selectedDistrict+" / "+pane.city.district.groupName+(pane.city.selectedBuilding?" ↗":""):"";color:pane.city.accent;font.pixelSize:12;MouseArea{anchors.fill:parent;enabled:!!pane.city.selectedBuilding;cursorShape:Qt.PointingHandCursor;onClicked:pane.city.focusDistrict(pane.city.selectedDistrict)}}
    Row{width:parent.width;spacing:8;visible:!!pane.city.selectedBuilding
     Image{width:26;height:26;source:pane.city.selectedBuilding?Quickshell.iconPath(pane.city.selectedBuilding.icon,true):"";sourceSize:Qt.size(40,40);fillMode:Image.PreserveAspectFit}
     Text{width:parent.width-34;text:pane.city.selectedBuilding?pane.city.selectedBuilding.app:"";font.pixelSize:body.height<300?18:20;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
    }
    Text{visible:!pane.city.selectedBuilding;width:parent.width;text:pane.city.district?pane.city.district.name:"";font.pixelSize:body.height<300?18:20;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
    Text{width:parent.width;text:pane.city.selectedBuilding?(pane.city.selectedBuilding.floating?"Floating":"Tiled")+" window\n"+pane.city.selectedBuilding.width+" × "+pane.city.selectedBuilding.windowHeight+" pixels":pane.city.district?pane.city.district.count+" windows / "+({custom:"Your label",workspace:"Workspace name",apps:"Observed app mix",number:"Workspace number"})[pane.city.district.nameSource]:"";font.pixelSize:13;color:Qt.alpha(pane.city.ink,.7);wrapMode:Text.Wrap;textFormat:Text.PlainText}
    NeonActionV2{id:enterButton;city:pane.city;width:parent.width;primary:true;text:pane.city.selectedBuilding?"Enter app window ↗":"Visit workspace ↗";enabled:!pane.city.actionBusy&&!pane.city.metadataBusy;onClicked:pane.city.navigate()}

   }
   Column{id:style;visible:(pane.view==="style"||pane.city.nameEditing)&&!!pane.city.district;width:parent.width;spacing:10
    Text{text:"PERSONALIZE / D"+pane.city.selectedDistrict;color:pane.city.accent;font.pixelSize:12}
    Column{width:parent.width;spacing:10;visible:!pane.city.nameEditing
     Text{width:parent.width;text:"Your label, pin and circuit stay with this neighborhood.";font.pixelSize:13;color:pane.city.ink;wrapMode:Text.Wrap}
     NeonActionV2{id:renameButton;city:pane.city;width:parent.width;text:"Name district";enabled:!pane.city.metadataBusy;onClicked:pane.city.beginRename()}
     NeonActionV2{id:pinButton;city:pane.city;width:parent.width;text:pane.city.district&&pane.city.district.pinned?"★ Pinned":"☆ Pin district";checked:!!pane.city.district&&pane.city.district.pinned;enabled:!pane.city.metadataBusy;onClicked:pane.city.customize({pinned:!pane.city.district.pinned})}
     Text{text:"CIRCUIT";color:Qt.alpha(pane.city.ink,.66);font.pixelSize:12}
     Row{spacing:8;Repeater{model:5
      Rectangle{required property int index;width:38;height:38;radius:6;color:pane.city.neons[index];border.width:pane.city.district&&pane.city.district.tint===index?3:0;border.color:pane.city.ink;opacity:pane.city.metadataBusy?.4:1
       MouseArea{anchors.fill:parent;cursorShape:Qt.PointingHandCursor;enabled:!pane.city.metadataBusy;onClicked:pane.city.customize({tint:parent.index})}
      }
     }}
    }
    Column{width:parent.width;spacing:10;visible:pane.city.nameEditing
     Controls.TextArea{id:nameInput;width:parent.width;height:84;text:"";color:pane.city.ink;font.pixelSize:14;wrapMode:TextEdit.Wrap;selectByMouse:true;placeholderText:"Your workspace label";placeholderTextColor:Qt.alpha(pane.city.ink,.45);enabled:!pane.city.metadataBusy
      background:Rectangle{radius:6;color:Qt.alpha(pane.city.ink,.06);border.color:pane.city.accent}
      onTextChanged:{if(Array.from(text).length>48)text=Array.from(text).slice(0,48).join("");if(pane.city.nameEditing)pane.city.renameDraft=text}
      Keys.onReturnPressed:function(event){pane.city.saveRename();event.accepted=true}
      Keys.onEscapePressed:function(event){pane.city.cancelRename();event.accepted=true}
     }
     Row{width:parent.width;spacing:8
      NeonActionV2{id:saveButton;city:pane.city;width:(parent.width-8)/2;primary:true;text:pane.city.metadataBusy?"Saving…":"Save name";enabled:!pane.city.metadataBusy;onClicked:pane.city.saveRename()}
      NeonActionV2{id:cancelButton;city:pane.city;width:(parent.width-8)/2;text:"Cancel";enabled:!pane.city.metadataBusy;onClicked:pane.city.cancelRename()}
     }
     Text{width:parent.width;text:"Up to 48 visible characters. Leave blank to restore the observed name.";font.pixelSize:12;color:Qt.alpha(pane.city.ink,.7);wrapMode:Text.Wrap}
    }
    Text{width:parent.width;visible:!!pane.city.message;text:pane.city.message;font.pixelSize:12;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   }
   Column{id:tools;visible:pane.view==="tools"&&!!pane.city.selectedBuilding;width:parent.width;spacing:12
    Text{text:"WINDOW TOOLS / D"+pane.city.selectedDistrict;color:pane.city.accent;font.pixelSize:12}
    Text{width:parent.width;text:"Trace highlights this app across the city. Relocation asks for a destination and confirmation.";font.pixelSize:13;color:pane.city.ink;wrapMode:Text.Wrap}
    NeonActionV2{id:traceButton;city:pane.city;width:parent.width;text:pane.city.lens?"Clear app trace":"Trace this app";checked:!!pane.city.lens;onClicked:pane.city.traceApp()}
    NeonActionV2{id:relocateButton;city:pane.city;width:parent.width;text:"Move to district…";enabled:!pane.city.actionBusy;onClicked:pane.city.beginMove()}
   }
   Column{id:heading;visible:!pane.city.district||pane.view==="list";width:parent.width;spacing:8
    Text{text:pane.city.district?(pane.city.lens?"APP TRACE / ACROSS CITY":"WINDOWS / D"+pane.city.selectedDistrict):"YOUR CITY / NEIGHBORHOODS";color:pane.city.accent;font.pixelSize:12}
    Text{visible:!pane.city.district;width:parent.width;text:"Inspect a neighborhood. Use the atlas to find an app anywhere.";font.pixelSize:13;color:pane.city.ink;wrapMode:Text.Wrap}
   }
   PagedListV2{id:pages;city:pane.city;visible:heading.visible;anchors.top:heading.bottom;anchors.topMargin:12;anchors.bottom:parent.bottom;width:parent.width;entries:pane.entries;selectedKey:pane.city.selected?"window:"+pane.city.selected:"district:"+pane.city.selectedDistrict
    onActivated:function(entry){var d=entry.payload;if(d.key)pane.city.inspectBuilding(d.key);else pane.city.focusDistrict(d.id)}
   }
  }
 }
 Connections{target:city;function onNameEditingChanged(){if(pane.city.nameEditing){pane.showStyle();nameInput.text=pane.city.renameDraft;Qt.callLater(function(){if(pane.city.nameEditing){nameInput.forceActiveFocus();nameInput.selectAll()}})}}}
}
