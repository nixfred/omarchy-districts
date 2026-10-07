import QtQuick
import "LensV2.js" as Lens
Item {
 id:pane
 required property var city
 property var snapshot:({windows:[],districts:[]})
 property var selectedWindow:null
 property var selectedDistrict:null
 property var lens:null
 signal selected(var lens)
 signal cleared()
 signal closed()
 property alias testReset:reset
 property alias testClose:close
 function testOption(index){return options.itemAt(index)}
 readonly property var choices:Lens.options(selectedWindow,selectedDistrict)
 readonly property var counts:Lens.counts(snapshot,lens)
 Rectangle{anchors.fill:parent;color:pane.city.panelPaper;border.color:Qt.alpha(pane.city.accent,.3);radius:12}
 Column{anchors.fill:parent;anchors.margins:14;spacing:7
  Row{width:parent.width;spacing:8
   Text{width:parent.width-88;text:"FOCUS LENS";color:pane.city.accent;font.pixelSize:12;anchors.verticalCenter:parent.verticalCenter}
   NeonActionV2{id:close;city:pane.city;width:80;text:"Close";onClicked:pane.closed()}
  }
  Text{width:parent.width;text:"Windows "+pane.counts.shownWindows+" / "+pane.counts.totalWindows+" · Districts "+pane.counts.shownDistricts+" / "+pane.counts.totalDistricts+" · Agents "+pane.counts.shownAgents+" / "+pane.counts.totalAgents;font.pixelSize:13;color:pane.city.ink;wrapMode:Text.Wrap}
  Text{width:parent.width;text:"Choose a scope. Filters this view only; real windows remain unchanged.";font.pixelSize:12;color:pane.city.ink;wrapMode:Text.Wrap}
  Grid{width:parent.width;columns:2;spacing:6
   Repeater{id:options;model:pane.choices
    NeonActionV2{required property var modelData;city:pane.city;width:(parent.width-6)/2;text:({app:"Same app",district:"This district",category:"Same category",family:"Agent family"})[modelData.kind];checked:!!pane.lens&&pane.lens.kind===modelData.kind&&pane.lens.value===modelData.value&&(pane.lens.provider||null)===(modelData.provider||null);onClicked:pane.selected(modelData)}
   }
  }
  Text{visible:pane.choices.length===0;width:parent.width;text:"Select a district or building first.";font.pixelSize:12;color:pane.city.ink;wrapMode:Text.Wrap}
  NeonActionV2{id:reset;city:pane.city;width:parent.width;text:"Show entire city";primary:true;enabled:!!pane.lens;onClicked:pane.cleared()}
 }
}
