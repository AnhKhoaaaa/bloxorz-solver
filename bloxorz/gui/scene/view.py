# bloxorz/gui/scene/view.py
from __future__ import annotations
from typing import Optional
from ursina import Entity, Vec3, camera, invoke
from bloxorz.gui.scene.theme import setup_environment, set_biome
from bloxorz.gui.scene.board import BoardMesh
from bloxorz.gui.scene.block import BlockMesh
from bloxorz.gui.scene.animate import animate_roll, animate_fall, animate_win


class _BiomeKeyListener(Entity):
    """Lắng nghe phím 1 / 2 / 3 để chuyển đổi nhanh giữa Overworld, Nether và The End."""

    def input(self, key: str) -> None:
        if key == "1":
            set_biome("overworld")
        elif key == "2":
            set_biome("nether")
        elif key == "3":
            set_biome("end")


class SceneView:
    """
    Lớp hiển thị cảnh 3D chính thức của phân hệ VT3 (Scene & Animation).
    Thực thi đầy đủ hợp đồng giao tiếp 4 phương thức cho Controller và App:
      1. is_animating()
      2. load_stage(stage, state)
      3. on_move(old, action, new)
      4. on_fall(old, action)
      5. on_win(state)
    """

    def __init__(self) -> None:
        self.env = setup_environment()
        self.hotkey_listener = _BiomeKeyListener()
        self.board: Optional[BoardMesh] = None
        self.block: Optional[BlockMesh] = None
        self.current_stage = None
        self.current_state = None
        self._is_animating: bool = False

    def is_animating(self) -> bool:
        """Kiểm tra scene có đang bận chạy hoạt ảnh không (phục vụ KeyBuffer)."""
        return getattr(self, "_is_animating", False)

    def load_stage(self, stage, state) -> None:
        """Khởi tạo bản đồ, dựng sàn Voxel, đặt khối gỗ sồi và căn chỉnh Camera."""
        self.current_stage = stage
        self.current_state = state
        self._is_animating = False

        if self.board is not None:
            self.board.clear_board()
            from ursina import destroy
            destroy(self.board)

        self.board = BoardMesh(stage)
        self.board.sync_bridges(getattr(state, "bridges_open", frozenset()), animate=False)

        if self.block is None:
            self.block = BlockMesh()

        self.block.sync_from_state(state)
        self._setup_camera(stage)

    def _setup_camera(self, stage) -> None:
        """Đặt góc nhìn Isometric 3D bao quát toàn bộ bàn cờ."""
        cx = (stage.cols - 1) / 2.0
        cz = -(stage.rows - 1) / 2.0
        span = max(stage.rows, stage.cols, 8)

        camera.position = Vec3(cx - span * 0.35, span * 1.15, cz - span * 1.18)
        camera.look_at(Vec3(cx, -0.2, cz))

    def on_move(self, old, action, new) -> None:
        """Khối lăn sang vị trí mới, cập nhật cầu và bàn đạp áp lực."""
        if self.block is None or self.board is None:
            return

        self.current_state = new
        self._is_animating = True

        def _after_move() -> None:
            if self.board is not None:
                if hasattr(self.board, "sync_bridges"):
                    self.board.sync_bridges(getattr(new, "bridges_open", frozenset()), animate=True)
                elif hasattr(self.board, "update_bridges"):
                    self.board.update_bridges(new)

                if hasattr(self.board, "depress_switch"):
                    r, c = new.pos
                    self.board.depress_switch((r, c))
                    pose_name = getattr(new.pose, "name", "")
                    pose_val = getattr(new.pose, "value", new.pose)
                    if pose_val == 1 or pose_name == "HORIZONTAL":
                        self.board.depress_switch((r, c + 1))
                    elif pose_val == 2 or pose_name == "VERTICAL":
                        self.board.depress_switch((r + 1, c))
            self._is_animating = False

        # Trường hợp tách khối
        if getattr(old, "pose", None) is None and getattr(new, "pose", None) is None:
            action_cube = getattr(action, "cube", 0)
            moving_cube = self.block.cube1 if (action_cube == 0) else self.block.cube2
            still = old.cube2 if action_cube == 0 else old.pos
            moved_to_cube2 = (new.pos == still)
            if moved_to_cube2 != (action_cube == 1):
                self.block.cube1, self.block.cube2 = self.block.cube2, self.block.cube1
            r, c = new.cube2 if moved_to_cube2 else new.pos
            target_pos = (float(c), 0.55, -float(r))

            def _finish_split() -> None:
                if hasattr(self.block, "update_from_state"):
                    self.block.update_from_state(new)
                elif hasattr(self.block, "sync_from_state"):
                    self.block.sync_from_state(new)
                _after_move()

            animate_roll(moving_cube, target_pos, on_complete=_finish_split)
            return

        # Khối nguyên vẹn
        try:
            animate_roll(self.block, old, action, new, on_complete=_after_move)
        except TypeError:
            r, c = new.pos
            target_pos = (float(c), 0.55, -float(r))
            animate_roll(getattr(self.block, "block", self.block), target_pos, on_complete=_after_move)

    def on_fall(self, old, action) -> None:
        """Khối bị rơi khỏi sàn (gọi hoạt ảnh lộn nhào rơi xuống vực và rung nhẹ camera)."""
        if self.block is None:
            return

        self._is_animating = True
        orig_cam_pos = Vec3(camera.position)

        def _shake(step: int = 0) -> None:
            if step >= 5:
                camera.position = orig_cam_pos
                return
            offset = 0.08 if step % 2 == 0 else -0.08
            camera.position = orig_cam_pos + Vec3(offset, offset * 0.5, 0)
            invoke(_shake, step + 1, delay=0.04)

        def _finish_fall() -> None:
            self._is_animating = False

        invoke(_shake, 0)
        target_entity = getattr(self.block, "block", self.block)
        animate_fall(target_entity, old, action, on_complete=_finish_fall)

    def on_win(self, state) -> None:
        """Khối đứng vào Cổng End (hạ từ từ xuống lòng cổng và phát pháo hoa pixel)."""
        if self.block is None:
            return

        self._is_animating = True

        def _finish_win() -> None:
            self._is_animating = False

        target_entity = getattr(self.block, "block", self.block)
        animate_win(target_entity, on_complete=_finish_win)
