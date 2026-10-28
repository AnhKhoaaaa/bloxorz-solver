# bloxorz/gui/scene/block.py
from __future__ import annotations
from typing import Optional
from ursina import Entity, Vec3
from bloxorz.gui.scene.theme import VoxelTextures
from bloxorz.gui.scene.board import grid_to_world


class OakCubeUnit(Entity):
    """Một đơn vị khối gỗ sồi 1x1x1 có 4 mặt bên là vỏ cây và 2 mặt đáy là vòng gỗ."""

    def __init__(self, parent: Entity, position: Vec3 = Vec3(0, 0, 0)) -> None:
        super().__init__(
            parent=parent,
            model="cube",
            position=position,
            scale=(1.0, 1.0, 1.0),
            texture=VoxelTextures.oak_bark(),
        )
        tex_rings = VoxelTextures.oak_top()
        # Nắp vân vòng gỗ phía trên (+Y)
        Entity(
            parent=self,
            model="quad",
            position=(0, 0.501, 0),
            rotation=(90, 0, 0),
            texture=tex_rings,
        )
        # Nắp vân vòng gỗ phía dưới (-Y)
        Entity(
            parent=self,
            model="quad",
            position=(0, -0.501, 0),
            rotation=(-90, 0, 0),
            texture=tex_rings,
        )


class BlockMesh(Entity):
    """
    Thực thể đại diện cho khối Bloxorz Gỗ Sồi (1x1x2).
    Sử dụng cấu trúc Pivot -> Visual để xoay lật 90 độ quanh cạnh đáy tiếp xúc sàn.
    """

    def __init__(self) -> None:
        super().__init__()
        # Nhóm chứa hình ảnh khối gỗ (gồm 2 đơn vị OakCubeUnit 1x1x1)
        self.visual = Entity(parent=self)
        self.bottom_unit = OakCubeUnit(parent=self.visual, position=Vec3(0, -0.5, 0))
        self.top_unit = OakCubeUnit(parent=self.visual, position=Vec3(0, 0.5, 0))

        # Khối phụ dùng khi người chơi ở trạng thái tách đôi (Split Block: pose is None)
        self.split_unit_a = OakCubeUnit(parent=self, position=Vec3(0, 0.5, 0))
        self.split_unit_b = OakCubeUnit(parent=self, position=Vec3(0, 0.5, 0))
        self.split_unit_a.enabled = False
        self.split_unit_b.enabled = False
        self.cube1 = self.split_unit_a
        self.cube2 = self.split_unit_b
        self.block = self

    def sync_from_state(self, state) -> None:
        """
        Đồng bộ chính xác vị trí, kích thước và góc xoay từ State của engine:
        - STANDING (0): Cao 2 theo Y, tâm ở y = 1.0
        - HORIZONTAL (1): Rộng 2 theo X (c..c+1), tâm ở x = c + 0.5, y = 0.5
        - VERTICAL (2): Dài 2 theo Z (r..r+1), tâm ở z = -r - 0.5, y = 0.5
        - None (Split): Hiển thị 2 khối đơn 1x1x1 tại state.pos và state.cube2
        """
        r, c = state.pos
        pose_val = getattr(state.pose, "value", state.pose)

        # Reset toàn bộ biến đổi của Pivot gốc và Visual con
        self.position = Vec3(0, 0, 0)
        self.rotation = Vec3(0, 0, 0)
        self.scale = Vec3(1, 1, 1)
        self.visual.scale = Vec3(1, 1, 1)

        if state.pose is None and getattr(state, "cube2", None) is not None:
            # Trạng thái tách thành 2 khối đơn 1x1x1
            self.visual.enabled = False
            self.split_unit_a.enabled = True
            self.split_unit_b.enabled = True

            r2, c2 = state.cube2
            self.split_unit_a.position = grid_to_world(r, c, y=0.5)
            self.split_unit_a.rotation = Vec3(0, 0, 0)
            self.split_unit_b.position = grid_to_world(r2, c2, y=0.5)
            self.split_unit_b.rotation = Vec3(0, 0, 0)
            return

        self.visual.enabled = True
        self.split_unit_a.enabled = False
        self.split_unit_b.enabled = False
        self.cube1 = self.split_unit_a
        self.cube2 = self.split_unit_b
        self.block = self

        if pose_val == 0 or getattr(state.pose, "name", "") == "STANDING":
            # Đứng thẳng 1x2x1 tại (r, c)
            self.visual.position = Vec3(float(c), 1.0, float(-r))
            self.visual.rotation = Vec3(0, 0, 0)

        elif pose_val == 1 or getattr(state.pose, "name", "") == "HORIZONTAL":
            # Nằm ngang dọc trục X: chiếm (r, c) và (r, c + 1)
            self.visual.position = Vec3(float(c) + 0.5, 0.5, float(-r))
            self.visual.rotation = Vec3(0, 0, 90)

        elif pose_val == 2 or getattr(state.pose, "name", "") == "VERTICAL":
            # Nằm dọc theo trục Z: chiếm (r, c) và (r + 1, c)
            self.visual.position = Vec3(float(c), 0.5, float(-r) - 0.5)
            self.visual.rotation = Vec3(90, 0, 0)

    def get_center_world_pos(self, state) -> Vec3:
        """Lấy tọa độ tâm của khối trên mặt phẳng bàn cờ để Camera hướng tới."""
        r, c = state.pos
        pose_val = getattr(state.pose, "value", state.pose)
        if state.pose is None:
            return Vec3(float(c), 0.0, float(-r))
        if pose_val == 1 or getattr(state.pose, "name", "") == "HORIZONTAL":
            return Vec3(float(c) + 0.5, 0.0, float(-r))
        if pose_val == 2 or getattr(state.pose, "name", "") == "VERTICAL":
            return Vec3(float(c), 0.0, float(-r) - 0.5)
        return Vec3(float(c), 0.0, float(-r))
    def update_from_state(self, state) -> None:
        self.sync_from_state(state)
