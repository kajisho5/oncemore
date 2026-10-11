"""`oncemore gui`: JSON API tests (always) and a browser test (Playwright, optional)."""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest import mock

from oncemore import tools
from oncemore.gui.server import make_server, safe_name

from .helpers import have

MEDIA_TOOLS = (have("ffmpeg", "ffprobe", "dvdauthor", "spumux") and tools.has_drawtext()
               and tools.iso_tool()[0] is not None)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT = True
except ImportError:  # pragma: no cover - optional dev dependency
    PLAYWRIGHT = False


class GuiServer:
    def __init__(self, directory):
        self.server, self.app = make_server(directory)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.app.port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, path, method="GET", body=None, raw=None, token=True, headers=None):
        h = dict(headers or {})
        if token:
            h["X-Oncemore-Token"] = self.app.token
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                payload = r.read()
                ctype = r.headers.get("Content-Type", "")
                return r.status, (json.loads(payload) if "json" in ctype else payload)
        except urllib.error.HTTPError as e:
            payload = e.read()
            try:
                return e.code, json.loads(payload)
            except ValueError:
                return e.code, payload


class TestGuiApi(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-gui-")
        self.s = GuiServer(self.dir)

    def tearDown(self):
        self.s.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_security(self):
        self.assertEqual(self.s.call("/api/state", token=False)[0], 401)
        self.assertEqual(self.s.call("/api/state", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.s.call("/api/state", headers={"Host": f"localhost:{self.s.app.port}"})[0], 200)
        # ?token= only works for <img> endpoints
        q = f"?token={self.s.app.token}"
        self.assertEqual(self.s.call("/api/state" + q, token=False)[0], 401)
        os.makedirs(os.path.join(self.dir, "media"))
        with open(os.path.join(self.dir, "media", "a.png"), "wb") as f:
            f.write(b"\x89PNG fake")
        self.assertEqual(self.s.call(f"/api/file?path=media/a.png&token={self.s.app.token}",
                                     token=False)[0], 200)
        for path in ("../../etc/passwd", "/etc/passwd", "media/../../x.png"):
            self.assertEqual(self.s.call("/api/file?path=" + path)[0], 403, path)
        # the project file itself is not an image: not served
        self.assertEqual(self.s.call("/api/file?path=project.oncemore.json")[0], 403)
        self.assertEqual(self.s.call("/", token=False)[0], 200)            # static page

    def test_frames_kept_by_size(self):
        app = self.s.app
        app.FRAME_CACHE_BYTES = 1000
        for k in range(5):
            app._remember(k, b"x" * 300)
        self.assertEqual(list(app.frame_cache), [2, 3, 4])          # the oldest go first
        self.assertEqual(app.frame_bytes, 900)
        app._remember(3, b"y" * 100)                                 # (replaced, not added)
        self.assertEqual(app.frame_bytes, 700)
        self.assertEqual(app._cached(3), b"y" * 100)
        app._remember("big", b"z" * 5000)                            # alone, over the cap
        self.assertEqual(list(app.frame_cache), ["big"])

    def test_previews_a_few_at_a_time(self):
        """Many titles asking for previews at once: two ffmpegs, not twelve."""
        app = self.s.app
        os.makedirs(os.path.join(self.dir, "media"))
        files = []
        for k in range(6):
            files.append(os.path.join(self.dir, "media", f"v{k}.mp4"))
            with open(files[-1], "wb") as f:
                f.write(bytes([k]) * 64)
        lock, running, most, go = threading.Lock(), [0], [0], threading.Event()

        def ffmpeg(args, duration, log, on_progress, what=""):
            with lock:
                running[0] += 1
                most[0] = max(most[0], running[0])
            go.wait(10)
            with open(args[-1], "wb") as f:
                f.write(b"proxy")
            with lock:
                running[0] -= 1
        with mock.patch.object(app, "proxy_codecs", return_value=[]), \
                mock.patch.object(app, "probe", return_value={"duration": 1.0}), \
                mock.patch("oncemore.encode.run_ffmpeg", side_effect=ffmpeg):
            for f in files:
                self.assertEqual(app.proxy_status(f, start=True)[0]["state"], "running")
            time.sleep(0.5)
            self.assertEqual(most[0], app.PROXIES_AT_ONCE)
            go.set()
            for f in files:
                for _ in range(100):
                    if app.proxy_status(f)[0]["state"] != "running":
                        break
                    time.sleep(0.05)
                self.assertEqual(app.proxy_status(f)[0]["state"], "ready")
        self.assertEqual(most[0], app.PROXIES_AT_ONCE)
        left = os.listdir(os.path.join(self.dir, ".oncemore-cache", "proxy"))
        self.assertFalse([n for n in left if n.endswith(".part")])

    def test_running_job_and_old_jobs(self):
        app = self.s.app
        self.s.call("/api/new", "POST", {"label": "jobs", "sample": True})
        app.JOBS_KEPT = 3
        done = []
        for _ in range(4):
            done.append(app.start_job("transcode", lambda project, rep: {}))
            done[-1].thread.join(10)
        self.assertIsNone(self.s.call("/api/state")[1]["job"])
        go = threading.Event()
        job = app.start_job("iso", lambda project, rep: go.wait(10) and {})
        self.assertEqual(self.s.call("/api/state")[1]["job"], {"id": job.id, "kind": "iso"})
        self.assertEqual(len(app.jobs), 3)                          # the oldest done ones went
        self.assertNotIn(done[0].id, app.jobs)
        self.assertEqual(self.s.call(f"/api/jobs/{done[0].id}")[0], 404)
        go.set()
        job.thread.join(10)
        self.assertIsNone(self.s.call("/api/state")[1]["job"])

    def test_backups(self):
        app = self.s.app
        self.assertEqual(self.s.call("/api/backups")[1]["backups"], [])
        self.s.call("/api/new", "POST", {"label": "first"})
        with open(app.path) as f:
            data = json.load(f)
        app.save(dict(data, disc=dict(data["disc"], label="SECOND")))     # keeps "first"
        app.save(dict(data, disc=dict(data["disc"], label="THIRD")))      # too soon: no new one
        names = [b["name"] for b in self.s.call("/api/backups")[1]["backups"]]
        self.assertEqual(len(names), 1)
        status, r = self.s.call("/api/backup?name=" + names[0])
        self.assertEqual((status, r["project"]["disc"]["label"]), (200, "first"))
        for bad in ("../project.oncemore.json", "x.json", ""):
            self.assertEqual(self.s.call("/api/backup?name=" + bad)[0], 400, bad)
        # only the newest are kept
        backups = os.path.join(self.dir, ".oncemore-backup")
        for k in range(5):
            with open(os.path.join(backups, f"project-20200101-00000{k}.json"), "w") as f:
                json.dump(data, f)
            os.utime(os.path.join(backups, f"project-20200101-00000{k}.json"), (1e9 + k, 1e9 + k))
        app.BACKUP_KEEP = 3
        self.assertIsNotNone(app.backup(force=True))
        self.assertEqual(len(os.listdir(backups)), 3)
        self.assertNotIn("project-20200101-000000.json", os.listdir(backups))
        # the media list does not show them
        self.assertFalse(any(m["path"].startswith(".oncemore-backup") for m in app.media()))

    def test_open_and_stat(self):
        os.makedirs(os.path.join(self.dir, "media"))
        path = os.path.join(self.dir, "media", "menu.psd")
        with open(path, "wb") as f:
            f.write(b"8BPS fake")
        status, st = self.s.call("/api/stat?path=media/menu.psd")
        self.assertEqual(status, 200)
        self.assertTrue(st["exists"])
        self.assertEqual(st["bytes"], 9)
        os.utime(path, (st["mtime"] + 5, st["mtime"] + 5))
        self.assertAlmostEqual(self.s.call("/api/stat?path=media/menu.psd")[1]["mtime"], st["mtime"] + 5)
        self.assertFalse(self.s.call("/api/stat?path=media/gone.psd")[1]["exists"])
        # opening is limited to existing files in the project folder
        self.assertEqual(self.s.call("/api/open", "POST", {"path": "../x.psd"})[0], 403)
        self.assertEqual(self.s.call("/api/open", "POST", {"path": "media/gone.psd"})[0], 404)
        self.assertEqual(self.s.call("/api/stat?path=/etc/passwd")[0], 403)

    def test_projects_open_recent_save_as_and_exports(self):
        """File > New / Open / Open recent / Save as, and the files the menus
        export (here: subtitles as SubRip)."""
        cfg, other = tempfile.mkdtemp(prefix="oncemore-cfg-"), tempfile.mkdtemp(prefix="oncemore-other-")
        self.addCleanup(shutil.rmtree, cfg, True)
        self.addCleanup(shutil.rmtree, other, True)
        other = os.path.realpath(other)
        q = lambda p: urllib.parse.quote(p)  # noqa: E731
        with mock.patch.dict(os.environ, {"ONCEMORE_CONFIG": cfg}):
            self.s.call("/api/new", "POST", {"label": "FIRST"})
            # the folder chooser: folders only (no files, no hidden ones), projects marked
            for d in ("b-project", "a-empty", ".hidden"):
                os.makedirs(os.path.join(other, d))
            with open(os.path.join(other, "b-project", "project.oncemore.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(other, "file.txt"), "w") as f:
                f.write("x")
            status, r = self.s.call("/api/dirs?path=" + q(other))
            self.assertEqual(status, 200)
            self.assertEqual(r["dirs"], [{"name": "a-empty", "project": False}, {"name": "b-project", "project": True}])
            self.assertEqual(r["parent"], os.path.dirname(other))
            self.assertEqual(self.s.call("/api/dirs?path=relative/x")[0], 400)
            self.assertEqual(self.s.call("/api/dirs?path=" + q(os.path.join(other, "nope")))[0], 404)
            # Open: a folder that is not there is made only for a new project
            new = os.path.join(other, "c-new")
            self.assertEqual(self.s.call("/api/switch", "POST", {"path": new})[0], 404)
            status, r = self.s.call("/api/switch", "POST", {"path": new, "create": True})
            self.assertEqual((status, r["project"], r["dir"]), (200, None, new))
            self.s.call("/api/new", "POST", {"label": "SECOND"})
            self.assertTrue(os.path.isfile(os.path.join(new, "project.oncemore.json")))
            status, r = self.s.call("/api/switch", "POST", {"path": self.dir})
            self.assertEqual(r["project"]["disc"]["label"], "FIRST")
            # Open recent: newest first
            recent = self.s.call("/api/recent")[1]["recent"]
            self.assertEqual([x["path"] for x in recent], [os.path.realpath(self.dir), new])
            self.assertTrue(all(x["exists"] for x in recent))
            # Save as: the project and its media, not what a build makes again;
            # the copy is then the project (with the page's edits), the original stays
            os.makedirs(os.path.join(self.dir, "output"))
            os.makedirs(os.path.join(self.dir, ".oncemore-cache", "proxy"))
            with open(os.path.join(self.dir, "media", "b.vtt"), "w", encoding="utf-8") as f:
                f.write("WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nHello\n")
            with open(os.path.join(self.dir, "output", "disc.iso"), "w") as f:
                f.write("iso")
            with open(self.s.app.path) as f:
                edited = json.load(f)
            edited["disc"]["label"] = "COPY"
            dest = os.path.join(other, "d-copy")
            status, r = self.s.call("/api/save_as", "POST", {"path": dest, "project": edited})
            self.assertEqual((status, r["dir"], r["project"]["disc"]["label"]), (200, dest, "COPY"))
            # (the copy as it was before the page's edits is its first backup)
            self.assertEqual(sorted(os.listdir(dest)), [".oncemore-backup", "media", "project.oncemore.json"])
            self.assertEqual(sorted(os.listdir(os.path.join(dest, "media"))), ["b.vtt"])
            with open(os.path.join(self.dir, "project.oncemore.json")) as f:
                self.assertEqual(json.load(f)["disc"]["label"], "FIRST")
            self.assertEqual(self.s.call("/api/recent")[1]["recent"][0]["path"], dest)
            self.assertEqual(self.s.call("/api/save_as", "POST", {"path": new})[0], 422)        # not empty
            self.assertEqual(self.s.call("/api/save_as", "POST", {"path": os.path.join(dest, "x")})[0], 400)
            # Export subtitles: SubRip in exports/, never over an earlier one
            status, r = self.s.call("/api/export", "POST", {"kind": "subtitles", "path": "media/b.vtt"})
            self.assertEqual((status, r["path"]), (200, "exports/b.srt"))
            with open(os.path.join(dest, "exports", "b.srt"), encoding="utf-8") as f:
                self.assertEqual(f.read().strip(), "1\n00:00:01,000 --> 00:00:02,500\nHello")
            self.assertEqual(self.s.call("/api/export", "POST", {"kind": "subtitles", "path": "media/b.vtt"})[1]["path"],
                             "exports/b-2.srt")
            self.assertEqual(self.s.call("/api/export", "POST", {"kind": "subtitles", "path": "../x.srt"})[0], 403)
            self.assertEqual(self.s.call("/api/export", "POST", {"kind": "nothing"})[0], 400)
            # nothing switches while a build runs
            from oncemore.gui.server import Job
            self.s.app.jobs["j"] = Job("j", "build")
            self.assertEqual(self.s.call("/api/switch", "POST", {"path": self.dir})[0], 422)
            self.assertEqual(self.s.app.dir, dest)

    def test_new_save_and_upload(self):
        status, st = self.s.call("/api/state")
        self.assertEqual(status, 200)
        self.assertIsNone(st["project"])
        status, st = self.s.call("/api/new", "POST", {"label": "My disc", "standard": "PAL",
                                                      "aspect": "4:3"})
        self.assertEqual(status, 200)
        self.assertEqual(st["project"]["disc"]["standard"], "PAL")
        self.assertFalse(st["check"]["valid"])                             # no titles yet
        self.assertEqual(self.s.call("/api/new", "POST", {})[0], 422)      # exists already
        # uploads land in media/, names are sanitised, duplicates renamed
        status, r = self.s.call("/api/upload?name=" + "..%2F..%2Fevil.srt", "POST",
                                raw=b"1\n00:00:01,000 --> 00:00:02,000\nhi\n")
        self.assertEqual(status, 200)
        self.assertEqual(r["path"], "media/evil.srt")
        status, r = self.s.call("/api/upload?name=evil.srt", "POST", raw=b"x")
        self.assertEqual(r["path"], "media/evil-2.srt")
        self.assertEqual(self.s.call("/api/upload?name=run.sh", "POST", raw=b"x")[0], 400)
        self.assertEqual(sorted(m["path"] for m in r["media"]), ["media/evil-2.srt", "media/evil.srt"])
        # save round trip
        project = st["project"]
        project["titles"] = [{"id": "t1", "source": "media/missing.mp4"}]
        status, r = self.s.call("/api/project", "PUT", {"project": project})
        self.assertTrue(r["saved"])
        self.assertIn("file not found", json.dumps(r["check"]["issues"]))
        with open(os.path.join(self.dir, "project.oncemore.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f), project)

    def test_safe_name(self):
        self.assertEqual(safe_name("../a b/映像 1.mp4"), "映像 1.mp4")
        self.assertEqual(safe_name("x;rm -rf.mov"), "x_rm -rf.mov")
        self.assertEqual(safe_name("..."), "file")

    @unittest.skipUnless(MEDIA_TOOLS, "needs ffmpeg/dvdauthor/ISO tool")
    def test_sample_preview_frame_and_build(self):
        status, st = self.s.call("/api/new", "POST", {"sample": True})
        self.assertEqual(status, 200)
        self.assertTrue(st["check"]["valid"], st["check"])
        status, info = self.s.call("/api/probe?path=media/sample_a.mp4")
        self.assertAlmostEqual(info["duration"], 24, delta=0.1)
        status, jpg = self.s.call(f"/api/frame?path=media/sample_a.mp4&t=3&w=320")
        self.assertEqual(status, 200)
        self.assertEqual(jpg[:2], b"\xff\xd8")
        status, pv = self.s.call("/api/preview", "POST", {"menu": "main", "outline": True})
        self.assertEqual(status, 200, pv)
        self.assertTrue(pv["image"].startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(pv["image"].split(",", 1)[1])[:4], b"\x89PNG")
        self.assertEqual([b["id"] for b in pv["buttons"]], ["play", "ch", "b"])
        # unsaved edits can be previewed
        project = st["project"]
        project["menus"][0]["buttons"][0]["label"] = "再生"
        status, pv2 = self.s.call("/api/preview", "POST", {"menu": "main", "project": project})
        self.assertEqual(status, 200)
        self.assertNotEqual(pv2["buttons"][0]["rect"], pv["buttons"][0]["rect"])
        status, v = self.s.call("/api/validate", "POST")
        self.assertTrue(v["valid"])
        status, err = self.s.call("/api/build", "POST", {"format": "hddvd", "kind": "iso"})
        self.assertEqual(status, 400, err)
        status, job = self.s.call("/api/build", "POST", {"kind": "iso", "fast": True})
        self.assertEqual(status, 200)
        self.assertEqual(self.s.call("/api/build", "POST", {"kind": "iso"})[0], 422)  # busy
        since, events = 0, []
        for _ in range(600):
            status, r = self.s.call(f"/api/jobs/{job['job']}?since={since}")
            events += r["events"]
            since = r["next"]
            if r["done"]:
                break
            time.sleep(0.5)
        self.assertTrue(r["ok"], events[-1])
        self.assertEqual(events[-1]["event"], "result")
        self.assertTrue(any(e["event"] == "progress" for e in events))
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "output", "SAMPLE_DISC.iso")))

    @unittest.skipUnless(MEDIA_TOOLS, "needs ffmpeg/dvdauthor/ISO tool")
    def test_build_web(self):
        """Build > Web (HTML5): a folder with index.html and the titles."""
        self.s.call("/api/new", "POST", {"sample": True})
        status, job = self.s.call("/api/build", "POST", {"format": "web", "kind": "iso",
                                                         "fast": True})
        self.assertEqual(status, 200, job)
        for _ in range(600):
            status, r = self.s.call(f"/api/jobs/{job['job']}")
            if r["done"]:
                break
            time.sleep(0.5)
        self.assertTrue(r["ok"], r["events"][-1:])
        result = r["events"][-1]
        self.assertEqual(result["event"], "result")
        out = os.path.join(self.dir, "output", "SAMPLE_DISC_web")
        # (macOS: the temporary folder is behind a symlink, /var -> /private/var)
        self.assertEqual(os.path.realpath(result["index"]),
                         os.path.realpath(os.path.join(out, "index.html")))
        for name in ("index.html", "disc.js", "titles/t1.mp4", "titles/t2.mp4", "menus/main.png"):
            self.assertTrue(os.path.isfile(os.path.join(out, name)), name)

    @unittest.skipUnless(MEDIA_TOOLS, "needs ffmpeg/dvdauthor/ISO tool")
    def test_playback_proxy(self):
        self.s.call("/api/new", "POST", {"sample": True})
        src = os.path.realpath(os.path.join(self.dir, "media", "sample_b.mp4"))  # macOS /var
        for fmt, magic, codecs in (("mp4", b"ftyp", ["aac", "h264"]),
                                   ("webm", b"\x1a\x45\xdf\xa3", ["opus", "vp8"])):
            q = f"path=media/sample_b.mp4&format={fmt}"
            self.assertEqual(self.s.call(f"/api/proxy?{q}")[0], 404)         # not made yet
            for _ in range(240):
                status, st = self.s.call(f"/api/proxy?{q}", "POST")
                self.assertEqual(status, 200, st)
                if st["state"] != "running":
                    break
                time.sleep(0.25)
            self.assertEqual(st["state"], "ready", st)
            # the <video> element sends ?token= and byte ranges
            url = f"/api/proxy?{q}&token={self.s.app.token}"
            status, whole = self.s.call(url, token=False)
            self.assertEqual(status, 200)
            self.assertIn(magic, whole[:8])
            status, part = self.s.call(url, token=False, headers={"Range": "bytes=100-199"})
            self.assertEqual((status, part), (206, whole[100:200]))
            status, tail = self.s.call(url, token=False, headers={"Range": "bytes=-10"})
            self.assertEqual((status, tail), (206, whole[-10:]))
            self.assertEqual(self.s.call(url, token=False,
                                         headers={"Range": f"bytes={len(whole)}-"})[0], 416)
            streams = json.loads(subprocess.run(
                [tools.find("ffprobe"), "-v", "error", "-show_streams", "-of", "json",
                 self.s.app.proxy_status(src, fmt)[1]],
                capture_output=True, text=True).stdout)["streams"]
            self.assertEqual(sorted(x["codec_name"] for x in streams), codecs)
            v = next(x for x in streams if x["codec_type"] == "video")
            self.assertEqual(v["height"], 360)
        # cached on disk: a new server finds it without encoding again
        s2 = GuiServer(self.dir)
        try:
            self.assertEqual(s2.call("/api/proxy?path=media/sample_b.mp4", "POST")[1]["state"],
                             "ready")
        finally:
            s2.close()
        # only videos inside the project, known formats
        self.assertEqual(self.s.call("/api/proxy?path=media/menu_bg.png", "POST")[0], 403)
        self.assertEqual(self.s.call("/api/proxy?path=../x.mp4", "POST")[0], 403)
        self.assertEqual(self.s.call("/api/proxy?path=media/sample_b.mp4&format=avi",
                                     "POST")[0], 400)
        # the cache folder is not listed as media
        _, state = self.s.call("/api/state")
        self.assertFalse(any(".oncemore-cache" in m["path"] for m in state["media"]))

    def test_subtitle_editor_api(self):
        self.s.call("/api/new", "POST", {"sample": True})
        cues = [{"start": 4, "end": 6, "text": "Second", "position": "top"},
                {"start": 1, "end": 3.5, "text": "First line\nand another"},
                {"start": 7, "end": 7, "text": "zero length is dropped"},
                {"start": 8, "end": 9, "text": "   "}]
        status, r = self.s.call("/api/subtitles?path=media/new.srt", "PUT", {"cues": cues})
        self.assertEqual(status, 200, r)
        self.assertEqual(r["cues"], 2)
        self.assertIn("media/new.srt", [m["path"] for m in r["media"]])
        status, r = self.s.call("/api/subtitles?path=media/new.srt")
        self.assertEqual(status, 200, r)
        self.assertTrue(r["editable"])
        self.assertEqual([(c["start"], c["end"], c["text"], c["position"]) for c in r["cues"]],
                         [(1.0, 3.5, "First line\nand another", None), (4.0, 6.0, "Second", "top")])
        # other formats are read (and can be saved as .srt), never overwritten
        with open(os.path.join(self.dir, "media", "x.vtt"), "w", encoding="utf-8") as f:
            f.write("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n")
        status, r = self.s.call("/api/subtitles?path=media/x.vtt")
        self.assertEqual((status, r["editable"], r["cues"][0]["text"]), (200, False, "Hello"))
        self.assertEqual(self.s.call("/api/subtitles?path=media/x.vtt", "PUT", {"cues": []})[0], 400)
        self.assertEqual(self.s.call("/api/subtitles?path=media/menu_bg.png")[0], 403)
        self.assertEqual(self.s.call("/api/subtitles?path=../x.srt", "PUT", {"cues": []})[0], 403)
        self.assertEqual(self.s.call("/api/subtitles?path=media/none.srt")[0], 404)

    @unittest.skipUnless(MEDIA_TOOLS, "needs ffmpeg/dvdauthor/ISO tool")
    def test_clips_join(self):
        _, st = self.s.call("/api/new", "POST", {"sample": True})
        project = st["project"]
        project["titles"].append({"id": "joined", "clips": [
            {"source": "media/sample_a.mp4", "in": "00:00:01", "out": "00:00:03"},
            {"source": "media/sample_b.mp4", "out": 1.5}]})
        status, r = self.s.call("/api/clips", "POST", {"title": "joined", "project": project})
        self.assertEqual(status, 200, r)
        self.assertTrue(r["path"].startswith(".oncemore-cache/clips/"), r["path"])
        # whole frames per clip: 2 s and 1.5 s at 29.97 fps
        self.assertAlmostEqual(r["clips"][0]["duration"], 60 * 1001 / 30000, places=5)
        self.assertAlmostEqual(r["clips"][1]["duration"], 45 * 1001 / 30000, places=5)
        self.assertEqual(r["starts"], [0.0, round(60 * 1001 / 30000, 6)])
        self.assertEqual([c["source"] for c in r["clips"]], ["media/sample_a.mp4",
                                                             "media/sample_b.mp4"])
        fmt = json.loads(subprocess.run(
            [tools.find("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of",
             "json", os.path.join(self.dir, r["path"])], capture_output=True, text=True).stdout)
        self.assertAlmostEqual(float(fmt["format"]["duration"]), r["duration"], delta=0.05)
        self.assertEqual(sorted(x["codec_type"] for x in fmt["streams"]), ["audio", "video"])
        # cached: the same request does not render again
        mtime = os.path.getmtime(os.path.join(self.dir, r["path"]))
        _, r2 = self.s.call("/api/clips", "POST", {"title": "joined", "project": project})
        self.assertEqual(r2["path"], r["path"])
        self.assertEqual(os.path.getmtime(os.path.join(self.dir, r["path"])), mtime)
        # the simulator shows the clip that is playing in each chapter
        project["menus"][0]["buttons"][0]["action"] = "title:joined"
        status, sim = self.s.call("/api/sim", "POST", {"project": project})
        self.assertEqual(status, 200, sim)
        status, sim = self.s.call("/api/sim", "POST", {"project": project, "state": sim["state"],
                                                       "key": "enter"})
        self.assertEqual(sim["title"]["frame"], {"path": "media/sample_a.mp4", "t": 1.5})
        status, sim = self.s.call("/api/sim", "POST", {"project": project, "state": sim["state"],
                                                       "key": "next"})
        self.assertEqual(sim["title"]["frame"], {"path": "media/sample_b.mp4", "t": 0.5})
        self.assertEqual(self.s.call("/api/clips", "POST", {"title": "t1", "project": project})[0],
                         400)

    @unittest.skipUnless(MEDIA_TOOLS, "needs ffmpeg/dvdauthor/ISO tool")
    def test_transcode_now_and_waveform(self):
        _, st = self.s.call("/api/new", "POST", {"sample": True})
        status, r = self.s.call("/api/encode_status", "POST", {"project": st["project"]})
        self.assertEqual((status, r["titles"]), (200, {"t1": False, "t2": False}))
        status, r = self.s.call("/api/transcode", "POST", {"titles": ["t2"], "fast": True})
        self.assertEqual(status, 200, r)
        for _ in range(600):
            _, j = self.s.call(f"/api/jobs/{r['job']}")
            if j["done"]:
                break
            time.sleep(0.2)
        self.assertTrue(j["ok"], j["events"][-3:])
        self.assertEqual(j["events"][-1]["titles"], {"t2": "transcoded"})
        _, r = self.s.call("/api/encode_status", "POST", {"project": st["project"], "fast": True})
        self.assertEqual(r["titles"], {"t1": False, "t2": True})
        self.assertEqual(self.s.call("/api/transcode", "POST", {"titles": "t2"})[0], 400)
        # the sound of a title, drawn for the timeline
        status, png = self.s.call("/api/waveform?" + urllib.parse.urlencode(
            {"path": "media/sample_a.mp4", "w": 400, "h": 40}))
        self.assertEqual(status, 200)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(self.s.call("/api/waveform?path=media/menu_bg.png")[0], 403)

    @unittest.skipUnless(MEDIA_TOOLS, "needs ffmpeg/dvdauthor/ISO tool")
    def test_slideshow_render(self):
        _, st = self.s.call("/api/new", "POST", {"sample": True})
        project = st["project"]
        project["titles"].append({"id": "pics", "slideshow": {
            "slides": [{"image": "media/menu_bg.png", "duration": 2},
                       {"image": "media/menu_bg.png", "duration": 1.5}]}})
        status, r = self.s.call("/api/slideshow", "POST", {"title": "pics", "project": project})
        self.assertEqual(status, 200, r)
        self.assertEqual((r["duration"], r["starts"]), (3.5, [0.0, 2.0]))
        self.assertTrue(r["path"].startswith(".oncemore-cache/slideshow/"), r["path"])
        full = os.path.join(self.dir, r["path"])
        self.assertTrue(os.path.isfile(full))
        streams = json.loads(subprocess.run(
            [tools.find("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json",
             full], capture_output=True, text=True).stdout)
        self.assertEqual(streams["streams"][0]["codec_name"], "ffv1")
        self.assertAlmostEqual(float(streams["format"]["duration"]), 3.5, delta=0.1)
        # it plays in the page like any title
        for _ in range(240):
            status, p = self.s.call("/api/proxy?" + urllib.parse.urlencode({"path": r["path"]}),
                                    "POST")
            if p.get("state") != "running":
                break
            time.sleep(0.25)
        self.assertEqual(p["state"], "ready", p)
        self.assertEqual(self.s.call("/api/slideshow", "POST", {"title": "t1", "project": project})[0],
                         400)

    def test_graph_and_simulator_api(self):
        self.s.call("/api/new", "POST", {"sample": True})
        status, r = self.s.call("/api/graph", "POST", {})
        self.assertEqual(status, 200, r)
        self.assertIn("menu:chapters", [n["id"] for n in r["graph"]["nodes"]])
        self.assertEqual([n for n in r["notes"] if n["level"] == "warning"], [])
        _, st = self.s.call("/api/state")
        bad = json.loads(json.dumps(st["project"]))
        bad["titles"][0]["end_action"] = "menu:nope"
        self.assertEqual(self.s.call("/api/graph", "POST", {"project": bad})[0], 422)
        if not MEDIA_TOOLS:
            return
        status, r = self.s.call("/api/sim", "POST", {})
        self.assertEqual((status, r["view"]), (200, ["menu", "main", 1]))
        for key, view in (("down", ["menu", "main", 2]), ("enter", ["menu", "chapters", 1]),
                          ("right", ["menu", "chapters", 2]), ("enter", ["title", 1, 2])):
            status, r = self.s.call("/api/sim", "POST", {"state": r["state"], "key": key})
            self.assertEqual((status, r["view"]), (200, view), key)
        self.assertEqual(r["title"]["source"], "media/sample_a.mp4")
        self.assertEqual(self.s.call("/api/sim", "POST", {"state": r["state"], "key": "x"})[0], 400)
        status, m = self.s.call("/api/sim_menu", "POST", {"menu": "main"})
        self.assertEqual(status, 200, m)
        self.assertTrue(m["image"].startswith("data:image/png;base64,"))
        self.assertEqual(sorted(m["overlays"]), ["b", "ch", "play"])
        self.assertEqual(m["storage"], [720, 480])
        # with a normal colour, each overlay shows the selected button in the
        # highlight colour and the others in the normal colour
        from oncemore import png4
        with open(os.path.join(self.dir, "project.oncemore.json")) as f:
            pj = json.load(f)
        pj["menus"][0]["normal_color"] = "#FFFFFF60"
        status, m = self.s.call("/api/sim_menu", "POST", {"menu": "main", "project": pj})
        self.assertEqual(status, 200, m)
        canvas, pal = png4.read_indexed_png(base64.b64decode(m["overlays"]["ch"].split(",", 1)[1]))
        self.assertEqual(canvas.used_indices(), [0, 1, 3])
        self.assertEqual(tuple(pal[3]), (255, 255, 255, 0x60))



class TestDesignSystem(unittest.TestCase):
    """The design system holds: tokens are the only source of colours, every
    variable used is defined, and the two languages have the same keys."""

    STATIC = os.path.join(os.path.dirname(__file__), "..", "oncemore", "gui", "static")

    def read(self, name):
        with open(os.path.join(self.STATIC, name), encoding="utf-8") as f:
            return f.read()

    def test_variables_defined(self):
        defined = set(re.findall(r"(--[\w-]+)\s*:", self.read("tokens.css") + self.read("app.css")))
        for name in ("app.css", "app.js", "styleguide.html", "styleguide.js", "index.html"):
            used = {v for v in re.findall(r"var\((--[\w-]+)", self.read(name))
                    if not v.endswith("-")}           # (built in code: var(--c-kind-${k}))
            self.assertEqual(used - defined, set(), name)
        # the style guide shows every colour token
        colours = {v for v in re.findall(r"(--c-[\w-]+)\s*:", self.read("tokens.css"))}
        shown = set(re.findall(r"--c-[\w-]+", self.read("styleguide.html")))
        self.assertEqual(colours - shown - {"--c-scrim", "--c-text-on-accent"}, set())

    def test_no_raw_colours_outside_tokens(self):
        css = self.read("app.css")
        self.assertEqual(re.findall(r"#[0-9a-fA-F]{3,8}\b", css), [])

    def test_light_theme_covers_colours(self):
        tokens = self.read("tokens.css")
        dark, light = tokens.split(':root[data-theme="light"]')
        need = {v for v in re.findall(r"(--c-[\w-]+)\s*:", dark)
                if v not in ("--c-picture", "--c-on-picture", "--c-guide", "--c-menu-guide", "--c-hit")}
        self.assertEqual(need - set(re.findall(r"(--c-[\w-]+)\s*:", light)), set())

    # (text, ground) pairs the interface uses: text needs 4.5:1 (WCAG 2 AA)
    TEXT_PAIRS = [("c-text", g) for g in ("c-bg-1", "c-bg-2", "c-bg-3", "c-bg-4", "c-bg-5")] + [
        ("c-text-2", "c-bg-1"), ("c-text-2", "c-bg-2"), ("c-text-field", "c-field"),
        ("c-text-on-ui", "c-ui"), ("c-text-on-accent", "c-accent"), ("c-text-on-danger", "c-danger"),
        ("c-clip-text", "c-clip"), ("c-clip-text", "c-clip-head"), ("c-clip-text", "c-clip-audio"),
        ("c-timecode", "c-bg-1"), ("c-timecode", "c-bg-2"), ("c-danger", "c-bg-1"),
        ("c-danger", "c-bg-2"), ("c-warning", "c-bg-2"), ("c-success", "c-bg-2"),
        ("c-accent-text", "c-bg-1"), ("c-accent-text", "c-bg-2")]
    # marks (focus, fields, kind icons) need 3:1; "a|b": either is enough (a field
    # shows by its border or by its fill)
    MARK_PAIRS = [("c-active-panel", "c-bg-1"), ("c-focus", "c-bg-1"), ("c-ui", "c-bg-1"),
                  ("c-field-border|c-field", "c-bg-1")] + \
        [(f"c-kind-{k}", "c-bg-1") for k in ("menu", "title", "playlist", "remote", "audio",
                                              "subtitle", "chapter")]

    def skins(self):
        """Every token's value in each skin and theme (at the default Brightness)."""
        css = self.read("tokens.css")

        def block(sel):
            i = css.index(sel + " {")
            body = css[i:css.index("\n}", i)]
            return {m[0]: " ".join(m[1].split()) for m in re.findall(r"--([\w-]+):\s*([^;]+);", body)}
        base, classic = block(":root"), block(':root[data-skin="classic"]')
        light = block(':root[data-theme="light"]')
        return {"modern": base, "classic": {**base, **classic}, "light": {**base, **light},
                "classic light": {**base, **classic, **light}}

    @staticmethod
    def luminance(value, tokens):
        import colorsys
        v = value.strip()
        m = re.match(r"var\(--([\w-]+)\)$", v)
        if m:
            return TestDesignSystem.luminance(tokens[m[1]], tokens)
        v = re.sub(r"calc\(([\d.]+)% \+ var\(--ui-b\)\)", r"\1%", v)
        if v.startswith("#"):
            rgb = [int(v[k:k + 2], 16) / 255 for k in (1, 3, 5)]
        else:
            h, s, li = map(float, re.match(r"hsl\(([\d.]+) ([\d.]+)% ([\d.]+)%\)", v).groups())
            rgb = colorsys.hls_to_rgb(h / 360, li / 100, s / 100)
        lin = [c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4 for c in rgb]
        return .2126 * lin[0] + .7152 * lin[1] + .0722 * lin[2]

    def test_contrast(self):
        """Text 4.5:1 and marks 3:1 on the grounds they are used on, in both
        skins and both themes. One exception: on Classic's mid-grey panels
        no blue carries white text (4.5:1) and also stands 3:1 off the panel,
        so there c-ui only has to carry its text (Classic's tabs are boxed;
        the underline is not what tells them apart)."""
        bad = []
        for skin, tokens in self.skins().items():
            for pairs, need in ((self.TEXT_PAIRS, 4.5), (self.MARK_PAIRS, 3.0)):
                for fg, bg in pairs:
                    if skin.startswith("classic") and skin != "classic light" and fg == "c-ui":
                        continue
                    lb = self.luminance(tokens[bg], tokens)
                    best = 0
                    for f in fg.split("|"):
                        lf = self.luminance(tokens[f], tokens)
                        best = max(best, (max(lf, lb) + .05) / (min(lf, lb) + .05))
                    if best < need:
                        bad.append(f"{skin}: {fg} on {bg} {best:.2f}:1")
        self.assertEqual(bad, [])

    def test_brand_files(self):
        """The logo files the app serves: the brand colours, outlined (no
        fonts needed), and linked from the pages."""
        tokens = self.read("tokens.css")
        for name in ("favicon.svg", "brand-lockup.svg"):
            svg = self.read(name)
            self.assertNotIn("<text", svg)
            for colour in re.findall(r"#[0-9a-f]{6}", svg):
                self.assertIn(colour, tokens, f"{name}: {colour} is not a brand token")
        for page in ("index.html", "styleguide.html"):
            self.assertIn('rel="icon" href="favicon.svg"', self.read(page))
        self.assertIn("brand-lockup.svg", self.read("app.js"))
        icon = os.path.join(self.STATIC, "..", "..", "..", "macos", "AppIcon.png")
        with open(icon, "rb") as f:
            head = f.read(24)
        self.assertEqual((head[:8], int.from_bytes(head[16:20], "big"),
                          int.from_bytes(head[20:24], "big")), (b"\x89PNG\r\n\x1a\n", 1024, 1024))

    def test_i18n_keys_match(self):
        js = self.read("app.js")
        start = js.index("const I18N = {")
        body = js[start:js.index("\n};", start)]
        en, ja = body.split("\n  ja: {")
        key = re.compile(r"(?:^|[{,\s])([a-z][a-z0-9_]*):\s*\"", re.M)
        ken, kja = set(key.findall(en)), set(key.findall(ja))
        self.assertEqual(ken ^ kja, set())
        used = {k for k in re.findall(r"\bt\(\"([a-z0-9_]+)\"", js)
                if not k.endswith("_")}               # (prefixes completed in code)
        self.assertEqual(used - ken, set())

    def test_styleguide_served(self):
        d = tempfile.mkdtemp(prefix="oncemore-sg-")
        s = GuiServer(d)
        try:
            for name, ctype in (("styleguide.html", "text/html"), ("tokens.css", "text/css"),
                                ("styleguide.js", "javascript")):
                status, body = s.call("/" + name, token=False)
                self.assertEqual(status, 200, name)
            status, body = s.call("/styleguide.html", token=False)
            self.assertIn(b"tokens.css", body)
        finally:
            s.close()
            shutil.rmtree(d, ignore_errors=True)


def _chromium():
    exe = None
    for cand in ("/opt/pw-browsers/chromium", os.environ.get("ONCEMORE_TEST_CHROMIUM", "")):
        if cand and os.path.isfile(cand):
            exe = cand
    return exe


@unittest.skipUnless(PLAYWRIGHT, "playwright not installed")
@unittest.skipUnless(MEDIA_TOOLS, "needs ffmpeg/dvdauthor/ISO tool")
class TestGuiBrowser(unittest.TestCase):
    """Drive the real page: new project, upload, add title, chapters, menu
    drag & undo, exact preview, build."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="oncemore-gui-ui-")
        self.s = GuiServer(self.dir)
        self.clip = os.path.join(self.dir, "..", os.path.basename(self.dir) + "-clip.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc2=s=640x360:r=25:d=6", "-f", "lavfi", "-i", "sine=d=6",
                        "-c:v", "mpeg4", "-c:a", "aac", "-shortest", self.clip], check=True)

    def tearDown(self):
        self.s.close()
        shutil.rmtree(self.dir, ignore_errors=True)
        if os.path.exists(self.clip):
            os.remove(self.clip)

    def project(self):
        with open(os.path.join(self.dir, "project.oncemore.json"), encoding="utf-8") as f:
            return json.load(f)

    def poll(self, fn, timeout=30):
        """Wait until fn() is truthy (reading the saved project file)."""
        end = time.time() + timeout
        while True:
            try:
                v = fn()
            except (StopIteration, KeyError, IndexError, ValueError):
                v = None
            if v or time.time() > end:
                self.assertTrue(v, "condition not met in time")
                return v
            time.sleep(0.2)

    def wait_saved(self, page):
        # (the page's CSP forbids eval, so no wait_for_function)
        page.locator("#save-state", has_text=re.compile("^(Saved|保存済み)$")).wait_for()

    def launch(self, p):
        try:
            return p.chromium.launch()
        except Exception:
            exe = _chromium()
            if not exe:
                self.skipTest("no Chromium for Playwright")
            return p.chromium.launch(executable_path=exe)

    def test_menu_bar_context_menus_and_shortcuts(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda d: d.accept())
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.locator(".nav-item[data-view=title][data-id=t2]").wait_for(timeout=120000)
            self.assertEqual(page.locator("#menubar > button").all_inner_texts(),
                             ["File", "Edit", "Object", "Menu", "Timeline", "View", "Window",
                              "Help"])
            # Disc > New playlist
            page.click("#menubar > button:has-text('Timeline')")
            page.click(".popup button:has-text('New playlist')")
            self.wait_saved(page)
            self.assertEqual(len(self.project().get("playlists", [])), 1)
            self.assertEqual(page.locator(".popup").count(), 0)
            # Edit > Undo takes it back
            page.click("#menubar > button:has-text('Edit')")
            page.click(".popup button:has-text('Undo')")
            self.poll(lambda: not self.project().get("playlists"))
            # right-click a title: duplicate, play first, delete
            page.click(".nav-item[data-view=title][data-id=t2]", button="right")
            page.click(".popup button:has-text('Duplicate')")
            self.poll(lambda: [x["id"] for x in self.project()["titles"]] == ["t1", "t2", "t2_copy1"])
            self.assertEqual(self.project()["titles"][2]["name"], "Sample Title B copy")
            page.click(".nav-item[data-view=title][data-id=t2_copy1]", button="right")
            page.click(".popup button:has-text('Play first')")
            self.poll(lambda: self.project()["disc"]["first_play"] == "title:t2_copy1")
            page.click(".nav-item[data-view=title][data-id=t2_copy1]", button="right")
            page.click(".popup button.danger:has-text('Delete')")
            self.poll(lambda: len(self.project()["titles"]) == 2)
            # nothing points at the deleted title any more
            self.assertNotIn("first_play", self.project()["disc"])
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.click(".nav-item[data-view=title][data-id=t1]", button="right")
            self.assertTrue(page.locator(".popup button:has-text('Move up')").is_disabled())
            page.keyboard.press("Escape")
            self.assertEqual(page.locator(".popup").count(), 0)
            # workspaces from the keyboard
            page.keyboard.press("Alt+Shift+2")
            page.locator("#center-head", has_text="Flowchart").wait_for()
            page.keyboard.press("Alt+Shift+1")
            page.locator("#inspector #rom-files").wait_for()           # the disc's properties
            # a chapter at the playhead with * (Shift+8)
            page.click(".nav-item[data-view=title][data-id=t2]")
            page.fill("#tc-input", "00:00:03.000")
            page.press("#tc-input", "Enter")
            page.locator("#tc-input").blur()
            page.keyboard.press("*")
            self.poll(lambda: len(self.project()["titles"][1]["chapters"]) == 2)
            # menu stage: right-click a button, duplicate it
            page.click(".nav-item[data-view=menu][data-id=main]")
            n = len(self.project()["menus"][0]["buttons"])
            page.click(".stage .el.button >> nth=0", button="right")
            page.click(".popup button:has-text('Duplicate')")
            self.poll(lambda: len(self.project()["menus"][0]["buttons"]) == n + 1)
            # the list of shortcuts
            page.keyboard.press("Shift+?")
            page.locator("#modal table.shortcuts", has_text="Add chapter at playhead").wait_for()
            browser.close()
        self.assertEqual(errors, [])

    def test_routing_and_drag_to_link(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            # the remote's routing: three buttons in a column, up / down between them
            page.check("#routing")
            page.locator(".stage svg.routing path[data-route]").first.wait_for(timeout=60000)
            n = page.locator(".stage svg.routing path[data-route]").count()
            self.assertGreaterEqual(n, 4)
            self.assertEqual(page.locator(".stage svg.routing path[data-route='play:down']").count(), 1)
            self.assertEqual(page.locator(".stage svg.routing path.manual").count(), 0)
            # a route set by hand is drawn solid
            last_id = self.project()["menus"][0]["buttons"][-1]["id"]
            page.click(".stage .el.button >> nth=0")
            page.select_option("#inspector select[data-k='nav.up']", last_id)
            self.wait_saved(page)
            page.locator(".stage svg.routing path.manual[data-route='play:up']").wait_for(timeout=60000)
            # drag a title onto the last button: it now plays that title
            last = page.locator(".stage .el.button").last
            page.locator(".nav-item[data-view=title][data-id=t1]").drag_to(last)
            self.poll(lambda: self.project()["menus"][0]["buttons"][-1]["action"] == "title:t1")
            # drag a menu onto an empty part of the menu: a new button for it
            n_buttons = len(self.project()["menus"][0]["buttons"])
            stage_w = page.locator("#stage").bounding_box()["width"]
            page.locator(".nav-item[data-view=menu][data-id=chapters]").drag_to(
                page.locator("#stage"), target_position={"x": stage_w - 40, "y": 30})
            self.poll(lambda: len(self.project()["menus"][0]["buttons"]) == n_buttons + 1)
            b = self.project()["menus"][0]["buttons"][-1]
            self.assertEqual((b["action"], b["label"]), ("menu:chapters", "CHAPTERS"))
            self.assertTrue(self.s.app.check(self.project())["valid"])
            browser.close()
        self.assertEqual(errors, [])

    def test_menu_pictures(self):
        """A picture placed on a menu: natural proportions, centred, resized
        with its proportions, listed in Layers, drawn in the exact preview."""
        self.s.call("/api/new", "POST", {"sample": True})
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                        "color=c=0x00FF00:s=160x80", "-frames:v", "1",
                        os.path.join(self.dir, "media", "logo.png")], check=True)
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            page.click("#add-picture")
            page.click("[data-pic='media/logo.png']")
            pic = self.poll(lambda: (self.project()["menus"][0].get("images") or [None])[0])
            # 160 x 80 square pixels on a 16:9 NTSC disc: 135 x 80 DVD pixels, centred
            self.assertEqual(pic, {"file": "media/logo.png", "x": 293, "y": 200, "w": 135, "h": 80})
            page.locator(".stage .el.image.selected img").wait_for()
            page.fill("#pic-w", "270")
            page.press("#pic-w", "Enter")
            self.poll(lambda: self.project()["menus"][0]["images"][0]["w"] == 270)
            self.assertEqual(self.project()["menus"][0]["images"][0]["h"], 160)
            page.locator("#layers .layer-row[data-lk=image]").wait_for()
            # drag it: moves like any element
            box = page.locator(".stage .el.image").bounding_box()
            page.mouse.move(box["x"] + 20, box["y"] + 20)
            page.mouse.down()
            page.mouse.move(box["x"] + 60, box["y"] + 20, steps=4)
            page.mouse.up()
            self.poll(lambda: self.project()["menus"][0]["images"][0]["x"] > 300)
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # Properties of the menu: buttons that wait for the loop point
            page.keyboard.press("Escape")
            page.evaluate("S.element = null; S.sels = []; renderInspector()")
            self.assertEqual(page.locator("#btn-at-loop").count(), 0)   # (no loop point yet)
            page.fill("#inspector [data-k=loop_point]", "2")
            page.press("#inspector [data-k=loop_point]", "Enter")
            page.check("#btn-at-loop")
            self.poll(lambda: self.project()["menus"][0].get("buttons_at_loop") is True)
            self.assertEqual(self.project()["menus"][0]["loop_point"], 2)
            browser.close()
        self.assertEqual(errors, [])
        status, pv = self.s.call("/api/preview", "POST", {"menu": "main"})
        self.assertEqual(status, 200, pv)

    def test_transcode_now_and_waveforms(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            # not transcoded yet: hollow marks in the project panel
            page.locator(".nav-item[data-id=t1] .enc:not(.ok)").wait_for(timeout=120000)
            page.click(".nav-item[data-view=title][data-id=t2]", button="right")
            page.click(".popup button:has-text('Transcode this title now')")
            page.locator(".nav-item[data-id=t2] .enc.ok").wait_for(timeout=300000)
            self.assertEqual(page.locator(".nav-item[data-id=t1] .enc.ok").count(), 0)
            # the timeline draws the title's sound
            page.click(".nav-item[data-view=title][data-id=t2]")
            wave = page.locator("#tl .tl-wave").first
            wave.wait_for(timeout=60000)
            self.assertIn("/api/waveform?", wave.get_attribute("src"))
            browser.close()
        self.assertEqual(errors, [])

    def test_authoring_tools_like_a_disc_authoring_app(self):
        """Tools strip, viewer bar, pick whip, flowchart links and preview keys."""
        def whip(page, handle, target):
            a, b = page.locator(handle).bounding_box(), page.locator(target).bounding_box()
            page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
            page.mouse.down()
            for k in range(1, 11):
                page.mouse.move(a["x"] + (b["x"] + b["width"] / 2 - a["x"]) * k / 10,
                                a["y"] + (b["y"] + b["height"] / 2 - a["y"]) * k / 10)
            page.mouse.up()

        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1800, "height": 1000}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            # Text tool (T): click where the text goes
            n_texts = len(self.project()["menus"][0].get("texts", []))
            page.locator("#stage").focus()
            page.keyboard.press("t")
            page.locator(".tools [data-tool=text].on").wait_for()
            box = page.locator("#stage").bounding_box()
            page.mouse.click(box["x"] + box["width"] * 0.8, box["y"] + box["height"] * 0.9)
            self.poll(lambda: len(self.project()["menus"][0]["texts"]) == n_texts + 1)
            txt = self.project()["menus"][0]["texts"][-1]
            self.assertGreater(txt["x"], 500)
            page.locator(".tools [data-tool=select].on").wait_for()
            # Zoom tool and keys
            page.keyboard.press("Escape")
            page.locator("#stage").focus()
            page.keyboard.press("z")
            page.locator(".tools [data-tool=zoom].on").wait_for()
            page.mouse.click(box["x"] + 20, box["y"] + 20)
            self.assertNotEqual(page.input_value("#zoom"), "fit")
            page.select_option("#zoom", "fit")
            page.keyboard.press("v")
            # every button in its "selected" state: the exact picture
            page.click("[data-sp=highlight]")
            page.locator(".stage img.exact").wait_for(timeout=120000)
            page.click("[data-sp=highlight]")
            page.locator(".stage img.exact").wait_for(state="detached")
            # overlapping buttons are outlined in red
            buttons = self.project()["menus"][0]["buttons"]
            page.click(".stage .el.button >> nth=1")
            page.fill("#inspector input[data-k=y]", str(buttons[0]["y"]))
            page.press("#inspector input[data-k=y]", "Enter")
            page.locator(".stage .overlap").first.wait_for(timeout=120000)
            self.assertEqual(page.locator(".stage .overlap").count(), 2)
            page.keyboard.press("Meta+z" if sys.platform == "darwin" else "Control+z")
            page.locator(".stage .overlap").first.wait_for(state="detached", timeout=60000)
            # the pick whip: from the button's link to a title in the project panel
            page.click(".stage .el.button >> nth=0")
            whip(page, "#inspector [data-whip=action]", ".nav-item[data-view=title][data-id=t2]")
            self.poll(lambda: self.project()["menus"][0]["buttons"][0]["action"] == "title:t2")
            # Cmd/Ctrl+L goes to the link
            page.locator("#stage").focus()
            page.keyboard.press("Meta+l" if sys.platform == "darwin" else "Control+l")
            page.locator("#inspector select[data-k=action]:focus").wait_for()
            # flowchart: drag from first play to a title; a new playlist is unused
            page.click("#menubar > button:has-text('Timeline')")
            page.click(".popup button:has-text('New playlist')")
            page.click("#menubar > button:has-text('Window')")
            page.click(".popup button:has-text('Flowchart')")
            page.locator("#flow g.node[data-node='title:t1']").wait_for(timeout=60000)
            page.locator("#flow g.node.unused[data-node^='playlist:']").wait_for()
            whip(page, "#flow g.node[data-node=fp]", "#flow g.node[data-node='title:t1']")
            self.poll(lambda: self.project()["disc"]["first_play"] == "title:t1")
            # Preview (Shift+Space) from a menu; number keys press its buttons
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator("#stage").focus()
            page.keyboard.press("Shift+Space")
            page.locator("#sim-status", has_text="main").wait_for(timeout=120000)
            page.locator("#sim-screen").focus()
            page.keyboard.press("1")
            page.locator("#sim-status", has_text="t2").wait_for(timeout=60000)
            browser.close()
        self.assertEqual(errors, [])

    def test_native_menus_in_the_mac_app(self):
        # Oncemore.app's menu bar is the page's: the page hides its own and
        # posts its menus (language, what can be done now) to the app, which
        # makes the native ones from them; their items call window.oncemoreCommand
        with sync_playwright() as p:
            browser = self.launch(p)
            ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="en-US",
                                      bypass_csp=True,
                                      user_agent="Mozilla/5.0 (Macintosh) AppleWebKit OncemoreApp")
            # what WKWebView gives the page for the app's message handlers
            ctx.add_init_script("""window.webkit = {messageHandlers: {
                oncemoreMenu: {postMessage: (s) => { window.__specs = (window.__specs || 0) + 1; window.__spec = s; }},
                oncemoreProject: {postMessage: (p) => { window.__project = p; }}}};""")
            page = ctx.new_page()
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.locator(".nav-item[data-view=title]").first.wait_for(timeout=120000)
            self.assertTrue(page.locator("#menubar").is_hidden())
            spec = lambda: json.loads(page.evaluate("window.__spec") or "[]")  # noqa: E731
            self.poll(lambda: [m["title"] for m in spec()] == ["File", "Edit", "Object", "Menu", "Timeline", "View",
                                                                "Window", "Help"])
            flat = lambda items: [y for x in items if x != "-" for y in ([x] + flat(x.get("sub", [])))]  # noqa: E731
            items = {x["id"]: x for m in spec() for x in flat(m["items"]) if x.get("id")}
            # the app's own items are there (only in the app), with their keys
            self.assertEqual(items["close_window"]["key"], "mod+w")
            self.assertEqual(items["full_screen"]["key"], "mod+ctrl+f")
            self.assertEqual(items["undo"]["key"], "mod+z")
            self.assertEqual([m["role"] for m in spec()][:2] + [spec()[6]["role"], spec()[7]["role"]], ["file", "edit", "window", "help"])
            # what cannot be done now is greyed; what is on is ticked
            self.assertTrue(items["align_left"]["disabled"])
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.click(".stage .el.button >> nth=0")
            now = lambda: {x["id"]: x for m in spec() for x in flat(m["items"]) if x.get("id")}  # noqa: E731
            self.poll(lambda: not now()["bring_front"]["disabled"])
            self.assertTrue(now()["safe_area"]["checked"])
            # and in Japanese when the page is
            page.evaluate("window.oncemoreCommand('language')")
            self.poll(lambda: spec()[0]["title"] == "ファイル")
            page.evaluate("window.oncemoreCommand('language')")
            page.evaluate("window.oncemoreCommand('ws_flow')")
            page.locator("#center-head", has_text="Flowchart").wait_for()
            page.evaluate("window.oncemoreCommand('new_slideshow')")
            self.wait_saved(page)
            self.assertTrue(any("slideshow" in t for t in self.project()["titles"]))
            browser.close()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "macos", "Oncemore", "main.swift"), encoding="utf-8") as f:
            swift = f.read()
        with open(os.path.join(root, "oncemore", "gui", "static", "app.js"), encoding="utf-8") as f:
            js = f.read()
        natives = re.findall(r'^ +"(\w+)": Native\(', swift, re.M)
        app_only = re.findall(r"^ +(\w+): \{ app: true", js, re.M)
        self.assertEqual(sorted(app_only), ["close_window", "full_screen", "minimize", "reload", "zoom_window"])
        for cid in natives:
            self.assertRegex(js, rf"[\n ] *{cid}: [{{a]", cid)    # every item the app does itself is a page command
        self.assertTrue(set(app_only) <= set(natives))
        self.assertIn('add(self, name: "oncemoreMenu")', swift)
        self.assertIn('applicationNameForUserAgent = "OncemoreApp"', swift)

    def test_every_menu_and_submenu(self):
        """The menu bar in disc authoring order, every submenu opens, every
        item has a label (English and Japanese), every command is reachable."""
        self.s.call("/api/new", "POST", {"sample": True})
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.locator(".stage .el.button").first.wait_for(timeout=120000)
            with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "oncemore", "gui", "static", "app.js"), encoding="utf-8") as f:
                js = f.read()
            commands = set(re.findall(r"^  (\w+): [{a-zA-Z]", js[js.index("const COMMANDS = {"):js.index("// The menu bar, in the order")], re.M))
            flat = lambda items: [y for x in items if x != "-" for y in ([x] + flat(x.get("sub", [])))]  # noqa: E731
            for lang, titles in (("en", ["File", "Edit", "Object", "Menu", "Timeline", "View", "Window", "Help"]),
                                 ("ja", ["ファイル", "編集", "オブジェクト", "メニュー", "タイムライン", "表示", "ウィンドウ", "ヘルプ"])):
                spec = json.loads(page.evaluate("JSON.stringify(window.oncemoreMenuSpec())"))
                self.assertEqual([m["title"] for m in spec], titles, lang)
                labels = [x["label"] for m in spec for x in flat(m["items"])]
                self.assertFalse([x for x in labels if not x or re.match(r"^(cmd|m)_", x)], lang)
                ids = {x["id"] for m in spec for x in flat(m["items"]) if x.get("id")}
                # every command is in the menu bar (except the shortcut-only Convert)
                self.assertEqual(sorted(commands - ids - {"convert"} - {f"recent_{i}" for i in range(1, 11)}
                                        - {"close_window", "reload", "full_screen", "minimize", "zoom_window"}), [], lang)
                self.assertEqual(page.locator("#menubar > button").all_inner_texts(), titles)
                if lang == "en":
                    page.evaluate("window.oncemoreCommand('language')")
            page.evaluate("window.oncemoreCommand('language')")
            # open every menu and every submenu
            for k in range(8):
                page.click(f"#menubar [data-mb='{k}']")
                pop = page.locator(".popup.from-bar")
                pop.wait_for()
                subs = pop.locator("button.has-sub:not([disabled])")
                for j in range(subs.count()):
                    subs.nth(j).hover()
                    page.locator(".popup.sub button").first.wait_for()
                    self.assertGreater(page.locator(".popup.sub button").count(), 0)
                page.keyboard.press("Escape")
            self.assertEqual(page.locator(".popup").count(), 0)
            # a submenu item runs: File > Build > Blu-ray folder… opens Build set up for it
            page.click("#menubar > button:has-text('File')")
            page.hover(".popup.from-bar button:has-text('Build')")
            page.click(".popup.sub button:has-text('Blu-ray folder')")
            page.locator("#sidebar #bformat").wait_for()
            self.assertEqual(page.input_value("#sidebar #bformat"), "bluray")
            self.assertTrue(page.is_checked("#sidebar input[name=kind][value=folder]"))
            # ... and Web (HTML5)…: a folder only (no image or disc to choose)
            page.click("#menubar > button:has-text('File')")
            page.hover(".popup.from-bar button:has-text('Build')")
            page.click(".popup.sub button:has-text('Web (HTML5)')")
            page.wait_for_function("document.querySelector('#sidebar #bformat')?.value === 'web'")
            self.assertEqual(page.locator("#sidebar input[name=kind]").count(), 0)
            # ticks for what is on
            page.evaluate("window.oncemoreCommand('win_project')")
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.click("#menubar > button:has-text('View')")
            self.assertEqual(page.get_attribute(".popup button:has-text('Show safe area')", "aria-checked"), "true")
            page.click(".popup button:has-text('Show safe area')")
            page.click("#menubar > button:has-text('View')")
            self.assertEqual(page.get_attribute(".popup button:has-text('Show safe area')", "aria-checked"), "false")
            page.keyboard.press("Escape")
            browser.close()
        self.assertEqual(errors, [])

    def test_sponsor_link(self):
        """Help > Support oncemore and the About box open the project's
        GitHub Sponsors page."""
        self.s.call("/api/new", "POST", {"sample": True})
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            # (a value, not the function: evaluate would call a function it gets back)
            page.evaluate("window.__opened = []; window.open = (u) => { window.__opened.push(u); }; 0")
            page.click("#menubar > button:has-text('Help')")
            page.click(".popup.from-bar button:has-text('Support oncemore (GitHub Sponsors)')")
            page.evaluate("window.oncemoreCommand('about')")
            page.click("#about-sponsor")
            self.assertEqual(page.evaluate("window.__opened"),
                             ["https://github.com/sponsors/kajisho5"] * 2)
            browser.close()
        self.assertEqual(errors, [])

    def test_menu_bar_commands(self):
        """Edit, Object, Menu, Timeline and View commands on the sample disc."""
        self.s.call("/api/new", "POST", {"sample": True})
        with open(os.path.join(self.dir, "media", "dialogue.srt"), "w", encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nHello\n")
        os.makedirs(os.path.join(self.dir, "extras"))
        mod = "Meta" if sys.platform == "darwin" else "Control"
        menu = lambda: self.project()["menus"][0]  # noqa: E731
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda d: d.accept())
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.locator(".stage .el.button").first.wait_for(timeout=120000)
            cmd = lambda c: page.evaluate(f"window.oncemoreCommand('{c}')")  # noqa: E731
            # Edit > Select all / Deselect all
            page.locator("#stage").focus()
            page.keyboard.press(f"{mod}+a")
            self.assertEqual(page.locator(".stage .el.selected").count(), 4)
            page.keyboard.press(f"{mod}+Shift+a")
            self.assertEqual(page.locator(".stage .el.selected").count(), 0)
            # Object > Align: one object alone goes to the safe area
            page.click(".stage .el.text")
            page.click("#menubar > button:has-text('Object')")
            page.hover(".popup.from-bar button:has-text('Align')")
            page.click(".popup.sub button:has-text('Align left edges')")
            self.poll(lambda: menu()["texts"][0]["x"] == 36)
            # Object > Arrange: one step back and forward, within the buttons
            page.click(".stage .el.button[data-i='2']")
            page.locator("#stage").focus()
            page.keyboard.press(f"{mod}+BracketLeft")
            self.poll(lambda: [b["id"] for b in menu()["buttons"]] == ["play", "b", "ch"])
            page.keyboard.press(f"{mod}+BracketRight")
            self.poll(lambda: [b["id"] for b in menu()["buttons"]] == ["play", "ch", "b"])
            # Menu > Set as default button
            cmd("default_button")
            self.poll(lambda: menu().get("default_button") == "b")
            # Object > Drop shadow and stroke
            page.click(".stage .el.text")
            cmd("drop_shadow")
            page.check("#ds-shadow-on")
            page.fill("#ds-shadow_offset", "5")
            page.click("#ds-ok")
            self.poll(lambda: menu()["texts"][0].get("shadow") == "#000000" and menu()["texts"][0]["shadow_offset"] == 5)
            # Convert: a text to a button, not the other way round here
            page.click("#menubar > button:has-text('Object')")
            self.assertFalse(page.locator(".popup button:has-text('Convert to button')").is_disabled())
            self.assertTrue(page.locator(".popup button:has-text('Convert to object')").is_disabled())
            page.keyboard.press("Escape")
            # Edit > Copy, Paste, Cut: objects of the menu
            page.click(".stage .el.button[data-i='0']")
            page.locator("#stage").focus()
            page.keyboard.press(f"{mod}+c")
            page.keyboard.press(f"{mod}+v")
            self.poll(lambda: len(menu()["buttons"]) == 4)
            page.locator("#stage").focus()
            page.keyboard.press(f"{mod}+x")
            self.poll(lambda: len(menu()["buttons"]) == 3)
            # … and titles in the project
            page.click(".nav-item[data-view=title][data-id=t2]")
            page.locator("#tc-input").wait_for(timeout=60000)
            page.locator("#tc-input").blur()
            cmd("copy")
            cmd("paste")
            self.poll(lambda: [x["id"] for x in self.project()["titles"]] == ["t1", "t2", "t2_copy1"])
            # Edit > Rename: what points at the title follows
            page.click(".nav-item[data-view=title][data-id=t2]")
            cmd("rename")
            page.fill("#rn-name", "Second")
            page.fill("#rn-id", "t9")
            page.click("#rn-ok")
            self.poll(lambda: self.project()["titles"][1]["id"] == "t9")
            self.assertEqual(self.project()["titles"][1]["name"], "Second")
            self.assertEqual(menu()["buttons"][2]["action"], "title:t9")
            # Timeline > New chapter playlist
            cmd("chapter_playlist")
            page.select_option("#cp-title", "t1")
            page.click("#cp-ok")
            n = len(self.project()["titles"][0]["chapters"])
            self.poll(lambda: self.project()["playlists"][0]["items"] == [f"t1:{i}" for i in range(1, n + 1)])
            # Timeline > Add subtitle track / audio track, Export subtitles
            page.click(".nav-item[data-view=title][data-id=t1]")
            page.locator("#tc-input").wait_for(timeout=60000)
            cmd("add_subtitle_track")
            page.select_option("#st-lang", "en")
            page.click("#st-ok")
            self.poll(lambda: self.project()["titles"][0].get("subtitles") == [{"file": "media/dialogue.srt", "lang": "en"}])
            cmd("export_subtitles")
            page.locator(".modal .mono, #modal .mono", has_text="exports/dialogue.srt").wait_for(timeout=30000)
            self.assertTrue(os.path.isfile(os.path.join(self.dir, "exports", "dialogue.srt")))
            page.keyboard.press("Escape")
            cmd("add_audio_track")
            page.fill("#at-stream", "1")
            page.select_option("#at-lang", "ja")
            page.click("#at-ok")
            self.poll(lambda: self.project()["titles"][0].get("audio_tracks") == [{}, {"stream": 1, "lang": "ja"}])
            # Timeline > Set poster frame at the playhead; Save frame as file
            page.fill("#tc-input", "00:00:03.000")
            page.press("#tc-input", "Enter")
            page.locator("#tc-input").blur()
            cmd("set_poster")
            self.poll(lambda: any(isinstance(c, dict) and str(c.get("poster", "")).startswith("00:00:03")
                                  for c in self.project()["titles"][0]["chapters"]))
            cmd("save_frame")
            page.locator("#modal .mono", has_text="exports/sample_a-00-00-03").wait_for(timeout=60000)
            page.keyboard.press("Escape")
            self.assertTrue([f for f in os.listdir(os.path.join(self.dir, "exports")) if f.endswith(".png")])
            # File > Interpret footage / Transcode settings
            cmd("interpret_footage")
            page.select_option("#modal-body select[data-k=aspect]", "4:3")
            page.click("#tf-ok")
            self.poll(lambda: self.project()["titles"][0].get("aspect") == "4:3")
            cmd("transcode_settings")
            page.select_option("#modal-body select[data-k=video_bitrate]", "5M")
            page.click("#tf-ok")
            self.poll(lambda: self.project()["titles"][0].get("video_bitrate") == "5M")
            # Timeline > Clear all chapter points
            cmd("clear_chapters")
            self.poll(lambda: len(self.project()["titles"][0]["chapters"]) == 1)
            self.assertEqual(set(self.project()["playlists"][0]["items"]), {"t1"})       # (the whole title now)
            # File > DVD-ROM content
            cmd("rom_folder")
            page.check("[data-rom='extras/']")
            page.click("#rom-ok")
            self.poll(lambda: self.project()["disc"].get("rom_files") == ["extras/"])
            # Menu > Save menu as file; Edit menu colour set
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator(".stage .el.button").first.wait_for()
            cmd("save_menu_file")
            page.locator("#modal .mono", has_text="exports/main.png").wait_for(timeout=120000)
            page.keyboard.press("Escape")
            cmd("colour_set")
            page.locator("#modal [data-cs-a=highlight_color]").fill("50")
            page.locator("#modal [data-cs-a=highlight_color]").dispatch_event("change")
            self.poll(lambda: menu()["highlight_color"] == "#FFD40080")
            page.click("#cs-ok")
            # View > Snap; Show highlights > Normal
            cmd("snap")
            self.assertFalse(page.is_checked("#snap"))
            cmd("view_normal")
            page.locator("[data-sp=normal].on").wait_for()
            # File > Save
            page.keyboard.press(f"{mod}+s")
            self.wait_saved(page)
            # Menu > Add button / text / rectangle
            n = len(menu()["buttons"])
            cmd("add_button")
            self.poll(lambda: len(menu()["buttons"]) == n + 1)
            cmd("add_rectangle")
            self.poll(lambda: len(menu().get("shapes", [])) == 1)
            cmd("add_text")
            self.poll(lambda: len(menu()["texts"]) == 2)
            # File > Import as > Timeline / Slideshow: choose the files, then they are used
            page.locator("#stage").focus()
            for item, path in (("Timeline…", self.clip), ("Slideshow…", os.path.join(self.dir, "media", "menu_bg.png"))):
                page.click("#menubar > button:has-text('File')")
                page.hover(".popup.from-bar button:has-text('Import as')")
                with page.expect_file_chooser() as fc:
                    page.click(f".popup.sub button:has-text('{item}')")
                fc.value.set_files(path)
            self.poll(lambda: len(self.project()["titles"]) == 5)
            self.assertTrue(self.project()["titles"][3]["source"].endswith("-clip.mp4"))
            self.assertTrue(self.project()["titles"][4]["slideshow"]["slides"][0]["image"].startswith("media/menu_bg"))
            # Help opens the guide (README) outside the app
            page.evaluate("window.open = (u) => { window.__opened = u; }")
            cmd("help")
            self.assertIn("/README.md", page.evaluate("window.__opened"))
            browser.close()
        self.assertEqual(errors, [])
        self.assertTrue(self.s.app.check(self.project())["valid"])

    def test_projects_from_the_file_menu(self):
        """File > Save as, Open recent, Open project and New project with the
        page's folder chooser."""
        cfg, other = tempfile.mkdtemp(prefix="oncemore-cfg-"), os.path.realpath(tempfile.mkdtemp(prefix="oncemore-other-"))
        self.addCleanup(shutil.rmtree, cfg, True)
        self.addCleanup(shutil.rmtree, other, True)
        self.s.call("/api/new", "POST", {"sample": True})
        with mock.patch.dict(os.environ, {"ONCEMORE_CONFIG": cfg}), sync_playwright() as p:
            self.s.call("/api/switch", "POST", {"path": self.dir})       # (what `oncemore gui` notes first)
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.locator(".stage .el.button").first.wait_for(timeout=120000)
            cmd = lambda c: page.evaluate(f"window.oncemoreCommand('{c}')")  # noqa: E731
            # Save as: a new folder in another place, which is then the project
            cmd("save_as")
            page.fill("#fb-path", other)
            page.locator("#fb-path").dispatch_event("change")
            page.locator("#fb-list", has_text="No folders").wait_for()
            page.fill("#fb-name", "Copy")
            page.click("#fb-ok")
            self.poll(lambda: self.s.app.dir == os.path.join(other, "Copy"))
            page.locator("#modal").wait_for(state="hidden")
            page.locator(".stage .el.button").first.wait_for()
            self.assertTrue(os.path.isfile(os.path.join(other, "Copy", "media", "sample_a.mp4")))
            # Open recent: the first project again
            page.click("#menubar > button:has-text('File')")
            page.hover(".popup.from-bar button:has-text('Open recent project')")
            self.assertTrue(page.locator(".popup.sub button:has-text('Copy')").is_disabled())   # (open now)
            page.click(f".popup.sub button:has-text('{os.path.basename(self.dir)}')")
            self.poll(lambda: self.s.app.dir == os.path.realpath(self.dir))
            # Open project: the chooser marks project folders; double-click opens
            cmd("open_project")
            page.fill("#fb-path", other)
            page.locator("#fb-path").dispatch_event("change")
            page.locator(".fb-item.is-project", has_text="Copy").dblclick()
            self.poll(lambda: self.s.app.dir == os.path.join(other, "Copy"))
            page.locator("#modal").wait_for(state="hidden")
            # New project: a new folder, then the New Project dialog for it
            cmd("new_project")
            page.fill("#fb-path", other)
            page.locator("#fb-path").dispatch_event("change")
            page.fill("#fb-name", "Fresh")
            page.click("#fb-ok")
            page.locator("#np-empty").wait_for()
            page.click("#np-empty")
            self.poll(lambda: os.path.isfile(os.path.join(other, "Fresh", "project.oncemore.json")))
            browser.close()
        self.assertEqual(errors, [])

    def test_job_picked_up_again(self):
        """A page opened while a transcode runs shows it, and its end."""
        self.s.call("/api/new", "POST", {"label": "again", "sample": True})
        go = threading.Event()

        def work(project, rep):
            rep.step("encode", "encoding", item="t1")
            go.wait(30)
            return {"titles": {}}
        job = self.s.app.start_job("transcode", work)
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.locator("#st-transcode", has_text="t1").wait_for(timeout=30000)
            go.set()
            job.thread.join(10)
            page.locator("#st-transcode").wait_for(state="detached", timeout=30000)
            self.assertEqual(errors, [])
            browser.close()

    def test_rotate_flip_and_guides(self):
        """Object > Rotate / Flip, Properties' rotation, the Rotate tool, and
        guides placed, snapped to, moved, locked, dragged off and cleared."""
        self.s.call("/api/new", "POST", {"sample": True})
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda d: d.accept())
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            cmd = lambda c: page.evaluate(f"window.oncemoreCommand('{c}')")  # noqa: E731
            btn = lambda: self.project()["menus"][0]["buttons"][0]          # noqa: E731
            page.click(".stage .el.button[data-i='0']")
            cmd("rotate_cw")
            self.poll(lambda: btn().get("rotate") == 90)
            cmd("rotate_cw")
            cmd("rotate_180")
            self.poll(lambda: "rotate" not in btn())                # a whole turn: none
            cmd("rotate_ccw")
            self.poll(lambda: btn().get("rotate") == 270)
            cmd("flip_h")                                           # on the screen's axis
            self.poll(lambda: (btn().get("rotate"), btn().get("flip")) == (90, "horizontal"))
            cmd("flip_v")
            self.poll(lambda: (btn().get("rotate"), btn().get("flip")) == (270, "both"))
            style = page.locator(".stage .el.button[data-i='0']").get_attribute("style")
            self.assertIn("rotate(270deg) scale(-1,-1)", style)
            # Properties: the angle and the flip
            page.fill("#tf-rot", "15")
            page.press("#tf-rot", "Tab")
            page.select_option("#tf-flip", "__none__")
            self.poll(lambda: btn().get("rotate") == 15 and "flip" not in btn())
            # the Rotate tool: a quarter turn by dragging (Shift: 45° steps)
            cmd("tool_rotate")
            node = page.locator(".stage .el.button[data-i='0']")
            box = node.bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            page.mouse.move(box["x"] + box["width"] - 4, cy)
            page.mouse.down()
            page.keyboard.down("Shift")
            page.mouse.move(cx + 2, cy + 120, steps=8)
            page.mouse.up()
            page.keyboard.up("Shift")
            self.poll(lambda: btn().get("rotate") == 90)
            cmd("tool_select")
            # the menu, with them, is a valid project
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # guides: New Guide…
            cmd("new_guide")
            page.check("input[name=gdir][value=vertical]")
            page.fill("#g-pos", "300")
            page.click("#m-ok")
            guides = lambda: self.project()["menus"][0].get("guides")     # noqa: E731
            self.poll(lambda: guides() == {"vertical": [300]})
            page.locator(".stage .uguide.v").wait_for()
            # a text dragged near it snaps to it (Snap to objects off: only guides)
            cmd("snap")
            stage = page.locator("#stage").bounding_box()
            k = stage["width"] / 720                                 # screen px per menu px
            text = page.locator(".stage .el.text[data-i='0']")
            tb = text.bounding_box()
            x0 = self.project()["menus"][0]["texts"][0]["x"]
            page.mouse.move(tb["x"] + 10, tb["y"] + 10)
            page.mouse.down()
            page.mouse.move(tb["x"] + 10 + (297 - x0) * k, tb["y"] + 10, steps=6)
            page.mouse.up()
            self.poll(lambda: self.project()["menus"][0]["texts"][0]["x"] == 300)
            cmd("snap")
            # moved by dragging
            g = page.locator(".stage .uguide.v").bounding_box()
            page.mouse.move(g["x"] + 1, g["y"] + 40)
            page.mouse.down()
            page.mouse.move(g["x"] + 1 + 100 * k, g["y"] + 40, steps=5)
            page.mouse.up()
            self.poll(lambda: guides() and abs(guides()["vertical"][0] - 400) <= 1)
            # locked: it cannot be grabbed
            cmd("lock_guides")
            self.assertIn("locked", page.locator(".stage .uguide.v").get_attribute("class"))
            cmd("lock_guides")
            # dragged off the menu: gone
            g = page.locator(".stage .uguide.v").bounding_box()
            page.mouse.move(g["x"] + 1, g["y"] + 40)
            page.mouse.down()
            page.mouse.move(stage["x"] - 60, g["y"] + 40, steps=5)
            page.mouse.up()
            self.poll(lambda: guides() is None)
            # Clear Guides
            cmd("new_guide")
            page.click("#m-ok")
            self.poll(lambda: guides() and len(guides().get("horizontal", [])) == 1)
            cmd("show_guides")
            self.assertEqual(page.locator(".stage .uguide").count(), 0)
            cmd("show_guides")
            cmd("clear_guides")
            self.poll(lambda: guides() is None)
            # the View and Object menus have them
            page.click("#menubar > button:has-text('View')")
            for label in ("Show guides", "Lock guides", "Clear guides", "New guide…", "Snap to guides"):
                self.assertTrue(page.locator(f".popup :text-is('{label}')").count(), label)
            page.keyboard.press("Escape")
            browser.close()
        self.assertEqual(errors, [])

    def test_text_script_subtitles_and_chapter_names(self):
        """Timeline > Import subtitles with a text script timed against
        01;00;00;00, its cues on the timeline, Export subtitles as a text
        script, and View > Show chapter names in the time ruler."""
        self.s.call("/api/new", "POST", {"sample": True})
        with open(os.path.join(self.dir, "media", "fr.txt"), "w", encoding="utf-8") as f:
            f.write("1 01;00;01;00 01;00;02;15 Bonjour\n2 01;00;04;00 01;00;06;00 Au revoir\nencore\n")
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            page.evaluate("textScriptBox('t1', 'media/fr.txt')")
            page.select_option("#ts-lang", "fr")
            page.fill("#ts-offset", "01;00;00;00")
            page.click("#ts-ok")
            self.poll(lambda: self.project()["titles"][0].get("subtitles") == [
                {"file": "media/fr.txt", "lang": "fr", "offset": "01;00;00;00"}])
            # on the timeline, where the title shows them
            page.locator("#tl .tl-clip.sub").nth(1).wait_for()
            self.assertEqual(page.locator("#tl .tl-clip.sub").first.get_attribute("title"), "Bonjour")
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # exported as a text script, timed as the title is
            cmd = lambda c: page.evaluate(f"window.oncemoreCommand('{c}')")  # noqa: E731
            cmd("export_subtitles_script")                     # (one track: no question)
            page.locator("#ex-reveal").wait_for()
            with open(os.path.join(self.dir, "exports", "fr.txt"), encoding="utf-8") as f:
                self.assertEqual(f.read(), "1\t00;00;01;00\t00;00;02;15\tBonjour\n"
                                           "2\t00;00;04;00\t00;00;06;00\tAu revoir\nencore\n")
            page.keyboard.press("Escape")
            # chapter names in the ruler
            self.assertEqual(page.locator("#tl-ruler .ch-name").count(), 0)
            cmd("chapter_names")
            names = page.locator("#tl-ruler .ch-name")
            names.first.wait_for()
            n = len(self.project()["titles"][0]["chapters"])
            self.assertEqual(names.count(), n)
            cmd("chapter_names")
            self.assertEqual(page.locator("#tl-ruler .ch-name").count(), 0)
            browser.close()
        self.assertEqual(errors, [])

    def test_image_script(self):
        """Timeline > Import subtitles with an image script and its pictures
        chosen together: a track whose subtitles show as their pictures."""
        self.s.call("/api/new", "POST", {"sample": True})
        src = tempfile.mkdtemp(prefix="oncemore-isub-gui-")
        self.addCleanup(shutil.rmtree, src, True)
        for name in ("one.png", "two.png"):
            subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "color=c=yellow:s=120x30", "-frames:v", "1", os.path.join(src, name)],
                           check=True)
        with open(os.path.join(src, "pics.txt"), "w") as f:
            f.write("1 00;00;01;00 00;00;02;00 one.png\n2 00;00;03;00 00;00;04;00 two.png\n")
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            with page.expect_file_chooser() as fc:
                page.evaluate("window.oncemoreCommand('import_subtitles')")
            fc.value.set_files([os.path.join(src, n) for n in ("pics.txt", "one.png", "two.png")])
            page.locator("#ts-ok").wait_for(timeout=60000)
            page.select_option("#ts-lang", "en")
            page.click("#ts-ok")
            self.poll(lambda: self.project()["titles"][0].get("subtitles") == [
                {"file": "media/pics.txt", "lang": "en"}])
            clips = page.locator("#tl .tl-clip.sub")
            clips.nth(1).wait_for(timeout=60000)
            self.assertEqual(clips.first.get_attribute("title"), "media/one.png")
            self.assertEqual(clips.first.inner_text(), "▣ one.png")
            self.assertTrue(self.s.app.check(self.project())["valid"])
            browser.close()
        self.assertEqual(errors, [])

    def test_closed_captions(self):
        """Title > Closed captions: a file, then an offset with it."""
        self.s.call("/api/new", "POST", {"sample": True})
        with open(os.path.join(self.dir, "media", "cc.scc"), "w") as f:
            f.write("Scenarist_SCC V1.0\n\n00:00:01:00\t9420 9420\n")
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            # (a .scc is captions only: not offered as a subtitle track)
            page.select_option("#cc-file", "media/cc.scc")
            self.poll(lambda: self.project()["titles"][0].get("captions") == "media/cc.scc")
            page.fill("#cc-offset", "01;00;00;00")
            page.press("#cc-offset", "Tab")
            self.poll(lambda: self.project()["titles"][0].get("captions") ==
                      {"file": "media/cc.scc", "offset": "01;00;00;00"})
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.select_option("#cc-file", "")
            self.poll(lambda: "captions" not in self.project()["titles"][0])
            browser.close()
        self.assertEqual(errors, [])

    def test_button_numbers(self):
        """Properties > Number renumbers a button, the menu's button number
        offset shows in the routing view, and the preview's number keys
        (two digits) press the button with that number."""
        self.s.call("/api/new", "POST", {"sample": True})
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            ids = lambda: [b["id"] for b in self.project()["menus"][0]["buttons"]]  # noqa: E731
            before = ids()
            page.click(".stage .el.button[data-i='2']")
            page.select_option("#btn-number", "0")                   # third becomes first
            self.poll(lambda: ids() == [before[2], before[0], before[1]])
            # the menu's offset (Properties of the menu itself)
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.fill("#inspector input[data-k=button_offset]", "10")
            page.press("#inspector input[data-k=button_offset]", "Tab")
            self.poll(lambda: self.project()["menus"][0].get("button_offset") == 10)
            page.evaluate("window.oncemoreCommand('routing')")
            page.locator(".stage .bnum").nth(2).wait_for(timeout=60000)
            self.assertEqual(page.locator(".stage .bnum text").all_text_contents(), ["11", "12", "13"])
            # the preview: 1 then 3 is button 13, the old second (CHAPTERS)
            page.locator("#stage").focus()
            page.keyboard.press("Shift+Space")
            page.locator("#sim-status", has_text="main").wait_for(timeout=120000)
            page.locator("#sim-screen").focus()
            page.keyboard.press("1")
            page.keyboard.press("3")
            page.locator("#sim-status", has_text="chapters").wait_for(timeout=60000)
            self.assertTrue(self.s.app.check(self.project())["valid"])
            browser.close()
        self.assertEqual(errors, [])

    def test_remote_keys_turned_off(self):
        """Properties > Remote keys turned off, for a title and a menu."""
        self.s.call("/api/new", "POST", {"sample": True})
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            page.check("#inspector [data-uop=menu]")
            page.check("#inspector [data-uop=next]")
            self.poll(lambda: self.project()["titles"][0].get("prohibit") == ["next", "menu"])
            page.uncheck("#inspector [data-uop=menu]")
            self.poll(lambda: self.project()["titles"][0].get("prohibit") == ["next"])
            page.uncheck("#inspector [data-uop=next]")
            self.poll(lambda: "prohibit" not in self.project()["titles"][0])
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.check("#inspector [data-uop=title]")
            self.poll(lambda: self.project()["menus"][0].get("prohibit") == ["title"])
            self.assertTrue(self.s.app.check(self.project())["valid"])
            browser.close()
        self.assertEqual(errors, [])

    def test_reorder_titles(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=title][data-id=t2]", timeout=120000)
            self.assertTrue(page.locator("[data-move='1']").is_disabled())   # already last
            page.click("[data-move='-1']")
            self.wait_saved(page)
            self.assertEqual([x["id"] for x in self.project()["titles"]], ["t2", "t1"])
            first = page.locator(".nav-item[data-view=title]").first
            self.assertEqual(first.get_attribute("data-id"), "t2")
            self.assertTrue(page.locator("[data-move='-1']").is_disabled())  # now first
            # Menu key target for this title
            page.select_option("#inspector select[data-k=remote_menu]", "chapters")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["remote_menu"], "chapters")
            # its own video bitrate, and AC-3 copied unchanged
            page.select_option("#inspector select[data-k=video_bitrate]", "4M")
            page.check("#inspector [data-k='audio.passthrough']")
            self.wait_saved(page)
            t = self.project()["titles"][0]
            self.assertEqual((t["video_bitrate"], t["audio"]["passthrough"]), ("4M", True))
            # DTS: always copied (5.1 unless told), at the source's own rate
            page.select_option("#inspector select[data-k='audio.codec']", "dts")
            self.poll(lambda: self.project()["titles"][0]["audio"] == {"codec": "dts"})
            page.locator("#inspector select[data-k='audio.bitrate']:disabled").wait_for(timeout=60000)
            box = page.locator("#inspector [data-k='audio.passthrough']")
            self.assertTrue(box.is_checked() and box.is_disabled())
            self.assertEqual(page.locator("#inspector select[data-k='audio.channels']").input_value(), "6")
            page.select_option("#inspector select[data-k='audio.codec']", "ac3")
            self.poll(lambda: "audio" not in self.project()["titles"][0]
                      or self.project()["titles"][0]["audio"] == {"codec": "ac3"})
            # film with 3:2 pulldown, then back to automatic
            page.select_option("#inspector select[data-k=scan]", "pulldown")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["scan"], "pulldown")
            page.select_option("#inspector select[data-k=scan]", "__none__")
            self.wait_saved(page)
            self.assertNotIn("scan", self.project()["titles"][0])
            # the picture used as it is: its encoding settings go away
            page.check("#ti-copy")
            self.wait_saved(page)
            t = self.project()["titles"][0]
            self.assertEqual(t.get("transcode"), False)
            self.assertNotIn("video_bitrate", t)
            self.assertEqual(page.locator("#inspector select[data-k=scan]").count(), 0)
            self.assertTrue(page.locator("#inspector select[data-k=video_bitrate]").is_disabled())
            page.uncheck("#ti-copy")
            self.wait_saved(page)
            self.assertNotIn("transcode", self.project()["titles"][0])
            # DVD-ROM content on the disc page
            page.click(".nav-item[data-view=disc]")
            page.fill("#rom-files", "extras/\nREADME.txt")
            page.locator("#rom-files").dispatch_event("change")
            self.wait_saved(page)
            self.assertEqual(self.project()["disc"]["rom_files"], ["extras/", "README.txt"])
            page.fill("#rom-files", "")                          # (they do not exist)
            page.locator("#rom-files").dispatch_event("change")
            self.wait_saved(page)
            self.assertNotIn("rom_files", self.project()["disc"])
            page.click(".nav-item[data-view=title][data-id=t1]")
            # one user menu: nothing to move
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator("#inspector [data-move]").first.wait_for()
            self.assertEqual(page.locator("#inspector [data-move]:disabled").count(), 2)
            # menu playback: twice, then play all; first button; no memory
            page.select_option("#inspector select[data-k=loop]", "2")
            page.locator("#inspector select[data-k=end_action]").wait_for()
            page.select_option("#inspector select[data-k=end_action]", "playall")
            page.select_option("#inspector select[data-k=default_button]", "ch")
            page.uncheck("#remember-btn")
            self.wait_saved(page)
            m = self.project()["menus"][0]
            self.assertEqual((m["loop"], m["end_action"], m["default_button"], m["remember_button"]),
                             (2, "playall", "ch", False))
            page.select_option("#inspector select[data-k=loop]", "forever")
            self.wait_saved(page)
            self.assertNotIn("loop", self.project()["menus"][0])
            page.fill("#inspector input[data-k=fade_in]", "1.5")         # fade in from black
            page.locator("#inspector input[data-k=fade_in]").dispatch_event("change")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["fade_in"], 1.5)
            page.fill("#inspector input[data-k=fade_in]", "")
            page.locator("#inspector input[data-k=fade_in]").dispatch_event("change")
            self.wait_saved(page)
            self.assertNotIn("fade_in", self.project()["menus"][0])
            # disc: the Title key
            page.click(".nav-item[data-view=disc]")
            page.select_option("select[data-k=title_key]", "title:t1")
            self.wait_saved(page)
            self.assertEqual(self.project()["disc"]["title_key"], "title:t1")
            page.click(".nav-item[data-view=menu][data-id=main]")
            # turn SAMPLE TITLE B into a picture button, then check the exact preview
            page.locator(".stage .el.button").nth(2).click()
            page.select_option("#inspector select[data-k=image]", "media/menu_bg.png")
            page.wait_for_selector(".stage .el.button img")   # after the image was probed
            self.wait_saved(page)
            b = self.project()["menus"][0]["buttons"][2]
            self.assertEqual((b["image"], b["width"]), ("media/menu_bg.png", 160))
            page.select_option("#inspector select[data-k=highlight]", "shape")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][2]["highlight"], "shape")
            page.click("#exact")
            page.wait_for_selector(".stage img.exact", timeout=60000)
            browser.close()

    def test_playlists_and_chapter_names(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            # name chapter 2, poster frame at 10 s
            page.fill("[data-ch-name='1']", "Middle")
            page.press("[data-ch-name='1']", "Enter")
            self.wait_saved(page)
            page.fill("#tc-input", "00:00:10.000")
            page.press("#tc-input", "Enter")
            page.click("[data-poster='1']")
            self.wait_saved(page)
            ch = self.project()["titles"][0]["chapters"]
            self.assertEqual((ch[1]["time"], ch[1]["name"]), ("00:00:08.000", "Middle"))
            self.assertRegex(ch[1]["poster"], r"^00:00:10\.0\d\d$")     # snapped to a frame
            self.assertEqual(ch[2], "00:00:16.000")
            # a playlist: chapter 2 of t1, then all of t2, then the main menu
            page.click("#add-playlist")
            page.locator("[data-item='0']").wait_for()
            page.select_option("[data-item='0'] [data-k=a]", "2")
            page.select_option("[data-item='0'] [data-k=b]", "2")
            self.wait_saved(page)
            page.click("#add-item")
            page.locator("[data-item='1']").wait_for()
            page.select_option("[data-item='1'] [data-k=tid]", "t2")
            page.select_option("select[data-k=end_action]", "menu:main")
            self.wait_saved(page)
            pl = self.project()["playlists"][0]
            self.assertEqual((pl["items"], pl["end_action"]), (["t1:2", "t2"], "menu:main"))
            # buttons can start it
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator(".stage .el.button").first.click()
            page.select_option("#inspector select[data-k=action]", f"playlist:{pl['id']}")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][0]["action"], f"playlist:{pl['id']}")
            browser.close()
        self.assertEqual(errors, [])

    def test_clips_editor(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=title][data-id=t2]", timeout=120000)
            # a second video makes the title a list of clips
            page.select_option("#clip-add", "media/sample_a.mp4")
            page.locator("tr[data-clip='1']").wait_for(timeout=180000)
            self.wait_saved(page)
            ti = self.project()["titles"][1]
            self.assertEqual(ti["clips"], [{"source": "media/sample_b.mp4"},
                                           {"source": "media/sample_a.mp4"}])
            self.assertNotIn("source", ti)
            page.fill("tr[data-clip='1'] [data-cf=in]", "2")
            page.press("tr[data-clip='1'] [data-cf=in]", "Enter")
            page.fill("tr[data-clip='1'] [data-cf=out]", "00:00:04")
            page.press("tr[data-clip='1'] [data-cf=out]", "Enter")
            self.poll(lambda: self.project()["titles"][1]["clips"][1].get("out"))
            self.assertEqual(self.project()["titles"][1]["clips"][1],
                             {"source": "media/sample_a.mp4", "in": "00:00:02.000",
                              "out": "00:00:04.000"})
            # joined preview, one chapter per clip, the clips on the timeline
            page.locator("#frame").wait_for(timeout=180000)
            page.locator(".chapter-list li").nth(1).wait_for(timeout=60000)
            self.assertEqual(page.locator(".chapter-list li").count(), 2)
            page.locator(".tl-clip.clip").nth(1).wait_for()
            self.assertEqual(page.locator(".tl-clip.clip").count(), 2)
            page.locator(".tl-clip.clip").nth(1).click()
            page.locator("#tc-input").wait_for()
            self.assertNotEqual(page.input_value("#tc-input"), "00:00:00.000")
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # a still picture: shown for a time (no in / out), filling the frame
            clip = lambda k: self.project()["titles"][1]["clips"][k]  # noqa: E731
            page.select_option("#clip-add", "media/menu_bg.png")
            page.locator("tr[data-clip='2'] [data-cd]").wait_for(timeout=60000)
            self.assertEqual(page.locator("tr[data-clip='2'] [data-cf]").count(), 0)
            self.wait_saved(page)
            page.fill("tr[data-clip='2'] [data-cd]", "2")
            page.press("tr[data-clip='2'] [data-cd]", "Enter")
            self.poll(lambda: clip(2).get("duration") == 2)
            self.wait_saved(page)
            page.select_option("tr[data-clip='2'] [data-cfit]", "fill")
            self.poll(lambda: clip(2).get("fit") == "fill")
            self.assertEqual(clip(2), {"source": "media/menu_bg.png", "duration": 2, "fit": "fill"})
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.locator(".chapter-list li").nth(2).wait_for(timeout=180000)   # joined with it
            page.click("tr[data-clip='2'] [data-crm]")
            self.poll(lambda: len(self.project()["titles"][1]["clips"]) == 2)
            page.locator("tr[data-clip='2']").wait_for(state="detached")
            self.wait_saved(page)
            # first clip moved down, then removed: an ordinary title again
            page.click("tr[data-clip='0'] [data-cmv='1']")
            self.poll(lambda: self.project()["titles"][1]["clips"][0]["source"] ==
                      "media/sample_a.mp4")
            page.click("tr[data-clip='1'] [data-crm]")
            self.poll(lambda: len(self.project()["titles"][1]["clips"]) == 1)
            page.locator("tr[data-clip='1']").wait_for(state="detached")
            page.fill("tr[data-clip='0'] [data-cf=in]", "")
            page.press("tr[data-clip='0'] [data-cf=in]", "Enter")
            # let that edit land (and the editor redraw) before the next field: an
            # input still focused when the editor redraws commits on its own
            self.poll(lambda: "in" not in self.project()["titles"][1]["clips"][0])
            self.wait_saved(page)
            page.locator("tr[data-clip='0'] [data-cf=out]").fill("")
            page.press("tr[data-clip='0'] [data-cf=out]", "Enter")
            self.poll(lambda: "source" in self.project()["titles"][1])
            self.assertEqual(self.project()["titles"][1]["source"], "media/sample_a.mp4")
            self.assertNotIn("clips", self.project()["titles"][1])
            browser.close()
        self.assertEqual(errors, [])

    def test_slideshow_and_subtitle_editor(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.locator(".nav-item[data-view=title][data-id=t1]").wait_for(timeout=120000)
            # two pieces of music in Media (3 s and 2 s)
            for name, secs in (("song1.wav", 3), ("song2.wav", 2)):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                                f"sine=d={secs}", os.path.join(self.dir, "media", name)], check=True)
            page.reload()
            page.locator(".nav-item[data-view=title][data-id=t1]").wait_for(timeout=120000)
            # a slideshow from the pictures in Media
            page.click("#add-slideshow")
            page.locator("[data-slide='0']").wait_for()
            self.wait_saved(page)
            ti = self.project()["titles"][-1]
            self.assertEqual(ti["slideshow"]["slides"], [{"image": "media/menu_bg.png"}])
            page.select_option("#ss-add", "media/menu_bg.png")
            page.locator("[data-slide='1']").wait_for()
            page.fill("[data-slide='0'] [data-f=duration]", "3")
            page.press("[data-slide='0'] [data-f=duration]", "Enter")
            page.check("#ss-pz")
            page.select_option("#ss-tr", "none")
            self.wait_saved(page)
            page.select_option("#ss-fit", "fill")
            self.wait_saved(page)
            page.select_option("[data-slide='0'] [data-f=transition]", "wipeleft")
            self.poll(lambda: self.project()["titles"][-1]["slideshow"]["slides"][0].get("transition"))
            self.wait_saved(page)
            self.assertEqual(page.locator("[data-slide='1'] [data-f=transition]").count(), 0)  # last
            page.select_option("[data-slide='1'] [data-f=fit]", "fit")
            self.poll(lambda: self.project()["titles"][-1]["slideshow"]["slides"][1].get("fit"))
            self.wait_saved(page)
            # both pieces of music, the pictures fitted to them
            page.select_option("#ss-audio", "media/song1.wav")
            page.locator(".ss-music").first.wait_for()
            self.wait_saved(page)
            page.select_option("#ss-audio", "media/song2.wav")
            page.locator(".ss-music").nth(1).wait_for()
            self.wait_saved(page)
            page.check("#ss-fitaudio")
            self.wait_saved(page)
            sh = self.project()["titles"][-1]["slideshow"]
            self.assertEqual(sh, {"slides": [{"image": "media/menu_bg.png", "duration": 3,
                                              "transition": "wipeleft"},
                                             {"image": "media/menu_bg.png", "fit": "fit"}],
                                  "pan_zoom": True, "transition": "none", "fit": "fill",
                                  "audio": ["media/song1.wav", "media/song2.wav"],
                                  "fit_to_audio": True})
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.click("#ss-play")
            page.locator("#player:not([hidden])").wait_for(timeout=180000)
            # 3 : 5 of the music's 5 s
            self.assertEqual(page.inner_text("[data-slide='0'] [data-fitted]"), "Fitted: 1.9 s")
            self.assertEqual(page.inner_text("[data-slide='1'] [data-fitted]"), "Fitted: 3.1 s")
            # one piece removed: a single file again
            page.click("[data-rmmusic='1']")
            self.poll(lambda: self.project()["titles"][-1]["slideshow"].get("audio") ==
                      "media/song1.wav")
            # advanced by hand: timing, transitions and music go
            page.check("#ss-manual")
            self.poll(lambda: self.project()["titles"][-1]["slideshow"].get("advance") == "manual")
            self.wait_saved(page)
            sh = self.project()["titles"][-1]["slideshow"]
            self.assertEqual(sh, {"slides": [{"image": "media/menu_bg.png"},
                                             {"image": "media/menu_bg.png", "fit": "fit"}],
                                  "fit": "fill", "advance": "manual"})
            self.assertTrue(self.s.app.check(self.project())["valid"])
            self.assertTrue(page.locator("#ss-tr").is_hidden())
            # a title from a sound file, with a picture to look at
            page.click(".media-item[data-media='media/song2.wav']")
            page.click("button[data-act=title]")
            page.locator("#inspector select[data-k=picture]").wait_for()
            self.wait_saved(page)
            page.select_option("#inspector select[data-k=picture]", "media/menu_bg.png")
            self.wait_saved(page)
            ti = self.project()["titles"][-1]
            self.assertEqual((ti["source"], ti["picture"]), ("media/song2.wav", "media/menu_bg.png"))
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # subtitles: a new track, two cues typed in, one removed
            page.click(".nav-item[data-view=title][data-id=t1]")
            page.click("#sub-new")
            page.locator("#sub-add").wait_for()
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["subtitles"], [{"file": "media/t1-1.srt"}])
            page.fill("#tc-input", "00:00:02.000")
            page.press("#tc-input", "Enter")
            page.click("#sub-add")
            page.locator("tr[data-cue='0']").wait_for()
            page.fill("tr[data-cue='0'] [data-f=text]", "Hello there")
            page.locator("tr[data-cue='0'] [data-f=text]").blur()
            page.locator("tr[data-cue='0'] textarea", has_text="Hello there").wait_for()
            page.fill("#tc-input", "00:00:05.000")
            page.press("#tc-input", "Enter")
            page.click("#sub-add")
            page.locator("tr[data-cue='1']").wait_for()
            page.select_option("tr[data-cue='1'] [data-f=position]", "top")
            page.locator("tr[data-cue='1'] [data-f=position]").wait_for()
            srt = os.path.join(self.dir, "media", "t1-1.srt")
            for _ in range(40):
                with open(srt, encoding="utf-8") as f:
                    text = f.read()
                if "{\\an8}" in text:
                    break
                time.sleep(0.25)
            # (the playhead snaps to frames, 2.002 s at 29.97 fps)
            self.assertRegex(text, r"00:00:02,0\d\d --> 00:00:04,0\d\d\nHello there")
            self.assertRegex(text, r"00:00:05,0\d\d --> 00:00:07,0\d\d")
            self.assertIn("{\\an8}", text)            # top, kept in the SubRip file
            page.click("[data-delcue='0']")
            page.locator("tr[data-cue='1']").wait_for(state="detached")
            with open(srt, encoding="utf-8") as f:
                self.assertNotIn("Hello there", f.read())
            browser.close()
        self.assertEqual(errors, [])

    def test_flowchart_and_simulator(self):
        from .test_simulate import rich_project
        self.s.call("/api/new", "POST", {"sample": True})
        with open(os.path.join(self.dir, "project.oncemore.json"), "w") as f:
            json.dump(rich_project(), f)
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=flow]")
            page.locator(".flow-svg").wait_for(timeout=60000)
            for node in ("fp", "menu:main", "menu:intro", "title:t1", "playlist:best",
                         "playall"):
                self.assertEqual(page.locator(f".flow-svg [data-node='{node}']").count(), 1)
            page.locator("#flow-notes", has_text="No navigation problems").wait_for()
            page.click(".flow-svg [data-node='menu:setup']")         # opens the menu editor
            page.locator(".nav-item.active[data-view=menu][data-id=setup]").wait_for()
            # the simulator: down to CHAPTERS, OK, then BACK with the mouse
            page.select_option("#workspaces", "sim")           # Project Preview, from first play
            page.locator("#pv-window #sim-screen img.hl").wait_for(timeout=120000)
            page.locator("#sim-status", has_text="main").wait_for()
            page.locator("#sim-screen").press("ArrowDown")
            page.locator("#sim-status", has_text="main · ").wait_for()
            page.click("[data-key=enter]")
            page.locator("#sim-status", has_text="chapters").wait_for(timeout=120000)
            page.locator("#sim-screen img.hl").wait_for(timeout=120000)
            page.click("[data-key=title]")                            # Title key -> intro
            page.locator("#sim-status", has_text="intro").wait_for(timeout=120000)
            page.click("[data-key=enter]")                            # SKIP -> chapter 3
            page.locator("#sim-status", has_text="Chapter 3 of 3").wait_for()
            page.click("[data-key=menu]")                             # remote_menu of t1
            page.locator("#sim-status", has_text="chapters").wait_for()
            page.locator("#sim-screen .hit").first.wait_for(timeout=120000)
            n = page.locator("#sim-screen .hit").count()
            page.locator("#sim-screen .hit").nth(n - 1).click()      # BACK
            page.locator("#sim-status", has_text="Menu main").wait_for()
            browser.close()
        self.assertEqual(errors, [])

    def test_photoshop_import(self):
        from .test_psdmenu import design
        self.s.call("/api/new", "POST", {"sample": True})
        status, r = self.s.call("/api/upload?name=design.psd", "POST", raw=design(),
                                headers={"Content-Type": "application/octet-stream"})
        self.assertEqual(status, 200, r)
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.locator(".media-item[data-media='media/design.psd']").wait_for(timeout=60000)
            page.click("#add-menu")
            page.locator("#psd-go").wait_for()
            page.click("#psd-go")
            page.locator("#modal", has_text="3 button(s) imported").wait_for(timeout=120000)
            self.assertIn("no action could be guessed", page.locator("#modal").inner_text())
            page.click(".modal-close")
            menu = self.poll(lambda: next((m for m in self.project()["menus"]
                                           if m["id"] == "design1"), None))
            self.assertEqual([b["id"] for b in menu["buttons"]], ["play", "chapter_2", "extras"])
            self.assertEqual(page.locator(".stage .el.button img.area").count(), 3)
            # retarget EXTRAS, then import again: the target stays
            page.locator(".stage .el.button").nth(2).click()
            page.select_option("#inspector select[data-k=action]", "title:t2")
            self.poll(lambda: next(m for m in self.project()["menus"]
                                   if m["id"] == "design1")["buttons"][2]["action"] == "title:t2")
            page.locator(".stage").click(position={"x": 5, "y": 5})
            page.click("#psd-again")
            page.locator("#modal", has_text="3 button(s) imported").wait_for(timeout=120000)
            page.click(".modal-close")
            self.wait_saved(page)
            time.sleep(1)
            self.wait_saved(page)
            menu = next(m for m in self.project()["menus"] if m["id"] == "design1")
            self.assertEqual(menu["buttons"][2]["action"], "title:t2")
            self.assertEqual(menu["psd"], "media/design.psd")
            self.assertTrue(self.s.app.check(self.project())["valid"])
            browser.close()
        self.assertEqual(errors, [])

    def test_workspace(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            page.locator(".stage .el.button").first.wait_for(timeout=60000)
            # workspaces
            page.select_option("#workspaces", "flow")
            page.locator(".flow-svg").wait_for(timeout=60000)
            page.select_option("#workspaces", "author")
            page.locator("#center-head", has_text="main").wait_for()
            # layers <-> stage selection
            rows = page.locator("#layers .layer-row[data-lk=button]")
            self.assertEqual(rows.count(), 3)
            rows.nth(1).click()
            page.locator("#layers .layer-row.selected[data-li='1']").wait_for()
            self.assertIn("selected", page.locator(".stage .el.button").nth(1).get_attribute("class"))
            self.assertEqual(page.locator("#inspector [data-k=label]").input_value(), "CHAPTERS")
            page.locator(".stage .el.button").nth(2).click()
            page.locator("#layers .layer-row.selected[data-li='2']").wait_for()
            # library: a text style on the selected button
            page.click("[data-lt=library]")
            page.click("[data-style=outline]")
            self.poll(lambda: self.project()["menus"][0]["buttons"][2].get("outline") == "#000000")
            page.click("[data-lt=project]")
            # timeline: move chapter 2 by dragging its mark, seek from the ruler
            page.click(".nav-item[data-view=title][data-id=t1]")
            page.locator("#p-timeline .tl-chapter[data-tlch='1']").wait_for(timeout=60000)
            mk = page.locator(".tl-chapter[data-tlch='1']").bounding_box()
            ruler = page.locator("#tl-ruler").bounding_box()
            page.mouse.move(mk["x"] + 1, mk["y"] + mk["height"] / 2)
            page.mouse.down()
            page.mouse.move(mk["x"] + 1 + ruler["width"] / 24 * 2, mk["y"] + mk["height"] / 2,
                            steps=5)
            page.mouse.up()
            def second():
                c = self.project()["titles"][0]["chapters"][1]
                c = c["time"] if isinstance(c, dict) else c
                return sum(float(x) * 60 ** i for i, x in enumerate(reversed(str(c).split(":"))))
            self.poll(lambda: abs(second() - 8) > 0.5, timeout=10)
            self.assertAlmostEqual(second(), 10, delta=0.4)          # ~2 s later, on a frame
            page.mouse.click(ruler["x"] + ruler["width"] * 0.75, ruler["y"] + 5)
            page.locator("#tc", has_text="00:00:18").wait_for()
            # theme and panel sizes are remembered
            # Modern is the default skin; Classic is chosen in Edit > Preferences
            self.assertIsNone(page.evaluate("document.documentElement.dataset.skin"))
            page.keyboard.press("Control+Comma")                       # Edit > Preferences
            page.select_option("#pref-skin", "classic")
            page.select_option("#pref-theme", "light")
            page.keyboard.press("Escape")
            self.assertEqual(page.evaluate("document.documentElement.dataset.skin"), "classic")
            self.assertEqual(page.evaluate("document.documentElement.dataset.theme"), "light")
            sp = page.locator(".splitter[data-split=left]").bounding_box()
            page.mouse.move(sp["x"] + 2, sp["y"] + 200)
            page.mouse.down()
            page.mouse.move(sp["x"] + 82, sp["y"] + 200, steps=4)
            page.mouse.up()
            width = page.locator("#p-left").bounding_box()["width"]
            page.reload()
            page.locator("#workspaces option").first.wait_for(state="attached", timeout=60000)
            self.assertEqual(page.evaluate("document.documentElement.dataset.theme"), "light")
            self.assertEqual(page.evaluate("document.documentElement.dataset.skin"), "classic")
            self.assertAlmostEqual(page.locator("#p-left").bounding_box()["width"], width, delta=2)
            browser.close()
        self.assertEqual(errors, [])

    def test_menu_design_tools(self):
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            # a menu from a template, with buttons for the project's titles
            page.click("#add-menu", timeout=120000)
            page.click("[data-template='classic']")
            page.wait_for_selector(".stage .el.shape")
            self.wait_saved(page)
            m = self.project()["menus"][-1]
            self.assertEqual(m["id"], "classic1")
            self.assertEqual([b["action"] for b in m["buttons"]][:3],
                             ["playall", "title:t1", "title:t2"])
            # the template lays out without overlaps: the exact preview renders
            page.click("#exact")
            page.wait_for_selector(".stage img.exact", timeout=60000)
            page.click("#exact")
            # select two buttons, align their left edges
            btn = page.locator(".stage .el.button")
            btn.nth(0).click()
            btn.nth(1).click(modifiers=["Shift"])
            page.locator("[data-align='left']").wait_for()
            page.locator(".stage .el.button").nth(1).click(modifiers=["Shift"])   # off again
            self.assertEqual(page.locator("[data-align]").count(), 0)
            page.locator(".stage .el.button").nth(1).click(modifiers=["Shift"])
            page.locator("#stage").focus()
            page.keyboard.press("Shift+ArrowRight")                # nudge both by 10
            self.wait_saved(page)
            b = self.project()["menus"][-1]["buttons"]
            self.assertEqual((b[0]["x"], b[1]["x"]), (94, 94))
            page.click("[data-align='right']")
            self.wait_saved(page)
            # duplicate, then delete the copy again
            n = len(self.project()["menus"][-1]["buttons"])
            page.locator(".stage .el.button").nth(0).click()
            page.keyboard.press("Control+d")
            self.wait_saved(page)
            self.assertEqual(len(self.project()["menus"][-1]["buttons"]), n + 1)
            page.keyboard.press("Delete")
            self.wait_saved(page)
            self.assertEqual(len(self.project()["menus"][-1]["buttons"]), n)
            # a rectangle, then its colour and opacity
            page.click("#add-shape")
            page.locator("#shape-a").wait_for()
            page.fill("#shape-rgb", "#336699")
            page.locator("#shape-a").fill("128")
            page.locator("#shape-a").dispatch_event("change")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][-1]["shapes"][-1]["color"], "#33669980")
            # text style: outline on the title text
            page.locator(".stage .el.text").first.click()
            page.check("#st-outline")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][-1]["texts"][0]["outline"], "#000000")
            browser.close()
        self.assertEqual(errors, [])

    def test_full_flow(self):
        errors = []
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception:
                exe = _chromium()
                if not exe:
                    self.skipTest("no Chromium for Playwright")
                browser = p.chromium.launch(executable_path=exe)
            page = browser.new_page(viewport={"width": 1400, "height": 900}, locale="en-US")
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: m.type == "error" and errors.append(m.text))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            # new empty project
            page.fill("#np-label", "Demo disc")
            page.click("#np-empty")
            page.wait_for_selector("#dropzone")
            # upload through the file picker
            with page.expect_file_chooser() as fc:
                page.click("#dropzone")
            fc.value.set_files(self.clip)
            page.wait_for_selector(".media-item[data-media$='-clip.mp4']")
            page.click(".media-item[data-media$='-clip.mp4']")
            page.click("button[data-act=title]")
            page.wait_for_selector("#scrub")
            # add a chapter at 3 s
            page.fill("#tc-input", "00:00:03.000")
            page.press("#tc-input", "Enter")
            page.click("#add-ch")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["chapters"], ["00:00:00", "00:00:03.000"])
            # 5.1 audio; the bitrate shown follows the 5.1 default
            page.select_option("select[data-k='audio.channels']", "6")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["audio"], {"channels": 6})
            self.assertEqual(page.input_value("select[data-k='audio.bitrate']"), "448k")
            # play the preview from the playhead (a WebM or MP4 copy, whichever this
            # browser plays), pause: back to exact frames, later than where it started
            page.click("#play")
            page.locator("#play", has_text="Pause").wait_for(timeout=120000)
            page.wait_for_timeout(1200)
            page.click("#play")
            page.locator("#play", has_text="Play").wait_for()
            self.assertTrue(page.locator("#player").is_hidden())
            self.assertTrue(page.locator("#frame").is_visible())
            self.assertGreater(float(page.input_value("#scrub")), 3.2)
            # enable the chapter menu, then add a menu
            page.check("#cm-on")
            page.click("#add-menu")
            page.click("[data-template='']")                  # Blank
            page.wait_for_selector(".stage .el.button")
            self.wait_saved(page)
            proj = self.project()
            self.assertEqual(proj["menus"][0]["buttons"][0]["action"], "title:t1")
            self.assertTrue(proj["titles"][0]["auto_chapter_menu"])
            # drag the button, then undo
            el = page.locator(".stage .el.button").first
            box = el.bounding_box()
            page.mouse.move(box["x"] + 4, box["y"] + 4)
            page.mouse.down()
            page.mouse.move(box["x"] + 104, box["y"] + 54, steps=6)
            page.mouse.up()
            self.wait_saved(page)
            moved = self.project()["menus"][0]["buttons"][0]
            self.assertGreater(moved["x"], 80 + 60)
            self.assertGreater(moved["y"], 200 + 30)
            page.click("#menubar [data-mb='1']")                       # Edit > Undo
            page.click(".popup button:has-text('Undo')")
            self.wait_saved(page)
            back = self.project()["menus"][0]["buttons"][0]
            self.assertEqual((back["x"], back["y"]), (80, 200))
            # point the button at the generated chapter menu via the inspector
            el.click()
            page.select_option("#inspector select[data-k=action]", "playall")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][0]["action"], "playall")
            page.select_option("#inspector select[data-k=action]", "resume")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][0]["action"], "resume")
            # a menu opened on one of its buttons
            m0 = self.project()["menus"][0]
            link = f"menu:{m0['id']}:{m0['buttons'][-1]['id']}"
            page.select_option("#inspector select[data-k=action]", link)
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][0]["action"], link)
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # a link whose button is gone (deleted, made text) opens the menu as usual
            self.assertEqual(page.evaluate("""() => {
                const p = {disc: {first_play: "menu:a:x"}, titles: [{end_action: "menu:a:y"}],
                           menus: [{id: "a", buttons: [{id: "y", action: "menu:a:x"}]}]};
                dropLostButtonLinks(p);
                return [p.disc.first_play, p.titles[0].end_action, p.menus[0].buttons[0].action];
            }"""), ["menu:a", "menu:a:y", "menu:a"])
            page.select_option("#inspector select[data-k=action]", "menu:chapters_t1")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][0]["action"], "menu:chapters_t1")
            # exact preview
            page.click("#exact")
            page.wait_for_selector(".stage img.exact", timeout=60000)
            # build
            page.click("[data-lt=build]")                              # the Build panel
            page.check("#fast")
            page.click("#start")
            page.wait_for_selector(".result-ok, .result-err", timeout=300000)
            self.assertEqual(page.locator(".result-ok").count(), 1, page.inner_text("#sidebar"))
            browser.close()
        self.assertEqual(errors, [])
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "output", "DEMO_DISC.iso")))

    def test_source_chapters(self):
        """A file's own chapter markers become the chapters of a title made
        from it, and Timeline > Import chapter markers reads them again."""
        self.s.call("/api/new", "POST", {"sample": True})
        meta = os.path.join(self.dir, "chapters.txt")
        with open(meta, "w") as f:
            f.write(";FFMETADATA1\n" + "".join(
                f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={a}\nEND={b}\ntitle={n}\n"
                for a, b, n in ((0, 8000, "Opening"), (8000, 15500, "Middle"),
                                (15500, 24000, "Ende"))))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i",
                        os.path.join(self.dir, "media", "sample_a.mp4"), "-i", meta,
                        "-map_metadata", "1", "-map_chapters", "1", "-c", "copy",
                        os.path.join(self.dir, "media", "marked.mp4")], check=True)
        status, info = self.s.call("/api/probe?path=media/marked.mp4")
        self.assertEqual(info["chapters"], [{"time": 0.0, "name": "Opening"},
                                            {"time": 8.0, "name": "Middle"},
                                            {"time": 15.5, "name": "Ende"}])
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            page.evaluate("mediaAction('title', 'media/marked.mp4')")
            ti = self.poll(lambda: next((t for t in self.project()["titles"]
                                         if t["source"] == "media/marked.mp4"
                                         and len(t["chapters"]) == 3), None))
            self.assertEqual(ti["chapters"], [{"time": "00:00:00", "name": "Opening"},
                                              {"time": "00:00:08.000", "name": "Middle"},
                                              {"time": "00:00:15.500", "name": "Ende"}])
            # sample_a has no markers: the command says so and changes nothing
            page.click(".nav-item[data-view=title][data-id=t1]")
            page.locator("#tc-input").wait_for(timeout=60000)
            messages = []
            page.on("dialog", lambda d: (messages.append(d.message), d.accept()))
            page.evaluate("window.oncemoreCommand('chapters_from_source')")
            page.wait_for_timeout(500)
            self.assertEqual(messages, ["The source has no chapter markers."])
            # point t1 at the marked file and import its markers
            page.evaluate("commit((p) => { p.titles[0].source = 'media/marked.mp4'; })")
            page.evaluate("window.oncemoreCommand('chapters_from_source')")
            self.poll(lambda: "Ende" in json.dumps(self.project()["titles"][0]["chapters"]))
            self.assertEqual(self.project()["titles"][0]["chapters"],
                             [{"time": "00:00:00", "name": "Opening"},
                              {"time": "00:00:08.000", "name": "Middle"},
                              {"time": "00:00:15.500", "name": "Ende"}])
            browser.close()
        self.assertEqual(errors, [])

    def test_conveniences(self):
        """Chapters at intervals, Replace asset (also for a missing file),
        Project settings, Window > panel, the Photoshop change notice."""
        self.s.call("/api/new", "POST", {"sample": True})
        pj = self.project()
        pj["titles"][1]["source"] = "media/gone.mp4"                 # a missing file
        pj["menus"][0]["psd"] = "media/main.psd"
        with open(os.path.join(self.dir, "media", "main.psd"), "wb") as f:
            f.write(b"8BPS fake")
        with open(os.path.join(self.dir, "project.oncemore.json"), "w") as f:
            json.dump(pj, f)
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            # a chapter every 5 seconds on the 24-second title, replacing its chapters
            page.click(".nav-item[data-view=title][data-id=t1]", timeout=120000)
            page.locator("#tc-input").wait_for(timeout=60000)
            page.evaluate("window.oncemoreCommand('chapters_interval')")
            page.fill("#ci-n", "5")
            page.select_option("#ci-unit", "1")
            page.locator("#ci-preview", has_text="5 chapters").wait_for()
            page.click("#ci-ok")
            self.wait_saved(page)
            ch = [c["time"] if isinstance(c, dict) else c for c in self.project()["titles"][0]["chapters"]]
            self.assertEqual(ch, ["00:00:00", "00:00:05.000", "00:00:10.000", "00:00:15.000",
                                  "00:00:20.000"])
            # the missing file is listed first and marked; replace it everywhere
            page.evaluate("window.oncemoreCommand('replace_asset')")
            self.assertIn("missing", page.locator("#ra-from option").first.inner_text())
            self.assertEqual(page.input_value("#ra-from"), "media/gone.mp4")
            page.select_option("#ra-to", "media/sample_b.mp4")
            page.click("#ra-ok")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][1]["source"], "media/sample_b.mp4")
            self.assertNotIn("gone.mp4", json.dumps(self.project()))
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # File > Project settings: the disc in Properties
            page.evaluate("window.oncemoreCommand('project_settings')")
            page.locator("#inspector #rom-files").wait_for()
            # Window > Library / Build bring those panels to the front
            page.evaluate("window.oncemoreCommand('win_library')")
            page.locator("#library .lib-section").first.wait_for()
            page.evaluate("window.oncemoreCommand('win_build')")
            page.locator("#sidebar #start").wait_for()
            page.check("#sidebar input[name=kind][value=disc]")         # Output: DVD disc
            page.fill("#recorder", "/dev/sr9")
            page.locator("#recorder").dispatch_event("change")
            page.check("#sidebar input[name=kind][value=iso]")
            self.assertEqual(page.locator("#recorder").count(), 0)
            page.check("#sidebar input[name=kind][value=disc]")
            self.assertEqual(page.input_value("#recorder"), "/dev/sr9")  # remembered
            page.check("#sidebar input[name=kind][value=iso]")
            page.evaluate("window.oncemoreCommand('win_project')")
            # File > Revert to a saved version: the oldest is the project before these
            # edits (the missing file is back); Undo returns to the current one
            page.evaluate("window.oncemoreCommand('revert_backup')")
            page.locator("[data-backup]").first.wait_for()
            page.on("dialog", lambda d: d.accept())
            page.locator("[data-backup]").last.click()
            self.poll(lambda: self.project()["titles"][1]["source"] == "media/gone.mp4")
            page.locator("#modal").wait_for(state="hidden")
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.keyboard.press("Control+z")
            self.poll(lambda: self.project()["titles"][1]["source"] == "media/sample_b.mp4")
            self.wait_saved(page)
            # the colour set: a 50% highlight, then a normal colour (40% white by default)
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator("#inspector [data-cs-a=highlight_color]").wait_for(timeout=60000)
            page.locator("#inspector [data-cs-a=highlight_color]").evaluate(
                "(e) => { e.value = 50; e.dispatchEvent(new Event('change')); }")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["highlight_color"], "#FFD40080")
            page.check("#inspector [data-cs-on=normal_color]")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["normal_color"], "#FFFFFF66")
            page.uncheck("#inspector [data-cs-on=normal_color]")
            self.wait_saved(page)
            self.assertNotIn("normal_color", self.project()["menus"][0])
            # the menu's Photoshop file changes on disk: the viewer offers to import it again
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator(".stage .el.button").first.wait_for(timeout=60000)
            page.locator("#inspector #psd-edit").wait_for()
            page.evaluate("S.psdWatch = {menu: 'main', path: 'media/main.psd', mtime: 1}; watchPsd()")
            page.locator("#psd-changed").wait_for(timeout=15000)
            browser.close()
        self.assertEqual(errors, [])

    def test_thumbnails_chapter_menu_texts_subtitle_look(self):
        """Settings that used to be JSON only: a button's thumbnail, the
        chapter menu's texts, the subtitle look; a button's end-action override."""
        with sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            page.locator(".stage .el.button[data-i='2']").click()          # B -> title:t2
            page.check("#th-on")
            self.wait_saved(page)
            th = self.project()["menus"][0]["buttons"][2]["thumbnail"]
            self.assertEqual(set(th), {"x", "y", "w", "h"})
            page.fill("#inspector [data-th=time]", "2")
            page.locator("#inspector [data-th=time]").dispatch_event("change")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][2]["thumbnail"]["time"], 2)
            page.locator(".stage .thumb-pv img").wait_for()
            self.assertTrue(page.locator("#th-anim").is_disabled())        # still menu
            # end-action override: after title 2, the chapter menu
            page.select_option("#inspector select[data-k=override]", "menu:chapters")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][2]["override"], "menu:chapters")
            self.assertTrue(self.s.app.check(self.project())["valid"])
            # a link transition: a video before the title
            page.select_option("#inspector select[data-k=transition]", "media/sample_b.mp4")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][2]["transition"],
                             "media/sample_b.mp4")
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.select_option("#inspector select[data-k=action]", "menu:main")
            self.wait_saved(page)
            b = self.project()["menus"][0]["buttons"][2]
            self.assertNotIn("thumbnail", b)
            self.assertNotIn("override", b)                     # (only for title / chapter links)
            self.assertEqual(b["transition"], "media/sample_b.mp4")   # (a menu link keeps it)
            page.select_option("#inspector select[data-k=transition]", "__none__")
            self.wait_saved(page)
            self.assertNotIn("transition", self.project()["menus"][0]["buttons"][2])
            # the chapter menu's texts
            page.click(".nav-item[data-view=title][data-id=t1]")
            page.fill("#inspector [data-cm=back_label]", "RETURN")
            page.locator("#inspector [data-cm=back_label]").dispatch_event("change")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["auto_chapter_menu"]["back_label"], "RETURN")
            # a title can end in a chapter, a playlist or play all too
            page.select_option("#inspector select[data-k=end_action]", "chapter:t1:3")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["end_action"], "chapter:t1:3")
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.select_option("#inspector select[data-k=end_action]", "playall")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["end_action"], "playall")
            page.select_option("#inspector select[data-k=end_action]", "lastmenu")   # back where it came from
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["end_action"], "lastmenu")
            # a second audio track: buttons can switch to it along with their link
            page.click("#add-track")
            self.wait_saved(page)
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator(".stage .el.button[data-i='0']").click()
            page.select_option("#inspector select[data-k=audio]", "2")
            self.wait_saved(page)
            self.assertEqual(self.project()["menus"][0]["buttons"][0]["audio"], 2)
            self.assertEqual(page.locator("#inspector select[data-k=subtitle]").count(), 0)  # none
            page.click(".nav-item[data-view=title][data-id=t1]")
            # the subtitle look
            page.click(".nav-item[data-view=disc]")
            page.fill("#inspector input[data-k='subtitle_style.size']", "40")
            page.locator("#inspector input[data-k='subtitle_style.size']").dispatch_event("change")
            self.wait_saved(page)
            page.fill("#inspector input[data-k='subtitle_style.color']", "#ffff00")
            page.locator("#inspector input[data-k='subtitle_style.color']").dispatch_event("change")
            self.wait_saved(page)
            self.assertEqual(self.project()["disc"]["subtitle_style"], {"size": 40, "color": "#FFFF00"})
            self.assertTrue(self.s.app.check(self.project())["valid"])
            self.assertEqual(errors, [])
            browser.close()

    def test_menu_tools(self):
        """Layer visibility, Save menu as template / a menu from it, Create
        chapter index."""
        lib = os.path.join(self.dir, "..", os.path.basename(self.dir) + "-templates")
        self.addCleanup(shutil.rmtree, lib, True)
        with mock.patch.dict(os.environ, {"ONCEMORE_TEMPLATES": lib}), sync_playwright() as p:
            browser = self.launch(p)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, locale="en-US")
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.click(".nav-item[data-view=menu][data-id=main]", timeout=120000)
            page.locator(".stage .el.button").first.wait_for(timeout=60000)
            # the eye in Layers: the button leaves the stage and the disc
            page.locator("#layers .layer-row[data-lk=button][data-li='2'] [data-leye]").click()
            self.wait_saved(page)
            self.assertTrue(self.project()["menus"][0]["buttons"][2]["hidden"])
            self.assertEqual(page.locator(".stage .el.button").count(), 2)
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.locator("#layers .layer-row[data-lk=button][data-li='2'] [data-leye]").click()
            self.wait_saved(page)
            self.assertNotIn("hidden", self.project()["menus"][0]["buttons"][2])
            # save the menu as a template; it appears in the Library and makes a new menu
            page.evaluate("window.oncemoreCommand('save_template')")
            page.fill("#tpl-name", "Blue main")
            page.click("#tpl-ok")
            page.locator("#library [data-utpl=blue_main]").wait_for(timeout=30000)
            self.assertTrue(os.path.isfile(os.path.join(lib, "blue_main", "files", "menu_bg.png")))
            page.keyboard.press("Escape")
            page.click("#library [data-utpl=blue_main]")
            page.locator(".nav-item.active[data-view=menu][data-id=blue_main]").wait_for(timeout=30000)
            self.wait_saved(page)
            made = [m for m in self.project()["menus"] if m["id"] == "blue_main"][0]
            self.assertEqual(made["background"], "media/menu_bg.png")         # the same file: reused
            self.assertEqual(len(made["buttons"]), 3)
            # Menu > Create chapter index for title B: its chapter menu opens
            page.evaluate("window.oncemoreCommand('chapter_index')")
            page.select_option("#ci-title", "t2")
            page.click("#cix-ok")
            self.wait_saved(page)
            self.assertTrue(self.project()["titles"][1]["auto_chapter_menu"])
            page.locator(".nav-item.active[data-view=menu][data-id=chapters_t2]").wait_for(timeout=30000)
            browser.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
