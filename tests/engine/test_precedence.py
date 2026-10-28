# Phụ trách: VT2 - Task 2.5
"""
Kiểm thử chuyên sâu về thứ tự ưu tiên xử lý (Precedence / Order of Operations) và các trường hợp biên đối kháng trong Engine - Task 2.5.

Các nguyên tắc thứ tự xử lý cốt lõi:
1. Rơi trước khi kích hoạt: Khối rơi vào void, ngoài biên hoặc cầu đóng thì lập tức rơi (None), KHÔNG kích hoạt công tắc.
2. Gạch vỡ trước khi đứng: Khối đứng lên gạch dễ vỡ 'F' bị vỡ gạch và rơi, KHÔNG kích hoạt công tắc trên ô đó.
3. Sập cầu dưới chân: Khối kích hoạt công tắc đóng cây cầu mà khối đang đứng đè lên một phần -> mất điểm tựa và rơi.
4. Nhiều công tắc kích hoạt đồng thời: Thứ tự duyệt switch phải nhất quán và xác định (deterministic) theo tọa độ ô.
5. Lỗ đích 'G' vs Khối nằm: Khối 1x1x2 nằm đè qua Goal và sàn bên cạnh vẫn an toàn (chưa thắng), chỉ thắng khi STANDING.
6. Thứ tự phân tách (Split): Tiếp đất an toàn -> dịch chuyển 2 cube tới targets -> kích hoạt soft switch tại targets -> tự động ghép lại nếu kề nhau.
7. Thứ tự ghép khối (Rejoin): Cube tiếp đất -> kích hoạt soft switch tại ô mới -> tự động ghép khối khi kề nhau -> kiểm tra an toàn của khối mới ghép.
8. Sập cầu dưới chân cube đồng đội: Cube 0 đạp switch đóng cầu mà Cube 1 đang đứng -> Cube 1 rơi -> nước đi thất bại (None).
"""

import pytest

from bloxorz.engine.rules import initial_state, is_goal, is_valid_state, step
from bloxorz.engine.split import split_block, step_split, try_merge_cubes
from bloxorz.engine.switches import can_activate_switch, trigger_switches
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage, Switch


# ==============================================================================
# 1. Rơi trước khi kích hoạt công tắc (Fall before trigger)
# ==============================================================================

def test_fall_into_void_before_triggering_switch():
    """Khối nằm ngang thò 1 ô ra ngoài void trong khi ô kia có soft switch: khối rơi, switch không kích hoạt."""
    bridge = Bridge(id="b1", cells=((0, 4),), initially_open=False)
    sw = Switch(id="s1", kind="soft", pos=(0, 1), mode="permanent", set_to="open", bridges=("b1",))
    # Hàng 0: S # . . B . G -> từ (0, 0) lăn R thành HORIZONTAL tại (0, 1) chiếm (0, 1) [# có switch] và (0, 2) [.]
    stage = Stage(
        id="void_precedence",
        group="G2",
        grid=("S#..B.G",),
        start=(0, 0),
        goal=(0, 6),
        bridges=(bridge,),
        switches=(sw,),
    )
    s0 = initial_state(stage)
    # Lăn R -> một nửa khối rơi vào void tại (0, 2)
    next_s = step(s0, Action(Direction.RIGHT), stage)
    # Khối rơi ngay lập tức
    assert next_s is None


def test_fall_into_closed_bridge_before_triggering_switch():
    """
    Khối nằm ngang chiếm (0, 1) và (0, 2).
    Ô (0, 1) là sàn '#' có soft switch mở cầu b1.
    Ô (0, 2) là cầu 'b1' ĐANG ĐÓNG.
    Khối không thể dùng switch trên ô (0, 1) để tự mở cầu dưới ô (0, 2) trong khi đang rơi!
    """
    bridge = Bridge(id="b1", cells=((0, 2),), initially_open=False)
    sw = Switch(id="s1", kind="soft", pos=(0, 1), mode="permanent", set_to="open", bridges=("b1",))
    stage = Stage(
        id="bridge_precedence",
        group="G2",
        grid=("S#B.G",),
        start=(0, 0),
        goal=(0, 4),
        bridges=(bridge,),
        switches=(sw,),
    )
    s0 = initial_state(stage)
    # Lăn R -> tiếp đất lên (0, 1) và (0, 2). Tại thời điểm tiếp đất, (0, 2) chưa mở -> Rơi!
    next_s = step(s0, Action(Direction.RIGHT), stage)
    assert next_s is None


