"""Kiểm thử thuật toán DFS (Graph-search) - Task 1.5."""

import threading
import pytest
from bloxorz.model import Action, Direction
from bloxorz.stage import Stage
from bloxorz.loader import load_stage
from bloxorz.search import run
from bloxorz.search.dfs import dfs
from bloxorz.search.base import Limits
from bloxorz.verify import verify_solution


# 1. Test màn 1 hàng siêu nhỏ: S##G
def test_dfs_tiny_corridor():
    stage = Stage(
        id="tiny",
        group="test",
        grid=("S##G",),
        start=(0, 0),
        goal=(0, 3),
    )
    res = run("dfs", stage)
    assert res.status == "solved"
    assert res.length == 2
    assert res.actions == (Action(Direction.RIGHT), Action(Direction.RIGHT))
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 2. Test xuất phát trùng ngay vạch đích
def test_dfs_start_is_goal():
    stage = Stage(
        id="already_goal",
        group="test",
        grid=("G",),
        start=(0, 0),
        goal=(0, 0),
    )
    res = run("dfs", stage)
    assert res.status == "solved"
    assert res.actions == ()
    assert res.length == 0
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 3. Test giải màn mẫu cơ bản (basic.json) và verify lời giải
def test_dfs_basic_fixture():
    stage = load_stage("stages/fixtures/basic.json")
    res = run("dfs", stage)
    assert res.status == "solved"
    assert res.length > 0
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 4. Test giải màn có gạch mỏng (fragile.json)
def test_dfs_fragile_fixture():
    stage = load_stage("stages/fixtures/fragile.json")
    res = run("dfs", stage)
    assert res.status == "solved"
    assert res.length > 0
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 5. Test giải màn có cơ chế phân tách (split.json)
def test_dfs_split_fixture():
    stage = load_stage("stages/fixtures/split.json")
    res = run("dfs", stage)
    assert res.status == "solved"
    assert res.length > 0
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 6. Test chống lặp vô tận (Graph search trên lưới trống không có đích)
def test_dfs_cyclic_unsolvable_loop():
    # Lưới 5x5 hoàn toàn là gạch '#' nhưng đích ở (99, 99) không thể chạm tới
    grid_5x5 = tuple("#####" for _ in range(5))
    stage = Stage(
        id="loop_no_goal",
        group="test",
        grid=grid_5x5,
        start=(2, 2),
        goal=(99, 99),
    )
    # DFS phải duyệt hết không gian trạng thái hữu hạn và dừng lại, không lặp vô tận
    res = run("dfs", stage, limits=Limits(timeout_s=5.0))
    assert res.status == "unsolvable"
    assert res.actions == ()
    assert res.length == 0


# 7. Test đích bị cô lập giữa vực thẳm
def test_dfs_isolated_goal_unsolvable():
    stage = Stage(
        id="isolated_goal",
        group="test",
        grid=(
            "S#....",
            "##....",
            "....#G",
        ),
        start=(0, 0),
        goal=(2, 5),
    )
    res = run("dfs", stage)
    assert res.status == "unsolvable"
    assert res.actions == ()
    assert res.length == 0


# 8. Test tính đơn định (Deterministic): Cùng 1 màn, chạy nhiều lần ra kết quả y hệt
def test_dfs_deterministic():
    stage = load_stage("stages/fixtures/basic.json")
    res1 = run("dfs", stage)
    res2 = run("dfs", stage)
    assert res1.status == "solved"
    assert res2.status == "solved"
    assert res1.actions == res2.actions
    assert res1.expanded == res2.expanded
    assert res1.length == res2.length


# 9. Test thứ tự ưu tiên rẽ nhánh: UP được duyệt trước tiên
def test_dfs_explores_up_first():
    # Lưới 5x5: Start tại (2, 2).
    # Vì nhánh UP được ưu tiên duyệt trước các nhánh DOWN/LEFT/RIGHT,
    # bước đi đầu tiên của lời giải tìm kiếm trên lưới đối xứng này sẽ là UP.
    grid_5x5 = tuple("#####" for _ in range(5))
    stage = Stage(
        id="grid_5x5_up_priority",
        group="test",
        grid=grid_5x5,
        start=(2, 2),
        goal=(1, 1),
    )
    res = run("dfs", stage)
    assert res.status == "solved"
    assert len(res.actions) > 0
    # Bước đầu tiên luôn là UP do thứ tự push ngược trong stack LIFO
    assert res.actions[0] == Action(Direction.UP)
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 10. Test cờ hủy (Cancelled)
def test_dfs_cancelled():
    stage = load_stage("stages/fixtures/basic.json")
    cancel_event = threading.Event()
    cancel_event.set()

    res = run("dfs", stage, limits=Limits(cancel=cancel_event))
    assert res.status == "cancelled"
    assert res.actions == ()


# 11. Test quá thời gian giới hạn (Timeout)
def test_dfs_timeout():
    # Mê cung lớn 40x40 để chắc chắn duyệt vượt quá ngưỡng tick check
    large_grid = tuple("#" * 40 for _ in range(40))
    stage = Stage(
        id="large_timeout_dfs",
        group="test",
        grid=large_grid,
        start=(20, 20),
        goal=(0, 0),
    )
    res = run("dfs", stage, limits=Limits(timeout_s=0.0))
    assert res.status == "timeout"
    assert res.actions == ()
