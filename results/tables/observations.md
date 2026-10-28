# Nhận xét nháp — LOCAL SAMPLE - 2026-10-28 (not Task 1.7)

Nhận xét chỉ áp dụng cho CSV và môi trường trong manifest.json; nếu đang dùng dữ liệu mẫu, cần thay bằng CSV chính thức 1.7 trước khi chốt báo cáo.

1. CSV có 17 màn, 5 thuật toán; 85/85 dòng giải thành công đã xác minh; 0 dòng thất bại/chưa xác minh được giữ riêng.

2. UCS có trung vị expanded lớn nhất trên tập thành công của từng thuật toán (78 nút); tập màn có thể khác nhau.

3. Trên 17 màn chung đã xác minh có expanded tham chiếu > 0, trung vị giảm expanded của A* relaxed so với UCS là 14.6% (tính tỷ lệ từng màn rồi lấy trung vị; giá trị âm nghĩa là tăng).

4. Trên 17 màn chung đã xác minh có expanded tham chiếu > 0, trung vị giảm expanded của A* relaxed so với A* Manhattan là 0.2% (tính tỷ lệ từng màn rồi lấy trung vị; giá trị âm nghĩa là tăng).

5. DFS dài hơn BFS trên 12/17 màn chung; DFS ưu tiên đi sâu và không tối ưu độ dài lời giải.

6. Thời gian A* bao gồm tạo heuristic ở đầu mỗi lần chạy; ít expanded hơn chưa bảo đảm tổng thời gian nhỏ hơn. RAM đo riêng bằng tracemalloc, không phải toàn bộ RAM của tiến trình.

7. Các thống kê thời gian dùng trung vị từng dòng từ runner; số mẫu thực tế nằm ở cột samples. Thời gian 0 ms có thể do runner làm tròn 0.1 ms và được đánh dấu riêng trên trục log.

8. Expanded được giữ nguyên như solver báo: BFS kiểm tra goal khi sinh successor, còn DFS/UCS/A* kiểm tra khi pop; vì vậy cần lưu ý khác biệt cách đếm nút đích khi diễn giải chênh lệch nhỏ.
