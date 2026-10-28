# 🐞 BÁO CÁO TOÀN DIỆN CÁC LỖI LOGIC GAME & RỦI RO TIỀM ẨN
**Dự án:** Bloxorz Solver (CSC14003 - Cơ sở Trí tuệ Nhân tạo - FIT, HCMUS)  
**Phân hệ rà soát:** Engine lõi (VT1, VT2) & Controller / GUI (VT4)  
**Người tổng hợp:** VT3 (Phân hệ Cảnh 3D & Hoạt ảnh)  
**Ngày báo cáo:** 28/10/2026  

---

## 📌 TÓM TẮT ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Trong quá trình tích hợp cảnh 3D vào hệ thống chung của nhóm (`bloxorz-solver`), phân hệ VT3 đã rà soát toàn bộ luồng xử lý trạng thái và phát hiện **6 vấn đề logic nghiêm trọng** trong `bloxorz/engine/` và `bloxorz/gui/controller.py`. 

Các lỗi này không thuộc về đồ họa hay diễn họa 3D, mà nằm ở:
1. **Ô đích `'G'` bị chặn cứng**: Nằm đè lên ô đích bị xử thua/rơi thay vì cho phép đi qua.
2. **Xung đột ký tự gạch dễ vỡ (`FRAGILE_TILES`)**: Chứa cả `'x'` và `'o'`, gây sập sàn khi đứng lên công tắc.
3. **Viên cube con $1 \times 1 \times 1$ dẫm vào `'G'` bị xử chết**: Không đúng với tinh thần Mục 2.5 của đề bài.
4. **Bỏ quên công tắc khi 2 viên cube con ghép lại (Rejoining)**.
5. **Lệch chỉ số `active_cube` trong Controller** khi tọa độ 2 cube bị tráo đổi do hàm sort của `State`.
6. **Xung đột phím điều khiển (`Space`)** giữa Controller (đổi khối) và các phân hệ khác.

---

## 🚨 CHI TIẾT CÁC LỖI & PHÂN TÍCH NGUYÊN NHÂN GỐC (ROOT CAUSE)

### 1. BUG 1 (NGUYÊM TRỌNG): Nằm đè qua ô Đích `'G'` bị xử thua/rớt xuống vực

* **Vị trí trong mã nguồn:**
  * File: `bloxorz/engine/rules.py` — Dòng 161–164:
  ```python
  # bloxorz/engine/rules.py (hàm is_valid_state)
  # 4. Kiểm tra ô đích 'G'
  # Chỉ được phép đứng vào lỗ đích, nếu nằm đè qua lỗ đích sẽ bị rơi
  if ch == "G" and state.pose != Pose.STANDING:
      return False
  ```
  * Unit test ràng buộc: `tests/engine/test_rules.py` — Dòng 240:
  ```python
  def test_goal_tile_lying_is_invalid(basic_stage):
      """Ô đích 'G' là một lỗ vuông (goal hole), khối nằm đè qua lỗ sẽ bị rơi xuống lỗ."""
      assert is_valid_state(State(Pose.HORIZONTAL, (3, 2)), basic_stage) is False
      assert is_valid_state(State(Pose.VERTICAL, (2, 3)), basic_stage) is False
  ```

* **Hiện tượng thực tế:**
  * Khi người chơi lăn khối ở tư thế nằm ngang (`HORIZONTAL`) hoặc nằm dọc (`VERTICAL`), nếu có một nửa thân khối đè lên ô đích `'G'` (ví dụ ô sàn liền kề `'G'` vẫn là sàn hợp lệ), game lập tức phán quyết `None` (Rơi vực) và kích hoạt hoạt ảnh rơi thua cuộc.

* **Đối chiếu với Đề bài chính thức (`AI - Project 1.pdf`, Section 2.4 - Victory):**
  > *"A stage is won when the block falls into the goal hole. This happens only when the block is standing upright on the goal cell. **A block that merely lies across the goal cell does not win.**"*
  > *(Trò chơi chỉ thắng khi khối rơi đứng thẳng vào lỗ đích. **Một khối chỉ nằm đè qua ô đích thì KHÔNG THẮNG**).*

* **Phân tích tranh cãi kỹ thuật:**
  * Đề bài ghi rõ là **"does not win"** (không kích hoạt điều kiện thắng), chứ **không ghi là "falls and loses"** (rơi xuống vực và thua).
  * Trong thiết kế game giải đố, ô đích có thể nằm giữa một hành lang. Khối có quyền lăn nằm đè qua ô đích để sang bờ bên kia quay đầu lấy góc đứng. Việc ép `return False` biến ô đích thành "hố tử thần" và chặn đứng nhiều đường đi hợp lệ của người chơi cũng như thuật toán tìm kiếm.

