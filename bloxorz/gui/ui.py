# Phụ trách: VT4 - Task 4.2 / 4.3 / 4.5
"""
Các thành phần nút bấm, nhãn, menu điều khiển (giao diện 2D phủ trên cảnh 3D).

Phong cách "đền cổ" lấy cảm hứng từ Temple Run: bảng đá có mạch ghép, khung vàng đinh tán, rêu và
dây leo rủ xuống, chữ tiêu đề cam vàng viền nâu (CarvedTitle), chữ thường khắc có bóng (CarvedText),
nút đá/vàng/rêu nổi có độ dày, nút đồng xu tròn nổi, vụn đá thỉnh thoảng rơi từ đáy bảng (Crumbs).
Chất liệu vẽ bằng code trong ui_textures.py; font (OFL) nằm trong assets/fonts/.
Cảnh 3D (sàn, khối, nền, ánh sáng) do VT3 phụ trách trong bloxorz/gui/scene/.

- Hud: bảng tiêu đề + trạng thái (góc trên-trái), 4 nút đồng xu Màn trước / Chơi lại / Lùi / Màn sau
  (góc trên-phải), dải phím tắt ở đáy màn hình.
- SolverPanel: bảng đá bên phải gồm nút chọn thuật toán, nút Giải/Replay/Hủy, kết quả và thanh tiến độ.
- Banner: bảng giữa vùng chơi khi thắng hoặc rơi, bật ra có hiệu ứng.
Mọi nút đều gọi press(key) giống hệt khi nhấn phím, nên bàn phím và chuột đi chung 1 đường.
"""

from __future__ import annotations

import random
import textwrap
from pathlib import Path
from typing import Callable

from ursina import Button, Entity, Text, Texture, Vec3, application, camera, color, curve, destroy, time, window

from bloxorz.gui import ui_textures as tex
from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import banner_text, hud_text
from bloxorz.gui.solver_runner import SolverSession, display_name

Press = Callable[[str], None]

FONTS_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
TITLE_FONT = "AlegreyaSC-Black.ttf"     # tiêu đề khắc đá
BUTTON_FONT = "AlegreyaSC-Bold.ttf"     # chữ trên nút
BODY_FONT = "Philosopher-Regular.ttf"   # chữ thường, đủ dấu tiếng Việt

# Ursina tìm font trong fonts_folder trước (nhanh, không quét cả thư mục dự án)
application.fonts_folder = FONTS_DIR
Text.default_font = BODY_FONT

TEMPLE = {
    "gold": color.rgb32(246, 196, 70),
    "gold_deep": color.rgb32(196, 140, 44),
    "parchment": color.rgb32(246, 232, 196),
    "moss": color.rgb32(140, 186, 84),
    "ember": color.rgb32(232, 98, 52),
    "ink": color.rgb32(52, 32, 8),
    "shadow": color.rgba32(8, 4, 0, 210),
}

HELP_TEXT = "Mũi tên/WASD: lăn khối   Space: đổi khối khi tách   R: chơi lại   U: lùi   N/P: màn sau/trước   Esc: thoát"

PIXELS_PER_UNIT = 1000  # độ phân giải chất liệu: số pixel cho 1 đơn vị UI (= chiều cao cửa sổ)
_textures: dict[tuple, Texture] = {}


def _px(width: float, height: float) -> tuple[int, int]:
    return max(8, min(2048, round(width * PIXELS_PER_UNIT))), max(8, min(2048, round(height * PIXELS_PER_UNIT)))


def texture(key: tuple, make: Callable[[], object]) -> Texture:
    """Dựng chất liệu 1 lần rồi dùng lại (cùng key = cùng ảnh)."""
    if key not in _textures:
        _textures[key] = Texture(make(), filtering="bilinear")
    return _textures[key]


def _left() -> float:
    return -window.aspect_ratio / 2


def _right() -> float:
    return window.aspect_ratio / 2


