from pathlib import Path

import pytest

from bloxorz.engine import initial_state, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction
from bloxorz.search.base import SearchContext, run
from bloxorz.search.cost import move_cost
from bloxorz.search.ucs import ucs
from bloxorz.stage import Stage


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


def test_ucs_returns_none_when_stage_is_unsolvable():
    stage = Stage(
        id="unsolvable",
        group="G1",
        grid=("#.G",),
        start=(0, 0),
        goal=(0, 2),
    )

    assert ucs(stage, SearchContext()) is None
