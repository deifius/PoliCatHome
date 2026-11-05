// Built-in, deterministic work only. No eval, imports, remote code or Catbox containers.
let cancelled=false;
self.onmessage=async ({data})=>{
  if(data.type==='cancel'){cancelled=true;return;}
  if(data.type!=='run')return;
  cancelled=false;
  const {seed,index,iterations,budget}=data;
  if(typeof seed!=='string'||!Number.isInteger(index)||!Number.isInteger(iterations)||iterations<1||iterations>10000){
    self.postMessage({type:'error',message:'Invalid or oversized browser work assignment'});return;
  }
  let bytes=new TextEncoder().encode(`${seed}:${index}`);
  try{
    const start=performance.now();
    for(let i=0;i<iterations;i++){
      if(cancelled)return;
      bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));
      if((i+1)%64===0||i+1===iterations){
        self.postMessage({type:'progress',done:i+1,total:iterations});
        // Cooperative pacing: not a thermal, OS scheduler or strict CPU quota.
        const nap=Math.max(0,(100-Math.min(75,Math.max(5,budget||25)))/100*7);
        if(nap)await new Promise(resolve=>setTimeout(resolve,nap));
        if(performance.now()-start>20000)throw Error('Browser task exceeded safe runtime limit');
      }
    }
    self.postMessage({type:'done',digest:[...bytes].map(b=>b.toString(16).padStart(2,'0')).join(''),duration_seconds:(performance.now()-start)/1000});
  }catch(err){self.postMessage({type:'error',message:String(err.message||err)});}
};
