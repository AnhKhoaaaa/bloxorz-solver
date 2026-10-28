# bloxorz/gui/scene/demo.py
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

# Đảm bảo import được gói `bloxorz` dù chạy trực tiếp từ bất kỳ thư mục nào
ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ursina import Ursina, Entity, Text, color, window  # noqa: E402
from bloxorz.gui.scene.view import SceneView  # noqa: E402
from bloxorz.gui.scene.theme import set_biome  # noqa: E402


# ---------------------------------------------------------------------------
# CƠ CHẾ TƯƠNG THÍCH ENGINE NHÓM & DỰ PHÒNG ĐỘC LẬP (FALLBACK)
# ---------------------------------------------------------------------------
class _FallbackPose(IntEnum):
    STANDING = 0
    HORIZONTAL = 1
    VERTICAL = 2


class _FallbackAction(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


@dataclass(frozen=True)
class _FallbackSwitch:
    pos: Tuple[int, int]
    kind: str = "soft"
    targets: Tuple[str, ...] = ()


@dataclass(frozen=True)
class _FallbackStage:
    grid: List[str]
    rows: int
    cols: int
    start: Tuple[int, int]
    goal: Tuple[int, int]
    switch_at: Dict[Tuple[int, int], _FallbackSwitch] = field(default_factory=dict)
    bridge_at: Dict[Tuple[int, int], str] = field(default_factory=dict)
    initial_bridges: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class _FallbackState:
    pos: Tuple[int, int]
    pose: Optional[_FallbackPose] = _FallbackPose.STANDING
    cube2: Optional[Tuple[int, int]] = None
    bridges_open: FrozenSet[str] = field(default_factory=frozenset)


def _load_stage_and_engine():
    """Ưu tiên nạp Stage/Engine thật của nhóm; nếu chưa có thì dùng bản Fallback chuẩn."""
    try:
        from bloxorz.model import Action, Direction
        from bloxorz.loader import load_stage
        from bloxorz.engine.rules import initial_state, step

        stage_path = ROOT_DIR / "stages" / "original" / "stage_01.json"
        if not stage_path.exists():
            stage_path = ROOT_DIR / "stages" / "fixtures" / "basic.json"
        if stage_path.exists():
            stage = load_stage(stage_path)
            state = initial_state(stage)

            def _real_step(stg, st, act):
                act_name = getattr(act, "name", str(act)).upper()
                dir_val = getattr(Direction, act_name)
                return step(st, Action(direction=dir_val), stg)

            return stage, state, Direction, _real_step
    except Exception:
        pass

    # Bản đồ Stage 1 kinh điển của Bloxorz
    grid = [
        "###.......",
        "#S####....",
        "#########.",
        ".#########",
        ".....##G##",
        "......###.",
    ]
    stage = _FallbackStage(
        grid=grid,
        rows=len(grid),
        cols=len(grid[0]),
        start=(1, 1),
        goal=(4, 7),
    )
    state = _FallbackState(pos=(1, 1), pose=_FallbackPose.STANDING)

    def _fallback_step(stg: _FallbackStage, st: _FallbackState, act: _FallbackAction):
        r, c = st.pos
        p = st.pose
        if act == _FallbackAction.LEFT:
            if p == _FallbackPose.STANDING:
                nr, nc, np = r, c - 2, _FallbackPose.HORIZONTAL
            elif p == _FallbackPose.HORIZONTAL:
                nr, nc, np = r, c - 1, _FallbackPose.STANDING
            else:
                nr, nc, np = r, c - 1, _FallbackPose.VERTICAL
        elif act == _FallbackAction.RIGHT:
            if p == _FallbackPose.STANDING:
                nr, nc, np = r, c + 1, _FallbackPose.HORIZONTAL
            elif p == _FallbackPose.HORIZONTAL:
                nr, nc, np = r, c + 2, _FallbackPose.STANDING
            else:
                nr, nc, np = r, c + 1, _FallbackPose.VERTICAL
        elif act == _FallbackAction.UP:
            if p == _FallbackPose.STANDING:
                nr, nc, np = r - 2, c, _FallbackPose.VERTICAL
            elif p == _FallbackPose.VERTICAL:
                nr, nc, np = r - 1, c, _FallbackPose.STANDING
            else:
                nr, nc, np = r - 1, c, _FallbackPose.HORIZONTAL
        else:  # DOWN
            if p == _FallbackPose.STANDING:
                nr, nc, np = r + 1, c, _FallbackPose.VERTICAL
            elif p == _FallbackPose.VERTICAL:
                nr, nc, np = r + 2, c, _FallbackPose.STANDING
            else:
                nr, nc, np = r + 1, c, _FallbackPose.HORIZONTAL

        cells = [(nr, nc)]
        if np == _FallbackPose.HORIZONTAL:
            cells.append((nr, nc + 1))
        elif np == _FallbackPose.VERTICAL:
            cells.append((nr + 1, nc))

        for cr, cc in cells:
            if cr < 0 or cr >= stg.rows or cc < 0 or cc >= stg.cols:
                return None
            ch = stg.grid[cr][cc]
            if ch in (".", " "):
                return None
            if ch in ("F", "!") and np == _FallbackPose.STANDING:
                return None

        return _FallbackState(pos=(nr, nc), pose=np, bridges_open=st.bridges_open)

    return stage, state, _FallbackAction, _fallback_step


class DemoController(Entity):
    """Bộ điều khiển bàn phím trực tiếp cho bản Demo độc lập."""

    def __init__(self, view: SceneView) -> None:
        super().__init__()
        self.view = view
        self.stage, self.initial_state, self.ActionCls, self.step_fn = _load_stage_and_engine()
        self.state = self.initial_state
        self.history: List = []
        self.moves: int = 0

        self.view.load_stage(self.stage, self.state)

        # HUD hiển thị thông tin phong cách Minecraft
        self.hud_title = Text(
            text="BLOXORZ: VOXEL EDITION (URSINA)",
            position=(-0.85, 0.46),
            scale=1.15,
            color=color.rgb32(85, 255, 85),
        )
        self.hud_info = Text(
            text=self._info_str(),
            position=(-0.85, 0.41),
            scale=0.95,
            color=color.rgb32(255, 255, 85),
        )
        self.hud_help = Text(
            text="[WASD / Arrows] Roll   [U] Undo   [R] Restart   [1] Overworld   [2] Nether   [3] The End",
            position=(-0.85, -0.45),
            scale=0.85,
            color=color.rgb32(220, 220, 220),
        )

    def _info_str(self) -> str:
        biome = self.view.env.current_biome.upper()
        return f"MOVES: {self.moves}   |   BIOME: {biome}"

    def _refresh_hud(self) -> None:
        self.hud_info.text = self._info_str()

    def _map_key_to_action(self, key: str):
        mapping = {
            "w": "UP",
            "up arrow": "UP",
            "s": "DOWN",
            "down arrow": "DOWN",
            "a": "LEFT",
            "left arrow": "LEFT",
            "d": "RIGHT",
            "right arrow": "RIGHT",
        }
        act_name = mapping.get(key)
        if not act_name:
            return None
        return getattr(self.ActionCls, act_name, act_name)

    def input(self, key: str) -> None:
        if key in ("1", "2", "3"):
            from ursina import invoke
            invoke(self._refresh_hud, delay=0.05)
            return

        is_anim = self.view.is_animating() if callable(self.view.is_animating) else self.view.is_animating
        if is_anim:
            return

        if key == "r":
            self.state = self.initial_state
            self.history.clear()
            self.moves = 0
            self.view.load_stage(self.stage, self.state)
            self._refresh_hud()
            return

        if key == "u" and self.history:
            self.state = self.history.pop()
            self.moves = max(0, self.moves - 1)
            self.view.load_stage(self.stage, self.state)
            self._refresh_hud()
            return

        action = self._map_key_to_action(key)
        if action is None:
            return

        res = self.step_fn(self.stage, self.state, action)
        next_state = res[0] if isinstance(res, tuple) else res

        if next_state is None or getattr(next_state, "fell", False):
            self.view.on_fall(self.state, action)
            return

        old_state = self.state
        self.history.append(old_state)
        self.state = next_state
        self.moves += 1
        self._refresh_hud()

        self.view.on_move(old_state, action, next_state)

        # Kiểm tra chiến thắng (Đứng thẳng tại ô đích 'G')
        r, c = next_state.pos
        pose_val = getattr(next_state.pose, "value", next_state.pose)
        pose_name = getattr(next_state.pose, "name", "")
        is_standing = (pose_val == 0 or pose_name == "STANDING")
        if is_standing and self.stage.grid[r][c] == "G":
            from ursina import invoke
            invoke(self.view.on_win, next_state, delay=0.18)


def main() -> None:
    app = Ursina(title="Bloxorz: Voxel Edition - Ursina 3D", borderless=False)
    window.exit_button.visible = False
    window.fps_counter.enabled = True

    view = SceneView()
    set_biome("overworld")
    DemoController(view)

    app.run()


if __name__ == "__main__":
    main()