"""Titles made of clips: the project format, the time mapping and the
filter graph that joins them (the encoded result is checked in test_e2e)."""

import copy
import unittest

from oncemore import clips, encode
from oncemore import project as P
from oncemore.errors import ProjectError
from oncemore.scaffold import sample_project


def build(data):
    return P.build_project(data, "/virtual/project.oncemore.json", check_files=False)


def with_clips(**extra):
    data = sample_project()
    t = data["titles"][1]
    del t["source"], t["chapters"]
    t["clips"] = [{"source": "media/sample_a.mp4", "in": "00:00:02", "out": 5},
                  {"source": "media/sample_b.mp4"}]
    t.update(extra)
    return data


PROBES = {
    "/virtual/media/sample_a.mp4": {"duration": 24.0, "has_video": True, "width": 1280,
                                     "height": 720, "fps": 29.97, "audio_streams": 1},
    "/virtual/media/sample_b.mp4": {"duration": 6.4, "has_video": True, "width": 640,
                                     "height": 480, "fps": 25.0, "audio_streams": 0},
    "/virtual/media/photo.jpg": {"duration": 0.04, "has_video": True, "width": 400,
                                  "height": 300, "fps": 25.0, "audio_streams": 0},
}


def with_still(**clip):
    data = with_clips()
    data["titles"][1]["clips"].insert(1, dict({"source": "media/photo.jpg"}, **clip))
    return data


