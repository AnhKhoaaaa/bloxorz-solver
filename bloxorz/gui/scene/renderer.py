"""100% Native OpenGL 3.3 Core 3D Voxel Renderer with Parametric Circle Arc Physics & 2-Node Gimbal Camera."""
from __future__ import annotations

import ctypes
from ctypes import c_float, c_uint, c_void_p
import math
import random
import time
from typing import Any

import numpy as np

from bloxorz.gui.scene.shaders import (
    GLCore,
    HUD_FRAGMENT_SHADER,
    HUD_VERTEX_SHADER,
    VOXEL_FRAGMENT_SHADER,
    VOXEL_VERTEX_SHADER,
)
from bloxorz.gui.scene.textures import MinecraftHUDRenderer, VoxelTextureCatalog


# ==============================================================================
# 0. ADAPTER HELPERS FOR BLOXORZ STATE & ACTIONS
# ==============================================================================

def get_action_delta(action: Any) -> tuple[int, int]:
    """Return (dx, dz) where dx is col delta and dz is row delta."""
    if hasattr(action, "delta"):
        return action.delta
    if hasattr(action, "direction"):
        d = action.direction
    else:
        d = action
    d_str = getattr(d, "name", str(d)).upper()
    if d_str in ("UP", "U"):
        return (0, -1)
    if d_str in ("DOWN", "D"):
        return (0, 1)
    if d_str in ("LEFT", "L"):
        return (-1, 0)
    if d_str in ("RIGHT", "R"):
        return (1, 0)
    return (0, 0)


def get_occupied_cells_list(state: Any) -> list[tuple[int, int]]:
    """Return list of (x, z) where x is col and z is row."""
    if state is None:
        return []
    if hasattr(state, "occupied_cells") and callable(state.occupied_cells):
        cells = state.occupied_cells()
        return [(int(c), int(r)) for r, c in cells]
    if hasattr(state, "pose") and state.pose is None:
        res = []
        if hasattr(state, "pos") and state.pos is not None:
            res.append((int(state.pos[1]), int(state.pos[0])))
        if hasattr(state, "cube2") and state.cube2 is not None:
            res.append((int(state.cube2[1]), int(state.cube2[0])))
        return res
    if hasattr(state, "pos"):
        r, c = state.pos
        p_str = str(state.pose).upper()
        if "STANDING" in p_str:
            return [(int(c), int(r))]
        elif "HORIZONTAL" in p_str:
            return [(int(c), int(r)), (int(c) + 1, int(r))]
        elif "VERTICAL" in p_str:
            return [(int(c), int(r)), (int(c), int(r) + 1)]
    if hasattr(state, "x") and hasattr(state, "z"):
        x, z = state.x, state.z
        p_str = str(state.pose).upper()
        if "STANDING" in p_str:
            return [(x, z)]
        elif "LYING_X" in p_str:
            return [(x, z), (x + 1, z)]
        elif "LYING_Z" in p_str:
            return [(x, z), (x, z + 1)]
    return []


def inspect_fall_details(stage: Any, old_state: Any, action: Any) -> dict:
    dx, dz = get_action_delta(action)
    fragile_pos = None
    try:
        if hasattr(old_state, "pose") and old_state.pose is not None:
            from bloxorz.engine.rules import is_fragile_tile, roll_transition
            from bloxorz.model import Direction

            d_map = {
                (0, -1): Direction.UP,
                (0, 1): Direction.DOWN,
                (-1, 0): Direction.LEFT,
                (1, 0): Direction.RIGHT,
            }
            d = d_map.get((dx, dz), Direction.RIGHT)
            new_pose, new_pos = roll_transition(old_state.pose, old_state.pos, d)
            p_str = str(new_pose).upper()
            if "STANDING" in p_str:
                r, c = new_pos
                if stage.in_bounds((r, c)) and is_fragile_tile(stage, (r, c)):
                    fragile_pos = (c, r)
    except Exception:
        pass

    return {
        "fragile_cell": fragile_pos,
        "delta": (dx, dz),
    }


# ==============================================================================
# 1. MATHEMATICAL HELPERS (MATRICES, RODRIGUES ROTATION, GIMBAL CAMERA)
# ==============================================================================

def perspective_matrix(fov_deg: float, aspect: float, near: float, far: float) -> np.ndarray:
    """Construct a column-major 4x4 perspective projection matrix for OpenGL."""
    f = 1.0 / math.tan(math.radians(fov_deg) * 0.5)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / max(aspect, 1e-4)
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m.T.copy()


def look_at_matrix(eye: np.ndarray, target: np.ndarray, world_up: np.ndarray) -> np.ndarray:
    """Construct a column-major 4x4 view matrix with zero horizon roll."""
    f = target - eye
    f_norm = float(np.linalg.norm(f))
    if f_norm < 1e-6:
        f = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    else:
        f = f / f_norm

    r = np.cross(f, world_up)
    r_norm = float(np.linalg.norm(r))
    if r_norm < 1e-6:
        r = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    else:
        r = r / r_norm

    u = np.cross(r, f)

    m = np.eye(4, dtype=np.float32)
    m[0, 0:3] = r
    m[1, 0:3] = u
    m[2, 0:3] = -f
    m[0, 3] = -float(np.dot(r, eye))
    m[1, 3] = -float(np.dot(u, eye))
    m[2, 3] = float(np.dot(f, eye))
    return m.T.copy()


def rodrigues_rotation_3x3(axis: tuple[float, float, float], theta_rad: float) -> np.ndarray:
    """Compute exact 3x3 rotation matrix around unit `axis` by `theta_rad` (Rodrigues' formula)."""
    kx, ky, kz = axis
    norm = math.sqrt(kx * kx + ky * ky + kz * kz)
    if norm < 1e-8 or abs(theta_rad) < 1e-8:
        return np.eye(3, dtype=np.float32)
    kx, ky, kz = kx / norm, ky / norm, kz / norm
    c = math.cos(theta_rad)
    s = math.sin(theta_rad)
    v = 1.0 - c
    return np.array(
        [
            [kx * kx * v + c, kx * ky * v - kz * s, kx * kz * v + ky * s],
            [ky * kx * v + kz * s, ky * ky * v + c, ky * kz * v - kx * s],
            [kz * kx * v - ky * s, kz * ky * v + kx * s, kz * kz * v + c],
        ],
        dtype=np.float32,
    )


