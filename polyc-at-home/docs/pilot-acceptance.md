# Five-cat acceptance test

## Automatic

```bash
pytest -q
python -m polyc.demo --timeout 35
```

Expected 25 `done` tasks, no outstanding tasks, five distinct contributors and 5 tasks credited per contributor. The demonstration starts a real HTTP coordinator on loopback, provisions five mutually consenting node identities, starts five worker control loops and their separate subprocess task runners, verifies every hash chain, retrieves five separate Chronicles, then shuts everything down.

## Negative tests

- Corrupted Ed25519 manifest denied.
- Untrusted signer denied by worker; coordinator cannot force execution.
- Unknown category, incompatible declared purpose, unwanted commercial work and disallowed contributor denied.
- Owner-revoked node cannot obtain or finish a lease.
- Duplicate completion and forged lease token denied.
- Incorrect digest rejected by coordinator independent recomputation.
- Expired lease returned to queue for another attempt.
- Owner pause prevents a new task even when coordinator cannot be reached.
- Constitution with unsupported mandatory energy telemetry or unsafe memory limit rejected.
- Server refuses non-loopback HTTP unless operator uses an unsafe explicit test flag.

## Physical five-host pilot — pending

On five real Linux devices: provision and distribute separately stored owner configs; run coordinator behind a private VPN or TLS reverse proxy; exercise users launching a foreground game or build; remove the coordinator network link during an assigned task; test offline owner pause; test slow/missing sensors; measure effective resource yield and actual household power (if instrumented). Report OS/kernel, CPU, hypervisor, GPU, energy and sensor information *as observed*, not as assumed. The star network still has a central coordination point; decentralized federation is a later stage.
