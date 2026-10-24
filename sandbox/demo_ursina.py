from ursina import *

app = Ursina()

# Đặt camera nhìn nghiêng góc 3D
camera.position = (5, 10, -10)
camera.rotation = (45, -30, 0)

#1 Tạo 1 ô gạch Tao
tile = Entity(
    model = 'cube',
    color = color.gray,
    scale=(10, 0.2, 10),
    position=(0, -0.1, 0)
)

#2 Tạo một đối tượng bloxorz
bloxorz = Entity(
    model = 'cube',
    color = color.azure,
    position = (0, 1, 0),
    scale = (1,2,1)
)

# 3. Muốn nó di chuyển mượt mà (Hoạt ảnh)? Dùng đúng 1 hàm:
# block.animate_position((1, 1, 0), duration=0.2)  # Trượt sang ô x=1 trong 0.2 giây!
def update():
    bloxorz.rotation_y += 50 * time.dt

app.run() # Mở cửa sổ game lên!