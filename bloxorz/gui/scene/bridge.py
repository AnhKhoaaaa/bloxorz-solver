"""
Cầu nối 2 chiều (Bidirectional IPC Bridge) giữa Python Core/Controller và Three.js Voxel Renderer.
Đảm nhận JSON Serialization cho Scene Protocol và quản lý cửa sổ Desktop Native (`pywebview` / GTK-WebKit2).
"""
from __future__ import annotations

import json
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def stage_to_dict(stg: Any) -> Dict[str, Any]:
    """Chuyển đổi Stage của bloxorz sang dict chuẩn JSON cho Three.js."""
    if hasattr(stg, "to_dict") and callable(stg.to_dict):
        return stg.to_dict()

    grid_rows = list(stg.grid)
    start_pos = getattr(stg, "start", (1, 1))
    sr, sc = start_pos
    if 0 <= sr < len(grid_rows) and 0 <= sc < len(grid_rows[sr]):
        row_chars = list(grid_rows[sr])
        if row_chars[sc] == "#":
            row_chars[sc] = "S"
            grid_rows[sr] = "".join(row_chars)

    switches_list = []
    for sw in getattr(stg, "switches", ()):
        switches_list.append({
            "id": getattr(sw, "id", ""),
            "pos": [sw.pos[0], sw.pos[1]],
            "kind": getattr(sw, "kind", "soft"),
            "bridges": list(getattr(sw, "bridges", ())),
            "mode": getattr(sw, "mode", "toggle") or "toggle",
        })

    bridges_dict = {}
    bridge_at = {}
    for br in getattr(stg, "bridges", ()):
        bridges_dict[br.id] = {
            "id": br.id,
            "cells": [[r, c] for r, c in br.cells],
            "initially_open": bool(getattr(br, "initially_open", False)),
        }
        for r, c in br.cells:
            bridge_at[f"{r},{c}"] = br.id

    goal_pos = getattr(stg, "goal", (0, 0))
    stg_id = getattr(stg, "id", "stage_01")
    raw_num = stg_id.replace("stage_", "").lstrip("0")
    stg_name = f"STAGE {raw_num or '1'}"

    return {
        "id": stg_id,
        "name": stg_name,
        "grid": grid_rows,
        "rows": getattr(stg, "rows", len(grid_rows)),
        "cols": getattr(stg, "cols", max((len(r) for r in grid_rows), default=0)),
        "start": [start_pos[0], start_pos[1]],
        "goal": [goal_pos[0], goal_pos[1]],
        "switches": switches_list,
        "bridges": bridges_dict,
        "bridge_at": bridge_at,
    }


def state_to_dict(st: Any) -> Dict[str, Any]:
    """Chuyển đổi State của bloxorz sang dict chuẩn JSON cho Three.js."""
    if hasattr(st, "to_dict") and callable(st.to_dict):
        return st.to_dict()

    pose = getattr(st, "pose", None)
    pos = getattr(st, "pos", (0, 0))
    cube2 = getattr(st, "cube2", None)
    bridges_open = sorted(getattr(st, "bridges_open", frozenset()))

    if pose is not None:
        pose_name = pose.name if hasattr(pose, "name") else str(pose)
        pose_val = pose.value if hasattr(pose, "value") else int(pose)
        if pose_name == "STANDING":
            b1 = {"r": pos[0], "c": pos[1]}
            b2 = {"r": pos[0], "c": pos[1]}
        elif pose_name == "HORIZONTAL":
            b1 = {"r": pos[0], "c": pos[1]}
            b2 = {"r": pos[0], "c": pos[1] + 1}
        elif pose_name == "VERTICAL":
            b1 = {"r": pos[0], "c": pos[1]}
            b2 = {"r": pos[0] + 1, "c": pos[1]}
        else:
            b1 = {"r": pos[0], "c": pos[1]}
            b2 = {"r": pos[0], "c": pos[1]}
    else:
        pose_name = "SPLIT"
        pose_val = -1
        b1 = {"r": pos[0], "c": pos[1]}
        c2 = cube2 if cube2 is not None else pos
        b2 = {"r": c2[0], "c": c2[1]}

    return {
        "pos": [pos[0], pos[1]],
        "pose": pose_name,
        "pose_val": pose_val,
        "cube2": [cube2[0], cube2[1]] if cube2 is not None else None,
        "b1": b1,
        "b2": b2,
        "bridges_open": bridges_open,
    }


def action_to_name(act: Any) -> str:
    """Trích xuất tên hướng ('UP', 'DOWN', 'LEFT', 'RIGHT') từ Action hoặc Direction."""
    if hasattr(act, "direction"):
        d = act.direction
        return d.name if hasattr(d, "name") else str(d)
    if hasattr(act, "name"):
        return act.name
    return str(act).upper()


