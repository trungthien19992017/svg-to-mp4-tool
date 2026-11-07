# Chạy source và import SVG mẫu

## Trên máy hiện tại

Source nằm ở `D:\Source\svg-to-mp4-tool`. Dependency đã được cài trong project.

**Cách 1:** mở thư mục và bấm đúp `start.cmd`. Giữ cửa sổ này mở trong lúc dùng tool.

**Cách 2:** mở PowerShell tại thư mục project rồi chạy:

```powershell
.\start.ps1
```

Mở công cụ SVG cũ tại **http://127.0.0.1:5188/whiteboard**. Trang gốc hiện là Story Studio nhiều cảnh. Script build source hiện tại trước khi chạy, nên thay đổi C#/Razor cũng được cập nhật. Khi đã build và muốn bỏ qua bước đó, dùng `.\start.ps1 -NoBuild`.

Dừng bằng Ctrl+C trong cửa sổ chạy. Khi cần chạy lại sau khi sửa code, dừng bản cũ rồi chạy lại script. Không cần Visual Studio để dùng hai cách trên.

## Import và thử ngay

Trong tool, bấm **Thả SVG vào đây** hoặc kéo file từ thư mục `samples` vào vùng này.

| File | Cách vẽ | Thiết lập thử |
|---|---|---|
| `samples/01-ngoi-nha-mau.svg` | Nét trước, màu sau | Dọc 9:16, 10 giây, giữ hình 1 giây, tay mẫu 1 |
| `samples/02-duong-cong-transform.svg` | Nét trước, màu sau | Ngang 16:9, 5 giây, giữ hình 1 giây |
| `samples/03-doodle-anh-nen.svg` | Doodle trên ảnh nền | Dọc 9:16, 5 giây, giữ hình 1 giây; thử tắt hoặc bật bàn tay |

1. Sau import, kiểm tra **Cách vẽ**. File có `g id="doodles"` tự chọn chế độ doodle.
2. Bấm **Tạo bản xem trước**, đợi hoàn tất. Video xem trước là 540p / 15 FPS.
3. Chọn tab **Video**, bấm Play trên video. Thanh tua cho phép xem từng đoạn.
4. Bấm **Xuất MP4** để tạo bản 1080p / 30 FPS, sau đó chọn **Tải MP4** trong lịch sử.
5. Muốn khôi phục một lần thử, chọn **Mở lại**. Muốn lấy SVG đang chỉnh, chọn **Tải SVG**.

**Nét trước, màu sau:** bắt đầu nền trắng, vẽ phác nét, chuyển dần sang màu gốc và giữ hình hoàn chỉnh. Chữ xuất hiện cùng màu; chưa mô phỏng viết từng nét chữ.

**Doodle trên ảnh nền:** ảnh nền có sẵn từ đầu, các path riêng được vẽ lên nền theo thứ tự. Ảnh và nét được đóng gói trong cùng file SVG, không cần tải ảnh từ mạng. Chế độ này không làm mưa, nhân vật hay đồ vật trong ảnh tự chuyển động.

Hai nút **Dùng bản mẫu** và **Mẫu doodle** trong giao diện cũng mở các ví dụ tương ứng. Nút **Chọn ảnh nền PNG/JPEG** tạo SVG từ ảnh của bạn và một số path doodle mẫu; chỉnh/thay path trong ô mã để có hình mình muốn. Nếu ảnh đã chứa doodle thì các nét trong ảnh vẫn hiện sẵn từ đầu.

## Chạy sau khi clone sang máy khác

Cài sẵn:

- .NET SDK 8, không chỉ runtime.
- Python 3.11+ và pip, có lệnh `python` trong PATH.
- FFmpeg và ffprobe có libx264, có trong PATH.
- Google Chrome hoặc Microsoft Edge.

Sau đó chạy tại thư mục project:

```powershell
.\setup.ps1
.\start.ps1
```

Setup cần mạng để tải package. Render không gọi AI, TTS hoặc dịch vụ cloud. Thư viện Python nằm trong `engine/.packages`, không cài vào Python hệ thống. Không cần clone engine vì phần source cần thiết đã nằm trong `engine/vendor` cùng license và commit được pin.

## Các lỗi thường gặp

- **PowerShell chặn script:** chạy `powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1`; lệnh chỉ áp dụng cho tiến trình này. Hoặc dùng `start.cmd`.
- **Cổng 5188 đã được dùng:** đóng cửa sổ chạy tool cũ bằng Ctrl+C rồi thử lại. Không mở hai bản tool cùng lúc trên cùng thư mục dữ liệu.
- **Chưa có dependency/build:** chạy lại `setup.ps1`. Nếu vừa cập nhật source mà giao diện không khớp, dừng và chạy lại `start.ps1`, sau đó Ctrl+F5 trên trình duyệt.
- **Python khác PATH:** dùng `.\setup.ps1 -Python 'C:\duong-dan\python.exe'` và `.\start.ps1 -Python 'C:\duong-dan\python.exe'`.
- **Không tìm được trình duyệt:** đặt `$env:SVG_CHROME = 'C:\duong-dan\chrome.exe'` rồi chạy `start.ps1` trong cùng cửa sổ.
- **SVG chưa hỗ trợ:** xem thông báo trong lịch sử; stylesheet, use, filter, clip/mask hoặc script chưa được nhận. SVG doodle cần một group `doodles` ở cuối, có stroke và `fill="none"`.
- **Render lỗi:** xem `data/jobs/<mã-tác-vụ>/encoder.log`; `result.json` chỉ xuất hiện sau khi kiểm chứng thành công.

Ứng dụng chỉ chạy local theo cấu hình đã chọn. Giữ thư mục `data` nếu muốn giữ lịch sử, input và video; thư mục này không được đưa vào Git.
