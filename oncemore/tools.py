"""External program discovery, `doctor`, and a subprocess runner.

oncemore never links against media libraries; it drives these programs:

  ffmpeg / ffprobe    encoding, menu rendering, probing
  ISO image          hdiutil (macOS built-in) / genisoimage / mkisofs, which write
                     the UDF file system DVD players need; xorriso as a last resort
"""

import os
import platform
import re
import shutil
import subprocess
import sys

from .errors import MissingToolsError, ToolFailedError

# Homebrew's plain `ffmpeg` formula is built without libfreetype, so it has no
# `drawtext` filter. `ffmpeg-full` has it but is keg-only (not on PATH), so we
# look inside its keg before falling back to PATH.
_FFMPEG_KEGS = (
    "/opt/homebrew/opt/ffmpeg-full/bin",
    "/usr/local/opt/ffmpeg-full/bin",
)

_ENV_OVERRIDE = {
    "ffmpeg": "ONCEMORE_FFMPEG",
    "ffprobe": "ONCEMORE_FFPROBE",
    "xorriso": "ONCEMORE_XORRISO",
    "genisoimage": "ONCEMORE_GENISOIMAGE",
    "mkisofs": "ONCEMORE_MKISOFS",
}

_VERSION_ARGS = {
    "ffmpeg": ["-hide_banner", "-version"],
    "ffprobe": ["-hide_banner", "-version"],
    "xorriso": ["-version"],
    "genisoimage": ["-version"],
    "mkisofs": ["-version"],
    "hdiutil": None,
}

REQUIRED = ("ffmpeg", "ffprobe")
# "builtin" is udfkit's UDF + ISO 9660 writer (discimage.py), always
# there; then the external UDF-capable tools; xorriso writes no UDF (iso.py)
ISO_TOOLS = ("builtin", "hdiutil", "genisoimage", "mkisofs", "xorriso")
UDF_TOOLS = ("builtin", "hdiutil", "genisoimage", "mkisofs")
EXTERNAL_ISO_TOOLS = ISO_TOOLS[1:]

_cache = {}


def is_macos():
    return sys.platform == "darwin"


def install_hint(names=None):
    """Return a copy-pasteable install command for the current platform."""
    if is_macos():
        pkgs = {"ffmpeg": "ffmpeg-full", "ffprobe": "ffmpeg-full", "xorriso": "xorriso",
                "drawtext": "ffmpeg-full", "genisoimage": "cdrtools", "mkisofs": "cdrtools", "iso": None}
        cmd = "brew install"
    else:
        pkgs = {"ffmpeg": "ffmpeg", "ffprobe": "ffmpeg", "xorriso": "xorriso", "drawtext": "ffmpeg",
                "genisoimage": "genisoimage", "mkisofs": "genisoimage", "iso": "genisoimage"}
        cmd = "sudo apt-get install -y"
    wanted = names or ["ffmpeg", "iso"]
    out = []
    for n in wanted:
        p = pkgs.get(n, n)
        if p and p not in out:
            out.append(p)
    return f"{cmd} {' '.join(out)}"


def find(name):
    """Absolute path of an external program, or None."""
    if name in _cache:
        return _cache[name]
    path = None
    env = _ENV_OVERRIDE.get(name)
    if env and os.environ.get(env):
        cand = os.environ[env]
        path = cand if os.path.isfile(cand) else shutil.which(cand)
    if path is None and name in ("ffmpeg", "ffprobe") and is_macos():
        for keg in _FFMPEG_KEGS:
            cand = os.path.join(keg, name)
            if os.access(cand, os.X_OK):
                path = cand
                break
    if path is None:
        path = shutil.which(name)
    _cache[name] = path
    return path


def reset_cache():
    _cache.clear()


def drawtext_option(name, ffmpeg=None):
    """Whether this ffmpeg's drawtext has an option (text_align: 6.1 on)."""
    key = ("drawtext_option", name, ffmpeg)
    if key not in _cache:
        ffmpeg = ffmpeg or find("ffmpeg")
        ok = False
        if ffmpeg:
            try:
                out = subprocess.run([ffmpeg, "-hide_banner", "-h", "filter=drawtext"],
                                     capture_output=True, text=True, timeout=30).stdout
                ok = re.search(rf"^\s*{re.escape(name)}\s", out, re.M) is not None
            except (OSError, subprocess.SubprocessError):
                ok = False
        _cache[key] = ok
    return _cache[key]


def has_drawtext(ffmpeg=None):
    key = ("drawtext", ffmpeg)
    if key in _cache:
        return _cache[key]
    ffmpeg = ffmpeg or find("ffmpeg")
    ok = False
    if ffmpeg:
        try:
            out = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True,
                                 text=True, timeout=30).stdout
            ok = re.search(r"^\s*\S+\s+drawtext\s", out, re.M) is not None
        except (OSError, subprocess.SubprocessError):
            ok = False
    _cache[key] = ok
    return ok


