# PHASE 00 — Story Production Contract & Capability Matrix

Đối chiếu source ngày 2026-11-07. Contract cho AI sản xuất **Story Format v1 (`schemaVersion: "1.0"`)** trên engine hiện tại. Không thêm API, không thay đổi format hoặc engine. Import thành công chỉ xác nhận cấu trúc/validation; chưa chứng minh chất lượng chuyển động, tiếp xúc hay continuity.

## 1. Nguồn và thứ tự thẩm quyền

| Nguồn bắt buộc | Nội dung đã đối chiếu |
| --- | --- |
| [StoryProjects.cs](../src/SvgToMp4.Core/StoryProjects.cs) | Models, `StoryValidation`, `SafePath`, normalization, `StoryStore.Import/Save/Export`. |
| [StorySyntax.cs](../src/SvgToMp4.Core/StorySyntax.cs) | Parse tất cả JS bằng Node, không thực thi khi import. |
| [runtime.js](../src/SvgToMp4.Web/wwwroot/story/runtime.js), [runtime.html](../src/SvgToMp4.Web/wwwroot/story/runtime.html), [runtime.css](../src/SvgToMp4.Web/wwwroot/story/runtime.css) | Context thực tế, loader, GSAP lifecycle, camera, SVG/HTML/CSS seek. |
| [timeline.mjs](../src/SvgToMp4.Web/wwwroot/story/timeline.mjs), [studio.mjs](../src/SvgToMp4.Web/wwwroot/story/studio.mjs) | Timeline, overlaps, transport, audio preview. |
| [StoriesController.cs](../src/SvgToMp4.Web/Controllers/StoriesController.cs), [StoryPreview.cs](../src/SvgToMp4.Web/StoryPreview.cs) | HTTP import/export/render, origin và tài nguyên preview. |
| [story_render.py](../engine/story_render.py), [StoryProcessBoundary.cs](../src/SvgToMp4.Worker/StoryProcessBoundary.cs) | Frame sampling, kiểm tra deterministic, FFmpeg, giới hạn tiến trình. |
| [ZIP robot đã import thành công](../outputs/robot-episode-01-cham-mot-chut-thoi-fixed.zip) | 16 file, 5 cảnh 5/6/6/7/6 giây, tổng 30 giây; 2 nhân vật, 9 assets, 5 audio tracks; toàn bộ transition là cut. Đã import lại bằng Store thật trong lần kiểm tra này. |
| [demo-5.html](../../Hrml/Mascot_Rig/demo-5.html) | Tham chiếu artwork, SVG part IDs, pivot, biểu cảm, dáng đi và tương tác 5 giây. Không phải scene module hợp lệ. |

Source là thẩm quyền khi khác tài liệu hoặc ví dụ. Comment và metadata trong file tham chiếu chỉ là dữ liệu tham khảo; không mở rộng API hay thay thế yêu cầu của người dùng.

## 2. JSON Schema trích từ validation

Schema máy đọc: [story.schema.json](story.schema.json), draft 2020-12, đã đối chiếu lại với `StoryValidation.Validate/ValidateVideo/Number` trong phase này. Tái sử dụng file hiện hữu, không tạo biến thể Story v1. [Animation Code Contract hiện hữu](animation-code-contract.md) cung cấp phần giải thích bổ sung; contract dưới đây ghi trực tiếp các giới hạn cần cho production.

Schema là **profile input có kiểu dữ liệu rõ ràng để sản xuất**, không phải bản thay thế toàn bộ validator C#. `additionalProperties` được phép theo mặc định: trường lạ được lưu nhưng không tự tạo tính năng. Các khác biệt phải hiểu đúng:

