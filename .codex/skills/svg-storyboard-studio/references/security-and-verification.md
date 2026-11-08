# Security and verification

Imported JS runs only in the isolated browser, never through MVC/Python/Node evaluation. Preview is an opaque-origin sandboxed iframe on 5189 controlled by 5188; keep CSP and source/channel/token checks. Export keeps Chromium sandboxing, offline exact-allowlist routing, immutable snapshots, and no filesystem/shell/credentials/downloads/service workers.

On Windows x64, the worker uses a fail-closed Job Object for Python, Playwright, Chromium, and FFmpeg descendants. Other platforms need equivalent containment. Lint/runtime blocking is not a security proof. Preserve ZIP/path/SVG/media validation, canonical routing, timeouts, process-tree cancellation, bounded logs, and partial cleanup. Keep both ports loopback-only.

## Verification ladder

1. Syntax and `dotnet build`.
2. `tests/StoryChecks`.
3. `node tests/story-timeline.mjs` (not browser/GSAP).
4. `python tests/test_story_audio.py`.
5. Targeted/full `python tests/test_engine.py`.
6. Current app plus `python tests/test_story_e2e.py`.
7. Legacy live regressions: `test_app.py`, `test_doodle_app.py`, `test_mode_validation.py` when shared code changes.

`.\scripts\check-story.ps1` is useful but inspect it before calling it exhaustive. `dotnet test SvgToMp4.sln` alone is not coverage because StoryChecks is a separate console project.

A SKIP is not a pass. Cached build is not clean setup. Timeline tests do not prove GSAP/browser/rendering. Audio fixture does not prove full MP4. Occupied ports do not identify a revision. Historical docs reflect different environments; only fresh runs establish current status. Never claim MVP/production acceptance while required browser/render/process-boundary tests remain blocked.
