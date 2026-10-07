import QtQuick
Rectangle {
  id:control
  required property var city
  property string text:""
  property bool primary:false
  property bool checked:false
  signal clicked()
  implicitWidth:caption.implicitWidth+28;implicitHeight:38
  height:38;radius:7;activeFocusOnTab:true
  opacity:enabled?1:.4
  color:primary||checked?Qt.alpha(city.accent,.16):mouse.containsMouse?Qt.alpha(city.ink,.10):Qt.alpha(city.ink,.04)
  border.color:activeFocus?city.ink:primary||checked?Qt.alpha(city.accent,.7):Qt.alpha(city.ink,.16)
  border.width:activeFocus?2:1
  Accessible.role:Accessible.Button;Accessible.name:text
  Text{id:caption;anchors.centerIn:parent;width:Math.min(implicitWidth,parent.width-20);text:control.text;color:control.primary||control.checked?control.city.accent:control.city.ink;font.pixelSize:12;elide:Text.ElideRight;textFormat:Text.PlainText}
  MouseArea{id:mouse;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:control.clicked()}
  Keys.onReturnPressed:clicked()
  Keys.onSpacePressed:clicked()
}
