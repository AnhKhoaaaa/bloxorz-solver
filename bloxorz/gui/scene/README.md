# 🎮 Tóm Tắt Cập Nhật & Sổ Tay Kỹ Thuật Phân Hệ Cảnh 3D (VT3)

Tài liệu này tổng hợp toàn bộ các tính năng, sổ tay lỗi (Bug Log) cùng các giải pháp đã khắc phục của phân hệ **3D Scene & Animations** trong dự án Bloxorz Solver.

---

## 🌟 1. Những Nâng Cấp Nổi Bật

### 🧱 Đồ Họa Voxel & 3 Thế Giới (Biome)
* **Phong cách Voxel nổi khối**: Từng ô sàn, khối gỗ Bloxorz, công tắc và cổng đích đều được vẽ khối 3D sắc nét theo phong cách Minecraft.
* **Màu sắc & Ánh sáng chân thực**: Cân bằng ánh sáng dịu mắt, bóng đổ rõ nét, không còn hiện tượng chói sáng trắng.
* **3 Biome chuyển đổi tức thì**:
  * 🌿 **Overworld**: Bầu trời xanh trong, mây trắng bay lơ lửng, sàn gạch đá cổ kính.
  * 🔥 **Nether**: Không gian đỏ rực tro than, biển dung nham cuồn cuộn bên dưới.
  * 🌌 **The End**: Bầu trời tím huyền bí, các hạt bụi sao bay lượn quanh cổng không gian.

---

### 🎲 Chuyển Động Lăn Khối Bám Sàn & Độ Nảy Cơ Học
* **Khối lăn chuẩn xác $100\%$**: Lăn mượt qua các cạnh đáy, bám khít từng viên gạch, không bị lún sàn hay bay lơ lửng.
* **Độ nảy khi tiếp đất (`Squash & Stretch`)**: Khi khối lật xong và chạm đất, khối có độ co giãn nhẹ tạo cảm giác đầm tay và có trọng lực như khối gỗ thật.
* **Hỗ trợ đầy đủ khối phân tách**: Khi dẫm vào công tắc đặc biệt, khối sẽ tách thành 2 khối vuông nhỏ và di chuyển độc lập.

---

