"""
Kiểm thử panel solver + replay - Task 4.3
- algorithm_names: lấy từ bloxorz.search, đúng thứ tự BFS, DFS, UCS, A*.
- SolverRunner: chạy nền, trả kết quả 1 lần, hủy được và bỏ kết quả của lần đã hủy.
- Replayer / apply_action: phát lại lời giải tới đích, kể cả khi khối tách; chờ hoạt ảnh và step_delay.
- SolverSession: phím Tab/G/Enter/C, chặn chơi tay khi replay, bỏ kết quả khi đổi màn.
"""

import threading
from pathlib import Path

import pytest

from bloxorz import search
from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import FakeScene, apply_action
from bloxorz.gui.solver_runner import (
    Replayer,
    SolverRunner,
    SolverSession,
    algorithm_names,
    display_name,
)
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, State
from bloxorz.search import SearchResult

FIXTURES = Path(__file__).resolve().parents[2] / "stages" / "fixtures"


def fixture(name):
    return load_stage(FIXTURES / f"{name}.json")


def solve(stage, algorithm="bfs"):
    result = search.run(algorithm, stage)
    assert result.status == "solved"
    return result


def replay_all(replayer, max_frames=1000):
    for _ in range(max_frames):
        if replayer.done:
            return
        replayer.tick(1.0)
    raise AssertionError("replay did not finish")


# ---------- algorithm_names ----------

def test_algorithm_names_follow_preferred_order():
    names = algorithm_names()
    assert set(names) == set(search.ALGORITHMS)
    known = [n for n in ("bfs", "dfs", "ucs", "astar", "astar_manhattan") if n in names]
    assert names[:len(known)] == known
    assert display_name("astar") == "A*" and display_name("lạ") == "lạ"


# ---------- SolverRunner ----------

def test_runner_returns_result_once():
    runner = SolverRunner()
    runner.start("bfs", fixture("basic"))
    assert runner.running and runner.algorithm == "bfs"
    runner.wait(5)
    result = runner.poll()
    assert result.status == "solved" and result.stage_id == "fixture_basic"
    assert runner.poll() is None and not runner.running


def blocking_run(started):
    """run_fn giả: chạy tới khi bị hủy, giống solver thật gọi ctx.tick()."""
    def run(algorithm, stage, limits):
        started.set()
        limits.cancel.wait(5)
        return SearchResult(algorithm, stage.id, "cancelled")
    return run


def test_runner_cancel_drops_result():
    started = threading.Event()
    runner = SolverRunner(run_fn=blocking_run(started))
    runner.start("bfs", fixture("basic"))
    started.wait(5)
    job = runner._job
    assert runner.cancel() and not runner.running
    job.thread.join(5)
    assert not job.thread.is_alive()  # solver đã nhận cờ hủy và dừng
    assert runner.poll() is None
    assert not runner.cancel()


def test_runner_restart_ignores_old_job():
    started = threading.Event()
    calls = []

    def run(algorithm, stage, limits):
        calls.append(algorithm)
        if algorithm == "slow":
            return blocking_run(started)(algorithm, stage, limits)
        return SearchResult(algorithm, stage.id, "solved")

    runner = SolverRunner(run_fn=run)
    runner.start("slow", fixture("basic"))
    started.wait(5)
    runner.start("fast", fixture("basic"))
    runner.wait(5)
    assert runner.poll().algorithm == "fast"
    assert calls == ["slow", "fast"]


def test_runner_passes_timeout():
    seen = []
    runner = SolverRunner(timeout_s=3.5, run_fn=lambda a, s, limits: seen.append(limits) or SearchResult(a, s.id, "solved"))
    runner.start("bfs", fixture("basic"))
    runner.wait(5)
    assert seen[0].timeout_s == 3.5 and seen[0].cancel is not None


# ---------- Replayer / apply_action ----------

@pytest.mark.parametrize("name", ["basic", "split", "bridge_soft", "bridge_heavy", "fragile"])
def test_replay_solution_reaches_goal(name):
    stage = fixture(name)
    result = solve(stage)
    game, scene = GameController([stage]), FakeScene()
    game.move(Direction.RIGHT)  # đang chơi dở: replay vẫn bắt đầu lại từ đầu màn
    replayer = Replayer(game, scene, result.actions, step_delay=0)
    assert game.moves == 0 and scene.events[-1][0] == "load"
    replay_all(replayer)
    assert game.status == "won" and game.moves == result.length
    assert scene.events[-1] == ("win", game.state)


