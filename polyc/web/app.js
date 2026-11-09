import { scenes, themes, validateTheme, demoSnapshot } from './scenes/registry.js';
import { canonical, digest, hex, verifySignedCat } from './protocol.js';
const $=id=>document.getElementById(id);
const encoder=new TextEncoder();
const state={snapshot:demoSnapshot(),node:null,adminToken:null,scene:null,sceneId:'gibson',theme:themes.gibson,
             sceneSpeed:.5,run:false,worker:null,abortTask:null,localProgress:0,polling:false,lastFrame:0,sessionDeadline:0,sessionMinutes:30,selfEnroll:null,catalog:[]};
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function api(path,method='GET',payload=null,token=null){const options={method,headers:{'Accept':'application/json'}};
  if(token)options.headers.Authorization=`Bearer ${token}`;
  if(payload!==null){options.headers['Content-Type']='application/json';options.body=JSON.stringify(payload);}
  const r=await fetch(path,options);const result=await r.json().catch(()=>({detail:`HTTP ${r.status}`}));
  if(!r.ok)throw Error(typeof result.detail==='string'?result.detail:JSON.stringify(result.detail));return result;
}
function message(where,text,isError=false){const box=$(where);box.textContent=text;box.classList.toggle('error',isError);}
function presentSnapshot(snap){state.snapshot=snap;$('connectBadge').textContent=snap.mode==='demo'?'DEMO • NO LIVE DATA':snap.scope==='operator'?'LIVE • OPERATOR':'LIVE • OWNER';
  $('connectBadge').classList.toggle('warn',snap.mode==='demo');$('sceneFeed').textContent=snap.mode==='demo'?'SYNTHETIC PREVIEW':`REAL COORDINATOR / ${snap.scope}`;
  $('screenMessage').hidden=snap.mode!=='demo';$('verifiedCount').textContent=Number(snap.counts?.done||0).toLocaleString();
  $('nodeCount').textContent=`${snap.counts?.nodes||0} participating nodes`;
  $('leasedCount').textContent=snap.counts?.leased||0;
  if(state.scene)state.scene.setData(snap);
  const target=$('chronicleFeed');target.replaceChildren();const events=[...(snap.events||[])].slice(-30).reverse();
  if(!events.length){const p=document.createElement('p');p.className='helper';p.textContent='No recorded task events in this scope yet.';target.append(p);}
  for(const e of events){const div=document.createElement('div');div.className='feed-entry';
    const t=document.createElement('time');t.textContent=new Date(e.at*1000).toLocaleTimeString();
    const k=document.createElement('span');k.className='kind';k.textContent=e.kind;
    const d=document.createElement('span');d.textContent=e.detail;div.append(t,k,d);target.append(div);
  }
}
function newCanvas(){const old=$('sceneCanvas');const canvas=document.createElement('canvas');canvas.id='sceneCanvas';canvas.tabIndex=0;canvas.setAttribute('aria-label','Catnap compute scene');old.replaceWith(canvas);return canvas;}
function switchScene(id){if(!scenes[id])return;state.scene?.destroy();const canvas=newCanvas();state.sceneId=id;
  try{state.scene=new scenes[id].factory(canvas,state.theme,item=>{
    $('selectedLabel').textContent=item.node||item.id;
    $('selectedDetail').textContent=`${item.project} • ${item.done} verified / ${item.leased} leased`;
  });}catch(err){state.sceneId='terminal';state.scene=new scenes.terminal.factory(newCanvas(),state.theme);message('catnapNotice',`WebGL unavailable: ${err.message}. Showing Chronicle Terminal.`,true);}
  state.scene.speed=state.sceneSpeed;state.scene.setData(state.snapshot);
  $('sceneTitle').textContent=scenes[state.sceneId].title;
  for(const b of document.querySelectorAll('[data-scene]'))b.classList.toggle('active',b.dataset.scene===state.sceneId);
}
function draw(t){requestAnimationFrame(draw);if(!$('visualizerDisclosure').open)return;const limit=state.run?12:30; if(t-state.lastFrame<1000/limit)return;state.lastFrame=t;
  $('sceneClock').textContent=new Date().toLocaleTimeString('en-GB',{hour12:false});
  try{state.scene?.draw(t/1000);}catch(err){console.error('scene error',err);if(state.sceneId!=='terminal')switchScene('terminal');}
}
async function refreshLive(){if(state.polling||(!state.node&&!state.adminToken))return;
  state.polling=true;try{
    const token=state.adminToken||state.node.token;
    const q=state.adminToken?'':`?node_id=${encodeURIComponent(state.node.node_id)}`;
    presentSnapshot(await api('/api/catnap/snapshot'+q,'GET',null,token));
  }catch(err){message('catnapNotice',`Live feed unavailable: ${err.message}`,true);
    // Do not silently label synthetic events as live if authorization fails.
    if(!state.run)presentSnapshot(demoSnapshot());
  }finally{state.polling=false;}
}
async function verifyAssignment(lease){const sp=lease.signed_project, project=sp.project,c=state.node.constitution;
  if(!c.spec.trust.trusted_signers.includes(sp.signer_pubkey))throw Error('Cat signer is not explicitly trusted');
  if(!c.spec.content.allow_categories.includes(project.category)||c.spec.content.deny_categories.includes(project.category))throw Error('Cat category not approved by owner');
  if(project.commercial&&!c.spec.ethos.allow_commercial_projects)throw Error('Commercial Cat not approved by owner');
  if(project.purposes.some(p=>c.spec.ethos.exclude_projects_with_declared_purposes.includes(p)))throw Error('Cat purpose is excluded');
  if(project.contributor_allowlist?.length&&!project.contributor_allowlist.includes(state.node.node_id))throw Error('Not on Cat contributor allowlist');
  if(project.contributor_denylist?.includes(state.node.node_id))throw Error('Cat denies this node');
  if(project.work.kind!=='sha256_chain_v1')throw Error('Browser does not execute unreviewed Catbox code');
  if(project.work.iterations>10000)throw Error('Cat task is too large for bounded browser worker (10k limit)');
  if(!Number.isInteger(lease.task_index)||lease.task_index<0||lease.task_index>=project.work.tasks)throw Error('Invalid task index');
  if(!await verifySignedCat(sp,c.spec.trust.trusted_signers))throw Error('Cat signature verification failed');
}
function executeTask(lease){return new Promise((resolve,reject)=>{
  let completed=false,timeout=null;const w=new Worker('/web/compute-worker.js',{type:'module'});state.worker=w;
  function finish(ok,value){if(completed)return;completed=true;clearTimeout(timeout);w.terminate();if(state.worker===w)state.worker=null;state.abortTask=null;ok?resolve(value):reject(Error(value));}
  state.abortTask=()=>finish(false,'Owner paused or left the visible page');
  w.onmessage=e=>{if(e.data.type==='progress'){$('workProgress').style.width=(100*e.data.done/e.data.total).toFixed(1)+'%';}
    if(e.data.type==='done')finish(true,e.data);if(e.data.type==='error')finish(false,e.data.message);};
  w.onerror=e=>finish(false,e.message||'Web worker failed');
  timeout=setTimeout(()=>finish(false,'Task runtime timeout'),Math.min(20000,state.node.constitution.spec.nice_plus.task_runtime_seconds_max*1000));
  w.postMessage({type:'run',seed:lease.signed_project.project.work.seed,index:lease.task_index,
    iterations:lease.signed_project.project.work.iterations,budget:state.node.constitution.spec.nice_plus.cpu_percent_max});
});}
async function computeLoop(){const id=state.node.node_id,token=state.node.token;
  while(state.run && state.node?.node_id===id){
    if(state.sessionDeadline && Date.now()>=state.sessionDeadline){stopCompute();message('catnapNotice','Your local session time limit has been reached. Catnap paused.');break;}
    if(document.hidden){$('workStatus').textContent='WAITING FOR VISIBLE TAB';await sleep(900);continue;}
    let lease;
    try{
      $('workStatus').textContent='REQUESTING CONSENTED WORK';
      const res=await api('/api/lease','POST',{node_id:id,constitution_digest:await digest(state.node.constitution)},token);
      if(!state.run)break;
      if(state.sessionDeadline && Date.now()>=state.sessionDeadline){stopCompute();break;}
      lease=res.assignment;
      if(!lease){$('workStatus').textContent='IDLE • NO MATCHING CATS';await sleep(1200);continue;}
      $('workStatus').textContent=`WORKING • ${lease.task_id}`;
      await verifyAssignment(lease);
      const result=await executeTask(lease);
      if(!state.run||document.hidden)throw Error('Owner paused before verified result submission');
      const validity=await api(`/api/tasks/${encodeURIComponent(lease.task_id)}/status?node_id=${encodeURIComponent(id)}`,'GET',null,token);
      if(!validity.active)throw Error('Task lease expired or Cat was cancelled');
      await api(`/api/tasks/${encodeURIComponent(lease.task_id)}/complete`,'POST',{
        node_id:id,lease_id:lease.lease_id,digest:result.digest,duration_seconds:result.duration_seconds},token);
      $('workProgress').style.width='100%';$('workStatus').textContent='RESULT VERIFIED';await refreshLive();await sleep(350);
    }catch(err){message('catnapNotice',`Catnap: ${err.message}`,true);
      if(lease){try{await api(`/api/tasks/${encodeURIComponent(lease.task_id)}/fail`,'POST',{
        node_id:id,lease_id:lease.lease_id,reason:String(err.message).slice(0,200)},token);}catch{/* lease may already be revoked/expired */}}
      await sleep(450);
    }
  }
  $('workStatus').textContent='PAUSED';
}
function stopCompute(){state.run=false;state.sessionDeadline=0;state.abortTask?.();state.worker?.terminate();state.worker=null;$('workStatus').textContent='PAUSED';$('workProgress').style.width='0%';updateVisitorStatus();}
const declaredPurpose=/^[A-Za-z0-9_-]{1,80}$/;
function selectedCategories(){const choices=[['categoryScience','open_science'],['categoryClimate','climate_research'],['categoryMedia','open_media']];
  return choices.filter(([id])=>$(id).checked).map(([,category])=>category);
}
function excludedPurposes(base){const values=$('excludedPurposes').value.split(/[,\n]+/).map(v=>v.trim()).filter(Boolean);
  if(values.length>30||values.some(v=>!declaredPurpose.test(v)))throw Error('Excluded purposes: up to 30 names, each 1–80 letters, digits, _ or -');
  return [...new Set([...base,...values])];
}
function fillApprovedCats(cats){
  const container=$('approvedCatList');const trusted=new Set([...container.querySelectorAll('input[type="checkbox"]:checked')].map(el=>el.value));
  container.replaceChildren();
  if(!cats.length){const p=document.createElement('p');p.className='helper';p.textContent='No approved Cats are currently available. You can enroll now, but no tasks will run until you select a trusted creator. An operator must approve a Cat first.';container.append(p);return;}
  for(const cat of cats){
    const label=document.createElement('label');label.className='approved-cat';
    const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.value=cat.creator_key;
    checkbox.checked=trusted.has(cat.creator_key);
    const content=document.createElement('span');const title=document.createElement('strong');title.textContent=cat.title;
    const detail=document.createElement('small');detail.textContent=`${cat.category.replaceAll('_',' ')} • ${cat.commercial?'commercial':'noncommercial'} • ${cat.work_kind} • ${cat.financial?'financial contract (not supported in browser)':'volunteer'}`;
    const key=document.createElement('code');key.textContent=`Creator key: ${cat.creator_key.slice(0,16)}… • ${cat.project_id}`;
    content.append(title,detail,key);label.append(checkbox,content);container.append(label);
  }
}
async function refreshCatalog(){try{
  const result=await api('/api/catnap/catalog');state.catalog=result.cats;
  fillApprovedCats(result.cats);message('catalogNotice',result.cats.length?`${result.cats.length} approved Cat(s) found. Choose creators explicitly; none are selected by default.`:'No approved Cats yet. Enrolling is allowed, but no work will be assigned until you later trust a creator.');
}catch(err){message('catalogNotice',`Could not load approved Cats: ${err.message}`,true);}}
async function loadEnrollmentOptions(){try{
  const settings=await api('/api/catnap/enrollment-options');state.selfEnroll=!!settings.self_enroll;
  $('inviteFallback').hidden=state.selfEnroll;
  $('enrollmentModeNotice').textContent=state.selfEnroll?'Self-enrollment is enabled: no invitation or operator account is needed.':'This Commons currently requires an invitation for Catnap registration.';
  document.querySelector('.self-join-note').hidden=!state.selfEnroll;
}catch(err){state.selfEnroll=null;$('enrollmentModeNotice').textContent=`Enrollment settings unavailable: ${err.message}`;}}
async function draftPolic(){const template=await api('/api/catnap/constitution-template');const constitution=template.constitution;
  const nodeId=$('catnapName').value.trim();if(!/^[a-z0-9-]{3,64}$/.test(nodeId))throw Error('Node ID must be 3–64 lowercase letters, digits or hyphens');
  const manualKeys=$('trustedSigners').value.split(/[\s,]+/).filter(Boolean).map(s=>s.toLowerCase());
  const selectedKeys=[...document.querySelectorAll('#approvedCatList input[type="checkbox"]:checked')].map(el=>el.value);
  const signers=[...new Set([...manualKeys,...selectedKeys])];
  if(signers.length>20||signers.some(s=>!/^[a-f0-9]{64}$/.test(s)))throw Error('Select at most 20 trusted creators, each with a 64-character hexadecimal public key');
  const categories=selectedCategories();if(!categories.length)throw Error('Allow at least one category to participate');
  constitution.metadata.name=nodeId;
  constitution.spec.trust.trusted_signers=[...new Set(signers)];
  constitution.spec.nice_plus.cpu_percent_max=Number($('cpuBudget').value);
  constitution.spec.nice_plus.task_runtime_seconds_max=Number($('taskSeconds').value);
  constitution.spec.content.allow_categories=categories;
  constitution.spec.ethos.allow_commercial_projects=$('allowCommercial').checked;
  constitution.spec.ethos.exclude_projects_with_declared_purposes=excludedPurposes(constitution.spec.ethos.exclude_projects_with_declared_purposes);
  return constitution;
}
async function previewPolic(exportFile=false){
  const btn=$('previewPolicBtn'),exportBtn=$('exportPolicBtn');
  btn.disabled=exportBtn.disabled=true;
  message('policActionNotice',exportFile?'Preparing your PoliC download…':'Building your PoliC preview…');
  try{
    // Preview/export are exploratory. They never require an invitation, trusted signer, or consent to compute.
    const c=await draftPolic();
    $('policPreview').textContent=JSON.stringify(c,null,2);
    $('policPreview').hidden=false;
    btn.setAttribute('aria-expanded','true');
    const needsKeys=c.spec.trust.trusted_signers.length===0;
    if(exportFile)download(c.metadata.name+'.polic.json',c);
    message('policActionNotice',
      (exportFile?'PoliC JSON downloaded. ':'PoliC preview is displayed below. ')+
      (needsKeys?'No Cats are trusted yet, so enrollment will be idle until you add one. ':'Selected creators will be trusted for compatible, approved work. ')+
      'Neither action enrolls you or starts compute.');
  }catch(err){
    $('policPreview').hidden=true;
    btn.setAttribute('aria-expanded','false');
    message('policActionNotice',`Could not ${exportFile?'export':'preview'} PoliC: ${err.message}`,true);
  }finally{btn.disabled=exportBtn.disabled=false;}
}
function sessionMinutes(){return Number($('sessionMinutes').value);}
async function enroll(){
  const btn=$('enrollBtn');btn.disabled=true;
  message('enrollmentNotice','Checking your enrollment information…');
  try{
    if(!globalThis.isSecureContext)throw Error('Use HTTPS or http://localhost:8765 for browser cryptography');
    if(state.selfEnroll===null)throw Error('Enrollment settings have not loaded. Reload the page and try again.');
    const invitation=$('inviteCatnap').value.trim();
    if(!state.selfEnroll&&!invitation)throw Error('This Commons requires a one-use invitation from its operator.');
    const constitution=await draftPolic();
    if(!$('browserConsent').checked)throw Error('Check the resource and safety acknowledgement before enrolling.');
    const nodeId=constitution.metadata.name;
    const token=hex(crypto.getRandomValues(new Uint8Array(32)));
    const payload={accepted_browser_limitations:true,node:{node_id:nodeId,token,constitution}};
    if(invitation)payload.invitation=invitation;
    await api('/api/catnap/enroll','POST',payload);
    state.node=payload.node;
    state.sessionMinutes=sessionMinutes();
    sessionStorage.setItem('polyc.catnap.node.v1',JSON.stringify(state.node));
    showEnrolled();
    message('catnapNotice',`Enrolled ${nodeId}. No CPU work has started. ${constitution.spec.trust.trusted_signers.length?'Press Start Catnap when ready.':'No creators are trusted yet; Catnap will be idle until you re-enroll with a selected creator.'} To amend your PoliC, revoke and re-enroll.`);
    await refreshLive();
  }catch(err){
    message('enrollmentNotice',`Not enrolled: ${err.message}`,true);
    message('catnapNotice',`Not enrolled: ${err.message}`,true);
  }finally{btn.disabled=false;}
}
function updateVisitorStatus(){
  const status=$('visitorStatus');if(!status)return;
  const enrolled=!!state.node;status.classList.toggle('is-enrolled',enrolled&&!state.run);status.classList.toggle('is-running',state.run);
  status.textContent=!enrolled?'Not enrolled · CPU work is off':state.run?'Catnap enabled · Browser work may be running':'Enrolled · CPU work is off until you press Start';
  const line=$('postEnrollIntro');if(line)line.textContent=state.run?'Catnap is enabled. Use Pause to stop local work or Revoke Consent to withdraw permission.':'Your PoliC is enrolled. Your CPU is not working until you press Start.';
}
function showEnrolled(){$('enrollForm').hidden=!!state.node;$('participationForm').hidden=!state.node;
  if(state.node){$('nodeIdentity').textContent=state.node.node_id;
    const c=state.node.constitution.spec;
    $('activePolicSummary').textContent=`Registered PoliC: ${c.trust.trusted_signers.length} trusted creator(s) · ${c.nice_plus.cpu_percent_max}% best-effort CPU pacing · ${c.nice_plus.task_runtime_seconds_max}s task ceiling · ${c.content.allow_categories.join(', ')} · Commercial ${c.ethos.allow_commercial_projects?'permitted':'excluded'}. ${c.trust.trusted_signers.length?'Nothing computes until you press Start.':'No Cats authorized; this session will stay idle.'} To amend your PoliC, revoke and enroll again.`;
  }
  updateVisitorStatus();
}
async function revoke(){if(!state.node)return;stopCompute();try{
  await api(`/api/nodes/${encodeURIComponent(state.node.node_id)}/revoke`,'POST',{},state.node.token);
  message('catnapNotice','Consent revoked at the coordinator. Local computing has stopped. You may re-enroll with a new visitor identity.');
  state.node=null;sessionStorage.removeItem('polyc.catnap.node.v1');$('catnapName').value='browser-cat-'+hex(crypto.getRandomValues(new Uint8Array(3)));showEnrolled();if(!state.adminToken)presentSnapshot(demoSnapshot());
}catch(err){message('catnapNotice',`Revocation not confirmed remotely: ${err.message}. Local work is stopped. Revoke through the operator if unreachable.`,true);}}
async function creatorPair(){if(!globalThis.isSecureContext||!crypto.subtle)throw Error('Create a Cat requires a secure browser context');
  return new Promise((resolve,reject)=>{const request=indexedDB.open('polyc-creators-v1',1);
    request.onupgradeneeded=()=>request.result.createObjectStore('keys');request.onerror=()=>reject(Error('Cannot open browser creator key storage'));
    request.onsuccess=async()=>{const db=request.result;
      const read=db.transaction('keys','readonly').objectStore('keys').get('creator');
      read.onsuccess=async()=>{if(read.result){db.close();resolve(read.result);return;}
        try{const pair=await crypto.subtle.generateKey({name:'Ed25519'},false,['sign','verify']);
          const tx=db.transaction('keys','readwrite');tx.objectStore('keys').put(pair,'creator');
          tx.oncomplete=()=>{db.close();resolve(pair);};tx.onerror=()=>{db.close();reject(Error('Cannot save creator identity'));};
        }catch(e){db.close();reject(e);}};
      read.onerror=()=>{db.close();reject(Error('Cannot read creator identity'));};
    };
  });
}
function parseContributors(value){const items=value.split(/[,\n]+/).map(s=>s.trim()).filter(Boolean);if(items.length>100||new Set(items).size!==items.length||items.some(s=>!/^[A-Za-z0-9_-]{1,80}$/.test(s)))throw Error('Contributor lists must contain unique alphanumeric, underscore or hyphen IDs');return items;}
async function signedCat(){const project={project_id:$('catId').value.trim(),title:$('catTitle').value.trim(),
  source_repo:$('catRepo').value.trim(),source_commit:$('catCommit').value.trim().toLowerCase(),
  category:$('catTemplate').value,purposes:[$('catPurpose').value.trim()],commercial:$('catCommercial').checked,
  contributor_allowlist:parseContributors($('catAllow').value),contributor_denylist:parseContributors($('catDeny').value),work:{kind:'sha256_chain_v1',tasks:Number($('catTasks').value),
    iterations:Number($('catIterations').value),seed:$('catSeed').value.trim()}};
  if($('catFunding').value==='test_credits')project.financial={model:'test_credits',asset_id:$('catAsset').value.trim(),credits_per_verified_task:Number($('catPay').value)};
  if(project.financial&&(!/^[a-z][a-z0-9._-]{3,79}$/.test(project.financial.asset_id)||!Number.isInteger(project.financial.credits_per_verified_task)||project.financial.credits_per_verified_task<1||project.financial.credits_per_verified_task>10000))throw Error('Invalid test-credit contract; choose an existing asset and 1–10,000 integer units');
  if(!/^[a-z0-9][a-z0-9-]{2,63}$/.test(project.project_id))throw Error('Cat ID must be 3–64 lowercase letters, digits and hyphens');
  if(project.title.length<4||project.title.length>120)throw Error('Cat name must be 4–120 characters');
  if(!/^https:\/\/[A-Za-z0-9._/-]+$/.test(project.source_repo))throw Error('A public HTTPS source repository is required');
  if(!/^[a-f0-9]{40}$/.test(project.source_commit))throw Error('Provide a genuine 40-hex source commit for review');
  if(!/^[a-zA-Z0-9_-]{1,80}$/.test(project.purposes[0]))throw Error('Purpose must be one short alphanumeric tag');
  if(!Number.isInteger(project.work.tasks)||project.work.tasks<1||project.work.tasks>100)throw Error('Task count must be 1–100');
  if(!Number.isInteger(project.work.iterations)||project.work.iterations<1||project.work.iterations>400000)throw Error('Iterations must be 1–400000');
  if(!/^[A-Za-z0-9._-]{1,128}$/.test(project.work.seed))throw Error('Seed accepts letters, numbers, periods, underscores, and hyphens');
  const pair=await creatorPair();const pub=hex(await crypto.subtle.exportKey('raw',pair.publicKey));
  const sig=hex(await crypto.subtle.sign({name:'Ed25519'},pair.privateKey,encoder.encode(canonical(project))));
  $('creatorPubKey').textContent=pub;
  return {project,signer_pubkey:pub,signature:sig};
}
function download(name,payload){const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});
  const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(href),2000);
}
async function prepareCat(submit){try{const signed=await signedCat();download(signed.project.project_id+'.signed.json',signed);
  if(submit){const result=await api('/api/workshop/cats','POST',{
    invitation:$('inviteCreate').value.trim(),signed_project:signed});
    message('creatorNotice',`Cat ${result.project_id} is STAGED for operator review, not yet executable. Share the creator public key with prospective Catnap contributors for explicit opt-in.`);
  }else message('creatorNotice','Signed Cat exported. This built-in task still requires an invitation, review, and explicit contributor trust before work starts.');
}catch(err){message('creatorNotice',err.message,true);}}
async function proposals(){if(!state.adminToken)return;
  const data=await api('/api/workshop/cats','GET',null,state.adminToken);const el=$('proposalList');el.replaceChildren();
  if(!data.cats.length){const p=document.createElement('p');p.className='helper';p.textContent='No Cats have been proposed yet.';el.append(p);}
  for(const cat of data.cats){const card=document.createElement('div');card.className='proposal';
    const name=document.createElement('strong');name.textContent=`${cat.title} [${cat.status.toUpperCase()}]`;
    const id=document.createElement('small');id.textContent=`${cat.project_id} · Signer: ${cat.signer_pubkey}`;card.append(name,id);
    if(cat.status==='staged'){const row=document.createElement('div');row.className='inline-actions';
      for(const [action,label] of [[true,'APPROVE BUILT-IN CAT'],[false,'REJECT']]){
        const btn=document.createElement('button');btn.className=action?'primary':'danger';btn.textContent=label;
        btn.onclick=async()=>{try{await api(`/api/workshop/cats/${encodeURIComponent(cat.project_id)}/review`,'POST',{
          approve:action,note:action?'Operator reviewed the built-in task':'Operator rejected this Cat'},state.adminToken);
          message('adminNotice',`Cat ${cat.project_id} ${action?'approved':'rejected'}. Contributor consent is still required.`);
          await proposals();await refreshLive();}catch(err){message('adminNotice',err.message,true);}};
        row.append(btn);
      }card.append(row);
    }el.append(card);
  }
}
function selectExplainer(step, moveFocus=false){
  const buttons=[...document.querySelectorAll('[data-explain]')];
  for(const button of buttons){
    const selected=button.dataset.explain===String(step);
    button.classList.toggle('active',selected);
    button.setAttribute('aria-selected',String(selected));
    button.tabIndex=selected?0:-1;
    $(button.getAttribute('aria-controls')).hidden=!selected;
    if(selected&&moveFocus)button.focus();
  }
}
function wireUI(){
  const explainButtons=[...document.querySelectorAll('[data-explain]')];
  for(const [index,button] of explainButtons.entries()){
    button.addEventListener('click',()=>selectExplainer(button.dataset.explain));
    button.addEventListener('keydown',event=>{
      const next=event.key==='ArrowRight'?index+1:event.key==='ArrowLeft'?index-1:event.key==='Home'?0:event.key==='End'?explainButtons.length-1:null;
      if(next===null)return;
      event.preventDefault();selectExplainer(explainButtons[(next+explainButtons.length)%explainButtons.length].dataset.explain,true);
    });
  }
  for(const btn of document.querySelectorAll('[data-panel]'))btn.onclick=()=>{ 
  for(const x of document.querySelectorAll('[data-panel]')){x.classList.toggle('selected',x===btn);if(x.matches('.main-nav [data-panel]')){if(x===btn)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current');}}
  for(const x of document.querySelectorAll('.panel'))x.classList.toggle('visible',x.id===btn.dataset.panel);
  if(!btn.closest('.main-nav'))$(btn.dataset.panel)?.scrollIntoView({block:'start'});
};
  for(const btn of document.querySelectorAll('[data-scene]'))btn.onclick=()=>switchScene(btn.dataset.scene);
  $('fullscreenBtn').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen();else $('screenShell').requestFullscreen?.();};
  $('skinSelect').onchange=e=>{const skin=themes[e.target.value];if(skin){state.theme=skin;switchScene(state.sceneId);localStorage.setItem('polyc.catnap.skin',e.target.value);}};
  $('speedRange').oninput=e=>{$('speedValue').textContent=e.target.value+'%';state.sceneSpeed=Number(e.target.value)/100;if(state.scene)state.scene.speed=state.sceneSpeed;};
  $('cpuBudget').oninput=e=>$('cpuValue').textContent=e.target.value+'%';
  $('refreshCatalog').onclick=refreshCatalog;
  $('previewPolicBtn').onclick=()=>previewPolic();
  $('exportPolicBtn').onclick=()=>previewPolic(true);
  $('exportSkinBtn').onclick=()=>download('catnap-skin.json',state.theme);
  $('importSkin').onchange=async e=>{try{const file=e.target.files?.[0];if(!file)return;if(file.size>10000)throw Error('Skin file too large');
    const skin=validateTheme(JSON.parse(await file.text()));themes.custom=skin;const sel=$('skinSelect');let opt=sel.querySelector('option[value=custom]');
    if(!opt){opt=document.createElement('option');opt.value='custom';sel.append(opt);}opt.textContent=skin.name;sel.value='custom';state.theme=skin;switchScene(state.sceneId);
    message('catnapNotice',`Skin imported: ${skin.name}. Only colors and labels were read—no code executed.`);
  }catch(err){message('catnapNotice',err.message,true);}};
  $('enrollBtn').onclick=enroll;
  $('startBtn').onclick=()=>{if(!state.node||state.run)return;state.sessionDeadline=state.sessionMinutes?Date.now()+state.sessionMinutes*60000:0;state.run=true;updateVisitorStatus();message('catnapNotice','Catnap started. Every assigned Cat is locally verified and consent checked.');computeLoop();};
  $('pauseBtn').onclick=()=>{stopCompute();message('catnapNotice','Catnap paused locally. No new leases will be requested.');};
  $('revokeBtn').onclick=revoke;
  $('catFunding').onchange=e=>$('fundingOptions').hidden=e.target.value!=='test_credits';
  $('prepareCat').onclick=()=>prepareCat(false);$('submitCat').onclick=()=>prepareCat(true);
  $('copyPubBtn').onclick=async()=>{const v=$('creatorPubKey').textContent;if(v.length===64){await navigator.clipboard.writeText(v);message('creatorNotice','Public signer key copied. Contributors must independently opt in to trust it.');}};
  $('adminConnect').onclick=async()=>{try{state.adminToken=$('adminToken').value.trim();$('adminToken').value='';
    if(!state.adminToken)throw Error('Enter an administrator token');
    await refreshLive();if(state.snapshot.mode!=='live'||state.snapshot.scope!=='operator')throw Error('Invalid administrator token');
    await proposals();message('adminNotice','Operator connected. Credential is held only in page memory.');
  }catch(err){state.adminToken=null;message('adminNotice',err.message,true);}};
  $('adminDisconnect').onclick=()=>{state.adminToken=null;message('adminNotice','Operator disconnected.');if(!state.node)presentSnapshot(demoSnapshot());else refreshLive();$('proposalList').replaceChildren();};
  $('makeInvites').onclick=async()=>{try{if(!state.adminToken)throw Error('Connect the operator first');
    const r=await api('/api/catnap/invitations','POST',{kind:$('inviteKind').value,count:Number($('inviteQuantity').value),ttl_seconds:3600},state.adminToken);
    $('inviteOutput').textContent=r.invitations.join('\n');message('adminNotice',`${r.invitations.length} one-use ${r.kind} invitations generated. Share each privately.`);
  }catch(err){message('adminNotice',err.message,true);}};
  $('refreshProposals').onclick=()=>proposals().catch(err=>message('adminNotice',err.message,true));
  $('openScreensaverFromExplainer').addEventListener('click',()=>{$('visualizerDisclosure').open=true;});
  const visualizer=$('visualizerDisclosure');visualizer.addEventListener('toggle',()=>{
    if(visualizer.open)switchScene(state.sceneId);else{state.scene?.destroy();state.scene=null;}
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden)state.abortTask?.();});
  window.addEventListener('pagehide',()=>{stopCompute();});
}
function init(){try{const n=JSON.parse(sessionStorage.getItem('polyc.catnap.node.v1'));if(n?.node_id&&n?.token&&n?.constitution)state.node=n;}catch{sessionStorage.removeItem('polyc.catnap.node.v1');}
  showEnrolled();if(!state.node)$('catnapName').value='browser-cat-'+hex(crypto.getRandomValues(new Uint8Array(3)));const saved=localStorage.getItem('polyc.catnap.skin');if(saved&&themes[saved]){$('skinSelect').value=saved;state.theme=themes[saved];}
  wireUI();loadEnrollmentOptions();refreshCatalog();$('policEditorReady').textContent='PoliC editor ready. You can preview a draft before enrolling.';presentSnapshot(demoSnapshot());requestAnimationFrame(draw);
  if(state.node)refreshLive();setInterval(refreshLive,2500);
}
init();
