import { getMonoliths } from './registry.js';
function fit(canvas){const w=Math.max(1,Math.floor(canvas.clientWidth*devicePixelRatio)),h=Math.max(1,Math.floor(canvas.clientHeight*devicePixelRatio));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}return [w,h];}
function cat(ctx,x,y,s,flap,color,done){ctx.save();ctx.translate(x,y);ctx.scale(s,s);ctx.fillStyle=color;ctx.strokeStyle=color;ctx.lineWidth=2;
  // Cat shape: arched tail, body, ears, eyes. Verified tasks carry a glowing star.
  ctx.beginPath();ctx.moveTo(-27,1);ctx.bezierCurveTo(-55,-33,-65,7,-38,15);ctx.stroke();
  ctx.beginPath();ctx.ellipse(-3,10,29,16,-.1,0,Math.PI*2);ctx.fill();
  ctx.beginPath();ctx.moveTo(10,4);ctx.lineTo(11,-24);ctx.lineTo(22,-13);ctx.lineTo(34,-24);ctx.lineTo(37,4);ctx.closePath();ctx.fill();
  ctx.fillStyle='#061523';ctx.fillRect(17,-1,3,3);ctx.fillRect(29,-1,3,3);
  ctx.strokeStyle=color;ctx.beginPath();ctx.moveTo(-8,7);ctx.quadraticCurveTo(8,flap*12+27,18,12);ctx.stroke();
  if(done){ctx.fillStyle='#ffe0a1';ctx.font='17px monospace';ctx.fillText('✦',-8,-30);}
  ctx.restore();}
function toaster(ctx,x,y,s,flap,color,done){
  ctx.save();ctx.translate(x,y);ctx.scale(s,s);
  ctx.fillStyle='#b8c5d2';ctx.strokeStyle=color;ctx.lineWidth=3;
  ctx.beginPath();ctx.roundRect(-26,-6,49,34,7);ctx.fill();ctx.stroke();
  ctx.fillStyle='#263a4f';ctx.fillRect(-17,-9,30,6);ctx.fillStyle='#ece4bb';ctx.fillRect(-15,-21,27,14);
  ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(-23,7);ctx.quadraticCurveTo(-64,flap*20-15,-47,32);ctx.lineTo(-19,18);ctx.closePath();ctx.fill();
  ctx.beginPath();ctx.moveTo(20,4);ctx.quadraticCurveTo(62,flap*20-13,48,28);ctx.lineTo(18,18);ctx.closePath();ctx.fill();
  ctx.fillStyle='#173349';ctx.beginPath();ctx.arc(14,18,3,0,Math.PI*2);ctx.fill();
  if(done){ctx.fillStyle='#ffdf92';ctx.font='18px monospace';ctx.fillText('✦',-10,-34);}
  ctx.restore();
}
export class FlyingScene{
  constructor(canvas,theme,onSelect){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.theme=theme;this.speed=.5;this.items=[];this.onSelect=onSelect;this.toasters=false;}
  setData(data){this.items=getMonoliths(data);this.done=(data.counts?.done||0);this.leased=(data.counts?.leased||0);}
  draw(seconds){const [w,h]=fit(this.canvas),ctx=this.ctx;ctx.fillStyle=this.theme.low;ctx.fillRect(0,0,w,h);
    const tick=seconds*(.035+this.speed*.07);ctx.strokeStyle=this.theme.accent+'30';
    for(let y=0;y<h;y+=h/16){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
    for(let i=0;i<85;i++){const x=((i*167.23)%w),y=((i*97.31)%h);ctx.fillStyle=this.theme.bright+'55';ctx.fillRect(x,y,2,2);}
    const n=Math.max(5,Math.min(32,this.items.length));for(let i=0;i<n;i++){
      const item=this.items[i]||{done:0,leased:0};const s=.62+(i%3)*.16;const x=(w+(i*135-tick*(90+i%5*26))%(w+230))%(w+230)-110;
      const y=(i*102.37)%(h*.75)+h*.11+Math.sin(tick*2+i)*14;
      ctx.globalAlpha=item.leased?1:.3+.5*Math.min(1,(item.done||0)/12);
      (this.toasters?toaster:cat)(ctx,x,y,s*(Math.min(w,h)/400),Math.sin(tick*7+i),this.theme.accent,item.done>0&&i%4===0);
      ctx.globalAlpha=1;
    }
    ctx.fillStyle=this.theme.bright;ctx.font=`${Math.max(12,Math.floor(w/84))}px monospace`;
    ctx.fillText(`${this.items.length} CATBOX SIGNALS    ${this.done} VERIFIED RESULTS`,25,h-27);
  }
  destroy(){}
}

export class ToasterScene extends FlyingScene {constructor(canvas,theme,onSelect){super(canvas,theme,onSelect);this.toasters=true;}}
