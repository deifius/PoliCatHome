# Validation record — five-cat CPU pilot

Verified locally on Linux / Python 3.13 with available dependencies at preparation time.

- `pytest -q`: **19 passed**.
- `python -m polyc.demo --timeout 35`: **25 / 25** deterministic tasks complete.
- Contributions: `cat-1`, `cat-2`, `cat-3`, `cat-4`, and `cat-5`: **5 verified tasks each**.
- Built-in task kinds tested: `sha256_chain_v1` only.
- New project submission tested: signed `project.yaml` + `polic.yaml` validation, rejection of mutable OCI tags, mismatched revisions, signature tampering, incompatible economics, prohibited host networking, staged coordinator registration, duplicate revision, and mutual policy preview. **No container executed.**
- New ledger tests: two verified CPU receipts, provisional credits, unauthorized read rejection, SHA-256 chain tamper detection. **No settlement/independent hash anchoring.**
- The coordinator recomputes expected digests before recording results.
- Tested on **one physical/container Linux host** with five independently configured worker agents; not five separate homes.
- Tested a process runner with resource limits, not a virtual machine or untrusted-code isolation.
- No GPU, temperature sensor, energy, actual payment, OCI VM, economic settlement, remote encrypted deployment or graphics tests have been performed.

To reproduce:

```bash
python -m pip install -e '.[test]'
pytest -q
python -m polyc.demo --timeout 35
```

No result should be interpreted as proof of decentralized model training or verified ecological benefit. The cats have finished their arithmetic and decline further testimony.
