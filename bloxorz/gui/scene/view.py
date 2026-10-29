"""SceneView Dual-Engine Implementation: Primary WebGL Three.js & Fallback Native OpenGL 3.3 Core."""
from __future__ import annotations

import math
import time
from typing import Any, Callable, Dict, Optional

from bloxorz.gui.scene.audio import ProceduralAudioEngine
from bloxorz.gui.scene.bridge import RendererBridge, action_to_name
from bloxorz.gui.scene.renderer import VoxelOpenGLRenderer


def animate_roll(
    entity: Any,
    target: tuple[float, float, float],
    on_complete: Callable[[], None] | None = None,
) -> None:
    """Animate roll helper preserved for test compatibility."""
    if on_complete:
        on_complete()


class SceneView:
    """Dual-Engine 3D SceneView:
    - Primary Engine: High-fidelity WebGL Three.js Desktop Micro-Renderer.
    - Fallback Engine (Replaces Ursina): Native OpenGL 3.3 Core Profile (v2).
    """

    def __init__(self, bridge: Optional[RendererBridge] = None, audio_enabled: bool = True) -> None:
        self.bridge: RendererBridge = bridge or RendererBridge()
        try:
            self.renderer: VoxelOpenGLRenderer | None = VoxelOpenGLRenderer()
        except Exception:
            self.renderer = None

        try:
            self.audio: ProceduralAudioEngine = ProceduralAudioEngine(enabled=audio_enabled)
        except Exception:
            self.audio = None

        self.current_stage: Any = None
        self.current_state: Any = None
        self.controller: Any = None
        self._animating: bool = False
        self.stage_index: int = 0
        self.total_stages: int = 1
        self.moves_count: int = 0

        # Solution playback queue for OpenGL
        self._playback_queue: list[Any] = []
        self._playback_delay: float = 0.20
        self._playback_timer: float = 0.0
        self.is_playing_solution: bool = False

        # Controller callbacks
        self.on_action_request: Callable[[Any], None] | None = None
        self.on_undo_request: Callable[[], None] | None = None
        self.on_restart_request: Callable[[], None] | None = None
        self.on_solve_request: Callable[[str], None] | None = None
        self.on_stage_delta_request: Callable[[int], None] | None = None

        # Mouse orbit state
        self._dragging_orbit: bool = False
        self._last_mouse_x: float = 0.0
        self._last_mouse_y: float = 0.0
        self._last_frame_time: float = time.perf_counter()

    # ==========================================================================
    # SCENE PROTOCOL CONTRACT METHODS
    # ==========================================================================

    def is_animating(self) -> bool:
        """True when the scene is busy animating (rolling, falling, winning)."""
        if getattr(self, "_animating", False):
            return True
        if hasattr(self, "renderer") and self.renderer is not None:
            return self.renderer.is_animating()
        return False

    def load_stage(self, stage: Any, state: Any | None = None) -> None:
        """1. Load a puzzle stage and initialize both WebGL and OpenGL 3D engines."""
        init_state = state if state is not None else getattr(stage, "initial_state", lambda: None)()
        self.current_stage = stage
        self.current_state = init_state
        self._playback_queue.clear()
        self.is_playing_solution = False
        self._animating = False

        if getattr(self, "controller", None) is not None:
            self.stage_index = getattr(self.controller, "index", 0)
            self.total_stages = len(getattr(self.controller, "stages", [stage]))
            self.moves_count = getattr(self.controller, "moves", 0)
        else:
            self.stage_index = getattr(self, "stage_index", 0)
            self.total_stages = getattr(self, "total_stages", 1)
            self.moves_count = getattr(self, "moves_count", 0)

        # 1. Sync to Primary WebGL Three.js
        if hasattr(self, "bridge") and self.bridge is not None:
            try:
                payload = self.bridge.serialize_load_stage(
                    stage=stage,
                    state=init_state,
                    stage_index=self.stage_index,
                    total_stages=self.total_stages,
                    moves=self.moves_count,
                )
                self.bridge.send_command("load_stage", payload)
            except Exception:
                pass

        # 2. Sync to Fallback Native OpenGL 3.3
        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.stage_index = self.stage_index
            self.renderer.total_stages = self.total_stages
            self.renderer.move_count = self.moves_count
            self.renderer.set_stage_and_state(stage, init_state)
            try:
                from bloxorz.search import run
                sol = run("astar", stage)
                self.renderer.optimal_moves = len(sol.actions) if sol.status == "solved" else None
            except Exception:
                self.renderer.optimal_moves = None

    def on_move(self, old_state: Any, action: Any, new_state: Any) -> None:
        """2. Animate block roll in WebGL Three.js and OpenGL 3.3."""
        self.current_state = new_state
        curr_moves = getattr(self, "moves_count", 0)
        ctrl = getattr(self, "controller", None)
        self.moves_count = getattr(ctrl, "moves", curr_moves + 1) if ctrl is not None else curr_moves + 1

        # 1. Sync to Primary WebGL Three.js
        if hasattr(self, "bridge") and self.bridge is not None:
            try:
                payload = self.bridge.serialize_move(
                    old_state=old_state,
                    action=action,
                    new_state=new_state,
                    moves=self.moves_count,
                )
                self.bridge.send_command("on_move", payload)
            except Exception:
                pass

        # 2. Sync to Fallback Native OpenGL 3.3
        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.move_count = self.moves_count
            self.renderer.start_roll(old_state, action, new_state)

        # Legacy Ursina / test compatibility hook
        if hasattr(self, "block") and self.block is not None:
            if getattr(old_state, "pose", None) is None and getattr(new_state, "pose", None) is None:
                action_cube = getattr(action, "cube", 0)
                moving_cube = getattr(self.block, "cube1", None) if action_cube == 0 else getattr(self.block, "cube2", None)
                still = old_state.cube2 if action_cube == 0 else old_state.pos
                moved_to_cube2 = (new_state.pos == still)
                if moved_to_cube2 != (action_cube == 1):
                    c1 = getattr(self.block, "cube1", None)
                    c2 = getattr(self.block, "cube2", None)
                    if c1 is not None and c2 is not None:
                        self.block.cube1, self.block.cube2 = c2, c1
                r, c = new_state.cube2 if moved_to_cube2 else new_state.pos
                target_pos = (float(c), 0.55, -float(r))

                def _finish_split() -> None:
                    self._animating = False
                    if hasattr(self.block, "sync_from_state"):
                        self.block.sync_from_state(new_state)
                    elif hasattr(self.block, "update_from_state"):
                        self.block.update_from_state(new_state)
                    if hasattr(self, "board") and self.board is not None and hasattr(self.board, "update_bridges"):
                        self.board.update_bridges(new_state)

                self._animating = True
                animate_roll(moving_cube, target_pos, on_complete=_finish_split)
            else:
                def _done():
                    self._animating = False
                    if hasattr(self.block, "sync_from_state"):
                        self.block.sync_from_state(new_state)
                    elif hasattr(self.block, "update_from_state"):
                        self.block.update_from_state(new_state)
                    if hasattr(self, "board") and self.board is not None and hasattr(self.board, "update_bridges"):
                        self.board.update_bridges(new_state)

                self._animating = True
                if hasattr(self.block, "update_from_state"):
                    self.block.update_from_state(new_state)
                _done()

        # Audio feedback
        if hasattr(self, "audio") and self.audio is not None:
            hit_switch = False
            if hasattr(self.current_stage, "switch_at") and callable(getattr(new_state, "occupied_cells", None)):
                for r, c in new_state.occupied_cells():
                    if (r, c) in self.current_stage.switch_at:
                        hit_switch = True
                        break
            bridges_changed = getattr(old_state, "bridges_open", None) != getattr(new_state, "bridges_open", None)
            if hit_switch or bridges_changed:
                self.audio.play_switch()
            else:
                self.audio.play_step()

    def on_fall(self, old_state: Any, action: Any) -> None:
        """3. Animate block fall in WebGL Three.js and OpenGL 3.3."""
        self._playback_queue.clear()
        self.is_playing_solution = False

        if hasattr(self, "bridge") and self.bridge is not None:
            try:
                payload = self.bridge.serialize_fall(old_state=old_state, action=action)
                self.bridge.send_command("on_fall", payload)
            except Exception:
                pass

        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.start_fall(old_state, action)

        if hasattr(self, "audio") and self.audio is not None:
            self.audio.play_fall()

    def on_win(self, state: Any) -> None:
        """4. Animate victory sequence with fireworks and victory chime."""
        self.current_state = state
        self._playback_queue.clear()
        self.is_playing_solution = False

        if hasattr(self, "bridge") and self.bridge is not None:
            try:
                payload = self.bridge.serialize_win(state=state, moves=self.moves_count)
                self.bridge.send_command("on_win", payload)
            except Exception:
                pass

        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.start_win(state)

        if hasattr(self, "audio") and self.audio is not None:
            self.audio.play_win()

    def play_solution(self, actions: list[Any], delay: float = 0.20) -> None:
        """5. Automatically step through solver actions with `delay` seconds."""
        if not actions or self.current_stage is None or self.current_state is None:
            return

        # 1. Primary WebGL solution playback
        if hasattr(self, "bridge") and self.bridge is not None:
            try:
                str_actions = [action_to_name(a) for a in actions]
                self.bridge.send_command("play_solution", {"actions": str_actions, "delay": delay})
            except Exception:
                pass

        # 2. Fallback OpenGL solution playback
        self._playback_queue = list(actions)
        self._playback_delay = max(0.16, float(delay))
        self._playback_timer = 0.0
        self.is_playing_solution = True

    # ==========================================================================
    # CONTROLLER BINDING
    # ==========================================================================

    def bind_controller(self, controller: Any) -> None:
        """Connect GameController instance to both WebGL and OpenGL event loops."""
        self.controller = controller
        from bloxorz.model import Direction

        dir_map = {
            "UP": Direction.UP,
            "DOWN": Direction.DOWN,
            "LEFT": Direction.LEFT,
            "RIGHT": Direction.RIGHT,
        }

        # Handle WebGL Client Events
        def _handle_webgl_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            if not self.controller:
                return {"ok": True}

            if event_type == "ready":
                self.load_stage(self.controller.stage, self.controller.state)

            elif event_type == "action":
                act_str = str(payload.get("action", "")).upper()
                d = dir_map.get(act_str)
                if d is not None:
                    old_st = self.controller.state
                    outcome = self.controller.move(d)
                    if outcome == "fell":
                        self.on_fall(old_st, d)
                    elif outcome in ("moved", "won"):
                        self.on_move(old_st, d, self.controller.state)
                        if outcome == "won":
                            self.on_win(self.controller.state)

            elif event_type == "undo":
                if self.controller.undo():
                    self.load_stage(self.controller.stage, self.controller.state)

            elif event_type == "restart":
                self.controller.restart()
                self.load_stage(self.controller.stage, self.controller.state)

            elif event_type == "next_stage":
                next_idx = (self.controller.index + 1) % len(self.controller.stages)
                self.controller.load(next_idx)
                self.load_stage(self.controller.stage, self.controller.state)

            elif event_type == "prev_stage":
                prev_idx = (self.controller.index - 1) % len(self.controller.stages)
                self.controller.load(prev_idx)
                self.load_stage(self.controller.stage, self.controller.state)

            elif event_type == "solve_ai":
                algo = str(payload.get("algorithm", "astar")).lower()
                try:
                    from bloxorz.search import run
                    res = run(algo, self.controller.stage)
                    if res.status == "solved" and res.actions:
                        self.play_solution(res.actions, delay=0.20)
                except Exception as err:
                    print(f"[AI Solver Error]: {err}")

            return {"ok": True}

        if hasattr(self, "bridge") and self.bridge is not None:
            self.bridge.set_event_handler(_handle_webgl_event)

        # Handle Native OpenGL Callbacks
        def _handle_opengl_action(act: Any) -> None:
            if not self.controller or self.is_animating():
                return
            if isinstance(act, str):
                d = dir_map.get(act.upper())
            elif hasattr(act, "direction"):
                d = act.direction
            else:
                d = act
            if d is None:
                return

            old_st = self.controller.state
            outcome = self.controller.move(d)
            if outcome == "fell":
                self.on_fall(old_st, d)
            elif outcome in ("moved", "won"):
                self.on_move(old_st, d, self.controller.state)
                if outcome == "won":
                    self.on_win(self.controller.state)

        def _handle_opengl_undo() -> None:
            if not self.controller:
                return
            if self.controller.undo():
                self.load_stage(self.controller.stage, self.controller.state)

        def _handle_opengl_restart() -> None:
            if not self.controller:
                return
            self.controller.restart()
            self.load_stage(self.controller.stage, self.controller.state)

        def _handle_opengl_solve(algo: str) -> None:
            if not self.controller:
                return
            try:
                from bloxorz.search import run
                res = run(algo, self.controller.stage)
                if res.status == "solved" and res.actions:
                    self.play_solution(res.actions, delay=0.20)
            except Exception as err:
                print(f"[AI Solver Error]: {err}")

        def _handle_opengl_stage_delta(delta: int) -> None:
            if not self.controller:
                return
            next_idx = (self.controller.index + delta) % len(self.controller.stages)
            self.controller.load(next_idx)
            self.load_stage(self.controller.stage, self.controller.state)

        self.on_action_request = _handle_opengl_action
        self.on_undo_request = _handle_opengl_undo
        self.on_restart_request = _handle_opengl_restart
        self.on_solve_request = _handle_opengl_solve
        self.on_stage_delta_request = _handle_opengl_stage_delta

    # ==========================================================================
    # WINDOW EXECUTION (PRIMARY WEBGL & FALLBACK OPENGL)
    # ==========================================================================

    def run_webgl(
        self,
        title: str = "Bloxorz: Voxel Edition (WebGL 3D)",
        width: int = 1280,
        height: int = 800,
    ) -> None:
        """Launch Primary WebGL Three.js Desktop Window."""
        if self.current_stage is None and self.controller is not None:
            self.load_stage(self.controller.stage, self.controller.state)
        self.bridge.run_window(title=title, width=width, height=height)

    def run_opengl(
        self,
        title: str = "Bloxorz: Voxel Edition (Native OpenGL 3.3 / GLSL)",
    ) -> None:
        """Launch Fallback Native OpenGL 3.3 Core Window."""
        self.run_native_window(title=title)

    def run_window(
        self,
        title: str = "Bloxorz: Voxel Edition",
    ) -> None:
        """Launch 3D Window: Tries Primary WebGL first, falls back to Native OpenGL 3.3."""
        try:
            self.run_webgl(title=f"{title} (WebGL 3D)")
        except Exception as exc:
            print(f"[SceneView] Chuyển đổi sang Fallback Native OpenGL 3.3: {exc}")
            self.run_opengl(title=f"{title} (OpenGL 3.3)")

    # ==========================================================================
    # NATIVE DESKTOP OPENGL 3.3 CORE WINDOW LOOP (GTK3 GLAREA)
    # ==========================================================================

    def update(self, dt: float) -> None:
        """Advance physics, animations, and AI solution playback by `dt` seconds."""
        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.update(dt)

        if self.is_playing_solution and self._playback_queue:
            self._playback_timer += dt
            is_idle = not (self.renderer and self.renderer.is_animating())
            if self._playback_timer >= self._playback_delay and is_idle:
                self._playback_timer = 0.0
                next_action = self._playback_queue.pop(0)
                if not self._playback_queue:
                    self.is_playing_solution = False
                if self.on_action_request is not None:
                    self.on_action_request(next_action)
                elif self.controller is not None:
                    d = getattr(next_action, "direction", next_action)
                    old_st = self.controller.state
                    outcome = self.controller.move(d)
                    if outcome == "fell":
                        self.on_fall(old_st, d)
                    elif outcome in ("moved", "won"):
                        self.on_move(old_st, d, self.controller.state)
                        if outcome == "won":
                            self.on_win(self.controller.state)

    def run_native_window(
        self, title: str = "Bloxorz: Voxel Edition (Native OpenGL 3.3 / GLSL)"
    ) -> None:
        """Launch the Native Python OpenGL 3.3 Core Desktop Window at 60 FPS."""
        if self.current_stage is None and self.controller is not None:
            self.load_stage(self.controller.stage, self.controller.state)

        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, Gtk
        from bloxorz.model import Direction

        win = Gtk.Window(title=title)
        win.set_default_size(1280, 760)
        win.set_position(Gtk.WindowPosition.CENTER)

        gl_area = Gtk.GLArea()
        gl_area.set_required_version(3, 3)
        gl_area.set_has_depth_buffer(True)
        gl_area.set_auto_render(True)
        gl_area.set_can_focus(True)
        gl_area.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.KEY_PRESS_MASK
        )

        def _on_realize(area: Gtk.GLArea) -> None:
            area.make_current()
            if area.get_error() is not None:
                return
            if self.renderer:
                self.renderer.init_gl()

        def _on_render(area: Gtk.GLArea, _ctx: object) -> bool:
            now = time.perf_counter()
            dt = now - self._last_frame_time
            self._last_frame_time = now
            self.update(dt)

            scale = area.get_scale_factor()
            alloc = area.get_allocation()
            w = max(1, alloc.width * scale)
            h = max(1, alloc.height * scale)
            if self.renderer:
                self.renderer.render(w, h)
            return True

        def _tick_callback(widget: Gtk.Widget, _frame_clock: object) -> bool:
            widget.queue_draw()
            return True

        def _on_button_press(area: Gtk.GLArea, event: Gdk.EventButton) -> bool:
            area.grab_focus()
            scale = area.get_scale_factor()
            sx, sy = event.x * scale, event.y * scale
            if event.button == 1 and self.renderer:
                btn_id = self.renderer.hud_renderer.hit_test(sx, sy)
                if btn_id is not None:
                    self._handle_hud_button(btn_id)
                    return True
                self._dragging_orbit = True
                self._last_mouse_x = event.x
                self._last_mouse_y = event.y
            return True

        def _on_button_release(_area: Gtk.GLArea, event: Gdk.EventButton) -> bool:
            if event.button == 1:
                self._dragging_orbit = False
            return True

        def _on_motion(area: Gtk.GLArea, event: Gdk.EventMotion) -> bool:
            if not self.renderer:
                return True
            scale = area.get_scale_factor()
            sx, sy = event.x * scale, event.y * scale
            hovered = self.renderer.hud_renderer.hit_test(sx, sy)
            if hovered != self.renderer.hover_btn_id:
                self.renderer.hover_btn_id = hovered
                self.renderer._hud_dirty = True

            if self._dragging_orbit:
                dx = event.x - self._last_mouse_x
                dy = event.y - self._last_mouse_y
                self._last_mouse_x = event.x
                self._last_mouse_y = event.y
                self.renderer.camera.orbit(-dx * 0.45, dy * 0.38)
            return True

        def _on_scroll(_area: Gtk.GLArea, event: Gdk.EventScroll) -> bool:
            if not self.renderer:
                return True
            if event.direction == Gdk.ScrollDirection.UP:
                self.renderer.camera.zoom(-1.0)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.renderer.camera.zoom(1.0)
            elif event.direction == Gdk.ScrollDirection.SMOOTH:
                _, _, dy = event.get_scroll_deltas()
                self.renderer.camera.zoom(dy)
            return True

        def _on_key_press(_win: Gtk.Window, event: Gdk.EventKey) -> bool:
            keyname = Gdk.keyval_name(event.keyval)
            if not keyname:
                return False
            k = keyname.lower()

            if k in ("escape",):
                Gtk.main_quit()
                return True
            if k in ("1",):
                if self.renderer:
                    self.renderer.set_biome("overworld")
                return True
            if k in ("2",):
                if self.renderer:
                    self.renderer.set_biome("nether")
                return True
            if k in ("3",):
                if self.renderer:
                    self.renderer.set_biome("end")
                return True
            if k in ("r",):
                if self.on_restart_request:
                    self.on_restart_request()
                return True
            if k in ("u", "backspace"):
                if self.on_undo_request:
                    self.on_undo_request()
                return True
            if k in ("space",):
                if self.controller and hasattr(self.controller, "switch_cube"):
                    self.controller.switch_cube()
                return True
            if k in ("p",):
                if self.on_solve_request:
                    self.on_solve_request("astar")
                return True
            if k in ("b",):
                if self.on_solve_request:
                    self.on_solve_request("bfs")
                return True
            if k in ("bracketleft",):
                if self.on_stage_delta_request:
                    self.on_stage_delta_request(-1)
                return True
            if k in ("bracketright", "n"):
                if self.on_stage_delta_request:
                    self.on_stage_delta_request(1)
                return True

            action_map = {
                "w": Direction.UP,
                "up": Direction.UP,
                "s": Direction.DOWN,
                "down": Direction.DOWN,
                "a": Direction.LEFT,
                "left": Direction.LEFT,
                "d": Direction.RIGHT,
                "right": Direction.RIGHT,
            }
            if k in action_map and not self.is_playing_solution:
                if self.on_action_request:
                    self.on_action_request(action_map[k])
                return True
            return False

        gl_area.connect("realize", _on_realize)
        gl_area.connect("render", _on_render)
        gl_area.connect("button-press-event", _on_button_press)
        gl_area.connect("button-release-event", _on_button_release)
        gl_area.connect("motion-notify-event", _on_motion)
        gl_area.connect("scroll-event", _on_scroll)
        gl_area.add_tick_callback(_tick_callback)

        win.connect("key-press-event", _on_key_press)
        win.connect("destroy", Gtk.main_quit)
        win.add(gl_area)
        win.show_all()
        gl_area.grab_focus()
        Gtk.main()

    def _handle_hud_button(self, btn_id: str) -> None:
        if not self.renderer:
            return
        if btn_id == "biome_overworld":
            self.renderer.set_biome("overworld")
        elif btn_id == "biome_nether":
            self.renderer.set_biome("nether")
        elif btn_id == "biome_end":
            self.renderer.set_biome("end")
        elif btn_id == "ai_astar" and self.on_solve_request:
            self.on_solve_request("astar")
        elif btn_id == "ai_bfs" and self.on_solve_request:
            self.on_solve_request("bfs")
        elif btn_id == "undo" and self.on_undo_request:
            self.on_undo_request()
        elif btn_id == "restart" and self.on_restart_request:
            self.on_restart_request()
        elif btn_id == "prev_stage" and self.on_stage_delta_request:
            self.on_stage_delta_request(-1)
        elif btn_id == "next_stage" and self.on_stage_delta_request:
            self.on_stage_delta_request(1)
