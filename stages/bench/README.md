# Bộ màn thực nghiệm G1–G5 — Task 5.3

Bộ chính cố định gồm 17 màn, dùng cho so sánh BFS/DFS/UCS/A*. Mỗi JSON có id
trùng tên file, group đúng nhóm, dùng contract hiện tại của loader. Thứ tự mở
nhánh chuẩn U → D → L → R; xét đủ hướng của cube 0 rồi đến cube 1.

Nguồn yêu cầu: [Task 5.3](https://www.notion.so/20a9cc1ed39082218e9501634f6dbe74).

## Metadata

Mỗi JSON lưu `source` và `note`; loader hiện hỗ trợ cả hai trường metadata
dạng chuỗi. Bảng dưới tóm tắt nguồn và mục tiêu của từng màn.

`original-N`: sao chép dữ liệu local `stages/original/stage_NN.json`, chỉ đổi id
và group. Test kiểm tra nguyên vẹn grid, bridge, switch, actions và targets.
Đây là bảo toàn bản chuyển đổi hiện có, không phải đối chiếu độc lập với trò
chơi gốc. `team`: tự thiết kế hoặc lấy fixture sẵn có; nguồn cụ thể ghi ở note.

## Danh mục và mục tiêu

| File / id | Group | source | note |
| --- | --- | --- | --- |
| g1_01 | G1 | team | Hành lang 1×4; hai lần lăn để kiểm tra tư thế đứng tại goal. |
| g1_02 | G1 | original-1 | Bàn nhỏ có vực và góc rẽ; đường tối thiểu 7 bước. |
| g1_03 | G1 | original-3 | Đường cơ bản dài hơn, nhiều lần đổi hướng; 19 bước. |
| g1_04 | G1 | original-6 | Bàn cơ bản lớn hơn, định hướng khối qua hành lang; 35 bước. |
| g2_01 | G2 | team | Từ fixture fragile; khối nằm đi qua F được, đứng trên F bị rơi. |
| g2_02 | G2 | team | Hai lối: BFS 7 bước/cost 15, UCS tránh F 10 bước/cost 10. |
| g2_03 | G2 | original-4 | Màn thuần fragile dài; so sánh số bước và chi phí có phạt F. |
| g3_01 | G3 | team | Từ fixture bridge_soft; soft toggle kích hoạt khi khối nằm. |
| g3_02 | G3 | team | Từ fixture bridge_heavy; heavy permanent chỉ mở khi khối đứng. |
| g3_03 | G3 | original-5 | Nhiều soft switch, cả toggle và permanent; giữ riêng trạng thái cầu. |
| g3_04 | G3 | original-12 | Heavy toggle và hành trình dài; kiểm tra đóng/mở cầu khi quay lại. |
| g4_01 | G4 | team | Từ fixture split; bắt buộc tách và di chuyển cube để ghép lại. |
| g4_02 | G4 | original-8 | Di chuyển cube độc lập nhiều bước, sau đó ghép và tới goal. |
| g4_03 | G4 | original-9 | Hai cube cần đổi vị trí và ghép theo tư thế phù hợp; 24 bước. |
| g5_01 | G5 | original-10 | Tổng hợp split, soft/heavy và cầu; lời giải 57 bước. |
| g5_02 | G5 | original-15 | Tổng hợp split và nhiều công tắc toggle/permanent; 57 bước. |
| g5_03 | G5 | team | Soft mở cầu vào vùng hai lối; BFS 9 bước/cost 17, UCS 12 bước/cost 12. |

G1: 4 màn chỉ sàn/void/goal. G2: 3 màn fragile, không công tắc/cầu.
G3: 4 màn công tắc/cầu, không split/fragile; bao phủ soft, heavy, toggle,
permanent. G4: 3 màn có split thực sự trong lời giải. G5: 3 màn tổng hợp
ít nhất hai cơ chế. Nhóm phân theo cơ chế, không tuyên bố mọi màn G5 khó hơn
mọi màn G4 theo thời gian hoặc số bước.

## Hai màn hai lối

| Màn | BFS bước | BFS cost | UCS bước | UCS cost | Chênh lệch bước |
| --- | ---: | ---: | ---: | ---: | ---: |
| g2_02 | 7 | 15 | 10 | 10 | +3 |
| g5_03 | 9 | 17 | 12 | 12 | +3 |

Đường UCS của hai màn không có bước nào chịu phạt F (cost bằng số bước).
Mỗi đường BFS có hai bước chịu phạt +4. Cầu `entry` ở g5_03 ban đầu đóng;
soft switch tại (0,1) phải mở cầu trước khi qua (0,3), nên cơ chế cầu không
chỉ là phần trang trí. Hai màn dùng chung lõi hình học để cô lập ảnh hưởng của
việc thêm cơ chế cầu; không coi chúng là hai mẫu thống kê độc lập.

## Chạy nghiệm thu tự động

Từ thư mục gốc repo:

```powershell
py -m pytest tests/informed/test_bench_stages.py -q
py -m pytest -q
py -m tools.validate_bench
py -m tools.validate_astar stages/bench
```

Đối chiếu ngày 27/10/2026: cả 17 màn qua loader; lời giải BFS chính thức
(`run("bfs", ...)`) khớp từng action, số bước và cost BFS trong `solutions.csv`.
Tạo lại CSV bằng công cụ bên dưới cho kết quả không đổi; BFS tham chiếu,
UCS và hai A* đều replay tới goal. Hai A* cùng cost UCS; relaxed A* expanded
không lớn hơn UCS trên 17 màn này. Mỗi solver được giới hạn 60 giây mỗi màn.

Công cụ `tools/validate_bench.py` vẫn dùng `reference_bfs` độc lập, không
đăng ký hoặc thay thế solver BFS chính thức trong `bloxorz/search/bfs.py`.
Đối chiếu BFS chính thức ở trên là kiểm tra riêng; chưa có số liệu DFS trong
task này. Test nghiệm thu còn replay lời giải qua GameController của app.

Toàn repo: **407 tests passed** ngày 27/10/2026. Khi thư mục tạm mặc định
của pytest bị hạn chế quyền, dùng thư mục tạm trong workspace:

```powershell
New-Item -ItemType Directory -Path results/tmp -Force | Out-Null
py -m pytest -q -p no:cacheprovider --basetemp=results/tmp/pytest-bench-review
```

Tất cả lời giải và số đo tất định nằm trong [solutions.csv](solutions.csv).
Tạo lại bằng:

```powershell
py -m tools.validate_bench --output stages/bench/solutions.csv
```

CSV không ghi thời gian/RAM vì các giá trị đó phụ thuộc môi trường. Đây là
bảng xác minh lời giải, không thay cho runner benchmark chính thức của VT1.
Nếu thay engine, cost, solver hoặc JSON thì phải chạy lại bảng và test.

### Diễn giải thời gian và số node A*

`python -m tools.validate_astar stages/bench` xuất cả `expanded`, `time_s`,
`prep_time_s` và `search_time_s`. `time_s` là tổng thời gian chạy solver;
`prep_time_s` đo riêng việc tạo heuristic (gồm bảng Relaxed BFS); `search_time_s`
là thời gian còn lại, gồm khởi tạo tìm kiếm, vòng lặp heap và dựng đường đi.
Các số đo lấy từ lượt chạy thời gian, không gồm lượt đo RAM hay replay tính cost.
Với UCS không có bước tiền xử lý được đo riêng: `prep_time_s = 0`.

Trong bảng so sánh BFS/DFS/UCS/A*, ghi rõ: **Thời gian A* đã bao gồm chi phí
tính trước bảng Relaxed Heuristic một lần ở đầu mỗi lần chạy solver.** Dùng
`expanded` để đánh giá mức giảm không gian tìm kiếm trên cùng màn/cost;
ít node hơn không bảo đảm tổng thời gian nhỏ hơn. Chỉ báo cáo BFS/DFS khi có
solver tương ứng được nghiệm thu. A* phá hòa theo `(f, h, serial)`: ưu tiên
`h` nhỏ khi cùng `f`, rồi dùng thứ tự sinh; số node có thể khác bản FIFO cũ.

## Chơi tay — chưa nghiệm thu

Mở app hoặc chế độ chữ:

```powershell
py main.py --stages-dir stages/bench
py main.py --stages-dir stages/bench --text
py main.py --stage stages/bench/g2_02.json --text
```

Phím W/A/S/D tương ứng U/L/D/R; Space đổi cube khi tách; N/P chuyển màn;
R chơi lại; U undo. Trong chế độ chữ có thể nhập nhiều phím trên một dòng.

CSV dùng U/D/L/R cho hướng; hậu tố 0 hoặc 1 chỉ cube theo thứ tự vị trí
chuẩn hóa của State ở bước hiện tại. HUD của app hiển thị cube 1/2 tương ứng
chỉ số 0/1. Dùng Space để chọn cube phù hợp trước mỗi bước có hậu tố.
Không gõ trực tiếp chuỗi U/D/L/R vào chế độ chữ: chữ `u` là undo, `r` là restart.

Replay tự động qua engine/controller không thay thế yêu cầu người chơi tay
thắng mỗi màn. Người thử điền tên, ngày và phiên bản đã thử vào bảng dưới.

| Màn | Người chơi tay | Ngày / commit | Kết quả |
| --- | --- | --- | --- |
| g1_01 | — | — | Chờ thử |
| g1_02 | — | — | Chờ thử |
| g1_03 | — | — | Chờ thử |
| g1_04 | — | — | Chờ thử |
| g2_01 | — | — | Chờ thử |
| g2_02 | — | — | Chờ thử |
| g2_03 | — | — | Chờ thử |
| g3_01 | — | — | Chờ thử |
| g3_02 | — | — | Chờ thử |
| g3_03 | — | — | Chờ thử |
| g3_04 | — | — | Chờ thử |
| g4_01 | — | — | Chờ thử |
| g4_02 | — | — | Chờ thử |
| g4_03 | — | — | Chờ thử |
| g5_01 | — | — | Chờ thử |
| g5_02 | — | — | Chờ thử |
| g5_03 | — | — | Chờ thử |
