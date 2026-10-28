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
TILE_GAP: float = 0.98
ANIM_ROLL_DURATION: float = 0.16


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ===========================================================================
# 1. BỘ TỔNG HỢP ÂM THANH NỘI SINH PYTHON (PROCEDURAL AUDIO SYNTHESIZER)
# ===========================================================================
class SoundManager:
    """Tự động tổng hợp âm thanh bằng Python wave/struct, không cần file ngoài."""

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
        dur = 0.11
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            # Sóng tam giác tần số giảm nhanh tạo tiếng cộc gỗ
            freq = 135 * math.exp(-t * 28)
            thump = math.sin(2 * math.pi * freq * t) * math.exp(-t * 32)
            # Tiếng lạo xạo đá sỏi (noise burst)
            noise = (random.random() * 2 - 1) * math.exp(-t * 45) * 0.4
            samples.append((thump + noise) * 0.65)
        path = os.path.join(tmp_dir, "bloxorz_step.wav")
        return cls._write_wav(path, samples, sr)

    @classmethod
    def _create_switch_sound(cls, tmp_dir: str) -> str:
        sr = 22050
        dur = 0.08
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            freq = 820 if t < 0.035 else 1250
            sq = 0.3 if math.sin(2 * math.pi * freq * t) > 0 else -0.3
            samples.append(sq * math.exp(-t * 35))
        path = os.path.join(tmp_dir, "bloxorz_switch.wav")
        return cls._write_wav(path, samples, sr)

    @classmethod
    def _create_fall_sound(cls, tmp_dir: str) -> str:
        sr = 22050
        dur = 0.65
        n = int(sr * dur)
        samples = []
        for i in range(n):
            t = i / sr
            freq = 280 * math.exp(-t * 3.5) + 30
            val = math.sin(2 * math.pi * freq * t) * math.exp(-t * 3.2) * 0.5
            samples.append(val)
        path = os.path.join(tmp_dir, "bloxorz_fall.wav")
        return cls._write_wav(path, samples, sr)

    @classmethod
    def _create_win_sound(cls, tmp_dir: str) -> str:
        sr = 22050
        dur = 0.95
        n = int(sr * dur)
        samples = [0.0] * n
        notes = [523.25, 659.25, 783.99, 1046.50, 1318.51]  # Hợp âm C5, E5, G5, C6, E6
        for idx, freq in enumerate(notes):
            start = int(idx * 0.12 * sr)
            for i in range(start, n):
                t = (i - start) / sr
                val = math.sin(2 * math.pi * freq * t) * math.exp(-t * 4.2) * 0.22
                samples[i] += val
        path = os.path.join(tmp_dir, "bloxorz_win.wav")
        return cls._write_wav(path, samples, sr)

    @classmethod
    def play(cls, sound_name: str) -> None:
        cls.init()
        wav_path = cls._sounds.get(sound_name)
        if wav_path and os.path.exists(wav_path):
            try:
                Audio(wav_path, autoplay=True, loop=False)
            except Exception:
                pass