class TwoNodeGimbalCamera:
    """2-Node Gimbal Orbit Camera Rig (Yaw around Y, Pitch around X clamped to [20°, 80°]).

    Eliminates gimbal lock and horizon roll while smoothly tracking the Oak Log center
    via exponential damping.
    """

    def __init__(self) -> None:
        self.yaw_deg: float = 24.0
        self.pitch_deg: float = 46.0
        self.distance: float = 14.0
        self.target_distance: float = 14.0
        self.target = np.array([4.5, 0.2, 2.5], dtype=np.float32)
        self.desired_target = np.array([4.5, 0.2, 2.5], dtype=np.float32)
        self.shake_intensity: float = 0.0
        self.shake_timer: float = 0.0

    def orbit(self, delta_yaw_deg: float, delta_pitch_deg: float) -> None:
        self.yaw_deg = (self.yaw_deg + delta_yaw_deg) % 360.0
        self.pitch_deg = max(20.0, min(80.0, self.pitch_deg + delta_pitch_deg))

    def zoom(self, delta_steps: float) -> None:
        self.target_distance = max(6.5, min(26.0, self.target_distance + delta_steps * 1.15))

    def trigger_shake(self, intensity: float = 0.36, duration: float = 0.45) -> None:
        self.shake_intensity = intensity
        self.shake_timer = duration

    def update(self, dt: float) -> None:
        alpha = 1.0 - math.exp(-10.5 * min(dt, 0.1))
        self.target = self.target + (self.desired_target - self.target) * alpha
        self.distance += (self.target_distance - self.distance) * alpha
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)

    def compute_eye_and_view(self, elapsed_time: float) -> tuple[np.ndarray, np.ndarray]:
        yaw_rad = math.radians(self.yaw_deg)
        pitch_rad = math.radians(self.pitch_deg)

        horiz = self.distance * math.cos(pitch_rad)
        eye_offset = np.array(
            [
                horiz * math.sin(yaw_rad),
                self.distance * math.sin(pitch_rad),
                horiz * math.cos(yaw_rad),
            ],
            dtype=np.float32,
        )

        shake_offset = np.zeros(3, dtype=np.float32)
        if self.shake_timer > 0.0:
            decay = self.shake_timer / 0.45
            amp = self.shake_intensity * decay
            shake_offset[0] = math.sin(elapsed_time * 58.0) * amp
            shake_offset[1] = math.cos(elapsed_time * 73.0) * amp * 0.8
            shake_offset[2] = math.sin(elapsed_time * 47.0) * amp * 0.6

        focus = self.target + shake_offset
        eye = focus + eye_offset
        view = look_at_matrix(eye, focus, np.array([0.0, 1.0, 0.0], dtype=np.float32))
        return eye, view


# ==============================================================================
# 2. BIOME PRESETS (OVERWORLD, NETHER, THE END)
# ==============================================================================

BIOME_PRESETS: dict[str, dict] = {
    "overworld": {
        "sky": (0.52, 0.77, 0.96),
        "fog_color": (0.62, 0.82, 0.97),
        "fog_density": 0.019,
        "sun_dir": (0.55, 0.88, 0.42),
        "sun_color": (1.02, 0.96, 0.84),
        "ambient_sky": (0.58, 0.66, 0.78),
        "ambient_ground": (0.28, 0.32, 0.26),
    },
    "nether": {
        "sky": (0.20, 0.04, 0.04),
        "fog_color": (0.34, 0.07, 0.04),
        "fog_density": 0.032,
        "sun_dir": (0.35, 0.85, -0.35),
        "sun_color": (1.05, 0.62, 0.36),
        "ambient_sky": (0.56, 0.22, 0.16),
        "ambient_ground": (0.72, 0.25, 0.06),
    },
    "end": {
        "sky": (0.04, 0.02, 0.09),
        "fog_color": (0.07, 0.03, 0.15),
        "fog_density": 0.025,
        "sun_dir": (-0.45, 0.90, 0.38),
        "sun_color": (0.78, 0.70, 1.05),
        "ambient_sky": (0.36, 0.28, 0.55),
        "ambient_ground": (0.14, 0.10, 0.26),
    },
}


# ==============================================================================
# 3. 3D VOXEL GEOMETRY BUILDER (13 FLOATS PER VERTEX: POS3, NORM3, UV2, TEX1, TINT4)
# ==============================================================================

_CUBE_FACES = [
    # +Y (Top)
    (
        (0.0, 1.0, 0.0),
        [(-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5), (0.5, 0.5, 0.5), (0.5, 0.5, -0.5)],
    ),
    # -Y (Bottom)
    (
        (0.0, -1.0, 0.0),
        [(-0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5)],
    ),
    # +Z (Front / South)
    (
        (0.0, 0.0, 1.0),
        [(-0.5, -0.5, 0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5)],
    ),
    # -Z (Back / North)
    (
        (0.0, 0.0, -1.0),
        [(0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5)],
    ),
    # +X (Right / East)
    (
        (1.0, 0.0, 0.0),
        [(0.5, -0.5, 0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5)],
    ),
    # -X (Left / West)
    (
        (-1.0, 0.0, 0.0),
        [(-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5)],
    ),
]

_FACE_UVS = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
_QUAD_TRI_INDICES = (0, 1, 2, 0, 2, 3)


def append_box_vertices(
    out_list: list[float],
    center: tuple[float, float, float],
    size: tuple[float, float, float],
    tex_ids_per_face: tuple[int, int, int, int, int, int] | int,
    tint: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    rot_mat: np.ndarray | None = None,
    pivot: tuple[float, float, float] | None = None,
) -> None:
    """Append 36 vertices (6 faces * 2 triangles) of a 3D box into `out_list`."""
    cx, cy, cz = center
    sx, sy, sz = size
    if isinstance(tex_ids_per_face, int):
        tids = (tex_ids_per_face,) * 6
    else:
        tids = tex_ids_per_face

    r, g, b, a = tint
    px, py, pz = pivot if pivot is not None else center

    for face_idx, (norm, corners) in enumerate(_CUBE_FACES):
        tid = float(tids[face_idx])
        if rot_mat is not None:
            n_vec = rot_mat @ np.array(norm, dtype=np.float32)
            nx, ny, nz = float(n_vec[0]), float(n_vec[1]), float(n_vec[2])
        else:
            nx, ny, nz = norm

        world_corners: list[tuple[float, float, float]] = []
        for lx, ly, lz in corners:
            wx = cx + lx * sx
            wy = cy + ly * sy
            wz = cz + lz * sz
            if rot_mat is not None:
                rel = np.array([wx - px, wy - py, wz - pz], dtype=np.float32)
                rot_p = rot_mat @ rel
                wx, wy, wz = px + float(rot_p[0]), py + float(rot_p[1]), pz + float(rot_p[2])
            world_corners.append((wx, wy, wz))

        for idx in _QUAD_TRI_INDICES:
            vx, vy, vz = world_corners[idx]
            u, v = _FACE_UVS[idx]
            out_list.extend((vx, vy, vz, nx, ny, nz, u, v, tid, r, g, b, a))


# ==============================================================================
# 4. NATIVE OPENGL 3.3 VOXEL SCENE RENDERER
# ==============================================================================

