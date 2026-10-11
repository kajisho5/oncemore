"""Image scripts: subtitles that are pictures (a text script whose text is a
picture file), in their own colours.

Reading the script, reducing a picture to the colours a disc allows, and
discs: the DVD's subpictures drawn in the IFO's palette show the pictures'
colours where the pictures are; a title with too many colours is refused;
the Blu-ray's PGS stream carries the pictures' colours.
"""

import json
import os
import shutil
import struct
import subprocess
import tempfile
import unittest

from oncemore import pgs, subtitles, tools
from oncemore.errors import ProjectError

from .helpers import have, run_cli

DVD_OK = have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext()


def rgba_frame(W, H, boxes):
    """A transparent W x H RGBA frame with filled boxes (x, y, w, h, rgba)."""
    px = bytearray(W * H * 4)
    for x, y, w, h, c in boxes:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                px[4 * (yy * W + xx):4 * (yy * W + xx) + 4] = bytes(c)
    return bytes(px)


class TestScript(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-isub-")
        self.addCleanup(shutil.rmtree, self.dir, True)
        for name in ("a.png", "B.BMP"):
            open(os.path.join(self.dir, name), "wb").close()

    def test_pictures_and_text(self):
        text = ("1 00;00;01;00 00;00;02;00 a.png\n"
                "2 00;00;03;00 00;00;04;00 B.BMP\n"
                "3 00;00;05;00 00;00;06;00 Just text.png and more\n"
                "4 00;00;07;00 00;00;08;00 a.png\nsecond line\n")
        cues = subtitles.parse_text_script(text, "NTSC", self.dir)
        self.assertEqual([c.image and os.path.basename(c.image) for c in cues],
                         ["a.png", "B.BMP", None, None])
        self.assertEqual(cues[0].lines, [])
        self.assertEqual(cues[0].image, os.path.join(self.dir, "a.png"))
        # (a picture's name with more text, or a second line, is text)
        self.assertEqual(cues[3].lines, ["a.png", "second line"])
        # without the script's folder it is all text
        self.assertEqual(subtitles.parse_text_script(text, "NTSC")[0].lines, ["a.png"])
        # written back as an image script; SubRip has no pictures
        self.assertTrue(subtitles.to_text_script(cues).startswith(
            "1\t00;00;01;00\t00;00;02;00\ta.png\n2\t00;00;03;00\t00;00;04;00\tB.BMP\n"))
        self.assertNotIn("a.png\n\n", subtitles.to_srt(cues))
        self.assertEqual(subtitles.to_srt(cues).count("-->"), 2)
        # the offset keeps the picture
        self.assertEqual(subtitles.shifted(cues, 0.5)[0].image, cues[0].image)

    def test_loaded_next_to_the_script(self):
        path = os.path.join(self.dir, "s.txt")
        with open(path, "w") as f:
            f.write("1 00:00:01:00 00:00:02:00 a.png\n")
        self.assertEqual(subtitles.load_subtitles(path, "PAL")[0].image,
                         os.path.join(self.dir, "a.png"))
        with open(path, "w") as f:
            f.write("1 00:00:01:00 00:00:02:00 missing.png\n")
        with self.assertRaises(ProjectError) as cm:
            subtitles.load_subtitles(path)
        self.assertIn("'missing.png' not found", str(cm.exception))


class TestColours(unittest.TestCase):
    RED, WHITE, BLACK, GREY = (250, 0, 0, 255), (255, 255, 255, 255), (0, 0, 0, 255), \
        (128, 128, 128, 255)

    def test_commonest_kept_others_nearest(self):
        # red 40 px, white 20, black 10, a near-red 2 (goes to red)
        rgba = rgba_frame(20, 10, [(3, 1, 10, 4, self.RED), (3, 5, 10, 2, self.WHITE),
                                   (3, 7, 5, 2, self.BLACK), (13, 1, 1, 2, (240, 10, 0, 255))])
        idx, w, h, x, y, colours = subtitles.reduce_colours(rgba, 20, 10, 3, even=True)
        self.assertEqual(colours, [self.RED, self.WHITE, self.BLACK])
        self.assertEqual((x, y), (2, 0))                   # even start
        self.assertEqual((w % 2, h % 2), (0, 0))
        at = lambda xx, yy: idx[(yy - y) * w + (xx - x)]   # noqa: E731
        self.assertEqual((at(4, 2), at(4, 5), at(4, 7), at(13, 1), at(2, 0)), (1, 2, 3, 1, 0))

    def test_opacity_steps(self):
        rgba = rgba_frame(4, 2, [(0, 0, 2, 2, (0, 255, 0, 255)), (2, 0, 2, 2, (0, 255, 0, 60))])
        idx, *_, colours = subtitles.reduce_colours(rgba, 4, 2, 255, alpha_steps=8)
        self.assertEqual(sorted(c[3] for c in colours), [73, 255])
        # all or nothing: the faint half is gone
        idx, w, h, x, y, colours = subtitles.reduce_colours(rgba, 4, 2, 3)
        self.assertEqual((w, colours), (2, [(0, 255, 0, 255)]))
        self.assertEqual(subtitles.reduce_colours(bytes(32), 4, 2, 3)[0], None)

    def test_pgs_palette(self):
        entries = pgs.picture_palette([(255, 0, 0, 255), (0, 0, 0, 128)])
        self.assertEqual(entries[0], (0, 16, 128, 128, 0))
        y, cb, cr = pgs.ycbcr((255, 0, 0))
        self.assertEqual(entries[1], (1, y, cr, cb, 255))
        self.assertEqual(entries[2], (2, 16, 128, 128, 128))


def make_pictures(d):
    """A frame-sized bitmap with no transparency (black is keyed out): a red
    box in a white frame low in the picture; and a small picture with
    transparency: a green box."""
    ff = [tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i"]
    subprocess.run(ff + ["color=c=black:s=720x480,drawbox=x=260:y=400:w=200:h=40:color=red:t=fill,"
                         "drawbox=x=256:y=396:w=208:h=48:color=white:t=4",
                         "-frames:v", "1", os.path.join(d, "full.bmp")], check=True)
    subprocess.run(ff + ["color=c=lime:s=180x30,format=rgba,pad=200:50:10:10:color=black@0",
                         "-frames:v", "1", os.path.join(d, "inset.png")], check=True)
    with open(os.path.join(d, "script.txt"), "w") as f:
        f.write("1 00;00;00;15 00;00;01;15 full.bmp\n"
                "2 00;00;02;00 00;00;03;00 inset.png\n"
                "3 00;00;03;10 00;00;04;00 Plain text too\n")


def write_project(d, aspect, subs="subs/script.txt"):
    with open(os.path.join(d, "project.oncemore.json"), "w") as f:
        json.dump({"version": 1,
                   "disc": {"label": "ISUB", "standard": "NTSC", "aspect": aspect,
                            "first_play": "title:t"},
                   "titles": [{"id": "t", "source": "grey.mp4",
                               "subtitles": [{"file": subs, "lang": "en", "default": True}]}]}, f)


def grey_video(d, size):
    subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi",
                    "-i", f"color=c=gray:s={size}:rate=30000/1001:d=5", "-f", "lavfi", "-i",
                    "sine=d=5:r=48000", "-c:v", "mpeg4", "-q:v", "3", "-c:a", "aac",
                    os.path.join(d, "grey.mp4")], check=True)


