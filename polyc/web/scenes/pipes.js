import { getMonoliths } from './registry.js';
const fit=c=>{const w=Math.max(1,Math.floor(c.clientWidth*devicePixelRatio)),h=Math.max(1,Math.floor(c.clientHeight*devicePixelRatio));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}return [w,h];};
export class PipesScene{
  constructor(canvas,theme){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.theme=theme;this.items=[];this.speed=.5;}
  setData(data){this.items=getMonoliths(data);this.done=data.counts?.done||0;this.leased=data.counts?.leased||0;}
  draw(seconds){const [w,h]=fit(this.canvas),ctx=this.ctx;ctx.fillStyle=this.theme.low;ctx.fillRect(0,0,w,h);
    let n=Math.max(4,Math.min(34,this.items.length));const t=seconds*(.3+this.speed*.9);const step=Math.max(28,Math.min(w,h)/11);
    for(let i=0;i<n;i++){let item=this.items[i]||{};const shift=(i*27)%10;let x=(i*73.17+step)%w,y=(i*51.91+step)%h;
      ctx.lineJoin='round';ctx.lineCap='round';const col=item.leased?this.theme.bright:this.theme.accent;
      const path=new Path2D();path.moveTo(x,y);for(let j=0;j<8;j++){
        const dir=(Math.floor(i*3+j*7+Math.floor(t/5))%4);const d=step*(1+.3*Math.sin(i+j));if(dir===0)x+=d;else if(dir===1)y+=d;else if(dir===2)x-=d;else y-=d;
        x=(x+w*2)%w;y=(y+h*2)%h;path.lineTo(x,y);
      }
      ctx.strokeStyle='#020a11';ctx.lineWidth=14;ctx.stroke(path);ctx.strokeStyle=col;ctx.lineWidth=7;ctx.globalAlpha=.24+.7*Math.min(1,((item.done||0)+(item.leased||0)*3)/15);ctx.stroke(path);
      ctx.strokeStyle=this.theme.bright;ctx.lineWidth=1.4;ctx.globalAlpha=.8;ctx.stroke(path);ctx.globalAlpha=1;
      if(item.leased){ctx.beginPath();ctx.arc(x,y,9+4*Math.sin(t*4+i),0,Math.PI*2);ctx.strokeStyle=this.theme.bright;ctx.lineWidth=2;ctx.stroke();}
    }
    ctx.fillStyle=this.theme.bright;ctx.font='13px monospace';ctx.fillText(`${this.leased} ACTIVE LEASES // ${this.done} VERIFIED PIPE SEGMENTS`,20,h-23);
  }
  destroy(){}
}
