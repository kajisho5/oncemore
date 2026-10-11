"""Blu-ray pictures besides 1920x1080 (DECISIONS §100): a disc can be
1280x720 progressive at twice its rate (720p 50 / 59.94, keeping 50 or 60
frames a second), and an AVCHD camera's 1440x1080 H.264 goes on a 1080 disc
as it is."""

import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from fractions import Fraction

from oncemore import bdmenu, bluray
from oncemore.errors import OncemoreError
from oncemore.project import build_project

from .helpers import have, run_cli

try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None


def disc(standard="NTSC", video="720"):
    return build_project({"version": 1, "disc": {"label": "T", "standard": standard, "aspect": "16:9",
                                                 "bluray": {"video": video}},
                          "titles": [{"id": "t", "source": "a.mp4"}]},
                         "/x/project.oncemore.json", check_files=False).disc


class TestFormats(unittest.TestCase):
    def test_codes(self):
        # (libbluray: 720P = 5; 23.976 = 1, 50 = 6, 59.94 = 7; 1080I = 4, 1080P = 6)
        ntsc, pal = disc("NTSC"), disc("PAL")
        self.assertEqual(bluray.frame_size(ntsc), (1280, 720))
        self.assertEqual(bluray.bd_fps((30000, 1001), ntsc), (60000, 1001))
        self.assertEqual(bluray.bd_format((30000, 1001), ntsc), (5, 7))
        self.assertEqual(bluray.bd_format((24000, 1001), ntsc), (5, 1))       # film stays
        self.assertEqual(bluray.bd_format((25, 1), pal), (5, 6))
        self.assertFalse(bluray.interlaced_format((25, 1), pal))
        hd = disc("NTSC", "1080")
        self.assertEqual(bluray.frame_size(hd), (1920, 1080))
        self.assertEqual(bluray.bd_format((30000, 1001), hd), (4, 4))
        self.assertTrue(bluray.interlaced_format((30000, 1001), hd))
        with self.assertRaises(OncemoreError):
            bluray.bd_format((30, 1), ntsc)

    def test_menus_are_drawn_on_the_720_frame(self):
        d = bdmenu.hd_disc(disc())
        self.assertEqual((d.width, d.height), (1280, 720))
        kx, ox, ky = bdmenu.frame_map(disc())
        self.assertAlmostEqual(kx, 1280 / 720)
        self.assertEqual(ox, 0)
        self.assertAlmostEqual(ky, 720 / 480)

    def test_video_args(self):
        args = bluray.stream_video_args((30000, 1001), 20_000_000, True, (), disc())
        self.assertEqual(args[args.index("-r") + 1], "60000/1001")
        self.assertNotIn("fake-interlaced", args[args.index("-x264-params") + 1])
        self.assertIn("keyint=60", args[args.index("-x264-params") + 1])
        hd = bluray.stream_video_args((30000, 1001), 20_000_000, True, (), disc("NTSC", "1080"))
        self.assertIn("fake-interlaced=1", hd[hd.index("-x264-params") + 1])

    def test_copy_compliance(self):
        base = {"codec": "h264", "profile": "High", "level": 40, "pix_fmt": "yuv420p",
                "gop": 15, "video_bit_rate": 20_000_000}
        hd = disc("NTSC", "1080")
        # (probe gives the pixel shape and the rate as fractions)
        avchd = dict(base, width=1440, height=1080, sar=Fraction(4, 3), fps=Fraction(30000, 1001),
                     fields=True)
        self.assertEqual(bluray.copy_compliance(avchd, (30000, 1001), hd), [])
        self.assertTrue(bluray.copy_compliance(dict(avchd, sar=Fraction(1)), (30000, 1001), hd))
        # a 720 disc takes 1280x720 at 59.94, not 1080 pictures
        small = dict(base, width=1280, height=720, sar=Fraction(1), fps=Fraction(60000, 1001), gop=30)
        self.assertEqual(bluray.copy_compliance(small, (30000, 1001), disc()), [])
        self.assertTrue(bluray.copy_compliance(avchd, (30000, 1001), disc()))
        self.assertTrue(bluray.copy_compliance(dict(small, fps=Fraction(30000, 1001)), (30000, 1001),
                                               disc()))


def pcs_size(sup):
    """(width, height) of the first presentation composition in a .sup."""
    with open(sup, "rb") as f:
        data = f.read()
    i = 0
    while i + 13 <= len(data):
        kind, size = data[i + 10], struct.unpack(">H", data[i + 11:i + 13])[0]
        if kind == 0x16:
            return struct.unpack(">HH", data[i + 13:i + 17])
        i += 13 + size
    return None


