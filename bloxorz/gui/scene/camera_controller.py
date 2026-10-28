# bloxorz/gui/scene/camera_controller.py
from __future__ import annotations
import math
import random
from ursina import (
    Entity,
    Vec3,
    camera,
    mouse,
    held_keys,
    time,
)

try:
    from bloxorz.gui.scene.theme import set_biome
except ImportError:
    try:
        from theme import set_biome
    except ImportError:
        set_biome = lambda b: None


class SmoothOrbitCamera(Entity):
    """
    Tái hiện toàn bộ hệ thống Camera Cinematic từ bản Three.js / HTML:
      1. Phối cảnh giả đẳng cự (Perspective Pseudo-Isometric: FOV 42, theta 0.55 rad, phi 0.92 rad)
      2. Tọa độ cầu có kẹp biên chặt chẽ (Spherical Orbit: radius, theta, phi)
      3. Bám mục tiêu trễ có quán tính (Dynamic Target Lerp / Spring Damping: factor 0.08)
      4. Rung chấn Camera suy giảm hàm mũ khi rơi vực (Decaying Camera Shake: decay 0.88)
      5. Kéo chuột xoay mượt + Con lăn Zoom + Phím C góc vàng + Phím T Top-down + Q/E xoay 45°
    """

    DEFAULT_THETA = 0.55   # ~31 độ
    DEFAULT_PHI = 0.92     # ~52 độ

    def __init__(self) -> None:
        super().__init__()
        # Góc mở hẹp (FOV 42) tạo hiệu ứng Pseudo-Isometric kinh điển
        camera.fov = 42

        # 1. Các tham số tọa độ cầu (Spherical Coordinates)
        self.default_radius: float = 22.0
        self.radius: float = 22.0
        self.theta: float = self.DEFAULT_THETA
        self.phi: float = self.DEFAULT_PHI

        # Giới hạn góc nâng (20 độ -> 79 độ) để triệt tiêu gimbal lock và lún sàn
        self.min_phi: float = 0.35
        self.max_phi: float = 1.38
        self.min_radius: float = 8.0
        self.max_radius: float = 48.0

        # 2. Hệ thống bám mục tiêu trễ (Target Smoothing / Damping)
        self.target_pos = Vec3(0, 0, 0)
        self.current_look = Vec3(0, 0, 0)
        self.smooth_speed: float = 0.08

        # 3. Rung chấn (Camera Shake)
        self.shake_intensity: float = 0.0

        # Khởi tạo vị trí ban đầu
        self._recompute_camera(instant=True)

    def set_target(self, target: Vec3, radius: float | None = None) -> None:
        """Đặt mục tiêu mới cho Camera (tâm bàn cờ hoặc tâm khối gỗ)."""
        self.target_pos = Vec3(target)
        if radius is not None:
            self.default_radius = max(self.min_radius, min(self.max_radius, radius))
            self.radius = self.default_radius

    def trigger_shake(self, intensity: float = 0.25) -> None:
        """Kích hoạt rung camera khi rơi vực (gọi trong on_fall)."""
        self.shake_intensity = intensity

    def reset_view(self) -> None:
        """Đưa camera về góc Pseudo-Isometric chuẩn mực đẹp nhất."""
        self.theta = self.DEFAULT_THETA
        self.phi = self.DEFAULT_PHI
        self.radius = self.default_radius
        self.current_look = Vec3(self.target_pos)
        self._recompute_camera(instant=True)

    def top_down_view(self) -> None:
        """Góc nhìn từ trên cao xuống (Top-down chiến thuật) giúp soi đường đi."""
        self.theta = 0.0
        self.phi = 0.35
        self.update_camera()

    def rotate_step(self, direction: int) -> None:
        """Xoay chuyển tự động đúng 45 độ vào các góc đối xứng hoàn hảo."""
        step = math.pi / 4.0
        cur_step = round(self.theta / step)
        self.theta = (cur_step + direction) * step
        self.update_camera()

    def update_camera(self) -> None:
        self._recompute_camera(instant=False, dt=time.dt)

    def input(self, key: str) -> None:
        if key == "1":
            set_biome("overworld")
        elif key == "2":
            set_biome("nether")
        elif key == "3":
            set_biome("end")
        elif key == "c":
            self.reset_view()
        elif key == "t":
            self.top_down_view()
        elif key == "q":
            self.rotate_step(-1)
        elif key == "e":
            self.rotate_step(1)
        elif key == "scroll up":
            self.radius = max(self.min_radius, self.radius - 1.5)
        elif key == "scroll down":
            self.radius = min(self.max_radius, self.radius + 1.5)

    def update(self) -> None:
        dt = time.dt

        # 1. Xử lý chuột kéo xoay Orbit (hỗ trợ cả chuột trái và chuột phải)
        if held_keys["left mouse"] or held_keys["right mouse"]:
            dx = mouse.velocity[0]
            dy = mouse.velocity[1]
            if abs(dx) > 0.0001 or abs(dy) > 0.0001:
                self.theta -= dx * 2.8
                self.phi = max(self.min_phi, min(self.max_phi, self.phi - dy * 2.8))

        # 2. Cập nhật vị trí camera mỗi frame
        self._recompute_camera(instant=False, dt=dt)

    def _recompute_camera(self, instant: bool = False, dt: float = 0.016) -> None:
        # Nội suy LERP mượt mà: current_look trôi dần về target_pos
        if instant:
            self.current_look = Vec3(self.target_pos)
        else:
            # Damping chuẩn độc lập với FPS (tương đương factor 0.08 ở 60fps)
            lerp_factor = 1.0 - math.pow(max(0.0, 1.0 - self.smooth_speed), dt * 60.0)
            self.current_look = self.current_look + (self.target_pos - self.current_look) * lerp_factor

        # Công thức chuyển từ Tọa độ cầu sang Tọa độ Descartes 3D
        cam_x = self.current_look.x + self.radius * math.sin(self.phi) * math.sin(self.theta)
        cam_y = self.current_look.y + self.radius * math.cos(self.phi)
        cam_z = self.current_look.z - self.radius * math.sin(self.phi) * math.cos(self.theta)

        # Áp dụng rung chấn suy giảm theo hàm mũ (Decaying Camera Shake)
        if self.shake_intensity > 0.003:
            cam_x += (random.random() - 0.5) * self.shake_intensity
            cam_y += (random.random() - 0.5) * self.shake_intensity
            cam_z += (random.random() - 0.5) * self.shake_intensity
            self.shake_intensity *= math.pow(0.88, dt * 60.0)
        else:
            self.shake_intensity = 0.0

        camera.position = Vec3(cam_x, cam_y, cam_z)
        camera.look_at(self.current_look)
