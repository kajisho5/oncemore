"""`oncemore gui`: JSON API tests (always) and a browser test (Playwright, optional)."""

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.error
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
            # one user menu: nothing to move
            page.click(".nav-item[data-view=menu][data-id=main]")
            page.locator("#inspector [data-move]").first.wait_for()
            self.assertEqual(page.locator("#inspector [data-move]:disabled").count(), 2)
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
            page.click("#btn-undo")
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
            page.click("#btn-build")
            page.check("#fast")
            page.click("#start")
            page.wait_for_selector(".result-ok, .result-err", timeout=300000)
            self.assertEqual(page.locator(".result-ok").count(), 1, page.inner_text("#main"))
            browser.close()
        self.assertEqual(errors, [])
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "output", "DEMO_DISC.iso")))


if __name__ == "__main__":
    unittest.main()
