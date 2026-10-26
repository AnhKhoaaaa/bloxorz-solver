# Phụ trách: VT3 - Task 3.2
"""Hoạt ảnh chuyển động lăn, rơi vực và chiến thắng."""


def animate_fall(block_entity, on_complete=None):
    """Hoạt ảnh rơi xuống vực"""
    from ursina import curve
    block_entity.animate_position(
        (block_entity.x, -10, block_entity.z), 
        duration=0.6,
        curve=curve.in_quad,
    )
    # Gắn on_complete vào hoạt ảnh xoay (cùng 0.6s)
    block_entity.animate_rotation(
        (block_entity.rotation_x + 90, 0, block_entity.rotation_z + 180),
        duration=0.6,
        curve=curve.in_quad,
        resolution=0,
    )
    if on_complete is not None:
        from ursina import invoke
        invoke(on_complete, delay=0.6)


def animate_win(block_entity, on_complete=None):
    """Hoạt ảnh chiến thắng: khối tụt thẳng đứng xuống lỗ đích"""
    from ursina import curve
    block_entity.animate_position(
        (block_entity.x, -1.2, block_entity.z),
        duration=0.5,
        curve=curve.linear,
    )
    if on_complete is not None:
        from ursina import invoke
        invoke(on_complete, delay=0.5)


def animate_roll(block_entity, target_pos, on_complete=None):
    """Hoạt ảnh lăn khối tới vị trí đích"""
    from ursina import curve
    block_entity.animate_position(
        target_pos,
        duration=0.18,
        curve=curve.out_quad,
    )
    if on_complete is not None:
        from ursina import invoke
        invoke(on_complete, delay=0.18)

        

