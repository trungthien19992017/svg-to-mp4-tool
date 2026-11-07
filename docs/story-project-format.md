# SVG Story Project Format v1

Import ZIP with `story.json` at root, or inside one common wrapper directory. Recommended files:

```text
story.json
assets/characters/may.svg
assets/backgrounds/forest.svg
assets/objects/star.svg
scenes/scene-001.js
scenes/scene-002.js
audio/sfx/chime.wav
metadata/storyboard.json
```

Schema: [story.schema.json](story.schema.json). Animation lifecycle: [animation-code-contract.md](animation-code-contract.md). These are the instructions to give ChatGPT along with the example ZIP when generating a compatible story. The app does not infer a timeline from arbitrary unrelated JavaScript; modules must obey the published contract.

Required manifest fields are schemaVersion `1.0`, stable projectId/title, logical video dimensions/FPS, and scenes. Each scene has a unique stable ID, source `.js`, duration and optional outgoing transition, HTML and CSS. Assets have stable IDs and ZIP-relative paths. Characters refer to a single SVG asset and list optional rig part IDs. Audio tracks refer to audio asset IDs and scheduling parameters.

Native video coordinates stay fixed for a project; export resolutions scale the stage with centered letterboxing when a different aspect ratio is selected. Video dimensions must be even, 64–3840 pixels, maximum 8,294,400 output pixels. 24/30/60 FPS; H.264/yuv420p; CRF 10–35. Changing scene duration scales its code's local time. No source edit is needed for every scene before importing/rendering.

Outgoing transition overlap: `start(i+1)=start(i)+duration(i)-overlap(i)`. Total is the sum of durations minus overlaps. Supported: cut (zero overlap), fade, slide. Overlap cannot exceed half of either adjacent scene duration. Last scene must be cut; reordering in the UI makes the new last scene cut and tells the user. Canonical `start` and `duration` are recalculated by the validator.

Limits: 64 MB ZIP upload, 128 MB expanded project, 16 MB/file, 512 published files, 80 scenes, 30-minute story, maximum compression ratio 200:1. Reject symlinks, traversal/drive/UNC paths, case-colliding files, unknown extensions, mismatched image/audio/font signatures, invalid JSON/XML, unsupported schema, duplicate IDs, missing references, unsafe SVG content and common forbidden scene APIs. JavaScript is executed only in the browser runtime. The linter does not parse/guarantee all JS semantics.

Save creates a new immutable revision under `data/stories/<storage-id>/revisions/<revision>`. Storage ID is separate from the manifest's projectId. Previous snapshots remain for running jobs. Optimistic concurrency rejects stale saves. Job records retain project/revision, exact output settings and timestamps. Existing whiteboard/doodle jobs and source files remain in their original data store.

API: `GET/POST /api/stories`, `POST /api/stories/import` multipart field `file`, `GET/PUT /api/stories/{id}` (PUT query `revision`), `GET .../export`, `GET .../files/{path}?revision=...`, `POST .../render`. Mutations require the anti-CSRF token obtained from `/api/session`. File reads in the main app return code/SVG as plain text. Executable scene modules are served only on the isolated preview port or from the renderer's in-memory route handler.

Request bodies for save/create are `{manifest, files:{'scenes/scene-001.js':'...'}}`; PUT merges edited text files into the current revision. Import/export retains binary assets. Additional assets can be introduced by editing/reimporting the ZIP; a graphical rig editor and arbitrary binary-upload asset editor are outside this first implementation.
