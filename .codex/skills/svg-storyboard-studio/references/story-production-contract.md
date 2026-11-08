# Story production contract

Use `docs/story.schema.json`, `docs/animation-code-contract.md`, and source validation for exact limits.

A Story ZIP has exactly one `story.json`, at root or under one common folder, with all references local. V1 uses `schemaVersion: "1.0"`; required concepts are project ID/title, video, and 1-80 scenes. Assets, characters, audio, seed, and render metadata are optional. Application derives starts/total. Unknown properties do not create features.

Video dimensions are even 64-3840, area <=8,294,400, FPS 24/30/60. Scenes last 0.25-600 seconds; total <=1800 seconds. Prefer lowercase ASCII relative paths. Consult C# validation for all ZIP/path/size/reference/type/signature/SVG rules.

Transitions are outgoing cut/fade/slide. Cut overlap is zero; fade/slide overlap cannot exceed half either adjacent scene. Final overlap is zero.

Scene JS exports named `createScene(context)` returning finite `duration` plus synchronous `seek`, `reset`, `dispose`. Create may be async. Imports are relative local modules; no CDN/npm or top-level side effects.

Supported context is source-defined: `root`, `sceneRoot`, `canvas`, dimensions, duration/sceneId, `gsap`, `timeline()`, `assetText()`, `assetUrl()`, `addSvg()`, `svg()`, `character()`, `camera`, `follow()`, `stroke()`, `random()`, `noise()`. Do not invent asset loaders, audio, physics, rigs, expressions/actions, delta time, or events.

`addSvg` copies children, not root attributes. Namespace IDs and scope selectors. Characters are scene-local clones; parts metadata is advisory. Use shared GSAP/plugins, paused timelines, and absolute `timeline.time(t,true)`.

The same timestamp must reconstruct the same image after arbitrary seeks. Initialize randomness once; never consume it or increment state during seek. Reset is not automatic. Avoid clock/random/timers/RAF/network/workers/eval/infinite repeats.

Audio is manifest-driven. Export samples `ceil(duration*fps)` frames at `k/fps`; exact final endpoint normally is not encoded. Use Studio/API through the guarded worker, not spoofed direct Python.

Import success proves structure only. Before acceptance test arbitrary seek order, overlaps, asset IDs, decoding, ZIP round-trip, actual preview, and a real MP4 when video is in scope.
