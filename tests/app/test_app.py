"""
Kiểm thử ứng dụng trên cảnh WebGL - Task 4.2 / 4.3 / 4.5
- app.WebEventRouter: cùng chuỗi sự kiện cho kết quả y hệt bộ xử lý cũ trong SceneView.bind_controller (VT3,
  đã gỡ khỏi view.py): cùng màn, số bước, trạng thái và cùng các lệnh vẽ gửi xuống WebGL (VT3_REFERENCE).
- Từng sự kiện: lăn / rơi / thắng, đổi khối khi tách, lùi, chơi lại, đổi màn quay vòng, giải AI, lỗi solver,
  chưa có controller; app.connect_events gắn bộ xử lý vào bridge của cảnh.
- Giải AI trên cảnh WebGL thật: đủ 5 thuật toán, gửi play_solution đúng định dạng WebGL cần (steps + solver),
  controller đi theo lời giải; không giải được thì báo lý do.
- Giao diện 2D (bloxorz/gui/web/): index.html của VT3 chỉ nhúng hud.css / hud.js; hud.js chạy thật bằng Node với
  DOM giả (số màn/số bước, biome, huy hiệu AI, banner, tự sang màn sau khi thắng, phím chơi tay);
  bridge chỉ phục vụ đúng 2 file này tại /web/...
"""

import json
import re
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from bloxorz.gui.app import WebEventRouter, connect_events
from bloxorz.gui.controller import GameController
from bloxorz.loader import load_stage
from bloxorz.model import Direction

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "stages" / "fixtures"
WEB = ROOT / "bloxorz" / "gui" / "web"
INDEX = ROOT / "bloxorz" / "gui" / "scene" / "index.html"

EVENTS = [
    ("ready", {}),
    ("action", {"action": "right"}),
    ("action", {"action": "RIGHT"}),
    ("action", {"action": "jump"}),          # hướng lạ: bỏ qua
    ("undo", {}),
    ("action", {"action": "UP"}),            # rơi khỏi bàn
    ("undo", {}),
    ("restart", {}),
    ("next_stage", {}),
    ("next_stage", {}),
    ("prev_stage", {}),
    ("prev_stage", {}),
    ("prev_stage", {}),                       # quay vòng về màn cuối
    ("unknown_event", {}),
]


def stages():
    return [load_stage(FIXTURES / f"{name}.json") for name in ("fragile", "basic", "split")]


def make_scene_view():
    view = pytest.importorskip("bloxorz.gui.scene.view")
    return view.SceneView(audio_enabled=False)


# Kết quả của bộ xử lý gốc trong SceneView.bind_controller (VT3) cho EVENTS, ghi lại trước khi phần này được
# chuyển sang VT4: (sự kiện, màn, số bước, trạng thái, các lệnh vẽ gửi xuống WebGL). VT4 phải cho kết quả y hệt.
# Riêng "solve_ai" được VT4 sửa (bản cũ gửi play_solution sai định dạng nên WebGL không phát được): xem test bên dưới.
VT3_REFERENCE = [
    ("ready", 0, 0, "playing", ["load_stage"]),
    ("action", 0, 1, "playing", ["on_move"]),
    ("action", 0, 2, "playing", ["on_move"]),
    ("action", 0, 2, "playing", []),
    ("undo", 0, 1, "playing", ["load_stage"]),
    ("action", 0, 2, "fell", ["on_fall"]),
    ("undo", 0, 1, "playing", ["load_stage"]),
    ("restart", 0, 0, "playing", ["load_stage"]),
    ("next_stage", 1, 0, "playing", ["load_stage"]),
    ("next_stage", 2, 0, "playing", ["load_stage"]),
    ("prev_stage", 1, 0, "playing", ["load_stage"]),
    ("prev_stage", 0, 0, "playing", ["load_stage"]),
    ("prev_stage", 2, 0, "playing", ["load_stage"]),
    ("unknown_event", 2, 0, "playing", []),
]


def test_same_behavior_as_previous_scene_view_handler():
    scene, controller = make_scene_view(), GameController(stages())
    scene.bind_controller(controller)
    router = connect_events(scene, controller)
    assert isinstance(router, WebEventRouter)
    assert scene.bridge._event_handler == router.handle  # bridge dùng bộ xử lý của VT4

    trace = []
    for event, payload in EVENTS:
        reply = scene.bridge.handle_client_event(event, payload)  # đúng đường thật từ WebGL
        assert reply["ok"] is True
        trace.append((event, controller.index, controller.moves, controller.status,
                      [command["type"] for command in reply["commands"]]))
    assert trace == VT3_REFERENCE


