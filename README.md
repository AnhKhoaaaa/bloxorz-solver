# Bloxorz Solver 🎮

Dự án đồ án môn Trí tuệ Nhân tạo (CSAI) - HCMUS.
Chương trình mô phỏng game giải đố Bloxorz 3D bằng Python, hỗ trợ người chơi tương tác trực tiếp và cung cấp 4 thuật toán tìm kiếm tự động: **BFS**, **DFS**, **UCS**, **A\***.

---

## 🛠️ Yêu Cầu Môi Trường
- **Python**: 3.12 (khuyến nghị) hoặc 3.13.
- **Hệ điều hành**: Windows / Linux / macOS.

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
Kết quả mong đợi: toàn bộ test `passed`, không có `failed`.

---

## 🎮 Chạy Chương Trình

```bash
python main.py                                   # cửa sổ 3D, bắt đầu từ màn gốc đầu tiên (stages/original)
python main.py --stage stage_05                  # bắt đầu từ màn có id stage_05
python main.py --stage stages/fixtures/split.json   # chơi đúng 1 file màn
python main.py --stages-dir stages/bench         # chơi bộ màn thực nghiệm G1–G5
python main.py --text                            # chơi trong terminal, không cần Ursina
```

### Điều khiển
| Phím | Nút trên màn hình | Tác dụng |
| :--- | :--- | :--- |
| Mũi tên / `W` `A` `S` `D` | | Lăn khối |
| `Space` | | Đổi khối đang điều khiển khi khối đã tách |
| `R` | **Chơi lại** | Chơi lại màn từ đầu |
| `U` / `Backspace` | **Lùi 1 bước** | Lùi 1 bước (kể cả ngay sau khi rơi) |
| `N` / `P` | **Màn sau** / **Màn trước** | Đổi màn |
| `Esc` | | Thoát |

### Giải tự động (bảng SOLVER bên phải)
| Phím | Nút | Tác dụng |
| :--- | :--- | :--- |
| `Tab` | Bấm tên thuật toán | Chọn thuật toán (danh sách lấy từ các solver đã đăng ký trong `bloxorz/search`) |
| `G` | **GIẢI (G)** | Giải màn hiện tại từ vị trí xuất phát, chạy nền nên cửa sổ không bị treo (giới hạn 60 giây) |
| `Enter` | **REPLAY (Enter)** | Phát lại lời giải từng bước có hoạt ảnh; nhấn lần nữa để tạm dừng / chạy tiếp |
| `C` | **HỦY (C)** | Hủy lần giải đang chạy hoặc dừng replay |

Sau khi giải, bảng hiện trạng thái (có lời giải / không có lời giải / quá thời gian / đã hủy), số bước, chi phí,
số nút đã mở rộng và thời gian chạy. Trong lúc replay, phím chơi tay bị khóa để không lệch với lời giải.

### Lưu ý trên macOS
Trên một số máy Mac (ví dụ Apple Silicon), OpenGL chỉ hỗ trợ GLSL 1.20 trong khi shader mặc định của Ursina 8
dùng GLSL 1.30/1.40, nên cảnh 3D có thể hiện màu đen (terminal báo `version '130' is not supported`).
Chữ và nút 2D vẫn hiện bình thường. Khi gặp lỗi này có thể chơi bằng `python main.py --text`.

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
│   └── gui/                   # Giao diện người dùng & cảnh 3D Ursina (VT3, VT4)
├── stages/                    # Dữ liệu các màn chơi
│   ├── fixtures/              # Màn mẫu cơ bản dùng cho unit test (VT4)
│   ├── original/              # 33 màn gốc chuyển đổi (VT4)
│   └── bench/                 # Bộ màn thực nghiệm G1-G5 (VT5)
├── benchmark/                 # Công cụ đo đạc thực nghiệm (VT1, VT5)
├── results/                   # Bảng số liệu và đồ thị kết quả (VT1, VT5)
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
