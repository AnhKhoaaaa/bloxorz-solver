# Phụ trách: VT1 - Task 1.3
"""Khung chung cho solver: SearchContext, Limits, SearchResult, register, run()."""
from __future__ import annotations

import threading
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Callable, Any
from bloxorz.model import Action, Direction, State
from bloxorz.stage import Stage

# Thứ tự duyệt rẽ nhánh chuẩn toàn dự án để đảm bảo tính công bằng và tất định khi Benchmark:
ORDERED_DIRECTIONS: tuple[Direction, ...] = (
    Direction.UP,
    Direction.DOWN,
    Direction.LEFT,
    Direction.RIGHT,
)

@dataclass(frozen=True)
class Limits:
    timeout_s: float = 60.0
    cancel: threading.Event | None = None

@dataclass(frozen=True)
class SearchResult:
    algorithm: str
    stage_id: str
    status: str             # "solved" | "unsolvable" | "timeout" | "cancelled" | "error"
    actions: tuple[Action, ...] = ()
    length: int = 0
    cost: float = 0.0
    expanded: int = 0
    time_s: float = 0.0
    peak_mem_bytes: int | None = None
    message: str = ""
    # time_s gồm tiền xử lý và tìm kiếm; không gồm lượt đo RAM/replay cost.
    prep_time_s: float = 0.0
    search_time_s: float = 0.0
    
class SearchAborted(Exception):
    def __init__(self, status: str):
        super().__init__(status)
        self.status = status

class SearchContext:
    """
    Bộ ngữ cảnh điều phối tiến trình tìm kiếm:
    - Lưu giới hạn (limits) và thời hạn kết thúc (deadline).
    - Đếm số nút đã mở rộng (expanded).
    - Cung cấp hàm tick() để thuật toán gọi mỗi khi duyệt một nút.
    """
    def __init__(self, limits: Limits | None = None):
        self.limits = limits or Limits()
        self.expanded: int = 0
        self.prep_time_s: float = 0.0
        self.deadline: float = time.perf_counter() + self.limits.timeout_s

    def tick(self) -> None:
        """
        Gọi MỖI LẦN mở rộng một nút trạng thái:
        - Tăng self.expanded lên 1.
        - Kiểm tra cờ hủy (cancel) nếu có.
        - Cứ mỗi 256 nút kiểm tra thời gian hết hạn (deadline) 1 lần bằng bitwise check.
        """
        self.expanded += 1
        # 1. Kiểm tra cờ hủy
        if self.limits.cancel is not None and self.limits.cancel.is_set():
            raise SearchAborted("cancelled")
        # 2. Kiểm tra timeout định kỳ mỗi 256 nút
        if (self.expanded & 255) == 0:
            if time.perf_counter() > self.deadline:
                raise SearchAborted("timeout")

    def observe(self, state: State, frontier: int, g: float | None = None) -> None:
        """Gọi ngay sau tick() với nút vừa mở rộng, kích thước frontier và chi phí g(n).
        Mặc định không làm gì; trace.TraceContext ghi lại cho visualizer."""

# Kiểu hàm solver: nhận (stage, ctx) -> trả về tuple các Action hoặc None (nếu không giải được)
SolverFn = Callable[[Stage, SearchContext], tuple[Action, ...] | None]
ALGORITHMS: dict[str, SolverFn] = {}

def register(name: str):
    """Decorator để đăng ký một thuật toán tìm kiếm vào danh sách ALGORITHMS."""
    def decorator(fn: SolverFn) -> SolverFn:
        ALGORITHMS[name] = fn
        return fn
    return decorator

def reconstruct(parents: dict[State, tuple[State, Action] | None], goal: State) -> tuple[Action, ...]:
    """
    Tái tạo lại danh sách các Action từ điểm xuất phát đến đích:
    - Truy vết ngược từ goal về start thông qua từ điển parents.
    - Đảo ngược lại danh sách để có thứ tự hành động từ đầu đến cuối.
    """
    actions: list[Action] = []
    curr: State = goal
    # Tránh trường hợp lặp vô tận
    seen: set[State] = set()
    while curr is not None and curr in parents and curr not in seen:
        seen.add(curr)
        entry = parents[curr]
        if entry is None:
            break
        parent_state, action = entry
        actions.append(action)
        curr = parent_state

    # Đảo ngược lại vì ta đang nhặt action từ đích lùi về xuất phát
    actions.reverse()
    return tuple(actions)

def run(
    algorithm: str,
    stage: Stage,
    limits: Limits | None = None,
    measure_memory: bool = False,
) -> SearchResult:
    """
    Thực thi một thuật toán tìm kiếm trên màn chơi đã cho với giới hạn limits:
    - Lượt 1: Đo thời gian chạy chính xác time_s và lấy actions.
    - Lượt 2: (Tùy chọn) Đo bộ nhớ RAM đỉnh điểm peak_mem_bytes bằng tracemalloc.
    - Trả về đối tượng SearchResult hoàn chỉnh.
    """
    if limits is None:
        limits = Limits()

    # 1. Tra cứu thuật toán
    fn = ALGORITHMS.get(algorithm)
    if fn is None:
        return SearchResult(
            algorithm=algorithm,
            stage_id=stage.id,
            status="error",
            message=f"Algorithm '{algorithm}' is not registered",
        )

    # 2. Lượt 1: Đo thời gian chạy tinh khiết
    ctx = SearchContext(limits)
    actions: tuple[Action, ...] = ()
    status: str = "error"
    message: str = ""
    time_s: float = 0.0

    t_start = time.perf_counter()
    try:
        res = fn(stage, ctx)
        if res is not None:
            status = "solved"
            actions = tuple(res)
        else:
            status = "unsolvable"
    except SearchAborted as e:
        status = e.status
    except Exception as e:
        status = "error"
        message = str(e)
    finally:
        time_s = time.perf_counter() - t_start

    expanded = ctx.expanded

    # 3. Lượt 2: Đo RAM (chỉ khi có yêu cầu và Lượt 1 không bị lỗi/timeout)
    peak_mem_bytes: int | None = None
    if measure_memory and status in ("solved", "unsolvable"):
        mem_ctx = SearchContext(limits)
        tracemalloc.start()
        try:
            fn(stage, mem_ctx)
            peak_mem_bytes = tracemalloc.get_traced_memory()[1]
        except (SearchAborted, Exception):
            peak_mem_bytes = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()

    # 4. Tính chi phí cost và length
    length = len(actions)
    cost = float(length)
    if actions:
        try:
            from .cost import move_cost
            from ..engine import initial_state, step

            s = initial_state(stage)
            total_cost = 0.0
            for act in actions:
                nxt = step(s, act, stage)
                if nxt is None:
                    total_cost = float(length)
                    break
                total_cost += move_cost(s, act, nxt, stage)
                s = nxt
            cost = total_cost
        except (ImportError, Exception):
            cost = float(length)

    return SearchResult(
        algorithm=algorithm,
        stage_id=stage.id,
        status=status,
        actions=actions,
        length=length,
        cost=cost,
        expanded=expanded,
        time_s=time_s,
        peak_mem_bytes=peak_mem_bytes,
        message=message,
        prep_time_s=ctx.prep_time_s,
        search_time_s=max(0.0, time_s - ctx.prep_time_s),
    )
