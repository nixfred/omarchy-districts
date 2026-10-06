.pragma library

function clamp(v, a, b) { return Math.max(a, Math.min(b, Number(v) || 0)) }
function hash(text) { var n=2166136261; for(var i=0;i<String(text).length;i++)n=Math.imul(n^String(text).charCodeAt(i),16777619);return n>>>0 }
function mix(a,b,t) { return a+(b-a)*t }
function project(x,y,z) { return {x:(x-y)*0.866, y:(x+y)*0.5-(z||0)} }
function unproject(x,y) { return {x:y+x/(2*0.866),y:y-x/(2*0.866)} }
function pointInPolygon(x,y,poly) {
  var hit=false
  for(var i=0,j=poly.length-1;i<poly.length;j=i++) {
    var a=poly[i],b=poly[j]
    if(((a.y>y)!==(b.y>y)) && x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x)hit=!hit
  }
  return hit
}
function count(n,one,many){return n+' '+(n===1?one:many)}
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
       group:g.key,groupName:d.groupName||g.key,groupColor:d.groupColor||'#aebbd0',groupReason:d.groupReason||'',groupPending:!!d.groupPending,hue:d.seed%360,borough:mi}
      result.districts.push(item);positions[d.id]=item
    })
    result.groups.push({key:g.key,name:g.list[0].groupName||g.key,color:g.list[0].groupColor||'#aebbd0',count:g.list.length,x:0,y:0,width:g.width,height:g.height})
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
        focused:w.focused,urgent:w.urgent,floating:w.floating,width:w.width,windowHeight:w.height,tint:d.tint,group:d.group,groupColor:d.groupColor,circuitOverride:d.circuitOverride,x:x,y:y,size:size,height:height,style:h%4,seed:h,monitor:w.monitor})
    }
  }
  // Headings sit just above each cluster's tallest structure, centred on screen. Building tops reserve the focus marker, so
  // changing focus never moves a heading.
  result.groups.forEach(function(g){var xs=[],top=Infinity
    result.districts.forEach(function(d){if(d.group!==g.key)return;xs.push(project(d.x,d.y).x);top=Math.min(top,project(d.x-120,d.y-120,0).y,project(d.x+44,d.y-101,140).y)})
    result.buildings.forEach(function(b){if(b.group===g.key)top=Math.min(top,project(b.x-b.size/2,b.y-b.size/2,b.height+(b.style===0?14:0)+31).y)})
    var at=unproject((Math.min.apply(null,xs)+Math.max.apply(null,xs))/2,top-16);g.x=at.x;g.y=at.y})
  var grid={};result.districts.forEach(function(d){grid[d.group+'|'+d.x+'|'+d.y]=d})
  result.districts.forEach(function(d){[[310,0],[0,330]].forEach(function(delta){var e=grid[d.group+'|'+(d.x+delta[0])+'|'+(d.y+delta[1])];if(e)result.roads.push({a:project(d.x,d.y+120),b:project(e.x,e.y+120),seed:d.seed})})})
  var corners=[]
  result.districts.forEach(function(d){[-145,145].forEach(function(dx){[-145,145].forEach(function(dy){corners.push(project(d.x+dx,d.y+dy,-30))})});corners.push(project(d.x,d.y,160))})
  result.groups.forEach(function(g){var p=project(g.x,g.y);corners.push({x:p.x-150,y:p.y-25});corners.push({x:p.x+150,y:p.y+20})})
  if(corners.length)result.bounds={minX:Math.min.apply(null,corners.map(function(p){return p.x})),maxX:Math.max.apply(null,corners.map(function(p){return p.x})),minY:Math.min.apply(null,corners.map(function(p){return p.y})),maxY:Math.max.apply(null,corners.map(function(p){return p.y}))}
  return result
}