def test_scene_view_no_longer_handles_events_itself():
    scene, controller = make_scene_view(), GameController(stages())
    scene.bind_controller(controller)
    assert scene.controller is controller
    assert scene.bridge._event_handler is None  # chỉ app.connect_events mới gắn bộ xử lý


class RecordingScene:
    def __init__(self):
        self.events = []

    def load_stage(self, stage, state):
        self.events.append(("load", stage.id))

    def on_move(self, old, action, new):  # Scene Protocol: action là Action (kèm cube khi tách)
        self.events.append(("move", action.direction.name, action.cube))

    def on_fall(self, old, action):
        self.events.append(("fall", action.direction.name, action.cube))

    def on_win(self, state):
        self.events.append(("win",))

    def play_solution(self, actions, delay):
        self.events.append(("play", len(actions), delay))


@pytest.fixture
def router():
    return WebEventRouter(GameController(stages()), RecordingScene())


def test_moves_fall_and_win(router):
    for _ in range(4):  # fixture_fragile: 4 lần sang phải là tới đích
        assert router.handle("action", {"action": "RIGHT"}) == {"ok": True}
    assert router.scene.events[-2:] == [("move", "RIGHT", None), ("win",)]
    router.controller.restart()
    router.handle("action", {"action": "UP"})
    assert router.scene.events[-1] == ("fall", "UP", None) and router.controller.status == "fell"


def test_space_switches_cube_when_split():
    from bloxorz.model import State

    router = WebEventRouter(GameController([load_stage(FIXTURES / "split.json")]), RecordingScene())
    controller = router.controller
    router.handle("action", {"action": "SWITCH"})
    assert controller.active_cube == 0 and router.scene.events == []  # khối chưa tách: không làm gì

    controller.state = State(None, (2, 0), (2, 3))  # khối đã tách
    router.handle("action", {"action": "RIGHT"})
    assert router.scene.events[-1] == ("move", "RIGHT", 0) and controller.state.pos == (2, 1)
    router.handle("action", {"action": "switch"})
    assert controller.active_cube == 1
    router.handle("action", {"action": "RIGHT"})
    assert router.scene.events[-1] == ("move", "RIGHT", 1) and controller.state.cube2 == (2, 4)


def test_split_stage_playable_by_hand_through_webgl_events():
    # màn tách: lăn tới công tắc tách, đổi khối, đi tiếp tới đích (chỉ bằng sự kiện như WebGL gửi lên)
    scene, controller = make_scene_view(), GameController([load_stage(FIXTURES / "split.json")])
    scene.bind_controller(controller)
    connect_events(scene, controller)
    send = lambda action: scene.bridge.handle_client_event("action", {"action": action})
    for action in ("RIGHT", "RIGHT"):  # đứng lên công tắc tách -> 2 cube
        send(action)
    assert controller.is_split
    send("SWITCH")
    assert controller.active_cube == 1
    send("SWITCH")
    for action in ("RIGHT", "RIGHT", "RIGHT", "RIGHT"):
        reply = send(action)
    assert controller.status == "won" and "on_win" in [c["type"] for c in reply["commands"]]


def selections(commands):
    return [c["payload"]["cube"] for c in commands if c["type"] == "set_selected"]


def test_webgl_receives_selected_cube_on_split_switch_and_merge():
    # Task 4.4: WebGL tô sáng cube đang điều khiển qua lệnh set_selected (SceneView.set_selected)
    scene, controller = make_scene_view(), GameController([load_stage(FIXTURES / "split.json")])
    scene.bind_controller(controller)
    connect_events(scene, controller)
    send = lambda event, action=None: scene.bridge.handle_client_event(event, {"action": action})["commands"]
    assert selections(send("action", "RIGHT")) == []                # khối nguyên: không gửi
    commands = send("action", "RIGHT")                              # event "split"
    assert [c["type"] for c in commands] == ["on_move", "set_selected"] and selections(commands) == [0]
    assert selections(send("action", "SWITCH")) == [1]              # Space: không có on_move, không tính nước
    assert controller.moves == 2
    assert selections(send("action", "RIGHT")) == [1]               # vẫn đi cube 1
    assert selections(send("undo")) == [1]                          # vẽ lại màn khi vẫn tách: báo lại
    assert selections(send("ready")) == [1]                         # trang tải lại
    send("action", "SWITCH")                                        # chọn cube 0 ở (2,0); cube 1 ở (2,2)
    commands = send("action", "RIGHT")                              # cube 0 sang (2,1) chạm cube 1: "merge"
    assert selections(commands) == [None] and controller.last_event == "merge"
    assert selections(send("restart")) == []


