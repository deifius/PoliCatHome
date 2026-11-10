/* PoliC@home Bloom: a non-computing welcome and an optional local preference.
 * The detailed app is the only place where a user can enroll or start Catnap.
 * A remembered workspace choice is NOT authentication, trust, or consent.
 */
import { validateFeaturedCatalog } from './featured-cats.js';
import { BLOOM_STAGES, storyFor } from './branching-story.mjs';

const $ = id => document.getElementById(id);
const home = $('branchingHome');
const stages = new Set(BLOOM_STAGES);
const PREFERENCE_KEY = 'polyc.home.start.v1';
const PREFERENCE_WORKSPACE = 'workspace';
let current = 'welcome';
let cats = null;
let position = 0;
let loading = false;
let preferenceButton = null;
let shortcutButton = null;

function preferredWorkspace() {
  try { return localStorage.getItem(PREFERENCE_KEY) === PREFERENCE_WORKSPACE; }
  catch { return false; }
}
function rememberWorkspace(yes) {
  try {
    if (yes) localStorage.setItem(PREFERENCE_KEY, PREFERENCE_WORKSPACE);
    else localStorage.removeItem(PREFERENCE_KEY);
    return true;
  } catch { return false; }
}
function updatePreferenceLabel() {
  if (!preferenceButton) return;
  const on = preferredWorkspace();
  preferenceButton.textContent = on ? 'Show welcome next visit' : 'Skip welcome next visit';
  preferenceButton.setAttribute('aria-pressed', String(on));
  preferenceButton.title = 'Changes only this browser’s starting screen. It never changes PoliC or Catnap consent.';
}
function installPreferenceControls() {
  const nav = document.querySelector('.main-nav');
  if (nav && !document.getElementById('branchingPreferenceButton')) {
    preferenceButton = document.createElement('button');
    preferenceButton.type = 'button';
    preferenceButton.id = 'branchingPreferenceButton';
    preferenceButton.className = 'branching-preference-button';
    preferenceButton.addEventListener('click', () => {
      rememberWorkspace(!preferredWorkspace());
      updatePreferenceLabel();
    });
    nav.append(preferenceButton);
  } else {
    preferenceButton = $('branchingPreferenceButton');
  }
  updatePreferenceLabel();

  if (!home) return;
  const footer = home.querySelector('.branching-foot');
  if (footer && !$('branchingWorkspaceShortcut')) {
    shortcutButton = document.createElement('button');
    shortcutButton.id = 'branchingWorkspaceShortcut';
    shortcutButton.type = 'button';
    shortcutButton.className = 'branching-home-link branching-workspace-shortcut';
    shortcutButton.textContent = 'Always open workspace here →';
    shortcutButton.title = 'Open the detailed workspace now and skip this welcome on later visits in this browser.';
    shortcutButton.addEventListener('click', () => go('remember-workspace'));
    footer.insertBefore(shortcutButton, footer.querySelector('a[href="/web/participate.html"]'));
  } else shortcutButton = $('branchingWorkspaceShortcut');
}

function choice(label, action, primary = false) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'branching-choice' + (primary ? ' is-primary' : '');
  button.dataset.branchAction = action;
  button.textContent = label;
  return button;
}
function setCopy({ kicker = '', title, description = '', status = '', actions = [], extraLink = null }) {
  $('branchingKicker').textContent = kicker;
  $('branchingTitle').textContent = title;
  $('branchingDescription').textContent = description;
  $('branchingDescription').hidden = !description;
  $('branchingStatus').textContent = status;
  $('branchingStatus').hidden = !status;
  $('branchingChoices').replaceChildren(...actions.map(([name, action, primary]) => choice(name, action, primary)));
  const extra = $('branchingExtra');
  extra.replaceChildren();
  if (extraLink) {
    const a = document.createElement('a');
    a.textContent = extraLink.label;
    a.href = extraLink.href;
    if (/^https:\/\//.test(a.href)) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
    extra.append(a);
  }
  $('branchingHomeButton').hidden = current === 'welcome';
  if (shortcutButton) shortcutButton.hidden = current !== 'welcome';
  const content = $('branchingContent');
  content.classList.remove('blooming');
  // Only animate after explicit navigation, and never against reduced motion.
  void content.offsetWidth;
  content.classList.add('blooming');
  $('branchingTitle').focus({ preventScroll: true });
}
function render() {
  if (!home || home.hidden) return;
  setCopy(storyFor(current, { cat: cats?.[position] ?? null,
    index: position, total: cats?.length || 0, loading }));
}
async function loadCats() {
  if (loading) return;
  loading = true;
  render();
  try {
    const response = await fetch('/web/featured-cats.json', { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) throw new Error('Registry unavailable');
    cats = validateFeaturedCatalog(await response.json());
  } catch (error) {
    cats = null;
    console.warn('Featured Cats exploration unavailable:', error);
  } finally {
    loading = false;
    if (current === 'explore') render();
  }
}
function openApp(target) {
  // No consent, trusted creator selection, enrollment or work happens here.
  home.hidden = true;
  document.documentElement.classList.remove('branching-active');
  const tab = document.querySelector(`.main-nav [data-panel="${target === 'create' ? 'createPanel' : 'catnapPanel'}"]`);
  tab?.click();
  const destination = $(target === 'create' ? 'createPanel' : 'contribute');
  destination?.scrollIntoView({ block: 'start', behavior: 'instant' });
  const heading = destination?.querySelector('h2, h1, legend');
  heading?.setAttribute('tabindex', '-1');
  heading?.focus({ preventScroll: true });
  updatePreferenceLabel();
}
function go(action) {
  switch (action) {
    case 'next-cat':
      if (cats?.length) position = (position + 1) % cats.length;
      current = 'explore'; break;
    case 'retry':
      cats = null;
      current = 'explore';
      void loadCats(); return;
    case 'enter-catnap': openApp('catnap'); return;
    case 'enter-create': openApp('create'); return;
    case 'remember-workspace':
      rememberWorkspace(true);
      openApp('catnap'); return;
    default:
      if (!stages.has(action)) return;
      current = action;
  }
  if (current === 'explore' && !cats) void loadCats();
  else render();
}
function hasEnrolledSession() {
  try {
    const saved = JSON.parse(sessionStorage.getItem('polyc.catnap.node.v1'));
    return Boolean(saved?.node_id && saved?.token);
  } catch { return false; }
}
function shouldShowHome() {
  // Deep links and enrolled sessions take priority over cosmetic preferences so
  // users can always reach operational pause/revoke controls immediately.
  try {
    if (location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)))) return false;
  } catch { /* A malformed hash should not break the public invitation. */ }
  return !hasEnrolledSession() && !preferredWorkspace();
}
function init() {
  installPreferenceControls();
  if (!home || !shouldShowHome()) return;
  home.hidden = false;
  document.documentElement.classList.add('branching-active');
  home.addEventListener('click', event => {
    const button = event.target.closest('button[data-branch-action]');
    if (button) go(button.dataset.branchAction);
  });
  $('branchingHomeButton').addEventListener('click', () => go('welcome'));
  render();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
else init();
