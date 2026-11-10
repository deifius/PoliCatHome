# Bloom landing: PoliC@home first-visit exploration

The first page intentionally behaves more like Google.com or a short choose-your-own-adventure than like a dashboard. It asks **one question at a time**, gives three choices, and uses a small, editable inline-SVG spline cat. The unmodified operational app remains accessible by intent, by deep link, and to already enrolled Catnap contributors.

## Install after Featured Cats v2

```bash
python3 scripts/activate-featured-cats.py --check
python3 scripts/activate-branching-home.py --check
python3 scripts/activate-branching-home.py --apply
node scripts/test-featured-cats.mjs
node scripts/test-branching-home.mjs
```

The installer is deliberately idempotent. It inserts markup at `<body>` and CSS/JS imports in `<head>` instead of patching a changing `index.html` hunk. It fails safely if Featured Cats v2 isn't integrated. Commit **the resulting `polyc/web/index.html` diff** as well as the new files.

## Interaction and content architecture

- **Arrival:** `What brings you here?` → `Explore Cats`, `Offer compute`, or `Create a Cat`. This page fills the viewport on ordinary desktop and mobile sizes; no masthead navigation, grid or consent form is visible.
- **Explore:** load `featured-cats.json` only after this choice; display one Cat at a time with a single sentence and a truthful `Pilot example`/`Concept only` status. `What would I do?` presents the next layer of explanation. `Next Cat` cycles the curated collection. Only the detail layer presents a source-repository link if it exists.
- **Offer:** a short ownership statement → optional one-screen consent explanation → explicit `Set my PoliC` opens the preexisting Catnap form. No trusted keys are selected, no consent box is checked, and no enrollment occurs.
- **Create:** a short introduction → `Open the workshop` opens the existing invited Create a Cat panel.
- **How it works** remains one quiet link to the complete, existing installation and lifecycle guide.

The gallery is **editorial**, not an execution catalog. `featured-cats.json` is not used to approve work, trust a creator, lease a task, authorize a worker or launch a Catbox. Concept Cats are labeled as not runnable. The browser pilot supports approved, matching SHA-256 work only. Creator-key trust in the existing consent UI can cover future approved Cats from that key; the full disclosure remains within the form.

## Intentional scope boundary

The **exploration** is viewport-bound and does not scroll under normal screen dimensions. Once visitors explicitly enter `Set my PoliC` or `Open the workshop`, the existing long and legally important form is visible and **can scroll**. A future phase can convert those forms into validated steps, but must never remove or compress disclosures merely to satisfy a no-scroll goal. At extreme text zoom or landscape phones, scrolling is allowed rather than clipping essential choices.

If JavaScript fails, the original app still renders, because the branching invitation begins with `hidden` and only hides `.app-shell` after successful initialization. Existing hash/deep links and previously enrolled session visitors skip the invitation so operational pause/revoke controls aren't obscured. Returning to the homepage from the operational app reloads it, invoking the existing `pagehide` stop logic.

### Accessibility

- Native buttons and links, a real `h1`, keyboard focus moved to the newly revealed question, visible focus rings, and restrained text.
- No color-only distinction for pilot versus future concept. Screen reader reads the stage status as ordinary text. Decorative SVG is hidden from accessibility tree.
- `prefers-reduced-motion` disables bloom and cat animations.
- At very short viewport heights or extreme text zoom, content can scroll instead of clipping; no absolute requirement should override readability or controls.

### Quick manual test

1. Visit `/`: see **only** the brand, spline cat, one question, three options, and a tiny non-compute assurance. Ensure no vertical scrollbar at typical 1440×900, 390×844, and 375×667 viewports.
2. `Explore Cats`: cycle 3 entries and check that the two concept Cats say **not available**. Inspect the repository link only in the pilot detail view.
3. `Offer compute` → `How is consent protected?` → `Set my PoliC`. Ensure the full form still appears and no CPU work began.
4. `Create a Cat` → `Open the workshop`. Verify original creator inputs still work; no arbitrary Catbox execution is implied.
5. Test browser hash `/#contribute`, previously enrolled browser session, keyboard Tab/Enter, reduced-motion, 200% text zoom and a blocked/unavailable JSON registry.

## Bloom v4: conversational wit and remembering this browser

Bloom v4 replaces the generic welcome and shallow branches with a tested story graph
in `polyc/web/branching-story.mjs`. The voice is dry and lightly feline, but button
labels remain literal, brief, and independently understandable. The three paths:

- **Meet the Cats:** one project, then what work it would do, with a constant
  pilot-vs-concept distinction and no suggestion that concept Cats can run.
- **Offer my computer:** resource disclosure and creator trust are two independent
  paths. Both lead to the unmodified detailed Catnap controls; neither enrolls,
  selects a creator, or starts computation.
- **Propose a project:** definitions and pilot-only proposal limitations precede
  the existing gated workshop.

The intro footer now offers **Always open workspace here**. Clicking that button
opens the existing detailed app immediately and saves a browser-local preference
under `polyc.home.start.v1`. The dense workspace has an accessible toggle:
**Skip welcome next visit / Show welcome next visit**. The preference is
*not* a login, not synchronized across devices and **never** stores PoliC consent
or invokes a compute API. A known enrolled browser session or an explicit hash
link continues to bypass Bloom, regardless of the preference. Clearing local
browser storage resets the preference. If storage is unavailable, browsing
continues and the preference simply cannot persist.

Do not silently enroll someone because they skipped the introduction. Do not
introduce Google authentication merely to control this cosmetic preference.
If account identity later becomes valuable, use optional OIDC with verified
server sessions and keep project-specific PoliC consent separate. A federated
identity must never be treated as a creator signer key or a Catnap authorization.

Run `node scripts/test-branching-home.mjs` to validate the narrative graph,
interaction boundaries and preference controls. No new HTML activation is needed
when upgrading from v3: the v4 entry point reuses the existing Bloom markup.