@unittest.skipUnless(have("ffmpeg") and have("ffprobe"), "needs ffmpeg")
class TestBuild720(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-bd720-")
        d = cls.d = os.path.join(cls.tmp, "proj")
        os.makedirs(d)
        ff = ["ffmpeg", "-v", "error", "-y"]
        # 59.94p, and the same motion as 1080i (fields of a 59.94p picture)
        src = ["-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=60000/1001:duration=2",
               "-f", "lavfi", "-i", "sine=duration=2"]
        subprocess.run(ff + src + ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                                   "-c:a", "aac", "-shortest", os.path.join(d, "p60.mp4")], check=True)
        subprocess.run(ff + src + ["-vf", "tinterlace=interleave_top,setfield=tff",
                                   "-c:v", "mpeg2video", "-b:v", "15M", "-flags", "+ilme+ildct",
                                   "-top", "1", "-c:a", "mp2", "-shortest",
                                   os.path.join(d, "i30.mpg")], check=True)
        with open(os.path.join(d, "t.srt"), "w") as f:
            f.write("1\n00:00:00,300 --> 00:00:01,500\nHello\n")
        project = {"version": 1,
                   "disc": {"label": "BD720", "standard": "NTSC", "aspect": "16:9",
                            "bluray": {"video": "720"}, "first_play": "menu:m"},
                   "menus": [{"id": "m", "buttons": [
                       {"id": "a", "label": "PLAY", "x": 100, "y": 200, "action": "title:p"},
                       {"id": "b", "label": "FIELDS", "x": 100, "y": 260, "action": "title:i"}]}],
                   "titles": [{"id": "p", "source": "p60.mp4", "subtitles": [{"file": "t.srt"}],
                               "remote_menu": "m"},
                              {"id": "i", "source": "i30.mpg"}]}
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump(project, f)
        cls.out = os.path.join(cls.tmp, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--format", "bluray",
                                                 "--fast", "--json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)

    def stream(self, n):
        return os.path.join(self.out, "BDMV", "STREAM", f"{n:05d}.m2ts")

    def test_pictures_are_720p_59_94(self):
        for n in (1, 2, 3):                      # both titles and the menu
            p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate,field_order", "-of", "json",
                                self.stream(n)], capture_output=True, text=True, check=True)
            v = json.loads(p.stdout)["streams"][0]
            self.assertEqual((v["width"], v["height"], v["r_frame_rate"]), (1280, 720, "60000/1001"), n)
            self.assertIn(v.get("field_order", "progressive"), ("progressive", "unknown"), n)

    def frame_diffs(self, path, n=12, w=160, h=90):
        """Mean change of a grey pixel between each picture and the next."""
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", "-frames:v",
                              str(n), "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                             capture_output=True, check=True).stdout
        fs = [raw[i * w * h:(i + 1) * w * h] for i in range(len(raw) // (w * h))]
        self.assertEqual(len(fs), n)
        return [sum(abs(a - b) for a, b in zip(x, y)) / (w * h) for x, y in zip(fs, fs[1:])]

    def test_motion_is_kept(self):
        # every picture moves on from the one before: 60 a second, not 30 shown
        # twice (a 29.97 source made 59.94 alternates ~2 and ~0.02 here). The 1080i
        # source too: each field became a picture. (The first picture may be held
        # once while the source's clock starts.)
        for n in (1, 2):
            d = self.frame_diffs(self.stream(n))[1:]
            self.assertGreater(min(d), 0.3, (n, d))

    def test_subtitles_are_drawn_for_720(self):
        sup = os.path.join(self.tmp, "pg.sup")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.stream(1), "-map", "0:s:0",
                        "-c", "copy", "-f", "sup", sup], check=True)
        self.assertEqual(pcs_size(sup), (1280, 720))

    @unittest.skipUnless(LIBBLURAY, "libbluray not installed")
    def test_libbluray_reads_720p(self):
        with bluray_sim.Disc(LIBBLURAY, self.out) as bd:
            self.assertTrue(bd.info()["bluray"])
            for n in (1, 2, 3):
                pl = bd.playlist(n)
                self.assertEqual(pl["video"], [(bluray.CODING_H264, 5, 7)], n)     # 720p 59.94
            self.assertEqual(len(bd.playlist(1)["pg"]), 1)



try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover
    PLAYWRIGHT = False


@unittest.skipUnless(PLAYWRIGHT, "needs playwright")
class TestPictureSetting(unittest.TestCase):
    """Build > Picture: the size and the picture are kept apart in disc.bluray."""

    def test_build_panel(self):
        from .test_gui import GuiServer, TestGuiBrowser
        tmp = tempfile.mkdtemp(prefix="oncemore-bd720-gui-")
        self.addCleanup(shutil.rmtree, tmp, True)
        s = GuiServer(tmp)
        self.addCleanup(s.close)
        s.call("/api/new", "POST", {"sample": True})

        def bluray():
            with open(os.path.join(tmp, "project.oncemore.json")) as f:
                return json.load(f)["disc"].get("bluray")
        with sync_playwright() as p:
            browser = TestGuiBrowser.launch(self, p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{s.base}/#token={s.app.token}")
            page.locator("[data-lt=build]").click(timeout=120000)
            page.select_option("#sidebar #bformat", "bluray")
            page.locator("#sidebar #bdvideo").wait_for()

            def until(want):
                for _ in range(100):
                    if bluray() == want:
                        return
                    page.wait_for_timeout(50)
                self.assertEqual(bluray(), want)
            page.select_option("#sidebar #bdvideo", "720")
            until({"video": "720"})
            page.select_option("#sidebar #bdsize", "BD50")
            until({"video": "720", "target": "BD50"})
            page.select_option("#sidebar #bdvideo", "1080")
            until({"target": "BD50"})
            page.select_option("#sidebar #bdsize", "BD25")
            until(None)
            browser.close()
        self.assertEqual(errors, [])

if __name__ == "__main__":
    unittest.main()
