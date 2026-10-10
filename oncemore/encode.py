"""ffmpeg/ffprobe: probing, geometry, bitrate planning and MPEG-2 encoding."""

import json
import os
import subprocess
from fractions import Fraction

from . import tools
from .errors import OncemoreError, ProjectError, ToolFailedError
from .project import chapter_points, gop_limits

# Upper limits we allow ourselves (DVD-Video allows 9.8 Mbit/s video and
# 10.08 Mbit/s total; staying below leaves headroom for players).
MAX_VIDEO_BPS = 8_000_000
MAX_TOTAL_BPS = 9_800_000
MAX_VIDEO_PEAK_BPS = 9_000_000
MIN_VIDEO_BPS = 1_000_000
LOW_QUALITY_BPS = 3_000_000

MUX_OVERHEAD = 0.03          # MPEG program-stream / NAV pack overhead
DISC_SAFETY = 0.02           # keep 2 % of the disc free
IFO_RESERVE = 4 * 1024 * 1024
MENU_VIDEO_BPS = 4_000_000   # still menus; real size is usually far smaller
MOTION_MENU_VIDEO_BPS = 6_000_000
MENU_AUDIO_BPS = 192_000


# --------------------------------------------------------------------------
# probing
# --------------------------------------------------------------------------

def probe(path):
    """Return a dict describing the first video/audio stream of `path`."""
    tools.require(["ffprobe"])
    cmd = [tools.find("ffprobe"), "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", path]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise ToolFailedError(f"ffprobe timed out on {path}")
    if p.returncode != 0:
        raise ToolFailedError(f"ffprobe cannot read {path}", details={"output": tools.tail(p.stderr)})
    info = json.loads(p.stdout or "{}")
    streams = info.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"
              and not s.get("disposition", {}).get("attached_pic")), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    fmt = info.get("format", {})
    out = {"path": path, "has_video": v is not None, "has_audio": a is not None,
           "audio_streams": sum(1 for s in streams if s.get("codec_type") == "audio"),
           "duration": _float(fmt.get("duration")) or (_float(v.get("duration")) if v else None),
           "format": fmt.get("format_name")}
    if v:
        sar = _ratio(v.get("sample_aspect_ratio")) or Fraction(1)
        out.update({
            "width": int(v["width"]), "height": int(v["height"]), "sar": sar,
            "fps": _ratio(v.get("avg_frame_rate")) or _ratio(v.get("r_frame_rate")),
            "codec": v.get("codec_name"),
            "interlaced": v.get("field_order") in ("tt", "bb", "tb", "bt"),
        })
    if a:
        out.update({"audio_codec": a.get("codec_name"),
                    "audio_rate": int(a.get("sample_rate", 0) or 0),
                    "audio_channels": int(a.get("channels", 0) or 0)})
    return out


def _float(s):
    try:
        f = float(s)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _ratio(s):
    if not s or s in ("N/A", "0:1", "0/0", "0/1"):
        return None
    sep = ":" if ":" in s else "/"
    a, b = s.split(sep)
    try:
        if int(b) == 0 or int(a) == 0:
            return None
        return Fraction(int(a), int(b))
    except ValueError:
        return None


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def _even(v):
    return max(2, int(round(v / 2.0)) * 2)