def test_standing_on_fragile_tile_with_switch_collapses_without_trigger():
    """
    Nếu một ô gạch dễ vỡ 'F' có switch mở cầu b1:
    Khối đứng lên gạch dễ vỡ sẽ làm vỡ gạch và rơi trước khi kịp kích hoạt switch.
    """
    bridge = Bridge(id="b1", cells=((0, 4),), initially_open=False)
    sw = Switch(id="s1", kind="soft", pos=(0, 3), mode="permanent", set_to="open", bridges=("b1",))
    stage = Stage(
        id="fragile_switch_precedence",
        group="G2",
        grid=("S##FB.G",),
        start=(0, 0),
        goal=(0, 6),
        bridges=(bridge,),
        switches=(sw,),
    )
    s0 = initial_state(stage)
    # (0, 0) STAND -> R -> (0, 1) HORIZ chiếm (0, 1), (0, 2)
    s1 = step(s0, Action(Direction.RIGHT), stage)
    assert s1 is not None and s1.pose == Pose.HORIZONTAL

    # Từ (0, 1) HORIZ lăn R -> STANDING tại (0, 3) là ô 'F' có switch s1!
    # Vì đứng trên gạch 'F' nên gạch vỡ -> rơi ngay lập tức!
    s2 = step(s1, Action(Direction.RIGHT), stage)
    assert s2 is None


# ==============================================================================
# 2. Sập cầu ngay dưới chân khối (Bridge collapse underneath)
# ==============================================================================

def test_bridge_collapse_underneath_horizontal_block():
    """
    Cầu b1 ban đầu mở tại ô (0, 2).
    Soft switch tại ô (0, 1) có lệnh ĐÓNG cầu b1.
    Khối lăn vào tư thế HORIZONTAL chiếm (0, 1) [#] và (0, 2) [b1].
    Switch đóng cầu b1 -> ô (0, 2) biến mất -> khối mất điểm tựa và rơi!
    """
    bridge = Bridge(id="b1", cells=((0, 2),), initially_open=True)
    sw = Switch(id="s1", kind="soft", pos=(0, 1), mode="permanent", set_to="close", bridges=("b1",))
    stage = Stage(
        id="bridge_collapse_horiz",
        group="G2",
        grid=("S#B.G",),
        start=(0, 0),
        goal=(0, 4),
        bridges=(bridge,),
        switches=(sw,),
    )
    s0 = initial_state(stage)
    assert "b1" in s0.bridges_open

    # Lăn R -> HORIZONTAL tại (0, 1) và (0, 2)
    next_s = step(s0, Action(Direction.RIGHT), stage)
    assert next_s is None


def test_bridge_collapse_underneath_vertical_block():
    """
    Cầu b1 ban đầu mở tại ô (2, 0).
    Soft switch tại ô (1, 0) có lệnh ĐÓNG cầu b1.
    Khối lăn DOWN vào tư thế VERTICAL chiếm (1, 0) [#] và (2, 0) [b1].
    Switch đóng cầu b1 -> ô (2, 0) biến mất -> khối rơi!
    """
    bridge = Bridge(id="b1", cells=((2, 0),), initially_open=True)
    sw = Switch(id="s1", kind="soft", pos=(1, 0), mode="permanent", set_to="close", bridges=("b1",))
    stage = Stage(
        id="bridge_collapse_vert",
        group="G2",
        grid=("S", "#", "B", ".", "G"),
        start=(0, 0),
        goal=(4, 0),
        bridges=(bridge,),
        switches=(sw,),
    )
    s0 = initial_state(stage)
    # Lăn DOWN -> VERTICAL tại (1, 0) chiếm (1, 0) và (2, 0)
    next_s = step(s0, Action(Direction.DOWN), stage)
    assert next_s is None


# ==============================================================================
# 3. Nhiều công tắc kích hoạt đồng thời (Simultaneous multi-switch order)
# ==============================================================================

def test_multi_switch_order_deterministic_open_then_close():
    """
    Khối nằm ngang chiếm (0, 1) và (0, 2).
    Ô (0, 1) có soft switch s1 mở cầu b1.
    Ô (0, 2) có soft switch s2 đóng cầu b1.
    Engine duyệt theo thứ tự tọa độ: s1 mở b1, sau đó s2 đóng b1 -> kết quả b1 đóng!
    """
    bridge = Bridge(id="b1", cells=((0, 4),), initially_open=False)
    sw1 = Switch(id="s1", kind="soft", pos=(0, 1), mode="permanent", set_to="open", bridges=("b1",))
    sw2 = Switch(id="s2", kind="soft", pos=(0, 2), mode="permanent", set_to="close", bridges=("b1",))
    stage = Stage(
        id="multi_sw_1",
        group="G2",
        grid=("S###B.G",),
        start=(0, 0),
        goal=(0, 6),
        bridges=(bridge,),
        switches=(sw1, sw2),
    )
    s0 = initial_state(stage)
    s1 = step(s0, Action(Direction.RIGHT), stage)
    assert s1 is not None
    # s1 mở b1 rồi s2 đóng b1 -> b1 phải đóng
    assert "b1" not in s1.bridges_open


