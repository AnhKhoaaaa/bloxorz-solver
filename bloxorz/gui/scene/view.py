# bloxorz/gui/scene/view.py
from __future__ import annotations
import math
from typing import Optional
from ursina import Entity, Vec3, camera, mouse, held_keys, invoke

try:
    from bloxorz.gui.scene.theme import setup_environment, set_biome, SoundManager
    from bloxorz.gui.scene.board import BoardMesh
    from bloxorz.gui.scene.block import BlockMesh
    from bloxorz.gui.scene.animate import animate_roll, animate_fall, animate_win
    from bloxorz.gui.scene.camera_controller import SmoothOrbitCamera
except ImportError:
    from theme import setup_environment, set_biome, SoundManager
    from board import BoardMesh
    from block import BlockMesh
    from animate import animate_roll, animate_fall, animate_win
    from camera_controller import SmoothOrbitCamera

# Alias tương thích ngược
OrbitCameraController = SmoothOrbitCamera


class SceneView:
    """Hợp đồng giao tiếp 3D chính thức của phân hệ VT3."""

    def __init__(self) -> None:
        self.env = setup_environment()
        self.cam_ctrl = SmoothOrbitCamera()
        self.board: Optional[BoardMesh] = None
        self.block: Optional[BlockMesh] = None
        self.current_stage = None
        self.current_state = None
        self._is_animating: bool = False

    def is_animating(self) -> bool:
        return getattr(self, "_is_animating", False)

    def load_stage(self, stage, state) -> None:
        self.current_stage = stage
        self.current_state = state
        self._is_animating = False

        if self.board is not None:
            self.board.clear_board()
            from ursina import destroy
            destroy(self.board)

        self.board = BoardMesh(stage)
        if hasattr(self.board, "sync_bridges"):
            self.board.sync_bridges(getattr(state, "bridges_open", frozenset()), animate=False)

        if self.block is None:
            self.block = BlockMesh()

        if hasattr(self.block, "sync_from_state"):
            self.block.sync_from_state(state)
        elif hasattr(self.block, "update_from_state"):
            self.block.update_from_state(state)

        # 1. Khi nạp màn: Hướng camera bao quát bàn cờ rộng rãi, thoáng mắt
        cx = (stage.cols - 1) / 2.0
        cz = -(stage.rows - 1) / 2.0
        span = max(stage.rows, stage.cols, 8) * 1.85
        self.cam_ctrl.set_target(Vec3(cx, 0.0, cz), radius=span)

    def on_move(self, old, action, new) -> None:
        if self.block is None or self.board is None:
            return

        self.current_state = new
        self._is_animating = True

        # 2. Khi khối lật: Cập nhật mục tiêu camera trôi êm theo tâm khối gỗ mới (Dynamic Target Lerp)
        if hasattr(self.block, "get_center_world_pos"):
            new_block_center = self.block.get_center_world_pos(new)
            self.cam_ctrl.set_target(new_block_center)

        def _after_move() -> None:
            if self.board is not None:
                old_bridges = getattr(old, "bridges_open", frozenset())
                new_bridges = getattr(new, "bridges_open", frozenset())
                if old_bridges != new_bridges:
                    SoundManager.play("switch")
                    if hasattr(self.board, "sync_bridges"):
                        self.board.sync_bridges(new_bridges, animate=True)
                    elif hasattr(self.board, "update_bridges"):
                        self.board.update_bridges(new)

                if hasattr(self.board, "depress_switch"):
                    if hasattr(BlockMesh, "get_occupied_cells"):
                        for pos in BlockMesh.get_occupied_cells(new):
                            self.board.depress_switch(pos)
                    else:
                        r, c = new.pos
                        self.board.depress_switch((r, c))

            self._is_animating = False

        # Trường hợp phân tách thành 2 khối vuông nhỏ
        if getattr(old, "pose", None) is None and getattr(new, "pose", None) is None:
            action_cube = getattr(action, "cube", 0)
            moving_cube = getattr(self.block, "cube1", None) if action_cube == 0 else getattr(self.block, "cube2", None)
            still = old.cube2 if action_cube == 0 else old.pos
            moved_to_cube2 = (new.pos == still)
            if moved_to_cube2 != (action_cube == 1):
                c1 = getattr(self.block, "cube1", None)
                c2 = getattr(self.block, "cube2", None)
                if c1 is not None and c2 is not None:
                    self.block.cube1, self.block.cube2 = c2, c1
            r, c = new.cube2 if moved_to_cube2 else new.pos
            target_pos = (float(c), 0.55, -float(r))

            def _finish_split() -> None:
                if hasattr(self.block, "sync_from_state"):
                    self.block.sync_from_state(new)
                elif hasattr(self.block, "update_from_state"):
                    self.block.update_from_state(new)
                _after_move()

            animate_roll(moving_cube, target_pos, on_complete=_finish_split)
            return

        # Khối nguyên vẹn
        animate_roll(self.block, old, action, new, on_complete=_after_move)

    def on_fall(self, old, action) -> None:
        if self.block is None:
            return

        self._is_animating = True

        # 3. Kích hoạt rung chấn Camera Cinematic suy giảm hàm mũ
        if hasattr(self.cam_ctrl, "trigger_shake"):
            self.cam_ctrl.trigger_shake(intensity=0.35)

        def _after_fall() -> None:
            self._is_animating = False

        animate_fall(self.block, old, action, on_complete=_after_fall)

    def on_win(self, state) -> None:
        if self.block is None:
            return

        self.current_state = state
        self._is_animating = True

        def _after_win() -> None:
            self._is_animating = False

        animate_win(self.block, state, on_complete=_after_win)

    def set_biome(self, biome_name: str) -> None:
        set_biome(biome_name)
