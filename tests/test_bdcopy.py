"""A source's H.264 picture used as it is on a Blu-ray (transcode: false).

What may be copied (bluray.copy_compliance, the field coding read from the
sequence parameter set), the bitrate plan with a copied picture, and a disc
whose copied pictures decode to the source's frames, with their parameter
sets where a Blu-ray stream has them, read by libbluray.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from fractions import Fraction

from oncemore import bluray, tools

from .helpers import have, run_cli

try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None


def ffmpeg_lists(kind):
    try:
        return subprocess.run([tools.find("ffmpeg"), "-hide_banner", f"-{kind}"],
                              capture_output=True, text=True).stdout.split()
    except Exception:
        return []


X264 = have("ffmpeg", "ffprobe") and "libx264" in ffmpeg_lists("encoders") and \
    {"h264_mp4toannexb", "filter_units", "dump_extra"} <= set(ffmpeg_lists("bsfs"))

GOOD = {"codec": "h264", "profile": "High", "level": 41, "pix_fmt": "yuv420p", "width": 1920,
        "height": 1080, "sar": Fraction(1), "fps": 24000 / 1001, "gop": 24,
        "video_bit_rate": 20_000_000, "fields": False}


class TestCompliance(unittest.TestCase):
    def test_film(self):
        self.assertEqual(bluray.copy_compliance(GOOD, (24000, 1001)), [])

    def test_refused(self):
        for change, fps, why in (
                ({"codec": "mpeg2video"}, (24000, 1001), "not H.264"),
                ({"profile": "Constrained Baseline"}, (24000, 1001), "not High or Main"),
                ({"level": 42}, (24000, 1001), "level is 4.2"),
                ({"width": 1280, "height": 720}, (24000, 1001), "not 1920x1080"),
                ({"sar": Fraction(4, 3)}, (24000, 1001), "square pixels"),
                ({"fps": 25.0}, (24000, 1001), "frame rate is 25.000"),
                ({"gop": 250}, (24000, 1001), "250 frames long"),
                ({"gop": None}, (24000, 1001), "key frames cannot be found"),
                ({"video_bit_rate": 45_000_000}, (24000, 1001), "45.0 Mbit/s"),
                # 29.97 is 1080i: frames-only coding cannot be copied
                ({"fps": 30000 / 1001, "gop": 30}, (30000, 1001), "not coded for fields")):
            with self.subTest(why=why):
                reasons = bluray.copy_compliance(dict(GOOD, **change), fps)
                self.assertTrue(any(why in r for r in reasons), reasons)

    def test_1080i(self):
        info = dict(GOOD, fps=30000 / 1001, gop=30, fields=True)
        self.assertEqual(bluray.copy_compliance(info, (30000, 1001)), [])
        self.assertEqual(bluray.copy_compliance(dict(info, fps=25.0, gop=25), (25, 1)), [])


class TestPlan(unittest.TestCase):
    def test_copied_picture_keeps_its_rate(self):
        hour, cap = 3600, bluray.CAPACITY["BD25"]
        shared = bluray.plan([(hour, 640_000), (hour, 640_000)], cap)
        # the second title's own 30 Mbit/s leaves the first less room
        mixed = bluray.plan([(hour, 640_000), (hour, 640_000, 30_000_000)], cap)
        self.assertLess(mixed["max_bps"], shared["max_bps"])
        self.assertEqual(mixed["total_seconds"], hour)            # (only the encoded one)
        # only copied pictures: nothing to share out
        alone = bluray.plan([(hour, 640_000, 30_000_000)], cap)
        self.assertEqual(alone["max_bps"], bluray.MAX_VIDEO_BPS)
        self.assertGreater(alone["estimated_bytes"], hour * 30_000_000 / 8)
        with self.assertRaises(Exception):
            bluray.plan([(3 * hour, 640_000, 30_000_000)], cap)    # does not fit


def make(path, rate, x264, profile=("-profile:v", "high")):
    subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi",
                    "-i", f"testsrc2=size=1920x1080:rate={rate}:duration=3", "-f", "lavfi",
                    "-i", "sine=d=3:r=48000", "-c:v", "libx264", "-preset", "veryfast",
                    *profile, "-level", "4.1", "-maxrate", "30M", "-bufsize", "30M",
                    "-x264-params", x264, "-pix_fmt", "yuv420p", "-c:a", "ac3", "-ac", "2",
                    path], check=True)


def frames(path):
    """A digest of every decoded picture of a file's video."""
    out = subprocess.run([tools.find("ffmpeg"), "-v", "error", "-i", path, "-map", "0:v",
                          "-f", "framemd5", "-"], capture_output=True, text=True, check=True).stdout
    return [line.rsplit(",", 1)[1].strip() for line in out.splitlines()
            if line and not line.startswith("#")]