function face(b) {
  var s=b.size/2,h=b.height*(b.growth===undefined?1:b.growth)
  return [project(b.x-s,b.y-s,h),project(b.x+s,b.y-s,h),project(b.x+s,b.y+s,0),project(b.x-s,b.y+s,0),project(b.x-s,b.y+s,h)]
}
function hit(scene,x,y,zoom) {
  var hitZoom=zoom||1
  for(var gi=0;gi<(scene.groups||[]).length;gi++){var g=scene.groups[gi],p=project(g.x,g.y);if(hitZoom>.25&&Math.abs(x-p.x)<150/hitZoom&&y>=p.y-24/hitZoom&&y<=p.y+6/hitZoom)return {type:'group',key:g.key}}
  var buildings=(scene.buildings||[]).slice().sort(function(a,b){return (b.x+b.y)-(a.x+a.y)})
  for(var i=0;i<buildings.length;i++)if((!zoom||zoom>.30)&&!buildings[i].dying && buildings[i].growth!==0 && pointInPolygon(x,y,face(buildings[i])))return {type:'building',key:buildings[i].key}
  var pos=unproject(x,y)
  for(var i=0;i<scene.districts.length;i++) {var d=scene.districts[i];if(Math.abs(pos.x-d.x)<120 && Math.abs(pos.y-d.y)<120)return {type:'district',key:d.id}}
  return null
}
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