def test_solution_steps_carry_selected_cube():
    _, commands = solve_on("split", "astar")
    steps = commands[-1]["payload"]["steps"]
    for step in steps:
        split = step["new_state"]["pose"] == "SPLIT"
        assert (step["selected"] in (0, 1)) if split else step["selected"] is None
    assert any(step["selected"] is not None for step in steps)


def test_stage_navigation_wraps_around(router):
    router.handle("prev_stage", {})
    assert router.controller.index == 2 and router.scene.events[-1] == ("load", "fixture_split")
    router.handle("next_stage", {})
    assert router.controller.index == 0


def test_undo_only_reloads_when_something_to_undo(router):
    router.handle("undo", {})
    assert router.scene.events == []
    router.handle("action", {"action": "RIGHT"})
    router.handle("undo", {})
    assert router.scene.events[-1][0] == "load" and router.controller.moves == 0


def test_solve_ai_plays_solution_and_reports_errors(router, capsys):
    router.handle("solve_ai", {"algorithm": "BFS"})
    assert router.scene.events[-1] == ("play", 4, 0.20)

    def broken(algorithm, stage):
        raise RuntimeError("hỏng")

    router.run_fn = broken
    assert router.handle("solve_ai", {}) == {"ok": True}
    assert "[AI Solver Error]: hỏng" in capsys.readouterr().out


def test_without_controller_does_nothing():
    scene = RecordingScene()
    assert WebEventRouter(None, scene).handle("restart", {}) == {"ok": True}
    assert scene.events == []


def test_connect_events_skips_scene_without_bridge():
    assert connect_events(RecordingScene(), GameController(stages())) is None


# ---------- giải AI trên cảnh WebGL thật ----------

def solve_on(stage_name, algorithm, run_fn=None):
    scene, controller = make_scene_view(), GameController([load_stage(FIXTURES / f"{stage_name}.json")])
    scene.bind_controller(controller)
    router = connect_events(scene, controller)
    if run_fn is not None:
        router.run_fn = run_fn
    scene.bridge.handle_client_event("ready", {})
    controller.move(Direction.RIGHT)  # đang chơi dở: giải AI vẫn phát từ đầu màn
    reply = scene.bridge.handle_client_event("solve_ai", {"algorithm": algorithm})
    return controller, reply["commands"]


@pytest.mark.parametrize("algorithm", ["bfs", "dfs", "ucs", "astar", "astar_manhattan"])
@pytest.mark.parametrize("stage_name", ["basic", "split", "bridge_heavy"])
def test_solve_ai_sends_playable_solution(stage_name, algorithm):
    controller, commands = solve_on(stage_name, algorithm)
    assert [c["type"] for c in commands] == ["load_stage", "play_solution"]  # vẽ lại từ đầu màn rồi phát
    payload = commands[1]["payload"]
    steps, solver = payload["steps"], payload["solver"]
    assert solver["status"] == "solved" and solver["moves"] == len(steps) > 0
    assert solver["nodes_expanded"] > 0 and solver["execution_time_ms"] >= 0
    assert [step["moves"] for step in steps] == list(range(1, len(steps) + 1))
    assert [step["is_win"] for step in steps] == [False] * (len(steps) - 1) + [True]
    for step in steps:
        assert {"old_state", "new_state", "action", "bridges_changed"} <= step.keys()
    for prev, step in zip(steps, steps[1:]):
        assert step["old_state"] == prev["new_state"]  # các bước nối tiếp nhau
    assert controller.status == "won" and controller.moves == len(steps)  # Python khớp màn hình


def test_solve_ai_failure_reports_reason_without_moving():
    from bloxorz.search import SearchResult

    controller, commands = solve_on("basic", "bfs", run_fn=lambda a, s: SearchResult(a, s.id, "timeout", expanded=12))
    assert [c["type"] for c in commands] == ["play_solution"]
    payload = commands[0]["payload"]
    assert payload["steps"] == []
    assert payload["solver"]["status"] == "timeout" and payload["solver"]["status_text"] == "quá thời gian"
    assert controller.moves == 1 and controller.status == "playing"  # ván đang chơi giữ nguyên