- C# không kiểm tra riêng kiểu/miền giá trị của nhiều metadata (`description`, `seed`, asset `type`, `parts`, audio `id/name`); schema đặt kiểu để AI tạo input ổn định. `parts` không được kiểm tra có tồn tại trong SVG.
- `assets/characters/audio` không phải array, hoặc `render/transition` không phải object, có thể bị C# bỏ qua như không khai báo; đó không phải input production được khuyến nghị. Nhiều giá trị optional `null` cũng được coi là thiếu. Hãy bỏ trường optional thay vì ghi `null`.
- `duration` cấp project và `scene.start` do engine tính lại. Schema đánh dấu `readOnly` chỉ là annotation; importer vẫn nhận rồi ghi đè. Không dùng giá trị tự điền để điều khiển thời gian.
- Duration của transition `cut` bị bỏ qua, kể cả validation số của trường này; schema vẫn yêu cầu số hợp lệ nếu có. `render.crf` validator nhận số thực nhưng DTO render API yêu cầu số nguyên. Dùng CRF nguyên.
- Pattern đường dẫn của schema chỉ kiểm tra một phần; `SafePath`, archive, tham chiếu chéo, cú pháp JS, binary signatures và runtime là các lớp bắt buộc riêng. Chưa chứng nhận schema bằng một thư viện meta-schema tổng quát.

| Manifest | Ràng buộc thực tế |
| --- | --- |
| Bắt buộc | `schemaVersion`, `projectId`, `title`, `video`, `scenes`. Version chính xác `"1.0"`; title không trắng, tối đa 160 ký tự C#. |
| IDs | Project/scene/asset/character: `^[A-Za-z0-9_-]{1,80}$`. Scene, asset, character IDs không trùng trong từng nhóm, so sánh phân biệt hoa thường. Audio `id` chỉ là metadata, không bắt buộc/không kiểm tra unique. |
| `video` | width/height số nguyên chẵn 64–3840, diện tích ≤8,294,400 px; fps 24/30/60; format thiếu/null hoặc `mp4`. |
| `render` | Optional width/height/fps cùng giới hạn video, validation fallback về video; crf 10–35, mặc định 18; preset `ultrafast/veryfast/medium`, mặc định `veryfast`. Render thật dùng options từ UI/API, không tự áp toàn bộ manifest render. |
| `scenes` | 1–80 object; mỗi cảnh có id, duration 0.25–600 s, source tồn tại với đuôi **`.js` chữ thường**. Tổng sau trừ overlap ≤1800 s. Optional html/css phải trỏ tới file tồn tại. |
| `assets` | Mỗi phần tử có id và path local tồn tại. `type` là metadata, không phải enum chọn decoder. Font asset đọc `family` hoặc dùng id làm tên FontFace. |
| `characters` | id và assetId đã khai báo. `parts` là danh sách mô tả advisory, không tự tạo rig hay selector API. |
| Scene refs | `characters` chỉ tham chiếu character đã khai báo; `background` chỉ tham chiếu asset. Khai báo không tự render: code phải gọi `character/addSvg` hoặc tạo DOM. |
| `transition` | Type thiếu ⇒ cut; chỉ cut/fade/slide. Fade/slide duration mặc định 0.5 s, ≥0 và ≤nửa thời lượng **cả hai cảnh kề nhau**. Cảnh cuối overlap phải 0. Cut có overlap 0. |
| `audio` | assetId audio đã khai báo; duration bắt buộc 0.01–1800 s; start/offset 0–1800 mặc định 0; volume 0–1 mặc định 1; fadeIn/fadeOut mỗi giá trị 0–duration mặc định 0; sceneId optional phải tồn tại. |

Các kiểm tra chéo không diễn đạt hoàn toàn bằng JSON Schema portable: unique theo trường ID, tồn tại file/asset/character/scene, diện tích video, tổng thời lượng, giới hạn overlap giữa hàng xóm, fade ≤track duration và nội dung file.

## 3. ZIP, đường dẫn, audio và metadata

```text
story.json                         # đúng một manifest
scenes/scene-001.js                # tên/folder tùy chọn; manifest tham chiếu chính xác
modules/helpers.js                # optional, import tương đối có extension
assets/characters/hero.svg         # optional, assets khai báo trong manifest
assets/backgrounds/room.svg
audio/music.wav
metadata/storyboard.json           # optional, chỉ metadata
```