function polygon(ctx,points,fill,stroke,width) {
  ctx.beginPath();ctx.moveTo(points[0].x,points[0].y);for(var i=1;i<points.length;i++)ctx.lineTo(points[i].x,points[i].y);ctx.closePath()
  if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width||1;ctx.stroke()}
}
function line(ctx,a,b,color,width) {ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=color;ctx.lineWidth=width||1;ctx.stroke()}
function color(hex,alpha) {var h=String(hex).replace('#','');if(h.length!==6)return 'rgba(130,205,200,'+alpha+')';return 'rgba('+parseInt(h.slice(0,2),16)+','+parseInt(h.slice(2,4),16)+','+parseInt(h.slice(4,6),16)+','+alpha+')'}
function terrace(ctx,p,x,y,w,d,h,palette,alpha) {
  var a=function(dx,dy,z){return p(x+dx,y+dy,z)}
  polygon(ctx,[a(-w,-d,h),a(-w,d,h),a(-w,d,0),a(-w,-d,0)],palette.left,color(palette.ink,alpha),.8)
  polygon(ctx,[a(-w,d,h),a(w,d,h),a(w,d,0),a(-w,d,0)],palette.right,color(palette.accent,alpha),.8)
  polygon(ctx,[a(-w,-d,h),a(w,-d,h),a(w,d,h),a(-w,d,h)],palette.roof,color(palette.accent,alpha),.9)
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
    polygon(ctx,[lp(-17,-17,31),lp(17,-17,31),lp(0,0,131)],palette.left,color(palette.accent,.6),1)
    polygon(ctx,[lp(-17,17,31),lp(17,17,31),lp(0,0,131)],palette.right,color(palette.accent,.75),1)
    line(ctx,lp(0,0,45),lp(0,0,131),color(palette.accent,.8),1.1)
    for(var ring=0;ring<3;ring++){var cap=lp(0,0,52+ring*19);ctx.beginPath();ctx.ellipse(cap.x,cap.y,20-ring*4,7-ring,0,0,Math.PI*2);ctx.strokeStyle=color(palette.accent,.45);ctx.stroke()}
  } else if(kind===1) {
    for(var pillar=0;pillar<4;pillar++)terrace(ctx,p,x+(pillar%2?20:-20),y+(pillar<2?-18:18),2,2,51,palette,.45)
    terrace(ctx,p,x,y,29,25,57,palette,.5)
    polygon(ctx,[lp(-30,-26,58),lp(0,-26,79),lp(30,-26,58),lp(30,26,58),lp(0,26,79),lp(-30,26,58)],color(palette.accent,.25),color(palette.accent,.65),1)
    tree(ctx,p,x,y,17,palette)
  } else {
    terrace(ctx,p,x,y,22,18,15,palette,.4)
    for(var t=0;t<5;t++)tree(ctx,p,x-19+(t%3)*18,y-12+Math.floor(t/3)*21,25+(t%2)*12,palette)
  }
}
function building(ctx,b,palette,selected,time,scale,lens) {
  var s=b.size/2,h=b.height*b.growth,p=function(x,y,z){return project(b.x+x,b.y+y,z)}
  var active=b.focused||b.key===selected
  var light=b.circuitOverride?palette.neons[b.tint||0]:(b.groupColor||palette.accent)
  var subdued=lens&&b.appClass!==lens;if(subdued)ctx.globalAlpha=.20
  // The geometry rises and folds; windows retain their app identity throughout a move.
  polygon(ctx,[p(-s,-s,0),p(s,-s,0),p(s+10,s+8,0),p(-s+10,s+8,0)],'rgba(0,0,0,.18)')
  if(active)polygon(ctx,[p(-s-9,-s-9,1),p(s+9,-s-9,1),p(s+9,s+9,1),p(-s-9,s+9,1)],color(palette.accent,.15),color(palette.accent,.5),1)
  polygon(ctx,[p(-s,-s,h),p(-s,s,h),p(-s,s,0),p(-s,-s,0)],palette.left,color(light,.28),.8)
  polygon(ctx,[p(-s,s,h),p(s,s,h),p(s,s,0),p(-s,s,0)],palette.right,color(light,.34),.8)
  polygon(ctx,[p(-s,-s,h),p(s,-s,h),p(s,s,h),p(-s,s,h)],active?palette.roofActive:palette.roof,color(light,.8),.8)
  var floors=scale<.35?2:Math.floor(h/12)
  for(var level=0;level<floors;level++) {
    var z=5+level*(scale<.35?h/2:12)
    for(var col=0;col<3;col++) {
      var xx=-s+4+col*(b.size-8)/3,brightness=active?.95:((b.seed+level*7+col*3)%4===0?.80:.30)
      line(ctx,p(xx,s+.3,z),p(xx+Math.max(2,b.size/7),s+.3,z),color(light,brightness),2.2)
      line(ctx,p(-s-.3,xx,z),p(-s-.3,xx+Math.max(2,b.size/7),z),color(light,brightness*.6),1.6)
    }
  }
  if(b.style===1) {
    line(ctx,p(0,0,h),p(0,0,h+19),color(light,.65),1)
    ctx.beginPath();var tip=p(0,0,h+19);ctx.arc(tip.x,tip.y,1.7,0,Math.PI*2);ctx.fillStyle=light;ctx.fill()
  } else if(b.style===2)polygon(ctx,[p(-s*.65,-s*.65,h+6),p(s*.65,-s*.65,h+6),p(s*.65,s*.65,h+6),p(-s*.65,s*.65,h+6)],color(light,.16),color(light,.55),.7)
  // Neon facade band and public app sign; actual window identities only.
  line(ctx,p(-s,s+.8,h*.72),p(s,s+.8,h*.72),color(light,.8),2)
  line(ctx,p(-s,-s,h),p(-s,s,h),color(light,.65),1.3)
  if(scale>.85){var sign=p(0,s+.5,h*.72+3);ctx.font='600 '+(10/scale)+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(light,.92);ctx.fillText(b.app.slice(0,8).toUpperCase(),sign.x,sign.y)}
  if(b.style===0){polygon(ctx,[p(-s*.5,-s*.5,h),p(s*.5,-s*.5,h),p(s*.5,s*.5,h+14),p(-s*.5,s*.5,h+14)],palette.roof,color(light,.7),1)}
  if(active) {
    var top=p(0,0,h+14),pulse=1
    ctx.beginPath();ctx.ellipse(top.x,top.y,9*pulse,4*pulse,0,0,Math.PI*2);ctx.strokeStyle=color(palette.accent,.75);ctx.lineWidth=1;ctx.stroke()
    line(ctx,p(0,0,h+8),p(0,0,h+31),color(palette.accent,.7),1)
  }
  ctx.globalAlpha=1
}
function draw(ctx,scene,palette,selected,districtSelected,time,motion,scale,view,lens) {
  scale=scale||1
  ctx.lineJoin='round';ctx.lineCap='round';var paletteBase=palette
  // Archipelago bridges and lanes connect actual neighbouring workspaces.
  scene.roads.forEach(function(r){line(ctx,r.a,r.b,color(palette.accent,.14),20);line(ctx,r.a,r.b,color(palette.ink,.30),1.4);line(ctx,{x:r.a.x,y:r.a.y-4},{x:r.b.x,y:r.b.y-4},color(palette.neons[1],.28),.9)
  })
  scene.districts.forEach(function(d){
    var center=project(d.x,d.y);if(view&&(center.x+240<view.minX||center.x-240>view.maxX||center.y+180<view.minY||center.y-220>view.maxY))return
    var palette=Object.assign({},paletteBase,{accent:d.groupColor||paletteBase.neons[d.tint||0]});
    var s=120,p=function(x,y,z){return project(d.x+x,d.y+y,z)}
    polygon(ctx,[p(-s,-s,-12),p(-s,s,-12),p(s,s,-12),p(s,-s,-12)],palette.foundation,color(palette.ink,.14),1)
    polygon(ctx,[p(-s,s,0),p(s,s,0),p(s,s,-12),p(-s,s,-12)],palette.left,color(palette.accent,.14),.5)
    polygon(ctx,[p(-s,-s,0),p(-s,s,0),p(-s,s,-12),p(-s,-s,-12)],palette.right,color(palette.accent,.12),.5)
    polygon(ctx,[p(-s,-s,0),p(s,-s,0),p(s,s,0),p(-s,s,0)],palette.ground,color(palette.accent,.48),1)
    if(d.id===districtSelected)polygon(ctx,[p(-s-3,-s-3,2),p(s+3,-s-3,2),p(s+3,s+3,2),p(-s-3,s+3,2)],null,color(palette.accent,.9),1.8)
    for(var g=-90;g<=90;g+=30){line(ctx,p(g,-s,1),p(g,s,1),color(palette.ink,.045),.7);line(ctx,p(-s,g,1),p(s,g,1),color(palette.ink,.045),.7)}
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
    ctx.font='500 '+(13/scale)+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(palette.ink,.9);var label=p(0,145,0);if(scale>.26||d.id===districtSelected)ctx.fillText((d.pinned?'★ ':'')+d.name.toUpperCase(),label.x,label.y)
    ctx.font=(10/scale)+'px sans-serif';ctx.fillStyle=color(palette.ink,.6);if(scale>.44)ctx.fillText('D'+d.id+' / '+count(d.count,'WINDOW','WINDOWS')+' · '+(d.groupName||d.landmark).toUpperCase(),label.x,label.y+16/scale)
  })
  scene.buildings.slice().sort(function(a,b){return (a.x+a.y)-(b.x+b.y)}).forEach(function(b){var pos=project(b.x,b.y,b.height/2);if(!view||(pos.x+100>view.minX&&pos.x-100<view.maxX&&pos.y+120>view.minY&&pos.y-120<view.maxY))building(ctx,b,palette,selected,time,scale,lens)})
  ;(scene.groups||[]).forEach(function(g){if(scale<=.25)return;var p=project(g.x,g.y);ctx.font='600 '+(14/scale)+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(g.color,.95);ctx.fillText(g.name.toUpperCase()+' / '+count(g.count,'DISTRICT','DISTRICTS'),p.x,p.y)})
  if(!(scene.groups||[]).length)scene.boroughs.forEach(function(b){var p=project(b.x,b.y,0);ctx.font='600 '+(12/scale)+'px sans-serif';ctx.textAlign='center';ctx.fillStyle=color(palette.accent,.95);ctx.fillText(b.name.toUpperCase()+' / BOROUGH',p.x,p.y)})
}
