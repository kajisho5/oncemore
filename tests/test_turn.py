"""Turned and mirrored menu objects (Object > Rotate / Flip) and guides.

The project fields, the picture the menu renderer draws, the highlight
shapes that turn with their buttons (for DVD and Blu-ray alike), and guides
read from Photoshop files.
"""

import os
import shutil
import struct
import subprocess
import tempfile
import unittest

from oncemore import bdmenu, psdmenu, tools
from oncemore.errors import ProjectError
from oncemore.menu import MenuBuilder
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have
from .psd_writer import build_psd, solid

RENDER = have("ffmpeg", "ffprobe") and tools.has_drawtext()


def project(data, base="/virtual"):
    return build_project(data, os.path.join(base, "project.oncemore.json"), check_files=False)


class TestProjectFields(unittest.TestCase):
    def test_parsed(self):
        d = sample_project()
        m = d["menus"][0]
        m["buttons"][0].update({"rotate": -90, "flip": "horizontal"})
        m["texts"][0]["rotate"] = 360
        m["shapes"] = [{"x": 10, "y": 10, "w": 40, "h": 20, "flip": "both"}]
        m["guides"] = {"horizontal": [240], "vertical": [36, 684]}
        menu = project(d).menus[0]
        self.assertEqual((menu.buttons[0].rotate, menu.buttons[0].flip), (270.0, "horizontal"))
        self.assertEqual(menu.texts[0].rotate, 0.0)             # (a whole turn: none)
        self.assertEqual((menu.shapes[0].rotate, menu.shapes[0].flip), (0.0, "both"))
        self.assertEqual((menu.buttons[1].rotate, menu.buttons[1].flip), (0.0, None))

    def test_refused(self):
        for change, path in ((lambda m: m["buttons"][0].update(flip="diagonal"), "buttons[0].flip"),
                             (lambda m: m["texts"][0].update(rotate=400), "texts[0].rotate"),
                             (lambda m: m.update(guides={"vertical": [800]}), "guides.vertical[0]"),
                             (lambda m: m.update(guides={"diagonal": [1]}), "guides.diagonal")):
            d = sample_project()
            change(d["menus"][0])
            with self.assertRaises(ProjectError) as cm:
                project(d)
            self.assertIn(path, str(cm.exception.issues))

    def test_blu_ray_keeps_them(self):
        d = sample_project()
        d["menus"][0]["buttons"][0].update({"rotate": 30, "flip": "vertical"})
        d["menus"][0]["shapes"] = [{"x": 10, "y": 10, "w": 40, "h": 20, "rotate": 45}]
        p = project(d)
        hd = bdmenu.scale_menu(p.menus[0], p.disc, lambda path: {"width": 100, "height": 50})
        self.assertEqual((hd.buttons[0].rotate, hd.buttons[0].flip), (30.0, "vertical"))
        self.assertEqual(hd.shapes[0].rotate, 45.0)


