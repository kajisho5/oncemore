"""One disc per session, in batch (DECISIONS §140): `oncemore batch` builds
one verified DVD image per CSV row from a template project, with a manifest."""

import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from oncemore import batch, build, iso as isomod, tools
from oncemore.errors import OncemoreError, ProjectError
from oncemore.report import Reporter

from .helpers import ROOT, have, json_lines, run_cli

DVD_OK = have("ffmpeg", "ffprobe") and tools.has_drawtext()
EXAMPLE = os.path.join(ROOT, "examples", "batch")


def copy_example(dest, media=True):
    shutil.copytree(EXAMPLE, dest, ignore=shutil.ignore_patterns("media", ".oncemore-cache"))
    if media:
        os.makedirs(os.path.join(dest, "media"))
        for n in ("01", "02", "03"):
            subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-v", "error", "-y",
                            "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30000/1001:duration=2",
                            "-f", "lavfi", "-i", "sine=duration=2", "-shortest",
                            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
                            os.path.join(dest, "media", f"session-{n}.mp4")], check=True)
    return dest


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class TestSessions(unittest.TestCase):
    """The CSV and the template, checked before anything is encoded."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oncemore-batch-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.dir = copy_example(os.path.join(self.tmp, "t"), media=False)

    def write(self, text):
        path = os.path.join(self.tmp, "s.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_fill(self):
        got, missing = batch.fill({"a": ["{{x}} and {{ y }}", 3], "b": "{{z}}"},
                                  {"x": "1", "y": "2"})
        self.assertEqual(got, {"a": ["1 and 2", 3], "b": "{{z}}"})
        self.assertEqual(missing, ["z"])

    def test_rows_become_projects(self):
        jobs = batch.plan(self.dir, os.path.join(self.dir, "sessions.csv"), check_files=False)
        self.assertEqual([j[1]["name"] for j in jobs], ["session-01", "session-02", "session-03"])
        p = jobs[1][2]
        self.assertEqual(p.disc.label, "SESSION_02")
        self.assertEqual(p.titles[0].name, "Dr. Ken Ito")
        self.assertTrue(p.titles[0].source.endswith(os.path.join("media", "session-02.mp4")))
        self.assertEqual([t.text for t in p.menus[0].texts][1:],
                         ["Dr. Ken Ito", "Imaging in practice"])

    def test_problems_named_by_row(self):
        path = self.write("name,label,speaker,video\n"            # (no `talk` column)
                          "a,A,X,a.mp4\n")
        with self.assertRaises(ProjectError) as cm:
            batch.plan(self.dir, path, check_files=False)
        self.assertIn("{{talk}}", str(cm.exception.issues))
        path = self.write("name,label,speaker,talk,video\n"
                          "same,A,X,T,a.mp4\nSame,B,Y,T,b.mp4\n../x,C,Z,T,c.mp4\n")
        with self.assertRaises(ProjectError) as cm:
            batch.plan(self.dir, path, check_files=False)
        issues = {i["path"]: i["message"] for i in cm.exception.issues}
        self.assertEqual(issues["row 2 (Same).name"], "the same as row 1")
        self.assertIn("row 3 (../x).name", issues)
        # a row's missing video is found before anything is built
        path = self.write("name,label,speaker,talk,video\nok,A,X,T,nothere.mp4\n")
        with self.assertRaises(ProjectError) as cm:
            batch.plan(self.dir, path)
        self.assertTrue(any(i["path"].startswith("row 1 (ok): titles[0].source")
                            for i in cm.exception.issues), cm.exception.issues)

    @unittest.skipUnless(have("ffprobe"), "needs ffprobe")
    def test_media_probed_before_anything_is_built(self):
        # a file that is there but is no video: found in the plan, by row
        with open(self._media("bad.mp4"), "w") as f:
            f.write("not a video")
        path = self.write("name,label,speaker,talk,video\nok,A,X,T,bad.mp4\n")
        with self.assertRaises(ProjectError) as cm:
            batch.plan(self.dir, path)
        self.assertEqual([i["path"] for i in cm.exception.issues], ["row 1 (ok)"])
        self.assertIn("bad.mp4", cm.exception.issues[0]["message"])

    def _media(self, name):
        os.makedirs(os.path.join(self.dir, "media"), exist_ok=True)
        return os.path.join(self.dir, "media", name)

    def test_template_is_an_object(self):
        with open(os.path.join(self.dir, "project.oncemore.json"), "w") as f:
            f.write("[]")
        with self.assertRaises(ProjectError):
            batch.plan(self.dir, os.path.join(self.dir, "sessions.csv"), check_files=False)

    def test_manifest_written_before_the_builds(self):
        # an earlier run's manifest does not outlive a run whose first image fails
        out = os.path.join(self.tmp, "out")
        os.makedirs(out)
        with open(os.path.join(out, "manifest.json"), "w") as f:
            f.write('{"images": [{"name": "stale"}]}')
        orig_plan, orig_build = batch.plan, batch.build.build_iso

        def failing(*a, **k):
            raise OncemoreError("encoder failed")
        batch.plan = lambda *a, **k: orig_plan(*a, **dict(k, check_files=False))
        batch.build.build_iso = failing
        try:
            with self.assertRaises(OncemoreError):
                batch.run(self.dir, os.path.join(self.dir, "sessions.csv"), out,
                          Reporter(json_mode=True, out=io.StringIO()))
        finally:
            batch.plan, batch.build.build_iso = orig_plan, orig_build
        with open(os.path.join(out, "manifest.json")) as f:
            self.assertEqual(json.load(f)["images"], [])

    def test_csv_needs_name_and_rows(self):
        with self.assertRaises(OncemoreError):
            batch.read_sessions(self.write("label,video\nA,a.mp4\n"))
        with self.assertRaises(OncemoreError):
            batch.read_sessions(self.write("name,label\n"))
        with self.assertRaises(OncemoreError):                  # (a row is not left out)
            batch.read_sessions(self.write("name,label\nok,A\n,,bad\n"))
        cols, rows = batch.read_sessions(self.write("\ufeffname, label\nx , X\n\n"))
        self.assertEqual((cols, rows), (["name", "label"], [{"name": "x", "label": "X"}]))

    def test_dvd_only(self):
        path = os.path.join(self.dir, "project.oncemore.json")
        with open(path) as f:
            data = json.load(f)
        data["disc"]["format"] = "bluray"
        with open(path, "w") as f:
            json.dump(data, f)
        with self.assertRaises(OncemoreError) as cm:
            batch.plan(self.dir, os.path.join(self.dir, "sessions.csv"), check_files=False)
        self.assertIn("DVD", cm.exception.message)


@unittest.skipUnless(DVD_OK, "needs ffmpeg (drawtext) and ffprobe")
class TestBatch(unittest.TestCase):
    """Done when: a 3-row fixture writes three verified images and one manifest."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="oncemore-batch-")
        cls.dir = copy_example(os.path.join(cls.tmp, "t"))
        cls.out = os.path.join(cls.tmp, "out")
        cls.rc, cls.stdout, cls.stderr = run_cli(
            "--json", "batch", cls.dir, os.path.join(cls.dir, "sessions.csv"), "-o", cls.out,
            "--fast")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_three_verified_images_and_a_manifest(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        result = json_lines(self.stdout)[-1]
        self.assertTrue(result["ok"])
        self.assertEqual(sorted(os.listdir(self.out)),
                         ["manifest.json", "session-01.iso", "session-02.iso", "session-03.iso"])
        with open(os.path.join(self.out, "manifest.json")) as f:
            manifest = json.load(f)
        self.assertEqual(manifest["images"], result["images"])
        self.assertEqual([i["row"] for i in manifest["images"]], [1, 2, 3])
        for i in manifest["images"]:
            iso = os.path.join(self.out, i["image"])
            self.assertEqual(i["sha256"], sha256(iso))
            self.assertEqual(i["bytes"], os.path.getsize(iso))
            self.assertEqual(i["label"], i["name"].upper().replace("-", "_"))
            self.assertGreaterEqual(i["verified"]["files"], 4)     # VIDEO_TS + a titleset
        # each disc is its own session (different menus and titles)
        self.assertEqual(len({i["sha256"] for i in manifest["images"]}), 3)
        events = [e for e in json_lines(self.stdout) if e.get("event") == "step"]
        self.assertEqual(sum(e["step"] == "verify" for e in events), 3)

    def test_verify_finds_a_changed_byte(self):
        self.assertEqual(self.rc, 0, self.stderr + self.stdout)
        # an image checked against the VIDEO_TS authored for it; one byte off fails
        disc = os.path.join(self.tmp, "disc")
        project = batch.plan(self.dir, os.path.join(self.dir, "sessions.csv"))[0][2]
        build.build(project, disc, Reporter(json_mode=True, out=io.StringIO()), fast=True)
        iso = os.path.join(self.tmp, "one.iso")
        isomod.make_iso(disc, iso, "SESSION_01", "builtin")
        self.assertEqual(batch.verify(iso, disc, "SESSION_01")["files"],
                         len(os.listdir(os.path.join(disc, "VIDEO_TS"))))
        with self.assertRaises(OncemoreError):
            batch.verify(iso, disc, "SESSION_02")              # another session's label
        with open(iso, "rb") as f:
            files = batch._iso9660_files(f)
        sector, _ = files["VIDEO_TS.IFO"]
        with open(iso, "r+b") as f:
            f.seek(sector * 2048 + 100)
            b = f.read(1)
            f.seek(sector * 2048 + 100)
            f.write(bytes([b[0] ^ 0xFF]))
        with self.assertRaises(OncemoreError) as cm:
            batch.verify(iso, disc, "SESSION_01")
        self.assertIn("VIDEO_TS.IFO", cm.exception.message)


if __name__ == "__main__":
    unittest.main()
