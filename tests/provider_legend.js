const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const p={};vm.createContext(p);vm.runInContext(fs.readFileSync(path.join(__dirname,'../ProviderLegendV2.js'),'utf8').replace('.pragma library',''),p);
const now=1791328800000;
function metric(s){return {state:'measured',freshness:'fresh',unit:'fraction',allowanceUsed:.2,allowanceRemaining:.8,source:'Provider quota observation',observedAt:now,resetAt:now+10000000,pace:{state:s>0?'banked':s<0?'behind':'on-pace',signedSeconds:s,source:'Provider quota observation',formula:'verified fixed-window allowance formula',meaning:'pace-equivalent allowance credit',fixedWindow:true}}}
assert.equal(p.normalizeMetric(metric(5400),now).headline,'+1h 30m banked');
assert.equal(p.normalizeMetric(metric(-5400),now).headline,'−1h 30m behind');
assert.equal(p.normalizeMetric(metric(0),now).headline,'0s · on pace');
assert(p.normalizeMetric(metric(-5400),now).wait.includes('if no additional usage'));
assert(p.normalizeMetric(metric(-5400),now).wait.includes('1h 30m'));
assert.equal(p.normalizeMetric(null,now).signedSeconds,null);
for(const patch of [{state:'unavailable'},{freshness:'unknown'},{source:''},{observedAt:null},{observedAt:now+60001}])assert.equal(p.normalizeMetric(Object.assign(metric(0),patch),now).signedSeconds,null);
assert.equal(p.normalizeMetric(Object.assign(metric(5400),{freshness:'stale'}),now).headline,'Pacing stale');
assert.equal(p.normalizeMetric(Object.assign(metric(5400),{resetAt:now}),now).headline,'Pacing stale');
const rolling=metric(-5400);rolling.pace.fixedWindow=false;assert(p.normalizeMetric(rolling,now).wait.includes('rolling or unknown'));
const invalid=metric(-5400);invalid.pace.state='banked';assert.equal(p.normalizeMetric(invalid,now).signedSeconds,null);
const agents=[{provider:'grok'},{provider:'claude'},{provider:'codex'},{provider:'pi',isKimi3:true},{provider:'pi',modelProvider:'openai'}];
const before=JSON.stringify(agents);assert.equal(p.filterAgents(agents,'kimi').length,1);assert.equal(p.filterAgents(agents,'codex').length,1);assert.equal(p.filterAgents(agents,'').length,5);assert.equal(JSON.stringify(agents),before);
const records=[{provider:'codex',metric:metric(5400),windows:[metric(5400),metric(-5400)]}],recordsBefore=JSON.stringify(records),cards=p.cards(records,agents,now);
assert.equal(cards.length,4);assert.equal(cards[2].metric.signedSeconds,5400);assert.equal(cards[0].metric.signedSeconds,null);assert.equal(cards[2].windows.length,2);assert.equal(JSON.stringify(records),recordsBefore);
assert.equal(new Set(cards.map(c=>c.color)).size,4);
const selectedPrimary=metric(-5400);selectedPrimary.label='Weekly (7-day)';
const jsonRecord=JSON.parse(JSON.stringify({provider:'codex',metric:selectedPrimary,windows:[metric(5400),selectedPrimary],ordinaryUsageAllowed:null}));
assert.equal(p.cards([jsonRecord],[],now)[2].primaryIndex,1);
assert.equal(p.cards([jsonRecord],[],now)[2].ordinaryUsageAllowed,null);
const live={provider:'codex',availability:'live',status:{type:'inProgress'},statusSource:'codex app-server thread/read',observedAt:now};
assert.equal(p.activity([live], 'codex',now),'inProgress: 1');
assert.equal(p.activity([Object.assign({},live,{availability:'stored'})], 'codex',now),'Workflow state unavailable');
assert.equal(p.activity([Object.assign({},live,{observedAt:now-900001})], 'codex',now),'Workflow state unavailable');
assert.equal(p.activity([Object.assign({},live,{statusSource:''})], 'codex',now),'Workflow state unavailable');
const long='Full source '.repeat(20),rows=p.splitRows([{label:'Source',value:long}]);assert.equal(rows.map(r=>r.value).join(''),long);assert(rows.every(r=>Array.from(r.value).length<=68));
console.log('PASS signed sourced pace, explicit unknown/stale, conditional pacing wait, provider filters and full paginated metadata.');
// Side dock: state word first, wait and local clock separate, unavailable/stale never shown as on pace.
{
 const records=[{provider:'claude',metric:metric(-5400)},{provider:'codex',metric:metric(5400)},{provider:'grok',metric:Object.assign(metric(0),{freshness:'stale'})}];
 const d=p.dock(records,[],now),byId=Object.fromEntries(d.cards.map(c=>[c.id,c]));
 assert.equal(d.cards.length,2);assert.equal(byId.claude.state,'BEHIND');assert.equal(byId.claude.amount,'1h 30m');
 assert.equal(byId.claude.wait,'Back on pace in 1h 30m');assert(byId.claude.clock.startsWith('≈ ')&&byId.claude.clock.endsWith(' local'));
 assert.equal(byId.codex.state,'BANKED');assert.equal(byId.codex.wait,'No pause needed');assert.equal(byId.codex.clock,'');
 assert(d.note.includes('Grok: stale'));assert(d.note.includes('Kimi: quota unavailable'));assert(!d.note.includes('Claude'));
 assert.equal(p.dock([{provider:'codex',metric:metric(0)}],[],now).cards[0].state,'ON PACE');
 assert.equal(p.dock([],[],now).cards.length,0);assert(p.dock([],[],now).note.includes('Grok, Claude, Codex, Kimi: quota unavailable'));
 assert.equal(p.shortClock(now+3600000,now).includes(' '),true);assert.equal(p.shortClock(null,now),null);
 console.log('PASS side dock: BANKED/ON PACE/BEHIND headline, wait and local clock separate, stale/unavailable explicit.');
}
