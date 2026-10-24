# Phụ trách: VT2 - Task 2.3
"""
Kiểm thử toàn diện cho cơ chế công tắc mềm (soft switch), công tắc nặng (heavy switch) và cầu (bridges) - Task 2.3.

Theo Section 2.5 của đặc tả đồ án:
1. Soft switch (hình tròn/bát giác):
   - Kích hoạt khi bất kỳ phần nào của khối đè lên nó (STANDING, HORIZONTAL, VERTICAL).
2. Heavy switch (chữ X):
   - Chỉ kích hoạt khi khối ĐỨNG THẲNG (STANDING) trên ô công tắc.
   - Nằm ngang hoặc nằm dọc đè qua ô công tắc nặng sẽ KHÔNG kích hoạt.
3. Cầu (Bridges):
   - Cầu đóng đóng vai trò như khoảng trống/void (bước lên sẽ rơi/thua).
   - Cầu mở hoạt động như ô sàn thường (bước lên an toàn).
   - Các chế độ hoạt động: toggle (đảo trạng thái), permanent open, permanent close, hoặc actions kết hợp.
4. Tương tác lăn khối (step):
   - Khối lăn lên công tắc: mở hoặc đóng cầu tương ứng.
   - Nếu công tắc làm sập cây cầu mà khối đang đứng đè lên: khối bị rơi.
   - Vượt qua màn chơi có cầu và công tắc (fixtures và stage_02 gốc).
"""

import pytest

from bloxorz.engine.rules import initial_state, is_goal, is_valid_state, step
from bloxorz.engine.switches import (
    apply_bridge_action,
    apply_switch,
    can_activate_switch,
    trigger_switches,
)
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Bridge, Stage, Switch


# ==============================================================================
# 1. Kiểm tra logic điều kiện kích hoạt công tắc (can_activate_switch)
# ==============================================================================

def test_can_activate_switch_soft():
    """Soft switch luôn kích hoạt với mọi tư thế (đứng, nằm ngang, nằm dọc, cube tách)."""
    sw = Switch(id="s_soft", kind="soft", pos=(1, 1), mode="toggle", bridges=("b1",))

    assert can_activate_switch(sw, Pose.STANDING) is True
    assert can_activate_switch(sw, Pose.HORIZONTAL) is True
    assert can_activate_switch(sw, Pose.VERTICAL) is True
    assert can_activate_switch(sw, None) is True  # Khối tách thành 1x1x1 cube


def test_can_activate_switch_heavy():
    """Heavy switch CHỈ kích hoạt khi khối ở tư thế STANDING."""
    sw = Switch(id="s_heavy", kind="heavy", pos=(1, 1), mode="toggle", bridges=("b1",))

    assert can_activate_switch(sw, Pose.STANDING) is True
    assert can_activate_switch(sw, Pose.HORIZONTAL) is False
    assert can_activate_switch(sw, Pose.VERTICAL) is False
    assert can_activate_switch(sw, None) is False  # Cube 1x1 không kích hoạt được heavy switch


def test_can_activate_switch_split():
    """Split switch chỉ kích hoạt khi khối ở tư thế STANDING."""
    sw = Switch(id="s_split", kind="split", pos=(1, 1), targets=((0, 0), (0, 1)))

    assert can_activate_switch(sw, Pose.STANDING) is True
    assert can_activate_switch(sw, Pose.HORIZONTAL) is False
    assert can_activate_switch(sw, Pose.VERTICAL) is False
    assert can_activate_switch(sw, None) is False


# ==============================================================================
# 2. Kiểm tra thao tác cầu đơn lẻ (apply_bridge_action) và công tắc (apply_switch)
# ==============================================================================

def test_apply_bridge_action_toggle():
    """Hành động toggle đảo giữa mở và đóng."""
    # Đang đóng -> Mở
    bridges = frozenset()
    b_after_open = apply_bridge_action(bridges, "b1", "toggle")
    assert b_after_open == frozenset({"b1"})

    # Đang mở -> Đóng
    b_after_close = apply_bridge_action(b_after_open, "b1", "toggle")
    assert b_after_close == frozenset()


def test_apply_bridge_action_open_and_close():
    """Hành động open mở cầu, close đóng cầu; lặp lại không đổi."""
    bridges = frozenset()
    # open
    b1 = apply_bridge_action(bridges, "b1", "open")
    assert b1 == frozenset({"b1"})
    # open lại vẫn mở
    assert apply_bridge_action(b1, "b1", "open") == frozenset({"b1"})

    # close
    b0 = apply_bridge_action(b1, "b1", "close")
    assert b0 == frozenset()
    # close lại vẫn đóng
    assert apply_bridge_action(b0, "b1", "close") == frozenset()


