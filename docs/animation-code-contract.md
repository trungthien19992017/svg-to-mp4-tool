# Story Production & Animation Code Contract v1

Source-derived contract, 2026-11-07. Companion: `story.schema.json`, JSON Schema draft 2020-12. This document describes current code, not proposed APIs.

## 1. Story ZIP and manifest

Use one `story.json` at ZIP root plus every referenced file. A single enclosing folder is accepted if all files lie below it and exactly one manifest exists. Example layout: `story.json`, `scenes/scene-001.js`, optional `modules/helpers.js`, `assets/characters/may.svg`, `assets/background.svg`, `audio/rain.wav`. Export uses project-relative paths and the normalized manifest. No machine paths, credentials, runtime binaries or entire app source.

Minimal manifest matching section 14:

```json
{
  "schemaVersion": "1.0",
  "projectId": "minimal-circle",
  "title": "A moving circle",
  "video": {"width": 720, "height": 1280, "fps": 24, "format": "mp4"},
  "scenes": [{"id": "scene-001", "duration": 3, "source": "scenes/scene-001.js", "transition": {"type": "cut", "duration": 0}}]
}
```

Required fields: schemaVersion, projectId, title, video, scenes. Optional assets/characters/audio may be omitted; author arrays when present. Description and asset type are metadata. Asset family controls font loading; seed initializes randomness (prefer a positive integer). **Not supported:** manifest camera configuration. Unknown properties are preserved, not interpreted as new features; schema allows additional properties to match storage behavior.

Schema describes well-typed production input, not every malformed/ignored/null value tolerated by C#. Prefer omission over null. Defaults/readOnly are annotations: they do not insert values or reject authored derived fields. Application overwrites total duration and scene start. Runtime-only end/overlap are not additional authoring fields.

### Rules requiring application/archive/code checks beyond portable JSON Schema

| Rule | Current requirement |
| --- | --- |
| IDs/references | IDs unique within scenes/assets/characters. Character assetId and scene background resolve to assets; scene characters resolve to characters; audio assetId resolves to audio and sceneId to scene. Audio id is optional metadata, not uniqueness-validated. |
| Files | Every asset path, scene source, optional html/css and helper import exists inside bundle. References alone do not draw backgrounds/characters: scene code must create nodes. |
| Video area | Width/height even integers 64–3840; FPS 24/30/60; **width × height <=8,294,400**, for video and effective render profile. Missing render dimensions/FPS fall back to video during validation. |
| Timeline | 1–80 scenes; .25–600 seconds each; total <=1800 seconds. Outgoing overlap <=half of both adjacent durations; final outgoing overlap zero. Derived starts/total recomputed on save. |
| Audio relations | duration .01–1800; start/offset 0–1800; volume 0–1; each fade 0–track duration. No validator requirement that track end <=story end or offset+duration <=source length; final mix is trimmed/padded to video duration. Audio asset extension must be lowercase .wav/.mp3/.m4a/.ogg. |
| ZIP bounds | HTTP ZIP 1–64,000,000 bytes; <=600 entries including directory entries. Saved project <=512 files and <=128,000,000 uncompressed bytes; each file <=16,000,000 bytes. Per-entry uncompressed/compressed ratio <=200 (denominator at least 1). No symlink or case-insensitive duplicate file path; actual decompressed size must equal declaration. |
| SafePath | <=200 C# string characters. Only Unicode letters/numbers, underscore, space, dot, hyphen, slash. No leading slash, backslash, colon, percent, question mark, hash, empty/dot/dot-dot component, component ending dot/space, Windows reserved basename CON/PRN/AUX/NUL/COM<digit>/LPT<digit> (case-insensitive, also before extension). Schema uses a portable partial pattern; Unicode whitelist/reserved names remain application checks. Prefer lowercase ASCII paths and exact URL case. |
| Extensions/content | Case-insensitive allowlist: .json .js .svg .html .css .png .jpg .jpeg .webp .wav .mp3 .m4a .ogg .ttf .woff2. Scene source specifically lowercase .js; .mjs helper files are not allowed in ZIP. JSON must parse; JS/CSS/HTML/SVG valid UTF-8; binary signature checks do not guarantee successful media decoding. |
| SVG | Root SVG, DTD disabled; reject script/foreignObject, attributes beginning on, http/https/file/javascript: or @import in attribute values, href not beginning #. Runtime also rejects malformed/active SVG. Story validation differs from legacy whiteboard. No remote/data-URI image href in Story SVG; use declared raster assets through DOM if needed. |
| JS/imports | Scene regex requires named `export function createScene(` or `export async function createScene(`. All JS parsed without execution through Node --input-type=module --check. Recognized import strings begin dot and resolve to existing bundle files; include extensions. No npm/CDN imports. |
| Runtime | Valid lifecycle, finite implementation duration, decoded fonts/images, actual part IDs, terminating code and deterministic seek require execution. |

