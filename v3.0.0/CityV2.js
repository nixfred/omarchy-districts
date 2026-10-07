.pragma library

function clamp(v, a, b) { return Math.max(a, Math.min(b, Number(v) || 0)) }
function hash(text) { var n=2166136261; for(var i=0;i<String(text).length;i++)n=Math.imul(n^String(text).charCodeAt(i),16777619);return n>>>0 }
function mix(a,b,t) { return a+(b-a)*t }
// The default orbit preserves the original isometric composition. Camera objects are
// explicit arguments so multiple plugin/fixture instances cannot change one another.
function orbit(camera) {
  if(camera&&camera._projection===true)return camera
  var yaw=Number(camera&&camera.yaw),tilt=Number(camera&&camera.tilt)
  if(!camera||camera.yaw===undefined||!isFinite(yaw))yaw=45
  if(!camera||camera.tilt===undefined||!isFinite(tilt))tilt=35.264389682754654
  yaw=((yaw%360)+360)%360;tilt=clamp(tilt,20,75)
  var a=yaw*Math.PI/180,e=tilt*Math.PI/180
  return {_projection:true,yaw:yaw,tilt:tilt,c:Math.cos(a),s:Math.sin(a),se:Math.sin(e),ce:Math.cos(e),scale:Math.sqrt(1.5),interactive:!!(camera&&camera.interactive)}
}
function project(x,y,z,camera) {
  var c=orbit(camera),height=Number(z)||0
  return {x:c.scale*(c.c*x-c.s*y),y:c.scale*(c.se*(c.s*x+c.c*y)-c.ce*height),depth:c.ce*(c.s*x+c.c*y)+c.se*height}
}
function unproject(x,y,camera,z) {
  var c=orbit(camera),right=x/c.scale,forward=(y/c.scale+c.ce*(Number(z)||0))/c.se
  return {x:c.c*right+c.s*forward,y:-c.s*right+c.c*forward}
}
function depth(x,y,z,camera){return project(x,y,z,camera).depth}
function polygonBounds(points) {
  return {minX:Math.min.apply(null,points.map(function(p){return p.x})),maxX:Math.max.apply(null,points.map(function(p){return p.x})),minY:Math.min.apply(null,points.map(function(p){return p.y})),maxY:Math.max.apply(null,points.map(function(p){return p.y}))}
}
function signedArea(points){var a=0;for(var i=0;i<points.length;i++){var p=points[i],q=points[(i+1)%points.length];a+=p.x*q.y-q.x*p.y}return a/2}
function boxFaces(x,y,z,w,d,h,camera,projector) {
  var c=orbit(camera);camera=c;var p=function(dx,dy,dz){return projector?projector(x+dx,y+dy,z+dz):project(x+dx,y+dy,z+dz,camera)},faces=[]
  function add(name,points,normal){if(Math.abs(signedArea(points))<1e-7)return;faces.push({name:name,points:points,normal:normal,bounds:polygonBounds(points)})}
  // Outward normals facing the camera; at a cardinal yaw the edge-on face is omitted.
  if(c.s>1e-9)add('east',[p(w,-d,0),p(w,d,0),p(w,d,h),p(w,-d,h)],{x:1,y:0,z:0})
  if(c.s< -1e-9)add('west',[p(-w,d,0),p(-w,-d,0),p(-w,-d,h),p(-w,d,h)],{x:-1,y:0,z:0})
  if(c.c>1e-9)add('south',[p(w,d,0),p(-w,d,0),p(-w,d,h),p(w,d,h)],{x:0,y:1,z:0})
  if(c.c< -1e-9)add('north',[p(-w,-d,0),p(w,-d,0),p(w,-d,h),p(-w,-d,h)],{x:0,y:-1,z:0})
  add('roof',[p(-w,-d,h),p(w,-d,h),p(w,d,h),p(-w,d,h)],{x:0,y:0,z:1})
  return faces
}
function pyramidFaces(p,x,y,z,w,d,h,camera) {
  var c=orbit(camera),tip=p(x,y,z+h),faces=[]
  function add(points,normal){if(normal.x*c.s*c.ce+normal.y*c.c*c.ce+normal.z*c.se>1e-9&&Math.abs(signedArea(points))>1e-7)faces.push(points)}
  add([p(x+w,y-d,z),p(x+w,y+d,z),tip],{x:h,y:0,z:w})
  add([p(x-w,y+d,z),p(x-w,y-d,z),tip],{x:-h,y:0,z:w})
  add([p(x+w,y+d,z),p(x-w,y+d,z),tip],{x:0,y:h,z:d})
  add([p(x-w,y-d,z),p(x+w,y-d,z),tip],{x:0,y:-h,z:d})
  return faces
}
function buildingFaces(b,camera){return boxFaces(b.x,b.y,0,b.size/2,b.size/2,b.height*(b.growth===undefined?1:b.growth),camera)}
// Projected face depth is affine. This is also the picking ray's true surface depth.
function plane(points){for(var i=1;i<points.length-1;i++){var p=points[0],q=points[i],r=points[i+1],det=(q.x-p.x)*(r.y-p.y)-(r.x-p.x)*(q.y-p.y);if(Math.abs(det)>1e-8){var a=((q.depth-p.depth)*(r.y-p.y)-(r.depth-p.depth)*(q.y-p.y))/det,b=((q.x-p.x)*(r.depth-p.depth)-(r.x-p.x)*(q.depth-p.depth))/det;return {a:a,b:b,c:p.depth-a*p.x-b*p.y}}}return {a:0,b:0,c:points.reduce(function(n,p){return n+(p.depth||0)},0)/Math.max(1,points.length)}}
function surfaceDepth(points,x,y){var p=plane(points);return p.a*x+p.b*y+p.c}
function convexHull(points) {
  var ps=points.slice().sort(function(a,b){return a.x-b.x||a.y-b.y}),lo=[],hi=[]
  function cross(a,b,c){return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x)}
  ps.forEach(function(p){while(lo.length>1&&cross(lo[lo.length-2],lo[lo.length-1],p)<=0)lo.pop();lo.push(p)})
  for(var i=ps.length-1;i>=0;i--){var p=ps[i];while(hi.length>1&&cross(hi[hi.length-2],hi[hi.length-1],p)<=0)hi.pop();hi.push(p)}
  lo.pop();hi.pop();return lo.concat(hi)
}
function overlapPolygon(a,b) {
  var result=a.slice(),sign=signedArea(b)>=0?1:-1
  for(var i=0;i<b.length&&result.length;i++){var p=b[i],q=b[(i+1)%b.length],input=result;result=[]
    function distance(r){return sign*((q.x-p.x)*(r.y-p.y)-(q.y-p.y)*(r.x-p.x))}
    for(var j=0;j<input.length;j++){var start=input[j],end=input[(j+1)%input.length],ds=distance(start),de=distance(end);if(ds>=-1e-7)result.push(start);if((ds>=0)!==(de>=0)){var t=ds/(ds-de);result.push({x:mix(start.x,end.x,t),y:mix(start.y,end.y,t)})}}
  }return result
}
// Painter order is derived from overlapping surfaces, rather than x+y/centre height.
// A sweep bounds the pair search; nonintersecting solid faces form a stable DAG.
function orderSurfaces(surfaces) {
  var entries=surfaces.map(function(s,i){var ps=s.points,hull=convexHull(ps);return {surface:s,index:i,hull:hull,bounds:polygonBounds(hull),plane:plane(ps),edges:[],incoming:0,mean:ps.reduce(function(n,p){return n+(p.depth||0)},0)/ps.length}})
  var sweep=entries.slice().sort(function(a,b){return a.bounds.minX-b.bounds.minX||a.index-b.index})
  for(var i=0;i<sweep.length;i++)for(var j=i+1;j<sweep.length&&sweep[j].bounds.minX<sweep[i].bounds.maxX-1e-7;j++){var a=sweep[i],b=sweep[j];if(a.bounds.maxY<=b.bounds.minY||b.bounds.maxY<=a.bounds.minY)continue;var da=a.plane.a-b.plane.a,db=a.plane.b-b.plane.b,dc=a.plane.c-b.plane.c;if(Math.abs(da)<1e-8&&Math.abs(db)<1e-8&&Math.abs(dc)<1e-7)continue;var overlap=overlapPolygon(a.hull,b.hull);if(overlap.length<3||Math.abs(signedArea(overlap))<1e-6)continue;var x=0,y=0;overlap.forEach(function(p){x+=p.x;y+=p.y});x/=overlap.length;y/=overlap.length;var delta=da*x+db*y+dc;if(Math.abs(delta)<1e-7)continue;var back=delta<0?a:b,front=delta<0?b:a;back.edges.push(front);front.incoming++}
  function compare(a,b){return a.mean-b.mean||a.index-b.index}
  var ready=entries.filter(function(e){return !e.incoming}).sort(compare),ordered=[]
  while(ready.length){var e=ready.shift();ordered.push(e);e.edges.forEach(function(next){next.incoming--;if(!next.incoming){var lo=0,hi=ready.length;while(lo<hi){var mid=(lo+hi)>>1;if(compare(ready[mid],next)<=0)lo=mid+1;else hi=mid}ready.splice(lo,0,next)}})}
  // Intersecting decorative outlines can form a painter cycle; keep deterministic order.
  if(ordered.length<entries.length){var emitted={};ordered.forEach(function(e){emitted[e.index]=true});entries.filter(function(e){return !emitted[e.index]}).sort(compare).forEach(function(e){ordered.push(e)})}
  return ordered.map(function(e){return e.surface})
}
function pointInPolygon(x,y,poly) {
  var hit=false
  for(var i=0,j=poly.length-1;i<poly.length;j=i++) {
    var a=poly[i],b=poly[j]
    if(((a.y>y)!==(b.y>y)) && x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x)hit=!hit
  }
  return hit
}
function count(n,one,many){return n+' '+(n===1?one:many)}
function lampBrightness(cpu) { return cpu&&cpu.state==='measured'&&isFinite(Number(cpu.level))?.18+.62*clamp(cpu.level,0,1):.12 }
function updateActivity(scene,windows) {
  var owners={};(windows||[]).forEach(function(w){owners[w.address]=w})
  scene.buildings.forEach(function(b){var w=owners[b.key];if(w){b.ownerPid=w.pid;b.ownerCpu=w.ownerCpu||{state:'unavailable'};b.illumination=lampBrightness(b.ownerCpu)}})
}
function activityName(snapshot,id){var names=[];(snapshot.windows||[]).forEach(function(w){if(w.workspace===id&&names.indexOf(w.app)<0)names.push(w.app)});names.sort();return names.length?names.slice(0,3).join(' + ').slice(0,48):'Workspace '+id}
function layout(snapshot) {
  var boroughs=snapshot.boroughs||[],districts=snapshot.districts||[],windows=snapshot.windows||[]
  var monitorIds=boroughs.map(function(m){return m.id}),positions={}
  var order=['development','entertainment','communication','research','system','mixed'],buckets={}
  districts.forEach(function(d){var key=order.indexOf(d.group)>=0?d.group:'mixed';if(!buckets[key])buckets[key]=[];buckets[key].push(d)})
  var clusters=order.filter(function(k){return buckets[k]&&buckets[k].length}).map(function(k){var list=buckets[k].slice().sort(function(a,b){return a.monitor-b.monitor||a.id-b.id}),cols=Math.min(3,Math.max(1,Math.ceil(Math.sqrt(list.length)))),rows=Math.ceil(list.length/cols);return {key:k,list:list,cols:cols,width:(cols-1)*310+300,height:(rows-1)*330+380}})
  var colWidths=[0,0,0],rowHeights=[]
  clusters.forEach(function(g,i){colWidths[i%3]=Math.max(colWidths[i%3],g.width);var row=Math.floor(i/3);rowHeights[row]=Math.max(rowHeights[row]||0,g.height)})
  var result={districts:[],buildings:[],roads:[],boroughs:[],groups:[],bounds:{minX:0,maxX:1,minY:0,maxY:1}}
  clusters.forEach(function(g,gi){var column=gi%3,row=Math.floor(gi/3),baseX=0,baseY=0;for(var c=0;c<column;c++)baseX+=colWidths[c]+170;for(var r=0;r<row;r++)baseY+=rowHeights[r]+170
    g.list.forEach(function(d,i){var mi=monitorIds.indexOf(d.monitor);if(mi<0)mi=monitorIds.length
      var x=baseX+(i%g.cols)*310,y=baseY+Math.floor(i/g.cols)*330
      var item={id:d.id,seed:d.seed,monitor:d.monitor,count:d.count,x:x,y:y,size:240,
       name:d.name||activityName(snapshot,d.id),nameSource:d.nameSource||'apps',customName:d.customName||'',autoName:d.autoName||activityName(snapshot,d.id),autoSource:d.autoSource||'apps',pinned:!!d.pinned,tint:d.tint===undefined?d.seed%5:d.tint,circuitOverride:!!d.circuitOverride,landmark:['Lighthouse','Canopy','Observatory','Spire','Garden'][d.seed%5],
       group:g.key,groupName:d.groupName||g.key,groupColor:d.groupColor||'#9e9e9e',groupReason:d.groupReason||'',groupPending:!!d.groupPending,hue:d.seed%360,borough:mi}
      result.districts.push(item);positions[d.id]=item
    })
    result.groups.push({key:g.key,name:g.list[0].groupName||g.key,color:g.list[0].groupColor||'#9e9e9e',count:g.list.length,x:0,y:0,width:g.width,height:g.height})
  })
  boroughs.forEach(function(b){var d=result.districts.find(function(d){return d.monitor===b.id});if(d)result.boroughs.push({name:b.name,id:b.id,x:d.x,y:d.y,focused:b.focused})})
  var byDistrict={}
  for(var wi=0;wi<windows.length;wi++) {var w=windows[wi];if(!byDistrict[w.workspace])byDistrict[w.workspace]=[];byDistrict[w.workspace].push(w)}
  for(var key in byDistrict) {
    var d=positions[key];if(!d)continue
    var list=byDistrict[key].slice().sort(function(a,b){return hash(a.address)-hash(b.address)})
    var cols=Math.max(3,Math.ceil(Math.sqrt(list.length+1))),spacing=Math.min(58,190/cols)
    for(var i=0;i<list.length;i++) {
      var w=list[i],h=hash(w.class),x=d.x+(i%cols-(cols-1)/2)*spacing,y=d.y+(Math.floor(i/cols)-(cols-1)/2)*spacing
      var size=Math.max(12,spacing*.60),height=42+h%62+Math.min(28,(w.height||0)/70)
      result.buildings.push({key:w.address,address:w.address,workspace:w.workspace,app:w.app,appClass:w.class,icon:w.icon,
        focused:w.focused,urgent:w.urgent,floating:w.floating,width:w.width,windowHeight:w.height,tint:d.tint,group:d.group,groupColor:d.groupColor,circuitOverride:d.circuitOverride,x:x,y:y,size:size,height:height,style:h%4,seed:h,monitor:w.monitor,ownerPid:w.pid,ownerCpu:w.ownerCpu||{state:'unavailable'},illumination:lampBrightness(w.ownerCpu)})
    }
  }
  // Headings sit just above each cluster's tallest structure, centred on screen. Building tops reserve the focus marker, so
  // changing focus never moves a heading.
  result.groups.forEach(function(g){var xs=[],top=Infinity
    result.districts.forEach(function(d){if(d.group!==g.key)return;xs.push(project(d.x,d.y).x);top=Math.min(top,project(d.x-120,d.y-120,0).y,project(d.x+44,d.y-101,140).y)})
    result.buildings.forEach(function(b){if(b.group===g.key)top=Math.min(top,project(b.x-b.size/2,b.y-b.size/2,b.height+(b.style===0?14:0)+31).y)})
    var at=unproject((Math.min.apply(null,xs)+Math.max.apply(null,xs))/2,top-16);g.x=at.x;g.y=at.y})
  var grid={};result.districts.forEach(function(d){grid[d.group+'|'+d.x+'|'+d.y]=d})
  result.districts.forEach(function(d){[[310,0],[0,330]].forEach(function(delta){var e=grid[d.group+'|'+(d.x+delta[0])+'|'+(d.y+delta[1])];if(e)result.roads.push({a:project(d.x,d.y+120),b:project(e.x,e.y+120),worldA:{x:d.x,y:d.y+120,z:0},worldB:{x:e.x,y:e.y+120,z:0},seed:d.seed})})})
  var corners=[]
  result.districts.forEach(function(d){[-145,145].forEach(function(dx){[-145,145].forEach(function(dy){corners.push(project(d.x+dx,d.y+dy,-30))})});corners.push(project(d.x,d.y,160))})
  result.groups.forEach(function(g){var p=project(g.x,g.y);corners.push({x:p.x-150,y:p.y-25});corners.push({x:p.x+150,y:p.y+20})})
  if(corners.length)result.bounds={minX:Math.min.apply(null,corners.map(function(p){return p.x})),maxX:Math.max.apply(null,corners.map(function(p){return p.x})),minY:Math.min.apply(null,corners.map(function(p){return p.y})),maxY:Math.max.apply(null,corners.map(function(p){return p.y}))}
  return result
}

