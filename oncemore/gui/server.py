"""`oncemore gui`: a local web app on top of the CLI core.

Python standard library only. The server listens on 127.0.0.1, serves the
single-page app from ./static and a small JSON API. Every API call must carry
the per-launch token (X-Oncemore-Token) and a Host header naming this server,
so other web pages cannot drive it (CSRF / DNS rebinding). Files are only
read or written inside the project directory.

API (all JSON unless noted):
  GET  /api/state                    project JSON, paths, media list, tools
  PUT  /api/project                  save the project; returns validation issues
  POST /api/new                      create a project (empty or sample)
  POST /api/validate                 full check incl. media probe and size plan
  POST /api/upload?name=FILE         raw body -> media/FILE
  GET  /api/probe?path=REL           duration, size, streams of a media file
  GET  /api/frame?path=REL&t=S&w=W   JPEG frame (any codec ffmpeg reads)
  GET  /api/file?path=REL            raw file (backgrounds in the menu editor)
  POST /api/preview                  exact menu render (PNG, data URL) + hit areas
  POST /api/build                    start iso/folder build -> job id
  GET  /api/jobs/ID?since=N          job events (same objects as --json)
  POST /api/reveal                   show a file in Finder / the file manager
"""

import base64
import json
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

from .. import __version__, build, encode, scaffold, tools
from ..errors import OncemoreError, ProjectError
from ..project import PROJECT_FILENAME, build_project, read_json
from ..report import Reporter

