# Episode Generator tích hợp — v1

Entry: **http://127.0.0.1:5188/episodes**, hoặc “Tạo tập từ Production Kit” trong Story Studio.
Import cập nhật `production-import-2` tự phân biệt Story ZIP/Kit ZIP. Story được chuyển tới Storyboard. Kit nguồn legacy chỉ được ánh xạ khi khớp chính xác SHA-256 trong `docs/production-kit-conversions.json`, sang một kit `testOnly` đã chuẩn bị trước; không tự chuyển đổi hoặc nâng trạng thái các kit không biết. Kit gốc của người dùng được giữ nguyên. Kiểm tra nhanh trên app đang chạy ngày 08/11/2026: Kit thử, Kit nguồn có ánh xạ và Story ZIP đều import PASS; không chạy render.
Source đã tích hợp; process cũ cần được khởi động lại bằng `start.ps1` sau khi các job đang chạy hoàn tất.
Không có thay đổi database/schema cũ. Không tự restart app hoặc hủy job.

## Tạo tập lần sau

1. Nhập Production Kit ZIP một lần. Kit được lưu riêng tại `data/production-kits/<kitId>/<version>.zip`.
2. Chọn mẫu của kit hoặc tự thêm cảnh/nhân vật. Có thể nhân bản một tập đã tạo, hoặc nhập JSON kịch bản.
3. Bấm **Tạo tập & mở Studio**, xem trước và dùng Render MP4 như hiện tại.

Form chỉ liệt kê capability Supported; bản nháp lưu trên trình duyệt theo SHA-256 của kit.
“Sao chép hướng dẫn cho AI” xuất danh sách capability thực, quy tắc và dữ liệu storytelling trong kit.
Dán hướng dẫn đó cùng ý tưởng vào cuộc trò chuyện, lấy JSON episode-1, sau đó nhập JSON vào form.
Không có cuộc gọi AI API hoặc chi phí AI phát sinh tự động trong ứng dụng.

Mỗi lần tạo sinh một project mới, có `metadata/episode.json` (kịch bản gốc) và `metadata/production-lock.json`.
Chỉnh scene code trong Studio không tự đồng bộ ngược về kịch bản gốc. Nhân bản dùng **kịch bản gốc**, không diễn giải lại code đã sửa.

## Manifest của Production Kit

Cấu trúc thư mục theo robot-series-production-kit đã thống nhất. Các catalog là array các object có id duy nhất.
Manifest chỉ rõ đường dẫn; compiler không đoán tên SVG/DOM node hoặc tên pose.

```json
{
  "schemaVersion":"production-1",
  "kitId":"robot-series",
  "title":"Robot Series",
  "version":"1.0.0",
  "rigVersion":"robot-rig-v1",
  "rig":"characters/character-rig.json",
  "video":{"width":720,"height":1280,"fps":24,"format":"mp4"},
  "catalogs":{
    "characters":"characters/character-catalog.json",
    "poses":"characters/pose-catalog.json",
    "expressions":"characters/expression-catalog.json",
    "motions":"motions/motion-catalog.json",
    "environments":"environments/environment-catalog.json",
    "audio":"audio/audio-catalog.json",
    "templates":"storytelling/scene-templates.json"
  }
}
```

characters/poses/expressions/motions là catalog bắt buộc (array có thể rỗng); ba catalog còn lại tùy chọn.
`demo-1` của bản demo trước vẫn đọc được và được đánh dấu minh họa trên UI.
ZIP thật chưa được cung cấp; cấu trúc catalog bên trong ZIP thật cần tuân theo profile này hoặc được chuyển đổi rõ ràng trước khi import.

| Catalog | Trường mỗi bản ghi |
|---|---|
| characters | id, label tùy chọn, status, artwork (SVG local) |
| poses | id, status, rigVersion, rotations: object joint-name → góc độ |
| expressions | id, status, rigVersion, nodeId (nhóm SVG biểu cảm) |
| motions | id, status, rigVersion, module, startPose, endPose, duration, requiredJoints: array, anchors: array |
| environments | id, status, artwork (SVG local) |
| audio | id, status, path, duration |
| templates | id, title, scenes: array theo episode-1 |

status nhận Supported / Partial / Unsupported / Unavailable. Chỉ Supported được compiler chọn.
Một kit v1 hiện dùng **một rig contract chung** cho các artwork; rig khác cần kit/rig version và catalog tương thích khác.
Expression có thể dùng `bindings: {characterId: nodeId}` thay cho một nodeId chung, để giữ nguyên ID SVG nam/nữ. Environment có thể thêm `foregroundArtwork` để vẽ lớp tiền cảnh sau nhân vật. SVG clipPath nội bộ được hỗ trợ với cùng kiểm tra ID và local fragment.

Ngoại lệ thử nghiệm: kit phải khai báo rõ `testOnly: true` và kịch bản phải có `allowExperimental: true` mới được chọn capability Partial. UI đánh dấu kit/bản thử, lock ghi testOnly và không thay đổi status của catalog. Kit production thông thường vẫn chỉ dùng Supported. Không tự nâng capability sau khi compile/import thành công.
Rig gồm version, joints và anchors. Ví dụ joint: `"leftArm":{"nodeId":"arm-left","pivot":[232,570],"parent":"body"}`.
`parent` tùy chọn; nếu có phải khớp quan hệ ancestor trong SVG. Anchors là object tên → [x,y] theo tọa độ rig.
Transform/presentation ở root SVG được giữ trong wrapper; viewBox không tự đổi sang tọa độ video. Dùng x/y/scale hoặc scene template để bố cục.

