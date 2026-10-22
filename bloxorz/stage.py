# Phụ trách: VT1 - Task 1.2
"""
Cấu trúc dữ liệu cho màn chơi Bloxorz:
- SwitchKind, SwitchMode: Các loại công tắc và chế độ hoạt động
- Bridge: Cầu gồm các ô và trạng thái ban đầu
- Switch: Công tắc (mềm, nặng, tách) điều khiển cầu (theo từng cầu qua actions) hoặc phân tách khối
- Stage: Bản đồ màn chơi bất biến, hỗ trợ truy vấn ô, công tắc và cầu
"""

from __future__ import annotations
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
from typing import Literal, Mapping

from bloxorz.model import Pos

SwitchKind = Literal["soft", "heavy", "split"]
SwitchMode = Literal["toggle", "permanent"]
BridgeAction = Literal["toggle", "open", "close"]

@dataclass(frozen=True)
class Bridge:
    """
    Cầu gồm một hoặc nhiều ô gạch:
    - id: Định danh duy nhất của cầu (ví dụ: "b1", "b2").
    - cells: Danh sách tọa độ các ô thuộc cây cầu.
    - initially_open: Trạng thái ban đầu (True nếu cầu đang mở/nối sàn, False nếu đang đóng/hổng).
    """
    id: str
    cells: tuple[Pos, ...]
    initially_open: bool = False

@dataclass(frozen=True)
class Switch:
    """
    Công tắc trên sàn:
    - id: Định danh công tắc.
    - kind: "soft" (công tắc mềm), "heavy" (công tắc nặng), "split" (công tắc phân tách).
    - pos: Tọa độ đặt công tắc.
    - mode: "toggle" (đảo trạng thái cầu) hoặc "permanent" (chỉ đóng hoặc chỉ mở 1 lần). Bắt buộc với soft/heavy; split là None.
    - set_to: Chỉ áp dụng khi mode="permanent" ("open" hoặc "close").
    - bridges: Danh sách id các cầu mà công tắc này điều khiển (với soft/heavy).
    - targets: Tọa độ 2 vị trí đặt 2 cube sau khi tách (với split).
    - actions: Hành động riêng cho từng cầu, dạng ((id cầu, "toggle" | "open" | "close"), ...).
      Engine chỉ cần đọc actions. Bỏ trống thì tự suy ra từ mode/set_to/bridges.
      Công tắc vừa mở cầu này vừa đóng cầu khác chỉ khai báo actions (mode=None, bridges tự điền).
    """
    id: str
    kind: SwitchKind
    pos: Pos
    mode: SwitchMode | None = None          # soft/heavy (trừ khi chỉ khai báo actions); split: None
    set_to: Literal["open", "close"] = "open"  # chỉ dùng khi mode="permanent"
    bridges: tuple[str, ...] = ()           # soft/heavy: id các cầu điều khiển
    targets: tuple[Pos, Pos] | None = None  # split: 2 ô cube xuất hiện khi nhấn
    actions: tuple[tuple[str, BridgeAction], ...] = ()  # soft/heavy: hành động theo từng cầu

    def __post_init__(self):
        if self.actions:
            acts = tuple((b, a) for b, a in self.actions)
            object.__setattr__(self, "actions", acts)
            inferred_bridges = tuple(b for b, _ in acts)
            if self.bridges and tuple(self.bridges) != inferred_bridges:
                raise ValueError(
                    f"bridges {self.bridges} does not match actions {inferred_bridges}"
                )
            object.__setattr__(self, "bridges", inferred_bridges)
        elif self.mode is not None:
            action = "toggle" if self.mode == "toggle" else self.set_to
            object.__setattr__(self, "actions", tuple((b, action) for b in self.bridges))

@dataclass(frozen=True)
class Stage:
    """
    Dữ liệu một màn chơi hoàn chỉnh (bất biến - frozen):
    - id: Mã màn chơi (ví dụ: "stage_01", "bench_g1_01").
    - group: Nhóm màn chơi ("G1".."G5").
    - grid: Lưới ký tự mô tả sàn chơi (mỗi chuỗi là 1 hàng). Ô 'S' đã được chuẩn hóa thành '#'.
    - start: Tọa độ ô xuất phát của khối (vị trí ban đầu ở tư thế STANDING).
    - goal: Tọa độ lỗ đích 'G'.
    - bridges: Bộ dữ liệu các cây cầu trong màn.
    - switches: Bộ dữ liệu các công tắc trong màn.
    """
    id: str
    group: str
    grid: tuple[str, ...]
    start: Pos
    goal: Pos
    bridges: tuple[Bridge, ...] = ()
    switches: tuple[Switch, ...] = ()

    @property
    def rows(self) -> int:
        """Số hàng của lưới."""
        return len(self.grid)

    @property
    def cols(self) -> int:
        """Số cột lớn nhất của lưới."""
        return max((len(r) for r in self.grid), default=0)

    def in_bounds(self, p: Pos) -> bool:
        """Kiểm tra tọa độ p có nằm trong giới hạn lưới hay không."""
        r, c = p
        return 0 <= r < len(self.grid) and 0 <= c < len(self.grid[r])

    def cell(self, p: Pos) -> str:
        """
        Lấy loại ô tại tọa độ p.
        Trả về '.' (khoảng trống ngoài sàn) nếu tọa độ nằm ngoài bàn chơi.
        """
        r, c = p
        if 0 <= r < len(self.grid) and 0 <= c < len(self.grid[r]):
            return self.grid[r][c]
        return "."

    @cached_property
    def switch_at(self) -> Mapping[Pos, Switch]:
        """Bảng tra cứu công tắc theo tọa độ đặt công tắc (bất biến / read-only)."""
        return MappingProxyType({s.pos: s for s in self.switches})

    @cached_property
    def bridge_at(self) -> Mapping[Pos, str]:
        """Bảng tra cứu id cầu theo từng tọa độ ô cầu (bất biến / read-only)."""
        mapping: dict[Pos, str] = {}
        for b in self.bridges:
            for cell_pos in b.cells:
                mapping[cell_pos] = b.id
        return MappingProxyType(mapping)

    def initial_bridges_open(self) -> frozenset[str]:
        """Trả về tập hợp các id cầu ở trạng thái mở ban đầu."""
        return frozenset(b.id for b in self.bridges if b.initially_open)
