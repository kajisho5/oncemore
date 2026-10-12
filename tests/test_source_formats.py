"""Sources the classic apps take besides the common ones (DECISIONS §102):
MPEG-2 video elementary streams (.m2v, delivered apart from their sound),
MPEG audio (.mp2, .mpa), Windows Media Audio (.wma), and GIF and Targa
(.tga) stills, as menu backgrounds, slides and image-script subtitles."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from fractions import Fraction

from oncemore import encode, subtitles, tools
from oncemore.gui.server import media_kind
from oncemore.project import is_image

from .helpers import have, json_lines, run_cli

FF = ["ffmpeg", "-v", "error", "-y"]


def ffprobe_streams(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)["streams"]


class TestKinds(unittest.TestCase):
    def test_extensions(self):
        for name, kind in (("a.m2v", "video"), ("a.MP2", "audio"), ("a.mpa", "audio"),
                           ("a.wma", "audio"), ("a.gif", "image"), ("a.TGA", "image")):
            self.assertEqual(media_kind(name), kind, name)
        self.assertTrue(is_image("a.GIF") and is_image("b.tga"))
        self.assertTrue(subtitles.IMAGE_FILE.search("sub0001.gif"))
        self.assertTrue(subtitles.IMAGE_FILE.search("sub0001.TGA"))

    def test_still_input(self):
        # (the gif demuxer has no -loop; image2 reads a GIF's first picture)
        self.assertEqual(tools.still_input("m/a.GIF"), ["-f", "image2", "-c:v", "gif"])
        self.assertEqual(tools.still_input("m/a.png"), [])
        self.assertEqual(tools.still_input("m/a.tga"), [])


def make_media(d):
    run = lambda *a: subprocess.run(FF + list(a), check=True)
    run("-f", "lavfi", "-i", "testsrc2=size=720x480:rate=30000/1001:duration=3",
        "-c:v", "mpeg2video", "-b:v", "6M", os.path.join(d, "v.m2v"))
    run("-f", "lavfi", "-i", "sine=f=440:d=3", "-ar", "48000", "-c:a", "mp2", os.path.join(d, "a.mp2"))
    shutil.copy(os.path.join(d, "a.mp2"), os.path.join(d, "a.mpa"))
    run("-f", "lavfi", "-i", "sine=f=660:d=3", "-c:a", "wmav2", os.path.join(d, "b.wma"))
    # an animated GIF (three pictures) and a Targa still
    run("-f", "lavfi", "-i", "testsrc2=size=720x480:rate=3:duration=1", os.path.join(d, "bg.gif"))
    run("-f", "lavfi", "-i", "testsrc=size=720x480", "-frames:v", "1", os.path.join(d, "s.tga"))
    # an image-script subtitle as a GIF with a transparent surround
    run("-f", "lavfi", "-i", "color=c=black@0:s=300x60:d=0.1,format=rgba", "-f", "lavfi", "-i",
        "color=c=white:s=200x30:d=0.1", "-filter_complex",
        "[0][1]overlay=50:15,split[a][b];[a]palettegen=reserve_transparent=1[p];"
        "[b][p]paletteuse=alpha_threshold=128", "-frames:v", "1", os.path.join(d, "sub1.gif"))
    with open(os.path.join(d, "subs.txt"), "w") as f:
        f.write("1 00;00;00;15 00;00;02;00 sub1.gif\n")


@unittest.skipUnless(have("ffmpeg", "ffprobe"), "needs ffmpeg")
class TestProbe(unittest.TestCase):
    def test_elementary_stream_length(self):
        # a .m2v carries no length of its own; the end of its last picture gives it
        d = tempfile.mkdtemp(prefix="oncemore-m2v-")
        self.addCleanup(shutil.rmtree, d, True)
        make_media(d)
        info = encode.probe(os.path.join(d, "v.m2v"))
        self.assertEqual((info["has_video"], info["has_audio"]), (True, False))
        self.assertAlmostEqual(info["duration"], 3.003, places=2)
        # (its average rate reads as the demuxer's default, 25)
        self.assertEqual(info["fps"], Fraction(30000, 1001))
        self.assertAlmostEqual(encode.probe(os.path.join(d, "b.wma"))["duration"], 3.0, places=1)


@unittest.skipUnless(have("ffmpeg", "ffprobe") and tools.has_drawtext(), "needs ffmpeg with drawtext")
class TestDvd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-fmt-")
        d = os.path.join(cls.tmp, "p")
        os.makedirs(d)
        make_media(d)
        project = {"version": 1,
                   "disc": {"label": "FORMATS", "standard": "NTSC", "aspect": "4:3", "first_play": "menu:m"},
                   "menus": [{"id": "m", "background": "bg.gif", "buttons": [
                       {"id": "a", "label": "PLAY", "x": 100, "y": 300, "action": "title:t"},
                       {"id": "b", "label": "PICTURES", "x": 100, "y": 360, "action": "title:s"}]}],
                   "titles": [{"id": "t", "source": "v.m2v",
                               "audio_tracks": [{"source": "a.mp2", "lang": "en"},
                                                {"source": "b.wma", "lang": "ja"},
                                                {"source": "a.mpa", "lang": "fr"}],
                               "subtitles": [{"file": "subs.txt", "lang": "en"}]},
                              {"id": "s", "slideshow": {"slides": [{"image": "s.tga"},
                                                                   {"image": "bg.gif"}]}}]}
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump(project, f)
        cls.out = os.path.join(cls.tmp, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--fast", "--json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)

    def vobs(self):
        vts = os.path.join(self.out, "VIDEO_TS")
        return [os.path.join(vts, n) for n in sorted(os.listdir(vts))
                if n.endswith("_1.VOB") and n.startswith("VTS_")]

    def test_streams(self):
        found = [[s["codec_type"] + ":" + s["codec_name"] for s in ffprobe_streams(v)
                  if s["codec_type"] != "data"] for v in self.vobs()]
        # the .m2v with its three separate tracks (made AC-3) and the GIF subtitle
        self.assertIn(sorted(["video:mpeg2video", "audio:ac3", "audio:ac3", "audio:ac3",
                              "subtitle:dvd_subtitle"]), [sorted(x) for x in found])

    def test_lengths(self):
        titles = {t["id"]: t for t in json_lines(self.stdout)[-1]["titles"]}
        self.assertAlmostEqual(titles["t"]["duration"], 3.003, places=2)
        self.assertEqual(titles["t"]["input"], "720x480@29.970")
        self.assertEqual(len(titles["t"]["audio_tracks"]), 3)


@unittest.skipUnless(have("ffmpeg"), "needs ffmpeg")
class TestEditorPictures(unittest.TestCase):
    def test_targa_is_sent_as_png(self):
        from .test_gui import GuiServer
        d = tempfile.mkdtemp(prefix="oncemore-fmt-gui-")
        self.addCleanup(shutil.rmtree, d, True)
        s = GuiServer(d)
        self.addCleanup(s.close)
        s.call("/api/new", "POST", {"sample": True})
        subprocess.run(FF + ["-f", "lavfi", "-i", "testsrc=size=64x48", "-frames:v", "1",
                             os.path.join(d, "media", "s.tga")], check=True)
        shutil.copy(os.path.join(d, "media", "menu_bg.png"), os.path.join(d, "media", "c.gif"))
        status, body = s.call("/api/file?path=media/s.tga")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"\x89PNG\r\n\x1a\n"))
        # a GIF the browser draws as it is
        status, body = s.call("/api/file?path=media/c.gif")
        with open(os.path.join(d, "media", "c.gif"), "rb") as f:
            self.assertEqual((status, body), (200, f.read()))


if __name__ == "__main__":
    unittest.main()
