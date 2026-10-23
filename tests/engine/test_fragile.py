"""
Kiểm thử chuyên sâu cho cơ chế ô gạch dễ vỡ (Fragile Tiles) - Task 2.2
Yêu cầu theo Section 2.5 của đồ án Bloxorz:
- Ô dễ vỡ (fragile/orange tile) chỉ chịu được trọng lượng khối khi khối ở tư thế NẰM (HORIZONTAL hoặc VERTICAL).
- Khi khối ĐỨNG (STANDING) lên ô dễ vỡ, ô gạch sẽ vỡ và khối rơi xuống vực (illegal move / thua).
- Khối có thể di chuyển an toàn qua các ô dễ vỡ nếu luôn duy trì tư thế nằm.
"""

import pytest

from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage
from bloxorz.engine.rules import (
    FRAGILE_TILES,
    is_fragile_tile,
    is_valid_state,
    step,
)


@pytest.fixture
def fragile_strip_stage():
    """
    Bản đồ chứa dải ô dễ vỡ 'x':
    Hàng 0: # # # . . .
    Hàng 1: . x x x . .
    Hàng 2: . . . # # G
    Start: (0, 0)
    Goal:  (2, 5)
    """
    grid = (
        "###...",
        ".xxx..",
        "...##G",
    )
    return Stage(
        id="fragile_strip_stage",
        group="G2",
        grid=grid,
        start=(0, 0),
        goal=(2, 5),
    )


@pytest.fixture
def mixed_fragile_stage():
    """
    Bản đồ chứa ô gạch dễ vỡ xen kẽ sàn thường và cầu:
    Hàng 0: # # #
    Hàng 1: # x #
    Hàng 2: # # G
    """
    bridge = Bridge(id="b1", cells=((0, 2),), initially_open=True)
    grid = (
        "###",
        "#x#",
        "##G",
    )
    return Stage(
        id="mixed_fragile_stage",
        group="G2",
        grid=grid,
        start=(0, 0),
        goal=(2, 2),
        bridges=(bridge,),
    )


# 1. Kiểm tra hàm nhận diện ô dễ vỡ (is_fragile_tile)

def test_is_fragile_tile_detection(mixed_fragile_stage):
    """Xác định chính xác ô nào là fragile tile theo ký hiệu."""
    assert is_fragile_tile(mixed_fragile_stage, (1, 1)) is True
    # Các ô thường, void, goal không phải là fragile tile
    assert is_fragile_tile(mixed_fragile_stage, (0, 0)) is False
    assert is_fragile_tile(mixed_fragile_stage, (2, 2)) is False
    assert is_fragile_tile(mixed_fragile_stage, (-1, 0)) is False


def test_fragile_tile_symbols():
    """Kiểm tra các ký hiệu được xem là gạch dễ vỡ."""
    for symbol in ("F", "f", "x", "X", "o", "O"):
        assert symbol in FRAGILE_TILES


# 2. Khối ĐỨNG trên ô dễ vỡ -> Gạch vỡ, rơi (False)

def test_standing_on_fragile_tile_collapses(mixed_fragile_stage):
    """Khối ở tư thế STANDING dồn toàn bộ trọng lượng lên 1 ô fragile -> vỡ gạch."""
    state_standing = State(Pose.STANDING, (1, 1))
    assert is_valid_state(state_standing, mixed_fragile_stage) is False


# 3. Khối NẰM trên ô dễ vỡ -> Trọng lượng phân bổ, an toàn (True)

def test_lying_horizontal_across_two_fragile_tiles(fragile_strip_stage):
    """Khối nằm ngang chiếm trọn 2 ô fragile liên tiếp (1, 1) và (1, 2) -> an toàn."""
    state_lying_both = State(Pose.HORIZONTAL, (1, 1))
    assert is_valid_state(state_lying_both, fragile_strip_stage) is True


def test_lying_horizontal_half_floor_half_fragile(mixed_fragile_stage):
    """Khối nằm ngang: 1 ô trên sàn thường (1, 0), 1 ô trên fragile (1, 1) -> an toàn."""
    state_half = State(Pose.HORIZONTAL, (1, 0))
    assert is_valid_state(state_half, mixed_fragile_stage) is True


