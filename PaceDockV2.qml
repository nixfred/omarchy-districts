import QtQuick
import "ProviderLegendV2.js" as Providers
// Persistent side legend: BANKED / ON PACE / BEHIND first, then the wait and the
// local return clock. Never scrolls; cards tighten to the space the city leaves.
Item {
 id:dock
 required property var city
 property var records:[]
 property var agents:[]
 property string activeProvider:""
 property real nowMs:Date.now()
 property real maxHeight:400
 // Narrow stages get a 140px dock: state + amount, then provider + return clock.
 property bool mini:false
 signal providerSelected(string provider)
 signal detailsRequested()
 signal hideRequested()
 readonly property var model:Providers.dock(records,agents,nowMs)
 // Card height steps down (clock line, then wait line) rather than overflow. On a
 // very short stage, cards that still do not fit fold into the text line below.
 readonly property real headerHeight:24
 readonly property real noteReserve:model.note?32:0
 readonly property real cardRoom:Math.max(0,maxHeight-headerHeight-noteReserve-16)
 readonly property int measuredCount:model.cards.length
 readonly property int detail:mini?-1:measuredCount===0?2:cardRoom>=measuredCount*80?2:cardRoom>=measuredCount*62?1:0
 readonly property real cardHeight:detail===-1?42:detail===2?74:detail===1?56:30
 readonly property int cardCount:Math.min(measuredCount,Math.floor((cardRoom-(measuredCount*(cardHeight+6)>cardRoom&&!model.note?32:0))/(cardHeight+6)))
 readonly property var folded:model.cards.slice(cardCount).map(function(c){return c.name+" "+c.state+" "+c.amount})
 readonly property string noteLine:folded.concat(model.note?[model.note]:[]).join(" · ")
 readonly property real noteHeight:noteLine?noteText.implicitHeight+6:0
 property alias testCards:cards
 property alias testNote:noteText
 width:mini?140:city.ui&&city.ui.compact?208:232
 height:Math.min(maxHeight,headerHeight+noteHeight+cardCount*(cardHeight+6)+16)
 Timer{interval:30000;running:dock.visible;repeat:true;onTriggered:dock.nowMs=Date.now()}
 Rectangle{anchors.fill:parent;radius:10;color:Qt.alpha(dock.city.panelPaper,.93);border.color:Qt.alpha(dock.city.accent,.35)}
 MouseArea{anchors.fill:parent;hoverEnabled:true;acceptedButtons:Qt.NoButton}
 Column{anchors.fill:parent;anchors.margins:8;spacing:6
  Item{width:parent.width;height:dock.headerHeight-6
   Text{anchors.verticalCenter:parent.verticalCenter;text:dock.mini?"PACE":"QUOTA PACE";font.pixelSize:11;font.letterSpacing:1.5;color:dock.city.accent}
   Row{anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter;spacing:4
    Text{id:detailsLink;text:"Details";font.pixelSize:11;color:dock.city.ink;opacity:detailsArea.containsMouse?1:.7;MouseArea{id:detailsArea;anchors.fill:parent;anchors.margins:-4;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:dock.detailsRequested()}}
    Text{text:"  ×";font.pixelSize:12;color:dock.city.ink;opacity:hideArea.containsMouse?1:.6;Accessible.role:Accessible.Button;Accessible.name:"Hide quota pace dock";MouseArea{id:hideArea;anchors.fill:parent;anchors.margins:-4;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:dock.hideRequested()}}
   }
  }
  Repeater{id:cards;model:dock.model.cards.slice(0,dock.cardCount)
   Rectangle{id:card;required property var modelData;width:parent.width;height:dock.cardHeight;radius:7
    readonly property bool behind:modelData.paceState==='behind'
    readonly property color stateColor:behind?"#ff6b6b":modelData.paceState==='banked'?"#5be49b":dock.city.accent
    color:Qt.alpha(stateColor,dock.activeProvider===modelData.id?.18:.08);border.color:dock.activeProvider===modelData.id?dock.city.accent:Qt.alpha(stateColor,.45);border.width:dock.activeProvider===modelData.id?2:1
    Rectangle{x:0;y:6;width:3;height:parent.height-12;radius:1;color:card.modelData.color}
    Column{x:10;y:6;width:parent.width-16;spacing:1
     Row{width:parent.width;spacing:6;visible:dock.detail>=0
      Text{id:stateText;text:card.modelData.state;font.pixelSize:dock.detail===0?14:17;font.bold:true;color:card.stateColor;textFormat:Text.PlainText}
      Text{id:amountText;anchors.baseline:stateText.baseline;text:card.modelData.amount;font.pixelSize:dock.detail===0?12:14;font.bold:true;color:dock.city.ink;textFormat:Text.PlainText}
      Text{anchors.baseline:stateText.baseline;width:parent.width-stateText.width-amountText.width-12;horizontalAlignment:Text.AlignRight;elide:Text.ElideRight;text:card.modelData.name;font.pixelSize:11;color:Qt.alpha(dock.city.ink,.75);textFormat:Text.PlainText}
     }
     Row{visible:dock.detail===-1;width:parent.width;spacing:5
      Text{id:miniState;text:card.modelData.state;font.pixelSize:13;font.bold:true;color:card.stateColor;textFormat:Text.PlainText}
      Text{anchors.baseline:miniState.baseline;text:card.modelData.amount;font.pixelSize:12;font.bold:true;color:dock.city.ink;textFormat:Text.PlainText}
     }
     Text{visible:dock.detail===-1;width:parent.width;elide:Text.ElideRight;text:card.modelData.name+(card.modelData.clockShort?" · "+card.modelData.clockShort:"");font.pixelSize:11;color:Qt.alpha(dock.city.ink,.85);textFormat:Text.PlainText}
     Text{visible:dock.detail>=1;width:parent.width;elide:Text.ElideRight;text:card.modelData.wait;font.pixelSize:12;font.bold:card.behind;color:dock.city.ink;textFormat:Text.PlainText}
     Text{visible:dock.detail>=2;width:parent.width;elide:Text.ElideRight;text:card.modelData.clock||card.modelData.window;font.pixelSize:11;color:Qt.alpha(dock.city.ink,card.modelData.clock?.95:.6);textFormat:Text.PlainText}
    }
    Accessible.role:Accessible.Button;Accessible.name:modelData.name+" "+modelData.state+" "+modelData.amount+". "+modelData.wait
    MouseArea{anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:dock.providerSelected(dock.activeProvider===card.modelData.id?"":card.modelData.id)}
   }
  }
  Text{id:noteText;visible:!!dock.noteLine;width:parent.width;wrapMode:Text.Wrap;maximumLineCount:2;elide:Text.ElideRight;text:dock.noteLine;font.pixelSize:11;color:Qt.alpha(dock.city.ink,.6);textFormat:Text.PlainText}
 }
}
