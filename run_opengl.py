"""Script khởi chạy trực tiếp bản Native OpenGL 3.3 Core Profile (v2)."""
import sys
from main import main

if __name__ == "__main__":
    # Tự động gán cờ --opengl nếu người dùng không truyền tham số
    args = sys.argv[1:]
    if "--opengl" not in args and "--text" not in args and "--ursina" not in args:
        args.append("--opengl")
    sys.exit(main(args))
