"""Slideshows: pictures with durations, cross-fades, gentle pan & zoom and
music, rendered once into a lossless video that then becomes an ordinary
title source.

The rendering is a single ffmpeg graph on the disc's square-pixel canvas
(e.g. 854 x 480 for NTSC 16:9) at the disc frame rate:

  picture -> fit (letterbox in the background colour) or fill (cropped)
             [-> zoompan] -> fps
  slides  -> xfade (cross-fade, wipe, slide ...) or concat (cut), per change
  music   -> one or more files joined, trimmed to the slideshow, faded
             out, padded with silence (fit_to_audio: the pictures' durations
             are scaled so the show is as long as the music; see apply)

With a cross-fade of d seconds, slide k (k >= 1) starts fading in at the sum
of the previous durations, so the total length is the sum of all durations
and chapter k begins there.
"""

import hashlib
import json
import os
import random
import threading
from dataclasses import dataclass, field

from . import settings, tools
from .errors import OncemoreError

CACHE_VERSION = 1
MANUAL_SECONDS = 1.0     # a picture advanced by hand: shown this long, then held
CHUNK = 60               # pictures drawn by one ffmpeg (each is an input of its own)

# transition name -> ffmpeg xfade transition (all in ffmpeg 4.4 and later)
TRANSITIONS = {"crossfade": "fade", "dissolve": "dissolve", "fadeblack": "fadeblack",
               "fadewhite": "fadewhite", "wipeleft": "wipeleft", "wiperight": "wiperight",
               "wipeup": "wipeup", "wipedown": "wipedown", "slideleft": "slideleft",
               "slideright": "slideright", "slideup": "slideup", "slidedown": "slidedown",
               "circleopen": "circleopen", "circleclose": "circleclose", "radial": "radial",
               "pixelize": "pixelize"}


@dataclass
class Slide:
    image: str
    duration: float = 5.0
    fit: str = None          # "fit" | "fill" (None = the slideshow's)
    transition: str = None   # to the next picture (None = the slideshow's)


@dataclass
class Slideshow:
    slides: list
    transition: str = "crossfade"     # a TRANSITIONS name | "random" | "none"
    transition_duration: float = 1.0
    pan_zoom: bool = False
    audio: object = None              # a music file, or a list of them
    background_color: str = "#000000"
    fit: str = "fit"                  # "fit" (whole picture) | "fill" (cropped to the frame)
    fit_to_audio: bool = False        # durations scaled to the music's length
    advance: str = "auto"             # "manual": each picture held until Next / Play
    auto_chapters: bool = True        # the title's chapters are the slides' starts
    music_length: float = None        # (fitted to it: the music's length, once probed)
    extra: dict = field(default_factory=dict)

    @property
    def music(self):
        """The music files, in order."""
        if not self.audio:
            return []
        return [self.audio] if isinstance(self.audio, str) else list(self.audio)

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

    def changes(self):
        """The xfade transition from each picture to the next (None: a cut);
        random ones are drawn the same way every time (seeded by place)."""
        out = []
        for k, s in enumerate(self.slides[:-1]):
            name = s.transition or self.transition
            if name == "random":
                name = random.Random(f"{len(self.slides)}:{k}").choice(sorted(TRANSITIONS))
            out.append(TRANSITIONS.get(name))
        return out

    def fades(self):
        """Seconds each picture runs on into the next one's transition."""
        return [self.transition_duration if c else 0.0 for c in self.changes()] + [0.0]

    @property
    def fade(self):
        """The longest transition (0: only cuts)."""
        return max(self.fades()) if self.slides else 0.0


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
                      "slides": [[_sig(s.image), s.duration] + ([s.fit] if s.fit else []) +
                                 ([s.transition] if s.transition else [])
                                 for s in show.slides],
                      "t": [show.transition, show.transition_duration, show.pan_zoom,
                            show.background_color],
                      "audio": (None if not show.music else _sig(show.music[0])
                                if len(show.music) == 1 else [_sig(a) for a in show.music]),
                      **({"fit": show.fit} if show.fit != "fit" else {}),
                      "disc": [disc.standard, disc.aspect, list(canvas(disc)), disc.fps]},
                     sort_keys=True, default=str)
    name = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24] + ".mkv"
    return os.path.join(settings.cache_dir(base_dir), "slideshow", name)


def _hex(color):
    c = color.lstrip("#")
    return "0x" + c[:6].upper()