def test_apply_switch_multi_actions():
    """Công tắc điều khiển nhiều cầu cùng lúc: mở b1, đóng b2, toggle b3."""
    sw = Switch(
        id="s_multi",
        kind="soft",
        pos=(0, 0),
        actions=(("b1", "open"), ("b2", "close"), ("b3", "toggle")),
    )
    # Trạng thái ban đầu: b2 mở, b3 mở, b1 đóng
    init_bridges = frozenset({"b2", "b3"})
    result = apply_switch(sw, init_bridges)

    # b1 mở, b2 đóng, b3 đảo từ mở sang đóng -> kết quả chỉ còn b1
    assert result == frozenset({"b1"})


# ==============================================================================
# 3. Kiểm tra hàm trigger_switches
# ==============================================================================

def test_trigger_switches_no_switch():
    """Không có công tắc tại vị trí khối tiếp đất -> giữ nguyên cầu."""
    stage = Stage(
        id="no_sw",
        group="G1",
        grid=("###", "###"),
        start=(0, 0),
        goal=(1, 2),
    )
    assert trigger_switches(stage, Pose.STANDING, [(0, 0)], frozenset({"b1"})) == frozenset({"b1"})


def test_trigger_switches_lying_on_heavy_switch_does_not_trigger():
    """Khối nằm đè lên heavy switch -> không kích hoạt, cầu giữ nguyên."""
    sw = Switch(id="sw1", kind="heavy", pos=(0, 1), mode="toggle", bridges=("b1",))
    stage = Stage(
        id="sw_stage",
        group="G2",
        grid=("####", "####"),
        start=(0, 0),
        goal=(1, 3),
        switches=(sw,),
    )
    # Khối nằm ngang chiếm (0, 0) và (0, 1)
    cells = ((0, 0), (0, 1))
    result = trigger_switches(stage, Pose.HORIZONTAL, cells, frozenset())
    assert result == frozenset()  # Heavy switch không bị kích hoạt


def test_trigger_switches_standing_on_heavy_switch_triggers():
    """Khối đứng thẳng trên heavy switch -> kích hoạt thành công."""
    sw = Switch(id="sw1", kind="heavy", pos=(0, 1), mode="toggle", bridges=("b1",))
    stage = Stage(
        id="sw_stage",
        group="G2",
        grid=("####", "####"),
        start=(0, 0),
        goal=(1, 3),
        switches=(sw,),
    )
    cells = ((0, 1),)
    result = trigger_switches(stage, Pose.STANDING, cells, frozenset())
    assert result == frozenset({"b1"})


# ==============================================================================
# 4. Kiểm tra tương tác qua bước di chuyển (step)
# ==============================================================================

@pytest.fixture
def soft_toggle_stage():
    """
    Màn kiểm thử soft switch toggle:
    Hàng 0: S # # B B # # G
    s1 (soft toggle) tại (0, 2), điều khiển cầu b1 tại (0, 3), (0, 4).
    Ban đầu b1 đóng.
    """
    bridge = Bridge(id="b1", cells=((0, 3), (0, 4)), initially_open=False)
    sw = Switch(id="s1", kind="soft", pos=(0, 2), mode="toggle", bridges=("b1",))
    return Stage(
        id="test_soft_toggle",
        group="G2",
        grid=("S##BB##G",),
        start=(0, 0),
        goal=(0, 7),
        bridges=(bridge,),
        switches=(sw,),
    )


def test_step_soft_switch_activates_lying_and_opens_bridge(soft_toggle_stage):
    """
    Từ (0, 0) STANDING:
    - Lăn R -> HORIZONTAL tại (0, 1) chiếm (0, 1) và (0, 2).
    - Ô (0, 2) có soft switch s1 -> s1 được kích hoạt ở tư thế nằm -> mở cầu b1!
    """
    s0 = initial_state(soft_toggle_stage)
    assert s0.bridges_open == frozenset()

    s1 = step(s0, Action(Direction.RIGHT), soft_toggle_stage)
    assert s1 is not None
    assert s1.pose == Pose.HORIZONTAL
    assert s1.pos == (0, 1)
    # Soft switch đã được kích hoạt khi khối nằm đè lên (0, 2)!
    assert s1.bridges_open == frozenset({"b1"})

    # Bây giờ cầu b1 đã mở -> lăn R tiếp để STANDING lên ô cầu (0, 3) an toàn!
    s2 = step(s1, Action(Direction.RIGHT), soft_toggle_stage)
    assert s2 is not None
    assert s2.pose == Pose.STANDING
    assert s2.pos == (0, 3)
    assert s2.bridges_open == frozenset({"b1"})


