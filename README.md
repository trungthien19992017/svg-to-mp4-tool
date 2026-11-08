# AI SVG Storyboard Studio — Story to Video

**Episode Generator tích hợp:** mở `/episodes` để nhập Production Kit, chọn mẫu/tạo cảnh bằng form hoặc nhập JSON kịch bản, rồi đưa thẳng vào Studio. Hỗ trợ bản nháp, nhân bản tập cũ và khóa version/hash asset. Xem [hướng dẫn Production Kit](docs/production-generator.md). Sau khi cập nhật source, khởi động lại bằng `start.ps1` khi các job đang chạy đã hoàn tất.

Trọng tâm mới: import một Story Project ZIP chứa SVG, scene JavaScript/GSAP, HTML/CSS và audio; quản lý nhiều cảnh, preview theo timeline và xuất MP4. Backend vẫn là ASP.NET Core MVC; preview/export dùng chung browser runtime và Python + Playwright + FFmpeg. Whiteboard/doodle được giữ ở **/whiteboard**, cùng lịch sử và dữ liệu cũ.

**Tình trạng bản cập nhật:** source đã được triển khai, build và các kiểm tra core/timeline/audio được ghi trong [báo cáo Story](docs/story-verification.md). Preview GSAP và MP4 toàn bộ Story **chưa được xác minh chạy thành công trong môi trường này** vì npm bị chặn mạng và bước khởi động lại/kiểm thử browser bị lỗi xét duyệt do hạn mức. Không coi bản này đã nghiệm thu MVP cho đến khi chạy các kiểm tra end-to-end.

## Chạy Story Studio

Đóng cửa sổ tool cũ bằng Ctrl+C trước khi build. Trong thư mục source:

```powershell
.\setup.ps1
.\start.ps1
```

Setup tải GSAP 3.15.0 vào local runtime, cài dependency Python và build .NET. Cần thêm Node.js/npm để cài GSAP và kiểm tra cú pháp module (Node chỉ dùng `--check`, không thực thi scene). Mở **http://127.0.0.1:5188**; cổng **5189** là preview origin cách ly, không phải ứng dụng/API thứ hai. Giữ cả hai cổng chỉ ở loopback.

Bấm **Câu chuyện mẫu** hoặc import [samples/lost-star.zip](samples/lost-star.zip): 4 cảnh / 34,5 giây, nhân vật Mèo Mây dùng chung, chuyển động vật thể, camera, chuyển cảnh và chime audio. Không cần sửa từng cảnh trước khi render. Play/Pause, tua tổng, từng frame và mở scene code đều có sẵn. **Lưu & áp dụng** tạo revision mới; **Export ZIP** lưu project; **Render MP4** xếp hàng bản lưu cố định.

- [Hướng dẫn Story](docs/story-run.md)
- [Kiến trúc hiện trạng/đích](docs/architecture-analysis.md)
- [Định dạng project + JSON Schema](docs/story-project-format.md)
- [Animation Code Contract v1](docs/animation-code-contract.md)
- [Ranh giới thực thi code](docs/story-security.md)
- [Nghiên cứu repository và license](docs/story-research.md)

## Công cụ SVG whiteboard/doodle cũ

Ứng dụng local một người dùng: nhập SVG, tạo video bàn tay vẽ nét, hiện dần màu gốc rồi giữ hình hoàn chỉnh. Giao diện tiếng Việt, nền sáng, ba vùng biên tập.

**Bắt đầu:** xem [hướng dẫn chạy source và import mẫu](docs/run-source.md). Có thể bấm đúp `start.cmd`; ba SVG để thử nằm trong [samples](samples/README.md).

## Chạy trên máy hiện tại

Trong PowerShell tại `D:\Source\svg-to-mp4-tool`:

```powershell
.\start.ps1
```

Mở công cụ cũ tại **http://127.0.0.1:5188/whiteboard**. Dừng bằng Ctrl+C. Các dependency whiteboard đã được cài; phần Story mới cần bổ sung GSAP qua setup như hướng dẫn phía trên.

Lần đầu sau khi clone sang máy khác:

```powershell
.\setup.ps1
.\start.ps1
```

Nếu Windows chặn chạy script, có thể dùng `powershell -ExecutionPolicy Bypass -File .\start.ps1` cho đúng lần chạy này; không cần đổi policy toàn máy. Python khác PATH: `./setup.ps1 -Python 'C:\path\python.exe'`, rồi chạy start với cùng tham số.

Yêu cầu: .NET SDK 8, Python 3.11+, pip, FFmpeg/ffprobe có libx264 trong PATH, Chrome hoặc Edge. Có thể đặt `SVG_CHROME` trỏ tới browser executable. Thư viện Python được cài riêng vào `engine/.packages`, không sửa Python hệ thống; cách này cũng hỗ trợ Python đi kèm LibreOffice trên máy hiện tại. Setup cần mạng để tải dependency; render không dùng cloud/API/AI/TTS.

## Sử dụng

1. Tải file SVG hoặc dán mã. Có bản mẫu ngôi nhà nhỏ.
2. Chọn cách vẽ, dọc 9:16 hoặc ngang 16:9, thời lượng 3–120 giây, bàn tay và thời gian giữ hình cuối.
3. **Tạo bản xem trước:** 540p, 15 FPS, cùng thời lượng và thuật toán.
4. **Xuất MP4:** 1080p, 30 FPS, H.264/yuv420p. Đợi hoàn tất rồi xem hoặc tải từ lịch sử.

