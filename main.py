# Phụ trách: VT4 - Task 4.2 / 4.5
"""
Điểm khởi chạy ứng dụng chính Bloxorz Solver.

    python main.py                       # cửa sổ Ursina, bắt đầu từ màn gốc đầu tiên
    python main.py --stage stage_05      # bắt đầu từ màn có id stage_05
    python main.py --stage stages/fixtures/split.json
    python main.py --stages-dir stages/fixtures --text   # chơi trong terminal, không cần Ursina
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bloxorz.gui.controller import GameController
from bloxorz.loader import load_stage, load_stages
from bloxorz.stage import Stage

DEFAULT_STAGES_DIR = Path(__file__).resolve().parent / "stages" / "original"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Bloxorz Solver: chơi tay và giải bằng BFS/DFS/UCS/A*.")
    ap.add_argument("--stages-dir", type=Path, default=DEFAULT_STAGES_DIR, help="thư mục chứa file màn *.json")
    ap.add_argument("--stage", help="id màn (vd. stage_05) trong --stages-dir, hoặc đường dẫn tới 1 file .json")
    ap.add_argument("--text", action="store_true", help="chơi trong terminal thay vì mở cửa sổ 3D")
    ap.add_argument("--opengl", action="store_true", help="chạy trực tiếp bằng Fallback Native OpenGL 3.3 Core (v2)")
    ap.add_argument("--ursina", action="store_true", help="dùng giao diện Ursina cũ")
    return ap.parse_args(argv)


def select_stages(stages_dir: Path, stage: str | None) -> tuple[list[Stage], int]:
    """Trả về (danh sách màn, vị trí màn bắt đầu). Một file .json riêng lẻ thì chơi đúng màn đó."""
    if stage and stage.endswith(".json"):
        return [load_stage(stage)], 0
    stages = load_stages(stages_dir)
    if not stages:
        raise SystemExit(f"Không có file màn *.json nào trong {stages_dir}")
    if stage is None:
        return stages, 0
    for i, st in enumerate(stages):
        if st.id == stage:
            return stages, i
    raise SystemExit(f"Không tìm thấy màn {stage!r} trong {stages_dir}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    stages, index = select_stages(args.stages_dir, args.stage)
    controller = GameController(stages, index)
    if args.text:
        from bloxorz.gui.fake_scene import run_text
        run_text(controller)
        return
    from bloxorz.gui.app import run
    if args.opengl:
        engine = "opengl"
    elif args.ursina:
        engine = "ursina"
    else:
        engine = "webgl"
    run(controller, engine=engine)


if __name__ == "__main__":
    sys.exit(main())
