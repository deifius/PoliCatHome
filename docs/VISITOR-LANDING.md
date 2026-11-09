# Visitor-facing landing page

The landing page at `/` is written for a newcomer deciding whether to share their own computing resources, **not** for the Commons administrator. A separate operator panel remains available through the footer.

## Decision order

1. **Understand what is being offered.** A concise headline introduces the Commons and links directly to policy setup. Visiting, previewing and watching a visualization never start compute.
2. **Learn through three numbered explainer buttons.** What runs / What it uses / What it cannot do are three accessible tabs sharing one compact explanation area. The default tab introduces the PoliC policy rather than leading with SHA-256 jargon. Its extra disclosure explains the actual SHA-256 pilot. Resource explanations distinguish browser CPU use from future GPU/VRAM work, and the limitations tab links to local Docker Catbox and the optional screensaver. None imply that GPU work, dynamic arbitrary Catboxes, or enforceable browser limits exist today.
3. **Set a personal PoliC.** The main route keeps trusted Cats and CPU pacing in sight. The more detailed category, purpose, task timeout, session-duration and nickname settings are in an optional disclosure. All are editable before enrolling.
4. **Inspect, then enroll.** Preview and export cannot cause enrollment or compute. The visitor must check an explicit acknowledgment and then click **Enroll in Catnap**. Enrollment leaves the CPU idle.
5. **Start separately, and retain control.** An enrolled visitor sees separate **Start Catnap**, **Pause**, and **Revoke Consent** actions. The prominent status line distinguishes not enrolled, enrolled-but-idle, and started.

## Disclosure and accessibility rules

- The 1–2–3 explanatory tabs are buttons with `role=tab`, `aria-selected`, tab-panel relationships, and Arrow Left/Right/Home/End keyboard navigation. On mobile only the three compact headings are shown, with the explanation beneath. Native `<details>` / `<summary>` sections provide optional depth. Essential limitations are never hover-only.
- Contextual `?` explanations appear on hover or keyboard focus and also open on click/tap. Any safety-critical fact in a tooltip is also available in the visible overview or disclosures.
- Inline messages sit beside the action that produced them. No invitation, trusted creator, or enrollment is required to preview the draft PoliC.
- Language must preserve the distinction between **approved Cat** and **trusted creator**. Trusting a creator can permit that creator's future approved Cats, constrained by the rest of the PoliC.
- The Gibson and other visualizations live in a closed disclosure below the consent flow; the scene engine is not initialized until the visitor opens it. A synthetic scene cannot be mistaken for verified work.
- Alternatives link to guided native Catbox and Commons paths. A browser page cannot silently start local Docker.
- The payment FAQ should acknowledge the protocol’s aspiration for accountable mutual prosperity and separately disclose that the current browser SHA-256 pilot has **no implemented payment or economic matching**. Do not imply a guaranteed return, or that a Catbox already brokers compensation.

## Manual review checklist

- As a first-time visitor, select all three numbered explanations by mouse and keyboard. On narrow screens, confirm the three controls fit on one row with a readable active explanation. Find answers to *what runs, where, who chooses, what it costs, how to stop* without scrolling through graphics or administrator tools.
- Preview the PoliC without checking consent or selecting a Cat; ensure that no work starts.
- Leave Cats untrusted; enroll and start only after consent; verify that no task is leased until an approved creator is deliberately trusted.
- With an approved Cat and matching PoliC, verify local browser work, pause, revocation, and accurate status changes.
- Check keyboard navigation, hover/tap/focus explanations, expandable sections, 390px mobile width, reduced-motion preference, and that the scene starts only when its disclosure opens.
- Use real HTTPS or localhost for a production-like WebCrypto test. Backend tests and static UI previews alone do not prove browser execution or live Docker integration.

See [Browser Catnap](CATNAP-BROWSER.md) and [Consent and lifecycle](CONSENT-AND-LIFECYCLE.md) for behavior and operational details.
