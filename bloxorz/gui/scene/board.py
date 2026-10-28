# bloxorz/gui/scene/board.py
from __future__ import annotations
from typing import Dict, FrozenSet, List, Tuple
from ursina import Entity, Vec3, color
from bloxorz.gui.scene.theme import (
    VoxelTextures,
    TILE_THICKNESS,
    TILE_GAP,
)

Pos = Tuple[int, int]


def grid_to_world(r: int, c: int, y: float = 0.0) -> Vec3:
    """Chuyển đổi tọa độ (row, col) sang tọa độ 3D Ursina: X = c, Z = -r."""
    return Vec3(float(c), float(y), float(-r))


class BoardMesh(Entity):
    """Thực thể quản lý toàn bộ gạch, cổng End, công tắc bàn đạp và cầu cửa sập."""

    def __init__(self, stage) -> None:
        super().__init__()
        self.stage = stage
        self.tiles: Dict[Pos, Entity] = {}
        self.bridge_entities: Dict[str, List[Entity]] = {}
        self.switch_plates: Dict[Pos, Entity] = {}

        self._build_board()

    def _build_board(self) -> None:
        tex_stone = VoxelTextures.stone_bricks()
        tex_start = VoxelTextures.crying_obsidian()
        tex_fragile = VoxelTextures.fragile_sand()
        tex_trapdoor = VoxelTextures.trapdoor()
        tex_end_frame = VoxelTextures.end_frame()
        tex_portal = VoxelTextures.portal_inside()

        y_tile = -TILE_THICKNESS / 2.0

        for r in range(self.stage.rows):
            row_str = self.stage.grid[r]
            for c in range(self.stage.cols):
                ch = row_str[c]
                if ch in (".", " "):
                    continue

                pos: Pos = (r, c)
                wx, _, wz = grid_to_world(r, c)

                if ch == "G":
                    # Miệng hố Cổng End (End Portal Frame + lòng hố vũ trụ thụt xuống)
                    portal_root = Entity(parent=self, position=(wx, 0.0, wz))
                    # 4 thành khung cổng End
                    Entity(
                        parent=portal_root,
                        model="cube",
                        scale=(TILE_GAP, TILE_THICKNESS, 0.14),
                        position=(0, y_tile, -0.42),
                        texture=tex_end_frame,
                    )
                    Entity(
                        parent=portal_root,
                        model="cube",
                        scale=(TILE_GAP, TILE_THICKNESS, 0.14),
                        position=(0, y_tile, 0.42),
                        texture=tex_end_frame,
                    )
                    Entity(
                        parent=portal_root,
                        model="cube",
                        scale=(0.14, TILE_THICKNESS, 0.70),
                        position=(0.42, y_tile, 0),
                        texture=tex_end_frame,
                    )
                    Entity(
                        parent=portal_root,
                        model="cube",
                        scale=(0.14, TILE_THICKNESS, 0.70),
                        position=(-0.42, y_tile, 0),
                        texture=tex_end_frame,
                    )
                    # Lòng hố thiên hà tím phát sáng
                    Entity(
                        parent=portal_root,
                        model="plane",
                        scale=(0.76, 1.0, 0.76),
                        position=(0, -0.26, 0),
                        texture=tex_portal,
                        unlit=True,
                    )
                    self.tiles[pos] = portal_root

                elif ch == "B" or pos in getattr(self.stage, "bridge_at", {}):
                    bridge_id = self.stage.bridge_at.get(pos, ch)
                    bridge_ent = Entity(
                        parent=self,
                        model="cube",
                        scale=(TILE_GAP, 0.14, TILE_GAP),
                        position=(wx, -0.07, wz),
                        texture=tex_trapdoor,
                    )
                    self.bridge_entities.setdefault(bridge_id, []).append(bridge_ent)
                    self.tiles[pos] = bridge_ent

                else:
                    # Sàn gạch thường ('#'), Ô xuất phát ('S'), Ô dễ vỡ ('F'/'!')
                    if ch == "S":
                        tex = tex_start
                    elif ch in ("F", "!"):
                        tex = tex_fragile
                    else:
                        tex = tex_stone

                    tile_ent = Entity(
                        parent=self,
                        model="cube",
                        scale=(TILE_GAP, TILE_THICKNESS, TILE_GAP),
                        position=(wx, y_tile, wz),
                        texture=tex,
                    )
                    self.tiles[pos] = tile_ent

                # Kiểm tra công tắc bàn đạp (Pressure Plate) tại ô này
                sw = getattr(self.stage, "switch_at", {}).get(pos)
                if sw is not None or ch in ("o", "x", "@"):
                    kind = getattr(sw, "kind", None)
                    if kind is None:
                        kind = "heavy" if ch == "x" else ("split" if ch == "@" else "soft")

                    plate_tex = VoxelTextures.pressure_plate(
                        is_heavy=(kind == "heavy"),
                        is_split=(kind == "split"),
                    )
                    plate = Entity(
                        parent=self,
                        model="cube",
                        scale=(0.68, 0.05, 0.68),
                        position=(wx, 0.025, wz),
                        texture=plate_tex,
                    )
                    self.switch_plates[pos] = plate

    def sync_bridges(self, bridges_open: FrozenSet[str], animate: bool = False) -> None:
        """Đồng bộ trạng thái đóng/mở của các cầu cửa sập gỗ (Oak Trapdoor)."""
        for bridge_id, entities in self.bridge_entities.items():
            is_open = bridge_id in bridges_open
            for ent in entities:
                if animate:
                    target_scale = (TILE_GAP, 0.14, TILE_GAP) if is_open else (0.001, 0.001, 0.001)
                    ent.enabled = True
                    ent.animate_scale(target_scale, duration=0.14)
                else:
                    if is_open:
                        ent.enabled = True
                        ent.scale = (TILE_GAP, 0.14, TILE_GAP)
                    else:
                        ent.scale = (0.001, 0.001, 0.001)
                        ent.enabled = False

    def depress_switch(self, pos: Pos) -> None:
        """Hiệu ứng lún bàn đạp áp lực khi khối đè lên."""
        plate = self.switch_plates.get(pos)
        if plate is not None:
            plate.y = 0.006
            plate.animate_y(0.025, duration=0.22)

    def clear_board(self) -> None:
        """Hủy toàn bộ thực thể bàn cờ khi nạp màn chơi mới."""
        for child in list(self.children):
            child.disable()
            from ursina import destroy
            destroy(child)
        self.tiles.clear()
        self.bridge_entities.clear()
        self.switch_plates.clear()
    def update_bridges(self, state) -> None:
        bridges = getattr(state, "bridges_open", state)
        self.sync_bridges(bridges, animate=True)