## Thêm tài nguyên

- Artwork cùng rig: thêm SVG và character record. IDs/pivots/hierarchy phải tương thích rig contract.
- Expression: thêm nhóm biểu cảm vào artwork và expression record. Các artwork trong cùng rig cần chứa expression Supported đó.
- Static pose: thêm rotations record. Chọn “không sử dụng” ở motion để giữ pose, không cần viết adapter mới.
- Motion mới: thêm module .js và motion record. Module xuất `export function evaluate(t, duration)` trả object joint → góc xoay tương đối so với start pose. Ví dụ `{leftArm: 20}`.
- Duration của motion là thời gian chuẩn; compiler scale về thời lượng scene. Không tự lặp motion hoặc tự tạo chuyển tiếp giữa hai pose không tương thích.
- Environment và audio: thêm file + record, rồi chọn theo cảnh. Audio mỗi cảnh được trim theo thời lượng catalog/scene, không tự loop.
- Cập nhật tăng kit version, không sửa bản đã phát hành. Cùng id/version nhưng khác bytes bị từ chối; cùng bytes import lại không tạo bản trùng.
- Thay rig mà giữ nguyên rig version bị chặn khi nhập version mới. Rig version mới phải cập nhật rigVersion của toàn bộ pose/expression/motion. Không có migration tự động.

Compiler xuất module helper + adapter và assets cần thiết vào Story v1 tự chứa. Studio không cần đọc kit gốc khi render tập cũ.
Giữ thứ tự SVG làm z-order. Namespace IDs riêng cho từng scene/actor, rewrite href/url fragments.
Motion adapter là code tin cậy từ tác giả kit, chạy trong browser isolation hiện có, không chạy khi CLI import. Kiểm tra cú pháp/regex không phải chứng minh an toàn đầy đủ.

## CLI

```powershell
dotnet run --project src/SvgToMp4.ProductionCli -- validate path/to/kit.zip
dotnet run --project src/SvgToMp4.ProductionCli -- compile path/to/kit.zip path/to/episode.json path/to/new-story.zip
```

CLI compile không ghi đè output đã tồn tại. Xem `samples/production-episode.json` và ZIP mẫu ở `src/SvgToMp4.Web/wwwroot/episodes/production-kit-demo.zip`.
Script `scripts/create_production_sample.py` chỉ dựng lại kit minh họa, không nhập nó vào registry hoặc ghi production kit.

## Phạm vi QA và giới hạn hiện tại

Đã có kiểm tra cấu trúc ZIP/path/size, XML/SVG allowlist/IDs/references, joint/pivot/hierarchy, rig version, dependencies, JS syntax/import paths, capability Supported, Story v1 validation và khóa SHA-256.
Supported là **tuyên bố QA của tác giả kit**, chưa có hệ thống cấp chứng nhận độc lập hoặc tự promote capability sau browser testing.
Không tuyên bố đã QA hình ảnh, tiếp xúc, z-order khi chuyển động hoặc continuity của một motion mới chỉ nhờ import thành công.

Theo yêu cầu bàn giao nhanh: chỉ build, kiểm tra cú pháp và smoke import/compile/export/re-import bằng StoryStore thực.
Kết quả ngày 08/11/2026: solution build 0 warnings/0 errors; cú pháp JS PASS; smoke kit import/idempotent import, compile 3 cảnh/12 giây, StoryStore export/re-import, A/B/C ở mức compiler và từ chối capability không tồn tại đều PASS. Smoke sử dụng `work/production-smoke-*`, không ghi vào dữ liệu app đang chạy.
Không chạy full browser suite hoặc render MP4 cho tính năng này. Người dùng nghiệm thu preview, tua tiến/lùi, reset và render trong Studio.
Kit mẫu chỉ là robot hình học; không phải Production Kit robot thật đã được duyệt.

Ngoài phạm vi v1: AI tự viết kịch bản bên trong ứng dụng, TTS/lip sync, IK/physics/contact solver, choreography tự động, keyframe editor, rig migration tự động và Asset Manager chỉnh artwork.
Runtime fix 08/11/2026: inactive scene dùng display:none thay cho chỉ visibility:hidden. SVG expression visibility:visible có thể vượt visibility của ancestor và làm nét mặt của cảnh khác chồng lên cảnh đang phát. Browser kiểm tra trực tiếp ở 8.409 → 0 → 14 → 8.409 giây PASS: chỉ cảnh active có diện tích hiển thị, các expression của cảnh inactive có rect 0×0; đã xem ảnh sau sửa. Không sửa artwork hoặc ZIP của người dùng, không chạy render/full regression.
Storytelling và interaction catalog là dữ liệu tham chiếu cho tác giả/AI; không được tự diễn giải thành chuyển động mà runtime chưa hỗ trợ.
