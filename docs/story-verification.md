# Story implementation and verification status

Date: 2026-11-07. This report supersedes no prior legacy test evidence; old results remain in verification.md.

## Implemented in source

- MVC/Core/Python retained. New project store with immutable revisions and optimistic saves; bounded ZIP import/export and manifest/source validation.
- Shared browser scene runtime with real GSAP dependency, code lifecycle, shared SVG characters/assets/fonts, camera/follow, motion/morph plugins, paused timelines and absolute seek; outgoing overlap master timeline.
- Dark studio, scene ordering/duration/transition controls, timeline/frame steps, editable code, layers/assets, project save/export, render settings and progress console. Legacy UI remains at /whiteboard.
- Story job dispatch, Windows OS resource boundary, browser request isolation, deterministic frame stepping/checks, H.264 output validation and sample-domain audio mix.
- JSON schema, code contract, architecture/security/dependency docs; four-scene 34.5-second self-contained source and ZIP with generated SVG art and audio.

## Executed checks

- Story Web/Core/Worker build to `work/story-build` passed with 0 warnings and 0 errors. A normal in-place build hit DLL locks from the still-running legacy app; the approval system did not allow restarting it. Temporary build verifies compilation without changing that running process.
- Story core: 21 checks passed, including sample timeline, shared character, ZIP round-trip, immutable snapshots, stale-save rejection, traversal paths, version/missing refs/transition/duplicate/timer/MIME errors, ZIP traversal and malformed JavaScript syntax. Source parsing uses Node --check without execution.
- Pure JavaScript timeline tests passed: scene boundaries, outgoing overlaps, final scene, arbitrary seek order, audio offsets and seeded random.
- Real FFmpeg audio test passed: 72 H.264 frames, 3-second AAC/video duration, nonzero sound only in its scheduled interval, source trim/fades. The initial time-domain filter test exposed a timestamp issue on the installed FFmpeg build; the implemented mix now uses explicit 48 kHz sample counts and timestamps.
- JavaScript/Python syntax, schema JSON and sample ZIP integrity checks passed. End-to-end script was invoked and explicitly returned SKIP because GSAP is missing; this is not a runtime test pass.

## Not verified / MVP not yet accepted

- npm install failed ENOTFOUND for registry.npmjs.org. GSAP runtime files are not yet available in this workspace; no simulated library was substituted. Setup must install/vendor them.
- Earlier automatic approval review failed because of an account usage limit, not because the action was judged unsafe. Restarting the app and browser/end-to-end runs requiring that approval have not been retried through another route.
- Therefore real Story preview, actual GSAP/nested/morph execution, opaque-origin module loading, preview/export parity, complete 34.5-second sample MP4, profile matrix, Windows job CPU/RAM behavior, cancellation after Chromium starts, and old browser regressions remain unverified for this new build.
- `tests/test_story_e2e.py` is provided to run these checks once setup and app startup are available. A skipped test is not a pass. 4K performance, public multi-user deployment, full maintenance audits of optional repos and commercial license clearance are not claimed.

No phase depending on those runtime checks is declared accepted. The source is reviewable and core/timing/audio checks can run independently, but a final runnable product handoff still requires the blocked dependency/runtime validation.