class PyWebViewJsApi:
    """
    Đối tượng API được gắn vào `window.pywebview.api` phía JavaScript,
    cho phép Renderer gửi sự kiện điều khiển của người chơi về Python Controller.
    """

    def __init__(self, bridge: RendererBridge) -> None:
        self._bridge = bridge

    def on_ready(self) -> Dict[str, Any]:
        return self._bridge.handle_client_event("ready", {})

    def on_action(self, action_name: str) -> Dict[str, Any]:
        return self._bridge.handle_client_event("action", {"action": action_name})

    def on_undo(self) -> Dict[str, Any]:
        return self._bridge.handle_client_event("undo", {})

    def on_restart(self) -> Dict[str, Any]:
        return self._bridge.handle_client_event("restart", {})

    def on_next_stage(self) -> Dict[str, Any]:
        return self._bridge.handle_client_event("next_stage", {})

    def on_prev_stage(self) -> Dict[str, Any]:
        return self._bridge.handle_client_event("prev_stage", {})

    def on_switch_cube(self) -> Dict[str, Any]:
        return self._bridge.handle_client_event("switch_cube", {})

    def on_solve_ai(self, algorithm: str = "astar") -> Dict[str, Any]:
        return self._bridge.handle_client_event("solve_ai", {"algorithm": algorithm})

    def poll_commands(self) -> List[Dict[str, Any]]:
        return self._bridge.drain_commands()


