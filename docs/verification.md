# Kết quả kiểm chứng triển khai

Ngày: 2026-11-06. Môi trường Windows, .NET SDK 8.0.121, Python 3.11.14, Chrome 156, FFmpeg gyan build 2026-07-30 có libx264. Source upstream pin `86848ea27077c1902950bf4e7e37e02d4bfbd1a3`.

## Bản tích hợp whiteboard + doodle đã kiểm chứng

- Build MVC/Core/Worker thành công, 0 warnings/0 errors.
- 8 engine tests đã đạt: chặn active content; arc/transform/relative subpath; evaluator không phụ thuộc thứ tự seek; nguồn ảnh nhúng; contract doodle; nền đầu video, màu/nét đứt/transform và seek lại; MP4 thực của cả hai chế độ.
- 7 nhóm integration checks đã đạt: thiếu CSRF bị từ chối; preview qua UI phát được (540×960, 150 frame/10 giây); xuất dọc và ngang 1080p/30 FPS đúng 300 frame/10 giây; range playback và download; SVG script bị từ chối và không có output tải được; hủy queued/active job và dọn partial; history sau reload, mobile không tràn ngang và không có JavaScript error.
- 9 nhóm kiểm tra doodle qua UI đã đạt: mở mẫu, preview, xuất 1080p có bàn tay (90 frame/3 giây), range playback, tải SVG, upload ảnh nền, khôi phục draft, mobile và không có lỗi JavaScript.
- Cả ba file trong `samples/` import được qua UI, tự nhận đúng chế độ whiteboard/doodle. Kiểm tra giao diện ở chiều rộng 1440, 1024, 768 và 390 pixel không tràn ngang.
- Đã khởi động lại bằng `start.ps1` sau build cuối: thành công, 0 warnings/0 errors, lịch sử video cũ vẫn có trong SQLite. Script mặc định build trước khi chạy để tránh dùng Razor/C# cũ.
- Đã dọn đúng các tác vụ thử lỗi/hủy do phiên kiểm tra này tạo, kiểm tra theo ID và nội dung input; giữ các video thành công và không dọn dữ liệu ngoài danh sách đó.
- Thời gian hai bản xuất whiteboard ở lần kiểm tra bản tích hợp: 1080×1920 khoảng 15,61 giây; 1920×1080 khoảng 17,56 giây. Đây là số đo cho một SVG minh họa 18 stroke units trên máy hiện tại, không phải cam kết cho mọi input hoặc phần cứng. Doodle chụp từng frame bằng Chrome để giữ nguyên style nên có thể chậm hơn.

## Ranh giới kết quả

Đã build và chạy lại các kiểm tra trên sau khi người dùng xác nhận giữ cả doodle và tích hợp chung. Source adapter được kiểm chứng có version `svg-adapter-2`; settings có `effect` mặc định `whiteboard` và lựa chọn `doodle`. Hướng dẫn chạy source nằm ở `docs/run-source.md`, ba SVG import thử nằm trong `samples/`.

Nguồn bằng chứng chi tiết: log kiểm thử trong phiên làm việc, `work/qa/integration.json`, `work/qa/doodle-integration.json`, ảnh QA trong `work/qa/`. Thư mục work bị bỏ qua bởi Git. Mỗi job xuất thành công lưu ffprobe, browser version, thời gian và commit engine trong `data/jobs/<id>/result.json`.

Chưa kiểm chứng installer, deployment nhiều người dùng, GPU, audio, 4K/60 FPS hoặc quyền phân phối thương mại mọi third-party asset. FFmpeg/browser là phần mềm có sẵn trên máy, không được đưa vào source repository này.
