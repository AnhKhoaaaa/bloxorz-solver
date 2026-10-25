# Phụ trách: VT4 - Task 4.1
"""
Đọc và kiểm tra tính hợp lệ của file cấu hình màn chơi JSON.

Định dạng file màn (1 file = 1 màn, mã hóa UTF-8):

    {
      "id": "stage_01",
      "group": "G1",
      "source": "Bloxorz gốc, level 1",
      "note": "Ví dụ đủ 3 loại công tắc",
      "grid": [
        "S###BB###G"
      ],
      "bridges": [
        {"id": "b1", "cells": [[0, 4], [0, 5]], "initially_open": false}
      ],
      "switches": [
        {"id": "s1", "kind": "soft", "pos": [0, 1], "mode": "toggle", "bridges": ["b1"]},
        {"id": "s2", "kind": "heavy", "pos": [0, 3], "mode": "permanent",
         "set_to": "close", "bridges": ["b1"]},
        {"id": "s3", "kind": "split", "pos": [0, 7], "targets": [[0, 6], [0, 8]]}
      ]
    }

Ký tự trong grid (mỗi chuỗi là 1 hàng, các hàng được phép dài ngắn khác nhau):
    '.' khoảng trống (rơi)        '#' sàn thường
    'S' ô xuất phát (đúng 1 ô)    'G' lỗ đích (đúng 1 ô)
    'F' ô dễ vỡ (không được đứng) 'B' ô cầu (trạng thái do "bridges" quyết định)

Tọa độ luôn là [hàng, cột], (0, 0) ở góc trên-trái, giống Pos trong model.py.
"bridges" và "switches" có thể bỏ qua (mặc định rỗng). Khóa lạ bị từ chối để bắt lỗi gõ sai.
"source" (nguồn gốc màn) và "note" (ghi chú) là metadata tùy chọn, nếu có phải là chuỗi.

Ràng buộc:
- Mỗi ô 'B' thuộc đúng 1 cầu; mọi ô của cầu phải là 'B'.
- Công tắc đặt trên ô '#', mỗi ô tối đa 1 công tắc.
- soft/heavy: "mode" bắt buộc ("toggle" | "permanent"); "set_to" ("open" | "close",
  mặc định "open") chỉ dùng khi mode="permanent"; "bridges" là danh sách id cầu đã khai báo.
  Công tắc làm nhiều việc khác nhau cùng lúc thì thay mode/set_to/bridges bằng
  "actions": [["b1", "open"], ["b2", "close"]] (hành động: "toggle" | "open" | "close").
- split: chỉ có "targets" gồm 2 ô khác nhau, không phải ô trống '.'.

Khi tạo Stage, ô 'S' được chuẩn hóa thành '#', start/goal lấy từ vị trí 'S'/'G'.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from bloxorz.model import Pos
from bloxorz.stage import Bridge, Stage, Switch

GRID_CHARS = frozenset(".#SGFB")
GROUPS = ("G1", "G2", "G3", "G4", "G5")
SWITCH_KINDS = ("soft", "heavy", "split")
SWITCH_MODES = ("toggle", "permanent")
SET_TO_VALUES = ("open", "close")
BRIDGE_ACTIONS = ("toggle", "open", "close")

_STAGE_KEYS = {"id", "group", "grid", "bridges", "switches", "source", "note"}
_BRIDGE_KEYS = {"id", "cells", "initially_open"}
_SWITCH_KEYS = {
    "soft": {"id", "kind", "pos", "mode", "set_to", "bridges", "actions"},
    "heavy": {"id", "kind", "pos", "mode", "set_to", "bridges", "actions"},
    "split": {"id", "kind", "pos", "targets"},
}


class StageFormatError(ValueError):
    """Dữ liệu màn chơi sai định dạng. `errors` chứa toàn bộ lỗi tìm được."""

    def __init__(self, source: str, errors: list[str]):
        self.source = source
        self.errors = list(errors)
        lines = "\n".join(f"  - {e}" for e in self.errors)
        super().__init__(f"{source}: invalid stage ({len(self.errors)} error(s))\n{lines}")


def _is_int(v: Any) -> bool:
    # bool là lớp con của int trong Python nên phải loại riêng
    return isinstance(v, int) and not isinstance(v, bool)


def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and v != ""


class _Validator:
    """Gom lỗi theo đường dẫn JSON (ví dụ: switches[0].pos) thay vì dừng ở lỗi đầu tiên."""

    def __init__(self, data: Any):
        self.data = data
        self.errors: list[str] = []
        self.grid: list[str] = []

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def cell(self, p: Pos) -> str:
        r, c = p
        if 0 <= r < len(self.grid) and 0 <= c < len(self.grid[r]):
            return self.grid[r][c]
        return "."

    def in_bounds(self, p: Pos) -> bool:
        r, c = p
        return 0 <= r < len(self.grid) and 0 <= c < len(self.grid[r])

    def check_keys(self, where: str, obj: Mapping, allowed: set[str], required: set[str]) -> None:
        for k in sorted(required - obj.keys()):
            self.err(where, f"missing key '{k}'")
        for k in sorted(obj.keys() - allowed):
            self.err(where, f"unknown key '{k}'")

    def pos(self, where: str, v: Any) -> Pos | None:
        if not (isinstance(v, list) and len(v) == 2 and all(_is_int(x) for x in v)):
            self.err(where, f"expected [row, col] of 2 integers, got {v!r}")
            return None
        p = (v[0], v[1])
        if not self.in_bounds(p):
            self.err(where, f"{list(p)} is outside the grid")
            return None
        return p

    def run(self) -> None:
        d = self.data
        if not isinstance(d, dict):
            self.err("<root>", f"expected a JSON object, got {type(d).__name__}")
            return
        self.check_keys("<root>", d, _STAGE_KEYS, {"id", "group", "grid"})

        if "id" in d and not _is_nonempty_str(d["id"]):
            self.err("id", "must be a non-empty string")
        if "group" in d and d["group"] not in GROUPS:
            self.err("group", f"must be one of {', '.join(GROUPS)}, got {d['group']!r}")
        for key in ("source", "note"):
            if key in d and not isinstance(d[key], str):
                self.err(key, "must be a string")

        self.check_grid(d.get("grid"))
        # Không kiểm tra cầu/công tắc trên lưới hỏng để tránh lỗi dây chuyền khó đọc
        if self.errors and not self.grid:
            return
        bridge_ids = self.check_bridges(d.get("bridges", []))
        self.check_switches(d.get("switches", []), bridge_ids)

    def check_grid(self, grid: Any) -> None:
        if grid is None:
            return
        if not (isinstance(grid, list) and grid and all(isinstance(r, str) for r in grid)):
            self.err("grid", "must be a non-empty list of strings")
            return
        bad = False
        for r, row in enumerate(grid):
            for c, ch in enumerate(row):
                if ch not in GRID_CHARS:
                    self.err(f"grid[{r}][{c}]", f"unknown tile {ch!r} (allowed: {''.join(sorted(GRID_CHARS))})")
                    bad = True
        if bad:
            return
        self.grid = grid
        for ch, name in (("S", "start"), ("G", "goal")):
            n = sum(row.count(ch) for row in grid)
            if n != 1:
                self.err("grid", f"must contain exactly one '{ch}' ({name}), found {n}")

    def check_bridges(self, bridges: Any) -> set[str]:
        ids: set[str] = set()
        owner: dict[Pos, str] = {}
        if not isinstance(bridges, list):
            self.err("bridges", "must be a list")
            return ids
        for i, b in enumerate(bridges):
            w = f"bridges[{i}]"
            if not isinstance(b, dict):
                self.err(w, "must be an object")
                continue
            self.check_keys(w, b, _BRIDGE_KEYS, {"id", "cells"})
            bid = b.get("id")
            if not _is_nonempty_str(bid):
                self.err(f"{w}.id", "must be a non-empty string")
            elif bid in ids:
                self.err(f"{w}.id", f"duplicate bridge id {bid!r}")
            else:
                ids.add(bid)
            if "initially_open" in b and not isinstance(b["initially_open"], bool):
                self.err(f"{w}.initially_open", "must be true or false")
            cells = b.get("cells")
            if not (isinstance(cells, list) and cells):
                if "cells" in b:
                    self.err(f"{w}.cells", "must be a non-empty list of [row, col]")
                continue
            for j, v in enumerate(cells):
                p = self.pos(f"{w}.cells[{j}]", v)
                if p is None:
                    continue
                if self.cell(p) != "B":
                    self.err(f"{w}.cells[{j}]", f"{list(p)} is {self.cell(p)!r}, bridge cells must be 'B'")
                elif p in owner:
                    self.err(f"{w}.cells[{j}]", f"{list(p)} already belongs to bridge {owner[p]!r}")
                else:
                    owner[p] = bid if isinstance(bid, str) else "?"
        for r, row in enumerate(self.grid):
            for c, ch in enumerate(row):
                if ch == "B" and (r, c) not in owner:
                    self.err(f"grid[{r}][{c}]", "'B' tile is not part of any bridge")
        return ids

    def check_switches(self, switches: Any, bridge_ids: set[str]) -> None:
        if not isinstance(switches, list):
            self.err("switches", "must be a list")
            return
        ids: set[str] = set()
        at: dict[Pos, str] = {}
        for i, s in enumerate(switches):
            w = f"switches[{i}]"
            if not isinstance(s, dict):
                self.err(w, "must be an object")
                continue
            kind = s.get("kind")
            if kind not in SWITCH_KINDS:
                self.err(f"{w}.kind", f"must be one of {', '.join(SWITCH_KINDS)}, got {kind!r}")
                continue
            if kind == "split":
                required = {"id", "kind", "pos", "targets"}
            elif "actions" in s:
                required = {"id", "kind", "pos", "actions"}
            else:
                required = {"id", "kind", "pos", "mode", "bridges"}
            self.check_keys(w, s, _SWITCH_KEYS[kind], required)

            sid = s.get("id")
            if not _is_nonempty_str(sid):
                self.err(f"{w}.id", "must be a non-empty string")
            elif sid in ids:
                self.err(f"{w}.id", f"duplicate switch id {sid!r}")
            else:
                ids.add(sid)

            if "pos" in s:
                p = self.pos(f"{w}.pos", s["pos"])
                if p is not None:
                    if self.cell(p) != "#":
                        self.err(f"{w}.pos", f"{list(p)} is {self.cell(p)!r}, switches must sit on '#'")
                    elif p in at:
                        self.err(f"{w}.pos", f"{list(p)} already has switch {at[p]!r}")
                    else:
                        at[p] = sid if isinstance(sid, str) else "?"

            if kind == "split":
                self.check_targets(f"{w}.targets", s.get("targets"))
            else:
                self.check_bridge_switch(w, s, bridge_ids)

    def check_bridge_switch(self, w: str, s: Mapping, bridge_ids: set[str]) -> None:
        if "actions" in s:
            self.check_actions(w, s, bridge_ids)
            return
        mode = s.get("mode")
        if "mode" in s and mode not in SWITCH_MODES:
            self.err(f"{w}.mode", f"must be one of {', '.join(SWITCH_MODES)}, got {mode!r}")
        if "set_to" in s:
            if mode != "permanent":
                self.err(f"{w}.set_to", "only allowed when mode is 'permanent'")
            elif s["set_to"] not in SET_TO_VALUES:
                self.err(f"{w}.set_to", f"must be one of {', '.join(SET_TO_VALUES)}, got {s['set_to']!r}")
        if "bridges" not in s:
            return
        refs = s["bridges"]
        if not (isinstance(refs, list) and refs and all(isinstance(x, str) for x in refs)):
            self.err(f"{w}.bridges", "must be a non-empty list of bridge ids")
            return
        if len(set(refs)) != len(refs):
            self.err(f"{w}.bridges", "contains duplicate bridge ids")
        for ref in refs:
            if ref not in bridge_ids:
                self.err(f"{w}.bridges", f"unknown bridge id {ref!r}")

    def check_actions(self, w: str, s: Mapping, bridge_ids: set[str]) -> None:
        for k in ("mode", "set_to", "bridges"):
            if k in s:
                self.err(f"{w}.{k}", "not allowed together with 'actions'")
        actions = s["actions"]
        if not (isinstance(actions, list) and actions):
            self.err(f"{w}.actions", "must be a non-empty list of [bridge id, action]")
            return
        seen: set[str] = set()
        for j, a in enumerate(actions):
            wj = f"{w}.actions[{j}]"
            if not (isinstance(a, list) and len(a) == 2 and isinstance(a[0], str)):
                self.err(wj, f"expected [bridge id, action], got {a!r}")
                continue
            ref, action = a
            if ref not in bridge_ids:
                self.err(wj, f"unknown bridge id {ref!r}")
            elif ref in seen:
                self.err(wj, f"bridge {ref!r} appears more than once")
            seen.add(ref)
            if action not in BRIDGE_ACTIONS:
                self.err(wj, f"action must be one of {', '.join(BRIDGE_ACTIONS)}, got {action!r}")

    def check_targets(self, w: str, targets: Any) -> None:
        if targets is None:
            return
        if not (isinstance(targets, list) and len(targets) == 2):
            self.err(w, "must be a list of exactly 2 [row, col]")
            return
        ps = [self.pos(f"{w}[{j}]", v) for j, v in enumerate(targets)]
        for j, p in enumerate(ps):
            if p is not None and self.cell(p) == ".":
                self.err(f"{w}[{j}]", f"{list(p)} is empty space '.'")
        if ps[0] is not None and ps[0] == ps[1]:
            self.err(w, "the two targets must be different cells")


def validate_stage_data(data: Any) -> list[str]:
    """Trả về danh sách lỗi của dữ liệu màn (đã parse từ JSON). Danh sách rỗng = hợp lệ."""
    v = _Validator(data)
    v.run()
    return v.errors


def _find(grid: list[str], ch: str) -> Pos:
    for r, row in enumerate(grid):
        c = row.find(ch)
        if c != -1:
            return (r, c)
    raise AssertionError(f"{ch!r} not in grid")  # đã được validator đảm bảo


def parse_stage(data: Any, source: str = "<data>") -> Stage:
    """Kiểm tra rồi chuyển dữ liệu JSON (dict) thành Stage. Ném StageFormatError nếu sai."""
    errors = validate_stage_data(data)
    if errors:
        raise StageFormatError(source, errors)

    grid: list[str] = data["grid"]
    start = _find(grid, "S")
    goal = _find(grid, "G")
    bridges = tuple(
        Bridge(
            id=b["id"],
            cells=tuple((r, c) for r, c in b["cells"]),
            initially_open=b.get("initially_open", False),
        )
        for b in data.get("bridges", [])
    )
    switches = []
    for s in data.get("switches", []):
        pos = (s["pos"][0], s["pos"][1])
        if s["kind"] == "split":
            (r1, c1), (r2, c2) = s["targets"]
            switches.append(Switch(id=s["id"], kind="split", pos=pos, targets=((r1, c1), (r2, c2))))
        elif "actions" in s:
            switches.append(Switch(id=s["id"], kind=s["kind"], pos=pos, actions=tuple((b, a) for b, a in s["actions"])))
        else:
            switches.append(Switch(
                id=s["id"],
                kind=s["kind"],
                pos=pos,
                mode=s["mode"],
                set_to=s.get("set_to", "open"),
                bridges=tuple(s["bridges"]),
            ))
    return Stage(
        id=data["id"],
        group=data["group"],
        grid=tuple(row.replace("S", "#") for row in grid),
        start=start,
        goal=goal,
        bridges=bridges,
        switches=tuple(switches),
    )


def load_stage(path: str | Path) -> Stage:
    """Đọc 1 file màn JSON. Ném StageFormatError nếu JSON hỏng hoặc sai định dạng."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise StageFormatError(str(path), [f"line {e.lineno} col {e.colno}: invalid JSON ({e.msg})"]) from e
    return parse_stage(data, source=str(path))


