"""
Kiểm thử cho khung tìm kiếm (search/base.py) - Task 1.3
Bao gồm 8 bài test mock solver kiểm tra toàn bộ các nhánh hành vi của run(), SearchContext, reconstruct.
"""

import threading
import pytest

from bloxorz.model import Action, Direction, Pose, State
from bloxorz.stage import Stage
from bloxorz.search.base import (
    ALGORITHMS,
    Limits,
    SearchResult,
    SearchContext,
    reconstruct,
    register,
    run,
)


@pytest.fixture
def dummy_stage():
    """Tạo một stage đơn giản dùng chung cho các test."""
    return Stage(
        id="dummy",
        group="G1",
        grid=("###", "###"),
        start=(0, 0),
        goal=(1, 2),
    )


@pytest.fixture(autouse=True)
def clean_registry():
    """Tự động dọn dẹp các mock solver sau mỗi bài test để không làm bẩn ALGORITHMS."""
    before = set(ALGORITHMS.keys())
    yield
    added = set(ALGORITHMS.keys()) - before
    for k in added:
        ALGORITHMS.pop(k, None)


# 1. Test Solved: Tìm thấy lời giải
def test_run_solved(dummy_stage):
    @register("mock_solved")
    def mock_solved(stage, ctx):
        ctx.tick()
        return (
            Action(Direction.RIGHT),
            Action(Direction.DOWN),
            Action(Direction.RIGHT),
        )

    res = run("mock_solved", dummy_stage)
    assert res.status == "solved"
    assert res.length == 3
    assert res.cost == 3.0
    assert len(res.actions) == 3
    assert res.expanded == 1
    assert res.time_s >= 0.0


# 2. Test Unsolvable: Không có lời giải
def test_run_unsolvable(dummy_stage):
    @register("mock_unsolvable")
    def mock_unsolvable(stage, ctx):
        ctx.tick()
        return None

    res = run("mock_unsolvable", dummy_stage)
    assert res.status == "unsolvable"
    assert res.actions == ()
    assert res.length == 0
    assert res.expanded == 1


# 3. Test Timeout: Dừng khi quá thời gian cho phép
def test_run_timeout(dummy_stage):
    @register("mock_timeout")
    def mock_timeout(stage, ctx):
        while True:
            ctx.tick()

    limits = Limits(timeout_s=0.1)
    res = run("mock_timeout", dummy_stage, limits=limits)
    assert res.status == "timeout"
    assert res.actions == ()
    assert res.time_s >= 0.09
    assert res.time_s <= 1.0


# 4. Test Cancelled: Dừng khi có cờ hủy
def test_run_cancelled(dummy_stage):
    @register("mock_cancel")
    def mock_cancel(stage, ctx):
        while True:
            ctx.tick()

    cancel_event = threading.Event()
    cancel_event.set()  # Giương cờ hủy trước khi chạy
    limits = Limits(timeout_s=10.0, cancel=cancel_event)

    res = run("mock_cancel", dummy_stage, limits=limits)
    assert res.status == "cancelled"
    assert res.actions == ()


# 5. Test Exception / Error: Bắt lỗi khi solver bị crash
def test_run_exception_error(dummy_stage):
    @register("mock_crash")
    def mock_crash(stage, ctx):
        raise ValueError("Lỗi tính toán bên trong!")

    res = run("mock_crash", dummy_stage)
    assert res.status == "error"
    assert "Lỗi tính toán bên trong!" in res.message


# 6. Test Measure Memory: Đo bộ nhớ RAM
def test_run_measure_memory(dummy_stage):
    @register("mock_alloc")
    def mock_alloc(stage, ctx):
        ctx.tick()
        # Cấp phát bộ nhớ
        _ = [i for i in range(10000)]
        return (Action(Direction.RIGHT),)

    res = run("mock_alloc", dummy_stage, measure_memory=True)
    assert res.status == "solved"
    assert res.peak_mem_bytes is not None
    assert res.peak_mem_bytes > 0


# 7. Test Reconstruct: Dựng ngược đường đi chính xác
def test_reconstruct():
    s0 = State(Pose.STANDING, (0, 0))
    s1 = State(Pose.HORIZONTAL, (0, 1))
    s2 = State(Pose.STANDING, (0, 3))

    a1 = Action(Direction.RIGHT)
    a2 = Action(Direction.RIGHT)

    parents = {
        s0: None,
        s1: (s0, a1),
        s2: (s1, a2),
    }

    actions = reconstruct(parents, s2)
    assert actions == (a1, a2)

    # Nếu đích chính là điểm xuất phát
    assert reconstruct(parents, s0) == ()


# 8. Test Unknown Algorithm: Thuật toán chưa đăng ký
def test_run_unknown_algorithm(dummy_stage):
    res = run("chua_dang_ky", dummy_stage)
    assert res.status == "error"
    assert "not registered" in res.message


# 9. Test phòng thủ: Reconstruct không bị lặp vô tận khi parents có chu trình
def test_reconstruct_cycle_prevention():
    s1 = State(Pose.STANDING, (0, 0))
    s2 = State(Pose.HORIZONTAL, (0, 1))
    a = Action(Direction.RIGHT)
    # Chu trình s1 -> s2 -> s1
    parents = {
        s1: (s2, a),
        s2: (s1, a),
    }
    # Phải ngắt an toàn và không bị treo máy vĩnh viễn
    actions = reconstruct(parents, s2)
    assert len(actions) <= 2


# 10. Test phòng thủ: Lượt 2 đo RAM bị timeout/lỗi không làm sập hàm run()
def test_run_measure_memory_handles_abort(dummy_stage):
    call_count = 0

    @register("mock_flaky_mem")
    def mock_flaky_mem(stage, ctx):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Lượt 1: Thành công
            return (Action(Direction.RIGHT),)
        else:
            # Lượt 2: Bị crash hoặc timeout
            raise TimeoutError("RAM measurement timed out")

    res = run("mock_flaky_mem", dummy_stage, measure_memory=True)
    assert res.status == "solved"
    assert len(res.actions) == 1
