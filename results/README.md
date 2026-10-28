# Task 5.5 — bảng và biểu đồ thực nghiệm

Nguồn yêu cầu: [Bảng + biểu đồ kết quả (5.5)](https://app.notion.com/p/d879cc1ed39082c59cef8180a9454e81).

## Trạng thái dữ liệu

**Các ảnh/bảng được bàn giao ở đây dùng dữ liệu chạy thử local ngày 28/10/2026,
không phải CSV chính thức của Task 1.7.** Mỗi ảnh/bảng có nhãn `LOCAL SAMPLE`.
Phần công cụ đã sẵn sàng nhận CSV chính thức; nghiệm thu số liệu và nhận xét cuối
cần chạy lại sau 1.7 và được nhóm kiểm tra khả năng đọc biểu đồ.

Hai file gốc ở `sample/bench.csv` và `sample/original.csv` được đo bằng runner 1.6,
trên code solver tại commit `acc01c6`, Python/machine ghi trong từng CSV.
Không sửa solver hoặc runner để tạo dữ liệu này. Chạy hai bộ tuần tự, không chạy
benchmark song song. Tham số: 5 lần đo thời gian, timeout 2 giây mỗi lần chạy;
đo RAM riêng theo API của runner. Số mẫu thực tế được giữ ở `time_ms_all` và
cột `samples` của bảng chi tiết. Không phải phép đo kiểm soát tải toàn bộ máy.

- Benchmark G1–G5: 17 màn × 5 thuật toán = **85 dòng solved, verified=True**.
- Màn gốc: 33 màn × 5 thuật toán = **165 dòng**. Mỗi thuật toán có 22 màn
  solved đã xác minh và 11 màn unsolvable; không có timeout/error trong lượt này.
- Các màn gốc được cả 5 thuật toán báo unsolvable: `stage_07`, `stage_11`,
  `stage_17`, `stage_18`, `stage_23`, `stage_25`, `stage_27`, `stage_28`,
  `stage_29`, `stage_30`, `stage_31`. Đây là kết quả với bản chuyển đổi/engine
  hiện có, không phải kết luận về khả năng giải của trò chơi gốc. Giữ các dòng
  đó trong phụ lục để nhóm kiểm tra nguồn/luật ở task liên quan.

## Một lệnh tạo báo cáo

Từ thư mục gốc repo, dùng Python trong `.venv`:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m benchmark.plots results/sample/bench.csv --original results/sample/original.csv --out results --label "LOCAL SAMPLE - 2026-10-28 (not Task 1.7)"
```

Khi có CSV chính thức 1.7:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m benchmark.plots results/final/results.csv --original results/final/original.csv --out results --label "Task 1.7 - official measurements"
```

`--original` là tùy chọn. Nếu chưa cung cấp, `tables/original.md` ghi rõ chưa có
dữ liệu phụ lục; không tự nhận bộ 17 màn là 33 màn gốc. Nếu CSV phụ lục chưa đủ
`stage_01`–`stage_33`, bảng liệt kê các id còn thiếu. `--out` là thư mục gốc cho
`figures/`, `tables/`, `manifest.json`. Các file có tên cố định được ghi lại khi
chạy lại, vì vậy dùng `--out results/tmp/preview` nếu chỉ muốn xem thử CSV khác.

Để tái tạo CSV mẫu (thời gian/RAM có thể thay đổi):

```powershell
.\.venv\Scripts\python.exe -X utf8 -m benchmark.run --stages stages/bench --repeat 5 --timeout 2 --out results/sample/bench.csv
.\.venv\Scripts\python.exe -X utf8 -m benchmark.run --stages stages/original --repeat 5 --timeout 2 --out results/sample/original.csv
```

`-X utf8` tránh lỗi in tiếng Việt ở terminal Windows dùng encoding khác UTF-8.
Không cần mở app đồ họa để đo hoặc xuất báo cáo.

## Sản phẩm đầu ra

| File | Nội dung |
| --- | --- |
| `figures/expanded.png` | Cột nhóm theo màn và thuật toán; trục y log, đơn vị nút |
| `figures/time.png` | Trung vị thời gian, trục y log, ms; bao gồm tiền xử lý heuristic |
| `figures/memory.png` | RAM đỉnh tracemalloc, KB = bytes/1024 |
| `figures/length_cost.png` | Hai ô độ dài (bước) và chi phí của BFS/UCS/A* relaxed |
| `figures/heuristics.png` | Expanded của A* relaxed và A* Manhattan, trục y log |
| `tables/summary.csv`, `summary.md` | Một dòng thuật toán × nhóm: solved/total, trung vị thời gian/RAM/expanded, trung bình độ dài/chi phí, số dòng thất bại/thiếu |
| `tables/details.csv`, `details.md` | Chi tiết từng màn, trạng thái, số mẫu đo thực tế |
| `tables/original.csv`, `original.md` | Phụ lục từng màn gốc, giữ cả màn unsolvable/timeout |
| `tables/observations.md` | 8 nhận xét nháp dựa trên dữ liệu, có giới hạn diễn giải |
| `manifest.json` | Nhãn bộ dữ liệu, đường dẫn, SHA-256 đầu vào (chuẩn hóa CRLF → LF), số dòng/màn, commit, Python, machine và quy ước đo |

Ảnh PNG xuất ở **180 dpi**, mỗi thuật toán giữ một màu cố định trong cả 5 ảnh.
Khi thiếu kết quả heuristic, ảnh tương ứng thông báo thiếu dữ liệu thay vì thay
bằng thuật toán khác. Có thể chạy lệnh trên CSV màn gốc với `--out` khác để xem
biểu đồ của cả 33 màn và các ký hiệu unsolvable.

## Quy tắc số liệu và so sánh

- Chỉ `status=solved` và `verified=True` được tính vào thống kê lời giải. Dòng
  solved nhưng verified=False được ghi `invalid`, verified trống là `unverified`.
- Màn timeout/unsolvable/error/cancelled/invalid/unverified vẫn có nhãn màn và
  ký hiệu riêng phía đáy biểu đồ; không vẽ số 0 giả cho lời giải thất bại. Cặp
  màn/thuật toán không có trong CSV được đánh dấu `missing` và tính vào mẫu số
  nhóm. Một màn hoàn toàn không có dòng nào trong CSV không thể được suy ra.
- `time_ms_median` ở summary là trung vị các trung vị theo màn, không phải
  trung vị gộp mọi lượt chạy. Mỗi dòng của runner làm tròn thời gian đến 0.1 ms;
  số 0 được đánh dấu riêng trên trục log, không tự thay bằng epsilon.
- RAM trống là thiếu phép đo, khác số 0. Trung vị RAM bỏ ô trống và công bố
  `memory_samples`. Đây là tracemalloc peak, không phải RSS toàn tiến trình.
  CSV 1.6 chưa ghi trạng thái riêng của lượt tracemalloc; công cụ này giữ số
  do runner cung cấp, không xác nhận riêng lượt đo RAM có chạy trọn lời giải.
- Trung vị/trung bình của mỗi thuật toán dùng tập màn thành công của chính nó.
  Không suy ra speedup từ hai trung vị nhóm khi tập thành công khác nhau.
  Nhận xét mức giảm expanded dùng tỷ lệ từng màn chung thành công rồi lấy
  trung vị; bỏ cặp có expanded tham chiếu bằng 0.
- Thời gian A* đã gồm tạo heuristic. Không suy từ ít expanded sang nhanh hơn.
  BFS hiện kiểm tra goal khi sinh successor, còn DFS/UCS/A* khi pop; giá trị
  expanded giữ nguyên từ runner và có thể khác quy ước đếm nút đích.
- Không ép DFS có độ dài/chi phí bằng UCS/A*. Hai màn hai lối `g2_02`, `g5_03`
  minh họa BFS ít bước hơn nhưng chi phí cao hơn UCS/A*.
- CSV phải đủ 14 cột của runner; số đo hữu hạn, không âm; length/expanded là
  số nguyên. Từ chối file rỗng, trùng stage/algorithm, trạng thái lạ, một màn
  thuộc nhiều nhóm hoặc trộn commit/Python/machine trong cùng bộ. Các lượt
  chạy cùng môi trường nhưng khác nhau không được tự động gộp.

## Kiểm tra

```powershell
.\.venv\Scripts\python.exe -m pytest tests/informed/test_plots.py -q -p no:cacheprovider --basetemp=results/tmp/pytest-plots
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=results/tmp/pytest-all
```

Không cần cài thư viện mới. Phần kiểm thử nằm ở `tests/informed/` (phạm vi VT5).
Sau khi VT1 review và có CSV chính thức 1.7, chạy lại lệnh xuất báo cáo, xem ảnh,
và đưa bảng/nhận xét đã duyệt vào các mục 5.4–5.6 cùng phụ lục của báo cáo nhóm.
