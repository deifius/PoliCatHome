/* PoliC identity: a voluntary, first-party way to return to your workspace.
 * Browser keys are non-extractable Web Crypto Ed25519 keys held in IndexedDB;
 * account sessions are HttpOnly server cookies, NOT localStorage tokens.
 * Nothing in this module enrolls a worker, changes a constitution or starts work.
 */
const dbName = 'polyc-browser-identity-v1';
let currentAccount = null;
let knownConfiguration = null;
let modal;
let notice;

export async function identityMe() {
  try {
    const response = await fetch('/api/identity/me', {credentials:'same-origin', cache:'no-store'});
    if (!response.ok) return {authenticated:false};
    const data = await response.json();
    currentAccount = data;
    return data;
  } catch { return {authenticated:false}; }
}

async function identityConfig() {
  if (knownConfiguration) return knownConfiguration;
  try {
    const r = await fetch('/api/identity/config',{credentials:'same-origin'});
    knownConfiguration = r.ok ? await r.json() : {google_enabled:false};
  } catch { knownConfiguration = {google_enabled:false}; }
  return knownConfiguration;
}

function openDb() {
  return new Promise((resolve,reject) => {
    if (!('indexedDB' in window)) { reject(new Error('Browser key storage is unavailable')); return; }
    const req = indexedDB.open(dbName,1);
    req.onupgradeneeded = () => req.result.createObjectStore('credentials');
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
  });
}
async function keyStore(method,value) {
  const db = await openDb();
  return new Promise((resolve,reject) => {
    const tx = db.transaction('credentials',method === 'get' ? 'readonly' : 'readwrite');
    const req = method === 'get' ? tx.objectStore('credentials').get('browser-key') : tx.objectStore('credentials').put(value,'browser-key');
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    tx.oncomplete = () => db.close();
  });
}
const hex = bytes => Array.from(new Uint8Array(bytes)).map(n=>n.toString(16).padStart(2,'0')).join('');
async function loadKey() { try { return await keyStore('get'); } catch { return null; } }
async function createKey() {
  if (!crypto?.subtle) throw new Error('Cryptographic identity requires HTTPS or localhost');
  const pair = await crypto.subtle.generateKey({name:'Ed25519'},false,['sign','verify']);
  const publicKey = hex(await crypto.subtle.exportKey('raw',pair.publicKey));
  const credential = {publicKey,privateKey:pair.privateKey};
  await keyStore('put',credential);
  return credential;
}
async function json(path,data,method='POST') {
  const r = await fetch(path, {method,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const value = await r.json().catch(()=>({detail:'The identity service is unavailable'}));
  if (!r.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Identity request failed');
  return value;
}
async function proveKey(purpose, key) {
  const challenge = await json('/api/identity/challenge',{purpose,public_key:key.publicKey});
  const signature = hex(await crypto.subtle.sign('Ed25519',key.privateKey,new TextEncoder().encode(challenge.message)));
  return json('/api/identity/prove',{challenge_id:challenge.challenge_id,signature});
}
function say(message, isError=false) {
  if (!notice) return;
  notice.textContent = message;
  notice.dataset.error = String(isError);
}
function button(label,callback,primary=false) {
  const b = document.createElement('button');
  b.type='button'; b.className='identity-option'+(primary?' identity-primary':'');
  b.textContent = label;
  b.addEventListener('click',async () => {
    b.disabled = true;
    try { await callback(); } catch(err) { say(err.message || 'That did not work.',true); }
    finally { b.disabled=false; }
  });
  return b;
}
async function renderModal() {
  if (!modal) return;
  const body = modal.querySelector('.identity-options');
  const heading = modal.querySelector('h2');
  body.replaceChildren(); say('');
  const account = currentAccount?.authenticated ? currentAccount.identity : null;
  const config = await identityConfig();
  if (account) {
    heading.textContent = 'Your identity, your choice.';
    const alias = document.createElement('p');
    alias.className='identity-alias'; alias.textContent = account.alias + ' · ' + account.id;
    body.append(alias);
    const explainer = document.createElement('p');
    explainer.className='identity-note';
    explainer.textContent='This identity opens your workspace. It cannot start Catnap, approve Cats, or operate the Commons.';
    body.append(explainer);
    const methods = currentAccount?.login_methods;
    if (methods && !methods.independent_keys) {
      const warning = document.createElement('p'); warning.className='identity-note identity-warning';
      warning.textContent = 'This identity currently depends on Google. Add an independent key before disconnecting Google.';
      body.append(warning);
    }
    const aliasLabel = document.createElement('label');
    aliasLabel.className='identity-label'; aliasLabel.textContent='Pseudonym';
    const aliasInput=document.createElement('input');
    aliasInput.type='text'; aliasInput.maxLength=40; aliasInput.minLength=2;
    aliasInput.value=account.alias; aliasInput.autocomplete='off';
    aliasLabel.append(aliasInput);body.append(aliasLabel);
    body.append(button('Save pseudonym',async()=>{
      const result=await json('/api/identity/alias',{alias:aliasInput.value.trim()},'PATCH');
      currentAccount.identity=result.identity;await renderModal();
    }));
    body.append(button('Open my workspace',()=>{modal.close();document.querySelector('.branching-home')?.setAttribute('hidden','');document.documentElement.classList.remove('branching-active');},true));
    body.append(button(account.default_landing === 'workspace' ? 'Show Bloom next visit' : 'Skip Bloom next visit',async()=>{
      const desired = account.default_landing === 'workspace' ? 'bloom' : 'workspace';
      const result = await json('/api/identity/preferences',{default_landing:desired},'PATCH');
      currentAccount.identity = result.identity;
      await renderModal();
    }));
    const key = await loadKey();
    if (!key) body.append(button('Give this browser an independent identity key',async()=>{
      say('Creating a non-exportable key on this browser…');
      const created = await createKey();
      await proveKey('link-key',created);
      say('Independent key linked. Keep another login method before clearing this browser.');
    }));
    if (config.google_enabled && !methods?.google_linked) body.append(button('Link a Google sign-in (optional)',async()=>{
      const result=await json('/api/identity/google/link/start',{});
      location.assign(result.url);
    }));
    body.append(button('Export my identity record',()=>{location.assign('/api/identity/export');}));
    if (config.google_enabled && methods?.google_linked) body.append(button('Unlink Google (keep another login method)',async()=>{
      const r = await fetch('/api/identity/providers/google',{method:'DELETE',credentials:'same-origin'});
      if(!r.ok) { const v=await r.json(); throw new Error(v.detail || 'Cannot unlink Google'); }
      currentAccount.login_methods.google_linked=false;
      await renderModal();say('Google unlinked. Your PoliC identity remains.');
    }));
    body.append(button('Sign out',async()=>{
      await json('/api/identity/logout',{});
      location.reload();
    }));
  } else {
    heading.textContent = 'An introduction is optional.';
    const key = await loadKey();
    const explainer = document.createElement('p');
    explainer.className='identity-note';
    explainer.textContent='An independent pseudonym can be recognized without your name or email. It does not authorize compute. The cat considers this very reasonable.';
    body.append(explainer);
    if (key) body.append(button('Continue with this browser key',async()=>{
      say('Proving this browser holds the key…');
      await proveKey('login',key);location.reload();
    },true));
    else body.append(button('Create a pseudonymous identity',async()=>{
      say('Creating a non-exportable key for this browser…');
      const created=await createKey();
      await proveKey('register',created); location.reload();
    },true));
    if (config.google_enabled) body.append(button('Continue with Google (optional)',()=>{
      location.assign('/api/identity/google/start');
    }));
    const caution = document.createElement('p');
    caution.className='identity-note';
    caution.textContent='Browser keys do not yet provide portable recovery. If you clear browser storage without another login, you can lose access to this identity.';
    body.append(caution);
  }
  body.append(button('No thanks — back to the Commons',()=>modal.close()));
}
export function openIdentity() {
  if (!modal) return;
  modal.showModal();
  void renderModal();
}
export function installIdentityUI() {
  if (document.getElementById('identityDialog')) return;
  modal=document.createElement('dialog');
  modal.id='identityDialog'; modal.className='identity-dialog';
  // Static markup only. No identity or provider data is injected as HTML.
  modal.innerHTML='<div class="identity-head"><span aria-hidden="true">⌁</span><button class="identity-close" type="button" aria-label="Close identity dialog">×</button></div><h2 tabindex="-1">Identity</h2><div class="identity-options"></div><p class="identity-notice" role="status" aria-live="polite"></p>';
  notice=modal.querySelector('.identity-notice');
  modal.querySelector('.identity-close').addEventListener('click',()=>modal.close());
  document.body.append(modal);
  const footer = document.querySelector('.branching-foot');
  if (footer) footer.append(button('Have an identity? Sign in',openIdentity));
  const nav=document.querySelector('.main-nav');
  if (nav) {
    const b=button(currentAccount?.authenticated ? 'My identity' : 'Sign in · optional',openIdentity);
    b.id='identityNavButton'; b.classList.add('identity-nav'); nav.append(b);
  }
}
