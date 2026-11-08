# Robot rig pack

1. Mở `rig-inspector.html` bằng trình duyệt. Chọn một trong 6 góc. Chọn bộ phận và kéo góc xoay; các khớp đã đặt giữ nguyên cho đến Reset.
2. Bật pivot/anchor để xem điểm gắn thật. Kéo thời gian để kiểm tra pose phối hợp, gồm seek ngược.
3. `assets/` chứa 6 SVG đã tách group. `character-rig.json` chứa hierarchy, mount, pivot, anchors và giới hạn. `pivots-and-anchors.csv` dùng xem tọa độ dạng bảng.
4. `rig-runtime.js` xuất applyPose và worldAnchor. Luôn scope querySelector vào nhân vật tương ứng khi có nhiều bản sao.
5. `rotation-checks.png` và `validation-report.md` ghi kết quả và giới hạn kiểm tra.
6. Nếu dùng Studio, import riêng `story-joint-check.zip` nằm trong gói này. ZIP ngoài là gói bàn giao, không phải story import. Scene thử 8 giây dùng 6 rig, không audio.

Đầu giữ hình của từng góc; thân và chi được tái dựng để có mảnh kín và vùng chồng. Không có rig khuôn mặt/biểu cảm, IK hoặc animation diễn xuất hoàn chỉnh.
