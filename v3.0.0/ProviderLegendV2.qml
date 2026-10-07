import QtQuick
import "ProviderLegendV2.js" as Providers
Item {
 id:pane
 required property var city
 property var records:[]
 property var agents:[]
 property string activeProvider:""
 property string selectedProvider:"codex"
 property int windowIndex:-1
 property int detailPage:0
 property real nowMs:Date.now()
 property bool liveClock:true
 signal providerSelected(string provider)
 signal cleared()
 signal refreshRequested()
 signal closed()
 property alias testReset:reset
 property alias testNext:next
 property alias testPrevious:previous
 property alias testNextWindow:nextWindow
 property alias testWait:waitText
 property alias testHeadline:headline
 property alias testRecovery:recoveryText
 property alias testFooter:footer
 property alias testRows:factRows
 function testProvider(index){return providerCards.itemAt(index)}
 readonly property var cards:Providers.cards(records,agents,nowMs)
 readonly property var selected:cards.find(function(c){return c.id===pane.selectedProvider})||cards[0]
 readonly property int visibleWindow:windowIndex<0?selected.primaryIndex:Math.max(0,Math.min(windowIndex,selected.windows.length-1))
 readonly property var windowMetric:selected.windows[visibleWindow]||null
 readonly property var metric:windowMetric?Providers.normalizeMetric(windowMetric,nowMs):selected.metric
 readonly property var rows:Providers.detailRows(selected,windowMetric,nowMs)
 FontMetrics{id:metrics;font.pixelSize:12}
 readonly property real rowHeight:{var result=62,usable=Math.max(100,width-44);rows.forEach(function(r){result=Math.max(result,31+Math.ceil(metrics.advanceWidth(r.value)*1.6/usable)*metrics.height)});return Math.ceil(result)}
 readonly property int capacity:Math.max(1,Math.min(3,Math.floor((height-362)/(rowHeight+5))))
 readonly property int pageCount:Math.max(1,Math.ceil(rows.length/capacity))
 onActiveProviderChanged:if(Providers.identity(activeProvider))selectedProvider=activeProvider
 onSelectedProviderChanged:{windowIndex=-1;detailPage=0}
 onRecordsChanged:detailPage=Math.min(detailPage,pageCount-1)
 Timer{interval:30000;running:pane.visible&&pane.liveClock;repeat:true;onTriggered:pane.nowMs=Date.now()}
 Rectangle{anchors.fill:parent;color:pane.city.panelPaper;border.color:Qt.alpha(pane.city.accent,.3);radius:12}
 Column{anchors.fill:parent;anchors.margins:12;spacing:4
  Row{width:parent.width;spacing:8
   Text{width:parent.width-280;text:"PROVIDERS / QUOTA PACE";font.pixelSize:12;color:pane.city.accent;anchors.verticalCenter:parent.verticalCenter}
   NeonActionV2{id:reset;city:pane.city;width:96;height:30;text:"All providers";enabled:!!pane.activeProvider;onClicked:{pane.cleared();pane.providerSelected("")}}
   NeonActionV2{city:pane.city;width:80;height:30;text:"Refresh";onClicked:pane.refreshRequested()}
   NeonActionV2{city:pane.city;width:80;height:30;text:"Close";onClicked:pane.closed()}
  }
  Row{width:parent.width;spacing:6
   Repeater{id:providerCards;model:pane.cards
    Rectangle{required property var modelData;width:(parent.width-18)/4;height:44;radius:6;color:Qt.alpha(pane.city.ink,.04);border.color:pane.activeProvider===modelData.id?pane.city.accent:Qt.alpha(pane.city.ink,.15);border.width:pane.activeProvider===modelData.id?2:1;activeFocusOnTab:true
     Rectangle{x:0;y:5;width:3;height:parent.height-10;radius:1;color:parent.modelData.color}
     Column{anchors.centerIn:parent;width:parent.width-14;spacing:3
      Text{width:parent.width;text:modelData.name;color:pane.city.ink;font.pixelSize:12;font.bold:true;textFormat:Text.PlainText}
      Text{width:parent.width;text:modelData.count+" sessions";color:Qt.alpha(pane.city.ink,.75);font.pixelSize:12;textFormat:Text.PlainText}
     }
     function choose(){pane.selectedProvider=modelData.id;pane.providerSelected(modelData.id)}
     Accessible.role:Accessible.Button;Accessible.name:modelData.name+" filter, "+modelData.count+" sessions"
     MouseArea{anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:parent.choose()}
     Keys.onReturnPressed:choose()
     Keys.onSpacePressed:choose()
    }
   }
  }
  Text{width:parent.width;text:pane.selected.name+" · "+(pane.windowMetric&&pane.windowMetric.label||"Quota unavailable");font.pixelSize:12;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Text{id:headline;width:parent.width;text:pane.metric.headline;font.pixelSize:26;font.bold:true;color:pane.metric.state==='measured'&&pane.metric.signedSeconds!==null?pane.city.accent:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Text{id:waitText;width:parent.width;text:pane.metric.wait;font.pixelSize:14;font.bold:pane.metric.paceState==='behind';color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Text{id:recoveryText;visible:!!pane.metric.recoveryClock;width:parent.width;text:pane.metric.recoveryClock?'Estimated back on pace at '+pane.metric.recoveryClock:'';font.pixelSize:12;font.bold:true;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Text{width:parent.width;text:"As of "+pane.metric.observed+". Pace-equivalent allowance credit; no guaranteed compute time.";font.pixelSize:12;color:Qt.alpha(pane.city.ink,.75);wrapMode:Text.Wrap;textFormat:Text.PlainText}
  Column{id:factRows;width:parent.width;spacing:5
   Repeater{model:pane.rows.slice(pane.detailPage*pane.capacity,(pane.detailPage+1)*pane.capacity)
    Rectangle{required property var modelData;width:parent.width;height:pane.rowHeight;radius:5;color:Qt.alpha(pane.city.ink,.04)
     Column{anchors.fill:parent;anchors.margins:8;spacing:3
      Text{width:parent.width;text:modelData.label;font.pixelSize:12;color:pane.city.accent;textFormat:Text.PlainText}
      Text{width:parent.width;text:modelData.value;font.pixelSize:12;color:pane.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
     }
    }
   }
  }
 }
 Row{id:footer;anchors.bottom:parent.bottom;anchors.left:parent.left;anchors.right:parent.right;anchors.margins:14;spacing:6
  NeonActionV2{id:previous;city:pane.city;width:60;height:30;text:"Back";enabled:pane.detailPage>0;onClicked:pane.detailPage--}
  Text{width:parent.width-260;text:(pane.detailPage+1)+" / "+pane.pageCount;font.pixelSize:12;color:pane.city.ink;horizontalAlignment:Text.AlignHCenter;anchors.verticalCenter:parent.verticalCenter}
  NeonActionV2{id:next;city:pane.city;width:60;height:30;text:"Next";enabled:pane.detailPage+1<pane.pageCount;onClicked:pane.detailPage++}
  NeonActionV2{id:nextWindow;city:pane.city;width:122;height:30;text:"Window "+(pane.visibleWindow+1)+" / "+Math.max(1,pane.selected.windows.length);enabled:pane.selected.windows.length>1;onClicked:{pane.windowIndex=(pane.visibleWindow+1)%pane.selected.windows.length;pane.detailPage=0}}
 }
}