class CarvedText:
    """Chữ khắc: chữ chính + bóng tối lệch xuống dưới-phải, đổi .text là đổi cả hai."""

    def __init__(self, text: str, parent: Entity, position: tuple[float, float], scale: float, col,
                 font: str = BODY_FONT, origin: tuple[float, float] = (-0.5, 0.5), depth: float = 0.0022) -> None:
        x, y = position
        self.shadow = Text(text, parent=parent, position=(x + depth * 0.7, y - depth, -0.011), origin=origin,
                           scale=scale, color=TEMPLE["shadow"], font=font)
        self.main = Text(text, parent=parent, position=(x, y, -0.012), origin=origin, scale=scale, color=col, font=font)

    @property
    def text(self) -> str:
        return self.main.text

    @text.setter
    def text(self, value: str) -> None:
        if value != self.main.text:
            self.main.text = value
            self.shadow.text = value

    @property
    def color(self):
        return self.main.color

    @color.setter
    def color(self, value) -> None:
        self.main.color = value


class CarvedTitle(Entity):
    """
    Chữ tiêu đề kiểu logo Temple Run (cam vàng, vân đá, viền nâu, nổi khối): ảnh dựng sẵn từ font
    bằng ui_textures.carved_title, cao height đơn vị UI. origin như Text: (-0.5, 0.5) = neo góc trên-trái.
    """

    FALL_TINT = (214, 70, 30)  # gam đỏ cam cho chữ báo rơi vực

    def __init__(self, text: str, parent: Entity, position: tuple[float, float], height: float,
                 origin: tuple[float, float] = (0, 0), seed: int = 0, tint: tuple[int, int, int] | None = None) -> None:
        super().__init__(parent=parent, model="quad", origin=origin, position=(*position, -0.012))
        self.title_height = height
        self.set(text, seed, tint)

    def set(self, text: str, seed: int = 0, tint: tuple[int, int, int] | None = None) -> None:
        image = texture(("title", text, seed, tint),
                        lambda: tex.carved_title(text, str(FONTS_DIR / TITLE_FONT), 160, seed, tint))
        self.texture = image
        self.scale = (self.title_height * image.width / image.height, self.title_height)


def stone_panel(width: float, height: float, position: tuple[float, float], seed: int,
                moss_seed: int | None = None, z: float = 1) -> Entity:
    """Bảng đá khung vàng có bóng đổ; moss_seed khác None thì phủ rêu ở mép trên. Con đặt theo tâm bảng."""
    root = Entity(parent=camera.ui, position=(*position, z))
    pad = 0.035
    Entity(parent=root, model="quad", scale=(width + 2 * pad, height + 2 * pad), position=(0.006, -0.012, 0.03),
           texture=texture(("shadow", width, height), lambda: tex.soft_shadow(_px(width + 2 * pad, height + 2 * pad),
                                                                                blur=14, radius=30)))
    Entity(parent=root, model="quad", scale=(width, height), z=0.02,
           texture=texture(("panel", width, height, seed), lambda: tex.stone_panel(_px(width, height), seed)))
    if moss_seed is not None:
        clump_h = min(0.075, height * 0.55)  # chùm rêu ôm mép trên
        moss_h = min(0.15, height * 0.7)     # phần dưới dành cho các cọng dây rủ xuống
        Entity(parent=root, model="quad", scale=(width + 0.006, moss_h), position=(0, height / 2 - moss_h / 2 + 0.009, 0.01),
               texture=texture(("moss", width, moss_h, moss_seed), lambda: tex.moss(
                   _px(width + 0.006, moss_h), moss_seed, clump_height=_px(width, clump_h)[1])))
    return root


class Crumbs(Entity):
    """
    Vụn đá thỉnh thoảng rơi lả tả từ mép dưới 1 bảng đá (cảm giác đền cổ đang sụp):
    mảnh nhỏ rơi có gia tốc, xoay, mờ dần rồi tự hủy. Entity.update() chạy mỗi frame.
    """

    GRAVITY = 0.9

    def __init__(self, panel: Entity, width: float, height: float, seed: int) -> None:
        super().__init__(parent=camera.ui)
        self.panel, self.width, self.height = panel, width, height
        self.rng = random.Random(seed)
        self.falling: list[tuple[Entity, list[float]]] = []
        self.wait = self.rng.uniform(1.0, 3.0)

    def _spawn(self) -> None:
        burst = self.rng.randint(1, 4)
        x0 = self.panel.x + self.rng.uniform(-self.width / 2 + 0.03, self.width / 2 - 0.03)
        for _ in range(burst):
            size = self.rng.uniform(0.006, 0.014)
            piece = Entity(parent=camera.ui, model="quad", scale=size, z=-0.02,
                           position=(x0 + self.rng.uniform(-0.012, 0.012), self.panel.y - self.height / 2 + 0.004),
                           texture=texture(("shard", self.rng.randint(0, 5)), lambda: tex.shard(32, self.rng.randint(0, 99))))
            # [vận tốc x, vận tốc y, tốc độ xoay]
            self.falling.append((piece, [self.rng.uniform(-0.03, 0.03), self.rng.uniform(-0.05, 0.0), self.rng.uniform(-240, 240)]))

    def update(self) -> None:
        dt = time.dt
        if self.panel.enabled:
            self.wait -= dt
            if self.wait <= 0:
                self._spawn()
                self.wait = self.rng.uniform(2.5, 6.0)
        for piece, v in list(self.falling):
            v[1] -= self.GRAVITY * dt
            piece.x += v[0] * dt
            piece.y += v[1] * dt
            piece.rotation_z += v[2] * dt
            piece.alpha = max(0.0, piece.alpha - dt * 0.6)
            if piece.y < -0.55 or piece.alpha <= 0:
                destroy(piece)
                self.falling.remove((piece, v))


