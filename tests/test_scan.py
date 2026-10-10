"""Interlaced output and soft 3:2 pulldown: mode choice, filters, the
pulldown bit patching, and chapter timing for film titles."""

import types
import unittest

from oncemore import author, encode, pulldown
from oncemore.errors import ProjectError
from oncemore.project import build_project, gop_limits, keyframe_plan, title_fps
from oncemore.scaffold import sample_project


def project(standard="NTSC", **title):
    d = sample_project(standard=standard)
    d["titles"][0].update(title)
    return build_project(d, "/virtual/project.oncemore.json", check_files=False)


def info(fps, interlaced=False, w=1920, h=1080, sar=1):
    return {"width": w, "height": h, "sar": sar, "fps": fps, "interlaced": interlaced,
            "has_video": True, "duration": 10}


class TestMode(unittest.TestCase):
    def test_auto(self):
        p = project()
        t, ntsc = p.titles[0], p.disc
        cases = [(info(24000 / 1001), "pulldown"),
                 (info(29.97, interlaced=True), "interlaced"),
                 (info(59.94, interlaced=True), "interlaced"),     # field rate reported
                 (info(59.94), "interlaced"),
                 (info(29.97), "progressive"),
                 (info(25, interlaced=True), "progressive"),       # PAL video on NTSC
                 (info(24), "progressive")]                        # true 24 is not film rate
        for i, want in cases:
            self.assertEqual(encode.video_mode(t, i, ntsc), want, i)
        pal = project("PAL")
        tp = pal.titles[0]
        self.assertEqual(encode.video_mode(tp, info(24000 / 1001), pal.disc), "progressive")
        self.assertEqual(encode.video_mode(tp, info(25, interlaced=True), pal.disc), "interlaced")
        self.assertEqual(encode.video_mode(tp, info(50), pal.disc), "interlaced")

    def test_forced(self):
        p = project(scan="progressive")
        self.assertEqual(encode.video_mode(p.titles[0], info(59.94), p.disc), "progressive")
        p = project(scan="pulldown")
        self.assertEqual(encode.video_mode(p.titles[0], info(29.97), p.disc), "pulldown")
        with self.assertRaises(ProjectError) as cm:
            project("PAL", scan="pulldown")
        self.assertIn("NTSC", str(cm.exception.issues))

    def test_filters(self):
        d = project().disc
        vf = encode.fit_filter(info(29.97, interlaced=True), d, mode="interlaced")
        self.assertTrue(vf.startswith("bwdif=mode=send_field,fps=60000/1001,scale=720:480"), vf)
        self.assertIn("interlace=scan=tff:lowpass=complex,setfield=tff", vf)
        # same size: the original fields pass through without a low-pass
        vf = encode.fit_filter(info(29.97, interlaced=True, w=720, h=480, sar=32 / 27), d, mode="interlaced")
        self.assertIn("lowpass=off", vf)
        vf = encode.fit_filter(info(59.94), d, mode="interlaced")
        self.assertTrue(vf.startswith("fps=60000/1001,"), vf)
        vf = encode.fit_filter(info(24000 / 1001, w=1280, h=720), d, mode="pulldown")
        self.assertIn("fps=24000/1001", vf)
        self.assertNotIn("interlace", vf)
        self.assertEqual(encode.fit_filter(info(29.97), d), encode.fit_filter(info(29.97), d,
                                                                              mode="progressive"))


class TestPulldownBits(unittest.TestCase):
    @staticmethod
    def stream(temporal_refs_per_gop):
        """A skeleton MPEG-2 stream: headers only, progressive 23.976."""
        seq = b"\x00\x00\x01\xB3" + bytes([0x2D, 0x01, 0xE0, 0x31, 0xFF, 0xFF, 0xE0, 0x00])
        seq_ext = b"\x00\x00\x01\xB5" + bytes([0x14, 0x8A, 0x00, 0x01, 0x00, 0x00])
        out = seq + seq_ext
        for refs in temporal_refs_per_gop:
            out += b"\x00\x00\x01\xB8" + bytes([0x00, 0x08, 0x00, 0x00])
            for tr in refs:
                out += b"\x00\x00\x01\x00" + bytes([tr >> 2, (tr & 3) << 6 | 0x08, 0, 0])
                # picture coding extension: progressive frame, frame picture, tff=0 rff=0
                out += b"\x00\x00\x01\xB5" + bytes([0x8F, 0xFF, 0xF3, 0x41, 0x80, 0x00])
        return bytearray(out)

    def flags(self, b):
        out, i = [], 0
        while True:
            i = b.find(b"\x00\x00\x01\xB5", i)
            if i < 0:
                return out
            if b[i + 4] >> 4 == 8:
                out.append((b[i + 7] >> 7, (b[i + 7] >> 1) & 1, b[i + 8] >> 7, b[i + 7] & 1))
            i += 4

    def test_patch(self):
        # coded order I P B B (display 2 0 1 ... ) in two GOPs of 4 pictures
        b = self.stream([[2, 0, 1, 3], [0, 3, 1, 2]])
        n = pulldown.soft_pulldown(b)
        self.assertEqual(n, 8)
        self.assertEqual(b[7] & 0x0F, 4)                    # 29.97 in the sequence header
        self.assertEqual(b[13] & 0x08, 0)                   # progressive_sequence = 0
        f = self.flags(b)
        # display order 0..7 must read (1,1) (0,0) (0,1) (1,0) (1,1) ...
        display = {}
        for (refs, base) in (([2, 0, 1, 3], 0), ([0, 3, 1, 2], 4)):
            for k, tr in enumerate(refs):
                display[base + tr] = f[base + k]
        self.assertEqual([display[k][:2] for k in range(8)],
                         [(1, 1), (0, 0), (0, 1), (1, 0)] * 2)
        self.assertTrue(all(x[2] == 1 and x[3] == 1 for x in f))   # progressive_frame, 420 type
        # field parity never breaks: each frame starts on the other parity
        last = None
        for k in range(8):
            tff, rff = display[k][:2]
            first = "T" if tff else "B"
            if last:
                self.assertNotEqual(first, last)
            fields = 3 if rff else 2
            last = first if fields == 3 else ("B" if first == "T" else "T")


class TestFilmTiming(unittest.TestCase):
    def test_gop_and_chapters(self):
        self.assertEqual(gop_limits((24000, 1001)), (14, 10))
        self.assertEqual(gop_limits((30000, 1001)), (18, 12))
        self.assertEqual(gop_limits((25, 1)), (15, 10))
        # GOPs of 14 film frames (35 fields); the short rest before a chapter is
        # spread so no GOP is under 10 frames (0.4 s)
        self.assertEqual(keyframe_plan([60], (24000, 1001)), [39, 50, 60])
        p = project(chapters=[0, 2.5, 5])
        t = p.titles[0]
        t.video_mode = "pulldown"
        self.assertEqual(title_fps(t, p.disc), (24000, 1001))
        xml = author.title_vob(p, t, "/x/t1.mpg")
        # chapter 2 is film frame 60 (2.5 s), marked half a frame late
        self.assertIn('chapters="0:00:00.000,0:00:02.523,0:00:05.026"', xml)
        t.video_mode = "interlaced"
        self.assertIn('chapters="0:00:00.000,0:00:02.519,0:00:05.022"',
                      author.title_vob(p, t, "/x/t1.mpg"))


if __name__ == "__main__":
    unittest.main()
