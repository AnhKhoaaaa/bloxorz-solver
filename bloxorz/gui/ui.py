# Phụ trách: VT4 - Task 4.2 / 4.3 / 4.5
"""
Các thành phần nút bấm, nhãn, menu điều khiển (giao diện 2D phủ trên cảnh 3D).

Phong cách "đền cổ" lấy cảm hứng từ Temple Run: bảng đá tối viền vàng, chữ vàng/giấy cổ,
nút đá đổi sang vàng khi được chọn. Bảng màu nằm ở TEMPLE; cảnh 3D (sàn, khối, nền, ánh sáng)
do VT3 phụ trách trong bloxorz/gui/scene/.

- Hud: bảng tiêu đề + trạng thái (góc trên-trái), hàng nút chơi lại/lùi/đổi màn (góc trên-phải),
  dải phím tắt ở đáy màn hình.
- SolverPanel: bảng đá bên phải gồm nút chọn thuật toán, nút Giải/Replay/Hủy, kết quả và thanh tiến độ.
- Banner: bảng giữa màn hình khi thắng hoặc rơi.
Mọi nút đều gọi press(key) giống hệt khi nhấn phím, nên bàn phím và chuột đi chung 1 đường.
"""

from __future__ import annotations

import textwrap
from typing import Callable

from ursina import Button, Entity, Quad, Text, camera, color, window

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import banner_text, hud_text
from bloxorz.gui.solver_runner import SolverSession, display_name

Press = Callable[[str], None]

TEMPLE = {
    "stone_dark": color.rgba32(36, 28, 18, 225),    # nền bảng đá
    "stone": color.rgb32(92, 70, 44),               # nút thường
    "stone_light": color.rgb32(128, 98, 62),        # nút khi rê chuột
    "gold": color.rgb32(242, 190, 60),              # tiêu đề, nút đang chọn, thanh tiến độ
    "gold_deep": color.rgb32(176, 122, 30),         # viền bảng
    "parchment": color.rgb32(246, 232, 196),        # chữ thường
    "moss": color.rgb32(110, 150, 70),              # thông báo thắng / trạng thái tốt
    "ember": color.rgb32(214, 84, 42),              # rơi vực / lỗi
    "ink": color.rgb32(40, 26, 10),                 # chữ trên nút vàng
}

HELP_TEXT = "Mũi tên/WASD: lăn khối   Space: đổi khối khi tách   R: chơi lại   U: lùi   N/P: màn sau/trước   Esc: thoát"


def _left() -> float:
    return -window.aspect_ratio / 2


def _right() -> float:
    return window.aspect_ratio / 2


def plaque(width: float, height: float, position: tuple[float, float], border: float = 0.006, z: float = 1) -> Entity:
    """Bảng đá viền vàng; con của nó (chữ, nút) đặt theo tọa độ UI tính từ tâm bảng. z nhỏ hơn thì nằm trên."""
    root = Entity(parent=camera.ui, position=(*position, z))
    Entity(parent=root, model=Quad(radius=0.02, aspect=width / height),
           scale=(width + 2 * border, height + 2 * border), color=TEMPLE["gold_deep"], z=0.02)
    Entity(parent=root, model=Quad(radius=0.018, aspect=width / height),
           scale=(width, height), color=TEMPLE["stone_dark"], z=0.01)
    return root


def stone_button(text: str, on_click: Callable[[], None], scale: tuple[float, float],
                 position: tuple[float, float], parent: Entity | None = None, text_size: float = 0.75) -> Button:
    button = Button(
        text=text,
        parent=parent or camera.ui,
        scale=scale,
        position=position,
        radius=0.25,
        color=TEMPLE["stone"],
        highlight_color=TEMPLE["stone_light"],
        text_color=TEMPLE["parchment"],
        text_size=text_size,
    )
    button.on_click = on_click
    return button