class RaisedButton(Button):
    """
    Nút nổi có độ dày: mặt nút (chính Button này) nằm trên thành nút và bóng đổ.
    Rê chuột: sáng lên và nhấc cao; nhấn: lún xuống sát thành nút; nhả: bật lên lại.
    kind: "stone" | "gold" | "moss" cho nút chữ nhật; face=ảnh riêng (đồng xu) thì nút tròn.
    """

    DEPTH = 0.0075
    FIT_CHARS = 10  # nhãn dài hơn số ký tự này thì thu nhỏ chữ cho vừa mặt nút
    NORMAL = color.Color(0.94, 0.94, 0.94, 1)
    HOVER = color.Color(1.1, 1.1, 1.06, 1)
    PRESSED = color.Color(0.8, 0.78, 0.74, 1)

    def __init__(self, label: str, on_click: Callable[[], None], size: tuple[float, float], position: tuple[float, float],
                 parent: Entity, kind: str = "stone", face=None, font: str = BUTTON_FONT, text_size: float = 0.95) -> None:
        width, height = size
        rounded = face is not None
        radius = _px(width, height)[1] // 2 if rounded else None
        self.holder = Entity(parent=parent, position=(*position, -0.005))
        self.shadow = Entity(parent=self.holder, model="quad", scale=(width * 1.3, height * 1.7),
                             position=(0.003, -self.DEPTH - 0.004, 0.003),
                             texture=texture(("btn-shadow", width, height, rounded), lambda: tex.soft_shadow(
                                 _px(width * 1.3, height * 1.7), blur=7, radius=radius if rounded else None)))
        side_color = (92, 56, 14) if rounded else (40, 27, 12)
        Entity(parent=self.holder, model="quad", scale=(width, height), position=(0, -self.DEPTH, 0.002),
               texture=texture(("btn-side", width, height, rounded), lambda: tex.solid_rounded(_px(width, height), side_color, radius)))
        if len(label) > self.FIT_CHARS:
            text_size *= self.FIT_CHARS / len(label) * 1.05
        super().__init__(text=label, parent=self.holder, model="quad", scale=(width, height), position=(0, 0, 0.001),
                         color=self.NORMAL, highlight_color=self.HOVER, pressed_color=self.PRESSED,
                         text_size=text_size, text_color=TEMPLE["parchment"])
        self.size = size
        self.seed = sum(map(ord, label)) % 997 + 1  # mỗi nhãn 1 vân đá riêng
        self.kind = None
        if face is not None:
            self.texture = face
        else:
            self.set_kind(kind)
        if self.text_entity:
            self.text_entity.font = font
            self.text_entity.y = 0.04  # chữ hơi lệch lên vì nửa dưới mặt nút tối hơn
        self.on_click = on_click

    def set_kind(self, kind: str) -> None:
        """Đổi chất liệu mặt nút (đá thường / vàng = đang chọn / rêu = hành động chính)."""
        if kind == self.kind:
            return
        self.kind = kind
        width, height = self.size
        self.texture = texture(("btn-face", width, height, kind, self.seed),
                               lambda: tex.button_face(_px(width, height), kind, seed=self.seed))
        self.text_color = TEMPLE["ink"] if kind == "gold" else TEMPLE["parchment"]

    def _rest(self) -> None:
        self.y = self.DEPTH * 0.35 if self.hovered else 0
        self.shadow.scale_y = self.size[1] * (1.85 if self.hovered else 1.7)

    def on_mouse_enter(self) -> None:
        super().on_mouse_enter()
        self._rest()

    def on_mouse_exit(self) -> None:
        super().on_mouse_exit()
        self._rest()

    def input(self, key: str) -> None:
        super().input(key)
        if key == "left mouse down" and self.hovered:
            self.y = -self.DEPTH * 0.85
            self.shadow.scale_y = self.size[1] * 1.3
        elif key == "left mouse up":
            self._rest()


