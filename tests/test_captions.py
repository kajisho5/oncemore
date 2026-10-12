"""Closed captions (line 21, CEA-608) on a DVD.

The caption bytes (parity, row addresses, characters), pop-on captions from
subtitles, Scenarist files, the DVD user data in the video stream, and a
built disc whose captions ffmpeg's caption decoder reads back as the text.
"""

import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

from oncemore import captions as oncemore_captions, tools
from oncemore._vendor.dvdcc import captions
from oncemore._vendor.dvdcc.subtitles import Cue
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.scaffold import sample_project

from .helpers import have, json_lines, run_cli

DVD_OK = have("ffmpeg", "ffprobe") and tools.has_drawtext() and \
    tools.iso_tool()[0] is not None


def decode(path):
    """The captions ffmpeg's decoder reads from a file: [(start, end, text)]."""
    out = subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-f", "lavfi",
                          "-i", f"movie={path}[out0+subcc]", "-map", "0:1", "-f", "srt", "-"],
                         capture_output=True, text=True, check=True).stdout
    cues = []
    for block in out.strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) < 3:
            continue
        a, b = lines[1].split(" --> ")
        sec = lambda s: sum(float(x) * k for x, k in zip(s.replace(",", ".").split(":"), (3600, 60, 1)))  # noqa: E731
        text = re.sub(r"<[^>]+>|\{[^}]*\}", "", "\n".join(lines[2:]))
        cues.append((sec(a), sec(b), text))
    return cues


class TestBytes(unittest.TestCase):
    def test_parity_and_codes(self):
        self.assertEqual(captions.parity(0x14), 0x94)      # two bits set: parity bit added
        self.assertEqual(captions.parity(0x20), 0x20)      # one bit: already odd
        self.assertEqual(captions.EOC, (0x94, 0x2F))
        self.assertEqual(captions.pac(15), (0x94, 0xE0))   # row 15, white
        self.assertEqual(captions.pac(15, 8), (0x94, 0xF4))  # ... indented 8
        self.assertEqual(captions.pac(1), (0x91, 0x40))

    def test_text(self):
        pairs, dropped = captions.text_pairs("Año *")
        # A ñ o space, then '*' (no such character) as a space, padded with a null
        self.assertEqual(pairs, [captions.pair(0x41, 0x7E), captions.pair(0x6F, 0x20),
                                 captions.pair(0x20, 0x00)])
        self.assertEqual(dropped, 1)
        self.assertEqual(captions.wrap(["a " * 20]), ["a " * 15 + "a", "a a a a"])
        self.assertEqual(len(captions.wrap(["x"] * 6)), 4)

    def test_pop_on(self):
        s, notes = captions.from_cues([Cue(1.0, 3.0, ["Hi"]), Cue(4.0, 5.0, ["Again"])])
        f = s.frames
        start, end = captions.frame_of(1.0), captions.frame_of(3.0)
        self.assertEqual((f[start], f[start + 1]), (captions.EOC, captions.EOC))
        self.assertEqual(f[end], captions.EDM)
        loaded = [k for k in f if k < start]
        self.assertEqual(f[min(loaded)], captions.RCL)       # loading starts with RCL
        sent = [b for pr in f.values() for b in pr]
        self.assertIn(captions.parity(0x48), sent)            # "H"
        self.assertIn(captions.parity(0x69), sent)            # "i"
        self.assertEqual(notes, [])
        # too much text right after the previous one: shown late, said so
        long = ["x" * 32] * 4
        s, notes = captions.from_cues([Cue(1.0, 1.1, ["a"]), Cue(1.2, 3.0, long)])
        self.assertTrue(any("late" in n for n in notes), notes)

    def test_scc(self):
        s = captions.parse_scc("Scenarist_SCC V1.0\n\n00:00:01:00\t9420 9420 94ae\n\n"
                               "00:00:01;00\t942f\n")
        f = captions.frame_of(1.0)
        # the second line's start is taken: it goes on after the first
        self.assertEqual([s.frames[k] for k in range(f, f + 4)],
                         [(0x94, 0x20), (0x94, 0x20), (0x94, 0xAE), (0x94, 0x2F)])
        with self.assertRaises(ValueError):
            captions.parse_scc("1\n00:00:01,000 --> 00:00:02,000\nnot scc\n")

    def test_errors_are_oncemore_errors(self):
        # dvdcc's CaptionError reaches the project check as a ProjectError
        d = tempfile.mkdtemp(prefix="oncemore-cc-")
        self.addCleanup(shutil.rmtree, d, True)
        for name, text in (("bad.scc", "1\n00:00:01,000 --> 00:00:02,000\nnot scc\n"),
                           ("bad.txt", "1 00:00:01:00 00:00:02:00 missing.png\n")):
            path = os.path.join(d, name)
            with open(path, "w") as f:
                f.write(text)
            with self.assertRaises(ProjectError) as cm:
                oncemore_captions.load(path)
            self.assertIn(path, cm.exception.message)
        path = os.path.join(d, "ok.srt")
        with open(path, "w") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nHi\n")
        (s, notes), (want, want_notes) = oncemore_captions.load(path), captions.load(path)
        self.assertEqual((s.frames, notes), (want.frames, want_notes))
        self.assertTrue(s.frames)

    def test_user_data(self):
        d = captions.user_data([(0x94, 0x20), captions.FILLER])
        self.assertEqual(d, bytes.fromhex("000001b2434301f8" "84" "ff9420fe8080" "ff8080fe8080"))
        self.assertEqual(captions.gop_sizes(b"\0\0\1\xb8xxxx\0\0\1\0aa\0\0\1\0bb\0\0\1\xb8yyyy\0\0\1\0"),
                         [2, 1])