def test_apply_action_moves_requested_cube():
    game, scene = GameController([fixture("split")]), FakeScene()
    game.state = State(None, (2, 0), (2, 3))
    assert apply_action(game, scene, Action(Direction.RIGHT, cube=1)) == "moved"
    assert game.last_action == Action(Direction.RIGHT, cube=1)
    assert game.state.cube2 == (2, 4) and scene.events[-2][0] == "move"
    assert scene.events[-1] == ("selected", 1)  # scene tô sáng cube vừa đi


def test_replayer_waits_for_animation_and_delay():
    stage = fixture("basic")
    game, scene = GameController([stage]), FakeScene()
    replayer = Replayer(game, scene, solve(stage).actions, step_delay=0.25)
    assert replayer.tick(0.1) is None and replayer.index == 0
    assert replayer.tick(0.2) == "moved" and replayer.index == 1
    scene.animating = True
    assert replayer.tick(1.0) is None and replayer.index == 1
    scene.animating = False
    replayer.paused = True
    assert replayer.tick(1.0) is None
    replayer.paused = False
    assert replayer.tick(1.0) == "moved" and replayer.index == 2


# ---------- SolverSession ----------

@pytest.fixture
def session():
    stages = [fixture("basic"), fixture("split")]
    return SolverSession(GameController(stages), FakeScene(), algorithms=["bfs", "astar"], step_delay=0)


def finish_solve(session):
    session.runner.wait(5)
    session.update(0)


def test_session_tab_cycles_algorithms(session):
    assert session.algorithm == "bfs"
    assert session.handle_key("tab") and session.algorithm == "astar"
    assert session.handle_key("tab") and session.algorithm == "bfs"


def test_session_solve_then_replay(session):
    assert session.handle_key("g") and session.solving
    finish_solve(session)
    assert session.result.status == "solved" and not session.solving
    assert "BFS: có lời giải, 7 bước" in session.text()

    assert session.handle_key("enter") and session.replaying
    assert session.handle_key("d")  # chơi tay / đổi màn bị chặn khi replay
    assert session.handle_key("n") and session.controller.index == 0
    for _ in range(100):
        session.update(1.0)
        if not session.replaying:
            break
    assert session.controller.status == "won" and not session.replaying
    assert not session.handle_key("d")  # replay xong thì chơi tay lại được


def test_session_enter_pauses_and_c_stops_replay(session):
    session.handle_key("g")
    finish_solve(session)
    session.handle_key("enter")
    session.update(1.0)
    session.handle_key("enter")
    assert session.replayer.paused and "tạm dừng" in session.text()
    index = session.replayer.index
    session.update(1.0)
    assert session.replayer.index == index
    session.handle_key("c")
    assert not session.replaying and session.message == "Đã dừng replay"


def test_session_replay_without_result(session):
    session.handle_key("enter")
    assert not session.replaying and "nhấn G" in session.message


def test_session_cancel_while_solving(session):
    started = threading.Event()
    session.runner = SolverRunner(run_fn=blocking_run(started))
    session.handle_key("g")
    started.wait(5)
    assert "Đang giải bằng BFS" in session.text()
    session.handle_key("tab")
    assert session.algorithm == "bfs"  # không đổi thuật toán khi đang giải
    session.handle_key("c")
    assert not session.solving and session.message == "Đã hủy BFS"


def test_session_drops_result_when_stage_changes(session):
    session.handle_key("g")
    finish_solve(session)
    session.controller.next_stage()
    assert session.update(0) and session.result is None

    started = threading.Event()
    session.runner = SolverRunner(run_fn=blocking_run(started))
    session.handle_key("g")
    started.wait(5)
    session.controller.prev_stage()
    session.update(0)
    assert not session.solving


def test_session_reports_failed_status(session):
    session.runner = SolverRunner(run_fn=lambda a, s, limits: SearchResult(a, s.id, "timeout", expanded=9))
    session.handle_key("g")
    finish_solve(session)
    assert "BFS: quá thời gian, mở 9 nút" in session.text()
    session.handle_key("enter")
    assert not session.replaying
