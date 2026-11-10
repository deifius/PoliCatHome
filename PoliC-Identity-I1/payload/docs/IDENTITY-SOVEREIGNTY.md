# Identity without captivity

**PoliC@home identity architecture · milestone I1 · November 2026**

> Identity is evidence, not authority. No PolyC without PoliC.

This project takes its **future ambition**, not a ready-made protocol, from **PURDAH** in Neal Stephenson's *Fall; or, Dodge in Hell*: *Personal Unseverable Registered Designator for Anonymous Holography*. The novel's idea of pseudonymous, verifiable authorship and an identity that cannot be severed by a platform is our point of departure. **This pilot does not implement Stephenson's complete PURDAH vision**, does not prove a participant is human, and does not bind a pseudonym to a legal person. Nor does it implement a distributed identity ledger. We intentionally distinguish what has been built from what is still a research agenda.

## The constitutional requirements

1. **Participation without identification.** Anyone can browse Bloom and inspect Featured Cats without signing in or loading Google code. Catnap continues to have its own enrollment and PoliC rules; identity login is not a prerequisite for its existing pilot path.
2. **Identity without captivity.** Local pseudonymous identity is a first-party account, not a Google email address. Google (when configured) is a removable way to authenticate. A Google-linked account can add an independent cryptographic key before unlinking Google.
3. **No authority laundering.** Having a session does not imply permission to run compute, choose a Cat on the contributor's behalf, change creator trust, submit/approve a Cat, mint credits, or obtain the operator token. Worker and creator signers remain cryptographically and semantically separate.
4. **User-directed disclosure.** We request no email, name, avatar, contacts, scopes beyond `openid`, or Google API access. We never publish account IDs or link public contribution receipts to accounts by default.
5. **No surprise third parties.** A first-party session probe on visiting the homepage is allowed; no Google scripts or network contact is made until someone explicitly chooses Google sign-in or linking.
6. **Portable design, honest limitations.** The account record can be exported as JSON now, but it is **not** a transportable login credential. Non-extractable browser keys in IndexedDB can be lost. Truly provider-independent recovery, key rotation, import/export, passkeys, federation, verifiable claims and cross-Commons portability are future milestones.
7. **Revocation with clarity.** Logging out invalidates a server-side session. Unlinking an identity provider removes that provider's login mapping without deleting the account. Neither operation substitutes for Catnap's Pause/Revoke or breaks leases automatically.
8. **Privacy by non-correlation.** A stable public ID used across unrelated Cats makes pseudonymity fragile. Do not copy the internal `plc_...` account ID, Google `sub`, or an account's primary public key into shared ledgers, public profiles, badges or audit logs. Implement per-project unlinkable attribution when the claim model is designed.
9. **Due process over reputation absolutism.** The eventual verifiable-contribution and reputation architecture must carry context, provenance, revocation, appeal and confidence; it must never silently turn into a universal social credit score.
10. **Separation of concern across Commons.** Operators can administer a Commons, not seize its participants' identities. Cryptographic claims should be portable to other coordinators without outsourcing the contributor's constitutional choices.

## What I1 actually implements

| Area | Implemented | Explicitly not implemented |
|---|---|---|
| Pseudonym | Random `plc_` identifier and editable alias, stored in the coordinator's SQLite | Globally portable DID or human identity proof |
| Independent key | Browser Web Crypto Ed25519 key with `extractable=false`; private key saved in IndexedDB; server stores public key | WebAuthn / passkey ceremonies, hardware-bound key validation, exportable recovery |
| Auth protocol | One-time, 180-second, domain- and purpose-separated signed challenge; fail-on-replay | Cross-coordinator identities or federated key rotation |
| Sessions | 7-day server-side expiring session, hash-only storage, HttpOnly SameSite=Lax cookie, Secure for HTTPS | Login overriding any PoliC or operator authority |
| Google | Optional Google OpenID Connect authorization-code login, PKCE S256, state cookie, nonce, RS256 ID-token signature and claim checks; `openid` scope only | Mandatory Google account, email-based linking, refresh-token storage, Google APIs |
| Preferences | Session-backed `workspace` / `bloom` landing preference; default workspace after sign-in | Syncing PoliC permissions, device trust or computational consent |
| Export | Account alias, internal ID, public keys, provider subject identifiers (authenticated caller only) | Portable credential/key backup or right-to-deletion automation |
| Controls | Sign in, create pseudonym, link an independent browser key, link/unlink Google, logout | Authenticated management of Cats or contributions |

All account identity tables are **separate** from `nodes`, worker bearer tokens, `cat_proposals`, jobs, creator signature trust, and financial ledgers, even while using the same SQLite database file and transactional lock.

## Trust boundaries and flow

