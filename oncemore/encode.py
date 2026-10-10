"""ffmpeg/ffprobe: probing, geometry, bitrate planning and MPEG-2 encoding."""

import json
import os
import subprocess
import threading
import time
from fractions import Fraction

from . import tools
from .errors import OncemoreError, ProjectError, ToolFailedError
from . import pulldown
from .project import FILM_FPS, chapter_points, gop_limits, title_fps

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
           "audio": [{"codec": s.get("codec_name"), "rate": int(s.get("sample_rate", 0) or 0),
                      "channels": int(s.get("channels", 0) or 0),
                      "bit_rate": int(s.get("bit_rate", 0) or 0)}
                     for s in streams if s.get("codec_type") == "audio"],
           "duration": _float(fmt.get("duration")) or (_float(v.get("duration")) if v else None),
           "format": fmt.get("format_name")}
    if v:
        sar = _ratio(v.get("sample_aspect_ratio")) or Fraction(1)
        out.update({
            "width": int(v["width"]), "height": int(v["height"]), "sar": sar,
            "fps": _ratio(v.get("avg_frame_rate")) or _ratio(v.get("r_frame_rate")),
            "codec": v.get("codec_name"),
            "interlaced": v.get("field_order") in ("tt", "bb", "tb", "bt"),
            "field_order": v.get("field_order"),
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


def video_mode(title, info, disc):
    """How a title's picture is stored: "progressive", "interlaced" or
    "pulldown" (23.976 fps film flagged for 3:2 pulldown), from the title's
    `scan` setting and its source (see DECISIONS §32)."""
    want = getattr(title, "scan", "auto") or "auto"
    if want != "auto":
        return want
    num, den = disc.fps
    rate, src = num / den, float(info.get("fps") or 0)
    if info.get("interlaced"):
        # (some files report the field rate instead of the frame rate)
        same = abs(src - rate) < 0.05 or abs(src - 2 * rate) < 0.1
        return "interlaced" if same else "progressive"
    if disc.standard == "NTSC" and abs(src - FILM_FPS[0] / FILM_FPS[1]) < 0.01:
        return "pulldown"
    if abs(src - 2 * rate) < 0.1:
        return "interlaced"            # 59.94p / 50p: keep the motion as fields
    return "progressive"


def fit_filter(info, disc, pad_color="black", fps=True, mode="progressive"):
    """ffmpeg -vf chain that converts `info` (from probe) to the disc format.

    mode "interlaced" works on fields: the source is split into one picture
    per field (bwdif send_field) or taken at the field rate, scaled, and
    woven back into top-field-first frames. mode "pulldown" keeps 23.976
    film frames (the pulldown flags are set after encoding)."""
    w, h, px, py = fit_geometry(info["width"], info["height"], info.get("sar", 1),
                                disc.width, disc.height, disc.dar)
    num, den = disc.fps
    parts = []
    if mode == "interlaced":
        if info.get("interlaced"):
            parts.append("bwdif=mode=send_field")
        parts.append(f"fps={2 * num}/{den}")
    else:
        if info.get("interlaced"):
            parts.append("bwdif")
        if fps:
            n, d = FILM_FPS if mode == "pulldown" else (num, den)
            parts.append(f"fps={n}/{d}")
    parts.append(f"scale={w}:{h}:flags=bicubic:out_color_matrix=bt601:out_range=tv")
    if (w, h) != (disc.width, disc.height):
        parts.append(f"pad={disc.width}:{disc.height}:{px}:{py}:color={pad_color}")
    if mode == "interlaced":
        # a vertical low-pass against twitter only when the picture was resized
        lowpass = "complex" if (info["width"], info["height"]) != (w, h) else "off"
        parts.append(f"interlace=scan=tff:lowpass={lowpass},setfield=tff")
    a, b = disc.aspect.split(":")
    parts.append(f"setdar={a}/{b}")
    return ",".join(parts)


# --------------------------------------------------------------------------
# bitrate planning
# --------------------------------------------------------------------------

def plan_bitrate(items, capacity, menu_seconds=0.0, fixed=None):
    """Choose the average video bitrate.

    items: list of (duration_seconds, audio_bps) or (duration_seconds,
    audio_bps, title_bps) for every title; title_bps fixes that title's video
    bitrate and the others share what is left. Returns a dict with
    "video_bps" (the shared rate), "per_title" (the rate of each item),
    "estimated_bytes", "capacity" and "warnings". Raises ProjectError if the
    content cannot fit.
    """
    items = [tuple(it) + (None,) * (3 - len(it)) for it in items]
    total = sum(d for d, _, _ in items)
    if total <= 0:
        raise ProjectError("titles have zero total duration")
    max_audio = max(a for _, a, _ in items)
    cap = min(MAX_VIDEO_BPS, MAX_TOTAL_BPS - max_audio)
    menu_bytes = menu_seconds * (MENU_VIDEO_BPS + MENU_AUDIO_BPS) / 8 * (1 + MUX_OVERHEAD)
    usable = capacity * (1 - DISC_SAFETY) - IFO_RESERVE - menu_bytes
    audio_bits = sum(d * a for d, a, _ in items)
    own_bits = sum(d * min(f, cap) for d, _, f in items if f)
    shared = sum(d for d, _, f in items if not f)
    fit = ((usable * 8 / (1 + MUX_OVERHEAD) - audio_bits - own_bits) / shared) if shared \
        else float("inf")
    warnings = []
    if fixed:
        video = min(int(fixed), cap)
        if video < fixed:
            warnings.append(f"video bitrate limited to {video // 1000}k by the DVD rate limit")
    else:
        video = int(min(cap, fit)) if shared else cap
    per_title = [min(int(f), cap) if f else video for _, _, f in items]
    est = (sum(d * (v + a) for (d, a, _), v in zip(items, per_title)) / 8) * (1 + MUX_OVERHEAD) \
        + menu_bytes + IFO_RESERVE
    if not fixed and fit < MIN_VIDEO_BPS:
        raise ProjectError(
            f"content does not fit: {total / 60:.1f} min would need a video bitrate of "
            f"{max(fit, 0) / 1e6:.2f} Mbit/s (minimum {MIN_VIDEO_BPS / 1e6:.1f}). "
            "Use DVD9, shorter titles or AC-3 instead of LPCM.")
    if (fixed or not shared) and est > capacity:
        raise ProjectError(f"estimated size {est / 2**30:.2f} GiB exceeds the "
                           f"{capacity / 2**30:.2f} GiB disc with the fixed video bitrate")
    if video < LOW_QUALITY_BPS:
        warnings.append(f"average video bitrate is only {video / 1e6:.2f} Mbit/s; "
                        "expect visible compression artefacts")
    return {"video_bps": video, "per_title": per_title, "estimated_bytes": int(est),
            "capacity": capacity, "total_seconds": total, "warnings": warnings}


def peak_bitrate(audio_bps):
    return min(MAX_VIDEO_PEAK_BPS, MAX_TOTAL_BPS - audio_bps)


# --------------------------------------------------------------------------
# running ffmpeg with progress
# --------------------------------------------------------------------------

# ffmpeg reports progress about twice a second; this long without a single
# report means it is stuck (it is then stopped and the log tail reported).
STALL_SECONDS = 300


def run_ffmpeg(args, duration, log, on_progress=None, cwd=None, what="ffmpeg"):
    """Run ffmpeg with -progress and report fraction via on_progress(f)."""
    cmd = [tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-progress", "pipe:1",
           "-nostats"] + list(args)
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "w", encoding="utf-8", errors="replace") as lf:
        lf.write("$ " + " ".join(tools._q(c) for c in cmd) + "\n")
        lf.flush()
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=lf, cwd=cwd, text=True,
                                    stdin=subprocess.DEVNULL)
        except FileNotFoundError as e:
            raise tools.MissingToolsError(f"Cannot execute ffmpeg: {e}", hint=tools.install_hint())
        last = [time.monotonic()]
        stalled = threading.Event()

        def watchdog():
            while proc.poll() is None:
                if time.monotonic() - last[0] > STALL_SECONDS:
                    stalled.set()
                    proc.kill()
                    return
                time.sleep(1)
        threading.Thread(target=watchdog, daemon=True).start()
        for line in proc.stdout:
            last[0] = time.monotonic()
            key, _, val = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms") and on_progress and duration:
                try:
                    t = int(val) / 1e6
                except ValueError:
                    continue
                on_progress(min(1.0, t / duration))
        proc.stdout.close()
        rc = proc.wait()
    if rc != 0:
        with open(log, encoding="utf-8", errors="replace") as lf:
            out = lf.read()
        why = f"made no progress for {STALL_SECONDS} s" if stalled.is_set() else f"failed (exit {rc})"
        raise ToolFailedError(f"{what} {why}", details={"log": log, "output": tools.tail(out)})
    if on_progress:
        on_progress(1.0)