def set_primary(button: Button) -> None:
    """Nút hành động chính: màu rêu, để không nhầm với nút đang chọn (vàng)."""
    button.color = TEMPLE["moss"]
    button.highlight_color = TEMPLE["moss"].tint(0.15)
    button.pressed_color = TEMPLE["moss"].tint(-0.15)


def set_selected(button: Button, selected: bool) -> None:
    """Nút đang chọn sáng vàng chữ mực, nút còn lại màu đá."""
    base = TEMPLE["gold"] if selected else TEMPLE["stone"]
    button.color = base
    button.highlight_color = base.tint(0.15)
    button.pressed_color = base.tint(-0.15)
    button.text_color = TEMPLE["ink"] if selected else TEMPLE["parchment"]


class Hud:
    """Bảng tiêu đề + trạng thái, hàng nút điều khiển ván chơi và dải phím tắt."""

    BUTTONS = (("Màn trước", "p"), ("Chơi lại", "r"), ("Lùi 1 bước", "u"), ("Màn sau", "n"))

    def __init__(self, press: Press) -> None:
        left, right = _left(), _right()
        self.title_plate = plaque(0.66, 0.12, (left + 0.36, 0.42))
        self.title = Text("BLOXORZ", parent=self.title_plate, position=(-0.31, 0.052, -0.01),
                          origin=(-0.5, 0.5), scale=1.9, color=TEMPLE["gold"])
        self.subtitle = Text("ngôi đền khối hộp", parent=self.title_plate, position=(-0.03, 0.036, -0.01),
                             origin=(-0.5, 0.5), scale=0.8, color=TEMPLE["gold_deep"])
        self.status = Text("", parent=self.title_plate, position=(-0.31, -0.004, -0.01),
                           origin=(-0.5, 0.5), scale=0.8, color=TEMPLE["parchment"])

        width, gap = 0.14, 0.012
        x = right - 0.03 - width / 2 - (len(self.BUTTONS) - 1) * (width + gap)
        self.buttons = []
        for i, (label, key) in enumerate(self.BUTTONS):
            self.buttons.append(stone_button(label, lambda k=key: press(k), scale=(width, 0.048),
                                             position=(x + i * (width + gap), 0.45)))

        self.help_bar = Entity(parent=camera.ui, model="quad", scale=(window.aspect_ratio, 0.045),
                               position=(0, -0.4775, 1), color=TEMPLE["stone_dark"])
        self.help = Text(HELP_TEXT, position=(0, -0.4775, 0), origin=(0, 0), scale=0.8, color=TEMPLE["parchment"])

    def update(self, controller: GameController) -> None:
        # Thông tin khối tách xuống dòng riêng cho vừa bảng tiêu đề
        self.status.text = hud_text(controller, show_result=False).replace("   Đang điều khiển", "\nĐang điều khiển")


