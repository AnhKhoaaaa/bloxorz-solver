# Phụ trách: VT3 - Task 3.1 / 3.3
"""Vẽ khối hộp Bloxorz (khối đơn và 2 khối sau khi tách)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bloxorz.model import Pose

if TYPE_CHECKING:
    from bloxorz.model import State


class BlockView:
    """Quản lý hiển thị 3D của khối Bloxorz (kích thước, vị trí và 3 tư thế)."""

    def __init__(self) -> None:
        from ursina import Entity, color

        # Khối hộp chính 1x1x2 (màu cam gỗ đặc trưng của Bloxorz)
        self.block = Entity(
            model="cube",
            color=color.rgb32(220, 125, 45),
            position=(0, 0, 0),
            scale=(1, 2, 1),
            visible=False,
        )

        # 2 khối lập phương con khi bị phân tách (chuẩn bị trước cho Task 3.3)
        self.cube1 = Entity(
            model="cube",
            color=color.rgb32(235, 145, 65),
            scale=(0.92, 0.92, 0.92),
            visible=False,
        )
        self.cube2 = Entity(
            model="cube",
            color=color.rgb32(195, 105, 35),
            scale=(0.92, 0.92, 0.92),
            visible=False,
        )

    def target_from_state(self, state: State) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        """Trả về (scale, position) cho khối nguyên dựa trên state."""
        r, c = state.pos
        if state.pose == Pose.STANDING:
            return (0.92, 1.92, 0.92), (float(c), 1.05, -float(r))
        elif state.pose == Pose.HORIZONTAL:
            return (1.92, 0.92, 0.92), (float(c) + 0.5, 0.55, -float(r))
        elif state.pose == Pose.VERTICAL:
            return (0.92, 0.92, 1.92), (float(c), 0.55, -float(r) - 0.5)
        return (0.92, 0.92, 0.92), (float(c), 0.55, -float(r))

    def update_from_state(self, state: State) -> None:
        """Cập nhật kích thước và tọa độ 3D của khối dựa trên State."""
        # Khôi phục góc xoay chuẩn (phòng trường hợp vừa xoay rơi vực)
        self.block.rotation = (0, 0, 0)
        self.cube1.rotation = (0, 0, 0)
        self.cube2.rotation = (0, 0, 0)

        if state.pose is None:
            # Khối đang bị tách làm 2 cube 1x1x1
            self.block.visible = False

            r1, c1 = state.pos
            self.cube1.position = (float(c1), 0.55, -float(r1))
            self.cube1.visible = True

            if state.cube2 is not None:
                r2, c2 = state.cube2
                self.cube2.position = (float(c2), 0.55, -float(r2))
                self.cube2.visible = True
            else:
                self.cube2.visible = False
            return

        # Khối nguyên vẹn 1x1x2
        self.cube1.visible = False
        self.cube2.visible = False
        self.block.visible = True

        scale, pos = self.target_from_state(state)
        self.block.scale = scale
        self.block.position = pos

    def hide(self) -> None:
        """Ẩn toàn bộ khối."""
        self.block.visible = False
        self.cube1.visible = False
        self.cube2.visible = False

