# bloxorz/gui/scene/animate.py
from __future__ import annotations
import random
from typing import Callable, Optional
from ursina import Entity, Vec3, curve, invoke, destroy, color
from bloxorz.gui.scene.theme import ANIM_ROLL_DURATION
from bloxorz.gui.scene.block import BlockMesh


def _action_name(action) -> str:
    """Chuẩn hóa tên hướng di chuyển từ Enum hoặc chuỗi."""
    name = getattr(action, "name", str(action)).upper()
    if "LEFT" in name:
        return "LEFT"
    if "RIGHT" in name:
        return "RIGHT"
    if "UP" in name:
        return "UP"
    if "DOWN" in name:
        return "DOWN"
    return name


def _compute_pivot_and_rotation(old_state, direction: str) -> tuple[Vec3, Vec3]:
    """
    Tính tọa độ cạnh đáy tiếp xúc sàn (Pivot Edge) và góc xoay 90 độ tương ứng.
    Hệ trục Ursina (Left-handed):
      - X tăng sang phải (RIGHT), giảm sang trái (LEFT)
      - Z tăng về phía Bắc/Lên (UP: r giảm -> -r tăng), giảm về phía Nam/Xuống (DOWN: r tăng -> -r giảm)
    """
    r, c = old_state.pos
    pose_val = getattr(old_state.pose, "value", old_state.pose)
    pose_name = getattr(old_state.pose, "name", "")

    if pose_val == 0 or pose_name == "STANDING":
        min_x = max_x = float(c)
        min_z = max_z = float(-r)
        cx, cz = float(c), float(-r)
    elif pose_val == 1 or pose_name == "HORIZONTAL":
        min_x, max_x = float(c), float(c) + 1.0
        min_z = max_z = float(-r)
        cx, cz = float(c) + 0.5, float(-r)
    else:  # VERTICAL: chiếm (r, c) và (r+1, c) -> z từ -r đến -r-1
        min_x = max_x = float(c)
        min_z, max_z = float(-r) - 1.0, float(-r)
        cx, cz = float(c), float(-r) - 0.5

    if direction == "LEFT":
        pivot = Vec3(min_x - 0.5, 0.0, cz)
        rot = Vec3(0, 0, -90)
    elif direction == "RIGHT":
        pivot = Vec3(max_x + 0.5, 0.0, cz)
        rot = Vec3(0, 0, 90)
    elif direction == "UP":
        pivot = Vec3(cx, 0.0, max_z + 0.5)
        rot = Vec3(90, 0, 0)
    else:  # DOWN
        pivot = Vec3(cx, 0.0, min_z - 0.5)
        rot = Vec3(-90, 0, 0)

    return pivot, rot


def animate_roll(*args, on_complete: Optional[Callable[[], None]] = None, **kwargs) -> None:
    if len(args) == 2:
        entity, target_pos = args
        if hasattr(entity, "animate_position"):
            entity.animate_position(target_pos, duration=ANIM_ROLL_DURATION, curve=curve.out_quad)
        if on_complete:
            invoke(on_complete, delay=ANIM_ROLL_DURATION + 0.01)
        return
    block, old_state, action, new_state = args[:4]
    """Hoạt ảnh lăn lật khối 90 độ quanh cạnh đáy tiếp xúc sàn trong 0.16 giây."""
    direction = _action_name(action)

    # Nếu đang ở chế độ tách khối (Split), di chuyển mượt từng khối đơn
    if old_state.pose is None or new_state.pose is None:
        block.sync_from_state(new_state)
        if on_complete:
            invoke(on_complete, delay=ANIM_ROLL_DURATION)
        return

    # Đồng bộ trạng thái xuất phát chuẩn trước khi xoay Pivot
    block.sync_from_state(old_state)
    visual_world_pos = block.visual.position
    visual_world_rot = block.visual.rotation

    pivot_pos, target_rot = _compute_pivot_and_rotation(old_state, direction)

    # Đặt gốc của BlockMesh ngay tại cạnh đáy và bù trừ vị trí của visual con
    block.position = pivot_pos
    block.rotation = Vec3(0, 0, 0)
    block.visual.position = visual_world_pos - pivot_pos
    block.visual.rotation = visual_world_rot

    block.animate_rotation(
        target_rot,
        duration=ANIM_ROLL_DURATION,
        curve=curve.out_quad,
    )

    def _finish_roll() -> None:
        block.sync_from_state(new_state)
        if on_complete:
            on_complete()

    invoke(_finish_roll, delay=ANIM_ROLL_DURATION)