class TestProject(unittest.TestCase):
    def test_fields(self):
        d = sample_project()
        d["titles"][0]["captions"] = "media/cc.scc"
        d["titles"][1]["captions"] = {"file": "media/c.srt", "offset": "01;00;00;00"}
        p = build_project(d, "/virtual/project.oncemore.json", check_files=False)
        self.assertEqual(p.titles[0].captions, "/virtual/media/cc.scc")
        # (drop-frame timecode is clock time: an hour, near enough)
        self.assertAlmostEqual(p.titles[1].captions_offset, 3600, delta=0.01)
        d["disc"]["standard"] = "PAL"
        d["menus"] = []
        d["disc"]["first_play"] = "title:t1"
        with self.assertRaises(ProjectError) as cm:
            build_project(d, "/virtual/project.oncemore.json", check_files=False)
        self.assertIn("titles[0].captions", str(cm.exception.issues))


@unittest.skipUnless(have("ffmpeg"), "needs ffmpeg")
class TestStream(unittest.TestCase):
    def test_injected_and_decoded(self):
        d = tempfile.mkdtemp(prefix="oncemore-cc-")
        self.addCleanup(shutil.rmtree, d, True)
        m2v = os.path.join(d, "v.m2v")
        subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc2=size=720x480:rate=30000/1001:duration=6", "-target",
                        "ntsc-dvd", "-an", "-f", "mpeg2video", m2v], check=True)
        s, _ = captions.from_cues([Cue(1.0, 2.5, ["First one"]), Cue(3.0, 5.0, ["Two", "rows"])])
        self.assertEqual(captions.inject_file(m2v, s), 180)
        mpg = os.path.join(d, "v.mpg")
        subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-fflags",
                        "+genpts", "-i", m2v, "-c", "copy", "-f", "dvd", mpg], check=True)
        got = decode(mpg)
        self.assertEqual([c[2] for c in got], ["First one", "Two\nrows"])
        # (a GOP's captions are read at its start: within a GOP, 0.6 s)
        for (a, b, _), want in zip(got, ((1.0, 2.5), (3.0, 5.0))):
            self.assertLess(abs(a - want[0]), 0.7)
            self.assertLess(abs(b - want[1]), 0.7)


@unittest.skipUnless(DVD_OK, "needs ffmpeg (drawtext) and an ISO tool")
class TestDisc(unittest.TestCase):
    """The sample disc: the first title captioned from SubRip, the second
    from a Scenarist file."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-ccdisc-")
        rc, _, err = run_cli("init", "s", cwd=cls.tmp)
        assert rc == 0, err
        cls.dir = os.path.join(cls.tmp, "s")
        with open(os.path.join(cls.dir, "media", "c.srt"), "w") as f:
            f.write("1\n00:00:02,000 --> 00:00:04,000\nHello captions\n\n"
                    "2\n00:00:06,000 --> 00:00:08,000\nSecond one\n")
        with open(os.path.join(cls.dir, "media", "c.scc"), "w") as f:
            # pop-on "OK" at 2 s: RCL ENM PAC(row 15) "OK" EOC, erased at 4 s
            f.write("Scenarist_SCC V1.0\n\n00:00:01:00\t9420 9420 94ae 94ae 94e0 94e0 4fcb "
                    "942f 942f\n\n00:00:04:00\t942c 942c\n")
        path = os.path.join(cls.dir, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["titles"][0]["captions"] = "media/c.srt"
        data["titles"][1]["captions"] = {"file": "media/c.scc"}
        with open(path, "w") as f:
            json.dump(data, f)
        cls.out = os.path.join(cls.tmp, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli("build", cls.dir, "-o", cls.out, "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_read_back(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        vts = os.path.join(self.out, "VIDEO_TS")
        got = decode(os.path.join(vts, "VTS_01_1.VOB"))
        texts = [c[2] for c in got]
        self.assertEqual(texts[:2], ["Hello captions", "Second one"])
        self.assertIn("OK", texts[2:])
        self.assertLess(abs(got[0][0] - 2.0), 0.7)
        # the titleset says it has line-21 captions (field 1)
        with open(os.path.join(vts, "VTS_01_0.IFO"), "rb") as f:
            ifo = f.read()
        self.assertTrue(ifo[0x201] & 0x80)
        self.assertEqual(struct.unpack(">H", ifo[0x200:0x202])[0] & 0x40, 0)   # (not field 2)

    def test_film_refused(self):
        d = os.path.join(self.tmp, "film")
        os.makedirs(d)
        subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "testsrc2=size=720x480:rate=24000/1001:duration=2",
                        os.path.join(d, "film.mp4")], check=True)
        shutil.copy(os.path.join(self.dir, "media", "c.srt"), d)
        with open(os.path.join(d, "project.oncemore.json"), "w") as f:
            json.dump({"version": 1, "disc": {"label": "F", "standard": "NTSC", "aspect": "4:3",
                                              "first_play": "title:f"},
                       "titles": [{"id": "f", "source": "film.mp4", "captions": "c.srt"}]}, f)
        rc, out, _ = run_cli("--json", "validate", d)
        self.assertNotEqual(rc, 0)
        issues = {i["path"]: i["message"] for e in json_lines(out) for i in e.get("issues", [])}
        self.assertIn("3:2 pulldown", issues["titles[0].captions"])


if __name__ == "__main__":
    unittest.main()
