const fs=require('fs'),vm=require('vm'),assert=require('assert');
const n={};vm.createContext(n);vm.runInContext(fs.readFileSync(__dirname+'/../NavigationV2.js','utf8').replace(/^\.pragma library\s*/,''),n);
const snapshot=(workspace=1,extra={})=>({schema:1,boroughs:[{id:0,name:'/private/monitor'}],districts:[{id:1,monitor:0,seed:123,name:'Secret project',group:'development',groupColor:'#4caf50'},{id:2,monitor:0,seed:22}],windows:[{address:'0xa',workspace,monitor:0,class:'Code',app:'/private/name',height:700,width:900,title:'PRIVATE TITLE',url:'https://private',pid:77,ownerCpu:{state:'measured',percent:99},...extra}],agents:[{id:'session-1',parentId:'parent-1',status:'working',source:'codex',latestReply:'PRIVATE REPLY',cwd:'/private'}]});
let camera=n.camera({x:Infinity,y:-2e9,zoom:100,yaw:765,tilt:95});assert.equal(camera.x,0);assert.equal(camera.y,-1e6);assert.equal(camera.zoom,6);assert.equal(camera.yaw,45);assert.equal(camera.tilt,75);
assert.equal(n.name(' \nNew\x00 view\t '),'New view');assert.equal(n.target(-1),null);assert.equal(n.target('1.2'),null);
assert.equal(JSON.stringify(n.tourIds([{id:3},{id:1},{id:3},{id:0}])), '[3,1]');assert.equal(n.nextTour([3,1,2],0,[{id:2}]).id,2);assert.equal(n.nextTour([3],0,[{id:3}]),null);
let h=n.createHistory();assert(n.observe(h,snapshot(),null,1000));assert.equal(h.frames.length,1);assert.equal(h.frames[0].boundary,'tracking-started');assert.equal(h.frames[0].events.length,0);
let raw=JSON.stringify(h);for(const privateText of ['PRIVATE','Secret project','https://private','/private','latestReply','"pid":77','"percent":99'])assert(!raw.includes(privateText),privateText+' omitted');assert.equal(h.frames[0].snapshot.windows[0].ownerCpu.state,'unavailable');assert.equal(h.frames[0].snapshot.windows[0].app,'Code');assert.equal(h.frames[0].snapshot.districts[0].name,'District 1');
assert(!n.observe(h,snapshot(2),null,1500),'bounded sample cadence');assert(n.observe(h,snapshot(2),null,3100));assert.equal(h.frames[1].events[0].kind,'window-membership-changed');assert.equal(h.frames[1].events[0].fromWorkspace,1);assert.equal(h.frames[1].events[0].workspace,2);assert.equal(h.frames[1].boundary,'');
let empty=snapshot();empty.windows=[];empty.agents=[];assert(n.observe(h,empty,null,5200));assert(h.frames[2].events.some(e=>e.kind==='window-no-longer-observed'));assert(h.frames[2].events.some(e=>e.kind==='agent-no-longer-observed'));
n.pause(h);assert(n.observe(h,snapshot(),null,8000));assert.equal(h.frames[3].boundary,'tracking-resumed');assert.equal(h.frames[3].events.length,0,'no invented events across a gap');
let changed=snapshot();changed.agents[0].status='approval';assert(n.observe(h,changed,null,10100));assert.equal(h.frames[4].events[0].kind,'agent-status-reported');assert.equal(h.frames[4].events[0].status.type,'approval');
assert(!n.observe(h,{...changed,windows:changed.windows.map(w=>({...w,title:'Different private title',ownerCpu:{state:'measured',percent:1}}))},null,12500),'content/CPU changes are not replay events');
for(let i=0;i<220;i++)n.observe(h,snapshot(i%2+1),null,15000+i*2100);assert(h.frames.length<=120);assert(h.bytes<=512*1024);assert(h.dropped>0);assert(h.frames.every(f=>f.timestamp>=15000));
n.prune(h,3e6);assert.equal(h.frames.length,0);assert.equal(h.bytes,0);
let giant=n.createHistory(),big=snapshot();big.windows=Array.from({length:900},(_,i)=>({address:'0x'+i,workspace:1,class:'x'.repeat(80),width:10000,height:10000}));assert(n.observe(giant,big,null,1e6));assert.equal(giant.frames[0].snapshot.windows.length,512);assert.equal(giant.frames[0].snapshot.truncated,true);for(let i=1;i<10;i++){big.windows[0].workspace=i%2+1;n.observe(giant,big,null,1e6+i*2100)}assert(giant.bytes<=512*1024);assert(giant.frames.length<10);
assert.equal(n.metadata(snapshot(1,{class:'/private/path',address:'/private/address'})).windows.length,0);assert.equal(n.metadata(snapshot(1,{class:'/private/path'})).windows[0].app,'Unknown');
let native=snapshot();native.agents[0].status={type:'active',activeFlags:['waitingOnApproval','private-flag']};native.agents[0].statusSource='Codex app server';let m=n.metadata(native);assert.equal(m.agents[0].status.type,'active');assert.equal(JSON.stringify(m.agents[0].status.activeFlags),'["waitingOnApproval"]');assert.equal(m.agents[0].source,'Codex app server');assert.equal(n.statusText(m.agents[0].status),'active / approval pending');let same=n.differences(m,n.metadata(native),9000);assert.equal(same.length,0,'reported object state equality is semantic');native.agents[0].status.activeFlags=['waitingOnUserInput'];let statusEvent=n.differences(m,n.metadata(native),12000);assert.equal(statusEvent[0].kind,'agent-status-reported');assert.equal(statusEvent[0].status.activeFlags[0],'waitingOnUserInput');
console.log('PASS: camera normalization, actual tour membership, history cadence/gaps, metadata privacy, actual membership/status observations, unavailable replay CPU, age/count/size caps.');