def fit_geometry(src_w, src_h, src_sar, width, height, dar):
    """Scale size and pad offset to fit a source into a DVD frame.

    The DVD frame is `width` x `height` storage pixels displayed at `dar`.
    Wider sources get letterboxed, narrower ones pillarboxed.
    Returns (scaled_w, scaled_h, pad_x, pad_y).
    """
    src_dar = src_w * float(src_sar) / src_h
    if abs(src_dar - dar) < 0.01:
        w, h = width, height
    elif src_dar > dar:
        w, h = width, _even(height * dar / src_dar)
    else:
        w, h = _even(width * src_dar / dar), height
    w, h = min(w, width), min(h, height)
    return w, h, ((width - w) // 4) * 2, ((height - h) // 4) * 2


def fit_filter(info, disc, pad_color="black", fps=True):
    """ffmpeg -vf chain that converts `info` (from probe) to the disc format."""
    w, h, px, py = fit_geometry(info["width"], info["height"], info.get("sar", 1),
                                disc.width, disc.height, disc.dar)
    parts = []
    if info.get("interlaced"):
        parts.append("bwdif")
    if fps:
        num, den = disc.fps
        parts.append(f"fps={num}/{den}")
    parts.append(f"scale={w}:{h}:flags=bicubic:out_color_matrix=bt601:out_range=tv")
    if (w, h) != (disc.width, disc.height):
        parts.append(f"pad={disc.width}:{disc.height}:{px}:{py}:color={pad_color}")
    a, b = disc.aspect.split(":")
    parts.append(f"setdar={a}/{b}")
    return ",".join(parts)


# --------------------------------------------------------------------------
# bitrate planning
# --------------------------------------------------------------------------

def plan_bitrate(items, capacity, menu_seconds=0.0, fixed=None):
    """Choose the average video bitrate.

    items: list of (duration_seconds, audio_bps) for every title.
    Returns a dict with "video_bps", "estimated_bytes", "capacity" and
    "warnings". Raises ProjectError if the content cannot fit.
    """
    total = sum(d for d, _ in items)
    if total <= 0:
        raise ProjectError("titles have zero total duration")
    max_audio = max(a for _, a in items)
    cap = min(MAX_VIDEO_BPS, MAX_TOTAL_BPS - max_audio)
    menu_bytes = menu_seconds * (MENU_VIDEO_BPS + MENU_AUDIO_BPS) / 8 * (1 + MUX_OVERHEAD)
    usable = capacity * (1 - DISC_SAFETY) - IFO_RESERVE - menu_bytes
    audio_bits = sum(d * a for d, a in items)
    fit = (usable * 8 / (1 + MUX_OVERHEAD) - audio_bits) / total
    warnings = []
    if fixed:
        video = min(int(fixed), cap)
        if video < fixed:
            warnings.append(f"video bitrate limited to {video // 1000}k by the DVD rate limit")
    else:
        video = int(min(cap, fit))
    est = (sum(d * (video + a) for d, a in items) / 8) * (1 + MUX_OVERHEAD) + menu_bytes + IFO_RESERVE
    if not fixed and fit < MIN_VIDEO_BPS:
        raise ProjectError(
            f"content does not fit: {total / 60:.1f} min would need a video bitrate of "
            f"{max(fit, 0) / 1e6:.2f} Mbit/s (minimum {MIN_VIDEO_BPS / 1e6:.1f}). "
            "Use DVD9, shorter titles or AC-3 instead of LPCM.")
    if fixed and est > capacity:
        raise ProjectError(f"estimated size {est / 2**30:.2f} GiB exceeds the "
                           f"{capacity / 2**30:.2f} GiB disc with the fixed video bitrate")
    if video < LOW_QUALITY_BPS:
        warnings.append(f"average video bitrate is only {video / 1e6:.2f} Mbit/s; "
                        "expect visible compression artefacts")
    return {"video_bps": video, "estimated_bytes": int(est), "capacity": capacity,
            "total_seconds": total, "warnings": warnings}


def peak_bitrate(audio_bps):
    return min(MAX_VIDEO_PEAK_BPS, MAX_TOTAL_BPS - audio_bps)


# --------------------------------------------------------------------------
# running ffmpeg with progress
# --------------------------------------------------------------------------

def run_ffmpeg(args, duration, log, on_progress=None, cwd=None, what="ffmpeg"):
    """Run ffmpeg with -progress and report fraction via on_progress(f)."""
    cmd = [tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-progress", "pipe:1",
           "-nostats"] + list(args)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "w", encoding="utf-8", errors="replace") as lf:
        lf.write("$ " + " ".join(tools._q(c) for c in cmd) + "\n")
        lf.flush()
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=lf, cwd=cwd, text=True)
        except FileNotFoundError as e:
            raise tools.MissingToolsError(f"Cannot execute ffmpeg: {e}", hint=tools.install_hint())
        for line in proc.stdout:
            key, _, val = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms") and on_progress and duration:
                try:
                    t = int(val) / 1e6
                except ValueError:
                    continue
                on_progress(min(1.0, t / duration))
        rc = proc.wait()
    if rc != 0:
        with open(log, encoding="utf-8", errors="replace") as lf:
            out = lf.read()
        raise ToolFailedError(f"{what} failed (exit {rc})", details={"log": log, "output": tools.tail(out)})
    if on_progress:
        on_progress(1.0)


# --------------------------------------------------------------------------
# titles
# --------------------------------------------------------------------------

