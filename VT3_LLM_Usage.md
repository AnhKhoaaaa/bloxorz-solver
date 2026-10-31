# BÁO CÁO NGHIÊN CỨU & THAM VẤN KỸ THUẬT CÙNG LLM
## PHÂN HỆ VT3: CẢNH 3D, HOẠT ẢNH VOXEL & TRỰC QUAN HÓA THUẬT TOÁN

---

## 1. TỔNG QUAN PHÂN HỆ VÀ VAI TRÒ CỦA TÁC GIẢ
- **Sinh viên thực hiện:** Trương Huệ Trí (MSSV: 24120472) - Phân hệ VT3.
- **Phạm vi trách nhiệm theo `CODEOWNERS`:**
  - `bloxorz/gui/scene/` (Lõi hiển thị 3D WebGL Three.js, Camera Gimbal, Texture procedural, Âm thanh Web Audio).
  - `bloxorz/gui/web/bench.css`, `bloxorz/gui/web/bench.js` (Giao diện Benchmark Studio / Engineering Terminal).
  - `bloxorz/search/trace.py` (Search Trace Engine thu thập vết duyệt không gian trạng thái).
- **Nguyên tắc kỹ thuật xuyên suốt:** Clean Architecture (MVC tách rời), KISS (Keep It Simple, Stupid), YAGNI (You Aren't Gonna Need It), EGM (Evidence-Guided Modification) và Conventional Commits.
- **Vai trò của LLM trong dự án:**
  - Tác giả là người trực tiếp thiết kế kiến trúc, trực tiếp viết 100% mã nguồn, gỡ lỗi và kiểm nghiệm toàn bộ hệ thống.
  - Large Language Model (LLM) được tác giả khai thác thuần túy như một **Đối tác Tham vấn Kỹ thuật & Phản biện Kiến trúc (Technical Sounding Board & Brainstorming Partner)** nhằm:
    1. Tra cứu, so sánh đánh giá ưu nhược điểm (Trade-off Analysis) giữa các giải pháp công nghệ.
    2. Brainstorm phương án kiến trúc phân tầng (Decoupled Micro-Renderer & Non-intrusive Search Trace).
    3. Phân tích nguyên nhân gốc rễ (Root Cause Analysis) của các lỗi logic phức tạp (turn-stealing khi tách khối, audio lifecycle reset).
    4. Tham vấn tiêu chuẩn công thái học thị giác (Visual Ergonomics, WCAG Accessibility, Pixel Art Geometry).

---

## 2. NHẬT KÝ THAM VẤN KỸ THUẬT THEO CÁC GIAI ĐOẠN PHÁT TRIỂN

### Giai đoạn 1: Nghiên cứu Kiến trúc Đồ họa & Lựa chọn Engine (WebGL vs OpenGL/Ursina)
- **Bài toán Kỹ thuật:** Cần xây dựng giao diện 3D phong cách Minecraft Voxel cho Bloxorz, đảm bảo lõi thuật toán AI chạy headless độc lập và đồ họa không làm nặng môi trường cài đặt.
- **Nội dung Tham vấn & Brainstorm:**
  - Đánh giá trade-off giữa Native OpenGL (PyOpenGL/ModernGL/Ursina) và Micro-Renderer WebGL Three.js.
  - Phân tích rủi ro tương thích đa nền tảng (Linux Wayland, Windows, macOS) của các thư viện đồ họa C-binding.
- **Phân tích Đánh giá Kỹ thuật:**
  - Native OpenGL/Ursina đòi hỏi cài đặt driver và C-extension phức tạp, dễ xung đột môi trường ảo và khó đóng gói cross-platform.
  - WebGL Three.js chạy thông qua Webview/Browser có tính tương thích tuyệt đối, hỗ trợ Canvas/Texture procedural siêu nhẹ và Web Audio API nội sinh không cần file âm thanh ngoài.
- **Quyết định & Hiện thực hóa của Tác giả:**
  - Tác giả quyết định chọn giải pháp **Single Engine WebGL Three.js**, loại bỏ hoàn toàn Ursina và OpenGL dependencies.
  - Xây dựng giao thức truyền thông hai chiều `SceneProtocol` và cầu nối `RendererBridge` kết nối Python Controller với WebGL.

---

### Giai đoạn 2: Cơ chế Khối Tách Đôi (Split Block) & Hoạt ảnh Lăn 90 Độ
- **Bài toán Kỹ thuật:** Mô phỏng hoạt ảnh lật khối chính xác khi khối tách thành 2 khối $1 \times 1 \times 1$ độc lập (Split Block) và chuyển đổi điều khiển giữa 2 khối mà không bị đoạt lượt.
- **Nội dung Tham vấn & Brainstorm:**
  - Tính toán ma trận pivot quay quanh mép sàn cho từng khối lập phương con độc lập.
  - Phân tích nguyên nhân gốc rễ của hiện tượng race condition/turn-stealing khi người chơi gửi lệnh liên tiếp trong lúc hoạt ảnh đang diễn ra.
- **Phân tích Đánh giá Kỹ thuật:**
  - Cần tách biệt tọa độ logic ($r, c$) của 2 khối và tọa độ nội suy đồ họa ($x, y, z$). Cờ `isProcessing` phải khóa lượt nhận input của khối không kích hoạt cho tới khi pivot quay hoàn tất góc $\pi/2$.
- **Quyết định & Hiện thực hóa của Tác giả:**
  - Tác giả tự lập trình cơ chế pivot quay 90 độ cho từng viên khối riêng biệt.
  - Dựng vật liệu phân biệt: Iron Slab (sắt trắng) cho khối nặng, Golden Slab (vàng) cho khối nhẹ, sàn nứt Cracked Stone.
  - Thiết kế con trỏ Purple Diamond (kim cương tím xoay 3D lơ lửng) chỉ thị trực quan khối đang được chọn.

---

### Giai đoạn 3: Search Trace Engine & Công cụ Đo đạc Thuật toán (Task 3.9)
- **Bài toán Kỹ thuật:** Cần thu thập chi tiết tiến trình mở rộng của 4 thuật toán tìm kiếm (BFS, DFS, UCS, A*) để trực quan hóa mà không được sửa đổi logic tìm kiếm sẵn có của các thành viên khác.
- **Nội dung Tham vấn & Brainstorm:**
  - Nghiên cứu design pattern phù hợp để hook vào vòng lặp tìm kiếm theo hướng Non-intrusive / Zero-overhead.
- **Phân tích Đánh giá Kỹ thuật:**
  - Sử dụng mô hình `SearchContext` mở rộng với hook thụ động `observe(...)`. Khi chạy benchmark thông thường, hook là hàm `pass` (chi phí gọi hàm xấp xỉ 0). Khi đo trace, `TraceContext` thu thập snapshot của frontier, closed set, $g(n), h(n), f(n)$.
- **Quyết định & Hiện thực hóa của Tác giả:**
  - Tác giả triển khai module `bloxorz/search/trace.py`, tích hợp an toàn với toàn bộ 4 thuật toán tìm kiếm mà không làm gãy bất kỳ unit test nào của nhóm.

---

### Giai đoạn 4: Thiết kế Benchmark Studio & Công thái học Thị giác (Ergonomics)
- **Bài toán Kỹ thuật:** Giao diện so sánh thuật toán ban đầu bị chật chội, bản đồ lệch tâm khi stage có kích thước không vuông, và biểu đồ đường cong không thể hiện rõ bản chất thuật toán.
- **Nội dung Tham vấn & Brainstorm:**
  - Đánh giá cách thể hiện trực quan dung lượng hàng đợi/ngăn xếp frontier: Biểu đồ đường cong trừu tượng vs Dải sóng âm Telemetry (Audio Waveform style).
  - Phương pháp tính toán Bounding Box tự động để căn giữa bàn chơi có hình dạng bất đối xứng.
- **Phân tích Đánh giá Kỹ thuật:**
  - Dải sóng âm Telemetry phản ánh trực tiếp và tức thời độ phình của tập biên (frontier), mang phong cách Engineering Terminal trực quan hơn nhiều so với biểu đồ đường cong.
  - Bounding Box cần quét tọa độ cực trị `minR, maxR, minC, maxC` của các ô chơi thật (bỏ qua ký tự trống `.`) để tính hệ số phóng đại tối ưu.
- **Quyết định & Hiện thực hóa của Tác giả:**
  - Tác giả tái cấu trúc Benchmark Studio thành bố cục 3 hàng công thái học.
  - Hiện thực hóa dải sóng Telemetry dạng cột sóng neon cao 64px và thuật toán Auto Bounding Box căn giữa tự động cho toàn bộ 33 màn chơi.
  - Xây dựng Leaderboard Modal tổng kết xếp hạng đa thuật toán theo 4 tiêu chí: số nút mở rộng $\rightarrow$ thời gian $\rightarrow$ chi phí $\rightarrow$ đỉnh frontier.

---

### Giai đoạn 5: Tinh giản Mã nguồn theo Tiêu chuẩn KISS & YAGNI
- **Bài toán Kỹ thuật:** Sau khi hoàn thành các tính năng phức tạp, codebase tích lũy mã thử nghiệm cũ (tàn dư OpenGL) và các đoạn CSS/JS lặp lại.
- **Nội dung Tham vấn & Brainstorm:**
  - Rà soát toàn bộ cây thư mục phân hệ để xác định các đoạn mã không còn đường dẫn thực thi (dead code) và các tầng trừu tượng sớm (premature abstraction).
- **Phân tích Đánh giá Kỹ thuật:**
  - Áp dụng triệt để nguyên lý YAGNI: Xóa bỏ dứt khoát 3 file di sản OpenGL không còn import (`demo.py`, `camera_controller.py`, `demo_ursina.py`). Làm phẳng cấu trúc CSS/JS của Benchmark Studio.
- **Quyết định & Hiện thực hóa của Tác giả:**
  - Tác giả tiến hành dọn dẹp và tối ưu hóa: Cắt giảm tổng cộng **-1.038 dòng mã dư thừa**, giảm 65% dung lượng `bench.css`, trong khi bảo toàn 100% tính năng và giao diện hiển thị.

---

### Giai đoạn 6: Tái cấu trúc HUD Bàn Chơi 4 Góc Độc lập & Phong cách Minecraft Pixel
- **Bài toán Kỹ thuật:** Bảng phím chức năng ở giữa màn hình che khuất góc nhìn 3D của bàn chơi khi ở góc camera thấp hoặc khi cửa sổ thu nhỏ.
- **Nội dung Tham vấn & Brainstorm:**
  - So sánh các mô hình phân bổ bố cục HUD trong game: Bố cục dải ngang truyền thống vs Bố cục 4 góc độc lập (Top-Left, Top-Right, Bottom-Left, Bottom-Right).
  - Nghiên cứu tỷ lệ tương phản WCAG và kích thước phím bấm tối thiểu để tránh mỏi mắt người chơi.
- **Phân tích Đánh giá Kỹ thuật:**
  - Bố cục 4 góc giải phóng 100% không gian trung tâm cho bàn chơi 3D, giữ cho góc nhìn luôn thông thoáng.
  - Hai panel phía trên cần có cùng độ rộng (340px) và chiều cao cân bằng tuyệt đối để tạo tính ổn định hình học.
- **Quyết định & Hiện thực hóa của Tác giả:**
  - Tác giả hiện thực hóa bố cục 4 góc độc lập với viền pixel Minecraft cổ điển (pixel border 3px, inset shadow `#aaaaaa` / `#444444`, font chữ pixel).
  - Tích hợp nút Thoát game chuẩn Minecraft vào Start/Pause Menu, hỗ trợ đóng cửa sổ mượt mà trên cả desktop native và web browser.

---

### Giai đoạn 7: Hệ thống 3 Biome BGM, Font Minecraft Tiếng Việt & Màn Ending Credits
- **Bài toán Kỹ thuật:**
  - Cần đa dạng hóa nhạc nền theo 3 Biome (Overworld, Nether, The End) và tạo màn hình kết thúc vinh danh nhóm sau khi vượt qua Stage 33.
  - Khắc phục lỗi âm thanh phát lặp 2 lần, lỗi nhạc nền bị restart từ đầu khi nhấn AI Solve / Restart, và lỗi hiển thị font tiếng Việt có dấu.
- **Nội dung Tham vấn & Brainstorm:**
  - **Single Audio Authority:** Phân tích nguyên nhân xung đột âm thanh giữa Web Audio API và Python Native Audio (`ProceduralAudioEngine`).
  - **Decoupled BGM Lifecycle:** Tìm nguyên nhân khiến HTML5 Audio tự động giải phóng buffer và reset tiến trình phát về 0:00 khi chuyển trạng thái game.
  - **Vietnamese Pixel Typography:** Lựa chọn giải pháp font pixel hỗ trợ chuẩn unicode tiếng Việt có dấu thay thế cho `Press Start 2P`.
- **Phân tích Đánh giá Kỹ thuật:**
  - *Về âm thanh:* Python Native Audio phải là nguồn phát duy nhất khi chạy native desktop. Ba. Three.js chỉ gửi tín hiệu `notifySfx` khi đang ở chế độ AI tự chạy (`isAutoPlaying === true`). Khi chơi tay, Python tự phát tức thì theo key event, loại bỏ hoàn toàn hiện tượng phát kép.
  - *Về BGM:* Gán lại thuộc tính `audio.src` (dù trùng URL) sẽ buộc trình duyệt reload lại file nhạc. Cần bổ sung guard kiểm tra: nếu track yêu cầu trùng với biome hiện tại thì giữ nguyên luồng phát để nhạc chạy liên tục, độc lập với các thao tác Undo/Restart/Solve.
  - *Về Typography:* Tích hợp font `minecraft-f2d-v1-42.otf` qua `@font-face` giúp giải quyết triệt để lỗi gãy font tiếng Việt, mang lại trải nghiệm thị giác pixel chuẩn Minecraft 100%.
- **Quyết định & Hiện thực hóa của Tác giả:**
  - Tác giả xây dựng đối tượng `BloxorzAudio` quản lý tập trung 3 biome track + credits music, cơ chế infinite loop và continuous playback.
  - Nhúng font `minecraft-f2d-v1-42.otf` vào hệ thống giao diện HUD, Menu và Credits.
  - Tích hợp banner Achievement popup `Achievement Made! The End?` xuất hiện mượt mà ở góc trên-phải khi chiến thắng Stage 33.
  - Xây dựng màn hình Ending Credits cuộn chữ phong cách Minecraft End Poem, vinh danh đầy đủ 5 thành viên nhóm kèm chức năng phụ trách ngắn gọn, trang trọng.
  - Nghiệm thu tự động: Đạt **550/550 passed tests** (100% test suite xanh).

---

## 3. TỔNG KẾT BÀI HỌC VÀ KINH NGHIỆM CỘNG TÁC KỸ THUẬT VỚI LLM

1. **Làm chủ tư duy kiến trúc và giữ vai trò quyết định:**
   - LLM là công cụ hỗ trợ tra cứu và phản biện đắc lực, nhưng người kỹ sư phải luôn nắm vững kiến trúc tổng thể, tự tay phân tích bằng chứng và kiểm soát từng dòng mã nguồn đi vào repository.
2. **Nguyên tắc "Hành động dựa trên Bằng chứng" (Evidence-Guided Modification):**
   - Không sửa đổi mã nguồn dựa trên phán đoán mơ hồ. Luôn tái hiện lỗi, thu thập log/trace cụ thể, xác định đúng nguyên nhân gốc rễ (Root Cause) trước khi tiến hành can thiệp.
3. **Nghiệm thu trực quan đa tầng (Visual Verification & Automated Testing):**
   - Đối với các phân hệ đồ họa 3D và giao diện người dùng, unit test xanh chỉ là điều kiện cần. Việc kết hợp chụp snapshot màn hình thực tế trên WebKit render engine giúp đảm bảo tính thẩm mỹ, tỷ lệ pixel và công thái học ở mức cao nhất.
4. **Vận dụng đúng lúc nguyên lý YAGNI và KISS:**
   - Liên tục rà soát và loại bỏ các thành phần phức tạp hóa sớm hoặc mã di sản không sử dụng, giúp dự án duy trì dung lượng gọn nhẹ, tốc độ thực thi cao và dễ dàng mở rộng trong tương lai.
