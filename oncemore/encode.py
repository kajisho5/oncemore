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
           "-show_format", "-show_streams", "-show_chapters", path]
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
                      "bit_rate": int(s.get("bit_rate", 0) or 0),
                      "profile": s.get("profile")}
                     for s in streams if s.get("codec_type") == "audio"],
           "duration": _float(fmt.get("duration")) or (_float(v.get("duration")) if v else None),
           "bit_rate": int(fmt.get("bit_rate", 0) or 0),
           "format": fmt.get("format_name"),
           # chapter markers in the file (MP4, MOV, MKV ...): start and title
           "chapters": _chapters(info)}
    if v:
        sar = _ratio(v.get("sample_aspect_ratio")) or Fraction(1)
        out.update({
            "width": int(v["width"]), "height": int(v["height"]), "sar": sar,
            "fps": _ratio(v.get("avg_frame_rate")) or _ratio(v.get("r_frame_rate")),
            "codec": v.get("codec_name"),
            "pix_fmt": v.get("pix_fmt"),
            "video_bit_rate": int(v.get("bit_rate", 0) or 0),
            "profile": v.get("profile"), "level": int(v.get("level", 0) or 0),
            "interlaced": v.get("field_order") in ("tt", "bb", "tb", "bt"),
            "field_order": v.get("field_order"),
        })
    if a:
        out.update({"audio_codec": a.get("codec_name"),
                    "audio_rate": int(a.get("sample_rate", 0) or 0),
                    "audio_channels": int(a.get("channels", 0) or 0)})
    return out


def _chapters(info):
    out = []
    for c in info.get("chapters", []):
        try:
            t = float(c.get("start_time"))
        except (TypeError, ValueError):
            continue
        if t >= 0:
            out.append({"time": round(t, 6), "name": (c.get("tags") or {}).get("title", "")})
    return sorted(out, key=lambda c: c["time"])


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
    if want == "ivtc":
        return "pulldown"              # film recovered from telecined video (fit_filter)
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


def is_ivtc(title):
    return getattr(title, "scan", None) == "ivtc"


def fill_crop(info, dar):
    """(crop filter + ",", info of the cropped picture) cutting a picture's
    edges so that it has the display aspect `dar` (for fill)."""
    w, h = info["width"], info["height"]
    sar = float(info.get("sar", 1) or 1)
    if w * sar / h > dar:
        cw, ch = min(w, int(round(h * dar / sar / 2)) * 2), h
    else:
        cw, ch = w, min(h, int(round(w * sar / dar / 2)) * 2)
    return f"crop={cw}:{ch}," if (cw, ch) != (w, h) else "", dict(info, width=cw, height=ch)


def fit_filter(info, disc, pad_color="black", fps=True, mode="progressive", ivtc=False):
    """ffmpeg -vf chain that converts `info` (from probe) to the disc format.

    mode "interlaced" works on fields: the source is split into one picture
    per field (bwdif send_field) or taken at the field rate, scaled, and
    woven back into top-field-first frames. mode "pulldown" keeps 23.976
    film frames (the pulldown flags are set after encoding). ivtc: the
    source is film that was telecined to 29.97i; its film frames are put
    back together (field matching, then the duplicate in every five frames
    dropped) instead of being deinterlaced."""
    w, h, px, py = fit_geometry(info["width"], info["height"], info.get("sar", 1),
                                disc.width, disc.height, disc.dar)
    num, den = disc.fps
    parts = []
    if mode == "interlaced":
        if info.get("interlaced"):
            parts.append("bwdif=mode=send_field")
        parts.append(f"fps={2 * num}/{den}")
    elif ivtc:
        parts += ["fieldmatch=order=auto:combmatch=full", "yadif=deint=interlaced", "decimate"]
        if fps:
            parts.append(f"fps={FILM_FPS[0]}/{FILM_FPS[1]}")
    else:
        if info.get("interlaced"):
            parts.append("bwdif")
        if fps:
            n, d = FILM_FPS if mode == "pulldown" else (num, den)
            parts.append(f"fps={n}/{d}")
    parts.append(f"scale={w}:{h}:flags=bicubic:out_color_matrix={getattr(disc, 'matrix', 'bt601')}:out_range=tv")
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


