"""The layer break of a dual-layer (DVD-9) disc.

Choosing it (ECC blocks, the first layer the larger, a layer's size), the
chapters read from the IFO files of a built disc (each one a navigation pack
where the image says), and a DVD-9 image whose layer break chapter the
built-in writer puts on an ECC block, given to the burner.

A real dual-layer image is over 4.38 GiB, so the image test makes the
single-layer size small instead.
"""

import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

from oncemore import build, burn, layerbreak, tools
from oncemore.errors import OncemoreError, ProjectError
from oncemore.project import build_project, load_project
from oncemore.report import Reporter
from oncemore.scaffold import sample_project

from .helpers import have, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None

DVD_OK = have("ffmpeg", "ffprobe") and tools.has_drawtext()


class TestPick(unittest.TestCase):
    CH = [(1, 1, 1, 100), (1, 1, 2, 900), (1, 2, 1, 1203), (1, 2, 2, 1700)]

    def test_problems(self):
        self.assertIsNone(layerbreak.problem(1024, 2000))
        self.assertIn("ECC", layerbreak.problem(1030, 2000))
        self.assertIn("second layer", layerbreak.problem(992, 2000))
        self.assertIn("first layer", layerbreak.problem(layerbreak.LAYER_MAX + 16, 4_171_000))

    def test_auto_and_chosen(self):
        # 900 is before the middle of 2000; 1203 is past it but not on an ECC block
        with self.assertRaises(OncemoreError):
            layerbreak.pick(self.CH[:3], 2000)
        # (1700 is not on one either: none works as the image is)
        with self.assertRaises(OncemoreError):
            layerbreak.pick(self.CH, 2000)
        # moving VIDEO_TS: 1203 + 13 = 1216, a multiple of 16
        c, sector, shift = layerbreak.pick(self.CH, 2000, shift_ok=True)
        self.assertEqual((c, sector, shift), (self.CH[2], 1216, 13))
        c, sector, shift = layerbreak.pick(self.CH, 2000, want=(1, 2, 2), shift_ok=True)
        self.assertEqual((sector, shift), (1712, 12))
        with self.assertRaises(OncemoreError) as cm:
            layerbreak.pick(self.CH, 2000, want=(1, 1, 2), shift_ok=True)
        self.assertIn("second layer", cm.exception.message)
        with self.assertRaises(OncemoreError):
            layerbreak.pick(self.CH, 2000, want=(2, 1, 1))
        self.assertFalse(layerbreak.needed(layerbreak.SINGLE_LAYER))
        self.assertTrue(layerbreak.needed(layerbreak.SINGLE_LAYER + 1))

    def test_burn_command(self):
        with mock.patch.object(tools, "is_macos", return_value=False), \
                mock.patch.object(tools, "find", return_value="/usr/bin/growisofs"):
            cmd = burn.command("/x/d.iso", "/dev/sr0", 1216)
        self.assertEqual(cmd, ["/usr/bin/growisofs", "-dvd-compat",
                               "-use-the-force-luke=break:1216", "-Z", "/dev/sr0=/x/d.iso"])


class TestProject(unittest.TestCase):
    def test_field(self):
        d = sample_project()
        d["disc"]["target"] = "DVD9"
        d["disc"]["layer_break"] = "t1:2"
        p = build_project(d, "/virtual/project.oncemore.json", check_files=False)
        self.assertEqual(p.disc.layer_break, ("t1", 2))
        d["disc"]["layer_break"] = "auto"
        self.assertIsNone(build_project(d, "/virtual/p.json", check_files=False).disc.layer_break)
        for bad, where in (("t1:9", "chapters"), ("tx:1", "no title")):
            d["disc"]["layer_break"] = bad
            with self.assertRaises(ProjectError) as cm:
                build_project(d, "/virtual/p.json", check_files=False)
            self.assertIn(where, str(cm.exception.issues))
        d["disc"]["layer_break"] = "t1:x"
        with self.assertRaises(ProjectError):
            build_project(d, "/virtual/p.json", check_files=False)
        d["disc"]["layer_break"] = "t1:1"
        d["disc"]["target"] = "DVD5"
        p = build_project(d, "/virtual/p.json", check_files=False)
        self.assertTrue(any("layer_break" in w for w in p.warnings))


