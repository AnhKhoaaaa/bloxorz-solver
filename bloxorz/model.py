# Phụ trách: VT1 - Task 1.2
"""
Khung dữ liệu cốt lõi cho game Bloxorz:
- Pos: Tọa độ ô lưới (hàng, cột)
- Direction: 4 hướng di chuyển (U, D, L, R)
- Pose: 3 tư thế của khối Bloxorz (STANDING, HORIZONTAL, VERTICAL)
- State: Trạng thái bất biến của khối và các cầu đang mở
- Action: Nước đi gồm hướng và khối được chọn khi tách
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

Pos = tuple[int, int]  # (hàng, cột), (0,0) ở góc trên-trái

class Direction(Enum):
    UP = "U"
    DOWN = "D"
    LEFT = "L"
    RIGHT = "R"

class Pose(Enum):
    STANDING = 0     # Khối đứng thẳng trên 1 ô (1x1)
    HORIZONTAL = 1   # Khối nằm ngang chiếm 1 hàng 2 cột (1x2)
    VERTICAL = 2     # Khối nằm dọc chiếm 2 hàng 1 cột (2x1)

@dataclass(frozen=True, slots=True)
class State:
    """
    Trạng thái của khối Bloxorz và các cầu trên bàn chơi:
    - pose: Tư thế khối (STANDING, HORIZONTAL, VERTICAL), hoặc None khi tách thành 2 cube 1x1.
    - pos: Ô trên-trái của khối (hoặc tọa độ cube thứ nhất khi tách).
    - cube2: Tọa độ cube thứ hai khi tách (None khi còn nguyên khối 1x1x2).
    - bridges_open: Tập hợp các id cầu đang ở trạng thái mở.
    """
    pose: Pose | None          # None khi đang tách
    pos: Pos                   # ô trên-trái của khối, hoặc cube thứ nhất khi tách
    cube2: Pos | None = None   # cube thứ hai; luôn có pos < cube2
    bridges_open: frozenset[str] = frozenset()

    def __post_init__(self):
        # Tự động chuẩn hóa: nếu tách 2 cube, luôn giữ pos < cube2
        # Giúp 2 trạng thái có cùng vị trí 2 cube luôn bằng nhau và có cùng hash
        if self.cube2 is not None and self.cube2 < self.pos:
            first, second = self.cube2, self.pos
            object.__setattr__(self, "pos", first)
            object.__setattr__(self, "cube2", second)

@dataclass(frozen=True, slots=True)
class Action:
    """
    Hành động di chuyển:
    - direction: Hướng lăn/đi (UP, DOWN, LEFT, RIGHT).
    - cube: None khi khối nguyên vẹn; 0 hoặc 1 khi đang tách thành 2 cube.
    """
    direction: Direction
    cube: int | None = None    # None = khối nguyên; 0 hoặc 1 khi đang tách
