"""Slideshows: timing, the ffmpeg graph, the cache key and the project fields."""

import dataclasses
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from oncemore import project as P
from oncemore import slideshow as S
from oncemore.errors import ProjectError
from oncemore.scaffold import sample_project

from .helpers import have


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
        # every slide but the last runs on for the fade; in whole frames of
        # 29.97 fps, each change on the frame nearest its time (4 s: frame 120)
        self.assertEqual(re.findall(r"trim=end_frame=(\d+)", fc), ["150", "210", "75"])
        self.assertEqual(re.findall(r"xfade=transition=fade:duration=1.001000:offset=([\d.]+)",
                                    fc), ["4.004000", "10.010000"])
        self.assertTrue(fc.endswith("[v]"))
        self.assertIn("scale=854:480", fc)
        self.assertIn("fps=30000/1001", fc)

    def test_long_show_keeps_to_its_chapters(self):
        """Whole frames per picture would add up: 100 five-second pictures at
        29.97 fps are 150 frames each (5.005 s), and the hundredth would come
        15 frames after its chapter. Each change is on its own frame instead,
        and every chapter lands on its picture (at most a frame in)."""
        s = show(*[5] * 100, transition="none")
        _, fc, _ = S.graph(s, disc())
        frames = [int(f) for f in re.findall(r"trim=end_frame=(\d+)", fc)]
        change = [sum(frames[:k]) for k in range(len(frames))]
        self.assertEqual(sum(frames), round(s.duration * 30000 / 1001))
        for k, start in enumerate(s.starts()):
            chapter = P.frame_at(start, (30000, 1001))
            self.assertIn(chapter - change[k], (0, 1), k)

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

    def test_several_pieces_of_music(self):
        s = show(4, 4, audio=["/music/a.flac", "/music/b.mp3"])
        args, fc, has_audio = S.graph(s, disc())
        self.assertTrue(has_audio)
        self.assertEqual(args[-4:], ["-i", "/music/a.flac", "-i", "/music/b.mp3"])
        self.assertIn("[m0][m1]concat=n=2:v=0:a=1,atrim=duration=8.000", fc)
        self.assertEqual(s.music, ["/music/a.flac", "/music/b.mp3"])
        self.assertEqual(show(4, audio="/music/a.flac").music, ["/music/a.flac"])
        self.assertNotEqual(S.output_path("/p", s, disc()),
                            S.output_path("/p", show(4, 4, audio=["/music/a.flac"]), disc()))

    def test_fit_to_audio(self):
        s = show(1, 3, transition="none")
        S.fit_to(s, 10)
        self.assertEqual([x.duration for x in s.slides], [2.5, 7.5])
        s = show(1, 1, 1)                       # 1 s cross-fades: each at least 1.1 s
        S.fit_to(s, 1.5)
        self.assertTrue(all(x.duration >= 1.1 for x in s.slides))
        # a title: durations from the probed music, then its render and chapters
        d = sample_project()
        d["titles"].append({"id": "pics", "slideshow": {
            "slides": [{"image": "media/a.jpg", "duration": 2}, {"image": "media/b.jpg"}],
            "audio": ["media/x.wav", "media/y.wav"], "fit_to_audio": True}})
        p = P.build_project(d, "/virtual/project.oncemore.json", check_files=False)
        t = p.titles[-1]
        before = t.source
        S.apply(t, p.disc, {"/virtual/media/x.wav": {"duration": 9.0},
                            "/virtual/media/y.wav": {"duration": 5.0}}.__getitem__)
        self.assertEqual([x.duration for x in t.slideshow.slides], [4.0, 10.0])
        self.assertEqual(t.chapters, [0.0, 4.0])
        self.assertNotEqual(t.source, before)
        self.assertTrue(t.source.startswith("/virtual/.oncemore-cache/slideshow/"))
        self.assertEqual(t.audio_tracks[0].source, t.source)
        self.assertEqual(S.overrun(t.slideshow), 0.0)

    def test_fitted_thumbnails_follow(self):
        """A thumbnail of a fitted show's chapter is grabbed in that chapter
        as it is after fitting, not as it was before."""
        d = sample_project()
        d["titles"].append({"id": "pics", "slideshow": {
            "slides": [{"image": "media/a.jpg", "duration": 2}, {"image": "media/b.jpg"}],
            "audio": "media/x.wav", "fit_to_audio": True}})
        d["menus"][0]["buttons"].append({
            "id": "two", "label": "TWO", "x": 100, "y": 300, "action": "chapter:pics:2",
            "thumbnail": {"x": 400, "y": 300, "w": 160, "h": 90}})
        p = P.build_project(d, "/virtual/project.oncemore.json", check_files=False)
        t = p.titles[-1]
        thumb = p.menu("main").buttons[-1].thumb
        self.assertEqual(thumb.time, 3.0)                     # 2 s in, before fitting
        S.apply(t, p.disc, {"/virtual/media/x.wav": {"duration": 28.0}}.__getitem__)
        P.retime_thumbs(p, t)
        self.assertEqual(t.chapters, [0.0, 8.0])
        self.assertEqual(thumb.time, 9.0)

    def test_music_too_short(self):
        s = show(*[1] * 20, audio="/music/a.wav", fit_to_audio=True)      # 1 s fades
        S.fit_to(s, 5.0)
        s.music_length = 5.0
        self.assertAlmostEqual(S.overrun(s), 20 * 1.1 - 5.0)

    def test_transition_kinds(self):
        s = show(3, 3, 3, 3, transition="wipeleft", transition_duration=0.5)
        s.slides[1].transition = "none"             # a cut after the second picture
        s.slides[2].transition = "slideup"
        _, fc, _ = S.graph(s, disc())
        self.assertIn("[s0][s1]xfade=transition=wipeleft:duration=0.500500:offset=3.003000[x1]",
                      fc)
        self.assertIn("[x1][s2]concat=n=2:v=1:a=0[x2]", fc)
        self.assertIn("[x2][s3]xfade=transition=slideup:duration=0.500500:offset=9.009000[v]",
                      fc)
        # each picture runs on only under a transition that follows it
        self.assertEqual(re.findall(r"trim=end_frame=(\d+)", fc), ["105", "90", "105", "90"])
        self.assertEqual(s.duration, 12.0)
        # random: one kind per change, the same every time
        r = show(3, 3, 3, transition="random")
        self.assertEqual(r.changes(), show(3, 3, 3, transition="random").changes())
        self.assertTrue(all(c in S.TRANSITIONS.values() for c in r.changes()))
        self.assertEqual(show(3, 3, transition="none").fade, 0.0)
        # the per-picture choice is part of the render's key
        self.assertNotEqual(S.output_path("/p", s, disc()),
                            S.output_path("/p", show(3, 3, 3, 3, transition="wipeleft",
                                                     transition_duration=0.5), disc()))

    @unittest.skipUnless(have("ffmpeg"), "needs ffmpeg")
    def test_renders(self):
        tmp = tempfile.mkdtemp(prefix="oncemore-slides-")
        try:
            pics = []
            for k, colour in enumerate(("red", "green", "blue")):
                pics.append(os.path.join(tmp, f"{k}.png"))
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                                f"color=c={colour}:s=320x240", "-frames:v", "1", pics[-1]],
                               check=True)
            s = S.Slideshow([S.Slide(p, 1.5) for p in pics], transition="random",
                            transition_duration=0.5)
            s.slides[0].transition = "circleopen"
            out = os.path.join(tmp, "show.mkv")
            S.render(s, disc(), out, os.path.join(tmp, "log"))
            seconds = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                 out], capture_output=True, text=True, check=True).stdout)
            self.assertAlmostEqual(seconds, 4.5, delta=0.1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

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
        # advanced by hand: a moment per picture, cuts, no music
        s = self.build(self.data(advance="manual")).titles[-1]
        self.assertEqual([x.duration for x in s.slideshow.slides], [1.0, 1.0])
        self.assertEqual((s.slideshow.fade, s.chapters), (0.0, [0.0, 1.0]))
        self.assertIn("no music", self.issues(self.data(advance="manual", audio="media/a.wav")))
        self.assertIn("with cuts", self.issues(self.data(advance="manual", transition="wipeleft")))
        self.assertIn("slideshow.fit_to_audio: needs music", self.issues(self.data(fit_to_audio=True)))
        d = self.data()
        del d["titles"][-1]["slideshow"]
        self.issues(d)                                       # neither source nor slideshow
        d["titles"][-1]["source"] = "media/x.mp4"
        self.build(d)
        self.assertIn("slideshow.slides[0].image: file not found",
                      self.issues(self.data(), "/nonexistent/project.oncemore.json", True))

if __name__ == "__main__":
    unittest.main()
