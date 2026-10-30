# bloxorz/gui/scene/animate.py
from __future__ import annotations
import random
from typing import Callable, Optional
from ursina import Entity, Vec3, curve, invoke, destroy, color

try:
    from bloxorz.gui.scene.theme import ANIM_ROLL_DURATION, SoundManager
    from bloxorz.gui.scene.block import BlockMesh
except ImportError:
    from theme import ANIM_ROLL_DURATION, SoundManager
    from block import BlockMesh


def _action_name(action) -> str:
    direction = getattr(action, "direction", action)
    name = getattr(direction, "name", str(direction)).upper()
    for d in ("LEFT", "RIGHT", "UP", "DOWN"):
        if d in name:
            return d
    return name


def _compute_pivot_edge(old_state, direction: str) -> tuple[Vec3, Vec3]:
    """
    Tính tọa độ cạnh đáy tiếp xúc sàn mà khối sẽ lật qua:
      - LEFT: xoay qua mép X cực tiểu (quay quanh trục Z)
      - RIGHT: xoay qua mép X cực đại (quay quanh trục Z)
      - UP: xoay qua mép Z cực đại (+Z, quay quanh trục X)
      - DOWN: xoay qua mép Z cực tiểu (-Z, quay quanh trục X)
    """
    cells = BlockMesh.get_occupied_cells(old_state)
    min_x = min(float(c) for _, c in cells) - 0.5
    max_x = max(float(c) for _, c in cells) + 0.5
    min_z = min(float(-r) for r, _ in cells) - 0.5
    max_z = max(float(-r) for r, _ in cells) + 0.5
    mid_x = (min_x + max_x) / 2.0
    mid_z = (min_z + max_z) / 2.0

    if direction == "LEFT":
        return Vec3(min_x, 0.0, mid_z), Vec3(0, 0, -90)
    elif direction == "RIGHT":
        return Vec3(max_x, 0.0, mid_z), Vec3(0, 0, 90)
    elif direction == "UP":
        return Vec3(mid_x, 0.0, max_z), Vec3(90, 0, 0)
    else:  # DOWN
        return Vec3(mid_x, 0.0, min_z), Vec3(-90, 0, 0)


