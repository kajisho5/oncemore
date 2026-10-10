"""Titles made of several clips: their lengths, and the joined preview the
app shows and plays while the title is edited.

On the disc the clips are joined while the title is encoded (encode.py,
clip_graph); nothing is rendered beforehand. The app needs one file to show
frames from and to play, so it gets a preview with the same joins, picture
format and frame rate as the title (MPEG-4 + PCM, cached by everything it
depends on).
"""

import hashlib
import json
import math
import os

from . import encode, tools
from .project import clip_starts, title_fps

CACHE_VERSION = 1


def resolve(title, disc, probe):
    """Fill in every clip's length from its file, in whole frames of the
    title (so picture and sound meet at the joins). Returns the total."""
    num, den = title_fps(title, disc)
    total = 0.0
    for c in title.clips:
        dur = probe(c.source).get("duration") or 0.0
        end = min(c.end, dur) if c.end is not None else dur
        length = max(0.0, end - c.start)
        c.duration = math.ceil(length * num / den - 1e-6) * den / num
        total += c.duration
    return total


def apply(project, title, probe):
    """resolve() and, unless the title gives its own, a chapter at every
    clip. Returns the title's length."""
    total = resolve(title, project.disc_for(title), probe)
    if title.clip_chapters:
        title.chapters = [s for s in clip_starts(title) if s < total] or [0.0]
        title.chapter_names = [None] * len(title.chapters)
        title.chapter_posters = [None] * len(title.chapters)
    return total


def apply_all(project, probe):
    """apply() to every title made of clips (the simulator and the flowchart
    need their chapters)."""
    for t in project.titles:
        if t.clips:
            apply(project, t, probe)


def _sig(path):
    try:
        st = os.stat(path)
        return [path, st.st_size, int(st.st_mtime)]
    except OSError:
        return [path, None, None]


def preview_path(base_dir, title, disc):
    key = json.dumps({"v": CACHE_VERSION,
                      "clips": [[_sig(c.source), c.start, c.end] for c in title.clips],
                      "disc": [disc.standard, disc.aspect, disc.width, disc.height, disc.fps],
                      "mode": getattr(title, "video_mode", None)},
                     sort_keys=True, default=str)
    name = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24] + ".mkv"
    return os.path.join(base_dir, ".oncemore-cache", "clips", name)


def render_preview(title, disc, out, log, on_progress=None):
    """Join the clips (lengths already resolved) into `out`."""
    tools.require(["ffmpeg", "ffprobe"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    probes = {c.source: encode.probe(c.source) for c in title.clips}
    # the preview is always progressive: frames are what the app shows
    saved = getattr(title, "video_mode", None)
    if saved != "pulldown":
        title.video_mode = "progressive"
    try:
        inputs, graph, _ = encode.clip_graph(title, probes, disc, title.video_mode or
                                             "progressive")
    finally:
        title.video_mode = saved
    total = sum(c.duration for c in title.clips)
    tmp = out + ".part"
    encode.run_ffmpeg(inputs + ["-filter_complex", graph, "-map", "[v]", "-map", "[a0]",
                                "-c:v", "mpeg4", "-q:v", "2", "-c:a", "pcm_s16le",
                                "-t", f"{total:.3f}", "-f", "matroska", tmp],
                      total, log, on_progress, what="ffmpeg (clips)")
    os.replace(tmp, out)
    return out
