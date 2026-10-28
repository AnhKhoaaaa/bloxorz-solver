"""
Kiểm thử toàn diện cho module luật game (bloxorz/engine/rules.py) - Task 2.1 / 2.2
Bao gồm:
1. Kiểm tra tập hợp ô khối chiếm giữ (get_block_cells) cho 3 tư thế (STANDING, HORIZONTAL, VERTICAL).
2. Kiểm tra bảng chuyển trạng thái lăn khối (roll_transition) đủ 12 trường hợp (3 tư thế x 4 hướng).
3. Kiểm tra tính hợp lệ của trạng thái trên bàn cờ (is_valid_state / rơi khỏi mép bàn, rơi vào void).
4. Kiểm tra cơ chế gạch dễ vỡ (fragile tiles): nằm an toàn, đứng gãy/rơi.
5. Kiểm tra cơ chế cầu (bridges): cầu mở đi được, cầu đóng coi như void/rơi.
6. Kiểm tra điều kiện thắng (is_goal): chỉ thắng khi ĐỨNG thẳng lên ô đích 'G'.
7. Kiểm tra hàm thực hiện bước di chuyển (step): trả về State mới khi hợp lệ, None khi rơi/thua.
"""

import pytest

from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage
from bloxorz.engine.rules import (
    get_block_cells,
    roll_transition,
    is_valid_state,
    is_goal,
    step,
    initial_state,
)


# 1. Test get_block_cells: Tập ô mà khối 1x1x2 chiếm giữ

def test_get_block_cells_standing():
    """Khối đứng tại (r, c) chỉ chiếm duy nhất 1 ô (r, c)."""
    cells = get_block_cells(Pose.STANDING, (2, 3))
    assert cells == ((2, 3),)


def test_get_block_cells_horizontal():
    """Khối nằm ngang tại (r, c) chiếm 2 ô (r, c) và (r, c+1)."""
    cells = get_block_cells(Pose.HORIZONTAL, (2, 3))
    assert cells == ((2, 3), (2, 4))


def test_get_block_cells_vertical():
    """Khối nằm dọc tại (r, c) chiếm 2 ô (r, c) và (r+1, c)."""
    cells = get_block_cells(Pose.VERTICAL, (2, 3))
    assert cells == ((2, 3), (3, 3))


# 2. Test roll_transition: 12 trường hợp chuyển tư thế và tọa độ

@pytest.mark.parametrize(
    "direction, expected_pose, expected_pos",
    [
        (Direction.UP, Pose.VERTICAL, (1, 3)),     # (r-2, c)
        (Direction.DOWN, Pose.VERTICAL, (4, 3)),   # (r+1, c)
        (Direction.LEFT, Pose.HORIZONTAL, (3, 1)), # (r, c-2)
        (Direction.RIGHT, Pose.HORIZONTAL, (3, 4)),# (r, c+1)
    ],
)
def test_roll_transition_from_standing(direction, expected_pose, expected_pos):
    """Khối STANDING tại (3, 3) lăn theo 4 hướng."""
    new_pose, new_pos = roll_transition(Pose.STANDING, (3, 3), direction)
    assert (new_pose, new_pos) == (expected_pose, expected_pos)


@pytest.mark.parametrize(
    "direction, expected_pose, expected_pos",
    [
        (Direction.UP, Pose.HORIZONTAL, (2, 3)),   # (r-1, c)
        (Direction.DOWN, Pose.HORIZONTAL, (4, 3)), # (r+1, c)
        (Direction.LEFT, Pose.STANDING, (3, 2)),   # (r, c-1)
        (Direction.RIGHT, Pose.STANDING, (3, 5)),  # (r, c+2)
    ],
)
def test_roll_transition_from_horizontal(direction, expected_pose, expected_pos):
    """Khối HORIZONTAL tại (3, 3) chiếm (3, 3) và (3, 4) lăn theo 4 hướng."""
    new_pose, new_pos = roll_transition(Pose.HORIZONTAL, (3, 3), direction)
    assert (new_pose, new_pos) == (expected_pose, expected_pos)


