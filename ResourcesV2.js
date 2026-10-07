.pragma library
function bytes(value){return typeof value==='number'&&isFinite(value)&&value>=0?(value/1048576).toFixed(1)+' MiB':'Unavailable'}
function number(value){return typeof value==='number'&&isFinite(value)&&value>=0?String(value):'Unavailable'}
function stamp(value){return typeof value==='number'&&isFinite(value)&&value>0?new Date(value).toLocaleString():'Timestamp unavailable'}
function workflow(agent){
 if(!agent||!agent.status||typeof agent.status.type!=='string'||!agent.status.type||agent.status.type.length>80||typeof agent.statusSource!=='string'||!agent.statusSource||agent.statusSource.length>256)return null
 var time=typeof agent.observedAt==='string'?Date.parse(agent.observedAt):agent.observedAt
 if(typeof time!=='number'||!isFinite(time)||time<=0||['live','stored'].indexOf(agent.availability)<0)return null
 return {state:agent.status.type,source:agent.statusSource,observedAt:time,availability:agent.availability}
}
function paginateValues(rows){
 var result=[];rows.forEach(function(row){var chars=Array.from(String(row.value)),parts=[];while(chars.length)parts.push(chars.splice(0,72).join(''));if(!parts.length)parts=[''];parts.forEach(function(value,i){result.push({label:row.label+(parts.length>1?' ('+(i+1)+'/'+parts.length+')':''),value:value})})});return result
}
function rows(details,reported,cpu) {
 var d=details&&details.ok?details:null,c=cpu||{},r=[]
 if(d){r.push({label:'Resident memory',value:bytes(d.residentBytes)});r.push({label:'Virtual address space',value:bytes(d.virtualBytes)});r.push({label:'Threads',value:number(d.threads)});r.push({label:'Open file descriptors',value:number(d.fileDescriptors)+(d.fileDescriptorsCapped?' or more (bounded count)':'')});r.push({label:'Owner identity',value:'PID '+d.pid+' / start tick '+d.startTime});r.push({label:'Observed',value:stamp(d.observedAt)+' / Linux /proc'})}
 r.push({label:'Owner CPU',value:c.state==='measured'&&typeof c.percent==='number'&&isFinite(c.percent)?c.percent.toFixed(1)+'% per core':c.state==='sampling'?'Sampling':'Unavailable'})
 r.push({label:'Resource scope',value:'Selected window owner only. Shared process totals; child processes excluded.'})
 r.push({label:'Meaning',value:'CPU and memory do not report agent progress, terminal commands or browser work.'})
 var state=workflow(reported)
 if(state){
  r.push({label:'Reported workflow state',value:state.state+' / '+state.availability});r.push({label:'Reported state source',value:state.source});r.push({label:'State observed',value:stamp(state.observedAt)});r.push({label:'Workflow scope',value:'Adapter-reported state, separate from resource usage. No percent progress inferred.'})
 }else r.push({label:'Reported workflow state',value:'Unavailable: no verified adapter report.'})
 return paginateValues(r)
}
