# bloxorz/gui/scene/demo.py
from __future__ import annotations
import json
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ursina import (  # noqa: E402
    Ursina,
    Entity,
    Text,
    Button,
    camera,
    color,
    window,
    invoke,
)
try:
    from bloxorz.gui.scene.view import SceneView  # noqa: E402
    from bloxorz.gui.scene.theme import set_biome  # noqa: E402
except ImportError:
    from view import SceneView  # noqa: E402
    from theme import set_biome  # noqa: E402


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
class _FallbackStage:
    id: str
    grid: List[str]
    rows: int
    cols: int
    start: Tuple[int, int]
    goal: Tuple[int, int]
    switch_at: Dict[Tuple[int, int], dict] = field(default_factory=dict)
    bridge_at: Dict[Tuple[int, int], str] = field(default_factory=dict)
    initial_bridges: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class _FallbackState:
    pos: Tuple[int, int]
    pose: Optional[_FallbackPose] = _FallbackPose.STANDING
    cube2: Optional[Tuple[int, int]] = None
    bridges_open: FrozenSet[str] = field(default_factory=frozenset)


def _scan_all_stage_files() -> List[Path]:
    stages_dir = ROOT_DIR / "stages"
    if not stages_dir.exists():
        stages_dir = REPO_ROOT / "stages"
    stage_files: List[Path] = []
    orig_dir = stages_dir / "original"
    if orig_dir.exists():
        orig_files = list(orig_dir.glob("stage_*.json"))
        orig_files.sort(key=lambda p: int(p.stem.split("_")[1]) if p.stem.split("_")[1].isdigit() else 999)
        stage_files.extend(orig_files)
    fix_dir = stages_dir / "fixtures"
    if fix_dir.exists():
        fix_files = sorted(fix_dir.glob("*.json"))
        stage_files.extend(fix_files)
    return stage_files


def _load_single_stage(path: Path) -> Tuple[_FallbackStage, _FallbackState]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_grid = data["grid"]
    rows = len(raw_grid)
    cols = max(len(r) for r in raw_grid)
    grid = [r.ljust(cols, ".") for r in raw_grid]

    start = (0, 0)
    goal = (0, 0)
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "S":
                start = (r, c)
            elif grid[r][c] == "G":
                goal = (r, c)

    bridge_at: Dict[Tuple[int, int], str] = {}
    init_open = set()
    for b in data.get("bridges", []):
        bid = b["id"]
        if b.get("initially_open", False):
            init_open.add(bid)
        for cell in b.get("cells", []):
            bridge_at[(cell[0], cell[1])] = bid

    switch_at: Dict[Tuple[int, int], dict] = {}
    for sw in data.get("switches", []):
        pos = (sw["pos"][0], sw["pos"][1])
        switch_at[pos] = sw

    stg = _FallbackStage(
        id=data.get("id", path.stem),
        grid=grid,
        rows=rows,
        cols=cols,
        start=start,
        goal=goal,
        switch_at=switch_at,
        bridge_at=bridge_at,
        initial_bridges=frozenset(init_open),
    )
    st = _FallbackState(
        pos=start,
        pose=_FallbackPose.STANDING,
        bridges_open=frozenset(init_open),
    )
    return stg, st


def _fallback_step(stg: _FallbackStage, st: _FallbackState, action) -> Optional[_FallbackState]:
    r, c = st.pos
    act_name = getattr(action, "name", str(action)).upper()
    pose = st.pose

    if pose == _FallbackPose.STANDING:
        if act_name == "LEFT":
            nr, nc, np = r, c - 2, _FallbackPose.HORIZONTAL
        elif act_name == "RIGHT":
            nr, nc, np = r, c + 1, _FallbackPose.HORIZONTAL
        elif act_name == "UP":
            nr, nc, np = r - 2, c, _FallbackPose.VERTICAL
        else:
            nr, nc, np = r + 1, c, _FallbackPose.VERTICAL
    elif pose == _FallbackPose.HORIZONTAL:
        if act_name == "LEFT":
            nr, nc, np = r, c - 1, _FallbackPose.STANDING
        elif act_name == "RIGHT":
            nr, nc, np = r, c + 2, _FallbackPose.STANDING
        elif act_name == "UP":
            nr, nc, np = r - 1, c, _FallbackPose.HORIZONTAL
        else:
            nr, nc, np = r + 1, c, _FallbackPose.HORIZONTAL
    else:  # VERTICAL
        if act_name == "LEFT":
            nr, nc, np = r, c - 1, _FallbackPose.VERTICAL
        elif act_name == "RIGHT":
            nr, nc, np = r, c + 1, _FallbackPose.VERTICAL
        elif act_name == "UP":
            nr, nc, np = r - 1, c, _FallbackPose.STANDING
        else:
            nr, nc, np = r + 2, c, _FallbackPose.STANDING

    cells = [(nr, nc)]
    if np == _FallbackPose.HORIZONTAL:
        cells.append((nr, nc + 1))
    elif np == _FallbackPose.VERTICAL:
        cells.append((nr + 1, nc))

    new_bridges = set(st.bridges_open)
    for cr, cc in cells:
        if not (0 <= cr < stg.rows and 0 <= cc < stg.cols):
            return None
        ch = stg.grid[cr][cc]
        if ch in (".", " "):
            return None
        if ch == "B":
            bid = stg.bridge_at.get((cr, cc))
            if bid and bid not in new_bridges:
                return None
        if ch in ("F", "!") and np == _FallbackPose.STANDING:
            return None

    for cr, cc in cells:
        sw = stg.switch_at.get((cr, cc))
        if sw:
            kind = sw.get("kind", "soft")
            if kind == "heavy" and np != _FallbackPose.STANDING:
                continue
            mode = sw.get("mode", "toggle")
            set_to = sw.get("set_to", "open")
            for bid in sw.get("bridges", []):
                if mode == "toggle":
                    if bid in new_bridges:
                        new_bridges.remove(bid)
                    else:
                        new_bridges.add(bid)
                elif set_to == "open":
                    new_bridges.add(bid)
                elif set_to == "close":
                    new_bridges.discard(bid)

    return _FallbackState(pos=(nr, nc), pose=np, bridges_open=frozenset(new_bridges))