ZIP root hoặc một folder bọc chung đều được; mọi file phải nằm dưới prefix của đúng một `story.json`. Không có đường dẫn ngoài prefix, symlink hoặc duplicate đường dẫn không phân biệt hoa thường. Export ghi đường dẫn tương đối và manifest đã normalize; projectId trong manifest khác GUID nội bộ dùng lưu project/revision.

- HTTP upload: file ZIP >0 và ≤64,000,000 byte; giới hạn request 70,000,000 byte. Archive ≤600 entries kể cả directory; project lưu ≤512 file, tổng giải nén ≤128,000,000 byte. Mỗi file ≤16,000,000 byte, tỷ lệ giải nén/nén ≤200 (mẫu số ít nhất 1), số byte đọc phải đúng khai báo.
- `SafePath`: tối đa 200 ký tự C#, dùng `/`, chỉ Unicode chữ/số hoặc `_ .-/`. Cấm slash đầu, backslash, `: % ? #`, thành phần rỗng/`.`/`..`, thành phần kết thúc dot/space; cấm basename Windows CON/PRN/AUX/NUL/COM+một chữ số/LPT+một chữ số, không phân biệt hoa thường, kể cả trước dấu chấm. Ưu tiên ASCII chữ thường và đúng case trong mọi URL/import.
- Extensions allowlist không phân biệt hoa thường: `.json .js .svg .html .css .png .jpg .jpeg .webp .wav .mp3 .m4a .ogg .ttf .woff2`. Không `.mjs`, `.mp4`, `.gif`, `.webm` trong Story ZIP hiện tại. Source scene và asset được track audio tham chiếu riêng yêu cầu đuôi chữ thường.
- JSON phải parse được; JS/CSS/HTML/SVG phải UTF-8 hợp lệ. File nhị phân được kiểm tra magic signature: PNG/JPEG/WebP, RIFF/WAVE, ID3 hoặc MP3 frame header, OggS, M4A ftyp, font TTF/OTTO/WOFF2. Signature đúng chưa bảo đảm decoder chạy được.
- SVG root phải là svg; cấm DTD, script/foreignObject, attribute bắt đầu `on`, URL http/https/file/javascript hoặc `@import` trong attribute, href không bắt đầu `#`. Không nhúng nguyên demo HTML/script vào SVG. Raster nên dùng `<img>` với assetUrl, không external/data href trong SVG.
- Tất cả JS được Node parse module không thực thi. Import được nhận diện bằng regex phải bắt đầu `.` và resolve tới file trong bundle; dùng extension `.js`; không CDN/npm/absolute import. Validator regex không phải bộ phân tích toàn bộ hành vi.

Audio local nhận `.wav/.mp3/.m4a/.ogg`; khả năng codec cụ thể phụ thuộc browser/FFmpeg. Production dễ kiểm chứng nhất là WAV PCM; đây là khuyến nghị, không phải giới hạn bắt buộc của format. Preview dùng HTMLAudioElement ở Studio, đồng bộ theo timeline với ngưỡng sai lệch 0.15 s; không bảo đảm sample accuracy. Export resample 48 kHz, trim offset/duration, volume, fade tuyến tính, delay rồi amix `normalize=0`, pad/trim tới video, encode AAC 192 kbps. Nhiều track có thể clipping; AI phải tự cân gain.

`start` là global trừ khi có `sceneId`: lúc đó cộng start dẫn xuất của scene. `offset` là vị trí đọc trong file. Validator không probe độ dài audio, không bắt `offset+duration` nằm trong nguồn hoặc track end nằm trong story. Track không tự loop, không tự duck, không tự lip-sync. Không có track ⇒ MP4 không audio.

