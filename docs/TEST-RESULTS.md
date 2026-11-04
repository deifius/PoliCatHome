# Validation record — five-cat CPU pilot

Verified locally on Linux / Python 3.13 with available dependencies at preparation time.

- `pytest -q`: **14 passed**.
- `python -m polyc.demo --timeout 35`: **25 / 25** deterministic tasks complete.
- Contributions: `cat-1`, `cat-2`, `cat-3`, `cat-4`, and `cat-5`: **5 verified tasks each**.
- Built-in task kinds tested: `sha256_chain_v1` only.
- The coordinator recomputes expected digests before recording results.
- Tested on **one physical/container Linux host** with five independently configured worker agents; not five separate homes.
- Tested a process runner with resource limits, not a virtual machine or untrusted-code isolation.
- No GPU, temperature sensor, energy, payment, economic agreement, remote encrypted deployment or graphics tests have been performed.

To reproduce:

```bash
python -m pip install -e '.[test]'
pytest -q
python -m polyc.demo --timeout 35
```

No result should be interpreted as proof of decentralized model training or verified ecological benefit. The cats have finished their arithmetic and decline further testimony.
