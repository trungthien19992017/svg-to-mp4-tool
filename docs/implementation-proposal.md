# Đề xuất dựng SVG → MP4 Whiteboard Studio

Ngày khảo sát: 2026-11-06. Project hiện có README và Git, chưa có ứng dụng. Đây là đề xuất thiết kế; chưa cài/chạy engine hoặc đo hiệu năng. Áp dụng hướng dẫn từ skill svg-whiteboard-video-renderer đã đóng gói trong cuộc trò chuyện trước.

## Hướng sản phẩm

Một studio web tiếng Việt: người dùng nhập SVG → chọn cách vẽ và bàn tay → tạo bản xem trước → xuất MP4. Tập trung ban đầu vào video vẽ từng nét từ SVG line art. Hai preset xuất chính là dọc 9:16 và ngang 16:9, 1080p, 30 FPS. Người dùng nhập thời lượng, bật/tắt tay và chọn thời gian giữ hình cuối.

Giao diện đề xuất: bên trái là file/SVG editor; giữa là vùng hình/video; bên phải là thời lượng, khung hình và bàn tay. Bên dưới có thanh tua video, nút Tạo bản xem trước, Xuất MP4 và danh sách tác vụ. Thay thiết lập sẽ đánh dấu bản xem trước cũ cần tạo lại. Khi có lỗi SVG, chỉ ra tính năng chưa hỗ trợ thay vì tạo video sai mà không báo.

## Lựa chọn engine