```text
Anonymous Bloom / Featured Cats
         |
         | visitor deliberately opens "Sign in" (no compute)
         v
   Independent browser key ----> one-time signed challenge ----+
         |                                                      |
   Optional Google OpenID ----> code + PKCE + verified ID token -+---> random local PoliC account
                                                                       |
                                                       HttpOnly first-party session
                                                                       |
                                                        UI landing preference only
                                                                       |
                      +--------------------- NOTHING CONNECTS AUTOMATICALLY --------+
                      |                                                             |
         Contributor PoliC + enrollment                                Cat creator invitation + signed work
         + trusted signers + separate Start                            + operator approval + separate trust
                      |                                                             |
                   Catnap                                                          Catbox
```

**The key and the provider are authentication methods, not the identity itself.** The local `plc_` identifier is currently coordinator-scoped. Future signed, portable identity documents will need multiple controller keys and carefully defined recovery rules; never claim 'unseverable' until a cross-provider account recovery demonstration survives an operator failure.

### Server routes

- `GET /api/identity/config`, `GET /api/identity/me` — first-party metadata/session probe; no Google requests.
- `POST /api/identity/challenge` — `register`, `login`, `link-key` challenge issuance for a 32-byte Ed25519 public key.
- `POST /api/identity/prove` — consume challenge, verify signature, create/link identity, issue a new cookie on sign-in.
- `POST /api/identity/logout` — revoke only the current identity session.
- `PATCH /api/identity/preferences`, `PATCH /api/identity/alias` — account presentation; no worker state.
- `GET /api/identity/export` — authenticated account metadata JSON; **not** a wallet, signature or key backup.
- `GET /api/identity/google/start`, `GET /api/identity/google/callback` — optional Google OIDC login.
- `POST /api/identity/google/link/start`, `DELETE /api/identity/providers/google` — user-initiated linking and unlinking; cannot remove the last login method.

### Browser behavior and editorial tone

Bloom stays one question at a time, with a single discreet footer control: **Have an identity? Sign in**. The identity dialog offers an independent pseudonymous key, then Google only if the operator has configured it. Anonymous visitors are free to close the dialog. A returning authenticated account with `default_landing=workspace` goes directly to the existing detailed Catnap/Create a Cat application, even after a fresh browser session as long as the server session remains valid. The user can choose to see Bloom again from the identity dialog.

The cat may be dry; the credential choices must be literal. No automatic Google One Tap, no wall of login providers, no forced registration, and no computation as a side effect of sign-in.

## Data minimization and information flows

- **Server:** coordinator SQLite persists random account ID, alias, preference, public keys, hashes of session tokens, Google provider + stable Google `sub` (if linked), short-lived challenge and OAuth state, and hashed peer rate-limit entries. It does **not** persist raw session tokens, OAuth access/refresh tokens, Google email, profile name or photo.
- **Browser:** IndexedDB holds the non-extractable private CryptoKey. An ephemeral signature is sent over the same origin. The browser's HttpOnly identity cookie cannot be read by application JavaScript. **Non-extractable does not mean XSS-proof:** compromised same-origin JavaScript can still ask the CryptoKey to sign messages, so CSP, code review, and isolation from user-supplied code remain necessary. Legacy Bloom's optional cosmetic `localStorage` preference is separate and remains anonymous.
- **Google (if chosen):** receives an authentication request and may observe sign-in metadata; the server receives an ID token for the `openid` scope, verifies it, stores only `sub`, and discards the token. Google is not informed which Cats the participant trusts or works on.
- **Public output:** no account identifier, Google subject, key fingerprint, email, or project-specific activity is automatically published. Account export is an authenticated, private response marked no-store.
- **Threat-model limitation:** account operators who can query the SQLite file can still correlate linked providers with pseudonyms; network logs and usage timestamps may be revealing. This is pseudonymity, not anonymity against the Commons operator.

## Security boundaries and deployment

**Do not expose a development coordinator directly to the Internet.** Browser identity operations require HTTPS except for localhost / loopback (the FastAPI test host is also accepted for tests). Only configure trusted reverse-proxy forwarding and HTTPS at the public ingress. Do not enable `--insecure-http-on-lan` as a substitute for TLS. Session cookies use `__Host-` prefix, `Secure`, `HttpOnly`, `Path=/` on HTTPS; localhost uses an explicitly development-only name. Mutating JSON endpoints enforce `Origin` and JSON content type. Linking and unlinking authentication methods additionally require a freshly established session (within 10 minutes); sign out and back in to reauthenticate when prompted. Google links require both a first-party active session and explicit same-origin POST; the Google callback rechecks the initiating identity.

Google login uses fixed authorization/token/JWKS URLs; no user-supplied token endpoint. The callback checks state cookie and one-time server-side record, PKCE verifier, ID-token RS256 signature, issuer, audience, nonce, issued-at, expiry and unique `sub`. No implicit account merge from matching email addresses. Google sessions are application sessions, not Google access tokens. No Google code or third-party assets are loaded for anonymous visitors.