def _framed(w, h, fit, bg):
    """Scale a picture to w x h: whole, with bars in `bg` (fit), or filling
    it with what is outside cropped (fill)."""
    if fit == "fill":
        return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    return (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={bg},setsar=1")


def graph(show, disc, part=None):
    """(input args, filter_complex, has_audio) for rendering `show`.

    part=(a, b): only pictures a..b-1, as one piece of a long show (video
    only; every picture is an ffmpeg input of its own, so a long show is
    drawn CHUNK pictures at a time, see render). A piece starts where the
    transition into picture a ends (the piece before draws it) and ends
    where the one out of picture b-1 ends (drawing the start of picture b
    for it), so the pieces joined are the frames of the whole show."""
    W, H = canvas(disc)
    num, den = disc.fps
    fades, changes = show.fades(), show.changes()
    bg = _hex(show.background_color)
    args, chains = [], []
    n = len(show.slides)
    a, b = part or (0, n)
    # every picture change on the frame nearest its start, so the pictures
    # do not drift from the chapters (whole frames per picture would add up)
    times = [0.0]
    for sl in show.slides:
        times.append(times[-1] + sl.duration)
    at = [int(round(t * num / den)) for t in times]
    # (a transition: the next picture's change starts it)
    fade_frames = [int(round((times[k + 1] + f) * num / den)) - at[k + 1] if f else 0
                   for k, f in enumerate(fades)]
    head = fade_frames[a - 1] if a else 0
    shown = list(range(a, b)) + ([b] if b < n and changes[b - 1] else [])
    for i, k in enumerate(shown):
        sl = show.slides[k]
        # running on under the next transition
        frames = max(1, at[k + 1] - at[k] + fade_frames[k])
        length = frames * den / num
        if show.pan_zoom:
            # one picture in, `frames` pictures out; drawn at twice the size so
            # the slow zoom does not wobble on whole-pixel steps
            args += tools.still_input(sl.image) + ["-i", sl.image]
            z = (f"1+0.10*on/{frames}" if k % 2 == 0 else f"1.10-0.10*on/{frames}")
            chain = (f"[{i}:v]{_framed(2 * W, 2 * H, sl.fit or show.fit, bg)},"
                     f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                     f"d={frames}:s={W}x{H}:fps={num}/{den}")
        else:
            args += tools.still_input(sl.image) + ["-loop", "1", "-framerate", f"{num}/{den}",
                     "-t", f"{length + 2 * den / num:.3f}", "-i", sl.image]
            chain = f"[{i}:v]{_framed(W, H, sl.fit or show.fit, bg)}"
        # (a piece: the first picture without what the piece before drew, the
        # picture after the last only as far as the transition into it)
        first = head if k == a else 0
        last = fade_frames[b - 1] if k == b else frames
        trim = f"trim=start_frame={first}:end_frame={last},setpts=PTS-STARTPTS" if first \
            else f"trim=end_frame={last}"
        # (zoompan makes its frames at the rate already; an fps filter after it
        # would drop the last one)
        rate = "" if show.pan_zoom else f",fps={num}/{den}"
        chains.append(chain + f"{rate},format=yuv420p,settb=AVTB,"
                              f"setpts=PTS-STARTPTS,{trim}[s{i}]")
    if len(shown) == 1:
        chains.append("[s0]null[v]")
    elif any(changes):
        # one change at a time: a transition overlaps the next picture, a cut
        # appends it
        cur = "s0"
        for i in range(1, len(shown)):
            k = shown[i]
            out = "v" if i == len(shown) - 1 else f"x{i}"
            kind = changes[k - 1]
            if kind:
                chains.append(f"[{cur}][s{i}]xfade=transition={kind}:"
                              f"duration={fade_frames[k - 1] * den / num:.6f}:"
                              f"offset={(at[k] - at[a] - head) * den / num:.6f}[{out}]")
            else:
                chains.append(f"[{cur}][s{i}]concat=n=2:v=1:a=0[{out}]")
            cur = out
    else:
        chains.append("".join(f"[s{i}]" for i in range(len(shown))) +
                      f"concat=n={len(shown)}:v=1:a=0[v]")
    if part:
        return args, ";".join(chains), False
    m_args, m_chains = music_graph(show, n)
    return args + m_args, ";".join(chains + m_chains), bool(m_args)


def music_graph(show, first):
    """(input args, filter chains -> [a]) of the show's music, its inputs
    numbered from `first`: joined, trimmed to the show, faded out, padded."""
    music = show.music
    if not music:
        return [], []
    total = show.duration
    f = min(2.0, total / 4)
    tail = (f"atrim=duration={total:.3f},"
            f"afade=t=out:st={max(0.0, total - f):.3f}:d={f:.3f},apad[a]")
    if len(music) == 1:
        return ["-i", music[0]], [f"[{first}:a]aresample=48000,{tail}"]
    # one after another: every file in one format first, then joined
    args, chains = [], []
    for k, path in enumerate(music):
        args += ["-i", path]
        chains.append(f"[{first + k}:a]aresample=48000,aformat=sample_fmts=fltp:"
                      f"channel_layouts=stereo[m{k}]")
    chains.append("".join(f"[m{k}]" for k in range(len(music))) +
                  f"concat=n={len(music)}:v=0:a=1,{tail}")
    return args, chains


def fit_to(show, seconds):
    """Scale the pictures' durations so they add up to `seconds` (each at
    least 0.5 s and longer than the cross-fade)."""
    total = show.duration
    if seconds <= 0 or total <= 0:
        return
    least = max(0.5, show.fade + 0.1)
    scale = seconds / total
    for s in show.slides:
        s.duration = max(least, round(s.duration * scale, 3))
    # (rounding) the last picture takes up the difference
    last = show.slides[-1]
    last.duration = max(least, round(last.duration + seconds - show.duration, 3))


def overrun(show):
    """Seconds the pictures run past the music they were fitted to (each
    picture has a least length, so many pictures to short music can)."""
    if not show.music_length:
        return 0.0
    over = show.duration - show.music_length
    return over if over > 0.5 else 0.0


def apply(title, disc, probe):
    """For a slideshow fitted to its music: scale its durations to the music
    (probed), then point the title at the matching render and, unless the
    title gives its own, move its chapters to the new slide starts."""
    show = title.slideshow
    if not (show and show.fit_to_audio and show.music):
        return
    seconds = sum(probe(a).get("duration") or 0.0 for a in show.music)
    fit_to(show, seconds)
    show.music_length = seconds
    # (in the same folder as the render before it was fitted)
    old = title.source
    title.source = os.path.join(os.path.dirname(old), os.path.basename(output_path("", show, disc)))
    for tr in title.audio_tracks:
        if tr.source == old:
            tr.source = title.source
    if show.auto_chapters:
        title.chapters = show.starts()
        title.chapter_names = [None] * len(title.chapters)
        title.chapter_posters = [None] * len(title.chapters)


def render(show, disc, out, log, on_progress=None):
    """Render `show` to `out` (lossless FFV1 + PCM in Matroska); a show of
    more than CHUNK pictures in pieces of CHUNK, joined (see graph)."""
    if not show.slides:
        raise OncemoreError("a slideshow needs at least one picture")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = f"{out}.{os.getpid()}-{threading.get_ident()}.part"   # (one per writer)
    tools.require(["ffmpeg"])
    from . import encode            # (encode imports project, which imports this module)
    n = len(show.slides)
    if n <= CHUNK:
        args, fc, has_audio = graph(show, disc)
        cmd = args + ["-filter_complex", fc, "-map", "[v]"]
        if has_audio:
            cmd += ["-map", "[a]", "-c:a", "pcm_s16le"]
        cmd += ["-c:v", "ffv1", "-level", "3", "-t", f"{show.duration:.3f}", "-f", "matroska",
                tmp]
        encode.run_ffmpeg(cmd, show.duration, log, on_progress, what="ffmpeg (slideshow)")
        os.replace(tmp, out)
        return out
    parts = [(a, min(n, a + CHUNK)) for a in range(0, n, CHUNK)]
    files = []
    try:
        for j, (a, b) in enumerate(parts):
            args, fc, _ = graph(show, disc, (a, b))
            files.append(f"{tmp}.{j}.mkv")
            share = sum(sl.duration for sl in show.slides[a:b])

            def progress(f, j=j):
                if on_progress:
                    on_progress((j + f) / (len(parts) + 1))
            encode.run_ffmpeg(args + ["-filter_complex", fc, "-map", "[v]", "-c:v", "ffv1",
                                      "-level", "3", "-f", "matroska", files[-1]],
                              share, log + f".{j}", progress,
                              what=f"ffmpeg (slideshow pictures {a + 1}-{b})")
        # joined frame by frame (the pieces' own time stamps do not line up
        # for a stream copy); FFV1 again, so still lossless
        m_args, m_chains = music_graph(show, len(files))
        cmd = [x for path in files for x in ("-i", path)] + m_args
        fc = "".join(f"[{j}:v]" for j in range(len(files))) + \
            f"concat=n={len(files)}:v=1:a=0[v]"
        cmd += ["-filter_complex", ";".join([fc] + m_chains), "-map", "[v]"]
        if m_args:
            cmd += ["-map", "[a]", "-c:a", "pcm_s16le"]
        cmd += ["-c:v", "ffv1", "-level", "3", "-t", f"{show.duration:.3f}", "-f", "matroska",
                tmp]
        encode.run_ffmpeg(cmd, show.duration, log,
                          (lambda f: on_progress((len(parts) + f) / (len(parts) + 1)))
                          if on_progress else None, what="ffmpeg (slideshow)")
        os.replace(tmp, out)
    finally:
        for path in files:
            try:
                os.remove(path)
            except OSError:
                pass
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
