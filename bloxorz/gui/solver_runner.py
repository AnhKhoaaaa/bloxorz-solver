# Phụ trách: VT4 - Task 4.3
"""
Tiến trình chạy solver ngầm và replay lời giải.

- algorithm_names(): các thuật toán đã đăng ký trong bloxorz.search, theo thứ tự BFS, DFS, UCS, A*.
- SolverRunner: chạy search.run() trên 1 luồng nền để cửa sổ không bị treo; cancel() dừng giữa chừng
  qua Limits.cancel, nên kết quả của lần chạy đã hủy không bao giờ được trả về.
- Replayer: phát lại lời giải từ đầu màn, từng bước qua GameController + Scene; chỉ đi bước tiếp
  khi scene hết diễn hoạt và đã chờ đủ step_delay giây.
- SolverSession: trạng thái panel solver trong app (chọn thuật toán, giải, hủy, replay) và chữ hiển thị.
- solver_info() / solution_steps(): dữ liệu cho cảnh WebGL khi bấm nút giải AI (huy hiệu kết quả và các bước
  lời giải để WebGL phát lại), app.WebEventRouter gửi đi qua lệnh play_solution.

Module này KHÔNG import Ursina (giống controller.py) để test được không cần đồ họa;
app.py gọi SolverSession.handle_key() khi có phím và SolverSession.update(dt) mỗi frame.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Sequence

from bloxorz import search
from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import Scene, apply_action
from bloxorz.model import Action
from bloxorz.search import Limits, SearchResult
from bloxorz.stage import Stage

DEFAULT_TIMEOUT_S = 60.0
REPLAY_STEP_DELAY_S = 0.25
WEB_STEP_DELAY_S = 0.20  # khoảng nghỉ giữa 2 bước khi cảnh WebGL phát lời giải

PREFERRED_ORDER = ("bfs", "dfs", "ucs", "astar", "astar_manhattan")
DISPLAY_NAMES = {
    "bfs": "BFS",
    "dfs": "DFS",
    "ucs": "UCS",
    "astar": "A*",
    "astar_manhattan": "A* (Manhattan)",
}
STATUS_TEXT = {
    "solved": "có lời giải",
    "unsolvable": "không có lời giải",
    "timeout": "quá thời gian",
    "cancelled": "đã hủy",
    "error": "lỗi",
}
# Phím của panel; mọi phím khác vẫn đi vào KeyBuffer để chơi tay
SOLVER_KEYS = {"tab": "next", "g": "solve", "c": "cancel", "enter": "replay"}
SOLVER_HELP = "Tab: đổi thuật toán   G: giải   Enter: replay / tạm dừng   C: hủy"

RunFn = Callable[[str, Stage, Limits], SearchResult]


def algorithm_names() -> list[str]:
    """Tên các thuật toán đã đăng ký: theo PREFERRED_ORDER trước, tên lạ xếp sau theo abc."""
    known = [name for name in PREFERRED_ORDER if name in search.ALGORITHMS]
    return known + sorted(name for name in search.ALGORITHMS if name not in PREFERRED_ORDER)


def display_name(algorithm: str) -> str:
    return DISPLAY_NAMES.get(algorithm, algorithm)


def solver_info(result: SearchResult) -> dict[str, Any]:
    """Thông tin kết quả solver cho huy hiệu trên giao diện WebGL."""
    return {
        "algorithm": display_name(result.algorithm),
        "status": result.status,
        "status_text": STATUS_TEXT.get(result.status, result.status),
        "moves": result.length,
        "cost": round(result.cost, 2),
        "execution_time_ms": round(result.time_s * 1000, 1),
        "nodes_expanded": result.expanded,
    }


def solution_steps(controller: GameController, actions: Sequence[Action],
                   serialize_move: Callable[..., dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Cho controller đi theo lời giải từ trạng thái hiện tại (đúng cube khi tách) để Python luôn khớp màn hình,
    và trả các bước cho WebGL phát lại: serialize_move(old, action, new, moves) kèm is_win và selected
    (cube đang chọn sau bước đó để tô sáng, None khi khối chưa tách).
    Dừng ở bước không hợp lệ với luật chơi.
    """
    steps = []
    for action in actions:
        old = controller.state
        outcome = controller.play(action)
        if outcome not in ("moved", "won"):
            break
        step = serialize_move(old, action, controller.state, controller.moves)
        step["is_win"] = outcome == "won"
        step["selected"] = controller.active_cube if controller.is_split else None
        steps.append(step)
    return steps