def version(name):
    path = find(name)
    if not path:
        return None
    args = _VERSION_ARGS.get(name, ["--version"])
    if args is None:
        return "present"
    try:
        p = subprocess.run([path] + args, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    text = (p.stdout or "") + (p.stderr or "")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.search(r"version\s+([0-9][\w.\-~+]*)", line, re.I) or \
            re.search(r"xorriso\s+([0-9][\w.]*)", line)
        if m:
            return m.group(1).rstrip(".,")
    return "unknown"


def iso_tool(preferred="auto"):
    """Pick the ISO backend: (name, path)."""
    order = ISO_TOOLS if preferred == "auto" else (preferred,)
    for n in order:
        if n == "builtin":
            return n, None
        if n == "hdiutil" and not is_macos():
            continue
        p = find(n)
        if p:
            return n, p
    return None, None


def require(names, need_drawtext=False, need_iso=False, iso_preference="auto"):
    """Raise MissingToolsError listing everything that is missing."""
    missing = [n for n in names if not find(n)]
    problems = [f"{n} not found" for n in missing]
    if need_drawtext and "ffmpeg" not in missing and not has_drawtext():
        missing.append("drawtext")
        problems.append(f"ffmpeg at {find('ffmpeg')} has no 'drawtext' filter (built without libfreetype)")
    if need_iso and iso_tool(iso_preference)[0] is None:
        if iso_preference == "auto":
            missing.append("iso")
            problems.append("no ISO tool found (hdiutil, genisoimage, mkisofs or xorriso)")
        else:
            missing.append(iso_preference)
            problems.append(f"{iso_preference} not found")
    if missing:
        hint = f"Install with:  {install_hint(missing)}"
        if is_macos() and ("drawtext" in missing or "ffmpeg" in missing):
            hint += ("\n(Homebrew's plain 'ffmpeg' lacks drawtext; oncemore finds the keg-only "
                     "'ffmpeg-full' automatically, or set ONCEMORE_FFMPEG / ONCEMORE_FFPROBE.)")
        raise MissingToolsError("Missing external tools: " + "; ".join(problems), hint=hint,
                                details={"missing": missing})


def doctor():
    """Collect tool status as a list of dicts (used by `oncemore doctor`)."""
    rows = []
    for n in REQUIRED + EXTERNAL_ISO_TOOLS:
        if n == "hdiutil" and not is_macos():
            continue
        p = find(n)
        row = {"name": n, "path": p, "version": version(n) if p else None,
               "required": n in REQUIRED}
        if n == "ffmpeg" and p:
            row["drawtext"] = has_drawtext()
        rows.append(row)
    return {
        "platform": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "python": platform.python_version(),
        "tools": rows,
        "iso_tool": iso_tool()[0],
        "iso_udf": iso_tool()[0] in UDF_TOOLS,
    }


def still_input(path):
    """ffmpeg options before `-i` for a still picture. A GIF goes through the
    image2 demuxer (the gif demuxer takes no -loop), which reads its first
    picture only."""
    if os.path.splitext(path)[1].lower() == ".gif":
        return ["-f", "image2", "-c:v", "gif"]
    return []


def tail(text, lines=25):
    parts = (text or "").strip().splitlines()
    return "\n".join(parts[-lines:])


def run(cmd, *, cwd=None, env=None, stdin=None, stdout=None, log=None, what=None,
        timeout=None):
    """Run a command; raise ToolFailedError with the tail of its output on failure
    (or when it runs longer than `timeout` seconds).

    `log` is a file path that receives stderr (and stdout unless redirected).
    """
    full_env = None
    if env:
        full_env = dict(os.environ)
        full_env.update(env)
    label = what or os.path.basename(cmd[0])
    try:
        if log:
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "w", encoding="utf-8", errors="replace") as lf:
                lf.write("$ " + " ".join(_q(c) for c in cmd) + "\n")
                lf.flush()
                try:
                    p = subprocess.run(cmd, cwd=cwd, env=full_env, stdin=stdin,
                                       stdout=stdout if stdout is not None else lf, stderr=lf,
                                       timeout=timeout)
                except subprocess.TimeoutExpired:
                    lf.flush()
                    with open(log, encoding="utf-8", errors="replace") as rf:
                        out = rf.read()
                    raise ToolFailedError(f"{label} did not finish within {timeout} s",
                                          details={"log": log, "output": tail(out)})
            if p.returncode != 0:
                with open(log, encoding="utf-8", errors="replace") as lf:
                    out = lf.read()
                raise ToolFailedError(f"{label} failed (exit {p.returncode})",
                                      details={"log": log, "output": tail(out)})
            return p
        p = subprocess.run(cmd, cwd=cwd, env=full_env, stdin=stdin,
                           stdout=stdout if stdout is not None else subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ToolFailedError(f"{label} did not finish within {timeout} s")
    except FileNotFoundError as e:
        raise MissingToolsError(f"Cannot execute {cmd[0]}: {e}", hint=install_hint())
    if p.returncode != 0:
        err = p.stderr.decode("utf-8", "replace") if isinstance(p.stderr, bytes) else p.stderr
        raise ToolFailedError(f"{label} failed (exit {p.returncode})",
                              details={"output": tail(err)})
    return p


def _q(s):
    s = str(s)
    return s if re.fullmatch(r"[\w@%+=:,./-]+", s) else "'" + s.replace("'", "'\\''") + "'"