def animate_fall(
    block: BlockMesh,
    old_state,
    action,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    """Hoạt ảnh khối lật ra ngoài mép sàn, mất trọng tâm và lộn nhào rơi xuống vực."""
    direction = _action_name(action)
    block.sync_from_state(old_state)

    visual_world_pos = block.visual.position
    pivot_pos, target_rot = _compute_pivot_and_rotation(old_state, direction)

    block.position = pivot_pos
    block.rotation = Vec3(0, 0, 0)
    block.visual.position = visual_world_pos - pivot_pos

    # Bước 1: Lật qua mép vực (0.14s)
    block.animate_rotation(target_rot * 1.15, duration=0.14, curve=curve.in_quad)

    # Bước 2: Rơi tự do kèm xoay lộn nhào xuống vực sâu
    def _plunge() -> None:
        offset = Vec3(0, -10.5, 0)
        if direction == "LEFT":
            offset.x -= 1.6
        elif direction == "RIGHT":
            offset.x += 1.6
        elif direction == "UP":
            offset.z += 1.6
        elif direction == "DOWN":
            offset.z -= 1.6

        block.animate_position(block.position + offset, duration=0.48, curve=curve.in_quad)
        block.animate_rotation(target_rot * 3.2, duration=0.48, curve=curve.linear)

        def _done() -> None:
            block.sync_from_state(old_state)
            if on_complete:
                on_complete()

        invoke(_done, delay=0.50)

    invoke(_plunge, delay=0.14)


def _spawn_voxel_fireworks(center: Vec3) -> None:
    """Bắn chùm pháo hoa hạt Voxel ăn mừng chiến thắng tại Cổng End."""
    palette = [
        color.rgb32(85, 255, 85),
        color.rgb32(255, 255, 85),
        color.rgb32(217, 107, 255),
        color.rgb32(85, 255, 255),
        color.rgb32(255, 170, 0),
    ]
    rng = random.Random()
    for i in range(28):
        p = Entity(
            model="cube",
            scale=0.18,
            position=center + Vec3(0, 0.8, 0),
            color=palette[i % len(palette)],
            unlit=True,
        )
        dest = center + Vec3(
            rng.uniform(-2.6, 2.6),
            rng.uniform(1.2, 4.2),
            rng.uniform(-2.6, 2.6),
        )
        p.animate_position(dest, duration=0.65, curve=curve.out_cubic)
        p.animate_scale(0.001, duration=0.65, curve=curve.in_quad)
        invoke(destroy, p, delay=0.68)


def animate_win(
    block: BlockMesh,
    state,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    """Hoạt ảnh chiến thắng: Khối đứng thẳng hạ từ từ xuống lòng Cổng End kèm pháo hoa."""
    block.sync_from_state(state)
    center = block.get_center_world_pos(state)
    _spawn_voxel_fireworks(center)

    target_pos = block.visual.position + Vec3(0, -1.75, 0)
    block.visual.animate_position(target_pos, duration=0.65, curve=curve.in_out_quad)
    block.visual.animate_rotation(Vec3(0, 360, 0), duration=0.65, curve=curve.in_out_quad)
    block.visual.animate_scale(Vec3(0.25, 0.85, 0.25), duration=0.65, curve=curve.in_quad)

    if on_complete:
        invoke(on_complete, delay=0.68)