def test_solve_ai_unknown_algorithm_reports_error():
    controller, commands = solve_on("basic", "khong_co")
    assert commands[0]["payload"]["solver"]["status"] == "error"


def start_slow_solve(algorithm="bfs"):
    """Màn basic rồi fragile; solver của lượt đầu dừng chờ tới khi release được set (giả lập solver chạy lâu)."""
    from bloxorz.search import run

    scene = make_scene_view()
    controller = GameController([load_stage(FIXTURES / "basic.json"), load_stage(FIXTURES / "fragile.json")])
    scene.bind_controller(controller)
    router = connect_events(scene, controller)
    started, release, calls = threading.Event(), threading.Event(), []

    def slow(name, stage):
        calls.append(stage.id)
        if len(calls) == 1:
            started.set()
            release.wait(5)
        return run(name, stage)

    router.run_fn = slow
    worker = threading.Thread(target=scene.bridge.handle_client_event, args=("solve_ai", {"algorithm": algorithm}))
    worker.start()
    assert started.wait(5)
    return scene, controller, release, worker


def test_stage_change_during_solve_drops_old_result(capsys):
    # Bridge xử lý mỗi request trên 1 luồng: đổi màn khi solver của màn cũ chưa xong
    scene, controller, release, worker = start_slow_solve()
    scene.bridge.handle_client_event("next_stage", {})
    release.set()
    worker.join(5)
    assert controller.stage.id == "fixture_fragile"
    assert controller.status == "playing" and controller.moves == 0  # lời giải của basic không được đi trên fragile
    assert all(c["type"] != "play_solution" for c in scene.bridge.drain_commands())
    assert "Bỏ kết quả bfs của màn fixture_basic" in capsys.readouterr().out


def test_newer_solve_replaces_older_one():
    scene, controller, release, worker = start_slow_solve("bfs")
    reply = scene.bridge.handle_client_event("solve_ai", {"algorithm": "astar"})  # lượt mới chạy xong trước
    played = [c for c in reply["commands"] if c["type"] == "play_solution"]
    assert played[-1]["payload"]["solver"]["algorithm"] == "A*"
    release.set()
    worker.join(5)
    assert all(c["type"] != "play_solution" for c in scene.bridge.drain_commands())  # lượt bfs cũ bị bỏ
    assert controller.status == "won"


def test_restart_during_solve_keeps_result():
    # cùng màn: lời giải vẫn hợp lệ vì luôn phát lại từ đầu màn
    scene, controller, release, worker = start_slow_solve()
    scene.bridge.handle_client_event("restart", {})
    release.set()
    worker.join(5)
    assert controller.status == "won" and controller.stage.id == "fixture_basic"


def test_index_locks_requests_while_solving():
    html = INDEX.read_text(encoding="utf-8")
    assert "this.isSolving = true;" in html and "this.isSolving = false;" in html
    for method in ("requestAction", "requestUndo", "requestRestart", "requestNextStage", "requestPrevStage"):
        body = html.split(f"    {method}(", 1)[1].split("}", 1)[0]
        assert "this.isSolving" in body, method


# ---------- giao diện 2D trên WebGL (bloxorz/gui/web/) ----------
UI_IDS = ("ui-stage-name", "ui-stage", "ui-moves", "ui-cube", "ui-ai-badge", "btn-overworld", "btn-nether", "btn-end", "banner-msg")


def test_index_delegates_ui_to_vt4_files():
    html = INDEX.read_text(encoding="utf-8")
    assert 'href="web/hud.css"' in html and 'src="web/hud.js"' in html
    touched = set(re.findall(r"getElementById\('([^']+)'\)", html))
    assert touched == {"canvas-container"}  # cảnh 3D chỉ chạm vào khung vẽ của nó
    assert "ui-layer" not in html.split("<script>", 1)[0].split("</head>", 1)[1]  # không còn HTML giao diện


def test_help_line_matches_keys():
    js = (WEB / "hud.js").read_text(encoding="utf-8")
    assert "SPACE</span> : ĐỔI KHỐI KHI TÁCH" in js and "G</span> : AI SOLVE (A*)" in js


def test_hud_has_a_solve_button_for_every_algorithm():
    js = (WEB / "hud.js").read_text(encoding="utf-8")
    for algorithm in ("astar", "bfs", "dfs", "ucs"):
        assert f"SceneBridge.requestAISolve('{algorithm}')" in js


