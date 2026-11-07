# Delivery by phase

2026-11-07. Implemented source and tested acceptance are tracked separately. No destructive schema/data migration was performed. Original whiteboard/doodle source, input snapshots and jobs remain available.

| Phase | Main files added/changed | Checks executed | Remaining gate |
|---|---|---|---|
| 1 — Code to Video | `wwwroot/story/runtime.js`, `runtime.html`, `runtime.css`, `studio.mjs`; `engine/story_render.py`; Story controller/view | Web/Core/Worker compile; JS/Python syntax | GSAP installation and real preview/export parity |
| 2 — Story Project | `Core/StoryProjects.cs`, `StorySyntax.cs`; `Controllers/StoriesController.cs`; `docs/story.schema.json` | 21 core checks, including real sample ZIP round-trip, immutable revisions, references and invalid imports | Larger real-world third-party projects |
| 3 — Storyboard | `timeline.mjs`; dark storyboard editor; `samples/lost-star/` and `lost-star.zip` | Pure timeline, overlap, arbitrary seek order, audio offsets, deterministic random; sample ZIP integrity | Four-scene visual preview, thumbnails, nested GSAP and sample MP4 |
| 4 — Production | `Worker/RenderWorker.cs`, `StoryProcessBoundary.cs`, `engine/story_render.py`; extended Job record | Real FFmpeg H.264/AAC mix test, sample-based scheduling/fade/trim | OS resource/cancellation behavior with Chromium; 720p/1080p/FPS matrix; multi-minute stress |
| 5 — Polish | Story CSS/UI, source editor, assets/layers/console, setup/start/vendor scripts, docs, regression/E2E test files | Build/static checks; no simulated animation-library tests counted | Live UI/accessibility/responsiveness and old browser regressions after restart |

The app is not declared MVP-accepted. Source is integrated and reviewable; browser acceptance is explicitly pending. GSAP could not be downloaded because registry access failed. Restart/browser testing was not approved because automatic review hit an account usage limit. A separate build output verified compilation without replacing locked DLLs of the existing process.

See [story-verification.md](story-verification.md), [story-run.md](story-run.md), and [architecture-analysis.md](architecture-analysis.md). To finish acceptance, install dependencies with setup, restart the app, run core checks and `tests/test_story_e2e.py`, inspect the produced MP4 and record the results. Any failures must be fixed before updating these gates to passed.
