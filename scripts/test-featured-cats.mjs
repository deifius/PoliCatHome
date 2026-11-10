import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

// Import browser ES module syntax without requiring a package-wide "type": "module".
const moduleSource = readFileSync(new URL('../polyc/web/featured-cats.js', import.meta.url), 'utf8');
const moduleUrl = `data:text/javascript;base64,${Buffer.from(moduleSource).toString('base64')}`;
const { validateFeaturedCatalog } = await import(moduleUrl);
const registry = JSON.parse(readFileSync(new URL('../polyc/web/featured-cats.json', import.meta.url), 'utf8'));

const featured = validateFeaturedCatalog(registry);
assert.ok(featured.length >= 1, 'Expected at least one featured Cat');
assert.ok(featured.some(cat => cat.stage === 'pilot'));
assert.ok(featured.every(cat => cat.name && cat.description && cat.contribution && cat.availability));
assert.ok(featured.every(cat => cat.stage !== 'concept' || /not available|concept only/i.test(cat.availability)));
assert.equal(validateFeaturedCatalog({schema_version: 1, cats: []}).length, 0);
assert.throws(() => validateFeaturedCatalog({schema_version: 2, cats: []}), /Unsupported/);
assert.throws(() => validateFeaturedCatalog({schema_version: 1, cats: [{...registry.cats[0]}, {...registry.cats[0]}]}), /duplicate/);
const injection = {...registry.cats[0], id: 'injection-test', repo_url: 'javascript:alert(1)', catbox_url: '//evil.example/evil', learn_url: 'http://example.com'};
const [clean] = validateFeaturedCatalog({schema_version: 1, cats: [injection]});
assert.equal(clean.repoUrl, null);
assert.equal(clean.catboxUrl, null);
assert.equal(clean.learnUrl, null);
const [safe] = validateFeaturedCatalog({schema_version: 1, cats: [{...injection, repo_url: 'https://github.com/deifius/PoliCatHome', catbox_url: '/web/participate.html#catbox'}]});
assert.ok(safe.repoUrl.startsWith('https://github.com/'));
assert.equal(safe.catboxUrl, '/web/participate.html#catbox');
const homepage = readFileSync(new URL('../polyc/web/index.html', import.meta.url), 'utf8');
for (const fragment of ['id="featured-cats"', '/web/featured-cats.css', '/web/featured-cats.js']) {
  assert.ok(homepage.includes(fragment), `Homepage integration missing: ${fragment}; run python3 scripts/activate-featured-cats.py --apply`);
}
console.log(`Featured Cats registry: ${featured.length} entries validated; unsafe links rejected.`);