def _is_busy(view: SceneView) -> bool:
    anim = getattr(view, "is_animating", False)
    return anim() if callable(anim) else bool(anim)


class DemoController(Entity):
    """Giao diện điều khiển và hiển thị phong cách Minecraft hoàn chỉnh (Thuần Python Ursina 3D)."""

    def __init__(self, view: SceneView) -> None:
        super().__init__()
        self.view = view
        self.stage_files = _scan_all_stage_files()
        self.stage_index: int = 0
        self.ActionCls = _FallbackAction
        self.step_fn = _fallback_step

        self._load_current_stage()
        self._build_minecraft_gui()

    def _load_current_stage(self) -> None:
        if self.stage_files:
            self.stage, self.initial_state = _load_single_stage(self.stage_files[self.stage_index])
        else:
            grid = ["###.......", "#S####....", "#########.", ".#########", ".....##G##", "......###."]
            self.stage = _FallbackStage(id="basic_fallback", grid=grid, rows=len(grid), cols=len(grid[0]), start=(1, 1), goal=(4, 7))
            self.initial_state = _FallbackState(pos=(1, 1), pose=_FallbackPose.STANDING)

        self.state = self.initial_state
        self.history: List = []
        self.moves: int = 0
        self.is_won: bool = False
        self.view.load_stage(self.stage, self.state)

    def _build_minecraft_gui(self) -> None:
        # Bảng thông tin góc trên bên trái
        Entity(parent=camera.ui, model="quad", scale=(0.54, 0.12), position=(-0.60, 0.42), color=color.rgba32(25, 25, 30, 220))
        Text(parent=camera.ui, text="BLOXORZ: VOXEL EDITION", position=(-0.84, 0.46), scale=1.05, color=color.rgb32(85, 255, 85))
        self.lbl_moves = Text(parent=camera.ui, text="", position=(-0.84, 0.40), scale=0.85, color=color.rgb32(255, 255, 85))

        # Thanh nút bấm phong cách Minecraft góc trên bên phải
        Entity(parent=camera.ui, model="quad", scale=(0.96, 0.10), position=(0.39, 0.43), color=color.rgba32(25, 25, 30, 220))
        Button(parent=camera.ui, text="Overworld", scale=(0.11, 0.055), position=(0.02, 0.43), color=color.rgb32(76, 133, 39), on_click=lambda: self.view.set_biome("overworld"))
        Button(parent=camera.ui, text="Nether", scale=(0.09, 0.055), position=(0.13, 0.43), color=color.rgb32(150, 34, 27), on_click=lambda: self.view.set_biome("nether"))
        Button(parent=camera.ui, text="The End", scale=(0.09, 0.055), position=(0.23, 0.43), color=color.rgb32(103, 33, 133), on_click=lambda: self.view.set_biome("end"))
        Button(parent=camera.ui, text="< Prev (P)", scale=(0.11, 0.055), position=(0.34, 0.43), color=color.rgb32(65, 75, 95), on_click=self.prev_stage)
        Button(parent=camera.ui, text="Next (N) >", scale=(0.11, 0.055), position=(0.46, 0.43), color=color.rgb32(65, 75, 95), on_click=self.next_stage)
        Button(parent=camera.ui, text="Reset Cam (C)", scale=(0.14, 0.055), position=(0.59, 0.43), color=color.rgb32(40, 110, 140), on_click=self.view.cam_ctrl.reset_view)
        Button(parent=camera.ui, text="Undo (U)", scale=(0.10, 0.055), position=(0.72, 0.43), color=color.rgb32(85, 85, 95), on_click=self.undo)
        Button(parent=camera.ui, text="Reset (R)", scale=(0.10, 0.055), position=(0.83, 0.43), color=color.rgb32(85, 85, 95), on_click=self.restart)

        # Hướng dẫn thao tác góc dưới màn hình
        Entity(parent=camera.ui, model="quad", scale=(1.10, 0.08), position=(-0.33, -0.44), color=color.rgba32(25, 25, 30, 220))
        Text(parent=camera.ui, text="[WASD / MŨI TÊN] LẬT KHỐI   |   [P / N] ĐỔI MÀN   |   [C] GÓC VÀNG   |   [T] TỪ TRÊN CAO   |   [Q / E] XOAY 45°", position=(-0.86, -0.42), scale=0.72, color=color.rgb32(85, 255, 255))
        Text(parent=camera.ui, text="[CHUỘT TRÁI/PHẢI + KÉO] XOAY 3D MƯỢT   |   [CON LĂN] ZOOM XA/GẦN   |   [U] HOÀN TÁC   |   [R] CHƠI LẠI", position=(-0.86, -0.45), scale=0.72, color=color.rgb32(200, 200, 200))

        # Banner ăn mừng chiến thắng
        self.win_banner = Entity(parent=camera.ui, model="quad", scale=(0.65, 0.18), position=(0, 0), color=color.rgba32(10, 10, 15, 240), enabled=False)
        self.win_title = Text(parent=self.win_banner, text="STAGE CLEAR!", origin=(0, 0), position=(0, 0.22), scale=1.6, color=color.rgb32(85, 255, 85))
        self.win_sub = Text(parent=self.win_banner, text="NHẤN [N] ĐỂ SANG MÀN TIẾP THEO!", origin=(0, 0), position=(0, -0.20), scale=0.85, color=color.rgb32(255, 255, 85))

        self._update_hud()

    def _update_hud(self) -> None:
        total = max(1, len(self.stage_files))
        idx = self.stage_index + 1
        self.lbl_moves.text = f"STAGE: {self.stage.id} ({idx}/{total})   MOVES: {self.moves}"

    def next_stage(self) -> None:
        if _is_busy(self.view):
            return
        if self.stage_files:
            self.stage_index = (self.stage_index + 1) % len(self.stage_files)
            self.win_banner.enabled = False
            self._load_current_stage()
            self._update_hud()

    def prev_stage(self) -> None:
        if _is_busy(self.view):
            return
        if self.stage_files:
            self.stage_index = (self.stage_index - 1) % len(self.stage_files)
            self.win_banner.enabled = False
            self._load_current_stage()
            self._update_hud()

    def restart(self) -> None:
        if _is_busy(self.view):
            return
        self.state = self.initial_state
        self.history.clear()
        self.moves = 0
        self.is_won = False
        self.win_banner.enabled = False
        self.view.load_stage(self.stage, self.state)
        self._update_hud()

    def undo(self) -> None:
        if _is_busy(self.view) or not self.history or self.is_won:
            return
        self.state = self.history.pop()
        self.moves = max(0, self.moves - 1)
        self.view.load_stage(self.stage, self.state)
        self._update_hud()

    def _map_action(self, key: str):
        mapping = {
            "w": "UP", "up arrow": "UP",
            "s": "DOWN", "down arrow": "DOWN",
            "a": "LEFT", "left arrow": "LEFT",
            "d": "RIGHT", "right arrow": "RIGHT",
        }
        act_name = mapping.get(key)
        return getattr(self.ActionCls, act_name, act_name) if act_name else None

    def input(self, key: str) -> None:
        if key in ("1", "2", "3"):
            return
        if key == "r":
            self.restart()
            return
        if key == "u":
            self.undo()
            return
        if key == "n":
            self.next_stage()
            return
        if key == "p":
            self.prev_stage()
            return

        if _is_busy(self.view) or self.is_won:
            return

        action = self._map_action(key)
        if action is None:
            return

        res = self.step_fn(self.stage, self.state, action)
        next_state = res[0] if isinstance(res, tuple) else res

        # Xử lý rơi vực
        if next_state is None or getattr(next_state, "fell", False):
            self.view.on_fall(self.state, action)
            invoke(self.restart, delay=0.75)
            return

        old_state = self.state
        self.history.append(old_state)
        self.state = next_state
        self.moves += 1
        self._update_hud()

        self.view.on_move(old_state, action, next_state)

        # Kiểm tra điều kiện chiến thắng
        r, c = next_state.pos
        pose_val = getattr(next_state.pose, "value", next_state.pose)
        pose_name = getattr(next_state.pose, "name", "")
        if (pose_val == 0 or pose_name == "STANDING") and (self.stage.grid[r][c] == "G" or (r, c) == self.stage.goal):
            self.is_won = True
            invoke(lambda: self.view.on_win(next_state), delay=0.18)
            invoke(lambda: setattr(self.win_banner, "enabled", True), delay=0.55)


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