# ===========================================================================
# 2. BỘ TẠO TEXTURE PROCEDURAL PIXEL 16x16 CHUẨN MINECRAFT
# ===========================================================================
class VoxelTextures:
    """Sinh Texture 16x16 sắc nét bằng PIL, nội suy NearestFilter."""

    _cache: Dict[str, Texture] = {}

    @classmethod
    def _make_tex(cls, name: str, draw_fn) -> Texture:
        if name in cls._cache:
            return cls._cache[name]
        img = Image.new("RGBA", (16, 16))
        pixels = img.load()
        draw_fn(pixels)
        tex = Texture(img)
        tex.filtering = None  # Giữ pixel sắc cạnh
        cls._cache[name] = tex
        return tex

    @classmethod
    def oak_bark(cls) -> Texture:
        def draw(px):
            cols = ["#5c4328", "#4e3820", "#6b4e30", "#3f2d18"]
            for x in range(16):
                stripe = cols[(x * 3) % len(cols)]
                for y in range(16):
                    c = "#3b2915" if (x * 17 + y * 31) % 7 == 0 else (
                        "#735536" if (x * 13 + y * 7) % 5 == 0 else stripe
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
                    is_h = y in (0, 8)
                    is_v = (y < 8 and x == 8) or (y >= 8 and x in (0, 15))
                    if is_h or is_v:
                        c = "#38383c"
                    else:
                        is_hi = y in (1, 9) or (y < 8 and x == 9) or (y >= 8 and x == 1)
                        h = (x * 37 + y * 73) % 19
                        if h in (0, 1):
                            c = "#4f7835"  # Đốm rêu
                        elif h == 2:
                            c = "#658f46"
                        elif is_hi:
                            c = "#96969e"
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
                    c = "#592305" if is_crack else palette[(x * 29 + y * 41) % len(palette)]
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
    def portal_galaxy(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    h = (x * 37 + y * 59) % 29
                    if h == 0:
                        c = "#55ffff"
                    elif h in (1, 2):
                        c = "#d96bff"
                    elif h in (3, 4):
                        c = "#8b2fc9"
                    else:
                        c = "#06010d"
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("portal_galaxy", draw)

    @classmethod
    def lava_surface(cls) -> Texture:
        def draw(px):
            for y in range(16):
                for x in range(16):
                    v = math.sin(x * 0.7) + math.cos(y * 0.7)
                    c = "#ffdd33" if v > 1.0 else ("#ff6600" if v > 0.1 else "#c92a04")
                    px[x, y] = (*_hex_to_rgb(c), 255)
        return cls._make_tex("lava_surface", draw)


# ===========================================================================
# 3. HỆ THỐNG BIOME & ÁNH SÁNG ĐỘNG
# ===========================================================================
class BiomeEnvironment(Entity):
    """Môi trường 3D với Mây pixel, Biển dung nham cuộn sóng và Hạt hư vô."""

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
        self.amb_light = AmbientLight(color=color.rgba32(255, 255, 255, 175))
        self.dir_light = DirectionalLight(
            color=color.rgb32(255, 245, 214),
            direction=Vec3(-1.2, -2.2, -1.0),
            shadows=False,
        )
        self.portal_light = PointLight(
            color=color.rgb32(180, 80, 255),
            position=Vec3(0, 1, 0),
        )

    def _init_clouds(self) -> None:
        rng = random.Random(42)
        for _ in range(16):
            w = rng.randint(3, 7)
            d = rng.randint(2, 5)
            cloud = Entity(
                parent=self,
                model="cube",
                scale=(w, 0.7, d),
                position=(rng.uniform(-30, 30), rng.uniform(7.0, 11.5), rng.uniform(-25, 22)),
                color=color.rgba32(255, 255, 255, 230),
            )
            cloud.speed = rng.uniform(0.35, 0.75)
            self.clouds.append(cloud)

    def _init_lava(self) -> None:
        self.lava_plane = Entity(
            parent=self,
            model="plane",
            scale=(95, 1, 95),
            position=(4, -4.5, -4),
            texture=VoxelTextures.lava_surface(),
            texture_scale=(28, 28),
            unlit=True,
            enabled=False,
        )

    def _init_particles(self) -> None:
        rng = random.Random(99)
        for _ in range(65):
            p = Entity(
                parent=self,
                model="cube",
                scale=0.15,
                position=(rng.uniform(-16, 22), rng.uniform(-4, 9), rng.uniform(-20, 14)),
                color=color.rgb32(255, 102, 0),
                unlit=True,
                enabled=False,
            )
            p.vy = rng.uniform(0.7, 1.6)
            p.phase = rng.uniform(0, math.pi * 2)
            self.particles.append(p)

    def apply_biome(self, name: str) -> None:
        name = name.lower()
        self.current_biome = name

        if name == "overworld":
            window.color = color.rgb32(135, 206, 235)
            scene.fog_color = color.rgb32(135, 206, 235)
            scene.fog_density = 0.002
            if self.amb_light:
                self.amb_light.color = color.rgba32(255, 255, 255, 195)
            if self.dir_light:
                self.dir_light.color = color.rgb32(255, 245, 215)
            for c in self.clouds:
                c.enabled = True
            if self.lava_plane:
                self.lava_plane.enabled = False
            for p in self.particles:
                p.enabled = False

        elif name == "nether":
            window.color = color.rgb32(43, 7, 5)
            scene.fog_color = color.rgb32(69, 13, 8)
            scene.fog_density = 0.004
            if self.amb_light:
                self.amb_light.color = color.rgba32(255, 120, 70, 175)
            if self.dir_light:
                self.dir_light.color = color.rgb32(255, 175, 80)
            for c in self.clouds:
                c.enabled = False
            if self.lava_plane:
                self.lava_plane.enabled = True
            for i, p in enumerate(self.particles):
                p.enabled = True
                p.color = color.rgb32(255, 95, 0) if i % 2 == 0 else color.rgb32(255, 215, 30)

        elif name == "end":
            window.color = color.rgb32(7, 3, 13)
            scene.fog_color = color.rgb32(19, 8, 36)
            scene.fog_density = 0.003
            if self.amb_light:
                self.amb_light.color = color.rgba32(185, 135, 255, 175)
            if self.dir_light:
                self.dir_light.color = color.rgb32(225, 185, 255)
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
                if c.x > 32:
                    c.x = -32

        elif self.current_biome in ("nether", "end"):
            if self.lava_plane and self.lava_plane.enabled:
                self.lava_plane.texture_offset = (
                    math.sin(t * 0.35) * 0.3,
                    math.cos(t * 0.28) * 0.3,
                )
            for p in self.particles:
                p.y += p.vy * dt
                p.x += math.sin(t * 2.2 + p.phase) * 0.45 * dt
                p.rotation_y += 85 * dt
                p.rotation_x += 55 * dt
                if p.y > 9.5:
                    p.y = -4.0


_ENV_INSTANCE: Optional[BiomeEnvironment] = None


def setup_environment() -> BiomeEnvironment:
    global _ENV_INSTANCE
    if _ENV_INSTANCE is None:
        _ENV_INSTANCE = BiomeEnvironment()
    return _ENV_INSTANCE


def set_biome(name: str) -> None:
    env = setup_environment()
    env.apply_biome(name)