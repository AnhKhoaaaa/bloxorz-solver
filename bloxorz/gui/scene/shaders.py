"""Custom GLSL 330 Core Shaders & Native OpenGL 3.3 Core Profile Binding."""
from __future__ import annotations

import ctypes
from ctypes import c_char_p, c_float, c_int, c_size_t, c_uint, c_void_p, POINTER
import numpy as np


# ==============================================================================
# 1. CUSTOM GLSL 330 CORE SHADERS (VOXEL 3D + COSMIC PORTAL + LAVA + BLOOM + AO)
# ==============================================================================

VOXEL_VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec3 a_pos;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;
layout(location = 3) in float a_tex_id;
layout(location = 4) in vec4 a_tint;

uniform mat4 u_proj;
uniform mat4 u_view;

out vec3 v_world_pos;
out vec3 v_normal;
out vec2 v_uv;
out float v_tex_id;
out vec4 v_tint;
out float v_view_dist;

void main() {
    v_world_pos = a_pos;
    v_normal = normalize(a_normal);
    v_uv = a_uv;
    v_tex_id = a_tex_id;
    v_tint = a_tint;

    vec4 view_pos = u_view * vec4(a_pos, 1.0);
    v_view_dist = length(view_pos.xyz);
    gl_Position = u_proj * view_pos;
}
"""

VOXEL_FRAGMENT_SHADER = """#version 330 core
in vec3 v_world_pos;
in vec3 v_normal;
in vec2 v_uv;
in float v_tex_id;
in vec4 v_tint;
in float v_view_dist;

uniform sampler2D u_atlas;
uniform float u_num_textures;
uniform float u_time;
uniform vec3 u_sun_dir;
uniform vec3 u_sun_color;
uniform vec3 u_ambient_sky;
uniform vec3 u_ambient_ground;
uniform vec3 u_fog_color;
uniform float u_fog_density;
uniform vec3 u_cam_pos;
uniform vec3 u_block_center;
uniform vec3 u_goal_pos;
uniform vec3 u_start_pos;

// Directional shadow uniforms for the player Oak Log (2x 1x1x1 units)
uniform vec3 u_unit_a_pos;
uniform vec3 u_unit_b_pos;
uniform mat3 u_block_rot;

out vec4 frag_color;

// Procedural 2D hash for cosmic portal stars & lava mosaic
float hash21(vec2 p) {
    p = fract(p * vec2(234.34, 435.345));
    p += dot(p, p + 34.23);
    return fract(p.x * p.y);
}

// Ray-AABB intersection for exact directional sunlight shadow casting
float ray_box_shadow(vec3 ray_orig, vec3 ray_dir, vec3 box_center, mat3 box_rot, vec3 box_half) {
    // Transform ray into box local space
    vec3 ro = transpose(box_rot) * (ray_orig - box_center);
    vec3 rd = transpose(box_rot) * ray_dir;

    vec3 inv_d = 1.0 / (rd + sign(rd) * 1e-6);
    vec3 t0 = (-box_half - ro) * inv_d;
    vec3 t1 = ( box_half - ro) * inv_d;

    vec3 tmin = min(t0, t1);
    vec3 tmax = max(t0, t1);

    float t_enter = max(max(tmin.x, tmin.y), tmin.z);
    float t_exit  = min(min(tmax.x, tmax.y), tmax.z);

    if (t_exit >= max(0.01, t_enter)) {
        return 0.42; // Shadow opacity (blocks 58% of sunlight)
    }
    return 0.0;
}

