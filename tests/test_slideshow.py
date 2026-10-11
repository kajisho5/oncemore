"""Slideshows: timing, the ffmpeg graph, the cache key and the project fields."""

import dataclasses
import re
import unittest

from oncemore import project as P
from oncemore import slideshow as S
from oncemore.errors import ProjectError
from oncemore.scaffold import sample_project


def show(*durations, **kw):
    return S.Slideshow([S.Slide(f"/pics/{i}.jpg", d) for i, d in enumerate(durations)], **kw)


def disc(standard="NTSC", aspect="16:9"):
    d = P.build_project(sample_project(standard=standard, aspect=aspect),
                        "/virtual/project.oncemore.json", check_files=False).disc
    return d


class TestTiming(unittest.TestCase):
    def test_starts_and_duration(self):
        s = show(4, 6, 2.5)
        self.assertEqual(s.duration, 12.5)
        self.assertEqual(s.starts(), [0.0, 4.0, 10.0])
        self.assertEqual(s.fade, 1.0)
        self.assertEqual(show(4, 6, transition="none").fade, 0.0)
        self.assertEqual(show(4).fade, 0.0)          # nothing to fade into

    def test_canvas(self):
        self.assertEqual(S.canvas(disc("NTSC", "16:9")), (854, 480))
        self.assertEqual(S.canvas(disc("NTSC", "4:3")), (640, 480))
        self.assertEqual(S.canvas(disc("PAL", "16:9")), (1024, 576))


class TestGraph(unittest.TestCase):
    def test_crossfade_offsets(self):
        args, fc, has_audio = S.graph(show(4, 6, 2.5), disc())
        self.assertFalse(has_audio)
        self.assertEqual(args.count("-i"), 3)
        # every slide but the last runs on for the fade
        self.assertEqual(re.findall(r"trim=duration=([\d.]+)", fc), ["5.000", "7.000", "2.500"])
        self.assertEqual(re.findall(r"xfade=transition=fade:duration=1.000:offset=([\d.]+)", fc),
                         ["4.000", "10.000"])
        self.assertTrue(fc.endswith("[v]"))
        self.assertIn("scale=854:480", fc)
        self.assertIn("fps=30000/1001", fc)

    def test_cuts_and_single_slide(self):
        _, fc, _ = S.graph(show(3, 3, transition="none"), disc())
        self.assertIn("[s0][s1]concat=n=2:v=1:a=0[v]", fc)
        self.assertNotIn("xfade", fc)
        _, fc, _ = S.graph(show(3), disc("PAL"))
        self.assertIn("[s0]null[v]", fc)
        self.assertIn("fps=25/1", fc)

    def test_pan_zoom_and_music(self):
        s = show(4, 4, pan_zoom=True, audio="/music/song.flac", background_color="#102030")
        args, fc, has_audio = S.graph(s, disc())
        self.assertTrue(has_audio)
        self.assertEqual(fc.count("zoompan="), 2)
        self.assertIn("color=0x102030", fc)
        self.assertNotIn("-loop", args)        # zoompan makes the frames itself
        self.assertEqual(args[-2:], ["-i", "/music/song.flac"])
        self.assertIn("[2:a]aresample=48000,atrim=duration=8.000", fc)
        self.assertIn("afade=t=out:st=6.000:d=2.000", fc)

    def test_fit_and_fill(self):
        _, fc, _ = S.graph(show(4, 4), disc())
        self.assertEqual(fc.count("force_original_aspect_ratio=decrease"), 2)
        self.assertNotIn("crop=", fc)
        s = show(4, 4, fit="fill")
        s.slides[1].fit = "fit"                 # a picture of its own
        _, fc, _ = S.graph(s, disc())
        chains = fc.split(";")
        self.assertIn("scale=854:480:force_original_aspect_ratio=increase,crop=854:480", chains[0])
        self.assertNotIn("pad=", chains[0])
        self.assertIn("force_original_aspect_ratio=decrease,pad=854:480", chains[1])
        _, fc, _ = S.graph(show(4, fit="fill", pan_zoom=True), disc())
        self.assertIn("crop=1708:960,setsar=1,zoompan", fc)

    def test_output_path_tracks_inputs(self):
        d = disc()
        a = S.output_path("/p", show(4, 6), d)
        self.assertTrue(a.startswith("/p/.oncemore-cache/slideshow/") and a.endswith(".mkv"))
        self.assertEqual(a, S.output_path("/p", show(4, 6), d))
        self.assertNotEqual(a, S.output_path("/p", show(4, 7), d))
        self.assertNotEqual(a, S.output_path("/p", show(4, 6, pan_zoom=True), d))
        self.assertNotEqual(a, S.output_path("/p", show(4, 6, fit="fill"), d))
        filled = show(4, 6)
        filled.slides[0].fit = "fill"
        self.assertNotEqual(a, S.output_path("/p", filled, d))
        self.assertNotEqual(a, S.output_path("/p", show(4, 6), dataclasses.replace(d, aspect="4:3")))


class TestProjectFields(unittest.TestCase):
    def data(self, **slideshow):
        d = sample_project()
        d["titles"].append({"id": "pics", "name": "Holiday",
                            "slideshow": dict({"slides": [{"image": "media/a.jpg", "duration": 3},
                                                          {"image": "media/b.jpg"}]},
                                              **slideshow)})
        return d

    def issues(self, data, path="/virtual/project.oncemore.json", check_files=False):
        with self.assertRaises(ProjectError) as cm:
            P.build_project(data, path, check_files=check_files)
        return " ".join(f"{i['path']}: {i['message']}" for i in cm.exception.issues)

    def build(self, data):
        return P.build_project(data, "/virtual/project.oncemore.json", check_files=False)

    def test_title_from_pictures(self):
        p = self.build(self.data(audio="media/song.wav", pan_zoom=True))
        t = p.titles[-1]
        self.assertEqual((t.slideshow.fit, t.slideshow.slides[0].fit), ("fit", None))
        d = self.data(fit="fill")
        d["titles"][-1]["slideshow"]["slides"][1]["fit"] = "fit"
        s = self.build(d).titles[-1].slideshow
        self.assertEqual((s.fit, s.slides[1].fit), ("fill", "fit"))
        self.assertEqual(t.chapters, [0.0, 3.0])            # a chapter per picture
        self.assertEqual(t.slideshow.duration, 8.0)
        self.assertEqual(t.slideshow.audio, "/virtual/media/song.wav")
        self.assertTrue(t.source.startswith("/virtual/.oncemore-cache/slideshow/"))
        # own chapters win
        d = self.data()
        d["titles"][-1]["chapters"] = ["00:00:00"]
        self.assertEqual(self.build(d).titles[-1].chapters, [0.0])

    def test_validation(self):
        self.assertIn("slideshow.transition_duration: every slide must be longer",
                      self.issues(self.data(transition_duration=3)))
        self.build(self.data(transition="none", transition_duration=3))   # no fade, fine
        d = self.data()
        d["titles"][-1]["slideshow"]["slides"] = []
        self.assertIn("slides", self.issues(d))
        self.assertIn("fit", self.issues(self.data(fit="crop")))
        d = self.data()
        del d["titles"][-1]["slideshow"]
        self.issues(d)                                       # neither source nor slideshow
        d["titles"][-1]["source"] = "media/x.mp4"
        self.build(d)
        self.assertIn("slideshow.slides[0].image: file not found",
                      self.issues(self.data(), "/nonexistent/project.oncemore.json", True))

if __name__ == "__main__":
    unittest.main()