def nav_pack_at(f, sector):
    """Whether the sector holds a DVD navigation pack (pack header, system
    header, then the PCI private stream 2 packet)."""
    f.seek(sector * layerbreak.SECTOR)
    b = f.read(64)
    return b[:4] == b"\x00\x00\x01\xba" and b[14:18] == b"\x00\x00\x01\xbb" and \
        b[38:42] == b"\x00\x00\x01\xbf"


@unittest.skipUnless(DVD_OK, "needs ffmpeg (drawtext)")
class TestImage(unittest.TestCase):
    """The sample disc as a DVD-9 image, its layer break at the second
    title (chapter 1)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-lb-")
        rc, _, err = run_cli("init", "s", cwd=cls.tmp)
        assert rc == 0, err
        cls.dir = os.path.join(cls.tmp, "s")
        path = os.path.join(cls.dir, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["disc"]["target"] = "DVD9"
        data["disc"]["layer_break"] = "t2:1"
        with open(path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "d.iso")
        rep = Reporter(out=io.StringIO(), err=io.StringIO())
        # (the sample is small: as if a layer held 1 sector)
        with mock.patch.object(layerbreak, "SINGLE_LAYER", 1):
            cls.res = build.build_iso(load_project(cls.dir), cls.iso, rep, fast=True,
                                      iso_tool="builtin")
            cls.found = burn.find_layer_break(cls.iso)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_chapters_are_nav_packs(self):
        chapters, total = layerbreak.iso_chapters(self.iso)
        # t1's chapters, then t2's
        self.assertEqual([c[:3] for c in chapters], [(1, 1, 1), (1, 1, 2), (1, 1, 3), (1, 2, 1)])
        with open(self.iso, "rb") as f:
            for c in chapters:
                self.assertTrue(nav_pack_at(f, c[3]), c)
        self.assertEqual(total * layerbreak.SECTOR, os.path.getsize(self.iso))

    def test_layer_break(self):
        lb = self.res["layer_break"]
        self.assertEqual((lb["title"], lb["chapter"]), ("t2", 1))
        self.assertEqual(lb["sector"] % 16, 0)
        chapters, total = layerbreak.iso_chapters(self.iso)
        self.assertEqual(lb["sector"], chapters[3][3])
        self.assertEqual(lb["layer0_sectors"] + lb["layer1_sectors"], total)
        self.assertGreaterEqual(lb["layer0_sectors"], lb["layer1_sectors"])
        # the burner finds it in the image too (the first chapter that can be one)
        self.assertEqual(self.found, lb["sector"])
        # an image that fits on one layer has none
        self.assertIsNone(burn.find_layer_break(self.iso))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_still_plays(self):
        """VIDEO_TS moved for the layer break: players read the image as before."""
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.num_titles(), 2)
            self.assertEqual(d.wait_menu(), 1)
            d.activate(3)                                 # SAMPLE TITLE B
            self.assertEqual(d.wait_title(), (2, 1))

    def test_a_chapter_too_early(self):
        p = load_project(self.dir)
        p.disc.layer_break = ("t1", 1)
        rep = Reporter(out=io.StringIO(), err=io.StringIO())
        with mock.patch.object(layerbreak, "SINGLE_LAYER", 1):
            with self.assertRaises(OncemoreError) as cm:
                build.layer_break(p, self.iso, rep, [])
        self.assertIn("second layer", cm.exception.message)
        # (auto with nothing that works: a warning, and the burner picks)
        p.disc.layer_break = None
        warnings = []
        with mock.patch.object(layerbreak, "SINGLE_LAYER", 1), \
                mock.patch.object(layerbreak, "ECC", 1 << 30):
            self.assertIsNone(build.layer_break(p, self.iso, rep, warnings))
        self.assertTrue(warnings)


if __name__ == "__main__":
    unittest.main()
