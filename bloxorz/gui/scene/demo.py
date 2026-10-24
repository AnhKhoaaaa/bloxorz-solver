# Phụ trách: VT3 - Task 3.1
"""File demo thử nghiệm cảnh 3D độc lập."""

from pathlib import Path

from ursina import Entity, Ursina, application, color, window

from bloxorz.gui.controller import GameController
from bloxorz.gui.fake_scene import apply_key
from bloxorz.gui.scene.view import SceneView
from bloxorz.loader import load_stage


def main() -> None:
    app = Ursina(title="Bloxorz 3D Demo (Task 3.1)", development_mode=False)
    window.color = color.rgb32(24, 26, 32)

    # Nạp màn cơ bản để test
    fixture_path = Path(__file__).resolve().parents[3] / "stages" / "fixtures" / "basic.json"
    stage = load_stage(fixture_path)
    controller = GameController([stage])

    scene = SceneView()
    scene.load_stage(controller.stage, controller.state)

    class InputHandler(Entity):
        def input(self, key: str) -> None:
            if key == "escape":
                application.quit()
            else:
                apply_key(controller, scene, key)

    InputHandler()
    app.run()


if __name__ == "__main__":
    main()
