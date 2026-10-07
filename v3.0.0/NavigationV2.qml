import QtQuick
import QtQuick.Controls as Controls
import "NavigationV2.js" as Navigation
Item {
 id: navigation
 required property var city
 property bool panelOpen:false
 property string section:"views"
 property var currentCamera:({x:0,y:0,zoom:1,yaw:45,tilt:35.26438968})
 property var districts:[]
 property int targetDistrict:-1
 property var savedViews:[]
 property bool persistenceBusy:false
 property string persistenceMessage:""
 property bool motion:true
 property bool touring:false
 property var tourSequence:[]
 property int tourIndex:-1
 property string tourMessage:""
 property var history:Navigation.createHistory()
 property int historyRevision:0
 property bool replaying:false
 property bool playing:false
 property int replayIndex:0
 readonly property int frameCount:{var revision=historyRevision;return history.frames.length}
 readonly property var replayFrame:{var revision=historyRevision;return Navigation.frameAt(history,replayIndex)}
 readonly property var viewEntries:savedViews.map(function(v){return {key:v.name,label:v.name,subtitle:"Yaw "+Math.round(v.camera.yaw)+"° / Tilt "+Math.round(v.camera.tilt)+"°"+(v.targetDistrict?" / D"+v.targetDistrict:""),payload:v}})
 readonly property var eventEntries:replayFrame?replayFrame.events.map(function(e,i){return {key:String(i),label:e.kind.replace(/-/g," "),subtitle:e.source+(e.workspace?" / D"+e.workspace:"")+(e.status?" / "+Navigation.statusText(e.status):""),payload:e}}):[]
 property string selectedView:""
 property alias testPanel:panel
 property alias testName:viewName
 property alias testPages:views
 property alias testEvents:events
 property alias testSlider:scrubber
 signal cameraRequested(var camera,var targetDistrict)
 signal tourDistrictRequested(int id,bool instant)
 signal tourStopped(string reason)
 signal replayRequested(var snapshot,double timestamp)
 signal liveRequested()
 signal persistenceRequested(var request)
 function open(view){section=view||"views";panelOpen=true;if(section==="views")persistenceRequested({operation:"list"})}
 function close(){panelOpen=false}
 function acceptPersistence(result){if(result&&result.ok){savedViews=Navigation.viewpoints(result);persistenceMessage="";if(!savedViews.some(function(v){return v.name===selectedView}))selectedView=""}else persistenceMessage=result&&result.error?String(result.error).slice(0,160):"Viewpoints could not be saved."}
 function saveView(){var label=Navigation.name(viewName.text);if(!label){persistenceMessage="Give this view a name.";return}userTakeover();persistenceRequested({operation:"save",name:label,camera:Navigation.camera(currentCamera),targetDistrict:Navigation.target(targetDistrict)})}
 function selectView(entry){userTakeover();if(replaying)returnLive();selectedView=entry.name;cameraRequested(Navigation.camera(entry.camera),entry.targetDistrict);panelOpen=false}
 function chooseView(entry){selectedView=entry.name;viewName.text=entry.name}
 function deleteView(){if(selectedView)persistenceRequested({operation:"delete",name:selectedView})}
 function startTour(){if(replaying)returnLive();tourSequence=Navigation.tourIds(districts);tourIndex=-1;if(!tourSequence.length){tourMessage="No observed districts to visit.";return}touring=true;panelOpen=false;advanceTour();tourTimer.start()}
 function advanceTour(){if(!touring)return;var next=Navigation.nextTour(tourSequence,tourIndex,districts);if(!next){stopTour("Tour complete");return}tourIndex=next.index;tourMessage="D"+next.id+" / "+(tourIndex+1)+" of "+tourSequence.length;tourDistrictRequested(next.id,!motion)}
 function stopTour(reason){var wasTouring=touring;tourTimer.stop();touring=false;tourMessage=reason||"Tour stopped";if(wasTouring)tourStopped(tourMessage)}
 function userTakeover(){if(touring)stopTour("You have control");playing=false}
 function pauseTracking(){Navigation.pause(history);historyRevision++}
 function observe(snapshot,agents,timestamp){var selectedTimestamp=replaying&&replayFrame?replayFrame.timestamp:0;var changed=Navigation.observe(history,snapshot,agents,timestamp);historyRevision++;if(!replaying)replayIndex=Math.max(0,frameCount-1);else {var index=history.frames.findIndex(function(f){return f.timestamp===selectedTimestamp});if(index<0)returnLive();else replayIndex=index}return changed}
 function clearHistory(){returnLive();history=Navigation.createHistory();historyRevision++;replayIndex=0}
 function seek(index){userTakeover();replayIndex=Math.max(0,Math.min(frameCount-1,Math.floor(index)));var frame=replayFrame;if(!frame)return;replaying=true;replayRequested(JSON.parse(JSON.stringify(frame.snapshot)),frame.timestamp)}
 function playReplay(){stopTour("Tour stopped");if(!frameCount)return;if(replayIndex>=frameCount-1)replayIndex=0;seek(replayIndex);playing=true}
 function advanceReplay(){if(!playing)return;if(replayIndex>=frameCount-1){playing=false;return}replayIndex++;var frame=replayFrame;if(frame)replayRequested(JSON.parse(JSON.stringify(frame.snapshot)),frame.timestamp)}
 function returnLive(){playing=false;if(replaying){replaying=false;liveRequested()}replayIndex=Math.max(0,frameCount-1)}
 function suspend(){stopTour("Tour stopped");pauseTracking();returnLive();panelOpen=false}
 function timeLabel(value){return value?new Date(value).toISOString().replace("T"," ").slice(0,19)+" UTC":"No observations yet"}
 Timer{id:tourTimer;interval:4500;repeat:true;onTriggered:navigation.advanceTour()}
 Timer{id:playTimer;interval:1300;repeat:true;running:navigation.playing;onTriggered:navigation.advanceReplay()}
 Item {anchors.fill:parent;visible:navigation.panelOpen;z:100
  Rectangle{anchors.fill:parent;color:"#ac020712"}
  MouseArea{anchors.fill:parent;onClicked:navigation.close()}
  Rectangle{id:panel;anchors.centerIn:parent;width:Math.min(760,parent.width-32);height:Math.min(610,parent.height-32);radius:16;color:navigation.city.panelPaper;border.color:Qt.alpha(navigation.city.accent,.5)
   MouseArea{anchors.fill:parent}
   Column{id:heading;x:16;y:14;width:parent.width-32;spacing:10
    Row{width:parent.width;spacing:8
     Text{width:parent.width-90;anchors.verticalCenter:parent.verticalCenter;text:"CITY JOURNEYS";font.pixelSize:18;color:navigation.city.accent}
     NeonActionV2{city:navigation.city;width:82;text:"Close ×";onClicked:navigation.close()}
    }
    Row{width:parent.width;spacing:6
     NeonActionV2{city:navigation.city;width:(parent.width-12)/3;text:"Viewpoints";checked:navigation.section==="views";onClicked:navigation.open("views")}
     NeonActionV2{city:navigation.city;width:(parent.width-12)/3;text:"Guided tour";checked:navigation.section==="tour";onClicked:navigation.section="tour"}
     NeonActionV2{city:navigation.city;width:(parent.width-12)/3;text:"Activity replay";checked:navigation.section==="replay";onClicked:navigation.section="replay"}
    }
   }
   Item{id:content;x:16;width:parent.width-32;anchors.top:heading.bottom;anchors.topMargin:12;anchors.bottom:parent.bottom;anchors.bottomMargin:14
    Item{anchors.fill:parent;visible:navigation.section==="views"
     Column{id:viewHeading;width:parent.width;spacing:8
      Text{width:parent.width;text:"Save this camera orientation and framing. Reopening a view fits the current city; desktop windows stay put.";font.pixelSize:13;color:navigation.city.ink;wrapMode:Text.Wrap}
      Row{width:parent.width;spacing:8
       Controls.TextField{id:viewName;width:parent.width-112;height:38;maximumLength:40;placeholderText:"Name this view…";color:navigation.city.ink;font.pixelSize:14;selectByMouse:true;background:Rectangle{radius:6;color:Qt.alpha(navigation.city.ink,.05);border.color:navigation.city.accent}onAccepted:navigation.saveView()}
       NeonActionV2{city:navigation.city;width:104;enabled:!navigation.persistenceBusy;text:navigation.persistenceBusy?"Saving…":"Save view";onClicked:navigation.saveView()}
      }
      Text{width:parent.width;visible:!!navigation.persistenceMessage;text:navigation.persistenceMessage;font.pixelSize:12;color:navigation.city.ink;wrapMode:Text.Wrap;textFormat:Text.PlainText}
     }
     Row{id:viewActions;width:parent.width;anchors.bottom:parent.bottom;spacing:8
      Text{width:parent.width-312;anchors.verticalCenter:parent.verticalCenter;text:navigation.savedViews.length+" / 12 saved";font.pixelSize:12;color:navigation.city.ink;wrapMode:Text.Wrap}
      NeonActionV2{city:navigation.city;width:148;text:"Open selected";enabled:!!navigation.selectedView;onClicked:{var entry=navigation.savedViews.find(function(v){return v.name===navigation.selectedView});if(entry)navigation.selectView(entry)}}
      NeonActionV2{city:navigation.city;width:148;text:"Delete selected";enabled:!!navigation.selectedView&&!navigation.persistenceBusy;onClicked:navigation.deleteView()}
     }
     PagedListV2{id:views;city:navigation.city;width:parent.width;anchors.top:viewHeading.bottom;anchors.topMargin:10;anchors.bottom:viewActions.top;anchors.bottomMargin:8;entries:navigation.viewEntries;selectedKey:navigation.selectedView;onActivated:function(entry){navigation.chooseView(entry.payload)}}
    }
    Column{width:parent.width;spacing:14;visible:navigation.section==="tour"
     Text{width:parent.width;text:"Visit the districts observed in this city, one at a time. The tour changes only the camera. No app receives focus and no real window moves.";font.pixelSize:14;color:navigation.city.ink;wrapMode:Text.Wrap}
     Text{width:parent.width;text:navigation.districts.length+" observed districts / 4.5 seconds per stop\n"+(navigation.motion?"Smooth camera travel":"Reduced motion: instant camera steps");font.pixelSize:14;color:navigation.city.ink;wrapMode:Text.Wrap}
     Row{width:parent.width;spacing:8
      NeonActionV2{city:navigation.city;width:(parent.width-8)/2;primary:true;text:navigation.touring?"Restart tour":"Start tour";enabled:navigation.districts.length>0;onClicked:navigation.startTour()}
      NeonActionV2{city:navigation.city;width:(parent.width-8)/2;text:"Stop tour";enabled:navigation.touring;onClicked:navigation.stopTour()}
     }
     Text{width:parent.width;text:"Pan, orbit, zoom, or inspect to take over immediately. Removed districts are skipped; newly observed districts join the next tour.";font.pixelSize:13;color:navigation.city.ink;wrapMode:Text.Wrap}
     Text{width:parent.width;text:navigation.tourMessage;font.pixelSize:13;color:navigation.city.accent;wrapMode:Text.Wrap;textFormat:Text.PlainText}
    }
    Item{anchors.fill:parent;visible:navigation.section==="replay"
     Column{id:replayHeading;width:parent.width;spacing:7
      Text{width:parent.width;text:"Observed here while tracking: up to 30 minutes / 120 changes / 512 KiB in memory. No chat, titles, URLs or saved history. Replay has no current CPU telemetry.";font.pixelSize:13;color:navigation.city.ink;wrapMode:Text.Wrap}
      Text{width:parent.width;text:navigation.timeLabel(navigation.replayFrame?navigation.replayFrame.timestamp:0)+(navigation.replayFrame&&navigation.replayFrame.boundary?" / "+navigation.replayFrame.boundary.replace(/-/g," "):"")+(navigation.replayFrame&&navigation.replayFrame.snapshot.truncated?" / Limited metadata":"");font.pixelSize:12;color:navigation.city.accent;wrapMode:Text.Wrap}
      Controls.Slider{id:scrubber;width:parent.width;height:30;from:0;to:Math.max(1,navigation.frameCount-1);stepSize:1;enabled:navigation.frameCount>0;value:navigation.replayIndex;onMoved:navigation.seek(value)}
      Row{width:parent.width;spacing:6
       NeonActionV2{city:navigation.city;width:(parent.width-18)/4;text:"Previous";enabled:navigation.frameCount>0;onClicked:navigation.seek(navigation.replayIndex-1)}
       NeonActionV2{city:navigation.city;width:(parent.width-18)/4;text:navigation.playing?"Pause":"Play";enabled:navigation.frameCount>0;onClicked:if(navigation.playing)navigation.playing=false;else navigation.playReplay()}
       NeonActionV2{city:navigation.city;width:(parent.width-18)/4;text:"Next";enabled:navigation.frameCount>0;onClicked:navigation.seek(navigation.replayIndex+1)}
       NeonActionV2{city:navigation.city;width:(parent.width-18)/4;primary:true;text:"Return live";onClicked:navigation.returnLive()}
      }
     }
     Row{id:replayFoot;width:parent.width;anchors.bottom:parent.bottom;spacing:8
      Text{width:parent.width-136;anchors.verticalCenter:parent.verticalCenter;text:navigation.frameCount+" observed frames · "+Math.ceil(navigation.history.bytes/1024)+" KiB"+(navigation.history.dropped?" · Older frames expired":"");font.pixelSize:12;color:navigation.city.ink;wrapMode:Text.Wrap}
      NeonActionV2{city:navigation.city;width:128;text:"Clear history";onClicked:navigation.clearHistory()}
     }
     PagedListV2{id:events;city:navigation.city;width:parent.width;anchors.top:replayHeading.bottom;anchors.topMargin:8;anchors.bottom:replayFoot.top;anchors.bottomMargin:8;entries:navigation.eventEntries;onActivated:function(entry){}}
    }
   }
  }
 }
 Rectangle{visible:!navigation.panelOpen&&(navigation.touring||navigation.replaying);z:99;anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:8;width:Math.min(580,parent.width-32);height:46;radius:8;color:navigation.city.panelPaper;border.color:navigation.city.accent
  Row{anchors.fill:parent;anchors.margins:5;spacing:8
   Text{width:parent.width-110;anchors.verticalCenter:parent.verticalCenter;text:navigation.replaying?"HISTORICAL VIEW · "+navigation.timeLabel(navigation.replayFrame?navigation.replayFrame.timestamp:0):"TOUR · "+navigation.tourMessage;font.pixelSize:12;color:navigation.city.ink;wrapMode:Text.Wrap}
   NeonActionV2{city:navigation.city;width:102;height:36;text:navigation.replaying?"Return live":"Stop tour";onClicked:if(navigation.replaying)navigation.returnLive();else navigation.stopTour()}
  }
 }
}
