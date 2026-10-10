import os
import tempfile
import unittest

from oncemore import subtitles
from oncemore.errors import ProjectError

SRT = """﻿1\r
00:00:01,000 --> 00:00:04,000\r
<i>Hello</i> there\r
second line\r
\r
2\r
00:00:03.500 --> 00:00:06,25\r
{\\an8}Overlapping cue\r
\r
3\r
00:00:07,000 --> 00:00:07,000\r
zero length is dropped\r
\r
4\r
00:01:02,5 --> 00:01:03,000\r
\r
"""


class TestSrt(unittest.TestCase):
    def test_parse(self):
        cues = subtitles.parse_srt(SRT)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].lines, ["Hello there", "second line"])
        self.assertEqual((cues[0].start, cues[0].end), (1.0, 3.5))   # clipped to next start
        self.assertEqual(cues[1].lines, ["Overlapping cue"])
        self.assertAlmostEqual(cues[1].end, 6.25)

    def test_sorted_and_hours(self):
        cues = subtitles.parse_srt("2\n01:00:00,000 --> 01:00:02,000\nlate\n\n"
                                   "1\n00:00:00,500 --> 00:00:01,000\nearly\n")
        self.assertEqual([c.lines[0] for c in cues], ["early", "late"])
        self.assertEqual(cues[1].start, 3600.0)

    def test_bad_timing(self):
        with self.assertRaises(ValueError):
            subtitles.parse_srt("1\n00:00:01 --> soon\ntext\n")

    def test_load_shift_jis_file(self):
        with tempfile.NamedTemporaryFile("wb", suffix=".srt", delete=False) as f:
            f.write("1\r\n00:00:01,000 --> 00:00:02,000\r\n日本語の字幕\r\n".encode("cp932"))
        self.addCleanup(os.remove, f.name)
        self.assertEqual(subtitles.load_srt(f.name)[0].lines, ["日本語の字幕"])

    def test_load_reports_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False) as f:
            f.write("1\n12:00 --> x\nbad\n")
        self.addCleanup(os.remove, f.name)
        with self.assertRaises(ProjectError):
            subtitles.load_srt(f.name)


class TestQuantise(unittest.TestCase):
    def test_four_levels_and_crop(self):
        W, H = 20, 10
        rgba = bytearray(W * H * 4)

        def put(x, y, r, g, b, a=255):
            i = 4 * (y * W + x)
            rgba[i:i + 4] = bytes((r, g, b, a))
        put(5, 3, 255, 255, 255)      # fill
        put(6, 3, 0, 0, 0)            # outline
        put(7, 4, 128, 128, 128)      # anti-alias
        put(9, 6, 255, 255, 255, 40)  # nearly transparent: ignored
        c, x, y = subtitles.quantise(bytes(rgba), W, H)
        self.assertEqual((x, y), (4, 2))                 # even offsets
        self.assertEqual((c.width % 2, c.height % 2), (0, 0))
        self.assertEqual(c.get(1, 1), 1)
        self.assertEqual(c.get(2, 1), 2)
        self.assertEqual(c.get(3, 2), 3)
        self.assertEqual(sorted(set(c.pixels)), [0, 1, 2, 3])

    def test_empty(self):
        self.assertEqual(subtitles.quantise(bytes(8 * 8 * 4), 8, 8), (None, 0, 0))


if __name__ == "__main__":
    unittest.main()
