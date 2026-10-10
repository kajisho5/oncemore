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
                if v not in ("--c-picture", "--c-on-picture", "--c-guide", "--c-hit")}
        self.assertEqual(need - set(re.findall(r"(--c-[\w-]+)\s*:", light)), set())

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
        # Oncemore.app has a real menu bar: the page hides its own and its
        # menu items call window.oncemoreCommand
        with sync_playwright() as p:
            browser = self.launch(p)
            ctx = browser.new_context(viewport={"width": 1400, "height": 900}, locale="en-US",
                                      bypass_csp=True,
                                      user_agent="Mozilla/5.0 (Macintosh) AppleWebKit OncemoreApp")
            page = ctx.new_page()
            page.goto(f"{self.s.base}/#token={self.s.app.token}")
            page.click("#np-sample")
            page.locator(".nav-item[data-view=title]").first.wait_for(timeout=120000)
            self.assertTrue(page.locator("#menubar").is_hidden())
            page.evaluate("window.oncemoreCommand('ws_flow')")
            page.locator("#center-head", has_text="Flowchart").wait_for()
            page.evaluate("window.oncemoreCommand('new_slideshow')")
            self.wait_saved(page)
            self.assertTrue(any("slideshow" in t for t in self.project()["titles"]))
            browser.close()
        swift = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "macos", "Oncemore", "main.swift"), encoding="utf-8").read()
        js = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "oncemore", "gui", "static", "app.js"), encoding="utf-8").read()
        for cid in re.findall(r'cmd\("[^"]+", "(\w+)"', swift):
            self.assertRegex(js, rf"[\n ] *{cid}: [{{a]", cid)  # every native item has a command
        self.assertIn('applicationNameForUserAgent = "OncemoreApp"', swift)

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
            # film with 3:2 pulldown, then back to automatic
            page.select_option("#inspector select[data-k=scan]", "pulldown")
            self.wait_saved(page)
            self.assertEqual(self.project()["titles"][0]["scan"], "pulldown")
            page.select_option("#inspector select[data-k=scan]", "__none__")
            self.wait_saved(page)
            self.assertNotIn("scan", self.project()["titles"][0])
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
            # first clip moved down, then removed: an ordinary title again
            page.click("tr[data-clip='0'] [data-cmv='1']")
            self.poll(lambda: self.project()["titles"][1]["clips"][0]["source"] ==
                      "media/sample_a.mp4")
            page.click("tr[data-clip='1'] [data-crm]")
            self.poll(lambda: len(self.project()["titles"][1]["clips"]) == 1)
            page.locator("tr[data-clip='1']").wait_for(state="detached")
            page.fill("tr[data-clip='0'] [data-cf=in]", "")
            page.press("tr[data-clip='0'] [data-cf=in]", "Enter")
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
            sh = self.project()["titles"][-1]["slideshow"]
            self.assertEqual(sh, {"slides": [{"image": "media/menu_bg.png", "duration": 3},
                                             {"image": "media/menu_bg.png"}],
                                  "pan_zoom": True, "transition": "none"})
            self.assertTrue(self.s.app.check(self.project())["valid"])
            page.click("#ss-play")
            page.locator("#player:not([hidden])").wait_for(timeout=180000)
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
            page.evaluate("window.oncemoreCommand('win_project')")
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


if __name__ == "__main__":
    unittest.main()
