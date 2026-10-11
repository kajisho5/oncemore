"""Paragraph text on a menu: several lines, lined up left, centred or right,
with extra space between them.

The fields, the drawtext options they become, and the lines as drawn (their
pixels): a short second line under a long first one starts where the first
starts, sits in its middle, or ends where it ends.
"""

import shutil
import tempfile
import unittest

from oncemore import tools
from oncemore.errors import ProjectError
from oncemore.menu import MenuBuilder
from oncemore.project import build_project
from oncemore.scaffold import sample_project

ALIGN_OK = tools.find("ffmpeg") and tools.has_drawtext() and tools.drawtext_option("text_align")


def project(**text):
    d = sample_project()
    d["menus"][0]["texts"] = [dict({"text": "WWWWWWWW\nI", "x": 100, "y": 100, "size": 40},
                                   **text)]
    return build_project(d, "/virtual/project.oncemore.json", check_files=False)


def lines(mask):
    """Per line of glyphs (row bands with pixels): (x0, x1, y0, y1)."""
    rows = sorted({r[0] for r in mask.runs})
    bands, start = [], rows[0]
    for a, b in zip(rows, rows[1:] + [None]):
        if b is None or b != a + 1:
            bands.append((start, a + 1))
            start = b
    out = []
    for y0, y1 in bands:
        rs = [r for r in mask.runs if y0 <= r[0] < y1]
        out.append((min(r[1] for r in rs), max(r[2] for r in rs), y0, y1))
    return out


class TestFields(unittest.TestCase):
    def test_parse_and_check(self):
        t = project(align="center", line_spacing=12).menus[0].texts[0]
        self.assertEqual((t.align, t.line_spacing), ("center", 12))
        t = project().menus[0].texts[0]
        self.assertEqual((t.align, t.line_spacing), ("left", 0))
        with self.assertRaises(ProjectError):
            project(align="justify")

    def test_drawtext_options(self):
        work = tempfile.mkdtemp(prefix="oncemore-para-")
        self.addCleanup(shutil.rmtree, work, True)
        p = project(align="right", line_spacing=8)
        mb = MenuBuilder(p, work)
        f = mb._drawtext("t.txt", 100, 100, 40, "#FFFFFF", p.menus[0].texts[0])
        self.assertIn(":line_spacing=8", f)
        if tools.find("ffmpeg") and tools.drawtext_option("text_align"):
            self.assertIn(":text_align=R", f)
        # one line: nothing to line up
        one = project(text="ONE", align="center").menus[0].texts[0]
        self.assertNotIn("text_align", mb._drawtext("t.txt", 0, 0, 40, "#FFFFFF", one))


@unittest.skipUnless(ALIGN_OK, "needs ffmpeg 6.1 or later with drawtext")
class TestDrawn(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="oncemore-para-")
        self.addCleanup(shutil.rmtree, self.work, True)

    def drawn(self, **text):
        p = project(**text)
        t = p.menus[0].texts[0]
        return lines(MenuBuilder(p, self.work).glyphs("t", t.text, t))

    def test_alignment(self):
        (wx0, wx1, _, _), (ix0, ix1, _, _) = self.drawn()
        self.assertLess(abs(ix0 - wx0), 6)                              # left
        (wx0, wx1, _, _), (ix0, ix1, _, _) = self.drawn(align="center")
        self.assertLess(abs((ix0 + ix1) / 2 - (wx0 + wx1) / 2), 4)      # centre
        (wx0, wx1, _, _), (ix0, ix1, _, _) = self.drawn(align="right")
        self.assertLess(abs(ix1 - wx1), 6)                              # right
        self.assertGreater(ix0 - wx0, (wx1 - wx0) / 2)

    def test_line_spacing(self):
        first, second = self.drawn()
        spaced = self.drawn(line_spacing=30)
        # the first line stays; the second moves down by the spacing
        self.assertEqual(spaced[0][2], first[2])
        self.assertAlmostEqual(spaced[1][2] - second[2], 30, delta=2)


if __name__ == "__main__":
    unittest.main()
