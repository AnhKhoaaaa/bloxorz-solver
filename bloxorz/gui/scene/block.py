# bloxorz/gui/scene/block.py
from __future__ import annotations
from typing import List, Tuple
from ursina import Entity, Vec3
try:
    from bloxorz.gui.scene.theme import VoxelTextures
    from bloxorz.gui.scene.board import grid_to_world
except ImportError:
    from theme import VoxelTextures
    from board import grid_to_world


class OakVoxelUnit(Entity):
    """Một khối lập phương 1x1x1 có vỏ cây 4 mặt bên và vân vòng tròn ở 2 đầu cắt."""

    def __init__(self, parent: Entity) -> None:
        super().__init__(
            parent=parent,
            model="cube",
            scale=(1.0, 1.0, 1.0),
            texture=VoxelTextures.oak_bark(),
        )
        tex_rings = VoxelTextures.oak_top()
        Entity(parent=self, model="quad", position=(0, 0.501, 0), rotation=(90, 0, 0), texture=tex_rings)
        Entity(parent=self, model="quad", position=(0, -0.501, 0), rotation=(-90, 0, 0), texture=tex_rings)


class BlockMesh(Entity):
    """
    Quản lý 2 khối lập phương tạo thành khối Bloxorz 1x1x2.
    Đảm bảo định vị chính xác tuyệt đối ở cả 3 tư thế (STANDING, HORIZONTAL, VERTICAL).
    """

    def __init__(self) -> None:
        super().__init__()
        self.unit_a = OakVoxelUnit(parent=self)
        self.unit_b = OakVoxelUnit(parent=self)

    @property
    def cube1(self):
        return self.unit_a

    @cube1.setter
    def cube1(self, val):
        self.unit_a = val

    @property
    def cube2(self):
        return self.unit_b

    @cube2.setter
    def cube2(self, val):
        self.unit_b = val

    def update_from_state(self, state) -> None:
        self.sync_from_state(state)

    @staticmethod
    def get_occupied_cells(state) -> List[Tuple[int, int]]:
        """Trả về danh sách các ô (row, col) mà khối đang chiếm trên mặt sàn."""
        r, c = state.pos
        pose_val = getattr(state.pose, "value", state.pose)
        pose_name = getattr(state.pose, "name", "")

        if state.pose is None and getattr(state, "cube2", None) is not None:
            return [(r, c), state.cube2]
        if pose_val == 1 or pose_name == "HORIZONTAL":
            return [(r, c), (r, c + 1)]
        if pose_val == 2 or pose_name == "VERTICAL":
            return [(r, c), (r + 1, c)]
        return [(r, c)]

    def sync_from_state(self, state) -> None:
        """Đồng bộ vị trí và góc xoay của 2 khối lập phương chuẩn xác từ State."""
        r, c = state.pos
        pose_val = getattr(state.pose, "value", state.pose)
        pose_name = getattr(state.pose, "name", "")

        self.position = Vec3(0, 0, 0)
        self.rotation = Vec3(0, 0, 0)
        self.scale = Vec3(1, 1, 1)

        if state.pose is None and getattr(state, "cube2", None) is not None:
            r2, c2 = state.cube2
            self.unit_a.position = grid_to_world(r, c, y=0.5)
            self.unit_a.rotation = Vec3(0, 0, 0)
            self.unit_b.position = grid_to_world(r2, c2, y=0.5)
            self.unit_b.rotation = Vec3(0, 0, 0)
            return

        if pose_val == 0 or pose_name == "STANDING":
            # Đứng thẳng 1x2x1 tại ô (r, c)
            self.unit_a.position = grid_to_world(r, c, y=0.5)
            self.unit_a.rotation = Vec3(0, 0, 0)
            self.unit_b.position = grid_to_world(r, c, y=1.5)
            self.unit_b.rotation = Vec3(0, 0, 0)

        elif pose_val == 1 or pose_name == "HORIZONTAL":
            # Nằm ngang dọc trục X: chiếm (r, c) và (r, c + 1), vân thân cây nằm ngang
            self.unit_a.position = grid_to_world(r, c, y=0.5)
            self.unit_a.rotation = Vec3(0, 0, 90)
            self.unit_b.position = grid_to_world(r, c + 1, y=0.5)
            self.unit_b.rotation = Vec3(0, 0, 90)

        elif pose_val == 2 or pose_name == "VERTICAL":
            # Nằm dọc theo trục Z: chiếm (r, c) và (r + 1, c), vân thân cây nằm dọc
            self.unit_a.position = grid_to_world(r, c, y=0.5)
            self.unit_a.rotation = Vec3(90, 0, 0)
            self.unit_b.position = grid_to_world(r + 1, c, y=0.5)
            self.unit_b.rotation = Vec3(90, 0, 0)

    def get_center_world_pos(self, state) -> Vec3:
        cells = self.get_occupied_cells(state)
        avg_x = sum(float(c) for _, c in cells) / len(cells)
        avg_z = sum(float(-r) for r, _ in cells) / len(cells)
        return Vec3(avg_x, 0.0, avg_z)
