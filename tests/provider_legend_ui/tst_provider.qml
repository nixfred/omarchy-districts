import QtQuick
import QtTest
import "../.." as Districts
Item {
 width:912;height:512
 QtObject{id:theme;property color panelPaper:"#171717";property color ink:"#eeeeee";property color accent:"#80cfff"}
 Districts.ProviderLegendV2{id:pane;city:theme;width:560;height:460;liveClock:false;nowMs:1791328800000;agents:[{provider:"grok"},{provider:"claude"},{provider:"codex"},{provider:"pi",isKimi3:true}]}
 SignalSpy{id:filterSpy;target:pane;signalName:"providerSelected"}
 SignalSpy{id:clearSpy;target:pane;signalName:"cleared"}
 TestCase {
  name:"ProviderLegendPacing";when:windowShown
  function metric(seconds){return {label:"Weekly (7-day)",state:"measured",freshness:"fresh",unit:"fraction",allowanceUsed:.2,allowanceRemaining:.8,source:"Verified provider quota snapshot",observedAt:pane.nowMs,resetAt:pane.nowMs+10000000,pace:{state:seconds>0?"banked":seconds<0?"behind":"on-pace",signedSeconds:seconds,source:"Verified provider quota snapshot",formula:"Declared fixed allowance window",meaning:"pace-equivalent allowance credit",fixedWindow:true}}}
  function fit(item,root){
   if(!item.visible)return
   if(item.toString().indexOf("QQuickText")>=0){verify(item.contentHeight<=item.height+.1,"full text height "+item.text);verify(item.contentWidth<=item.width+.1,"full text width "+item.text)}
   var p=item.mapToItem(root,0,0)
   if(item.height>0&&item.width>0){verify(p.y+item.height<=root.height+.1,"bottom fits "+item+" "+(p.y+item.height));verify(p.x+item.width<=root.width+.1,"right fits")}
   for(var i=0;i<item.children.length;i++)fit(item.children[i],root)
  }
  function pages(){for(var page=0;page<pane.pageCount;page++){pane.detailPage=page;wait(5);fit(pane,pane);verify(pane.testRows.mapToItem(pane,0,0).y+pane.testRows.height<=pane.testFooter.y-4,"detail content stays above footer")}}
  function test_all_source_states_fit(){
   for(var width of [560,900]){pane.width=width;for(var seconds of [5400,-5400,0]){var m=metric(seconds);pane.records=[{provider:"codex",metric:m,windows:[m]}];pane.detailPage=0;wait(30);pages()}}
   pane.width=560;pane.records=[];wait(30);pages();verify(pane.testHeadline.text.includes("unavailable"));var stale=metric(5400);stale.freshness="stale";pane.records=[{provider:"codex",metric:stale,windows:[stale]}];wait(30);pages();verify(pane.testHeadline.text.includes("stale"))
  }
  function test_filter_reset_windows_and_paginated_metadata(){
   pane.width=560;var first=metric(-5400),second=metric(5400);first.source="Complete provider observation source ".repeat(4);pane.records=[{provider:"codex",metric:first,windows:[first,second]}];pane.selectedProvider="codex";pane.windowIndex=0;pane.detailPage=0;wait(30);pages();verify(pane.testWait.text.includes("if no additional usage"));mouseClick(pane.testNextWindow,pane.testNextWindow.width/2,15);compare(pane.windowIndex,1);pane.detailPage=0;mouseClick(pane.testNext,pane.testNext.width/2,15);compare(pane.detailPage,1);mouseClick(pane.testPrevious,pane.testPrevious.width/2,15);compare(pane.detailPage,0)
   for(var i=0;i<4;i++){mouseClick(pane.testProvider(i),40,25);compare(filterSpy.count,i+1);compare(filterSpy.signalArguments[i][0],["grok","claude","codex","kimi"][i])}
   pane.activeProvider="kimi";mouseClick(pane.testReset,40,15);compare(clearSpy.count,1)
  }
 }
}