MEDIA_EXT = {
    "video": {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".mpg", ".mpeg", ".mts", ".m2ts",
              ".ts", ".webm", ".wmv", ".dv", ".vob", ".mxf"},
    "audio": {".wav", ".aif", ".aiff", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".ac3", ".opus"},
    "image": {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"},
    "subtitle": {".srt"},
    "font": {".ttf", ".otf", ".ttc"},
}
SKIP_DIRS = {"output", ".work", "__pycache__", "node_modules"}


def media_kind(name):
    ext = os.path.splitext(name)[1].lower()
    for kind, exts in MEDIA_EXT.items():
        if ext in exts:
            return kind
    return None


def safe_name(name):
    base = os.path.basename(name.replace("\\", "/"))
    base = re.sub(r"[^\w.\- ()぀-ヿ一-鿿]", "_", base).strip(" .")
    return base or "file"


class JobReporter(Reporter):
    """Collects the same event objects `--json` prints."""

    def __init__(self):
        super().__init__(json_mode=True, verbose=True)
        self.events = []
        self.lock = threading.Lock()

    def _emit(self, obj):
        obj = dict(obj, time=round(time.time(), 3))
        with self.lock:
            self.events.append(obj)


class Job:
    def __init__(self, job_id, kind):
        self.id = job_id
        self.kind = kind
        self.reporter = JobReporter()
        self.done = False
        self.ok = None
        self.thread = None


class App:
    """State shared by request handlers."""

    def __init__(self, project_dir):
        self.dir = os.path.realpath(project_dir)
        self.path = os.path.join(self.dir, PROJECT_FILENAME)
        self.token = secrets.token_urlsafe(18)
        self.port = None
        self.jobs = {}
        self.jobs_lock = threading.Lock()
        self.probe_cache = {}
        self.frame_cache = {}
        self._drawtext = None

    # -- paths -----------------------------------------------------------------
    def resolve(self, rel):
        """Absolute path for a project-relative path; refuses anything outside."""
        if not rel:
            raise ValueError("missing path")
        full = os.path.realpath(os.path.join(self.dir, rel))
        if full != self.dir and not full.startswith(self.dir + os.sep):
            raise PermissionError("path outside the project folder")
        return full

    def rel(self, full):
        return os.path.relpath(full, self.dir).replace(os.sep, "/")

    def media(self):
        out = []
        for root, dirs, files in os.walk(self.dir):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
            if root[len(self.dir):].count(os.sep) > 3:
                dirs[:] = []
            for f in sorted(files):
                kind = media_kind(f)
                if kind:
                    full = os.path.join(root, f)
                    out.append({"path": self.rel(full), "kind": kind,
                                "bytes": os.path.getsize(full)})
        return out

    # -- project -----------------------------------------------------------------
    def load(self):
        if not os.path.isfile(self.path):
            return None
        return read_json(self.path)

    def save(self, data):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, self.path)

    def check(self, data):
        """Schema + reference + file checks, never raises."""
        try:
            p = build_project(data, self.path, check_files=True)
            return {"valid": True, "issues": [], "warnings": p.warnings}
        except ProjectError as e:
            return {"valid": False, "issues": e.issues or [{"path": "", "message": e.message}],
                    "warnings": []}

    def probe(self, full):
        key = (full, os.path.getmtime(full))
        if key not in self.probe_cache:
            info = encode.probe(full)
            info = {k: (str(v) if k in ("sar", "fps") else v) for k, v in info.items()}
            self.probe_cache[key] = info
        return self.probe_cache[key]

    def frame(self, full, t, width):
        key = (full, os.path.getmtime(full), round(t, 2), width)
        if key in self.frame_cache:
            return self.frame_cache[key]
        vf = (f"scale=trunc(iw*sar/2)*2:ih,setsar=1,scale={width}:-2")
        cmd = [tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error",
               "-ss", f"{max(0.0, t):.3f}", "-i", full, "-frames:v", "1", "-vf", vf,
               "-f", "image2", "-c:v", "mjpeg", "-q:v", "4", "pipe:1"]
        p = subprocess.run(cmd, capture_output=True, timeout=60)
        if p.returncode != 0 or not p.stdout:
            raise OncemoreError("cannot read a frame",
                                details={"output": tools.tail(p.stderr.decode("utf-8", "replace"))})
        if len(self.frame_cache) > 400:
            self.frame_cache.clear()
        self.frame_cache[key] = p.stdout
        return p.stdout

    # -- jobs --------------------------------------------------------------------
    def start_build(self, kind, fast):
        with self.jobs_lock:
            if any(not j.done for j in self.jobs.values()):
                raise OncemoreError("a build is already running")
            job = Job(secrets.token_hex(4), kind)
            self.jobs[job.id] = job

        def run():
            rep = job.reporter
            try:
                project = build_project(self.load(), self.path, check_files=True)
                outdir = os.path.join(self.dir, "output")
                if kind == "iso":
                    res = build.build_iso(project, os.path.join(outdir, f"{project.disc.label}.iso"),
                                          rep, fast=fast)
                else:
                    res = build.build(project, os.path.join(outdir, project.disc.label), rep,
                                      fast=fast)
                rep.result(res)
                job.ok = True
            except ProjectError as e:
                rep.error(e.message, e.hint, issues=e.issues)
                job.ok = False
            except OncemoreError as e:
                rep.error(e.message, e.hint, **e.details)
                job.ok = False
            except Exception as e:  # keep the server alive, report the bug
                rep.error(f"internal error: {e}", output=traceback.format_exc())
                job.ok = False
            finally:
                job.done = True

        job.thread = threading.Thread(target=run, daemon=True)
        job.thread.start()
        return job


def static_dir():
    return str(resources.files("oncemore.gui").joinpath("static"))


