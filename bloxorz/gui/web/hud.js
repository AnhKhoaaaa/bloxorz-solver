/* Phụ trách: VT4 - Task 4.2 / 4.3 / 4.4 / 4.5
 * Giao diện 2D và phím chơi tay cho cảnh WebGL của VT3 (scene/index.html), tách nguyên văn từ index.html:
 * - BloxorzMenu: màn hình mở đầu (logo, Chơi / Chọn màn / Cài đặt / Hướng dẫn) phủ trên cảnh 3D đang xoay chậm,
 *   chọn màn (đánh dấu màn đã qua + số bước tốt nhất), cài đặt âm lượng / tắt tiếng / biome mặc định / bảng phím
 *   tắt, lưu trong localStorage của trình duyệt; Esc mở lại menu (tạm dừng). Danh sách màn và nhảy màn đi qua
 *   sự kiện "stage_list" / "select_stage" của app.WebEventRouter (POST /api/event).
 * - BloxorzHud: dựng lớp giao diện (bảng tiêu đề + số màn/số bước, thanh nút, bảng phím tắt, banner qua màn)
 *   và các hàm cập nhật mà cảnh 3D gọi tới (số bước, nút biome đang chọn, huy hiệu kết quả AI, banner).
 * - BloxorzInput: phím chơi tay (lăn khối, Space đổi khối khi tách, lùi, chơi lại, đổi màn, G giải AI)
 *   gửi qua SceneBridge của VT3; đổi khối đi qua sự kiện "action" với giá trị "SWITCH".
 *   Phím camera và biome vẫn do cảnh 3D (VT3) xử lý.
 * Nút trên giao diện gọi API của SceneBridge (requestUndo, requestAISolve, setBiome, ...).
 */