def animate_roll(
    block: BlockMesh,
    old_state,
    action=None,
    new_state=None,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    """Lăn khối mượt mà qua cạnh đáy, phát âm thanh bước chân và hiệu ứng nảy nhẹ."""
    # Trường hợp gọi 2 tham số cho 1 khối con khi đang tách: animate_roll(moving_cube, target_pos, on_complete=...)
    if action is None and new_state is None:
        target_pos = old_state
        if hasattr(block, "animate_position"):
            tx, ty, tz = target_pos
            block.animate_position(Vec3(tx, ty, tz), duration=ANIM_ROLL_DURATION, curve=curve.out_quad)
            SoundManager.play("step")
            if on_complete:
                invoke(on_complete, delay=ANIM_ROLL_DURATION)
        elif on_complete:
            on_complete()
        return

    direction = _action_name(action)

    if old_state.pose is None or new_state.pose is None:
        block.sync_from_state(new_state)
        SoundManager.play("step")
        if on_complete:
            invoke(on_complete, delay=ANIM_ROLL_DURATION)
        return

    block.sync_from_state(old_state)
    pivot_pos, target_rot = _compute_pivot_edge(old_state, direction)

    # Đưa khối vào một Pivot Entity tạm thời
    pivot_ent = Entity(position=pivot_pos, rotation=Vec3(0, 0, 0))
    block.unit_a.world_parent = pivot_ent
    block.unit_b.world_parent = pivot_ent

    pivot_ent.animate_rotation(
        target_rot,
        duration=ANIM_ROLL_DURATION,
        curve=curve.out_quad,
    )

    def _finish() -> None:
        block.unit_a.world_parent = block
        block.unit_b.world_parent = block
        destroy(pivot_ent)
        block.sync_from_state(new_state)

        # Phát âm thanh bước chân gạch/gỗ
        SoundManager.play("step")

        # Hiệu ứng nảy nhẹ tự nhiên khi tiếp đất
        block.animate_scale(Vec3(1.05, 0.94, 1.05), duration=0.04)
        invoke(lambda: block.animate_scale(Vec3(1.0, 1.0, 1.0), duration=0.06), delay=0.04)

        if on_complete:
            on_complete()

    invoke(_finish, delay=ANIM_ROLL_DURATION + 0.005)


def animate_fall(
    block: BlockMesh,
    old_state,
    action,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    """Khối mất trọng tâm, lộn nhào xoay tròn và rơi xuống vực sâu kèm tiếng gió rít."""
    direction = _action_name(action)
    block.sync_from_state(old_state)
    SoundManager.play("fall")

    pivot_pos, target_rot = _compute_pivot_edge(old_state, direction)
    pivot_ent = Entity(position=pivot_pos, rotation=Vec3(0, 0, 0))
    block.unit_a.world_parent = pivot_ent
    block.unit_b.world_parent = pivot_ent

    # Bước 1: Nghiêng lật qua mép vực
    pivot_ent.animate_rotation(target_rot * 1.15, duration=0.13, curve=curve.in_quad)

    def _plunge() -> None:
        offset = Vec3(0, -11.0, 0)
        if direction == "LEFT":
            offset.x -= 2.0
        elif direction == "RIGHT":
            offset.x += 2.0
        elif direction == "UP":
            offset.z += 2.0
        elif direction == "DOWN":
            offset.z -= 2.0

        pivot_ent.animate_position(pivot_ent.position + offset, duration=0.55, curve=curve.in_quad)
        pivot_ent.animate_rotation(target_rot * 3.5, duration=0.55, curve=curve.linear)

        def _done() -> None:
            block.unit_a.world_parent = block
            block.unit_b.world_parent = block
            destroy(pivot_ent)
            block.sync_from_state(old_state)
            if on_complete:
                on_complete()

        invoke(_done, delay=0.58)

    invoke(_plunge, delay=0.13)


def _spawn_voxel_fireworks(center: Vec3) -> None:
    palette = [
        color.rgb32(85, 255, 85),
        color.rgb32(255, 255, 85),
        color.rgb32(217, 107, 255),
        color.rgb32(85, 255, 255),
        color.rgb32(255, 170, 0),
    ]
    rng = random.Random()
    for i in range(35):
        p = Entity(
            model="cube",
            scale=0.18,
            position=center + Vec3(0, 0.8, 0),
            color=palette[i % len(palette)],
            unlit=True,
        )
        dest = center + Vec3(
            rng.uniform(-2.8, 2.8),
            rng.uniform(1.2, 4.6),
            rng.uniform(-2.8, 2.8),
        )
        p.animate_position(dest, duration=0.72, curve=curve.out_cubic)
        p.animate_scale(0.001, duration=0.72, curve=curve.in_quad)
        invoke(destroy, p, delay=0.75)


def animate_win(
    block: BlockMesh,
    target_state,
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    """Khối đứng vào Cổng End, chìm xuống lòng hố vũ trụ và bắn pháo hoa pixel."""
    block.sync_from_state(target_state)
    SoundManager.play("win")

    # Từ từ hạ độ cao khối xuống lòng cổng End (-0.8y)
    block.animate_position(block.position + Vec3(0, -0.85, 0), duration=0.75, curve=curve.in_out_quad)
    block.animate_scale(Vec3(0.01, 0.01, 0.01), duration=0.75, curve=curve.in_quad)

    _spawn_voxel_fireworks(block.position)

    def _done() -> None:
        block.scale = Vec3(1, 1, 1)
        block.sync_from_state(target_state)
        if on_complete:
            on_complete()

    invoke(_done, delay=0.85)
