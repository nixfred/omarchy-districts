.pragma library
// Identity/filtering and display only. No provider calls, credentials or compositor actions.
var providers=[{id:'grok',name:'Grok',color:'#b787ff'},{id:'claude',name:'Claude',color:'#f5ad75'},{id:'codex',name:'Codex',color:'#72d6b0'},{id:'kimi',name:'Kimi',color:'#7eaeff'}]
var meaning='pace-equivalent allowance credit'
function identity(value){return typeof value==='string'&&providers.some(function(p){return p.id===value})?value:''}
function agentProvider(agent){if(!agent)return '';return agent.isKimi3===true?'kimi':identity(agent.provider)}
function filterAgents(agents,provider){provider=identity(provider);return (agents||[]).filter(function(a){return !provider||agentProvider(a)===provider})}
function finite(value){return typeof value==='number'&&isFinite(value)}
function timestamp(value){var t=typeof value==='string'?Date.parse(value):value;return finite(t)&&t>0?t:null}
function duration(seconds){if(!finite(seconds)||seconds<0)return 'Unavailable';var value=Math.ceil(seconds);if(value<60)return value+'s';var minutes=Math.ceil(value/60);if(minutes<60)return minutes+'m';var h=Math.floor(minutes/60),m=minutes%60;return h+'h'+(m?' '+m+'m':'')}
function localClock(value){
 var stamp=timestamp(value);if(!stamp)return null
 var date=new Date(stamp),offset=-date.getTimezoneOffset();if(!finite(offset))return null
 var hours=Math.floor(Math.abs(offset)/60),minutes=Math.abs(offset)%60
 return date.toLocaleString()+' (desktop local time, UTC'+(offset<0?'−':'+')+String(hours).padStart(2,'0')+':'+String(minutes).padStart(2,'0')+')'
}
function numeric(value,unit){if(!finite(value)||value<0)return 'Unavailable';return unit==='fraction'?(value*100).toFixed(1)+'%':unit==='percent'?value.toFixed(1)+'%':value.toFixed(value%1?1:0)+' '+unit}
function activity(agents,provider,now){
 var states=Object.create(null),eligible=filterAgents(agents,provider).filter(function(a){var stamp=timestamp(a.observedAt);return a.availability==='live'&&a.status&&typeof a.status.type==='string'&&a.status.type.length<=40&&typeof a.statusSource==='string'&&!!a.statusSource&&stamp&&stamp<=now+60000&&now-stamp<=900000})
 eligible.forEach(function(a){states[a.status.type]=(states[a.status.type]||0)+1})
 var keys=Object.keys(states).sort();return keys.length?keys.slice(0,4).map(function(k){return k+': '+states[k]}).join(' · ')+(keys.length>4?' · additional reported states':''):'Workflow state unavailable'
}
function normalizeMetric(metric,now){
 var absent={state:'unavailable',headline:'Pacing unavailable',signedSeconds:null,wait:'Estimated pacing wait unavailable',recoveryClock:null,used:'Unavailable',remaining:'Unavailable',reset:'Unavailable',source:'No supported metric source',observed:'Observation unavailable',reason:'No verified quota observation',meaning:meaning}
 if(!metric||typeof metric!=='object')return absent
 var result=Object.assign({},absent),observed=timestamp(metric.observedAt),reset=timestamp(metric.resetAt)
 if(typeof metric.source==='string'&&metric.source&&metric.source.length<=160)result.source=metric.source
 if(observed)result.observed=new Date(observed).toLocaleString()
 if(typeof metric.reason==='string')result.reason=metric.reason.slice(0,160)
 if(metric.state==='stale'||metric.freshness==='stale'||observed&&now-observed>900000||reset&&now>=reset){result.state='stale';result.headline='Pacing stale';result.wait='Estimated pacing wait unavailable: refresh the observation';return result}
 if(metric.state!=='measured'||metric.freshness!=='fresh'||!observed||observed>now+60000||result.source===absent.source)return result
 result.state='measured';result.reason='Pacing as of the quota observation'
 if(['fraction','percent','requests','credits'].indexOf(metric.unit)>=0){result.used=numeric(metric.allowanceUsed,metric.unit);result.remaining=numeric(metric.allowanceRemaining,metric.unit)}
 if(reset)result.reset=new Date(reset).toLocaleString()
 var p=metric.pace,s=p&&p.signedSeconds
 if(!p||p.meaning!==meaning||!finite(s)||typeof p.source!=='string'||!p.source||p.source.length>160||typeof p.formula!=='string'||!p.formula||p.formula.length>256)return result
 if(p.fixedWindow!==true||!reset){result.wait='Estimated pacing wait unavailable: rolling or unknown window';return result}
 var start=timestamp(p.windowStartAt)
 if(start){var expected=(observed-start)/1000-metric.allowanceUsed*(reset-start)/1000;if(metric.unit!=='fraction'||!finite(expected)||Math.abs(expected-s)>.001)return result}
 if(p.state!==(s>0?'banked':s<0?'behind':'on-pace'))return result
 result.signedSeconds=s;result.paceState=p.state;result.headline=s>0?'+'+duration(s)+' banked':s<0?'−'+duration(-s)+' behind':'0s · on pace'
 result.reason='Allowance pacing credit; no guaranteed compute time or rollover credit'
 if(s<0){
  if(p.fixedWindow===true&&reset){var expectedRecovery=observed-s*1000,recovery=timestamp(p.recoveryAt)||expectedRecovery;if(recovery<=reset&&Math.abs(recovery-expectedRecovery)<1000){result.wait='Estimated pacing wait '+duration(Math.max(0,(recovery-now)/1000))+' if no additional usage';result.recoveryClock=localClock(recovery)}else result.wait='Estimated pacing wait unavailable: window assumption invalid'}
  else result.wait='Estimated pacing wait unavailable: rolling or unknown window'
 }else result.wait='No pacing pause indicated by this observation'
 return result
}
function primaryIndex(record,windows){var m=record.metric;if(!m)return 0;var index=windows.findIndex(function(w){return w===m||w.label===m.label&&w.observedAt===m.observedAt&&w.pace&&m.pace&&w.pace.signedSeconds===m.pace.signedSeconds});return Math.max(0,index)}
function cards(records,agents,now){return providers.map(function(provider){var record=(records||[]).find(function(r){return r&&r.provider===provider.id})||{},windows=Array.isArray(record.windows)?record.windows.slice(0,8):record.metric?[record.metric]:[],metric=normalizeMetric(record.metric||windows[0],now);return {id:provider.id,name:provider.name,color:provider.color,count:filterAgents(agents,provider.id).length,activity:activity(agents,provider.id,now),metric:metric,ordinaryUsageAllowed:metric.state==='measured'&&typeof record.ordinaryUsageAllowed==='boolean'?record.ordinaryUsageAllowed:null,windows:windows,primaryIndex:primaryIndex(record,windows),label:record.metric&&record.metric.label||'Quota window',overflowCount:finite(record.overflowCount)&&record.overflowCount>0?record.overflowCount:0}})}
function splitRows(rows){var result=[];rows.forEach(function(row){var chars=Array.from(String(row.value)),parts=[];while(chars.length)parts.push(chars.splice(0,68).join(''));if(!parts.length)parts=[''];parts.forEach(function(part,index){result.push({label:row.label+(parts.length>1?' ('+(index+1)+'/'+parts.length+')':''),value:part})})});return result}
function detailRows(card,window,now){var metric=normalizeMetric(window||null,now),rows=[{label:'Quota window',value:window&&window.label||'Unavailable'},{label:'Reported workflow states',value:card.activity||'Workflow state unavailable'},{label:'Workflow evidence',value:'Fresh live session-adapter reports only. Saved sessions are not assumed active.'},{label:'Allowance used / remaining',value:metric.used+' / '+metric.remaining},{label:'Rate-limit reset',value:metric.reset},{label:'Provider ordinary usage',value:card.ordinaryUsageAllowed===true?'Provider explicitly reports allowed':card.ordinaryUsageAllowed===false?'Provider explicitly reports restricted':'Permission unknown; not inferred from usage or reset'},{label:'Quota observation',value:metric.observed},{label:'Metric source',value:metric.source},{label:'Pacing meaning',value:metric.reason},{label:'Pacing wait assumption',value:'No additional usage since the quota observation. Pacing recovery is separate from quota reset or provider unblocking.'}];if(card.overflowCount)rows.push({label:'Additional windows',value:card.overflowCount+' outside the bounded display'});return splitRows(rows)}
