"""
Kiểm thử cho khung dữ liệu chung (model.py và stage.py) - Task 1.2
Bao gồm 5 bài test bắt buộc theo quy định của đồ án:
1. Gán state.pos = (0, 0) thì báo lỗi FrozenInstanceError (tính bất biến).
2. State dùng được làm khóa dict và phần tử của set (tính hashable).
3. State(None, (5, 5), (1, 1)) == State(None, (1, 1), (5, 5)) và hash bằng nhau (chuẩn hóa 2 cube).
4. Stage.cell((-1, 0)) trả '.' (xử lý tọa độ ngoài bàn chơi an toàn).
5. Stage.switch_at tìm đúng công tắc theo vị trí (tra cứu cached_property).
"""

from dataclasses import FrozenInstanceError
import pytest

from bloxorz.model import Direction, Pose, State, Action
from bloxorz.stage import Bridge, Switch, Stage


def test_state_immutable():
    """1. Kiểm tra State là bất biến: gán lại thuộc tính phải ném lỗi FrozenInstanceError."""
    state = State(pose=Pose.STANDING, pos=(2, 3))
    with pytest.raises(FrozenInstanceError):
        state.pos = (0, 0)


def test_state_hashable_and_usable_in_set_and_dict():
    """2. Kiểm tra State có thể làm phần tử set và khóa dict (phục vụ thuật toán tìm kiếm)."""
    s1 = State(pose=Pose.STANDING, pos=(0, 0), bridges_open=frozenset(["b1"]))
    s2 = State(pose=Pose.HORIZONTAL, pos=(0, 1), bridges_open=frozenset())
    s3 = State(pose=Pose.STANDING, pos=(0, 0), bridges_open=frozenset(["b1"]))

    # Kiểm tra set deduplication
    state_set = {s1, s2, s3}
    assert len(state_set) == 2
    assert s1 in state_set

    # Kiểm tra dict key
    state_dict = {s1: "start_node", s2: "next_node"}
    assert state_dict[s3] == "start_node"


def test_state_two_cubes_normalization_and_equality():
    """3. Kiểm tra tự động chuẩn hóa thứ tự 2 cube: đổi chỗ vẫn bằng nhau và cùng hash."""
    s_a = State(pose=None, pos=(5, 5), cube2=(1, 1))
    s_b = State(pose=None, pos=(1, 1), cube2=(5, 5))

    # Cả hai đều phải được chuẩn hóa thành pos=(1, 1), cube2=(5, 5)
    assert s_a.pos == (1, 1)
    assert s_a.cube2 == (5, 5)
    assert s_a == s_b
    assert hash(s_a) == hash(s_b)


def test_stage_cell_out_of_bounds():
    """4. Kiểm tra Stage.cell((-1, 0)) trả '.' khi truy vấn tọa độ ngoài phạm vi bản đồ."""
    dummy_stage = Stage(
        id="test_stage",
        group="G1",
        grid=("###", "###"),
        start=(0, 0),
        goal=(1, 2)
    )
    # Tọa độ âm
    assert dummy_stage.cell((-1, 0)) == "."
    assert dummy_stage.cell((0, -1)) == "."
    # Tọa độ vượt quá kích thước
    assert dummy_stage.cell((2, 0)) == "."
    assert dummy_stage.cell((0, 3)) == "."
    # Tọa độ hợp lệ
    assert dummy_stage.cell((0, 0)) == "#"


def test_stage_switch_at_lookup():
    """5. Kiểm tra Stage.switch_at tìm đúng công tắc theo tọa độ."""
    sw1 = Switch(id="sw1", kind="soft", pos=(1, 1), mode="toggle", bridges=("b1",))
    sw2 = Switch(id="sw2", kind="heavy", pos=(2, 3), mode="permanent", set_to="open", bridges=("b2",))
    
    stage = Stage(
        id="stage_with_switches",
        group="G1",
        grid=("####", "####", "####"),
        start=(0, 0),
        goal=(2, 2),
        switches=(sw1, sw2)
    )

    mapping = stage.switch_at
    assert len(mapping) == 2
    assert mapping[(1, 1)] == sw1
    assert mapping[(2, 3)] == sw2
    assert (0, 0) not in mapping
