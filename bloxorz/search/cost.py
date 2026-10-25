# Phụ trách: VT5 - Task 5.1
"""Hàm tính chi phí di chuyển.

Hàm chi phí thống nhất theo thiết kế nhóm (bloxorz_ucs_astar_design.md §1):

    c(s, s') = 5  nếu khối sau bước đi chiếm ít nhất một ô dễ vỡ F
             = 1  trong mọi trường hợp còn lại

Quy tắc chi tiết:
- Khối nguyên vẹn  : kiểm tra TẤT CẢ ô khối chiếm SAU bước đi.
- Trạng thái tách  : chỉ kiểm tra ô MỚI mà cube ĐƯỢC ĐIỀU KHIỂN di chuyển tới;
                     cube đứng yên không được tính.
- Kích hoạt switch : bản thân việc kích hoạt không cộng phạt, trừ khi
                     quy tắc trên xác định ô đích thuộc F.

Mỗi bước cơ bản có chi phí 1; nếu điều kiện fragile thỏa, cộng thêm 4 → tổng 5.
"""

from __future__ import annotations

from bloxorz.engine import get_block_cells, is_fragile_tile, FRAGILE_TILES
from bloxorz.model import Action, Pose, State
from bloxorz.stage import Stage


def _any_fragile(stage: Stage, cells: tuple) -> bool:
    """Trả True nếu ÍT NHẤT một ô trong tập cells là fragile tile."""
    return any(is_fragile_tile(stage, p) for p in cells)


def move_cost(
    state_before: State,
    action: Action,
    state_after: State,
    stage: Stage,
) -> float:
    """Trả về chi phí của bước di chuyển từ state_before → state_after.

    Args:
        state_before: Trạng thái TRƯỚC khi thực hiện action.
        action      : Hành động vừa thực hiện.
        state_after : Trạng thái SAU khi thực hiện action (đã hợp lệ).
        stage       : Bản đồ màn chơi.

    Returns:
        1.0  — bước thông thường
        5.0  — khối sau bước đi chiếm ít nhất một ô fragile
    """
    base = 1.0
    penalty = 4.0

    # ── Trường hợp 1: khối NGUYÊN VẸN sau bước đi ──────────────────────────
    if state_after.pose is not None:
        cells = get_block_cells(state_after.pose, state_after.pos)
        return base + penalty if _any_fragile(stage, cells) else base

    # ── Trường hợp 2: trạng thái TÁCH ĐÔI sau bước đi ───────────────────────
    # Chỉ kiểm tra ô CỦA CUBE ĐƯỢC DI CHUYỂN.
    # action.cube = 0 → cube thứ nhất (state_after.pos) di chuyển
    # action.cube = 1 → cube thứ hai (state_after.cube2) di chuyển
    # None            → không xác định cube nào bị di chuyển (ví dụ: hành động
    #                   tách lần đầu) → kiểm tra cả hai để an toàn.
    if action.cube == 0:
        moved_cells = (state_after.pos,)
    elif action.cube == 1:
        moved_cells = (state_after.cube2,)
    else:
        # action.cube is None trong split state: kiểm tra cả hai cube
        moved_cells = (state_after.pos,)
        if state_after.cube2 is not None:
            moved_cells = (state_after.pos, state_after.cube2)

    return base + penalty if _any_fragile(stage, moved_cells) else base