function face(b,camera){var ps=[];buildingFaces(b,camera).forEach(function(f){ps=ps.concat(f.points)});return convexHull(ps)}
function hit(scene,x,y,zoom,camera) {
  if(camera)camera=orbit(camera)
  var hitZoom=zoom||1
  for(var gi=0;gi<(scene.groups||[]).length;gi++){var g=scene.groups[gi],p=groupLabel(scene,g,camera,hitZoom);if(hitZoom>.25&&Math.abs(x-p.x)<p.halfWidth&&y>=p.y-20/hitZoom&&y<=p.y+10/hitZoom)return {type:'group',key:g.key}}
  var target=null,closest=-Infinity
  if(!zoom||zoom>.30)(scene.buildings||[]).forEach(function(b){if(b.dying||b.growth===0)return;buildingFaces(b,camera).forEach(function(f){if(pointInPolygon(x,y,f.points)){var z=surfaceDepth(f.points,x,y);if(z>closest){closest=z;target={type:'building',key:b.key}}}})})
  // Near platforms can occlude far buildings at low elevation: picking follows rendering.
  ;(scene.districts||[]).forEach(function(d){var size=districtSize(d);boxFaces(d.x,d.y,-12,size.halfWidth,size.halfDepth,12,camera).forEach(function(f){if(pointInPolygon(x,y,f.points)){var z=surfaceDepth(f.points,x,y);if(z>closest){closest=z;target={type:'district',key:d.id}}}})})
  return target
}
function roadPoints(r,camera){return r.worldA&&r.worldB?{a:project(r.worldA.x,r.worldA.y,r.worldA.z,camera),b:project(r.worldB.x,r.worldB.y,r.worldB.z,camera)}:{a:r.a,b:r.b}}
function districtSize(d){return {halfWidth:clamp(Number(d.width)||Number(d.size)||240,24,100000)/2,halfDepth:clamp(Number(d.depth)||Number(d.height)||Number(d.size)||240,24,100000)/2}}
function districtBounds(d,camera){camera=orbit(camera);var ps=[],size=districtSize(d);[-size.halfWidth-25,size.halfWidth+25].forEach(function(x){[-size.halfDepth-25,size.halfDepth+25].forEach(function(y){[-30,160].forEach(function(z){ps.push(project(d.x+x,d.y+y,z,camera))})})});return polygonBounds(ps)}
function districtLabel(d,camera,zoom){var b=districtBounds(d,camera);return {x:(b.minX+b.maxX)/2,y:b.maxY+14/(zoom||1)}}
function groupLabel(scene,g,camera,zoom){var ps=[],z=zoom||1;if(!camera){var old=project(g.x,g.y);return {x:old.x,y:old.y,halfWidth:150/z}};(scene.districts||[]).forEach(function(d){if(d.group===g.key){var b=districtBounds(d,camera);ps.push({x:b.minX,y:b.minY},{x:b.maxX,y:b.minY})}});(scene.buildings||[]).forEach(function(b){if(b.group===g.key)ps.push(project(b.x,b.y,b.height+31,camera))});if(!ps.length)return {x:project(g.x,g.y,0,camera).x,y:project(g.x,g.y,0,camera).y,halfWidth:150/z};var box=polygonBounds(ps),text=g.name.toUpperCase()+' / '+count(g.count,'DISTRICT','DISTRICTS');return {x:(box.minX+box.maxX)/2,y:box.minY-20/z,halfWidth:Math.max(80,text.length*4.9)/z}}
function bounds(scene,camera,zoom){var ps=[],z=zoom||1;(scene.districts||[]).forEach(function(d){var b=districtBounds(d,camera),label=districtLabel(d,camera,z),w=Math.max(140,String(d.name||'').length*4.6)/z;ps.push({x:b.minX,y:b.minY},{x:b.maxX,y:b.maxY},{x:label.x-w,y:label.y+20/z},{x:label.x+w,y:label.y-18/z})});(scene.buildings||[]).forEach(function(b){ps=ps.concat(face(b,camera));ps.push(project(b.x,b.y,b.height+31,camera))});(scene.groups||[]).forEach(function(g){var p=groupLabel(scene,g,camera,z);ps.push({x:p.x-p.halfWidth,y:p.y-20/z},{x:p.x+p.halfWidth,y:p.y+10/z})});return ps.length?polygonBounds(ps):{minX:0,maxX:1,minY:0,maxY:1}}
function transition(previous,next,motion,now) {
  var old={};(previous.buildings||[]).forEach(function(b){old[b.key]=b})
  next.buildings.forEach(function(b){var a=old[b.key],changed=!a||a.targetX!==b.x||a.targetY!==b.y;b.startX=a?a.x:b.x;b.startY=a?a.y:b.y;b.targetX=b.x;b.targetY=b.y;b.bornAt=a?a.bornAt:now;b.movedAt=changed?now:(a.movedAt||now);b.growth=motion?(a?a.growth:0):1;delete old[b.key]})
  if(motion)for(var key in old){var a=old[key];if(!a.dying){a.dying=true;a.diedAt=now}next.buildings.push(a)}
  return next
}
function advance(scene,now,motion) {
  scene.buildings=scene.buildings.filter(function(b){return !b.dying||now-b.diedAt<650})
  scene.buildings.forEach(function(b){var t=motion?clamp((now-b.movedAt)/700,0,1):1;t=1-Math.pow(1-t,3);b.x=mix(b.startX,b.targetX,t);b.y=mix(b.startY,b.targetY,t);b.growth=b.dying?1-clamp((now-b.diedAt)/650,0,1):motion?clamp((now-b.bornAt)/800,0,1):1})
}