// Multi-layer trigonometric cosmic vortex for End Portal Core (tex_id == 5)
vec3 render_end_portal_cosmic(vec2 uv, vec3 world_pos, float t) {
    vec2 p = (uv - 0.5) * 2.2;
    float r = length(p);
    float angle = atan(p.y, p.x);

    float swirl1 = sin(angle * 3.0 - r * 7.5 + t * 2.8);
    float swirl2 = cos(angle * 5.0 + r * 9.0 - t * 2.1);
    float nebula = smoothstep(-0.4, 0.9, swirl1 * 0.55 + swirl2 * 0.45);

    vec3 deep_void = vec3(0.03, 0.01, 0.08);
    vec3 purple_nebula = vec3(0.58, 0.18, 0.92);
    vec3 cyan_core = vec3(0.15, 0.92, 0.98);

    vec3 col = mix(deep_void, purple_nebula, nebula * 0.75);
    col = mix(col, cyan_core, smoothstep(0.65, 0.0, r) * (0.55 + 0.35 * sin(t * 3.5)));

    for (int layer = 1; layer <= 3; layer++) {
        float fl = float(layer);
        float s = sin(t * 0.35 * fl);
        float c = cos(t * 0.35 * fl);
        mat2 rot = mat2(c, -s, s, c);
        vec2 st = rot * (world_pos.xz * (2.5 + fl * 1.8)) + vec2(t * 0.15 * fl, -t * 0.12 * fl);
        vec2 id = floor(st);
        vec2 gv = fract(st) - 0.5;
        float rnd = hash21(id + fl * 19.7);
        if (rnd > 0.72) {
            float star = smoothstep(0.28, 0.02, length(gv));
            float twinkle = 0.55 + 0.45 * sin(t * 5.0 + rnd * 62.8);
            vec3 star_col = (layer == 2) ? vec3(0.4, 0.98, 1.0) : vec3(0.92, 0.65, 1.0);
            col += star * twinkle * star_col * 1.35;
        }
    }
    return col;
}

// Authentic Minecraft Nether Lava Ocean with animated repeating magma cells (tex_id == 10)
vec3 render_animated_lava(vec2 uv, vec3 world_pos, float t) {
    vec2 p = world_pos.xz * 1.4;
    vec2 cell_id = floor(p);
    vec2 cell_uv = fract(p) - 0.5;

    float dist_center = length(cell_uv);
    float pulse = sin(t * 2.2 + dot(cell_id, vec2(1.7, 2.3))) * 0.5 + 0.5;
    float border = max(abs(cell_uv.x), abs(cell_uv.y));

    vec3 dark_crust = vec3(0.55, 0.08, 0.02);
    vec3 bright_magma = vec3(0.98, 0.42, 0.05);
    vec3 yellow_core = vec3(1.0, 0.88, 0.22);

    vec3 col = mix(dark_crust, bright_magma, smoothstep(0.46, 0.18, border));
    col = mix(col, yellow_core, smoothstep(0.24, 0.04, dist_center) * (0.65 + 0.35 * pulse));
    return col;
}

