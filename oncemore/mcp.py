"""`oncemore mcp`: an MCP server, so AI assistants can author discs.

The Model Context Protocol (https://modelcontextprotocol.io) lets an AI
application (Claude Desktop, Claude Code, ...) call tools a local program
offers. This one offers oncemore's own operations: make a project, read and
change its JSON, bring media in, check it, render a menu, press the remote
on it, build the DVD or Blu-ray (image or folder). Each tool names the
project folder it works on, so no call depends on an earlier one (the
protocol's revision 2026-07-28 is stateless).

Transport: JSON-RPC 2.0 messages, one per line, on stdin / stdout (stdio).
Both protocol eras are served: the current one (2026-07-28: every request
carries its version in _meta, `server/discover`) and the earlier ones that
open with an `initialize` handshake (2024-11-05 to 2025-11-25).

Only folders inside the allowed roots (`--root`, default: the home folder)
are read or written. Python standard library only.
"""

import base64
import copy
import json
import os
import shutil
import sys
import tempfile
import threading
import traceback
import types

from . import __version__
from .errors import OncemoreError, ProjectError
from .project import PROJECT_FILENAME, build_project, read_json
from .report import Reporter

MODERN = ("2026-07-28",)
LEGACY = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
META = "io.modelcontextprotocol/"
SERVER_INFO = {"name": "oncemore", "title": "oncemore disc authoring", "version": __version__}

INSTRUCTIONS = """\
oncemore authors DVD-Video and Blu-ray discs with menus, chapters, playlists and
subtitles from video files. A project is a folder holding project.oncemore.json
and the media it uses (usually in media/). Every tool names the folder.

Typical flow: create_project (or read_project on an existing folder) ->
import_media for the user's videos -> edit the project JSON (write_project or
edit_project; call project_format first for the schema: titles[], menus[] with
buttons whose action is title:<id>, menu:<id>, chapter:<id>:<n>, playall ...)
-> validate -> preview_menu to look at a menu -> simulate to press remote keys
-> build (runs in the background; poll build_status). Times are seconds or
"HH:MM:SS". Menus are laid out on a 720-wide grid (480 high NTSC, 576 PAL).
A project needs at least one title to be valid: add the first title (and its
menu) in one write. Invalid projects are never written; the issues come back."""


class Collector(Reporter):
    """The CLI's reporter, collecting its JSON events instead of printing them
    (nothing may reach stdout but protocol messages)."""

    def __init__(self):
        super().__init__(json_mode=True, verbose=False)
        self.events = []

    def _emit(self, obj):
        self.events.append(obj)


class ToolError(Exception):
    """A tool that could not do what was asked: reported to the model as a
    tool result with isError, so it can correct the call."""


def _obj(props, required=()):
    return {"type": "object", "properties": props, "required": list(required),
            "additionalProperties": False}


FOLDER = {"type": "string", "description": "The project folder (absolute path; ~ is allowed)."}


