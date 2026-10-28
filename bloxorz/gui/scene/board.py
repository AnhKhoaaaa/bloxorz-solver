# bloxorz/gui/scene/board.py
from __future__ import annotations
import math
from typing import Dict, FrozenSet, List, Tuple
from ursina import Entity, Vec3, color, time

try:
    from bloxorz.gui.scene.theme import (
        VoxelTextures,
        TILE_THICKNESS,
        TILE_SIZE,
        setup_environment,
    )
except ImportError:
    from theme import (
        VoxelTextures,
        TILE_THICKNESS,
        TILE_SIZE,
        setup_environment,
    )

Pos = Tuple[int, int]


def grid_to_world(r: int, c: int, y: float = 0.0) -> Vec3:
    return Vec3(float(c), float(y), float(-r))


class EndPortalVortex(Entity):
    """Cổng End gồm 3 tầng hào quang xoay ngược chiều và nhấp nháy phát quang."""
    def __init__(self, parent: Entity) -> None:
        super().__init__(parent=parent)
        tex = VoxelTextures.portal_vortex()
        # Lớp đáy sâu
        self.l1 = Entity(parent=self, model="plane", scale=(0.80, 1.0, 0.80), position=(0, -0.28, 0), texture=tex, unlit=True)
        # Lớp hào quang giữa
        self.l2 = Entity(parent=self, model="plane", scale=(0.68, 1.0, 0.68), position=(0, -0.25, 0), texture=tex, color=color.rgba32(255, 255, 255, 200), unlit=True)
        # Lớp tâm phát quang
        self.l3 = Entity(parent=self, model="plane", scale=(0.45, 1.0, 0.45), position=(0, -0.22, 0), texture=tex, color=color.rgba32(34, 211, 238, 220), unlit=True)

    def update(self) -> None:
        dt = time.dt
        t = time.time()
        self.l1.rotation_y += 30 * dt
        self.l2.rotation_y -= 45 * dt
        self.l3.rotation_y += 70 * dt
        # Nhấp nháy nhẹ độ sáng
        pulse = (math.sin(t * 4.0) * 0.15 + 0.85)
        self.l3.scale = (0.45 * pulse, 1.0, 0.45 * pulse)


EndPortalVoid = EndPortalVortex


class BoardMesh(Entity):
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
        start_pos = getattr(self.stage, "start", None)
        goal_pos = getattr(self.stage, "goal", None)

        for r in range(self.stage.rows):
            row_str = self.stage.grid[r]
            for c in range(self.stage.cols):
                ch = row_str[c]
                if ch in (".", " "):
                    continue

                pos: Pos = (r, c)
                wx, _, wz = grid_to_world(r, c)

                # 1. ĐẾ LÓT RÃNH VỮA ĐEN TẠO ĐỘ NỔI 3D GIỮA CÁC VIÊN GẠCH
                Entity(
                    parent=self,
                    model="cube",
                    scale=(0.98, TILE_THICKNESS * 0.9, 0.98),
                    position=(wx, y_tile - 0.02, wz),
                    color=color.rgb32(18, 18, 22),
                )

                if ch == "G" or pos == goal_pos:
                    portal_root = Entity(parent=self, position=(wx, 0.0, wz))
                    # 4 thành viền End Frame
                    Entity(parent=portal_root, model="cube", scale=(TILE_SIZE, TILE_THICKNESS, 0.14), position=(0, y_tile, -0.39), texture=tex_end_frame)
                    Entity(parent=portal_root, model="cube", scale=(TILE_SIZE, TILE_THICKNESS, 0.14), position=(0, y_tile, 0.39), texture=tex_end_frame)
                    Entity(parent=portal_root, model="cube", scale=(0.14, TILE_THICKNESS, 0.64), position=(0.39, y_tile, 0), texture=tex_end_frame)
                    Entity(parent=portal_root, model="cube", scale=(0.14, TILE_THICKNESS, 0.64), position=(-0.39, y_tile, 0), texture=tex_end_frame)
                    EndPortalVortex(parent=portal_root)
                    self.tiles[pos] = portal_root

                    if env.portal_light:
                        env.portal_light.position = Vec3(wx, 1.2, wz)

                elif ch == "B" or pos in getattr(self.stage, "bridge_at", {}):
                    bridge_id = self.stage.bridge_at.get(pos, ch)
                    bridge_ent = Entity(
                        parent=self,
                        model="cube",
                        scale=(TILE_SIZE, 0.14, TILE_SIZE),
                        position=(wx, -0.07, wz),
                        texture=tex_trapdoor,
                    )
                    self.bridge_entities.setdefault(bridge_id, []).append(bridge_ent)
                    self.tiles[pos] = bridge_ent

                else:
                    is_start = (ch == "S" or pos == start_pos)
                    tex = tex_start if is_start else (tex_fragile if ch in ("F", "!") else tex_stone)
                    tile_ent = Entity(
                        parent=self,
                        model="cube",
                        scale=(TILE_SIZE, TILE_THICKNESS, TILE_SIZE),
                        position=(wx, y_tile, wz),
                        texture=tex,
                    )
                    self.tiles[pos] = tile_ent

                # Bàn đạp áp lực
                sw = getattr(self.stage, "switch_at", {}).get(pos)
                if sw is not None or ch in ("o", "x", "@", "*"):
                    kind = sw.get("kind") if isinstance(sw, dict) else getattr(sw, "kind", None)
                    if kind is None:
                        kind = "heavy" if ch == "x" else ("split" if ch in ("@", "*") else "soft")

                    plate = Entity(
                        parent=self,
                        model="cube",
                        scale=(0.66, 0.05, 0.66),
                        position=(wx, 0.025, wz),
                        texture=VoxelTextures.pressure_plate(kind == "heavy", kind == "split"),
                    )
                    self.switch_plates[pos] = plate

    def sync_bridges(self, bridges_open: FrozenSet[str], animate: bool = False) -> None:
        for bridge_id, entities in self.bridge_entities.items():
            is_open = bridge_id in bridges_open
            for ent in entities:
                if animate:
                    target = (TILE_SIZE, 0.14, TILE_SIZE) if is_open else (0.001, 0.001, 0.001)
                    ent.enabled = True
                    ent.animate_scale(target, duration=0.15)
                else:
                    ent.scale = (TILE_SIZE, 0.14, TILE_SIZE) if is_open else (0.001, 0.001, 0.001)
                    ent.enabled = is_open

    def update_bridges(self, state) -> None:
        self.sync_bridges(getattr(state, "bridges_open", frozenset()), animate=True)

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