(function () {
    "use strict";

    const HUD_MARKUP = `
<div class="ui-layer">
    <div class="top-bar">
        <!-- Corner 1: Top-Left (Stage Info) -->
        <div class="top-bar-left">
            <div class="mc-panel title-box">
                <h1>BLOXORZ: VOXEL EDITION</h1>
                <div class="stage-title" id="ui-stage-name">STAGE 1: KHỞI ĐẦU CỔNG END</div>
                <div class="stats-row">
                    <div>STAGE: <span id="ui-stage" style="color:#55ffff">1/6</span></div>
                    <div>MOVES: <span id="ui-moves" style="color:#ffaa00">0</span></div>
                    <div id="ui-cube"></div>
                    <div id="ui-ai-badge">AI A*: 0 moves</div>
                </div>
            </div>
        </div>

        <!-- Corner 2: Top-Right (Gameplay Actions) -->
        <div class="top-bar-right">
            <div class="mc-panel gameplay-bar">
                <div class="gameplay-row">
                    <button class="mc-btn" onclick="SceneBridge.requestUndo()">Undo (U)</button>
                    <button class="mc-btn" onclick="SceneBridge.requestRestart()">Restart (R)</button>
                </div>
                <div class="gameplay-row">
                    <button class="mc-btn" onclick="SceneBridge.requestPrevStage()">&lt; Prev (P)</button>
                    <button class="mc-btn" onclick="SceneBridge.requestNextStage()">Next (N) &gt;</button>
                    <button class="mc-btn" onclick="BloxorzMenu.open('pause')">Menu (Esc)</button>
                </div>
            </div>
        </div>
    </div>

    <div class="bottom-bar">
        <!-- Corner 3: Bottom-Left (Help Shortcuts) -->
        <div class="mc-panel help-panel">
            <div><span class="key-badge">W</span><span class="key-badge">A</span><span class="key-badge">S</span><span class="key-badge">D</span> / <span class="key-badge">ARROWS</span> : LẬT KHỐI GỖ SỒI &nbsp; <span class="key-badge">SPACE</span> : ĐỔI KHỐI KHI TÁCH</div>
            <div><span class="key-badge">U</span> : HOÀN TÁC &nbsp; <span class="key-badge">R</span> : CHƠI LẠI &nbsp; <span class="key-badge">P</span>/<span class="key-badge">N</span> : ĐỔI MÀN &nbsp; <span class="key-badge">G</span> : AI SOLVE (A*)</div>
            <div><span class="key-badge">CHUỘT TRÁI + KÉO</span> : GIMBAL ORBIT &nbsp; <span class="key-badge">CON LĂN</span> : ZOOM &nbsp; <span class="key-badge">1</span><span class="key-badge">2</span><span class="key-badge">3</span> : BIOME</div>
        </div>

        <!-- Corner 4: Bottom-Right (AI Solvers & Biomes) -->
        <div class="mc-panel ai-bar">
            <div class="ai-bar-title">AI SOLVERS &amp; BIOMES</div>
            <div class="mc-btn-grid-ai" id="ai-solvers-group">
                <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('astar')" title="Giải tự động bằng thuật toán A*">AI Solve (A*)</button>
                <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('bfs')" title="Giải tự động bằng thuật toán BFS">AI Solve (BFS)</button>
                <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('dfs')" title="Giải tự động bằng thuật toán DFS">AI Solve (DFS)</button>
                <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('ucs')" title="Giải tự động bằng thuật toán UCS">AI Solve (UCS)</button>
            </div>
            <div class="mc-btn-row-biomes" id="ai-biomes-group" style="margin-top: 5px;">
                <button class="mc-btn active" id="btn-overworld" onclick="SceneBridge.setBiome('overworld')">Overworld</button>
                <button class="mc-btn biome-nether" id="btn-nether" onclick="SceneBridge.setBiome('nether')">Nether</button>
                <button class="mc-btn biome-end" id="btn-end" onclick="SceneBridge.setBiome('end')">The End</button>
            </div>
            <button class="mc-btn ai-btn mc-btn-bench-full" id="btn-bench-studio" onclick="window.BloxorzBench &amp;&amp; BloxorzBench.open()" title="Mở Visualizer Thuật Toán (Engineering Terminal)">Benchmark Studio</button>
        </div>
    </div>
</div>

<div id="banner-msg">
    STAGE CLEAR!
    <span class="sub">ĐANG DỊCH CHUYỂN QUA CỔNG END...</span>
</div>

<div id="mc-menu" class="mc-menu show" data-screen="title">
    <section class="mc-screen" data-screen="title">
        <div class="mc-logo">
            <div class="mc-logo-main" data-text="BLOXORZ">BLOXORZ</div>
            <div class="mc-logo-sub">VOXEL EDITION</div>
            <div class="mc-splash" id="mc-splash">Tách đôi khối!</div>
        </div>
        <div class="mc-menu-buttons">
            <button class="mc-btn mc-btn-wide mc-btn-play" id="menu-play">Bắt đầu</button>
            <button class="mc-btn mc-btn-wide" data-go="levels">Chọn màn</button>
            <button class="mc-btn mc-btn-wide" data-go="help">Hướng dẫn</button>
            <div class="mc-btn-row">
                <button class="mc-btn" data-go="settings">Cài đặt</button>
                <button class="mc-btn" id="menu-quit">Thoát game</button>
            </div>
        </div>
        <div class="mc-footer">
            <span>CSAI · HCMUS</span>
            <span id="menu-progress-note">0/0 MÀN ĐÃ QUA</span>
            <span>BFS · DFS · UCS · A*</span>
        </div>
    </section>

    <section class="mc-screen" data-screen="levels">
        <h2 class="mc-screen-title">Chọn màn</h2>
        <div class="mc-panel mc-dialog mc-levels">
            <div class="mc-dialog-head">
                <span id="level-summary">ĐÃ QUA 0/0</span>
                <span class="mc-legend"><i class="lv-dot done"></i>ĐÃ QUA <i class="lv-dot current"></i>ĐANG CHƠI</span>
            </div>
            <div class="mc-scroll" id="level-groups"><div class="mc-empty">Đang tải danh sách màn...</div></div>
        </div>
        <button class="mc-btn mc-btn-wide" data-go="back">Xong</button>
    </section>

    <section class="mc-screen" data-screen="settings">
        <h2 class="mc-screen-title">Cài đặt</h2>
        <div class="mc-panel mc-dialog mc-settings">
            <label class="mc-slider">
                <input type="range" id="set-volume" min="0" max="100" step="5" value="80">
                <span class="mc-slider-label" id="set-volume-label">ÂM LƯỢNG: 80%</span>
            </label>
            <button class="mc-btn mc-btn-wide" id="set-mute">Âm thanh: Bật</button>
            <button class="mc-btn mc-btn-wide" id="set-bgm">Nhạc nền: Tắt</button>
            <div class="mc-setting-label">KHUNG CẢNH MẶC ĐỊNH</div>
            <div class="mc-btn-row mc-btn-row-3">
                <button class="mc-btn" data-biome="overworld">Overworld</button>
                <button class="mc-btn biome-nether" data-biome="nether">Nether</button>
                <button class="mc-btn biome-end" data-biome="end">The End</button>
            </div>
            <button class="mc-btn mc-btn-wide" id="set-help">Bảng phím tắt: Hiện</button>
            <button class="mc-btn mc-btn-wide mc-btn-danger" id="set-reset">Xoá tiến trình</button>
        </div>
        <button class="mc-btn mc-btn-wide" data-go="back">Xong</button>
    </section>

    <section class="mc-screen" data-screen="help">
        <h2 class="mc-screen-title">Hướng dẫn</h2>
        <div class="mc-panel mc-dialog mc-scroll mc-help">
            <p class="mc-goal">Lăn khối gỗ 1x1x2 tới <b>Cổng End</b> và <b>đứng thẳng</b> trên đó để qua màn. Rơi khỏi bàn là phải chơi lại.</p>
            <div class="mc-help-grid">
                <div><span class="key-badge">W A S D</span> / <span class="key-badge">ARROWS</span></div><div>Lăn khối</div>
                <div><span class="key-badge">SPACE</span></div><div>Đổi khối khi đã tách (kim cương tím chỉ khối đang chọn)</div>
                <div><span class="key-badge">U</span> <span class="key-badge">R</span></div><div>Hoàn tác 1 bước / Chơi lại màn</div>
                <div><span class="key-badge">P</span> <span class="key-badge">N</span></div><div>Màn trước / Màn sau</div>
                <div><span class="key-badge">G</span></div><div>AI giải bằng A* (nút trên màn hình: A*, BFS, DFS, UCS)</div>
                <div><span class="key-badge">M</span></div><div>Bật/tắt nhạc nền (BGM)</div>
                <div><span class="key-badge">1</span> <span class="key-badge">2</span> <span class="key-badge">3</span></div><div>Overworld / Nether / The End</div>
                <div><span class="key-badge">C T Q E</span> <span class="key-badge">CHUỘT</span></div><div>Góc camera, kéo để xoay, con lăn để zoom</div>
                <div><span class="key-badge">ESC</span></div><div>Mở menu</div>
            </div>
            <div class="mc-setting-label">CÁC LOẠI Ô</div>
            <div class="mc-help-grid">
                <div><i class="tile t-plate"></i>Bàn đạp gỗ</div><div>Bật/tắt cầu khi chạm bất kỳ</div>
                <div><i class="tile t-iron"></i>Phiến sắt</div><div>Chỉ kích hoạt khi khối đứng thẳng đè lên</div>
                <div><i class="tile t-gold"></i>Phiến vàng</div><div>Tách khối thành 2 khối 1x1</div>
                <div><i class="tile t-sand"></i>Cát cam</div><div>Vỡ nếu khối đứng thẳng lên trên</div>
                <div><i class="tile t-trap"></i>Cửa sập gỗ</div><div>Cầu: chỉ đi được khi đang mở</div>
            </div>
        </div>
        <button class="mc-btn mc-btn-wide" data-go="back">Xong</button>
    </section>
</div>

<div class="mc-toast" id="mc-end-toast" title="Achievement Made! The End?"></div>

<div class="mc-credits-overlay" id="mc-credits">
    <button class="mc-btn mc-credits-skip" onclick="BloxorzHud.hideEndCredits()">Bỏ qua (ESC)</button>
    <div class="mc-credits-scroll">
        <div class="mc-credits-logo">BLOXORZ: VOXEL EDITION</div>
        <div class="mc-credits-sub">CHÚC MỪNG BẠN ĐÃ VƯỢT QUA TOÀN BỘ 33 MÀN CHƠI!</div>
        <div class="mc-credits-poem">
            <p>Và vũ trụ thì thầm rằng bạn đã làm rất tốt.</p>
            <p>Và vũ trụ thì thầm rằng mọi thứ bạn cần đều ở trong bạn.</p>
            <p>Bạn là người chơi, lật từng khối gỗ qua miền hư vô.</p>
            <p>Từ đồng cỏ Overworld thanh bình...</p>
            <p>Vượt qua biển dung nham rực lửa của cõi Nether...</p>
            <p>Cho đến đĩa đá huyền bí của The End.</p>
            <br>
            <p>Bạn đã đồng hành cùng các thuật toán tìm kiếm:</p>
            <p class="mc-credits-accent">BFS · DFS · UCS · A* HEURISTIC</p>
            <br>
            <p>Tất cả thử thách đã được giải mã trọn vẹn.</p>
            <p>Và giấc mơ kết thúc, người chơi thức giấc.</p>
            <br>
            <p class="mc-credits-gold">THE END...?</p>
            <br>
            <p class="mc-credits-gold">NHÓM SINH VIÊN THỰC HIỆN</p>
            <div class="mc-credits-team">
                <p><span class="mc-credits-accent">24120072 · Lê Công Anh Khoa</span><br>Trưởng nhóm · Kiến trúc Core &amp; Thuật toán BFS/DFS</p>
                <p><span class="mc-credits-accent">24120318 · Trịnh Văn Hợp</span><br>Mô phỏng Môi trường &amp; Luật chơi (Engine Game)</p>
                <p><span class="mc-credits-accent">24120472 · Trương Huệ Trí</span><br>Cảnh 3D WebGL, Hoạt ảnh Voxel &amp; Trực quan hóa Thuật toán</p>
                <p><span class="mc-credits-accent">24120334 · Hoàng Khang</span><br>Điều phối Ứng dụng, Giao diện Người dùng &amp; Màn chơi</p>
                <p><span class="mc-credits-accent">24120372 · Nguyễn Hữu Hoàng Long</span><br>Thuật toán UCS, A* Heuristic &amp; Thực nghiệm Benchmark</p>
            </div>
            <br>
            <p>ĐỒ ÁN CƠ SỞ TRÍ TUỆ NHÂN TẠO</p>
            <p>TRƯỜNG ĐẠI HỌC KHOA HỌC TỰ NHIÊN - ĐHQG-HCM</p>
            <br>
            <p>Cảm ơn bạn đã trải nghiệm trò chơi!</p>
        </div>
    </div>
</div>
`;

    const BloxorzHud = {
        /** Chèn lớp giao diện vào trang (gọi 1 lần, ngay khi tải file này ở cuối <body>). */
        mount() {
            if (document.querySelector(".ui-layer")) return;
            document.body.insertAdjacentHTML("beforeend", HUD_MARKUP);
        },

        updateStats(stageName, stageIdx, totalStages, moves) {
            this.stageIdx = stageIdx;
            this.totalStages = totalStages;
            BloxorzMenu.onStage(stageIdx - 1);
            if (stageName) document.getElementById("ui-stage-name").innerText = stageName;
            document.getElementById("ui-stage").innerText = `${stageIdx}/${totalStages}`;
            document.getElementById("ui-moves").innerText = moves;
        },

        setMoves(moves) {
            document.getElementById("ui-moves").innerText = moves;
        },

        /** Tô sáng nút của biome đang chọn. */
        markBiome(biomeName) {
            BloxorzMenu.onBiome(biomeName);
            document.getElementById("btn-overworld").classList.toggle("active", biomeName === "overworld");
            document.getElementById("btn-nether").classList.toggle("active", biomeName === "nether");
            document.getElementById("btn-end").classList.toggle("active", biomeName === "end");
            if (typeof BloxorzAudio !== "undefined") {
                BloxorzAudio.setBiomeTrack(biomeName);
            }
        },

        /** Khối đang điều khiển khi khối tách (0 / 1); null: khối chưa tách, ẩn nhãn. */
        setSelected(cube) {
            const label = document.getElementById("ui-cube");
            const show = cube === 0 || cube === 1;
            label.style.display = show ? "inline-block" : "none";
            label.innerText = show ? `KHỐI ${cube + 1}/2 · SPACE ĐỔI KHỐI` : "";
        },

        /** Huy hiệu kết quả AI: số bước, cost, thời gian, số nút mở rộng; hoặc lý do không giải được. */
        showSolver(solver) {
            if (!solver) return;
            this.aiPlaying = solver.status === "solved";  // thắng nhờ AI thì không tính vào tiến trình
            const badge = document.getElementById("ui-ai-badge");
            badge.style.display = "inline-block";
            badge.innerText = solver.status === "solved"
                ? `${solver.algorithm}: ${solver.moves} MOVES | COST ${solver.cost} | ${solver.execution_time_ms}ms | ${solver.nodes_expanded} NODES`
                : `${solver.algorithm}: ${String(solver.status_text).toUpperCase()} | ${solver.nodes_expanded} NODES`;
        },

        hideSolver() {
            this.aiPlaying = false;
            document.getElementById("ui-ai-badge").style.display = "none";
        },

        showBanner() {
            document.getElementById("banner-msg").classList.add("show");
        },

        hideBanner() {
            document.getElementById("banner-msg").classList.remove("show");
        },

        /** Hoạt ảnh thắng của cảnh đã xong: tự sang màn sau hoặc mở màn kết thúc nếu là màn 33. */
        afterWin(client) {
            if (!this.aiPlaying) BloxorzMenu.recordWin(Number(document.getElementById("ui-moves").innerText));
            if (this.stageIdx && this.totalStages && this.stageIdx >= this.totalStages) {
                this.showEndCredits();
                return;
            }
            client.requestNextStage();
        },

        showEndCredits() {
            const toast = document.getElementById("mc-end-toast");
            if (toast) {
                toast.classList.add("show");
                setTimeout(() => toast.classList.remove("show"), 6000);
            }
            const credits = document.getElementById("mc-credits");
            if (credits) {
                credits.classList.add("show");
                if (typeof BloxorzAudio !== "undefined") {
                    BloxorzAudio.playCreditsMusic();
                }
            }
        },

        hideEndCredits() {
            const credits = document.getElementById("mc-credits");
            if (credits) credits.classList.remove("show");
            if (typeof BloxorzAudio !== "undefined") {
                BloxorzAudio.setBiomeTrack(BloxorzMenu.settings.biome || "overworld");
            }
            BloxorzMenu.open("title");
        },
    };

    // phím -> hàm của SceneBridge; bỏ qua khi cảnh đang diễn hoạt, đang chờ solver hoặc đang phát lời giải
    const GAMEPLAY_KEYS = {
        arrowleft: (c) => c.requestAction("LEFT"), a: (c) => c.requestAction("LEFT"),
        arrowright: (c) => c.requestAction("RIGHT"), d: (c) => c.requestAction("RIGHT"),
        arrowup: (c) => c.requestAction("UP"), w: (c) => c.requestAction("UP"),
        arrowdown: (c) => c.requestAction("DOWN"), s: (c) => c.requestAction("DOWN"),
        u: (c) => c.requestUndo(),
        r: (c) => c.requestRestart(),
        n: (c) => c.requestNextStage(),
        p: (c) => c.requestPrevStage(),
        " ": (c) => c.requestAction("SWITCH"),  // đổi khối đang điều khiển khi khối đã tách (như chơi trong terminal)
        g: (c) => c.requestAISolve("astar"),
        m: () => BloxorzAudio.toggleBGM(),
    };

    const BloxorzAudio = {
        bgm: null,
        bgmEnabled: true,
        volume: 0.35,
        currentBiome: "overworld",

        _getTrackUrl(name) {
            let file = name;
            if (file === "nether") file = "neither";
            if (file === "credits") file = "credit";
            const base = (window.location.pathname.includes("standalone_browser.html"))
                ? "bloxorz/gui/"
                : (window.location.protocol === "file:" ? "../" : "gui/");
            return `${base}${file}.mp3`;
        },

        init() {
            if (!this.bgm) {
                this.bgm = new Audio();
                this.bgm.loop = true;
                this.bgm.volume = this.volume;
                this.bgm.src = this._getTrackUrl(this.currentBiome);
                this.bgm.addEventListener("ended", () => {
                    if (this.bgmEnabled) {
                        this.bgm.play().catch(() => {});
                    }
                });
                this.bgm.addEventListener("error", () => {});
            }
        },

        setBiomeTrack(biomeName) {
            let track = (biomeName || "overworld").toLowerCase();
            if (track === "nether") track = "neither";
            // Giữ nguyên nguồn nhạc nếu cùng biome và đang phát, không reset src để tránh giật/phát lại từ đầu
            if (this.currentBiome === track && this.bgm) {
                if (this.bgmEnabled && this.bgm.paused) {
                    this.bgm.play().catch(() => {});
                }
                return;
            }
            this.currentBiome = track;
            const targetSrc = this._getTrackUrl(track);
            if (this.bgm) {
                const wasPlaying = !this.bgm.paused;
                this.bgm.src = targetSrc;
                if (this.bgmEnabled && (wasPlaying || !this.bgm.currentTime)) {
                    this.bgm.play().catch(() => {});
                }
            }
        },

        playCreditsMusic() {
            this.currentBiome = "credits";
            if (this.bgm) {
                this.bgm.src = this._getTrackUrl("credit");
                if (this.bgmEnabled) {
                    this.bgm.play().catch(() => {});
                }
            }
        },

        toggleBGM() {
            this.init();
            this.bgmEnabled = !this.bgmEnabled;
            if (window.BloxorzMenu && window.BloxorzMenu.settings) {
                window.BloxorzMenu.settings.bgm = this.bgmEnabled;
                window.BloxorzMenu.save();
            }
            if (this.bgmEnabled) {
                this.bgm.play().catch((err) => {
                    console.log("Autoplay prevented:", err);
                });
            } else {
                this.bgm.pause();
            }
            this.updateUI();
            return this.bgmEnabled;
        },

        setVolume(volPercent) {
            this.volume = (Math.max(0, Math.min(100, volPercent)) / 100) * 0.40;
            if (this.bgm) this.bgm.volume = this.volume;
        },

        updateUI() {
            const setBtn = document.getElementById("set-bgm");
            if (setBtn) {
                setBtn.innerText = `Nhạc nền: ${this.bgmEnabled ? "Bật" : "Tắt"}`;
            }
        }
    };

    const BloxorzInput = {
        /** Xử lý 1 phím chơi tay; bỏ qua khi cảnh đang diễn hoạt, đang chờ solver hoặc đang phát lời giải. */
        handleKey(event, client) {
            const credits = document.getElementById("mc-credits");
            if (credits && credits.classList.contains("show")) {
                if (event.key === "Escape" || event.key === " " || event.key === "Enter") {
                    event.preventDefault();
                    BloxorzHud.hideEndCredits();
                    return true;
                }
            }
            if (event.key === "Escape") {
                event.preventDefault();
                BloxorzMenu.toggle();
                return true;
            }
            if (BloxorzMenu.isOpen()) return false;  // menu đang mở: không chơi
            if (client.isProcessing || client.isAutoPlaying || client.isSolving) return false;
            const run = GAMEPLAY_KEYS[event.key.toLowerCase()];
            if (!run) return false;
            event.preventDefault();
            run(client);
            return true;
        },
    };

    const SETTINGS_KEY = "bloxorz.settings.v1";
    const PROGRESS_KEY = "bloxorz.progress.v1";
    const DEFAULT_SETTINGS = { volume: 80, muted: false, biome: "overworld", showHelp: true, lastStage: 0, bgm: true };
    const GROUP_NAMES = { G1: "Cơ bản", G2: "Ô dễ vỡ", G3: "Cầu & công tắc", G4: "Tách khối", G5: "Kết hợp" };
    const SPLASHES = ["Tách đôi khối!", "33 màn chơi!", "A* biết đường!", "Đừng rơi nhé!", "Đứng thẳng vào cổng!",
        "BFS · DFS · UCS · A*", "Cẩn thận cát cam!", "Phiến vàng tách khối!"];
    const ORBIT_DEG_PER_S = 6;  // tốc độ xoay cảnh nền khi menu mở

    // localStorage có thể bị chặn (chế độ riêng tư, file://): lỗi thì dùng giá trị mặc định, không làm hỏng game
    const storage = {
        load(key, fallback) {
            try {
                const value = JSON.parse(window.localStorage.getItem(key));
                return value && typeof value === "object" ? { ...fallback, ...value } : { ...fallback };
            } catch (_) {
                return { ...fallback };
            }
        },
        save(key, value) {
            try { window.localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* bỏ qua */ }
        },
    };

    /** Gửi sự kiện tới app.WebEventRouter qua bridge HTTP; lệnh vẽ trả về chuyển cho SceneBridge như mọi sự kiện. */
    async function postEvent(event, payload = {}) {
        try {
            const resp = await fetch("/api/event", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ event, payload }),
            });
            const data = await resp.json();
            if (data && data.commands && window.SceneBridge) window.SceneBridge.receiveCommands(data.commands);
            return data;
        } catch (_) {
            return null;  // mở trang không qua bridge (standalone): chỉ dùng được màn hiện tại
        }
    }

    const BloxorzMenu = {
        settings: storage.load(SETTINGS_KEY, DEFAULT_SETTINGS),
        progress: storage.load(PROGRESS_KEY, {}),  // id màn -> số bước tốt nhất khi tự chơi
        stages: [],
        current: -1,
        started: false,   // đã vào chơi ít nhất 1 lần: menu thành menu tạm dừng
        booted: false,    // đã áp cài đặt lúc tải trang (trước đó không lưu biome do cảnh tự đặt)
        history: [],
        orbitFrame: 0,

        el(id) { return document.getElementById(id); },

        init() {
            const menu = this.el("mc-menu");
            menu.addEventListener("click", (e) => {
                const go = e.target.closest("[data-go]");
                if (go) this.go(go.dataset.go);
                const biome = e.target.closest("[data-biome]");
                if (biome) this.setBiome(biome.dataset.biome);
                const level = e.target.closest("[data-level]");
                if (level) this.selectStage(Number(level.dataset.level));
            });
            this.el("menu-play").addEventListener("click", () => this.play());
            const quitBtn = this.el("menu-quit");
            if (quitBtn) {
                quitBtn.addEventListener("click", () => {
                    postEvent("quit");
                    setTimeout(() => window.close(), 150);
                });
            }
            const volume = this.el("set-volume");
            volume.addEventListener("input", () => this.setVolume(Number(volume.value), false));
            volume.addEventListener("change", () => this.setVolume(Number(volume.value), true));
            this.el("set-mute").addEventListener("click", () => this.setMuted(!this.settings.muted));
            const setBgm = this.el("set-bgm");
            if (setBgm) {
                setBgm.addEventListener("click", () => BloxorzAudio.toggleBGM());
            }
            this.el("set-help").addEventListener("click", () => this.setShowHelp(!this.settings.showHelp));
            this.el("set-reset").addEventListener("click", (e) => this.resetProgress(e.currentTarget));
            this.el("mc-splash").innerText = SPLASHES[Math.floor(Math.random() * SPLASHES.length)];
            this.renderSettings();
            this.applyHelp();
            this.open("title");
            window.addEventListener("load", () => this.boot());
        },

        /** Sau khi cảnh 3D của VT3 đã dựng: áp âm lượng đã lưu, lấy danh sách màn. */
        async boot() {
            if (this.settings.bgm !== undefined) {
                BloxorzAudio.bgmEnabled = Boolean(this.settings.bgm);
            } else {
                BloxorzAudio.bgmEnabled = true;
            }
            BloxorzAudio.init();
            this.applyAudio();
            this.booted = true;
            const data = await postEvent("stage_list");
            if (data && Array.isArray(data.stages)) {
                this.stages = data.stages;
                if (this.current < 0) this.current = data.current;
            }
            this.renderLevels();
            this.renderPlayButton();
            this.renderSettings();
            const unlockAudio = () => {
                if (BloxorzAudio.bgmEnabled && BloxorzAudio.bgm && BloxorzAudio.bgm.paused) {
                    BloxorzAudio.bgm.play().catch(() => {});
                }
                window.removeEventListener("pointerdown", unlockAudio);
                window.removeEventListener("keydown", unlockAudio);
            };
            window.addEventListener("pointerdown", unlockAudio, { once: true });
            window.addEventListener("keydown", unlockAudio, { once: true });
        },

        isOpen() { return this.el("mc-menu").classList.contains("show"); },

        open(screen = "title") {
            this.history = [];
            this.show(screen === "pause" ? "title" : screen);
            this.el("mc-menu").classList.add("show");
            document.body.classList.add("menu-open");
            this.renderPlayButton();
            this.startOrbit();
        },

        close() {
            this.el("mc-menu").classList.remove("show");
            document.body.classList.remove("menu-open");
            this.stopOrbit();
            this.started = true;
        },

        toggle() { this.isOpen() ? this.close() : this.open("pause"); },

        show(screen) {
            this.el("mc-menu").dataset.screen = screen;
            if (screen === "levels") this.renderLevels();
        },

        go(target) {
            if (target === "back") {
                this.show(this.history.pop() || "title");
                return;
            }
            this.history.push(this.el("mc-menu").dataset.screen);
            this.show(target);
        },

        /** Bắt đầu / tiếp tục: vào màn chơi gần nhất (lưu lại giữa các lần mở game). */
        play() {
            if (BloxorzAudio.bgmEnabled && BloxorzAudio.bgm && BloxorzAudio.bgm.paused) {
                BloxorzAudio.bgm.play().catch(() => {});
            }
            const last = this.settings.lastStage;
            if (!this.started && this.stages.length && last !== this.current && last >= 0 && last < this.stages.length) {
                this.selectStage(last);
                return;
            }
            this.close();
        },

        selectStage(index) {
            const client = window.SceneBridge;
            if (!client || client.isAutoPlaying || client.isSolving) return;
            client.cmdQueue = [];
            client.isProcessing = false;
            postEvent("select_stage", { index });
            this.close();
        },

        renderPlayButton() {
            const button = this.el("menu-play");
            const index = this.started ? this.current : this.settings.lastStage;
            const stage = this.stages[index];
            if (this.started) button.innerText = "Tiếp tục";
            else button.innerText = stage && index > 0 ? `Chơi tiếp · ${stage.name}` : "Bắt đầu";
            const done = this.stages.filter((st) => this.progress[st.id] !== undefined).length;
            this.el("menu-progress-note").innerText = `${done}/${this.stages.length} MÀN ĐÃ QUA`;
        },

        renderLevels() {
            const box = this.el("level-groups");
            if (!this.stages.length) return;
            const groups = {};
            this.stages.forEach((st) => (groups[st.group] = groups[st.group] || []).push(st));
            box.innerHTML = Object.keys(groups).sort().map((group) => `
                <div class="lv-group">
                    <div class="lv-group-title"><span class="lv-tag lv-${group}">${group}</span>${GROUP_NAMES[group] || ""}</div>
                    <div class="lv-grid">${groups[group].map((st) => {
                        const best = this.progress[st.id];
                        const cls = ["lv-tile", `lv-${group}`, best !== undefined ? "done" : "", st.index === this.current ? "current" : ""].join(" ");
                        return `<button class="${cls}" data-level="${st.index}" title="${st.name}">
                            <span class="lv-num">${st.name.replace("STAGE ", "")}</span>
                            <span class="lv-best">${best !== undefined ? `${best} BƯỚC` : "&nbsp;"}</span></button>`;
                    }).join("")}</div>
                </div>`).join("");
            const done = this.stages.filter((st) => this.progress[st.id] !== undefined).length;
            this.el("level-summary").innerText = `ĐÃ QUA ${done}/${this.stages.length}`;
        },

        // ---- cài đặt ----
        save() { storage.save(SETTINGS_KEY, this.settings); },

        renderSettings() {
            const { volume, muted, biome, showHelp } = this.settings;
            this.el("set-volume").value = volume;
            this.el("set-volume-label").innerText = muted ? "ÂM LƯỢNG: TẮT" : `ÂM LƯỢNG: ${volume}%`;
            this.el("set-volume").style.setProperty("--fill", `${muted ? 0 : volume}%`);
            this.el("set-mute").innerText = `Âm thanh: ${muted ? "Tắt" : "Bật"}`;
            const setBgm = this.el("set-bgm");
            if (setBgm) setBgm.innerText = `Nhạc nền: ${BloxorzAudio.bgmEnabled ? "Bật" : "Tắt"}`;
            this.el("set-help").innerText = `Bảng phím tắt: ${showHelp ? "Hiện" : "Ẩn"}`;
            document.querySelectorAll("#mc-menu [data-biome]").forEach((b) => b.classList.toggle("active", b.dataset.biome === biome));
        },

        /** Âm lượng qua kênh master của bộ âm thanh VT3 (SFX trong scene/index.html, mức gốc 0.85). */
        applyAudio() {
            if (typeof BloxorzAudio !== "undefined") {
                BloxorzAudio.setVolume(this.settings.muted ? 0 : this.settings.volume);
            }
            if (typeof SFX === "undefined") return;
            SFX.init();
            if (!SFX.master || !SFX.ctx) return;
            const gain = SFX.master.gain;
            gain.cancelScheduledValues(0);  // bỏ mức 0.85 VT3 đặt lúc khởi tạo; gán thẳng có hiệu lực cả khi chưa mở khóa âm thanh
            gain.value = this.settings.muted ? 0 : 0.85 * this.settings.volume / 100;
        },

        setVolume(volume, preview) {
            this.settings.volume = Math.max(0, Math.min(100, volume));
            this.settings.muted = false;
            this.save();
            this.renderSettings();
            this.applyAudio();
            if (preview && typeof SFX !== "undefined") SFX.playStep(true);
        },

        setMuted(muted) {
            this.settings.muted = muted;
            this.save();
            this.renderSettings();
            this.applyAudio();
        },

        setBiome(biome) {
            if (window.SceneBridge) window.SceneBridge.setBiome(biome);  // cảnh gọi lại markBiome -> onBiome lưu
            else this.onBiome(biome);
        },

        setShowHelp(show) {
            this.settings.showHelp = show;
            this.save();
            this.renderSettings();
            this.applyHelp();
        },

        applyHelp() { document.body.classList.toggle("hide-help", !this.settings.showHelp); },

        resetProgress(button) {
            if (!button.classList.contains("confirm")) {
                button.classList.add("confirm");
                button.innerText = "Bấm lần nữa để xoá";
                setTimeout(() => { button.classList.remove("confirm"); button.innerText = "Xoá tiến trình"; }, 2500);
                return;
            }
            this.progress = {};
            storage.save(PROGRESS_KEY, this.progress);
            button.classList.remove("confirm");
            button.innerText = "Đã xoá tiến trình";
            this.renderLevels();
            this.renderPlayButton();
        },

        // ---- móc từ BloxorzHud ----
        onStage(index) {
            if (index < 0) return;
            this.current = index;
            if (this.booted) {
                this.settings.lastStage = index;
                this.save();
            }
        },

        onBiome(biome) {
            if (!this.booted) return;  // lúc tải trang cảnh tự đặt biome mặc định: không ghi đè cài đặt
            this.settings.biome = biome;
            this.save();
            this.renderSettings();
        },

        recordWin(moves) {
            const stage = this.stages[this.current];
            if (!stage || !Number.isFinite(moves)) return;
            const best = this.progress[stage.id];
            if (best === undefined || moves < best) {
                this.progress[stage.id] = moves;
                storage.save(PROGRESS_KEY, this.progress);
            }
        },

        // ---- cảnh nền xoay chậm (camera của VT3) ----
        startOrbit() {
            if (this.orbitFrame) return;
            let last = performance.now();
            const step = (now) => {
                const cam = window.SceneBridge && window.SceneBridge.renderer && window.SceneBridge.renderer.gimbalCam;
                if (cam) cam.rotateStep(ORBIT_DEG_PER_S * Math.min(now - last, 100) / 1000);
                last = now;
                this.orbitFrame = requestAnimationFrame(step);
            };
            this.orbitFrame = requestAnimationFrame(step);
        },

        stopOrbit() {
            cancelAnimationFrame(this.orbitFrame);
            this.orbitFrame = 0;
            const cam = window.SceneBridge && window.SceneBridge.renderer && window.SceneBridge.renderer.gimbalCam;
            if (cam) cam.resetGoldenAngle();
        },
    };

    window.BloxorzHud = BloxorzHud;
    window.BloxorzInput = BloxorzInput;
    window.BloxorzMenu = BloxorzMenu;
    window.BloxorzAudio = BloxorzAudio;
    BloxorzHud.mount();
    BloxorzMenu.init();
})();
