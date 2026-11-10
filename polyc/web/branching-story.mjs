/* Original PoliC@home Bloom dialogue. Kept separate from the DOM so the
 * narrative, available choices and truthful capability claims can be tested.
 * This is presentation copy, never a source of runtime authorization.
 */
export const BLOOM_STAGES = Object.freeze([
  'welcome', 'explore', 'cat-detail', 'offer', 'offer-resources',
  'offer-consent', 'create', 'create-scope',
]);

const action = (label, target, primary = false) => [label, target, primary];

export function storyFor(stage, { cat = null, index = 0, total = 0, loading = false } = {}) {
  switch (stage) {
    case 'welcome':
      return {
        kicker: 'PoliC@home · the computing commons',
        title: 'What brings you here?',
        description: 'People share spare computing power with projects they choose. The cat is here to supervise. It has no qualifications.',
        actions: [
          action('Meet the Cats', 'explore', true),
          action('Offer my computer', 'offer'),
          action('Propose a project', 'create'),
        ],
      };
    case 'offer':
      return {
        kicker: 'Catnap · contribute computing power',
        title: 'Shall we borrow a little computing time?',
        description: 'Only for approved Cats you permit, and only when you press Start. The cat recommends reading the terms. Uncharacteristically sensible.',
        actions: [
          action('What will it use?', 'offer-resources'),
          action('Who decides what runs?', 'offer-consent'),
          action('Review Catnap controls', 'enter-catnap', true),
        ],
      };
    case 'offer-resources':
      return {
        kicker: 'What your computer contributes',
        title: 'There will be some heat.',
        description: 'Today Catnap uses browser CPU time, not GPU compute. It uses electricity and may warm your machine. The pacing slider is a preference, not a hardware safety limit.',
        actions: [
          action('Who decides what runs?', 'offer-consent'),
          action('Review Catnap controls', 'enter-catnap', true),
          action('Back', 'offer'),
        ],
      };
    case 'offer-consent':
      return {
        kicker: 'Your machine · your permission',
        title: 'Your permission is specific.',
        description: 'You choose which creators to trust; that trust can cover their future approved Cats. Enrolling and pressing Start are separate decisions. You can pause or revoke.',
        status: 'Today: approved, matching SHA-256 browser CPU tasks only.',
        actions: [
          action('What resources does it use?', 'offer-resources'),
          action('Review Catnap controls', 'enter-catnap', true),
          action('Back', 'offer'),
        ],
      };
    case 'create':
      return {
        kicker: 'Create a Cat · propose a project',
        title: 'Have a problem worth computing?',
        description: 'In this Commons, a Cat is a project; a Catbox is where its work would run. A name like “Mittens” is optional.',
        actions: [
          action('What can I submit today?', 'create-scope'),
          action('Open the workshop', 'enter-create', true),
          action('Meet example Cats', 'explore'),
        ],
      };
    case 'create-scope':
      return {
        kicker: 'What the pilot supports',
        title: 'For now, small Cats only.',
        description: 'The workshop creates signed proposals for bounded SHA-256 pilot tasks. An operator must approve them. Running arbitrary containers or GPU jobs comes later.',
        actions: [
          action('Open the workshop', 'enter-create', true),
          action('Back to project idea', 'create'),
          action('Meet example Cats', 'explore'),
        ],
      };
    case 'explore':
    case 'cat-detail': {
      if (!cat) {
        return loading ? {
          kicker: 'Meet the Cats',
          title: 'Looking for the Cats…',
          description: 'The catalog is loading. No computing has started.',
          actions: [action('Start over', 'welcome')],
        } : {
          kicker: 'Meet the Cats',
          title: 'The catalog is unavailable.',
          description: 'The cat offers no explanation. You can try again, or learn how Catnap works.',
          actions: [
            action('Try again', 'retry', true),
            action('How does Catnap work?', 'offer'),
            action('Start over', 'welcome'),
          ],
        };
      }
      const concept = cat.stage === 'concept';
      const status = concept
        ? 'Concept only · this Cat cannot run in Catnap today.'
        : 'Pilot example · running requires approval, eligibility and your PoliC.';
      if (stage === 'explore') {
        return {
          kicker: `Cat ${index + 1} of ${total} · ${cat.category}`,
          title: cat.name,
          description: cat.tagline,
          status,
          actions: [
            action('What would my computer do?', 'cat-detail', true),
            action('Next Cat', 'next-cat'),
            action('Back to choices', 'welcome'),
          ],
        };
      }
      return {
        kicker: `Behind this Cat · ${cat.category}`,
        title: 'What is the actual work?',
        description: cat.contribution,
        status,
        actions: concept ? [
          action('Next Cat', 'next-cat', true),
          action('Back to this Cat', 'explore'),
          action('How does Catnap work?', 'offer'),
        ] : [
          action('How could I contribute?', 'offer', true),
          action('Next Cat', 'next-cat'),
          action('Back to this Cat', 'explore'),
        ],
        extraLink: cat.repoUrl ? { label: 'Inspect the source ↗', href: cat.repoUrl } : null,
      };
    }
    default:
      throw new Error(`Unknown Bloom stage: ${stage}`);
  }
}