Giữ hình cuối đã nằm trong tổng thời lượng. Màu xuất hiện bằng chuyển tiếp từ bản nét sang ảnh màu SVG, sau đó giữ hình gốc không có bàn tay. Video H.264 có nén mất dữ liệu; pixel sau giải mã có thể lệch nhẹ so với ảnh nguồn.

Lịch sử, input và kết quả lưu ở `data/`, ngoài thư mục public và được bỏ qua bởi Git. Bản đang chỉnh lưu trong localStorage; **Mở lại** trong lịch sử khôi phục input/settings của lần render đó. Đóng tab không hủy tác vụ khi ứng dụng còn chạy; dừng ứng dụng sẽ đánh dấu tác vụ đang xử lý bị gián đoạn ở lần chạy sau. Các tác vụ chờ tiếp tục chạy.

## Doodle trên ảnh nền

Chọn **Mẫu doodle** để thử SVG có ảnh nền nhúng và nét trắng riêng. Chế độ **Doodle trên ảnh nền** giữ nền từ đầu, vẽ từng nét theo thứ tự trong SVG với màu, độ dày, nét đứt, độ trong suốt và transform gốc. Không có giai đoạn tô màu trong chế độ này.

Nút **Chọn ảnh nền PNG/JPEG** tạo SVG mới có ảnh nhúng và một số nét doodle mẫu để thay thế/chỉnh sửa. Nút **Tải SVG** lưu file độc lập. Đây là SVG kết hợp raster nền và vector doodle, không phải vector thuần. Ảnh đã có doodle vẫn giữ các nét đó; dùng nền chưa có doodle nếu muốn chúng chỉ xuất hiện khi vẽ.

Chi tiết định dạng và API: [docs/doodle-svg.md](docs/doodle-svg.md). Chế độ **Nét trước, màu sau** tiếp tục dùng cho các SVG thông thường.

## Input hỗ trợ và giới hạn

- Path gồm Bézier/arc/subpath, shape cơ bản, group transforms, màu/opacity, gradient nội bộ và text. Chrome đọc geometry và tạo ảnh màu để tránh các hạn chế parser SVG upstream.
- Chữ hiện ở phần màu; chưa có mô phỏng viết từng nét chữ. Các vùng fill được phác viền trong phần vẽ, không tái hiện nguyên phong cách stroke/brush của mọi SVG.
- Hỗ trợ ảnh PNG/JPEG nhúng base64, không nhận ảnh qua link hoặc đường dẫn file. Chưa nhận stylesheet `<style>`, `use`, filter, clip/mask, SVG lồng hoặc animation. Xuất SVG với presentation attributes/inline style được hỗ trợ hoặc chuyển phần đó thành path trước. Input chưa hỗ trợ được báo lỗi, không âm thầm bỏ.
- Phần outline dùng thứ tự tài liệu, không có editor chỉnh timeline từng nét. Nét có thể bị che trong ảnh gốc vẫn có thể xuất hiện ở bước phác viền. Preview ở resolution khác có thể khác nhẹ về phân bổ pause giữa nét.
- Tối đa 20 MB tính cả ảnh nhúng; ảnh không quá 25 triệu pixel. Giới hạn 5.000 XML elements, 4.000 stroke units, 250.000 điểm mẫu, 5 tác vụ chưa hoàn tất và 15 phút/tác vụ. Một worker xử lý lần lượt.
- Chỉ phục vụ loopback và chưa có đăng nhập, đúng phạm vi local đã chọn. Không cấu hình thành dịch vụ public khi chưa bổ sung xác thực và isolation phù hợp.

## Cấu trúc và engine

`src/SvgToMp4.Web`: ASP.NET Core MVC/Razor + JavaScript/CSS. `src/SvgToMp4.Worker`: background queue/process management. `src/SvgToMp4.Core`: contracts và SQLite store. `engine/render.py`: adapter SVG và frame rendering.

Tái sử dụng timeline, stroke helpers, hand sprites, color blending và frame streaming từ [gnipbao/whiteboard-video-engine](https://github.com/gnipbao/whiteboard-video-engine), pin commit `86848ea27077c1902950bf4e7e37e02d4bfbd1a3`. Source cần thiết được giữ nguyên trong `engine/vendor/`; xem [nguồn và license](engine/vendor/UPSTREAM.md). Không cần clone hoặc tải lại repo khi chạy ứng dụng.

## Kiểm chứng

```powershell
python tests/test_engine.py
# Sau khi start.ps1 đã chạy:
python tests/test_app.py
python tests/test_doodle_app.py
```

Engine tests kiểm tra input độc hại, arc/transform/relative subpath, seek evaluator, MP4 thực và sai số màu cuối. App tests tạo các tác vụ thử thật: preview, xuất dọc/ngang, range playback/download, CSRF, SVG script rejection, active/queued cancel, history và mobile layout. App tests thêm dữ liệu thử vào lịch sử; chỉ chạy khi muốn kiểm chứng toàn luồng.

Kết quả triển khai ghi ở [docs/verification.md](docs/verification.md). File `result.json` trong từng job chứa ffprobe, browser version và thời gian render. Lỗi encoder nằm trong `encoder.log`. Chưa hỗ trợ đóng gói executable hoặc installer.
