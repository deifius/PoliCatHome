# Browser resources, capability inspection and PoliC YAML

This guide describes what the PoliC@home guest interface **actually does today**.
The **Inspect my browser** action is optional and runs locally. It never enrolls
Catnap, allocates a Cat workload, or submits inspection data to the Commons.

## What can be reported

| Reading | Source | What it does **not** prove |
|---|---|---|
| Logical CPU concurrency | `navigator.hardwareConcurrency` | Physical cores or a hardware CPU quota |
| Approximate RAM tier | `navigator.deviceMemory`, if exposed | Free RAM, exact installed RAM or our memory usage |
| WebGL 2 availability and texture limit | Temporary WebGL 2 context | Compute capacity or GPU memory |
| WebGPU adapter and buffer limits | `navigator.gpu.requestAdapter()` | Total/free VRAM, GPU watts, GPU usage percentage or temperatures |
| Battery percentage / charging | Optional `navigator.getBattery()` | Accuracy, predictable availability, or automatic power-management policy |
| Temperatures, fans, watts | No standard browser API | Not measurable or enforceable by this web page |

The browser may deliberately hide, quantize or reduce hardware information for
privacy. WebGPU support typically requires HTTPS or loopback. A GPU allocation
*limit* does not mean a corresponding amount of free VRAM exists. GPU adapter
vendor may be visible locally but is never included in the exported PoliC.

## GPU proof vs. Catnap

The separate **Run local GPU proof** button runs only after the visitor has
expanded the diagnostic and explicitly clicked the button. A small WebGPU WGSL
shader writes four numbers into a 16-byte buffer, checks the result, then
releases the GPU device and buffers. This does not start Catnap or submit data.
The current Catnap task implementation still uses the CPU-only SHA-256 worker.

## Actual controls

- The Cat creator trust and category selections are policy-matched when work is leased.
- CPU pacing is **best effort**, not an enforced CPU utilization percentage.
- Per-task runtime has a browser worker timeout; an in-flight request may still
  be finishing at the moment of cancellation.
- Session duration is enforced only while the browser page is open. It is a
  **local setting, not a field in the registered PoliC**.
- Start, Pause and Revoke remain separate actions, with confirmation of remote
  revocation required before stating that consent has been withdrawn.
- Temperature, fan, power and total/free VRAM limits are neither shown as
  enforceable sliders nor implied to be accessible by browser JavaScript.

## Exporting your PoliC

**View My PoliC**, **Download PoliC YAML**, and **Download JSON** remain visible
before and after enrollment. Before enrollment, files reflect the current draft
choices. After enrollment, they reflect the exact registered constitution;
editing the policy requires revocation and re-enrollment.

Both YAML and JSON are human-readable exports of the **same** constitution.
They contain no bearer authentication token and no browser inspection telemetry.
The YAML is valid YAML 1.2 and can be read by PyYAML or other YAML parsers. Do
not confuse an export with enrollment: saving a file does not start computing.
