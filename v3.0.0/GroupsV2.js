.pragma library
// Public app roles and explicit compositor workspace names only; no titles or URLs.
var groups=[
 {key:'development',name:'Development',color:'#4caf50'},
 {key:'entertainment',name:'Entertainment',color:'#e53935'},
 {key:'communication',name:'Communication',color:'#2196f3'},
 {key:'research',name:'Research & Office',color:'#ff9800'},
 {key:'system',name:'System & Tools',color:'#9c27b0'},
 {key:'mixed',name:'Mixed / Unclassified',color:'#9e9e9e'}
]
function info(key){return groups.find(function(g){return g.key===key})||groups[5]}
function preferences(value){value=value||{};return {revision:Number(value.revision)||0,colors:value.colors||{},rules:value.rules||{}}}
function color(key,prefs){return prefs&&prefs.colors&&prefs.colors[key]||info(key).color}
function identity(w){return String(w.class||'Application').toLowerCase()}
function appRole(w,prefs){
 var key=identity(w),rules=prefs&&prefs.rules||{}
 if(rules[key]&&groups.some(function(g){return g.key===rules[key]}))return {key:rules[key],reason:'Your app rule'}
 var known={development:['code','code-oss','vscodium','codium','zed','dev.zed.zed','sublime_text','sublime-text','jetbrains-idea','jetbrains-pycharm','jetbrains-webstorm','jetbrains-clion','jetbrains-rustrover','dbeaver','postman','gitkraken'],entertainment:['spotify','com.spotify.client','vlc','org.videolan.vlc','mpv','steam','lutris','com.valvesoftware.steam'],communication:['slack','com.slack.slack','discord','com.discordapp.discord','signal','org.signal.signal','telegramdesktop','org.telegram.desktop','teams','zoom','thunderbird','org.mozilla.thunderbird'],research:['obsidian','md.obsidian.obsidian','zotero','org.zotero.zotero','libreoffice','libreoffice-writer','libreoffice-calc','libreoffice-impress','org.gnome.evince','okular','org.kde.okular','calibre'],system:['kitty','foot','alacritty','wezterm','org.wezfurlong.wezterm','org.gnome.terminal','konsole','org.kde.konsole','org.gnome.nautilus','dolphin','org.kde.dolphin','thunar','pavucontrol','org.gnome.settings','gparted']}
 for(var group in known)if(known[group].indexOf(key)>=0)return {key:group,reason:'Known public app identity'}
 // A generic browser's public Network category says nothing about its contents.
 var cats=w.desktopCategories||[]
 if(cats.indexOf('WebBrowser')>=0||/^(brave(?:-browser)?|firefox|org\.mozilla\.firefox|chromium|google-chrome|chrome|microsoft-edge|vivaldi|librewolf|zen|zen-browser)$/.test(key))return {key:'mixed',reason:'Browser contents are not inspected'}
 var roles={Development:'development',Game:'entertainment',AudioVideo:'entertainment',Audio:'entertainment',Video:'entertainment',Chat:'communication',InstantMessaging:'communication',Email:'communication',Office:'research',Education:'research',Science:'research',Graphics:'research',System:'system',Utility:'system'}
 var found=[];cats.forEach(function(c){if(roles[c]&&found.indexOf(roles[c])<0)found.push(roles[c])})
 if(found.length===1)return {key:found[0],reason:'Public desktop-entry category'}
 return {key:'mixed',reason:found.length?'Ambiguous public app categories':'No recognized public app role'}
}
function classify(d,windows,prefs){
 var distinct=Object.create(null),votes={},strong={},evidence=[]
 windows.forEach(function(w){if(w.workspace!==d.id||distinct[identity(w)])return;distinct[identity(w)]=true;var role=appRole(w,prefs);votes[role.key]=(votes[role.key]||0)+1;if((role.key!=='mixed'&&role.key!=='system')||role.reason==='Your app rule'){strong[role.key]=(strong[role.key]||0)+1;evidence.push(String(w.app||w.class).slice(0,64))}})
 var active=groups.map(function(g){return g.key}).filter(function(k){return strong[k]>0}),total=active.reduce(function(n,k){return n+strong[k]},0)
 if(active.length){active.sort(function(a,b){return strong[b]-strong[a]});var best=active[0];if(strong[best]>total/2)return {key:best,reason:'Public app roles: '+evidence.sort().slice(0,3).join(' + ')};return {key:'mixed',reason:'Several activity groups; no majority'} }
 // Only use an explicit compositor label if app roles provide no activity signal.
 if(d.autoSource==='workspace'||d.autoSource==='workspace-names'){
  var text=String(d.autoName||'').toLowerCase(),matches=[]
  var names={development:/\b(dev|development|coding)\b/,entertainment:/\b(entertainment|games|gaming|media)\b/,communication:/\b(communication|chat|calls)\b/,research:/\b(research|office|study)\b/,system:/\b(system|tools)\b/}
  for(var k in names)if(names[k].test(text))matches.push(k)
  if(matches.length===1)return {key:matches[0],reason:'Explicit workspace name: '+String(d.autoName).slice(0,48)}
 }
 if(votes.system)return {key:'system',reason:'Public system/tool apps only'}
 return {key:'mixed',reason:windows.some(function(w){return w.workspace===d.id})?'No recognized activity; browser contents stay private':'Empty workspace; no activity evidence'}
}
function enrich(snapshot,history,now,prefs){
 var present={},next=Object.assign({},snapshot)
 next.districts=(snapshot.districts||[]).map(function(d){
  present[d.id]=true;var candidate=classify(d,snapshot.windows||[],prefs),entry=history[d.id]
  var ruleChanged=entry&&entry.revision!==prefs.revision&&(snapshot.windows||[]).some(function(w){return w.workspace===d.id&&((entry.rules||{})[identity(w)]||'auto')!==(prefs.rules[identity(w)]||'auto')})
  if(!entry||ruleChanged){entry={shown:candidate.key,reason:candidate.reason,pending:candidate.key,since:now};history[d.id]=entry}
  else if(entry.pending!==candidate.key){entry.pending=candidate.key;entry.since=now}
  else if(candidate.key===entry.shown||now-entry.since>=6000){entry.shown=candidate.key;entry.reason=candidate.reason}
  entry.revision=prefs.revision;entry.rules=prefs.rules
  return Object.assign({},d,{group:entry.shown,groupName:info(entry.shown).name,groupColor:color(entry.shown,prefs),groupReason:entry.reason,groupPending:entry.shown!==candidate.key})
 })
 Object.keys(history).forEach(function(k){if(!present[k])delete history[k]})
 return next
}
function appEntries(snapshot,prefs){var found=Object.create(null);(snapshot.windows||[]).forEach(function(w){if(!found[identity(w)]){var role=appRole(w,prefs);found[identity(w)]={key:identity(w),label:w.app||w.class,subtitle:info(role.key).name+' / '+role.reason,payload:w}}});Object.keys(prefs.rules||{}).forEach(function(k){if(!found[k])found[k]={key:k,label:k,subtitle:info(prefs.rules[k]).name+' / Saved rule; app not running',payload:{class:k,app:k.slice(0,64)}}});return Object.keys(found).sort().map(function(k){return found[k]})}