@pytest.mark.parametrize(
    "direction, expected_pose, expected_pos",
    [
        (Direction.UP, Pose.STANDING, (2, 3)),     # (r-1, c)
        (Direction.DOWN, Pose.STANDING, (5, 3)),   # (r+2, c)
        (Direction.LEFT, Pose.VERTICAL, (3, 2)),   # (r, c-1)
        (Direction.RIGHT, Pose.VERTICAL, (3, 4)),  # (r, c+1)
    ],
)
def test_roll_transition_from_vertical(direction, expected_pose, expected_pos):
    """Khối VERTICAL tại (3, 3) chiếm (3, 3) và (4, 3) lăn theo 4 hướng."""
    new_pose, new_pos = roll_transition(Pose.VERTICAL, (3, 3), direction)
    assert (new_pose, new_pos) == (expected_pose, expected_pos)


# 3. Test is_valid_state: Rơi ra ngoài mép bàn hoặc rơi vào void '.'

@pytest.fixture
def basic_stage():
    """Bàn cờ cơ bản 4x4, có một số ô void '.'."""
    grid = (
        "####",
        "##..",
        "####",
        "###G",
    )
    return Stage(
        id="basic_stage",
        group="G1",
        grid=grid,
        start=(0, 0),
        goal=(3, 3),
    )


def test_valid_state_on_floor(basic_stage):
    """Khối nằm hoàn toàn trên sàn hợp lệ."""
    # Đứng tại (0, 0)
    assert is_valid_state(State(Pose.STANDING, (0, 0)), basic_stage) is True
    # Nằm ngang tại (0, 0) chiếm (0, 0) và (0, 1)
    assert is_valid_state(State(Pose.HORIZONTAL, (0, 0)), basic_stage) is True
    # Nằm dọc tại (0, 0) chiếm (0, 0) và (1, 0)
    assert is_valid_state(State(Pose.VERTICAL, (0, 0)), basic_stage) is True


def test_invalid_state_out_of_bounds(basic_stage):
    """Khối vượt ra ngoài ranh giới bản đồ."""
    # Đứng ngoài biên âm
    assert is_valid_state(State(Pose.STANDING, (-1, 0)), basic_stage) is False
    # Đứng ngoài biên dương
    assert is_valid_state(State(Pose.STANDING, (4, 0)), basic_stage) is False
    # Nằm ngang thò 1 ô ra ngoài biên cột
    assert is_valid_state(State(Pose.HORIZONTAL, (0, 3)), basic_stage) is False  # ô (0, 4) ngoài biên
    # Nằm dọc thò 1 ô ra ngoài biên hàng
    assert is_valid_state(State(Pose.VERTICAL, (3, 0)), basic_stage) is False    # ô (4, 0) ngoài biên


def test_invalid_state_over_void(basic_stage):
    """Khối rơi vào ô void '.'."""
    # Đứng ngay trên ô void (1, 2)
    assert is_valid_state(State(Pose.STANDING, (1, 2)), basic_stage) is False
    # Nằm ngang: 1 ô trên sàn (1, 1), 1 ô trên void (1, 2)
    assert is_valid_state(State(Pose.HORIZONTAL, (1, 1)), basic_stage) is False


# 4. Test gạch dễ vỡ (Fragile tiles ký hiệu 'x')

@pytest.fixture
def fragile_stage():
    """Bàn cờ có ô gạch dễ vỡ 'x' tại (1, 1)."""
    grid = (
        "###",
        "#x#",
        "##G",
    )
    return Stage(
        id="fragile_stage",
        group="G2",
        grid=grid,
        start=(0, 0),
        goal=(2, 2),
    )


def test_fragile_tile_standing_collapses(fragile_stage):
    """Khối ĐỨNG trên ô gạch dễ vỡ sẽ làm vỡ gạch và rơi xuống vực (không hợp lệ)."""
    state_standing = State(Pose.STANDING, (1, 1))
    assert is_valid_state(state_standing, fragile_stage) is False