A small DB-level limit of 40 identity challenges per hour per directly connected peer slows accidental abuse; it is **not production bot protection**, and a reverse proxy may make multiple real visitors share an IP. For public deployment add ingress limits, alerting, abuse policy and data-retention jobs. Expired sessions, OAuth states and rate buckets need periodic maintenance; I1 cleans some rows opportunistically only. Protect SQLite backups and file permissions. Rotate signing/provider secrets with a documented maintenance procedure.

## Google configuration (opt-in)

Create a **Google Cloud OAuth 2.0 Web application** client and register exactly this URI for the public deployment:

`https://policathome.dafehughes.com/api/identity/google/callback`

Then configure the coordinator privately (never in Git):

```bash
export POLYC_GOOGLE_CLIENT_ID='YOUR_GOOGLE_WEB_CLIENT_ID'
export POLYC_GOOGLE_CLIENT_SECRET='YOUR_GOOGLE_WEB_CLIENT_SECRET'
export POLYC_GOOGLE_REDIRECT_URI='https://policathome.dafehughes.com/api/identity/google/callback'
```

If any of these three are absent, Google sign-in is not offered. To test independent identities locally, **none is required**. Configure the OAuth consent screen according to Google's requirements; this patch does not create a Google Cloud project or credentials. Google callback has *not* been exercised against Google's production endpoints; the tests mock a signed ID token and network exchange.

`POLYC_ADMIN_TOKEN` remains independently required to run the coordinator, and is never returned by any identity route. A Google account, valid identity cookie, or browser key **must never** authorize operator endpoints.

### Local walkthrough

```bash
cd ~/projects/PoliCatHome
source .venv/bin/activate
export POLYC_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"
polyc serve --db runtime/browser.sqlite --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/` in a fresh browser session; select **Have an identity? Sign in** → **Create a pseudonymous identity**. The new `Cat ...` persona should go directly to the workspace. Use **My identity** in the workspace to change the landing preference, export your identity record or sign out. In the same browser, the independent key can sign in again after logout. In another browser the key is not present; this is *not yet* portable recovery. A Google-only account should add an independent key before attempting to unlink Google.

Run:

```bash
node scripts/test-identity-ui.mjs
node scripts/test-branching-home.mjs
node scripts/test-featured-cats.mjs
python -m pytest -q
```

## Roadmap toward a genuinely PURDAH-like paradigm

| Milestone | Result required before advancing |
|---|---|
| **I1 — Private account and provider independence (this patch)** | Pseudonym + local signer + optional Google, separate permissions, first-party sessions, tested origin/replay/revocation |
| **I2 — Strong recoverable controller identity** | Standards-compliant WebAuthn/passkeys; hardware security keys; multiple device keys; key rotation, recovery policy and emergency session revoke; no reliance on one provider |
| **I3 — Portable author identity** | Signed identity document and controller change history, deterministic verification across independent Commons, clear loss-and-recovery semantics; evaluate DID Core and DID:key only where they fit |
| **I4 — Anonymous holography (authorship, not a single public profile)** | Project-scoped pseudonyms, verifiable signed contribution statements, selectively revealed attestations, unlinkable presentation trials, explicit retention and dispute rules |
| **I5 — Federated reputation and governance** | Cross-Commons claim transport and independent verification; revocation witnesses; appeals and non-coercive reputation rules; never one operator's universal ranking |
| **I6 — Severance adversary test** | Demonstrate recovery with original coordinator gone, Google inaccessible, and original device lost; independent evidence of attributable authorship survives without leaking unrelated projects |

Potential standards: W3C WebAuthn Level 3 (2026), W3C DID Core, W3C Verifiable Credentials Data Model v2, and NIST SP 800-63-4 (2025). Each requires its own threat model; do not declare compliance simply because the specification was consulted.

### Open architectural questions

- Who can witness a controller-key rotation when the original key is lost? How can abuse protection avoid rebuilding centralized gatekeeping?
- How do we preserve provable authorship while allowing right-to-forget, erasure of personal data, and consent withdrawal? **No immutable public personally identifying ledger by default.**
- Are creator and contributor reputations intentionally distinct? Should each Cat define its own trust context?
- Which trust attestations are portable, which are local to a Commons, and which should never be shared?
- How do anonymous contributors obtain due process without being forced to disclose legal identity?
- When, if ever, may the system legally require identity verification for real-money settlement? How is that compartmentalized?

## References

- Neal Stephenson, *Fall; or, Dodge in Hell* (2019), source of the PURDAH concept; this is an independently designed implementation direction, not an official adaptation or a claim of equivalence.
- [W3C Web Authentication Level 3, Recommendation 25 August 2026](https://www.w3.org/TR/2026/REC-webauthn-3-20260825/)
- [NIST Digital Identity Guidelines SP 800-63-4](https://pages.nist.gov/800-63-4/sp800-63.html)
- [Google: Verify ID tokens server-side](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token)
- [Google: OAuth 2.0 for web server applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [OWASP: Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet)
