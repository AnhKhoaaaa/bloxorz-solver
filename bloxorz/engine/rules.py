# Phụ trách: VT2 - Task 2.1 / 2.2
"""
Luật lăn khối, rơi xuống vực, kiểm tra ô đích và ô dễ vỡ.
- get_block_cells: Tập hợp các ô lưới mà khối 1x1x2 đang chiếm giữ.
- roll_transition: Bảng chuyển đổi tư thế và tọa độ khi lăn khối 1x1x2 theo 4 hướng.
- is_valid_state: Kiểm tra tính an toàn/hợp lệ của trạng thái khối trên bàn cờ.
- is_goal: Kiểm tra điều kiện hoàn thành màn chơi (khối đứng thẳng trên ô đích).
- step: Thực hiện một nước đi di chuyển khối, trả về trạng thái mới hoặc None nếu rơi/thua.
- is_fragile_tile: Kiểm tra nhanh một tọa độ có phải là ô gạch dễ vỡ.
- initial_state: Trạng thái ban đầu chuẩn của khối trên màn chơi.
"""

from __future__ import annotations
from typing import Sequence

from bloxorz.model import Action, Direction, Pose, Pos, State
from bloxorz.stage import Stage
from .split import split_block, step_split
from .switches import trigger_switches

# Ký hiệu ô gạch dễ vỡ trên bản đồ ('F' theo quy chuẩn repo, 'x'/'o' để tương thích)
FRAGILE_TILES: frozenset[str] = frozenset({"F", "f", "x", "X", "o", "O"})


def is_fragile_tile(stage: Stage, pos: Pos) -> bool:
    """
    Kiểm tra ô tại vị trí pos có phải là ô gạch dễ vỡ (fragile tile) hay không.
    Gạch dễ vỡ chỉ chịu được khối khi ở tư thế nằm (trọng lượng phân bổ).
    """
    return stage.cell(pos) in FRAGILE_TILES


def get_block_cells(pose: Pose, pos: Pos) -> tuple[Pos, ...]:
    """
    Trả về tập hợp tọa độ các ô mà khối 1x1x2 chiếm giữ trên mặt sàn:
    - STANDING: 1 ô (r, c)
    - HORIZONTAL: 2 ô kề nhau cùng hàng (r, c) và (r, c + 1)
    - VERTICAL: 2 ô kề nhau cùng cột (r, c) và (r + 1, c)
    """
    r, c = pos
    if pose == Pose.STANDING:
        return ((r, c),)
    elif pose == Pose.HORIZONTAL:
        return ((r, c), (r, c + 1))
    elif pose == Pose.VERTICAL:
        return ((r, c), (r + 1, c))
    raise ValueError(f"Tư thế khối không hợp lệ: {pose}")


def roll_transition(pose: Pose, pos: Pos, direction: Direction) -> tuple[Pose, Pos]:
    """
    Bảng chuyển trạng thái (Orientation Transition Table) cho khối 1x1x2:
    Nhận vào (pose, pos, direction) -> trả về (tư thế mới, tọa độ mới).
    12 trường hợp xác định theo đúng luật lăn khối của game Bloxorz:
    - Đứng (STANDING):
      * Lăn UP:    đổ dọc lên trên      -> VERTICAL tại (r - 2, c)
      * Lăn DOWN:  đổ dọc xuống dưới    -> VERTICAL tại (r + 1, c)
      * Lăn LEFT:  đổ ngang sang trái   -> HORIZONTAL tại (r, c - 2)
      * Lăn RIGHT: đổ ngang sang phải   -> HORIZONTAL tại (r, c + 1)
    - Nằm ngang (HORIZONTAL) chiếm (r, c) và (r, c + 1):
      * Lăn UP:    lăn theo chiều ngang -> HORIZONTAL tại (r - 1, c)
      * Lăn DOWN:  lăn theo chiều ngang -> HORIZONTAL tại (r + 1, c)
      * Lăn LEFT:  dựng đứng sang trái  -> STANDING tại (r, c - 1)
      * Lăn RIGHT: dựng đứng sang phải  -> STANDING tại (r, c + 2)
    - Nằm dọc (VERTICAL) chiếm (r, c) và (r + 1, c):
      * Lăn UP:    dựng đứng lên trên   -> STANDING tại (r - 1, c)
      * Lăn DOWN:  dựng đứng xuống dưới -> STANDING tại (r + 2, c)
      * Lăn LEFT:  lăn theo chiều dọc   -> VERTICAL tại (r, c - 1)
      * Lăn RIGHT: lăn theo chiều dọc   -> VERTICAL tại (r, c + 1)
    """
    r, c = pos
    if pose == Pose.STANDING:
        if direction == Direction.UP:
            return Pose.VERTICAL, (r - 2, c)
        elif direction == Direction.DOWN:
            return Pose.VERTICAL, (r + 1, c)
        elif direction == Direction.LEFT:
            return Pose.HORIZONTAL, (r, c - 2)
        elif direction == Direction.RIGHT:
            return Pose.HORIZONTAL, (r, c + 1)

    elif pose == Pose.HORIZONTAL:
        if direction == Direction.UP:
            return Pose.HORIZONTAL, (r - 1, c)
        elif direction == Direction.DOWN:
            return Pose.HORIZONTAL, (r + 1, c)
        elif direction == Direction.LEFT:
            return Pose.STANDING, (r, c - 1)
        elif direction == Direction.RIGHT:
            return Pose.STANDING, (r, c + 2)

    elif pose == Pose.VERTICAL:
        if direction == Direction.UP:
            return Pose.STANDING, (r - 1, c)
        elif direction == Direction.DOWN:
            return Pose.STANDING, (r + 2, c)
        elif direction == Direction.LEFT:
            return Pose.VERTICAL, (r, c - 1)
        elif direction == Direction.RIGHT:
            return Pose.VERTICAL, (r, c + 1)

    raise ValueError(f"Hướng di chuyển hoặc tư thế không hợp lệ: {direction}, {pose}")


