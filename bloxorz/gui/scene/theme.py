# bloxorz/gui/scene/theme.py
from __future__ import annotations
import math
import random
from typing import Dict, List, Optional
from PIL import Image
from ursina import (
    Entity,
    Texture,
    DirectionalLight,
    AmbientLight,
    color,
    window,
    scene,
    time,
    Vec3,
)

# Hằng số hình học chuẩn của bàn cờ
TILE_THICKNESS: float = 0.36
TILE_GAP: float = 0.98
ANIM_ROLL_DURATION: float = 0.16


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class VoxelTextures:
    """Bộ sinh Texture 16x16 Pixel Art nội sinh chuẩn Minecraft (không cần file ảnh ngoài)."""

    _cache: Dict[str, Texture] = {}

    @classmethod
    def _make_tex(cls, name: str, draw_fn) -> Texture:
        if name in cls._cache:
            return cls._cache[name]
        img = Image.new("RGBA", (16, 16))
        pixels = img.load()
        draw_fn(pixels)
        tex = Texture(img)
        tex.filtering = None  # Nearest-neighbor: sắc nét từng hạt pixel
        cls._cache[name] = tex
        return tex

    @classmethod
    def oak_bark(cls) -> Texture:
        def draw(px):
            cols = ["#5c4328", "#4e3820", "#6b4e30", "#3f2d18"]
            for x in range(16):
                stripe = cols[(x * 3) % len(cols)]
                for y in range(16):
                    if (x * 17 + y * 31) % 7 == 0:
                        c = "#3b2915"
                    elif (x * 13 + y * 7) % 5 == 0:
                        c = "#735536"
                    else:
                        c = stripe
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("oak_bark", draw)

    @classmethod
    def oak_top(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    dist = max(abs(x - 7.5), abs(y - 7.5))
                    if dist >= 6.5:
                        c = "#5c4328" if (x + y) % 2 == 0 else "#4a351e"
                    elif round(dist) % 2 == 0:
                        c = "#b8945f"
                    else:
                        c = "#9e7c4a"
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("oak_top", draw)

    @classmethod
    def stone_bricks(cls) -> Texture:
        def draw(px):
            shades = ["#7a7a82", "#707078", "#83838c", "#686870"]
            for y in range(16):
                for x in range(16):
                    is_h_groove = y in (0, 8)
                    is_v_groove = (y < 8 and x == 8) or (y >= 8 and x in (0, 15))
                    if is_h_groove or is_v_groove:
                        c = "#38383c"
                    else:
                        is_hi = y in (1, 9) or (y < 8 and x == 9) or (y >= 8 and x == 1)
                        h = (x * 37 + y * 73) % 19
                        if h in (0, 1):
                            c = "#4f7835"  # Đốm rêu xanh
                        elif h == 2:
                            c = "#658f46"  # Đốm rêu sáng
                        elif is_hi:
                            c = "#96969e"  # Viền gạch bắt sáng
                        else:
                            c = shades[(x * 11 + y * 23) % len(shades)]
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("stone_bricks", draw)

    @classmethod
    def crying_obsidian(cls) -> Texture:
        def draw(px):
            base = ["#181026", "#211536", "#110b1c", "#2b1b47"]
            for y in range(16):
                for x in range(16):
                    h = (x * 43 + y * 19) % 23
                    if h == 0:
                        c = "#d96bff"
                    elif h in (1, 2):
                        c = "#9922ff"
                    elif h == 3:
                        c = "#4c127a"
                    else:
                        c = base[(x * 7 + y * 13) % len(base)]
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("crying_obsidian", draw)

    @classmethod
    def fragile_sand(cls) -> Texture:
        def draw(px):
            palette = ["#d67229", "#c2611d", "#e08338", "#ab5012"]
            for y in range(16):
                for x in range(16):
                    is_crack = (x == y and 2 < x < 13) or (x + y == 15 and 4 < x < 12)
                    if is_crack:
                        c = "#592305"
                    else:
                        c = palette[(x * 29 + y * 41) % len(palette)]
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("fragile_sand", draw)

    @classmethod
    def trapdoor(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    is_border = x < 3 or x > 12 or y < 3 or y > 12
                    is_cross = x in (7, 8) or y in (7, 8)
                    if is_border or is_cross:
                        c = "#8c693e" if (x + y) % 3 == 0 else "#a37b49"
                        if x in (0, 15) or y in (0, 15):
                            c = "#5c4328"
                    else:
                        c = "#291d12"
                    px[x, y] = (*_hex_to_rgb(c), 255)
            # Bản lề sắt
            for dy in (3, 4, 11, 12):
                for dx in (1, 2):
                    px[dx, dy] = (*_hex_to_rgb("#4a4a52"), 255)

        return cls._make_tex("trapdoor", draw)

    @classmethod
    def pressure_plate(cls, is_heavy: bool = False, is_split: bool = False) -> Texture:
        key = f"plate_{'heavy' if is_heavy else ('split' if is_split else 'soft')}"

        def draw(px):
            for y in range(16):
                for x in range(16):
                    border = x in (0, 15) or y in (0, 15)
                    if is_heavy:
                        c = "#686870" if border else ("#d8d8e2" if (x + y) % 2 == 0 else "#c4c4cf")
                        if x in (2, 13) and y in (2, 13):
                            c = "#44444a"
                    elif is_split:
                        c = "#28596b" if border else ("#4be0f5" if (x + y) % 2 == 0 else "#32b5c9")
                        if x in (2, 13) and y in (2, 13):
                            c = "#163845"
                    else:
                        c = "#6e502d" if border else ("#997243" if y % 4 == 0 else "#b58852")
                        if x in (2, 13) and y in (2, 13):
                            c = "#4f381f"
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex(key, draw)

    @classmethod
    def end_frame(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    if x < 2 or x > 13 or y < 2 or y > 13:
                        c = "#326b5c" if (x + y) % 2 == 0 else "#245246"
                    else:
                        c = "#d8d29c"
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("end_frame", draw)

    @classmethod
    def portal_inside(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    h = (x * 31 + y * 53) % 29
                    if h == 0:
                        c = "#55ffff"
                    elif h in (1, 2):
                        c = "#d96bff"
                    elif h in (3, 4):
                        c = "#7b2cbf"
                    else:
                        c = "#090314"
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("portal_inside", draw)

    @classmethod
    def lava_surface(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    v = math.sin(x * 0.6) + math.cos(y * 0.6)
                    if v > 1.0:
                        c = "#ffdd33"
                    elif v > 0.1:
                        c = "#ff6600"
                    else:
                        c = "#c92a04"
                    px[x, y] = (*_hex_to_rgb(c), 255)

        return cls._make_tex("lava_surface", draw)


class BiomeEnvironment(Entity):
    """Quản lý hiệu ứng môi trường 3D (Mây Overworld, Biển Lava Nether, Hạt tinh thể The End)."""

    def __init__(self) -> None:
        super().__init__()
        self.current_biome: str = "overworld"
        self.clouds: List[Entity] = []
        self.particles: List[Entity] = []
        self.lava_plane: Optional[Entity] = None
        self.dir_light: Optional[DirectionalLight] = None
        self.amb_light: Optional[AmbientLight] = None

        self._init_lights()
        self._init_clouds()
        self._init_lava()
        self._init_particles()
        self.apply_biome("overworld")

    def _init_lights(self) -> None:
        self.amb_light = AmbientLight(color=color.rgb32(145, 155, 170))
        self.dir_light = DirectionalLight(
            color=color.rgb32(255, 245, 220),
            direction=Vec3(-1, -2, -1.5),
            shadows=False,
        )

    def _init_clouds(self) -> None:
        rng = random.Random(42)
        for _ in range(14):
            w = rng.randint(3, 7)
            d = rng.randint(2, 5)
            cloud = Entity(
                parent=self,
                model="cube",
                scale=(w, 0.75, d),
                position=(rng.uniform(-25, 25), rng.uniform(11.0, 15.0), rng.uniform(-22, 18)),
                color=color.rgba32(255, 255, 255, 210),
            )
            cloud.speed = rng.uniform(0.35, 0.85)
            self.clouds.append(cloud)

    def _init_lava(self) -> None:
        self.lava_plane = Entity(
            parent=self,
            model="plane",
            scale=(85, 1, 85),
            position=(4, -4.2, -4),
            texture=VoxelTextures.lava_surface(),
            texture_scale=(24, 24),
            unlit=True,
            enabled=False,
        )

    def _init_particles(self) -> None:
        rng = random.Random(99)
        for _ in range(45):
            p = Entity(
                parent=self,
                model="cube",
                scale=0.14,
                position=(rng.uniform(-14, 20), rng.uniform(-4, 9), rng.uniform(-18, 12)),
                color=color.rgb32(255, 102, 0),
                unlit=True,
                enabled=False,
            )
            p.vy = rng.uniform(0.6, 1.5)
            p.phase = rng.uniform(0, math.pi * 2)
            self.particles.append(p)

    def apply_biome(self, name: str) -> None:
        name = name.lower()
        self.current_biome = name

        if name == "overworld":
            window.color = color.rgb32(110, 185, 240)
            scene.fog_color = color.rgb32(110, 185, 240)
            scene.fog_density = 0.002
            if self.amb_light:
                self.amb_light.color = color.rgb32(145, 155, 170)
            if self.dir_light:
                self.dir_light.color = color.rgb32(255, 248, 225)
            for c in self.clouds:
                c.enabled = True
            if self.lava_plane:
                self.lava_plane.enabled = False
            for p in self.particles:
                p.enabled = False

        elif name == "nether":
            window.color = color.rgb32(38, 8, 8)
            scene.fog_color = color.rgb32(48, 12, 10)
            scene.fog_density = 0.008
            if self.amb_light:
                self.amb_light.color = color.rgb32(160, 80, 50)
            if self.dir_light:
                self.dir_light.color = color.rgb32(255, 150, 70)
            for c in self.clouds:
                c.enabled = False
            if self.lava_plane:
                self.lava_plane.enabled = True
            for i, p in enumerate(self.particles):
                p.enabled = True
                p.color = color.rgb32(255, 90, 0) if i % 2 == 0 else color.rgb32(255, 204, 34)

        elif name == "end":
            window.color = color.rgb32(12, 6, 20)
            scene.fog_color = color.rgb32(16, 8, 30)
            scene.fog_density = 0.006
            if self.amb_light:
                self.amb_light.color = color.rgb32(120, 90, 160)
            if self.dir_light:
                self.dir_light.color = color.rgb32(210, 165, 255)
            for c in self.clouds:
                c.enabled = False
            if self.lava_plane:
                self.lava_plane.enabled = False
            for i, p in enumerate(self.particles):
                p.enabled = True
                p.color = color.rgb32(217, 107, 255) if i % 2 == 0 else color.rgb32(123, 44, 191)

    def update(self) -> None:
        dt = time.dt
        t = time.time()

        if self.current_biome == "overworld":
            for c in self.clouds:
                c.x += c.speed * dt
                if c.x > 28:
                    c.x = -28

        elif self.current_biome in ("nether", "end"):
            if self.lava_plane and self.lava_plane.enabled:
                self.lava_plane.texture_offset = (
                    math.sin(t * 0.4) * 0.25,
                    math.cos(t * 0.3) * 0.25,
                )
            for p in self.particles:
                p.y += p.vy * dt
                p.x += math.sin(t * 2.0 + p.phase) * 0.4 * dt
                p.rotation_y += 90 * dt
                p.rotation_x += 60 * dt
                if p.y > 9.5:
                    p.y = -4.0


_ENV_INSTANCE: Optional[BiomeEnvironment] = None


def setup_environment() -> BiomeEnvironment:
    """Khởi tạo hoặc trả về singleton BiomeEnvironment."""
    global _ENV_INSTANCE
    if _ENV_INSTANCE is None:
        _ENV_INSTANCE = BiomeEnvironment()
    return _ENV_INSTANCE


def set_biome(name: str) -> None:
    """Chuyển đổi tức thì giữa 3 Biome: 'overworld', 'nether', 'end'."""
    env = setup_environment()
    env.apply_biome(name)