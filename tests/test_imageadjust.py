"""A menu's background and its pictures adjusted before they are placed:
crop, brightness, contrast and saturation (`background_adjust`, a
picture's `adjust`)."""

import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import schemalite
from oncemore.errors import ProjectError
from oncemore.menu import MenuBuilder, adjust_filter
from oncemore.project import Adjust, build_project, load_schema
from oncemore.scaffold import sample_project

from .helpers import have


def data(**menu):
    d = sample_project()
    d["menus"][0].update(menu)
    return d


def project(d, path="/virtual/project.oncemore.json"):
    return build_project(d, path, check_files=False)


class TestModel(unittest.TestCase):
    def test_loaded(self):
        p = project(data(background_adjust={"crop": {"x": 0.25, "y": 0, "w": 0.5, "h": 1},
                                            "brightness": 0.1},
                         images=[{"file": "logo.png", "x": 10, "y": 10, "w": 50, "h": 50,
                                  "adjust": {"saturation": 0}}]))
        m = p.menus[0]
        self.assertEqual(m.background_adjust, Adjust((0.25, 0, 0.5, 1), 0.1, 1.0, 1.0))
        self.assertEqual(m.images[0].adjust, Adjust(saturation=0))
        # what leaves the picture as it is is no adjustment
        m = project(data(background_adjust={"crop": {"x": 0, "y": 0, "w": 1, "h": 1},
                                            "contrast": 1})).menus[0]
        self.assertIsNone(m.background_adjust)

    def test_refused(self):
        with self.assertRaises(ProjectError) as e:
            project(data(background_adjust={"crop": {"x": 0.6, "y": 0, "w": 0.5, "h": 1}}))
        self.assertIn("past the picture's edge", str(e.exception.issues))
        bad = data(background_adjust={"contrast": 5})
        self.assertTrue(schemalite.validate(bad, load_schema()))

    def test_filters(self):
        self.assertEqual(adjust_filter(None, ","), "")
        self.assertEqual(adjust_filter(Adjust((0.25, 0, 0.5, 1)), ","),
                         "crop=iw*0.5000:ih*1.0000:iw*0.2500:ih*0.0000,")
        self.assertEqual(adjust_filter(Adjust(brightness=0.2, contrast=1.5)),
                         "eq=brightness=0.200:contrast=1.500:saturation=1.000")


@unittest.skipUnless(have("ffmpeg"), "needs ffmpeg")
class TestRendered(unittest.TestCase):
    """The menu's first frame, drawn as the disc gets it."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-adjust-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def picture(self, name, lavfi):
        path = os.path.join(self.tmp, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", lavfi,
                        "-frames:v", "1", path], check=True)
        return path

    def render(self, **menu):
        d = data(texts=[], buttons=[{"id": "x", "label": "X", "x": 0, "y": 0, "action": "stop"}],
                 **menu)
        p = project(d, os.path.join(self.tmp, "project.oncemore.json"))
        m = p.menus[0]
        m.buttons = []
        png = MenuBuilder(p, self.tmp).render_base(m)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", png, "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
        width = len(raw) // 3 // p.disc.height
        return lambda x, y: tuple(raw[3 * (y * width + x):3 * (y * width + x) + 3]), width

    def test_background_cropped(self):
        # red on the left, blue on the right: the left half fills the menu
        bg = self.picture("halves.png", "color=c=red:s=64x48,"
                                        "drawbox=x=32:y=0:w=32:h=48:color=blue:t=fill")
        px, w = self.render(background=bg, background_color="#000000")
        r, g, b = px(w // 2 + 20, 240)
        self.assertLess(r, 100)                           # (as it is: blue there)
        px, w = self.render(background=bg, background_color="#000000",
                            background_adjust={"crop": {"x": 0, "y": 0, "w": 0.5, "h": 1}})
        r, g, b = px(w // 2 + 20, 240)
        self.assertGreater(r, 200, (r, g, b))
        self.assertLess(b, 60, (r, g, b))

    def test_background_brighter_and_grey(self):
        bg = self.picture("teal.png", "color=c=0x208080:s=64x48")
        px, w = self.render(background=bg)
        plain = px(w // 2, 240)
        px, w = self.render(background=bg, background_adjust={"brightness": 0.3})
        brighter = px(w // 2, 240)
        self.assertGreater(sum(brighter), sum(plain) + 150, (plain, brighter))
        px, w = self.render(background=bg, background_adjust={"saturation": 0})
        r, g, b = px(w // 2, 240)
        self.assertLessEqual(max(r, g, b) - min(r, g, b), 6, (r, g, b))   # (grey)

    def test_picture_cropped_keeps_transparency(self):
        # a picture: transparent left half, white right half; its right half
        # alone fills its box, and a transparent part still shows the menu
        pic = self.picture("half.png", "color=c=black@0.0:s=20x40,format=rgba[a];"
                                       "color=c=white:s=20x40,format=rgba[b];[a][b]hstack[out0]")
        px, w = self.render(background=None, background_color="#000000",
                            images=[{"file": pic, "x": 100, "y": 100, "w": 100, "h": 100,
                                     "adjust": {"crop": {"x": 0.5, "y": 0, "w": 0.5, "h": 1}}}])
        sx = w / 720
        self.assertGreater(min(px(round(120 * sx), 150)), 200)          # (the white half)
        px, w = self.render(background=None, background_color="#000000",
                            images=[{"file": pic, "x": 100, "y": 100, "w": 100, "h": 100,
                                     "adjust": {"brightness": 0.2}}])
        self.assertLess(max(px(round(120 * sx), 150)), 30)              # (still see-through)
        self.assertGreater(min(px(round(180 * sx), 150)), 200)


if __name__ == "__main__":
    unittest.main()