* **Kiến nghị giải pháp:**
  * **Trách nhiệm:** **VT2**.
  * **Đề xuất sửa:** Xóa bỏ việc kiểm tra `ch == "G"` trong `is_valid_state()`. Chỉ giữ logic kiểm tra thắng tại `is_goal(state, stage)`:
  ```python
  def is_goal(state: State, stage: Stage) -> bool:
      return state.pose == Pose.STANDING and state.pos == stage.goal
  ```

---

### 2. BUG 2 (NGUY CƠ CAO): Ký tự gạch dễ vỡ (`FRAGILE_TILES`) xung đột với công tắc (`'x'`, `'o'`)

* **Vị trí trong mã nguồn:**
  * File: `bloxorz/engine/rules.py` — Dòng 22:
  ```python
  FRAGILE_TILES: frozenset[str] = frozenset({"F", "f", "x", "X", "o", "O"})
  ```

* **Phân tích rủi ro:**
  * Trong quy ước chuẩn của Bloxorz và các bộ dữ liệu cộng đồng:
    * **`'o'`** là ký hiệu chuẩn của **Soft Switch** (công tắc tròn/bát giác).
    * **`'x'`** là ký hiệu chuẩn của **Heavy Switch** (công tắc chữ X).
  * Việc VT2 đưa cả `'x'` và `'o'` vào danh sách gạch dễ vỡ tạo ra lỗ hổng nghiêm trọng: Nếu người dùng nạp một màn chơi ASCII có công tắc nặng ký hiệu `'x'` trên bản đồ, khi khối **ĐỨNG THẲNG** lên ô này để kích hoạt cầu thì sàn sẽ **bị vỡ và khối rơi chết ngay lập tức**.

* **Kiến nghị giải pháp:**
  * **Trách nhiệm:** **VT2 & VT1**.
  * **Đề xuất sửa:** Rút gọn `FRAGILE_TILES` về duy nhất:
  ```python
  FRAGILE_TILES: frozenset[str] = frozenset({"F", "f"})
  ```

---

### 3. BUG 3: Cube con $1 \times 1 \times 1$ bước vào ô đích `'G'` bị giết chết vô lý

* **Vị trí trong mã nguồn:**
  * File: `bloxorz/engine/split.py` — Dòng 165:
  ```python
  ch = stage.cell(new_p)
  # Cube đơn rơi vào void '.' hoặc rơi vào lỗ Goal 'G' là thua
  if ch == "." or ch == "G":
      return None
  ```
  * File: `bloxorz/engine/rules.py` — Dòng 137:
  ```python
  if ch == "." or ch == "G":
      return False
  ```

* **Đối chiếu với Đề bài chính thức (Section 2.5 - Block splitting):**
  > *"A single cube can activate soft switches but cannot activate heavy switches or complete the stage."*
  > *(Một khối cube đơn lẻ có thể kích hoạt công tắc mềm nhưng không thể kích hoạt công tắc nặng hoặc hoàn thành màn chơi).*

* **Phân tích:**
  * Đề bài chỉ quy định cube con **không thể hoàn thành màn chơi** (`cannot complete the stage`).
  * Việc coi `'G'` như một khoảng trống chết người khiến một viên cube con không thể đi băng qua khu vực có ô đích để hội ngộ với viên còn lại.

* **Kiến nghị giải pháp:**
  * **Trách nhiệm:** **VT2**.
  * **Đề xuất sửa:** Cho phép cube con đi qua `'G'` bình thường, chỉ chặn không kích hoạt `is_goal()` (điều này đã được `is_goal` đảm bảo vì `state.pose is None`).

---

### 4. BUG 4: Ghép khối khi tách (Cube Rejoining) bỏ sót công tắc tại vị trí viên thứ hai

* **Vị trí trong mã nguồn:**
  * File: `bloxorz/engine/split.py` — Dòng 175–190 (`step_split`):
  ```python
  # 3. Kích hoạt soft switch nếu có tại ô mới
  new_bridges = trigger_switches(stage, None, (new_p,), state.bridges_open)
  ...
  # 5. Kiểm tra tự động ghép khối nếu 2 cube kề nhau
  merged = try_merge_cubes(new_p, p_other, new_bridges)
  if merged is not None:
      from .rules import is_valid_state
      if not is_valid_state(merged, stage):
          return None
      return merged
  ```

