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


class TestFormatsAndStyles(unittest.TestCase):
    def test_srt_tags_set_position_and_colour(self):
        cues = subtitles.parse_srt(SRT)
        self.assertEqual(cues[1].position, "top")                     # {\an8}
        c = subtitles.parse_srt('1\n00:00:01,000 --> 00:00:02,000\n<font color="#ffff00">Y</font>\n')
        self.assertEqual((c[0].color, c[0].lines), ("#FFFF00", ["Y"]))

    def test_vtt(self):
        cues = subtitles.parse_vtt("WEBVTT - demo\n\nNOTE a comment\n\nSTYLE\n::cue { color: red }\n\n"
                                   "intro\n00:01.000 --> 00:02.500 line:0 align:center\n<b>Top</b>\n\n"
                                   "01:00:03.000 --> 01:00:04.000\nAn hour in\n")
        self.assertEqual([(c.start, c.end, c.lines, c.position) for c in cues],
                         [(1.0, 2.5, ["Top"], "top"), (3603.0, 3604.0, ["An hour in"], None)])
        with self.assertRaises(ValueError):
            subtitles.parse_vtt("1\n00:00:01,000 --> 00:00:02,000\nnot vtt\n")

    def test_ass(self):
        ass = ("[Script Info]\nScriptType: v4.00+\n\n[V4+ Styles]\n"
               "Format: Name, Fontname, Fontsize, PrimaryColour, Bold, Alignment\n"
               "Style: Default,Arial,20,&H00FFFFFF,0,2\nStyle: Sign,Arial,20,&H0000FFFF,0,8\n\n"
               "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
               "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Line, with comma\\Nsecond\n"
               "Dialogue: 0,0:00:03.00,0:00:04.50,Sign,,0,0,0,,{\\c&H0000FF&}Red sign\n"
               "Comment: 0,0:00:05.00,0:00:06.00,Default,,0,0,0,,ignored\n")
        cues = subtitles.parse_ass(ass)
        self.assertEqual(cues[0].lines, ["Line, with comma", "second"])
        self.assertEqual((cues[1].position, cues[1].color), ("top", "#FF0000"))   # style + override
        self.assertEqual((cues[0].color, cues[0].style_color), (None, "#FFFFFF"))
        self.assertEqual(len(cues), 2)

    def test_srt_round_trip(self):
        cues = subtitles.parse_srt('1\n00:00:01,000 --> 00:00:02,000\n{\\an8}<font color="#00FF00">G</font>\n')
        again = subtitles.parse_srt(subtitles.to_srt(cues))
        self.assertEqual(again, cues)

    def test_palette_budget(self):
        style = {"color": "#FFFFFF"}
        cues = [subtitles.Cue(0, 1, ["a"], color=f"#0000{i:02X}") for i in range(10)]
        self.assertEqual(subtitles.palette_size([(None, cues[:3])], style), 2 + 2 * 4)
        self.assertGreater(subtitles.palette_size([(None, cues)], style), 16)


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
