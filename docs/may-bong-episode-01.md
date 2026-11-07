# Mây & Bông — Episode 01

Demo MVP ngày 07/11/2026. Hình ảnh vector gốc lấy cảm hứng từ ảnh tham chiếu rừng mưa: hiên nhà ấm, hai bạn cáo, sách, tách trà, suối và doodle. Không đưa giao diện mạng xã hội hoặc chữ trong ảnh tham chiếu vào sản phẩm.

## Deliverables

- ZIP: `outputs/may-bong-episode-01/may-bong-episode-01.zip`.
- MP4 khi acceptance hoàn tất: `outputs/may-bong-episode-01/may-bong-episode-01.mp4`.
- Source project: `samples/may-bong-episode-01/`.
- Module animation mới: `samples/may-bong-episode-01/modules/cozy-engine.js`; ba scene adapter trong `scenes/`.
- Script tạo SVG, manifest, audio gốc: `scripts/create_may_bong_demo.py`. Module engine được giữ như source riêng, script không ghi đè module này.
- Acceptance thực: `tests/test_may_bong_demo.py`; kết quả máy đọc được ở `outputs/may-bong-episode-01/acceptance.json`, metadata MP4 ở `render-result.json`.

Project v1: **3 scene, tổng 14 giây, 720×1280, 24 FPS**, hai nhân vật dùng chung SVG. Scene 1 đọc sách, scene 2 đưa tách trà lên, scene 3 nghỉ ngơi. Mưa, gợn nước, hơi trà, đuôi/chớp mắt và nhịp thở được tính lại từ local time; GSAP dùng context hiện có. Audio mưa được tạo local, đã khai báo và dùng trong manifest. Không có AI service, TTS, tài nguyên remote hoặc đường dẫn máy tác giả trong bundle.

## Luồng đóng gói và kiểm chứng

1. Tạo seed ZIP từ source để gửi vào `POST /api/stories/import` chính thức; không bàn giao seed như bản export.
2. Lấy ZIP cuối từ **`GET /api/stories/{id}/export`**, lưu đúng tên deliverable.
3. Kiểm tra CRC, đường dẫn, schemaVersion, thời lượng, scene/asset references, helper module và toàn bộ binary/source bytes.
4. Import lại chính ZIP cuối, export lần hai, so sánh **mọi file byte-for-byte**.
5. Mở project re-import trong Story Studio thật, dùng iframe cách ly hiện có; cả ba scene phải khởi tạo và playback không có page errors.
6. Seek không tuần tự ở **0; 1,75; 4,75; 6,25; 9,25; 12,25; 13,95 giây**, bao gồm cả hai overlap.
7. Render qua `POST /api/stories/{id}/render` và BackgroundService/Windows Job Object/Python/Playwright/FFmpeg hiện có. Không chạy renderer bằng cách giả biến resource guard.
8. Kiểm tra output **336 frame, 14 giây, H.264/yuv420p, 720×1280/24 FPS và AAC**; lấy video qua download API.

ZIP tự chứa 12 file, gồm manifest, 3 scene modules, 1 engine module, 6 SVG và 1 WAV. Nó cần ứng dụng Story Studio đã setup GSAP/browser/FFmpeg theo contract v1; không yêu cầu file ngoài project hoặc sửa source thủ công. Không tạo schema mới và không thay pipeline import/export.

## Ghi chú kiểm thử

- **Kết quả cuối: PASS toàn bộ acceptance**, gồm ZIP export/re-import, 3 scene initialization, playback, 7 mốc seek và queued MP4 render. Browser: Chrome **156.0.8078.80**.
- MP4 đã tạo thành công: **14,000 giây, 336 frame, H.264/yuv420p 720×1280/24 FPS + AAC**, dung lượng **1.431.735 bytes**. Renderer mất khoảng **80,56 giây** trên máy hiện tại. Đã giải mã và kiểm tra trực quan frame video tại 2,5 giây.
- ZIP cuối: **565.029 bytes**, SHA-256 `b0a79c091b73568393503b0d7c415b2f929984298c23df167b582dd5b73ee725`; 12 file. Project re-import cuối: `f7e3d559b95b4f419d147ada4c932ffb`; job: `c4cfcccbc0c2436599a4c491b117c125`. Các ID chỉ phục vụ tra cứu instance local này.
- Build solution hiện tại đạt **0 warnings / 0 errors**, khoảng 6,94 giây.
- `node tests/story-timeline.mjs`: PASS.
- `python tests/test_story_audio.py`: PASS, FFmpeg audio thực.
- Test demo sửa cách chờ iframe qua Playwright locator assertions: polling bằng Python sleep không tự bơm browser events; `wait_for_function` kiểu compile predicate bị CSP chặn. Không nới CSP để chạy test.
- Preview thu nhỏ dùng fractional CSS pixels. Lần đo có **20 pixel lệch tối đa 1/255 mỗi kênh** dù SVG DOM không đổi. Test yêu cầu active scene DOM giống hệt, sai số raster tối đa 1/255 trên dưới 0,1% pixel khi ảnh không khớp byte. Không đổi renderer production: exporter vẫn kiểm tra **hash PNG full-size chính xác** sau chuỗi seek không tuần tự.
- Test tạo project/revision và job demo trong local app store; giữ lại project re-import để mở trực tiếp trong UI. Không xóa lịch sử hoặc dừng process có sẵn.

## Chạy lại

Trong workspace đã setup, giữ `start.ps1` chạy để phục vụ hai cổng loopback 5188/5189, rồi:

```powershell
$env:PYTHONUTF8 = '1'
python scripts/create_may_bong_demo.py
python tests/test_may_bong_demo.py
```

Acceptance exit 0 và `acceptance.json` có `status: PASS` là kết quả hoàn tất. Chi tiết browser version, ZIP SHA-256, project/revision/job IDs và ffprobe nằm trong báo cáo JSON; không đưa các ID/đường dẫn runtime này vào Story ZIP.
