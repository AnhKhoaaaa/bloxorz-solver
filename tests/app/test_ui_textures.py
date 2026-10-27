"""
Kiểm thử chất liệu giao diện - Task 4.5
- ui_textures vẽ đúng kích thước, có kênh trong suốt, góc bo trong suốt, tất định theo seed.
- Font và giấy phép OFL đi kèm có trong assets/fonts/.
"""

from pathlib import Path

import pytest

from bloxorz.gui import ui_textures as tex

FONTS = Path(__file__).resolve().parents[2] / "bloxorz" / "gui" / "assets" / "fonts"


@pytest.mark.parametrize("make", [
    lambda: tex.stone_panel((220, 120), seed=1),
    lambda: tex.button_face((160, 48), "gold"),
    lambda: tex.solid_rounded((160, 48), (40, 27, 12)),
    lambda: tex.soft_shadow((200, 90), blur=6),
    lambda: tex.coin(72, "restart"),
])
def test_images_are_rgba_with_transparent_corner(make):
    img = make()
    assert img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0  # góc bo / nền rêu trong suốt


def test_moss_grows_in_clumps_and_leaves_gaps():
    img = tex.moss((400, 80), seed=2)
    alpha = img.split()[3]
    covered = sum(alpha.histogram()[129:]) / (400 * 80)
    assert img.mode == "RGBA" and 0.1 < covered < 0.7  # có rêu nhưng không phủ kín thành 1 dải
    assert img.getpixel((200, 79))[3] == 0  # giữa mép dưới để trống (rêu dày ở 2 góc)
    assert img.getpixel((20, 15))[3] > 128  # góc trên có chùm rêu


def test_sizes_match_request():
    assert tex.stone_panel((300, 140)).size == (300, 140)
    assert tex.stone((50, 20)).size == (50, 20)
    assert tex.coin(64, "prev").size == (64, 64)


def test_same_seed_same_image_different_seed_differs():
    assert tex.stone_panel((120, 80), seed=5).tobytes() == tex.stone_panel((120, 80), seed=5).tobytes()
    assert tex.stone_panel((120, 80), seed=5).tobytes() != tex.stone_panel((120, 80), seed=6).tobytes()
    assert tex.moss((120, 40), seed=1).tobytes() == tex.moss((120, 40), seed=1).tobytes()


def test_panel_center_is_opaque_stone():
    r, g, b, a = tex.stone_panel((200, 120), seed=0).getpixel((100, 60))
    assert a == 255 and r > b  # đá nâu ấm


@pytest.mark.parametrize("kind", tex.FACE_FILLS)
def test_button_face_kinds(kind):
    face = tex.button_face((120, 40), kind)
    assert face.getpixel((60, 20))[3] == 255


def test_unknown_names_rejected():
    with pytest.raises(ValueError):
        tex.coin(64, "home")
    with pytest.raises(KeyError):
        tex.button_face((100, 40), "ruby")


@pytest.mark.parametrize("name", ["AlegreyaSC-Black.ttf", "AlegreyaSC-Bold.ttf", "Philosopher-Regular.ttf",
                                  "OFL-AlegreyaSC.txt", "OFL-Philosopher.txt"])
def test_font_assets_present(name):
    assert (FONTS / name).is_file()


def test_carved_title_renders_vietnamese():
    font = str(FONTS / "AlegreyaSC-Black.ttf")
    title = tex.carved_title("RƠI XUỐNG VỰC!", font, height=60, seed=1, tint=(214, 70, 30))
    assert title.mode == "RGBA" and title.width > title.height * 3
    assert title.getpixel((0, 0))[3] == 0  # nền trong suốt
    assert sum(title.split()[3].histogram()[200:]) > 0
    assert tex.carved_title("A", font, 40).tobytes() == tex.carved_title("A", font, 40).tobytes()


def test_buttons_with_different_seeds_differ():
    assert tex.button_face((160, 48), "stone", seed=1).tobytes() != tex.button_face((160, 48), "stone", seed=2).tobytes()
    assert tex.button_face((160, 48), "stone", seed=1).tobytes() == tex.button_face((160, 48), "stone", seed=1).tobytes()


def test_shard_is_small_transparent_piece():
    piece = tex.shard(32, seed=3)
    assert piece.size == (32, 32) and piece.getpixel((0, 0))[3] == 0 and piece.getpixel((16, 16))[3] == 255
