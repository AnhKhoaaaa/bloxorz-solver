"""Module luật chơi Bloxorz."""

from .rules import (
    FRAGILE_TILES,
    get_block_cells,
    initial_state,
    is_fragile_tile,
    is_goal,
    is_valid_state,
    roll_transition,
    step,
)
from .split import (
    is_adjacent,
    split_block,
    step_split,
    try_merge_cubes,
)
from .switches import (
    apply_bridge_action,
    apply_switch,
    can_activate_switch,
    trigger_switches,
)

__all__ = [
    "FRAGILE_TILES",
    "get_block_cells",
    "initial_state",
    "is_fragile_tile",
    "is_goal",
    "is_valid_state",
    "roll_transition",
    "step",
    "apply_bridge_action",
    "apply_switch",
    "can_activate_switch",
    "trigger_switches",
    "is_adjacent",
    "split_block",
    "step_split",
    "try_merge_cubes",
]