void main() {
    int tid = int(floor(v_tex_id + 0.5));
    vec4 tex_color = vec4(1.0);

    if (tid >= 0) {
        vec2 local_uv = clamp(fract(v_uv), 0.002, 0.998);
        float u_atlas_coord = (float(tid) + local_uv.x) / u_num_textures;
        tex_color = texture(u_atlas, vec2(u_atlas_coord, local_uv.y));
    }

    vec3 base_rgb = tex_color.rgb * v_tint.rgb;
    float alpha = tex_color.a * v_tint.a;

    float emissive = 0.0;
    if (tid == 5) {
        base_rgb = render_end_portal_cosmic(v_uv, v_world_pos, u_time);
        emissive = 1.25;
    } else if (tid == 10) {
        base_rgb = render_animated_lava(v_uv, v_world_pos, u_time);
        emissive = 0.95;
    } else if (tid == 3) {
        float is_tear = smoothstep(0.42, 0.75, base_rgb.r + base_rgb.b * 0.6);
        float pulse = 0.75 + 0.25 * sin(u_time * 3.4 + v_world_pos.x * 3.0 + v_world_pos.z * 3.0);
        emissive = is_tear * 0.95 * pulse;
        base_rgb += vec3(0.32, 0.06, 0.48) * emissive;
    } else if (tid == 4) {
        float is_teal = smoothstep(0.45, 0.85, base_rgb.g - base_rgb.r * 0.4);
        emissive = is_teal * 0.65;
    } else if (tid < 0) {
        emissive = 0.85;
    }

    // Voxel Edge Bevel & Inset Ambient Occlusion
    float edge_dist = min(min(v_uv.x, 1.0 - v_uv.x), min(v_uv.y, 1.0 - v_uv.y));
    float voxel_ao = smoothstep(0.0, 0.095, edge_dist);
    voxel_ao = mix(0.66, 1.0, voxel_ao);
    float edge_bevel = (1.0 - smoothstep(0.0, 0.055, edge_dist)) * max(0.0, v_normal.y * 0.5 + 0.5);

    // Directional Sunlight & Hemisphere Lighting
    vec3 N = normalize(v_normal);
    vec3 L = normalize(u_sun_dir);
    vec3 V = normalize(u_cam_pos - v_world_pos);
    vec3 H = normalize(L + V);

    float ndotl = max(dot(N, L), 0.0);
    float hemi_factor = N.y * 0.5 + 0.5;
    vec3 ambient = mix(u_ambient_ground, u_ambient_sky, hemi_factor);

    // Directional Geometric Shadow Mapping (cast by the player Oak Log along sunlight ray)
    float shadow_factor = 1.0;
    if (v_world_pos.y <= 0.08) {
        vec3 ray_orig = v_world_pos + N * 0.01;
        float sh_a = ray_box_shadow(ray_orig, L, u_unit_a_pos, u_block_rot, vec3(0.49));
        float sh_b = ray_box_shadow(ray_orig, L, u_unit_b_pos, u_block_rot, vec3(0.49));
        float total_shadow = max(sh_a, sh_b);

        // Soft ground contact shadow immediately under the block
        float dist_to_block = length(v_world_pos.xz - u_block_center.xz);
        float contact_shadow = smoothstep(1.15, 0.35, dist_to_block) * 0.35;
        total_shadow = max(total_shadow, contact_shadow);

        shadow_factor = 1.0 - total_shadow;
    }

    float spec = pow(max(dot(N, H), 0.0), 28.0) * 0.18 * ndotl;
    vec3 lit_rgb = base_rgb * (ambient + u_sun_color * ndotl * shadow_factor) * voxel_ao;
    lit_rgb += vec3(edge_bevel * 0.045);
    lit_rgb += vec3(spec);

    float dist_goal = length(v_world_pos - u_goal_pos);
    float goal_glow = exp(-dist_goal * 0.85) * (0.42 + 0.14 * sin(u_time * 3.0));
    lit_rgb += vec3(0.18, 0.85, 0.95) * goal_glow * 0.48;

    float dist_start = length(v_world_pos - u_start_pos);
    float start_glow = exp(-dist_start * 1.15) * (0.35 + 0.12 * cos(u_time * 2.6));
    lit_rgb += vec3(0.68, 0.18, 0.88) * start_glow * 0.35;

    vec3 final_rgb = mix(lit_rgb, base_rgb * 1.22, clamp(emissive, 0.0, 1.0));

    // Exponential Fog (FogExp2)
    float fog_factor = exp(-pow(v_view_dist * u_fog_density, 2.0));
    fog_factor = clamp(fog_factor, 0.0, 1.0);
    final_rgb = mix(u_fog_color, final_rgb, fog_factor);

    frag_color = vec4(final_rgb, alpha);
}
"""

HUD_VERTEX_SHADER = """#version 330 core
layout(location = 0) in vec2 a_pos;
layout(location = 1) in vec2 a_uv;

out vec2 v_uv;

void main() {
    v_uv = a_uv;
    gl_Position = vec4(a_pos, 0.0, 1.0);
}
"""

HUD_FRAGMENT_SHADER = """#version 330 core
in vec2 v_uv;
uniform sampler2D u_hud_tex;
out vec4 frag_color;