def ifo_palette(vts_ifo):
    """The first title PGC's 16 subpicture colours as RGB hex (for ffmpeg)."""
    with open(vts_ifo, "rb") as f:
        ifo = f.read()
    pgci = struct.unpack(">I", ifo[0xCC:0xD0])[0] * 2048
    pgc = pgci + struct.unpack(">I", ifo[pgci + 12:pgci + 16])[0]
    out = []
    for k in range(16):
        _, y, cr, cb = ifo[pgc + 0xA4 + 4 * k:pgc + 0xA8 + 4 * k]
        rgb = (y + 1.402 * (cr - 128), y - 0.344 * (cb - 128) - 0.714 * (cr - 128),
               y + 1.772 * (cb - 128))
        out.append("%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in rgb))
    return ",".join(out)


@unittest.skipUnless(DVD_OK, "needs ffmpeg (drawtext), dvdauthor and spumux")
class TestDvd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-isub-dvd-")
        os.makedirs(os.path.join(d, "subs"))
        make_pictures(os.path.join(d, "subs"))
        grey_video(d, "720x480")
        write_project(d, "4:3")
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def pixels(self, t, points):
        vts = os.path.join(self.out, "VIDEO_TS")
        raw = subprocess.run([tools.find("ffmpeg"), "-v", "error", "-palette",
                              ifo_palette(os.path.join(vts, "VTS_01_0.IFO")), "-i",
                              os.path.join(vts, "VTS_01_1.VOB"), "-filter_complex",
                              "[0:v][0:s:0]overlay[o]", "-map", "[o]", "-ss", str(t),
                              "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        return [tuple(raw[(y * 720 + x) * 3:(y * 720 + x) * 3 + 3]) for x, y in points]

    def assertColour(self, got, want, tol=40):
        self.assertTrue(all(abs(a - b) <= tol for a, b in zip(got, want)), (got, want))

    def test_pictures_in_their_colours(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        # the full-frame bitmap: red inside white, the keyed black not drawn
        red, white, keyed = self.pixels(1.0, [(360, 420), (258, 398), (100, 100)])
        self.assertColour(red, (255, 0, 0))
        self.assertColour(white, (255, 255, 255))
        self.assertColour(keyed, (128, 128, 128))
        # the small picture, at the bottom margin, centred
        green, above = self.pixels(2.5, [(360, 420), (360, 380)])
        self.assertColour(green, (0, 255, 0))
        self.assertColour(above, (128, 128, 128))

    def test_too_many_colours(self):
        d = os.path.join(self.tmp, "many")
        os.makedirs(os.path.join(d, "subs"), exist_ok=True)
        shutil.copy(os.path.join(self.tmp, "grey.mp4"), d)
        lines = []
        for k in range(6):                   # 6 pictures x 3 colours of their own
            c = [f"0x{(40 * k + 10 * j) % 256:02x}{(200 - 30 * k) % 256:02x}{30 * j:02x}"
                 for j in range(3)]
            subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f",
                            "lavfi", "-i", f"color=c={c[0]}:s=60x20,format=rgba,"
                            f"drawbox=x=0:y=0:w=20:h=20:color={c[1]}:t=fill,"
                            f"drawbox=x=40:y=0:w=20:h=20:color={c[2]}:t=fill",
                            "-frames:v", "1", os.path.join(d, "subs", f"p{k}.png")], check=True)
            lines.append(f"{k + 1} 00;00;0{k // 2};{(k % 2) * 15:02d} "
                         f"00;00;0{k // 2};{(k % 2) * 15 + 10:02d} p{k}.png")
        with open(os.path.join(d, "subs", "script.txt"), "w") as f:
            f.write("\n".join(lines) + "\n")
        write_project(d, "4:3")
        rc, out, err = run_cli("build", d, "-o", os.path.join(d, "out"), "--fast")
        self.assertNotEqual(rc, 0)
        self.assertIn("subpicture colours (a DVD title has 16)", out + err)


def ffmpeg_has_x264():
    try:
        return "libx264" in subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-encoders"],
                                           capture_output=True, text=True).stdout
    except Exception:
        return False


@unittest.skipUnless(have("ffmpeg", "ffprobe") and tools.has_drawtext() and ffmpeg_has_x264(),
                     "needs ffmpeg with drawtext and libx264")
class TestBluray(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-isub-bd-")
        os.makedirs(os.path.join(d, "subs"))
        make_pictures(os.path.join(d, "subs"))
        grey_video(d, "1280x720")
        write_project(d, "16:9")
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--format", "bluray",
                                                 "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_pgs_carries_the_pictures(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        sup = os.path.join(self.tmp, "track.sup")
        subprocess.run([tools.find("ffmpeg"), "-v", "error", "-y", "-i",
                        os.path.join(self.out, "BDMV", "STREAM", "00001.m2ts"), "-map", "0:s:0",
                        "-c", "copy", "-f", "sup", sup], check=True)
        with open(sup, "rb") as f:
            shown = [c for c in pgs.decode(f.read()) if c[1]]
        self.assertEqual(len(shown), 3)

        def colours(comp):
            return {(e[0], e[1], e[2]) for e in comp[2].values() if e[3] == 255}
        y, cb, cr = pgs.ycbcr((255, 0, 0))
        # the full-frame bitmap, scaled to 1920 x 1080: red, low in the frame
        (x, top, w, h, _), = shown[0][1]
        self.assertTrue(any(abs(e[0] - y) <= 4 and abs(e[1] - cr) <= 4 and abs(e[2] - cb) <= 4
                            for e in colours(shown[0])), shown[0][2])
        self.assertTrue(660 <= x <= 700 and 870 <= top <= 900 and w > 500, (x, top, w, h))
        # the small picture keeps its size (square pixels) and sits at the margin
        (x, top, w, h, _), = shown[1][1]
        y, cb, cr = pgs.ycbcr((0, 255, 0))
        self.assertTrue(any(abs(e[0] - y) <= 4 and abs(e[1] - cr) <= 4 for e in colours(shown[1])))
        self.assertEqual((w, h), (180, 30))
        self.assertEqual(x, (1920 - 200) // 2 + 10)


if __name__ == "__main__":
    unittest.main()
