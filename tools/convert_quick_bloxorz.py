# Phụ trách: VT4 - Task 4.7
"""
Script chuyển đổi dữ liệu 33 màn gốc sang JSON của nhóm.

Nguồn: Quick Bloxorz của Jeffrey Gordon (CC BY), https://github.com/jgordon510/quick_bloxorz
Mỗi màn là 1 file Tiled `maps/bloxorzN.json`. Mỗi object group là 1 loại ô, tọa độ tính
bằng pixel (50px = 1 ô, có thể âm):
    normal -> '#'    weak -> 'F'    goal -> 'G'    bridge -> 'B'
    button -> công tắc soft (hard=false) / heavy (hard=true) trên ô '#'
              type: toggle -> toggle, on -> permanent open, off -> permanent close
    splitter -> công tắc split trên ô '#', split1/split2 là id object của 2 ô đích
    border -> vùng chết quanh màn, tương đương '.' nên bỏ qua
Khối luôn xuất phát đứng tại ô (0, 0) của Tiled.

Cách dùng:
    git clone https://github.com/jgordon510/quick_bloxorz /tmp/quick_bloxorz
    python tools/convert_quick_bloxorz.py /tmp/quick_bloxorz/maps
    python tools/convert_quick_bloxorz.py /tmp/quick_bloxorz/maps --out stages/original --levels 1 2 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Cho phép chạy trực tiếp `python tools/convert_quick_bloxorz.py` từ thư mục gốc repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bloxorz.loader import parse_stage  # noqa: E402

TILE = 50
TILE_CHARS = {"normal": "#", "weak": "F", "goal": "G", "bridge": "B", "button": "#", "splitter": "#"}
BUTTON_MODES = {"toggle": ("toggle", None), "on": ("permanent", "open"), "off": ("permanent", "close")}


class UnsupportedStage(ValueError):
    """Màn dùng cơ chế mà định dạng JSON/Stage hiện tại chưa biểu diễn được."""


def group_of(data: dict[str, Any]) -> str:
    """Xếp nhóm theo cơ chế khó nhất có trong màn."""
    if data.get("switches") and any(s["kind"] == "split" for s in data["switches"]):
        return "G4"
    if data.get("switches") or data.get("bridges"):
        return "G3"
    if any("F" in row for row in data["grid"]):
        return "G2"
    return "G1"


def convert(tiled: dict[str, Any], level: int) -> dict[str, Any]:
    """Chuyển 1 map Tiled của Quick Bloxorz thành dict đúng định dạng file màn (chưa kiểm tra)."""
    cells: dict[tuple[int, int], str] = {}
    by_id: dict[int, tuple[int, int]] = {}
    bridge_cells: dict[str, list[tuple[int, int]]] = {}
    bridge_open: dict[str, bool] = {}
    buttons: dict[tuple[int, int], list[dict[str, Any]]] = {}
    splitters: list[tuple[tuple[int, int], dict[str, Any]]] = []

    for layer in tiled["layers"]:
        name = layer.get("name")
        if layer.get("type") != "objectgroup" or name == "border":
            continue
        if name not in TILE_CHARS:
            raise UnsupportedStage(f"level {level}: unknown layer {name!r}")
        for obj in layer["objects"]:
            # Tiled dùng (x, y) = (cột, hàng); bỏ qua width/height vì game cũng chỉ vẽ 1 ô
            p = (obj["y"] // TILE, obj["x"] // TILE)
            by_id[obj["id"]] = p
            ch = TILE_CHARS[name]
            if cells.setdefault(p, ch) != ch:
                raise UnsupportedStage(f"level {level}: cell {p} is both {cells[p]!r} and {ch!r}")
            props = obj.get("properties") or {}
            if name == "bridge":
                bridge_cells.setdefault(props["id"], []).append(p)
                # Game coi cầu là mở nếu bất kỳ ô nào của nó có startActivated
                bridge_open[props["id"]] = bridge_open.get(props["id"], False) or bool(props.get("startActivated"))
            elif name == "button":
                buttons.setdefault(p, [])
                if props not in buttons[p]:
                    buttons[p].append(props)
            elif name == "splitter":
                splitters.append((p, props))

    if (0, 0) not in cells:
        raise UnsupportedStage(f"level {level}: no tile at start position (0, 0)")

    # Dời tọa độ để ô trên-trái của màn là (0, 0)
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    rows = max(r for r, _ in cells) - r0 + 1
    cols = max(c for _, c in cells) - c0 + 1

    def shift(p: tuple[int, int]) -> list[int]:
        return [p[0] - r0, p[1] - c0]

    grid = [["."] * cols for _ in range(rows)]
    for p, ch in cells.items():
        r, c = shift(p)
        grid[r][c] = ch
    sr, sc = shift((0, 0))
    grid[sr][sc] = "S"

    switches: list[tuple[tuple[int, int], dict[str, Any]]] = []
    for p, variants in buttons.items():
        if len(variants) > 1:
            desc = "; ".join(f"{v['type']} {v['activating']}" for v in variants)
            raise UnsupportedStage(f"level {level}: switch at {shift(p)} has several actions ({desc})")
        v = variants[0]
        mode, set_to = BUTTON_MODES[v["type"]]
        sw: dict[str, Any] = {"kind": "heavy" if v.get("hard") else "soft", "pos": shift(p), "mode": mode}
        if set_to:
            sw["set_to"] = set_to
        sw["bridges"] = v["activating"].split(",")
        switches.append((p, sw))
    for p, props in splitters:
        targets = [shift(by_id[props["split1"]]), shift(by_id[props["split2"]])]
        switches.append((p, {"kind": "split", "pos": shift(p), "targets": targets}))

    data: dict[str, Any] = {
        "id": f"stage_{level:02d}",
        "group": "",
        "grid": ["".join(row) for row in grid],
    }
    if bridge_cells:
        data["bridges"] = [
            {"id": bid, "cells": sorted(shift(p) for p in ps), "initially_open": bridge_open[bid]}
            for bid, ps in sorted(bridge_cells.items())
        ]
    if switches:
        switches.sort(key=lambda item: item[0])
        data["switches"] = [{"id": f"s{i}", **sw} for i, (_, sw) in enumerate(switches, 1)]
    data["group"] = group_of(data)
    return data


def format_stage(data: dict[str, Any]) -> str:
    """JSON dễ đọc: mỗi hàng grid, mỗi cầu, mỗi công tắc nằm trên 1 dòng."""
    def one(v: Any) -> str:
        return json.dumps(v, ensure_ascii=False, separators=(", ", ": "))

    lines = ["{", f'  "id": {one(data["id"])},', f'  "group": {one(data["group"])},']
    sections = [k for k in ("grid", "bridges", "switches") if k in data]
    for i, key in enumerate(sections):
        items = ",\n".join(f"    {one(x)}" for x in data[key])
        comma = "," if i < len(sections) - 1 else ""
        lines.append(f'  "{key}": [\n{items}\n  ]{comma}')
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert Quick Bloxorz Tiled maps to stage JSON.")
    ap.add_argument("maps_dir", type=Path, help="thư mục maps/ của repo quick_bloxorz")
    ap.add_argument("--out", type=Path, default=Path("stages/original"), help="thư mục ghi file JSON")
    ap.add_argument("--levels", type=int, nargs="+", default=list(range(1, 34)), help="các màn cần đổi (mặc định 1..33)")
    args = ap.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for level in args.levels:
        src = args.maps_dir / f"bloxorz{level}.json"
        try:
            data = convert(json.loads(src.read_text(encoding="utf-8")), level)
            parse_stage(data, source=str(src))  # chặn ghi file nếu sai định dạng
        except (UnsupportedStage, ValueError, OSError) as e:
            failed += 1
            print(f"SKIP {src.name}: {e}", file=sys.stderr)
            continue
        dst = args.out / f"{data['id']}.json"
        dst.write_text(format_stage(data), encoding="utf-8")
        print(f"OK   {src.name} -> {dst} ({data['group']})")
    print(f"{len(args.levels) - failed}/{len(args.levels)} stages converted")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