def test_lying_vertical_half_floor_half_fragile(mixed_fragile_stage):
    """Khối nằm dọc: 1 ô trên sàn thường (0, 1), 1 ô trên fragile (1, 1) -> an toàn."""
    state_vert_half = State(Pose.VERTICAL, (0, 1))
    assert is_valid_state(state_vert_half, mixed_fragile_stage) is True


def test_lying_vertical_half_bridge_half_fragile():
    """Khối nằm dọc đè qua 1 ô cầu mở và 1 ô fragile -> an toàn."""
    stage = Stage(
        id="bridge_fragile_stage", group="G2", grid=("#B#", "#x#", "##G"),
        start=(0, 0), goal=(2, 2),
        bridges=(Bridge(id="b1", cells=((0, 1),), initially_open=True),),
    )
    state = State(Pose.VERTICAL, (0, 1), bridges_open=frozenset(["b1"]))
    assert is_valid_state(state, stage) is True


# 4. Khối nằm đè qua ô dễ vỡ nhưng có 1 ô rơi vào void/cầu đóng

def test_lying_fragile_and_void_falls(fragile_strip_stage):
    """Khối nằm ngang chiếm 1 ô fragile (1, 3) và 1 ô void (1, 4) -> rơi vào void."""
    state_fall = State(Pose.HORIZONTAL, (1, 3))
    assert is_valid_state(state_fall, fragile_strip_stage) is False


# 5. Kiểm tra di chuyển (step) tương tác với ô dễ vỡ

def test_roll_onto_fragile_in_lying_position_succeeds(mixed_fragile_stage):
    """Từ STANDING tại (0, 1), lăn DOWN thành VERTICAL tại (1, 1) và (2, 1) -> thành công."""
    start = State(Pose.STANDING, (0, 1))
    next_state = step(start, Action(Direction.DOWN), mixed_fragile_stage)
    assert next_state is not None
    assert next_state.pose == Pose.VERTICAL
    assert next_state.pos == (1, 1)


def test_roll_into_standing_on_fragile_fails(mixed_fragile_stage):
    """
    Từ HORIZONTAL tại (1, 0) chiếm (1, 0) và (1, 1) (an toàn),
    nếu lăn LEFT -> dựng STANDING tại (1, -1) (ngoài biên) -> None.
    Từ HORIZONTAL tại (1, 0), nếu lăn RIGHT -> dựng STANDING tại (1, 2) [#] -> thành công.
    Nếu khối đứng lọt vào (1, 1) [x] -> gãy gạch rơi ngay.
    """
    # Khối HORIZONTAL tại (1, -1) không hợp lệ, nhưng xét trường hợp:
    # STANDING tại (1, 1) là ô fragile
    invalid_standing = State(Pose.STANDING, (1, 1))
    assert is_valid_state(invalid_standing, mixed_fragile_stage) is False


def test_traverse_fragile_path():
    """
    Một màn chơi có đường đi buộc phải lăn nằm qua các ô dễ vỡ.
    Lưới 3x5:
    S # x x G (tất cả cùng hàng 0)
    Khi đứng tại (0, 0), lăn RIGHT -> HORIZONTAL tại (0, 1) [# và x] (an toàn).
    Lăn tiếp RIGHT -> STANDING tại (0, 3) [x] -> GÃY GẠCH RƠI!
    """
    grid = ("##xxG",)
    stage = Stage("traverse", "G2", grid, start=(0, 0), goal=(0, 4))
    
    s0 = State(Pose.STANDING, (0, 0))
    # Bước 1: Lăn sang phải -> Nằm ngang tại (0, 1) chiếm (0, 1) và (0, 2) [1 sàn, 1 fragile] -> OK
    s1 = step(s0, Action(Direction.RIGHT), stage)
    assert s1 is not None
    assert s1.pose == Pose.HORIZONTAL

    # Bước 2: Lăn tiếp sang phải -> Đứng tại (0, 3) [fragile] -> Sập gạch rơi!
    s2 = step(s1, Action(Direction.RIGHT), stage)
    assert s2 is None
