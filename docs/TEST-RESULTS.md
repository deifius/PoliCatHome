# Validation record — CPU pilot and test-credit exchange v0.3

Verified locally on Linux / Python 3.13 with available dependencies at preparation time.

- `pytest -q`: **35 passed** (current local run, including economic tests).
- `python -m polyc.demo --timeout 35
python -m polyc.economy_demo`: **25 / 25** deterministic tasks complete.
- Contributions: `cat-1`, `cat-2`, `cat-3`, `cat-4`, and `cat-5`: **5 verified tasks each**.
- Built-in task kinds tested: `sha256_chain_v1` only.
- New project submission tested: signed `project.yaml` + `polic.yaml` validation, rejection of mutable OCI tags, mismatched revisions, signature tampering, incompatible economics, prohibited host networking, staged coordinator registration, duplicate revision, and mutual policy preview. **No container executed.**
- Contribution receipt tests: provisional points, authorization and hash-chain tampering.
- Test-only financial ledger: issuer supply limit, explicit wallet enrollment, proof of owner key, signed two-party transfer, replay and cross-coordinator rejection, overspend rejection, atomic simultaneous double-spend protection, funded-job refusal when budget is absent, verified task settlement, partial cancel refund, ledger tamper detection, schema refusal of cash conversion, disabled provider catalogue.
- `python -m polyc.economy_demo`: five distinct contributor identities + one project wallet, 25 verified volunteer tasks, 25 noncash test credits issued, 5 signed transfers to project, 5 further verified credit-priced tasks, 5 credit units settled, balances and local ledger verified. **No external payments.**
- The coordinator recomputes expected digests before recording results.
- Tested on **one physical/container Linux host** with five independently configured worker agents; not five separate homes.
- Tested a process runner with resource limits, not a virtual machine or untrusted-code isolation.
- No GPU, temperature sensor, energy, actual payment, OCI VM, external provider integration, independent ledger anchoring, remote encrypted deployment or graphics tests have been performed. Local TEST-CREDIT settlement is not real payment.

To reproduce:

```bash
python -m pip install -e '.[test]'
pytest -q
python -m polyc.demo --timeout 35
python -m polyc.economy_demo
```

No result should be interpreted as proof of decentralized model training or verified ecological benefit. The cats have finished their arithmetic and decline further testimony.
