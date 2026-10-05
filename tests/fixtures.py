"""Synthetic public app activity only; no copied live desktop data."""
def city_fixture():
    groups=[['Kitty','Code'],['Brave'],['Code'],['Kitty','Files'],[],['Files','Brave']]
    classes={'Kitty':'kitty','Code':'Code','Brave':'brave-browser','Files':'org.gnome.Nautilus'}
    icons={'Kitty':'kitty','Code':'code','Brave':'brave-browser','Files':'system-file-manager'}
    return {'schema':1,'version':'2.0.0','timestamp':0,'focused':'0xa','boroughs':[{'id':0,'name':'DP-1','focused':True},{'id':1,'name':'eDP-1','focused':False}],
     'districts':[{'id':i,'seed':i*3317,'monitor':0 if i<5 else 1,'count':len(g)}for i,g in enumerate(groups,1)],
     'windows':[{'address':hex(i*10+j),'workspace':i,'monitor':0 if i<5 else 1,'app':app,'class':classes[app],'icon':icons[app],'focused':i==1 and j==0,'height':700+j*90,'width':900,'floating':app=='Files'}for i,g in enumerate(groups,1)for j,app in enumerate(g)]}


def pagination_fixture():
  return {'schema':1,'timestamp':0,'boroughs':[{'id':0,'name':'DP-1'}],
  'districts':[{'id':i,'seed':i*3100,'monitor':0,'count':100 if i==1 else 1,'name':'W'*48 if i==2 else 'District '+str(i),'nameSource':'custom','customName':'W'*48 if i==2 else 'District '+str(i),'autoName':'Kitty','autoSource':'apps'}for i in range(1,41)],
  'windows':[{'address':hex(i),'workspace':1 if i<=100 else i-99,'monitor':0,'app':'W'*64 if i==1 else 'App '+str(i),'class':'org.fixture','icon':'application-x-executable','height':600,'width':900}for i in range(1,140)]}