def test_step_closed_bridge_causes_fall_without_triggering():
    """Nếu cầu chưa mở, lăn khối lên cầu sẽ bị rơi (step trả về None)."""
    bridge = Bridge(id="b1", cells=((0, 2), (0, 3)), initially_open=False)
    stage = Stage(
        id="bridge_closed",
        group="G2",
        grid=("##BB##G",),
        start=(0, 0),
        goal=(0, 6),
        bridges=(bridge,),
    )
    s0 = initial_state(stage)
    # Lăn R -> HORIZONTAL tại (0, 1) chiếm (0, 1) [#] và (0, 2) [B đóng] -> Rơi!
    assert step(s0, Action(Direction.RIGHT), stage) is None


@pytest.fixture
def heavy_switch_stage():
    """
    Màn kiểm thử heavy switch:
    Sàn:
    S # # # B B # G
    Heavy switch s1 tại (0, 3), điều khiển cầu b1 tại (0, 4), (0, 5).
    Ban đầu b1 đóng.
    """
    bridge = Bridge(id="b1", cells=((0, 4), (0, 5)), initially_open=False)
    sw = Switch(id="s1", kind="heavy", pos=(0, 3), mode="permanent", set_to="open", bridges=("b1",))
    return Stage(
        id="test_heavy_stage",
        group="G2",
        grid=("S###BB#G",),
        start=(0, 0),
        goal=(0, 7),
        bridges=(bridge,),
        switches=(sw,),
    )


def test_step_heavy_switch_ignored_when_lying_then_activated_when_standing(heavy_switch_stage):
    """
    Khối di chuyển qua heavy switch:
    - (0, 0) STANDING
    - Lăn R -> (0, 1) HORIZONTAL chiếm (0, 1) và (0, 2) (chưa chạm switch)
    - Lăn R -> (0, 3) STANDING ngay trên heavy switch tại (0, 3) -> Kích hoạt! b1 mở!
    """
    s0 = initial_state(heavy_switch_stage)
    s1 = step(s0, Action(Direction.RIGHT), heavy_switch_stage)
    assert s1 is not None
    assert s1.bridges_open == frozenset()

    # Lăn R tiếp -> ĐỨNG tại (0, 3)
    s2 = step(s1, Action(Direction.RIGHT), heavy_switch_stage)
    assert s2 is not None
    assert s2.pose == Pose.STANDING
    assert s2.pos == (0, 3)
    # Heavy switch kích hoạt vì khối STANDING!
    assert s2.bridges_open == frozenset({"b1"})


def test_step_heavy_switch_lying_across_does_not_activate():
    """
    Heavy switch đặt tại ô (0, 2).
    Từ (0, 0) STANDING, lăn R -> HORIZONTAL chiếm (0, 1) và (0, 2).
    Khối nằm đè lên (0, 2) nhưng vì là heavy switch nên KHÔNG kích hoạt.
    """
    bridge = Bridge(id="b1", cells=((0, 4),), initially_open=False)
    sw = Switch(id="s1", kind="heavy", pos=(0, 2), mode="permanent", set_to="open", bridges=("b1",))
    st = Stage(
        id="heavy_lying",
        group="G2",
        grid=("###.B.G",),
        start=(0, 0),
        goal=(0, 6),
        bridges=(bridge,),
        switches=(sw,),
    )
    s0 = initial_state(st)
    s1 = step(s0, Action(Direction.RIGHT), st)
    assert s1 is not None
    assert s1.pose == Pose.HORIZONTAL
    assert (0, 2) in ((0, 1), (0, 2))
    # Vì nằm đè lên heavy switch -> không kích hoạt -> cầu vẫn đóng!
    assert s1.bridges_open == frozenset()


def test_step_switch_collapses_bridge_under_block():
    """
    Nếu công tắc đóng/sập cây cầu mà khối đang đứng đè một phần lên,
    khối sẽ mất điểm tựa và bị rơi (step trả về None).
    """
    # Cầu b1 mở sẵn tại (0, 2). Soft switch tại (0, 1) có lệnh đóng b1.
    bridge = Bridge(id="b1", cells=((0, 2),), initially_open=True)
    sw = Switch(id="s1", kind="soft", pos=(0, 1), mode="permanent", set_to="close", bridges=("b1",))
    st = Stage(
        id="bridge_collapse",
        group="G2",
        grid=("###G",),
        start=(0, 0),
        goal=(0, 3),
        bridges=(bridge,),
        switches=(sw,),
    )
    s0 = initial_state(st)
    assert s0.bridges_open == frozenset({"b1"})

    # Lăn R -> HORIZONTAL chiếm (0, 1) [chứa switch s1] và (0, 2) [chứa cầu b1].
    # Switch s1 đóng b1 -> ô (0, 2) trở thành void -> khối rơi!
    next_s = step(s0, Action(Direction.RIGHT), st)
    assert next_s is None


