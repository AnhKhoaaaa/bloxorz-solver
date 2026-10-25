from pathlib import Path

import pytest

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction
from bloxorz.search.base import SearchContext, run
from bloxorz.search.cost import move_cost
from bloxorz.search.ucs import ucs
from bloxorz.stage import Stage, Switch


FIXTURES = Path(__file__).parents[2] / "stages" / "fixtures"


def test_move_cost_for_normal_and_fragile_tiles():
    stage = load_stage(FIXTURES / "fragile.json")
    right = Action(Direction.RIGHT)

    start = initial_state(stage)
    on_fragile = step(start, right, stage)
    assert on_fragile is not None
    assert move_cost(start, right, on_fragile, stage) == 5.0

    on_normal = step(on_fragile, right, stage)
    assert on_normal is not None
    assert move_cost(on_fragile, right, on_normal, stage) == 1.0


@pytest.mark.parametrize(
    ("filename", "expected_length", "expected_cost"),
    (
        ("basic.json", 7, 7.0),
        ("fragile.json", 4, 12.0),
        ("split.json", 6, 6.0),
    ),
)
def test_ucs_solves_fixture_with_optimal_length_and_cost(
    filename,
    expected_length,
    expected_cost,
):
    stage = load_stage(FIXTURES / filename)

    result = run("ucs", stage)

    assert result.status == "solved"
    assert result.length == expected_length
    assert result.cost == expected_cost


@pytest.mark.parametrize("moving_cube", (0, 1))
def test_ucs_moves_either_cube_and_merges_before_reaching_goal(moving_cube):
    # Hai vùng sàn cách biệt: bắt buộc tách để tới vùng có đích.
    # Hai cube phải ghép đúng vị trí để khối đi vào hành lang dọc tới đích.
    targets = ((2, 0), (2, 3)) if moving_cube == 0 else ((2, 3), (2, 6))
    stage = Stage(
        id=f"split_cube_{moving_cube}",
        group="G3",
        grid=("####...", ".......", "#######", "...#...", "...#...", "...G..."),
        start=(0, 0),
        goal=(5, 3),
        switches=(Switch(id="split", kind="split", pos=(0, 3), targets=targets),),
    )

    result = run("ucs", stage)

    assert result.status == "solved"
    assert result.length == 7
    assert result.cost == 7.0
    state = initial_state(stage)
    split_actions = []
    for action in result.actions:
        if state.pose is None:
            split_actions.append(action)
        else:
            assert action.cube is None
        state = step(state, action, stage)
        assert state is not None
    assert split_actions
    assert any(action.cube == moving_cube for action in split_actions)
    assert is_goal(state, stage)


def test_ucs_returns_none_when_stage_is_unsolvable():
    stage = Stage(
        id="unsolvable",
        group="G1",
        grid=("#.G",),
        start=(0, 0),
        goal=(0, 2),
    )

    assert ucs(stage, SearchContext()) is None