class SolverPanel:
    """Bảng solver bên phải: chọn thuật toán, Giải / Replay / Hủy, kết quả và thanh tiến độ replay."""

    WIDTH = 0.42
    BAR_WIDTH = 0.38
    WRAP = 44  # số ký tự mỗi dòng chữ kết quả cho vừa bảng

    def __init__(self, session: SolverSession, press: Press, refresh: Callable[[], None]) -> None:
        rows = (len(session.algorithms) + 1) // 2
        height = 0.33 + 0.055 * rows
        top = 0.37
        center_x = _right() - 0.03 - self.WIDTH / 2
        self.root = plaque(self.WIDTH, height, (center_x, top - height / 2))
        half_w, half_h = self.WIDTH / 2, height / 2

        Text("SOLVER", parent=self.root, position=(0, half_h - 0.012, -0.01), origin=(0, 0.5),
             scale=1.5, color=TEMPLE["gold"])

        def choose(name: str) -> None:
            session.select(name)
            refresh()

        self.algorithm_buttons: dict[str, Button] = {}
        width = (self.WIDTH - 0.05) / 2
        for i, name in enumerate(session.algorithms):
            row, col = divmod(i, 2)
            x = -width / 2 - 0.006 if col == 0 else width / 2 + 0.006
            y = half_h - 0.085 - row * 0.055
            self.algorithm_buttons[name] = stone_button(
                display_name(name), lambda n=name: choose(n), scale=(width, 0.045),
                position=(x, y, -0.01), parent=self.root)

        actions_y = half_h - 0.085 - rows * 0.055 - 0.01
        width = (self.WIDTH - 0.06) / 3
        self.action_buttons = [
            stone_button(label, lambda k=key: press(k), scale=(width, 0.05),
                         position=(-self.WIDTH / 2 + 0.02 + width / 2 + i * (width + 0.01), actions_y, -0.01),
                         parent=self.root)
            for i, (label, key) in enumerate((("GIẢI", "g"), ("REPLAY", "enter"), ("HỦY", "c")))
        ]
        set_primary(self.action_buttons[0])
        Text("Phím: G giải · Enter phát / tạm dừng · C hủy · Tab đổi", parent=self.root,
             position=(0, actions_y - 0.038, -0.01), origin=(0, 0), scale=0.58, color=TEMPLE["gold_deep"])

        self.info = Text("", parent=self.root, position=(-half_w + 0.02, actions_y - 0.065, -0.01),
                         origin=(-0.5, 0.5), scale=0.75, color=TEMPLE["parchment"])

        bar_y = -half_h + 0.025
        self.bar_back = Entity(parent=self.root, model=Quad(radius=0.5, aspect=self.BAR_WIDTH / 0.014),
                               scale=(self.BAR_WIDTH, 0.014), position=(0, bar_y, -0.01), color=TEMPLE["stone"])
        self.bar_fill = Entity(parent=self.root, model="quad", origin=(-0.5, 0), scale=(0, 0.01),
                               position=(-self.BAR_WIDTH / 2, bar_y, -0.02), color=TEMPLE["gold"])

    def update(self, session: SolverSession) -> None:
        for name, button in self.algorithm_buttons.items():
            set_selected(button, name == session.algorithm)
        lines = session.text(show_header=False, show_help=False).splitlines()
        self.info.text = "\n".join(textwrap.fill(line, self.WRAP) for line in lines)
        result = session.result
        if result is not None and result.status not in ("solved", "cancelled") and not session.solving:
            self.info.color = TEMPLE["ember"]
        else:
            self.info.color = TEMPLE["parchment"]
        progress = session.replay_progress
        self.bar_fill.scale_x = self.BAR_WIDTH * (progress or 0.0)
        self.bar_fill.visible = progress is not None
        self.bar_back.visible = progress is not None


class Banner:
    """
    Bảng giữa màn hình khi thắng (vàng) hoặc rơi vực (đỏ cam); ẩn khi đang chơi.
    App gọi update() mỗi frame; banner chờ hoạt ảnh lăn/rơi chạy xong mới hiện.
    """

    def __init__(self) -> None:
        panel_left = _right() - 0.03 - SolverPanel.WIDTH
        self.root = plaque(0.7, 0.17, ((_left() + panel_left) / 2, 0.02), z=0.5)
        self.title = Text("", parent=self.root, position=(0, 0.025, -0.01), origin=(0, 0), scale=2.6)
        self.subtitle = Text("", parent=self.root, position=(0, -0.05, -0.01), origin=(0, 0),
                             scale=0.95, color=TEMPLE["parchment"])
        self.root.enabled = False
        self.shown: tuple[str, str] | None = None

    def update(self, controller: GameController, animating: bool = False) -> None:
        banner = None if animating else banner_text(controller)
        if banner == self.shown:
            return  # tránh dựng lại chữ mỗi frame
        self.shown = banner
        self.root.enabled = banner is not None
        if banner is not None:
            self.title.text, self.subtitle.text = banner
            self.title.color = TEMPLE["gold"] if controller.status == "won" else TEMPLE["ember"]