def is_valid_state(state: State, stage: Stage) -> bool:
    """
    Kiểm tra xem trạng thái hiện tại của khối có hợp lệ (an toàn) trên sàn hay không.
    Trả về False (nước đi dẫn đến thua/rơi) nếu:
    - Bất kỳ ô nào của khối nằm ngoài bàn cờ.
    - Bất kỳ ô nào của khối nằm trên ô trống (void '.').
    - Ô thuộc một cây cầu nhưng cây cầu đó chưa được mở (không có trong state.bridges_open).
    - Khối ở tư thế STANDING trên ô gạch dễ vỡ (fragile tile) -> gạch vỡ khiến khối rơi.
    - Khối ở tư thế nằm (HORIZONTAL hoặc VERTICAL) đè qua ô đích 'G' -> 'G' là một lỗ vuông,
      nằm đè qua lỗ sẽ bị rơi xuống lỗ.
    """
    if state.pose is None:
        # Trường hợp khối đang bị phân tách thành 2 cube con 1x1x1
        cubes = (state.pos, state.cube2) if state.cube2 is not None else (state.pos,)
        for p in cubes:
            if not stage.in_bounds(p):
                return False
            ch = stage.cell(p)
            if ch == "." or ch == "G":
                return False
            # Kiểm tra cầu
            if p in stage.bridge_at:
                bridge_id = stage.bridge_at[p]
                if bridge_id not in state.bridges_open:
                    return False
        return True

    # Trường hợp khối nguyên vẹn 1x1x2
    cells = get_block_cells(state.pose, state.pos)
    for p in cells:
        # 1. Kiểm tra giới hạn ranh giới
        if not stage.in_bounds(p):
            return False

        # 2. Kiểm tra ô trống (void)
        ch = stage.cell(p)
        if ch == ".":
            return False

        # 3. Kiểm tra cầu đóng
        if p in stage.bridge_at:
            bridge_id = stage.bridge_at[p]
            if bridge_id not in state.bridges_open:
                return False

        # 4. Kiểm tra ô đích 'G'
        # Chỉ được phép đứng vào lỗ đích, nếu nằm đè qua lỗ đích sẽ bị rơi
        if ch == "G" and state.pose != Pose.STANDING:
            return False

        # 5. Kiểm tra gạch dễ vỡ (fragile tile)
        # Chỉ gãy khi khối đứng dồn toàn bộ trọng lượng lên 1 ô
        if ch in FRAGILE_TILES and state.pose == Pose.STANDING:
            return False

    return True


def is_goal(state: State, stage: Stage) -> bool:
    """
    Kiểm tra điều kiện chiến thắng:
    Khối phải nguyên vẹn, ở tư thế STANDING và đứng ngay tại tọa độ ô đích stage.goal.
    """
    return state.pose == Pose.STANDING and state.pos == stage.goal


def step(state: State, action: Action, stage: Stage) -> State | None:
    """
    Thực hiện di chuyển khối theo một Action:
    - Nếu khối đang ở trạng thái phân tách thành 2 cube 1x1 (state.pose is None):
      uỷ quyền xử lý cho step_split.
    - Nếu khối nguyên vẹn 1x1x2:
      * Tính toán tư thế và vị trí mới qua roll_transition.
      * Kiểm tra tính an toàn khi tiếp đất (dựa trên trạng thái cầu hiện tại).
      * Nếu đứng trên split switch: phân tách thành 2 cube qua split_block.
      * Kích hoạt các công tắc (soft/heavy) nếu có trên các ô tiếp đất, cập nhật bridges_open.
      * Kiểm tra lại tính an toàn sau khi cập nhật cầu (tránh trường hợp cầu dưới chân bị sập).
      * Trả về State mới nếu hợp lệ, hoặc None nếu khối bị rơi khỏi mép bàn/void/gãy gạch/sập cầu.
    """
    if state.pose is None:
        return step_split(state, action, stage)

    new_pose, new_pos = roll_transition(state.pose, state.pos, action.direction)

    # 1. Kiểm tra an toàn tại thời điểm tiếp đất (dựa trên trạng thái cầu hiện tại)
    landing_state = State(
        pose=new_pose,
        pos=new_pos,
        bridges_open=state.bridges_open,
    )
    if not is_valid_state(landing_state, stage):
        return None

    # 2. Khối tiếp đất an toàn: Kiểm tra kích hoạt công tắc phân tách (split switch)
    if new_pose == Pose.STANDING:
        sw = stage.switch_at.get(new_pos)
        if sw is not None and sw.kind == "split":
            return split_block(stage, landing_state, sw)

    # 3. Kích hoạt các công tắc thường (soft/heavy) nếu có
    cells = get_block_cells(new_pose, new_pos)
    new_bridges_open = trigger_switches(stage, new_pose, cells, state.bridges_open)

    new_state = State(
        pose=new_pose,
        pos=new_pos,
        bridges_open=new_bridges_open,
    )

    # 4. Kiểm tra lại an toàn (phòng trường hợp công tắc làm sập cầu dưới chân)
    if not is_valid_state(new_state, stage):
        return None

    return new_state


def initial_state(stage: Stage) -> State:
    """Trả về trạng thái ban đầu của khối trên màn chơi (tư thế STANDING tại stage.start)."""
    return State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )
