const VS=`attribute vec3 a_position;uniform mat4 u_matrix;uniform vec4 u_color;varying vec4 v_color;void main(){gl_Position=u_matrix*vec4(a_position,1.0);v_color=u_color;}`;
const FS=`precision mediump float;varying vec4 v_color;void main(){gl_FragColor=v_color;}`;
const CUBE=new Float32Array([
-1,-1,1,1,-1,1,1,1,1,-1,-1,1,1,1,1,-1,1,1,
1,-1,-1,-1,-1,-1,-1,1,-1,1,-1,-1,-1,1,-1,1,1,-1,
-1,1,1,1,1,1,1,1,-1,-1,1,1,1,1,-1,-1,1,-1,
-1,-1,-1,1,-1,-1,1,-1,1,-1,-1,-1,1,-1,1,-1,-1,1,
1,-1,1,1,-1,-1,1,1,-1,1,-1,1,1,1,-1,1,1,1,
-1,-1,-1,-1,-1,1,-1,1,1,-1,-1,-1,-1,1,1,-1,1,-1]);
function shader(gl,type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s}
function makeProgram(gl){const p=gl.createProgram();gl.attachShader(p,shader(gl,gl.VERTEX_SHADER,VS));gl.attachShader(p,shader(gl,gl.FRAGMENT_SHADER,FS));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p}
function id(){return new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1])}
function mul(a,b){const o=new Float32Array(16);for(let r=0;r<4;r++)for(let c=0;c<4;c++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o}
function trans(x,y,z){const m=id();m[12]=x;m[13]=y;m[14]=z;return m}
function scale(x,y,z){const m=id();m[0]=x;m[5]=y;m[10]=z;return m}
function persp(fov,aspect,near,far){const f=1/Math.tan(fov/2),nf=1/(near-far),m=new Float32Array(16);m[0]=f/aspect;m[5]=f;m[10]=(far+near)*nf;m[11]=-1;m[14]=2*far*near*nf;return m}
function ortho(l,r,b,t,n,f){const m=id();m[0]=2/(r-l);m[5]=2/(t-b);m[10]=-2/(f-n);m[12]=-(r+l)/(r-l);m[13]=-(t+b)/(t-b);m[14]=-(f+n)/(f-n);return m}
function norm(v){const l=Math.hypot(...v)||1;return v.map(x=>x/l)}
function cross(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}
function dot(a,b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]}
function look(eye,target,up){const z=norm(eye.map((x,i)=>x-target[i])),x=norm(cross(up,z)),y=cross(z,x),m=id();m[0]=x[0];m[1]=y[0];m[2]=z[0];m[4]=x[1];m[5]=y[1];m[6]=z[1];m[8]=x[2];m[9]=y[2];m[10]=z[2];m[12]=-dot(x,eye);m[13]=-dot(y,eye);m[14]=-dot(z,eye);return m}
function project(m,p){const[x,y,z]=p,w=m[3]*x+m[7]*y+m[11]*z+m[15]||1;return[(m[0]*x+m[4]*y+m[8]*z+m[12])/w,(m[1]*x+m[5]*y+m[9]*z+m[13])/w]}
function rgba(hex,a=1){const v=hex.replace('#','');return[parseInt(v.slice(0,2),16)/255,parseInt(v.slice(2,4),16)/255,parseInt(v.slice(4,6),16)/255,a]}