Manifest render.crf accepts a number 10–35, but render API StoryRenderOptions requires **integer** CRF: author integers. Schema documents that boundary. Actual render options are a separate API request; UI submits its selected profile, not automatically all manifest values. Preview logical dimensions use video.width/height. UI maps output options to standard aspect/resolution presets; verify nonstandard profiles explicitly.

## 2. Scene module and exact signature

```typescript
// Documentation notation only; ZIP contains JavaScript, not TypeScript.
export function createScene(context: SceneContext): SceneImplementation;
// Also accepted: export async function createScene(context): Promise<SceneImplementation>
interface SceneImplementation {
  duration: number;          // finite >0, implementation-local seconds
  seek(time: number): void;  // synchronous; runtime does not await it
  reset(): void;
  dispose(): void;
}
```

Use named function exports, not default/arrow export/re-export alone: source regex does not accept these as scene entrypoints. Helpers can use normal ES exports. Import top-level code runs before createScene; avoid side effects. Initialization is awaited once; required assets are already preloaded. Async seek/reset/dispose sequencing: **Not supported**.

## 3. Actual context API (exhaustive)

| Member | Behavior |
| --- | --- |
| root | HTML .story-camera container, transformed by camera, containing SVG canvas and optional HTML. |
| sceneRoot | HTML .story-scene wrapper; runtime owns visibility/opacity/transform for compositing. Avoid competing animation on these properties. |
| canvas | Native SVG with viewBox `0 0 width height`. |
| width, height | Logical manifest.video dimensions, independent of output viewport. |
| duration, sceneId | Manifest scene duration in seconds and ID. |
| gsap | Actual shared GSAP object. |
| timeline(options={}) | Paused GSAP timeline. `{nested:true}` removes that custom option and unpauses child for addition to controlled parent. Returns GSAP timeline. |
| assetText(id) | TextDecoder of preloaded asset bytes; missing ID throws. |
| assetUrl(id) | Existing declared asset's bundle-local URL, not filesystem path. |
| addSvg(markup, options={}) | Parse SVG, copy its **children** into new g; append to options.parent or canvas. Apply x/y default 0, scale default 1, transformOrigin center center, optional id. Return group. |
| svg(markup) | addSvg shorthand; no options forwarded. |
| character(id, options={}) | Find manifest character, clone its asset with addSvg options, set data-character; return group. Warn when parts absent/empty. |
| camera | Mutable `{x:0,y:0,scale:1,rotation:0}` object, applied after seek. |
| follow(target) | Set tracked SVG node; derive camera translation from getBBox center plus GSAP x/y. Returns undefined. follow(null) clears. |
| stroke(target) | Selector string scoped to root or one getTotalLength-capable node. Set dasharray/dashoffset to length; return original argument. No array/NodeList overload. |
| random() | Stateful PRNG for initialization only; scene seed `(manifest.seed || 1)+sceneIndex*1009`. Reordering changes seed. |
| noise(index) | Stateless first PRNG value from `(manifest.seed || 1)+Number(index)*1009`; no scene offset or smooth interpolation. |

**Not supported:** context.assets, loadAsset, audio, time, deltaTime, events, physics, rig, setExpression, interact, or other invented helpers. An error message mentions context.assets, but that property does not exist; use assetText/assetUrl.

## 4. Lifecycle

Load declared assets/fonts → install runtime controls → create every scene DOM/context → load optional HTML/CSS → import module → await createScene inside GSAP context → validate returned object → await fonts/images → seek zero and resize. All scenes initialize before ready. Thumbnail generation also seeks scene times then restores previous master time.

Each master seek hides wrappers, applies active scene(s) and composites transition. Inactive scenes are not replayed or disposed. reset is required but **not automatically called on backward seek or scene change**. seek alone must reconstruct state. Dispose command calls implementations, reverts GSAP scopes, clears global timeline/DOM. Dispose your custom listeners/resources; do not rely on it for visual transitions.

## 5. GSAP and bundled plugins

GSAP **3.15.0**, **MotionPathPlugin**, **MorphSVGPlugin** are locally loaded; plugins register when available. Use context.gsap, no new library imports. Core APIs used by samples include set/to/fromTo, timeline.add, SVG attribute animation, transforms, easing and finite repeat/yoyo. Morphing requires authored paths; it does not create rigs. Other bundled plugins: **Not supported**.

Ticker sleeps and wake is disabled; created timelines are paused. Timeline time/totalTime/seek setters force suppressEvents=true. Use `timeline.time(t,true)`. Avoid visual state in onUpdate/onComplete/.call callbacks, which are suppressed on seek. Add context.timeline({nested:true}) children to paused master; autonomous tween playback is **Not supported** as a timing mechanism.

