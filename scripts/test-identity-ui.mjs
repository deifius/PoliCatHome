/* Invariant checks for optional identity UX. This is static contract validation;
 * authentication cryptography, cookies, OAuth and CSRF are exercised by pytest.
 */
import fs from 'node:fs';
import assert from 'node:assert/strict';
const read = path => fs.readFileSync(new URL('../'+path,import.meta.url),'utf8');
const html = read('polyc/web/index.html');
const entry = read('polyc/web/branching-home.js');
const ui = read('polyc/web/identity-ui.js');
const style=read('polyc/web/identity-ui.css');
const docs=read('docs/IDENTITY-SOVEREIGNTY.md');
assert.match(html,/identity-ui\.css/);
assert.match(entry,/import \{ identityMe, installIdentityUI \} from '\.\/identity-ui\.js'/);
assert.match(entry,/const identity = await identityMe\(\)/);
assert.match(entry,/identity\.identity\?\.default_landing === 'bloom'/);
assert.match(ui,/extractable|generateKey\(\{name:'Ed25519'\},false/);
assert.match(ui,/indexedDB\.open\(/);
assert.match(ui,/\/api\/identity\/challenge/);
assert.match(ui,/\/api\/identity\/prove/);
assert.match(ui,/\/api\/identity\/logout/);
assert.match(ui,/Have an identity\? Sign in/);
assert.match(ui,/Google \(optional\)/);
assert.doesNotMatch(html,/accounts\.google\.com|gsi\/client|googleapis\.com/);
assert.doesNotMatch(ui,/localStorage\.setItem|sessionStorage\.setItem/);
assert.doesNotMatch(ui,/\/api\/catnap\/(?:enroll|lease)|\/api\/workshop\/cats|\/api\/jobs/);
assert.match(style,/\.identity-dialog/);
assert.match(docs,/This pilot does not implement Stephenson's complete PURDAH vision/);
assert.match(docs,/Signing in cannot|does not imply permission/);
console.log('PURDAH I1: identity UX, optional providers, Bloom bypass and non-compute boundaries validated.');
