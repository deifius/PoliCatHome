// Crypto protocol shared by browser Cat creators and volunteers.
// Matches Python polyc.crypto.canonical(...), including ASCII escaping.
const encoder=new TextEncoder();
export const hex=bytes=>[...new Uint8Array(bytes)].map(x=>x.toString(16).padStart(2,'0')).join('');
export const bytesFromHex=s=>new Uint8Array(s.match(/../g).map(x=>parseInt(x,16)));
export function noNull(obj){return Array.isArray(obj)?obj.map(noNull):obj&&typeof obj==='object'?
  Object.fromEntries(Object.entries(obj).filter(([,v])=>v!==null&&v!==undefined).map(([k,v])=>[k,noNull(v)])):obj;}
export function canonical(obj){function sort(v){if(Array.isArray(v))return v.map(sort);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,sort(v[k])]));return v;}
  return JSON.stringify(sort(noNull(obj))).replace(/[\u007f-\uffff]/g,c=>`\\u${c.charCodeAt(0).toString(16).padStart(4,'0')}`);
}
export async function digest(value){return hex(await crypto.subtle.digest('SHA-256',encoder.encode(canonical(value))));}
export async function verifySignedCat(sp, trusted){
  if(!trusted.includes(sp.signer_pubkey))return false;
  if(!/^[a-f0-9]{64}$/.test(sp.signer_pubkey)||!/^[a-f0-9]{128}$/.test(sp.signature))return false;
  try{const pub=await crypto.subtle.importKey('raw',bytesFromHex(sp.signer_pubkey),{name:'Ed25519'},false,['verify']);
    return await crypto.subtle.verify({name:'Ed25519'},pub,bytesFromHex(sp.signature),encoder.encode(canonical(sp.project)));
  }catch{return false;}
}