def rgb(png, w, h):
    """The pixels of a picture file as rows of (r, g, b)."""
    raw = subprocess.run([tools.find("ffmpeg"), "-v", "error", "-i", png, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return [[tuple(raw[(y * w + x) * 3:(y * w + x) * 3 + 3]) for x in range(w)] for y in range(h)]


@unittest.skipUnless(RENDER, "needs ffmpeg with drawtext")
class TestRendered(unittest.TestCase):
    """What the menu renderer draws, on a black menu (720 x 480 NTSC 4:3, so
    display and storage pixels are the same)."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-turn-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.data = sample_project(aspect="4:3")
        m = self.data["menus"][0]
        m.pop("background", None)
        m["background_color"] = "#000000"
        m["texts"] = []

    def builder(self):
        p = project(self.data, self.dir)
        return p, MenuBuilder(p, self.dir)

    def picture(self, menu):
        _, mb = self.builder()
        path = mb.render_base(menu)
        return rgb(path, 720, 480)

    def test_shape_turned_about_its_centre(self):
        # a 200 x 20 red bar centred at (360, 240), turned a quarter: upright
        self.data["menus"][0]["shapes"] = [{"x": 260, "y": 230, "w": 200, "h": 20,
                                            "color": "#FF0000", "rotate": 90}]
        p, _ = self.builder()
        px = self.picture(p.menus[0])
        red = lambda c: c[0] > 200 and c[1] < 60 and c[2] < 60      # noqa: E731
        self.assertTrue(red(px[160][360]) and red(px[320][360]))     # along the upright bar
        self.assertFalse(red(px[240][280]) or red(px[240][440]))     # where it lay before
        self.assertTrue(red(px[240][360]))                           # the centre stays

    def test_picture_flipped(self):
        # a picture red on its left half, blue on its right, flipped: blue left
        pic = os.path.join(self.dir, "media", "half.png")
        os.makedirs(os.path.dirname(pic), exist_ok=True)
        subprocess.run([tools.find("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                        "color=c=red:s=50x40,format=rgb24[a];color=c=blue:s=50x40,format=rgb24[b];"
                        "[a][b]hstack", "-frames:v", "1", pic], check=True)
        self.data["menus"][0]["images"] = [{"file": "media/half.png", "x": 300, "y": 200,
                                            "w": 100, "h": 40, "flip": "horizontal"}]
        p, _ = self.builder()
        px = self.picture(p.menus[0])
        self.assertGreater(px[220][320][2], 200)          # blue on the left now
        self.assertGreater(px[220][380][0], 200)          # red on the right

    def test_text_button_highlight_turns_with_it(self):
        m = self.data["menus"][0]
        m["buttons"] = m["buttons"][:1]
        b = m["buttons"][0]
        p, mb = self.builder()
        flat = mb.layout(p.menus[0])[0].rect
        b["rotate"] = 90
        p, mb = self.builder()
        turned = mb.layout(p.menus[0])[0]
        w0, h0 = flat[2] - flat[0], flat[3] - flat[1]
        w1, h1 = turned.rect[2] - turned.rect[0], turned.rect[3] - turned.rect[1]
        self.assertGreater(w0, h0)                         # a label lies flat ...
        self.assertGreater(h1, w1)                         # ... and stands when turned
        # about the same centre
        c0 = ((flat[0] + flat[2]) / 2, (flat[1] + flat[3]) / 2)
        c1 = ((turned.rect[0] + turned.rect[2]) / 2, (turned.rect[1] + turned.rect[3]) / 2)
        self.assertLess(abs(c0[0] - c1[0]), 8)
        self.assertLess(abs(c0[1] - c1[1]), 8)
        # the highlight is the turned glyphs (and underline), drawn where the label is
        mask = turned.shape[0]
        box = mask.bbox()
        self.assertGreater(box[3] - box[1], box[2] - box[0])
        px = self.picture(p.menus[0])
        lit = [y for y in range(box[1], box[3] + 1) if any(sum(px[y][x]) > 300
                                                           for x in range(box[0], box[2] + 1))]
        self.assertGreater(len(lit), (box[3] - box[1]) * 0.6)

    def test_image_button_shape_mirrored(self):
        # an image button opaque on its left half only, highlighted by its shape
        pic = os.path.join(self.dir, "media", "left.png")
        os.makedirs(os.path.dirname(pic), exist_ok=True)
        subprocess.run([tools.find("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                        "color=c=white:s=40x40,format=rgba[a];color=c=black@0:s=40x40,format=rgba[b];"
                        "[a][b]hstack", "-frames:v", "1", pic], check=True)
        m = self.data["menus"][0]
        m["buttons"] = [{"id": "pic", "x": 300, "y": 200, "action": "title:t1",
                         "image": "media/left.png", "width": 80, "highlight": "shape"}]
        p, mb = self.builder()
        plain = mb.layout(p.menus[0])[0].shape[0].bbox()
        m["buttons"][0]["flip"] = "horizontal"
        p, mb = self.builder()
        flipped = mb.layout(p.menus[0])[0].shape[0].bbox()
        self.assertLess(plain[0], 305)          # left half: from x 300
        self.assertGreaterEqual(flipped[0], 335)  # mirrored: the right half
        self.assertEqual(plain[1], flipped[1])

    def test_thumbnail_stays(self):
        m = self.data["menus"][0]
        m["buttons"] = m["buttons"][1:2]
        m["buttons"][0].update({"action": "title:t1", "rotate": 45,
                                "thumbnail": {"x": 400, "y": 100, "w": 160, "h": 120}})
        p, mb = self.builder()
        g = mb.layout(p.menus[0])[0]
        self.assertIn(("frame", (396, 96, 564, 224)), g.shape)


class TestPhotoshopGuides(unittest.TestCase):
    """Guides of a Photoshop file come with the menu made from it (image
    resource 1032: 1/32 pixel positions; 0 vertical, 1 horizontal)."""

    def test_imported(self):
        d = tempfile.mkdtemp(prefix="oncemore-psdg-")
        self.addCleanup(shutil.rmtree, d, True)
        W, H = 1440, 960                      # twice the menu: positions halve
        guides = [(720 * 32, 0), (100 * 32, 0), (480 * 32 + 16, 1), (5000 * 32, 1)]
        res = struct.pack(">I", 1) + struct.pack(">II", 576, 576) + struct.pack(">I", len(guides))
        res += b"".join(struct.pack(">iB", pos, kind) for pos, kind in guides)
        block = b"8BIM" + struct.pack(">H", 1032) + b"\0\0" + struct.pack(">I", len(res)) + res
        data = build_psd(W, H, [], composite=solid(W, H, (10, 20, 60, 255)), resources=block)
        path = os.path.join(d, "design.psd")
        with open(path, "wb") as f:
            f.write(data)
        if not have("ffmpeg"):
            self.skipTest("needs ffmpeg")
        menu, _ = psdmenu.import_psd(path, sample_project(), "art", os.path.join(d, "media"), d)
        # (x on the 720-wide grid; the one past the bottom is left out)
        self.assertEqual(menu["guides"], {"horizontal": [240], "vertical": [50, 360]})
        # a file without guides keeps the menu's own
        plain = build_psd(W, H, [], composite=solid(W, H, (10, 20, 60, 255)))
        with open(path, "wb") as f:
            f.write(plain)
        project_ = sample_project()
        project_["menus"].append({"id": "art", "buttons": [], "guides": {"vertical": [10]}})
        menu, _ = psdmenu.import_psd(path, project_, "art", os.path.join(d, "media"), d)
        self.assertEqual(menu["guides"], {"vertical": [10]})


if __name__ == "__main__":
    unittest.main()
