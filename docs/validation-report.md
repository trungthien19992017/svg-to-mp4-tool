# Character Pack V4 validation

## Inputs

Production SVG rigs, facial states, pose and interaction catalogs, latest accepted pair preview and animation-code-contract(4).md were available.
The supplied story-production-contract.zip contains sample-story.zip. Its real manifest and file structure were inspected.
Missing execution input: Studio application/runtime and an accessible running Studio instance. Its actual GSAP bundle was also unavailable locally.

## Performed checks

- robot-male.svg XML, unique IDs, local fragment references, security attributes PASS
- robot-male.svg 12 independent front expression states PASS
- robot-female.svg XML, unique IDs, local fragment references, security attributes PASS
- robot-female.svg 12 independent front expression states PASS
- Rig parent references, finite local pivots and anchor coordinates PASS
- Offline preview JavaScript syntax PASS
- Two-scene manifest references and explicit final cut PASS

## Execution and visual limitations

Actual Studio integration: NOT RUN.
GSAP 3.15.0 execution: NOT RUN. The Studio scene requires context.gsap.version === "3.15.0".
Forward/backward seek, reset, idempotent dispose, scene overlap boundaries and multiple instances: implemented, execution QA pending.
Visual pose QA, z-order under movement, pivot rotation continuity, joint silhouette continuity and contact/collision QA: pending.
Instance IDs are reserved and prefixed, fragment references are rewritten before addSvg. Execution collision QA remains pending.
All static poses remain Partial pending visual and structural execution QA. Unsupported interactions retain that status.
Female left view is the explicitly approved mirrored right view, including the heart.

## Runtime contract

scenes/scene-001.js uses only context.gsap, context.timeline, context.assetText, context.addSvg, context.sceneId and context.duration.
It supplies synchronous duration/seek/reset/dispose lifecycle. Paused timeline writes a clock object; seek applies authored states explicitly after timeline.time(t,true).
Scene code contains no timers, RAF, random consumption, network operations or event-driven visual callbacks.
The offline HTML preview uses browser playback controls outside Studio. Its RAF and controls are not scene code.
Production SVG has local vector content only. The nested couple preview may embed raster references in HTML for review.

## Availability

Front facial expressions: Partial, exactly 12 IDs per character, independently controllable eyes/brows/mouth/cheeks/tears/highlights.
Other-view facial expression swapping: Unsupported. Authored faces remain present.
Poses: idle and arm-review implemented in offline preview. Other catalog poses require artwork binding.
Interaction controls: all nine listed, first three rig previews, remaining reference-only or asset requests.
The arm-review pose is a technical rotation diagnostic, not a newly approved storytelling pose.
Couple preview preserves the accepted implementation; numerical contact and limb limits remain Partial.
Mirrored SVG anchors are source-local and require the documented mirror transform.

## How to use

Open character-preview.html directly for offline review.
Import studio-sample.zip into Studio to test the two-scene lifecycle project.
character-pack-v4.zip is an asset delivery archive, not a Story ZIP. Its documentation .md files are outside the Studio Story allowlist.
