// Reviewed, bundled paradigms only. Do not eval or dynamically import submitted user code.
import { GibsonScene } from './gibson.js';
import { FlyingScene, ToasterScene } from './flying.js';
import { PipesScene } from './pipes.js';
import { TerminalScene } from './terminal.js';
export const scenes = {
  gibson:{ title:'GIBSON / MONOLITH ARRAY', factory:GibsonScene },
  flying:{ title:'FLYING CATS / THE SKY', factory:FlyingScene },
  toasters:{ title:'FLYING TOASTERS / CLASSIC', factory:ToasterScene },
  pipes:{ title:'PIPES / CATBOX NETWORK', factory:PipesScene },
  terminal:{ title:'CHRONICLE / TEXT MODE', factory:TerminalScene },
};
// Adding a new full scene requires reviewing its JS and registering a factory above.
// Scene API: constructor(canvas, theme, onSelect), setData(snapshot), draw(seconds), destroy().
export const themes = {
  gibson:{name:'Gibson Blue',accent:'#35bcff',low:'#06162c',bright:'#a9edff'},
  emerald:{name:'Phosphor Green',accent:'#57f0ba',low:'#021a18',bright:'#c2ffe0'},
  ember:{name:'Amber Terminal',accent:'#ffac51',low:'#201009',bright:'#ffe3af'},
  graphite:{name:'Thurber Graphite',accent:'#c6d3e4',low:'#151c2b',bright:'#f7f8fa'},
};
export function validateTheme(value){
  if(!value || typeof value!=='object' || Array.isArray(value)) throw Error('Skin must be an object');
  const hex = s => typeof s==='string' && /^#[0-9a-fA-F]{6}$/.test(s);
  if(!hex(value.accent)||!hex(value.low)||!hex(value.bright)) throw Error('A skin needs accent, low and bright #RRGGBB colors');
  if(typeof value.name!=='string'||value.name.length<2||value.name.length>50) throw Error('Skin name must be 2–50 characters');
  return {name:value.name,accent:value.accent,low:value.low,bright:value.bright};
}
export function demoSnapshot(){
  const projects=[
    {id:'climate-tiles',title:'Open Climate Tiles',category:'climate_research',status:'open',tasks:{done:84,leased:8,pending:20}},
    {id:'star-catalogue',title:'Public Star Catalogue',category:'open_science',status:'open',tasks:{done:62,leased:5,pending:13}},
    {id:'biodiversity',title:'Commons Biodiversity Map',category:'open_science',status:'open',tasks:{done:25,leased:4,pending:9}},
    {id:'render-demo',title:'Open Animation Frames',category:'open_media',status:'open',tasks:{done:14,leased:2,pending:10}},
  ];
  const nodes=Array.from({length:32},(_,i)=>{
    const project=projects[i%projects.length];const done=(i*7+11)%26;
    return {id:`demo-node-${String(i+1).padStart(2,'0')}`,revoked:false,
      projects:{[project.id]:{done,leased:i%3===0?1:0}}};
  });
  const events=Array.from({length:14},(_,i)=>({id:i+1,at:Date.now()/1000-(13-i)*19,
    node_id:nodes[(i*5)%nodes.length].id,job_id:projects[i%4].id,
    kind:i%4===0?'task_leased':'task_verified',detail:`Preview ${i%4===0?'leased':'verified'} task ${i+1}`}));
  return {schema:'polyc.catnap.snapshot/v1',mode:'demo',scope:'synthetic',server_time:Date.now()/1000,
    nodes,projects,events,counts:{nodes:32,pending:52,leased:19,done:185,failed:0}};
}
export function getMonoliths(data){
  const nodes=data?.nodes||[],projects=data?.projects||[];
  const out=[];
  for(const node of nodes){
    const entries=Object.entries(node.projects||{});
    if(!entries.length){out.push({id:node.id,project:'Idle / awaiting consent',done:0,leased:0,pending:0,revoked:node.revoked});continue;}
    for(const [id,c] of entries){
      out.push({id:node.id+' · '+id,project:projects.find(x=>x.id===id)?.title||id,
        node:node.id,done:c.done||0,leased:c.leased||0,pending:c.pending||0,revoked:node.revoked});
    }
  }
  if(!out.length){for(const p of projects)out.push({id:p.id,project:p.title,done:p.tasks?.done||0,leased:p.tasks?.leased||0,pending:p.tasks?.pending||0,revoked:false});}
  return out.slice(0,180);
}