def load_stages(directory: str | Path) -> list[Stage]:
    """
    Đọc mọi file *.json trong thư mục, sắp theo tên file. Ném lỗi nếu trùng id màn.
    Ném FileNotFoundError nếu thư mục không tồn tại (tránh âm thầm trả [] khi gõ sai đường dẫn).
    """
    d = Path(directory)
    if not d.is_dir():
        raise FileNotFoundError(f"stage directory not found: {directory}")
    stages = [load_stage(p) for p in sorted(d.glob("*.json"))]
    seen: dict[str, int] = {}
    for st in stages:
        seen[st.id] = seen.get(st.id, 0) + 1
    dup = sorted(k for k, n in seen.items() if n > 1)
    if dup:
        raise StageFormatError(str(directory), [f"duplicate stage id {k!r}" for k in dup])
    return stages


def stage_to_dict(stage: Stage) -> dict[str, Any]:
    """Chuyển Stage ngược lại thành dict đúng định dạng file (dùng cho tool chuyển đổi, test)."""
    grid = list(stage.grid)
    r, c = stage.start
    grid[r] = grid[r][:c] + "S" + grid[r][c + 1:]
    data: dict[str, Any] = {"id": stage.id, "group": stage.group, "grid": grid}
    if stage.bridges:
        data["bridges"] = [
            {"id": b.id, "cells": [list(p) for p in b.cells], "initially_open": b.initially_open}
            for b in stage.bridges
        ]
    if stage.switches:
        out = []
        for s in stage.switches:
            d: dict[str, Any] = {"id": s.id, "kind": s.kind, "pos": list(s.pos)}
            if s.kind == "split":
                d["targets"] = [list(p) for p in s.targets]
            elif s.mode is None:
                d["actions"] = [[b, a] for b, a in s.actions]
            else:
                d["mode"] = s.mode
                if s.mode == "permanent":
                    d["set_to"] = s.set_to
                d["bridges"] = list(s.bridges)
            out.append(d)
        data["switches"] = out
    return data
