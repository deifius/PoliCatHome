const fit=c=>{const w=Math.max(1,Math.floor(c.clientWidth*devicePixelRatio)),h=Math.max(1,Math.floor(c.clientHeight*devicePixelRatio));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}return [w,h];};
export class TerminalScene{
  constructor(canvas,theme){this.canvas=canvas;this.ctx=canvas.getContext('2d');this.theme=theme;this.speed=.5;this.events=[];this.counts={};}
  setData(data){this.events=data.events||[];this.counts=data.counts||{};this.scope=data.scope||'';}
  draw(seconds){const [w,h]=fit(this.canvas),ctx=this.ctx;ctx.fillStyle=this.theme.low;ctx.fillRect(0,0,w,h);
    const fs=Math.max(11,Math.min(17,w/70));ctx.font=`${fs}px monospace`;let y=45;
    ctx.fillStyle=this.theme.bright;ctx.fillText('POLIC@HOME  //  CHRONICLE LIVE',23,y);y+=fs*1.9;
    ctx.fillStyle=this.theme.accent;ctx.fillText(`SCOPE: ${this.scope.toUpperCase()}   VERIFIED: ${this.counts.done||0}   LEASED: ${this.counts.leased||0}`,23,y);y+=fs*2;
    ctx.fillStyle=this.theme.bright;const max=Math.max(1,Math.floor((h-y-35)/(fs*1.6)));for(const e of this.events.slice(-max)){
      const stamp=new Date(e.at*1000).toLocaleTimeString();const line=`[${stamp}]  ${(e.kind||'event').padEnd(19,' ')}  ${e.detail||''}`;
      ctx.fillText(line.slice(0,Math.floor(w/fs*1.52)),23,y);y+=fs*1.6;
    }
    if(!this.events.length){ctx.fillText('> No verified activity yet. The Commons is listening.',23,y);}
    if(Math.sin(seconds*3)>.0){ctx.fillRect(23,Math.min(h-22,y+4),fs*.7,fs);}
  }
  destroy(){}
}