// Collect geometric draw commands so platform sides, civic architecture and real
// app facades share one depth order. Text is an explicit readable billboard layer.
function recordingContext(target,cache) {
  var queue=[],overlays=[],ops=[],path=[],current=null,c={_recording:true,_depth:0,globalAlpha:1,fillStyle:target.fillStyle,strokeStyle:target.strokeStyle,lineWidth:1,font:'10px sans-serif',textAlign:'center',lineJoin:'round',lineCap:'round'}
  function state(){return {globalAlpha:c.globalAlpha,fillStyle:c.fillStyle,strokeStyle:c.strokeStyle,lineWidth:c.lineWidth,font:c.font,textAlign:c.textAlign,lineJoin:c.lineJoin,lineCap:c.lineCap}}
  function replay(st,steps){var usesFont=steps.some(function(op){return op.name==='fillText'});return function(){Object.keys(st).forEach(function(k){if(k!=='font'||usesFont)target[k]=st[k]});steps.forEach(function(op){target[op.name].apply(target,op.args)})}}
  function enqueue(points,steps,overlay){var command={points:points,run:replay(state(),steps)};(overlay?overlays:queue).push(command)}
  function op(name,args){ops.push({name:name,args:Array.prototype.slice.call(args)})}
  c.beginPath=function(){ops=[{name:'beginPath',args:[]}];path=[];current=null}
  c.moveTo=function(x,y){op('moveTo',arguments);current={x:x,y:y,depth:c._depth};path.push(current)}
  c.lineTo=function(x,y){op('lineTo',arguments);current={x:x,y:y,depth:c._depth};path.push(current)}
  c.closePath=function(){op('closePath',arguments)}
  c.arc=function(x,y,r){op('arc',arguments);path=path.concat([{x:x-r,y:y-r,depth:c._depth},{x:x+r,y:y-r,depth:c._depth},{x:x+r,y:y+r,depth:c._depth},{x:x-r,y:y+r,depth:c._depth}])}
  c.ellipse=function(x,y,rx,ry){op('ellipse',arguments);path=path.concat([{x:x-rx,y:y-ry,depth:c._depth},{x:x+rx,y:y-ry,depth:c._depth},{x:x+rx,y:y+ry,depth:c._depth},{x:x-rx,y:y+ry,depth:c._depth}])}
  c.fill=function(){if(path.length>2)enqueue(path,ops.concat([{name:'fill',args:[]}]),false)}
  c.stroke=function(){if(path.length>2)enqueue(path,ops.concat([{name:'stroke',args:[]}]),false);else if(path.length===2)c.recordLine(path[0],path[1],c.strokeStyle,c.lineWidth)}
  c.fillText=function(text,x,y){var half=String(text).length*7;enqueue([{x:x-half,y:y-14,depth:0},{x:x+half,y:y-14,depth:0},{x:x+half,y:y+3,depth:0},{x:x-half,y:y+3,depth:0}],[{name:'fillText',args:[text,x,y]}],true)}
  c.fillRect=function(x,y,w,h){enqueue([{x:x,y:y,depth:0},{x:x+w,y:y,depth:0},{x:x+w,y:y+h,depth:0},{x:x,y:y+h,depth:0}],[{name:'fillRect',args:[x,y,w,h]}],true)}
  c.recordPolygon=function(points,fill,stroke,width){var st=state();queue.push({points:points,run:function(){Object.keys(st).forEach(function(k){if(k!=='font')target[k]=st[k]});polygon(target,points,fill,stroke,width)}})}
  c.recordLine=function(a,b,ink,width){var dx=b.x-a.x,dy=b.y-a.y,length=Math.sqrt(dx*dx+dy*dy),r=(width||1)/2;if(length<1e-8)return;var nx=-dy/length*r,ny=dx/length*r,ps=[{x:a.x+nx,y:a.y+ny,depth:a.depth||0},{x:b.x+nx,y:b.y+ny,depth:b.depth||0},{x:b.x-nx,y:b.y-ny,depth:b.depth||0},{x:a.x-nx,y:a.y-ny,depth:a.depth||0}],st=state();queue.push({points:ps,run:function(){Object.keys(st).forEach(function(k){if(k!=='font')target[k]=st[k]});line(target,a,b,ink,width)}})}
  c.flush=function(){var keyParts=[];queue.forEach(function(command){keyParts.push(command.points.length);command.points.forEach(function(p){keyParts.push(p.x,p.y,p.depth)})});var key=keyParts.join('|'),ordered;if(cache&&cache.key===key)ordered=cache.order.map(function(i){return queue[i]});else{queue.forEach(function(command,i){command.orderIndex=i});ordered=orderSurfaces(queue);if(cache){cache.key=key;cache.order=ordered.map(function(command){return command.orderIndex})}}ordered.forEach(function(command){command.run()});overlays.forEach(function(command){command.run()});target.globalAlpha=1}
  return c
}
function markedProject(ctx,x,y,z,camera){var p=project(x,y,z,camera);ctx._depth=p.depth;return p}
function polygon(ctx,points,fill,stroke,width) {
  if(ctx._recording===true){ctx.recordPolygon(points,fill,stroke,width);return}
  ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(var i=1;i<points.length;i++)ctx.lineTo(points[i].x,points[i].y);ctx.closePath()
  if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width||1;ctx.stroke()}
}
function line(ctx,a,b,color,width) {if(ctx._recording===true){ctx.recordLine(a,b,color,width);return}ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=color;ctx.lineWidth=width||1;ctx.stroke()}
function color(hex,alpha) {var h=String(hex).replace('#','');if(h.length!==6)return 'rgba(130,205,200,'+alpha+')';return 'rgba('+parseInt(h.slice(0,2),16)+','+parseInt(h.slice(2,4),16)+','+parseInt(h.slice(4,6),16)+','+alpha+')'}
function terrace(ctx,p,x,y,w,d,h,palette,alpha) {
  boxFaces(x,y,0,w,d,h,p.camera,p).forEach(function(f){polygon(ctx,f.points,f.name==='roof'?palette.roof:(f.name==='east'||f.name==='west'?palette.left:palette.right),color(f.name==='roof'?palette.accent:palette.ink,alpha),.8)})
}
function tree(ctx,p,x,y,height,palette) {
  line(ctx,p(x,y,0),p(x,y,height),color(palette.ink,.4),1.1)
  for(var tier=0;tier<3;tier++) {
    var cap=p(x,y,height+tier*5),radius=11-tier*2
    ctx.beginPath();ctx.ellipse(cap.x,cap.y,radius,radius*.6,0,0,Math.PI*2)
    ctx.fillStyle=color(palette.accent,.18+tier*.055);ctx.fill();ctx.strokeStyle=color(palette.accent,.23);ctx.lineWidth=.6;ctx.stroke()
  }
}
function landmark(ctx,d,p,palette) {
  // Decorative civic architecture is stable per workspace; it never represents an app.
  var x=73,y=-76,kind=d.seed%5,lp=function(dx,dy,z){return p(x+dx,y+dy,z)}
  terrace(ctx,p,x,y,29,25,9,palette,.28)
  if(kind===0) {
    terrace(ctx,p,x,y,12,12,82,palette,.55)
    terrace(ctx,p,x,y,18,18,91,palette,.7)
    for(var z=20;z<80;z+=18)line(ctx,lp(-12,12,z),lp(12,12,z),color(palette.accent,.65),1.5)
    var top=lp(0,0,100);ctx.beginPath();ctx.ellipse(top.x,top.y,17,8,0,0,Math.PI*2);ctx.fillStyle=color(palette.accent,.30);ctx.fill();ctx.strokeStyle=color(palette.accent,.9);ctx.stroke()
    line(ctx,lp(0,0,99),lp(0,0,120),color(palette.accent,.75),1.3)
  } else if(kind===2) {
    terrace(ctx,p,x,y,23,20,45,palette,.45)
    var dome=lp(0,0,47);ctx.beginPath();ctx.ellipse(dome.x,dome.y,29,28,0,Math.PI,2*Math.PI);ctx.closePath();ctx.fillStyle=palette.roof;ctx.fill();ctx.strokeStyle=color(palette.accent,.65);ctx.lineWidth=1.1;ctx.stroke()
    for(var a=0;a<3;a++){var q=lp(-14+a*14,0,46);line(ctx,q,{x:dome.x,y:dome.y-28},color(palette.ink,.25),.7)}
    var telescope=lp(0,0,75);line(ctx,telescope,{x:telescope.x+27,y:telescope.y-18},color(palette.accent,.85),5)
  } else if(kind===3) {
    terrace(ctx,p,x,y,17,17,31,palette,.45)
    pyramidFaces(p,x,y,31,17,17,100,p.camera).forEach(function(points,i){polygon(ctx,points,i%2?palette.left:palette.right,color(palette.accent,.7),1)})
    line(ctx,lp(0,0,45),lp(0,0,131),color(palette.accent,.8),1.1)
    for(var ring=0;ring<3;ring++){var cap=lp(0,0,52+ring*19);ctx.beginPath();ctx.ellipse(cap.x,cap.y,20-ring*4,7-ring,0,0,Math.PI*2);ctx.strokeStyle=color(palette.accent,.45);ctx.stroke()}
  } else if(kind===1) {
    for(var pillar=0;pillar<4;pillar++)terrace(ctx,p,x+(pillar%2?20:-20),y+(pillar<2?-18:18),2,2,51,palette,.45)
    terrace(ctx,p,x,y,29,25,57,palette,.5)
    polygon(ctx,[lp(-30,-26,58),lp(0,-26,79),lp(0,26,79),lp(-30,26,58)],color(palette.accent,.25),color(palette.accent,.65),1)
    polygon(ctx,[lp(0,-26,79),lp(30,-26,58),lp(30,26,58),lp(0,26,79)],color(palette.accent,.25),color(palette.accent,.65),1)
    tree(ctx,p,x,y,17,palette)
  } else {
    terrace(ctx,p,x,y,22,18,15,palette,.4)
    for(var t=0;t<5;t++)tree(ctx,p,x-19+(t%3)*18,y-12+Math.floor(t/3)*21,25+(t%2)*12,palette)
  }
}
function building(ctx,b,palette,selected,time,scale,lens,camera) {
  camera=orbit(camera)
  var s=b.size/2,h=b.height*(b.growth===undefined?1:b.growth),p=function(x,y,z){return markedProject(ctx,b.x+x,b.y+y,z,camera)},faces=buildingFaces(b,camera),sides=faces.filter(function(f){return f.name!=='roof'})
  var active=b.focused||b.key===selected
  var light=b.circuitOverride?palette.neons[b.tint||0]:(b.groupColor||palette.accent)
  var subdued=lens&&b.appClass!==lens;if(subdued)ctx.globalAlpha=.20
  // The geometry rises and folds; windows retain their app identity throughout a move.
  polygon(ctx,[p(-s,-s,0),p(s,-s,0),p(s+10,s+8,0),p(-s+10,s+8,0)],'rgba(0,0,0,.18)')
  if(active)polygon(ctx,[p(-s-9,-s-9,1),p(s+9,-s-9,1),p(s+9,s+9,1),p(-s-9,s+9,1)],color(palette.accent,.15),color(palette.accent,.5),1)
  faces.forEach(function(f){polygon(ctx,f.points,f.name==='roof'?(active?palette.roofActive:palette.roof):(f.name==='east'||f.name==='west'?palette.left:palette.right),color(light,f.name==='roof'?.8:.34),.8)})
  var floors=scale<.35?2:Math.floor(h/12);if(camera&&camera.interactive)floors=Math.min(2,floors)
  for(var level=0;level<floors;level++) {
    var z=5+level*(scale<.35?h/2:12)
    for(var col=0;col<(camera&&camera.interactive?2:3);col++) {
      var xx=-s+4+col*(b.size-8)/3,brightness=(b.illumination===undefined?.12:b.illumination)*((b.seed+level*7+col*3)%4===0?1:.65)
      sides.forEach(function(f){var sign=f.name==='east'||f.name==='south'?1:-1,other=xx+Math.max(2,b.size/7),a=f.name==='east'||f.name==='west'?p(sign*(s+.3),xx,z):p(xx,sign*(s+.3),z),q=f.name==='east'||f.name==='west'?p(sign*(s+.3),other,z):p(other,sign*(s+.3),z);line(ctx,a,q,color('#ffdca8',brightness*(f.name==='east'||f.name==='west'?.6:1)),f.name==='east'||f.name==='west'?1.6:2.2)})
    }
  }
  if(b.style===1) {
    line(ctx,p(0,0,h),p(0,0,h+19),color(light,.65),1)
    ctx.beginPath();var tip=p(0,0,h+19);ctx.arc(tip.x,tip.y,1.7,0,Math.PI*2);ctx.fillStyle=light;ctx.fill()
  } else if(b.style===2)polygon(ctx,[p(-s*.65,-s*.65,h+6),p(s*.65,-s*.65,h+6),p(s*.65,s*.65,h+6),p(-s*.65,s*.65,h+6)],color(light,.16),color(light,.55),.7)
  // Neon facade band and public app sign; actual window identities only.
  sides.forEach(function(f){var sign=f.name==='east'||f.name==='south'?1:-1,a=f.name==='east'||f.name==='west'?p(sign*(s+.5),-s,h*.72):p(-s,sign*(s+.5),h*.72),q=f.name==='east'||f.name==='west'?p(sign*(s+.5),s,h*.72):p(s,sign*(s+.5),h*.72);line(ctx,a,q,color(light,.8),2)})
  if(scale>.85){var sign=p(0,0,h+6);ctx.font='600 '+Math.max(1,Math.round(10/scale))+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(light,.92);ctx.fillText(b.app.slice(0,8).toUpperCase(),sign.x,sign.y)}
  if(b.style===0){polygon(ctx,[p(-s*.5,-s*.5,h),p(s*.5,-s*.5,h),p(s*.5,s*.5,h+14),p(-s*.5,s*.5,h+14)],palette.roof,color(light,.7),1)}
  if(active) {
    var top=p(0,0,h+14),pulse=1
    ctx.beginPath();ctx.ellipse(top.x,top.y,9*pulse,4*pulse,0,0,Math.PI*2);ctx.strokeStyle=color(palette.accent,.75);ctx.lineWidth=1;ctx.stroke()
    line(ctx,p(0,0,h+8),p(0,0,h+31),color(palette.accent,.7),1)
  }
  ctx.globalAlpha=1
}
function draw(ctx,scene,palette,selected,districtSelected,time,motion,scale,view,lens,camera) {
  if(!scene._renderOrderCache)scene._renderOrderCache={}
  ctx=recordingContext(ctx,scene._renderOrderCache);camera=orbit(camera)
  scale=scale||1
  ctx.lineJoin='round';ctx.lineCap='round';var paletteBase=palette
  // Archipelago bridges and lanes connect actual neighbouring workspaces.
  scene.roads.forEach(function(road){var r=roadPoints(road,camera);line(ctx,r.a,r.b,color(palette.accent,.14),20);line(ctx,r.a,r.b,color(palette.ink,.30),1.4);line(ctx,{x:r.a.x,y:r.a.y-4,depth:r.a.depth},{x:r.b.x,y:r.b.y-4,depth:r.b.depth},color(palette.neons[1],.28),.9)
  })
  scene.districts.forEach(function(d){
    var db=districtBounds(d,camera);if(view&&(db.maxX<view.minX||db.minX>view.maxX||db.maxY+40/scale<view.minY||db.minY>view.maxY))return
    var palette=Object.assign({},paletteBase,{accent:d.groupColor||paletteBase.neons[d.tint||0]});
    var size=districtSize(d),s=size.halfWidth,t=size.halfDepth,p=function(x,y,z){return markedProject(ctx,d.x+x,d.y+y,z,camera)};p.camera=camera
    boxFaces(d.x,d.y,-12,s,t,12,camera).forEach(function(f){polygon(ctx,f.points,f.name==='roof'?palette.ground:(f.name==='east'||f.name==='west'?palette.left:palette.right),color(palette.accent,f.name==='roof'?.48:.14),f.name==='roof'?1:.5)})
    if(d.id===districtSelected)polygon(ctx,[p(-s-3,-t-3,2),p(s+3,-t-3,2),p(s+3,t+3,2),p(-s-3,t+3,2)],null,color(palette.accent,.9),1.8)
    if(!camera.interactive){var stepX=Math.max(30,s/12),stepY=Math.max(30,t/12);for(var g=-s+stepX;g<s;g+=stepX)line(ctx,p(g,-t,1),p(g,t,1),color(palette.ink,.045),.7);for(var g=-t+stepY;g<t;g+=stepY)line(ctx,p(-s,g,1),p(s,g,1),color(palette.ink,.045),.7)}
    if(!camera.interactive&&d.kind!=='agentFamily'){
    // Promenade, illuminated perimeter and a procedural landmark common to this district.
    line(ctx,p(-105,104,1),p(105,104,1),color(palette.accent,.55),2)
    line(ctx,p(104,-105,1),p(104,105,1),color(palette.accent,.19),1)
    polygon(ctx,[p(-105,86,1),p(105,86,1),p(105,103,1),p(-105,103,1)],color(palette.ink,.065),color(palette.accent,.18),.6)
    for(var lane=-90;lane<105;lane+=18)line(ctx,p(lane,87,1),p(lane,102,1),color(palette.ink,.10),.6)
    polygon(ctx,[p(-105,-28,1),p(-76,-28,1),p(-76,74,1),p(-105,74,1)],color(palette.accent,.055),color(palette.accent,.15),.6)
    for(var garden=0;garden<4;garden++)tree(ctx,p,-92,-13+garden*24,14+(garden%2)*8,palette)
    for(var lamp=-95;lamp<105;lamp+=38){line(ctx,p(lamp,101,1),p(lamp,101,14),color(palette.ink,.3),.7);var glow=p(lamp,101,15);ctx.beginPath();ctx.arc(glow.x,glow.y,1.6,0,Math.PI*2);ctx.fillStyle=color(palette.accent,.8);ctx.fill()}
    // Low civic arcades and illuminated transit plazas are decorative, not fake apps.
    terrace(ctx,p,50,40,22,18,12,palette,.4)
    terrace(ctx,p,50,40,17,13,19,palette,.35)
    line(ctx,p(-70,35,1),p(24,35,1),color(palette.accent,.25),7)
    line(ctx,p(-70,35,2),p(24,35,2),color(palette.accent,.7),1)
    for(var ring=0;ring<2;ring++){var plaza=p(3,65,2);ctx.beginPath();ctx.ellipse(plaza.x,plaza.y,18+ring*8,8+ring*4,0,0,Math.PI*2);ctx.strokeStyle=color(palette.accent,.4-ring*.1);ctx.lineWidth=1;ctx.stroke()}
    landmark(ctx,d,p,palette)
    }
    ctx.font='500 '+Math.max(1,Math.round(13/scale))+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(palette.ink,.9);var label=districtLabel(d,camera,scale);if(scale>.26||d.id===districtSelected)ctx.fillText((d.pinned?'★ ':'')+d.name.toUpperCase(),label.x,label.y)
    ctx.font=Math.max(1,Math.round(10/scale))+'px sans-serif';ctx.fillStyle=color(palette.ink,.6);if(scale>.44)ctx.fillText(d.virtualWorkspace?count(d.count,'AGENT','AGENTS')+' / RECORDED FAMILY':'D'+d.id+' / '+count(d.count,'WINDOW','WINDOWS')+' · '+(d.groupName||d.landmark).toUpperCase(),label.x,label.y+16/scale)
  })
  scene.buildings.forEach(function(b){var bb=polygonBounds(face(b,camera));if(!view||(bb.maxX>view.minX&&bb.minX<view.maxX&&bb.maxY>view.minY&&bb.minY-40<view.maxY))building(ctx,b,palette,selected,time,scale,lens,camera)})
  ;(scene.groups||[]).forEach(function(g){if(scale<=.25)return;var p=groupLabel(scene,g,camera,scale);ctx.font='600 '+Math.max(1,Math.round(14/scale))+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(palette.ink,.95);ctx.fillText(g.name.toUpperCase()+' / '+count(g.count,'DISTRICT','DISTRICTS'),p.x,p.y);ctx.fillStyle=color(g.color,1);ctx.fillRect(p.x-40/scale,p.y+7/scale,80/scale,3/scale)})
  if(!(scene.groups||[]).length)scene.boroughs.forEach(function(b){var p=project(b.x,b.y,0,camera);ctx.font='600 '+Math.max(1,Math.round(12/scale))+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(palette.accent,.95);ctx.fillText(b.name.toUpperCase()+' / BOROUGH',p.x,p.y)})
  ctx.flush()
}
