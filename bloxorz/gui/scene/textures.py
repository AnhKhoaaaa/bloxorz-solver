"""Procedural 16x16 Pixel-Art Voxel Texture Generator & Minecraft HUD Renderer (NumPy + PIL.Image)."""
from __future__ import annotations

import math
import random
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _hex_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


class VoxelTextureCatalog:
    """Synthesizes 16x16 RGBA pixel-art textures for all Minecraft blocks using NumPy & Pillow.

    All textures are designed for `GL_NEAREST` magnification/minification filtering to
    preserve crisp pixel boundaries without bilinear blurring.
    """

    TILE_SIZE = 16

    # Texture indices in the horizontal atlas
    TEX_OAK_BARK = 0
    TEX_OAK_TOP = 1
    TEX_STONE_BRICKS = 2
    TEX_CRYING_OBSIDIAN = 3
    TEX_END_FRAME_TOP = 4
    TEX_END_PORTAL_CORE = 5
    TEX_FRAGILE_SAND = 6
    TEX_OAK_TRAPDOOR = 7
    TEX_PLATE_SOFT = 8
    TEX_PLATE_HEAVY = 9
    TEX_LAVA = 10
    TEX_CLOUD = 11
    NUM_TEXTURES = 12

    def __init__(self, seed: int = 1337) -> None:
        self._seed = seed
        self.images: dict[str, Image.Image] = {}
        self.arrays: dict[str, np.ndarray] = {}
        self._build_all()
        self.atlas_image, self.atlas_array = self._build_atlas()

    def _make_tex(
        self, name: str, salt: int, pixel_fn: Callable[[int, int, random.Random], tuple[int, int, int, int]]
    ) -> Image.Image:
        rng = random.Random(self._seed + salt * 97)
        arr = np.zeros((self.TILE_SIZE, self.TILE_SIZE, 4), dtype=np.uint8)
        for y in range(self.TILE_SIZE):
            for x in range(self.TILE_SIZE):
                arr[y, x] = pixel_fn(x, y, rng)
        img = Image.fromarray(arr, mode="RGBA")
        self.arrays[name] = arr
        self.images[name] = img
        return img

    def _build_all(self) -> None:
        # 1. Oak Log Side Bark (Exact 1:1 match with bloxzor.html)
        def oak_bark(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            cols = ["#5c4328", "#4e3820", "#6b4e30", "#3f2d18"]
            stripe = cols[(x * 3) % len(cols)]
            if (x * 17 + y * 31) % 7 == 0:
                n = "#3b2915"
            elif (x * 13 + y * 7) % 5 == 0:
                n = "#735536"
            else:
                n = stripe
            return _hex_rgba(n)

        self._make_tex("oak_bark", 1, oak_bark)

        # 2. Oak Log Cross-Section Top/Bottom (Exact 1:1 match with bloxzor.html)
        def oak_top(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            dist = max(abs(x - 7.5), abs(y - 7.5))
            if dist >= 6.5:
                c = "#5c4328" if (x + y) % 2 == 0 else "#4a351e"
            elif int(round(dist)) % 2 == 0:
                c = "#b8945f"
            else:
                c = "#9e7c4a"
            return _hex_rgba(c)

        self._make_tex("oak_top", 2, oak_top)

        # 3. Stone Bricks with grooves & moss (Exact 1:1 match with bloxzor.html)
        def stone_bricks(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            is_horizontal_groove = (y == 0 or y == 8)
            is_vertical_groove = (y < 8 and x == 8) or (y >= 8 and (x == 0 or x == 15))
            if is_horizontal_groove or is_vertical_groove:
                return _hex_rgba("#38383c")
            is_highlight = (y == 1 or y == 9 or (y < 8 and x == 9) or (y >= 8 and x == 1))
            h = (x * 37 + y * 73) % 19
            if h in (0, 1):
                return _hex_rgba("#4f7835")  # Green moss
            if h == 2:
                return _hex_rgba("#658f46")  # Light moss
            if is_highlight:
                return _hex_rgba("#96969e")  # Bevel highlight
            shades = ["#7a7a82", "#707078", "#83838c", "#686870"]
            return _hex_rgba(shades[(x * 11 + y * 23) % len(shades)])

        self._make_tex("stone_bricks", 3, stone_bricks)

        # 4. Start Tile (S): Crying Obsidian (Exact 1:1 match with bloxzor.html)
        def crying_obsidian(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            h = (x * 43 + y * 19) % 23
            if h == 0:
                return _hex_rgba("#d96bff")
            if h in (1, 2):
                return _hex_rgba("#9922ff")
            if h == 3:
                return _hex_rgba("#4c127a")
            base = ["#181026", "#211536", "#110b1c", "#2b1b47"]
            return _hex_rgba(base[(x * 7 + y * 13) % len(base)])

        self._make_tex("crying_obsidian", 4, crying_obsidian)

        # 5. Goal Tile (G): End Portal Frame Top (Exact 1:1 match with bloxzor.html)
        def end_frame_top(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            is_outer = (x < 2 or x > 13 or y < 2 or y > 13)
            if is_outer:
                return _hex_rgba("#326b5c" if (x + y) % 2 == 0 else "#245246")
            return _hex_rgba("#d8d29c")

        self._make_tex("end_frame_top", 5, end_frame_top)

        # 6. End Portal Cosmic Core base texture
        def end_portal_core(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            r = rng.random()
            if r < 0.08:
                return _hex_rgba("#67e8f9")
            if r < 0.18:
                return _hex_rgba("#c084fc")
            return _hex_rgba("#070312")

        self._make_tex("end_portal_core", 6, end_portal_core)

        # 7. Fragile Tile (F / !): Cracked Sand (Exact 1:1 match with bloxzor.html)
        def fragile_sand(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            is_crack = (x == y and 2 < x < 13) or (x + y == 15 and 4 < x < 12)
            if is_crack:
                return _hex_rgba("#592305")
            palette = ["#d67229", "#c2611d", "#e08338", "#ab5012"]
            return _hex_rgba(palette[(x * 29 + y * 41) % len(palette)])

        self._make_tex("fragile_sand", 7, fragile_sand)

        # 8. Bridge Tile (B): Oak Trapdoor with 4 window insets & iron hinges (Exact 1:1 match with bloxzor.html)
        def oak_trapdoor(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            # Iron hinges at (1,3), (1,11)
            if x in (1, 2) and (3 <= y <= 4 or 11 <= y <= 12):
                return _hex_rgba("#4a4a52")
            is_border = (x < 3 or x > 12 or y < 3 or y > 12)
            is_cross = (x in (7, 8) or y in (7, 8))
            if is_border or is_cross:
                c = "#8c693e" if (x + y) % 3 == 0 else "#a37b49"
                if x in (0, 15) or y in (0, 15):
                    c = "#5c4328"
                return _hex_rgba(c)
            return _hex_rgba("#291d12")  # Dark cutout window

        self._make_tex("oak_trapdoor", 8, oak_trapdoor)

        # 9. Soft Pressure Plate ('o'): Minecraft Oak Wood Pressure Plate with corner rivets
        def plate_soft(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            border = (x == 0 or y == 0 or x == 15 or y == 15)
            if border:
                c = "#6e502d"
            elif y % 4 == 0:
                c = "#997243"
            else:
                c = "#b58852"
            if (x in (2, 13)) and (y in (2, 13)):
                c = "#4f381f"  # Rivet
            return _hex_rgba(c)

        self._make_tex("plate_soft", 9, plate_soft)

        # 10. Heavy Pressure Plate ('x'): Minecraft Iron Heavy Pressure Plate with corner rivets
        def plate_heavy(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            border = (x == 0 or y == 0 or x == 15 or y == 15)
            if border:
                c = "#686870"
            elif (x + y) % 2 == 0:
                c = "#d8d8e2"
            else:
                c = "#c4c4cf"
            if (x in (2, 13)) and (y in (2, 13)):
                c = "#44444a"  # Rivet
            return _hex_rgba(c)

        self._make_tex("plate_heavy", 10, plate_heavy)

        # 11. Nether Lava Ocean surface texture
        def lava_tex(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            wave_val = math.sin(x * 0.6) + math.cos(y * 0.6)
            if wave_val > 0.8:
                return _hex_rgba("#fef08a")
            if wave_val > 0.0:
                return _hex_rgba("#f97316")
            return _hex_rgba("#dc2626") if rng.random() < 0.5 else _hex_rgba("#b91c1c")

        self._make_tex("lava", 11, lava_tex)

        # 12. Overworld 3D Voxel Cloud texture
        def cloud_tex(x: int, y: int, rng: random.Random) -> tuple[int, int, int, int]:
            return _hex_rgba("#f8fafc", 235) if (x + y) % 3 != 0 else _hex_rgba("#e2e8f0", 235)

        self._make_tex("cloud", 12, cloud_tex)

    def _build_atlas(self) -> tuple[Image.Image, np.ndarray]:
        """Pack all 12 16x16 textures horizontally into a (16, 192, 4) RGBA atlas."""
        ordered_names = [
            "oak_bark",
            "oak_top",
            "stone_bricks",
            "crying_obsidian",
            "end_frame_top",
            "end_portal_core",
            "fragile_sand",
            "oak_trapdoor",
            "plate_soft",
            "plate_heavy",
            "lava",
            "cloud",
        ]
        atlas_w = self.TILE_SIZE * len(ordered_names)
        atlas_arr = np.zeros((self.TILE_SIZE, atlas_w, 4), dtype=np.uint8)
        for idx, name in enumerate(ordered_names):
            x0 = idx * self.TILE_SIZE
            atlas_arr[:, x0 : x0 + self.TILE_SIZE, :] = self.arrays[name]
        return Image.fromarray(atlas_arr, mode="RGBA"), atlas_arr


class MinecraftHUDRenderer:
    """Renders authentic Minecraft Inventory HUD panels, bevel buttons & Vietnamese badges using PIL."""

    def __init__(self) -> None:
        self._font_xs = self._load_font(10)
        self._font_sm = self._load_font(12)
        self._font_md = self._load_font(14)
        self._font_lg = self._load_font(17)
        self._font_xl = self._load_font(24)
        self.buttons: list[dict] = []

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for candidate in (
            "/usr/share/fonts/jetbrains-mono-fonts/JetBrainsMono-Bold.otf",
            "/usr/share/fonts/liberation-mono-fonts/LiberationMono-Bold.ttf",
            "/usr/share/fonts/google-droid-sans-mono-fonts/DroidSansMono.ttf",
        ):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    @staticmethod
    def _draw_mc_panel(
        draw: ImageDraw.ImageDraw,
        box: tuple[int, int, int, int],
        bg: tuple[int, int, int, int] = (20, 20, 24, 230),
        light_border: tuple[int, int, int, int] = (170, 170, 170, 255),
        dark_border: tuple[int, int, int, int] = (68, 68, 68, 255),
        outer_border: tuple[int, int, int, int] = (0, 0, 0, 255),
        border_w: int = 3,
    ) -> None:
        """Draw an authentic Minecraft stone panel with 3px solid black border & 3D bevels."""
        x0, y0, x1, y1 = box
        draw.rectangle([x0, y0, x1, y1], fill=outer_border)
        bw = border_w
        draw.rectangle([x0 + bw, y0 + bw, x1 - bw, y1 - bw], fill=bg)
        # Top & Left highlight
        draw.line([(x0 + bw, y0 + bw), (x1 - bw, y0 + bw)], fill=light_border, width=bw)
        draw.line([(x0 + bw, y0 + bw), (x0 + bw, y1 - bw)], fill=light_border, width=bw)
        # Bottom & Right shadow
        draw.line([(x0 + bw, y1 - bw), (x1 - bw, y1 - bw)], fill=dark_border, width=bw)
        draw.line([(x1 - bw, y0 + bw), (x1 - bw, y1 - bw)], fill=dark_border, width=bw)

    def _draw_text_shadow(
        self,
        draw: ImageDraw.ImageDraw,
        pos: tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        fill: tuple[int, int, int, int],
        shadow_fill: tuple[int, int, int, int] = (0, 0, 0, 255),
        offset: int = 2,
    ) -> None:
        x, y = pos
        draw.text((x + offset, y + offset), text, font=font, fill=shadow_fill)
        draw.text((x, y), text, font=font, fill=fill)

    def render_hud(
        self,
        width: int,
        height: int,
        *,
        stage_name: str,
        stage_idx: int,
        total_stages: int,
        biome_name: str,
        moves: int,
        optimal_moves: int | None,
        ai_status: str,
        banner_title: str | None = None,
        banner_subtitle: str | None = None,
        banner_color: tuple[int, int, int] = (85, 255, 85),
        hover_btn_id: str | None = None,
    ) -> np.ndarray:
        """Render the complete Minecraft HUD overlay matching Image 2 exactly."""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        self.buttons = []

        # 1. Top-Left Title Box (Green retro title + Stage + Moves)
        panel_w = min(440, max(360, width // 3))
        self._draw_mc_panel(draw, (18, 14, 18 + panel_w, 88))
        self._draw_text_shadow(
            draw, (32, 22), "BLOXORZ: VOXEL EDITION", self._font_lg, (85, 255, 85, 255)
        )
        self._draw_text_shadow(
            draw, (32, 44), stage_name.upper(), self._font_xs, (200, 200, 200, 255)
        )
        opt_s = f"  OPTIMAL: {optimal_moves}" if optimal_moves is not None else ""
        stats_line = f"STAGE: {stage_idx + 1}/{total_stages}   MOVES: {moves}{opt_s}"
        self._draw_text_shadow(
            draw, (32, 62), stats_line, self._font_sm, (85, 255, 255, 255)
        )

        # 2. Top-Right / Controls Bar (Authentic Minecraft Bevel Buttons matching Image 2)
        row1 = [
            ("biome_overworld", "Overworld", biome_name == "overworld", "biome_overworld"),
            ("biome_nether", "Nether", biome_name == "nether", "biome_nether"),
            ("biome_end", "The End", biome_name == "end", "biome_end"),
            ("sep1", "|", False, "sep"),
            ("ai_astar", "AI Solve (A*)", False, "ai"),
            ("ai_bfs", "AI Solve (BFS)", False, "ai"),
            ("sep2", "|", False, "sep"),
            ("undo", "Undo (U)", False, "normal"),
        ]
        row2 = [
            ("restart", "Restart (R)", False, "normal"),
            ("prev_stage", "< Prev (P)", False, "normal"),
            ("next_stage", "Next (N) >", False, "normal"),
        ]

        def draw_button_row(btn_defs: list[tuple[str, str, bool, str]], y_top: int, container_w: int) -> None:
            btn_h = 32
            gap = 6
            # Measure widths
            widths: list[int] = []
            for btn_id, label, _, style in btn_defs:
                if style == "sep":
                    widths.append(12)
                else:
                    bb = draw.textbbox((0, 0), label, font=self._font_xs)
                    widths.append((bb[2] - bb[0]) + 20)
            total_w = sum(widths) + gap * (len(btn_defs) - 1)
            start_x = 24 + 18 + 4

            curr_x = start_x
            for (btn_id, label, is_active, style), bw in zip(btn_defs, widths):
                if style == "sep":
                    draw.text((curr_x + 3, y_top + 6), "|", font=self._font_sm, fill=(85, 85, 85, 255))
                    curr_x += bw + gap
                    continue

                is_hover = hover_btn_id == btn_id
                # Authentic Minecraft Button Themes
                if is_active:
                    if style == "biome_nether":
                        bg = (150, 34, 27, 255)
                        light_b = (212, 66, 56, 255)
                        dark_b = (82, 15, 11, 255)
                    elif style == "biome_end":
                        bg = (103, 33, 133, 255)
                        light_b = (166, 75, 204, 255)
                        dark_b = (54, 12, 71, 255)
                    else:
                        bg = (76, 133, 39, 255)
                        light_b = (115, 189, 66, 255)
                        dark_b = (43, 79, 20, 255)
                    txt_c = (255, 255, 255, 255)
                elif style == "ai":
                    bg = (34, 112, 128, 255) if not is_hover else (52, 148, 168, 255)
                    light_b = (85, 255, 255, 255)
                    dark_b = (16, 58, 68, 255)
                    txt_c = (85, 255, 255, 255)
                else:
                    bg = (110, 110, 110, 255) if not is_hover else (126, 136, 191, 255)
                    light_b = (170, 170, 170, 255) if not is_hover else (180, 190, 255, 255)
                    dark_b = (68, 68, 68, 255) if not is_hover else (74, 82, 133, 255)
                    txt_c = (224, 224, 224, 255) if not is_hover else (255, 255, 160, 255)

                box = (curr_x, y_top, curr_x + bw, y_top + btn_h)
                self._draw_mc_panel(draw, box, bg=bg, light_border=light_b, dark_border=dark_b)
                bb = draw.textbbox((0, 0), label, font=self._font_xs)
                tw, th = bb[2] - bb[0], bb[3] - bb[1]
                tx = curr_x + (bw - tw) // 2
                ty = y_top + (btn_h - th) // 2 - 1
                self._draw_text_shadow(draw, (tx, ty), label, self._font_xs, txt_c)
                self.buttons.append({"id": btn_id, "rect": box})
                curr_x += bw + gap

        # Outer bar container for controls
        ctrl_bar_w = min(width - 36, 880)
        self._draw_mc_panel(draw, (18, 102, 18 + ctrl_bar_w, 184))
        draw_button_row(row1, 112, ctrl_bar_w)
        draw_button_row(row2, 146, ctrl_bar_w)

        # 3. Bottom Panels Matching Image 2
        # Panel A: Controls Legend with Minecraft Badges
        p_left_w = min(660, width - 36)
        p_left_h = 76
        p_left_y = height - p_left_h - 18
        self._draw_mc_panel(draw, (18, p_left_y, 18 + p_left_w, height - 18))

        # Row 1 of Controls
        def draw_key_badge(x: int, y: int, txt: str) -> int:
            bb = draw.textbbox((0, 0), txt, font=self._font_xs)
            bw = (bb[2] - bb[0]) + 10
            draw.rectangle([x, y, x + bw, y + 17], fill=(0, 0, 0, 255))
            draw.rectangle([x + 1, y + 1, x + bw - 1, y + 16], fill=(51, 51, 51, 255))
            draw.line([(x + 1, y + 1), (x + bw - 1, y + 1)], fill=(102, 102, 102, 255))
            draw.line([(x + 1, y + 1), (x + 1, y + 16)], fill=(102, 102, 102, 255))
            self._draw_text_shadow(draw, (x + 5, y + 1), txt, self._font_xs, (85, 255, 255, 255), offset=1)
            return bw

        bx = 28
        by = p_left_y + 8
        for k in ("W", "A", "S", "D"):
            bx += draw_key_badge(bx, by, k) + 3
        draw.text((bx + 2, by + 1), "/", font=self._font_xs, fill=(200, 200, 200, 255))
        bx += 14
        bx += draw_key_badge(bx, by, "ARROWS") + 6
        draw.text((bx, by + 1), ": LẬT KHỐI GỖ SỒI    ", font=self._font_xs, fill=(200, 200, 200, 255))
        bx += 164
        bx += draw_key_badge(bx, by, "SPACE") + 6
        draw.text((bx, by + 1), ": AI SOLVE (A*)", font=self._font_xs, fill=(200, 200, 200, 255))

        # Row 2 of Controls
        bx = 28
        by = p_left_y + 29
        bx += draw_key_badge(bx, by, "U") + 5
        draw.text((bx, by + 1), ": HOÀN TÁC   ", font=self._font_xs, fill=(200, 200, 200, 255))
        bx += 105
        bx += draw_key_badge(bx, by, "R") + 5
        draw.text((bx, by + 1), ": CHƠI LẠI   ", font=self._font_xs, fill=(200, 200, 200, 255))
        bx += 105
        bx += draw_key_badge(bx, by, "P / N") + 5
        draw.text((bx, by + 1), ": ĐỔI MÀN   ", font=self._font_xs, fill=(200, 200, 200, 255))
        bx += 100
        for b_num in ("1", "2", "3"):
            bx += draw_key_badge(bx, by, b_num) + 3
        draw.text((bx + 4, by + 1), ": BIOME", font=self._font_xs, fill=(200, 200, 200, 255))

        # Row 3 of Controls
        bx = 28
        by = p_left_y + 50
        bx += draw_key_badge(bx, by, "CHUỘT TRÁI + KÉO") + 6
        draw.text((bx, by + 1), ": GIMBAL ORBIT    ", font=self._font_xs, fill=(200, 200, 200, 255))
        bx += 175
        bx += draw_key_badge(bx, by, "CON LĂN") + 6
        draw.text((bx, by + 1), ": ZOOM", font=self._font_xs, fill=(200, 200, 200, 255))

        # Panel B: Legend Panel (Chú thích khối voxel 16x16)
        p_right_w = 380
        p_right_h = 92
        p_right_x = max(18 + p_left_w + 14, width - p_right_w - 18)
        p_right_y = height - p_right_h - 18
        if width >= 900:
            self._draw_mc_panel(draw, (p_right_x, p_right_y, p_right_x + p_right_w, height - 18))
            rx = p_right_x + 14
            ry = p_right_y + 8
            self._draw_text_shadow(draw, (rx + 24, ry), "CHÚ THÍCH KHỐI VOXEL 16x16:", self._font_xs, (255, 170, 0, 255))
            ry += 18
            draw.text((rx, ry), "CỔNG END ĐA TẦNG (G): Đích (Đứng thẳng 1x1)", font=self._font_xs, fill=(200, 200, 200, 255))
            ry += 16
            draw.text((rx, ry), "BÀN ĐẠP GỖ (o): Bật/tắt cầu khi chạm bất kỳ", font=self._font_xs, fill=(200, 200, 200, 255))
            ry += 16
            draw.text((rx, ry), "BÀN ĐẠP SẮT (x): Cần đứng thẳng đè mạnh", font=self._font_xs, fill=(200, 200, 200, 255))
            ry += 16
            draw.text((rx, ry), "CÁT CAM (! / F): Vỡ nếu đứng thẳng lên trên", font=self._font_xs, fill=(200, 200, 200, 255))

        # 4. Center Victory / Fall Banner
        if banner_title:
            bw, bh = 480, 110
            bx0 = (width - bw) // 2
            by0 = (height - bh) // 2 - 20
            self._draw_mc_panel(
                draw,
                (bx0, by0, bx0 + bw, by0 + bh),
                bg=(0, 0, 0, 235),
                light_border=(*banner_color, 255),
                border_w=4,
            )
            tb = draw.textbbox((0, 0), banner_title, font=self._font_xl)
            tx = bx0 + (bw - (tb[2] - tb[0])) // 2
            self._draw_text_shadow(draw, (tx, by0 + 20), banner_title, self._font_xl, (*banner_color, 255))
            if banner_subtitle:
                sb = draw.textbbox((0, 0), banner_subtitle, font=self._font_sm)
                sx = bx0 + (bw - (sb[2] - sb[0])) // 2
                self._draw_text_shadow(
                    draw, (sx, by0 + 64), banner_subtitle, self._font_sm, (255, 255, 85, 255)
                )

        return np.asarray(img, dtype=np.uint8)

    def hit_test(self, x: float, y: float) -> str | None:
        """Return button ID if screen coordinate (x, y) is inside an interactive HUD button."""
        for btn in self.buttons:
            x0, y0, x1, y1 = btn["rect"]
            if x0 <= x <= x1 and y0 <= y <= y1:
                return btn["id"]
        return None
