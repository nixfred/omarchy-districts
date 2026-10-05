import QtQuick
import QtQuick.Controls as Controls
import "GroupsV2.js" as Groups
Item {
 id:legend
 required property var city
 property string view:"groups"
 property string groupKey:"development"
 property var ruleApp:null
 property alias testPages:pages
 property alias testPanel:panel
 property alias testBody:body
 function testRule(index){return ruleRepeater.itemAt(index)}
 property alias testColor:colorInput
 property alias testColorSave:colorSave
 property alias testReset:colorReset
 property alias testRules:rulesButton
 property alias testBack:backButton
 property alias testRuleContent:ruleContent
 property alias testColorContent:colorContent
 readonly property var groupEntries:Groups.groups.map(function(g){return {key:g.key,label:g.name,color:Groups.color(g.key,legend.city.groupingPreferences),subtitle:legend.city.scene.districts.filter(function(d){return d.group===g.key}).length+" districts / Edit group color",payload:g}})
 readonly property var appEntries:Groups.appEntries(city.snapshot,city.groupingPreferences)
 function showGroups(){view="groups";ruleApp=null}
 function editColor(key){groupKey=key;colorInput.text=Groups.color(key,city.groupingPreferences);view="color"}
 function showRules(){view="rules";ruleApp=null}
 function editRule(app){ruleApp=app;view="rule"}
 function back(){if(view==="color")showGroups();else if(view==="rule")showRules();else showGroups()}
 visible:city.legendOpen
 Rectangle{anchors.fill:parent;color:"#ac020712"}
 MouseArea{anchors.fill:parent;onClicked:legend.city.closeLegend()}
 Rectangle {
  id:panel;anchors.centerIn:parent;width:Math.min(660,parent.width-32);height:Math.min(700,parent.height-32);radius:16;color:legend.city.panelPaper;border.color:Qt.alpha(legend.city.accent,.5)
  MouseArea{anchors.fill:parent}
  Row{id:header;x:16;y:16;width:parent.width-32;spacing:8
   NeonActionV2{id:backButton;city:legend.city;visible:legend.view!=="groups";width:64;text:"Back";onClicked:legend.back()}
   Text{width:parent.width-90-(backButton.visible?72:0);anchors.verticalCenter:parent.verticalCenter;text:legend.view==="groups"?"GROUP CITIES":legend.view==="rules"?"APP RULES":legend.view==="color"?Groups.info(legend.groupKey).name:"APP GROUP";font.pixelSize:18;color:legend.city.accent;wrapMode:Text.Wrap}
   NeonActionV2{city:legend.city;width:82;text:"Close ×";onClicked:legend.city.closeLegend()}
  }
  Item{id:body;x:16;width:parent.width-32;anchors.top:header.bottom;anchors.topMargin:12;anchors.bottom:parent.bottom;anchors.bottomMargin:16
   Column{id:heading;width:parent.width;spacing:8;visible:legend.view==="groups"||legend.view==="rules"
    Text{width:parent.width;text:legend.view==="groups"?"Same activity, same color. These cities group the view; your real workspaces stay put.":"An app rule changes grouping wherever that public app identity appears.";font.pixelSize:13;color:legend.city.ink;wrapMode:Text.Wrap}
    NeonActionV2{id:rulesButton;city:legend.city;visible:legend.view==="groups";width:parent.width;text:"Edit app grouping rules…";onClicked:legend.showRules()}
   }
   PagedListV2{id:pages;city:legend.city;visible:heading.visible;width:parent.width;anchors.top:heading.bottom;anchors.topMargin:12;anchors.bottom:parent.bottom;entries:legend.view==="groups"?legend.groupEntries:legend.appEntries
    onActivated:function(entry){if(legend.view==="groups")legend.editColor(entry.key);else legend.editRule(entry.payload)}
   }
   Column{id:colorContent;visible:legend.view==="color";width:parent.width;spacing:12
    Text{width:parent.width;text:"All districts in this group inherit its color. Existing personal circuit accents stay preserved.";font.pixelSize:13;color:legend.city.ink;wrapMode:Text.Wrap}
    Row{width:parent.width;spacing:12
     Rectangle{width:44;height:44;radius:8;color:Groups.color(legend.groupKey,legend.city.groupingPreferences);border.color:legend.city.ink}
     Controls.TextField{id:colorInput;width:parent.width-56;height:44;maximumLength:7;font.pixelSize:16;color:legend.city.ink;selectByMouse:true;placeholderText:"#57dfff";background:Rectangle{radius:7;color:Qt.alpha(legend.city.ink,.05);border.color:legend.city.accent}}
    }
    Row{width:parent.width;spacing:8
     NeonActionV2{id:colorSave;city:legend.city;width:(parent.width-8)/2;text:legend.city.groupingBusy?"Saving…":"Save group color";primary:true;enabled:!legend.city.groupingBusy;onClicked:legend.city.updateGrouping({group:legend.groupKey,color:colorInput.text})}
     NeonActionV2{id:colorReset;city:legend.city;width:(parent.width-8)/2;text:"Default color";enabled:!legend.city.groupingBusy;onClicked:{colorInput.text=Groups.info(legend.groupKey).color;legend.city.updateGrouping({group:legend.groupKey,color:"default"})}}
    }
    Text{width:parent.width;text:"Each group uses a distinct color. Activity apps take priority over terminals and unidentified browsers. A tie becomes Mixed / Unclassified.";font.pixelSize:12;color:Qt.alpha(legend.city.ink,.75);wrapMode:Text.Wrap}
    Text{width:parent.width;visible:!!legend.city.district;text:legend.city.district?"Selected D"+legend.city.district.id+" / "+legend.city.district.groupName+"\n"+legend.city.district.groupReason+(legend.city.district.groupPending?"\nWaiting for the new activity to settle.":""):"";font.pixelSize:12;color:legend.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
    Text{width:parent.width;visible:!!legend.city.groupingMessage;text:legend.city.groupingMessage;font.pixelSize:12;color:legend.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   }
   Column{id:ruleContent;visible:legend.view==="rule";width:parent.width;spacing:8
    Text{width:parent.width;text:legend.ruleApp?legend.ruleApp.app:"";font.pixelSize:16;color:legend.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
    Text{width:parent.width;text:legend.ruleApp?legend.ruleApp.class:"";font.pixelSize:12;color:Qt.alpha(legend.city.ink,.7);wrapMode:Text.Wrap;textFormat:Text.PlainText}
    Text{width:parent.width;text:"Choose a reusable app rule. Automatic restores public app-role detection.";font.pixelSize:12;color:legend.city.ink;wrapMode:Text.Wrap}
    Grid{width:parent.width;columns:2;spacing:6
     Repeater{id:ruleRepeater;model:[{key:"auto",name:"Automatic"}].concat(Groups.groups)
      NeonActionV2{required property var modelData;city:legend.city;width:(parent.width-6)/2;text:modelData.name;checked:legend.ruleApp?((legend.city.groupingPreferences.rules[Groups.identity(legend.ruleApp)]||"auto")===modelData.key):false;enabled:!legend.city.groupingBusy
       onClicked:if(legend.ruleApp)legend.city.updateGrouping({app:legend.ruleApp.class,rule:modelData.key})
      }
     }
    }
    Text{width:parent.width;visible:!!legend.city.groupingMessage;text:legend.city.groupingMessage;font.pixelSize:12;color:legend.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
   }
  }
 }
 Connections{target:city;function onLegendOpenChanged(){if(legend.city.legendOpen){legend.showGroups();legend.city.groupingMessage=""}}}
}
