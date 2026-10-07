.pragma library
function clamp(n,a,b){return Math.max(a,Math.min(b,Number(n)||0))}
function metrics(w,h){return {margin:w<1500?24:40,sidebar:w<1500?292:328,header:h<850?104:126,footer:66,control:38,compact:w<1500||h<850}}
function range(w,h){return {min:.08,max:Math.min(6,Math.max(3.6,Math.sqrt(w*h/1000000)*2.2))}}
// Orthographic orbit is instance-owned. Elevation never reaches a singular edge-on ground plane.
function angle(value,fallback){var n=Number(value);return isFinite(n)?((n%360)+360)%360:fallback}
function orbit(camera,yaw,tilt){return Object.assign({},camera||{},{yaw:angle(yaw,45),tilt:tilt===undefined||!isFinite(Number(tilt))?35.264389682754654:clamp(tilt,20,75)})}
function reset(camera){return orbit(camera,45,35.264389682754654)}
function orientation(camera){return orbit({},camera&&camera.yaw,camera&&camera.tilt)}
function anchored(camera,factor,x,y,w,h){var r=range(w,h),z=clamp(camera.zoom*factor,r.min,r.max),px=x-w/2,py=y-h/2;return Object.assign({},camera,{zoom:z,x:px-(px-camera.x)*z/camera.zoom,y:py-(py-camera.y)*z/camera.zoom})}
function interpolate(a,b,t){t=clamp(t,0,1);t=1-Math.pow(1-t,3);var result={x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t,zoom:a.zoom+(b.zoom-a.zoom)*t};if(a.yaw!==undefined||b.yaw!==undefined||a.tilt!==undefined||b.tilt!==undefined){var aa=orientation(a),bb=orientation(b),delta=((bb.yaw-aa.yaw+540)%360)-180;result.yaw=angle(aa.yaw+delta*t,45);result.tilt=aa.tilt+(bb.tilt-aa.tilt)*t}return result}
function fit(bounds,w,h,reserve,camera){var usable=Math.max(260,w-reserve-60),height=Math.max(220,h-100),r=range(w,h),z=clamp(Math.min(usable/(bounds.maxX-bounds.minX+100),height/(bounds.maxY-bounds.minY+100)),r.min,2.2);return Object.assign({},camera||{},{zoom:z,x:-(bounds.minX+bounds.maxX)/2*z-reserve/2,y:-(bounds.minY+bounds.maxY)/2*z+20})}
function view(camera,w,h){return {minX:(-w/2-camera.x)/camera.zoom,maxX:(w/2-camera.x)/camera.zoom,minY:(-h/2-camera.y)/camera.zoom,maxY:(h/2-camera.y)/camera.zoom}}
function visible(p,size,view){return p.x+size>view.minX&&p.x-size<view.maxX&&p.y+size>view.minY&&p.y-size<view.maxY}
