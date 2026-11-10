# Featured Cats: editorial project discovery

## Integrate or update the homepage

The registry, CSS, and renderer are additive files. To avoid brittle patches against an evolving `index.html`, a one-time integration command adds the section and asset imports using the existing `before-you-decide` section as an anchor:

```bash
python3 scripts/activate-featured-cats.py --check
python3 scripts/activate-featured-cats.py --apply
node scripts/test-featured-cats.mjs
```

It is idempotent, keeps unfamiliar hero copy intact, and never touches consent-related Javascript or API code. Commit the resulting `polyc/web/index.html` change along with the new files. If your page no longer includes `before-you-decide`, inspect the HTML and adjust the integration instead of forcing a patch.

The homepage's **Meet the Cats** gallery reads `polyc/web/featured-cats.json` from the same origin (`/web/featured-cats.json`). This is a **curated presentation file**, not an execution catalog. It works before login, invites, enrollment, or a Catnap session. Its purpose is to explain what people might choose to support before asking them to configure consent.

## Add a featured Cat

1. Add an object to the `cats` array in `polyc/web/featured-cats.json` and set `featured: true`.
2. Use a unique lowercase-hyphenated `id` and short plain-language `name`, `tagline`, `description`, and `contribution` text. Explain a concrete user-visible outcome.
3. Supply `category`, `runtime`, `availability` and `review` text. Choose `stage: "pilot"` only for a currently implemented capability, **not** to imply the project is approved or matched; use `stage: "concept"` for speculative projects.
4. Add `repo_url` for a public HTTPS repository or homepage, plus optional `source_ref` (commit or tag), `catbox_url` and `learn_url`. On-site links must be absolute paths beginning with `/`; external links must be HTTPS. You may leave an unknown link as `null`; do not invent repositories.
5. Run `node scripts/test-featured-cats.mjs` and the regular project test suite. Review the copy and links in a pull request. Publish the changed static site.

Example entry:

```json
{
  "id": "example-bounded-research",
  "name": "Example bounded research",
  "tagline": "An understandable one-line reason this project matters.",
  "description": "What the project hopes to learn or create and why this is useful.",
  "contribution": "What a volunteer would actually contribute, and any real limitations.",
  "category": "Open research",
  "stage": "concept",
  "runtime": "Future Catbox",
  "availability": "Concept only — not available for Catnap",
  "review": "Illustrative; not submitted or approved",
  "repo_url": null,
  "catbox_url": null,
  "learn_url": null,
  "source_ref": null,
  "featured": true
}
```

## Trust boundary: featured is not trusted

**Never** let any registry field enroll a user, trust a signer, trigger a work lease, approve a Cat, download remote code, or execute a Catbox. The actual approved/eligible Cats remain available from the coordinator's `/api/catnap/catalog` endpoint and continue to require independent operator approval, compatible policies, and contributor trust. Trust in a creator key in the current pilot also covers future approved Cats from that creator; make that scope clear in the separate consent flow.

The public gallery fetches JSON only and renders text via DOM `textContent`, not as HTML. It does not fetch arbitrary repository manifests. Repository URLs are **links for inspection**, not workload sources. A versioned commit `source_ref` is informational unless the coordinator independently verifies it. This intentionally avoids turning an easy-to-edit marketing file into an execution or authorization path.

## States and honesty

- `pilot` = a documented, implemented *workflow/capability* exists; this does **not** mean a Cat is approved, available now, or eligible for your constitution.
- `concept` = illustration of a future possibility; it cannot currently run through this browser pilot.
- The current browser pilot is **bounded SHA-256 work in a Web Worker**, not general Docker/OCI execution or GPU compute.
- Gallery errors should not block the consent editor. Invalid entries are rejected and the UI displays a friendly unavailable message.
- Browser Catnap remains off until the existing explicit enrollment **and** start decisions are taken. The gallery itself performs no compute.

## Next iterations

Once approved Cats have public metadata, a server-side process may build the editorial registry from reviewed GitHub repository pointers and metadata. Keep a separate editorial allowlist and approval pipeline, and retain the coordinator's signed, independently enforced approval and policy gates. A future project-detail view can include activity receipts and reviewed Catbox manifests without automatically trusting their contents.