def nal_types(m2ts, count=12):
    """The first H.264 NAL unit types of a Blu-ray stream's video."""
    with open(m2ts, "rb") as f:
        data = f.read()
    es = bytearray()
    for i in range(0, len(data), 192):
        p = data[i + 4:i + 192]
        if ((p[1] & 0x1F) << 8 | p[2]) != bluray.VIDEO_PID:
            continue
        payload = p[4 + (1 + p[4] if p[3] & 0x20 else 0):]
        if p[1] & 0x40:                                   # a PES packet starts here
            payload = payload[9 + payload[8]:]
        es += payload
    out, at = [], 0
    while len(out) < count:
        at = es.find(b"\0\0\1", at)
        if at < 0:
            break
        out.append(es[at + 3] & 0x1F)
        at += 3
    return out


BD = "bluray-compat=1:slices=4:aud=1:nal-hrd=vbr:min-keyint=1:force-cfr=1"


@unittest.skipUnless(X264, "needs ffmpeg with libx264 and its H.264 bitstream filters")
class TestDisc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = d = tempfile.mkdtemp(prefix="oncemore-bdcopy-")
        make(os.path.join(d, "film.mp4"), "24000/1001", BD + ":keyint=24")
        make(os.path.join(d, "fields.mp4"), "30000/1001",
             BD + ":keyint=30:fake-interlaced=1:pic-struct=1")
        make(os.path.join(d, "frames.mp4"), "30000/1001", "keyint=30")
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump({"version": 1,
                       "disc": {"label": "COPY", "standard": "NTSC", "aspect": "16:9",
                                "first_play": "title:film"},
                       "titles": [{"id": "film", "source": "film.mp4", "transcode": False,
                                   "chapters": [0, 1, 2]},
                                  {"id": "fields", "source": "fields.mp4", "transcode": False},
                                  {"id": "frames", "source": "frames.mp4", "transcode": False}]},
                      f)
        cls.out = os.path.join(d, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", d, "-o", cls.out, "--format", "bluray",
                                                 "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def stream(self, n):
        return os.path.join(self.out, "BDMV", "STREAM", f"{n:05d}.m2ts")

    def test_fields_read_from_the_stream(self):
        self.assertIs(bluray.coded_for_fields(os.path.join(self.tmp, "film.mp4")), False)
        self.assertIs(bluray.coded_for_fields(os.path.join(self.tmp, "fields.mp4")), True)
        self.assertIsNone(bluray.coded_for_fields(os.path.join(self.tmp, "nothing.mp4")))

    def test_copied(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        log = self.stdout + self.stderr
        self.assertIn("'film' in HD (3.0s, picture copied)", log)
        self.assertIn("'fields' in HD (3.0s, picture copied)", log)
        # the same pictures, decoded
        for n, name in ((1, "film"), (2, "fields")):
            self.assertEqual(frames(self.stream(n)), frames(os.path.join(self.tmp, name + ".mp4")))
        # a key picture: delimiter, parameter sets, then the SEI and slices
        for n in (1, 2):
            types = nal_types(self.stream(n))
            self.assertEqual(types[:3], [9, 7, 8], types)
            self.assertLess(types.index(8), types.index(6))
            self.assertIn(5, types)

    def test_frames_only_encoded_again(self):
        log = self.stdout + self.stderr
        self.assertIn("titles[2].transcode: the picture is encoded for the Blu-ray anyway", log)
        self.assertIn("not coded for fields", log)
        self.assertNotIn("'frames' in HD (3.0s, picture copied)", log)

    @unittest.skipUnless(LIBBLURAY, "libbluray not installed")
    def test_read_by_libbluray(self):
        with bluray_sim.Disc(LIBBLURAY, self.out) as disc:
            self.assertTrue(disc.info()["bluray"])
            film = disc.playlist(1)
            # 1080p 23.976 (format 6, rate 1); chapters on the source's key frames
            self.assertEqual(film["video"], [(bluray.CODING_H264, 6, 1)])
            self.assertEqual(len(film["chapters"]), 3)
            for want, got in zip((0, 1, 2), film["chapters"]):
                self.assertLess(abs(got - want), 0.05)
            self.assertAlmostEqual(film["duration"], 3, delta=0.1)
            # 29.97: 1080i (format 4, rate 4)
            self.assertEqual(disc.playlist(2)["video"], [(bluray.CODING_H264, 4, 4)])


if __name__ == "__main__":
    unittest.main()