void main() {
    frag_color = texture(u_hud_tex, v_uv);
}
"""


# ==============================================================================
# 2. NATIVE OPENGL 3.3 CORE PROFILE C-API WRAPPER (LIBEPOXY / LIBGL)
# ==============================================================================

class GLCore:
    """Direct ctypes binding to OpenGL 3.3 Core Profile via `libepoxy.so.0` / `libGL.so.1`."""

    GL_FALSE = 0
    GL_TRUE = 1
    GL_TRIANGLES = 0x0004
    GL_DEPTH_BUFFER_BIT = 0x00000100
    GL_COLOR_BUFFER_BIT = 0x00004000
    GL_DEPTH_TEST = 0x0B71
    GL_BLEND = 0x0BE2
    GL_CULL_FACE = 0x0B44
    GL_SRC_ALPHA = 0x0302
    GL_ONE_MINUS_SRC_ALPHA = 0x0303
    GL_LEQUAL = 0x0203
    GL_FLOAT = 0x1406
    GL_UNSIGNED_BYTE = 0x1401
    GL_TEXTURE_2D = 0x0DE1
    GL_TEXTURE0 = 0x84C0
    GL_TEXTURE1 = 0x84C1
    GL_RGBA = 0x1908
    GL_RGBA8 = 0x8058
    GL_TEXTURE_MAG_FILTER = 0x2800
    GL_TEXTURE_MIN_FILTER = 0x2801
    GL_TEXTURE_WRAP_S = 0x2802
    GL_TEXTURE_WRAP_T = 0x2803
    GL_NEAREST = 0x2600
    GL_CLAMP_TO_EDGE = 0x812F
    GL_ARRAY_BUFFER = 0x8892
    GL_STATIC_DRAW = 0x88E4
    GL_DYNAMIC_DRAW = 0x88E8
    GL_FRAGMENT_SHADER = 0x8B30
    GL_VERTEX_SHADER = 0x8B31
    GL_COMPILE_STATUS = 0x8B81
    GL_LINK_STATUS = 0x8B82

    def __init__(self) -> None:
        self.lib = ctypes.CDLL("libGL.so.1")
        self._bind_signatures()

    def _bind_signatures(self) -> None:
        L = self.lib
        L.glViewport.argtypes = [c_int, c_int, c_int, c_int]
        L.glClearColor.argtypes = [c_float, c_float, c_float, c_float]
        L.glClear.argtypes = [c_uint]
        L.glEnable.argtypes = [c_uint]
        L.glDisable.argtypes = [c_uint]
        L.glDepthFunc.argtypes = [c_uint]
        L.glDepthMask.argtypes = [c_uint]
        L.glBlendFunc.argtypes = [c_uint, c_uint]

        L.glCreateShader.argtypes = [c_uint]
        L.glCreateShader.restype = c_uint
        L.glShaderSource.argtypes = [c_uint, c_int, POINTER(c_char_p), POINTER(c_int)]
        L.glCompileShader.argtypes = [c_uint]
        L.glGetShaderiv.argtypes = [c_uint, c_uint, POINTER(c_int)]
        L.glGetShaderInfoLog.argtypes = [c_uint, c_int, POINTER(c_int), c_char_p]
        L.glDeleteShader.argtypes = [c_uint]

        L.glCreateProgram.argtypes = []
        L.glCreateProgram.restype = c_uint
        L.glAttachShader.argtypes = [c_uint, c_uint]
        L.glLinkProgram.argtypes = [c_uint]
        L.glGetProgramiv.argtypes = [c_uint, c_uint, POINTER(c_int)]
        L.glGetProgramInfoLog.argtypes = [c_uint, c_int, POINTER(c_int), c_char_p]
        L.glUseProgram.argtypes = [c_uint]

        L.glGetUniformLocation.argtypes = [c_uint, c_char_p]
        L.glGetUniformLocation.restype = c_int
        L.glUniform1i.argtypes = [c_int, c_int]
        L.glUniform1f.argtypes = [c_int, c_float]
        L.glUniform3f.argtypes = [c_int, c_float, c_float, c_float]
        L.glUniformMatrix3fv.argtypes = [c_int, c_int, c_uint, POINTER(c_float)]
        L.glUniformMatrix4fv.argtypes = [c_int, c_int, c_uint, POINTER(c_float)]

        L.glGenVertexArrays.argtypes = [c_int, POINTER(c_uint)]
        L.glBindVertexArray.argtypes = [c_uint]
        L.glGenBuffers.argtypes = [c_int, POINTER(c_uint)]
        L.glBindBuffer.argtypes = [c_uint, c_uint]
        L.glBufferData.argtypes = [c_uint, c_size_t, c_void_p, c_uint]
        L.glEnableVertexAttribArray.argtypes = [c_uint]
        L.glVertexAttribPointer.argtypes = [c_uint, c_int, c_uint, c_uint, c_int, c_void_p]
        L.glDrawArrays.argtypes = [c_uint, c_int, c_int]

        L.glGenTextures.argtypes = [c_int, POINTER(c_uint)]
        L.glBindTexture.argtypes = [c_uint, c_uint]
        L.glActiveTexture.argtypes = [c_uint]
        L.glTexParameteri.argtypes = [c_uint, c_uint, c_int]
        L.glTexImage2D.argtypes = [
            c_uint,
            c_int,
            c_int,
            c_int,
            c_int,
            c_int,
            c_uint,
            c_uint,
            c_void_p,
        ]

    def compile_shader(self, source: str, shader_type: int) -> int:
        sid = self.lib.glCreateShader(shader_type)
        src_bytes = source.encode("utf-8")
        src_ptr = c_char_p(src_bytes)
        length = c_int(len(src_bytes))
        self.lib.glShaderSource(sid, 1, ctypes.byref(src_ptr), ctypes.byref(length))
        self.lib.glCompileShader(sid)

        status = c_int(0)
        self.lib.glGetShaderiv(sid, self.GL_COMPILE_STATUS, ctypes.byref(status))
        if not status.value:
            log_buf = ctypes.create_string_buffer(2048)
            self.lib.glGetShaderInfoLog(sid, 2048, None, log_buf)
            raise RuntimeError(f"GLSL Shader compilation failed:\n{log_buf.value.decode('utf-8', 'replace')}")
        return sid

    def create_program(self, vert_src: str, frag_src: str) -> int:
        vs = self.compile_shader(vert_src, self.GL_VERTEX_SHADER)
        fs = self.compile_shader(frag_src, self.GL_FRAGMENT_SHADER)
        prog = self.lib.glCreateProgram()
        self.lib.glAttachShader(prog, vs)
        self.lib.glAttachShader(prog, fs)
        self.lib.glLinkProgram(prog)

        status = c_int(0)
        self.lib.glGetProgramiv(prog, self.GL_LINK_STATUS, ctypes.byref(status))
        if not status.value:
            log_buf = ctypes.create_string_buffer(2048)
            self.lib.glGetProgramInfoLog(prog, 2048, None, log_buf)
            raise RuntimeError(f"GLSL Program link failed:\n{log_buf.value.decode('utf-8', 'replace')}")

        self.lib.glDeleteShader(vs)
        self.lib.glDeleteShader(fs)
        return prog

    def create_nearest_texture(self, rgba_array: np.ndarray) -> int:
        """Create an OpenGL 2D texture with strict GL_NEAREST pixel-art filtering."""
        tex_id = c_uint(0)
        self.lib.glGenTextures(1, ctypes.byref(tex_id))
        self.lib.glBindTexture(self.GL_TEXTURE_2D, tex_id.value)
        self.lib.glTexParameteri(self.GL_TEXTURE_2D, self.GL_TEXTURE_MIN_FILTER, self.GL_NEAREST)
        self.lib.glTexParameteri(self.GL_TEXTURE_2D, self.GL_TEXTURE_MAG_FILTER, self.GL_NEAREST)
        self.lib.glTexParameteri(self.GL_TEXTURE_2D, self.GL_TEXTURE_WRAP_S, self.GL_CLAMP_TO_EDGE)
        self.lib.glTexParameteri(self.GL_TEXTURE_2D, self.GL_TEXTURE_WRAP_T, self.GL_CLAMP_TO_EDGE)
        self.update_texture(tex_id.value, rgba_array)
        return tex_id.value

    def update_texture(self, tex_id: int, rgba_array: np.ndarray) -> None:
        contig = np.ascontiguousarray(rgba_array, dtype=np.uint8)
        h, w, _ = contig.shape
        self.lib.glBindTexture(self.GL_TEXTURE_2D, tex_id)
        self.lib.glTexImage2D(
            self.GL_TEXTURE_2D,
            0,
            self.GL_RGBA8,
            w,
            h,
            0,
            self.GL_RGBA,
            self.GL_UNSIGNED_BYTE,
            contig.ctypes.data_as(c_void_p),
        )