def test_fragile_tile_lying_is_safe(fragile_stage):
    """Khối NẰM ngang hoặc dọc đè qua ô gạch dễ vỡ vẫn an toàn (hợp lệ)."""
    # Nằm ngang chiếm (1, 0) [#] và (1, 1) [x]
    state_horiz = State(Pose.HORIZONTAL, (1, 0))
    assert is_valid_state(state_horiz, fragile_stage) is True

    # Nằm dọc chiếm (0, 1) [#] và (1, 1) [x]
    state_vert = State(Pose.VERTICAL, (0, 1))
    assert is_valid_state(state_vert, fragile_stage) is True


# 5. Test cầu (Bridges)

@pytest.fixture
def bridge_stage():
    """Bàn cờ có cầu b1 tại ô (1, 1). Ban đầu cầu đóng."""
    bridge = Bridge(id="b1", cells=((1, 1),), initially_open=False)
    grid = (
        "###",
        "###",
        "##G",
    )
    return Stage(
        id="bridge_stage",
        group="G3",
        grid=grid,
        start=(0, 0),
        goal=(2, 2),
        bridges=(bridge,),
    )


def test_bridge_closed_acts_as_void(bridge_stage):
    """Cầu đang đóng (không có trong bridges_open) xem như khoảng trống (void)."""
    # Khối đứng trên ô cầu (1, 1) khi b1 chưa mở -> rơi
    state_closed = State(Pose.STANDING, (1, 1), bridges_open=frozenset())
    assert is_valid_state(state_closed, bridge_stage) is False

    # Khối nằm ngang qua (1, 0) và (1, 1) khi b1 đóng -> rơi
    state_lying = State(Pose.HORIZONTAL, (1, 0), bridges_open=frozenset())
    assert is_valid_state(state_lying, bridge_stage) is False


def test_bridge_open_acts_as_floor(bridge_stage):
    """Cầu đang mở (có trong bridges_open) hoạt động như ô sàn bình thường."""
    # Khối đứng trên ô cầu (1, 1) khi b1 đã mở -> hợp lệ
    state_open = State(Pose.STANDING, (1, 1), bridges_open=frozenset(["b1"]))
    assert is_valid_state(state_open, bridge_stage) is True

    # Khối nằm ngang qua (1, 0) và (1, 1) khi b1 đã mở -> hợp lệ
    state_lying = State(Pose.HORIZONTAL, (1, 0), bridges_open=frozenset(["b1"]))
    assert is_valid_state(state_lying, bridge_stage) is True


# 6. Test is_goal: Điều kiện chiến thắng

def test_goal_detection(basic_stage):
    """Chỉ thắng khi khối STANDING trên ô đích 'G' (3, 3)."""
    # Đứng thẳng tại (3, 3) -> Thắng
    assert is_goal(State(Pose.STANDING, (3, 3)), basic_stage) is True

    # Đứng ở vị trí khác (0, 0) -> Không thắng
    assert is_goal(State(Pose.STANDING, (0, 0)), basic_stage) is False

    # Nằm đè lên ô Goal (ví dụ nằm ngang chiếm (3, 2) và (3, 3)) -> Không thắng
    assert is_goal(State(Pose.HORIZONTAL, (3, 2)), basic_stage) is False

    # Nằm dọc đè lên ô Goal -> Không thắng
    assert is_goal(State(Pose.VERTICAL, (2, 3)), basic_stage) is False


