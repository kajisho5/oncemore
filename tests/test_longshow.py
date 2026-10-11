"""Slideshows of more than 99 pictures.

A long show is drawn in pieces (each picture is an ffmpeg input of its
own): the pieces' graphs, and the frames of a show drawn in pieces being
those of the same show drawn at once, with transitions, cuts and pan &
zoom across the joins. On a DVD a title has at most 99 chapters, so the
pictures after the 98th are part of chapter 99; a Blu-ray keeps them all
(read back by libdvdnav and libbluray).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from oncemore import project as P
from oncemore import slideshow as S
from oncemore import tools
from oncemore.errors import ProjectError
from oncemore.scaffold import sample_project

from .helpers import have, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None
try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None

COLOURS = ["red", "green", "blue", "yellow", "magenta", "cyan", "white", "gray", "orange",
           "purple", "navy", "olive", "teal"]


def disc():
    return P.build_project(sample_project(), "/virtual/project.oncemore.json",
                           check_files=False).disc


def pictures(folder, n):
    out = []
    for k in range(n):
        path = os.path.join(folder, f"p{k}.png")
        subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi",
                        "-i", f"color=c={COLOURS[k % len(COLOURS)]}:s=160x120", "-frames:v", "1",
                        path], check=True)
        out.append(path)
    return out


class TestPieces(unittest.TestCase):
    def show(self, n=5, **kw):
        return S.Slideshow([S.Slide(f"/p/{k}.png", 2.0) for k in range(n)], **kw)

    def test_graph_of_a_piece(self):
        s = self.show()
        args, fc, audio = S.graph(s, disc(), (0, 2))
        # pictures 0 and 1, and the start of 2 for the cross-fade into it
        self.assertEqual(args.count("-i"), 3)
        self.assertIn("/p/2.png", args)
        self.assertFalse(audio)
        self.assertIn("[2:v]", fc)
        self.assertIn("trim=end_frame=30[s2]", fc)                 # 1 s at 29.97: the fade
        args, fc, _ = S.graph(s, disc(), (2, 5))
        self.assertEqual(args.count("-i"), 3)
        # picture 2 without the second the piece before drew
        self.assertIn("trim=start_frame=30:end_frame=", fc.split(";")[0])
        # its first cross-fade is at picture 3's start, counted from the piece's own start
        self.assertIn("offset=1.001000", fc)
        # (a cut at the join: nothing of the next picture)
        s = self.show(transition="none")
        args, fc, _ = S.graph(s, disc(), (0, 2))
        self.assertEqual(args.count("-i"), 2)
        self.assertNotIn("start_frame", S.graph(s, disc(), (2, 5))[1])

    def test_up_to_999(self):
        d = sample_project()
        d["titles"].append({"id": "show", "slideshow": {"slides": [{"image": "p.png"}] * 150}})
        p = P.build_project(d, "/virtual/p.json", check_files=False)
        self.assertEqual(len(p.title("show").chapters), 150)
        d["titles"][-1]["slideshow"]["slides"] = [{"image": "p.png"}] * 1000
        with self.assertRaises(ProjectError):
            P.build_project(d, "/virtual/p.json", check_files=False)


def framemd5(path):
    out = subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-i", path,
                          "-map", "0:v", "-f", "framemd5", "-"], capture_output=True, text=True,
                         check=True).stdout
    return [line.split(",")[-1].strip() for line in out.splitlines() if not line.startswith("#")]


@unittest.skipUnless(have("ffmpeg", "ffprobe"), "needs ffmpeg")
class TestRenderInPieces(unittest.TestCase):
    """13 pictures drawn at once and in pieces of 4: the same frames."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-longshow-")
        cls.pics = pictures(cls.tmp, 13)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def same(self, name, **kw):
        slides = [S.Slide(p, 0.6 + 0.1 * (k % 3), transition=("none" if k % 4 == 3 else None))
                  for k, p in enumerate(self.pics)]
        show = S.Slideshow(slides, transition_duration=0.3, **kw)
        whole = S.render(show, disc(), os.path.join(self.tmp, f"{name}-whole.mkv"),
                         os.path.join(self.tmp, f"{name}-whole.log"))
        with mock.patch.object(S, "CHUNK", 4):
            pieces = S.render(show, disc(), os.path.join(self.tmp, f"{name}-pieces.mkv"),
                              os.path.join(self.tmp, f"{name}-pieces.log"))
        a, b = framemd5(whole), framemd5(pieces)
        num, den = disc().fps
        self.assertEqual(len(a), round(show.duration * num / den))
        self.assertEqual(a, b)
        # (the pieces' files are gone)
        self.assertEqual([f for f in os.listdir(self.tmp) if ".part" in f], [])

    def test_crossfades_and_cuts(self):
        self.same("fade")

    def test_pan_and_zoom(self):
        self.same("zoom", pan_zoom=True)

    def test_wipes(self):
        self.same("wipe", transition="random")


DVD_OK = have("ffmpeg", "ffprobe") and tools.has_drawtext()


def x264():
    try:
        return "libx264" in subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-encoders"],
                                           capture_output=True, text=True).stdout
    except Exception:
        return False


@unittest.skipUnless(DVD_OK and x264() and LIBDVDNAV and LIBBLURAY,
                     "needs ffmpeg (drawtext, libx264), libdvdnav and "
                     "libbluray")
class TestDiscs(unittest.TestCase):
    """A slideshow of 120 short pictures: 99 chapters on the DVD, 120 on the
    Blu-ray."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-120-")
        pics = pictures(d, 13)
        slides = [{"image": os.path.basename(pics[k % 13]), "duration": 0.5}
                  for k in range(120)]
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump({"version": 1,
                       "disc": {"label": "LONG", "standard": "NTSC", "aspect": "16:9"},
                       "titles": [{"id": "show", "slideshow": {"slides": slides,
                                                               "transition": "none"}}]}, f)
        cls.dvd = os.path.join(d, "dvd")
        cls.dvd_run = run_cli("--json", "build", d, "-o", cls.dvd, "--fast")
        cls.bd = os.path.join(d, "bd")
        cls.bd_run = run_cli("build", d, "-o", cls.bd, "--format", "bluray", "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_dvd(self):
        rc, out, err = self.dvd_run
        self.assertEqual(rc, 0, err + out)
        self.assertIn("chapters 100-120 are part of chapter 99", out + err)
        with dvdnav_sim.DvdSim(os.path.join(self.dvd, "VIDEO_TS"), LIBDVDNAV) as d:
            self.assertEqual(d.num_parts(1), 99)

    def test_bluray(self):
        rc, out, err = self.bd_run
        self.assertEqual(rc, 0, err + out)
        with bluray_sim.Disc(LIBBLURAY, self.bd) as disc:
            disc.info()
            pl = disc.playlist(1)
        self.assertEqual(len(pl["chapters"]), 120)
        self.assertAlmostEqual(pl["duration"], 60, delta=0.2)
        self.assertAlmostEqual(pl["chapters"][100], 50, delta=0.05)


if __name__ == "__main__":
    unittest.main()
