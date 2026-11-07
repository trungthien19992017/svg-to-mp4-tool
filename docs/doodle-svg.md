# SVG doodle trên ảnh nền

## Định dạng

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 1920">
  <image width="1080" height="1920" href="data:image/png;base64,..."/>
  <!-- Hình và chữ tĩnh đặt trước lớp doodle. -->
  <g id="doodles" fill="none" stroke="white" stroke-width="4"
     stroke-linecap="round" stroke-linejoin="round">
    <path d="M100 200 Q150 130 200 200"/>
    <path d="M250 300 Q320 250 400 300" stroke-dasharray="8 8"/>
  </g>
</svg>
```

`g` có id `doodles` phải là phần tử con trực tiếp cuối cùng của SVG. Các shape trong group này được vẽ theo thứ tự tài liệu. Hỗ trợ path, line, polyline, polygon, rect, circle, ellipse và group transform bên trong. Các nét cần `fill="none"`, stroke và stroke-width > 0. Các thành phần bên ngoài group hiển thị ngay từ đầu. Không nhận image/text trong group doodles; chữ viết từng nét cần chuyển thành nét không fill.

Ảnh dùng `href` hoặc `xlink:href` dạng data URL PNG/JPEG base64, MIME khớp dữ liệu ảnh. Không dùng URL, file bên ngoài, SVG nhúng, script, CSS stylesheet, clip/mask của người dùng. Giới hạn toàn bộ SVG 20.000.000 byte, 5.000 phần tử; ảnh không quá 25 triệu pixel. Geometry tiếp tục chịu giới hạn số path và số điểm của adapter.

## Render

API settings thêm `effect: "doodle"`; mặc định `"whiteboard"` để tương thích tác vụ cũ. Ở chế độ doodle, toàn bộ thời gian trước phần giữ hình cuối được dùng để vẽ; không làm mờ toàn cảnh để hiện màu. Bàn tay vẫn có thể chọn hoặc tắt.

Browser giữ stroke gốc và dùng mask nội bộ riêng để lần lượt lộ từng nét. Mask không thay stroke-dasharray của nguồn nên nét đứt vẫn giữ nguyên. Tiến độ được tính tuyệt đối, có thể quay lại frame trước mà không phụ thuộc lịch sử. Frame cuối và giai đoạn giữ hình dùng hình SVG hoàn chỉnh. Video MP4/H.264 có nén mất dữ liệu nên có thể chênh lệch màu nhẹ so với PNG.

Vì chụp frame bằng browser để giữ style, chế độ doodle có thể chậm hơn whiteboard. Tách các nét bút thành từng path giúp thứ tự vẽ và chuyển động tay tự nhiên hơn; path có nhiều subpath cách xa nhau có thể khiến tay di chuyển không đều qua khoảng trống. Hai chế độ không tự tạo chuyển động cho mưa, nhân vật hoặc vật thể nằm trong raster.

## Sử dụng

Chọn **Mẫu doodle** để mở bản mẫu, tạo bản xem trước rồi xuất MP4. **Chọn ảnh nền PNG/JPEG** tạo SVG mới với ảnh nhúng và các nét mẫu; thay những path mẫu bằng doodle của bạn. **Tải SVG** lưu file chứa cả ảnh và vector.

Ảnh đã có doodle sẽ giữ sẵn các nét đó. Muốn chúng xuất hiện lần lượt, cần ảnh nền chưa có doodle và các path riêng tương ứng.

Mẫu: `src/SvgToMp4.Web/wwwroot/samples/doodle.svg`.

## Kiểm tra

`python -u tests/test_engine.py -v` kiểm tra nguồn ảnh nhúng, chặn tài nguyên ngoài, geometry cũ, frame đầu giữ nền, nét trắng, transform, nét đứt, tua lại tuyệt đối và xuất MP4 thật của cả hai chế độ.

`python -u tests/test_doodle_app.py` kiểm tra ứng dụng đang chạy, tạo các tác vụ thật trong lịch sử. Kiểm tra mẫu, preview, xuất 1080p có bàn tay, range playback, tải SVG, chọn ảnh nền, khôi phục bản nháp, bố cục mobile và lỗi JavaScript.

Kết quả lần triển khai: 8 engine tests đạt; kiểm tra giao diện đạt tất cả các bước trên. Video doodle 1080 × 1920, 30 FPS, 3 giây có 90 frame, 6 nét, được ffprobe xác nhận H.264/yuv420p; thời gian xử lý mẫu khoảng 18 giây trên máy hiện tại. Thời gian phụ thuộc SVG và cấu hình máy. Build .NET đạt, không có warning/error. Khi tool đang chạy có thể khóa file build; dừng ứng dụng trước khi build lại.
