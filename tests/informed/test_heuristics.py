"""Kiểm tra heuristic bằng đồ thị thật và khoảng cách Dijkstra tới đích."""
from collections import defaultdict, deque
import heapq
from itertools import count
from math import inf
from pathlib import Path

import pytest

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Pose, State
from bloxorz.search.base import ORDERED_DIRECTIONS
from bloxorz.search.cost import move_cost
from bloxorz.search.heuristics import make_heuristic, relaxed_distances
from bloxorz.stage import Stage, Switch

FIXTURES = Path(__file__).parents[2] / "stages" / "fixtures"


def shortcut_stage(adjacent=False):
    return Stage(
        id="shortcut", group="G4",
        grid=("####.........",) + (".............",) * 4 + (".........G###",),
        start=(0, 0), goal=(5, 9),
        switches=(Switch(id="split", kind="split", pos=(0, 3),
                         targets=((5, 10), (5, 11 if adjacent else 12))),),
    )


def exact_remaining_costs(stage, start=None):
    """Explore all reachable states, then reverse Dijkstra (UCS) on real edges."""
    start = start if start is not None else initial_state(stage)
    seen, queue = {start}, deque([start])
    reverse, edges = defaultdict(list), []
    while queue:
        state = queue.popleft()
        if is_goal(state, stage):
            continue
        for direction in ORDERED_DIRECTIONS:
            for cube in ((0, 1) if state.pose is None else (None,)):
                action = Action(direction, cube)
                nxt = step(state, action, stage)
                if nxt is None:
                    continue
                cost = move_cost(state, action, nxt, stage)
                edges.append((state, nxt, cost))
                reverse[nxt].append((state, cost))
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    best = {s: 0.0 for s in seen if is_goal(s, stage)}
    serial = count()
    heap = [(0.0, next(serial), s) for s in best]
    heapq.heapify(heap)
    while heap:
        cost, _, state = heapq.heappop(heap)
        if cost != best[state]:
            continue
        for previous, weight in reverse[state]:
            candidate = cost + weight
            if candidate < best.get(previous, inf):
                best[previous] = candidate
                heapq.heappush(heap, (candidate, next(serial), previous))
    return seen, edges, best


@pytest.mark.parametrize("name", ("relaxed", "manhattan"))
@pytest.mark.parametrize("filename", ("basic.json", "fragile.json", "split.json", "bridge_soft.json"))
def test_admissible_and_consistent_on_every_reachable_state(name, filename):
    stage = load_stage(FIXTURES / filename)
    h = make_heuristic(stage, name)
    states, edges, optimal = exact_remaining_costs(stage)
    assert optimal  # Không để kiểm tra admissibility đúng rỗng.
    for state in states:
        assert 0 <= h(state) <= optimal.get(state, inf)
        if is_goal(state, stage):
            assert h(state) == 0
    for state, nxt, cost in edges:
        assert h(state) <= cost + h(nxt)


@pytest.mark.parametrize("name", ("relaxed", "manhattan"))
@pytest.mark.parametrize("adjacent", (False, True))
def test_teleport_and_immediate_merge_preserve_bounds(name, adjacent):
    stage = shortcut_stage(adjacent)
    h = make_heuristic(stage, name)
    states, edges, optimal = exact_remaining_costs(stage)
    assert optimal[initial_state(stage)] == (3 if adjacent else 4)
    for state in states:
        assert h(state) <= optimal.get(state, inf)
    for state, nxt, cost in edges:
        assert h(state) <= cost + h(nxt)


@pytest.mark.parametrize("case,naive_value,true_cost", ((1, 2, 1), (2, 7, 4), (3, 3, 2)))
def test_three_counterexamples_to_naive_heuristics(case, naive_value, true_cost):
    if case == 1:
        stage = Stage(id="lying", group="G1", grid=("##G",), start=(0, 0), goal=(0, 2))
        state = State(Pose.HORIZONTAL, (0, 0))
        naive = (abs(state.pos[0] - stage.goal[0]) + abs(state.pos[1] - stage.goal[1])) / 2 + 1
    elif case == 2:
        stage = shortcut_stage()
        state = initial_state(stage)
        naive = (abs(state.pos[0] - stage.goal[0]) + abs(state.pos[1] - stage.goal[1])) / 2
    else:
        stage = Stage(id="standing", group="G1", grid=("###G",), start=(0, 0), goal=(0, 3))
        state = initial_state(stage)
        naive = abs(state.pos[0] - stage.goal[0]) + abs(state.pos[1] - stage.goal[1])
    _, _, optimal = exact_remaining_costs(stage, state)
    assert naive == naive_value > true_cost == optimal[state]
    for name in ("relaxed", "manhattan"):
        assert make_heuristic(stage, name)(state) <= true_cost


def test_relaxed_board_ignores_void_fragile_bridges_and_ragged_rows():
    stage = Stage(id="relaxed", group="G1", grid=("F..G", "#", "BBBB"), start=(0, 0), goal=(0, 3))
    distances = relaxed_distances(stage, [stage.goal])
    assert distances[Pose.STANDING, (0, 0)] == 2
    assert (Pose.HORIZONTAL, (0, 3)) not in distances
    assert relaxed_distances(stage, []) == {}


def test_unknown_heuristic_is_rejected():
    with pytest.raises(ValueError, match="heuristic"):
        make_heuristic(shortcut_stage(), "typo")
