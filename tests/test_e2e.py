"""End-to-end: oncemore init -> oncemore iso -> inspect the image.

Needs ffmpeg (with drawtext), ffprobe, dvdauthor/spumux and an ISO tool.
The navigation checks additionally need libdvdnav (skipped otherwise).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import tools
from oncemore.project import CAPACITY

from .helpers import have, json_lines, run_cli

try:
    from . import dvdnav_sim
    LIBDVDNAV = dvdnav_sim.load_library()
except Exception:  # pragma: no cover
    LIBDVDNAV = None

TOOLS_OK = (have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext()
            and tools.iso_tool()[0] is not None)
SKIP_REASON = "needs ffmpeg (drawtext), ffprobe, dvdauthor, spumux and an ISO tool"


def ffprobe_streams(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                        "-probesize", "50M", "-analyzeduration", "50M", path],
                       capture_output=True, text=True, check=True)
    return json.loads(p.stdout)["streams"]


def iso_list(iso):
    """Paths inside the ISO 9660 tree of an image."""
    if shutil.which("xorriso"):
        p = subprocess.run(["xorriso", "-indev", iso, "-find", "/", "-type", "f"],
                           capture_output=True, text=True, check=True)
        return sorted(line.strip().strip("'") for line in p.stdout.splitlines()
                      if line.strip().startswith("'/"))
    if shutil.which("isoinfo"):
        p = subprocess.run(["isoinfo", "-f", "-i", iso], capture_output=True, text=True,
                           check=True)
        return sorted(line.split(";")[0] for line in p.stdout.splitlines()
                      if "." in line.rsplit("/", 1)[-1])
    raise unittest.SkipTest("needs xorriso or isoinfo to list the image")


def iso_extract(iso, inner, dest):
    if shutil.which("xorriso"):
        subprocess.run(["xorriso", "-osirrox", "on", "-indev", iso, "-extract", inner, dest],
                       capture_output=True, check=True)
    elif shutil.which("isoinfo"):
        with open(dest, "wb") as f:
            subprocess.run(["isoinfo", "-i", iso, "-x", inner + ";1"], stdout=f, check=True)
    else:
        raise unittest.SkipTest("needs xorriso or isoinfo to extract files")
    return dest


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestDefaultSample(unittest.TestCase):
    """The completion criterion: init + iso with no edits, default settings."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-")
        rc, out, err = run_cli("init", "demo", cwd=cls.tmp)
        assert rc == 0, err
        cls.iso = os.path.join(cls.tmp, "demo.iso")
        rc, out, err = run_cli("--json", "iso", "demo/project.oncemore.json", "-o", "demo.iso",
                               cwd=cls.tmp)
        cls.rc, cls.events, cls.err = rc, json_lines(out), err
        assert rc == 0, err + out
        cls.result = cls.events[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_json_progress_and_result(self):
        kinds = [e["event"] for e in self.events]
        self.assertIn("step", kinds)
        self.assertIn("progress", kinds)
        self.assertEqual(self.result["event"], "result")
        self.assertTrue(self.result["ok"])
        # realpath: on macOS the temp dir is /var -> /private/var
        self.assertEqual(os.path.realpath(self.result["iso"]), os.path.realpath(self.iso))
        steps = [e["step"] for e in self.events if e["event"] == "step"]
        for s in ("probe", "menu", "encode", "author", "iso"):
            self.assertIn(s, steps)

    def test_build_dir_removed(self):
        self.assertEqual(sorted(os.listdir(self.tmp)), ["demo", "demo.iso"])

    def test_iso_contains_video_ts(self):
        files = iso_list(self.iso)
        for name in ("VIDEO_TS.IFO", "VIDEO_TS.BUP", "VTS_01_0.IFO", "VTS_01_0.BUP",
                     "VTS_01_0.VOB", "VTS_01_1.VOB"):
            self.assertIn(f"/VIDEO_TS/{name}", files)
        self.assertFalse([f for f in files if ".work" in f], "work files leaked into the ISO")

    def test_iso_is_udf_readable(self):
        if not self.result.get("iso_udf"):
            self.skipTest("ISO tool without UDF")
        with open(self.iso, "rb") as f:
            f.seek(16 * 2048)
            vrs = f.read(2048 * 4)
        self.assertIn(b"CD001", vrs)  # ISO 9660 primary descriptor
        self.assertIn(b"NSR02", vrs)  # UDF 1.02 descriptor
        self.assertEqual(vrs[1:6], b"CD001")
        # PVD volume id; genisoimage pads with spaces, hdiutil with NULs
        self.assertEqual(vrs[40:72].decode("ascii").rstrip(" \x00"), "SAMPLE_DISC")
        # libdvdread (VLC, mpv) shows the UDF volume name as the disc title
        from oncemore.udfinfo import volume_names
        names = volume_names(self.iso)
        self.assertEqual(names, self.result["volume_names"])
        self.assertEqual(names["udf_volume"], "SAMPLE_DISC", names)

    def test_title_vob_streams(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_1.VOB", os.path.join(self.tmp, "t.vob"))
        streams = ffprobe_streams(vob)
        v = [s for s in streams if s["codec_type"] == "video"]
        a = [s for s in streams if s["codec_type"] == "audio"]
        self.assertEqual(v[0]["codec_name"], "mpeg2video")
        self.assertEqual((v[0]["width"], v[0]["height"]), (720, 480))
        self.assertEqual(v[0]["r_frame_rate"], "30000/1001")
        self.assertEqual(v[0]["display_aspect_ratio"], "16:9")
        self.assertEqual(a[0]["codec_name"], "ac3")
        self.assertEqual(a[0]["sample_rate"], "48000")

    def test_menu_vob_has_subpictures(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_0.VOB", os.path.join(self.tmp, "m.vob"))
        codecs = [s["codec_name"] for s in ffprobe_streams(vob)]
        self.assertIn("mpeg2video", codecs)
        self.assertIn("dvd_subtitle", codecs)

    def test_size_within_target(self):
        self.assertLessEqual(self.result["bytes"], CAPACITY["DVD5"])
        self.assertLessEqual(os.path.getsize(self.iso), CAPACITY["DVD5"])
        self.assertEqual(self.result["iso_bytes"], os.path.getsize(self.iso))

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_menu_navigation(self):
        """Press buttons like a remote control would, through libdvdnav."""
        if not self.result.get("iso_udf"):
            self.skipTest("libdvdread needs a UDF image")
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.num_titles(), 2)
            self.assertEqual(d.num_parts(1), 3)
            # first play lands on the main menu with three buttons
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 3)
            self.assertEqual(d.highlight(), 1)
            self.assertEqual(d.move("down"), 2)
            self.assertEqual(d.move("down"), 3)
            self.assertEqual(d.move("down"), 1)       # wraps
            self.assertEqual(d.move("right"), 1)      # nothing to the right
            # CHAPTERS -> generated chapter menu
            d.activate(2)
            self.assertEqual(d.wait_menu(), 2)
            self.assertEqual(d.button_count(), 4)
            self.assertEqual(d.move("right"), 2)
            # chapter 2 button starts title 1 at chapter 2
            d.activate(2)
            self.assertEqual(d.wait_title(), (1, 2))
            # played on its own, title 1 ends -> end_action menu:main
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            # PLAY ALL: title 1, then title 2, then title 2's end_action
            d.activate(1)
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual(d.play_to_end_of_title(), ("title", (2, 1)))
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            # chapter 3 after PLAY ALL is a single play again
            d.activate(2)
            self.assertEqual(d.wait_menu(), 2)
            d.activate(3)
            self.assertEqual(d.wait_title(), (1, 3))
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            # BACK from the chapter menu returns to main
            d.activate(2)
            self.assertEqual(d.wait_menu(), 2)
            d.activate(4)
            self.assertEqual(d.wait_menu(), 1)
            # SAMPLE TITLE B plays title 2 directly
            d.activate(3)
            self.assertEqual(d.wait_title(), (2, 1))


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestPalLpcmBuild(unittest.TestCase):
    """PAL 4:3 with LPCM audio, `build` to a folder, --fast, --keep-work."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-pal-")
        rc, _, err = run_cli("init", "pal", "--standard", "PAL", "--aspect", "4:3", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "pal", "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        for t in data["titles"]:
            t["audio"] = {"codec": "lpcm"}
        data["disc"]["label"] = "Sample PAL disc"
        with open(path, "w") as f:
            json.dump(data, f)
        cls.out = os.path.join(cls.tmp, "out")
        rc, out, err = run_cli("--json", "build", path, "-o", cls.out, "--fast", "--keep-work",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]
        cls.project = path

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_folder_layout(self):
        self.assertTrue(os.path.isdir(os.path.join(self.out, ".work")))
        self.assertTrue(os.path.isdir(os.path.join(self.out, "AUDIO_TS")))
        files = sorted(os.listdir(os.path.join(self.out, "VIDEO_TS")))
        self.assertEqual(files, self.result["files"])
        self.assertIn("VTS_01_1.VOB", files)
        self.assertIn("disc.label normalised to 'SAMPLE_PAL_DISC'", self.result["warnings"])

    def test_dvdauthor_reports_no_timing_problems(self):
        """ffmpeg writes fixed LPCM frame counts; without lpcmfix dvdauthor
        prints thousands of 'Audio pts ... moves backwards' warnings."""
        with open(os.path.join(self.out, ".work", "logs", "dvdauthor.log")) as f:
            warns = [l for l in f if l.startswith("WARN")]
        self.assertEqual(warns, [])

    def test_pal_lpcm_streams(self):
        streams = ffprobe_streams(os.path.join(self.out, "VIDEO_TS", "VTS_01_1.VOB"))
        v = next(s for s in streams if s["codec_type"] == "video")
        a = next(s for s in streams if s["codec_type"] == "audio")
        self.assertEqual((v["width"], v["height"], v["r_frame_rate"]), (720, 576, "25/1"))
        self.assertEqual(v["display_aspect_ratio"], "4:3")
        self.assertEqual(a["codec_name"], "pcm_dvd")
        self.assertEqual(a["sample_rate"], "48000")

    @unittest.skipUnless(have("dvdunauthor"), "dvdunauthor not installed")
    def test_chapter_cells_are_frame_accurate(self):
        d = os.path.join(self.tmp, "unauthor")
        os.makedirs(d, exist_ok=True)
        subprocess.run(["dvdunauthor", os.path.join(self.out, "VIDEO_TS")], cwd=d,
                       capture_output=True, check=True)
        with open(os.path.join(d, "dvdauthor.xml")) as f:
            xml = f.read()
        # title 1 chapters at 0, 8 and 16 s (exact frames at 25 fps)
        self.assertIn('<cell start="0:00:00.000" end="0:00:08.000" chapter="1"/>', xml)
        self.assertIn('<cell start="0:00:08.000" end="0:00:16.000" chapter="1"/>', xml)

    def test_menu_colours_survive_encoding(self):
        """A solid background must decode to (nearly) the same RGB. Catches a
        double colour-matrix conversion such as ffmpeg 7.1+'s colourspace
        negotiation re-converting already-BT.601 frames."""
        mpg = os.path.join(self.out, ".work", "menus", "chapters.mpg")
        p = subprocess.run(["ffmpeg", "-v", "error", "-i", mpg, "-frames:v", "1",
                            "-vf", "crop=32:32:680:536,scale=in_color_matrix=bt601:in_range=tv,"
                                   "format=rgb24",
                            "-f", "rawvideo", "pipe:1"], capture_output=True, check=True)
        px = p.stdout
        avg = [sum(px[i::3]) / (len(px) // 3) for i in range(3)]
        for got, want in zip(avg, (0x10, 0x18, 0x20)):  # DEFAULT_BG #101820
            self.assertAlmostEqual(got, want, delta=6, msg=f"decoded {avg}")

    def test_validate_reports_plan(self):
        rc, out, err = run_cli("--json", "validate", self.project)
        self.assertEqual(rc, 0, err)
        r = json_lines(out)[-1]
        self.assertEqual(r["video_bps"], 8_000_000)
        self.assertEqual([t["audio"] for t in r["titles"]], ["lpcm", "lpcm"])
        self.assertEqual(r["titles"][0]["chapters"], [0.0, 8.0, 16.0])
        self.assertTrue(r["font"])

    def test_preview_menu(self):
        png = os.path.join(self.tmp, "preview.png")
        rc, out, err = run_cli("--json", "preview-menu", self.project, "--menu", "chapters",
                               "--button", "ch2", "-o", png)
        self.assertEqual(rc, 0, err)
        r = json_lines(out)[-1]
        self.assertEqual(r["size"], [768, 576])  # square-pixel 4:3 PAL
        self.assertEqual(r["button"], "ch2")
        with open(png, "rb") as f:
            head = f.read(24)
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(int.from_bytes(head[16:20], "big"), 768)
        rc, _, err = run_cli("preview-menu", self.project, "--menu", "nope", "-o", png)
        self.assertEqual(rc, 1)
        self.assertIn("no menu 'nope'", err)


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestMixedTitlesets(unittest.TestCase):
    """A 16:9 AC-3 title and a 4:3 LPCM title on one disc: two titlesets,
    menus in the first, jumps and returns across them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-mixed-")
        rc, _, err = run_cli("init", "mixed", cwd=cls.tmp)
        assert rc == 0, err
        path = os.path.join(cls.tmp, "mixed", "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        b = data["titles"][1]
        b.update({"aspect": "4:3", "audio": {"codec": "lpcm"}, "chapters": [0, 6],
                  "end_action": "menu:chapters_b",
                  "auto_chapter_menu": {"id": "chapters_b", "back": "menu:main"}})
        data["menus"][0]["buttons"].append(
            {"id": "cb", "label": "B CHAPTERS", "x": 120, "y": 400, "action": "menu:chapters_b"})
        with open(path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "mixed.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_two_titlesets(self):
        files = iso_list(self.iso)
        for name in ("VTS_01_0.IFO", "VTS_01_1.VOB", "VTS_02_0.IFO", "VTS_02_1.VOB"):
            self.assertIn(f"/VIDEO_TS/{name}", files)
        self.assertEqual([(t["titleset"], t["aspect"], t["audio"]) for t in self.result["titles"]],
                         [(1, "16:9", "ac3"), (2, "4:3", "lpcm")])
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_02_1.VOB", os.path.join(self.tmp, "b.vob"))
        streams = ffprobe_streams(vob)
        v = next(s for s in streams if s["codec_type"] == "video")
        a = next(s for s in streams if s["codec_type"] == "audio")
        self.assertEqual(v["display_aspect_ratio"], "4:3")
        self.assertEqual(a["codec_name"], "pcm_dvd")

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_navigation_across_titlesets(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.num_titles(), 2)
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 4)
            d.activate(4)                                    # B CHAPTERS (menu 3)
            self.assertEqual(d.wait_menu(), 3)
            d.activate(2)                                    # chapter 2 of the 4:3 title
            self.assertEqual(d.wait_title(), (2, 2))
            # end_action menu:chapters_b from titleset 2, routed through VMGM
            self.assertEqual(d.play_to_end_of_title(), ("menu", 3))
            d.activate(3)                                    # BACK
            self.assertEqual(d.wait_menu(), 1)
            d.activate(1)                                    # PLAY ALL: t1 -> t2 across titlesets
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual(d.play_to_end_of_title(), ("title", (2, 1)))
            self.assertEqual(d.play_to_end_of_title(), ("menu", 3))  # last title's end_action


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestTracksSubtitlesMotionMenu(unittest.TestCase):
    """Two audio tracks, two subtitle languages (Japanese on by default),
    stream-switch buttons and a motion menu, written as an ISO."""

    SRT_JA = ("1\n00:00:01,000 --> 00:00:03,000\n日本語の字幕です\n\n"
              "2\n00:00:04,000 --> 00:00:06,000\n二行目の\nテストです\n")
    SRT_EN = "1\n00:00:01,500 --> 00:00:05,000\nDemo subtitle in English\n"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-tracks-")
        media = os.path.join(cls.tmp, "proj", "media")
        os.makedirs(media)

        def ff(*args):
            subprocess.run(["ffmpeg", "-v", "error", "-y"] + list(args), check=True)
        ff("-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30000/1001:d=8", "-f", "lavfi", "-i",
           "sine=f=440:d=8", "-c:v", "mpeg4", "-c:a", "aac", "-shortest",
           os.path.join(media, "main.mp4"))
        ff("-f", "lavfi", "-i", "sine=f=880:d=6", "-c:a", "pcm_s16le",
           os.path.join(media, "commentary.wav"))
        ff("-f", "lavfi", "-i", "mandelbrot=s=640x360:r=25", "-t", "3", "-c:v", "mpeg4",
           os.path.join(media, "loop.mp4"))
        for name, text in (("ja.srt", cls.SRT_JA), ("en.srt", cls.SRT_EN)):
            with open(os.path.join(media, name), "w", encoding="utf-8") as f:
                f.write(text)
        project = {
            "version": 1,
            "disc": {"label": "SAMPLE_TRACKS", "standard": "NTSC", "aspect": "16:9"},
            "titles": [{"id": "t1", "name": "Sample Tracks", "source": "media/main.mp4",
                        "audio_tracks": [{"lang": "ja"},
                                         {"source": "media/commentary.wav", "lang": "en"}],
                        "subtitles": [{"file": "media/ja.srt", "lang": "ja", "default": True},
                                      {"file": "media/en.srt", "lang": "en"}]}],
            "menus": [{"id": "main", "background_video": "media/loop.mp4",
                       "texts": [{"text": "サンプル", "x": 100, "y": 40, "size": 40}],
                       "buttons": [
                           {"id": "play", "label": "PLAY", "x": 100, "y": 120,
                            "action": "title:t1"},
                           {"id": "a2", "label": "COMMENTARY", "x": 100, "y": 180,
                            "action": "audio:2"},
                           {"id": "s2", "label": "ENGLISH SUBTITLES", "x": 100, "y": 240,
                            "action": "subtitle:2"},
                           {"id": "off", "label": "SUBTITLES OFF", "x": 100, "y": 300,
                            "action": "subtitle:off"}]}],
        }
        cls.project = os.path.join(cls.tmp, "proj", "project.oncemore.json")
        with open(cls.project, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False)
        cls.iso = os.path.join(cls.tmp, "tracks.iso")
        rc, out, err = run_cli("--json", "iso", cls.project, "-o", cls.iso, "--fast",
                               cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_title_streams(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_1.VOB", os.path.join(self.tmp, "t.vob"))
        codecs = [s["codec_name"] for s in ffprobe_streams(vob)]
        self.assertEqual(codecs.count("ac3"), 2)
        self.assertEqual(codecs.count("dvd_subtitle"), 2)
        t = self.result["titles"][0]
        self.assertEqual([a["lang"] for a in t["audio_tracks"]], ["ja", "en"])
        self.assertEqual([s["cues"] for s in t["subtitles"]], [2, 1])
        self.assertEqual(t["audio_bps"], 2 * 192_000)

    def test_motion_menu_moves(self):
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_01_0.VOB", os.path.join(self.tmp, "m.vob"))
        frames = []
        for n in (0, 45):
            p = subprocess.run(["ffmpeg", "-v", "error", "-i", vob, "-vf",
                                f"select=eq(n\\,{n}),scale=64:36,format=gray",
                                "-frames:v", "1", "-f", "rawvideo", "pipe:1"],
                               capture_output=True, check=True)
            frames.append(p.stdout)
        diff = sum(abs(a - b) for a, b in zip(*frames)) / len(frames[0])
        self.assertGreater(diff, 2.0, "menu background did not change between frames")

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_stream_selection(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), 1)
            self.assertEqual(d.button_count(), 4)
            d.activate(1)
            self.assertEqual(d.wait_title(), (1, 1))
            self.assertEqual([d.audio_lang(0), d.audio_lang(1)], ["ja", "en"])
            self.assertEqual([d.subtitle_lang(0), d.subtitle_lang(1)], ["ja", "en"])
            self.assertEqual(d.active_audio(), 0)
            self.assertEqual(d.active_subtitle(), (0, True))     # Japanese, on by default
            self.assertEqual(d.play_to_end_of_title(), ("menu", 1))
            d.activate(2)                                         # COMMENTARY
            d.activate(3)                                         # ENGLISH SUBTITLES
            d.activate(1)
            d.wait_title()
            self.assertEqual(d.active_audio(), 1)
            self.assertEqual(d.active_subtitle(), (1, True))
            d.play_to_end_of_title()
            d.activate(4)                                         # SUBTITLES OFF
            d.activate(1)
            d.wait_title()
            self.assertFalse(d.active_subtitle()[1])


@unittest.skipUnless(TOOLS_OK, SKIP_REASON)
class TestSurround(unittest.TestCase):
    """Title B from a 5.1 source kept as 5.1 AC-3 (its own titleset), title A
    stereo; a stereo source asked for 5.1 gets a warning."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-e2e-51-")
        rc, _, err = run_cli("init", "surround", cwd=cls.tmp)
        assert rc == 0, err
        proj = os.path.join(cls.tmp, "surround")
        # 6 s of video with a different tone on each of the six channels
        tones = "|".join(f"0.3*sin({f}*2*PI*t)" for f in (330, 440, 550, 60, 660, 770))
        subprocess.run(["ffmpeg", "-v", "error", "-y",
                        "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30000/1001:d=6",
                        "-f", "lavfi", "-i", f"aevalsrc={tones}:c=5.1:s=48000:d=6",
                        "-c:v", "mpeg4", "-q:v", "5", "-c:a", "aac", "-b:a", "384k",
                        "-shortest", os.path.join(proj, "media", "surround.mp4")], check=True)
        path = os.path.join(proj, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["titles"][1].update({"source": "media/surround.mp4",
                                  "audio": {"codec": "ac3", "channels": 6}})
        cls.data, cls.path = data, path
        with open(path, "w") as f:
            json.dump(data, f)
        cls.iso = os.path.join(cls.tmp, "surround.iso")
        rc, out, err = run_cli("--json", "iso", path, "-o", cls.iso, "--fast", cwd=cls.tmp)
        assert rc == 0, err + out
        cls.result = json_lines(out)[-1]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_51_track(self):
        self.assertEqual([(t["titleset"], t["audio_channels"]) for t in self.result["titles"]],
                         [(1, 2), (2, 6)])
        vob = iso_extract(self.iso, "/VIDEO_TS/VTS_02_1.VOB", os.path.join(self.tmp, "b.vob"))
        a = next(s for s in ffprobe_streams(vob) if s["codec_type"] == "audio")
        self.assertEqual((a["codec_name"], a["channels"]), ("ac3", 6))
        # the centre channel (550 Hz in the source) survived as its own channel
        p = subprocess.run(["ffmpeg", "-v", "info", "-i", vob, "-vn",
                            "-af", "pan=mono|c0=FC,volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True)
        mean = float(p.stderr.split("mean_volume:")[1].split("dB")[0])
        self.assertGreater(mean, -30)

    @unittest.skipUnless(LIBDVDNAV, "libdvdnav not installed")
    def test_player_sees_six_channels(self):
        with dvdnav_sim.DvdSim(self.iso, LIBDVDNAV) as d:
            self.assertEqual(d.wait_menu(), 1)
            d.activate(3)                                   # SAMPLE TITLE B
            self.assertEqual(d.wait_title(), (2, 1))
            self.assertEqual(d.audio_channels(0), 6)

    def test_stereo_source_warns(self):
        data = json.loads(json.dumps(self.data))
        data["titles"][0]["audio"] = {"codec": "ac3", "channels": 6}
        path = os.path.join(self.tmp, "surround", "warn.oncemore.json")
        with open(path, "w") as f:
            json.dump(data, f)
        rc, out, err = run_cli("--json", "validate", path, cwd=self.tmp)
        self.assertEqual(rc, 0, err + out)
        self.assertIn("only use the front speakers", out)


if __name__ == "__main__":
    unittest.main()
