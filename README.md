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
