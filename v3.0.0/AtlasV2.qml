import QtQuick
import QtQuick.Controls as Controls
Item {
 id:atlas
 required property var city
 property string resultKey:""
 readonly property int resultIndex:city.atlasResults.findIndex(function(e){return resultKey===entryKey(e)})
 property alias testSearch:search
 property alias testResults:results
 property alias testPanel:panel
 property alias testHeading:heading
 property alias testHint:hint
 readonly property var entries:city.atlasResults.map(function(e){return {key:atlas.entryKey(e),label:e.label,subtitle:e.subtitle,payload:e}})
 function entryKey(e){return e?e.type+":"+e.key:""}
 function selectIndex(index){var entry=city.atlasResults[index];resultKey=entryKey(entry);if(entry)results.show(index)}
 function inspect(){if(resultIndex>=0)city.inspectResult(city.atlasResults[resultIndex])}
 visible:city.atlasOpen
 Rectangle{anchors.fill:parent;color:"#ac020712"}
 MouseArea{anchors.fill:parent;onClicked:atlas.city.closeAtlas()}
 Rectangle {
  id:panel;width:Math.min(660,parent.width-32);height:Math.min(700,parent.height-32);anchors.centerIn:parent
  color:atlas.city.panelPaper;border.color:Qt.alpha(atlas.city.accent,.5);radius:16
  MouseArea{anchors.fill:parent}
  Column{id:heading;x:16;y:16;width:parent.width-32;spacing:10
   Row{width:parent.width
    Text{width:parent.width-90;anchors.verticalCenter:parent.verticalCenter;text:"CITY ATLAS";color:atlas.city.accent;font.pixelSize:18;font.letterSpacing:2}
    NeonActionV2{city:atlas.city;text:"Close ×";onClicked:atlas.city.closeAtlas()}
   }
   Controls.TextField{id:search;width:parent.width;height:44;maximumLength:80;color:atlas.city.ink;font.pixelSize:16;selectByMouse:true;text:atlas.city.queryText;placeholderText:"Find a district or app…";placeholderTextColor:Qt.alpha(atlas.city.ink,.45)
    background:Rectangle{radius:7;color:Qt.alpha(atlas.city.ink,.05);border.color:atlas.city.accent}
    onTextEdited:{atlas.city.queryText=text;Qt.callLater(function(){atlas.selectIndex(0)})}
    onAccepted:atlas.inspect()
    Keys.onEscapePressed:function(event){atlas.city.closeAtlas();event.accepted=true}
    Keys.onDownPressed:function(event){atlas.selectIndex(Math.min(atlas.city.atlasResults.length-1,atlas.resultIndex+1));event.accepted=true}
    Keys.onUpPressed:function(event){atlas.selectIndex(Math.max(0,atlas.resultIndex-1));event.accepted=true}
    Keys.onPressed:function(event){if(event.key===Qt.Key_PageDown){atlas.selectIndex(Math.min(atlas.city.atlasResults.length-1,Math.max(0,atlas.resultIndex)+results.capacity));event.accepted=true}else if(event.key===Qt.Key_PageUp){atlas.selectIndex(Math.max(0,atlas.resultIndex-results.capacity));event.accepted=true}}

   }
   Text{width:parent.width;text:"Inspect here. Enter an app only from its passport.";color:Qt.alpha(atlas.city.ink,.7);font.pixelSize:12;wrapMode:Text.Wrap}
  }
  Text{id:hint;x:16;width:parent.width-32;anchors.bottom:parent.bottom;anchors.bottomMargin:16;text:"↑ ↓ choose / PgUp PgDn page / Enter inspect / Esc cancel";color:Qt.alpha(atlas.city.ink,.66);font.pixelSize:12;wrapMode:Text.Wrap}
  PagedListV2{id:results;city:atlas.city;x:16;width:parent.width-32;anchors.top:heading.bottom;anchors.topMargin:12;anchors.bottom:hint.top;anchors.bottomMargin:12;entries:atlas.entries;selectedKey:atlas.resultKey
   onPaged:function(index){atlas.selectIndex(index)}
   onActivated:function(entry){atlas.resultKey=entry.key;atlas.city.inspectResult(entry.payload)}
  }
 }
 Connections{target:city;function onAtlasOpenChanged(){if(atlas.city.atlasOpen)Qt.callLater(function(){atlas.selectIndex(0);search.forceActiveFocus();search.selectAll()})}}
}