export class Infrastructure3DViewer{
constructor(canvas,{onSelect=()=>{}}={}){
this.canvas=canvas;this.gl=canvas.getContext('webgl',{antialias:true,alpha:false});this.onSelect=onSelect;
if(!this.gl){canvas.parentElement.innerHTML='<div class="notice">此浏览器不支持 WebGL。</div>';return}
const gl=this.gl;this.program=makeProgram(gl);this.pos=gl.getAttribLocation(this.program,'a_position');this.mat=gl.getUniformLocation(this.program,'u_matrix');this.col=gl.getUniformLocation(this.program,'u_color');this.buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.buf);gl.bufferData(gl.ARRAY_BUFFER,CUBE,gl.STATIC_DRAW);
this.mode='rack';this.rack=null;this.trace=null;this.yaw=-.65;this.pitch=.22;this.distance=8;this.orthographic=false;this.picks=[];this.selected=null;this.drag=false;this.last=[0,0];this.down=[0,0];
canvas.addEventListener('pointerdown',e=>{this.drag=true;this.last=this.down=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener('pointermove',e=>{if(!this.drag)return;this.yaw+=(e.clientX-this.last[0])*.008;this.pitch=Math.max(-1.2,Math.min(1.2,this.pitch+(e.clientY-this.last[1])*.008));this.last=[e.clientX,e.clientY];this.render()});
canvas.addEventListener('pointerup',e=>{this.drag=false;if(Math.hypot(e.clientX-this.down[0],e.clientY-this.down[1])<4)this.pick(e)});
canvas.addEventListener('wheel',e=>{e.preventDefault();this.distance=Math.max(3,Math.min(35,this.distance*Math.exp(e.deltaY*.001)));this.render()},{passive:false});
new ResizeObserver(()=>this.render()).observe(canvas)}
setRack(d){this.rack=d;this.mode='rack';this.distance=8;this.render()}
setTrace(d){this.trace=d;this.mode='trace';this.distance=10;this.render()}
setFront(front=true){this.yaw=front?-.18:Math.PI-.18;this.render()}
toggleProjection(){this.orthographic=!this.orthographic;this.render();return this.orthographic}
camera(){const d=this.distance;return look([d*Math.cos(this.pitch)*Math.sin(this.yaw),d*Math.sin(this.pitch),d*Math.cos(this.pitch)*Math.cos(this.yaw)],[0,0,0],[0,1,0])}
resize(){const dpr=Math.min(devicePixelRatio||1,2),w=Math.max(1,Math.floor(this.canvas.clientWidth*dpr)),h=Math.max(1,Math.floor(this.canvas.clientHeight*dpr));if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h}this.gl.viewport(0,0,w,h);return w/h}
render(){if(!this.gl)return;const gl=this.gl,aspect=this.resize();gl.clearColor(.025,.06,.10,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.useProgram(this.program);gl.bindBuffer(gl.ARRAY_BUFFER,this.buf);gl.enableVertexAttribArray(this.pos);gl.vertexAttribPointer(this.pos,3,gl.FLOAT,false,0,0);const p=this.orthographic?ortho(-4*aspect,4*aspect,-4,4,.1,100):persp(Math.PI/4,aspect,.1,100);this.vp=mul(p,this.camera());this.picks=[];this.mode==='rack'?this.renderRack():this.renderRoute()}
box(center,size,color,key=null,data=null){const model=mul(trans(...center),scale(size[0]/2,size[1]/2,size[2]/2)),mvp=mul(this.vp,model),gl=this.gl;gl.uniformMatrix4fv(this.mat,false,mvp);gl.uniform4fv(this.col,rgba(color,key===this.selected?1:.92));gl.drawArrays(gl.TRIANGLES,0,36);if(key){const pts=[];for(const x of[-1,1])for(const y of[-1,1])for(const z of[-1,1])pts.push(project(mvp,[x,y,z]));const xs=pts.map(p=>(p[0]+1)*this.canvas.clientWidth/2),ys=pts.map(p=>(1-p[1])*this.canvas.clientHeight/2);this.picks.push({key,data,minX:Math.min(...xs),maxX:Math.max(...xs),minY:Math.min(...ys),maxY:Math.max(...ys)})}}
line(points,color){if(points.length<2)return;const gl=this.gl,b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(points.flat()),gl.STREAM_DRAW);gl.vertexAttribPointer(this.pos,3,gl.FLOAT,false,0,0);gl.uniformMatrix4fv(this.mat,false,this.vp);gl.uniform4fv(this.col,rgba(color));gl.lineWidth(4);gl.drawArrays(gl.LINE_STRIP,0,points.length);gl.bindBuffer(gl.ARRAY_BUFFER,this.buf);gl.vertexAttribPointer(this.pos,3,gl.FLOAT,false,0,0);gl.deleteBuffer(b)}
renderRack(){if(!this.rack)return;const H=5.6,W=2.15,D=1.7;for(const x of[-W/2,W/2])for(const z of[-D/2,D/2])this.box([x,0,z],[.08,H,.08],'#527392');for(const y of[-H/2,H/2]){this.box([0,y,-D/2],[W,.08,.08],'#527392');this.box([0,y,D/2],[W,.08,.08],'#527392')}for(let u=1;u<=this.rack.rack.height_u;u+=3){const y=-H/2+(u/this.rack.rack.height_u)*H;this.box([0,y,D/2+.012],[W,.012,.015],'#263e56')}for(const d of this.rack.devices){const h=Math.max(.08,d.rack_units/this.rack.rack.height_u*H),y=-H/2+((d.start_u-1+d.rack_units/2)/this.rack.rack.height_u)*H,z=d.face==='rear'?-D/2+.13:D/2-.13,color=d.device_type.includes('patch')?'#58d3e4':d.device_type.includes('fiber')?'#e6b94e':'#5f8dff';this.box([0,y,z],[W-.22,h,.22],color,d.id,d)}this.box([0,-H/2-.17,0],[W+1,.08,D+1],'#15283a')}
routePoints(){const raw=[];for(const item of this.trace?.items||[])if(item.kind==='cable'&&item.selected)for(const seg of item.route||[])for(const c of seg.coordinates||[])raw.push([Number(c.x||0),Number(c.z||0),Number(c.y||0)]);if(!raw.length)return[[-2,0,0],[0,1,0],[2,0,0]];const min=[0,1,2].map(i=>Math.min(...raw.map(p=>p[i]))),max=[0,1,2].map(i=>Math.max(...raw.map(p=>p[i]))),mid=min.map((v,i)=>(v+max[i])/2),span=Math.max(...max.map((v,i)=>v-min[i]),1),s=6/span;return raw.map(p=>p.map((v,i)=>(v-mid[i])*s))}
renderRoute(){const p=this.routePoints();this.line(p,'#59d6e8');for(let i=0;i<p.length;i++)this.box(p[i],[.14,.14,.14],i===0?'#55d49b':i===p.length-1?'#f5b85f':'#5f8dff');this.box([0,-2.2,0],[8,.04,6],'#112338')}
pick(e){const r=this.canvas.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,hit=[...this.picks].reverse().find(p=>x>=p.minX&&x<=p.maxX&&y>=p.minY&&y<=p.maxY);if(hit){this.selected=hit.key;this.onSelect(hit.data);this.render()}}
}
