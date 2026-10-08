.pragma library
// Actual session metadata has its own courts. Courts are never real workspaces.
var maxRecords=128,maxVisibleDepth=8,cell=74,padding=64,courtGap=96
function key(r){return 'agent:'+String(r.provider||'unknown')+':'+String(r.id||r.sessionId||'')}
function shortId(value){return String(value||'').replace(/[^A-Za-z0-9-]/g,'').slice(0,8)}
var providerTitles={codex:'Codex',claude:'Claude',grok:'Grok',pi:'Pi',kimi:'Kimi'}
function providerTitle(r){return r&&r.isKimi3===true?'Kimi':providerTitles[r&&r.provider]||String(r&&r.provider||'Agent')}
function clean(value,limit){return typeof value==='string'?value.replace(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\u2066-\u2069]/g,' ').replace(/\s+/g,' ').trim().slice(0,limit||64):''}
// Real provider-recorded names first; a project basename next; the short ID last.
function displayName(r){if(!r)return 'Agent';var name=clean(r.name);if(name)return name;var project=clean(r.project,40);if(project)return providerTitle(r)+' · '+project;return clean(r.label)||providerTitle(r)+' '+shortId(r.id||r.sessionId)}
// Roof sign: whole leading words of the name up to 10 characters, so signs read
// "FIX PULSE" or "BLIP:GUS" rather than a mid-word cut.
function signText(name){var text=clean(name),out='',parts=text.split(/([\s:_\-\/·]+)/);for(var i=0;i<parts.length;i+=2){var next=out+(i?parts[i-1]:'')+parts[i];if(next.length>10)break;out=next}out=out.replace(/[\s:_\-\/·]+$/,'');return out||text.slice(0,9)}
function signFor(r){if(clean(r&&r.name))return signText(r.name);if(clean(r&&r.project,40))return signText(r.project);return providerTitle(r).slice(0,4)+' '+shortId(r&&(r.id||r.sessionId)).slice(0,4)}
function hasRealName(r){return !!clean(r&&r.name)}
function subtitle(r){if(!r)return '';var parts=[providerTitle(r)];var project=clean(r.project,40);if(project&&clean(r.name))parts.push(project);parts.push(String(r.availability||'unknown'));var status=r.status&&typeof r.status.type==='string'?r.status.type:'unknown';parts.push(status);return parts.join(' · ')}
// Building glow follows the adapter's reported workflow state, never a PID or
// decorative timer. Stored or unreported sessions stay dim and say so.
var glowStates={
 working:{state:'working',label:'Working',color:'#57dfff',illumination:.85,pulse:true},
 waiting:{state:'waiting',label:'Needs attention',color:'#ffb347',illumination:.7,pulse:true},
 idle:{state:'idle',label:'Idle',color:'#57dfff',illumination:.34,pulse:false},
 dormant:{state:'dormant',label:'Stored / not reported live',color:'#6f7d93',illumination:.1,pulse:false}
}
function glow(r){
 if(!r||r.availability!=='live')return glowStates.dormant
 var status=r.status||{},type=String(status.type||'').toLowerCase(),flags=Array.isArray(status.activeFlags)?status.activeFlags:[]
 if(flags.indexOf('waitingOnApproval')>=0||flags.indexOf('waitingOnUserInput')>=0||['blocked','waiting','waitingonapproval','waitingonuserinput','needsinput'].indexOf(type)>=0)return glowStates.waiting
 if(['busy','active','working','running','thinking','streaming'].indexOf(type)>=0)return glowStates.working
 if(type==='idle')return glowStates.idle
 return glowStates.dormant
}
// Status and names change without moving geometry; refresh them in place.
function applyState(b,r){if(!b||!r)return b;var g=glow(r);b.agent=r;b.app=displayName(r);b.sign=signFor(r);b.agentGlow=g;b.illumination=g.illumination;return b}
function records(value){var seen=Object.create(null),out=[];(Array.isArray(value)?value:[]).slice(0,maxRecords).forEach(function(r){if(!r||!String(r.id||r.sessionId||'')||typeof r.provider!=='string'||!r.provider)return;var k=key(r);if(seen[k])return;seen[k]=true;out.push(r)});return out.sort(function(a,b){return key(a).localeCompare(key(b))})}
function parent(r,list){if(!r.parentId)return null;return list.find(function(p){return p.provider===r.provider&&String(p.id||p.sessionId)===String(r.parentId)})||null}
function familyMap(list){
 // Real parent links keep components together even when reported family IDs differ.
 // A shared explicit family ID may join components, but never creates parent links.
 var roots=Object.create(null),reported=Object.create(null),components=Object.create(null),answer=Object.create(null)
 list.forEach(function(r){roots[key(r)]=key(r)})
 function find(k){while(roots[k]!==k){roots[k]=roots[roots[k]];k=roots[k]}return k}
 function join(a,b){a=find(a);b=find(b);if(a!==b){var first=a<b?a:b;roots[a]=first;roots[b]=first}}
 list.forEach(function(r){var p=parent(r,list);if(p)join(key(r),key(p));if(r.familyId){var f=String(r.provider)+':'+String(r.familyId);if(reported[f])join(key(r),reported[f]);else reported[f]=key(r)}})
 list.forEach(function(r){var k=find(key(r));if(!components[k])components[k]=[];components[k].push(r)})
 Object.keys(components).forEach(function(k){var rows=components[k],top=rows.filter(function(r){return !r.parentId}).map(key).sort(),explicit=rows.filter(function(r){return !!r.familyId}).map(function(r){return String(r.provider)+':'+String(r.familyId)}).sort(),f=explicit.length?'family:'+explicit[0]:top.length?top[0]:rows.map(key).sort()[0];rows.forEach(function(r){answer[key(r)]=f})})
 return answer
}
function family(r,list){return familyMap(list)[key(r)]||key(r)}
function actualDepth(r,list){
 var at=r,path=[],seen=Object.create(null)
 while(at&&path.length<=maxRecords){var k=key(at);if(seen[k]!==undefined)return seen[k];seen[k]=path.length;path.push(k);var p=parent(at,list);if(!p)return path.length-1;at=p}
 return maxRecords
}
function localCourt(rows,index){
 var positions=Object.create(null),levels=Object.create(null),ordered=rows.slice(),dimensions=[],width=180,totalDepth=0
 ordered.sort(function(a,b){return actualDepth(a,rows)-actualDepth(b,rows)||key(a).localeCompare(key(b))})
 ordered.forEach(function(r){var level=Math.min(maxVisibleDepth,actualDepth(r,rows));if(!levels[level])levels[level]=[];levels[level].push(r)})
 Object.keys(levels).map(Number).sort(function(a,b){return a-b}).forEach(function(level){
  var siblings=levels[level],cols=Math.min(12,Math.max(1,Math.ceil(Math.sqrt(siblings.length)))),rowCount=Math.ceil(siblings.length/cols),span=(cols-1)*cell+30
  dimensions.push({level:level,entries:siblings,cols:cols,rows:rowCount,start:totalDepth});width=Math.max(width,span+padding*2);totalDepth+=rowCount*cell
 })
 var depth=Math.max(180,Math.max(0,totalDepth-cell)+30+padding*2)
 dimensions.forEach(function(layer){layer.entries.forEach(function(r,i){var actual=actualDepth(r,rows),isRoot=!r.parentId&&r.isSubagent!==true,x=(i%layer.cols-(layer.cols-1)/2)*cell,y=-depth/2+padding+15+layer.start+Math.floor(i/layer.cols)*cell,k=key(r),b={key:k,kind:'agent',address:null,sessionId:String(r.id||r.sessionId),agent:r,agentDepth:actual,depthClamped:actual>maxVisibleDepth,reportedRoot:isRoot,workspace:0,virtualWorkspace:true,app:displayName(r),sign:signFor(r),appClass:'agent:'+String(r.provider),icon:'applications-development',focused:false,urgent:false,floating:false,width:0,windowHeight:0,tint:0,group:'agent-sessions',groupColor:'#57dfff',circuitOverride:false,x:x,y:y,size:30,height:isRoot?105:65,style:isRoot?0:2,seed:Math.abs(index*maxRecords+ordered.indexOf(r)+29),monitor:-1,ownerPid:null,ownerCpu:{state:'unavailable',scope:'session-not-process'},agentGlow:glow(r),illumination:glow(r).illumination};positions[k]=b})})
 return {width:width,height:depth,positions:positions,ordered:ordered}
}
function isRoot(r){return !r.parentId&&r.isSubagent!==true}
// A collapsed family court keeps its reported root building(s) and counts the
// rest. Session records themselves are untouched; the Desk still lists them.
function decorate(scene,input,options){
 var agents=records(input),next=Object.assign({},scene),list=Object.create(null),collapsed=options&&options.collapsed||{},membership=Object.create(null)
 next.districts=(scene.districts||[]).slice();next.buildings=(scene.buildings||[]).slice();next.roads=(scene.roads||[]).slice();next.groups=(scene.groups||[]).slice()
 if(!agents.length)return next
 var familiesByKey=familyMap(agents)
 agents.forEach(function(r){var f=familiesByKey[key(r)];if(!list[f])list[f]=[];list[f].push(r)})
 Object.keys(list).forEach(function(f){var all=list[f],roots=all.filter(isRoot),kept=collapsed[f]&&roots.length&&roots.length<all.length?roots:all;membership[f]={all:all.length,collapsible:roots.length>0&&roots.length<all.length,collapsed:kept!==all,hidden:all.length-kept.length};list[f]=kept})
 var families=Object.keys(list).sort(),maxX=0,minY=0,totalArea=0,maxWidth=0,courts=families.map(function(f,index){var court=localCourt(list[f],index);court.family=f;court.index=index;totalArea+=(court.width+courtGap)*(court.height+courtGap);maxWidth=Math.max(maxWidth,court.width);return court})
 next.districts.forEach(function(d){var width=Number(d.width)||Number(d.size)||240,depth=Number(d.depth)||Number(d.height)||Number(d.size)||240;maxX=Math.max(maxX,d.x+width/2);minY=Math.min(minY,d.y-depth/2)})
 var baseX=maxX+320,baseY=minY,targetWidth=Math.max(maxWidth,Math.ceil(Math.sqrt(totalArea)*1.25/cell)*cell),offsetX=0,offsetY=0,rowHeight=0,bounds={minX:baseX,minY:baseY,maxX:baseX,maxY:baseY}
 var group={key:'agent-sessions',name:'AGENT SESSIONS',color:'#57dfff',count:families.length,x:baseX,y:baseY,width:0,height:0}
 courts.forEach(function(court){
  if(offsetX&&offsetX+court.width>targetWidth){offsetX=0;offsetY+=rowHeight+courtGap;rowHeight=0}
  var rows=list[court.family],courtX=baseX+offsetX+court.width/2,courtY=baseY+offsetY+court.height/2,virtualId=-900000-court.index,reportedRoot=rows.find(function(r){return !r.parentId}),label=reportedRoot||rows[0],worldBounds={minX:courtX-court.width/2,maxX:courtX+court.width/2,minY:courtY-court.height/2,maxY:courtY+court.height/2}
  var district={id:virtualId,kind:'agentFamily',virtualWorkspace:true,sessionFamily:court.family,familyId:label.familyId||null,familyProvider:label.familyId?label.provider:null,seed:court.index+103,monitor:-1,count:rows.length,x:courtX,y:courtY,width:court.width,height:court.height,size:Math.max(court.width,court.height),worldBounds:worldBounds,name:displayName(label),nameSource:hasRealName(label)?'session-name':'session',customName:'',autoName:'',pinned:false,tint:0,circuitOverride:false,group:'agent-sessions',groupName:'Agent sessions',groupColor:group.color,groupReason:'Explicit session metadata; separate from desktop workspaces',landmark:'Session court',collapsible:membership[court.family].collapsible,collapsed:membership[court.family].collapsed,hiddenCount:membership[court.family].hidden,familyCount:membership[court.family].all}
  next.districts.push(district)
  court.ordered.forEach(function(r){var b=court.positions[key(r)];b.x+=courtX;b.y+=courtY;b.workspace=virtualId;if(district.collapsed&&isRoot(r))b.collapsedChildren=district.hiddenCount;next.buildings.push(b)})
  court.ordered.forEach(function(r){var p=parent(r,rows),a=court.positions[key(r)],b=p?court.positions[key(p)]:null;if(b&&a.key!==b.key)next.roads.push({kind:'agent-link',parentKey:b.key,childKey:a.key,worldA:{x:b.x,y:b.y,z:0},worldB:{x:a.x,y:a.y,z:0},a:{x:0,y:0},b:{x:0,y:0},seed:a.seed})})
  bounds.maxX=Math.max(bounds.maxX,worldBounds.maxX);bounds.maxY=Math.max(bounds.maxY,worldBounds.maxY);offsetX+=court.width+courtGap;rowHeight=Math.max(rowHeight,court.height)
 })
 group.x=(bounds.minX+bounds.maxX)/2;group.y=bounds.minY-64;group.width=bounds.maxX-bounds.minX;group.height=bounds.maxY-bounds.minY;group.worldBounds=bounds;group.labelWorld={x:group.x,y:group.y,z:0};next.groups.push(group);return next
}
