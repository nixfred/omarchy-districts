import QtQuick
Item {
 id:list
 required property var city
 property var entries:[]
 property string selectedKey:""
 property int page:0
 property string anchorKey:""
 property alias testPrevious:previous
 property alias testNext:next
 property alias testRows:rows
 function testRow(index){return repeater.itemAt(index)}
 signal activated(var entry)
 signal paged(int index)
 FontMetrics{id:mainMetrics;font.family:"sans-serif";font.pixelSize:13}
 FontMetrics{id:subMetrics;font.family:"sans-serif";font.pixelSize:12}
 readonly property real rowHeight:{
  var usable=Math.max(100,width-24),height=58
  // A conservative bound leaves room for word wrapping and wide Unicode labels.
  entries.forEach(function(e){var a=Math.max(1,Math.ceil(mainMetrics.advanceWidth(String(e.label))*2/usable)),b=e.subtitle?Math.max(1,Math.ceil(subMetrics.advanceWidth(String(e.subtitle))*2/usable)):0;height=Math.max(height,a*mainMetrics.height+b*subMetrics.height+18)})
  return Math.ceil(height)
 }
 readonly property int capacity:Math.max(1,Math.floor((height-46+6)/(rowHeight+6)))
 readonly property int pageCount:Math.max(1,Math.ceil(entries.length/capacity))
 readonly property int visiblePage:Math.max(0,Math.min(page,pageCount-1))
 readonly property var shownEntries:entries.slice(visiblePage*capacity,(visiblePage+1)*capacity)
 function key(e){return e?String(e.key):""}
 function sync(){page=Math.max(0,Math.min(page,pageCount-1));anchorKey=key(entries[page*capacity])}
 function reconcile(){if(anchorKey){var i=entries.findIndex(function(e){return key(e)===anchorKey});if(i>=0)page=Math.floor(i/capacity)}sync()}
 function turn(delta){page=Math.max(0,Math.min(page+delta,pageCount-1));sync();paged(page*capacity)}
 function show(index){page=Math.max(0,Math.min(Math.floor(index/capacity),pageCount-1));sync()}
 onEntriesChanged:Qt.callLater(reconcile)
 onCapacityChanged:Qt.callLater(reconcile)
 Item{id:rows;width:parent.width;height:list.shownEntries.length?list.shownEntries.length*(list.rowHeight+6)-6:0
  Repeater{id:repeater;model:list.shownEntries
   Rectangle{
    required property var modelData
    required property int index
    y:index*(list.rowHeight+6);width:rows.width;height:list.rowHeight;radius:7
    color:list.selectedKey===String(modelData.key)?Qt.alpha(list.city.accent,.16):Qt.alpha(list.city.ink,.04)
    border.color:list.selectedKey===String(modelData.key)?list.city.accent:Qt.alpha(list.city.ink,.15)
    activeFocusOnTab:true
    Accessible.role:Accessible.Button;Accessible.name:String(modelData.label)+" "+String(modelData.subtitle||"")
    Rectangle{x:2;y:8;width:3;height:parent.height-16;radius:2;visible:!!parent.modelData.color;color:parent.modelData.color||list.city.accent}
    Column{anchors.verticalCenter:parent.verticalCenter;x:12;width:parent.width-24;spacing:3
     Text{width:parent.width;text:modelData.label;font.family:"sans-serif";font.pixelSize:13;color:list.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
     Text{width:parent.width;visible:!!modelData.subtitle;text:modelData.subtitle||"";font.family:"sans-serif";font.pixelSize:12;color:Qt.alpha(list.city.ink,.66);wrapMode:Text.Wrap;textFormat:Text.PlainText}
    }
    MouseArea{anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:list.activated(parent.modelData)}
    Keys.onReturnPressed:list.activated(modelData)
    Keys.onSpacePressed:list.activated(modelData)
   }
  }
  Text{visible:list.entries.length===0;width:parent.width;text:"No current entries.";font.pixelSize:13;color:list.city.ink;wrapMode:Text.Wrap}
 }
 Row{anchors.bottom:parent.bottom;width:parent.width;spacing:8
  NeonActionV2{id:previous;city:list.city;width:64;text:"Back";enabled:list.page>0;onClicked:list.turn(-1)}
  Text{width:parent.width-144;anchors.verticalCenter:parent.verticalCenter;horizontalAlignment:Text.AlignHCenter;text:(list.visiblePage+1)+" / "+list.pageCount+"\n"+list.entries.length+" entries";font.pixelSize:12;color:list.city.ink}
  NeonActionV2{id:next;city:list.city;width:64;text:"Next";enabled:list.page+1<list.pageCount;onClicked:list.turn(1)}
 }
}