Metadata hợp lệ là JSON parse được ở đường dẫn an toàn hoặc trường bổ sung của manifest. Không có schema runtime cho `metadata/storyboard.json`, contact, action, expression hay continuity. Robot mẫu có `contact.female_hand_source`, `male_hand_source`, translations và ghi chú kiểm tra bằng mắt; loader không đọc chúng. Không được coi metadata được lưu là feature được hỗ trợ.

## 4. Animation Code Contract chính xác

```javascript
export function createScene(context) {
  // Hoặc export async function createScene(context), được await khi khởi tạo.
  const timeline = context.timeline();
  // Tạo artwork, set pose ban đầu, thêm tween hữu hạn tại thời điểm tuyệt đối.
  return {
    duration: context.duration,         // số finite > 0, giây implementation
    seek(time) { timeline.time(time, true); }, // synchronous
    reset() { timeline.pause(0); },
    dispose() { timeline.kill(); }
  };
}
```

Đây là skeleton, sample hiển thị thật ở mục 8. Import regex chỉ nhận named `export function createScene(` hoặc `export async function createScene(`. Default export, arrow export hoặc re-export đơn thuần không đủ. Runtime bắt buộc object có duration finite >0 và ba hàm seek/reset/dispose; không await ba lifecycle methods. Runtime không gọi reset khi quay ngược hay đổi cảnh.

**Toàn bộ context hiện tại:**

| Member | Hành vi |
| --- | --- |
| `root`, `sceneRoot`, `canvas` | `.story-camera` HTML container, `.story-scene` wrapper, SVG canvas. Runtime sở hữu wrapper visibility/opacity/transform cho transition. |
| `width`, `height`, `duration`, `sceneId` | Kích thước logical từ manifest video, thời lượng và ID cảnh. |
| `gsap` | GSAP thật dùng chung; không cần import library. |
| `timeline(options={})` | Paused timeline; `{nested:true}` bỏ custom option và unpause child để thêm vào master paused. |
| `assetText(id)` | TextDecoder từ bytes asset đã preload; ID thiếu ⇒ throw. |
| `assetUrl(id)` | URL asset đã khai báo trong cùng bundle; không phải filesystem path. |
| `addSvg(markup, options={})` | Parse SVG, copy **children** vào `<g>`, append `options.parent` hoặc canvas; options id/x/y/scale; mặc định x=y=0, scale=1, transformOrigin center center; trả group. |
| `svg(markup)` | Shorthand addSvg, không chuyển options. |
| `character(id, options={})` | Clone asset của manifest character bằng addSvg, gắn data-character, trả group; cảnh báo nếu parts thiếu/rỗng. |
| `camera` | Object mutable `{x:0,y:0,scale:1,rotation:0}`; được áp sau implementation.seek. |
| `follow(target)` | Theo bbox tâm SVG + GSAP x/y; ghi đè camera translation; `follow(null)` tắt. Không giải mọi nested transform/zoom. |
| `stroke(target)` | Selector scoped trong root hoặc một node có getTotalLength; set dasharray/dashoffset bằng length; trả đối số gốc. Không nhận NodeList/array. |
| `random()` | PRNG có state, seed `(manifest.seed || 1)+sceneIndex*1009`, dùng khi khởi tạo; đổi thứ tự cảnh đổi seed. |
| `noise(index)` | PRNG một lần từ `(manifest.seed || 1)+Number(index)*1009`; stateless, không phải smooth noise, không có scene offset. |

Không có `context.assets`, `loadAsset`, `rig`, `setExpression`, `walk`, `contact`, `audio`, `time`, `deltaTime`, physics hay state chia sẻ. Dù thông báo chặn fetch nhắc `context.assets`, property đó không tồn tại.

### Asset và SVG

Tất cả manifest assets được fetch trước khi createScene; TTF/WOFF2 đăng ký FontFace. Dùng `context.addSvg(context.assetText('room'))`, `context.character('female', {x:120,y:920,scale:1.35})`; query part bằng `actor.querySelector(...)`, kiểm tra node tồn tại. `parts` không đảm bảo node thật.

