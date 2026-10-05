const fs=require('fs'),vm=require('vm'),assert=require('assert');
const context={console};vm.createContext(context);vm.runInContext(fs.readFileSync(__dirname+'/../CityV2.js','utf8').replace(/^\.pragma library\s*/,''),context);
const c=context;
const fixture={boroughs:[{id:0,name:'DP-1'},{id:1,name:'eDP-1'}],districts:[{id:1,seed:12,monitor:0,count:1},{id:2,seed:99,monitor:1,count:1}],windows:[{address:'0x1',workspace:1,class:'kitty',app:'Kitty',height:800,focused:true},{address:'0x2',workspace:2,class:'browser',app:'Browser',height:600}]};
let s=c.layout(fixture);assert.equal(s.buildings.length,2);assert.equal(s.boroughs.length,2);assert.notEqual(s.districts[0].x,s.districts[1].x);
for(const x of [-500,0,55,1300])for(const y of [-400,0,80,1100]){const p=c.project(x,y),q=c.unproject(p.x,p.y);assert(Math.abs(q.x-x)<1e-8);assert(Math.abs(q.y-y)<1e-8)}
let next=c.transition({buildings:[]},s,true,1000);assert.equal(next.buildings[0].growth,0);c.advance(next,1800,true);assert.equal(next.buildings[0].growth,1);
let b=next.buildings[0],p=c.project(b.x,b.y,b.height*.5);assert.equal(c.hit(next,p.x,p.y).key,'0x1');
let moved=JSON.parse(JSON.stringify(fixture));moved.windows[0].workspace=2;moved.districts[0].count=0;moved.districts[1].count=2;
let t=c.transition(next,c.layout(moved),true,2000);assert.equal(t.buildings[0].key,'0x1');c.advance(t,2700,true);assert.equal(t.buildings[0].x,t.buildings[0].targetX);
let closed=JSON.parse(JSON.stringify(moved));closed.windows=closed.windows.slice(1);let u=c.transition(t,c.layout(closed),true,3000);assert(u.buildings.some(b=>b.dying));c.advance(u,3700,true);assert.equal(u.buildings.length,1);
let reduced=c.transition({buildings:[]},c.layout(fixture),false,4000);assert(reduced.buildings.every(b=>b.growth===1));assert.equal(c.hit(reduced,99999,99999),null);
let empty=c.layout({boroughs:[],districts:[],windows:[]});assert.equal(empty.buildings.length,0);assert(Number.isFinite(empty.bounds.minX));
console.log('PASS: projection, multi-monitor layout, safe hit tests, build/fold/move lifecycle, reduced motion, empty desktop.');
