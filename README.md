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
Chạy lệnh kiểm tra test đầu tiên (smoke test):
```bash
pytest -q
```
Kết quả mong đợi: `1 passed in ...s`.

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
