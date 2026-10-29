/* Phụ trách: VT4 - Task 4.2 / 4.3 / 4.4 / 4.5
 * Giao diện 2D và phím chơi tay cho cảnh WebGL của VT3 (scene/index.html), tách nguyên văn từ index.html:
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

        <div class="mc-panel controls-bar">
            <button class="mc-btn active" id="btn-overworld" onclick="SceneBridge.setBiome('overworld')">Overworld</button>
            <button class="mc-btn biome-nether" id="btn-nether" onclick="SceneBridge.setBiome('nether')">Nether</button>
            <button class="mc-btn biome-end" id="btn-end" onclick="SceneBridge.setBiome('end')">The End</button>
            <span style="color:#555">|</span>
            <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('astar')" title="Giải tự động bằng thuật toán A*">AI Solve (A*)</button>
            <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('bfs')" title="Giải tự động bằng thuật toán BFS">AI Solve (BFS)</button>
            <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('dfs')" title="Giải tự động bằng thuật toán DFS">AI Solve (DFS)</button>
            <button class="mc-btn ai-btn" onclick="SceneBridge.requestAISolve('ucs')" title="Giải tự động bằng thuật toán UCS">AI Solve (UCS)</button>
            <span style="color:#555">|</span>
            <button class="mc-btn" onclick="SceneBridge.requestUndo()">Undo (U)</button>
            <button class="mc-btn" onclick="SceneBridge.requestRestart()">Restart (R)</button>
            <button class="mc-btn" onclick="SceneBridge.requestPrevStage()">&lt; Prev (P)</button>
            <button class="mc-btn" onclick="SceneBridge.requestNextStage()">Next (N) &gt;</button>
        </div>
    </div>

    <div class="bottom-bar">
        <div class="mc-panel help-panel">
            <div><span class="key-badge">W</span><span class="key-badge">A</span><span class="key-badge">S</span><span class="key-badge">D</span> / <span class="key-badge">ARROWS</span> : LẬT KHỐI GỖ SỒI &nbsp; <span class="key-badge">SPACE</span> : ĐỔI KHỐI KHI TÁCH &nbsp; <span class="key-badge">G</span> : AI SOLVE (A*)</div>
            <div><span class="key-badge">U</span> : HOÀN TÁC &nbsp; <span class="key-badge">R</span> : CHƠI LẠI &nbsp; <span class="key-badge">P</span>/<span class="key-badge">N</span> : ĐỔI MÀN &nbsp; <span class="key-badge">1</span><span class="key-badge">2</span><span class="key-badge">3</span> : BIOME</div>
            <div><span class="key-badge">CHUỘT TRÁI + KÉO</span> : GIMBAL ORBIT &nbsp; <span class="key-badge">CON LĂN</span> : ZOOM &nbsp; <span class="key-badge">C</span>/<span class="key-badge">T</span>/<span class="key-badge">Q</span>/<span class="key-badge">E</span> : GÓC CAM</div>
        </div>
        <div class="mc-panel help-panel" style="text-align: right;">
            <div style="color:#ffaa00">CHÚ THÍCH BÀN ĐẠP VOXEL (MINECRAFT):</div>
            <div>BÀN ĐẠP SẮT (x): Iron Slab (Cần khối đứng thẳng đè nặng)</div>
            <div>BÀN ĐẠP VÀNG (S): Golden Slab (Tách đôi thành 2 khối 1x1)</div>
            <div>BÀN ĐẠP GỖ (o): Oak Slab (Chạm nhẹ bất kỳ là kích hoạt)</div>
            <div>CÁT CAM (! / F): Vỡ nếu đứng thẳng lên trên</div>
        </div>
    </div>
</div>

<div id="banner-msg">
    STAGE CLEAR!
    <span class="sub">ĐANG DỊCH CHUYỂN QUA CỔNG END...</span>
</div>
`;

    const BloxorzHud = {
        /** Chèn lớp giao diện vào trang (gọi 1 lần, ngay khi tải file này ở cuối <body>). */
        mount() {
            if (document.querySelector(".ui-layer")) return;
            document.body.insertAdjacentHTML("beforeend", HUD_MARKUP);
        },

        updateStats(stageName, stageIdx, totalStages, moves) {
            if (stageName) document.getElementById("ui-stage-name").innerText = stageName;
            document.getElementById("ui-stage").innerText = `${stageIdx}/${totalStages}`;
            document.getElementById("ui-moves").innerText = moves;
        },

        setMoves(moves) {
            document.getElementById("ui-moves").innerText = moves;
        },

        /** Tô sáng nút của biome đang chọn. */
        markBiome(biomeName) {
            document.getElementById("btn-overworld").classList.toggle("active", biomeName === "overworld");
            document.getElementById("btn-nether").classList.toggle("active", biomeName === "nether");
            document.getElementById("btn-end").classList.toggle("active", biomeName === "end");
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
            const badge = document.getElementById("ui-ai-badge");
            badge.style.display = "inline-block";
            badge.innerText = solver.status === "solved"
                ? `${solver.algorithm}: ${solver.moves} MOVES | COST ${solver.cost} | ${solver.execution_time_ms}ms | ${solver.nodes_expanded} NODES`
                : `${solver.algorithm}: ${String(solver.status_text).toUpperCase()} | ${solver.nodes_expanded} NODES`;
        },

        hideSolver() {
            document.getElementById("ui-ai-badge").style.display = "none";
        },

        showBanner() {
            document.getElementById("banner-msg").classList.add("show");
        },

        hideBanner() {
            document.getElementById("banner-msg").classList.remove("show");
        },

        /** Hoạt ảnh thắng của cảnh đã xong: tự sang màn sau. */
        afterWin(client) {
            client.requestNextStage();
        },
    };

    // phím -> hàm của SceneBridge; bỏ qua khi cảnh đang diễn hoạt hoặc đang phát lời giải
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
    };

    const BloxorzInput = {
        /** Xử lý 1 phím chơi tay; bỏ qua khi cảnh đang diễn hoạt hoặc đang phát lời giải. */
        handleKey(event, client) {
            if (client.isProcessing || client.isAutoPlaying) return false;
            const run = GAMEPLAY_KEYS[event.key.toLowerCase()];
            if (!run) return false;
            event.preventDefault();
            run(client);
            return true;
        },
    };

    window.BloxorzHud = BloxorzHud;
    window.BloxorzInput = BloxorzInput;
    BloxorzHud.mount();
})();
