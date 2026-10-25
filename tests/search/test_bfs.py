"""Kiểm thử thuật toán BFS và hàm verify_solution - Task 1.4."""

import pytest
from bloxorz.model import Action, Direction
from bloxorz.stage import Stage
from bloxorz.loader import load_stage
from bloxorz.search import run
from bloxorz.search.bfs import bfs
from bloxorz.search.base import SearchContext
from bloxorz.verify import verify_solution


# 1. Test màn 1 hàng siêu nhỏ: S##G
def test_bfs_tiny_corridor():
    stage = Stage(
        id="tiny",
        group="test",
        grid=("S##G",),
        start=(0, 0),
        goal=(0, 3),
    )
    res = run("bfs", stage)
    assert res.status == "solved"
    assert res.length == 2
    assert res.actions == (Action(Direction.RIGHT), Action(Direction.RIGHT))
    ok, _ = verify_solution(stage, res.actions)
    assert ok is True


# 2. Test xuất phát trùng đích
def test_bfs_start_is_goal():
    stage = Stage(
        id="already_goal",
        group="test",
        grid=("G",),
        start=(0, 0),
        goal=(0, 0),
    )
    res = run("bfs", stage)
    assert res.status == "solved"
    assert res.actions == ()
    assert res.length == 0
    ok, _ = verify_solution(stage, res.actions)
    assert ok is True


# 3. Test với màn mẫu fixture basic.json
def test_bfs_basic_fixture():
    stage = load_stage("stages/fixtures/basic.json")
    res = run("bfs", stage)
    assert res.status == "solved"
    assert res.length == 7
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 4. Test verify_solution bắt được gian lận / bước đi sai
def test_verify_solution_detects_invalid_move():
    stage = load_stage("stages/fixtures/basic.json")
    res = run("bfs", stage)
    assert res.status == "solved"

    # Thay đổi bước đi đầu tiên thành UP (rơi xuống vực ngay lập tức)
    tampered_actions = (Action(Direction.UP),) + res.actions[1:]
    ok, msg = verify_solution(stage, tampered_actions)
    assert ok is False
    assert "Fall or violate" in msg

    # Cắt ngắn lời giải (chưa tới đích)
    short_actions = res.actions[:-1]
    ok, msg = verify_solution(stage, short_actions)
    assert ok is False
    assert "Not reach the goal" in msg


# 5. Test màn không thể giải được (Unsolvable)
def test_bfs_unsolvable():
    # Goal bị cô lập giữa các ô vực '.'
    stage = Stage(
        id="unsolvable",
        group="test",
        grid=(
            "S#....",
            "##....",
            "....#G",
        ),
        start=(0, 0),
        goal=(2, 5),
    )
    res = run("bfs", stage)
    assert res.status == "unsolvable"
    assert res.actions == ()
    assert res.length == 0


# 6. Test với màn có gạch mỏng (Fragile tiles)
def test_bfs_fragile_fixture():
    stage = load_stage("stages/fixtures/fragile.json")
    res = run("bfs", stage)
    assert res.status == "solved"
    assert res.length == 4
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""


# 7. Test cờ hủy (Cancelled)
def test_bfs_cancelled():
    import threading
    from bloxorz.search.base import Limits

    stage = load_stage("stages/fixtures/basic.json")
    cancel_event = threading.Event()
    cancel_event.set()  # Giương cờ hủy ngay từ đầu

    res = run("bfs", stage, limits=Limits(cancel=cancel_event))
    assert res.status == "cancelled"
    assert res.actions == ()


# 8. Test hết thời gian cho phép (Timeout)
def test_bfs_timeout():
    from bloxorz.search.base import Limits

    # Tạo mê cung rộng để BFS cần duyệt > 256 nút
    large_grid = tuple("#" * 40 for _ in range(40))
    stage = Stage(
        id="large_timeout",
        group="test",
        grid=large_grid,
        start=(20, 20),
        goal=(0, 0),
    )
    # timeout_s = 0.0 để chắc chắn quá hạn khi kiểm tra ở nút thứ 256
    res = run("bfs", stage, limits=Limits(timeout_s=0.0))
    assert res.status == "timeout"
    assert res.actions == ()


# 9. Test verify_solution phát hiện phần tử không phải Action (Bảo vệ sập hệ thống)
def test_verify_solution_detects_non_action_objects():
    stage = load_stage("stages/fixtures/basic.json")
    # Truyền string thay vì Action
    bad_actions = ["RIGHT", "DOWN"]  # type: ignore
    ok, msg = verify_solution(stage, bad_actions)
    assert ok is False
    assert "invalid action object" in msg


# 10. Test BFS giải màn chơi có cơ chế phân tách (Split switch)
def test_bfs_split_fixture():
    stage = load_stage("stages/fixtures/split.json")
    res = run("bfs", stage)
    assert res.status == "solved"
    assert res.length == 6
    ok, msg = verify_solution(stage, res.actions)
    assert ok is True
    assert msg == ""

    # Test verify_solution hiển thị thông tin cube khi bước đi phân tách vi phạm/rơi
    # res.actions[2] là Action(Direction.RIGHT, cube=0)
    # Thay bằng Action(Direction.UP, cube=1) khiến cube 1 đi lên ô '.' (vực) và rơi
    invalid_split_actions = res.actions[:2] + (Action(Direction.UP, cube=1),) + res.actions[3:]
    ok_inv, msg_inv = verify_solution(stage, invalid_split_actions)
    assert ok_inv is False
    assert "cube = 1" in msg_inv
    assert "Fall or violate" in msg_inv


