const fs=require('fs'),vm=require('vm'),assert=require('assert');
const c={};vm.createContext(c);vm.runInContext(fs.readFileSync(__dirname+'/../CameraV2.js','utf8').replace(/^\.pragma library\s*/,''),c);
for (const [w,h]of [[1366,768],[1600,900],[1920,1080],[2560,1440],[3840,2160],[3440,1440],[5120,1440]]){
 const m=c.metrics(w,h),mw=w-m.sidebar-3*m.margin,mh=h-m.header-m.footer;assert(mw>=800&&mh>=598);assert(m.control>=38);
 const a={x:125,y:-60,zoom:.8},px=mw*.35,py=mh*.7,b=c.anchored(a,1.8,px,py,mw,mh);
 assert(Math.abs((px-mw/2-a.x)/a.zoom-(px-mw/2-b.x)/b.zoom)<1e-8);assert(Math.abs((py-mh/2-a.y)/a.zoom-(py-mh/2-b.y)/b.zoom)<1e-8);
 const fit=c.fit({minX:-800,maxX:1200,minY:-700,maxY:600},mw,mh,0);assert(fit.zoom>=.08&&fit.zoom<=2.2);assert(Number.isFinite(fit.x)&&Number.isFinite(fit.y));
 for(const t of [-1,0,.5,1,2]){const p=c.interpolate(a,b,t);assert(p.zoom>=a.zoom&&p.zoom<=b.zoom);}
 const v=c.view(b,mw,mh);assert(v.minX<v.maxX&&v.minY<v.maxY);assert(c.visible({x:(v.minX+v.maxX)/2,y:(v.minY+v.maxY)/2},10,v));assert(!c.visible({x:v.maxX+100,y:v.maxY+100},10,v));
 const z=c.anchored(a,100,px,py,mw,mh);assert(z.zoom<=6);assert(c.anchored(a,.0001,px,py,mw,mh).zoom===.08);
}
console.log('PASS: seven viewport compositions, pointer anchor invariance, camera bounds/interpolation, culling.');
