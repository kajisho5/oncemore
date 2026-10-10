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
        self.assertEqual(self.result["iso"], self.iso)
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
            # title 1 ends -> end_action title:t2
            self.assertEqual(d.play_to_end_of_title(), ("title", (2, 1)))
            # title 2 ends -> end_action menu:main
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

    def test_validate_reports_plan(self):
        rc, out, err = run_cli("--json", "validate", self.project)
        self.assertEqual(rc, 0, err)
        r = json_lines(out)[-1]
        self.assertEqual(r["video_bps"], 8_000_000)
        self.assertEqual([t["audio"] for t in r["titles"]], ["lpcm", "lpcm"])
        self.assertEqual(r["titles"][0]["chapters"], [0.0, 8.0, 16.0])

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


if __name__ == "__main__":
    unittest.main()
