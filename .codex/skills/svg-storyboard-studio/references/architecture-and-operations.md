# Architecture and operations

Snapshot synthesized from source and docs on 2026-11-07. Recheck source after material changes.

The repository hosts Story Studio at `/` and legacy SVG whiteboard/doodle at `/whiteboard`. Stack: .NET 8 ASP.NET Core MVC/Razor, vanilla JS/CSS, SQLite, hosted worker, Python/Playwright/Pillow, Chrome or Edge, and FFmpeg/ffprobe. GSAP 3.15.0 plus MotionPath/MorphSVG are local. Node is not a service; npm vendors dependencies and Node parses Story JS without executing it on import.

## Components

- `SvgToMp4.Core`: models, SQLite jobs, paths, Story validation, immutable revisions, optimistic conflicts, JS syntax.
- `SvgToMp4.Web`: pages/APIs; `/`, `/whiteboard`, `/api/stories`, backward-compatible `/api/renders`.
- `wwwroot/story`: Studio, master timeline, isolated runtime, styles, GSAP/plugins.
- `SvgToMp4.Worker`: sequential queue, cancellation/timeouts, Python dispatch, Windows x64 Job Object.
- `engine/story_render.py`: Playwright frames, deterministic probes, FFmpeg/audio, ffprobe.
- `engine/render.py`: legacy renderer.
- Runtime `data/`: SQLite, revisions, inputs, logs, outputs; non-public and Git-ignored.

Flow: bounded ZIP validation -> Node syntax parse -> normalized immutable revision. Preview uses 127.0.0.1:5188 and isolated runtime on 5189. Render snapshots a revision -> queue -> worker -> Playwright seeks `k/fps` -> PNG pipe -> FFmpeg/audio -> ffprobe.

## Run

Requires Windows x64 for current Story export isolation, .NET 8, Python 3.11+, Node/npm, browser, FFmpeg/ffprobe.

```powershell
.\setup.ps1
.\start.ps1
```

Setup vendors npm/GSAP, installs Python into `engine/.packages`, restores/builds .NET, and may need network. Start builds unless `-NoBuild`. Use consistent `-Python`; `SVG_CHROME` selects browser. Inspect occupied ports before starting; do not kill unknown processes.

Key sources: `README.md`, `docs/01-architecture-audit.md`, `docs/story-run.md`, `StoryProjects.cs`, `StorySyntax.cs`, `StoriesController.cs`, `StoryPreview.cs`, `runtime.js`, `timeline.mjs`, `RenderWorker.cs`, `StoryProcessBoundary.cs`, `engine/story_render.py`. On conflict prefer current executable source, then tests, then newest dated audit.