class Server:
    def __init__(self, roots=None):
        self.roots = [os.path.realpath(os.path.expanduser(r)) for r in (roots or ["~"])]
        self.apps = {}                  # folder -> gui.server.App (its build jobs)
        self.legacy = None              # protocol version an `initialize` chose
        self.out_lock = threading.Lock()
        self.tools = self._tools()

    # -- paths -----------------------------------------------------------------
    def path(self, value, what="folder"):
        if not isinstance(value, str) or not value.strip():
            raise ToolError(f"{what}: give an absolute path")
        p = os.path.expanduser(value.strip())
        if not os.path.isabs(p):
            raise ToolError(f"{what}: {value!r} is not an absolute path")
        p = os.path.realpath(p)
        if not any(p == r or p.startswith(r.rstrip(os.sep) + os.sep) for r in self.roots):
            raise ToolError(f"{what}: {p} is outside the folders this server may use "
                            f"({', '.join(self.roots)}; see `oncemore mcp --root`)")
        return p

    def project_dir(self, args, must_exist=True):
        d = self.path(args.get("folder"))
        if must_exist and not os.path.isfile(os.path.join(d, PROJECT_FILENAME)):
            raise ToolError(f"no project in {d} (create_project makes one)")
        return d

    def app(self, folder):
        from .gui.server import App
        if folder not in self.apps:
            self.apps[folder] = App(folder)
        return self.apps[folder]

    # -- running the CLI's commands ----------------------------------------------
    @staticmethod
    def run_cli(fn, **kw):
        rep = Collector()
        try:
            fn(types.SimpleNamespace(**kw), rep)
        except ProjectError as e:
            raise ToolError(_issues_text(e.message, e.issues))
        except OncemoreError as e:
            raise ToolError(e.message + (f"\n{e.hint}" if e.hint else ""))
        result = next((e for e in reversed(rep.events) if e["event"] == "result"), None)
        if result is None:
            raise ToolError("no result")
        warnings = [e["message"] for e in rep.events
                    if e["event"] == "log" and e.get("level") == "warn"]
        out = {k: v for k, v in result.items() if k not in ("event", "ok")}
        if warnings:
            out["warnings"] = warnings
        return out

    # -- tools -------------------------------------------------------------------
    def _tools(self):
        t = {}

        def tool(name, title, description, schema, readonly=False, destructive=False):
            def deco(fn):
                t[name] = {"name": name, "title": title, "description": description,
                           "inputSchema": schema, "fn": fn,
                           "annotations": {"readOnlyHint": readonly,
                                           "destructiveHint": destructive,
                                           "openWorldHint": False}}
                return fn
            return deco

        @tool("project_format", "Project format",
              "The JSON Schema of project.oncemore.json, with the rules that matter "
              "when writing one. Read this before write_project / edit_project.",
              _obj({}), readonly=True)
        def project_format(args):
            from importlib import resources
            schema = json.loads(resources.files("oncemore").joinpath(
                "project.schema.json").read_text(encoding="utf-8"))
            return {"schema": schema, "notes": INSTRUCTIONS}

        @tool("create_project", "Create a project",
              "Make a new disc project in a folder (created if missing): an empty one, or "
              "the sample disc (two titles, a menu, a chapter menu; needs ffmpeg).",
              _obj({"folder": FOLDER,
                    "label": {"type": "string", "description": "Disc label (A-Z, 0-9, _)."},
                    "standard": {"enum": ["NTSC", "PAL"], "default": "NTSC"},
                    "aspect": {"enum": ["16:9", "4:3"], "default": "16:9"},
                    "sample": {"type": "boolean", "default": False},
                    "overwrite": {"type": "boolean", "default": False,
                                  "description": "Replace a project already in the folder."}},
                   ["folder"]))
        def create_project(args):
            from . import scaffold
            d = self.path(args.get("folder"))
            if os.path.exists(os.path.join(d, PROJECT_FILENAME)) and not args.get("overwrite"):
                raise ToolError(f"{d} already has a project (read_project, or overwrite: true)")
            standard, aspect = args.get("standard", "NTSC"), args.get("aspect", "16:9")
            if args.get("sample"):
                try:
                    scaffold.init(d, standard=standard, aspect=aspect, force=True)
                except OncemoreError as e:
                    raise ToolError(e.message)
            else:
                os.makedirs(os.path.join(d, "media"), exist_ok=True)
                self.save(d, {"version": 1,
                              "disc": {"label": args.get("label") or "MY_DISC",
                                       "standard": standard, "aspect": aspect,
                                       "target": "DVD5"},
                              "titles": [], "menus": []}, check=False)
            return self.read(d)

        @tool("read_project", "Read a project",
              "The project JSON, the media files in its folder, and what is wrong with it "
              "(schema, references, missing files, navigation dead ends).",
              _obj({"folder": FOLDER}, ["folder"]), readonly=True)
        def read_project(args):
            return self.read(self.project_dir(args))

        @tool("write_project", "Write a project",
              "Replace project.oncemore.json with `project`. It is checked first and not "
              "written if it is invalid (the issues are returned). The previous version is "
              "kept in .oncemore-backup.",
              _obj({"folder": FOLDER, "project": {"type": "object"}}, ["folder", "project"]))
        def write_project(args):
            d = self.project_dir(args)
            if not isinstance(args.get("project"), dict):
                raise ToolError("project must be an object")
            self.save(d, args["project"])
            return self.read(d)

        @tool("edit_project", "Edit a project",
              "Change part of the project with a JSON Merge Patch (RFC 7386): objects are "
              "merged, null deletes a key, arrays (titles, menus, buttons ...) are replaced "
              "whole. Checked before it is written.",
              _obj({"folder": FOLDER, "patch": {"type": "object"}}, ["folder", "patch"]))
        def edit_project(args):
            d = self.project_dir(args)
            if not isinstance(args.get("patch"), dict):
                raise ToolError("patch must be an object")
            data = merge_patch(read_json(os.path.join(d, PROJECT_FILENAME)), args["patch"])
            self.save(d, data)
            return self.read(d)

        @tool("import_media", "Import media",
              "Copy video, audio, picture, subtitle, font or Photoshop files into the "
              "project's media/ folder. Returns their project paths (use them in the JSON).",
              _obj({"folder": FOLDER,
                    "files": {"type": "array", "items": {"type": "string"}, "minItems": 1,
                              "description": "Absolute paths of the files to bring in."}},
                   ["folder", "files"]))
        def import_media(args):
            from .gui.server import media_kind, safe_name
            d = self.project_dir(args)
            out = []
            for f in args.get("files") or []:
                src = self.path(f, "file")
                if not os.path.isfile(src):
                    raise ToolError(f"file: {src} not found")
                if not media_kind(src):
                    raise ToolError(f"file: {os.path.basename(src)} is not a kind of file a "
                                    "disc uses (video, audio, picture, subtitles, font, .psd)")
                media = os.path.join(d, "media")
                os.makedirs(media, exist_ok=True)
                if src.startswith(media + os.sep):        # already there
                    out.append(os.path.relpath(src, d).replace(os.sep, "/"))
                    continue
                stem, ext = os.path.splitext(safe_name(os.path.basename(src)))
                dest, n = os.path.join(media, stem + ext), 2
                while os.path.exists(dest):
                    dest, n = os.path.join(media, f"{stem}-{n}{ext}"), n + 1
                shutil.copy2(src, dest)
                out.append(os.path.relpath(dest, d).replace(os.sep, "/"))
            return {"imported": out}

        @tool("validate", "Check a project",
              "Check the project the way a build would: its media probed, the size plan "
              "(bitrate, does it fit the disc), the navigation. media: false only checks the "
              "JSON (fast, no ffprobe).",
              _obj({"folder": FOLDER, "media": {"type": "boolean", "default": True}},
                   ["folder"]), readonly=True)
        def validate(args):
            from .cli import cmd_validate
            d = self.project_dir(args)
            return self.run_cli(cmd_validate, project=d, no_media=not args.get("media", True))

        @tool("preview_menu", "Preview a menu",
              "Render a menu as the TV shows it (PNG), with one button highlighted.",
              _obj({"folder": FOLDER,
                    "menu": {"type": "string", "description": "Menu id (default: the first)."},
                    "button": {"type": "string", "description": "Button id to highlight."},
                    "state": {"enum": ["highlight", "select", "normal"], "default": "highlight"}},
                   ["folder"]), readonly=True)
        def preview_menu(args):
            from .cli import cmd_preview
            d = self.project_dir(args)
            tmp = tempfile.mkdtemp(prefix="oncemore-mcp-")
            try:
                png = os.path.join(tmp, "menu.png")
                res = self.run_cli(cmd_preview, project=d, menu=args.get("menu"),
                                   output=png, button=args.get("button"),
                                   state=args.get("state", "highlight"), outline=False,
                                   keep_work=False)
                with open(png, "rb") as f:
                    data = base64.b64encode(f.read()).decode("ascii")
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            res.pop("path", None)
            return {"_image": data, **res}

        @tool("simulate", "Press the remote",
              "Play the disc in a simulator without building it: start at first play, then "
              "press keys (up, down, left, right, enter, menu, title, next, prev, play, end, "
              "timeout, select:<button id>). Returns where the disc is after each key.",
              _obj({"folder": FOLDER,
                    "keys": {"type": "array", "items": {"type": "string"}, "default": []}},
                   ["folder"]), readonly=True)
        def simulate(args):
            from .cli import cmd_simulate
            d = self.project_dir(args)
            keys = args.get("keys") or []
            if any("," in k for k in keys):
                raise ToolError("keys: one key per item")
            from . import tools as tools_mod
            res = self.run_cli(cmd_simulate, project=d, keys=",".join(keys),
                               simple_layout=not tools_mod.has_drawtext())
            res.pop("state", None)
            return res

        @tool("import_psd", "Menu from Photoshop",
              "Make (or update) a menu from a layered .psd in the project: layer sets named "
              "(+)Name become buttons, (=1) layers their highlights.",
              _obj({"folder": FOLDER, "psd": {"type": "string",
                                              "description": "The .psd, absolute or project path."},
                    "menu": {"type": "string"}, "first_play": {"type": "boolean"}},
                   ["folder", "psd", "menu"]))
        def import_psd(args):
            from .cli import cmd_import_psd
            d = self.project_dir(args)
            psd = args["psd"]
            psd = self.path(psd, "psd") if os.path.isabs(os.path.expanduser(psd)) else \
                self.path(os.path.join(d, psd), "psd")
            return self.run_cli(cmd_import_psd, project=d, psd=psd, menu=args["menu"],
                                first_play=bool(args.get("first_play")))

        @tool("build", "Build the disc",
              "Encode and author the disc in the background (minutes): a DVD or Blu-ray "
              "image (.iso) or folder (VIDEO_TS / BDMV) in <folder>/output. Returns a job "
              "id; follow it with build_status.",
              _obj({"folder": FOLDER, "format": {"enum": ["dvd", "bluray"], "default": "dvd"},
                    "output": {"enum": ["iso", "folder"], "default": "iso"},
                    "fast": {"type": "boolean", "default": False,
                             "description": "1-pass encoding (quicker, a little worse)."}},
                   ["folder"]))
        def build(args):
            d = self.project_dir(args)
            fmt, kind = args.get("format", "dvd"), args.get("output", "iso")
            if fmt not in ("dvd", "bluray") or kind not in ("iso", "folder"):
                raise ToolError("format: dvd | bluray, output: iso | folder")
            try:
                job = self.app(d).start_build(kind, bool(args.get("fast")), fmt=fmt)
            except OncemoreError as e:
                raise ToolError(e.message)
            return {"job": job.id, "folder": d, "output": os.path.join(d, "output")}

        @tool("build_status", "Build progress",
              "Where a build started with build is: its steps, progress, and at the end the "
              "result (the image or folder written) or the error.",
              _obj({"folder": FOLDER, "job": {"type": "string"}}, ["folder", "job"]),
              readonly=True)
        def build_status(args):
            d = self.path(args.get("folder"))
            app = self.apps.get(d)
            job = app.jobs.get(args.get("job")) if app else None
            if job is None:
                raise ToolError("no such build (the server may have restarted: start it again)")
            with job.reporter.lock:
                events = list(job.reporter.events)
            steps = [e["message"] for e in events if e["event"] == "step"]
            progress = next((e for e in reversed(events) if e["event"] == "progress"), None)
            out = {"done": job.done, "ok": job.ok, "steps": steps,
                   "current": steps[-1] if steps else None}
            if progress and not job.done:
                out["progress"] = progress.get("fraction")
            end = next((e for e in reversed(events) if e["event"] in ("result", "error")), None)
            if end:
                out["result" if end["event"] == "result" else "error"] = \
                    {k: v for k, v in end.items() if k not in ("event", "time")}
            out["warnings"] = [e["message"] for e in events
                               if e["event"] == "log" and e.get("level") == "warn"]
            return out

        @tool("doctor", "Check the tools",
              "Which external tools oncemore finds (ffmpeg with drawtext, dvdauthor, spumux) "
              "and how to install what is missing.", _obj({}), readonly=True)
        def doctor(args):
            from .cli import cmd_doctor
            try:
                return self.run_cli(cmd_doctor)
            except ToolError as e:
                return {"ok": False, "problem": str(e)}

        return t

    # -- project helpers -----------------------------------------------------------
    def read(self, d):
        app = self.app(d)
        data = app.load()
        return {"folder": d, "project": data, "media": app.media(),
                "check": app.check(data) if data is not None else None}

    def save(self, d, data, check=True):
        if check:
            try:
                build_project(copy.deepcopy(data), os.path.join(d, PROJECT_FILENAME),
                              check_files=True)
            except ProjectError as e:
                raise ToolError(_issues_text("not written: " + e.message, e.issues))
        self.app(d).save(data)

    # -- protocol ------------------------------------------------------------------
    def tool_list(self):
        return [{k: v for k, v in t.items() if k != "fn"} for t in self.tools.values()]

    def call(self, params):
        name = params.get("name")
        if name not in self.tools:
            raise RpcError(-32602, f"Unknown tool: {name}")
        args = params.get("arguments") or {}
        if not isinstance(args, dict):
            raise RpcError(-32602, "arguments must be an object")
        try:
            out = self.tools[name]["fn"](args)
        except ToolError as e:
            return {"content": [{"type": "text", "text": str(e)}], "isError": True}
        except (OncemoreError, OSError, ValueError) as e:
            return {"content": [{"type": "text", "text": str(e)}], "isError": True}
        content = []
        image = out.pop("_image", None) if isinstance(out, dict) else None
        if image:
            content.append({"type": "image", "data": image, "mimeType": "image/png"})
        content.append({"type": "text", "text": json.dumps(out, ensure_ascii=False, indent=1)})
        return {"content": content, "structuredContent": out, "isError": False}

    def capabilities(self):
        return {"tools": {"listChanged": False}}

    def handle(self, msg):
        """One JSON-RPC message in; the response (or None for a notification)."""
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
            if isinstance(msg, dict) and ("result" in msg or "error" in msg):
                return None                 # (a response: this server sends no requests)
            return _error(msg.get("id") if isinstance(msg, dict) else None, -32600,
                          "Invalid Request")
        method, params, rid = msg["method"], msg.get("params") or {}, msg.get("id")
        if "id" not in msg:
            return None                     # notifications (initialized, cancelled ...)
        try:
            result = self.dispatch(method, params)
        except RpcError as e:
            return _error(rid, e.code, e.message, e.data)
        except Exception as e:              # a bug: answer, stay alive
            traceback.print_exc(file=sys.stderr)
            return _error(rid, -32603, f"Internal error: {e}")
        return {"jsonrpc": "2.0", "id": rid, "result": result}

    def dispatch(self, method, params):
        if not isinstance(params, dict):
            raise RpcError(-32602, "params must be an object")
        if method == "initialize":          # an earlier protocol revision: a session
            asked = params.get("protocolVersion")
            self.legacy = asked if asked in LEGACY else LEGACY[0]
            return {"protocolVersion": self.legacy, "capabilities": self.capabilities(),
                    "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS}
        meta = params.get("_meta") or {}
        version = meta.get(META + "protocolVersion")
        if version is not None:
            if version not in MODERN:
                raise RpcError(-32022, "Unsupported protocol version",
                               {"supported": list(MODERN + LEGACY), "requested": version})
            if META + "clientCapabilities" not in meta:
                raise RpcError(-32602, f"missing _meta {META}clientCapabilities")
        elif self.legacy is None and method != "ping":
            raise RpcError(-32602, f"missing _meta {META}protocolVersion "
                                   f"(supported: {', '.join(MODERN + LEGACY)})")
        modern = version is not None
        if method == "ping":
            result = {}
        elif method == "server/discover":
            result = {"supportedVersions": list(MODERN + LEGACY),
                      "capabilities": self.capabilities(), "instructions": INSTRUCTIONS}
        elif method == "tools/list":
            result = {"tools": self.tool_list()}
        elif method == "tools/call":
            result = self.call(params)
        else:
            raise RpcError(-32601, f"Method not found: {method}")
        if modern:
            result = {"resultType": "complete", **result,
                      "_meta": {META + "serverInfo": SERVER_INFO}}
        return result

    def serve(self, stdin, stdout):
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                reply = _error(None, -32700, "Parse error")
            else:
                reply = self.handle(msg)
            if reply is not None:
                with self.out_lock:
                    stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
                    stdout.flush()


class RpcError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def _error(rid, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": rid, "error": err}


def _issues_text(message, issues):
    lines = [message] + [f"- {i.get('path') or ''}: {i['message']}" for i in issues or []]
    return "\n".join(lines)


def merge_patch(target, patch):
    """RFC 7386 JSON Merge Patch."""
    if not isinstance(patch, dict):
        return copy.deepcopy(patch)
    out = copy.deepcopy(target) if isinstance(target, dict) else {}
    for k, v in patch.items():
        if v is None:
            out.pop(k, None)
        else:
            out[k] = merge_patch(out.get(k), v)
    return out


def serve(roots=None):
    """Run on this process's stdin / stdout. Anything else that would print
    (a library, a stray print) goes to stderr, keeping stdout for the protocol."""
    out = sys.stdout
    sys.stdout = sys.stderr
    stdin = open(sys.stdin.fileno(), encoding="utf-8", closefd=False)
    protocol = open(out.fileno(), "w", encoding="utf-8", closefd=False)
    Server(roots).serve(stdin, protocol)
    return 0