Dùng [gnipbao/whiteboard-video-engine](https://github.com/gnipbao/whiteboard-video-engine) làm nền tảng khảo sát và tích hợp. Package yêu cầu Python 3.11+ theo [pyproject.toml](https://github.com/gnipbao/whiteboard-video-engine/blob/main/pyproject.toml). [CLI](https://github.com/gnipbao/whiteboard-video-engine/blob/main/src/whiteboard_skill/cli.py) có nhánh render-image chuyển thiết lập sang render_image. Đây là cơ sở cho adapter Python; chưa phải API job/progress của ứng dụng.

Phát hiện từ [preprocess.py](https://github.com/gnipbao/whiteboard-video-engine/blob/main/src/whiteboard_skill/preprocess.py): nhánh arc chỉ thêm endpoint; svg_to_strokes chưa áp dụng transform lồng và không tái hiện đầy đủ style/fill SVG. Cần bổ sung SVG adapter và regression fixtures trước khi nhận file SVG phức tạp. Kết luận này dựa trên source nhánh main được đọc, chưa phải kiểm chứng runtime tại commit được pin.

Repo có [LICENSE](https://github.com/gnipbao/whiteboard-video-engine/blob/main/LICENSE) và [THIRD_PARTY_NOTICES](https://github.com/gnipbao/whiteboard-video-engine/blob/main/THIRD_PARTY_NOTICES.md). Khi chọn commit, đọc lại cùng quyền dùng sprite, font, dependencies và FFmpeg build. Không coi license code là quyền dùng mọi asset.

## Kiến trúc chốt đề xuất

```text
ASP.NET Core MVC + Razor/JavaScript
                 ↓
SQLite: projects, revisions, render jobs
                 ↓
.NET background worker, khởi đầu chạy một job mỗi lần
                 ↓ JSON job contract
Python adapter → whiteboard-video-engine → FFmpeg
                 ↓
MP4 + metadata kiểm chứng → xem trước / tải về
```

Web quản lý upload, settings, project và jobs. Background worker nhận việc ngoài vòng đời HTTP request, gọi Python bằng argument list và đọc structured events từ adapter. Python phụ trách chuẩn hóa hình, gọi engine và encode. FFprobe xác nhận đầu ra trước khi chuyển job sang hoàn tất. Hủy phải dừng cả cây tiến trình và không công bố file dở.

Không bắt buộc thêm Node, React hoặc FastAPI ở MVP. Node chỉ là công cụ build frontend nếu sau này cần. Worker Python có thể được tách thành dịch vụ khi có nhu cầu nhiều máy render; lúc đó bổ sung queue/lease phù hợp.

## Adapter cần xây

1. Input: asset IDs/đường dẫn nội bộ do server cấp, thời lượng, resolution, FPS, hand preset/scale và final hold. Không nhận command line tự do.
2. Kiểm tra và chuẩn hóa SVG: allowlist, resolve transform/style trong tập hỗ trợ, chuyển shapes thành đường vẽ, xử lý đường cong/arc chính xác bằng parser phù hợp; giữ metadata nhóm và thứ tự.
3. Gọi engine qua adapter hẹp, pin full commit SHA. Giữ thay đổi upstream tối thiểu; nếu phải sửa thì lưu patch và fixture đi kèm. Không lấy source nhánh main mới mỗi lần chạy.
4. Output: MP4 tạm, log và result JSON gồm dimensions/FPS/frame count/duration. Bổ sung callback/progress hook nếu engine chưa có; UI chỉ hiển thị tiến độ theo giai đoạn cho đến khi có số frame thực, không tạo phần trăm giả.
5. Version hóa contract, settings và cache fingerprint để đổi engine/settings không dùng nhầm video cũ.

SVG line art được xử lý trước. Bảo toàn SVG màu, gradient, clip/mask, text hay hình nhúng là phạm vi riêng cần kiểm chứng; chưa hứa mọi SVG sẽ giống hình gốc. Nét SVG outline cũng không đảm bảo mang thứ tự bút vẽ tự nhiên.

## Xem trước và timeline

MVP tạo MP4 xem trước bằng cùng engine, giữ nguyên tổng thời lượng ở khoảng 540p và 15 FPS; nếu preprocessing phụ thuộc resolution thì ưu tiên tái sử dụng stroke plan ở resolution xuất. Nếu engine chưa cho tách plan, ghi rõ xem trước chỉ để đánh giá gần đúng. Có thể thêm nút xem thử 5 giây để tiết kiệm thời gian.

Thanh tua đầu tiên là seek video đã render. Chỉnh thời lượng/cách vẽ rồi tạo lại preview. Timeline chỉnh từng nhóm/nét trực tiếp là phase sau, cần engine xuất stroke plan và evaluator theo thời gian tuyệt đối. Không xây animation JavaScript độc lập rồi mặc định nó khớp Python.

## Cấu trúc dự án đề xuất

```text
src/SvgToMp4.Web/           MVC, API, giao diện
src/SvgToMp4.Worker/        Queue consumer và process lifecycle
src/SvgToMp4.Core/          Contracts, settings và job state
engine/                    Python adapter và dependency lock
tests/fixtures/            SVG input và expected behavior
tests/integration/         Pipeline thật và job lifecycle
docs/                      Kiến trúc, kết quả khảo sát, cách chạy
```

Lưu database/assets/render workspace ngoài thư mục phục vụ file công khai, cấu hình theo môi trường và bỏ khỏi Git. Bản đầu ưu tiên chạy local; nếu đưa lên mạng phải có authentication và kiểm tra ownership trên job/download.

## Thứ tự thực hiện

1. **Chứng minh engine phù hợp:** pin commit; chạy SVG đơn giản, Bézier, arc, transform, fill/text và file thực. Xuất video 10 giây, kiểm tra hình và ffprobe; ghi thời gian/RAM. Chốt lỗi cần adapter xử lý trước khi làm UI đầy đủ.
2. **MVP dùng được:** MVC upload/paste → thiết lập → preview → export 1080p/30 FPS, lịch sử jobs và cancel. Một worker, SQLite, UI tiếng Việt.
3. **Biên tập:** quản lý project, preset, nhiều cảnh, chỉnh nhóm/thứ tự, cache preprocessing; thêm nhạc nếu cần.
4. **Mở rộng:** ảnh PNG/JPG, raster tracing, audio/subtitles và batch rendering. AI sinh ảnh, TTS, 4K, 60 FPS chỉ thêm theo nhu cầu và benchmark.

## Điều kiện hoàn tất MVP

- Hai preset dọc/ngang xuất đúng kích thước, FPS và số frame; video 10 giây/30 FPS có 300 frame.
- Tay bám đầu nét, không có nét nối giả giữa subpath; giữ hình hoàn chỉnh ở cuối video.
- Arc và transform fixture đúng; input ngoài tập hỗ trợ báo rõ lý do.
- Job không phụ thuộc việc người dùng giữ tab mở; lỗi có thông báo, cancel không để process chạy mồ côi, file tạm không tải được.
- SVG có script, external resources hoặc input vượt giới hạn bị chặn; worker không có quyền đọc secrets và không nhận URL/command tùy ý.
- Lưu versions, benchmark, MP4 mẫu và các giới hạn thực tế. Không cam kết tốc độ render trước khi đo trên máy chạy.

Khuyến nghị bước triển khai đầu tiên: hoàn thành engine spike và adapter SVG tối thiểu trong repository này, rồi dùng kết quả đó để xây MVC MVP.
