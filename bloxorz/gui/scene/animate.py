# Phụ trách: VT3 - Task 3.2
"""Hoạt ảnh chuyển động lăn, rơi vực và chiến thắng."""
from ursina import curve 

#block.animate_position((block.x, -10, block.z), duration = 1.0, curve = curve.in_quad)


#block.animate_rotation((block.rotation_x + 90, block.rotation_y + 180, 0), duration = 1.0)

def animate_fall(block_entity, on_complete = None):
    """"Hoạt ảnh rơi xuống vực"""

    block_entity.animate_position(
        (block_entity.x, -10, block_entity.z), 
        duration = 0.6,
        curve=curve.in_quad 
    )

    block_entity.animate_rotation(
        (block_entity.rotation_x + 90, 0, block_entity.rotation_z + 180),
        duration = 0.6,
        curve=curve.in_quad
    )

def animate_win(block_entity, on_complete = None):
    """Hoạt ảnh chiến thắng"""

    block_entity.animate_position(
        (block_entity.x, -1.2, block_entity.z),
        duration = 0.5,
        curve=curve.linear
    )

def animate_roll(block_entity, target_pos, on_complete = None):
    """ Hoạt ảnh lăn khối theo hướng (direction)"""
    block_entity.animate_position(
        target_pos,
        duration = 0.5,
        curve=curve.out_bounce)
        

