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
  POST /api/clips                    a title made of clips: lengths + joined preview
  POST /api/routing                  a menu's computed remote-control routing
  POST /api/transcode                encode titles now (job), ahead of the build
  POST /api/encode_status            which titles are already transcoded
  GET  /api/waveform?path=REL&w&h&s  the sound of a file (stream s) as a PNG
  GET  /api/recent                   recently opened project folders
  GET  /api/dirs?path=ABS            the folders in a folder (folder chooser)
  POST /api/switch                   open another project folder (or make one)
  POST /api/save_as                  copy the project folder elsewhere and open it
  POST /api/export                   a frame, a menu or subtitles as a file in exports/
"""

import base64
import dataclasses
import hashlib
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

from .. import (__version__, build, burn, clips, encode, graph, png4, scaffold, simulate, slideshow,
               subtitles, templates, tools, usertemplates)
from ..errors import OncemoreError, ProjectError
from ..project import PROJECT_FILENAME, build_project, clip_starts, read_json, source_at
from ..report import Reporter

MEDIA_EXT = {
    "video": {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".mpg", ".mpeg", ".mts", ".m2ts",
              ".ts", ".webm", ".wmv", ".dv", ".vob", ".mxf"},
    "audio": {".wav", ".aif", ".aiff", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".ac3", ".opus"},
    "image": {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"},
    "subtitle": {".srt", ".vtt", ".ass", ".ssa"},
    "font": {".ttf", ".otf", ".ttc"},
    "design": {".psd", ".psb"},
}
SKIP_DIRS = {"output", "exports", ".work", "__pycache__", "node_modules"}
BACKUP_RE = re.compile(r"^project-\d{8}-\d{6}\.json$")


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


def config_dir():
    """Where oncemore keeps what is not part of a project (the recent
    projects list): ONCEMORE_CONFIG, else the platform's place for it."""
    env = os.environ.get("ONCEMORE_CONFIG")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/oncemore")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "oncemore")


RECENT_KEEP = 10


def recent_projects():
    """File > Open recent: project folders, newest first."""
    try:
        with open(os.path.join(config_dir(), "recent.json"), encoding="utf-8") as f:
            items = json.load(f)
    except (OSError, ValueError):
        return []
    out = []
    for p in items if isinstance(items, list) else []:
        if isinstance(p, str) and os.path.isabs(p) and p not in (x["path"] for x in out):
            out.append({"path": p, "name": os.path.basename(p) or p,
                        "exists": os.path.isfile(os.path.join(p, PROJECT_FILENAME))})
    return out[:RECENT_KEEP]


