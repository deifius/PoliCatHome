import { getMonoliths } from './registry.js';
const VERT=`#version 300 es
precision highp float;
in vec3 aPos; in vec3 aNormal;
in vec3 iOffset; in vec4 iStats;
uniform mat4 uViewProj; uniform float uTime;
out vec3 vLocal; out vec3 vNormal; out vec4 vStats; out float vHeight;
void main(){
  float h=iStats.x;
  vLocal=aPos; vNormal=aNormal;vStats=iStats;vHeight=h;
  vec3 world=vec3(aPos.x*2.18+iOffset.x, aPos.y*h+0.04,aPos.z*2.18+iOffset.z);
  gl_Position=uViewProj*vec4(world,1.0);
}`;
const FRAG=`#version 300 es
precision highp float;
in vec3 vLocal; in vec3 vNormal; in vec4 vStats; in float vHeight;
uniform float uTime; uniform vec3 uAccent; uniform vec3 uLow; uniform vec3 uBright;
out vec4 fragColor;
void main(){
  float side=abs(vNormal.y)<.5?1.:0.;
  float stripeCoord=abs(vNormal.x)>.5?vLocal.z:vLocal.x;
  float windowX=step(.27,fract((stripeCoord+.5)*5.));
  float windowY=step(.22,fract(vLocal.y*vHeight*2.75));
  float pulse=.58+.42*sin(uTime*1.8+vStats.w*13.);
  float windows=side*windowX*windowY;
  float work=clamp(vStats.y,0.,1.);
  float verified=clamp(vStats.z,0.,1.);
  float vertical=.4+.6*fract(vLocal.y*vHeight*.32+uTime*(.09+work*.21)+vStats.w);
  vec3 base=mix(uLow,uAccent,.08+max(0.,vNormal.z)*.13);
  base+=uAccent*(windows*(.23+.45*work*pulse+.25*verified)*vertical);
  float seam=step(.983,fract(vLocal.y*vHeight*.35));
  base+=uAccent*seam*(.07+.16*work);
  float edge=step(.47,abs(stripeCoord));
  base+=uAccent*edge*(.15+.2*work);
  if(vNormal.y>.5) base=mix(uAccent,uBright,.38+.2*pulse)*(.3+.55*work+.16*verified);
  fragColor=vec4(base,1.0);
}`;
const LINEVERT=`#version 300 es
precision highp float;in vec3 aPos;uniform mat4 uViewProj;void main(){gl_Position=uViewProj*vec4(aPos,1.);}`;
const LINEFRAG=`#version 300 es
precision highp float;uniform vec3 uColor;out vec4 fragColor;void main(){fragColor=vec4(uColor,0.67);}`;
const cubePositions=[],cubeNormals=[],cubeIndices=[];
function face(corners, normal){let start=cubePositions.length/3;for(const v of corners){cubePositions.push(...v);cubeNormals.push(...normal);}cubeIndices.push(start,start+1,start+2,start,start+2,start+3);}
face([[-.5,0,.5],[.5,0,.5],[.5,1,.5],[-.5,1,.5]],[0,0,1]);
face([[.5,0,-.5],[-.5,0,-.5],[-.5,1,-.5],[.5,1,-.5]],[0,0,-1]);
face([[-.5,0,-.5],[-.5,0,.5],[-.5,1,.5],[-.5,1,-.5]],[-1,0,0]);
face([[.5,0,.5],[.5,0,-.5],[.5,1,-.5],[.5,1,.5]],[1,0,0]);
face([[-.5,1,.5],[.5,1,.5],[.5,1,-.5],[-.5,1,-.5]],[0,1,0]);
face([[-.5,0,-.5],[.5,0,-.5],[.5,0,.5],[-.5,0,.5]],[0,-1,0]);
function makeShader(gl,type,source){const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));return shader;}
function program(gl,vs,fs){const p=gl.createProgram();gl.attachShader(p,makeShader(gl,gl.VERTEX_SHADER,vs));gl.attachShader(p,makeShader(gl,gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));return p;}
function perspective(fov,aspect,near,far){const f=1/Math.tan(fov/2),nf=1/(near-far);return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)*nf,-1,0,0,2*far*near*nf,0]);}
function lookAt(eye,at){let z=normalize(sub(eye,at)),x=normalize(cross([0,1,0],z)),y=cross(z,x);
return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
function matmul(a,b){const c=new Float32Array(16);for(let col=0;col<4;col++)for(let row=0;row<4;row++)for(let k=0;k<4;k++)c[col*4+row]+=a[k*4+row]*b[col*4+k];return c;}
const sub=(a,b)=>a.map((v,i)=>v-b[i]);const dot=(a,b)=>a.reduce((n,v,i)=>n+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const normalize=a=>{let l=Math.hypot(...a)||1;return a.map(v=>v/l);};
function rgb(hex){return [1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255);}
function makeBuffer(gl,values,size,location,divisor=0){const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(values),gl.STATIC_DRAW);gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,size,gl.FLOAT,false,0,0);gl.vertexAttribDivisor(location,divisor);return buf;}
const hash=s=>{let h=2166136261;for(let i=0;i<s.length;i++)h=Math.imul(h^s.charCodeAt(i),16777619);return h>>>0;};
export class GibsonScene{
  constructor(canvas,theme,onSelect){this.canvas=canvas;this.theme=theme;this.onSelect=onSelect;this.speed=.5;this.selected=-1;this.items=[];this.built=[];this.gl=canvas.getContext('webgl2',{antialias:true,alpha:false,powerPreference:'low-power'});if(!this.gl)throw Error('WebGL 2 unavailable; choose another Catnap scene');this.setup();
    this.click=e=>{const rect=canvas.getBoundingClientRect();let x=(e.clientX-rect.left)/rect.width*2-1,y=1-(e.clientY-rect.top)/rect.height*2;let best=-1,d=.20;for(let i=0;i<this.built.length;i++){const item=this.built[i];const p=this.project([item.x,item.height*.55,item.z]);if(!p||p[2]<-1||p[2]>1)continue;let radius=Math.hypot(p[0]-x,p[1]-y);if(radius<d){best=i;d=radius;}}if(best>=0){this.selected=best;this.onSelect(this.items[best]);}};
    canvas.addEventListener('click',this.click);
  }
  setup(){const gl=this.gl;this.p=program(gl,VERT,FRAG);this.lp=program(gl,LINEVERT,LINEFRAG);this.vao=gl.createVertexArray();gl.bindVertexArray(this.vao);
    this.pos=makeBuffer(gl,cubePositions,3,gl.getAttribLocation(this.p,'aPos'));
    this.norm=makeBuffer(gl,cubeNormals,3,gl.getAttribLocation(this.p,'aNormal'));
    this.offset=makeBuffer(gl,[0,0,0],3,gl.getAttribLocation(this.p,'iOffset'),1);
    this.stats=makeBuffer(gl,[1,0,0,0],4,gl.getAttribLocation(this.p,'iStats'),1);
    const indices=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indices);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(cubeIndices),gl.STATIC_DRAW);gl.bindVertexArray(null);
    this.lineVao=gl.createVertexArray();gl.bindVertexArray(this.lineVao);this.lineBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.lineBuffer);gl.enableVertexAttribArray(gl.getAttribLocation(this.lp,'aPos'));gl.vertexAttribPointer(gl.getAttribLocation(this.lp,'aPos'),3,gl.FLOAT,false,0,0);gl.bindVertexArray(null);
    const points=[];for(let k=-18;k<=18;k+=2){points.push(-38,0,k*2,38,0,k*2,k*2,0,-38,k*2,0,38);}this.gridPoints=new Float32Array(points);
    gl.enable(gl.DEPTH_TEST);
  }
  setData(snapshot){this.items=getMonoliths(snapshot);if(!this.items.length){this.items=[{id:'awaiting-cats',project:'Awaiting Catnap',done:0,leased:0}];}
    const list=[],stats=[];let k=0;for(const item of this.items){const angle=k*2.399963229728653;const radius=2.8*Math.sqrt(k);const x=Math.sin(angle)*radius,z=Math.cos(angle)*radius;
      const height=3.5+Math.log2(1+item.done)*1.8+(item.leased?1.9:0);item.x=x;item.z=z;item.height=height;
      list.push(x,0,z);stats.push(height,item.leased>0?1:0,Math.min(1,item.done/15),(hash(item.id)%1000)/1000);k++;}
    this.built=this.items;
    const gl=this.gl;gl.bindBuffer(gl.ARRAY_BUFFER,this.offset);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(list),gl.DYNAMIC_DRAW);gl.bindBuffer(gl.ARRAY_BUFFER,this.stats);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(stats),gl.DYNAMIC_DRAW);
  }
  project(pos){if(!this.vp)return null;const m=this.vp;let w=m[3]*pos[0]+m[7]*pos[1]+m[11]*pos[2]+m[15];if(w<=0)return null;return [(m[0]*pos[0]+m[4]*pos[1]+m[8]*pos[2]+m[12])/w,(m[1]*pos[0]+m[5]*pos[1]+m[9]*pos[2]+m[13])/w,(m[2]*pos[0]+m[6]*pos[1]+m[10]*pos[2]+m[14])/w];}
  draw(seconds){const gl=this.gl,c=this.canvas;let w=Math.max(1,Math.floor(c.clientWidth*devicePixelRatio)),h=Math.max(1,Math.floor(c.clientHeight*devicePixelRatio));const maxSide=1600;if(w>maxSide||h>maxSide){const f=maxSide/Math.max(w,h);w=Math.floor(w*f);h=Math.floor(h*f);}if(c.width!==w||c.height!==h){c.width=w;c.height=h;}gl.viewport(0,0,w,h);
    const s=seconds*(.025+this.speed*.12);const r=Math.max(28,12+Math.sqrt(this.items.length)*6), eye=[Math.sin(s)*r,16+Math.sin(s*.7)*5,Math.cos(s)*r];this.vp=matmul(perspective(Math.PI/3,w/h,.1,230),lookAt(eye,[0,4.6,0]));
    const low=rgb(this.theme.low);gl.clearColor(low[0]*.2,low[1]*.35,low[2]*.48,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    gl.useProgram(this.lp);gl.bindVertexArray(this.lineVao);gl.uniformMatrix4fv(gl.getUniformLocation(this.lp,'uViewProj'),false,this.vp);
    gl.uniform3fv(gl.getUniformLocation(this.lp,'uColor'),rgb(this.theme.accent).map(v=>v*.15));
    gl.bindBuffer(gl.ARRAY_BUFFER,this.lineBuffer);gl.bufferData(gl.ARRAY_BUFFER,this.gridPoints,gl.DYNAMIC_DRAW);gl.drawArrays(gl.LINES,0,this.gridPoints.length/3);
    // Real task relationships: link monoliths belonging to the same project.
    const lines=[];const byProject=new Map();for(const item of this.built){let p=byProject.get(item.project);if(p)lines.push(p.x,1,p.z,item.x,1,item.z);else byProject.set(item.project,item);}
    gl.bindBuffer(gl.ARRAY_BUFFER,this.lineBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(lines),gl.DYNAMIC_DRAW);
    gl.uniform3fv(gl.getUniformLocation(this.lp,'uColor'),rgb(this.theme.accent).map(v=>v*.48));gl.drawArrays(gl.LINES,0,lines.length/3);
    gl.useProgram(this.p);gl.bindVertexArray(this.vao);gl.uniformMatrix4fv(gl.getUniformLocation(this.p,'uViewProj'),false,this.vp);gl.uniform1f(gl.getUniformLocation(this.p,'uTime'),seconds);
    gl.uniform3fv(gl.getUniformLocation(this.p,'uAccent'),rgb(this.theme.accent));gl.uniform3fv(gl.getUniformLocation(this.p,'uLow'),rgb(this.theme.low));gl.uniform3fv(gl.getUniformLocation(this.p,'uBright'),rgb(this.theme.bright));
    gl.drawElementsInstanced(gl.TRIANGLES,cubeIndices.length,gl.UNSIGNED_SHORT,0,this.items.length);gl.bindVertexArray(null);
  }
  destroy(){this.canvas.removeEventListener('click',this.click);const gl=this.gl;if(gl){for(const p of [this.p,this.lp])gl.deleteProgram(p);for(const b of [this.pos,this.norm,this.offset,this.stats,this.lineBuffer])gl.deleteBuffer(b);gl.deleteVertexArray(this.vao);gl.deleteVertexArray(this.lineVao);}}
}