* **Phân tích:**
  * Khi viên A di chuyển đến `new_p` kề với viên B (`p_other`), chúng hợp nhất thành khối $1 \times 1 \times 2$.
  * Trong mã nguồn hiện tại, `trigger_switches` chỉ được gọi cho tọa độ `(new_p,)` với `pose=None`.
  * Nếu tại tọa độ của viên B (`p_other`) có một công tắc, hoặc sau khi hợp nhất tạo thành một thế đứng kích hoạt công tắc nặng, thì công tắc đó **hoàn toàn không được kích hoạt** vì không có bước quét công tắc lại cho khối `merged`.

* **Kiến nghị giải pháp:**
  * **Trách nhiệm:** **VT2**.
  * **Đề xuất sửa:** Sau khi `merged = try_merge_cubes(...)` thành công, cần gọi lại:
  ```python
  if merged is not None:
      cells = get_block_cells(merged.pose, merged.pos)
      final_bridges = trigger_switches(stage, merged.pose, cells, new_bridges)
      merged = State(pose=merged.pose, pos=merged.pos, bridges_open=final_bridges)
  ```

---

### 5. BUG 5: Lệch chỉ số `active_cube` trong Controller khi 2 cube tráo đổi vị trí

* **Vị trí trong mã nguồn:**
  * File: `bloxorz/gui/controller.py` — Dòng 86–90:
  ```python
  if new.pose is None:
      # State luôn chuẩn hóa pos < cube2 nên viên vừa đi có thể bị đổi chỗ sang cube2:
      # chọn lại đúng viên vừa đi để nước sau không "nhảy khối".
      self.active_cube = 1 if new.pos == still else 0
  ```

* **Phân tích:**
  * `State` trong `model.py` luôn tự động sắp xếp sao cho `pos < cube2` (theo thứ tự hàng, cột).
  * Do đó, khi viên cube đang di chuyển vượt qua mặt viên đang đứng yên, vị trí của chúng trong `State` sẽ bị hoán đổi.
  * Phép so sánh `new.pos == still` của VT4 là một mẹo heuristic. Trong các trường hợp di chuyển phức tạp hoặc khi người chơi bấm **Undo (`U`)**, chỉ số `active_cube` có thể bị nhảy lung tung giữa viên 0 và viên 1, dẫn đến việc người chơi bấm phím nhưng viên cube bị điều khiển lại là viên kia.

* **Kiến nghị giải pháp:**
  * **Trách nhiệm:** **VT4**.
  * **Đề xuất sửa:** Controller nên lưu trực tiếp tọa độ của viên đang được chọn (`active_pos: Pos`) thay vì dựa vào chỉ số `0` hoặc `1`.

---

### 6. BUG 6: Xung đột phím điều khiển (`Space`) giữa Controller và các phân hệ

* **Vị trí trong mã nguồn:**
  * File: `bloxorz/gui/controller.py` — Dòng 29:
  ```python
  KEY_COMMANDS = {
      ...
      "space": "switch",
  }
  ```

* **Phân tích:**
  * Phím `Space` được VT4 gán cố định cho chức năng **đổi khối khi phân tách (switch cube)**.
  * Nếu các module khác (như Camera) gán phím `Space` để Reset góc nhìn thì sự kiện sẽ bị xung đột hoặc nuốt lệnh khi đang ở màn phân tách khối.

* **Kiến nghị giải pháp:**
  * **Thống nhất giữa VT3 & VT4**: Phím `Space` dành riêng $100\%$ cho VT4 (đổi khối); Camera chỉ dùng duy nhất phím **`C`** để căn góc chuẩn Isometric.

---

## 📋 BẢNG TỔNG HỢP KIẾN NGHỊ PHÂN CÔNG SỬA LỖI

| Mã Bug | Tên Bug | File bị ảnh hưởng | Phụ trách chính | Mức độ ưu tiên |
| :---: | :--- | :--- | :---: | :---: |
| **BUG 1** | Khối nằm đè qua ô `'G'` bị xử rơi | `bloxorz/engine/rules.py` | **VT2** | 🔴 Nghiêm trọng |
| **BUG 2** | `FRAGILE_TILES` chứa `'x'`, `'o'` | `bloxorz/engine/rules.py` | **VT2 & VT1** | 🔴 Nguy cơ cao |
| **BUG 3** | Cube con bước vào `'G'` bị chết | `bloxorz/engine/split.py`, `rules.py` | **VT2** | 🟡 Trung bình |
| **BUG 4** | Bỏ sót switch khi hợp nhất khối | `bloxorz/engine/split.py` | **VT2** | 🟡 Trung bình |
| **BUG 5** | Lệch `active_cube` khi di chuyển | `bloxorz/gui/controller.py` | **VT4** | 🟡 Trung bình |
| **BUG 6** | Xung đột phím `Space` | `controller.py`, `view.py` | **VT3 & VT4** | 🟢 Đã xử lý |
