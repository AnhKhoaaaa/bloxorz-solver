# Bloxorz Solver 🎮

Dự án đồ án môn Trí tuệ Nhân tạo (CSAI) - HCMUS.
Chương trình mô phỏng game giải đố Bloxorz 3D bằng Python, hỗ trợ người chơi tương tác trực tiếp và cung cấp 4 thuật toán tìm kiếm tự động: **BFS**, **DFS**, **UCS**, **A\***.

---

## 🛠️ Yêu Cầu Môi Trường
- **Python**: 3.12 (khuyến nghị) hoặc 3.13.
- **Hệ điều hành**: Windows / Linux / macOS.
- **Trình duyệt** hỗ trợ WebGL (Chrome, Edge, Firefox, Safari) để hiển thị cảnh 3D.

---

## 🚀 Cài Đặt & Chạy Thử Nghiệm

### 1. Clone repository
```bash
git clone <URL_REPO_GITHUB>
cd bloxorz-solver
```

### 2. Thiết lập môi trường ảo (Virtual Environment)
- **Trên Windows:**
  ```cmd
  py -3.12 -m venv .venv
  .venv\Scripts\activate
  pip install --upgrade pip
  pip install -r requirements.txt
  ```
- **Trên Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

### 3. Kiểm tra môi trường với Pytest
```bash
pytest -q
```
Kết quả mong đợi: tất cả test đều `passed`.

---

## 🎮 Chạy Ứng Dụng

```bash
python main.py                                      # chơi 33 màn gốc, bắt đầu từ màn 1
python main.py --stage stage_05                     # chơi 33 màn gốc, bắt đầu từ màn stage_05
python main.py --stages-dir stages/custom           # chơi các màn trong 1 thư mục khác
python main.py --stage stages/fixtures/split.json   # chỉ chơi đúng 1 file màn
python main.py --stages-dir stages/fixtures --text  # chơi trong terminal, không cần đồ họa
```

| Tham số | Ý nghĩa |
| :--- | :--- |
| `--stages-dir <thư mục>` | Thư mục chứa các file màn `*.json` (mặc định `stages/original`) |
| `--stage <id hoặc file>` | Màn bắt đầu: id màn trong thư mục (vd. `stage_05`) hoặc đường dẫn tới 1 file `.json` |
| `--text` | Chơi trong terminal thay vì cảnh 3D |

- Cảnh 3D chạy bằng WebGL (Three.js). Nếu máy đã cài `pywebview` (`pip install pywebview`) thì mở trong cửa sổ riêng; nếu chưa thì tự mở trong trình duyệt mặc định. Dừng chương trình bằng `Ctrl+C` trong terminal.
- Khi nạp cả thư mục màn: thắng xong tự sang màn tiếp theo; `N` / `P` để đổi màn, đi quá màn cuối thì quay về màn đầu.

### Điều khiển

| Phím | Tác dụng |
| :--- | :--- |
| `↑ ↓ ← →` / `W A S D` | Lăn khối |
| `Space` | Đổi khối đang điều khiển khi khối đã tách đôi |
| `U` | Lùi 1 bước |
| `R` | Chơi lại màn |
| `N` / `P` | Màn sau / màn trước |
| `G` | Giải màn hiện tại bằng A\* |
| `1` / `2` / `3` | Đổi khung cảnh (Overworld / Nether / End) |
| `C` / `T` | Camera về góc mặc định / nhìn từ trên xuống |
| `Q` / `E` | Xoay camera 45° |

Ở chế độ `--text`, gõ phím rồi Enter (có thể gõ nhiều phím một lần, vd. `ddw`): `W/A/S/D` lăn khối, dấu cách đổi khối khi tách, `U` lùi, `R` chơi lại, `N/P` đổi màn, `Q` thoát.

### Giải tự động bằng AI
Bấm nút **A\***, **BFS**, **DFS** hoặc **UCS** trên màn hình (hoặc phím `G` cho A\*). Chương trình giải màn hiện tại từ vị trí xuất phát rồi phát lại lời giải từng bước. Góc màn hình hiện kết quả:

```
A*: 12 MOVES | COST 12 | 3.5ms | 140 NODES      # có lời giải: số bước, chi phí, thời gian, số nút đã mở rộng
DFS: QUÁ THỜI GIAN | 90000 NODES                # không giải được: lý do (không có lời giải / quá thời gian / lỗi)
```

---

