"""Subtitle scripts as subtitling houses deliver them (DECISIONS §104),
after the classic apps' manual: the image script that opens with
Display_Area and Directory lines, the FAB image script with a place for
each picture, and scripts saved as UTF-16."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import subtitles, tools
from oncemore.errors import ProjectError

from .helpers import run_cli
from .test_imagesubs import DVD_OK, grey_video, ifo_palette

FAB = ("RACE001.PNG 00;00;00;15 00;00;01;15 100 060 300 110\n"
       "race 2.png\t00;00;02;00\t00;00;03;00\t000 000 720 480\n")


class TestScripts(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-deliver-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        for name in ("RACE001.PNG", "race 2.png", "a.tif"):
            open(os.path.join(self.dir, name), "wb").close()

    def write(self, name, text, encoding="utf-8"):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding=encoding, newline="") as f:
            f.write(text)
        return path

    def test_image_script_with_display_area(self):
        # (the manual's example; the Windows folder is not here, so the
        # pictures are looked for next to the script)
        path = self.write("s.txt", "Display_Area (000 020 720 460)\n"
                                   "Directory C:\\Subtitles\\Image Files\\Caption Inc Images\\\n"
                                   "1 00;00;02;02 00;00;03;15 a.tif\n"
                                   "2 00;00;05;18 00;00;09;20 Text stays text\n")
        cues = subtitles.load_subtitles(path)
        self.assertEqual(cues[0].image, os.path.join(self.dir, "a.tif"))
        self.assertEqual(cues[0].area, (0, 20, 720, 460))
        self.assertEqual((cues[1].lines, cues[1].area), (["Text stays text"], None))
        # a Directory that is there is used first
        other = os.path.join(self.dir, "pics")
        os.makedirs(other)
        open(os.path.join(other, "a.tif"), "wb").close()
        path = self.write("s2.txt", f"Directory {other}\n1 0;0;1;0 0;0;2;0 a.tif\n")
        self.assertEqual(subtitles.load_subtitles(path)[0].image, os.path.join(other, "a.tif"))
        with self.assertRaises(ProjectError):
            subtitles.load_subtitles(self.write("bad.txt", "Display_Area (10 10 5 20)\n"
                                                           "1 0;0;1;0 0;0;2;0 a.tif\n"))

    def test_fab_script(self):
        self.assertTrue(subtitles.is_fab_script(FAB))
        self.assertFalse(subtitles.is_fab_script("1 00;00;01;00 00;00;02;00 Hello\n"))
        cues = subtitles.load_subtitles(self.write("fab.txt", FAB))
        self.assertEqual([os.path.basename(c.image) for c in cues], ["RACE001.PNG", "race 2.png"])
        self.assertEqual(cues[0].area, (100, 60, 300, 110))
        self.assertAlmostEqual(cues[1].start, 2.002, places=3)
        # written back as it came: a FAB script keeps the places
        again = subtitles.parse_fab_script(subtitles.to_text_script(cues), "NTSC", self.dir)
        self.assertEqual([(c.image, c.area) for c in again], [(c.image, c.area) for c in cues])
        with self.assertRaises(ProjectError) as cm:
            subtitles.load_subtitles(self.write("fab2.txt", FAB + "missing.png 0;0;4;0 0;0;5;0 0 0 9 9\n"))
        self.assertIn("'missing.png' not found", str(cm.exception))

    def test_utf16(self):
        text = "1 00;00;01;00 00;00;02;00 こんにちは\n2 00;00;03;00 00;00;04;00 Ça va\n"
        for enc in ("utf-16", "utf-16-le", "utf-16-be"):      # (with a byte order mark, and without)
            cues = subtitles.load_subtitles(self.write(f"{enc}.txt", text, enc))
            self.assertEqual([c.lines for c in cues], [["こんにちは"], ["Ça va"]], enc)
        self.assertEqual(subtitles.load_subtitles(self.write("fab16.txt", FAB, "utf-16"))[0].area,
                         (100, 60, 300, 110))


@unittest.skipUnless(DVD_OK, "needs ffmpeg (drawtext)")
class TestDvd(unittest.TestCase):
    """Pictures drawn where the scripts put them, not centred at the bottom."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-deliver-dvd-")
        subs = os.path.join(d, "subs")
        os.makedirs(subs)
        ff = [tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i"]
        # a small green picture with transparency round it
        subprocess.run(ff + ["color=c=lime:s=180x30,format=rgba,pad=200:50:10:10:color=black@0",
                             "-frames:v", "1", os.path.join(subs, "green.png")], check=True)
        with open(os.path.join(subs, "fab.txt"), "w", encoding="utf-16") as f:
            f.write("green.png 00;00;00;15 00;00;01;15 100 060 300 110\n")
        with open(os.path.join(subs, "old.txt"), "w") as f:
            f.write("Display_Area (400 300 600 350)\nDirectory D:\\Elsewhere\\\n"
                    "1 00;00;02;00 00;00;03;00 green.png\n")
        grey_video(d, "720x480")
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump({"version": 1,
                       "disc": {"label": "DELIVER", "standard": "NTSC", "aspect": "4:3",
                                "first_play": "title:t"},
                       "titles": [{"id": "t", "source": "grey.mp4", "subtitles": [
                           {"file": "subs/fab.txt", "lang": "en", "default": True},
                           {"file": "subs/old.txt", "lang": "ja"}]}]}, f)
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def pixels(self, stream, t, points):
        vts = os.path.join(self.out, "VIDEO_TS")
        raw = subprocess.run([tools.find("ffmpeg"), "-v", "error", "-palette",
                              ifo_palette(os.path.join(vts, "VTS_01_0.IFO")), "-i",
                              os.path.join(vts, "VTS_01_1.VOB"), "-filter_complex",
                              f"[0:v][0:s:{stream}]overlay[o]", "-map", "[o]", "-ss", str(t),
                              "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        return [tuple(raw[(y * 720 + x) * 3:(y * 720 + x) * 3 + 3]) for x, y in points]

    def assertColour(self, got, want, tol=40):
        self.assertTrue(all(abs(a - b) <= tol for a, b in zip(got, want)), (got, want))

    def test_fab_place(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        # area 100,60 - 300,110: the green box inside it, nothing at the bottom
        inside, below = self.pixels(0, 1.0, [(200, 85), (360, 420)])
        self.assertColour(inside, (0, 255, 0))
        self.assertColour(below, (128, 128, 128))

    def test_display_area(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        inside, centre_bottom = self.pixels(1, 2.5, [(500, 325), (360, 420)])
        self.assertColour(inside, (0, 255, 0))
        self.assertColour(centre_bottom, (128, 128, 128))


if __name__ == "__main__":
    unittest.main()
