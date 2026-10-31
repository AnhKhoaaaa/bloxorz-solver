# Hướng Dẫn Đóng Góp (CONTRIBUTING)

Chào mừng các thành viên nhóm Bloxorz Solver! Tài liệu này quy định quy trình làm việc với Git, Review code và các quy tắc kỹ thuật chung nhằm đảm bảo mã nguồn ổn định, nhất quán.

---

## 1. 5 Điều Quan Trọng Nhất
1. **Chỉ sửa file của mình.** Cần sửa file người khác thì nhắn người đó.
2. **Không đẩy thẳng lên `main`.** Mỗi task làm trên một nhánh riêng rồi mở PR (Ngoại lệ duy nhất là task 1.1 khởi tạo repo).
3. **Merge xong thì báo nhóm** nếu có người đang chờ phần của bạn.
4. **Mỗi tối trước 22:00** gửi 3 dòng báo cáo tiến độ vào nhóm chat.
5. **Kẹt quá 1 ngày thì báo Lead ngay.**

---

## 2. Quy Trình Làm Việc Với Git

### Các bước cho một task:
```bash
# 1. Lấy code mới nhất từ main
git switch main && git pull

# 2. Tạo nhánh mới cho task
git switch -c feat/<mã_task>-<mô tả ngắn>

# 3. Code + viết test, rồi commit (chỉ add file thuộc quyền phụ trách)
git add <file của mình>
git commit -m "feat(<module>): <mô tả ngắn bằng tiếng Anh hoặc tiếng Việt>"

# 4. Cập nhật main mới nhất và chạy test lại
pytest -q && git fetch origin && git merge origin/main && pytest -q

# 5. Đẩy lên GitHub, mở PR và chọn reviewer theo phân công
git push -u origin feat/<mã_task>-<mô tả ngắn>
```

### Đặt tên nhánh:
- Công thức: `loại/mã_task-mô_tả_ngắn` (chữ thường, nối bằng gạch ngang).
- Ví dụ:
  - `feat/2.1-basic-engine`
  - `fix/2.3-heavy-switch`
  - `test/1.4-bfs`

> ⏱️ **Lưu ý:** Hạn chế để một nhánh làm task quá 3 ngày để tránh xung đột mã nguồn (conflict).

### Quy ước Commit:
- Cú pháp: `loại(module): nội dung tóm tắt`
- Các loại commit:
  - `feat`: Thêm tính năng mới.
  - `fix`: Sửa lỗi.
  - `test`: Thêm hoặc sửa test.
  - `refactor`: Sắp xếp lại mã nguồn (không đổi hành vi).
  - `docs`: Cập nhật tài liệu, README.
  - `chore`: Cấu hình, thư viện, việc lặt vặt.
- Các module hợp lệ: `engine`, `switch`, `split`, `bfs`, `dfs`, `ucs`, `astar`, `heur`, `scene`, `app`, `loader`, `bench`, `report`...
- Ví dụ:
  - `feat(engine): add roll transition table`
  - `fix(switch): ignore heavy switch when lying`

### Mở và Merge Pull Request (PR):
1. Tiêu đề PR: `loại(module): mô tả thay đổi (mã task)` (ví dụ: `feat(switch): add soft/heavy switches and bridges (2.3)`).
2. Điền đầy đủ thông tin theo mẫu PR (mã task, việc đã làm, lệnh kiểm tra, `Closes #số_issue`).
3. Tag đúng **Reviewer** theo bảng phân công bên dưới và gửi link PR vào nhóm Zalo.
4. Reviewer phản hồi trong vòng 24 giờ. Tác giả sửa đổi trực tiếp trên cùng nhánh nếu có yêu cầu chỉnh sửa.
5. **Chỉ Lead (VT1)** mới được bấm **"Squash and merge"** khi: PR đã được approve, CI test xanh và không có conflict. Sau khi merge, xóa nhánh feature.
6. Tag người cần dùng phần code này ở bước tiếp theo vào Zalo.

---

## 3. Bảng Phân Công Review Code

| Viết code | Reviewer chính | Ghi chú |
| :---: | :---: | :--- |
| **VT1** | **VT5** | |
| **VT2** | **VT1** | (Nếu VT1 vắng thì VT5) |
| **VT3** | **VT4** | |
| **VT4** | **VT3** | (Riêng file `loader.py`: **VT2**) |
| **VT5** | **VT1** | |

### Checklist cho Reviewer:
- [ ] Kéo nhánh về máy, chạy `pytest -q` thấy toàn bộ test xanh.
- [ ] PR chỉ sửa các file thuộc phạm vi phân công của tác giả.
- [ ] Có kèm test tương ứng với kết quả kiểm thử cụ thể.
- [ ] Người review đọc hiểu code để tự tin giải thích khi được hỏi.

---

## 4. Quy Tắc Code (Code Rules)
1. **Đảm bảo tính độc lập của logic:**
   - Các module logic (`bloxorz/model.py`, `bloxorz/stage.py`, `bloxorz/engine/`, `bloxorz/search/`, `benchmark/`, `tests/`) tuyệt đối không phụ thuộc môi trường đồ họa để đảm bảo logic chạy độc lập (headless).
2. **Không sửa test chỉ để test xanh:**
   - Nếu test fail, phải tìm nguyên nhân từ logic triển khai hoặc trao đổi với người viết test.
3. **Quản lý dependencies:**
   - Chỉ Lead (VT1) mới được phép cập nhật `requirements.txt`. Nếu cần thư viện mới, đề xuất lên nhóm.
4. **Quy trình thay đổi Contract (Khung dữ liệu / Giao tiếp chung):**
   - Không tự ý thay đổi tên hàm, tham số truyền vào, cấu trúc trả về của các class/hàm trong `model.py`, `stage.py`, `rules.py` hay định dạng file JSON màn chơi.
   - Khi cần đổi: đề xuất lên Zalo (nêu rõ lý do và module bị ảnh hưởng) $\rightarrow$ thống nhất với Lead và các bên liên quan trước khi sửa.
5. **Quy ước thứ tự duyệt rẽ nhánh (Tie-breaking convention):**
   - Để đảm bảo tính khách quan, công bằng và tái lập được (deterministic) khi chạy Benchmark so sánh các thuật toán (BFS, DFS, UCS, A*), tất cả solver **bắt buộc** phải duyệt các hướng di chuyển theo thứ tự ưu tiên cố định:
     `Direction.UP -> Direction.DOWN -> Direction.LEFT -> Direction.RIGHT`
   - Bắt buộc import và sử dụng hằng số `ORDERED_DIRECTIONS` từ `bloxorz.search.base` (hoặc `bloxorz.search`).