## 📁 Cấu Trúc Dự Án
```
bloxorz-solver/
├── main.py                    # Điểm khởi chạy ứng dụng chính (VT4)
├── requirements.txt           # Danh sách thư viện phụ thuộc (VT1)
├── CONTRIBUTING.md            # Hướng dẫn quy trình Git & review (VT1)
├── README.md                  # Hướng dẫn cài đặt và sử dụng (VT4 hoàn thiện)
├── conftest.py                # Cấu hình pytest (VT1)
├── bloxorz/                   # Gói mã nguồn cốt lõi
│   ├── model.py               # Các cấu trúc dữ liệu cốt lõi State, Action (VT1)
│   ├── stage.py               # Quản lý bản đồ, cầu, công tắc (VT1)
│   ├── loader.py              # Đọc và xác thực dữ liệu màn chơi JSON (VT4)
│   ├── verify.py              # Kiểm tra tính hợp lệ của đường đi nghiệm (VT1)
│   ├── engine/                # Luật chuyển động và cơ chế game (VT2)
│   ├── search/                # Các giải thuật tìm kiếm BFS, DFS, UCS, A* (VT1, VT5)
│   └── gui/                   # Giao diện người dùng
│       ├── app.py             # Khởi chạy ứng dụng, xử lý sự kiện từ cảnh 3D (VT4)
│       ├── controller.py      # Trạng thái ván chơi: lăn, lùi, chơi lại, đổi màn, đổi khối (VT4)
│       ├── solver_runner.py   # Gọi solver và chuẩn bị lời giải để phát lại (VT4)
│       ├── fake_scene.py      # Chế độ chơi trong terminal (VT4)
│       ├── web/               # Thanh thông tin, nút bấm và phím chơi trên cảnh 3D (VT4)
│       └── scene/             # Cảnh 3D WebGL Three.js và cầu nối Python ↔ trình duyệt (VT3)
├── stages/                    # Dữ liệu các màn chơi
│   ├── fixtures/              # Màn mẫu cơ bản dùng cho unit test (VT4)
│   ├── original/              # 33 màn gốc chuyển đổi (VT4)
│   ├── custom/                # Màn tự thiết kế
│   └── bench/                 # Bộ màn thực nghiệm G1-G5 (VT5)
├── benchmark/                 # Công cụ đo đạc thực nghiệm (VT1, VT5)
├── results/                   # Bảng số liệu và đồ thị kết quả (VT1, VT5)
├── tools/
│   └── convert_quick_bloxorz.py  # Chuyển 33 màn gốc sang định dạng JSON của nhóm (VT4)
└── tests/                     # Hệ thống kiểm thử tự động với pytest
```

---

## 🗺️ Định Dạng File Màn Chơi (JSON)
Mỗi màn là 1 file `.json` (UTF-8). Đặc tả đầy đủ nằm ở docstring của `bloxorz/loader.py`; ví dụ mẫu ở `stages/fixtures/`.

```json
{
  "id": "fixture_bridge_soft",
  "group": "G2",
  "grid": ["S###BB###G"],
  "bridges": [{"id": "b1", "cells": [[0, 4], [0, 5]], "initially_open": false}],
  "switches": [{"id": "s1", "kind": "soft", "pos": [0, 1], "mode": "toggle", "bridges": ["b1"]}]
}
```

| Ký tự | Ý nghĩa | Ký tự | Ý nghĩa |
| :---: | :--- | :---: | :--- |
| `.` | Khoảng trống (rơi) | `G` | Lỗ đích (đúng 1 ô) |
| `#` | Sàn thường | `F` | Ô dễ vỡ (không được đứng) |
| `S` | Ô xuất phát (đúng 1 ô) | `B` | Ô cầu (khai báo trong `bridges`) |

- Tọa độ là `[hàng, cột]`, `(0, 0)` ở góc trên-trái.
- Công tắc `soft`/`heavy`: bắt buộc `mode` (`toggle` | `permanent`), `bridges`; `set_to` (`open` | `close`) chỉ dùng khi `permanent`.
- Công tắc làm nhiều việc cùng lúc: thay `mode`/`set_to`/`bridges` bằng `"actions": [["b1", "open"], ["b2", "close"]]` (`toggle` | `open` | `close`).
- Công tắc `split`: chỉ có `targets` gồm 2 ô.

```python
from bloxorz.loader import load_stage, load_stages
stage = load_stage("stages/fixtures/basic.json")   # ném StageFormatError nếu file sai, kèm danh sách mọi lỗi
stages = load_stages("stages/original")
```

Muốn tự tạo màn mới: viết file `.json` theo định dạng trên vào `stages/custom/` rồi chạy `python main.py --stages-dir stages/custom`. File sai định dạng sẽ bị báo lỗi kèm vị trí cụ thể khi nạp.

---

## 📜 Nguồn Dữ Liệu Màn Chơi
33 màn trong `stages/original/` được chuyển đổi từ [Quick Bloxorz](https://github.com/jgordon510/quick_bloxorz) của Jeffrey Gordon (giấy phép CC BY) bằng `tools/convert_quick_bloxorz.py`:

```bash
git clone https://github.com/jgordon510/quick_bloxorz /tmp/quick_bloxorz
python tools/convert_quick_bloxorz.py /tmp/quick_bloxorz/maps --out stages/original
```