def note_recent(path):
    items = [path] + [x["path"] for x in recent_projects() if x["path"] != path]
    try:
        os.makedirs(config_dir(), exist_ok=True)
        tmp = os.path.join(config_dir(), "recent.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items[:RECENT_KEEP], f, indent=1, ensure_ascii=False)
        os.replace(tmp, os.path.join(config_dir(), "recent.json"))
    except OSError:
        pass                    # a list that cannot be written never stops opening


# Save as copies the project folder without what can be made again
SAVE_AS_SKIP = {"output", ".work", ".oncemore-cache", ".oncemore-backup", "__pycache__"}
EXPORT_DIR = "exports"


class App:
    """State shared by request handlers."""

    def __init__(self, project_dir):
        self.token = secrets.token_urlsafe(18)
        self.port = None
        self.jobs = {}
        self.jobs_lock = threading.Lock()
        self.open(project_dir)

    def open(self, project_dir):
        """Work on the project in this folder (File > Open project, Save as):
        everything kept about the last one is dropped."""
        self.dir = os.path.realpath(project_dir)
        self.path = os.path.join(self.dir, PROJECT_FILENAME)
        self.probe_cache = {}
        self.frame_cache = {}
        self.proxies = {}          # proxy file -> {"state", "fraction", "error"}
        self.proxy_lock = threading.Lock()
        self._encoders = None
        self._drawtext = None
        self.sim_cache = {}        # menu signature -> layout / images for the simulator
        self.sim_lock = threading.Lock()
        self.clip_lock = threading.Lock()

    def busy(self):
        with self.jobs_lock:
            return any(not j.done for j in self.jobs.values())

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

    BACKUP_DIR = ".oncemore-backup"
    BACKUP_EVERY = 300          # seconds between kept versions
    BACKUP_KEEP = 30

    def backup_dir(self):
        return os.path.join(self.dir, self.BACKUP_DIR)

    def backup(self, force=False):
        """Keep the project file as it is now (the version a save is about to
        replace), at most every BACKUP_EVERY seconds; the newest BACKUP_KEEP
        are kept."""
        if not os.path.isfile(self.path):
            return None
        d = self.backup_dir()
        os.makedirs(d, exist_ok=True)
        names = sorted(n for n in os.listdir(d) if BACKUP_RE.match(n))
        now = time.time()
        if names and not force and now - os.path.getmtime(os.path.join(d, names[-1])) < self.BACKUP_EVERY:
            return None
        name = time.strftime("project-%Y%m%d-%H%M%S.json", time.localtime(now))
        shutil.copy2(self.path, os.path.join(d, name))      # (the same second: replaced)
        os.utime(os.path.join(d, name), (now, now))
        for old in sorted(set(names) | {name})[:-self.BACKUP_KEEP]:
            os.remove(os.path.join(d, old))
        return name

    def backups(self):
        d = self.backup_dir()
        out = []
        for n in sorted((n for n in os.listdir(d) if BACKUP_RE.match(n)), reverse=True) if os.path.isdir(d) else []:
            full = os.path.join(d, n)
            try:
                with open(full, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            out.append({"name": n, "time": os.path.getmtime(full), "bytes": os.path.getsize(full),
                        "label": (data.get("disc") or {}).get("label"),
                        "titles": len(data.get("titles") or []), "menus": len(data.get("menus") or [])})
        return out

    def save(self, data):
        try:
            self.backup()
        except OSError:
            pass                    # a backup that cannot be written never stops a save
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp, self.path)

    def check(self, data):
        """Schema + reference + file checks, never raises."""
        try:
            p = build_project(data, self.path, check_files=True)
            nav = graph.check(p)
            return {"valid": True, "issues": [], "navigation": nav,
                    "warnings": p.warnings + [f"{n['path']}: {n['message']}" for n in nav
                                              if n["level"] == "warning"]}
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

    def waveform(self, full, w, h, stream=0):
        key = ("wave", full, os.path.getmtime(full), w, h, stream)
        if key in self.frame_cache:
            return self.frame_cache[key]
        cmd = [tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error", "-i", full,
               "-filter_complex",
               f"[0:a:{stream}]aformat=channel_layouts=mono,showwavespic=s={w}x{h}:colors=white:"
               "scale=sqrt,format=rgba", "-frames:v", "1", "-f", "image2", "-c:v", "png", "pipe:1"]
        p = subprocess.run(cmd, capture_output=True, timeout=300)
        if p.returncode != 0 or not p.stdout:
            raise OncemoreError("no sound to draw",
                                details={"output": tools.tail(p.stderr.decode("utf-8", "replace"))})
        if len(self.frame_cache) > 400:
            self.frame_cache.clear()
        self.frame_cache[key] = p.stdout
        return p.stdout

    # -- playback proxies ----------------------------------------------------------
    # Titles can be any format ffmpeg reads; the page plays a small copy cached
    # in .oncemore-cache/proxy: H.264/AAC MP4 (Safari/WKWebView, Chrome), or
    # VP8/Opus WebM for browsers without H.264 (Firefox, Chromium builds).
    PROXY_HEIGHT = 360
    PROXY_FORMATS = {"mp4": "video/mp4", "webm": "video/webm"}

    def encoders(self):
        if self._encoders is None:
            p = subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-encoders"],
                               capture_output=True, text=True)
            self._encoders = {line.split()[1] for line in p.stdout.splitlines()
                              if len(line.split()) > 1 and line[:2] in (" V", " A")}
        return self._encoders

    def proxy_codecs(self, fmt):
        have = self.encoders()
        if fmt == "mp4":
            if "libx264" in have:
                v = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26"]
            elif "h264_videotoolbox" in have:
                v = ["-c:v", "h264_videotoolbox", "-b:v", "1500k"]
            else:
                raise OncemoreError("this ffmpeg has no H.264 encoder (libx264) for previews")
            return v + ["-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart"]
        if "libvpx" not in have:
            raise OncemoreError("this ffmpeg has no VP8 encoder (libvpx) for previews")
        a = ["-c:a", "libopus", "-b:a", "96k"] if "libopus" in have else \
            ["-c:a", "libvorbis", "-q:a", "3"]
        return ["-c:v", "libvpx", "-deadline", "realtime", "-cpu-used", "8",
                "-b:v", "1200k", "-pix_fmt", "yuv420p"] + a

    def proxy_path(self, full, fmt):
        key = f"{full}\0{os.path.getmtime(full)}\0{os.path.getsize(full)}\0{self.PROXY_HEIGHT}"
        name = hashlib.sha256(key.encode("utf-8", "surrogateescape")).hexdigest()[:24]
        return os.path.join(self.dir, ".oncemore-cache", "proxy", f"{name}.{fmt}")

    def proxy_status(self, full, fmt="mp4", start=False):
        if fmt not in self.PROXY_FORMATS:
            raise ValueError(f"unknown preview format {fmt!r}")
        out = self.proxy_path(full, fmt)
        with self.proxy_lock:
            st = self.proxies.get(out)
            if st is None and os.path.isfile(out):
                st = self.proxies[out] = {"state": "ready", "fraction": 1.0}
            if start and (st is None or st["state"] == "error"):
                st = self.proxies[out] = {"state": "running", "fraction": 0.0}
                threading.Thread(target=self._make_proxy, args=(full, fmt, out, st),
                                 daemon=True).start()
        return dict(st or {"state": "none", "fraction": 0.0}), out

    def _make_proxy(self, full, fmt, out, st):
        try:
            codecs = self.proxy_codecs(fmt)
            info = self.probe(full)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            tmp = f"{out}.part"
            args = ["-i", full, "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn",
                    "-vf", f"scale=trunc(iw*sar/2)*2:ih,setsar=1,"
                           f"scale=-2:'min({self.PROXY_HEIGHT},ih)':flags=bicubic",
                    "-ac", "2"] + codecs + ["-f", fmt, tmp]
            encode.run_ffmpeg(args, info.get("duration"),
                              os.path.join(os.path.dirname(out), "last.log"),
                              lambda f: st.update(fraction=round(f, 3)),
                              what="ffmpeg (preview)")
            os.replace(tmp, out)
            st.update(state="ready", fraction=1.0)
        except OncemoreError as e:
            st.update(state="error", error=e.message)
        except Exception as e:  # keep the server alive
            st.update(state="error", error=f"internal error: {e}")

    # -- jobs --------------------------------------------------------------------
    def start_build(self, kind, fast, cache=True, device=None, fmt="dvd"):
        def work(project, rep):
            outdir = os.path.join(self.dir, "output")
            if fmt == "bluray" and kind == "folder":
                return build.build_bluray(project, os.path.join(outdir, f"{project.disc.label}_BD"),
                                          rep, fast=fast, cache=cache)
            if fmt == "bluray":
                res = build.build_bluray_iso(
                    project, os.path.join(outdir, f"{project.disc.label}_BD.iso"), rep,
                    fast=fast, cache=cache)
                if kind == "disc":
                    res.update(burn.burn(res["iso"], rep, device=device,
                                         log=os.path.join(outdir, "burn.log")))
                return res
            if kind in ("iso", "disc"):
                res = build.build_iso(project, os.path.join(outdir, f"{project.disc.label}.iso"),
                                      rep, fast=fast, cache=cache)
                if kind == "disc":
                    res.update(burn.burn(res["iso"], rep, device=device,
                                         log=os.path.join(outdir, "burn.log")))
                return res
            return build.build(project, os.path.join(outdir, project.disc.label), rep,
                               fast=fast, cache=cache)
        return self.start_job(kind, work)

    def start_transcode(self, titles, fast):
        return self.start_job("transcode",
                              lambda project, rep: build.transcode(project, rep, titles, fast))

    def start_job(self, kind, work):
        """Run work(project, reporter) in the background; one job at a time."""
        with self.jobs_lock:
            if any(not j.done for j in self.jobs.values()):
                raise OncemoreError("a build is already running")
            job = Job(secrets.token_hex(4), kind)
            self.jobs[job.id] = job

        def run():
            rep = job.reporter
            try:
                project = build_project(self.load(), self.path, check_files=True)
                res = work(project, rep)
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
        try:
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
        except (BrokenPipeError, ConnectionResetError):
            pass                     # the page no longer wanted it (e.g. a timeline redrawn)

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
                self.path.startswith(("/api/frame?", "/api/file?", "/api/proxy?",
                                      "/api/waveform?")):
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

    # -- subtitle editor -----------------------------------------------------------
    def _subtitle_path(self, q, must_exist=True):
        full = self.app.resolve(q.get("path"))
        if media_kind(full) != "subtitle":
            raise PermissionError("not a subtitle file")
        if must_exist and not os.path.isfile(full):
            raise FileNotFoundError(full)
        return full

    def api_get_subtitles(self, q):
        full = self._subtitle_path(q)
        cues = subtitles.load_subtitles(full)
        self.json({"editable": full.lower().endswith(".srt"),
                   "cues": [{"start": c.start, "end": c.end, "text": "\n".join(c.lines),
                             "position": c.position, "color": c.color} for c in cues]})

    def api_put_subtitles(self, q):
        """Save cues as SubRip (the editor only writes .srt files)."""
        full = self._subtitle_path(q, must_exist=False)
        if not full.lower().endswith(".srt"):
            raise ValueError("only .srt files are written; save as a new .srt")
        cues = []
        for c in self.body_json().get("cues", []):
            lines = [l for l in str(c.get("text", "")).split("\n") if l.strip()]
            start, end = float(c["start"]), float(c["end"])
            if lines and end > start >= 0:
                cues.append(subtitles.Cue(start, end, lines, c.get("position") or None,
                                          c.get("color") or None))
        cues.sort(key=lambda c: c.start)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        tmp = full + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(subtitles.to_srt(cues))
        os.replace(tmp, full)
        self.json({"saved": True, "cues": len(cues), "media": self.app.media()})

    # -- slideshows --------------------------------------------------------------
    def api_post_slideshow(self, q):
        """Render (or reuse) a slideshow title so the page can play it."""
        body = self.body_json()
        project = build_project(body.get("project") or self.app.load(), self.app.path,
                                check_files=True)
        t = project.title(body["title"])
        if t is None or not t.slideshow:
            raise ValueError("not a slideshow title")
        slideshow.apply(t, project.disc_for(t), encode.probe)      # (fitted to its music)
        slideshow.ensure(t, project.disc_for(t),
                         os.path.join(os.path.dirname(t.source), f"{t.id}.log"))
        self.json({"path": self.app.rel(t.source), "duration": t.slideshow.duration,
                   "starts": t.slideshow.starts(),
                   "durations": [s.duration for s in t.slideshow.slides]})

    def api_post_clips(self, q):
        """A title made of clips: their lengths and where each starts, and the
        joined preview (rendered once, then cached) the page shows and plays."""
        body = self.body_json()
        project = self._project_from(body, check_files=True)
        t = project.title(body["title"])
        if t is None or not t.clips:
            raise ValueError("not a title made of clips")
        disc = project.disc_for(t)
        total = clips.resolve(t, disc, encode.probe)
        if total <= 0:
            raise ValueError("the clips are empty")
        out = clips.preview_path(self.app.dir, t, disc)
        with self.app.clip_lock:
            if not os.path.isfile(out):
                clips.render_preview(t, disc, out, out + ".log")
        starts = clip_starts(t)
        self.json({"path": self.app.rel(out), "duration": round(total, 6), "starts": starts,
                   "clips": [{"source": self.app.rel(c.source), "in": c.start,
                              "duration": round(c.duration, 6), "start": s}
                             for c, s in zip(t.clips, starts)]})

    # -- flowchart, project check and the disc simulator --------------------------
    def _project_from(self, body, check_files=False):
        return build_project(body.get("project") or self.app.load(), self.app.path,
                             check_files=check_files)

    def api_post_graph(self, q):
        project = self._project_from(self.body_json())
        try:
            clips.apply_all(project, encode.probe)       # chapters of titles made of clips
        except OncemoreError:
            pass
        g = graph.build(project)
        seen = graph.reachable(g)
        # (unused elements go to the bottom of the flowchart)
        unused = [n["id"] for n in g["nodes"] if n["kind"] in ("menu", "title", "playlist")
                  and n["id"] not in seen]
        self.json({"graph": g, "notes": graph.check(project), "unused": unused})

    def _sim_menu(self, project, menu, images=False):
        """Layout (and with `images`, the picture without highlights plus one
        highlight overlay per button) of a menu, cached by its definition."""
        from ..menu import MenuBuilder
        key = json.dumps([dataclasses.asdict(menu), project.disc.standard, project.disc.aspect,
                          {t.id: [t.source, t.chapters, t.aspect,
                                 [[c.source, c.start, c.end] for c in t.clips]]
                          for t in project.titles}],
                         sort_keys=True, default=str)
        with self.app.sim_lock:
            hit = self.app.sim_cache.get(key)
        if hit and (hit.get("image") or not images):
            return hit
        tools.require(["ffmpeg", "ffprobe"], need_drawtext=True)
        work = tempfile.mkdtemp(prefix="oncemore-sim-")
        try:
            mb = MenuBuilder(project, work)
            overlaps = []
            geoms = mb.layout(menu, overlaps)
            out = {"buttons": [{"id": g.id, "rect": list(g.rect), "nav": g.nav, "auto": g.auto,
                                "action": g.action} for g in geoms],
                   "overlaps": overlaps,
                   "size": [mb.dw, project.disc.height],
                   "storage": [project.disc.width, project.disc.height]}
            if images:
                png = os.path.join(work, "normal.png")
                if geoms:
                    mb.preview(menu, png, state="none")     # the buttons are in the overlays
                else:
                    tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y",
                               "-i", mb.render_base(menu), "-vf",
                               f"scale={mb.dw}:{project.disc.height},setsar=1",
                               "-frames:v", "1", png], what="ffmpeg (preview)")
                with open(png, "rb") as f:
                    out["image"] = "data:image/png;base64," + base64.b64encode(f.read()).decode()
                # one picture per selected button: that button highlighted, the
                # others in the menu's normal colour (if it has one)
                palette = mb.state_palette(menu, menu.highlight_color)
                out["overlays"] = {}
                for g in geoms:
                    data = png4.encode_indexed_png(mb.state_canvas(menu, geoms, "highlight", g.id),
                                                   palette)
                    out["overlays"][g.id] = ("data:image/png;base64," +
                                             base64.b64encode(data).decode())
        finally:
            shutil.rmtree(work, ignore_errors=True)
        with self.app.sim_lock:
            if len(self.app.sim_cache) > 64:
                self.app.sim_cache.clear()
            self.app.sim_cache[key] = out
        return out

    def api_post_sim(self, q):
        """One remote-control key: {project?, state?, key?} -> the new state
        and what the screen shows (no state: insert the disc)."""
        body = self.body_json()
        project = self._project_from(body)
        layouts = {m.id: self._sim_menu(project, m)["buttons"] for m in project.menus}
        clips.apply_all(project, encode.probe)
        sim = simulate.Simulator(project, layouts)
        state = body.get("state")
        if not state:
            state = sim.start()
            if body.get("from_menu"):            # preview from the menu being edited
                state["log"] = []
                sim.enter_menu(state, body["from_menu"])
        elif body.get("key"):
            try:
                sim.press(state, body["key"])
            except (simulate.SimError, KeyError, IndexError) as e:
                raise ValueError(str(e))
        out = {"state": state, "view": list(sim.view(state))}
        if state["domain"] == "title":
            t = project.title(state["title"])
            # a picture from the chapter: the file playing then, and where in it
            k = state["chapter"]
            at = (t.chapters[k - 1] if 0 < k <= len(t.chapters) else 0.0) + 0.5
            path, at = source_at(t, at)
            out["title"] = {"id": t.id, "name": t.name, "source": self.app.rel(t.source),
                            "chapters": t.chapters, "chapter": k, "names": t.chapter_names,
                            "frame": {"path": self.app.rel(path), "t": round(at, 3)}}
        self.json(out)

    def api_post_routing(self, q):
        """Where the remote's arrow keys go from each button of a menu (the
        computed routing, as the disc will have it), for the stage overlay."""
        body = self.body_json()
        project = self._project_from(body)
        menu = project.menu(body.get("menu"))
        if menu is None:
            raise ValueError(f"no menu {body.get('menu')!r}")
        lay = self._sim_menu(project, menu)
        self.json({"buttons": lay["buttons"], "storage": lay["storage"],
                   "manual": {b.id: sorted((b.nav or {}).keys()) for b in menu.buttons}})

    def api_post_sim_menu(self, q):
        body = self.body_json()
        project = self._project_from(body)
        menu = project.menu(body.get("menu"))
        if menu is None:
            raise ValueError(f"no menu {body.get('menu')!r}")
        self.json(self._sim_menu(project, menu, images=True))

    def api_post_import_psd(self, q):
        """A menu from a layered Photoshop file in the project (not saved:
        the page adds it to the project, so it can be undone)."""
        from .. import psdmenu
        body = self.body_json()
        full = self.app.resolve(body.get("path"))
        if media_kind(full) != "design":
            raise PermissionError("not a Photoshop file")
        if not os.path.isfile(full):
            raise FileNotFoundError(full)
        mid = body.get("menu") or ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", mid):
            raise ValueError("bad menu id")
        data = body.get("project") or self.app.load()
        menu, notes = psdmenu.import_psd(full, data, mid,
                                         os.path.join(self.app.dir, "media", "psd"), self.app.dir)
        self.json({"menu": menu, "notes": notes, "media": self.app.media()})

    def api_get_templates(self, q):
        self.json({"templates": [{"id": k, **v} for k, v in templates.TEMPLATES.items()]})

    def api_post_template(self, q):
        """A new menu from a template, for the project the page is editing."""
        body = self.body_json()
        project = body.get("project") or self.app.load()
        menu = templates.make_menu(body["template"], project, body["id"], back=body.get("back"))
        self.json({"menu": menu})

    # -- menus saved as templates (Menu > Save menu as template) -----------------
    def api_get_user_templates(self, q):
        self.json({"templates": usertemplates.list_templates(), "folder": usertemplates.library()})

    def api_post_save_template(self, q):
        body = self.body_json()
        tid = usertemplates.save(body.get("menu"), body.get("name"), self.app.dir)
        self.json({"id": tid, "templates": usertemplates.list_templates()})

    def api_post_apply_template(self, q):
        body = self.body_json()
        project = body.get("project") or self.app.load() or {}
        menu = usertemplates.apply(body.get("template"), project, self.app.dir, body["id"])
        self.json({"menu": menu, "media": self.app.media()})

    def api_post_delete_template(self, q):
        usertemplates.delete(self.body_json().get("template"))
        self.json({"templates": usertemplates.list_templates()})

    def api_post_proxy(self, q):
        full = self.app.resolve(q.get("path"))
        if media_kind(full) != "video":
            raise PermissionError("only videos have previews")
        self.json(self.app.proxy_status(full, q.get("format", "mp4"), start=True)[0])

    def api_get_proxy(self, q):
        """The finished preview, with byte ranges (WebKit requires them)."""
        fmt = q.get("format", "mp4")
        st, out = self.app.proxy_status(self.app.resolve(q.get("path")), fmt)
        ctype = self.app.PROXY_FORMATS[fmt]
        if st["state"] != "ready":
            raise FileNotFoundError(out)
        size = os.path.getsize(out)
        start, end = 0, size - 1
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
        partial = bool(m and (m.group(1) or m.group(2)))
        if partial:
            if m.group(1):
                start = int(m.group(1))
                end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
            else:                                  # bytes=-N: the last N bytes
                start = max(0, size - int(m.group(2)))
            if start > end or start >= size:
                return self._send(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE, b"",
                                  ctype, {"Content-Range": f"bytes */{size}"})
        length = end - start + 1
        self.send_response(HTTPStatus.PARTIAL_CONTENT if partial else HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if partial:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        if self.command == "HEAD":
            return
        with open(out, "rb") as f:
            f.seek(start)
            left = length
            try:
                while left > 0:
                    chunk = f.read(min(left, 1 << 16))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass                               # the player dropped this range

    def api_get_file(self, q):
        full = self.app.resolve(q.get("path"))
        if media_kind(full) not in ("image", "subtitle", "font"):
            raise PermissionError("only images, subtitles and fonts are served")
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
                outline=bool(body.get("outline")), every=bool(body.get("every")))
            with open(out, "rb") as f:
                res["image"] = "data:image/png;base64," + base64.b64encode(f.read()).decode()
        finally:
            shutil.rmtree(work, ignore_errors=True)
        res.pop("path", None)
        self.json(res)

    def api_post_build(self, q):
        body = self.body_json()
        kind = body.get("kind", "iso")
        if kind not in ("iso", "folder", "disc"):
            raise ValueError("kind must be iso, folder or disc")
        fmt = body.get("format", "dvd")
        if fmt not in ("dvd", "bluray"):
            raise ValueError("format must be dvd or bluray")
        device = body.get("device") or None
        if device is not None and not isinstance(device, str):
            raise ValueError("device must be a string")
        job = self.app.start_build(kind, bool(body.get("fast")), cache=not body.get("no_cache"),
                                   device=device, fmt=fmt)
        self.json({"job": job.id})

    def api_post_transcode(self, q):
        """Encode titles now (all, or `titles`), ahead of the build."""
        body = self.body_json()
        titles = body.get("titles")
        if titles is not None and not (isinstance(titles, list) and
                                       all(isinstance(x, str) for x in titles)):
            raise ValueError("titles must be a list of title ids")
        job = self.app.start_transcode(titles, bool(body.get("fast")))
        self.json({"job": job.id})

    def api_post_encode_status(self, q):
        """Which titles are already transcoded (in the encode cache)."""
        body = self.body_json()
        project = self._project_from(body, check_files=True)
        self.json({"titles": build.encode_status(project, bool(body.get("fast")))})

    def api_get_waveform(self, q):
        """The sound of a file drawn as a picture (PNG), for the timeline."""
        full = self.app.resolve(q.get("path"))
        if media_kind(full) not in ("video", "audio"):
            raise PermissionError("only videos and sound files have a waveform")
        w = max(64, min(int(q.get("w", 800)), 4000))
        h = max(16, min(int(q.get("h", 40)), 200))
        stream = max(0, min(int(q.get("s", 0)), 31))
        self._send(HTTPStatus.OK, self.app.waveform(full, w, h, stream), "image/png",
                   {"Cache-Control": "private, max-age=600"})

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


    def api_get_backups(self, q):
        """Earlier versions of the project file (newest first)."""
        self.json({"backups": self.app.backups(), "every": self.app.BACKUP_EVERY})

    def api_get_backup(self, q):
        name = q.get("name", "")
        if not BACKUP_RE.match(name):
            raise ValueError("bad backup name")
        self.json({"project": read_json(os.path.join(self.app.backup_dir(), name))})

    def api_post_open(self, q):
        """Open a project file in the program the system uses for it (Edit
        Menu in Photoshop opens the menu's .psd)."""
        full = self.app.resolve(self.body_json().get("path"))
        if not os.path.isfile(full):
            raise FileNotFoundError(full)
        if sys.platform == "darwin":
            cmd = ["open", full]
        elif sys.platform.startswith("win"):
            os.startfile(full)          # noqa: (Windows only)
            return self.json({"opened": True, "path": full})
        elif shutil.which("xdg-open"):
            cmd = ["xdg-open", full]
        else:
            return self.json({"opened": False, "path": full})
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.json({"opened": True, "path": full})

    def api_get_stat(self, q):
        """When a project file last changed (null if it is not there)."""
        full = self.app.resolve(q.get("path"))
        try:
            st = os.stat(full)
        except OSError:
            return self.json({"exists": False, "mtime": None, "bytes": None})
        self.json({"exists": True, "mtime": st.st_mtime, "bytes": st.st_size})

    # -- projects: open, recent, save as ------------------------------------------
    def api_get_recent(self, q):
        self.json({"recent": recent_projects(), "current": self.app.dir})

    def _folder_arg(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("missing folder")
        path = os.path.expanduser(value.strip())
        if not os.path.isabs(path):
            raise ValueError("give the folder's full path")
        return os.path.realpath(path)

    def api_get_dirs(self, q):
        """The folders in a folder (the page's folder chooser)."""
        path = self._folder_arg(q.get("path") or os.path.dirname(self.app.dir))
        if not os.path.isdir(path):
            raise FileNotFoundError(path)
        dirs = []
        try:
            names = sorted(os.listdir(path), key=str.lower)
        except PermissionError:
            names = []
        for n in names:
            full = os.path.join(path, n)
            if n.startswith(".") or not os.path.isdir(full):
                continue
            dirs.append({"name": n, "project": os.path.isfile(os.path.join(full, PROJECT_FILENAME))})
            if len(dirs) >= 500:
                break
        parent = os.path.dirname(path)
        self.json({"path": path, "parent": parent if parent != path else None, "dirs": dirs,
                   "project": os.path.isfile(os.path.join(path, PROJECT_FILENAME)),
                   "home": os.path.expanduser("~")})

    def api_post_switch(self, q):
        """File > Open project / New project / Open recent: work on another
        project folder (made when `create` is set)."""
        body = self.body_json()
        path = self._folder_arg(body.get("path"))
        if self.app.busy():
            raise OncemoreError("wait for the build or transcode to finish first")
        if not os.path.isdir(path):
            if not body.get("create"):
                raise FileNotFoundError(path)
            os.makedirs(path)
        self.app.open(path)
        note_recent(self.app.dir)
        self.api_get_state(q)

    def api_post_save_as(self, q):
        """File > Save as: the project folder (the project and its media, not
        what the build makes again) copied to a new folder, which is then the
        one being worked on."""
        body = self.body_json()
        dest = self._folder_arg(body.get("path"))
        if self.app.busy():
            raise OncemoreError("wait for the build or transcode to finish first")
        if dest == self.app.dir or dest.startswith(self.app.dir + os.sep):
            raise ValueError("choose a folder outside this project")
        if os.path.exists(dest) and (not os.path.isdir(dest) or os.listdir(dest)):
            raise OncemoreError(f"{dest} already exists and is not empty")
        src = self.app.dir
        skip = lambda d, names: [n for n in names if d == src and n in SAVE_AS_SKIP]  # noqa: E731
        shutil.copytree(src, dest, ignore=skip, symlinks=True, dirs_exist_ok=True)
        self.app.open(dest)
        if isinstance(body.get("project"), dict):      # the project as it is in the page
            self.app.save(body["project"])
        note_recent(self.app.dir)
        self.api_get_state(q)

    # -- exports: frames, menus and subtitles as files -----------------------------
    def _export_path(self, name):
        d = os.path.join(self.app.dir, EXPORT_DIR)
        os.makedirs(d, exist_ok=True)
        stem, ext = os.path.splitext(safe_name(name))
        full, n = os.path.join(d, stem + ext), 2
        while os.path.exists(full):
            full, n = os.path.join(d, f"{stem}-{n}{ext}"), n + 1
        return full

    def api_post_export(self, q):
        """Timeline > Save frame as file, Menu > Save menu as file, Timeline >
        Export subtitles: written to exports/ in the project folder."""
        body = self.body_json()
        kind = body.get("kind")
        if kind == "frame":
            src = self.app.resolve(body.get("path"))
            t = max(0.0, float(body.get("t", 0)))
            tools.require(["ffmpeg"])
            stamp = f"{int(t // 3600):02d}-{int(t % 3600 // 60):02d}-{t % 60:06.3f}".replace(".", "_")
            out = self._export_path(f"{os.path.splitext(os.path.basename(src))[0]}-{stamp}.png")
            tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-ss", f"{t:.3f}",
                       "-i", src, "-frames:v", "1", "-vf", "scale=trunc(iw*sar/2)*2:ih,setsar=1",
                       "-update", "1", out], what="ffmpeg (frame)")
        elif kind == "menu":
            from ..menu import MenuBuilder
            project = build_project(body.get("project") or self.app.load(), self.app.path,
                                    check_files=True)
            menu = project.menu(body.get("menu"))
            if menu is None:
                raise ValueError(f"no menu {body.get('menu')!r}")
            state = body.get("state", "highlight")
            if state not in ("normal", "highlight", "select"):
                raise ValueError("bad state")
            tools.require(["ffmpeg", "ffprobe"], need_drawtext=True)
            out = self._export_path(f"{menu.id}.png")
            work = tempfile.mkdtemp(prefix="oncemore-gui-")
            try:
                MenuBuilder(project, work).preview(menu, out, button=menu.default_button,
                                                   state=state)
            finally:
                shutil.rmtree(work, ignore_errors=True)
        elif kind == "subtitles":
            src = self._subtitle_path({"path": body.get("path")})
            cues = subtitles.load_subtitles(src)
            out = self._export_path(os.path.splitext(os.path.basename(src))[0] + ".srt")
            with open(out, "w", encoding="utf-8") as f:
                f.write(subtitles.to_srt(cues))
        else:
            raise ValueError("kind must be frame, menu or subtitles")
        self.json({"path": self.app.rel(out), "media": self.app.media()})


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
    note_recent(app.dir)
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
