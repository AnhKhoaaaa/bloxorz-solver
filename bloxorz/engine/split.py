# Phụ trách: VT2 - Task 2.4
"""
Cơ chế công tắc phân tách (split switch), điều khiển từng khối cube 1x1x1 độc lập, và ghép khối.

Quy tắc theo Section 2.5 của đồ án Bloxorz:
- Split switch (hình ngoặc "( )"):
  * Chỉ kích hoạt khi khối nguyên vẹn ở tư thế ĐỨNG THẲNG (STANDING) trên ô công tắc.
  * Khi kích hoạt, khối lập tức phân tách và dịch chuyển thành hai khối lập phương đơn lẻ
    1x1x1 tại hai vị trí mục tiêu định trước (switch.targets).
- Điều khiển từng khối cube:
  * Khi đang ở trạng thái phân tách (state.pose is None), mỗi bước đi người chơi điều khiển
    một khối cube di chuyển 1 ô theo 4 hướng (UP, DOWN, LEFT, RIGHT).
  * Khối cube đơn lẻ có thể kích hoạt công tắc mềm (soft switch), nhưng KHÔNG thể kích hoạt
    công tắc nặng (heavy switch) hay hoàn thành màn chơi (rơi vào lỗ đích 'G' là thua).
  * Khối cube đơn lẻ có thể đi an toàn trên các ô gạch dễ vỡ (fragile tiles 'F').
  * Hai cube không thể di chuyển đè lên cùng một ô.
- Ghép khối (Rejoining / Merging):
  * Khi hai khối cube di chuyển đến hai vị trí kề cạnh nhau (chung cạnh theo hàng hoặc cột),
    chúng sẽ tự động ghép lại thành khối chuẩn 1x1x2:
    - Kề nhau cùng hàng: ghép thành khối nằm ngang (Pose.HORIZONTAL).
    - Kề nhau cùng cột: ghép thành khối nằm dọc (Pose.VERTICAL).
"""

from __future__ import annotations
from typing import Sequence

from bloxorz.model import Action, Direction, Pose, Pos, State
from bloxorz.stage import Stage, Switch
from .switches import trigger_switches


def is_adjacent(p1: Pos, p2: Pos) -> bool:
    """
    Kiểm tra hai tọa độ ô có kề nhau (chung cạnh 4 hướng) trên mặt phẳng hay không:
    - Kề ngang: cùng hàng và cách nhau đúng 1 cột.
    - Kề dọc: cùng cột và cách nhau đúng 1 hàng.
    """
    r1, c1 = p1
    r2, c2 = p2
    return (r1 == r2 and abs(c1 - c2) == 1) or (c1 == c2 and abs(r1 - r2) == 1)


def try_merge_cubes(p1: Pos, p2: Pos, bridges_open: frozenset[str]) -> State | None:
    """
    Kiểm tra xem hai vị trí p1 và p2 có kề nhau hay không để tự động ghép lại:
    - Nếu kề ngang (cùng hàng): ghép thành khối nằm ngang (HORIZONTAL),
      tọa độ gốc là ô bên trái (r, min(c1, c2)).
    - Nếu kề dọc (cùng cột): ghép thành khối nằm dọc (VERTICAL),
      tọa độ gốc là ô phía trên (min(r1, r2), c).
    - Nếu không kề nhau: trả về None.
    """
    r1, c1 = p1
    r2, c2 = p2

    if r1 == r2 and abs(c1 - c2) == 1:
        # Kề ngang -> HORIZONTAL
        pos = (r1, min(c1, c2))
        return State(
            pose=Pose.HORIZONTAL,
            pos=pos,
            cube2=None,
            bridges_open=bridges_open,
        )

    if c1 == c2 and abs(r1 - r2) == 1:
        # Kề dọc -> VERTICAL
        pos = (min(r1, r2), c1)
        return State(
            pose=Pose.VERTICAL,
            pos=pos,
            cube2=None,
            bridges_open=bridges_open,
        )

    return None


