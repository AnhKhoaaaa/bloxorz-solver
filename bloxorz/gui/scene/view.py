# Phụ trách: VT3 - Task 3.1 / 3.2
"""SceneView dựng khung nhìn 3D tổng thể và điều phối hoạt ảnh."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bloxorz.gui.scene.animate import animate_fall, animate_roll, animate_win
from bloxorz.gui.scene.block import BlockView
from bloxorz.gui.scene.board import BoardView

if TYPE_CHECKING:
    from bloxorz.model import Action, State
    from bloxorz.stage import Stage


class SceneView:
    """Khung nhìn 3D chính của game, thực thi đầy đủ Scene Protocol của fake_scene.py."""

    def __init__(self) -> None:
        self.board = BoardView()
        self.block = BlockView()
        self._animating: bool = False

    def is_animating(self) -> bool:
        """Kiểm tra scene có đang bận chạy hoạt ảnh không (phục vụ KeyBuffer)."""
        return self._animating

    def _setup_camera(self, stage: Stage) -> None:
        """Đặt góc nhìn camera isometric bao quát toàn bộ bàn cờ."""
        from ursina import camera

        mid_x = (stage.cols - 1) / 2.0
        mid_z = -(stage.rows - 1) / 2.0
        span = max(stage.rows, stage.cols, 8)

        # Đặt camera ở góc chéo phía trước nhìn xuống tâm bàn cờ
        camera.position = (mid_x + span * 0.65, span * 1.3, mid_z - span * 1.1)
        camera.rotation = (45, -30, 0)

    def load_stage(self, stage: Stage, state: State) -> None:
        """Vẽ lại toàn bộ màn và đặt khối ở vị trí ban đầu."""
        self._animating = False
        self.board.build(stage, state)
        self.block.update_from_state(state)
        self._setup_camera(stage)

    def on_move(self, old: State, action: Action, new: State) -> None:
        """Khối lăn sang trạng thái mới với hoạt ảnh mượt mà."""
        self._animating = True

        def finish_move() -> None:
            self.block.update_from_state(new)
            self.board.update_bridges(new)
            self._animating = False

        if old.pose is not None and new.pose is not None:
            # Khối nguyên lăn sang vị trí mới
            _, target_pos = self.block.target_from_state(new)
            animate_roll(self.block.block, target_pos, on_complete=finish_move)
        elif old.pose is None and new.pose is None:
            # Đang ở trạng thái tách khối
            moving_cube = self.block.cube1 if (action.cube == 0) else self.block.cube2
            r, c = (new.pos if action.cube == 0 else new.cube2) or new.pos
            target_pos = (float(c), 0.55, -float(r))
            animate_roll(moving_cube, target_pos, on_complete=finish_move)
        else:
            # Tách khối hoặc ghép khối
            finish_move()

    def on_fall(self, old: State, action: Action) -> None:
        """Khối bị rơi ra ngoài mép hoặc gạch vỡ."""
        self._animating = True

        def finish_fall() -> None:
            self._animating = False

        target_entity = self.block.block if old.pose is not None else (
            self.block.cube1 if action.cube == 0 else self.block.cube2
        )
        animate_fall(target_entity, on_complete=finish_fall)

    def on_win(self, state: State) -> None:
        """Khối đứng vào đích và tụt xuống lỗ chiến thắng."""
        self._animating = True

        def finish_win() -> None:
            self._animating = False

        animate_win(self.block.block, on_complete=finish_win)

