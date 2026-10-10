"""Slideshows: pictures with durations, cross-fades, gentle pan & zoom and
music, rendered once into a lossless video that then becomes an ordinary
title source.

The rendering is a single ffmpeg graph on the disc's square-pixel canvas
(e.g. 854 x 480 for NTSC 16:9) at the disc frame rate:

  picture -> fit (letterbox in the background colour) [-> zoompan] -> fps
  slides  -> xfade (cross-fade) or concat
  music   -> trimmed to the slideshow, faded out, padded with silence

With a cross-fade of d seconds, slide k (k >= 1) starts fading in at the sum
of the previous durations, so the total length is the sum of all durations
and chapter k begins there.
"""

import hashlib
import json
import os
from dataclasses import dataclass, field

from . import tools
from .errors import OncemoreError

CACHE_VERSION = 1


@dataclass
class Slide:
    image: str
    duration: float = 5.0


@dataclass
class Slideshow:
    slides: list
    transition: str = "crossfade"     # "crossfade" | "none"
    transition_duration: float = 1.0
    pan_zoom: bool = False
    audio: str = None
    background_color: str = "#000000"
    extra: dict = field(default_factory=dict)

    @property
    def duration(self):
        return sum(s.duration for s in self.slides)

    def starts(self):
        """Start time of every slide (the chapter points)."""
        out, t = [], 0.0
        for s in self.slides:
            out.append(round(t, 3))
            t += s.duration
        return out

    @property
    def fade(self):
        return self.transition_duration if self.transition == "crossfade" and \
            len(self.slides) > 1 else 0.0


def _sig(path):
    try:
        st = os.stat(path)
        return [path, st.st_size, int(st.st_mtime)]
    except OSError:
        return [path, None, None]


def _code():
    with open(__file__, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def canvas(disc):
    """(width, height) of the square-pixel canvas for `disc`."""
    w = int(round(disc.height * disc.dar / 2.0)) * 2
    return w, disc.height


def output_path(base_dir, show, disc):
    """Where the rendered slideshow lives (keyed by everything it depends on)."""
    key = json.dumps({"v": CACHE_VERSION, "code": _code(),
                      "slides": [[_sig(s.image), s.duration] for s in show.slides],
                      "t": [show.transition, show.transition_duration, show.pan_zoom,
                            show.background_color],
                      "audio": _sig(show.audio) if show.audio else None,
                      "disc": [disc.standard, disc.aspect, list(canvas(disc)), disc.fps]},
                     sort_keys=True, default=str)
    name = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24] + ".mkv"
    return os.path.join(base_dir, ".oncemore-cache", "slideshow", name)


def _hex(color):
    c = color.lstrip("#")
    return "0x" + c[:6].upper()


def graph(show, disc):
    """(input args, filter_complex, has_audio) for rendering `show`."""
    W, H = canvas(disc)
    num, den = disc.fps
    fps = num / den
    fade = show.fade
    bg = _hex(show.background_color)
    args, chains = [], []
    n = len(show.slides)
    for k, s in enumerate(show.slides):
        length = s.duration + (fade if k < n - 1 else 0.0)
        frames = max(1, int(round(length * fps)))
        if show.pan_zoom:
            # one picture in, `frames` pictures out; drawn at twice the size so
            # the slow zoom does not wobble on whole-pixel steps
            args += ["-i", s.image]
            z = (f"1+0.10*on/{frames}" if k % 2 == 0 else f"1.10-0.10*on/{frames}")
            chain = (f"[{k}:v]scale={2 * W}:{2 * H}:force_original_aspect_ratio=decrease,"
                     f"pad={2 * W}:{2 * H}:(ow-iw)/2:(oh-ih)/2:color={bg},setsar=1,"
                     f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                     f"d={frames}:s={W}x{H}:fps={num}/{den}")
        else:
            args += ["-loop", "1", "-framerate", f"{num}/{den}", "-t", f"{length:.3f}",
                     "-i", s.image]
            chain = (f"[{k}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                     f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg},setsar=1")
        chains.append(chain + f",fps={num}/{den},format=yuv420p,settb=AVTB,"
                              f"setpts=PTS-STARTPTS,trim=duration={length:.3f}[s{k}]")
    if n == 1:
        chains.append("[s0]null[v]")
    elif fade:
        cur, offset = "s0", 0.0
        for k in range(1, n):
            offset += show.slides[k - 1].duration
            out = "v" if k == n - 1 else f"x{k}"
            chains.append(f"[{cur}][s{k}]xfade=transition=fade:duration={fade:.3f}:"
                          f"offset={offset:.3f}[{out}]")
            cur = out
    else:
        chains.append("".join(f"[s{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[v]")
    total = show.duration
    has_audio = bool(show.audio)
    if has_audio:
        args += ["-i", show.audio]
        f = min(2.0, total / 4)
        chains.append(f"[{n}:a]aresample=48000,atrim=duration={total:.3f},"
                      f"afade=t=out:st={max(0.0, total - f):.3f}:d={f:.3f},apad[a]")
    return args, ";".join(chains), has_audio


def render(show, disc, out, log, on_progress=None):
    """Render `show` to `out` (lossless FFV1 + PCM in Matroska)."""
    if not show.slides:
        raise OncemoreError("a slideshow needs at least one picture")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    args, fc, has_audio = graph(show, disc)
    tmp = out + ".part"
    cmd = args + ["-filter_complex", fc, "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "[a]", "-c:a", "pcm_s16le"]
    cmd += ["-c:v", "ffv1", "-level", "3", "-t", f"{show.duration:.3f}", "-f", "matroska", tmp]
    tools.require(["ffmpeg"])
    from . import encode            # (encode imports project, which imports this module)
    encode.run_ffmpeg(cmd, show.duration, log, on_progress, what="ffmpeg (slideshow)")
    os.replace(tmp, out)
    return out


def ensure(title, disc, log, reporter=None):
    """Render the title's slideshow unless an identical one is cached."""
    if os.path.isfile(title.source):
        return False
    if reporter:
        reporter.step("slideshow", f"Rendering slideshow '{title.id}' "
                                   f"({len(title.slideshow.slides)} pictures, "
                                   f"{title.slideshow.duration:.1f}s)", item=title.id)
    render(title.slideshow, disc, title.source, log,
           (lambda f: reporter.progress("slideshow", f, title.id)) if reporter else None)
    return True
