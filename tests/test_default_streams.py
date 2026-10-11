"""The disc's starting streams (DECISIONS §18, §101): an audio track marked
`default` and `disc.subtitles_off`, set once at first play (DVD, Blu-ray and
the simulator)."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import author, bluray, tools
from oncemore.errors import ProjectError
from oncemore.project import build_project
from oncemore.simulate import Simulator

from .helpers import have, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None
try:
    from . import bluray_sim
    LIBBLURAY = bluray_sim.load_library()
except Exception:  # pragma: no cover
    LIBBLURAY = None


def project(disc=None, tracks=None, subs=None):
    t = {"id": "t", "source": "a.mp4",
         "audio_tracks": tracks or [{"lang": "ja"}, {"source": "b.wav", "lang": "en", "default": True}]}
    if subs is not None:
        t["subtitles"] = subs
    return build_project({"version": 1, "disc": {"label": "T", "standard": "NTSC", "aspect": "16:9",
                                                 **(disc or {})}, "titles": [t]},
                         "/x/project.oncemore.json", check_files=False)


class TestCommands(unittest.TestCase):
    def test_dvd_first_play(self):
        p = project()
        self.assertEqual(author.default_audio(p), 1)
        self.assertEqual(author.start_streams(p), "audio = 1; ")
        self.assertTrue(author.first_play_command(p).startswith("audio = 1; jump title 1;"))
        off = project(disc={"subtitles_off": True}, subs=[{"file": "a.srt"}])
        self.assertEqual(author.start_streams(off), "audio = 1; subtitle = 0; ")
        # a subtitle track on at start wins over subtitles_off
        on = project(disc={"subtitles_off": True}, subs=[{"file": "a.srt"}, {"file": "b.srt", "default": True}])
        self.assertEqual(author.start_streams(on), "audio = 1; subtitle = 65; ")
        none = project(tracks=[{"lang": "ja"}])
        self.assertEqual(author.start_streams(none), "")

    def test_one_default_per_title(self):
        with self.assertRaises(ProjectError):
            project(tracks=[{"lang": "ja", "default": True}, {"source": "b.wav", "default": True}])

    def test_bluray_first_play(self):
        p = project()
        objects, first, _ = bluray.navigation(p)
        self.assertEqual(objects[first][0], bluray.set_streams(audio=2))
        objects, first, _ = bluray.navigation(project(tracks=[{"lang": "ja"}]))
        self.assertNotEqual(objects[first][0][:2], bluray.set_streams(audio=1)[:2])

    def test_simulator(self):
        s = Simulator(project(disc={"subtitles_off": True}, subs=[{"file": "a.srt"}])).start()
        self.assertEqual((s["audio"], s["subtitle"]), (2, 0))


def make_media(d):
    ff = ["ffmpeg", "-v", "error", "-y"]
    subprocess.run(ff + ["-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30000/1001:duration=3",
                         "-f", "lavfi", "-i", "sine=f=440:d=3", "-c:v", "mpeg4", "-c:a", "aac",
                         "-shortest", os.path.join(d, "a.mp4")], check=True)
    subprocess.run(ff + ["-f", "lavfi", "-i", "sine=f=880:d=3", "-c:a", "pcm_s16le",
                         os.path.join(d, "b.wav")], check=True)
    with open(os.path.join(d, "a.srt"), "w") as f:
        f.write("1\n00:00:00,200 --> 00:00:02,500\nHello\n")


def disc_json(**disc):
    return {"version": 1,
            "disc": {"label": "STREAMS", "standard": "NTSC", "aspect": "16:9", "subtitles_off": True,
                     **disc},
            "titles": [{"id": "t", "source": "a.mp4",
                        "audio_tracks": [{"lang": "ja"}, {"source": "b.wav", "lang": "en", "default": True}],
                        "subtitles": [{"file": "a.srt", "lang": "en"}]}]}


@unittest.skipUnless(LIBDVDNAV and have("ffmpeg") and tools.iso_tool()[0] is not None,
                     "needs ffmpeg, an ISO tool and libdvdnav")
class TestDvd(unittest.TestCase):
    def test_disc_starts_with_the_default_audio_and_no_subtitles(self):
        tmp = tempfile.mkdtemp(prefix="oncemore-streams-dvd-")
        self.addCleanup(shutil.rmtree, tmp, True)
        make_media(tmp)
        with open(os.path.join(tmp, "project.oncemore.json"), "w") as f:
            json.dump(disc_json(), f)
        iso = os.path.join(tmp, "s.iso")
        rc, out, err = run_cli("iso", tmp, "-o", iso, "--fast")
        self.assertEqual(rc, 0, err + out)
        with dvdnav_sim.DvdSim(iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual(d.active_audio(), 1)                # the English track
            self.assertFalse(d.active_subtitle()[1])             # subtitles off


@unittest.skipUnless(LIBBLURAY and have("ffmpeg"), "needs ffmpeg and libbluray")
class TestBluray(unittest.TestCase):
    def test_disc_starts_with_the_default_audio(self):
        tmp = tempfile.mkdtemp(prefix="oncemore-streams-bd-")
        self.addCleanup(shutil.rmtree, tmp, True)
        make_media(tmp)
        with open(os.path.join(tmp, "project.oncemore.json"), "w") as f:
            json.dump(disc_json(), f)
        out_dir = os.path.join(tmp, "out")
        rc, out, err = run_cli("build", tmp, "-o", out_dir, "--format", "bluray", "--fast")
        self.assertEqual(rc, 0, err + out)
        with bluray_sim.Disc(LIBBLURAY, out_dir) as disc:
            events = disc.play(audio=True)
        start = events.index(("title", 1))
        self.assertIn(("audio_stream", 2), events[:start + 3])
        self.assertNotIn(("subtitles_shown", 1), events)


if __name__ == "__main__":
    unittest.main()
