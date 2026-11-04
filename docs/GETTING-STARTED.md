# Getting started

See the root README's verified `python -m polyc.demo` and manually managed five-owner tutorial.

## Files and secrets

`polyc init-pilot --out runtime/my-first-household --nodes 5` creates an administrator credential, project Ed25519 keypair, signed example task, and five independent owner configuration files. `runtime/` must be excluded from Git and kept private. Only share a given node's YAML with its owner. The signed example source repository and commit are **placeholders**: no Git checkout or source-to-artifact verification is implemented.

## Where the limits bite

Linux process `nice +19` is real. Nice Plus 20..99 is an *application* scale, not a Linux syscalls extension. A user pause flag is authoritative locally. CPU utilization duty cycle and process address-space limit are prototypes and do not provide VM-grade isolation. GPU, whole-system thermals, electricity limits and automatic content analysis are not implemented. Configure `cpu_package_c_max` only if a usable Linux CPU package sensor is available; the worker denies if required telemetry is missing.

For actual five-host machines, provide private encrypted communications and test revocation during coordinator failure before enrolling any real volunteer. No automatic exposure on a public Internet address is provided.