def _color_args(disc):
    if disc.standard == "PAL":
        return ["-color_primaries", "bt470bg", "-color_trc", "gamma28", "-colorspace", "bt470bg"]
    return ["-color_primaries", "smpte170m", "-color_trc", "smpte170m", "-colorspace", "smpte170m"]


def audio_args(codec, bitrate):
    if codec == "lpcm":
        return ["-c:a", "pcm_s16be", "-ar", "48000", "-ac", "2"]
    return ["-c:a", "ac3", "-b:a", str(bitrate), "-ar", "48000", "-ac", "2"]


def audio_graph(title, probes):
    """Inputs and filter_complex mapping every audio track of a title.

    Returns (extra_input_args, filter_complex, [output labels]). Input 0 is
    the title source; other sources are appended. Tracks whose stream does not
    exist (a source without audio) become silence; every track is padded so
    the output can be cut to the video length with -t.
    """
    sources = [title.source]
    for tr in title.audio_tracks:
        if tr.source not in sources:
            sources.append(tr.source)
    extra = []
    for src in sources[1:]:
        extra += ["-i", src]
    chains, labels = [], []
    for k, tr in enumerate(title.audio_tracks):
        idx = sources.index(tr.source)
        have = probes[tr.source].get("audio_streams", 0)
        if tr.stream < have:
            chains.append(f"[{idx}:a:{tr.stream}]aresample=48000,apad[a{k}]")
        else:
            chains.append(f"anullsrc=channel_layout=stereo:sample_rate=48000[a{k}]")
        labels.append(f"[a{k}]")
    return extra, ";".join(chains), labels


def encode_title(title, info, disc, video_bps, out_path, work, two_pass=True,
                 on_progress=None, probes=None):
    """Encode one title to a DVD-compliant MPEG-2 program stream."""
    if not info.get("has_video"):
        raise OncemoreError(f"title {title.id!r}: {title.source} has no video stream")
    duration = info["duration"]
    target = "ntsc-dvd" if disc.standard == "NTSC" else "pal-dvd"
    probes = dict(probes or {})
    probes.setdefault(title.source, info)
    extra, graph, labels = audio_graph(title, probes)
    inputs = ["-i", title.source] + extra
    amap = ["-filter_complex", graph]
    for lab in labels:
        amap += ["-map", lab]
    keys, _ = chapter_points(title.chapters, disc.fps)
    keyframes = ",".join(f"{t:.6f}" for t in keys)
    video = ["-map", "0:v:0", "-vf", fit_filter(info, disc), "-target", target,
             "-aspect", disc.aspect, "-b:v", str(video_bps),
             "-maxrate", str(peak_bitrate(title.audio_bps)), "-bufsize", "1835008",
             # fixed GOP grid so chapter key frames can be planned (see keyframe_plan)
             "-g", str(gop_limits(disc.fps)[0]), "-sc_threshold", "1000000000"]
    if keyframes:
        video += ["-force_key_frames", keyframes]
    video += _color_args(disc)
    passlog = os.path.join(work, f"{title.id}-pass")
    logdir = os.path.join(work, "logs")
    passes = 2 if two_pass else 1

    def prog(i):
        return (lambda f: on_progress((i + f) / passes)) if on_progress else None

    if two_pass:
        run_ffmpeg(inputs + video + ["-pass", "1", "-passlogfile", passlog, "-an",
                                     "-f", "null", os.devnull],
                   duration, os.path.join(logdir, f"title-{title.id}-pass1.log"), prog(0),
                   cwd=work, what=f"ffmpeg (title {title.id}, pass 1)")
        video += ["-pass", "2", "-passlogfile", passlog]
    run_ffmpeg(inputs + video + amap + audio_args(title.audio_codec, title.audio_bitrate)
               + ["-t", f"{duration:.3f}", out_path],
               duration, os.path.join(logdir, f"title-{title.id}.log"), prog(passes - 1),
               cwd=work, what=f"ffmpeg (title {title.id})")
    return out_path


def extract_thumbnail(source, info, disc, time, size, out_path, log):
    """Grab one frame at `time`, formatted like the encoded title, scaled to size."""
    t = max(0.0, min(time, (info.get("duration") or time + 1) - 0.2))
    vf = fit_filter(info, disc, fps=False) + f",scale={size[0]}:{size[1]},setsar=1"
    tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-ss", f"{t:.3f}",
               "-i", source, "-frames:v", "1", "-vf", vf, out_path], log=log,
              what="ffmpeg (thumbnail)")
    return out_path