class RendererBridge:
    """
    Cầu nối giao tiếp chuẩn JSON giữa Python (SceneView / GameController) và Three.js (index.html).
    """

    def __init__(self, html_path: Optional[Path] = None) -> None:
        self.html_path: Path = html_path or (Path(__file__).resolve().parent / "index.html")
        self._lock = threading.Lock()
        self._command_queue: List[Dict[str, Any]] = []
        self._event_handler: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None
        self._webview_window: Any = None
        self._http_server: Optional[ThreadingHTTPServer] = None
        self._server_port: int = 0
        self.js_api = PyWebViewJsApi(self)

    def set_event_handler(
        self,
        handler: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """Đăng ký hàm callback phía Python Controller để xử lý sự kiện từ UI/bàn phím."""
        self._event_handler = handler

    def handle_client_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Xử lý sự kiện từ phía JS gửi lên và trả kèm các lệnh Scene Protocol mới nhất."""
        result: Dict[str, Any] = {"ok": True}
        if self._event_handler is not None:
            try:
                res = self._event_handler(event_type, payload)
                if isinstance(res, dict):
                    result.update(res)
            except Exception as exc:
                result = {"ok": False, "error": str(exc)}
        result["commands"] = self.drain_commands()
        return result

    def send_command(self, cmd_type: str, payload: Dict[str, Any]) -> None:
        """
        Đẩy một lệnh diễn hoạt (Scene Protocol) từ Python xuống Renderer.
        Nếu cửa sổ `pywebview` đang mở và sẵn sàng, đẩy trực tiếp qua `evaluate_js`,
        đồng thời lưu hàng đợi an toàn luồng (thread-safe queue).
        """
        envelope = {"type": cmd_type, "payload": payload}
        with self._lock:
            self._command_queue.append(envelope)

        if self._webview_window is not None:
            try:
                cmds = self.drain_commands()
                if cmds:
                    js_payload = json.dumps(cmds, ensure_ascii=False)
                    self._webview_window.evaluate_js(
                        f"window.SceneBridge && window.SceneBridge.receiveCommands({js_payload});"
                    )
            except Exception:
                with self._lock:
                    self._command_queue = cmds + self._command_queue

    def drain_commands(self) -> List[Dict[str, Any]]:
        """Lấy và xóa toàn bộ các lệnh đang chờ trong hàng đợi."""
        with self._lock:
            cmds = list(self._command_queue)
            self._command_queue.clear()
            return cmds

    # -----------------------------------------------------------------------
    # Các hàm đóng gói JSON chuẩn Scene Protocol
    # -----------------------------------------------------------------------
    @staticmethod
    def serialize_load_stage(
        stage: Any,
        state: Any,
        stage_index: int = 0,
        total_stages: int = 1,
        moves: int = 0,
        active_cube: int = 0,
    ) -> Dict[str, Any]:
        return {
            "stage": stage_to_dict(stage),
            "state": state_to_dict(state),
            "stage_index": stage_index,
            "total_stages": total_stages,
            "moves": moves,
            "active_cube": active_cube,
        }

    @staticmethod
    def serialize_move(
        old_state: Any,
        action: Any,
        new_state: Any,
        moves: int = 0,
        active_cube: int = 0,
    ) -> Dict[str, Any]:
        old_d = state_to_dict(old_state)
        new_d = state_to_dict(new_state)
        action_cube = getattr(action, "cube", None)
        return {
            "old_state": old_d,
            "action": action_to_name(action),
            "action_cube": action_cube,
            "active_cube": active_cube,
            "new_state": new_d,
            "bridges_changed": sorted(new_d["bridges_open"]) != sorted(old_d["bridges_open"]),
            "moves": moves,
        }

    @staticmethod
    def serialize_fall(
        old_state: Any,
        action: Any,
        broken_cell: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        return {
            "old_state": state_to_dict(old_state),
            "action": action_to_name(action),
            "broken_cell": [broken_cell[0], broken_cell[1]] if broken_cell else None,
        }

    @staticmethod
    def serialize_win(state: Any, moves: int = 0) -> Dict[str, Any]:
        return {
            "state": state_to_dict(state),
            "moves": moves,
        }

    # -----------------------------------------------------------------------
    # Khởi chạy Local HTTP Server & Desktop Native Window (pywebview / GTK)
    # -----------------------------------------------------------------------
    def _start_local_http_server(self) -> str:
        """Khởi chạy HTTP Server nội bộ phục vụ index.html và REST/RPC Bridge."""
        if self._http_server is not None:
            return f"http://127.0.0.1:{self._server_port}"

        bridge_ref = self
        html_file = self.html_path

        class BridgeRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass  # Tắt log HTTP để terminal luôn sạch

            def do_GET(self) -> None:
                if self.path in ("/", "/index.html"):
                    if html_file.exists():
                        content = html_file.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                        self.send_header("Content-Length", str(len(content)))
                        self.end_headers()
                        self.wfile.write(content)
                    else:
                        self.send_error(404, "Không tìm thấy index.html")
                elif self.path == "/api/poll":
                    cmds = bridge_ref.drain_commands()
                    body = json.dumps({"commands": cmds}, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_error(404)

            def do_POST(self) -> None:
                if self.path == "/api/event":
                    length = int(self.headers.get("Content-Length", "0"))
                    raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                    data = json.loads(raw)
                    ev_type = str(data.get("event", ""))
                    ev_payload = dict(data.get("payload", {}))
                    response_data = bridge_ref.handle_client_event(ev_type, ev_payload)
                    body = json.dumps(response_data, ensure_ascii=False).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_error(404)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            self._server_port = s.getsockname()[1]

        self._http_server = ThreadingHTTPServer(("127.0.0.1", self._server_port), BridgeRequestHandler)
        thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        thread.start()
        return f"http://127.0.0.1:{self._server_port}"

    def run_window(
        self,
        title: str = "Bloxorz: Voxel Edition (Minecraft 3D)",
        width: int = 1280,
        height: int = 800,
    ) -> None:
        """
        Khởi chạy cửa sổ Desktop Native Micro-Renderer:
        1. Ưu tiên sử dụng `pywebview` (chuẩn kiến trúc quy định).
        2. Nếu môi trường chưa cài `pywebview`, tự động dùng GTK3 + WebKit2 Native Window
           hoặc trình duyệt hệ thống kết nối qua Local IPC Server.
        """
        url = self._start_local_http_server()

        # 1. Thử khởi chạy bằng pywebview
        try:
            import webview  # type: ignore

            self._webview_window = webview.create_window(
                title=title,
                url=url,
                js_api=self.js_api,
                width=width,
                height=height,
                min_size=(900, 600),
                background_color="#111111",
            )
            webview.start(gui="gtk")
            return
        except ImportError:
            pass
        except Exception:
            pass

        # 2. Thử khởi chạy Native Window bằng GTK3 + WebKit2 (hỗ trợ Linux Desktop)
        try:
            import gi  # type: ignore

            gi.require_version("Gtk", "3.0")
            gi.require_version("WebKit2", "4.1")
            from gi.repository import GLib, Gtk, WebKit2  # type: ignore

            win = Gtk.Window(title=title)
            win.set_default_size(width, height)
            win.set_position(Gtk.WindowPosition.CENTER)

            web_view = WebKit2.WebView()
            settings = web_view.get_settings()
            settings.set_enable_webgl(True)
            settings.set_enable_write_console_messages_to_stdout(False)
            web_view.load_uri(url)

            win.add(web_view)
            win.connect("destroy", Gtk.main_quit)
            win.show_all()
            Gtk.main()
            return
        except Exception:
            pass

        # 3. Fallback khởi chạy bằng trình duyệt hệ thống qua Local IPC Server
        print(f"[Bloxorz Micro-Renderer] Đang khởi chạy giao diện WebGL tại: {url}")
        webbrowser.open(url)
        try:
            while True:
                threading.Event().wait(1.0)
        except KeyboardInterrupt:
            pass
