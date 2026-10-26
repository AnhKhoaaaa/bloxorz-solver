# Phụ trách: VT3 - Task 3.1 / 3.3
"""Vẽ các ô sàn, ô vỡ, cầu và công tắc."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bloxorz.model import State
    from bloxorz.stage import Stage


def grid_to_world(r: int, c: int) -> tuple[float, float, float]:
    """Chuyển đổi tọa độ lưới (r, c) sang tọa độ không gian 3D (x, y, z)."""
    return float(c), 0.0, -float(r)


class BoardView:
    """Quản lý hiển thị 3D của các ô bàn cờ (sàn, đích, khoảng trống)."""

    def __init__(self) -> None:
        self.tile_entities: list[object] = []

    def clear(self) -> None:
        """Xóa toàn bộ các ô sàn hiện có."""
        from ursina import destroy

        for entity in self.tile_entities:
            destroy(entity)
        self.tile_entities.clear()

    def build(self, stage: Stage, state: State | None = None) -> None:
        """Dựng lại toàn bộ bàn cờ dựa trên thông tin Stage."""
        from ursina import Entity, color

        self.clear()

        # Màu sắc các loại ô cơ bản
        FLOOR_COLOR = color.rgb32(180, 185, 195)
        START_COLOR = color.rgb32(160, 195, 230)
        GOAL_COLOR = color.rgb32(35, 35, 45)         # Lỗ đích tối màu tạo chiều sâu
        FRAGILE_COLOR = color.rgb32(235, 140, 60)    # Ô cam dễ vỡ
        BRIDGE_COLOR = color.rgb32(145, 175, 205)

        for r, row in enumerate(stage.grid):
            for c, char in enumerate(row):
                if char == ".":
                    continue  # Vực thẳm/ô trống -> không tạo sàn

                x, y, z = grid_to_world(r, c)

                if char == "G":
                    # Ô lỗ đích: hạ thấp xuống một chút tạo cảm giác cái hố
                    tile = Entity(
                        model="cube",
                        color=GOAL_COLOR,
                        position=(x, y - 0.2, z),
                        scale=(0.95, 0.2, 0.95),
                    )
                elif char == "S":
                    # Ô xuất phát
                    tile = Entity(
                        model="cube",
                        color=START_COLOR,
                        position=(x, y, z),
                        scale=(0.95, 0.2, 0.95),
                    )
                elif char == "F":
                    # Ô cam dễ vỡ (chuẩn bị trước cho Task 3.3)
                    tile = Entity(
                        model="cube",
                        color=FRAGILE_COLOR,
                        position=(x, y, z),
                        scale=(0.95, 0.15, 0.95),
                    )
                elif char == "B":
                    # Ô cầu nối: chỉ vẽ khi cầu đang mở
                    bid = stage.bridge_at.get((r, c))
                    is_open = state is not None and bid in state.bridges_open
                    if is_open:
                        tile = Entity(
                            model="cube",
                            color=BRIDGE_COLOR,
                            position=(x, y, z),
                            scale=(0.95, 0.2, 0.95),
                        )
                    else:
                        continue
                else:
                    # Sàn gạch thường '#'
                    tile = Entity(
                        model="cube",
                        color=FLOOR_COLOR,
                        position=(x, y, z),
                        scale=(0.95, 0.2, 0.95),
                    )

                self.tile_entities.append(tile)
