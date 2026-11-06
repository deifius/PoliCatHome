// Verify JS's canonical manifest and Ed25519 signature format against Python's protocol.
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { canonical, hex, digest, verifySignedCat } from '../polyc/web/protocol.js';
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const project={project_id:'web-cat-test',title:'Web Cat Test',source_repo:'https://example.org/repo',
  source_commit:'a'.repeat(40),category:'open_science',purposes:['open_knowledge'],commercial:false,
  contributor_allowlist:[],contributor_denylist:[],work:{kind:'sha256_chain_v1',tasks:3,iterations:100,seed:'cat'}};
const pair=await crypto.subtle.generateKey({name:'Ed25519'},false,['sign','verify']);
const pub=hex(await crypto.subtle.exportKey('raw',pair.publicKey));
const signature=hex(await crypto.subtle.sign('Ed25519',pair.privateKey,new TextEncoder().encode(canonical(project))));
const sp={project,signer_pubkey:pub,signature};
assert(await verifySignedCat(sp,[pub]));assert(!await verifySignedCat(sp,[]));
assert(!(await verifySignedCat({...sp,project:{...project,commercial:true}},[pub])));
assert.match(await digest(project),/^[a-f0-9]{64}$/);
writeFileSync('/tmp/polic-js-signed.json',JSON.stringify(sp));
console.log('Browser project signing and verification passed.');
