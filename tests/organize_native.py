"""Move only three purpose-created invisible Qt fixtures; preserve every real client/focus."""
import json,os,shlex,subprocess,tempfile,time
from pathlib import Path
from native_session import ROOT
import sys
sys.path.insert(0,str(ROOT))
import organize

def read(kind):return json.loads(subprocess.check_output(['hyprctl',kind,'-j'],text=True))
def run(*args):return subprocess.check_output(args,text=True,stderr=subprocess.PIPE,timeout=10).strip()
def identities(clients):return {c['address']:(c.get('pid'),c.get('class'),c.get('workspace',{}).get('id'),c.get('monitor')) for c in clients}
before=identities(read('clients'));focus=read('activewindow').get('address');workspace=read('activeworkspace').get('id');used={w['id'] for w in read('workspaces')};ids=[i for i in range(90001,99999)if i not in used][:2]
assert len(ids)==2
rules=[];process=None
with tempfile.TemporaryDirectory(prefix='districts-organize-native-',dir='/tmp')as tmp:
 folder=Path(tmp);code=folder/'fixture.cpp';binary=folder/'fixture'
 code.write_text('''#include <QApplication>
#include <QLabel>
#include <QTimer>
int main(int argc,char**argv){QApplication app(argc,argv);QGuiApplication::setDesktopFileName("Code");QLabel a("Synthetic organizer fixture A"),b("Synthetic organizer fixture B"),c("Synthetic organizer fixture C");a.setWindowTitle("Districts Organize Fixture A");b.setWindowTitle("Districts Organize Fixture B");c.setWindowTitle("Districts Organize Fixture C");for(auto*w:{&a,&b,&c}){w->resize(320,180);w->show();}QTimer::singleShot(30000,&app,&QCoreApplication::quit);return app.exec();}''')
 flags=shlex.split(run('pkg-config','--cflags','--libs','Qt6Widgets'));subprocess.run(['g++',str(code),'-o',str(binary),*flags],check=True)
 try:
  for title,target in [('A',ids[0]),('B',ids[0]),('C',ids[1])]:
   rule='districts_organize_'+str(os.getpid())+'_'+title;rules.append(rule)
   run('hyprctl','eval',rule+'=hl.window_rule({name="'+rule+'",match={class="^Code$",title="^Districts Organize Fixture '+title+'$"},no_focus=true,float=true,workspace="'+str(target)+' silent"})')
  env={**os.environ,'QT_QPA_PLATFORM':'wayland','XDG_STATE_HOME':str(folder/'state')};process=subprocess.Popen([str(binary)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(80):
   own=[c for c in read('clients')if c.get('pid')==process.pid]
   if len(own)==3:break
   time.sleep(.05)
  assert len(own)==3 and all(c['class']=='Code' for c in own),own
  assert sorted(c['workspace']['id']for c in own)==[ids[0],ids[0],ids[1]]
  assert read('activewindow').get('address')==focus
  snapshot={'schema':1,'districts':[{'id':wid,'monitor':next(c['monitor']for c in own if c['workspace']['id']==wid),'count':sum(c['workspace']['id']==wid for c in own)}for wid in ids],'windows':[{'address':c['address'],'class':c['class'],'app':'Code','pid':c['pid'],'workspace':c['workspace']['id'],'monitor':c['monitor']}for c in own]}
  preview=organize.preview(snapshot);plan=preview['plan'];assert len(plan['moves'])==1 and plan['moves'][0]['pid']==process.pid
  old_state=os.environ.get('XDG_STATE_HOME');os.environ['XDG_STATE_HOME']=str(folder/'state')
  try:result=organize.apply(plan,plan['planId'])
  finally:
   if old_state is None:os.environ.pop('XDG_STATE_HOME',None)
   else:os.environ['XDG_STATE_HOME']=old_state
  assert result['ok']and result['applied']==1,result
  after=identities(read('clients'));changed={a:{'before':v,'after':after.get(a)}for a,v in before.items()if after.get(a)!=v}
  if changed:(ROOT/'verification/organize-native-conflict.json').write_text(json.dumps({'changed':changed,'fixturePid':process.pid,'result':result},indent=2))
  assert not changed,'Unrelated client changed; private diagnostic retained'
  assert read('activewindow').get('address')==focus and read('activeworkspace').get('id')==workspace
  (ROOT/'verification/organize-native.json').write_text(json.dumps({'fixtureOnly':True,'fixtureWindows':3,'confirmedOwnMoves':1,'unrelatedClientIdentitiesUnchanged':True,'focusUnchanged':True,'workspaceUnchanged':True,'realLuaScopedDispatch':True},indent=2))
  print('PASS actual scoped organizer move of one own invisible Qt fixture; every unrelated window, focus and active workspace unchanged.')
 finally:
  if process:
   process.terminate();process.wait(timeout=5)
  for rule in rules:run('hyprctl','eval',rule+':set_enabled(false);'+rule+'=nil')
assert identities(read('clients'))==before,'Fixture cleanup left clients or changed originals'
assert read('activewindow').get('address')==focus and read('activeworkspace').get('id')==workspace
