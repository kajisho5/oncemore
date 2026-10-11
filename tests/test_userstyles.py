"""The user's own styles (Library > My styles): saved from an element with
its font, listed, applied to a project (the font copied once), deleted."""

import os
import shutil
import tempfile
import unittest
from unittest import mock

from oncemore import userstyles


class TestUserStyles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-styles-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.lib = os.path.join(self.tmp, "lib")
        env = mock.patch.dict(os.environ, {"ONCEMORE_STYLES": self.lib})
        env.start()
        self.addCleanup(env.stop)
        self.a, self.b = os.path.join(self.tmp, "a"), os.path.join(self.tmp, "b")
        os.makedirs(os.path.join(self.a, "media"))
        with open(os.path.join(self.a, "media", "Title.ttf"), "wb") as f:
            f.write(b"font bytes")

    def test_round_trip(self):
        text = {"text": "SAMPLE", "x": 10, "y": 20, "size": 56, "color": "#FFCC00",
                "font": "media/Title.ttf", "outline": "#000000", "outline_width": 3}
        sid = userstyles.save(text, "Big title", self.a)
        self.assertEqual(sid, "big_title")
        self.assertEqual(userstyles.save({"color": "#FF0000"}, "Big title", self.a), "big_title_2")
        styles = {s["id"]: s for s in userstyles.list_styles()}
        # only the look is kept, the font with it
        self.assertEqual(styles["big_title"]["props"],
                         {"font": "files/Title.ttf", "size": 56, "color": "#FFCC00",
                          "outline": "#000000", "outline_width": 3})
        self.assertTrue(os.path.isfile(os.path.join(self.lib, "big_title", "files", "Title.ttf")))
        # another project: the font is copied into its media, once
        props = userstyles.apply("big_title", self.b)
        self.assertEqual(props["font"], "media/Title.ttf")
        self.assertEqual(userstyles.apply("big_title", self.b)["font"], "media/Title.ttf")
        self.assertEqual(os.listdir(os.path.join(self.b, "media")), ["Title.ttf"])
        # a different file of that name is kept: the style's comes in beside it
        with open(os.path.join(self.b, "media", "Title.ttf"), "wb") as f:
            f.write(b"another font")
        self.assertEqual(userstyles.apply("big_title", self.b)["font"], "media/Title_2.ttf")
        userstyles.delete("big_title")
        self.assertEqual([s["id"] for s in userstyles.list_styles()], ["big_title_2"])

    def test_refused(self):
        with self.assertRaises(ValueError):
            userstyles.save({"text": "no look", "x": 1}, "x", self.a)
        with self.assertRaises(ValueError):
            userstyles.apply("../etc", self.a)
        with self.assertRaises(FileNotFoundError):
            userstyles.apply("missing", self.a)


if __name__ == "__main__":
    unittest.main()
