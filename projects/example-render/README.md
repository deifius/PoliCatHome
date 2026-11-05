# Example rendering-project petition (not a functioning renderer)

These are **template contracts** for future image-based work, not a job you can submit to the currently running HIRD/process backend.

- `project.yaml`: public source revision, digest-pinned OCI artifact, task adapter and runtime limits.
- `polic.yaml`: project owner's candid statement of intended use, eligibility, commercial status, credits and mutual consent.
- `Dockerfile` + `worker.py`: a *toy* JSON file adapter showing the eventual task mount ABI; does not generate a movie or use GPUs. `FROM` is intentionally not digest-pinned so don't treat this as a reproducible published release.

**Important placeholders:** the source repository, commit, OCI image digest, and signer public key are not real release attestations. Replace them before considering deployment. Even after you replace them, v0.2 only validates and stages declarations; no image is downloaded, scanned, or executed. For full instructions see `docs/project-submissions.md`.