# DTS is copied as its core stream: DTS-HD extensions (which neither disc
# format takes as "DTS") are dropped; plain DTS passes unchanged
DTS_CORE = ["-bsf:a", "dca_core"]


def copy_args(title):
    """Encoder options for sound copied from the sources (audio_passthrough)."""
    return ["-c:a", "copy"] + (DTS_CORE if title.audio_codec == "dts" else [])


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


def clip_graph(title, probes, disc, mode, video=True, audio=True):
    """Inputs and filter_complex joining a title's clips (see DECISIONS §36).

    Every clip is cut from its file (-ss / -t before -i), converted to the
    disc format on its own (sizes and rates may differ between clips), and
    the pieces are joined with concat. A clip without sound gets silence of
    its length, so picture and sound stay together across the joins.
    A still picture is read as a video of its length (-loop 1) and fitted
    or cropped to the frame (fill_crop); it has no sound, so it gets silence.
    Returns (inputs, filter_complex, [output labels]): "[v]" for the
    picture, then "[a0]" for the sound."""
    inputs, chains, pieces = [], [], []
    layout = "5.1" if title.audio_channels == 6 and title.audio_codec != "lpcm" else "stereo"
    fmt = f"aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts={layout}"
    num, den = title_fps(title, disc)
    for k, c in enumerate(title.clips):
        info = probes[c.source]
        dur = c.duration
        if c.still:
            inputs += ["-loop", "1", "-framerate", f"{num}/{den}", "-t", f"{dur:.6f}",
                       "-i", c.source]
        else:
            inputs += ["-ss", f"{c.start:.6f}", "-t", f"{dur:.6f}", "-i", c.source]
        if video:
            # exactly the clip's frames: a short file is held on its last one
            frames = round(dur * num / den)
            if c.still:
                crop, pic = fill_crop(info, disc.dar) if c.fit == "fill" else ("", info)
                fit = crop + fit_filter(pic, disc, mode=mode)
            else:
                fit = fit_filter(info, disc, mode=mode, ivtc=is_ivtc(title))
            chains.append(f"[{k}:v:0]setpts=PTS-STARTPTS,{fit},"
                          f"tpad=stop_mode=clone:stop_duration=1,trim=end_frame={frames},"
                          f"setpts=PTS-STARTPTS,format=yuv420p[v{k}]")
            pieces.append(f"[v{k}]")
        if audio:
            if info.get("audio_streams", 0) > 0:
                chain = f"[{k}:a:0]aresample=48000,asetpts=PTS-STARTPTS,{fmt},apad"
            else:
                chain = f"anullsrc=channel_layout={layout}:sample_rate=48000,{fmt}"
            chains.append(f"{chain},atrim=end={dur:.6f},asetpts=PTS-STARTPTS[s{k}]")
            pieces.append(f"[s{k}]")
    outs = (["[v]"] if video else []) + (["[cat]"] if audio else [])
    chains.append(f"{''.join(pieces)}concat=n={len(title.clips)}:v={int(video)}:a={int(audio)}"
                  + "".join(outs))
    labels = ["[v]"] if video else []
    if audio:
        tail = "," + LPCM_FRAME_FILTER if title.audio_codec == "lpcm" else ""
        chains.append(f"[cat]anull{tail}[a0]")
        labels.append("[a0]")
    return inputs, ";".join(chains), labels


