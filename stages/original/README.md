# Màn gốc (task 4.7)

Dữ liệu màn lấy từ [Quick Bloxorz](https://github.com/jgordon510/quick_bloxorz) của Jeffrey Gordon
(bản HTML5 của Bloxorz, Damien Clarke, 2007), phát hành theo giấy phép
[CC BY](https://creativecommons.org/licenses/). Các file JSON ở đây được sinh tự động bằng:

```bash
git clone https://github.com/jgordon510/quick_bloxorz /tmp/quick_bloxorz
python tools/convert_quick_bloxorz.py /tmp/quick_bloxorz/maps
```

Không sửa tay các file `stage_NN.json`; sửa script rồi chạy lại.

Nhóm (`group`) được gán theo cơ chế khó nhất trong màn: G1 chỉ có sàn, G2 có ô dễ vỡ,
G3 có cầu/công tắc, G4 có công tắc tách.

Ô có nhiều nút chồng nhau trong Quick Bloxorz (màn 17, 23, 25, 29, 30, 31) được gộp thành
1 công tắc dùng `"actions"`, ví dụ vừa mở cầu này vừa đóng cầu khác.