`addSvg` không giữ attributes của root SVG: viewBox, width/height, style/class, transform, fill/stroke ở root có thể mất. Đưa thuộc tính cần thiết vào child group, dùng hệ tọa độ logical của canvas; nested artwork cần scale/translate tường minh. Clone có thể trùng ID giữa cảnh/actor: scope selector và namespace defs/gradient IDs cùng `url(#...)` references. Runtime không tự namespace.

HTML/css optional được chèn trước createScene; CSS không tự scope, hãy giới hạn dưới `[data-scene="..."]`. Raster tạo DOM img bằng assetUrl, chờ decode khi khởi tạo. Runtime chờ fonts và các img có trong stage sau initialization; không hứa chờ mọi CSS background hay asset thêm muộn.

### GSAP lifecycle

Runtime load GSAP local **3.15.0**, MotionPathPlugin và MorphSVGPlugin; register plugin khi có. Không giả định plugin khác được nạp. Mọi scene khởi tạo trước khi ready; module top-level chạy trước createScene. GSAP context bao quanh lệnh gọi createScene; code sau await trong async init nên tự quản lý/kill tài nguyên rõ ràng.

Ticker bị sleep, wake bị vô hiệu; timeline được ép paused. Setters time/totalTime/seek của timeline ép `suppressEvents=true`. `.call`, onUpdate/onComplete không được dùng để tạo trạng thái hình ảnh cần seek. Không dùng autonomous tweens/delayedCall làm đồng hồ. Child timeline dùng `context.timeline({nested:true})`, add vào master paused và seek master. Repeat/yoyo phải hữu hạn.

Thứ tự load: assets/fonts → runtime controls → scene DOM/context → CSS/HTML → import module → await createScene → kiểm tra lifecycle → fonts/img readiness → seek(0). Thumbnails cũng seek sang các mốc rồi quay về. Dispose gọi implementation.dispose, scope.revert, clear global timeline/DOM; code scene phải dọn resources tự tạo.

Source lint cấm direct call Date.now/Math.random/setTimeout/setInterval/requestAnimationFrame/fetch/WebSocket/XMLHttpRequest/Worker/SharedWorker/eval và `repeat:-1`; regex có thể match comment/string và không chứng minh toàn bộ code an toàn. Runtime tiếp tục chặn timers/network/random, cố định Date/performance clock. Không né lint bằng alias/helper. Không đưa CDN script, UI onclick, Node API hay code không kết thúc vào scene.

## 5. Supported / Partial / Unsupported

**Supported**: engine có cơ chế trực tiếp. **Partial**: có thể dựng bằng SVG/GSAP nhưng AI phải tự choreography/đo/kiểm tra. **Unsupported**: không có API/cơ chế tự động tương ứng trong source.

| Nhóm | Supported | Partial | Unsupported |
| --- | --- | --- | --- |
| Facial animation | Tween transform/opacity/attributes của SVG parts; MorphSVG khi plugin/paths hợp lệ. | Blink, nghiêng đầu, layer biểu cảm `data-e`, mouth shape phải tự dựng và evaluate theo local time. | Facial rig semantic, expression presets của engine, phoneme/viseme detection, lip-sync tự động. |
| Walking/poses | Animate root/limb, SVG pivots, finite repeat/yoyo trên timeline seek. | Walk cycle, bob, tốc độ dịch chuyển, lie/sit/stand phải tự phối; foot sliding phải kiểm tra. | `walkTo`, gait engine, ground/contact solver, IK, collision/physics. |
| Contact anchors | Đọc native SVG DOM/getBBox/getScreenCTM và tween transform thông thường. | Anchor do tác giả tự định nghĩa; đổi tọa độ qua ma trận, tính pose tay/prop theo t, tự đo sai số. | Manifest contact anchor có runtime semantics, auto hand alignment, constraint solver, auto parenting/handoff. |
| Camera | Object x/y/scale/rotation, tween GSAP, `follow(target)` cơ bản. | Follow dùng bbox + x/y, không đầy đủ nested/world/zoom transforms; framing phải kiểm tra. | Manifest camera track/keyframes, panTo/zoomTo, cinematic solver, auto continuity. |
| Audio | Local WAV/MP3/M4A/OGG; start/offset/duration/volume/fades, sceneId scheduling; preview và AAC mix export. | Codec/browser decode, transport preview sai lệch; source length/loudness/mix phải tự QA. | context.audio, TTS, auto lip-sync, audio-reactive rig, effect/duck/loop tự động. |
| Scene transitions | Outgoing cut/fade/slide, overlap hợp lệ và seek hai scene. | Pose/camera/prop continuity phải dựng giống nhau trong hai bản clone. | Custom transition type/direction/easing, state actor tự chuyển cảnh. |

