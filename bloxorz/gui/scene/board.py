# bloxorz/gui/scene/board.py
from __future__ import annotations
import math
from typing import Dict, FrozenSet, List, Tuple
from ursina import Entity, Vec3, color, time
try:
    from bloxorz.gui.scene.theme import (
        VoxelTextures,
        TILE_THICKNESS,
        TILE_GAP,
        setup_environment,
    )
except ImportError:
    from theme import (
        VoxelTextures,
        TILE_THICKNESS,
        TILE_GAP,
        setup_environment,
    )

Pos = Tuple[int, int]


def grid_to_world(r: int, c: int, y: float = 0.0) -> Vec3:
    """Tọa độ Ursina 3D: X = c, Z = -r (càng xuống hàng dưới Z càng âm)."""
    return Vec3(float(c), float(y), float(-r))


class EndPortalVoid(Entity):
    """Lòng cổng End huyền bí với 2 tầng thiên hà xoay ngược chiều nhau."""

    def __init__(self, parent: Entity) -> None:
        super().__init__(parent=parent)
        tex = VoxelTextures.portal_galaxy()
        self.layer1 = Entity(
            parent=self,
            model="plane",
            scale=(0.76, 1.0, 0.76),
            position=(0, -0.27, 0),
            texture=tex,
            unlit=True,
        )
        self.layer2 = Entity(
            parent=self,
            model="plane",
            scale=(0.68, 1.0, 0.68),
            position=(0, -0.25, 0),
            texture=tex,
            color=color.rgba32(255, 255, 255, 180),
            unlit=True,
        )

    def update(self) -> None:
        dt = time.dt
        self.layer1.rotation_y += 35 * dt
        self.layer2.rotation_y -= 50 * dt


class BoardMesh(Entity):
    """Dựng và quản lý toàn bộ các ô sàn, công tắc, cửa sập và cổng End."""

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

        y_tile = -TILE_THICKNESS / 2.0
        env = setup_environment()

        for r in range(self.stage.rows):
            row_str = self.stage.grid[r]
            for c in range(self.stage.cols):
                ch = row_str[c]
                if ch in (".", " "):
                    continue

                pos: Pos = (r, c)
                wx, _, wz = grid_to_world(r, c)

                if ch == "G":
                    # Cổng End có thành viền và hố vũ trụ phát quang
                    portal_root = Entity(parent=self, position=(wx, 0.0, wz))
                    # 4 thành viền End Frame
                    Entity(parent=portal_root, model="cube", scale=(TILE_GAP, TILE_THICKNESS, 0.14), position=(0, y_tile, -0.42), texture=tex_end_frame)
                    Entity(parent=portal_root, model="cube", scale=(TILE_GAP, TILE_THICKNESS, 0.14), position=(0, y_tile, 0.42), texture=tex_end_frame)
                    Entity(parent=portal_root, model="cube", scale=(0.14, TILE_THICKNESS, 0.70), position=(0.42, y_tile, 0), texture=tex_end_frame)
                    Entity(parent=portal_root, model="cube", scale=(0.14, TILE_THICKNESS, 0.70), position=(-0.42, y_tile, 0), texture=tex_end_frame)
                    # Lòng hố xoay động
                    EndPortalVoid(parent=portal_root)
                    self.tiles[pos] = portal_root

                    if env.portal_light:
                        env.portal_light.position = Vec3(wx, 0.8, wz)

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
                    tex = tex_start if ch == "S" else (tex_fragile if ch in ("F", "!") else tex_stone)
                    tile_ent = Entity(
                        parent=self,
                        model="cube",
                        scale=(TILE_GAP, TILE_THICKNESS, TILE_GAP),
                        position=(wx, y_tile, wz),
                        texture=tex,
                    )
                    self.tiles[pos] = tile_ent

                # Công tắc bàn đạp áp lực
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
        """Đóng/mở cầu cửa sập gỗ (Oak Trapdoor)."""
        for bridge_id, entities in self.bridge_entities.items():
            is_open = bridge_id in bridges_open
            for ent in entities:
                if animate:
                    target_scale = (TILE_GAP, 0.14, TILE_GAP) if is_open else (0.001, 0.001, 0.001)
                    ent.enabled = True
                    ent.animate_scale(target_scale, duration=0.15)
                else:
                    ent.scale = (TILE_GAP, 0.14, TILE_GAP) if is_open else (0.001, 0.001, 0.001)
                    ent.enabled = is_open

    def depress_switch(self, pos: Pos) -> None:
        plate = self.switch_plates.get(pos)
        if plate is not None:
            plate.y = 0.006
            plate.animate_y(0.025, duration=0.22)

    def clear_board(self) -> None:
        from ursina import destroy
        for child in list(self.children):
            child.disable()
            destroy(child)
        self.tiles.clear()
        self.bridge_entities.clear()
        self.switch_plates.clear()