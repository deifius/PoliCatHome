# Validation record — CPU pilot, test-credit exchange and v0.4 browser extension

Verified locally on Linux / Python 3.13 with available dependencies at preparation time.

- `pytest -q`: **40 passed** (current local run, including economic tests).
- `python -m polyc.demo --timeout 35`: **25 / 25** deterministic tasks complete with five distinct contributors.
- Contributions: `cat-1`, `cat-2`, `cat-3`, `cat-4`, and `cat-5`: **5 verified tasks each**.
- Built-in task kinds tested: `sha256_chain_v1` only.
- New project submission tested: signed `project.yaml` + `polic.yaml` validation, rejection of mutable OCI tags, mismatched revisions, signature tampering, incompatible economics, prohibited host networking, staged coordinator registration, duplicate revision, and mutual policy preview. **No container executed.**
- Contribution receipt tests: provisional points, authorization and hash-chain tampering.
- Test-only financial ledger: issuer supply limit, explicit wallet enrollment, proof of owner key, signed two-party transfer, replay and cross-coordinator rejection, overspend rejection, atomic simultaneous double-spend protection, funded-job refusal when budget is absent, verified task settlement, partial cancel refund, ledger tamper detection, schema refusal of cash conversion, disabled provider catalogue.
- `python -m polyc.economy_demo`: five distinct contributor identities + one project wallet, 25 verified volunteer tasks, 25 noncash test credits issued, 5 signed transfers to project, 5 further verified credit-priced tasks, 5 credit units settled, balances and local ledger verified. **No external payments.**
- The coordinator recomputes expected digests before recording results.
- Tested on **one physical/container Linux host** with five independently configured worker agents; not five separate homes.
- Tested a process runner with resource limits, not a virtual machine or untrusted-code isolation.
- v0.4 additions covered by tests: one-use browser invitation tokens, expiry/use rejection, browser enrollment with explicit trusted Ed25519 signer and hardware-policy refusal, consent-scoped real node/Chronicle telemetry, staged signed Cat proposals, operator approval/rejection and duplicate refusal, five browser-token enrollments, JS Web Crypto signer -> Python signed protocol -> real leased and independently verified result.
- `node scripts/test-browser-worker.mjs`: independent SHA-256 digest reference and 10,000-iteration bound tested using the actual browser worker logic under Node.js Web Crypto.
- `node scripts/test-browser-protocol.mjs`: browser-compatible Web Crypto Ed25519 project signing and verification, with Python cross-language validation.
- **Not tested:** actual live five-tab physical browser Catnap, WebGL 2 shader rendering/visual regression on an unrestricted browser, background-tab throttling in multiple browsers, fullscreen integration on real devices, and real HTTPS household deployment. The container's installed Chromium blocks URLs through managed security policy; no claim of a passing graphical browser test is made.
- No GPU worker, temperature sensor, energy, real payment, OCI VM, external provider integration, independent ledger anchoring or remote encrypted deployment tests have been performed. Local TEST-CREDIT settlement is not real payment.

To reproduce:

```bash
python -m pip install -e '.[test]'
pytest -q
node scripts/test-browser-worker.mjs
node scripts/test-browser-protocol.mjs
python -m polyc.demo --timeout 35
python -m polyc.economy_demo
```

No result should be interpreted as proof of decentralized model training or verified ecological benefit. The cats have finished their arithmetic and decline further testimony.
