import assert from 'node:assert/strict';
import { BLOOM_STAGES, storyFor } from '../polyc/web/branching-story.mjs';
import { readFileSync } from 'node:fs';

const catalog = JSON.parse(readFileSync(new URL('../polyc/web/featured-cats.json', import.meta.url), 'utf8'));
const pilot = catalog.cats.find(cat => cat.stage === 'pilot');
const concept = catalog.cats.find(cat => cat.stage === 'concept');
assert.ok(pilot && concept, 'Requires pilot and concept examples');
const terminal = new Set(['enter-catnap', 'enter-create', 'next-cat', 'retry']);
for (const stage of BLOOM_STAGES) {
  const stories = stage === 'explore' || stage === 'cat-detail'
    ? [storyFor(stage, { cat: pilot, total: 3 }), storyFor(stage, { cat: concept, index: 1, total: 3 })]
    : [storyFor(stage)];
  for (const story of stories) {
    assert.ok(story.title && story.kicker && story.description, `${stage}: readable structure`);
    assert.ok(story.actions.length >= 2 && story.actions.length <= 3, `${stage}: at most 3 meaningful choices`);
    assert.ok(story.description.length <= 205, `${stage}: one brief paragraph`);
    for (const [label, target] of story.actions) {
      assert.ok(label.length >= 3 && label.length <= 32, `${stage}: comprehensible button label ${label}`);
      assert.ok(BLOOM_STAGES.includes(target) || terminal.has(target), `${stage}: unknown target ${target}`);
    }
  }
}
for (const stage of ['offer', 'create']) {
  assert.ok(storyFor('welcome').actions.some((a) => a[1] === stage), `Welcome reaches ${stage}`);
}
const conceptView = storyFor('explore', { cat: concept, index: 1, total: 3 });
assert.match(conceptView.status, /Concept only.*cannot run/);
assert.doesNotMatch(JSON.stringify(storyFor('cat-detail', { cat: concept })), /enter-catnap|Run this Cat|Start Catnap/);
const pilotView = storyFor('cat-detail', { cat: pilot });
assert.match(pilotView.status, /requires approval, eligibility and your PoliC/);
assert.match(storyFor('offer-consent').description, /future approved Cats/);
assert.match(storyFor('offer-consent').description, /Enrolling and pressing Start are separate/);
assert.match(storyFor('offer-resources').description, /electricity.*hardware safety limit/);
assert.match(storyFor('create-scope').description, /operator must approve/);
for (const stage of ['explore', 'cat-detail']) {
  for (const loading of [true, false]) {
    const result = storyFor(stage, { loading });
    assert.ok(result.actions.length, `${stage}: loading/error state has an exit`);
  }
}
console.log('Bloom v4 story: all branches, capability boundaries, failure states and choices validated.');