# --------------------------------------------------------------------------
# titles
# --------------------------------------------------------------------------

def _color_args(disc):
    if disc.standard == "PAL":
        return ["-color_primaries", "bt470bg", "-color_trc", "gamma28", "-colorspace", "bt470bg"]
    return ["-color_primaries", "smpte170m", "-color_trc", "smpte170m", "-colorspace", "smpte170m"]


# LPCM is encoded in 80-sample frames (one DVD LPCM frame, 1/600 s) so that
# ffmpeg's packet PTS line up with frame starts; see lpcmfix.py.
# Resampling/remixing must happen before the split: a converter ffmpeg inserts
# after the user filters would re-chunk the frames.
LPCM_FRAME_FILTER = ("aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,"
                     "asetnsamples=n=80:p=0")


def audio_args(codec, bitrate, framing=True, channels=2):
    """Encoder options. `framing=False` when the LPCM framing filter is
    already part of a -filter_complex chain (-af cannot be combined).
    channels=6 encodes 5.1 AC-3; fewer source channels are up-mixed by
    ffmpeg's default matrix (front channels only)."""
    if codec == "lpcm":
        return ["-c:a", "pcm_s16be", "-ar", "48000", "-ac", "2"] + \
            (["-af", LPCM_FRAME_FILTER] if framing else [])
    return ["-c:a", "ac3", "-b:a", str(bitrate), "-ar", "48000", "-ac", str(channels)]


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
            chain = f"[{idx}:a:{tr.stream}]aresample=48000,apad"
        else:
            layout = "5.1" if title.audio_channels == 6 else "stereo"
            chain = f"anullsrc=channel_layout={layout}:sample_rate=48000"
        if title.audio_codec == "lpcm":
            chain += "," + LPCM_FRAME_FILTER
        chains.append(f"{chain}[a{k}]")
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
    if title.audio_passthrough:
        # AC-3 copied as it is: map the streams directly, no filter graph
        sources = [title.source] + [extra[i + 1] for i in range(0, len(extra), 2)]
        amap = []
        for tr in title.audio_tracks:
            amap += ["-map", f"{sources.index(tr.source)}:a:{tr.stream}"]
        acodec = ["-c:a", "copy"]
    else:
        amap = ["-filter_complex", graph]
        for lab in labels:
            amap += ["-map", lab]
        acodec = audio_args(title.audio_codec, title.audio_bitrate, framing=False,
                            channels=title.audio_channels)
    mode = getattr(title, "video_mode", None) or "progressive"
    fps = title_fps(title, disc)
    keys, _ = chapter_points(title.chapters, fps)
    keyframes = ",".join(f"{t:.6f}" for t in keys)
    video = ["-map", "0:v:0", "-vf", fit_filter(info, disc, mode=mode), "-target", target,
             "-aspect", disc.aspect, "-b:v", str(video_bps),
             "-maxrate", str(peak_bitrate(title.audio_bps)), "-bufsize", "1835008",
             # fixed GOP grid so chapter key frames can be planned (see keyframe_plan)
             "-g", str(gop_limits(fps)[0]), "-sc_threshold", "1000000000"]
    if mode == "interlaced":
        # top field first comes from the frames (setfield=tff in the filter);
        # ffmpeg 7+ no longer has the -top option
        video += ["-flags", "+ilme+ildct", "-alternate_scan", "1"]
    elif mode == "pulldown":
        video += ["-r", f"{fps[0]}/{fps[1]}"]
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
    if mode == "pulldown":
        # film frames go to an elementary stream, get their pulldown flags,
        # and are then muxed with the audio unchanged
        m2v = os.path.join(work, f"{title.id}.m2v")
        run_ffmpeg(inputs + video + ["-an", "-t", f"{duration:.3f}", "-f", "mpeg2video", m2v],
                   duration, os.path.join(logdir, f"title-{title.id}.log"), prog(passes - 1),
                   cwd=work, what=f"ffmpeg (title {title.id})")
        pulldown.patch_file(m2v)
        n = 1 + len(extra) // 2
        run_ffmpeg(inputs + ["-fflags", "+genpts", "-i", m2v, "-map", f"{n}:v:0", "-c:v", "copy"]
                   + amap + acodec + ["-f", "dvd", "-muxrate", "10080000", "-packetsize", "2048",
                                      "-t", f"{duration:.3f}", out_path],
                   duration, os.path.join(logdir, f"title-{title.id}-mux.log"), None,
                   cwd=work, what=f"ffmpeg (title {title.id}, mux)")
        os.remove(m2v)
        return out_path
    run_ffmpeg(inputs + video + amap + acodec + ["-t", f"{duration:.3f}", out_path],
               duration, os.path.join(logdir, f"title-{title.id}.log"), prog(passes - 1),
               cwd=work, what=f"ffmpeg (title {title.id})")
    return out_path


def extract_thumbnail(source, info, disc, time, size, out_path, log):
    """Grab one frame at `time`, formatted like the encoded title (`disc` =
    the title's settings), and fit it into a `size` box of square pixels."""
    t = max(0.0, min(time, (info.get("duration") or time + 1) - 0.2))
    w, h = size
    vf = (fit_filter(info, disc, fps=False) +
          f",scale=iw*sar:ih,setsar=1,scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1")
    tools.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-y", "-ss", f"{t:.3f}",
               "-i", source, "-frames:v", "1", "-vf", vf, out_path], log=log,
              what="ffmpeg (thumbnail)", timeout=600)
    return out_path