### Đối chiếu cụ thể `demo-5.html`

Artwork có `f/m-root`, head/eyes/arm/leg IDs; sáu expression layers `default/happy/sad/surprised/satisfied/content`, pivots `svgOrigin` trong ORIGINS. Tương tác 5 giây: blink 0.3/0.5, nghiêng đầu 1.0, đưa tay 2.0, chạm khoảng 3.2–3.5, tim 3.4, thu pose 4.5–5.0. Đây là choreography tham khảo, không phải built-in actions.

Không import nguyên demo: CDN GSAP 3.12.2, script inline, window.onload, controls/onclick, `.call(applyExpr)`, autonomous tween trong applyExpr/motion, delayedCall cho chuỗi pose và infinite repeat của tear không tương thích contract seek. Chuyển artwork thành SVG sạch, giữ pivot trong scene JS; dựng timeline paused hữu hạn; đổi biểu cảm bằng thuộc tính timeline hoặc hàm thuần của local time. Walk 8 nhịp hữu hạn có thể port nhưng cần kiểm tra điểm tựa chân. Động tác chạm trong demo chỉ là góc/scale/translation tác giả đặt, không xác nhận anchor solver hay độ chính xác tiếp xúc.

ZIP robot đã dùng `expressionTracks/applyExpressions(time)` tính opacity lại mỗi seek thay cho callback. Tọa độ contact trong metadata không được engine thực thi và phải kiểm tra riêng.

## 6. Timeline, seek và transitions

```text
overlap[i] = 0 nếu cut, ngược lại transition.duration hoặc 0.5
start[0] = 0
start[i+1] = start[i] + sceneDuration[i] - overlap[i]
storyDuration = Σ(sceneDuration[i] - overlap[i])
localTime = masterTime - start[i]
implementationTime = localTime * implementation.duration / sceneDuration[i]
```

Master clamp [0,total]. Start inclusive/end exclusive, riêng cảnh cuối gồm endpoint tổng. Overlap gọi seek cả hai scene; fade chỉ tăng opacity của cảnh incoming từ 0→1, cảnh outgoing vẫn opaque. Slide đưa outgoing sang trái và incoming từ phải bằng phần trăm width, không đọc hướng/easing metadata.

Sau implementation.seek, runtime áp camera translate → rotate → scale trên cameraRoot, origin center; follow nếu có ghi đè x/y. Sau đó SVG SMIL nhận `setCurrentTime(localTime)` và DOM animations nhận currentTime=localTime*1000, đều paused. SMIL/CSS dùng **manifest-local time**, GSAP implementation dùng thời gian scale như trên: nên giữ hai duration bằng nhau khi phối hợp.

Exporter dùng runtime này, frame k ở k/F với k=0..ceil(D*F)-1; output duration ceil(D*F)/F, endpoint D thường không được lấy mẫu. MP4 H.264/yuv420p. Preview audio thuộc parent Studio, không nằm trong implementation.seek.

### Ràng buộc deterministic bắt buộc cho AI

