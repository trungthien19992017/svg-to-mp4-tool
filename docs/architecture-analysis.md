# Architecture analysis — AI SVG Storyboard Studio

Date: 2026-11-07. Baseline: local ASP.NET Core MVC .NET 8; Razor, vanilla JS/CSS; Microsoft.Data.Sqlite 8.0.33; Python 3.11 adapter using Playwright 1.64.1/Pillow; installed Chrome and FFmpeg/libx264. Repository currently contains uncommitted implementation files; preserve these and existing `data/`.

## Existing system

- `SvgToMp4.Core`: render settings, JSON job records in SQLite, workspace paths. Existing jobs use immutable input/settings snapshots.
- `SvgToMp4.Web`: loopback MVC app on 5188; SVG upload/paste, whiteboard/doodle editor, preview MP4 and history. No Story ZIP, scene modules, continuous animation preview, shared character library or audio timeline.
- `SvgToMp4.Worker`: one background consumer, Python subprocess, JSON progress, 15-minute cancellation and process-tree termination. Requests do not block during video export.
- `engine/render.py`: static SVG geometry, whiteboard reveal and doodle masks. FFmpeg receives RGB frames through a bounded pipe, outputs H.264/yuv420p, then ffprobe validates frames. This is not a general JavaScript scene runtime.
- Current import/export: SVG text only. A selected doodle mode can mismatch an ordinary SVG; a pending fix adds early validation and readable errors. Preserve this fix.

## Target and compatibility

Keep .NET/Python; no Node microservice. Add Story modules beside the existing implementation. `/` becomes the storyboard studio; `/whiteboard` retains the original UI and `/api/renders` remains backward compatible. Do not migrate/delete old jobs or input files.

New modules:

1. Story package storage/validation in Core: immutable project revision directories, manifest validation, bounded ZIP extraction, import/export, file editing and stable asset IDs.
2. Shared browser runtime: GSAP paused timelines, scene contract, deterministic seek, shared SVG/character helpers, camera, master timeline, transitions. Exact same runtime files for preview and export.
3. Preview isolation: sandboxed opaque-origin iframe from a separate loopback port 5189. That port exposes only read-only story files and runtime; no main application APIs. Restrictive CSP, no external network, origin/source/token checks for messages.
4. Production rendering: existing single .NET worker dispatches Story jobs to a separate Python adapter. Browser sandbox enabled, requests fulfilled from the immutable snapshot only, no file URLs, no arbitrary host bindings. Worker process tree has timeout/cancellation; Windows Job Object adds memory/CPU/kill-on-close boundaries. Unsupported environments fail closed for imported executable code until equivalent isolation is configured.
5. Studio UI: dark editor, scene list/reorder, global timeline, frame steps, asset/layer panels, editable scene source, console, project ZIP import/export, job progress. Monaco is optional if its local dependency can be provisioned; textarea fallback must be usable and disclosed.
6. Audio: manifest tracks with global or scene-relative positions, trimming, volume/fades; preview synchronized to master time, export mixed by FFmpeg with exact video duration.

## Time model

Seconds in manifest; output frames are `k/fps`, `k=0..ceil(duration*fps)-1`. Outgoing transitions overlap scene intervals: next start = previous end - outgoing transition duration. Total duration = sum(scene durations) - sum(valid outgoing overlaps). Last scene has no outgoing overlap. Each overlap is shorter than both adjacent scenes and at most half of each scene duration. Only cut/fade/slide are accepted initially; unsupported transition names are rejected.

Each scene initializes once per load and exposes `duration`, `seek`, `reset`, `dispose`. GSAP timelines are paused, explicitly sought with callback suppression; finite repetitions only. No uncontrolled timers, clock, network or unseeded randomness. Import lint plus runtime restrictions and nonsequential frame comparison detect common violations; arbitrary JS determinism cannot be proved statically.

## Data and code safety

Project ZIP files are untrusted. Reject traversal/absolute paths/symlinks/case collisions, excessive count/size/ratios, executable host files and external references. Validate manifest and all referenced files before publishing a revision. Parse XML without entities. SVG asset scripts/event handlers/foreignObject/external links are rejected; scene JS only executes inside the isolated browser, never in MVC/Node/Python itself. Do not pretend regex filtering is an execution sandbox.

Browser renderer sandbox, separate preview origin/CSP, asset-only request routing, no main-origin iframe privileges, process limits and job cancellation are complementary boundaries. They are not a general-purpose service for hostile internet tenants; retain loopback-only deployment.

## Implementation phases and gates

1. Code to Video: browser runtime + createScene contract, native SVG/HTML/CSS, GSAP, manual seek, MP4 dispatch. Gate: build, seek regression tests and real output; mark unverified if environment cannot launch browser.
2. Story Project: versioned manifest/schema, ZIP round-trip, immutable saves, validation. Gate: valid ZIP and adversarial import tests.
3. Storyboard: master time, transitions, shared character assets, reorder/duration, UI. Gate: four-scene 30–40-second sample and boundary/seek tests.
4. Production: progress, cancellation, audio mix, resource boundaries. Gate: codec/FPS/duration/frame count, audio offsets and child cleanup tests.
5. Polish: dark UI, usable code editor, documentation, samples and completion report. Do not mark a phase tested without actually running its checks.

## Known constraints at start

The previous automatic approval review could not approve restarting the app because of an account usage limit; it explicitly said this was a review failure rather than an unsafe-action finding. Do not bypass that check. Source edits and allowed build/static checks can proceed. Browser/FFmpeg/end-to-end runs requiring that approval remain pending until the environment allows them or the user runs documented commands.

Research evidence and dependency/license decisions will be recorded separately. No destructive change or backend replacement is required by this design.
