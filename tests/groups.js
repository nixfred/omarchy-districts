const fs=require('fs'),vm=require('vm'),assert=require('assert');
const g={},c={};for(const [scope,name]of [[g,'GroupsV2.js'],[c,'CityV2.js']]){vm.createContext(scope);vm.runInContext(fs.readFileSync(__dirname+'/../'+name,'utf8').replace(/^\.pragma library\s*/,''),scope)}
const prefs=g.preferences(),d={id:1,autoName:'Workspace 1',autoSource:'number'};
const w=(id,key,categories=[])=>({address:'0x'+id,workspace:1,class:key,app:key,desktopCategories:categories,height:600});
assert.equal(g.classify(d,[w(1,'Code'),w(2,'kitty'),w(3,'Brave')],prefs).key,'development');
assert.equal(g.classify(d,[w(1,'Spotify'),w(2,'Discord')],prefs).key,'mixed');
assert.equal(g.classify(d,[w(1,'Code'),w(2,'Code'),w(3,'Discord')],prefs).key,'mixed','duplicate windows are one app-role vote');
assert.equal(g.classify(d,[w(1,'Code'),w(2,'zed'),w(3,'Discord')],prefs).key,'development');
assert.equal(g.classify(d,[w(1,'Firefox',['Office','WebBrowser'])],prefs).key,'mixed');
assert.equal(g.classify(d,[w(1,'Unknown',['Network'])],prefs).key,'mixed');
assert.equal(g.classify(d,[w(1,'Unknown',['Development'])],prefs).key,'development');
assert.equal(g.classify(d,[w(1,'Unknown',['Development','Game'])],prefs).key,'mixed');
assert.equal(g.classify({...d,autoSource:'workspace',autoName:'Research'},[w(1,'Brave')],prefs).key,'research');
assert.equal(g.classify({...d,name:'Development',nameSource:'custom'},[w(1,'Brave')],prefs).key,'mixed','custom district names do not become hidden classification');
assert.equal(g.classify(d,[],prefs).key,'mixed');assert.equal(g.classify(d,[w(1,'kitty')],prefs).key,'system');
assert.equal(g.classify(d,[w(1,'__proto__',['Development'])],prefs).key,'development');
assert.equal(g.classify(d,[w(1,'Code')],{revision:1,rules:{code:'research'},colors:{}}).key,'research');
assert.equal(g.classify(d,[w(1,'Code'),w(2,'Brave')],{revision:1,rules:{code:'mixed'},colors:{}}).key,'mixed');
let snapshot={boroughs:[{id:0,name:'Monitor'}],districts:[{...d,seed:3,monitor:0,count:1}],windows:[w(1,'Code')]},history={};
let first=g.enrich(snapshot,history,0,prefs);assert.equal(first.districts[0].group,'development');
let focus=JSON.parse(JSON.stringify(snapshot));focus.windows[0].focused=true;assert.equal(g.enrich(focus,history,100,prefs).districts[0].group,'development');
let changed={...snapshot,windows:[w(2,'Spotify')]};assert.equal(g.enrich(changed,history,1000,prefs).districts[0].group,'development');assert.equal(g.enrich(changed,history,6999,prefs).districts[0].group,'development');assert.equal(g.enrich(changed,history,7000,prefs).districts[0].group,'entertainment');
assert.equal(g.enrich(changed,history,7100,{revision:2,rules:{spotify:'communication'},colors:{communication:'#123456'}}).districts[0].group,'communication');
assert.equal(g.enrich(changed,history,7200,{revision:2,rules:{spotify:'communication'},colors:{communication:'#123456'}}).districts[0].groupColor,'#123456');
g.enrich({...snapshot,districts:[]},history,8000,prefs);assert.equal(Object.keys(history).length,0);
const keys=g.groups.map(x=>x.key);assert.equal(new Set(g.groups.map(x=>x.color)).size,6);
const many={boroughs:[{id:0,name:'DP-1'},{id:1,name:'DP-2'}],districts:Array.from({length:512},(_,i)=>({id:i+1,monitor:i%2,seed:i,group:keys[i%6],groupName:keys[i%6],groupColor:g.info(keys[i%6]).color,count:1})),windows:Array.from({length:512},(_,i)=>({...w(i,'Code'),workspace:i+1,monitor:i%2}))};
let scene=c.layout(many);assert.equal(scene.districts.length,512);assert.equal(scene.buildings.length,512);assert.equal(scene.groups.length,6);assert(scene.roads.length<=1024);
for(let i=0;i<scene.districts.length;i++)for(let j=i+1;j<scene.districts.length;j++){let a=scene.districts[i],b=scene.districts[j];assert(Math.abs(a.x-b.x)>=290||Math.abs(a.y-b.y)>=290,'district footprints never overlap')}
assert(scene.districts.every(x=>many.districts.find(d=>d.id===x.id).monitor===x.monitor));assert(scene.buildings.every(x=>many.windows.find(w=>w.address===x.key).workspace===x.workspace));
const positions=s=>JSON.stringify(s.districts.map(d=>[d.id,d.x,d.y]));assert.equal(positions(scene),positions(c.layout({...many,windows:many.windows.map(w=>({...w,focused:true}))})));
assert.equal(positions(scene),positions(c.layout({...many,districts:[...many.districts].reverse()})));
const flat=c.layout({...many,districts:many.districts.map(d=>({...d,group:'development'}))});assert.equal(flat.groups.length,1);assert(Number.isFinite(flat.bounds.maxY));
console.log('PASS: conservative role classification; neutral browsers/helpers; global rules; 6s stability; six distinct colors; 512-district clusters; focus/order stability; no topology mutation.');
// Color-only and unrelated rule edits preserve a pending automatic activity change.
let slow={},start=g.enrich(snapshot,slow,0,prefs);g.enrich(changed,slow,1000,prefs);
let painted=g.enrich(changed,slow,2000,{revision:1,rules:{},colors:{development:'#123456'}});assert.equal(painted.districts[0].group,'development');assert.equal(painted.districts[0].groupPending,true);
assert.equal(g.enrich(changed,slow,3000,{revision:2,rules:{discord:'research'},colors:{}}).districts[0].group,'development');assert.equal(g.enrich(changed,slow,7000,{revision:2,rules:{discord:'research'},colors:{}}).districts[0].group,'entertainment');
const saved=g.appEntries({windows:[]},{rules:{code:'research'},colors:{}});assert.equal(saved.length,1);assert.equal(saved[0].payload.class,'code');assert(saved[0].subtitle.includes('not running'));
let texts=[];const ctx=new Proxy({},{get(t,k){return k in t?t[k]:(...args)=>{if(k==='fillText')texts.push(args[0])}},set(t,k,v){t[k]=v;return true}});
let small=c.transition({buildings:[]},c.layout({...many,districts:many.districts.slice(0,12),windows:many.windows.slice(0,12)}),false,0);
c.draw(ctx,small,{accent:'#ffffff',ink:'#ffffff',neons:g.groups.map(g=>g.color),ground:'#111111',foundation:'#111111',left:'#111111',right:'#111111',roof:'#111111',roofActive:'#222222'},'',-1,0,false,1,null,'');
assert.equal(texts.filter(t=>t.includes('DISTRICTS')).length,6,'all city labels paint without JS exceptions');
for(const group of small.groups){const p=c.project(group.x,group.y);assert.equal(c.hit(small,p.x,p.y-8,1).type,'group');assert.equal(c.hit(small,p.x,p.y-8,1).key,group.key)}
console.log('PASS: color/rule edits preserve settling; saved inactive rules remain editable; group headers paint and hit their group.');