1. Cùng timestamp phải tạo cùng hình sau mọi thứ tự seek xuôi/ngược/lặp; seek là synchronous, không lệ thuộc play/pause/callback hay frame trước. Runtime chỉ seek cảnh active, không reset/replay cảnh inactive.
2. Dựng timeline một lần với mốc tuyệt đối; khởi tạo pose đầy đủ; dùng fromTo/set khi cần để tránh GSAP đọc nhầm state cuối của tween khác. Với nhiều fromTo trên cùng property, kiểm soát immediateRender và kiểm tra cả t=0, trước/sau mốc tween.
3. Không tích lũy x+=..., delta simulation, DOM mutation phụ thuộc lịch sử hoặc random() trong seek. Random chỉ lấy khi init rồi lưu constants; noise(index) là lựa chọn stateless, dùng seed số nguyên ổn định.
4. Biểu cảm/visibility/contact tự tính phải gán lại **mọi** thuộc tính do code đó điều khiển ở mỗi seek, kể cả trạng thái trước và sau interval. Không trông đợi reset được gọi.
5. `readyFrame(t)` seek hai lần quanh document.fonts.ready; scene phải idempotent. Thumbnail generation có thể seek trước khi người dùng bấm Play. Không tải nội dung bất đồng bộ ở seek.
6. Export chỉ so hash PNG tại c,min(1,D),min(8,D),0,c với c=min(5,D/2); đây là probe giới hạn. AI cần kiểm tra thêm boundary, overlap, biểu cảm, contact, nhiều chu kỳ và timestamp ngẫu nhiên cố định. Không coi một probe PASS là chứng minh mọi thời điểm/mọi máy.

## 7. Scene continuity

Engine clone asset mỗi scene, không duy trì pose, biểu cảm, prop attachment hay camera giữa cảnh. Scene i+1 phải **tự dựng** pose đầu từ trạng thái mong muốn của scene i, không đọc DOM/state scene i. Mọi scene khởi tạo từ đầu, không có onEnter/onExit contract.

Với cut, đối chiếu outgoing tại duration và incoming tại 0: root position/scale, từng limb transform/pivot, expression opacity, prop transform, background, camera. Với overlap, incoming bắt đầu khi outgoing ở `duration-overlap`, không phải lúc outgoing kết thúc; kiểm tra cặp trạng thái trong cả khoảng chồng. Fade/slide không tự sửa continuity.

Giữ cùng logical canvas, asset coordinates và pivots; nhớ camera biến đổi cả sân khấu. Tiếp xúc tay/prop phải được tính trong cùng hệ tọa độ (native DOMPoint + getScreenCTM là API browser, không phải helper engine). Đặt tolerance đo trước nếu cần nghiệm thu; metadata contact không phải constraint. File storyboard có thể ghi pose đầu/cuối để AI tham khảo nhưng scene JS vẫn phải tái tạo.

Với ZIP robot mẫu: starts 0/5/11/17/24, total 30. Scene-003 có các set đầu cảnh để nối pose/camera scene-002. Comment continuity không chứng minh hình ảnh liên tục; kiểm tra seek deterministic và kiểm tra continuity là hai việc riêng.

## 8. Sample tối thiểu import được

Import trực tiếp [phase00-minimal.zip](../samples/phase00-minimal.zip). Nguồn: [story.json](../samples/phase00-minimal/story.json), [scene-001.js](../samples/phase00-minimal/scenes/scene-001.js). ZIP đúng hai file; không assets/audio/fonts/helper bên ngoài. Một circle chuyển x 0→480 trong 3 giây, canvas 720×1280, 24 fps, mặc định cut.

```json
{
  "schemaVersion": "1.0",
  "projectId": "phase00-minimal",
  "title": "Phase 00 - deterministic circle",
  "video": {"width":720,"height":1280,"fps":24,"format":"mp4"},
  "scenes": [{"id":"scene-001","duration":3,"source":"scenes/scene-001.js"}]
}
```

Scene dùng SVG nội tuyến sạch, `context.timeline()`, fromTo duration 3, seek bằng `timeline.time(time,true)`, reset pause(0), dispose kill. Đây là sample import, không phải documentation pack để import.