## 6. SVG and shared character access

```javascript
const hero = context.character('may', {x:100,y:450});
const eyes = hero.querySelector('#eyes');
context.addSvg(context.assetText('forest'));
context.stroke('#draw-path');
```

These fragments require declared assets/real part nodes; section 14 is self-contained. Scope selectors to character/root. Shared artwork is cloned on each character call/per scene; no persistent actor state.

addSvg does **not copy root viewBox, dimensions, class/style/transform/presentation attributes**. Put required styling/transforms on child groups; author coordinates for logical canvas. Namespace gradient/definition IDs and update url(#id) references: all scenes share one document. For raster art create an HTML img within root with assetUrl(id), appropriate dimensions and awaited load. Custom SVG DOM can use document.createElementNS with the SVG namespace.

## 7. Facial animation

Animate actual authored SVG parts; for an eyes group:

```javascript
const eyes = hero.querySelector('#eyes');
if (!eyes) throw new Error('Character requires #eyes');
timeline.fromTo(eyes, {scaleY:1}, {
  scaleY:0.08, transformOrigin:'50% 50%', duration:0.12,
  repeat:1, yoyo:true, ease:'sine.inOut'
}, 1);
```

Animate mouth/brows through transforms, attributes, opacity or MorphSVG on authored paths. parts is advisory; no existence validation or rig creation. Expression library, facial rig API, automatic lip sync/talking head: **Not supported**.

## 8. Character interactions

```javascript
const may = context.character('may', {x:80,y:450});
const bong = context.character('bong', {x:620,y:450});
timeline.fromTo(may, {x:80}, {x:260,duration:2,ease:'sine.inOut'}, 0);
timeline.fromTo(bong, {x:620}, {x:420,duration:2,ease:'sine.inOut'}, 0);
```

Interactions are authored choreography on one paused timeline. For handoff animate a real prop and relevant arms at explicit times. Collision/physics/IK, semantic action APIs, click branches and cross-scene memory: **Not supported**. MP4 contains no interactivity.

## 9. Camera and transitions

Animate camera object with GSAP, e.g. `timeline.fromTo(context.camera,{x:0,y:0,scale:1,rotation:0},{x:-30,y:-15,scale:1.05,rotation:0,duration:3},0)`. Runtime applies CSS translate → rotate → scale, origin center. follow(target) overrides x/y with simple bbox-plus-position tracking, preserving scale/rotation. It does not solve arbitrary world transforms or zoom-aware framing. Camera manifest keyframes and camera.panTo/zoomTo: **Not supported**.

Transitions are outgoing: cut/fade/slide. Missing type=cut. Cut ignores duration, effective overlap=0. Fade/slide default overlap=.5 seconds; explicit duration 0–600 subject to half-duration bounds of both neighbors. Fade changes incoming opacity; slide moves outgoing left and incoming from right. Custom direction/easing/transition API: **Not supported**. Final scene should use cut duration 0; final fade/slide is only accepted with explicit zero overlap.

## 10. Scene-local time

```text
start[0] = 0
start[i+1] = start[i] + duration[i] - outgoingOverlap[i]
storyDuration = sum(duration[i] - outgoingOverlap[i])
local = masterTime - start[i]
implementationTime = local * implementation.duration / manifestScene.duration
```

Master time clamps to [0,total]. Scene start inclusive/end exclusive; final scene includes exact final endpoint. Overlaps seek both scenes at their own local times. JS implementation duration can differ from manifest duration: runtime scales it. Native SVG SMIL/CSS/Web Animations instead pause and receive **manifest-local** t seconds / t*1000 ms. Keep both durations equal when mixing them. Frame delta, automatic simulation/replay from zero or scene-entry events: **Not supported**.

## 11. Deterministic seek

Same timestamp must reconstruct same picture after arbitrary forward/backward/repeated seeks. readyFrame seeks twice around font readiness. Use absolute GSAP timelines or pure time functions. Initialize context.random once, not on seek; noise(index) is stateless. Give explicit from/to values where prior state matters; restore every property seek modifies. Do not increment state, consume RNG or change DOM based on traversal history. reset is not a recovery mechanism.

Exporter checks decoded frame pixels at c,min(1,D),min(8,D),0,c where c=min(5,D/2). The repeated frame may differ by at most 1/255 in a channel on fewer than 0.1% of pixels, matching the accepted Chromium compositor tolerance; larger differences fail. This probe is not proof for every time: test additional timestamps and overlaps.

## 12. Prohibited/unsupported behavior

Source lint rejects direct calls matching Date.now, Math.random, setTimeout, setInterval, requestAnimationFrame, fetch, WebSocket, XMLHttpRequest, Worker, SharedWorker, eval, and repeat:-1. Regex can match comments/strings and is not a full analyzer; do not evade it via helpers/aliases.

Runtime blocks fetch/timers/RAF/Math.random, WebSocket/XHR/workers/EventSource/WebTransport/WebRTC constructors and window.open; Date default/now and attempted performance.now become zero. These are not a security proof. Use official browser isolation/CSP/guarded worker. External network/scripts, dynamic eval, workers, filesystem access and nonterminating loops are invalid. No Node/server APIs inside scenes.

Optional HTML enters innerHTML and CSS a style node. Scope CSS to `.story-scene[data-scene="scene-001"]`. HTML script tags are not supported lifecycle. Arbitrary third-party HTML packages and autonomous browser animation timing: **Not supported**.

## 13. Preview, audio and MP4

Preview runs sandbox allow-scripts iframe on 5189, controlled by parent Studio 5188 with source/origin/channel/token-checked postMessage. window.storyReady and window.storyRenderer.readyFrame(masterTime) are exporter/runtime hooks, **not context APIs**. Scene code must not drive parent transport.

Playwright export uses same runtime in Chromium/Chrome/Edge with offline routing restricted to runtime and immutable snapshot. Render via Studio/API; current worker requires Windows x64 Job Object boundary. Do not spoof guard environment variable to invoke Python directly.

For output FPS F, N=ceil(totalSeconds*F). Frame k seeks k/F for k=0…N−1, PNG streams to FFmpeg libx264/yuv420p; effective duration N/F. Exact final timeline endpoint is normally not sampled. Actual API render options: dimensions/area/FPS above, integer CRF 10–35 default18, preset ultrafast/veryfast/medium default veryfast. ffprobe checks frame count, codec/pixel format, dimensions, FPS/duration and audio presence when scheduled.

Audio is manifest-driven, not scene JS. start is global unless sceneId adds derived scene start; offset trims source; duration/volume/fades schedule interval. Parent HTMLAudioElement previews it; FFmpeg trims/resamples/mixes at 48kHz to AAC. No tracks = silent MP4. No TTS, context.audio, procedural sound engine, speech API or lip sync: **Not supported**. Supply declared local audio files.

## 14. Minimal runnable JavaScript

Save exactly as scenes/scene-001.js with the manifest in section 1. No character/font/audio/other asset required.

```javascript
export function createScene(context) {
  const art = context.svg('<svg xmlns="http://www.w3.org/2000/svg"><rect width="720" height="1280" fill="#173b40"/><circle id="dot" cx="100" cy="640" r="42" fill="#ffd68a"/></svg>');
  const dot = art.querySelector('#dot');
  const timeline = context.timeline();
  timeline.fromTo(dot, {x:0}, {x:480,duration:3,ease:'none'}, 0);
  return {
    duration:3,
    seek(time) { timeline.time(time,true); },
    reset() { timeline.pause(0); },
    dispose() { timeline.kill(); }
  };
}
```

## 15. Sources and verification

Authoritative files: Core/StoryProjects.cs (DTOs/validation/ZIP/store), StorySyntax.cs; Web/Controllers/StoriesController.cs, StoryPreview.cs, wwwroot/story/runtime.js, timeline.mjs, runtime.html, studio.mjs; Worker/RenderWorker.cs, StoryProcessBoundary.cs; engine/story_render.py. Examples checked against samples/lost-star and samples/may-bong-episode-01, including existing ZIP exports.

Pack contains sample-story.zip, unchanged from the application's exported Mây & Bông v1 ZIP: 3 scenes/14s, two shared SVG characters, audio. Import **that nested ZIP**, not the outer documentation pack. Prior official export/re-import and MP4 acceptance details are in workspace docs/may-bong-episode-01.md. New verification results for this documentation are recorded below after checks.


### Verification for this documentation revision

- JSON parsing, schema vocabulary/internal-reference/regex checks: PASS. A dependency-free local checker evaluated the standard keywords actually used in this schema; no new dependency was installed. This is not a claim of independent full meta-schema certification by a general-purpose validator.
- Schema plus semantic asset/character/audio/timeline reference checks: PASS for both source manifests (lost-star and may-bong-episode-01) and three existing ZIP manifests (lost-star ZIP, public lost-star sample ZIP, application-exported Mây & Bông ZIP).
- Minimal manifest: PASS. Seven negative cases rejected: missing scenes, odd dimension, invalid FPS, short scene, traversal source, bad source extension and forbidden asset extension.
- Exact section-14 code extracted from this document: Node syntax PASS; actual shared browser runtime PASS on Chrome 156.0.8078.80. GSAP x positions 0/240/480 at 0/1.5/3 seconds; exact full-size PNG hashes after reverse seek; reset/dispose; no page errors.
- Documentation pack CRC and unchanged nested sample SHA-256 verified. No engine/application code changed. No new MP4 render was needed for this documentation task; nested sample's prior real render is documented separately.