class _Job:
    """1 lần chạy solver; luồng nền chỉ ghi vào job của chính nó."""

    def __init__(self, algorithm: str, stage_id: str) -> None:
        self.algorithm = algorithm
        self.stage_id = stage_id
        self.cancel = threading.Event()
        self.result: SearchResult | None = None
        self.started_at = time.perf_counter()
        self.thread: threading.Thread | None = None


class SolverRunner:
    """
    Chạy tối đa 1 solver mỗi lúc trên luồng nền:
    - start(algorithm, stage): hủy lần chạy cũ (nếu có) rồi chạy lần mới.
    - poll(): gọi mỗi frame, trả SearchResult đúng 1 lần khi chạy xong, còn lại trả None.
    - cancel(): báo solver dừng và bỏ luôn kết quả của lần chạy đó.
    """

    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S, run_fn: RunFn | None = None) -> None:
        self.timeout_s = timeout_s
        self._run: RunFn = run_fn or search.run
        self._job: _Job | None = None

    @property
    def running(self) -> bool:
        return self._job is not None

    @property
    def algorithm(self) -> str | None:
        return self._job.algorithm if self._job else None

    @property
    def stage_id(self) -> str | None:
        return self._job.stage_id if self._job else None

    def elapsed(self) -> float:
        return time.perf_counter() - self._job.started_at if self._job else 0.0

    def start(self, algorithm: str, stage: Stage) -> None:
        self.cancel()
        job = _Job(algorithm, stage.id)
        limits = Limits(timeout_s=self.timeout_s, cancel=job.cancel)

        def work() -> None:
            job.result = self._run(algorithm, stage, limits)

        job.thread = threading.Thread(target=work, name=f"solver-{algorithm}", daemon=True)
        self._job = job
        job.thread.start()

    def cancel(self) -> bool:
        """Trả False nếu không có gì đang chạy."""
        if self._job is None:
            return False
        self._job.cancel.set()
        self._job = None
        return True

    def poll(self) -> SearchResult | None:
        job = self._job
        if job is None or job.result is None:
            return None
        self._job = None
        return job.result

    def wait(self, timeout: float | None = None) -> None:
        """Chờ lần chạy hiện tại xong (dùng trong test; app thì gọi poll() mỗi frame)."""
        if self._job is not None and self._job.thread is not None:
            self._job.thread.join(timeout)


class Replayer:
    """Phát lại actions từ đầu màn hiện tại của controller."""

    def __init__(
        self,
        controller: GameController,
        scene: Scene,
        actions: Sequence[Action],
        step_delay: float = REPLAY_STEP_DELAY_S,
    ) -> None:
        self.controller = controller
        self.scene = scene
        self.actions = tuple(actions)
        self.step_delay = step_delay
        self.index = 0
        self.paused = False
        self._waited = 0.0
        controller.restart()
        scene.load_stage(controller.stage, controller.state)

    @property
    def done(self) -> bool:
        return self.index >= len(self.actions) or self.controller.status != "playing"

    def tick(self, dt: float) -> str | None:
        """Gọi mỗi frame. Trả kết quả bước vừa đi ("moved" | "won" | "fell" | ...) hoặc None."""
        if self.done or self.paused or self.scene.is_animating():
            return None
        self._waited += dt
        if self._waited < self.step_delay:
            return None
        self._waited = 0.0
        action = self.actions[self.index]
        self.index += 1
        return apply_action(self.controller, self.scene, action)