def sound_only(info, title, disc):
    """The probe-like info of a title whose source is sound only: its
    picture is `title.picture` held still, or black (info["still"] is the
    picture's path, or None)."""
    num, den = disc.fps
    out = dict(info, has_video=True, fps=num / den, interlaced=False, still=title.picture,
               codec=None)
    if title.picture:
        pic = probe(title.picture)
        out.update(width=pic.get("width"), height=pic.get("height"), sar=pic.get("sar") or 1)
    else:
        out.update(width=disc.width, height=disc.height, sar=disc.dar * disc.height / disc.width)
    return out


def still_input(info, fps, duration, size):
    """ffmpeg input of a sound-only title's picture (sound_only): the still,
    or black of `size`, for `duration` seconds at `fps`."""
    num, den = fps
    if info.get("still"):
        return ["-loop", "1", "-framerate", f"{num}/{den}", "-t", f"{duration:.3f}",
                "-i", info["still"]]
    w, h = size
    return ["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={num}/{den}:d={duration:.3f}"]


DVD_MAX_VIDEO_BPS = 9_800_000
DVD_MAX_MUX_BPS = 10_080_000


def is_film(info, disc):
    """23.976 film on an NTSC disc (shown with pulldown)."""
    return disc.standard == "NTSC" and abs(float(info.get("fps") or 0)
                                           - FILM_FPS[0] / FILM_FPS[1]) < 0.01


def longest_gop(path, seconds=60):
    """The most pictures between two key frames in the first `seconds` of a
    file's video (its packets' key flags: nothing is decoded); None when
    ffprobe cannot tell."""
    cmd = [tools.find("ffprobe"), "-v", "error", "-read_intervals", f"%+{seconds}",
           "-select_streams", "v:0", "-show_entries", "packet=flags", "-of", "csv=p=0", path]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return None
    flags = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    keys = [i for i, f in enumerate(flags) if "K" in f]
    if p.returncode != 0 or not keys:
        return None
    # (the last group may be cut off by the interval: not counted)
    return max([b - a for a, b in zip(keys, keys[1:])] or [len(flags) - keys[0]])


def dvd_compliance(info, disc, audio_bps=0):
    """Why the picture of `info` (probe) cannot go on a `disc` DVD as it is
    (an empty list when it can): MPEG-2 4:2:0 at a DVD frame size of the
    disc's standard, its frame rate (or 23.976 film on NTSC, which gets its
    pulldown flags when copied) and aspect, GOPs no longer than DVD allows
    (`info["gop"]`, from longest_gop), at most 9.8 Mbit/s, and with the
    sound (`audio_bps`) within the 10.08 Mbit/s a DVD reads."""
    out = []
    if info.get("codec") != "mpeg2video":
        out.append(f"the video is {info.get('codec')}, not MPEG-2")
    if info.get("pix_fmt") and info["pix_fmt"] != "yuv420p":
        out.append(f"the picture is {info['pix_fmt']}, not 4:2:0 (yuv420p)")
    if (info.get("width"), info.get("height")) not in ((disc.width, disc.height),
                                                        (704, disc.height), (352, disc.height)):
        out.append(f"the frame is {info.get('width')}x{info.get('height')}, not "
                   f"{disc.width}x{disc.height}")
    num, den = disc.fps
    rates = [num / den] + ([FILM_FPS[0] / FILM_FPS[1]] if disc.standard == "NTSC" else [])
    fps = float(info.get("fps") or 0)
    if not any(abs(fps - r) < 0.01 for r in rates):
        out.append(f"the frame rate is {fps:.3f}, not {num / den:.3f}")
    w, h = info.get("width") or 0, info.get("height") or 1
    dar = w * float(info.get("sar") or 1) / h
    if abs(dar - disc.dar) > 0.05 * disc.dar:
        out.append(f"the picture is {dar:.2f}:1, not {disc.aspect}")
    film = is_film(info, disc)
    gop = info.get("gop")
    most = gop_limits(FILM_FPS if film else disc.fps)[0]
    if gop and gop > most:
        out.append(f"a group of pictures is {gop} frames long (at most {most} on a DVD)")
    # a VBR stream in a program stream does not say its own rate: the
    # file's, less the sound's, is the most it can be
    vbps = info.get("video_bit_rate") or max(
        0, (info.get("bit_rate") or 0) - sum(a.get("bit_rate") or 0 for a in info.get("audio", [])))
    if vbps > DVD_MAX_VIDEO_BPS:
        out.append(f"the video bitrate is {vbps / 1e6:.1f} Mbit/s (at most 9.8)")
    elif vbps and audio_bps and vbps + audio_bps > DVD_MAX_MUX_BPS:
        out.append(f"the video ({vbps / 1e6:.2f} Mbit/s) and the sound "
                   f"({audio_bps / 1e6:.2f} Mbit/s) are more than the 10.08 Mbit/s a DVD reads")
    return out


