# Kết Quả Thực Nghiệm Chính Thức (Official Benchmark Results)

Tài liệu này ghi nhận môi trường thực thi, cấu hình phần cứng và tổng hợp kết quả đo đạc chính thức của **Task 1.7** cho toàn bộ 5 thuật toán tìm kiếm trên 2 bộ màn chơi của đồ án Bloxorz Solver.

---

## 1. Môi Trường Thực Thi & Cấu Hình Phần Cứng

Để đảm bảo số liệu đo đạc thời gian (`time_ms_median`) và bộ nhớ đỉnh (`peak_mem_kb`) đạt tính khách quan, ổn định và có thể tái lập, toàn bộ quá trình benchmark được thực hiện trong điều kiện:
- Máy tính cắm sạc nguồn trực tiếp (AC Power plugged in), bật chế độ hiệu năng cao (Best Performance), tắt các phần mềm chạy ngầm nặng.
- Hệ thống thực thi:

| Thông số | Giá trị thực tế |
| :--- | :--- |
| **Vi xử lý (CPU)** | 12th Gen Intel(R) Core(TM) i5-12500H (12 nhân, 16 luồng, xung nhịp cơ bản 2.5 GHz, Boost tối đa 4.5 GHz) |
| **Định danh CPU trong CSV** | `Intel64 Family 6 Model 154 Stepping 3, GenuineIntel` |
| **Bộ nhớ trong (RAM)** | 16 GB (16,474,616 KB khả dụng) |
| **Hệ điều hành (OS)** | Microsoft Windows 11 Pro 64-bit (Version 10.0.22621) |
| **Phiên bản Python** | Python 3.13.6 (64-bit) |
| **Mã Git Commit** | `7f77404` (tại git tag `stages-v1`) |
| **Thời điểm chạy** | 28/10/2026 |

---

## 2. Thiết Lập Tham Số Benchmark

- **Số lần lặp đo thời gian (`--repeat`):** `5` lần chạy thuần túy (`measure_memory=False`), lấy giá trị **trung vị (median)** làm đại diện và lưu toàn bộ 5 lần đo vào `time_ms_all`.
- **Đo bộ nhớ đỉnh (`peak_mem_kb`):** Chạy thêm `1` lần riêng biệt có bật công cụ `tracemalloc` (`measure_memory=True`).
- **Giới hạn thời gian (`--timeout`):** `60.0` giây cho mỗi màn chơi $\times$ thuật toán.
- **Danh sách 5 thuật toán:**
  1. `bfs` (Breadth-First Search)
  2. `dfs` (Depth-First Search có tập visited / parents chống lặp)
  3. `ucs` (Uniform-Cost Search tối ưu chi phí gạch mỏng)
  4. `astar` (A* Search với heuristic Relaxed Trajectory)
  5. `astar_manhattan` (A* Search với heuristic Manhattan)
- **Kiểm định tính đúng đắn (`verified`):** 100% kết quả có trạng thái `solved` đều được kiểm tra tính hợp lệ bằng hàm `bloxorz.verify.verify_solution`.

---

## 3. Tổng Hợp Kết Quả Thực Nghiệm

| Tên File | Bộ màn chơi khảo sát | Số màn | Số thuật toán | Tổng số dòng | Tỷ lệ Solved | Tỷ lệ Verified |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`results.csv`** | `stages/bench` (Bộ thực nghiệm G1 – G5) | 17 | 5 | 85 | **85/85 (100%)** | **85/85 (100%)** |
| **`original.csv`** | `stages/original` (Bộ màn Bloxorz gốc) | 33 | 5 | 165 | **165/165 (100%)** | **165/165 (100%)** |

> 🎯 **Nhận xét sơ bộ:**
> - Cả 5 thuật toán đều giải thành công 100% các màn chơi trong thời gian cho phép mà không bị timeout hay gặp lỗi.
> - Toàn bộ các chuỗi hành động tìm được đều đưa khối về đúng lỗ đích ở tư thế đứng và tuân thủ chặt chẽ luật chơi của engine (`verified = True`).
> - Dữ liệu này được bàn giao nguyên vẹn cho **VT5** để tiến hành chạy script `benchmark/plots.py` vẽ các biểu đồ so sánh và trích xuất bảng số liệu cho báo cáo đồ án.

---

## 4. Cấu Trúc Các Cột Trong File CSV

Mỗi file CSV gồm đúng 14 cột theo quy chuẩn của dự án:

1. `stage_id`: Mã định danh màn chơi (ví dụ `g1_01`, `stage_05`).
2. `group`: Nhóm màn chơi (`G1`, `G2`, `G3`, `G4`, `G5` hoặc `original`).
3. `algorithm`: Tên thuật toán (`bfs`, `dfs`, `ucs`, `astar`, `astar_manhattan`).
4. `status`: Trạng thái kết thúc (`solved`, `unsolvable`, `timeout`, `error`).
5. `length`: Số bước di chuyển trong lời giải (số lượng Action).
6. `cost`: Tổng chi phí bước đi (tính theo hàm `move_cost`).
7. `expanded`: Số lượng nút trạng thái đã mở rộng (`ctx.expanded`).
8. `time_ms_median`: Trung vị thời gian chạy thuật toán (đơn vị: mili-giây ms).
9. `time_ms_all`: Danh sách thời gian chạy của cả 5 lần lặp, ngăn cách bởi dấu chấm phẩy `;`.
10. `peak_mem_kb`: Bộ nhớ RAM đỉnh điểm tiêu thụ bởi thuật toán (đơn vị: Kilobytes kB).
11. `verified`: Kết quả kiểm định độc lập qua `verify_solution` (`True` / `False`).
12. `commit`: Mã commit hash ngắn của phiên bản code lúc chạy.
13. `python`: Phiên bản Python thực thi.
14. `machine`: Chuỗi định danh vi xử lý / phần cứng.

---

## 5. Lệnh Tái Lập Kết Quả (Reproduction)

Để chạy lại toàn bộ quy trình đo đạc từ đầu:

```bash
# 1. Đo trên bộ màn thực nghiệm G1-G5:
python -m benchmark.run --stages stages/bench --algos bfs dfs ucs astar astar_manhattan --repeat 5 --timeout 60 --out results/final/results.csv

# 2. Đo trên bộ màn gốc:
python -m benchmark.run --stages stages/original --algos bfs dfs ucs astar astar_manhattan --repeat 5 --timeout 60 --out results/final/original.csv
```

