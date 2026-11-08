---
name: svg-storyboard-studio
description: Work on the local AI SVG Storyboard Studio repository, including its Story ZIP format, deterministic GSAP scene runtime, ASP.NET/Python rendering pipeline, legacy whiteboard mode, tests, and project-specific safety constraints. Use for analysis, implementation, debugging, review, or Story content production in this repository.
---

# SVG Storyboard Studio

Treat current source as authoritative. Documentation may reflect different dates or earlier environment failures; never turn old claims into current evidence without rerunning the relevant check.

## Load relevant context

- Architecture, routes, persistence, setup, or operations: read [references/architecture-and-operations.md](references/architecture-and-operations.md).
- Story ZIP, manifest, scenes, animation, transitions, characters, camera, or audio: read [references/story-production-contract.md](references/story-production-contract.md), then consult `docs/story.schema.json`, `docs/animation-code-contract.md`, and named source files for exact details.
- Imported code, isolation, rendering, cancellation, or verification claims: read [references/security-and-verification.md](references/security-and-verification.md).

## Invariants

- Preserve Story Studio at `/` and legacy whiteboard/doodle at `/whiteboard`. Keep `/api/renders` backward compatible unless explicitly asked otherwise.
- Retain .NET 8 MVC/Core/Worker plus Python/Playwright/FFmpeg unless an architectural replacement is requested.
- Preview and export use the same browser runtime and absolute master-time seeking. Scenes must render deterministically across forward, backward, and repeated seeks.
- Treat ZIP, SVG, HTML/CSS, JS, images, fonts, and audio as untrusted. Lint is not a sandbox; preserve preview-origin isolation, CSP/message checks, offline export routing, Chromium sandbox, immutable revisions, and the Windows process boundary.
- Keep ports 5188/5189 loopback-only.
- Preserve projects, history, `data/`, outputs, and unrelated changes. Do not migrate/delete them merely to test.
- Do not invent runtime APIs. Confirm against `runtime.js`, `timeline.mjs`, Core validation, and the render adapter.
- Report verification by layer. A skipped, blocked, stale, or partial run is not a pass.

Inspect the smallest authoritative file set, make scoped changes, and test the affected layer. Contract/runtime changes must keep validation, schema, samples, preview, exporter, tests, and docs consistent. State exactly what ran and what remains unverified.
