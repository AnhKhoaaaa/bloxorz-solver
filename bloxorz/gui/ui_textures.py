# Phụ trách: VT4 - Task 4.5
"""
Vẽ chất liệu cho giao diện 2D phong cách đền cổ (Temple Run) bằng Pillow, không cần file ảnh.

Các hàm trả về ảnh PIL (stone() là RGB, còn lại RGBA có nền trong suốt; ui.py đổi sang Texture
của Ursina) và tất định theo seed, nên mỗi lần mở game giao diện giống hệt nhau.
Module này KHÔNG import Ursina để test được.

- stone_panel(): bảng đá có vân, mạch ghép khối, khung vàng và đinh tán ở 4 góc.
- moss(): rêu mọc thành chùm + vài cọng dây rủ xuống, đặt chồng lên mép trên của bảng.
- button_face(): mặt nút bo góc có gờ sáng phía trên, viền tối phía dưới (cảm giác nổi).
- solid_rounded(): khối bo góc 1 màu (thành nút phía dưới mặt nút).
- soft_shadow(): bóng đổ mờ.
- coin(): đồng xu vàng có biểu tượng khắc chìm (nút tròn nổi).
- carved_title(): chữ tiêu đề cam vàng có vân đá, viền nâu, nổi khối như logo Temple Run.
- shard(): mảnh vụn đá cho hiệu ứng đá rơi.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

RGB = tuple[int, int, int]

STONE: RGB = (96, 76, 52)
STONE_DARK: RGB = (46, 35, 22)
GOLD_LIGHT: RGB = (255, 222, 120)
GOLD: RGB = (232, 176, 52)
GOLD_DEEP: RGB = (150, 98, 22)

FACE_FILLS: dict[str, tuple[RGB, RGB]] = {
    # (màu trên, màu dưới) của gradient mặt nút
    "stone": ((132, 104, 70), (92, 70, 44)),
    "gold": ((255, 214, 100), (214, 150, 36)),
    "moss": ((122, 168, 72), (70, 112, 42)),
}

ICONS = ("prev", "next", "restart", "undo")


def _gradient(size: tuple[int, int], top: RGB, bottom: RGB) -> Image.Image:
    w, h = size
    column = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        column.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return column.resize((w, h))


def _noise(size: tuple[int, int], seed: int, sigma: float = 40) -> Image.Image:
    """Nhiễu xám quanh 128, độ tương phản theo sigma. Tự sinh từ seed (Image.effect_noise không nhận seed)."""
    w, h = size
    raw = Image.frombytes("L", (w, h), random.Random(seed).randbytes(w * h))
    gain = sigma / 74  # độ lệch chuẩn của phân bố đều 0..255 xấp xỉ 74
    return raw.point(lambda v: max(0, min(255, round(128 + (v - 128) * gain))))


def _rounded_mask(size: tuple[int, int], radius: int, inset: int = 0) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (inset, inset, size[0] - 1 - inset, size[1] - 1 - inset), radius=max(radius - inset, 1), fill=255)
    return mask


def stone(size: tuple[int, int], seed: int = 0, base: RGB = STONE) -> Image.Image:
    """Mặt đá: màu nền + vân nhiễu + mạch ghép khối + tối dần về mép."""
    w, h = size
    img = Image.new("RGB", size, base)
    grain = _noise(size, seed, 48).filter(ImageFilter.GaussianBlur(1.2)).convert("RGB")
    img = ImageChops.overlay(img, grain)
    blotch = _noise((max(w // 8, 1), max(h // 8, 1)), seed + 1, 70).resize(size, Image.BICUBIC).convert("RGB")
    img = Image.blend(img, ImageChops.multiply(img, blotch), 0.35)

    img = _masonry(img, seed)

    vignette = Image.new("L", size, 0)
    margin = max(min(w, h) // 6, 4)
    ImageDraw.Draw(vignette).rectangle((margin, margin, w - margin, h - margin), fill=255)
    vignette = vignette.filter(ImageFilter.GaussianBlur(margin))
    return Image.composite(img, ImageChops.multiply(img, Image.new("RGB", size, (150, 140, 128))), vignette)


def _masonry(img: Image.Image, seed: int, block: int = 64) -> Image.Image:
    """Mạch ghép khối đá xếp so le: rãnh tối mảnh, mép dưới rãnh sáng nhẹ như đá đục."""
    w, h = img.size
    rng = random.Random(seed + 7)
    dark = Image.new("L", img.size, 0)
    light = Image.new("L", img.size, 0)
    dd, ld = ImageDraw.Draw(dark), ImageDraw.Draw(light)
    row_h = max(block // 2, 12)
    for row, y in enumerate(range(row_h, h, row_h)):
        dd.line((0, y, w, y), fill=120, width=2)
        ld.line((0, y + 2, w, y + 2), fill=60, width=1)
        x = -rng.uniform(0, block) if row % 2 else -block / 2
        while x < w:
            x += rng.uniform(block * 0.8, block * 1.4)
            dd.line((x, y, x, y + row_h), fill=120, width=2)
    img = Image.composite(Image.new("RGB", img.size, STONE_DARK), img, dark.filter(ImageFilter.GaussianBlur(0.7)))
    return Image.composite(Image.new("RGB", img.size, (170, 146, 112)), img, light.filter(ImageFilter.GaussianBlur(0.7)))


SHARD_EDGE: RGB = (22, 13, 4)
SHARD_LIGHT: RGB = (196, 170, 128)
SHARD_FACE: RGB = (150, 122, 86)


TITLE_TOP: RGB = (255, 222, 96)      # cam vàng sáng ở đỉnh chữ
TITLE_MID: RGB = (240, 150, 30)
TITLE_BOTTOM: RGB = (150, 72, 8)     # cam nâu ở chân chữ
TITLE_EDGE: RGB = (48, 24, 4)        # viền nâu sẫm


def carved_title(text: str, font_path: str, height: int = 160, seed: int = 0, tint: RGB | None = None) -> Image.Image:
    """
    Chữ tiêu đề kiểu logo Temple Run: thân chữ cam vàng có vân đá, gờ sáng phía trên, viền nâu sẫm dày
    và bóng đổ. tint (vd. đỏ cam cho "RƠI XUỐNG VỰC!") thay gam màu cam vàng.
    """
    from PIL import ImageFont

    font = ImageFont.truetype(font_path, height)
    left, top, right, bottom = font.getbbox(text)
    pad = round(height * 0.14)
    size = (right - left + 2 * pad, bottom - top + 2 * pad)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).text((pad - left, pad - top), text, font=font, fill=255)

    top_c, mid_c, bot_c = (TITLE_TOP, TITLE_MID, TITLE_BOTTOM) if tint is None else (
        _mix(tint, (255, 235, 200), 0.45), tint, _mix(tint, (40, 10, 0), 0.55))
    h = size[1]
    upper = _gradient((size[0], h // 2), top_c, mid_c)
    lower = _gradient((size[0], h - h // 2), mid_c, bot_c)
    body = Image.new("RGB", size)
    body.paste(upper, (0, 0))
    body.paste(lower, (0, h // 2))
    body = Image.blend(body, ImageChops.overlay(body, _noise(size, seed, 55).convert("RGB")), 0.6)

    fill = body.convert("RGBA")
    fill.putalpha(mask)
    stroke = max(2, round(height * 0.035))
    # gờ sáng mép trên-trái và tối mép dưới-phải cho chữ nổi khối
    bevel_hi = ImageChops.subtract(mask, ImageChops.offset(mask, 2, 3))
    bevel_lo = ImageChops.subtract(mask, ImageChops.offset(mask, -2, -3))
    fill.paste(Image.new("RGB", size, _mix(top_c, (255, 255, 255), 0.5)), (0, 0), bevel_hi.point(lambda v: v * 0.7))
    fill.paste(Image.new("RGB", size, TITLE_EDGE), (0, 0), bevel_lo.point(lambda v: v * 0.6))

    outline = mask.filter(ImageFilter.MaxFilter(stroke * 2 + 1))
    shadow = Image.new("RGBA", size, (10, 4, 0, 0))
    shadow.putalpha(ImageChops.offset(outline, round(stroke * 0.8), round(stroke * 1.4)).filter(ImageFilter.GaussianBlur(stroke)))
    edge = Image.new("RGBA", size, (*TITLE_EDGE, 0))
    edge.putalpha(outline)
    return Image.alpha_composite(Image.alpha_composite(shadow, edge), fill)


def _gold_ring(size: tuple[int, int], radius: int, frame: int) -> Image.Image:
    gold = _gradient(size, GOLD_LIGHT, GOLD_DEEP)
    shine = Image.new("L", size, 0)
    ImageDraw.Draw(shine).rounded_rectangle((1, 1, size[0] - 2, size[1] // 2), radius=radius, fill=70)
    return Image.composite(Image.new("RGB", size, (255, 240, 190)), gold, shine.filter(ImageFilter.GaussianBlur(3)))


def _stud(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD_DEEP)
    draw.ellipse((cx - r * 0.75, cy - r * 0.8, cx + r * 0.7, cy + r * 0.6), fill=GOLD)
    draw.ellipse((cx - r * 0.45, cy - r * 0.55, cx, cy - r * 0.1), fill=GOLD_LIGHT)


def stone_panel(size: tuple[int, int], seed: int = 0, radius: int = 18, frame: int = 9) -> Image.Image:
    """Bảng đá có khung vàng (gờ sáng phía trên), rãnh tối bên trong khung và 4 đinh tán ở góc."""
    w, h = size
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(_gold_ring(size, radius, frame), (0, 0), _rounded_mask(size, radius))
    out.paste(Image.new("RGB", size, STONE_DARK), (0, 0), _rounded_mask(size, radius, frame - 2))
    out.paste(stone(size, seed), (0, 0), _rounded_mask(size, radius, frame))
    # rãnh khắc mờ ngay trong khung
    groove = Image.new("L", size, 0)
    ImageDraw.Draw(groove).rounded_rectangle(
        (frame + 6, frame + 6, w - frame - 7, h - frame - 7), radius=max(radius - frame, 2), outline=110, width=2)
    out.paste(Image.new("RGB", size, STONE_DARK), (0, 0), groove.filter(ImageFilter.GaussianBlur(0.8)))
    draw = ImageDraw.Draw(out)
    r = frame * 0.95
    for cx, cy in ((frame + r, frame + r), (w - frame - r, frame + r),
                   (frame + r, h - frame - r), (w - frame - r, h - frame - r)):
        _stud(draw, cx, cy, r)
    return out


MOSS_LIGHT: RGB = (168, 196, 78)   # ngọn lá hứng sáng
MOSS_MID: RGB = (96, 142, 50)
MOSS_DEEP: RGB = (34, 62, 24)      # lá nằm khuất phía dưới


def _mix(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _leaf(draw: ImageDraw.ImageDraw, x: float, y: float, length: float, width: float, angle: float, fill: tuple) -> None:
    """Lá hình hạt (nhọn 2 đầu) xoay theo angle."""
    ca, sa = math.cos(angle), math.sin(angle)
    points = []
    for i in range(10):
        t = i / 9 * math.pi
        u, v = math.cos(t) * length / 2, math.sin(t) * width / 2 * math.sin(t) ** 0.4
        points.append((x + u * ca - v * sa, y + u * sa + v * ca))
    for i in range(10):
        t = math.pi + i / 9 * math.pi
        u, v = math.cos(t) * length / 2, math.sin(t) * width / 2 * abs(math.sin(t)) ** 0.4
        points.append((x + u * ca - v * sa, y + u * sa + v * ca))
    draw.polygon(points, fill=fill)


def _leaf_color(rng: random.Random, depth: float) -> RGB:
    """depth 0 = trên cùng (sáng), 1 = dưới cùng (sẫm); thêm lệch màu nhỏ cho tự nhiên."""
    base = _mix(MOSS_LIGHT, MOSS_MID, min(depth * 1.8, 1)) if depth < 0.55 else _mix(MOSS_MID, MOSS_DEEP, (depth - 0.55) / 0.45)
    j = rng.uniform(-14, 14)
    return tuple(max(0, min(255, round(c + j * k))) for c, k in zip(base, (0.8, 1.0, 0.5)))


def _hanging_vine(draw: ImageDraw.ImageDraw, rng: random.Random, x0: float, y0: float, length: float,
                  bottom: float, k: int) -> None:
    """Cọng dây rủ xuống: thân cong mềm, lá mọc so le, lá nhỏ dần về ngọn."""
    sway, phase = rng.uniform(2.5, 6) * k, rng.uniform(0, math.tau)
    prev = (x0, y0)
    steps = int(length / (3 * k))
    for i in range(1, steps):
        y = y0 + i * 3 * k
        if y > bottom:
            break
        x = x0 + math.sin(phase + i * 0.22) * sway * min(1.0, i / 6)
        draw.line((prev, (x, y)), fill=(*MOSS_DEEP, 255), width=max(2, round(2.2 * k * (1 - 0.4 * i / steps))))
        if i % 3 == 0:
            side = 1 if (i // 3) % 2 else -1
            shrink = 1 - 0.4 * i / steps
            col = _leaf_color(rng, 0.25 + 0.3 * i / steps)
            lx, ly = x + side * 5 * k * shrink, y + 1 * k
            angle = math.radians(90 + side * 55)
            _leaf(draw, lx + 0.6 * k, ly + 0.9 * k, 13 * k * shrink, 6.5 * k * shrink, angle, (*_mix(col, MOSS_DEEP, 0.6), 255))
            _leaf(draw, lx, ly, 12 * k * shrink, 5.6 * k * shrink, angle, (*col, 255))
        prev = (x, y)


def moss(size: tuple[int, int], seed: int = 0, clump_height: int | None = None) -> Image.Image:
    """
    Rêu trong suốt đặt chồng lên mép trên của bảng: mọc thành chùm (dày ở 2 góc, thưa ở giữa),
    lá xoay ngẫu nhiên sáng trên sẫm dưới, vài cọng dây rủ xuống có lá so le, đổ bóng mờ xuống mặt đá.
    clump_height: chùm lá chỉ nằm trong khoảng này tính từ mép trên (mặc định cả ảnh); phần còn lại
    của ảnh dành cho các cọng dây rủ dài xuống. Vẽ ở độ phân giải gấp đôi rồi thu nhỏ để khử răng cưa.
    """
    w, h = size
    k = 2
    W, H = w * k, h * k
    CH = min(H, (clump_height or h) * k)
    rng = random.Random(seed)
    leaves = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(leaves)
    margin = 9 * k  # chừa lề để lá không bị xén thẳng ở mép ảnh

    # chùm rêu: luôn có ở 2 góc, giữa thêm vài chùm nhỏ
    corner = min(W * 0.16, 120 * k)
    clumps = [(margin + corner * rng.uniform(0.25, 0.4), corner, rng.uniform(0.8, 1.0)),
              (W - margin - corner * rng.uniform(0.25, 0.4), corner, rng.uniform(0.8, 1.0))]
    for _ in range(rng.randint(1, 3)):
        clumps.append((rng.uniform(W * 0.25, W * 0.75), rng.uniform(W * 0.05, W * 0.11), rng.uniform(0.35, 0.65)))

    vine_roots = []
    for cx, half, droop in clumps:
        depth_px = (CH - margin * 2) * droop
        count = int(half * depth_px / (18 * k)) + 25
        placed = []
        for _ in range(count):
            # dày ở mép trên, thưa dần khi rủ xuống; mép chùm thấp hơn giữa chùm
            dx = rng.gauss(0, half / 2.2)
            edge = max(0.0, 1 - (abs(dx) / half) ** 2)
            dy = depth_px * edge * rng.random() ** 1.7
            x = min(max(cx + dx, margin), W - margin)
            lift = rng.uniform(0, margin * 0.9) * (1 - min(dy / (margin * 4), 1))  # mép trên lởm chởm
            placed.append((x, margin + dy - lift, dy / max(depth_px, 1)))
        placed.sort(key=lambda p: -p[2])  # vẽ lá sâu trước, lá nổi trên cùng vẽ sau
        for x, y, depth in placed:
            length = rng.uniform(7, 13) * k * (1 - depth * 0.35)
            width = length * rng.uniform(0.42, 0.6)
            angle = rng.uniform(0, math.tau)
            col = _leaf_color(rng, depth)
            _leaf(draw, x + 0.8 * k, y + 1.2 * k, length, width, angle, (*_mix(col, MOSS_DEEP, 0.6), 255))  # viền tối
            _leaf(draw, x, y, length * 0.92, width * 0.85, angle, (*col, 255))
            if depth < 0.35 and rng.random() < 0.35:  # đốm phản quang trên lá hứng sáng
                _leaf(draw, x - 0.6 * k, y - 0.8 * k, length * 0.35, width * 0.3, angle, (*_mix(col, (230, 240, 160), 0.55), 230))
        # cọng dây rủ: 3 cọng ở chùm góc, 1 cọng ngắn ở chùm giữa
        for _ in range(3 if droop > 0.6 else 1):
            vine_roots.append((cx + rng.uniform(-half * 0.6, half * 0.6), margin + depth_px * 0.45, droop > 0.6))

    for vx, vy, long_vine in vine_roots:
        room = H - 4 * k - vy
        length = room * (rng.uniform(0.55, 1.0) if long_vine else rng.uniform(0.25, 0.45))
        _hanging_vine(draw, rng, vx, vy, length, H - 4 * k, k)

    # bóng đổ của cả mảng rêu xuống mặt đá
    alpha = leaves.split()[3]
    shadow = Image.new("RGBA", (W, H), (12, 8, 2, 0))
    shadow.putalpha(alpha.point(lambda a: a * 0.55).filter(ImageFilter.GaussianBlur(3 * k)))
    shadow = ImageChops.offset(shadow, 2 * k, 4 * k)
    out = Image.alpha_composite(shadow, leaves)
    return out.resize((w, h), Image.LANCZOS)


def button_face(size: tuple[int, int], kind: str = "stone", seed: int = 0, radius: int | None = None) -> Image.Image:
    """Mặt nút nổi: gradient sáng trên tối dưới, dải phản quang phía trên, viền sẫm, vân đá nhẹ."""
    w, h = size
    radius = radius if radius is not None else h // 3
    top, bottom = FACE_FILLS[kind]
    face = _gradient(size, top, bottom)
    face = Image.blend(face, ImageChops.overlay(face, _noise(size, seed, 30).convert("RGB")), 0.5)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(Image.new("RGB", size, tuple(c // 2 for c in bottom)), (0, 0), _rounded_mask(size, radius))
    out.paste(face, (0, 0), _rounded_mask(size, radius, 2))
    gloss = Image.new("L", size, 0)
    ImageDraw.Draw(gloss).rounded_rectangle((4, 3, w - 5, int(h * 0.42)), radius=max(radius - 3, 1), fill=80)
    out.paste(Image.new("RGB", size, (255, 248, 225)), (0, 0), gloss.filter(ImageFilter.GaussianBlur(2)))
    return out


def solid_rounded(size: tuple[int, int], color: RGB, radius: int | None = None) -> Image.Image:
    radius = radius if radius is not None else size[1] // 3
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(Image.new("RGB", size, color), (0, 0), _rounded_mask(size, radius))
    return out


def soft_shadow(size: tuple[int, int], blur: int = 8, radius: int | None = None, alpha: int = 150) -> Image.Image:
    """Bóng đổ: khối tối bo góc đã làm mờ; size gồm cả phần lề cho vùng mờ."""
    w, h = size
    radius = radius if radius is not None else (h - 4 * blur) // 3
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((2 * blur, 2 * blur, w - 2 * blur, h - 2 * blur), radius=max(radius, 1), fill=alpha)
    out = Image.new("RGBA", size, (10, 6, 2, 0))
    out.putalpha(mask.filter(ImageFilter.GaussianBlur(blur)))
    return out


def shard(size: int, seed: int = 0) -> Image.Image:
    """Mảnh vụn đá nhỏ (đa giác lởm chởm) có mặt sáng phía trên, dùng cho hiệu ứng đá vụn rơi."""
    rng = random.Random(seed)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c = size / 2
    count = rng.randint(4, 6)
    points = [(c + math.cos(i / count * math.tau + rng.uniform(-0.4, 0.4)) * c * rng.uniform(0.55, 0.95),
               c + math.sin(i / count * math.tau + rng.uniform(-0.4, 0.4)) * c * rng.uniform(0.55, 0.95))
              for i in range(count)]
    draw = ImageDraw.Draw(out)
    draw.polygon(points, fill=(*_mix(STONE, SHARD_FACE, rng.uniform(0.2, 0.8)), 255), outline=(*SHARD_EDGE, 255))
    top = sorted(points, key=lambda p: p[1])[:2]
    draw.line(top, fill=(*SHARD_LIGHT, 255), width=max(1, size // 12))
    return out


def _icon(draw: ImageDraw.ImageDraw, name: str, c: float, s: float, fill: tuple, width: int) -> None:
    """Vẽ biểu tượng tại tâm (c, c), cạnh khoảng s."""
    if name in ("prev", "next"):
        sign = -1 if name == "prev" else 1
        tip, back = c + sign * s * 0.42, c - sign * s * 0.18
        draw.polygon(((tip, c), (back, c - s * 0.4), (back, c + s * 0.4)), fill=fill)
        bar = c - sign * s * 0.4
        draw.rectangle((min(bar, bar - sign * width * 1.6), c - s * 0.4, max(bar, bar - sign * width * 1.6), c + s * 0.4), fill=fill)
    elif name == "restart":
        r = s * 0.38
        draw.arc((c - r, c - r, c + r, c + r), start=-60, end=250, fill=fill, width=width)
        ax, ay = c + r * math.cos(math.radians(-60)), c + r * math.sin(math.radians(-60))
        draw.polygon(((ax + s * 0.2, ay - s * 0.02), (ax - s * 0.06, ay - s * 0.2), (ax - s * 0.02, ay + s * 0.14)), fill=fill)
    elif name == "undo":
        r = s * 0.34
        draw.arc((c - r * 0.9, c - r, c + r * 1.3, c + r), start=200, end=90, fill=fill, width=width)
        ax, ay = c - r * 0.9 + 2, c - r * 0.25
        draw.polygon(((ax - s * 0.2, ay), (ax + s * 0.12, ay - s * 0.2), (ax + s * 0.12, ay + s * 0.16)), fill=fill)
    else:
        raise ValueError(f"unknown icon {name!r}")


def coin(size: int, icon: str) -> Image.Image:
    """Đồng xu vàng: vành sẫm, gờ khắc tròn bên trong, biểu tượng khắc chìm (bóng sáng lệch xuống)."""
    if icon not in ICONS:
        raise ValueError(f"unknown icon {icon!r}")
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    disc = _gradient((size, size), GOLD_LIGHT, GOLD_DEEP)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out.paste(Image.new("RGB", (size, size), GOLD_DEEP), (0, 0), mask)
    inner = Image.new("L", (size, size), 0)
    rim = size * 0.08
    ImageDraw.Draw(inner).ellipse((rim, rim, size - 1 - rim, size - 1 - rim), fill=255)
    out.paste(disc, (0, 0), inner)
    draw = ImageDraw.Draw(out)
    ring = size * 0.17
    draw.ellipse((ring, ring, size - 1 - ring, size - 1 - ring), outline=GOLD_DEEP, width=max(size // 40, 1))
    gloss = Image.new("L", (size, size), 0)
    ImageDraw.Draw(gloss).ellipse((size * 0.2, size * 0.1, size * 0.8, size * 0.45), fill=90)
    out.paste(Image.new("RGB", (size, size), (255, 248, 220)), (0, 0), Image.composite(gloss.filter(ImageFilter.GaussianBlur(size / 25)), Image.new("L", (size, size), 0), inner))
    c, s, width = size / 2, size * 0.5, max(size // 14, 2)
    _icon(draw, icon, c, s, (255, 236, 170, 200), width)  # bóng sáng của nét khắc
    _icon(ImageDraw.Draw(out), icon, c - size * 0.012, s, (78, 46, 10, 255), width)
    return out
