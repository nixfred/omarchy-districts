import QtQuick
import QtTest
import "../.." as Districts
Item {
 width:912;height:512
 QtObject{id:theme;property color paper:"#111111";property color panelPaper:"#171717";property color ink:"#eeeeee";property color accent:"#80cfff"}
 Districts.ResourcesV2{id:resources;city:theme;width:320;height:330;details:({ok:true,pid:42,startTime:100,observedAt:1791288000000,residentBytes:1048576,virtualBytes:8192000,threads:4,fileDescriptors:4096,fileDescriptorsCapped:true});reported:({status:{type:"running"},statusSource:"codex app-server thread/read",observedAt:"2026-10-06T12:00:00Z",availability:"live"});cpu:({state:"measured",percent:200})}
 Districts.LensV2{id:lens;city:theme;width:320;height:330;selectedWindow:({class:"Code",app:"Code",agent:{familyId:"family"}});selectedDistrict:({id:1,group:"development",groupName:"Development"});snapshot:({windows:[{class:"Code",workspace:1}],districts:[{id:1,group:"development"}],agents:[{id:"a",provider:"codex",familyId:"family"}]})}
 SignalSpy{id:refreshSpy;target:resources;signalName:"refreshRequested"}
 SignalSpy{id:lensSpy;target:lens;signalName:"selected"}
 SignalSpy{id:resetSpy;target:lens;signalName:"cleared"}
 TestCase {
  name:"ResourcesAndLensModules";when:windowShown
  function fit(item,root){
   if(!item.visible)return
   if(item.toString().indexOf("QQuickText")>=0){verify(item.contentHeight<=item.height+.1,"text has full allocated height");verify(item.contentWidth<=item.width+.1,"text wraps to width")}
   var p=item.mapToItem(root,0,0)
   if(item.height>0&&item.width>0){verify(p.y+item.height<=root.height+.1,"bottom fits "+item+" "+(p.y+item.height));verify(p.x+item.width<=root.width+.1,"right fits")}
   for(var i=0;i<item.children.length;i++)fit(item.children[i],root)
  }
  function test_resource_pages_fit_and_controls(){
   for(var w of [320,600]){resources.width=w;wait(30);for(var i=0;i<resources.pageCount;i++){resources.page=i;wait(10);fit(resources,resources)}}
   resources.page=0;mouseClick(resources.testNext);compare(resources.page,1);mouseClick(resources.testPrevious);compare(resources.page,0);mouseClick(resources.testRefresh);compare(refreshSpy.count,1)
   resources.busy=true;mouseClick(resources.testRefresh);compare(refreshSpy.count,1);resources.busy=false
  }
  function test_resource_full_long_errors_and_sources_fit(){
   resources.width=320;resources.targetLabel="Long target ".repeat(20);resources.error="Owner changed during observation. ".repeat(6);resources.reported={status:{type:"running"},statusSource:"Provider transport source ".repeat(9),observedAt:"2026-10-06T12:00:00Z",availability:"stored"};wait(30)
   for(var i=0;i<resources.pageCount;i++){resources.page=i;wait(5);fit(resources,resources)}
   resources.error="";resources.targetLabel="Selected owner";resources.reported=null;resources.page=0
  }
  function test_lens_scopes_and_reset_fit(){
   lens.width=320;wait(30);fit(lens,lens)
   for(var i=0;i<4;i++){mouseClick(lens.testOption(i));compare(lensSpy.count,i+1)}
   lens.lens={kind:"family",value:"family"};wait(10);mouseClick(lens.testReset);compare(resetSpy.count,1)
  }
 }
}
