/* Benchmark Studio: Minimalist Engineering Terminal Aesthetic
 * - Zero SaaS slop, no rounded plastic cards, no muddy navy gradients.
 * - Map occupies maximum space at the center (80%+).
 * - Bottom telemetry strip matches the reference video: [ ALGO > COMMS ] --- |||||||| ---
 * - Preserves loved vibrant neon colors: Neon Purple (#a855f7), Emerald (#10b981), Amber (#f59e0b).
 */
(function () {
    "use strict";

    const ALGOS = [
        ["astar", "A* (Relaxed)"],
        ["astar_manhattan", "A* (Manhattan)"],
        ["ucs", "UCS"],
        ["bfs", "BFS"],
        ["dfs", "DFS"],
    ];
    const FULL_NAME = Object.fromEntries(ALGOS);

    const C = {
        tile: "#090d14",
        tileEdge: "#1e293b",
        fragile: "#3b1a08",
        bridge: "#072b4a",
        goal: "#f43f5e",
        blockFill: "#ecfdf5",
        blockEdge: "#10b981",
        path: "#fbbf24",
        purpleCore: "#c084fc",
        purpleGlow: "#a855f7",
        phosphor: "#00ff66",
    };
    const SWITCH_COLOR = { heavy: "#e2e8f0", soft: "#f59e0b", split: "#38bdf8" };

    const selectOptions = (def) =>
        ALGOS.map(([v, n]) => `<option value="${v}" ${v === def ? "selected" : ""}>${n}</option>`).join("");

    const MARKUP = `
<div id="bench-overlay" class="bench">
    <!-- Row 1: Technical Top Bar (Navigation & Mode) -->
    <div class="bench-toolbar">
        <div class="bench-brand">
            <span class="bench-brand-title">BLOXORZ // BENCHMARK TERMINAL</span>
        </div>

        <div class="bench-stage-stepper">
            <button type="button" id="bench-prev-stage" class="bench-stepper-btn" title="Màn trước">◀</button>
            <select id="bench-stage-select" class="bench-stage-dropdown" title="Chọn màn chơi"></select>
            <button type="button" id="bench-next-stage" class="bench-stepper-btn" title="Màn kế tiếp">▶</button>
        </div>

        <div class="bench-segmented" id="bench-mode-toggle">
            <button type="button" data-mode="single" class="on">SINGLE</button>
            <button type="button" data-mode="compare">COMPARE</button>
        </div>

        <button type="button" id="bench-close" class="bench-close-btn" title="Đóng (Esc)">[ ✕ ]</button>
    </div>

    <!-- Row 2: Action Bar (Chức năng Playback & Điều khiển) -->
    <div class="bench-action-bar">
        <div class="bench-bar-group">
            <div class="bench-btn-group">
                <button type="button" id="bench-run" class="bench-btn bench-btn-run">▶ RUN</button>
                <button type="button" id="bench-play" class="bench-btn">❚❚ PAUSE</button>
                <button type="button" id="bench-step" class="bench-btn">⏭ STEP</button>
                <button type="button" id="bench-reset" class="bench-btn">↺ RESET</button>
            </div>

            <div class="bench-speed-box">
                <span class="bench-label-muted">SPEED</span>
                <input id="bench-speed" type="range" min="0" max="10" value="4">
            </div>

            <div class="bench-step-counter" id="bench-step-counter">
                <span class="bench-label-muted">STEP:</span> <b class="bench-metric-val" id="bench-step-val">0 / 0</b>
            </div>
        </div>

        <div class="bench-subbar-legend">
            <div class="bench-legend-item"><span class="bench-legend-box" style="background:#090d14;border:1px solid #1e293b"></span>Unvisited</div>
            <div class="bench-legend-item"><span class="bench-legend-box" style="background:#a855f7"></span>Visited (Neon)</div>
            <div class="bench-legend-item"><span class="bench-legend-box" style="background:#0284c7"></span>h(n) Field</div>
            <div class="bench-legend-item"><span class="bench-legend-box" style="background:#10b981"></span>Block</div>
            <div class="bench-legend-item"><span class="bench-legend-box" style="background:#fbbf24"></span>Solution</div>
            <div class="bench-legend-item"><span class="bench-legend-box" style="background:#f43f5e"></span>Goal</div>
        </div>
    </div>

    <!-- Row 3: Dedicated Selection & View Bar (Dãy riêng dưới các phím chức năng) -->
    <div class="bench-select-bar">
        <!-- Single Mode Selection & Status -->
        <div class="bench-select-bar-inner single-only">
            <div class="bench-bar-group">
                <span class="bench-label-muted">ALGORITHM:</span>
                <select id="bench-algo-single" class="bench-select">${selectOptions("astar")}</select>
                <span class="bench-divider">|</span>
                <span class="bench-label-muted">STATUS:</span>
                <span id="bench-single-status" class="bench-status-badge" style="color:#38bdf8;">READY</span>
            </div>
        </div>

        <!-- Compare Mode Selection, Leaderboard & View Switcher -->
        <div class="bench-select-bar-inner compare-only">
            <div class="bench-bar-group">
                <span class="bench-label-muted">COMPARE:</span>
                <div class="bench-compare-pills" id="bench-compare-pills">
                    <button type="button" class="bench-pill on" data-algo="astar">A* (Relaxed)</button>
                    <button type="button" class="bench-pill on" data-algo="astar_manhattan">A* (Manh)</button>
                    <button type="button" class="bench-pill on" data-algo="ucs">UCS</button>
                    <button type="button" class="bench-pill on" data-algo="bfs">BFS</button>
                    <button type="button" class="bench-pill" data-algo="dfs">DFS</button>
                </div>
                <button type="button" id="bench-leaderboard-btn" class="bench-btn bench-btn-gold" title="Mở bảng tổng kết">🏆 BXH TỔNG KẾT</button>
            </div>

            <!-- Dedicated View Switcher in Row 3 -->
            <div class="bench-view-switcher">
                <span class="bench-view-label">VIEWING:</span>
                <button type="button" id="bench-view-prev" class="bench-stepper-btn" title="Xem thuật toán trước (←)">◀</button>
                <select id="bench-view-select" class="bench-stage-dropdown"></select>
                <button type="button" id="bench-view-next" class="bench-stepper-btn" title="Xem thuật toán kế tiếp (→)">▶</button>
                <span class="bench-view-count" id="bench-view-count">(1 / 1)</span>
                <span id="bench-view-status" class="bench-status-badge" style="color:#34d399;">SOLVED</span>
            </div>
        </div>
    </div>

    <!-- Main Workspace Body: Map Central -->
    <div class="bench-body" id="bench-body">
        <div style="margin: auto; color: #475569; font-size: 13px; letter-spacing: 1px;">INITIALIZING TELEMETRY STREAM...</div>
    </div>

    <!-- Leaderboard Popup / Modal -->
    <div class="bench-modal-backdrop" id="bench-leaderboard-modal">
        <div class="bench-modal">
            <div class="bench-modal-header">
                <div class="bench-modal-title">🏆 BENCHMARK LEADERBOARD // STAGE STATS</div>
                <button type="button" id="bench-modal-close" class="bench-close-btn" title="Đóng">[ ✕ ]</button>
            </div>
            <div class="bench-modal-body">
                <table class="bench-table">
                    <thead>
                        <tr>
                            <th>RANK</th>
                            <th>ALGORITHM</th>
                            <th>STATUS</th>
                            <th>EXPANDED</th>
                            <th>FRONTIER (PEAK)</th>
                            <th>PATH MOVES</th>
                            <th>TIME (MS)</th>
                        </tr>
                    </thead>
                    <tbody id="bench-leaderboard-tbody"></tbody>
                </table>
            </div>
            <div class="bench-modal-footer">
                <span id="bench-modal-summary">&gt; BENCHMARK COMPLETE</span>
                <span style="font-size:10px;color:#64748b;">(Click [✕] hoặc Esc để tắt)</span>
            </div>
        </div>
    </div>
</div>`;

    const key = (cell) => cell[0] + "," + cell[1];

    function makeLane(trace, idx) {
        return {
            trace,
            idx,
            i: 0,
            acc: 0,
            visits: new Map(),
            cur: null,
        };
    }

    function makeBenchView() {
        const el = document.createElement("div");
        el.className = "bench-single-view";
        el.innerHTML = `
            <div class="bench-single-map-area">
                <canvas data-slot="map"></canvas>
            </div>
            <div class="bench-telemetry-deck">
                <div class="bench-comms-row">
                    <span class="bench-comms-badge" data-slot="comms-badge">COMMS</span>
                    <div class="bench-wave-canvas-wrap">
                        <canvas data-slot="wave"></canvas>
                    </div>
                </div>
                <div class="bench-telemetry-metrics-line" data-slot="metrics-line">
                    &gt; ACQUIRING SEARCH TELEMETRY...
                </div>
            </div>
        `;
        return {
            el,
            canvasMap: el.querySelector('[data-slot="map"]'),
            canvasWave: el.querySelector('[data-slot="wave"]'),
            commsBadge: el.querySelector('[data-slot="comms-badge"]'),
            metricsLine: el.querySelector('[data-slot="metrics-line"]'),
        };
    }

    function resetLane(lane) {
        lane.i = 0;
        lane.acc = 0;
        lane.visits.clear();
        lane.cur = lane.trace.events.length ? lane.trace.events[0] : null;
    }

    function stepLane(lane) {
        const ev = lane.trace.events[lane.i];
        if (!ev) return;
        lane.i += 1;
        lane.cur = ev;
        for (const cell of ev.cells) lane.visits.set(key(cell), (lane.visits.get(key(cell)) || 0) + 1);
    }

    const isDone = (lane) => lane.i >= lane.trace.events.length;

    function drawWave(lane, canvas) {
        if (!canvas) canvas = lane.canvasWave;
        if (!canvas) return;
        const dpr = window.devicePixelRatio || 1;
        const w = canvas.clientWidth, h = canvas.clientHeight;
        if (w <= 0 || h <= 0) return;
        if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
            canvas.width = Math.round(w * dpr);
            canvas.height = Math.round(h * dpr);
        }
        const g = canvas.getContext("2d");
        g.setTransform(dpr, 0, 0, dpr, 0, 0);
        g.clearRect(0, 0, w, h);

        // Nét đứt ngang dẫn hướng kiểu comms
        g.strokeStyle = "rgba(255, 255, 255, 0.12)";
        g.setLineDash([4, 4]);
        g.beginPath();
        g.moveTo(0, h - 3);
        g.lineTo(w, h - 3);
        g.stroke();
        g.setLineDash([]);

        const events = lane.trace.events;
        const numBars = Math.min(140, Math.max(48, Math.floor(w / 7)));
        const barW = Math.max(2, Math.floor((w / numBars) * 0.58));
        const maxFrontier = Math.max(4, ...events.map((e) => e.frontier || 1));

        for (let b = 0; b < numBars; b++) {
            const evIdx = events.length ? Math.floor((b / numBars) * events.length) : 0;
            const bx = Math.floor(b * (w / numBars));

            if (evIdx < lane.i && events[evIdx]) {
                const fVal = events[evIdx].frontier || 1;
                const ratio = Math.min(1, fVal / maxFrontier);
                // Vươn cao ấn tượng (chiếm tới gần hết chiều cao canvas 64px)
                const bh = Math.max(4, Math.floor(ratio * (h - 8)));
                const isHead = b === Math.floor(((lane.i - 1) / Math.max(1, events.length)) * numBars);

                g.fillStyle = isHead ? "#f8fafc" : lane.idx % 2 === 1 ? "#c084fc" : C.phosphor;
                g.fillRect(bx, h - bh - 3, barW, bh);

                // Highlight cap trên đỉnh
                g.fillStyle = isHead ? "#ffffff" : lane.idx % 2 === 1 ? "#f3e8ff" : "#86efac";
                g.fillRect(bx, h - bh - 3, barW, Math.min(2, bh));
            }
        }
    }

    function drawMap(lane, canvas) {
        if (!canvas) canvas = lane.canvasMap;
        if (!canvas || !lane) return;
        const { trace } = lane;
        const dpr = window.devicePixelRatio || 1;
        const w = canvas.clientWidth, h = canvas.clientHeight;
        if (w <= 0 || h <= 0) return;
        if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
            canvas.width = Math.round(w * dpr);
            canvas.height = Math.round(h * dpr);
        }
        const g = canvas.getContext("2d");
        g.setTransform(dpr, 0, 0, dpr, 0, 0);
        g.clearRect(0, 0, w, h);

        // Lưới tọa độ kỹ thuật tối giản (Technical Hairline Grid)
        const gridStep = 32;
        g.strokeStyle = "rgba(255, 255, 255, 0.03)";
        g.lineWidth = 1;
        g.beginPath();
        for (let x = 0; x < w; x += gridStep) { g.moveTo(x, 0); g.lineTo(x, h); }
        for (let y = 0; y < h; y += gridStep) { g.moveTo(0, y); g.lineTo(w, y); }
        g.stroke();

        // Tính Bounding Box thực của các ô chơi (bỏ qua ký tự '.' trống)
        let minR = Infinity, maxR = -Infinity, minC = Infinity, maxC = -Infinity;
        trace.grid.forEach((row, r) => {
            for (let c = 0; c < row.length; c++) {
                if (row[c] !== ".") {
                    if (r < minR) minR = r;
                    if (r > maxR) maxR = r;
                    if (c < minC) minC = c;
                    if (c > maxC) maxC = c;
                }
            }
        });
        if (minR === Infinity) { minR = 0; maxR = trace.grid.length - 1; minC = 0; maxC = 14; }

        const contentRows = maxR - minR + 1;
        const contentCols = maxC - minC + 1;
        const pad = 28;
        const availW = Math.max(100, w - pad * 2);
        const availH = Math.max(100, h - pad * 2);
        const size = Math.max(16, Math.floor(Math.min(availW / contentCols, availH / contentRows)));

        // Căn giữa tuyệt đối cụm ô chơi vào trung tâm canvas
        const ox = Math.floor((w - size * contentCols) / 2) - minC * size;
        const oy = Math.floor((h - size * contentRows) / 2) - minR * size;

        const center = (cell) => [ox + (cell[1] + 0.5) * size, oy + (cell[0] + 0.5) * size];

        // 1. Sàn ô vuông phẳng, kỹ thuật, sắc nét
        const field = trace.heuristic_field;
        const hMax = field ? Math.max(1, ...Object.values(field).filter((v) => v !== null)) : 1;

        trace.grid.forEach((row, r) => [...row].forEach((ch, c) => {
            if (ch === ".") return;
            const x = ox + c * size, y = oy + r * size;
            g.fillStyle = ch === "F" ? C.fragile : ch === "B" ? C.bridge : C.tile;
            g.fillRect(x + 1, y + 1, size - 2, size - 2);
            g.strokeStyle = C.tileEdge;
            g.lineWidth = 1;
            g.strokeRect(x + 1, y + 1, size - 2, size - 2);

            const hv = field ? field[r + "," + c] : null;
            if (hv !== null && hv !== undefined) {
                const ratio = 1 - hv / hMax;
                g.fillStyle = `rgba(2, 132, 199, ${(0.24 * ratio).toFixed(3)})`;
                g.fillRect(x + 2, y + 2, size - 4, size - 4);
            }
        }));

        // 2. Ô đã mở rộng: TÍM NEON PHÁT QUANG RỰC RỠ (#a855f7)
        for (const [k, n] of lane.visits) {
            const [r, c] = k.split(",").map(Number);
            const x = ox + c * size, y = oy + r * size;
            const alpha = Math.min(0.35 + 0.16 * n, 0.92);
            g.save();
            g.shadowColor = C.purpleGlow;
            g.shadowBlur = Math.min(20, 8 + n * 3);
            g.fillStyle = `rgba(168, 85, 247, ${alpha.toFixed(2)})`;
            g.fillRect(x + 2, y + 2, size - 4, size - 4);
            g.strokeStyle = `rgba(216, 180, 254, ${Math.min(0.98, alpha + 0.25).toFixed(2)})`;
            g.lineWidth = 1.5;
            g.strokeRect(x + 2.5, y + 2.5, size - 5, size - 5);
            g.restore();
        }

        // 3. Số Heuristic h(n) trên từng ô
        if (field && size >= 24) {
            g.save();
            g.fillStyle = "rgba(148, 163, 184, 0.85)";
            g.font = `600 ${Math.max(9, Math.floor(size * 0.25))}px ui-monospace, monospace`;
            g.textAlign = "right";
            g.textBaseline = "bottom";
            trace.grid.forEach((row, r) => [...row].forEach((ch, c) => {
                if (ch === ".") return;
                const hv = field[r + "," + c];
                if (hv !== null && hv !== undefined) {
                    g.fillText(String(hv), ox + (c + 1) * size - 3, oy + (r + 1) * size - 2);
                }
            }));
            g.restore();
        }

        // 4. Công tắc & Lỗ đích
        for (const s of trace.switches) {
            const [x, y] = center(s.pos);
            g.save();
            g.strokeStyle = SWITCH_COLOR[s.kind] || "#fff";
            g.shadowColor = g.strokeStyle;
            g.shadowBlur = 8;
            g.lineWidth = Math.max(2, size * 0.08);
            g.beginPath();
            g.arc(x, y, size * 0.26, 0, Math.PI * 2);
            g.stroke();
            g.restore();
        }
        g.save();
        g.shadowColor = C.goal;
        g.shadowBlur = size * 0.7;
        g.fillStyle = C.goal;
        const gx = ox + trace.goal[1] * size + size * 0.18;
        const gy = oy + trace.goal[0] * size + size * 0.18;
        g.fillRect(gx, gy, size * 0.64, size * 0.64);
        g.restore();

        // 5. Đường nghiệm tối ưu (Vàng hổ phách mềm mại)
        if (isDone(lane) && trace.path.length) {
            g.save();
            g.strokeStyle = C.path;
            g.shadowColor = C.path;
            g.shadowBlur = 12;
            g.lineWidth = Math.max(3, size * 0.13);
            g.lineJoin = "round";
            g.lineCap = "round";
            g.beginPath();
            trace.path.forEach((cells, idx) => {
                const pts = cells.map(center);
                const x = pts.reduce((a, p) => a + p[0], 0) / pts.length;
                const y = pts.reduce((a, p) => a + p[1], 0) / pts.length;
                idx ? g.lineTo(x, y) : g.moveTo(x, y);
            });
            g.stroke();
            g.restore();
        }

        // 6. Khối 2D (Active Block Footprint)
        const cells = isDone(lane) && trace.path.length ? trace.path[trace.path.length - 1] : lane.cur && lane.cur.cells;
        if (cells) {
            const adjacent = cells.length === 2 &&
                Math.abs(cells[0][0] - cells[1][0]) + Math.abs(cells[0][1] - cells[1][1]) === 1;
            const groups = adjacent ? [cells] : cells.map((cell) => [cell]);
            for (const group of groups) {
                const r0 = Math.min(...group.map((p) => p[0])), c0 = Math.min(...group.map((p) => p[1]));
                const r1 = Math.max(...group.map((p) => p[0])), c1 = Math.max(...group.map((p) => p[1]));
                const inset = size * (group.length === 1 && !adjacent && cells.length === 2 ? 0.22 : 0.12);
                const x = ox + c0 * size + inset, y = oy + r0 * size + inset;
                const bw = (c1 - c0 + 1) * size - 2 * inset, bh = (r1 - r0 + 1) * size - 2 * inset;
                g.save();
                g.shadowColor = C.blockEdge;
                g.shadowBlur = 14;
                g.fillStyle = C.blockFill;
                g.fillRect(x, y, bw, bh);
                g.strokeStyle = C.blockEdge;
                g.lineWidth = Math.max(2, size * 0.08);
                g.strokeRect(x, y, bw, bh);
                g.restore();
            }
        }
    }

    function updateTelemetryLine(lane, view) {
        if (!lane || !view) return;
        const { trace, i, cur } = lane;
        const done = isDone(lane);
        const total = trace.events.length;
        const pct = total ? Math.round((i / total) * 100) : 0;
        const statusStr = done ? trace.status.toUpperCase() : "EXPLORING";

        const statusColor = done ? (trace.status === "solved" ? "#34d399" : "#f43f5e") : "#38bdf8";

        const singleStatus = document.getElementById("bench-single-status");
        if (singleStatus) {
            singleStatus.textContent = statusStr;
            singleStatus.style.color = statusColor;
        }

        const viewStatus = document.getElementById("bench-view-status");
        if (viewStatus) {
            viewStatus.textContent = statusStr;
            viewStatus.style.color = statusColor;
        }

        if (view.commsBadge) {
            view.commsBadge.textContent = `${(trace.algorithm || "").toUpperCase()} > COMMS`;
            view.commsBadge.className = `bench-comms-badge ${lane.idx % 2 === 1 ? 'purple' : ''}`;
        }

        if (view.metricsLine) {
            const costStr = done && trace.status === "solved" ? `${trace.stats.cost} (${trace.stats.length} MOVES)` : (cur && cur.g !== null ? `g: ${cur.g}` : "-");
            const heurStr = cur && cur.h !== null ? ` | HEURISTIC: <b class="bench-metric-val cyan">h(n)=${cur.h}</b>` : "";
            const fVal = cur ? (cur.frontier ?? 0) : 0;

            view.metricsLine.innerHTML = `
                <span>&gt; STATUS: <b class="bench-metric-val ${done ? 'emerald' : 'cyan'}">${statusStr}</b></span>
                <span>|</span>
                <span>EXPANDED: <b class="bench-metric-val emerald">${i}/${total} (${pct}%)</b></span>
                <span>|</span>
                <span>FRONTIER: <b class="bench-metric-val purple">${fVal}</b></span>
                <span>|</span>
                <span>COST: <b class="bench-metric-val amber">${costStr}</b>${heurStr}</span>
                <span>|</span>
                <span>TIME: <b class="bench-metric-val">${trace.stats.time_ms} MS</b></span>
            `;
        }
    }

    const BloxorzBench = {
        mode: "single",
        algoSingle: "astar",
        selectedAlgos: new Set(["astar", "astar_manhattan", "ucs", "bfs"]),
        stages: [],
        currentStageIdx: 0,
        lanes: [],
        activeLaneIdx: 0,
        view: null,
        playing: false,
        shown: false,

        el(id) { return document.getElementById(id); },

        mount() {
            document.body.insertAdjacentHTML("beforeend", MARKUP);
            const overlay = this.el("bench-overlay");

            // Segmented mode toggle (Single vs Compare)
            overlay.querySelectorAll("#bench-mode-toggle button").forEach((b) =>
                b.addEventListener("click", () => this.switchMode(b.dataset.mode)));

            // Stage Stepper & Dropdown
            this.el("bench-prev-stage").addEventListener("click", () => this.changeStageRel(-1));
            this.el("bench-next-stage").addEventListener("click", () => this.changeStageRel(1));
            this.el("bench-stage-select").addEventListener("change", (e) => this.selectStage(Number(e.target.value)));

            // Single algo selector
            this.el("bench-algo-single").addEventListener("change", (e) => {
                this.algoSingle = e.target.value;
                if (this.mode === "single") this.run();
            });

            // Compare multi-pills toggle
            this.el("bench-compare-pills").querySelectorAll("button").forEach((btn) => {
                btn.addEventListener("click", () => {
                    const algo = btn.dataset.algo;
                    if (this.selectedAlgos.has(algo)) {
                        if (this.selectedAlgos.size > 1) {
                            this.selectedAlgos.delete(algo);
                            btn.classList.remove("on");
                        }
                    } else {
                        this.selectedAlgos.add(algo);
                        btn.classList.add("on");
                    }
                    if (this.mode === "compare") this.run();
                });
            });

            // Playback controls
            this.el("bench-run").addEventListener("click", () => this.run());
            this.el("bench-play").addEventListener("click", () => this.togglePlay());
            this.el("bench-step").addEventListener("click", () => this.step());
            this.el("bench-reset").addEventListener("click", () => this.reset());
            this.el("bench-close").addEventListener("click", () => this.close());

            // Leaderboard modal buttons
            this.el("bench-leaderboard-btn").addEventListener("click", () => this.openLeaderboard());
            this.el("bench-modal-close").addEventListener("click", () => this.closeLeaderboard());
            this.el("bench-leaderboard-modal").addEventListener("click", (e) => {
                if (e.target === this.el("bench-leaderboard-modal")) this.closeLeaderboard();
            });

            // View Switcher controls (in Row 3)
            this.el("bench-view-prev").addEventListener("click", () => this.switchActiveLaneRel(-1));
            this.el("bench-view-next").addEventListener("click", () => this.switchActiveLaneRel(1));
            this.el("bench-view-select").addEventListener("change", (e) => this.setActiveLane(Number(e.target.value)));

            // Mount button in main 3D HUD controls bar
            const bar = document.querySelector(".controls-bar");
            if (bar) {
                const btn = document.createElement("button");
                btn.className = "mc-btn ai-btn";
                btn.textContent = "Benchmark Studio";
                btn.title = "Mở Visualizer Thuật Toán (Engineering Terminal)";
                btn.addEventListener("click", () => this.open());
                bar.appendChild(btn);
            }

            window.addEventListener("keydown", (e) => {
                if (!this.isOpen()) return;
                e.stopPropagation();
                if (e.key === "Escape") {
                    if (this.isLeaderboardOpen()) this.closeLeaderboard();
                    else this.close();
                } else if (e.key === " ") {
                    e.preventDefault();
                    this.togglePlay();
                } else if (e.key === "ArrowLeft") {
                    e.preventDefault();
                    this.switchActiveLaneRel(-1);
                } else if (e.key === "ArrowRight") {
                    e.preventDefault();
                    this.switchActiveLaneRel(1);
                }
            }, true);

            requestAnimationFrame(() => this.frame());
        },

        isOpen() { return this.el("bench-overlay").classList.contains("show"); },
        isLeaderboardOpen() { return this.el("bench-leaderboard-modal").classList.contains("show"); },

        openLeaderboard() {
            if (!this.lanes.length) return;
            const traces = this.lanes.map((l) => l.trace);
            const sorted = [...traces].sort((a, b) => {
                if (a.status === "solved" && b.status !== "solved") return -1;
                if (b.status === "solved" && a.status !== "solved") return 1;
                if (a.stats.expanded !== b.stats.expanded) return a.stats.expanded - b.stats.expanded;
                return a.stats.time_ms - b.stats.time_ms;
            });

            const tbody = this.el("bench-leaderboard-tbody");
            tbody.innerHTML = sorted.map((t, idx) => {
                const isWinner = idx === 0 && t.status === "solved";
                const rankBadge = idx === 0 ? "bench-rank-1" : idx === 1 ? "bench-rank-2" : idx === 2 ? "bench-rank-3" : "bench-rank-n";
                const peakFrontier = Math.max(1, ...t.events.map((e) => e.frontier || 0));
                return `
                    <tr class="${isWinner ? 'winner-row' : ''}" style="cursor:pointer;" data-algo="${t.algorithm}">
                        <td><span class="bench-rank-badge ${rankBadge}">#${idx + 1}</span></td>
                        <td style="font-weight:700;color:${isWinner ? '#fbbf24' : '#f8fafc'};">${FULL_NAME[t.algorithm] || t.algorithm}</td>
                        <td><span style="color:${t.status === 'solved' ? '#34d399' : '#f43f5e'};font-weight:700;">${t.status.toUpperCase()}</span></td>
                        <td style="color:#10b981;font-weight:700;">${t.stats.expanded}</td>
                        <td style="color:#c084fc;">${peakFrontier}</td>
                        <td style="color:#fbbf24;">${t.stats.length || '-'} (${t.stats.cost || '-'})</td>
                        <td>${t.stats.time_ms} MS</td>
                    </tr>
                `;
            }).join("");

            tbody.querySelectorAll("tr").forEach((row) => {
                row.addEventListener("click", () => {
                    const algo = row.dataset.algo;
                    const lIdx = this.lanes.findIndex((l) => l.trace.algorithm === algo);
                    if (lIdx !== -1) this.setActiveLane(lIdx);
                    this.closeLeaderboard();
                });
            });

            const summaryEl = this.el("bench-modal-summary");
            if (sorted.length >= 2 && sorted[0].status === "solved") {
                const diff = sorted[1].stats.expanded - sorted[0].stats.expanded;
                summaryEl.innerHTML = `&gt; 🏆 WINNER: <b style="color:#fbbf24;">${FULL_NAME[sorted[0].algorithm] || sorted[0].algorithm}</b> (TIẾT KIỆM ${diff} NODES SO VỚI TOP 2)`;
            } else {
                summaryEl.textContent = "> BENCHMARK COMPLETE";
            }

            this.el("bench-leaderboard-modal").classList.add("show");
        },

        closeLeaderboard() {
            this.el("bench-leaderboard-modal").classList.remove("show");
        },

        async open() {
            this.el("bench-overlay").classList.add("show");
            await this.loadStages();
            this.run();
        },

        close() {
            this.playing = false;
            this.closeLeaderboard();
            this.el("bench-overlay").classList.remove("show");
        },

        async loadStages() {
            try {
                const resp = await fetch("/api/event", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ event: "stage_list", payload: {} }),
                });
                const data = await resp.json();
                if (data && Array.isArray(data.stages)) {
                    this.stages = data.stages;
                    this.currentStageIdx = data.current ?? 0;
                    const select = this.el("bench-stage-select");
                    select.innerHTML = this.stages.map((st) =>
                        `<option value="${st.index}" ${st.index === this.currentStageIdx ? "selected" : ""}>${st.name}</option>`
                    ).join("");
                }
            } catch (_) { /* fallback standalone */ }
        },

        async changeStageRel(delta) {
            if (!this.stages.length) return;
            const nextIdx = (this.currentStageIdx + delta + this.stages.length) % this.stages.length;
            await this.selectStage(nextIdx);
        },

        async selectStage(idx) {
            this.currentStageIdx = idx;
            const select = this.el("bench-stage-select");
            if (select) select.value = String(idx);

            try {
                const resp = await fetch("/api/event", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ event: "select_stage", payload: { index: idx } }),
                });
                const data = await resp.json();
                if (data && data.commands && window.SceneBridge) window.SceneBridge.receiveCommands(data.commands);
            } catch (_) { /* fallback */ }

            this.run();
        },

        switchMode(mode) {
            if (this.mode === mode) return;
            this.mode = mode;
            this.el("bench-overlay").classList.toggle("compare", mode === "compare");
            this.el("bench-mode-toggle").querySelectorAll("button").forEach((b) =>
                b.classList.toggle("on", b.dataset.mode === mode));
            this.run();
        },

        message(text) {
            this.lanes = [];
            this.el("bench-body").innerHTML = `<div style="margin:auto;color:#64748b;font-size:13px;letter-spacing:1px;">&gt; ${text}</div>`;
        },

        setActiveLane(idx) {
            if (!this.lanes.length) return;
            this.activeLaneIdx = (idx + this.lanes.length) % this.lanes.length;
            const viewSelect = this.el("bench-view-select");
            if (viewSelect) viewSelect.value = String(this.activeLaneIdx);
            const viewCount = this.el("bench-view-count");
            if (viewCount) {
                viewCount.textContent = `(${this.activeLaneIdx + 1} / ${this.lanes.length})`;
            }
            const active = this.lanes[this.activeLaneIdx];
            if (active && this.view) {
                drawMap(active, this.view.canvasMap);
                drawWave(active, this.view.canvasWave);
                updateTelemetryLine(active, this.view);
            }
        },

        switchActiveLaneRel(delta) {
            if (!this.lanes.length) return;
            this.setActiveLane(this.activeLaneIdx + delta);
        },

        async run() {
            const algos = this.mode === "single" ? [this.algoSingle] : Array.from(this.selectedAlgos);
            if (!algos.length) algos.push("astar");

            this.message("ACQUIRING MULTI-ALGO SEARCH STREAMS FROM ENGINE...");

            let traces = null;
            try {
                const resp = await fetch("/api/event", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ event: "benchmark_trace", payload: { algorithms: algos } }),
                });
                const data = await resp.json();
                if (data && data.commands && window.SceneBridge) window.SceneBridge.receiveCommands(data.commands);
                traces = data && data.traces;
            } catch (_) { /* fallback standalone */ }

            if (!Array.isArray(traces) || !traces.length) {
                this.message("CANNOT ACQUIRE TRACE STREAM (REQUIRE BACKEND APP: PYTHON MAIN.PY)");
                return;
            }

            const body = this.el("bench-body");
            body.innerHTML = "";

            this.view = makeBenchView();
            body.appendChild(this.view.el);

            this.lanes = traces.map((t, idx) => makeLane(t, idx));
            this.activeLaneIdx = 0;

            // Setup viewing dropdown options in Compare mode
            const viewSelect = this.el("bench-view-select");
            if (viewSelect) {
                viewSelect.innerHTML = this.lanes.map((l, idx) =>
                    `<option value="${idx}">${FULL_NAME[l.trace.algorithm] || l.trace.algorithm}</option>`
                ).join("");
            }

            this.setActiveLane(0);
            this.reset();
            this.playing = true;
            this.renderPlay();
        },

        reset() {
            this.lanes.forEach(resetLane);
            this.shown = false;
        },

        step() {
            this.playing = false;
            this.renderPlay();
            this.lanes.forEach(stepLane);
        },

        togglePlay() {
            if (!this.lanes.length) return;
            if (this.lanes.every(isDone)) this.reset();
            this.playing = !this.playing;
            this.renderPlay();
        },

        renderPlay() {
            this.el("bench-play").textContent = this.playing ? "❚❚ PAUSE" : "▶ PLAY";
        },

        frame() {
            if (this.isOpen() && this.lanes.length && this.view) {
                if (this.playing) {
                    const rate = Math.pow(2, Number(this.el("bench-speed").value)) / 8;
                    for (const lane of this.lanes) {
                        lane.acc += rate;
                        while (lane.acc >= 1 && !isDone(lane)) { stepLane(lane); lane.acc -= 1; }
                    }
                }

                const active = this.lanes[this.activeLaneIdx] || this.lanes[0];
                if (active) {
                    drawMap(active, this.view.canvasMap);
                    drawWave(active, this.view.canvasWave);
                    updateTelemetryLine(active, this.view);
                }

                const maxI = Math.max(...this.lanes.map((l) => l.i));
                const maxTotal = Math.max(...this.lanes.map((l) => l.trace.events.length));
                const stepEl = this.el("bench-step-val");
                if (stepEl) stepEl.textContent = `${maxI} / ${maxTotal}`;

                if (!this.shown && this.lanes.every(isDone)) {
                    this.shown = true;
                    this.playing = false;
                    this.renderPlay();
                    if (this.mode === "compare") {
                        this.openLeaderboard();
                    }
                }
            }
            requestAnimationFrame(() => this.frame());
        },
    };

    window.BloxorzBench = BloxorzBench;
    BloxorzBench.mount();
})();