class SolverSession:
    """
    Panel solver của app:
    - Tab đổi thuật toán, G giải màn hiện tại (luôn từ vị trí xuất phát), C hủy giải / dừng replay.
    - Enter: phát lời giải vừa tìm được từ đầu màn; đang phát thì tạm dừng / chạy tiếp.
    - Trong lúc replay, phím chơi tay bị chặn để không lệch với lời giải.
    - Đổi màn (N/P) khi đang giải thì hủy lần giải đó; kết quả của màn cũ bị bỏ.
    """

    def __init__(
        self,
        controller: GameController,
        scene: Scene,
        runner: SolverRunner | None = None,
        algorithms: Sequence[str] | None = None,
        step_delay: float = REPLAY_STEP_DELAY_S,
    ) -> None:
        self.controller = controller
        self.scene = scene
        self.runner = runner or SolverRunner()
        self.algorithms = list(algorithms) if algorithms is not None else algorithm_names()
        self.step_delay = step_delay
        self.selected = 0
        self.result: SearchResult | None = None
        self.replayer: Replayer | None = None
        self.message = ""

    @property
    def algorithm(self) -> str | None:
        return self.algorithms[self.selected] if self.algorithms else None

    @property
    def solving(self) -> bool:
        return self.runner.running

    @property
    def replaying(self) -> bool:
        return self.replayer is not None

    def handle_key(self, key: str) -> bool:
        """Trả True nếu panel đã dùng phím (app không chuyển phím đó cho KeyBuffer nữa)."""
        command = SOLVER_KEYS.get(key)
        if command == "next":
            if self.algorithms and not self.solving:
                self.selected = (self.selected + 1) % len(self.algorithms)
                self.message = ""
        elif command == "solve":
            self.solve()
        elif command == "cancel":
            self.cancel()
        elif command == "replay":
            self.toggle_replay()
        else:
            return self.replaying
        return True

    def solve(self) -> None:
        if self.algorithm is None:
            self.message = "Chưa có thuật toán nào được đăng ký"
            return
        self.replayer = None
        self.result = None
        self.message = ""
        self.runner.start(self.algorithm, self.controller.stage)

    def cancel(self) -> None:
        running = self.runner.algorithm
        if self.runner.cancel():
            self.message = f"Đã hủy {display_name(running or '')}"
        elif self.replayer is not None:
            self.replayer = None
            self.message = "Đã dừng replay"

    def toggle_replay(self) -> None:
        if self.replayer is not None:
            self.replayer.paused = not self.replayer.paused
            return
        if self.result is None or self.result.status != "solved":
            self.message = "Chưa có lời giải để replay (nhấn G để giải)"
            return
        self.message = ""
        self.replayer = Replayer(self.controller, self.scene, self.result.actions, self.step_delay)

    def update(self, dt: float) -> bool:
        """Gọi mỗi frame. Trả True khi chữ trên panel/HUD cần vẽ lại."""
        changed = False
        stage_id = self.controller.stage.id
        if self.runner.running and self.runner.stage_id != stage_id:
            self.runner.cancel()
            changed = True
        if self.result is not None and self.result.stage_id != stage_id:
            self.result = None
            self.replayer = None
            changed = True

        result = self.runner.poll()
        if result is not None:
            self.result = result
            changed = True

        if self.replayer is not None:
            if self.replayer.tick(dt) is not None:
                changed = True
            if self.replayer.done and not self.scene.is_animating():
                if self.controller.status != "won":
                    self.message = "Replay không tới đích, lời giải có thể sai"
                self.replayer = None
                changed = True
        return changed

    def text(self) -> str:
        """Nội dung panel: thuật toán đang chọn, trạng thái giải/replay, thống kê lời giải."""
        name = display_name(self.algorithm) if self.algorithm else "-"
        lines = [f"Solver: {name}   ({len(self.algorithms)} thuật toán)"]
        if self.solving:
            lines.append(f"Đang giải bằng {display_name(self.runner.algorithm or '')}... {self.runner.elapsed():.1f}s")
        elif self.result is not None:
            r = self.result
            line = f"{display_name(r.algorithm)}: {STATUS_TEXT.get(r.status, r.status)}"
            if r.status == "solved":
                line += f", {r.length} bước, cost {r.cost:g}"
            elif r.message:
                line += f" ({r.message})"
            line += f", mở {r.expanded} nút, {r.time_s:.3f}s"
            lines.append(line)
        if self.replayer is not None:
            state = "tạm dừng" if self.replayer.paused else "đang phát"
            lines.append(f"Replay {self.replayer.index}/{len(self.replayer.actions)} ({state})")
        if self.message:
            lines.append(self.message)
        lines.append(SOLVER_HELP)
        return "\n".join(lines)