def test_multi_switch_order_deterministic_close_then_open():
    """
    Khối nằm ngang chiếm (0, 1) và (0, 2).
    Ô (0, 1) có soft switch s1 đóng cầu b1.
    Ô (0, 2) có soft switch s2 mở cầu b1.
    Engine duyệt theo thứ tự tọa độ: s1 đóng b1, sau đó s2 mở b1 -> kết quả b1 mở!
    """
    bridge = Bridge(id="b1", cells=((0, 4),), initially_open=True)
    sw1 = Switch(id="s1", kind="soft", pos=(0, 1), mode="permanent", set_to="close", bridges=("b1",))
    sw2 = Switch(id="s2", kind="soft", pos=(0, 2), mode="permanent", set_to="open", bridges=("b1",))
    stage = Stage(
        id="multi_sw_2",
        group="G2",
        grid=("S###B.G",),
        start=(0, 0),
        goal=(0, 6),
        bridges=(bridge,),
        switches=(sw1, sw2),
    )
    s0 = initial_state(stage)
    s1 = step(s0, Action(Direction.RIGHT), stage)
    assert s1 is not None
    # s1 đóng b1 rồi s2 mở b1 -> b1 phải mở
    assert "b1" in s1.bridges_open


# ==============================================================================
# 4. Lỗ đích Goal ('G') vs Khối nằm & Cube đơn lẻ
# ==============================================================================

def test_lying_across_goal_is_safe_but_not_win():
    """Khối 1x1x2 nằm ngang đè qua ô Goal 'G' và ô sàn '#' bên cạnh vẫn an toàn nhưng chưa thắng."""
    stage = Stage(
        id="goal_lie_safe",
        group="G1",
        grid=("S#G",),
        start=(0, 0),
        goal=(0, 2),
    )
    s0 = initial_state(stage)
    # Lăn R -> HORIZONTAL chiếm (0, 1) [#] và (0, 2) [G] -> Hợp lệ nhưng chưa phải Goal
    next_s = step(s0, Action(Direction.RIGHT), stage)
    assert next_s is not None
    assert next_s.pose == Pose.HORIZONTAL
    assert next_s.pos == (0, 1)
    assert is_goal(next_s, stage) is False


def test_standing_on_goal_wins():
    """Khối đứng thẳng trên ô Goal 'G' -> Chiến thắng hoàn toàn."""
    stage = Stage(
        id="goal_win",
        group="G1",
        grid=("S##G",),
        start=(0, 0),
        goal=(0, 3),
    )
    s0 = initial_state(stage)
    # Lăn R -> (0, 1) HORIZ
    s1 = step(s0, Action(Direction.RIGHT), stage)
    assert s1 is not None
    # Lăn R -> (0, 3) STANDING ngay trên Goal!
    s2 = step(s1, Action(Direction.RIGHT), stage)
    assert s2 is not None and is_goal(s2, stage) is True


# ==============================================================================
# 5. Thứ tự phân tách (Split switch precedence) & Ghép khối (Rejoining)
# ==============================================================================

def test_split_switch_triggers_soft_switches_at_targets():
    """
    Khi khối đứng lên split switch:
    Khối phân tách tới targets (t1, t2).
    Nếu tại t1 có soft switch mở cầu b1 -> soft switch được kích hoạt ngay lập tức!
    """
    bridge = Bridge(id="b1", cells=((2, 4),), initially_open=False)
    sw_target = Switch(id="s_target", kind="soft", pos=(2, 0), mode="permanent", set_to="open", bridges=("b1",))
    sw_split = Switch(id="s_split", kind="split", pos=(0, 3), targets=((2, 0), (2, 2)))
    stage = Stage(
        id="split_target_sw",
        group="G3",
        grid=("S###...", ".......", "####B.G"),
        start=(0, 0),
        goal=(2, 6),
        bridges=(bridge,),
        switches=(sw_target, sw_split),
    )
    s0 = initial_state(stage)
    assert "b1" not in s0.bridges_open

    # Lăn R -> (0, 1) HORIZ
    s1 = step(s0, Action(Direction.RIGHT), stage)
    # Lăn R -> (0, 3) STANDING trên split switch!
    s2 = step(s1, Action(Direction.RIGHT), stage)
    assert s2 is not None
    assert s2.pose is None  # Đã tách
    # Cube tại (2, 0) đã kích hoạt soft switch s_target -> cầu b1 đã mở!
    assert "b1" in s2.bridges_open


