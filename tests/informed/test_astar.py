from pathlib import Path
import importlib
import threading

import pytest

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.search.base import Limits, SearchContext, run
from bloxorz.stage import Bridge, Stage, Switch
from tests.informed.test_heuristics import shortcut_stage

ROOT = Path(__file__).parents[2]
STAGES = sorted((ROOT / "stages" / "fixtures").glob("*.json")) + sorted(
    (ROOT / "stages" / "bench").rglob("*.json")
) + sorted((ROOT / "stages" / "original").glob("*.json"))


@pytest.mark.parametrize("path", STAGES, ids=lambda p: p.stem)
@pytest.mark.parametrize("algorithm", ("astar", "astar_manhattan"))
def test_matches_ucs_cost_and_replays_to_goal(path, algorithm):
    stage = load_stage(path)
    reference = run("ucs", stage)
    result = run(algorithm, stage)
    assert result.status == reference.status
    assert result.status in ("solved", "unsolvable")
    assert result.cost == reference.cost
    if result.status == "unsolvable":
        return
    state = initial_state(stage)
    for action in result.actions:
        state = step(state, action, stage)
        assert state is not None
    assert is_goal(state, stage)


@pytest.mark.parametrize("algorithm", ("astar", "astar_manhattan"))
def test_split_shortcut_is_optimal_and_deterministic(algorithm):
    stage = shortcut_stage()
    results = [run(algorithm, stage) for _ in range(3)]
    assert all(r.status == "solved" and r.cost == 4 for r in results)
    assert all(r.actions == results[0].actions and r.expanded == results[0].expanded for r in results)


@pytest.mark.parametrize("algorithm", ("astar", "astar_manhattan"))
def test_unsolvable_and_already_at_goal(algorithm):
    blocked = Stage(id="blocked", group="G1", grid=("#.G",), start=(0, 0), goal=(0, 2))
    assert run(algorithm, blocked).status == "unsolvable"
    done = Stage(id="done", group="G1", grid=("G",), start=(0, 0), goal=(0, 0))
    result = run(algorithm, done)
    assert result.status == "solved" and result.actions == () and result.cost == 0


@pytest.mark.parametrize("algorithm", ("astar", "astar_manhattan"))
def test_cancellation(algorithm):
    cancel = threading.Event()
    cancel.set()
    assert run(algorithm, shortcut_stage(), Limits(cancel=cancel)).status == "cancelled"


def test_reopens_a_state_reached_later_with_lower_cost(monkeypatch):
    module = importlib.import_module("bloxorz.search.astar")
    start, first, second, goal = [State(Pose.STANDING, (0, i)) for i in range(4)]
    up, down = Action(Direction.UP), Action(Direction.DOWN)
    graph = {
        (start, up): (first, 3), (start, down): (second, 1),
        (second, up): (first, 1), (first, up): (goal, 3),
    }
    monkeypatch.setattr(module, "initial_state", lambda stage: start)
    monkeypatch.setattr(module, "is_goal", lambda state, stage: state == goal)
    monkeypatch.setattr(module, "step", lambda s, a, stage: graph.get((s, a), (None, 0))[0])
    monkeypatch.setattr(module, "move_cost", lambda s, a, nxt, stage: graph[s, a][1])
    # Admissible nhưng inconsistent: first mở rộng trước second, rồi cần mở lại.
    h = {start: 0, first: 0, second: 4, goal: 0}
    assert module.best_first(shortcut_stage(), SearchContext(), h.__getitem__) == (down, up, up)


def test_bridge_states_remain_distinct_during_search():
    stage = Stage(
        id="bridge_revisit", group="G3", grid=("######G", "#######", "#######"),
        start=(0, 0), goal=(0, 6),
        bridges=(Bridge("wall", ((0, 4), (1, 4), (2, 4))),),
        switches=(Switch("open", "soft", (2, 1), mode="permanent", bridges=("wall",)),),
    )
    reference = run("ucs", stage)
    assert reference.status == "solved"
    for algorithm in ("astar", "astar_manhattan"):
        result = run(algorithm, stage)
        assert result.status == "solved" and result.cost == reference.cost


def test_equal_f_prefers_lower_h_before_insertion_order(monkeypatch):
    module = importlib.import_module("bloxorz.search.astar")
    start, detour, goal = [State(Pose.STANDING, (0, i)) for i in range(3)]
    up, down = Action(Direction.UP), Action(Direction.DOWN)
    graph = {(start, up): (detour, 1), (start, down): (goal, 2)}
    monkeypatch.setattr(module, "initial_state", lambda stage: start)
    monkeypatch.setattr(module, "is_goal", lambda state, stage: state == goal)
    monkeypatch.setattr(module, "step", lambda s, a, stage: graph.get((s, a), (None, 0))[0])
    monkeypatch.setattr(module, "move_cost", lambda s, a, nxt, stage: graph[s, a][1])
    h = {start: 2, detour: 1, goal: 0}
    ctx = SearchContext()
    assert module.best_first(shortcut_stage(), ctx, h.__getitem__) == (down,)
    # Cả hai nhánh có f=2; goal được sinh sau nhưng h nhỏ hơn, bỏ qua detour.
    assert ctx.expanded == 2


@pytest.mark.parametrize("algorithm", ("astar", "astar_manhattan"))
@pytest.mark.parametrize("measure_memory", (False, True))
def test_timing_separates_preparation_and_search(monkeypatch, algorithm, measure_memory):
    module = importlib.import_module("bloxorz.search.astar")
    base = importlib.import_module("bloxorz.search.base")
    clock = [0.0]
    calls = [0]

    def prepare(stage, name):
        calls[0] += 1
        clock[0] += 2.0 * calls[0]
        return lambda state: 0.0

    def search(stage, ctx, heuristic):
        clock[0] += 3.0 * calls[0]
        return ()

    monkeypatch.setattr(base.time, "perf_counter", lambda: clock[0])
    monkeypatch.setattr(module, "make_heuristic", prepare)
    monkeypatch.setattr(module, "best_first", search)
    result = run(algorithm, shortcut_stage(), measure_memory=measure_memory)
    assert result.status == "solved"
    assert result.prep_time_s == 2.0
    assert result.search_time_s == 3.0
    assert result.time_s == 5.0