def source_video_bps(info):
    """The video bitrate of a source used as it is (the whole file's rate
    when the stream does not say)."""
    return info.get("video_bit_rate") or info.get("bit_rate") or DVD_MAX_VIDEO_BPS


def encode_title(title, info, disc, video_bps, out_path, work, two_pass=True,
                 on_progress=None, probes=None):
    """Encode one title to a DVD-compliant MPEG-2 program stream."""
    if not info.get("has_video"):
        raise OncemoreError(f"title {title.id!r}: {title.source} has no video stream")
    duration = info["duration"]
    target = "ntsc-dvd" if disc.standard == "NTSC" else "pal-dvd"
    probes = dict(probes or {})
    probes.setdefault(title.source, info)
    mode = getattr(title, "video_mode", None) or "progressive"
    if title.clips:
        for c in title.clips:
            probes.setdefault(c.source, probe(c.source))
        return _encode_clips(title, disc, video_bps, out_path, work, two_pass, on_progress,
                             probes, duration, target, mode)
    extra, graph, labels = audio_graph(title, probes)
    inputs = ["-i", title.source] + extra
    if title.audio_passthrough:
        # AC-3 copied as it is: map the streams directly, no filter graph
        sources = [title.source] + [extra[i + 1] for i in range(0, len(extra), 2)]
        amap = []
        for tr in title.audio_tracks:
            amap += ["-map", f"{sources.index(tr.source)}:a:{tr.stream}"]
        acodec = copy_args(title)
    else:
        amap = ["-filter_complex", graph]
        for lab in labels:
            amap += ["-map", lab]
        acodec = audio_args(title.audio_codec, title.audio_bitrate, framing=False,
                            channels=title.audio_channels)
    if not getattr(title, "transcode", True):
        # already DVD video: the picture is copied, only the sound is made
        # (film gets its pulldown flags, as when it is encoded)
        if is_film(info, disc):
            _pulldown_mux(title, inputs, ["-map", "0:v:0", "-c:v", "copy"], amap, acodec,
                          1 + len(extra) // 2, duration, out_path, work, on_progress)
            return out_path
        run_ffmpeg(inputs + ["-map", "0:v:0", "-c:v", "copy"] + amap + acodec +
                   ["-f", "dvd", "-muxrate", "10080000", "-packetsize", "2048",
                    "-t", f"{duration:.3f}", out_path],
                   duration, os.path.join(work, "logs", f"title-{title.id}.log"), on_progress,
                   cwd=work, what=f"ffmpeg (title {title.id}, picture copied)")
        return out_path
    vin = "0:v:0"
    if "still" in info:
        # sound only: the picture comes from its own input, after the sound's
        inputs += still_input(info, disc.fps, duration, (disc.width, disc.height))
        vin = f"{inputs.count('-i') - 1}:v:0"
    video = ["-map", vin, "-vf", fit_filter(info, disc, mode=mode, ivtc=is_ivtc(title))] + \
        _video_args(title, disc, video_bps, target, mode)
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
        _pulldown_mux(title, inputs, video, amap, acodec, 1 + len(extra) // 2, duration,
                      out_path, work, prog(passes - 1))
        return out_path
    run_ffmpeg(inputs + video + amap + acodec + ["-t", f"{duration:.3f}", out_path],
               duration, os.path.join(logdir, f"title-{title.id}.log"), prog(passes - 1),
               cwd=work, what=f"ffmpeg (title {title.id})")
    return out_path


def _encode_clips(title, disc, video_bps, out_path, work, two_pass, on_progress, probes,
                  duration, target, mode):
    """encode_title for a title made of clips: one filter graph joins them."""
    inputs, graph, _ = clip_graph(title, probes, disc, mode)
    _, vgraph, _ = clip_graph(title, probes, disc, mode, audio=False)
    _, agraph, _ = clip_graph(title, probes, disc, mode, video=False)
    acodec = audio_args(title.audio_codec, title.audio_bitrate, framing=False,
                        channels=title.audio_channels)
    venc = _video_args(title, disc, video_bps, target, mode)
    # (an unused output of a filter graph is an error, hence the three graphs)
    vonly = ["-filter_complex", vgraph, "-map", "[v]"] + venc
    passlog = os.path.join(work, f"{title.id}-pass")
    logdir = os.path.join(work, "logs")
    passes = 2 if two_pass else 1

    def prog(i):
        return (lambda f: on_progress((i + f) / passes)) if on_progress else None

    if two_pass:
        run_ffmpeg(inputs + vonly + ["-pass", "1", "-passlogfile", passlog,
                                     "-f", "null", os.devnull],
                   duration, os.path.join(logdir, f"title-{title.id}-pass1.log"), prog(0),
                   cwd=work, what=f"ffmpeg (title {title.id}, pass 1)")
        venc += ["-pass", "2", "-passlogfile", passlog]
        vonly += ["-pass", "2", "-passlogfile", passlog]
    if mode == "pulldown":
        _pulldown_mux(title, inputs, vonly, ["-filter_complex", agraph, "-map", "[a0]"],
                      acodec, len(title.clips), duration, out_path, work, prog(passes - 1))
        return out_path
    run_ffmpeg(inputs + ["-filter_complex", graph, "-map", "[v]", "-map", "[a0]"] + venc +
               acodec + ["-t", f"{duration:.3f}", out_path],
               duration, os.path.join(logdir, f"title-{title.id}.log"), prog(passes - 1),
               cwd=work, what=f"ffmpeg (title {title.id})")
    return out_path


def _video_args(title, disc, video_bps, target, mode):
    fps = title_fps(title, disc)
    keys, _ = chapter_points(title.chapters, fps)
    keyframes = ",".join(f"{t:.6f}" for t in keys)
    video = ["-target", target,
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
    return video


def _pulldown_mux(title, inputs, video, amap, acodec, n, duration, out_path, work, progress):
    """Film frames go to an elementary stream, get their pulldown flags, and
    are then muxed with the sound (input `n` is the patched stream)."""
    logdir = os.path.join(work, "logs")
    m2v = os.path.join(work, f"{title.id}.m2v")
    run_ffmpeg(inputs + video + ["-an", "-t", f"{duration:.3f}", "-f", "mpeg2video", m2v],
               duration, os.path.join(logdir, f"title-{title.id}.log"), progress,
               cwd=work, what=f"ffmpeg (title {title.id})")
    pulldown.patch_file(m2v)
    run_ffmpeg(inputs + ["-fflags", "+genpts", "-i", m2v, "-map", f"{n}:v:0", "-c:v", "copy"]
               + amap + acodec + ["-f", "dvd", "-muxrate", "10080000", "-packetsize", "2048",
                                  "-t", f"{duration:.3f}", out_path],
               duration, os.path.join(logdir, f"title-{title.id}-mux.log"), None,
               cwd=work, what=f"ffmpeg (title {title.id}, mux)")
    os.remove(m2v)


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