class Hud:
    """Bảng tiêu đề + trạng thái, 4 nút đồng xu điều khiển ván chơi và dải phím tắt."""

    COINS = (("prev", "Màn trước", "p"), ("restart", "Chơi lại", "r"), ("undo", "Lùi", "u"), ("next", "Màn sau", "n"))
    COIN = 0.072

    def __init__(self, press: Press) -> None:
        left, right = _left(), _right()
        plate = stone_panel(0.66, 0.12, (left + 0.36, 0.42), seed=11, moss_seed=21)
        self.crumbs = Crumbs(plate, 0.66, 0.12, seed=1)
        CarvedTitle("BLOXORZ", plate, (-0.318, 0.066), 0.07, origin=(-0.5, 0.5), seed=1)
        CarvedText("ngôi đền khối hộp", plate, (0.065, 0.03), 0.85, TEMPLE["gold_deep"], font=BUTTON_FONT)
        self.status = CarvedText("", plate, (-0.30, -0.012), 0.85, TEMPLE["parchment"])

        gap = 0.105
        x = right - 0.06 - (len(self.COINS) - 1) * gap
        for i, (icon, label, key) in enumerate(self.COINS):
            face = texture(("coin", icon), lambda icon=icon: tex.coin(_px(self.COIN, self.COIN)[0], icon))
            RaisedButton("", lambda k=key: press(k), (self.COIN, self.COIN), (x + i * gap, 0.44),
                         parent=camera.ui, face=face)
            CarvedText(label, camera.ui, (x + i * gap, 0.385), 0.72, TEMPLE["parchment"], font=BUTTON_FONT, origin=(0, 0))

        strip_h = 0.05
        Entity(parent=camera.ui, model="quad", scale=(window.aspect_ratio, strip_h), position=(0, -0.5 + strip_h / 2, 1),
               texture=texture(("strip", strip_h), lambda: tex.stone(_px(window.aspect_ratio, strip_h), seed=5)))
        Entity(parent=camera.ui, model="quad", scale=(window.aspect_ratio, 0.003), position=(0, -0.5 + strip_h, 0.99),
               color=TEMPLE["gold_deep"])
        CarvedText(HELP_TEXT, camera.ui, (0, -0.5 + strip_h / 2), 0.85, TEMPLE["parchment"], origin=(0, 0))

    def update(self, controller: GameController) -> None:
        # Thông tin khối tách xuống dòng riêng cho vừa bảng tiêu đề
        self.status.text = hud_text(controller, show_result=False).replace("   Đang điều khiển", "\nĐang điều khiển")