def test_goal_tile_lying_is_valid_but_not_goal(basic_stage):
    """Ô đích 'G' là lỗ 1x1, khối 1x1x2 nằm đè qua lỗ và sàn bên cạnh vẫn an toàn (nhưng chưa thắng)."""
    # Nằm ngang qua (3, 2) [#] và (3, 3) [G] -> An toàn, chưa thắng
    assert is_valid_state(State(Pose.HORIZONTAL, (3, 2)), basic_stage) is True
    assert is_goal(State(Pose.HORIZONTAL, (3, 2)), basic_stage) is False
    # Nằm dọc qua (2, 3) [#] và (3, 3) [G] -> An toàn, chưa thắng
    assert is_valid_state(State(Pose.VERTICAL, (2, 3)), basic_stage) is True
    assert is_goal(State(Pose.VERTICAL, (2, 3)), basic_stage) is False


# 7. Test step: Thực hiện nước đi và trả về State mới

def test_step_valid_move(basic_stage):
    """Bước đi hợp lệ trả về State mới chính xác."""
    start_state = State(Pose.STANDING, (0, 0))
    # Lăn sang phải -> HORIZONTAL tại (0, 1) chiếm (0, 1) và (0, 2)
    next_state = step(start_state, Action(Direction.RIGHT), basic_stage)
    assert next_state is not None
    assert next_state.pose == Pose.HORIZONTAL
    assert next_state.pos == (0, 1)

    # Từ HORIZONTAL tại (0, 1) lăn sang phải -> STANDING tại (0, 3)
    goal_standing = step(next_state, Action(Direction.RIGHT), basic_stage)
    assert goal_standing is not None
    assert goal_standing.pose == Pose.STANDING
    assert goal_standing.pos == (0, 3)


def test_step_illegal_move_returns_none(basic_stage):
    """Bước đi khiến khối rơi khỏi bàn hoặc rơi vào void trả về None."""
    start_state = State(Pose.STANDING, (0, 0))
    # Lăn lên trên (ra ngoài biên trên) -> Rơi
    assert step(start_state, Action(Direction.UP), basic_stage) is None
    # Lăn sang trái (ra ngoài biên trái) -> Rơi
    assert step(start_state, Action(Direction.LEFT), basic_stage) is None


def test_step_intact_block_with_cube_index_returns_none(basic_stage):
    """Khi khối nguyên vẹn (pose != None), truyền action.cube != None là không hợp lệ -> trả về None."""
    start_state = State(Pose.STANDING, (0, 0))
    assert step(start_state, Action(Direction.RIGHT, cube=0), basic_stage) is None
    assert step(start_state, Action(Direction.RIGHT, cube=1), basic_stage) is None


def test_fragile_tile_with_standard_symbol_f():
    """Kiểm tra ô gạch dễ vỡ với ký hiệu chuẩn 'F' (theo quy định đề án và loader)."""
    grid = ("###", "#F#", "##G")
    stage = Stage(id="f_stage", group="G2", grid=grid, start=(0, 0), goal=(2, 2))
    # Đứng trên 'F' -> Rơi
    assert is_valid_state(State(Pose.STANDING, (1, 1)), stage) is False
    # Nằm ngang qua 'F' -> An toàn
    assert is_valid_state(State(Pose.HORIZONTAL, (1, 0)), stage) is True


def test_split_cube_falling_into_goal():
    """Khối con 1x1x1 khi phân tách nếu rơi vào lỗ đích 'G' thì bị thua."""
    grid = ("###", "#.G")
    stage = Stage(id="g_stage", group="G1", grid=grid, start=(0, 0), goal=(1, 2))
    # Khối con 1 tại (1, 2) [G] -> Rơi
    assert is_valid_state(State(pose=None, pos=(1, 2), cube2=(0, 0)), stage) is False


def test_initial_state_helper():
    """Kiểm tra hàm initial_state tạo đúng State ban đầu từ Stage."""
    stage = Stage(
        id="init_stage",
        group="G1",
        grid=("###", "###"),
        start=(1, 2),
        goal=(1, 0),
        bridges=(Bridge("b1", ((0, 0),), initially_open=True),),
    )
    s0 = initial_state(stage)
    assert s0.pose == Pose.STANDING
    assert s0.pos == (1, 2)
    assert s0.bridges_open == frozenset(["b1"])

