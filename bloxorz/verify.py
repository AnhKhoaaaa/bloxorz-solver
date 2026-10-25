# Phụ trách: VT1 - Task 1.4
"""Xác thực lời giải của thuật toán tìm kiếm."""

from __future__ import annotations
from typing import Sequence

from bloxorz.engine import initial_state, is_goal, step
from bloxorz.model import Action
from bloxorz.stage import Stage


def verify_solution(stage: Stage, actions: Sequence[Action]) -> tuple[bool, str]:
    """
    Kiểm tra một chuỗi hành động có đưa khối từ điểm xuất phát về đích an toàn không:
    - Bắt đầu từ trạng thái initial_state(stage).
    - Duyệt qua từng action: dùng enumerate(actions) để biết số thứ tự bước i.
    - Nếu step() trả về None: trả về (False, f"bước {i}: phạm luật hoặc rơi vực").
    - Sau khi đi hết tất cả actions: kiểm tra is_goal().
      + Nếu chưa tới đích: trả về (False, "chưa tới đích").
      + Nếu đã tới đích: trả về (True, "").
    """
    curr = initial_state(stage)

    for i, action in enumerate(actions):

        if not isinstance(action, Action):
            return (False, f"Step {i}: invalid action object {action!r}")
        try:
            new_state = step(curr, action, stage)
        except Exception as e:
            dir_str = action.direction.value if hasattr(action, "direction") else "?"
            act_info = f"dir = {dir_str}, cube = {action.cube}" if getattr(action, "cube", None) is not None else f"dir = {dir_str}"
            return (False, f"Step {i} ({act_info}): engine crashed with error {e}")
        
        if new_state is None:
            dir_str = action.direction.value if hasattr(action, "direction") else "?"
            act_info = f"dir = {dir_str}, cube = {action.cube}" if getattr(action, "cube", None) is not None else f"dir = {dir_str}"
            return (False, f"Step {i} ({act_info}): Fall or violate the rules!")
        curr = new_state

    if is_goal(curr, stage):
        return (True, "")
    return (False, "Not reach the goal yet!")
