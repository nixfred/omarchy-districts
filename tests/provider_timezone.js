const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path'),child=require('child_process');
if(!process.env.PROVIDER_CLOCK_CHILD){
 for(const timezone of ['Etc/UTC','America/New_York'])child.execFileSync(process.execPath,[__filename],{env:Object.assign({},process.env,{TZ:timezone,PROVIDER_CLOCK_CHILD:'1'}),stdio:'inherit'});
 process.exit(0);
}
const p={};vm.createContext(p);vm.runInContext(fs.readFileSync(path.join(__dirname,'../ProviderLegendV2.js'),'utf8').replace('.pragma library',''),p);
const before=Date.parse('2026-03-08T06:50:00Z'),after=Date.parse('2026-03-08T07:10:00Z'),rollover=Date.parse('2026-10-07T00:20:00Z');
for(const stamp of [before,after,rollover]){assert(p.localClock(stamp).includes(new Date(stamp).toLocaleString()));assert(p.localClock(stamp).includes('desktop local time'))}
if(process.env.TZ==='America/New_York'){assert(p.localClock(before).includes('UTC−05:00'));assert(p.localClock(after).includes('UTC−04:00'));assert.equal(new Date(rollover).getDate(),6)}
else {assert(p.localClock(after).includes('UTC+00:00'));assert.equal(new Date(rollover).getDate(),7)}
const metric={state:'measured',freshness:'fresh',unit:'fraction',allowanceUsed:.5,allowanceRemaining:.5,source:'Verified quota source',observedAt:before,resetAt:after+3600000,pace:{state:'behind',signedSeconds:-1200,meaning:'pace-equivalent allowance credit',source:'Verified quota source',formula:'Verified fixed-window model',fixedWindow:true,recoveryAt:after}};
const normalized=p.normalizeMetric(metric,before);assert(normalized.wait.includes('20m'));assert(normalized.recoveryClock.includes(new Date(after).toLocaleString()));assert(normalized.wait.includes('if no additional usage'));
assert.equal(p.localClock(null),null);assert.equal(p.localClock(1e20),null);assert.equal(p.normalizeMetric(null,before).recoveryClock,null);
console.log('PASS actual local clock, date rollover, DST and unknown estimates in '+process.env.TZ);
