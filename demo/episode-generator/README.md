# Episode Generator — demo độc lập

Không thay đổi project .NET, route, runtime Studio, database, process hoặc production kit đang có.
Python standard library; Node chỉ dùng kiểm tra cú pháp khi chạy tests. Không cài dependency mới.

## Xem ngay

Từ thư mục source, chạy:

Cách nhanh: bấm đúp `start-demo.cmd` trong thư mục này, sau đó mở địa chỉ hiện trong cửa sổ.

```powershell
python -m http.server 5198 --bind 127.0.0.1 --directory demo/episode-generator/generated
```

Mở **http://127.0.0.1:5198**. Dừng riêng demo bằng Ctrl+C.

- Gốc: robot gật đầu.
- A: thêm expression bằng SVG + expression catalog.
- B: thêm static pose bằng rotations trong pose catalog; cấu hình motion bắt đầu/kết thúc tại pose mới.
- C: thêm module `wave.js` + motion catalog, dùng robot nữ.
- Mỗi lựa chọn có Production Kit ZIP và Story ZIP v1 để tải.
- Artwork là robot hình học minh họa, không lấy hoặc thay artwork production.

## Nhận ZIP thật

Demo nhận thư mục bọc `robot-series-production-kit/` như cấu trúc đã cung cấp. Tên thư mục không bắt buộc.
`production-manifest.json` khai báo schema `demo-1`, kitId, version, rigVersion, đường dẫn rig và bốn catalog.
Xem manifest/catalog trong `generated/base/production-kit.zip` làm mẫu chính xác.
Demo bổ sung `characters/character-catalog.json` để ánh xạ ID nhân vật sang artwork mà không hardcode tên SVG.

```powershell
python demo/episode-generator/generator.py validate path/to/production-kit.zip
python demo/episode-generator/generator.py compile path/to/production-kit.zip path/to/episode.json path/to/new-episode.zip
```

Episode JSON tối thiểu:

```json
{"id":"episode-02","character":"male","pose":"idle","expression":"neutral","motion":"nod"}
```

Thêm artwork có cùng joint node IDs bằng bản ghi character mới; thêm pose bằng bản ghi rotations theo tên joint logic.
Nếu catalog ZIP thật dùng cấu trúc khác, cần ánh xạ sang profile demo trước; compiler báo lỗi thay vì đoán.
Thay rig version bị chặn với thông báo migration. Kiểm tra cấu trúc rig sâu hơn chưa được triển khai.

## Ranh giới và kiểm thử

- Đã triển khai: registry theo catalog, chọn Supported, kiểm tra SVG allowlist/IDs/pivots/references và joint/anchor dependencies; ZIP bounds/path checks; khóa version + SHA-256; xuất Story v1 tự chứa; không ghi đè file episode đã có.
- Motion adapter: module JS xuất `evaluate(t, duration)` trả về góc xoay tương đối theo joint logic; không dùng DOM ID. Adapter là code tin cậy do tác giả kit cung cấp, KHÔNG phải plugin sandbox. CLI không chạy code adapter; Studio tiếp tục validation/isolation riêng khi import.
- Preview độc lập dùng context tối thiểu tương ứng assetText/addSvg của contract, không phải bằng chứng Studio integration. Nó không kết nối API Studio.
- Tests: `python demo/episode-generator/checks.py`; browser: `python demo/episode-generator/checks.py --browser` (dùng Playwright đã có trong engine).
- Kết quả browser trong `generated/verification.json`; ảnh trong `generated/preview.png`.
- Kết quả bàn giao lần đầu: bốn nhóm tests Python/Node PASS, gồm A/B/C và kiểm tra lõi không đổi. Kiểm thử browser tự động đã dừng vì khởi động chậm; chưa xác minh preview/seek/reset bằng browser, chưa có ảnh chụp.
- Chưa kiểm thử import/render qua Studio, MP4, rig production thực, nhiều scene/actor, z-order động, va chạm/tiếp xúc hoặc migration tự động.
- Environment/audio/storytelling/contracts được giữ trong kit như tài liệu/tài nguyên; compiler demo chưa sử dụng chúng. Background trong robot SVG chỉ minh họa. Sample đã duyệt chưa có vì chưa nhận ZIP thật.
- Supported ở fixture chỉ áp dụng demo và kiểm thử kỹ thuật. Không có hệ thống cấp/duyệt QA độc lập; không tin nhãn Supported như chứng nhận production.
- Không có UI import/upload hoặc Asset Manager. Chỉ có preview để thử A/B/C.

`demo.py` tạo bộ mẫu mới khi chưa có thư mục `generated`; không tự ghi đè kết quả hiện hữu. CLI không sửa ZIP đầu vào.
