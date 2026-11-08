# Kết quả kiểm tra rig

## Phạm vi

6 rig độc lập: nam/nữ × front/three-quarter/side. Đầu giữ vector của đúng góc đã duyệt; không dùng front để tạo góc bên. Thân và chi được tái dựng thành mảnh vector kín có phần chồng tại khớp, nên không phải bản tách giữ nguyên từng pixel của vector trace trước đó. Đây là bản rig kỹ thuật để kiểm tra chuyển động, chưa phải xác nhận hoàn thiện diễn xuất.

## Pivot và anchor

Mỗi bộ phận có group SVG thật với `data-part`, pivot local (0,0), mount theo hệ tọa độ parent và parentAnchor trùng mount. Transform = translate(mount) rotate(angle). Tọa độ SVG: x sang phải, y xuống dưới, độ dương xoay theo chiều kim đồng hồ.

- `head` nối `neck`, rồi `torso`.
- `upper-arm-L/R` → `forearm-L/R` → `hand-L/R`; anchor elbow, wrist, contact.
- `thigh-L/R` → `shin-L/R` → `foot-L/R`; anchor knee, ankle, sole, toe.
- L/R là nhãn chuỗi theo bên trái/phải màn hình ở front, không khẳng định quy ước trái/phải giải phẫu.
- Chi xa ở side tồn tại đầy đủ nhưng ẩn theo hình tham chiếu.

`worldAnchor()` tính từ cùng mount và góc đã áp dụng cho SVG, không dùng tọa độ world viết cố định. Phạm vi góc trong JSON là phạm vi kiểm thử; runtime không tự clamp.

## Kiểm tra tự động

- 336 pose: neutral, 33 thời điểm trong bài thử 8 giây, từng khớp tại hai giới hạn xoay.
- 4.128 kiểm tra chồng alpha giữa các mảnh kề nhau: không có cặp mất kết nối tại khớp trong phạm vi thử. Mask render ở tỷ lệ 1/2; kiểm tra này chứng minh có vùng chồng, không chứng minh mọi đường ráp đều đẹp.
- 17.802 kiểm tra world anchor bằng JavaScript so với nhân ma trận độc lập: sai số lớn nhất 1,61e-13 px.
- Tâm pivot của child trùng parentAnchor trong mọi pose thử.
- Render lại sau chuỗi seek 2.1 → 7 → 0 → 2.1: SHA-256 PNG ở 2.1 trùng nhau cho cả 6 rig. Đây là render kiểm tra độc lập bằng CairoSVG, không phải hash exporter của Studio.
- Reset transform JavaScript: trùng trạng thái ban đầu.
- SVG XML, ID duy nhất trong từng SVG, không raster, không script/foreignObject/event handler; JavaScript syntax: PASS.
- Story manifest: PASS JSON Schema Draft 2020-12 từ contract đính kèm; tham chiếu tệp và giới hạn ZIP đã kiểm tra.

| Rig | Pose | Vùng chồng nhỏ nhất, pixel ở tỷ lệ 1/2 | Lỗi kết nối |
|---|---:|---:|---:|
| robot-men-front | 60 | 499 | 0 |
| robot-men-three-quarter | 60 | 560 | 0 |
| robot-men-side | 48 | 630 | 0 |
| robot-women-front | 60 | 310 | 0 |
| robot-women-three-quarter | 60 | 389 | 0 |
| robot-women-side | 48 | 391 | 0 |

## Quan sát hình ảnh và giới hạn

Đã render và xem 18 hình: neutral, xoay phối hợp và gập chi cho mỗi rig, trong rotation-checks.png. Không thấy mảnh rời tại khớp trong các hình này. Một số đường ráp/cạnh chồng vẫn có thể thấy khi gập mạnh; không tuyên bố đã loại mọi đường ráp, tự va chạm hoặc xuyên thân. Không có IK/physics, khóa chân xuống đất, đổi lớp tự động theo hành động, hoặc xoay yaw 3D. Anchor sole/contact cho phép code cảnh đặt ràng buộc sau này nhưng không tự tạo ràng buộc.

Trang inspector có thanh chỉnh từng khớp, bật/tắt pivot/anchor, seek và bài thử phối hợp. JavaScript đã kiểm tra cú pháp và toán học runtime; tương tác DOM trong trình duyệt chưa được xác nhận vì môi trường không có Chromium chạy được. Nút chạy ở trang inspector dùng timer riêng cho kiểm tra thủ công; timer này không nằm trong scene Story.

Scene demo chỉ dùng context.assetText, context.addSvg và lifecycle seek/reset/dispose theo contract. Chưa import/chạy scene trong Studio hoặc xuất MP4. Không tuyên bố đạt kiểm thử exporter thực tế.