def test_cube_0_triggers_switch_closing_bridge_under_cube_1():
    """
    Trạng thái phân tách:
    Cube 0 ở (0, 1), Cube 1 đang đứng trên cầu b1 ở (2, 3).
    Cube 0 di chuyển DOWN tới (1, 1) là soft switch ĐÓNG cầu b1.
    Cầu b1 dưới chân Cube 1 bị sập -> Cube 1 rơi -> nước đi thất bại (None).
    """
    bridge = Bridge(id="b1", cells=((2, 3),), initially_open=True)
    sw_close = Switch(id="s_close", kind="soft", pos=(1, 1), mode="permanent", set_to="close", bridges=("b1",))
    stage = Stage(
        id="teammate_fall",
        group="G3",
        grid=(
            "###..",
            "###..",
            "###BG",
        ),
        start=(0, 0),
        goal=(2, 4),
        bridges=(bridge,),
        switches=(sw_close,),
    )
    s_split = State(pose=None, pos=(0, 1), cube2=(2, 3), bridges_open=frozenset({"b1"}))
    assert is_valid_state(s_split, stage) is True

    # Cube 0 (ở 0, 1) đi DOWN xuống (1, 1) có switch đóng b1
    res = step(s_split, Action(Direction.DOWN, cube=0), stage)
    # Cầu dưới chân Cube 1 sập -> trả về None
    assert res is None


def test_rejoining_over_closed_bridge_fails():
    """
    Cube 0 di chuyển kề Cube 1 để ghép lại, nhưng vị trí của Cube 0 là cầu đang đóng:
    Cube 0 rơi vào cầu đóng trước khi kịp ghép -> thất bại (None).
    """
    bridge = Bridge(id="b1", cells=((1, 2),), initially_open=False)
    stage = Stage(
        id="rejoin_closed_bridge",
        group="G3",
        grid=("###", "##B", "###"),
        start=(0, 0),
        goal=(2, 2),
        bridges=(bridge,),
    )
    # Cube 0 tại (0, 2), Cube 1 tại (1, 1). Cầu b1 tại (1, 2) đóng.
    s_split = State(pose=None, pos=(0, 2), cube2=(1, 1), bridges_open=frozenset())
    # Cube 0 đi DOWN tới (1, 2) là cầu đóng -> rơi!
    res = step(s_split, Action(Direction.DOWN, cube=0), stage)
    assert res is None


# ==============================================================================
# 6. Đóng góp 2 màn chơi mới (Task 2.5 - Contributed Stages)
# ==============================================================================

def test_contributed_stage_custom_g5_combo():
    """
    Màn đóng góp 1: custom_g5_combo.json (Nhóm G5)
    - Kết hợp: Gạch dễ vỡ 'F' + Heavy switch + Cầu đóng/mở.
    - Giải thành công bằng BFS trong đúng 12 bước.
    """
    from bloxorz.loader import load_stage
    from bloxorz.search.bfs import bfs
    from bloxorz.search.base import SearchContext

    stage = load_stage("stages/custom/custom_g5_combo.json")
    assert stage.id == "custom_g5_combo"
    assert stage.group == "G5"

    ctx = SearchContext()
    path = bfs(stage, ctx)
    assert path is not None
    assert len(path) == 12

    # Replay chuỗi hành động để kiểm chứng
    curr = initial_state(stage)
    for act in path:
        curr = step(curr, act, stage)
        assert curr is not None
    assert is_goal(curr, stage) is True


def test_contributed_stage_custom_g4_split():
    """
    Màn đóng góp 2: custom_g4_split.json (Nhóm G4)
    - Thử thách: Split switch -> 2 cube tách biệt -> Cube 0 đi mở cầu b1
      -> Cube 0 qua cầu phối hợp với Cube 1 -> Tự động ghép lại -> Về Goal 'G'.
    - Giải thành công bằng BFS trong 14 bước.
    """
    from bloxorz.loader import load_stage
    from bloxorz.search.bfs import bfs
    from bloxorz.search.base import SearchContext

    stage = load_stage("stages/custom/custom_g4_split.json")
    assert stage.id == "custom_g4_split"
    assert stage.group == "G4"

    ctx = SearchContext()
    path = bfs(stage, ctx)
    assert path is not None
    assert len(path) == 14

    # Replay chuỗi hành động kiểm tra split và rejoining
    curr = initial_state(stage)
    seen_split = False
    seen_rejoin = False
    for act in path:
        curr = step(curr, act, stage)
        assert curr is not None
        if curr.pose is None:
            seen_split = True
        elif seen_split and curr.pose is not None:
            seen_rejoin = True
    assert seen_split is True
    assert seen_rejoin is True
    assert is_goal(curr, stage) is True

