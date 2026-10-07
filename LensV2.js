.pragma library
// A view filter only. Never dispatches compositor actions or alters input objects.
function normalize(lens) {
 if(!lens || ['app','district','category','family'].indexOf(lens.kind)<0)return null
 var value=lens.value
 if(lens.kind==='district'){if(typeof value!=='number'||!isFinite(value)||Math.floor(value)!==value)return null}
 else {if(typeof value!=='string'||!value.trim()||value.length>256)return null;value=value.trim();if(lens.kind==='app')value=value.toLowerCase()}
 var result={kind:lens.kind,value:value,label:String(lens.label||value).slice(0,80)}
 if(lens.kind==='family'&&lens.provider!==undefined){if(typeof lens.provider!=='string'||!lens.provider.trim()||lens.provider.length>64)return null;result.provider=lens.provider.trim()}
 return result
}
function districts(snapshot){var map={};(snapshot.districts||[]).forEach(function(d){map[d.id]=d});return map}
function agentRecord(w){return w&&(w.agent||(w.provider&&w.id?w:null))}
function agentFamily(w){var agent=agentRecord(w);return agent&&typeof agent.familyId==='string'?agent.familyId:null}
function matchesAgent(agent,lens){lens=normalize(lens);if(!lens)return true;var record=agentRecord(agent);return lens.kind==='family'&&agentFamily(agent)===lens.value&&(!lens.provider||!!record&&record.provider===lens.provider)}
function matches(w,lens,map) {
 lens=normalize(lens);if(!lens)return true
 if(lens.kind==='app')return String(w.class||w.appClass||'').toLowerCase()===lens.value
 if(lens.kind==='district')return w.workspace===lens.value
 if(lens.kind==='category')return !!map[w.workspace]&&map[w.workspace].group===lens.value
 return matchesAgent(w,lens)
}
function apply(snapshot,lens) {
 lens=normalize(lens);if(!lens)return snapshot
 var map=districts(snapshot),result=Object.assign({},snapshot),visible={}
 result.windows=(snapshot.windows||[]).filter(function(w){return matches(w,lens,map)})
 result.windows.forEach(function(w){visible[w.workspace]=(visible[w.workspace]||0)+1})
 result.districts=(snapshot.districts||[]).filter(function(d){return visible[d.id]||lens.kind==='district'&&d.id===lens.value||lens.kind==='category'&&d.group===lens.value}).map(function(d){return Object.assign({},d,{count:visible[d.id]||0,totalCount:d.count})})
 var monitors={};result.districts.forEach(function(d){monitors[d.monitor]=true})
 result.boroughs=(snapshot.boroughs||[]).filter(function(b){return monitors[b.id]})
 if(snapshot.agents)result.agents=snapshot.agents.filter(function(a){return matchesAgent(a,lens)||result.windows.some(function(w){return w.agent&&w.agent.id===a.id&&w.agent.provider===a.provider})})
 return result
}
function counts(snapshot,lens){var shown=apply(snapshot,lens);return {shownWindows:(shown.windows||[]).length,totalWindows:(snapshot.windows||[]).length,shownDistricts:(shown.districts||[]).length,totalDistricts:(snapshot.districts||[]).length,shownAgents:(shown.agents||[]).length,totalAgents:(snapshot.agents||[]).length}}
function options(window,district) {
 var result=[],virtual=!!window&&window.kind==='agent'||!!district&&!!district.virtualWorkspace
 if(!virtual){
  if(window&&(window.class||window.appClass))result.push({kind:'app',value:String(window.class||window.appClass).toLowerCase(),label:window.app||window.class||window.appClass})
  if(district){result.push({kind:'district',value:district.id,label:district.name||'D'+district.id});if(district.group)result.push({kind:'category',value:district.group,label:district.groupName||district.group})}
 }
 var record=agentRecord(window),family=agentFamily(window)||virtual&&district&&district.familyId
 if(family){var choice={kind:'family',value:family,label:'Agent family'},provider=record&&record.provider||virtual&&district&&district.familyProvider;if(provider)choice.provider=provider;choice=normalize(choice);if(choice)result.push(choice)}
 return result
}