class Handler(BaseHTTPRequestHandler):
    server_version = f"oncemore/{__version__}"
    app = None  # set by make_server

    def log_message(self, fmt, *args):  # keep the terminal quiet
        if os.environ.get("ONCEMORE_GUI_LOG"):
            super().log_message(fmt, *args)

    # -- plumbing ------------------------------------------------------------------
    def _send(self, status, body, ctype, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def json(self, obj, status=HTTPStatus.OK):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def fail(self, status, message, **extra):
        self.json(dict({"error": message}, **extra), status)

    def body_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def host_ok(self):
        host = (self.headers.get("Host") or "").lower()
        port = self.app.port
        return host in (f"127.0.0.1:{port}", f"localhost:{port}")

    def authorised(self, query=None):
        token = self.headers.get("X-Oncemore-Token", "")
        # <img> cannot send headers: frames and images may carry ?token=
        if not token and query and self.command in ("GET", "HEAD") and \
                self.path.startswith(("/api/frame", "/api/file")):
            token = query.get("token", "")
        return secrets.compare_digest(token, self.app.token)

    def route(self, method):
        if not self.host_ok():
            return self.fail(HTTPStatus.FORBIDDEN, "bad host")
        url = urllib.parse.urlsplit(self.path)
        query = dict(urllib.parse.parse_qsl(url.query))
        if not url.path.startswith("/api/"):
            if method in ("GET", "HEAD"):
                return self.static(url.path)
            return self.fail(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
        if not self.authorised(query):
            return self.fail(HTTPStatus.UNAUTHORIZED, "missing or wrong token")
        name = url.path[len("/api/"):]
        if name.startswith("jobs/"):
            return self.api_job(name[5:], query)
        fn = getattr(self, f"api_{method.lower()}_{name}", None)
        if fn is None:
            return self.fail(HTTPStatus.NOT_FOUND, "no such endpoint")
        try:
            fn(query)
        except PermissionError as e:
            self.fail(HTTPStatus.FORBIDDEN, str(e))
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            self.fail(HTTPStatus.BAD_REQUEST, f"bad request: {e}")
        except FileNotFoundError as e:
            self.fail(HTTPStatus.NOT_FOUND, f"not found: {e.filename or e}")
        except ProjectError as e:
            self.fail(HTTPStatus.UNPROCESSABLE_ENTITY, e.message, issues=e.issues)
        except OncemoreError as e:
            self.fail(HTTPStatus.UNPROCESSABLE_ENTITY, e.message, hint=e.hint, **e.details)

    def do_GET(self):
        self.route("GET")

    def do_HEAD(self):
        self.route("HEAD")

    def do_POST(self):
        self.route("POST")

    def do_PUT(self):
        self.route("PUT")

    def static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        root = os.path.realpath(static_dir())
        full = os.path.realpath(os.path.join(root, path.lstrip("/")))
        if not full.startswith(root + os.sep) or not os.path.isfile(full):
            return self.fail(HTTPStatus.NOT_FOUND, "not found")
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            self._send(HTTPStatus.OK, f.read(), ctype,
                       {"Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:;"
                                                   " style-src 'self' 'unsafe-inline'"})

    # -- endpoints -----------------------------------------------------------------
    def api_get_state(self, q):
        data = self.app.load()
        if self.app._drawtext is None and tools.find("ffmpeg"):
            from ..menu import drawtext_probe
            self.app._drawtext = drawtext_probe()["ok"]
        dr = self.app._drawtext
        self.json({
            "version": __version__, "dir": self.app.dir, "path": self.app.path,
            "project": data, "media": self.app.media(),
            "check": self.app.check(data) if data is not None else None,
            "tools": {"ffmpeg": bool(tools.find("ffmpeg")), "drawtext": dr,
                      "dvdauthor": bool(tools.find("dvdauthor")),
                      "spumux": bool(tools.find("spumux")),
                      "iso": tools.iso_tool()[0], "install": tools.install_hint()},
            "platform": sys.platform,
        })

    def api_put_project(self, q):
        data = self.body_json().get("project")
        if not isinstance(data, dict):
            raise ValueError("project must be an object")
        self.app.save(data)
        self.json({"saved": True, "check": self.app.check(data)})

    def api_post_new(self, q):
        body = self.body_json()
        if os.path.exists(self.app.path) and not body.get("force"):
            raise OncemoreError("a project already exists in this folder")
        standard = body.get("standard", "NTSC")
        aspect = body.get("aspect", "16:9")
        if standard not in ("NTSC", "PAL") or aspect not in ("4:3", "16:9"):
            raise ValueError("bad standard/aspect")
        if body.get("sample"):
            scaffold.init(self.app.dir, standard=standard, aspect=aspect, force=True)
        else:
            os.makedirs(os.path.join(self.app.dir, "media"), exist_ok=True)
            self.app.save({"version": 1,
                           "disc": {"label": body.get("label") or "MY_DISC", "standard": standard,
                                    "aspect": aspect, "target": "DVD5"},
                           "titles": [], "menus": []})
        self.api_get_state(q)

    def api_post_validate(self, q):
        project = build_project(self.app.load(), self.app.path, check_files=True)
        infos, plan = build.inspect(project)
        self.json({"valid": True, "summary": build.summary(project, infos, plan)})

    def api_post_upload(self, q):
        name = safe_name(q.get("name", "upload"))
        if not media_kind(name):
            raise ValueError(f"unsupported file type: {name}")
        target_dir = self.app.resolve("media")
        os.makedirs(target_dir, exist_ok=True)
        stem, ext = os.path.splitext(name)
        dest, n = os.path.join(target_dir, name), 2
        while os.path.exists(dest):
            dest, n = os.path.join(target_dir, f"{stem}-{n}{ext}"), n + 1
        remaining = int(self.headers.get("Content-Length") or 0)
        with open(dest + ".part", "wb") as f:
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 1 << 20))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        if remaining:
            os.remove(dest + ".part")
            raise ValueError("upload interrupted")
        os.replace(dest + ".part", dest)
        self.json({"path": self.app.rel(dest), "kind": media_kind(dest),
                   "media": self.app.media()})

    def api_get_probe(self, q):
        self.json(self.app.probe(self.app.resolve(q.get("path"))))

    def api_get_frame(self, q):
        full = self.app.resolve(q.get("path"))
        width = max(64, min(int(q.get("w", 480)), 1920))
        data = self.app.frame(full, float(q.get("t", 0)), width)
        self._send(HTTPStatus.OK, data, "image/jpeg", {"Cache-Control": "private, max-age=600"})

    def api_get_file(self, q):
        full = self.app.resolve(q.get("path"))
        if media_kind(full) not in ("image", "subtitle"):
            raise PermissionError("only images and subtitles are served")
        with open(full, "rb") as f:
            self._send(HTTPStatus.OK, f.read(),
                       mimetypes.guess_type(full)[0] or "application/octet-stream")

    def api_post_preview(self, q):
        from ..menu import MenuBuilder
        body = self.body_json()
        data = body.get("project") or self.app.load()
        project = build_project(data, self.app.path, check_files=True)
        menu = project.menu(body.get("menu"))
        if menu is None:
            raise ValueError(f"no menu {body.get('menu')!r}")
        tools.require(["ffmpeg", "ffprobe"], need_drawtext=True)
        work = tempfile.mkdtemp(prefix="oncemore-gui-")
        try:
            out = os.path.join(work, "preview.png")
            res = MenuBuilder(project, work).preview(
                menu, out, button=body.get("button"), state=body.get("state", "highlight"),
                outline=bool(body.get("outline")))
            with open(out, "rb") as f:
                res["image"] = "data:image/png;base64," + base64.b64encode(f.read()).decode()
        finally:
            shutil.rmtree(work, ignore_errors=True)
        res.pop("path", None)
        self.json(res)

    def api_post_build(self, q):
        body = self.body_json()
        kind = body.get("kind", "iso")
        if kind not in ("iso", "folder"):
            raise ValueError("kind must be iso or folder")
        job = self.app.start_build(kind, bool(body.get("fast")))
        self.json({"job": job.id})

    def api_job(self, job_id, q):
        job = self.app.jobs.get(job_id)
        if job is None:
            return self.fail(HTTPStatus.NOT_FOUND, "no such job")
        since = int(q.get("since", 0))
        with job.reporter.lock:
            events = job.reporter.events[since:]
            total = len(job.reporter.events)
        self.json({"job": job.id, "kind": job.kind, "done": job.done, "ok": job.ok,
                   "events": events, "next": total})

    def api_post_reveal(self, q):
        full = self.app.resolve(self.body_json().get("path"))
        if not os.path.exists(full):
            raise FileNotFoundError(full)
        if sys.platform == "darwin":
            cmd = ["open", "-R", full]
        elif shutil.which("xdg-open"):
            cmd = ["xdg-open", os.path.dirname(full)]
        else:
            return self.json({"revealed": False, "path": full})
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.json({"revealed": True, "path": full})


def make_server(project_dir, port=0):
    app = App(project_dir)
    handler = type("BoundHandler", (Handler,), {"app": app})
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    app.port = server.server_address[1]
    return server, app


def serve(project_dir, port=0, open_browser=True, reporter=None):
    os.makedirs(project_dir, exist_ok=True)
    server, app = make_server(project_dir, port)
    url = f"http://127.0.0.1:{app.port}/#token={app.token}"
    msg = f"oncemore GUI for {app.dir}\n  {url}\n  (Ctrl+C to quit)"
    if reporter:
        reporter.info(msg)
    else:
        print(msg, flush=True)
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