def split_block(stage: Stage, state: State, switch: Switch) -> State | None:
    """
    Kích hoạt phân tách khối khi khối nguyên vẹn đứng thẳng trên ô split switch:
    - Dịch chuyển 2 cube đến hai vị trí switch.targets.
    - Kiểm tra an toàn của 2 vị trí mục tiêu.
    - Kích hoạt soft switch nếu có tại 2 vị trí mục tiêu (theo thứ tự tọa độ tăng dần).
    - Tự động ghép lại nếu 2 vị trí mục tiêu kề nhau.
    - Trả về State mới (tách hoặc ghép) hoặc None nếu không hợp lệ.
    """
    if state.pose != Pose.STANDING or switch.kind != "split" or state.pos != switch.pos:
        return None
    if switch.targets is None or len(switch.targets) != 2:
        return None

    t1, t2 = switch.targets

    # 1. Kiểm tra hai vị trí mục tiêu không được trùng nhau
    if t1 == t2:
        return None

    # 2. Kiểm tra tính an toàn của hai vị trí mục tiêu với trạng thái cầu hiện tại
    for p in (t1, t2):
        if not stage.in_bounds(p):
            return None
        ch = stage.cell(p)
        if ch == "." or ch == "G":
            return None
        if p in stage.bridge_at:
            bridge_id = stage.bridge_at[p]
            if bridge_id not in state.bridges_open:
                return None

    # 3. Kích hoạt soft switch nếu có tại các ô mục tiêu (theo thứ tự tọa độ nhất quán)
    ordered_targets = (t1, t2) if t1 < t2 else (t2, t1)
    new_bridges = trigger_switches(stage, None, ordered_targets, state.bridges_open)

    # 4. Kiểm tra xem 2 vị trí mục tiêu có kề nhau để tự động ghép lại không
    merged = try_merge_cubes(t1, t2, new_bridges)
    if merged is not None:
        from .rules import is_valid_state
        if not is_valid_state(merged, stage):
            return None
        return merged

    # 5. Tạo trạng thái phân tách 2 cube
    split_state = State(
        pose=None,
        pos=t1,
        cube2=t2,
        bridges_open=new_bridges,
    )

    from .rules import is_valid_state
    if not is_valid_state(split_state, stage):
        return None

    return split_state


def step_split(state: State, action: Action, stage: Stage) -> State | None:
    """
    Thực hiện 1 bước di chuyển khi khối đang ở trạng thái phân tách thành 2 cube 1x1x1:
    - action.cube: bắt buộc phải chỉ định cube di chuyển (0 hoặc 1). Nếu None hoặc không hợp lệ -> trả về None.
    - action.direction: hướng di chuyển (UP, DOWN, LEFT, RIGHT).
    - Kiểm tra va chạm với cube còn lại.
    - Kiểm tra ô đích an toàn (biên, void, cầu đóng, không rơi vào Goal).
    - Kích hoạt soft switch nếu có tại ô đích.
    - Tự động ghép lại thành khối 1x1x2 nếu 2 cube kề nhau.
    - Trả về State mới hoặc None nếu bước đi không hợp lệ / thua.
    """
    if state.pose is not None or state.cube2 is None:
        return None

    # Ở trạng thái phân tách, action bắt buộc phải chỉ định rõ cube (0 hoặc 1)
    if action.cube not in (0, 1):
        return None

    moving_cube = action.cube

    if moving_cube == 0:
        p_moving = state.pos
        p_other = state.cube2
    else:
        p_moving = state.cube2
        p_other = state.pos

    # Xác định độ dời theo hướng di chuyển
    direction_deltas = {
        Direction.UP: (-1, 0),
        Direction.DOWN: (1, 0),
        Direction.LEFT: (0, -1),
        Direction.RIGHT: (0, 1),
    }
    dr, dc = direction_deltas[action.direction]
    new_p = (p_moving[0] + dr, p_moving[1] + dc)

    # 1. Kiểm tra va chạm: không được đi vào cùng ô với cube còn lại
    if new_p == p_other:
        return None

    # 2. Kiểm tra tính an toàn của ô mới (với trạng thái cầu hiện tại)
    if not stage.in_bounds(new_p):
        return None

    ch = stage.cell(new_p)
    # Cube đơn rơi vào void '.' hoặc rơi vào lỗ Goal 'G' là thua
    if ch == "." or ch == "G":
        return None

    # Cầu đóng coi như void
    if new_p in stage.bridge_at:
        bridge_id = stage.bridge_at[new_p]
        if bridge_id not in state.bridges_open:
            return None

    # 3. Kích hoạt soft switch nếu có tại ô mới
    new_bridges = trigger_switches(stage, None, (new_p,), state.bridges_open)

    # 4. Kiểm tra lại an toàn cho cube còn lại (phòng trường hợp công tắc làm sập cầu dưới chân cube kia)
    if not stage.in_bounds(p_other) or stage.cell(p_other) in (".", "G"):
        return None
    if p_other in stage.bridge_at:
        other_bridge_id = stage.bridge_at[p_other]
        if other_bridge_id not in new_bridges:
            return None

    # 5. Kiểm tra tự động ghép khối nếu 2 cube kề nhau
    merged = try_merge_cubes(new_p, p_other, new_bridges)
    if merged is not None:
        from .rules import is_valid_state
        if not is_valid_state(merged, stage):
            return None
        return merged

    # 6. Giữ nguyên trạng thái phân tách
    new_state = State(
        pose=None,
        pos=new_p,
        cube2=p_other,
        bridges_open=new_bridges,
    )

    from .rules import is_valid_state
    if not is_valid_state(new_state, stage):
        return None

    return new_state
