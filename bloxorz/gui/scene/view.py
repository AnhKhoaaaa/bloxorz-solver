# Phụ trách: VT3 - Task 3.1
"""SceneView dựng khung nhìn 3D tổng thể."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bloxorz.gui.scene.block import BlockView
from bloxorz.gui.scene.board import BoardView

if TYPE_CHECKING:
    from bloxorz.model import Action, State
    from bloxorz.stage import Stage


class SceneView:
    """Khung nhìn 3D chính của game, thực thi Scene Protocol của fake_scene.py."""

    def __init__(self) -> None:
        self.board = BoardView()
        self.block = BlockView()

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
        self.board.build(stage, state)
        self.block.update_from_state(state)
        self._setup_camera(stage)

    def on_move(self, old: State, action: Action, new: State) -> None:
        """Khối lăn sang trạng thái mới."""
        self.block.update_from_state(new)

    def on_fall(self, old: State, action: Action) -> None:
        """Khối bị rơi (Task 3.2 sẽ thêm hoạt ảnh rơi vực)."""
        pass

    def on_win(self, state: State) -> None:
        """Khối đứng vào đích (Task 3.2 sẽ thêm hoạt ảnh chiến thắng)."""
        pass
