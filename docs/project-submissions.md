# PoliC Project Submission Protocol (v0alpha1, staged prototype)

> A project may request computation. It may not demand it. The household has a filing cabinet; the cats still retain the keys to their own rooms.

This is the design for **third-party project intake**, not permission to execute third-party containers. Version 0.2 implements offline schema validation, Ed25519 signatures of both YAML documents, and an admin-authenticated **staging-only** coordinator API. **No uploaded OCI image can be scheduled or executed.** The original built-in `sha256_chain_v1` CPU pilot remains the only executable task.

## Project repository structure

```text
project-repository/
  Dockerfile                  # builds an OCI image; may use Docker or another OCI builder
  project.yaml                # workload manifest and immutable artifact reference
  polic.yaml                  # the project's own constitution
  src/                        # open-source project source
  tests/                      # verification and reproducibility tests
  README.md                   # public purpose and instructions
```

A published submission references a **public source repository at a pinned commit**, an OCI image at `registry/path@sha256:<64 hex digits>`, and the *signed canonical contents* of `project.yaml` and `polic.yaml`. The artifact is portable OCI; Docker is an image-builder option, **not** a requirement that contributor hosts run the Docker daemon. The future runtime should launch the image **inside HIRD/Linux (KVM)**, without mounting a host Docker socket. A container by itself is not the security boundary for hostile workloads.

Optional evidence includes an SBOM hash and reproducible-build/provenance attestation hash. Such assertions are only strings in v0.2; later acceptance must independently fetch and verify image bytes, source commit, license, build provenance, malware scanning and software supply-chain attestations. Public code is necessary but insufficient for trust.

## Two constitutions, one work agreement

**Node PoliC:** allowed categories, forbidden declared purposes, trusted signer keys, power and temperature ceilings, owner local priority and pause, jurisdiction preferences.

**Project PoliC:** purpose, category, intended and prohibited uses, commercial status, contributor allow/deny lists, allowed verified jurisdictions, distribution terms, credited output license, revocation and attribution rules. The project is entitled to say *no* to contributors as much as the node is entitled to say *no* to the project.

Matching is an **intersection**, never an override. A project cannot raise a node's thermal ceiling or grant itself network access. A node cannot use participation as a claim of copyright ownership or automatic revenue participation beyond agreed terms. When jurisdiction attestations or signer trust are absent, a restricted project must be refused. Do not infer a person's values, political identity, or culpability from undeclared metadata. Explicit identities, voluntary organizational certifications, and reviewed agreements may be used only subject to privacy and appeals protections.

Accepted project revisions are immutable; any change to either signed document requires a new numbered revision and a new opt-in agreement. Already-earned credits and contractual obligations survive cancellation according to the agreed policy; technical revocation stops *future work*, not past receipts.

## Task ABI (planned; OCI execution unavailable)

The standard adapter `polyc-task-json-v1` is a request/response protocol:

- HIRD mounts a **task-scoped** JSON request read-only at `/polyc/input/task.json`, containing `task_id`, `project_digest`, `shard`, input content digests, and a time-limited task token.
- HIRD mounts a constrained, empty output volume at `/polyc/output/`. The workload writes `/polyc/output/result.json` and any permitted result blobs; each blob receives an independently computed hash.
- Workloads should be deterministic or idempotent; checkpoint support is explicitly advertised and later tested. Data locality, latency, hard GPU/CPU caps, and energy availability must be negotiated by the host. No root, no host network, no host filesystem or Docker socket, read-only root image.
- HIRD/Linux host owns job termination; guest termination signals, a scheduler lease, and checkpoint requests are advisory, not substitutes for host-enforced kill.
- A project may declare `independent_recompute`, `project_verifier` or `human_review`; **declaring a method does not implement it**. Crediting work must be gated on the verification actually performed. For nondeterministic video renders, use verifiable frame artifacts, reviewer sign-off, or agreed provenance checks—not raw GPU-second claims.

For projects with complex stages, submit a *DAG of shards*, each with inputs, outputs, dependencies, and verification rules. This initial schema models only a single stage split into `task_count` shards. A future DAG revision will not break v0alpha1 signatures.

## Intake lifecycle

1. **Publish** the source under an actual open-source license in a public repository. Build an OCI image, push to a registry, pin its digest, and publish SBOM/provenance where possible.
2. **Declare** the immutable `project.yaml` and project-owned `polic.yaml` (see `projects/example-render/`), including distribution, content, mutual consent and cancellation rules.
3. **Validate locally:** `polyc validate-submission --dir projects/example-render` checks schemas and computes the bundle digest; it **does not** verify source/image contents.
4. **Sign both documents as one contract:** `polyc sign-submission --dir PROJECT --private /secure/owner.pem --out /secure/signed-submission.json`. The Ed25519 signer must match the public key in `polic.yaml`.
5. **Stage on the coordinator:** `polyc submit-submission --signed /secure/signed-submission.json --server http://127.0.0.1:8765 --admin-token-file /secure/admin-token.txt`. The API returns `state=staged`, `executable=false`. Pilot access is admin-mediated, not a public marketplace. Use TLS/private transport in real networks.
6. **Review and negotiate (future):** check public source/artifact attestation, licensing, identity agreements, contribution terms, consent, HIRD capability, budgets, device thermals, jurisdiction and latency. Nodes each explicitly accept the exact signed bundle digest.
7. **Execute only after the HIRD VM safety milestone (future):** issue task-scoped leases; distribute object digests instead of secrets or arbitrary host paths; verify output; issue signed receipts; update contribution shares and Chronicle reports.
8. **Settle only by explicit agreement (future):** audit provisional credits, provide appeal/correction mechanisms, and handle payouts externally with legal and tax review. No cryptocurrency requirement.

The old `/api/jobs` path submits **only** signed built-in deterministic projects. The new `/api/submissions` path merely stages OCI paperwork. They are deliberately non-interchangeable.

## Security and licensing unresolved before execution

The v0alpha1 schema checks immutable image syntax, not the image's bytes or its provenance; SHA-256 paths with fake digests still pass schema checks. The source repository may not exist. Nor does a claim in YAML enforce ethical conduct or ensure actual license compliance. Enforce these checks during future admission. An OCI artifact must never be run with `docker run` on an owner's host under the v0.1 process backend; doing so bypasses the proposed VM boundary.

Current schemas use IDs as pseudonyms and restrict jurisdictions only against **verified** jurisdiction metadata. There is no automatic geographic or ideological attestation. The `project_owner_pubkey` must be controlled by the author, ideally with rotating/revocable key identities planned before public acceptance.

## Example author workflow

```bash
# Demo inputs are placeholders. Replace repo, commit, OCI digest, and owner key!
polyc keygen --private runtime/owner.pem --public runtime/owner.pub
# Edit projects/example-render/polic.yaml to put the key from runtime/owner.pub in project_owner_pubkey.
# Edit projects/example-render/project.yaml to point to a REAL public source and pinned OCI image.
polyc validate-submission --dir projects/example-render
polyc sign-submission --dir projects/example-render --private runtime/owner.pem \
  --out runtime/signed-submission.json
# Local coordinator running with the POLYC_ADMIN_TOKEN:
polyc submit-submission --signed runtime/signed-submission.json \
  --server http://127.0.0.1:8765 --admin-token-file runtime/admin-token.txt
```

> The cats will consider your petition. Filing it under the saucer does not constitute approval.