# ==============================================================================
# 5. Kiểm thử với file fixture chính thức
# ==============================================================================

def test_solve_fixture_bridge_soft():
    """Giải hoàn chỉnh màn fixture_bridge_soft bằng các bước lăn."""
    stage = load_stage("stages/fixtures/bridge_soft.json")
    s = initial_state(stage)
    assert s.bridges_open == frozenset()

    # Màn: S###BB###G
    # Start (0, 0). Switch s1 tại (0, 1) soft toggle b1 ([0, 4], [0, 5]). Goal (0, 9).
    # 1. R -> HORIZ tại (0, 1) chiếm (0, 1) và (0, 2) -> chạm s1 -> b1 mở!
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and "b1" in s.bridges_open

    # 2. R -> STAND tại (0, 3)
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None

    # 3. R -> HORIZ tại (0, 4) chiếm (0, 4) và (0, 5) (nằm trên cầu b1)
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and s.pos == (0, 4)

    # 4. R -> STAND tại (0, 6)
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and s.pos == (0, 6)

    # 5. R -> HORIZ tại (0, 7) chiếm (0, 7) và (0, 8)
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and s.pos == (0, 7)

    # 6. R -> STAND tại (0, 9) là ô Goal!
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and is_goal(s, stage)


def test_solve_fixture_bridge_heavy():
    """Giải hoàn chỉnh màn fixture_bridge_heavy bằng các bước lăn."""
    stage = load_stage("stages/fixtures/bridge_heavy.json")
    s = initial_state(stage)
    assert s.bridges_open == frozenset()

    # Màn: S###BB###G
    # Start (0, 0). Heavy switch tại (0, 3) mở b1. Goal (0, 9).
    # 1. R -> HORIZ tại (0, 1) chiếm (0, 1), (0, 2)
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and "b1" not in s.bridges_open

    # 2. R -> STAND tại (0, 3) trên heavy switch -> b1 mở!
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and "b1" in s.bridges_open

    # 3. R -> HORIZ tại (0, 4) chiếm (0, 4), (0, 5) trên cầu b1
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None

    # 4. R -> STAND tại (0, 6)
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None

    # 5. R -> HORIZ tại (0, 7)
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None

    # 6. R -> STAND tại (0, 9) Goal!
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and is_goal(s, stage)


# ==============================================================================
# 6. Kiểm thử tương tác với màn chơi gốc stage_02.json
# ==============================================================================

def test_stage_02_mechanics_and_path():
    """
    Kiểm tra cơ chế hoạt động thực tế trên stage_02.json:
    - Xuất phát tại (4, 1).
    - Đến (2, 2) chạm soft switch s2 -> mở bridgeA tại hàng 4.
    - Đi qua bridgeA sang đảo giữa.
    - Tại đảo giữa, đứng lên heavy switch s1 tại (1, 8) -> mở bridgeB tại hàng 4.
    - Đi qua bridgeB về đích Goal tại (1, 13).
    """
    stage = load_stage("stages/original/stage_02.json")
    s = initial_state(stage)
    assert s.bridges_open == frozenset()
    assert s.pos == (4, 1)

    # 1. Từ (4, 1) STANDING -> U -> VERTICAL tại (2, 1) chiếm (2, 1) và (3, 1)
    s = step(s, Action(Direction.UP), stage)
    assert s is not None

    # 2. Từ (2, 1) VERTICAL -> R -> VERTICAL tại (2, 2) chiếm (2, 2) và (3, 2)
    # Ô (2, 2) có soft switch s2 -> kích hoạt s2 -> mở bridgeA!
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None
    assert "bridgeA" in s.bridges_open
    assert "bridgeB" not in s.bridges_open

    # 3. Lăn xuống D -> STANDING tại (4, 2)
    s = step(s, Action(Direction.DOWN), stage)
    assert s is not None and s.pos == (4, 2)

    # 4. Lăn R -> HORIZONTAL tại (4, 3) chiếm (4, 3) [#] và (4, 4) [bridgeA mở!]
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and s.pos == (4, 3)

    # 5. Lăn R -> STANDING tại (4, 5) [bridgeA mở!]
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and s.pos == (4, 5)

    # 6. Lăn R -> HORIZONTAL tại (4, 6) chiếm (4, 6) và (4, 7) [đảo giữa]
    s = step(s, Action(Direction.RIGHT), stage)
    assert s is not None and s.pos == (4, 6)