// Use the actual family-lens controller to verify raw history can retain live filters.
const lens={};vm.createContext(lens);vm.runInContext(fs.readFileSync(__dirname+'/../LensV2.js','utf8').replace(/^\.pragma library\s*/,''),lens);
const uuid='11111111-2222-4333-8444-555555555555';
const collision={...snapshot(),agents:[
 {id:uuid,provider:'codex',familyId:'actual-family',parentId:'parent-uuid',status:{type:'active',activeFlags:[]},statusSource:'Codex app server',title:'PRIVATE TITLE',latestReply:'PRIVATE REPLY',cwd:'/private'},
 {id:uuid,provider:'claude',familyId:'actual-family',parentId:'other-parent',status:{type:'idle',activeFlags:[]},statusSource:'Claude adapter'},
 {id:uuid,provider:'codex',familyId:'actual-family',parentId:'parent-uuid',status:{type:'active',activeFlags:[]},statusSource:'Codex app server'}
]};
const collisionBefore=JSON.stringify(collision),replay=n.metadata(collision);
assert.equal(replay.agents.length,2,'same UUID in two providers remains two records; duplicate in one provider dedupes');
assert.equal(replay.agents.map(a=>n.agentKey(a)).join(','),'claude:'+uuid+',codex:'+uuid,'provider-scoped deterministic record order');
assert.equal(replay.agents.find(a=>a.provider==='codex').familyId,'actual-family');
assert.equal(replay.agents.find(a=>a.provider==='codex').parentId,'parent-uuid');
const cleanCollision={...collision,agents:collision.agents.slice(0,2)};
for(const provider of ['codex','claude']){const scoped={kind:'family',value:'actual-family',provider};assert.equal(lens.apply(cleanCollision,scoped).agents.length,1);assert.equal(lens.apply(replay,scoped).agents.length,1);assert.equal(lens.apply(replay,scoped).agents[0].provider,provider)}
assert.equal(lens.apply(replay,{kind:'family',value:'actual-family'}).agents.length,2);
assert.equal(JSON.stringify(collision),collisionBefore,'metadata and family filtering never mutate input');
const collisionRaw=JSON.stringify(replay);for(const secret of ['PRIVATE','/private','latestReply','cwd','title'])assert(!collisionRaw.includes(secret));
const invalidFamily=n.metadata({...snapshot(),agents:[{id:uuid,provider:'codex',familyId:'/private/family',parentId:'https://private/path',status:'idle'},{id:'second-id',provider:'codex',status:'idle'}]});assert(invalidFamily.agents.every(a=>a.familyId===''));assert(invalidFamily.agents.every(a=>a.parentId===''),'invalid paths/URLs and missing lineage remain absent');
const pairBefore=n.metadata({...snapshot(),agents:collision.agents.slice(0,2)});
const altered=JSON.parse(JSON.stringify(collision.agents.slice(0,2)));altered[1].status={type:'active',activeFlags:['waitingOnApproval']};
const oneChange=n.differences(pairBefore,n.metadata({...snapshot(),agents:altered}),22000).filter(e=>e.kind.startsWith('agent-'));
assert.equal(oneChange.length,1);assert.equal(oneChange[0].kind,'agent-status-reported');assert.equal(oneChange[0].id,'claude:'+uuid);assert.equal(oneChange[0].provider,'claude');assert.equal(oneChange[0].sessionId,uuid);
const removal=n.differences(pairBefore,n.metadata({...snapshot(),agents:[collision.agents[1]]}),25000).filter(e=>e.kind.startsWith('agent-'));
assert.equal(removal.length,1);assert.equal(removal[0].kind,'agent-no-longer-observed');assert.equal(removal[0].id,'codex:'+uuid);assert.equal(removal[0].provider,'codex');
const appearance=n.differences(n.metadata({...snapshot(),agents:[collision.agents[0]]}),pairBefore,28000).filter(e=>e.kind.startsWith('agent-'));
assert.equal(appearance.length,1);assert.equal(appearance[0].kind,'agent-observed');assert.equal(appearance[0].id,'claude:'+uuid);
assert.equal(n.differences(pairBefore,n.metadata({...snapshot(),agents:collision.agents.slice(0,2).reverse()}),31000).length,0,'provider order does not fabricate events');
let familyHistory=n.createHistory();assert(n.observe(familyHistory,collision,null,100000));assert.equal(lens.apply(n.frameAt(familyHistory,0).snapshot,{kind:'family',value:'actual-family',provider:'codex'}).agents.length,1,'family lens survives actual retained frame round trip');
console.log('PASS: provider-scoped replay identities/events, exact opaque family IDs, raw-frame family lens round trip, private-content exclusion and absent lineage preservation.');