### 🎥 Hệ Thống Camera Cinematic (Tái Hiện 100% Thuật Toán Bản HTML)
Hệ thống Camera mới trong [`bloxorz/gui/scene/camera_controller.py`](file:///home/acheron/Acheron/0000_ITUS/05_26-27_01/0003_FoAI/Projects/bloxorz-solver/bloxorz/gui/scene/camera_controller.py) (`SmoothOrbitCamera`) tái hiện trọn vẹn 4 kỹ thuật toán học cao cấp từ bản Three.js:

1. **Phối cảnh giả đẳng cự (Perspective Pseudo-Isometric)**:
   * Sử dụng góc mở hẹp `camera.fov = 42` kết hợp góc nghiêng chuẩn mực:
     * $\theta \approx 31^\circ$ ($0.55\text{ rad}$)
     * $\phi \approx 52^\circ$ ($0.92\text{ rad}$)
   * Giúp bàn cờ trông vuông vức, ngay ngắn như game isometric cổ điển nhưng vẫn giữ trọn vẹn chiều sâu không gian 3D hiện đại.
2. **Tọa độ cầu có kẹp góc (Spherical Coordinate Orbit System)**:
   * Tính toán vị trí camera hoàn toàn theo tọa độ cầu $(r, \theta, \phi)$, chuyển sang Descartes:
     $$\begin{cases} X = X_{\text{look}} + r \cdot \sin(\phi) \cdot \sin(\theta) \\ Y = Y_{\text{look}} + r \cdot \cos(\phi) \\ Z = Z_{\text{look}} - r \cdot \sin(\phi) \cdot \cos(\theta) \end{cases}$$
   * Góc nâng $\phi$ được kẹp chặt chẽ trong khoảng $[0.35\text{ rad}, 1.38\text{ rad}]$ ($20^\circ \to 79^\circ$), triệt tiêu hoàn toàn hiện tượng gimbal lock, chui xuống gầm sàn hay nhìn đỉnh đầu.
3. **Bám mục tiêu trễ có quán tính (Dynamic Target Lerp / Spring Damping)**:
   * Khi khối gỗ lăn sang ô mới, điểm nhìn không giật cục mà trôi êm theo tâm khối gỗ bằng hàm LERP độc lập với FPS (tương đương hệ số $0.08$ ở 60 FPS):
     $$\text{currentLook} = \text{currentLook} + (\text{target} - \text{currentLook}) \times (1 - (1 - 0.08)^{\Delta t \cdot 60})$$
   * Tạo cảm giác ống kính máy quay có trọng lượng đầm như trong các tựa game AAA.
4. **Rung chấn Camera suy giảm hàm mũ (Decaying Camera Shake) khi rơi vực**:
   * Khi khối rơi, `shake_intensity` kích hoạt mức $0.35$.
   * Mỗi khung hình, độ rung tắt dần theo hàm mũ $\times 0.88^{\Delta t \cdot 60}$, tạo cảm giác chấn động thị giác cực mạnh khi người chơi mắc sai lầm.
5. **Bộ phím căn góc vàng một chạm**:
   * 🏆 **Phím `C` (Góc Vàng Isometric)**: Đưa góc nhìn về góc kinh điển đẹp nhất của Bloxorz.
   * 🗺️ **Phím `T` (Góc Chiến Thuật Top-Down)**: Nhìn thẳng từ trên cao xuống để soi toàn bộ mê cung.
   * 🔄 **Phím `Q` / `E` (Xoay 45° đối xứng)**: Tự động nhảy đúng 45° vào các góc máy đối xứng hoàn hảo.

---

### 🎵 Âm Thanh Tương Tác Sống Động
* 🔊 **Tiếng bước chân**: Âm thanh gõ gỗ/đá trầm đầm mỗi khi khối lật tiếp đất.
* 🌪️ **Tiếng gió rít**: Giảm cao độ khi khối mất thăng bằng và rơi xuống vực sâu.
* 🔘 **Tiếng click cơ học**: Khi khối dẫm lên bàn đạp công tắc.
* 🎆 **Hợp âm chiến thắng & Pháo hoa**: Nở rộ khi khối đứng thẳng vào Cổng End.

---

## 🛠️ 2. Bảng Tổng Hợp Lỗi Đã Gặp & Cách Khắc Phục (Bug Log)

| STT | Hiện tượng lỗi | Nguyên nhân gốc rễ | Phân định trách nhiệm | Giải pháp đã khắc phục |
| :---: | :--- | :--- | :---: | :--- |
| **1** | Màn hình trắng xóa, cháy sáng | Hàm `color.rgb(r, g, b)` của Ursina nhận số thực `0.0 - 1.0`. Code AI truyền số nguyên `255`, khiến độ sáng bị nhân lên **255 lần**. | **VT3** (Đồ họa) | Chuyển toàn bộ sang `color.rgb32()` và `color.rgba32()`; giảm `fog_density` xuống `0.002 - 0.004`. |
| **2** | Khối lăn bị lún sâu xuống sàn | Hệ trục Ursina (Left-handed) có quy ước góc quay Euler trục Z ngược lại. Lệnh quay `LEFT` bị gán nhầm góc dương `+90°`. | **VT3** (Hoạt ảnh) | Sửa lại vector quay: `LEFT: -90°`, `RIGHT: +90°`. Khối lật đúng mép trên sàn gạch. |
| **3** | Sửa code trong `Test/` nhưng không tác dụng | Code ban đầu import dạng `from bloxorz.gui.scene...`, khiến Python luôn nạp code từ repo chính thay vì đọc file tại chỗ. | **VT3** (Sandbox) | Chuyển sang import kép (hỗ trợ cả chạy cục bộ độc lập trong `Test/` và đóng gói package trong repo). |
| **4** | Lệch nhịp giữa Controller và Animation | Controller cập nhật trạng thái `State` tức thì ($0$s) trong khi hoạt ảnh cần $0.16$s để diễn hoạt, gây giật đè hành động. | **VT3 & VT4** (Tích hợp) | Dùng cờ `is_animating()` kết hợp bộ đệm `KeyBuffer`: chặn phím bấm dở dang, đảm bảo khối chạm sàn mới nhận lệnh tiếp. |
| **5** | Camera quá gần, xoay trên/dưới ngược chiều, khó tìm góc đẹp | Vận tốc chuột trục dọc `dy` bị cộng sai dấu; bán kính `span` bị hẹp; xoay tự do khiến người chơi khó căn góc đối xứng. | **VT3** (Camera) | Tái hiện 100% thuật toán `SmoothOrbitCamera` bản HTML: FOV 42, đảo dấu `dy`, tăng bán kính, thêm phím **`C`** (Góc vàng), **`T`** (Top-down) và **`Q/E`** (Xoay 45°). |
| **6** | Phím bấm bị lệch khi camera xoay 180° | `GameController` ánh xạ phím cố định theo trục thế giới bàn cờ (W luôn là đi Bắc, S là Nam). Khi xoay camera sang hướng đối diện, mắt nhìn thấy phím bị ngược. | **VT4** (Controller) | *Ghi chú cho VT4*: Thuộc phạm vi của `controller.py`. Phía VT3 đã cung cấp các góc máy chuẩn (`C`, `T`, `Q/E`) để người chơi luôn giữ được góc nhìn thuận mắt nhất. |

---

## 📌 3. Đánh Giá Kỹ Thuật & Kế Hoạch Thay Thế Ursina (Roadmap)

> [!NOTE]
> **Đánh giá thẩm mỹ & Giới hạn của Ursina Engine:**
> * **Đồ họa & Ánh sáng**: Ursina xây dựng trên nền Panda3D cũ, sử dụng pipeline render cơ bản, thiếu các công nghệ xử lý hậu kỳ (Post-processing) hiện đại như PBR (Physically Based Rendering), Bloom, Ambient Occlusion (SSAO), Tone Mapping và Khử răng cưa (Antialiasing). Do đó, màu sắc dễ bị bệt, thiếu độ sâu quang học và độ tương phản bắt mắt so với WebGL/Three.js.
> * **Camera & Cảm giác hình ảnh**: Góc chiếu và cơ chế culling của Ursina còn thô, việc thể hiện phối cảnh chưa đạt độ bóng bẩy, sang trọng như các công cụ đồ họa 3D thế hệ mới.
> * **Kế hoạch tiếp theo (Đang tìm hiểu thêm)**:
>   * Giữ Ursina như một bản mẫu (Baseline Prototype) để nghiệm thu yêu cầu môn học cho nhóm.
>   * Song song đó, đang nghiên cứu phương án **thay thế Ursina** bằng các nền tảng đồ họa mạnh mẽ hơn (ví dụ: nhúng WebGL/Three.js qua Electron/WebView, Panda3D PBR RenderPipeline, hoặc ModernGL / Raylib) để mang lại hiệu ứng thị giác đỉnh cao, màu sắc rực rỡ và chuyên nghiệp hơn hẳn.

---

## 🕹️ 4. Bảng Phím Tắt Điều Khiển

| Thao tác | Phím bấm | Chức năng |
| :--- | :--- | :--- |
| **Lăn khối** | `W / A / S / D` hoặc `Mũi Tên` | Lật khối Bloxorz theo 4 hướng |
| **Căn Góc Vàng** | Phím **`C`** | Đưa camera về góc nhìn Pseudo-Isometric $45^\circ$ chuẩn đẹp nhất |
| **Góc Trên Cao** | Phím **`T`** | Nhìn thẳng từ trên cao xuống (Top-down chiến thuật) |
| **Xoay 45° chuẩn** | Phím **`Q`** / **`E`** | Xoay 45° sang trái (**Q**) hoặc sang phải (**E**) |
| **Xoay Tự Do** | `Chuột trái / Chuột phải + Kéo` | Xoay góc nhìn 3D mượt mà thuận tay cả 2 trục |
| **Thu phóng Camera** | `Con lăn chuột` | Phóng to / Thu nhỏ góc nhìn ($10.0 \to 48.0$) |
| **Chuyển màn chơi** | Phím **`N`** / **`P`** | Sang màn kế tiếp (**N**) / Về màn trước (**P**) |
| **Đổi Thế Giới** | `1`, `2`, `3` | Đổi Biome: Overworld $\rightarrow$ Nether $\rightarrow$ The End |
| **Hoàn tác bước đi** | Phím **`U`** | Quay lại 1 bước di chuyển trước |
| **Chơi lại màn này** | Phím **`R`** | Đặt lại khối về vị trí xuất phát |

---

## 🚀 5. Lệnh Khởi Chạy Kiểm Thử

* **Chạy trong thư mục Sandbox độc lập (`Test/`)**:
  ```bash
  cd /home/acheron/Acheron/0000_ITUS/05_26-27_01/0003_FoAI/Projects/Test
  ./run.sh
  ```
* **Chạy trong repo chính của nhóm (`bloxorz-solver/`)**:
  ```bash
  cd /home/acheron/Acheron/0000_ITUS/05_26-27_01/0003_FoAI/Projects/bloxorz-solver
  .venv/bin/python bloxorz/gui/scene/demo.py
  ```
