# Chạy AI SVG Storyboard Studio

## Cài và chạy

Trong `D:\Source\svg-to-mp4-tool`, dừng bản cũ bằng Ctrl+C trước khi cập nhật. Cần Windows 64-bit, .NET SDK 8, Python 3.11+/pip, Node.js/npm, Chrome hoặc Edge, FFmpeg/ffprobe có libx264 và AAC.

```powershell
.\setup.ps1
.\start.ps1
```

Setup cần mạng để tải npm GSAP và Python dependency. GSAP là thư viện thật, pin 3.15.0, được copy local cùng MotionPath/MorphSVG và notices; không tải CDN trong preview/render. Node chỉ kiểm tra cú pháp module bằng `--check`, không chạy scene. Nếu npm lỗi mạng, chạy lại setup sau khi kết nối được registry.npmjs.org; đừng coi warning thiếu GSAP là preview đã hoạt động.

Mở **http://127.0.0.1:5188**. Cổng 5189 dành riêng cho iframe preview cách ly; không mở cổng ra mạng. Có thể bấm đúp `start.cmd`. Màn hình cũ ở **http://127.0.0.1:5188/whiteboard**.

## Thử toàn bộ câu chuyện

1. Bấm **Câu chuyện mẫu**, hoặc **Import ZIP** và chọn `samples/lost-star.zip`.
2. Đợi bốn scene và thumbnail hiện ra. Dùng Space, Play/Pause, thanh timeline, nút từng frame/cảnh.
3. Mở scene code ở dưới; thay đổi rồi bấm **Lưu & áp dụng**. Đổi thứ tự bằng kéo scene; thời lượng và outgoing transition ở Properties.
4. Chọn 720p/1080p/4K, FPS 24/30/60, aspect ratio và CRF. Nếu khác tỷ lệ logic gốc, nội dung được giữ tỷ lệ và thêm letterbox ở giữa.
5. Bấm **Render MP4**. Job dùng revision cố định; các sửa đổi sau không thay video đang render. Theo dõi số frame, hủy hoặc tải file khi Completed.
6. **Export ZIP** lưu toàn bộ source/assets/audio để dùng lại hoặc nhờ ChatGPT sửa.

Mẫu **Mèo Mây và ngôi sao lạc** dài 34,5 giây, 4 cảnh dùng cùng character SVG, camera/pan/zoom, MotionPath, finite loops, fade/slide overlaps và chime audio. Không cần chỉnh từng cảnh để chạy. Source giải nén ở `samples/lost-star/`; tạo lại bằng `python scripts/create_story_sample.py`.

**Từ code** tạo một Story một cảnh, có module GSAP để bạn thay bằng code tuân thủ contract. **Import code** nhận một module `.js` theo contract, SVG tĩnh hoặc HTML/CSS rồi đóng thành Story một cảnh. Script tag trong HTML không được thực thi như lifecycle; đặt JS/GSAP trong scene module. SVG/HTML/CSS cũng có thể nằm trong asset hoặc file scene được tham chiếu từ manifest. Không phải mọi đoạn JavaScript bất kỳ đều tương thích: dùng [Animation Code Contract](animation-code-contract.md) và [schema/format](story-project-format.md) khi yêu cầu ChatGPT sinh ZIP.

## Kiểm chứng sau cài

```powershell
$env:DOTNET_CLI_HOME = Join-Path (Get-Location) '.dotnet'
dotnet restore tests/StoryChecks/StoryChecks.csproj
dotnet run --project tests/StoryChecks/StoryChecks.csproj -- D:\Source\svg-to-mp4-tool
node tests/story-timeline.mjs
python tests/test_story_audio.py
# Giữ start.ps1 chạy ở cửa sổ khác:
python tests/test_story_e2e.py
```

End-to-end tạo project/job kiểm thử thật và render cả sample. Nó kiểm tra nonsequential seek, transitions, sandbox preview, nested timeline/loop, 720p/1080p, FPS, audio, cancellation. Nếu chưa cài GSAP, test trả mã 77 / SKIP, không được tính là đã đạt. Kiểm tra 4K phụ thuộc RAM/CPU và không có cam kết realtime.

## Giới hạn hiện tại

- Monaco chưa được thêm; editor textarea có mở/sửa/lưu code thật. Chưa có no-code keyframe/rig builder.
- Thumbnail là SVG snapshot của scene, có thể không thể hiện đầy đủ HTML/CSS/camera. Đây không phải screenshot pixel của toàn frame.
- Source lint, parser và một vài seek comparison không chứng minh mọi code bất kỳ deterministic. Scene phải tuân thủ contract; lỗi theo scene hiện ở console.
- Cảnh code không được dùng visual callbacks hoặc timers để quyết định trạng thái. Asset dùng local trong ZIP; remote dependencies bị chặn.
- Audio preview có thể cần người dùng bấm Phát để trình duyệt cho phát âm thanh. Các track dùng chung master time; không có TTS.
- Render imported JS chỉ được bật khi Windows 64-bit Job Object cấu hình được. Preview có browser isolation/CSP nhưng chưa có quota RAM riêng cho từng iframe.
- Chưa có multi-user server, public deployment hoặc packaged installer. Giữ local và review [security](story-security.md) trước khi mở rộng.

Xem [báo cáo kiểm chứng](story-verification.md) để phân biệt source đã viết, kiểm tra đã chạy và phần browser/export còn pending do môi trường.