class TestClipProject(unittest.TestCase):
    def errors(self, data):
        with self.assertRaises(ProjectError) as cm:
            build(data)
        return " | ".join(f"{i['path']}: {i['message']}" for i in cm.exception.issues)

    def test_parsed(self):
        t = build(with_clips()).title("t2")
        self.assertEqual([(c.source, c.start, c.end) for c in t.clips],
                         [("/virtual/media/sample_a.mp4", 2.0, 5.0),
                          ("/virtual/media/sample_b.mp4", 0.0, None)])
        self.assertEqual(t.source, "/virtual/media/sample_a.mp4")   # the first clip
        self.assertTrue(t.clip_chapters)
        self.assertFalse(build(with_clips(chapters=[0, 1])).title("t2").clip_chapters)

    def test_invalid(self):
        data = with_clips()
        data["titles"][1]["source"] = "media/sample_b.mp4"
        self.assertIn("give one of source, slideshow or clips", self.errors(data))
        data = with_clips()
        data["titles"][1]["clips"][0]["out"] = 1
        self.assertIn("clips[0].out: must be after in", self.errors(data))
        self.assertIn("audio_tracks", self.errors(with_clips(audio_tracks=[{}, {}])))
        self.assertIn("passthrough", self.errors(with_clips(audio={"passthrough": True})))
        data = with_clips()
        data["titles"][1]["clips"] = []
        self.assertIn("clips", self.errors(data))
        # pictures are shown for a time; videos are trimmed
        self.assertIn("clips[1]: a still picture has no in or out",
                      self.errors(with_still(out=3)))
        self.assertIn("clips[1].duration: must be from 0.5 s", self.errors(with_still(duration=0.2)))
        self.assertIn("fit", self.errors(with_still(fit="stretch")))
        data = with_clips()
        data["titles"][1]["clips"][1]["duration"] = 3
        self.assertIn("clips[1]: duration and fit are for still pictures", self.errors(data))

    def test_still_pictures(self):
        p = build(with_still(duration="00:00:02.5", fit="fill"))
        t = p.title("t2")
        still = t.clips[1]
        self.assertEqual((still.still, still.hold, still.fit), (True, 2.5, "fill"))
        self.assertFalse(t.clips[0].still)
        self.assertEqual(build(with_still()).title("t2").clips[1].hold, 5.0)   # the default
        # its length is its duration (the file has none), in whole frames
        clips.apply(p, t, PROBES.__getitem__)
        f = 1001 / 30000
        self.assertAlmostEqual(still.duration, 75 * f)
        self.assertEqual(t.chapters, [0.0, round(90 * f, 6), round(165 * f, 6)])
        self.assertEqual(P.source_at(t, 4.0), ("/virtual/media/photo.jpg", 0.0))
        probes = {c.source: PROBES[c.source] for c in t.clips}
        inputs, graph, _ = encode.clip_graph(t, probes, p.disc, "progressive")
        # read as a video of its length, at the title's rate
        self.assertEqual(inputs[6:15], ["-loop", "1", "-framerate", "30000/1001", "-t",
                                        "2.502500", "-i", "/virtual/media/photo.jpg", "-ss"])
        # 4:3 filling 16:9: the top and bottom are cut, nothing padded
        chain = graph.split(";")[2]
        self.assertTrue(chain.startswith("[1:v:0]setpts=PTS-STARTPTS,crop=400:224,"), chain)
        self.assertNotIn(",pad=", chain)           # (only tpad, which holds the end)
        self.assertIn("trim=end_frame=75", chain)
        self.assertIn("anullsrc", graph.split(";")[3])        # pictures are silent
        # fit: the whole picture, with bars at the sides
        t.clips[1].fit = "fit"
        _, graph, _ = encode.clip_graph(t, probes, p.disc, "progressive")
        self.assertNotIn("crop=", graph)
        self.assertIn("pad=720:480", graph.split(";")[2])

    def test_fill_crop(self):
        info = {"width": 400, "height": 300, "sar": 1}
        self.assertEqual(encode.fill_crop(info, 16 / 9)[0], "crop=400:224,")
        self.assertEqual(encode.fill_crop(info, 4 / 3), ("", info))
        wide = {"width": 1920, "height": 800, "sar": 1}
        crop, pic = encode.fill_crop(wide, 16 / 9)
        self.assertEqual((crop, pic["width"], pic["height"]), ("crop=1422:800,", 1422, 800))

    def test_cache_keys_follow_the_picture(self):
        p = build(with_still(duration=3))
        t = p.title("t2")
        a = clips.preview_path("/p", t, p.disc)
        t.clips[1].fit = "fill"
        self.assertNotEqual(a, clips.preview_path("/p", t, p.disc))
        b = clips.preview_path("/p", t, p.disc)
        t.clips[1].hold = 4.0
        self.assertNotEqual(b, clips.preview_path("/p", t, p.disc))

    def test_lengths_and_chapters(self):
        p = build(with_clips())
        t = p.title("t2")
        total = clips.apply(p, t, PROBES.__getitem__)
        # whole frames at 29.97: 3 s -> 90 frames, 6.4 s -> 192 frames (rounded up)
        f = 1001 / 30000
        self.assertAlmostEqual(t.clips[0].duration, 90 * f)
        self.assertAlmostEqual(t.clips[1].duration, 192 * f)
        self.assertAlmostEqual(total, 282 * f)
        self.assertEqual(t.chapters, [0.0, round(90 * f, 6)])
        # a moment of the title -> the file playing then
        self.assertEqual(P.source_at(t, 1.0), ("/virtual/media/sample_a.mp4", 3.0))
        src, at = P.source_at(t, 4.0)
        self.assertEqual(src, "/virtual/media/sample_b.mp4")
        self.assertAlmostEqual(at, 4.0 - 90 * f)

    def test_graph(self):
        p = build(with_clips())
        t = p.title("t2")
        clips.apply(p, t, PROBES.__getitem__)
        probes = {c.source: PROBES[c.source] for c in t.clips}
        inputs, graph, labels = encode.clip_graph(t, probes, p.disc, "progressive")
        self.assertEqual(inputs[:6], ["-ss", "2.000000", "-t", "3.003000", "-i",
                                      "/virtual/media/sample_a.mp4"])
        self.assertEqual(labels, ["[v]", "[a0]"])
        self.assertIn("trim=end_frame=90", graph)
        self.assertIn("trim=end_frame=192", graph)
        self.assertIn("[1:v:0]", graph)
        self.assertNotIn("[1:a:0]", graph)              # no sound in that file: silence
        self.assertIn("anullsrc", graph)
        self.assertIn("[v0][s0][v1][s1]concat=n=2:v=1:a=1[v][cat]", graph)
        _, vgraph, vlabels = encode.clip_graph(t, probes, p.disc, "progressive", audio=False)
        self.assertEqual(vlabels, ["[v]"])
        self.assertNotIn("anullsrc", vgraph)
        _, agraph, alabels = encode.clip_graph(t, probes, p.disc, "progressive", video=False)
        self.assertEqual(alabels, ["[a0]"])
        self.assertIn("concat=n=2:v=0:a=1[cat]", agraph)
        # LPCM: framed in 80-sample packets after the join
        t2 = copy.copy(t)
        t2.audio_codec = "lpcm"
        _, g, _ = encode.clip_graph(t2, probes, p.disc, "progressive")
        self.assertTrue(g.endswith("asetnsamples=n=80:p=0[a0]"), g)


if __name__ == "__main__":
    unittest.main()
