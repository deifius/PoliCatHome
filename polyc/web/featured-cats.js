/* Public, editorial Featured Cats registry. Not a coordinator catalog or consent input. */
const CATALOG_PATH = '/web/featured-cats.json';
const STAGES = new Set(['pilot', 'concept']);
const MAX_CATS = 48;

function boundedString(value, max = 600) {
  return typeof value === 'string' ? value.trim().slice(0, max) : '';
}

function safeCatalogLink(value) {
  if (typeof value !== 'string' || value.length > 2048) return null;
  // Only reviewed on-site paths and HTTPS destinations may appear in the gallery.
  if (/^\/(?!\/)[a-zA-Z0-9/_#.?=&%-]*$/.test(value)) return value;
  try {
    const url = new URL(value);
    if (url.protocol === 'https:' && !url.username && !url.password) return url.href;
  } catch { /* Ignore invalid links. */ }
  return null;
}

/**
 * Validate and normalize a human-curated editorial registry.  Deliberately does
 * not interpret approval, signer trust, authorization, or executable manifests.
 */
export function validateFeaturedCatalog(input) {
  if (!input || input.schema_version !== 1 || !Array.isArray(input.cats) || input.cats.length > MAX_CATS) {
    throw new Error('Unsupported Featured Cats registry format');
  }
  const seen = new Set();
  const cats = [];
  for (const item of input.cats) {
    if (!item || item.featured !== true) continue;
    const id = boundedString(item.id, 80);
    const name = boundedString(item.name, 100);
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id) || !name || !STAGES.has(item.stage) || seen.has(id)) {
      throw new Error('Invalid or duplicate Featured Cat entry');
    }
    seen.add(id);
    cats.push({
      id,
      name,
      tagline: boundedString(item.tagline, 220),
      description: boundedString(item.description, 900),
      contribution: boundedString(item.contribution, 700),
      category: boundedString(item.category, 80),
      stage: item.stage,
      runtime: boundedString(item.runtime, 60),
      availability: boundedString(item.availability, 180),
      review: boundedString(item.review, 180),
      repoUrl: safeCatalogLink(item.repo_url),
      catboxUrl: safeCatalogLink(item.catbox_url),
      learnUrl: safeCatalogLink(item.learn_url),
      sourceRef: boundedString(item.source_ref, 100)
    });
  }
  return cats;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function link(label, href) {
  if (!href) return null;
  const a = element('a', 'featured-cat-link', label);
  a.href = href;
  if (/^https:\/\//.test(href)) {
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
  }
  return a;
}

function card(cat) {
  const article = element('article', 'featured-cat-card');
  article.dataset.stage = cat.stage;
  article.setAttribute('aria-labelledby', `featured-${cat.id}`);
  const header = element('div', 'featured-cat-card-head');
  const mark = element('span', 'featured-cat-mark', cat.stage === 'pilot' ? '◈' : '✧');
  mark.setAttribute('aria-hidden', 'true');
  const badge = element('span', `featured-stage featured-stage-${cat.stage}`, cat.stage === 'pilot' ? 'PILOT WORKFLOW' : 'FUTURE CONCEPT');
  header.append(mark, badge);
  const title = element('h3', '', cat.name);
  title.id = `featured-${cat.id}`;
  const tagline = element('p', 'featured-cat-tagline', cat.tagline);
  const meta = element('p', 'featured-cat-meta', `${cat.category} · ${cat.runtime}`);
  const details = element('details', 'featured-cat-details');
  details.append(element('summary', '', 'What would my contribution do?'));
  details.append(element('p', '', cat.description));
  details.append(element('p', '', cat.contribution));
  const terms = element('p', 'featured-cat-availability', cat.availability);
  const review = element('p', 'featured-cat-review', cat.review);
  const actions = element('div', 'featured-cat-links');
  for (const [label, href] of [['Source repository', cat.repoUrl], ['Catbox information', cat.catboxUrl], ['Learn more', cat.learnUrl]]) {
    const a = link(label, href);
    if (a) actions.append(a);
  }
  article.append(header, title, tagline, meta, details, terms, review, actions);
  return article;
}

export async function initializeFeaturedCats({ fetchCatalog = fetch } = {}) {
  const grid = document.getElementById('featuredCatsGrid');
  const status = document.getElementById('featuredCatsStatus');
  const filters = [...document.querySelectorAll('[data-featured-filter]')];
  if (!grid || !status) return;
  try {
    const response = await fetchCatalog(CATALOG_PATH, { credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const cats = validateFeaturedCatalog(await response.json());
    grid.replaceChildren(...cats.map(card));
    status.textContent = cats.length ? `${cats.length} featured Cats. Exploring never starts computation.` : 'No featured Cats have been published yet.';
    for (const filter of filters) {
      filter.addEventListener('click', () => {
        const selected = filter.dataset.featuredFilter;
        for (const button of filters) button.setAttribute('aria-pressed', String(button === filter));
        let visible = 0;
        for (const item of grid.children) {
          item.hidden = selected !== 'all' && item.dataset.stage !== selected;
          if (!item.hidden) visible++;
        }
        status.textContent = `${visible} ${selected === 'all' ? 'featured' : selected} Cat${visible === 1 ? '' : 's'} shown. Browsing does not enroll or start Catnap.`;
      });
    }
  } catch (error) {
    grid.replaceChildren();
    status.textContent = 'The featured collection is unavailable. You can still review the Catnap policy and approved projects below.';
    console.warn('Featured Cats registry unavailable', error);
    for (const filter of filters) filter.disabled = true;
  }
}

if (typeof document !== 'undefined') {
  // The script is loaded from the document head; defer until DOM nodes exist.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { void initializeFeaturedCats(); }, { once: true });
  } else {
    void initializeFeaturedCats();
  }
}