def test_hud_markup_has_every_element_the_page_uses():
    js = (WEB / "hud.js").read_text(encoding="utf-8")
    for element_id in UI_IDS:
        assert f'id="{element_id}"' in js
    css = (WEB / "hud.css").read_text(encoding="utf-8")
    for selector in (".ui-layer", ".mc-panel", ".mc-btn", "#ui-ai-badge", "#banner-msg.show"):
        assert selector in css


NODE_HARNESS = r"""
const path = process.argv[2];
const elements = {};
function el(id) {
  if (!elements[id]) {
    const classes = new Set();
    elements[id] = { id, innerText: "", style: {}, classList: {
      add: (c) => classes.add(c), remove: (c) => classes.delete(c),
      toggle: (c, on) => (on ? classes.add(c) : classes.delete(c)), has: (c) => classes.has(c) } };
  }
  return elements[id];
}
let inserted = 0;
global.document = {
  body: { insertAdjacentHTML: () => { inserted += 1; } },
  querySelector: () => (inserted ? {} : null),
  getElementById: el,
};
global.window = global;
require(path);
window.BloxorzHud.mount();  // gọi lại: không chèn lần 2

const calls = [];
const client = { isProcessing: false, isAutoPlaying: false };
for (const m of ["requestAction", "requestUndo", "requestRestart", "requestNextStage", "requestPrevStage", "requestAISolve"]) {
  client[m] = (arg) => calls.push(arg === undefined ? m : `${m}:${arg}`);
}
const key = (k) => { let prevented = false; const handled = window.BloxorzInput.handleKey({ key: k, preventDefault: () => { prevented = true; } }, client); return [handled, prevented]; };

const H = window.BloxorzHud;
H.updateStats("STAGE 2", 2, 5, 7);
H.updateStats("", 3, 5, 8);
H.setMoves(9);
H.markBiome("nether");
H.showSolver(undefined);
const badgeBefore = el("ui-ai-badge").style.display;
H.showSolver({ algorithm: "BFS", status: "solved", moves: 7, cost: 7, execution_time_ms: 3, nodes_expanded: 48 });
const badgeText = el("ui-ai-badge").innerText, badgeShown = el("ui-ai-badge").style.display;
H.showSolver({ algorithm: "A*", status: "timeout", status_text: "quá thời gian", nodes_expanded: 900 });
const badgeFail = el("ui-ai-badge").innerText;
H.hideSolver();
H.setSelected(1); const cubeText = el("ui-cube").innerText, cubeShown = el("ui-cube").style.display;
H.setSelected(null); const cubeHidden = el("ui-cube").style.display;
H.showBanner(); const bannerShown = el("banner-msg").classList.has("show");
H.hideBanner();
H.afterWin(client);

const keys = {};
for (const k of ["ArrowLeft", "a", "D", "w", "s", "u", "r", "n", "p", " ", "G", "x"]) keys[k] = key(k);
client.isAutoPlaying = true; keys.blocked = key("w"); client.isAutoPlaying = false;
client.isSolving = true; keys.blocked3 = key("n"); client.isSolving = false;
client.isProcessing = true; keys.blocked2 = key("u");

console.log(JSON.stringify({
  inserted, stageName: el("ui-stage-name").innerText, stage: el("ui-stage").innerText, moves: el("ui-moves").innerText,
  nether: el("btn-nether").classList.has("active"), overworld: el("btn-overworld").classList.has("active"),
  badgeBefore, badgeText, badgeShown, badgeFail, badgeAfter: el("ui-ai-badge").style.display,
  bannerShown, bannerAfter: el("banner-msg").classList.has("show"), calls, keys, cubeText, cubeShown, cubeHidden,
}));
"""


@pytest.fixture(scope="module")
def hud_run(tmp_path_factory):
    node = shutil.which("node")
    if node is None:
        pytest.skip("cần Node.js để chạy thử hud.js")
    harness = tmp_path_factory.mktemp("hud") / "harness.js"
    harness.write_text(NODE_HARNESS, encoding="utf-8")
    out = subprocess.run([node, str(harness), str(WEB / "hud.js")], capture_output=True, text=True,
                         encoding="utf-8", check=True)  # Node in tiếng Việt UTF-8; Windows mặc định đọc CP1252
    return json.loads(out.stdout)


