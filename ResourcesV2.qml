import QtQuick
import "ResourcesV2.js" as Resources
Item {
 id:pane
 required property var city
 property var details:null
 property var reported:null
 property var cpu:null
 property string targetLabel:"Selected owner"
 property bool busy:false
 property string error:""
 property int page:0
 signal refreshRequested()
 signal closed()
 property alias testRefresh:refresh
 property alias testPrevious:previous
 property alias testNext:next
 property alias testClose:close
 readonly property var facts:Resources.paginateValues([{label:"Selected target",value:targetLabel}].concat(error?[{label:"Detail result",value:error}]:[])).concat(Resources.rows(details,reported,cpu))
 FontMetrics{id:metrics;font.pixelSize:12}
 readonly property real rowHeight:{var high=64,usable=Math.max(100,width-44);facts.forEach(function(f){high=Math.max(high,31+Math.ceil(metrics.advanceWidth(f.value)*1.6/usable)*metrics.height)});return Math.ceil(high)}
 readonly property int capacity:Math.max(1,Math.min(4,Math.floor((height-174)/(rowHeight+6))))
 readonly property int pageCount:Math.max(1,Math.ceil(facts.length/capacity))
 readonly property int visiblePage:Math.min(page,pageCount-1)
 onDetailsChanged:page=0
 Rectangle{anchors.fill:parent;color:pane.city.panelPaper;border.color:Qt.alpha(pane.city.accent,.3);radius:12}
 Column{anchors.fill:parent;anchors.margins:14;spacing:8
  Row{width:parent.width;spacing:8
   Text{width:parent.width-88;text:"OWNER DETAILS";color:pane.city.accent;font.pixelSize:12;anchors.verticalCenter:parent.verticalCenter}
   NeonActionV2{id:close;city:pane.city;width:80;text:"Close";onClicked:pane.closed()}
  }
  Text{width:parent.width;text:pane.busy?"Reading selected owner…":pane.error?"Details unavailable; select again or refresh.":"Verified owner counters / reported state";color:pane.city.ink;font.pixelSize:12;wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Column{width:parent.width;spacing:6
   Repeater{model:pane.facts.slice(pane.visiblePage*pane.capacity,(pane.visiblePage+1)*pane.capacity)
    Rectangle{required property var modelData;width:parent.width;height:pane.rowHeight;radius:6;color:Qt.alpha(pane.city.ink,.04);border.color:Qt.alpha(pane.city.ink,.12)
     Column{anchors.fill:parent;anchors.margins:8;spacing:3
      Text{width:parent.width;text:modelData.label;color:pane.city.accent;font.pixelSize:12;textFormat:Text.PlainText}
      Text{width:parent.width;text:modelData.value;color:pane.city.ink;font.pixelSize:12;wrapMode:Text.Wrap;textFormat:Text.PlainText}
     }
    }
   }
  }
 }
 Row{anchors.bottom:parent.bottom;anchors.bottomMargin:14;anchors.left:parent.left;anchors.right:parent.right;anchors.margins:14;spacing:6
  NeonActionV2{id:previous;city:pane.city;width:60;text:"Back";enabled:pane.page>0;onClicked:pane.page--}
  Text{width:parent.width-222;text:(pane.visiblePage+1)+" / "+pane.pageCount;color:pane.city.ink;font.pixelSize:12;horizontalAlignment:Text.AlignHCenter;anchors.verticalCenter:parent.verticalCenter}
  NeonActionV2{id:next;city:pane.city;width:60;text:"Next";enabled:pane.visiblePage+1<pane.pageCount;onClicked:pane.page++}
  NeonActionV2{id:refresh;city:pane.city;width:84;text:"Refresh";enabled:!pane.busy;onClicked:pane.refreshRequested()}
 }
}