class SolverPanel:
    """Bảng solver bên phải: chọn thuật toán, Giải / Replay / Hủy, kết quả và thanh tiến độ replay."""

    WIDTH = 0.42
    BAR_WIDTH = 0.36
    WRAP = 44  # số ký tự mỗi dòng chữ kết quả cho vừa bảng

    def __init__(self, session: SolverSession, press: Press, refresh: Callable[[], None]) -> None:
        rows = (len(session.algorithms) + 1) // 2
        height = 0.35 + 0.058 * rows
        top = 0.34
        center_x = _right() - 0.03 - self.WIDTH / 2
        self.root = stone_panel(self.WIDTH, height, (center_x, top - height / 2), seed=3, moss_seed=7)
        self.crumbs = Crumbs(self.root, self.WIDTH, height, seed=2)
        half_w, half_h = self.WIDTH / 2, height / 2

        CarvedTitle("SOLVER", self.root, (0, half_h - 0.048), 0.068, seed=2)

        def choose(name: str) -> None:
            session.select(name)
            refresh()

        self.algorithm_buttons: dict[str, RaisedButton] = {}
        width = (self.WIDTH - 0.07) / 2
        for i, name in enumerate(session.algorithms):
            row, col = divmod(i, 2)
            x = -width / 2 - 0.008 if col == 0 else width / 2 + 0.008
            y = half_h - 0.105 - row * 0.058
            self.algorithm_buttons[name] = RaisedButton(display_name(name), lambda n=name: choose(n), (width, 0.044),
                                                        (x, y), parent=self.root)

        actions_y = half_h - 0.105 - rows * 0.058 - 0.012
        width = (self.WIDTH - 0.08) / 3
        actions = (("GIẢI", "g", "moss"), ("REPLAY", "enter", "stone"), ("HỦY", "c", "stone"))
        for i, (label, key, kind) in enumerate(actions):
            x = -self.WIDTH / 2 + 0.03 + width / 2 + i * (width + 0.01)
            RaisedButton(label, lambda k=key: press(k), (width, 0.05), (x, actions_y), parent=self.root, kind=kind)
        CarvedText("Phím: G giải · Enter phát / tạm dừng · C hủy · Tab đổi", self.root, (0, actions_y - 0.045),
                   0.66, TEMPLE["gold_deep"], origin=(0, 0))

        self.info = CarvedText("", self.root, (-half_w + 0.035, actions_y - 0.07), 0.8, TEMPLE["parchment"])

        bar_y = -half_h + 0.04
        self.bar_back = Entity(parent=self.root, model="quad", scale=(self.BAR_WIDTH, 0.016), position=(0, bar_y, -0.008),
                               texture=texture(("groove", self.BAR_WIDTH), lambda: tex.solid_rounded(
                                   _px(self.BAR_WIDTH, 0.016), (30, 20, 8))))
        self.bar_fill = Entity(parent=self.root, model="quad", origin=(-0.5, 0), scale=(0, 0.011),
                               position=(-self.BAR_WIDTH / 2 + 0.003, bar_y, -0.009), color=TEMPLE["gold"])

    def update(self, session: SolverSession) -> None:
        for name, button in self.algorithm_buttons.items():
            button.set_kind("gold" if name == session.algorithm else "stone")
        lines = session.text(show_header=False, show_help=False).splitlines()
        self.info.text = "\n".join(textwrap.fill(line, self.WRAP) for line in lines)
        result = session.result
        failed = result is not None and result.status not in ("solved", "cancelled") and not session.solving
        self.info.color = TEMPLE["ember"] if failed else TEMPLE["parchment"]
        progress = session.replay_progress
        self.bar_fill.scale_x = (self.BAR_WIDTH - 0.006) * (progress or 0.0)
        self.bar_fill.visible = progress is not None
        self.bar_back.visible = progress is not None


class Banner:
    """
    Bảng giữa vùng chơi khi thắng (chữ vàng) hoặc rơi vực (chữ đỏ cam); ẩn khi đang chơi.
    App gọi update() mỗi frame; banner chờ hoạt ảnh lăn/rơi chạy xong mới bật ra.
    """

    def __init__(self) -> None:
        panel_left = _right() - 0.03 - SolverPanel.WIDTH
        self.root = stone_panel(0.72, 0.2, ((_left() + panel_left) / 2, 0.02), seed=17, moss_seed=29, z=0.5)
        self.title = CarvedTitle("HOÀN THÀNH!", self.root, (0, 0.022), 0.1, seed=3)
        self.subtitle = CarvedText("", self.root, (0, -0.055), 1.0, TEMPLE["parchment"], origin=(0, 0))
        self.root.enabled = False
        self.crumbs = Crumbs(self.root, 0.72, 0.2, seed=3)
        self.shown: tuple[str, str] | None = None

    def update(self, controller: GameController, animating: bool = False) -> None:
        banner = None if animating else banner_text(controller)
        if banner == self.shown:
            return  # tránh dựng lại chữ mỗi frame
        self.shown = banner
        self.root.enabled = banner is not None
        if banner is not None:
            title, self.subtitle.text = banner
            fell = controller.status == "fell"
            self.title.set(title, seed=3, tint=CarvedTitle.FALL_TINT if fell else None)
            self.root.scale = 0.8
            self.root.animate_scale(Vec3(1, 1, 1), duration=0.28, curve=curve.out_back)
            if fell:
                # rơi vực: cho đá vụn rơi ngay từ banner
                for _ in range(3):
                    self.crumbs._spawn()
