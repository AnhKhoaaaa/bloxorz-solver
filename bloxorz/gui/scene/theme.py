# bloxorz/gui/scene/theme.py
from __future__ import annotations
import math
import os
import random
import struct
import tempfile
import wave
from typing import Dict, List, Optional
from PIL import Image
from panda3d.core import SamplerState
from ursina import (
    Entity,
    Texture,
    DirectionalLight,
    AmbientLight,
    PointLight,
    Audio,
    color,
    window,
    scene,
    time,
    Vec3,
)

TILE_THICKNESS: float = 0.36
TILE_SIZE: float = 0.92          # Kích thước gạch tạo rãnh vữa 3D nổi khối
TILE_GAP: float = 0.98           # Hằng số tương thích ngược cho đế gạch
ANIM_ROLL_DURATION: float = 0.16


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ===========================================================================
# 1. ÂM THANH NỘI SINH (SYNTHESIZER)
# ===========================================================================
class SoundManager:
    _initialized = False
    _sounds: Dict[str, str] = {}

    @classmethod
    def init(cls) -> None:
        if cls._initialized:
            return
        tmp_dir = tempfile.gettempdir()
        cls._sounds["step"] = cls._create_step_sound(tmp_dir)
        cls._sounds["switch"] = cls._create_switch_sound(tmp_dir)
        cls._sounds["fall"] = cls._create_fall_sound(tmp_dir)
        cls._sounds["win"] = cls._create_win_sound(tmp_dir)
        cls._initialized = True

    @staticmethod
    def _write_wav(path: str, samples: list[float], sample_rate: int = 22050) -> str:
        with wave.open(path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            raw = bytearray()
            for s in samples:
                val = max(-1.0, min(1.0, s))
                raw.extend(struct.pack("<h", int(val * 32767)))
            wf.writeframes(raw)
        return path

    @classmethod
    def _create_step_sound(cls, tmp_dir: str) -> str:
        sr = 22050
        dur = 0.10
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            thump = math.sin(2 * math.pi * (140 * math.exp(-t * 30)) * t) * math.exp(-t * 35)
            noise = (random.random() * 2 - 1) * math.exp(-t * 50) * 0.35
            samples.append((thump + noise) * 0.7)
        return cls._write_wav(os.path.join(tmp_dir, "bx_step.wav"), samples, sr)

    @classmethod
    def _create_switch_sound(cls, tmp_dir: str) -> str:
        sr = 22050
        dur = 0.08
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            f = 900 if t < 0.03 else 1350
            sq = 0.35 if math.sin(2 * math.pi * f * t) > 0 else -0.35
            samples.append(sq * math.exp(-t * 35))
        return cls._write_wav(os.path.join(tmp_dir, "bx_switch.wav"), samples, sr)

    @classmethod
    def _create_fall_sound(cls, tmp_dir: str) -> str:
        sr = 22050
        dur = 0.60
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            f = 320 * math.exp(-t * 4.0) + 30
            samples.append(math.sin(2 * math.pi * f * t) * math.exp(-t * 3.5) * 0.5)
        return cls._write_wav(os.path.join(tmp_dir, "bx_fall.wav"), samples, sr)

    @classmethod
    def _create_win_sound(cls, tmp_dir: str) -> str:
        sr = 22050
        dur = 0.90
        n = int(sr * dur)
        samples = [0.0] * n
        for idx, freq in enumerate([523.25, 659.25, 783.99, 1046.50, 1318.51]):
            start = int(idx * 0.11 * sr)
            for i in range(start, n):
                t = (i - start) / sr
                samples[i] += math.sin(2 * math.pi * freq * t) * math.exp(-t * 4.5) * 0.22
        return cls._write_wav(os.path.join(tmp_dir, "bx_win.wav"), samples, sr)

    @classmethod
    def play(cls, name: str) -> None:
        cls.init()
        p = cls._sounds.get(name)
        if p and os.path.exists(p):
            try:
                Audio(p, autoplay=True, loop=False)
            except Exception:
                pass


# ===========================================================================
# 2. BỘ TEXTURE ĐỘ TƯƠNG PHẢN CAO & KHÓA SAMPLER STATE NEAREST
# ===========================================================================
class VoxelTextures:
    _cache: Dict[str, Texture] = {}

    @classmethod
    def _make_tex(cls, name: str, draw_fn) -> Texture:
        if name in cls._cache:
            return cls._cache[name]
        img = Image.new("RGBA", (16, 16))
        px = img.load()
        draw_fn(px)
        tex = Texture(img)
        # Khóa cứng lọc Nearest ở tầng Panda3D Core (Sắc cạnh từng hạt pixel)
        try:
            tex._texture.setMagfilter(SamplerState.FT_nearest)
            tex._texture.setMinfilter(SamplerState.FT_nearest)
        except Exception:
            tex.filtering = None
        cls._cache[name] = tex
        return tex

    @classmethod
    def oak_bark(cls) -> Texture:
        def draw(px):
            cols = ["#6b4e30", "#5c4328", "#4e3820", "#3d2b17"]
            for x in range(16):
                stripe = cols[(x * 3) % len(cols)]
                for y in range(16):
                    c = "#2e1e0f" if (x * 17 + y * 31) % 7 == 0 else (
                        "#845f3a" if (x * 13 + y * 7) % 5 == 0 else stripe
                    )
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("oak_bark", draw)

    @classmethod
    def oak_top(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    dist = max(abs(x - 7.5), abs(y - 7.5))
                    if dist >= 6.5:
                        c = "#6b4e30" if (x + y) % 2 == 0 else "#4e3820"
                    elif round(dist) % 2 == 0:
                        c = "#d4a76a"  # Vòng sinh trưởng sáng màu
                    else:
                        c = "#ad824a"
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("oak_top", draw)

    @classmethod
    def stone_bricks(cls) -> Texture:
        def draw(px):
            shades = ["#8c8c96", "#7e7e88", "#9999a4", "#71717a"]
            for y in range(16):
                for x in range(16):
                    is_h = y in (0, 8)
                    is_v = (y < 8 and x == 8) or (y >= 8 and x in (0, 15))
                    if is_h or is_v:
                        c = "#26262a"  # Rãnh vữa tối màu sắc nét
                    else:
                        is_hi = y in (1, 9) or (y < 8 and x == 9) or (y >= 8 and x == 1)
                        h = (x * 37 + y * 73) % 19
                        if h in (0, 1):
                            c = "#5da638"  # Đốm rêu xanh tươi
                        elif is_hi:
                            c = "#b5b5c2"  # Viền gạch phản quang
                        else:
                            c = shades[(x * 11 + y * 23) % len(shades)]
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("stone_bricks", draw)

    @classmethod
    def crying_obsidian(cls) -> Texture:
        def draw(px):
            base = ["#1a0f2e", "#251442", "#110721", "#331859"]
            for y in range(16):
                for x in range(16):
                    h = (x * 43 + y * 19) % 23
                    if h == 0:
                        c = "#f0abfc"  # Tím neon dạ quang
                    elif h in (1, 2):
                        c = "#c084fc"
                    elif h == 3:
                        c = "#7e22ce"
                    else:
                        c = base[(x * 7 + y * 13) % len(base)]
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("crying_obsidian", draw)

    @classmethod
    def fragile_sand(cls) -> Texture:
        def draw(px):
            palette = ["#ea580c", "#c2410c", "#f97316", "#9a3412"]
            for y in range(16):
                for x in range(16):
                    is_crack = (x == y and 2 < x < 13) or (x + y == 15 and 4 < x < 12)
                    c = "#451a03" if is_crack else palette[(x * 29 + y * 41) % len(palette)]
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("fragile_sand", draw)

    @classmethod
    def trapdoor(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    is_b = x < 3 or x > 12 or y < 3 or y > 12
                    is_c = x in (7, 8) or y in (7, 8)
                    if is_b or is_c:
                        c = "#9a6a38" if (x + y) % 3 == 0 else "#b88349"
                        if x in (0, 15) or y in (0, 15):
                            c = "#5c3d1e"
                    else:
                        c = "#1f1207"  # Khe hở tối
                    px[x, y] = (*_hex_to_rgb(c), 255)
            for dy in (3, 4, 11, 12):
                for dx in (1, 2):
                    px[dx, dy] = (*_hex_to_rgb("#52525b"), 255)
        return cls._make_tex("trapdoor", draw)

    @classmethod
    def pressure_plate(cls, is_heavy: bool = False, is_split: bool = False) -> Texture:
        key = f"plate_{'heavy' if is_heavy else ('split' if is_split else 'soft')}"
        def draw(px):
            for y in range(16):
                for x in range(16):
                    border = x in (0, 15) or y in (0, 15)
                    if is_heavy:
                        c = "#52525b" if border else ("#f4f4f5" if (x + y) % 2 == 0 else "#d4d4d8")
                        if x in (2, 13) and y in (2, 13):
                            c = "#27272a"
                    elif is_split:
                        c = "#0e7490" if border else ("#22d3ee" if (x + y) % 2 == 0 else "#06b6d4")
                        if x in (2, 13) and y in (2, 13):
                            c = "#155e75"
                    else:
                        c = "#784b1f" if border else ("#b4793d" if y % 4 == 0 else "#d29553")
                        if x in (2, 13) and y in (2, 13):
                            c = "#45270c"
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex(key, draw)

    @classmethod
    def end_frame(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    if x < 2 or x > 13 or y < 2 or y > 13:
                        c = "#134e4a" if (x + y) % 2 == 0 else "#042f2e"
                    else:
                        c = "#fef08a"  # Đá End vàng sáng rực
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("end_frame", draw)

    @classmethod
    def portal_vortex(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    dist = math.sqrt((x - 7.5)**2 + (y - 7.5)**2)
                    h = (x * 37 + y * 59) % 29
                    if dist < 2.5:
                        c = "#22d3ee"  # Lõi thiên hà sáng xanh
                    elif h in (0, 1):
                        c = "#f472b6"
                    elif h in (2, 3, 4):
                        c = "#a855f7"
                    else:
                        c = "#05010a"
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("portal_vortex", draw)

    @classmethod
    def lava_surface(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    v = math.sin(x * 0.7) + math.cos(y * 0.7)
                    c = "#fde047" if v > 0.9 else ("#ea580c" if v > 0.0 else "#b91c1c")
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("lava_surface", draw)


# ===========================================================================
# 3. HỆ THỐNG ÁNH SÁNG VÀ BIOME ĐA NGUỒN
# ===========================================================================
class BiomeEnvironment(Entity):
    def __init__(self) -> None:
        super().__init__()
        self.current_biome: str = "overworld"
        self.clouds: List[Entity] = []
        self.particles: List[Entity] = []
        self.lava_plane: Optional[Entity] = None
        self.dir_light: Optional[DirectionalLight] = None
        self.amb_light: Optional[AmbientLight] = None
        self.portal_light: Optional[PointLight] = None

        self._init_lights()
        self._init_clouds()
        self._init_lava()
        self._init_particles()
        self.apply_biome("overworld")

    def _init_lights(self) -> None:
        self.amb_light = AmbientLight(color=color.rgba32(240, 245, 255, 195))
        self.dir_light = DirectionalLight(
            color=color.rgb32(255, 250, 230),
            direction=Vec3(-1.4, -2.5, -1.2),
            shadows=False,
        )
        self.portal_light = PointLight(
            color=color.rgb32(216, 120, 255),
            position=Vec3(0, 1.2, 0),
        )

    def _init_clouds(self) -> None:
        rng = random.Random(42)
        for _ in range(18):
            w = rng.randint(3, 8)
            d = rng.randint(2, 5)
            cloud = Entity(
                parent=self,
                model="cube",
                scale=(w, 0.75, d),
                position=(rng.uniform(-35, 35), rng.uniform(8.0, 12.0), rng.uniform(-30, 25)),
                color=color.rgba32(255, 255, 255, 240),
            )
            cloud.speed = rng.uniform(0.4, 0.8)
            self.clouds.append(cloud)

    def _init_lava(self) -> None:
        self.lava_plane = Entity(
            parent=self,
            model="plane",
            scale=(100, 1, 100),
            position=(4, -4.8, -4),
            texture=VoxelTextures.lava_surface(),
            texture_scale=(32, 32),
            unlit=True,
            enabled=False,
        )

    def _init_particles(self) -> None:
        rng = random.Random(99)
        for _ in range(75):
            p = Entity(
                parent=self,
                model="cube",
                scale=0.16,
                position=(rng.uniform(-18, 24), rng.uniform(-4, 9), rng.uniform(-22, 16)),
                color=color.rgb32(255, 102, 0),
                unlit=True,
                enabled=False,
            )
            p.vy = rng.uniform(0.8, 1.8)
            p.phase = rng.uniform(0, math.pi * 2)
            self.particles.append(p)

    def apply_biome(self, name: str) -> None:
        name = name.lower()
        self.current_biome = name

        def _set_window_color(col):
            try:
                window.color = col
            except Exception:
                pass

        if name == "overworld":
            _set_window_color(color.rgb32(125, 195, 240))
            try:
                scene.fog_color = color.rgb32(125, 195, 240)
                scene.fog_density = 0.002
            except Exception:
                pass
            if self.amb_light:
                self.amb_light.color = color.rgba32(235, 245, 255, 205)
            if self.dir_light:
                self.dir_light.color = color.rgb32(255, 248, 220)
            for c in self.clouds:
                c.enabled = True
            if self.lava_plane:
                self.lava_plane.enabled = False
            for p in self.particles:
                p.enabled = False

        elif name == "nether":
            _set_window_color(color.rgb32(55, 8, 6))
            try:
                scene.fog_color = color.rgb32(85, 15, 10)
                scene.fog_density = 0.004
            except Exception:
                pass
            if self.amb_light:
                self.amb_light.color = color.rgba32(255, 110, 50, 185)
            if self.dir_light:
                self.dir_light.color = color.rgb32(255, 160, 60)
            for c in self.clouds:
                c.enabled = False
            if self.lava_plane:
                self.lava_plane.enabled = True
            for i, p in enumerate(self.particles):
                p.enabled = True
                p.color = color.rgb32(255, 80, 0) if i % 2 == 0 else color.rgb32(255, 220, 20)

        elif name == "end":
            _set_window_color(color.rgb32(10, 4, 18))
            try:
                scene.fog_color = color.rgb32(24, 10, 44)
                scene.fog_density = 0.003
            except Exception:
                pass
            if self.amb_light:
                self.amb_light.color = color.rgba32(180, 120, 255, 185)
            if self.dir_light:
                self.dir_light.color = color.rgb32(230, 180, 255)
            for c in self.clouds:
                c.enabled = False
            if self.lava_plane:
                self.lava_plane.enabled = False
            for i, p in enumerate(self.particles):
                p.enabled = True
                p.color = color.rgb32(232, 121, 249) if i % 2 == 0 else color.rgb32(168, 85, 247)

    def update(self) -> None:
        dt = time.dt
        t = time.time()
        if self.current_biome == "overworld":
            for c in self.clouds:
                c.x += c.speed * dt
                if c.x > 35:
                    c.x = -35
        elif self.current_biome in ("nether", "end"):
            if self.lava_plane and self.lava_plane.enabled:
                self.lava_plane.texture_offset = (
                    math.sin(t * 0.4) * 0.35,
                    math.cos(t * 0.3) * 0.35,
                )
            for p in self.particles:
                p.y += p.vy * dt
                p.x += math.sin(t * 2.5 + p.phase) * 0.5 * dt
                p.rotation_y += 90 * dt
                p.rotation_x += 60 * dt
                if p.y > 9.5:
                    p.y = -4.0


_ENV_INSTANCE: Optional[BiomeEnvironment] = None

def setup_environment() -> BiomeEnvironment:
    global _ENV_INSTANCE
    if _ENV_INSTANCE is None:
        _ENV_INSTANCE = BiomeEnvironment()
    return _ENV_INSTANCE

def set_biome(name: str) -> None:
    setup_environment().apply_biome(name)