def test_hud_mounts_once_and_updates_stats(hud_run):
    assert hud_run["inserted"] == 1
    assert hud_run["stageName"] == "STAGE 2"  # tên rỗng thì giữ tên cũ
    assert hud_run["stage"] == "3/5" and hud_run["moves"] == 9


def test_hud_biome_badge_banner(hud_run):
    assert hud_run["nether"] and not hud_run["overworld"]
    assert hud_run.get("badgeBefore") in ("", None)  # không có kết quả solver thì không hiện huy hiệu (JSON bỏ undefined)
    assert hud_run["badgeShown"] == "inline-block"
    assert hud_run["badgeText"] == "BFS: 7 MOVES | COST 7 | 3ms | 48 NODES"
    assert hud_run["badgeFail"] == "A*: QUÁ THỜI GIAN | 900 NODES"
    assert hud_run["badgeAfter"] == "none"
    assert hud_run["bannerShown"] and not hud_run["bannerAfter"]


def test_hud_shows_selected_cube_when_split(hud_run):
    assert hud_run["cubeText"] == "KHỐI 2/2 · SPACE ĐỔI KHỐI" and hud_run["cubeShown"] == "inline-block"
    assert hud_run["cubeHidden"] == "none"


def test_index_renders_split_cubes_and_selection():
    html = INDEX.read_text(encoding="utf-8")
    assert "type === 'set_selected'" in html and "setSelected(cube)" in html  # nhận lệnh tô sáng từ Python
    assert "this.splitMeshes" in html and "_movingCube(oldState, newState)" in html  # 2 cube riêng, chỉ cube đi mới lăn
    assert "BloxorzHud.setSelected(" in html
    assert "this.splitMeshes[this.selected].getWorldPosition" in html  # kim cương tím (VT3) đặt theo cube Python chọn
    # đầu mỗi bước lăn khi tách: kim cương chuyển ngay lên cube đang lăn (action_cube của trạng thái cũ), không đợi lăn xong
    roll = html.split("    onMove(payload, onComplete) {", 1)[1].split("const rotAxis", 1)[0]
    assert "payload.action_cube" in roll and "this.selected = moving;" in roll
    assert roll.index("this.selected = moving;") < roll.index("this.applyStateTransform(oldState);")
    standalone = (ROOT / "standalone_browser.html").read_text(encoding="utf-8")
    assert standalone == html.replace('href="web/hud.css"', 'href="bloxorz/gui/web/hud.css"').replace(
        'src="web/hud.js"', 'src="bloxorz/gui/web/hud.js"')


def test_gameplay_keys(hud_run):
    keys = hud_run["keys"]
    assert all(keys[k] == [True, True] for k in ("ArrowLeft", "a", "D", "w", "s", "u", "r", "n", "p", " ", "G"))
    assert keys["x"] == [False, False]  # phím khác (camera/biome) để cảnh 3D xử lý
    assert keys["blocked"] == [False, False] and keys["blocked2"] == [False, False]  # đang diễn hoạt / phát lời giải
    assert keys["blocked3"] == [False, False]  # đang chờ solver: không đổi màn được
    assert hud_run["calls"] == [
        "requestNextStage",  # afterWin: thắng xong tự sang màn sau
        "requestAction:LEFT", "requestAction:LEFT", "requestAction:RIGHT", "requestAction:UP", "requestAction:DOWN",
        "requestUndo", "requestRestart", "requestNextStage", "requestPrevStage",
        "requestAction:SWITCH",  # Space: đổi khối khi tách
        "requestAISolve:astar",  # G: giải A*
    ]


def test_bridge_serves_only_vt4_web_assets():
    pytest.importorskip("bloxorz.gui.scene.bridge")
    from bloxorz.gui.scene.bridge import RendererBridge

    bridge = RendererBridge()
    base = bridge._start_local_http_server()
    try:
        for name, kind in (("hud.css", "text/css"), ("hud.js", "application/javascript")):
            with urllib.request.urlopen(f"{base}/web/{name}") as resp:
                assert resp.headers["Content-Type"].startswith(kind)
                assert resp.read() == (WEB / name).read_bytes()
        for bad in ("/web/../scene/bridge.py", "/web/%2e%2e/scene/bridge.py", "/web/nope.js"):
            with pytest.raises(urllib.error.HTTPError) as err:
                urllib.request.urlopen(base + bad)
            assert err.value.code == 404
    finally:
        bridge._http_server.shutdown()
