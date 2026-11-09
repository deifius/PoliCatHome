# Catnap Scenes: rendering without authority

> Visualizers may **observe** Catbox activity, but they cannot dispatch work, change constitutions or issue credits.

The app loads only reviewed, bundled scene modules from `polyc/web/scenes/registry.js`. Third-party developer code can add a new paradigm after ordinary source review; the web UI deliberately **does not execute imported JS or shader code**. Ordinary users can import color/typography skins as validated JSON without introducing executable code.

## Skin schema

```json
{
  "name": "My Northern Lights",
  "accent": "#4ee0c8",
  "low": "#061824",
  "bright": "#e0fff8"
}
```

Use **Export Skin** to get the current settings as JSON and **Import Skin** to load one. The parser refuses files over 10 KB, validates the four recognized fields and ignores extra code-like properties. No external URLs, JS, shaders or HTML may be loaded through a skin. The palette is shared by Gibson, Flying Cats, Flying Toasters, Pipes and Terminal scenes.

## Add a new full paradigm

Create a reviewed module, for example `polyc/web/scenes/aurora.js`:

```javascript
export class AuroraScene {
  constructor(canvas, theme, onSelect) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.theme = theme;
    this.speed = .5;
  }
  setData(snapshot) {
    // All values originate from the authenticated, read-only scene snapshot.
    this.nodes = snapshot.nodes;
    this.events = snapshot.events;
    this.verified = snapshot.counts.done;
  }
  draw(seconds) {
    // Called by an adaptive, ~12–30 fps renderer. No network calls here.
    const {canvas,ctx} = this;
    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;
    ctx.fillStyle = this.theme.low;
    ctx.fillRect(0,0,canvas.width,canvas.height);
    ctx.fillStyle = this.theme.accent;
    ctx.fillText(`${this.verified} verified tasks`, 30, 55);
  }
  destroy() { /* release listeners, textures, shaders, resources */ }
}
```

Then explicitly import and register `AuroraScene` in `registry.js` and add a scene-selection button in `index.html`. This SDK does not depend on Three.js, Node, a bundler or a CDN. A project can choose WebGL 2, WebGPU (where supported), 2D Canvas or a terminal display as long as its rendering is bounded and its data access is read-only.

## Scene snapshot schema

The endpoint returns one object:

```json
{
  "schema": "polyc.catnap.snapshot/v1",
  "mode": "live",
  "scope": "operator",
  "server_time": 1793900000.0,
  "counts": {"nodes": 5, "pending": 10, "leased": 3, "done": 25, "failed": 0},
  "nodes": [{"id": "browser-cat-example", "revoked": false,
             "projects": {"example-cat": {"done": 5, "leased": 1}}}],
  "projects": [{"id":"example-cat", "title":"Example Cat", "category":"open_science",
                "status":"open", "tasks":{"done":25,"leased":3}}],
  "events": [{"id":5,"at":1793900000.0,"node_id":"browser-cat-example",
               "job_id":"example-cat", "kind":"task_completed", "detail":"example-cat-0004"}]
}
```

This is an **illustrative schema**, not a claim of real work. An actual `GET /api/catnap/snapshot` requires a valid operator token; a node token must supply `?node_id=<own node>`. The UI has a **separate, visibly watermarked synthetic preview** that is never written to a contribution ledger.

## Gibson mappings

- A **blue monolith** is an actual node/project Catbox association if such assignments exist. Idle consented nodes get an idle tower; before any assignments, approved Cats can appear as waiting project towers.
- **Height** is a logarithmic artistic encoding of tasks verified by the node for the project, plus a visual accent for an active lease. It is **not** physical server height, FLOPS, energy, location or actual hardware size.
- **Brighter pulses** represent current leased tasks. **Lighted windows** are a shader animation based on verified or leased counts; individual windows are **not** proof of individual tasks.
- **Ground links** connect currently visible monoliths working on the same Cat, not measured network packet routes.
- Clicking a monolith reveals its node/association, project name and real verified/leased count. Operator data reveals IDs only to the operator; owners see just their own account scope. A future opt-in public gallery would require separate privacy policy and aggregation.

## Performance and safety

Render budget drops to about 12 fps while contributing compute, about 30 fps while idle, and clamps WebGL canvas dimensions to 1600 pixels on the longest axis. Browser frames can still consume GPU and electrical power; this is not a measured power governor. Do not load third-party scripts from a gallery, let scenes fetch URLs, or give scenes coordinator bearer tokens. New paradigms belong in reviewed source control, with controls for untrusted asset handling if community uploads are added later.

The visual vocabulary is a fresh implementation paying homage to classic 1990s screensavers and *Hackers*' Gibson rather than distributing copyrighted film or historical DirectX assets.