class VoxelOpenGLRenderer:
    """Hardware-accelerated OpenGL 3.3 Core renderer for Bloxorz: Voxel Edition.

    Implements:
    - Parametric Circle Arc rolling kinematics (0.16s, Quadratic Out easing) for the Oak Log.
    - Full support for split blocks (two 1x1x1 cubes rolling independently).
    - Squash & Stretch bounce upon landing.
    - Free-fall tumbling & camera shake on void/fragile fall.
    - End Portal sink & 3D voxel fireworks burst on victory.
    - Hinged Oak Trapdoor bridges & depressing pressure plates.
    - 3 atmospheric biomes (Overworld, Nether, The End) with smooth transitions.
    - Crisp Minecraft Inventory HUD overlay rendered via a 2D textured quad.
    """

    ROLL_DURATION = 0.16
    BOUNCE_DURATION = 0.13

    def __init__(self) -> None:
        self.stage: Any = None
        self.state: Any = None
        self.camera = TwoNodeGimbalCamera()
        self.textures = VoxelTextureCatalog()
        self.hud_renderer = MinecraftHUDRenderer()

        self.active_biome: str = "overworld"
        self._curr_sky = np.array(BIOME_PRESETS["overworld"]["sky"], dtype=np.float32)
        self._curr_fog = np.array(BIOME_PRESETS["overworld"]["fog_color"], dtype=np.float32)
        self._curr_fog_density = float(BIOME_PRESETS["overworld"]["fog_density"])
        self._curr_sun_dir = np.array(BIOME_PRESETS["overworld"]["sun_dir"], dtype=np.float32)
        self._curr_sun_col = np.array(BIOME_PRESETS["overworld"]["sun_color"], dtype=np.float32)
        self._curr_amb_sky = np.array(BIOME_PRESETS["overworld"]["ambient_sky"], dtype=np.float32)
        self._curr_amb_gnd = np.array(BIOME_PRESETS["overworld"]["ambient_ground"], dtype=np.float32)

        # Animation states: "idle" | "roll" | "fall" | "win"
        self.anim_mode: str = "idle"
        self.anim_timer: float = 0.0
        self.bounce_timer: float = 0.0

        # Rolling kinematics state
        self.roll_old_state: Any = None
        self.roll_action: Any = None
        self.roll_new_state: Any = None

        # Fall physics state
        self.fall_details: dict | None = None
        self.fall_pos = np.zeros(3, dtype=np.float32)
        self.fall_vel = np.zeros(3, dtype=np.float32)
        self.fall_axis: tuple[float, float, float] = (1.0, 0.0, 0.0)
        self.fall_angle: float = 0.0
        self.fall_base_rot = np.eye(3, dtype=np.float32)
        self.fall_unit_offsets: list[np.ndarray] = []

        # Trapdoor bridge smooth hinge angles: (x, z) -> radians (0 = closed, -1.52 = open)
        self.bridge_angles: dict[tuple[int, int], float] = {}

        # Dynamic 3D Voxel Particles
        self.particles: list[dict] = []
        self.clouds: list[dict] = self._init_clouds()
        self.ambient_motes: list[dict] = self._init_ambient_motes()

        # HUD state & caching
        self.viewport_w: int = 1280
        self.viewport_h: int = 760
        self.stage_index: int = 0
        self.total_stages: int = 1
        self.move_count: int = 0
        self.optimal_moves: int | None = None
        self.ai_status: str | None = None
        self.banner_title: str | None = None
        self.banner_subtitle: str | None = None
        self.banner_color: tuple[int, int, int] = (255, 255, 255)
        self.hover_btn_id: str | None = None
        self._hud_dirty: bool = True

        # Fragile sand shattered cells
        self.broken_fragile_cells: set[tuple[int, int]] = set()

        # OpenGL Core state & resources
        self.gl: GLCore | None = None
        self.voxel_prog: int = 0
        self.hud_prog: int = 0
        self.vao_voxel: int = 0
        self.vbo_voxel: int = 0
        self.vao_hud: int = 0
        self.vbo_hud: int = 0
        self.tex_atlas_gl: int = 0
        self.tex_hud_gl: int = 0
        self.start_time: float = time.perf_counter()

    def is_animating(self) -> bool:
        return self.anim_mode != "idle"

    @staticmethod
    def _init_clouds() -> list[dict]:
        rng = random.Random(42)
        clouds = []
        for _ in range(16):
            clouds.append(
                {
                    "pos": np.array(
                        [rng.uniform(-35.0, 45.0), rng.uniform(8.5, 14.0), rng.uniform(-35.0, 45.0)],
                        dtype=np.float32,
                    ),
                    "size": (
                        rng.uniform(4.5, 12.0),
                        rng.uniform(1.2, 2.4),
                        rng.uniform(3.5, 8.0),
                    ),
                    "speed": rng.uniform(0.45, 1.2),
                }
            )
        return clouds

    @staticmethod
    def _init_ambient_motes() -> list[dict]:
        rng = random.Random(1337)
        motes = []
        for _ in range(48):
            motes.append(
                {
                    "pos": np.array(
                        [rng.uniform(-10.0, 20.0), rng.uniform(0.2, 7.5), rng.uniform(-10.0, 20.0)],
                        dtype=np.float32,
                    ),
                    "phase": rng.uniform(0.0, 6.28),
                    "speed": rng.uniform(0.2, 0.7),
                    "size": rng.uniform(0.06, 0.12),
                }
            )
        return motes

    def init_gl(self) -> None:
        """Compile GLSL 330 core shaders, allocate VAO/VBOs, and upload textures."""
        self.gl = GLCore()
        gl = self.gl

        gl.lib.glEnable(GLCore.GL_DEPTH_TEST)
        gl.lib.glDepthFunc(GLCore.GL_LEQUAL)
        gl.lib.glEnable(GLCore.GL_CULL_FACE)
        gl.lib.glEnable(GLCore.GL_BLEND)
        gl.lib.glBlendFunc(GLCore.GL_SRC_ALPHA, GLCore.GL_ONE_MINUS_SRC_ALPHA)

        # 1. Compile 3D Voxel Shader Program
        vs = gl.compile_shader(GLCore.GL_VERTEX_SHADER, VOXEL_VERTEX_SHADER)
        fs = gl.compile_shader(GLCore.GL_FRAGMENT_SHADER, VOXEL_FRAGMENT_SHADER)
        self.voxel_prog = gl.link_program(vs, fs)
        gl.lib.glDeleteShader(vs)
        gl.lib.glDeleteShader(fs)

        # 2. Compile 2D HUD Shader Program
        h_vs = gl.compile_shader(GLCore.GL_VERTEX_SHADER, HUD_VERTEX_SHADER)
        h_fs = gl.compile_shader(GLCore.GL_FRAGMENT_SHADER, HUD_FRAGMENT_SHADER)
        self.hud_prog = gl.link_program(h_vs, h_fs)
        gl.lib.glDeleteShader(h_vs)
        gl.lib.glDeleteShader(h_fs)

        # 3. Allocate Voxel VAO & Dynamic VBO (13 floats per vertex)
        vao = (c_uint * 1)()
        vbo = (c_uint * 1)()
        gl.lib.glGenVertexArrays(1, vao)
        gl.lib.glGenBuffers(1, vbo)
        self.vao_voxel = vao[0]
        self.vbo_voxel = vbo[0]

        gl.lib.glBindVertexArray(self.vao_voxel)
        gl.lib.glBindBuffer(GLCore.GL_ARRAY_BUFFER, self.vbo_voxel)

        stride = 13 * 4
        # layout(location = 0) in vec3 a_pos
        gl.lib.glEnableVertexAttribArray(0)
        gl.lib.glVertexAttribPointer(0, 3, GLCore.GL_FLOAT, GLCore.GL_FALSE, stride, c_void_p(0))
        # layout(location = 1) in vec3 a_normal
        gl.lib.glEnableVertexAttribArray(1)
        gl.lib.glVertexAttribPointer(1, 3, GLCore.GL_FLOAT, GLCore.GL_FALSE, stride, c_void_p(3 * 4))
        # layout(location = 2) in vec2 a_uv
        gl.lib.glEnableVertexAttribArray(2)
        gl.lib.glVertexAttribPointer(2, 2, GLCore.GL_FLOAT, GLCore.GL_FALSE, stride, c_void_p(6 * 4))
        # layout(location = 3) in float a_tex_id
        gl.lib.glEnableVertexAttribArray(3)
        gl.lib.glVertexAttribPointer(3, 1, GLCore.GL_FLOAT, GLCore.GL_FALSE, stride, c_void_p(8 * 4))
        # layout(location = 4) in vec4 a_tint
        gl.lib.glEnableVertexAttribArray(4)
        gl.lib.glVertexAttribPointer(4, 4, GLCore.GL_FLOAT, GLCore.GL_FALSE, stride, c_void_p(9 * 4))

        # 4. Allocate HUD VAO & Dynamic VBO (4 floats: pos2 + uv2)
        gl.lib.glGenVertexArrays(1, vao)
        gl.lib.glGenBuffers(1, vbo)
        self.vao_hud = vao[0]
        self.vbo_hud = vbo[0]

        gl.lib.glBindVertexArray(self.vao_hud)
        gl.lib.glBindBuffer(GLCore.GL_ARRAY_BUFFER, self.vbo_hud)
        gl.lib.glEnableVertexAttribArray(0)
        gl.lib.glVertexAttribPointer(0, 2, GLCore.GL_FLOAT, GLCore.GL_FALSE, 4 * 4, c_void_p(0))
        gl.lib.glEnableVertexAttribArray(1)
        gl.lib.glVertexAttribPointer(1, 2, GLCore.GL_FLOAT, GLCore.GL_FALSE, 4 * 4, c_void_p(2 * 4))

        # 5. Upload Atlas Texture (GL_NEAREST for sharp Minecraft pixel art)
        tex = (c_uint * 1)()
        gl.lib.glGenTextures(1, tex)
        self.tex_atlas_gl = tex[0]
        gl.lib.glBindTexture(GLCore.GL_TEXTURE_2D, self.tex_atlas_gl)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_MAG_FILTER, GLCore.GL_NEAREST)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_MIN_FILTER, GLCore.GL_NEAREST)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_WRAP_S, GLCore.GL_CLAMP_TO_EDGE)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_WRAP_T, GLCore.GL_CLAMP_TO_EDGE)

        atlas_data = self.textures.atlas_array
        h, w, _ = atlas_data.shape
        gl.lib.glTexImage2D(
            GLCore.GL_TEXTURE_2D,
            0,
            GLCore.GL_RGBA8,
            w,
            h,
            0,
            GLCore.GL_RGBA,
            GLCore.GL_UNSIGNED_BYTE,
            atlas_data.ctypes.data_as(c_void_p),
        )

        # 6. Allocate Dynamic HUD Texture
        gl.lib.glGenTextures(1, tex)
        self.tex_hud_gl = tex[0]
        gl.lib.glBindTexture(GLCore.GL_TEXTURE_2D, self.tex_hud_gl)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_MAG_FILTER, GLCore.GL_NEAREST)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_MIN_FILTER, GLCore.GL_NEAREST)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_WRAP_S, GLCore.GL_CLAMP_TO_EDGE)
        gl.lib.glTexParameteri(GLCore.GL_TEXTURE_2D, GLCore.GL_TEXTURE_WRAP_T, GLCore.GL_CLAMP_TO_EDGE)

        gl.lib.glBindVertexArray(0)

    def _compute_camera_focus(self, state: Any) -> np.ndarray:
        cx, _, cz = self._state_world_center(state)
        if self.stage is not None:
            stage_w = getattr(self.stage, "cols", getattr(self.stage, "width", 0))
            stage_h = getattr(self.stage, "rows", getattr(self.stage, "height", 0))
            mid_x = (stage_w - 1) * 0.5
            mid_z = (stage_h - 1) * 0.5
            fx = 0.55 * cx + 0.45 * mid_x
            fz = 0.55 * cz + 0.45 * mid_z
            return np.array([fx, 0.25, fz], dtype=np.float32)
        return np.array([cx, 0.25, cz], dtype=np.float32)

    def set_stage_and_state(self, stage: Any, state: Any) -> None:
        self.stage = stage
        self.state = state
        self.active_biome = getattr(stage, "biome", "overworld")
        if self.active_biome not in BIOME_PRESETS:
            self.active_biome = "overworld"
        self.anim_mode = "idle"
        self.anim_timer = 0.0
        self.bounce_timer = 0.0
        self.broken_fragile_cells.clear()
        self.particles.clear()
        self.banner_title = None
        self.banner_subtitle = None

        stage_w = getattr(stage, "cols", getattr(stage, "width", 0))
        stage_h = getattr(stage, "rows", getattr(stage, "height", 0))

        # Initialize trapdoor bridge angles
        self.bridge_angles.clear()
        for z in range(stage_h):
            for x in range(stage_w):
                is_bridge = False
                if hasattr(stage, "cell"):
                    is_bridge = (stage.cell((z, x)) == "B")
                elif hasattr(stage, "get_tile"):
                    tile = stage.get_tile(x, z)
                    is_bridge = (str(tile) == "B" or getattr(tile, "name", "") == "BRIDGE")
                if is_bridge:
                    is_open = False
                    if hasattr(stage, "bridge_at") and hasattr(state, "bridges_open"):
                        b_id = stage.bridge_at.get((z, x))
                        is_open = (b_id in state.bridges_open)
                    elif hasattr(state, "bridges"):
                        is_open = (x, z) in state.bridges
                    self.bridge_angles[(x, z)] = 0.0 if is_open else -1.52

        span = max(stage_w, stage_h)
        self.camera.target_distance = max(12.5, min(22.0, span * 1.15))
        self.camera.desired_target = self._compute_camera_focus(state)
        self.camera.target = self.camera.desired_target.copy()
        self._hud_dirty = True

    def set_biome(self, biome_name: str) -> None:
        if biome_name in BIOME_PRESETS:
            self.active_biome = biome_name
            self._hud_dirty = True

    def start_roll(self, old_state: Any, action: Any, new_state: Any) -> None:
        self.roll_old_state = old_state
        self.roll_action = action
        self.roll_new_state = new_state
        self.state = new_state
        self.anim_mode = "roll"
        self.anim_timer = 0.0
        self.bounce_timer = 0.0
        self.banner_title = None
        self.camera.desired_target = self._compute_camera_focus(new_state)
        self._hud_dirty = True

    def start_fall(self, old_state: Any, action: Any) -> None:
        if self.stage is None:
            return
        self.roll_old_state = old_state
        self.roll_action = action
        self.fall_details = inspect_fall_details(self.stage, old_state, action)
        self.anim_mode = "fall"
        self.anim_timer = 0.0
        self.banner_title = "FELL INTO THE ABYSS!"
        self.banner_subtitle = "Press [R] to Restart or [U] to Undo"
        self.banner_color = (248, 113, 113)
        self._hud_dirty = True

    def start_win(self, state: Any) -> None:
        self.state = state
        self.anim_mode = "win"
        self.anim_timer = 0.0
        self.banner_title = "STAGE COMPLETE!"
        self.banner_subtitle = "Press [Next >] or [N] for the next stage"
        self.banner_color = (74, 222, 128)
        self._hud_dirty = True
        if hasattr(state, "pos"):
            r, c = state.pos
            self._spawn_victory_fireworks(float(c), float(r))
        elif hasattr(state, "x") and hasattr(state, "z"):
            self._spawn_victory_fireworks(float(state.x), float(state.z))

    def _spawn_victory_fireworks(self, gx: float, gz: float) -> None:
        rng = random.Random()
        palette = [
            (0.25, 0.95, 1.0, 1.0),
            (0.85, 0.35, 1.0, 1.0),
            (1.0, 0.88, 0.25, 1.0),
            (0.30, 0.98, 0.55, 1.0),
        ]
        for _ in range(56):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            speed_h = rng.uniform(1.4, 4.6)
            vy = rng.uniform(4.5, 9.2)
            self.particles.append(
                {
                    "pos": np.array([float(gx), 0.35, float(gz)], dtype=np.float32),
                    "vel": np.array(
                        [math.cos(angle) * speed_h, vy, math.sin(angle) * speed_h],
                        dtype=np.float32,
                    ),
                    "size": rng.uniform(0.11, 0.20),
                    "color": rng.choice(palette),
                    "life": rng.uniform(0.85, 1.55),
                    "max_life": 1.55,
                    "gravity": 12.5,
                }
            )

    def _spawn_fragile_shatter(self, fx: int, fz: int) -> None:
        if (fx, fz) in self.broken_fragile_cells:
            return
        self.broken_fragile_cells.add((fx, fz))
        rng = random.Random()
        sand_palette = [
            (0.88, 0.77, 0.52, 1.0),
            (0.82, 0.71, 0.46, 1.0),
            (0.74, 0.63, 0.39, 1.0),
            (0.92, 0.82, 0.58, 1.0),
        ]
        for _ in range(36):
            angle = rng.uniform(0.0, 2.0 * math.pi)
            speed_h = rng.uniform(0.8, 3.2)
            vy = rng.uniform(2.5, 6.5)
            self.particles.append(
                {
                    "pos": np.array(
                        [float(fx) + rng.uniform(-0.4, 0.4), -0.05, float(fz) + rng.uniform(-0.4, 0.4)],
                        dtype=np.float32,
                    ),
                    "vel": np.array(
                        [math.cos(angle) * speed_h, vy, math.sin(angle) * speed_h],
                        dtype=np.float32,
                    ),
                    "size": rng.uniform(0.07, 0.14),
                    "color": rng.choice(sand_palette),
                    "life": rng.uniform(0.55, 1.15),
                    "max_life": 1.15,
                    "gravity": 18.0,
                }
            )

    @staticmethod
    def _state_unit_centers_and_rot(state: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if state is None:
            ca = np.zeros(3, dtype=np.float32)
            cb = np.zeros(3, dtype=np.float32)
            rot = np.eye(3, dtype=np.float32)
            return ca, cb, rot

        if getattr(state, "pose", None) is None and getattr(state, "cube2", None) is not None:
            r0, c0 = state.pos
            r1, c1 = state.cube2
            ca = np.array([float(c0), 0.5, float(r0)], dtype=np.float32)
            cb = np.array([float(c1), 0.5, float(r1)], dtype=np.float32)
            rot = np.eye(3, dtype=np.float32)
            return ca, cb, rot

        if hasattr(state, "pos"):
            r, c = state.pos
            x, z = float(c), float(r)
        else:
            x, z = float(state.x), float(state.z)

        p_str = str(state.pose).upper()
        if "STANDING" in p_str:
            ca = np.array([x, 0.5, z], dtype=np.float32)
            cb = np.array([x, 1.5, z], dtype=np.float32)
            rot = np.eye(3, dtype=np.float32)
            return ca, cb, rot

        if "HORIZONTAL" in p_str or "LYING_X" in p_str:
            ca = np.array([x, 0.5, z], dtype=np.float32)
            cb = np.array([x + 1.0, 0.5, z], dtype=np.float32)
            rot = rodrigues_rotation_3x3((0.0, 0.0, -1.0), math.pi * 0.5)
            return ca, cb, rot

        # VERTICAL / LYING_Z
        ca = np.array([x, 0.5, z], dtype=np.float32)
        cb = np.array([x, 0.5, z + 1.0], dtype=np.float32)
        rot = rodrigues_rotation_3x3((1.0, 0.0, 0.0), math.pi * 0.5)
        return ca, cb, rot

    @classmethod
    def _state_world_center(cls, state: Any) -> tuple[float, float, float]:
        ca, cb, _ = cls._state_unit_centers_and_rot(state)
        mid = 0.5 * (ca + cb)
        return float(mid[0]), float(mid[1]), float(mid[2])

    @classmethod
    def compute_parametric_arc_pose(
        cls, old_state: Any, action: Any, progress_t: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        t = max(0.0, min(1.0, progress_t))
        u = 1.0 - (1.0 - t) * (1.0 - t)

        dx, dz = get_action_delta(action)

        if getattr(old_state, "pose", None) is None and getattr(old_state, "cube2", None) is not None:
            cube_idx = getattr(action, "cube", 0)
            moving_pos = old_state.pos if cube_idx == 0 else old_state.cube2
            still_pos = old_state.cube2 if cube_idx == 0 else old_state.pos
            r_m, c_m = moving_pos
            r_s, c_s = still_pos

            c_moving0 = np.array([float(c_m), 0.5, float(r_m)], dtype=np.float32)
            c_still = np.array([float(c_s), 0.5, float(r_s)], dtype=np.float32)

            px = float(c_m) + 0.5 * dx
            pz = float(r_m) + 0.5 * dz
            pivot = np.array([px, 0.0, pz], dtype=np.float32)
            axis = (float(dz), 0.0, float(-dx))
            theta = u * (math.pi * 0.5)
            arc_rot = rodrigues_rotation_3x3(axis, theta)

            c_moving = pivot + arc_rot @ (c_moving0 - pivot)
            if cube_idx == 0:
                return c_moving, c_still, arc_rot
            else:
                return c_still, c_moving, arc_rot

        ca0, cb0, base_rot0 = cls._state_unit_centers_and_rot(old_state)
        cells = get_occupied_cells_list(old_state)

        if not cells:
            return ca0, cb0, base_rot0

        if dx == 1:
            px = max(cx for cx, _ in cells) + 0.5
            pz = sum(cz for _, cz in cells) / len(cells)
        elif dx == -1:
            px = min(cx for cx, _ in cells) - 0.5
            pz = sum(cz for _, cz in cells) / len(cells)
        elif dz == 1:
            px = sum(cx for cx, _ in cells) / len(cells)
            pz = max(cz for _, cz in cells) + 0.5
        else:
            px = sum(cx for cx, _ in cells) / len(cells)
            pz = min(cz for _, cz in cells) - 0.5

        pivot = np.array([px, 0.0, pz], dtype=np.float32)
        axis = (float(dz), 0.0, float(-dx))
        theta = u * (math.pi * 0.5)
        arc_rot = rodrigues_rotation_3x3(axis, theta)

        ca = pivot + arc_rot @ (ca0 - pivot)
        cb = pivot + arc_rot @ (cb0 - pivot)
        rot = arc_rot @ base_rot0
        return ca, cb, rot

    def update(self, dt: float) -> None:
        dt = min(dt, 0.05)
        self.camera.update(dt)

        # 1. Smoothly interpolate Biome lighting & fog uniforms
        preset = BIOME_PRESETS.get(self.active_biome, BIOME_PRESETS["overworld"])
        lerp_k = 1.0 - math.exp(-4.5 * dt)
        self._curr_sky += (np.array(preset["sky"], dtype=np.float32) - self._curr_sky) * lerp_k
        self._curr_fog += (np.array(preset["fog_color"], dtype=np.float32) - self._curr_fog) * lerp_k
        self._curr_fog_density += (float(preset["fog_density"]) - self._curr_fog_density) * lerp_k
        self._curr_sun_dir += (np.array(preset["sun_dir"], dtype=np.float32) - self._curr_sun_dir) * lerp_k
        self._curr_sun_col += (np.array(preset["sun_color"], dtype=np.float32) - self._curr_sun_col) * lerp_k
        self._curr_amb_sky += (np.array(preset["ambient_sky"], dtype=np.float32) - self._curr_amb_sky) * lerp_k
        self._curr_amb_gnd += (np.array(preset["ambient_ground"], dtype=np.float32) - self._curr_amb_gnd) * lerp_k

        # 2. Update Trapdoor Bridge Hinge Angles
        if self.stage is not None and self.state is not None:
            for (x, z), curr_ang in list(self.bridge_angles.items()):
                is_open = False
                if hasattr(self.stage, "bridge_at") and hasattr(self.state, "bridges_open"):
                    b_id = self.stage.bridge_at.get((z, x))
                    is_open = (b_id in self.state.bridges_open)
                elif hasattr(self.state, "bridges"):
                    is_open = (x, z) in self.state.bridges
                target_ang = 0.0 if is_open else -1.52
                self.bridge_angles[(x, z)] = curr_ang + (target_ang - curr_ang) * min(1.0, dt * 14.0)

        # 3. Update Block Rolling / Squash-Bounce / Falling / Victory Animations
        if self.anim_mode == "roll":
            self.anim_timer += dt
            if self.anim_timer >= self.ROLL_DURATION:
                self.anim_mode = "idle"
                self.anim_timer = 0.0
                self.bounce_timer = self.BOUNCE_DURATION
        elif self.anim_mode == "idle" and self.bounce_timer > 0.0:
            self.bounce_timer = max(0.0, self.bounce_timer - dt)
        elif self.anim_mode == "fall":
            prev_timer = self.anim_timer
            self.anim_timer += dt
            if prev_timer <= self.ROLL_DURATION and self.anim_timer > self.ROLL_DURATION:
                ca, cb, rot = self.compute_parametric_arc_pose(
                    self.roll_old_state, self.roll_action, 1.0
                )
                mid = 0.5 * (ca + cb)
                self.fall_pos = mid.copy()
                dx, dz = get_action_delta(self.roll_action)
                self.fall_vel = np.array([dx * 2.4, -1.2, dz * 2.4], dtype=np.float32)
                self.fall_axis = (float(dz), 0.25, float(-dx))
                self.fall_angle = 0.0
                self.fall_base_rot = rot
                self.fall_unit_offsets = [ca - mid, cb - mid]
                self.camera.trigger_shake(0.38, 0.45)
                if self.fall_details and self.fall_details.get("fragile_cell"):
                    fx, fz = self.fall_details["fragile_cell"]
                    self._spawn_fragile_shatter(fx, fz)
            elif self.anim_timer > self.ROLL_DURATION:
                self.fall_vel[1] -= 26.0 * dt
                self.fall_pos += self.fall_vel * dt
                self.fall_angle += 7.5 * dt
        elif self.anim_mode == "win":
            self.anim_timer += dt

        # 4. Update Particles & Drifting Voxel Clouds
        alive: list[dict] = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["vel"][1] -= p["gravity"] * dt
                p["pos"] += p["vel"] * dt
                alive.append(p)
        self.particles = alive

        for c in self.clouds:
            c["pos"][0] += c["speed"] * dt
            if c["pos"][0] > 48.0:
                c["pos"][0] = -42.0

        for m in self.ambient_motes:
            m["phase"] += m["speed"] * dt
            m["pos"][1] += math.sin(m["phase"]) * 0.15 * dt

    def _build_frame_vertices(
        self, elapsed: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Build the vertex array for all 3D voxels in the current frame."""
        verts: list[float] = []
        T = VoxelTextureCatalog
        zero3 = np.zeros(3, dtype=np.float32)
        eye3 = np.eye(3, dtype=np.float32)
        if self.stage is None or self.state is None:
            return np.zeros((0, 13), dtype=np.float32), zero3, zero3, zero3, eye3

        occupied_now = set(get_occupied_cells_list(self.state)) if self.anim_mode == "idle" else set()
        stage_w = getattr(self.stage, "cols", getattr(self.stage, "width", 0))
        stage_h = getattr(self.stage, "rows", getattr(self.stage, "height", 0))

        # 1. Stage Platform Tiles
        for z in range(stage_h):
            for x in range(stage_w):
                if hasattr(self.stage, "cell"):
                    ch = self.stage.cell((z, x))
                elif hasattr(self.stage, "get_tile"):
                    tile = self.stage.get_tile(x, z)
                    ch = getattr(tile, "value", str(tile))
                else:
                    ch = "."

                if ch in (".", " "):
                    continue
                if (ch in ("F", "f")) and (x, z) in self.broken_fragile_cells:
                    continue

                if ch == "B":
                    # Hinged Oak Trapdoor Bridge
                    ang = self.bridge_angles.get((x, z), 0.0)
                    rot_m = rodrigues_rotation_3x3((0.0, 0.0, -1.0), ang)
                    append_box_vertices(
                        verts,
                        center=(float(x), -0.09, float(z)),
                        size=(0.96, 0.18, 0.96),
                        tex_ids_per_face=T.TEX_OAK_TRAPDOOR,
                        rot_mat=rot_m,
                        pivot=(float(x) - 0.48, 0.0, float(z)),
                    )
                    continue

                if ch == "G" or (hasattr(self.stage, "goal") and (z, x) == self.stage.goal):
                    # End Portal Frame with recessed cosmic well
                    wall_h = 0.34
                    wall_t = 0.18
                    frame_faces = (
                        T.TEX_END_FRAME_TOP,
                        T.TEX_STONE_BRICKS,
                        T.TEX_END_FRAME_TOP,
                        T.TEX_END_FRAME_TOP,
                        T.TEX_END_FRAME_TOP,
                        T.TEX_END_FRAME_TOP,
                    )
                    append_box_vertices(
                        verts,
                        (float(x), -wall_h * 0.5, float(z) - 0.5 + wall_t * 0.5),
                        (1.0, wall_h, wall_t),
                        frame_faces,
                    )
                    append_box_vertices(
                        verts,
                        (float(x), -wall_h * 0.5, float(z) + 0.5 - wall_t * 0.5),
                        (1.0, wall_h, wall_t),
                        frame_faces,
                    )
                    append_box_vertices(
                        verts,
                        (float(x) - 0.5 + wall_t * 0.5, -wall_h * 0.5, float(z)),
                        (wall_t, wall_h, 1.0 - 2.0 * wall_t),
                        frame_faces,
                    )
                    append_box_vertices(
                        verts,
                        (float(x) + 0.5 - wall_t * 0.5, -wall_h * 0.5, float(z)),
                        (wall_t, wall_h, 1.0 - 2.0 * wall_t),
                        frame_faces,
                    )
                    append_box_vertices(
                        verts,
                        (float(x), -0.26, float(z)),
                        (0.76, 0.10, 0.76),
                        T.TEX_END_PORTAL_CORE,
                    )
                    continue

                # Standard solid platform block
                if ch == "S" or (hasattr(self.stage, "start") and (z, x) == self.stage.start):
                    tid = T.TEX_CRYING_OBSIDIAN
                elif ch in ("F", "f"):
                    tid = T.TEX_FRAGILE_SAND
                else:
                    tid = T.TEX_STONE_BRICKS

                append_box_vertices(
                    verts,
                    center=(float(x), -0.19, float(z)),
                    size=(0.98, 0.38, 0.98),
                    tex_ids_per_face=tid,
                )

                # Elevated Pressure Plates ('o' Soft, 'x' Heavy, split)
                sw = getattr(self.stage, "switch_at", {}).get((z, x)) if hasattr(self.stage, "switch_at") else None
                if sw is not None or ch in ("o", "x"):
                    is_soft = (sw.kind == "soft") if sw else (ch == "o")
                    is_standing = self.state and getattr(self.state, "pose", None) and "STANDING" in str(self.state.pose).upper()
                    is_depressed = (x, z) in occupied_now and (is_soft or is_standing)
                    plate_h = 0.022 if is_depressed else 0.045
                    plate_tid = T.TEX_PLATE_SOFT if is_soft else T.TEX_PLATE_HEAVY
                    append_box_vertices(
                        verts,
                        center=(float(x), plate_h * 0.5, float(z)),
                        size=(0.74, plate_h, 0.74),
                        tex_ids_per_face=plate_tid,
                    )

        # 2. Player 1x1x2 Oak Log Block
        oak_faces = (
            T.TEX_OAK_TOP,
            T.TEX_OAK_TOP,
            T.TEX_OAK_BARK,
            T.TEX_OAK_BARK,
            T.TEX_OAK_BARK,
            T.TEX_OAK_BARK,
        )

        block_center = np.array(self._state_world_center(self.state), dtype=np.float32)

        if self.anim_mode == "roll" and self.roll_old_state and self.roll_action:
            progress = min(1.0, self.anim_timer / self.ROLL_DURATION)
            ca, cb, rot = self.compute_parametric_arc_pose(
                self.roll_old_state, self.roll_action, progress
            )
            block_center = 0.5 * (ca + cb)
            for c_pos in (ca, cb):
                append_box_vertices(
                    verts,
                    center=(float(c_pos[0]), float(c_pos[1]), float(c_pos[2])),
                    size=(0.98, 0.98, 0.98),
                    tex_ids_per_face=oak_faces,
                    rot_mat=rot,
                )
        elif self.anim_mode == "fall" and self.roll_old_state and self.roll_action:
            if self.anim_timer <= self.ROLL_DURATION:
                progress = self.anim_timer / self.ROLL_DURATION
                ca, cb, rot = self.compute_parametric_arc_pose(
                    self.roll_old_state, self.roll_action, progress
                )
                block_center = 0.5 * (ca + cb)
                for c_pos in (ca, cb):
                    append_box_vertices(
                        verts,
                        center=(float(c_pos[0]), float(c_pos[1]), float(c_pos[2])),
                        size=(0.98, 0.98, 0.98),
                        tex_ids_per_face=oak_faces,
                        rot_mat=rot,
                    )
            else:
                tumble_rot = rodrigues_rotation_3x3(self.fall_axis, self.fall_angle)
                total_rot = tumble_rot @ self.fall_base_rot
                block_center = self.fall_pos.copy()
                for offset in self.fall_unit_offsets:
                    c_pos = self.fall_pos + tumble_rot @ offset
                    append_box_vertices(
                        verts,
                        center=(float(c_pos[0]), float(c_pos[1]), float(c_pos[2])),
                        size=(0.98, 0.98, 0.98),
                        tex_ids_per_face=oak_faces,
                        rot_mat=total_rot,
                    )
        elif self.anim_mode == "win":
            ca, cb, rot = self._state_unit_centers_and_rot(self.state)
            sink_t = min(1.0, self.anim_timer / 0.85)
            sink_y = -1.65 * (sink_t * sink_t)
            spin_rot = rodrigues_rotation_3x3((0.0, 1.0, 0.0), self.anim_timer * 5.0) @ rot
            scale = max(0.15, 1.0 - sink_t * 0.72)
            for c_pos in (ca, cb):
                append_box_vertices(
                    verts,
                    center=(float(c_pos[0]), float(c_pos[1]) + sink_y, float(c_pos[2])),
                    size=(0.98 * scale, 0.98 * scale, 0.98 * scale),
                    tex_ids_per_face=oak_faces,
                    rot_mat=spin_rot,
                )
        else:
            # Idle + Post-Landing Squash & Stretch Bounce
            ca, cb, rot = self._state_unit_centers_and_rot(self.state)
            sx, sy, sz = 1.0, 1.0, 1.0
            if self.bounce_timer > 0.0:
                b = 1.0 - (self.bounce_timer / self.BOUNCE_DURATION)
                squash = math.sin(b * math.pi) * math.exp(-2.4 * b) * 0.14
                sy = 1.0 - squash
                sx = sz = 1.0 / math.sqrt(max(0.5, sy))

            for c_pos in (ca, cb):
                append_box_vertices(
                    verts,
                    center=(float(c_pos[0]), float(c_pos[1]) - (1.0 - sy) * 0.5, float(c_pos[2])),
                    size=(0.98 * sx, 0.98 * sy, 0.98 * sz),
                    tex_ids_per_face=oak_faces,
                    rot_mat=rot,
                )

        # 3. Dynamic 3D Voxel Particles
        for p in self.particles:
            append_box_vertices(
                verts,
                center=(float(p["pos"][0]), float(p["pos"][1]), float(p["pos"][2])),
                size=(p["size"], p["size"], p["size"]),
                tex_ids_per_face=T.TEX_CRYING_OBSIDIAN,
                tint=p["color"],
            )

        # 4. Volumetric Minecraft Voxel Clouds
        if self.active_biome == "overworld":
            for c in self.clouds:
                append_box_vertices(
                    verts,
                    center=(float(c["pos"][0]), float(c["pos"][1]), float(c["pos"][2])),
                    size=c["size"],
                    tex_ids_per_face=T.TEX_CLOUD,
                    tint=(1.0, 1.0, 1.0, 0.72),
                )

        # 5. Ambient Atmospheric Motes
        mote_color = (
            (1.0, 0.45, 0.2, 0.85) if self.active_biome == "nether" else (0.8, 0.45, 1.0, 0.85)
        )
        if self.active_biome in ("nether", "end"):
            for m in self.ambient_motes:
                append_box_vertices(
                    verts,
                    center=(float(m["pos"][0]), float(m["pos"][1]), float(m["pos"][2])),
                    size=(m["size"], m["size"], m["size"]),
                    tex_ids_per_face=T.TEX_CRYING_OBSIDIAN,
                    tint=mote_color,
                )

        arr = np.array(verts, dtype=np.float32).reshape(-1, 13)
        ca_ret, cb_ret, rot_ret = self._state_unit_centers_and_rot(self.state)
        return arr, block_center, ca_ret, cb_ret, rot_ret

    def render(self, width: int, height: int) -> None:
        """Render the complete frame (3D voxels + HUD overlay) into the current OpenGL framebuffer."""
        if self.gl is None:
            self.init_gl()
        gl = self.gl
        assert gl is not None

        self.viewport_w = width
        self.viewport_h = height
        gl.lib.glViewport(0, 0, width, height)

        # Clear background with interpolated biome sky color
        sr, sg, sb = self._curr_sky
        gl.lib.glClearColor(sr, sg, sb, 1.0)
        gl.lib.glClear(GLCore.GL_COLOR_BUFFER_BIT | GLCore.GL_DEPTH_BUFFER_BIT)

        now = time.perf_counter()
        elapsed = now - self.start_time

        # Build dynamic 3D voxel geometry
        v_data, blk_center, ca, cb, _ = self._build_frame_vertices(elapsed)
        num_verts = len(v_data)

        if num_verts > 0:
            gl.lib.glBindBuffer(GLCore.GL_ARRAY_BUFFER, self.vbo_voxel)
            gl.lib.glBufferData(
                GLCore.GL_ARRAY_BUFFER,
                v_data.nbytes,
                v_data.ctypes.data_as(c_void_p),
                GLCore.GL_DYNAMIC_DRAW,
            )

        # 1. Draw 3D Voxel Scene
        gl.lib.glEnable(GLCore.GL_DEPTH_TEST)
        gl.lib.glEnable(GLCore.GL_CULL_FACE)
        gl.lib.glUseProgram(self.voxel_prog)

        aspect = float(width) / max(float(height), 1.0)
        proj_m = perspective_matrix(48.0, aspect, 0.25, 120.0)
        eye, view_m = self.camera.compute_eye_and_view(elapsed)

        gl.set_uniform_mat4(self.voxel_prog, "u_proj", proj_m)
        gl.set_uniform_mat4(self.voxel_prog, "u_view", view_m)
        gl.set_uniform_1f(self.voxel_prog, "u_time", float(elapsed))
        gl.set_uniform_1f(self.voxel_prog, "u_num_textures", float(VoxelTextureCatalog.NUM_TEXTURES))

        sx, sy, sz = self._curr_sun_dir
        gl.set_uniform_3f(self.voxel_prog, "u_sun_dir", sx, sy, sz)
        cr, cg, cb_col = self._curr_sun_col
        gl.set_uniform_3f(self.voxel_prog, "u_sun_color", cr, cg, cb_col)
        ar, ag, ab = self._curr_amb_sky
        gl.set_uniform_3f(self.voxel_prog, "u_ambient_sky", ar, ag, ab)
        gr, gg, gb = self._curr_amb_gnd
        gl.set_uniform_3f(self.voxel_prog, "u_ambient_ground", gr, gg, gb)
        fr, fg, fb = self._curr_fog
        gl.set_uniform_3f(self.voxel_prog, "u_fog_color", fr, fg, fb)
        gl.set_uniform_1f(self.voxel_prog, "u_fog_density", float(self._curr_fog_density))

        gl.set_uniform_3f(self.voxel_prog, "u_cam_pos", float(eye[0]), float(eye[1]), float(eye[2]))
        gl.set_uniform_3f(
            self.voxel_prog,
            "u_block_center",
            float(blk_center[0]),
            float(blk_center[1]),
            float(blk_center[2]),
        )
        gl.set_uniform_3f(
            self.voxel_prog, "u_cube_a", float(ca[0]), float(ca[1]), float(ca[2])
        )
        gl.set_uniform_3f(
            self.voxel_prog, "u_cube_b", float(cb[0]), float(cb[1]), float(cb[2])
        )

        gl.lib.glActiveTexture(GLCore.GL_TEXTURE0)
        gl.lib.glBindTexture(GLCore.GL_TEXTURE_2D, self.tex_atlas_gl)
        gl.set_uniform_1i(self.voxel_prog, "u_atlas", 0)

        gl.lib.glBindVertexArray(self.vao_voxel)
        if num_verts > 0:
            gl.lib.glDrawArrays(GLCore.GL_TRIANGLES, 0, num_verts)

        # 2. Draw 2D Minecraft HUD Overlay (Textured Quad)
        if self._hud_dirty or True:
            stage_name = getattr(self.stage, "name", getattr(self.stage, "id", f"Stage {self.stage_index + 1}"))
            hud_arr = self.hud_renderer.render_hud_bitmap(
                width,
                height,
                stage_index=self.stage_index,
                total_stages=self.total_stages,
                stage_name=stage_name,
                moves=self.move_count,
                optimal_moves=self.optimal_moves,
                active_biome=self.active_biome,
                banner_title=self.banner_title,
                banner_subtitle=self.banner_subtitle,
                banner_color=self.banner_color,
                ai_status=self.ai_status,
                hover_id=self.hover_btn_id,
            )
            gl.lib.glBindTexture(GLCore.GL_TEXTURE_2D, self.tex_hud_gl)
            gl.lib.glTexImage2D(
                GLCore.GL_TEXTURE_2D,
                0,
                GLCore.GL_RGBA8,
                width,
                height,
                0,
                GLCore.GL_RGBA,
                GLCore.GL_UNSIGNED_BYTE,
                hud_arr.ctypes.data_as(c_void_p),
            )
            self._hud_dirty = False

        gl.lib.glDisable(GLCore.GL_DEPTH_TEST)
        gl.lib.glDisable(GLCore.GL_CULL_FACE)
        gl.lib.glUseProgram(self.hud_prog)

        hud_quad = np.array(
            [
                # pos2 (NDC: -1 to 1), uv2 (0 to 1)
                -1.0, -1.0, 0.0, 1.0,
                 1.0, -1.0, 1.0, 1.0,
                 1.0,  1.0, 1.0, 0.0,
                -1.0, -1.0, 0.0, 1.0,
                 1.0,  1.0, 1.0, 0.0,
                -1.0,  1.0, 0.0, 0.0,
            ],
            dtype=np.float32,
        )

        gl.lib.glBindBuffer(GLCore.GL_ARRAY_BUFFER, self.vbo_hud)
        gl.lib.glBufferData(
            GLCore.GL_ARRAY_BUFFER,
            hud_quad.nbytes,
            hud_quad.ctypes.data_as(c_void_p),
            GLCore.GL_DYNAMIC_DRAW,
        )

        gl.lib.glActiveTexture(GLCore.GL_TEXTURE0)
        gl.lib.glBindTexture(GLCore.GL_TEXTURE_2D, self.tex_hud_gl)
        gl.set_uniform_1i(self.hud_prog, "u_hud_tex", 0)

        gl.lib.glBindVertexArray(self.vao_hud)
        gl.lib.glDrawArrays(GLCore.GL_TRIANGLES, 0, 6)

        gl.lib.glBindVertexArray(0)
