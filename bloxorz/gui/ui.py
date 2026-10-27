# Phụ trách: VT4 - Task 4.2 / 4.3 / 4.5
"""Các thành phần nút bấm, nhãn, menu điều khiển."""

from __future__ import annotations

from ursina import Text, color

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import HELP, hud_text
from bloxorz.gui.solver_runner import SolverSession


class Hud:
    """Dòng trạng thái ở góc trên-trái (màn, số bước, thắng/rơi) và dòng phím tắt ở đáy màn hình."""

    def __init__(self) -> None:
        self.status = Text(text="", position=(-0.85, 0.47), origin=(-0.5, 0.5), scale=1.1)
        self.help = Text(text=HELP.replace("W/A/S/D", "Mũi tên/WASD").replace("Q: thoát", "Esc: thoát"),
                         position=(0, -0.46), origin=(0, 0), scale=0.9, color=color.light_gray)

    def update(self, controller: GameController) -> None:
        self.status.text = hud_text(controller)
        if controller.status == "won":
            self.status.color = color.lime
        elif controller.status == "fell":
            self.status.color = color.orange
        else:
            self.status.color = color.white


class SolverPanel:
    """Panel solver (task 4.3) ngay dưới dòng trạng thái: thuật toán, kết quả giải, tiến độ replay."""

    def __init__(self) -> None:
        self.text = Text(text="", position=(-0.85, 0.42), origin=(-0.5, 0.5), scale=0.9, color=color.azure)

    def update(self, session: SolverSession) -> None:
        self.text.text = session.text()