## 9. Validation và giới hạn nghiệm thu

Các kiểm tra phase này chạy trên source/runtime thực, không sửa engine:

- **PASS** actual `StoryStore.Import → Export → Import`: minimal (2 file/1 cảnh/3 s) và robot fixed (16 file/5 cảnh/30 s), byte equality toàn bộ project sau normalization; Node syntax checks nằm trong Save thật.
- **PASS** 7 negative cases qua actual StoryValidation: version, width lẻ, fps, duration ngắn, file thiếu, traversal source, final outgoing overlap.
- **PASS** bộ StoryChecks hiện hữu: 21 kiểm tra core (ZIP, references, revisions/conflict, paths, signatures, JS syntax, forbidden timer).
- **PASS** `node tests/story-timeline.mjs`: boundary/overlap/final endpoint, nonsequential locate, audio offset, PRNG.
- **PASS** `python tests/test_story_audio.py`: FFmpeg thật, video 72 frames/3 s, AAC, trim/offset/fades và khoảng im lặng hai đầu.
- **PASS** schema parse/vocabulary/internal refs/patterns, schema keywords đã dùng + semantic refs cho 7 manifests mẫu gồm hai ZIP của phase này; 7 schema negative cases. Checker local không phải thư viện JSON Schema tổng quát.
- **PASS** shared runtime offline trên Chrome 156.0.8078.80: minimal initialize, 9 lần seek qua 0/1.5/3 rồi đảo/lặp; x chính xác 0/240/480; PNG SHA-256 giống nhau tại timestamp lặp; reset/dispose và không page error.
- **PASS initialize/lifecycle, FAIL mở rộng deterministic** cho robot fixed: 48 lần seek qua danh sách dưới đây, xuôi → ngược → xuôi. PNG khác tại 25/24/5/0 s khi quay ngược; serialized DOM của **cảnh đang hiển thị** cũng khác, nên không thể giải thích kết quả này chỉ bằng rounding/compositor. Chưa xác định nguyên nhân gốc; không sửa sample/engine. Bộ probe mặc định của exporter không bao phủ các mốc này theo cùng thứ tự, vì vậy không thay kết quả trên bằng giả định rằng importer hoặc probe ngắn là đủ.
- **Đo tham khảo contact** ở 21.1 s: hai điểm local lấy đúng từ metadata `(245,305)` và `(135,305)`, đổi qua getScreenCTM của arm tương ứng, cách nhau **24.2074 px** trong viewport 1080×1920. Đây là khoảng cách hai điểm metadata, không phải phép chứng minh silhouette hai bàn tay có/không chạm. Chưa có tolerance nghiệm thu; không chứng nhận contact.
- **Giới hạn ID**: robot runtime tạo 80 ID trùng trong document sau khi clone 5 cảnh. Scoped selector vẫn cần thiết; gradient/defs references cần namespace nếu dùng. Không kết luận ID trùng là nguyên nhân lỗi seek khi chưa điều tra.
- **PASS** links file trong tài liệu, minimal ZIP CRC và byte equality với source sample. ZIP robot được giữ nguyên, SHA-256 `4a08aea06925bc7d60b48246ee6036af1396247282b144c5f3ab0c6ba29dc200`.

Timestamp robot đã kiểm tra, mỗi mốc 3 lượt: `0, 2.5, 4.999, 5, 7.5, 10.999, 11, 15.4, 16.999, 17, 21.1, 23.999, 24, 25, 29.999, 30`. Đây là kiểm tra giới hạn trên một browser/máy; không phải chứng minh mọi timestamp. Sai lệch deterministic là finding của phase này dù các bước kiểm tra khác PASS.

Không chạy full UI end-to-end hoặc encode MP4 robot mới trong phase contract. Không tuyên bố continuity, foot locking, anchor alignment hay chất lượng diễn xuất chỉ từ việc import/seek thành công. Không thay đổi Story Format v1 hoặc engine.
