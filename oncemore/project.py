"""Loading, validating and normalising project.oncemore.json.

`load_project()` turns the JSON into plain dataclasses with every default
filled in, every path resolved relative to the project file, and the
auto-generated chapter menus expanded into ordinary Menu objects. Everything
downstream (encoding, menus, authoring) only sees the normalised model.
"""

import dataclasses
import json
import math
import os
import re
from dataclasses import dataclass, field
from importlib import resources

from . import schemalite
from . import slideshow
from .errors import ProjectError

PROJECT_FILENAME = "project.oncemore.json"

STANDARDS = {
    # name: (width, height, frame rate as (num, den), dvdauthor format)
    "NTSC": (720, 480, (30000, 1001), "ntsc"),
    "PAL": (720, 576, (25, 1), "pal"),
}

# Bytes on a single-layer / dual-layer DVD±R (2048-byte sectors).
CAPACITY = {
    "DVD5": 2_295_104 * 2048,   # 4,700,372,992 B = 4.38 GiB
    "DVD9": 4_171_712 * 2048,   # 8,543,666,176 B = 7.96 GiB
}

DEFAULT_HIGHLIGHT = "#FFD400"
DEFAULT_SELECT = "#FF5A00"
DEFAULT_TEXT = "#FFFFFF"
DEFAULT_BG = "#101820"
DEFAULT_FONT_SIZE = 32
DEFAULT_MENU_SECONDS = 5.0
MAX_BUTTONS = 36
CHAPTERS_PER_PAGE = 6


# --------------------------------------------------------------------------
# small parsers
# --------------------------------------------------------------------------

def parse_time(value):
    """Seconds from a number or "HH:MM:SS[.mmm]" / "MM:SS" / "SS" string."""
    if isinstance(value, bool):
        raise ValueError("time must be a number or string")
    if isinstance(value, (int, float)):
        if value < 0:
            raise ValueError("time must not be negative")
        return float(value)
    s = str(value).strip()
    if not re.fullmatch(r"([0-9]+:){0,2}[0-9]+(\.[0-9]+)?", s):
        raise ValueError(f"invalid time {value!r}")
    parts = s.split(":")
    secs = 0.0
    for p in parts:
        secs = secs * 60 + float(p)
    if len(parts) > 1 and any(float(p) >= 60 for p in parts[1:]):
        raise ValueError(f"invalid time {value!r}: minutes/seconds must be < 60")
    return secs


def format_time(seconds):
    """Seconds -> "H:MM:SS.mmm" (dvdauthor accepts this)."""
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h}:{m:02d}:{s:02d}.{ms:03d}"


def gop_limits(fps):
    """(max GOP length, min VOBU length) in frames for a frame rate.

    DVD-Video caps a GOP at 18 frames (NTSC) / 15 (PAL), and every VOBU (one
    GOP here) must last at least 0.4 s.
    """
    num, den = fps
    rate = num / den
    if rate < 24.5:
        # film with soft pulldown on NTSC: 14 pictures show as 35 fields (the
        # 36-field GOP limit); 10 pictures last 25 fields = 0.417 s
        return (14, 10)
    return (18, 12) if rate > 26 else (15, 10)


def keyframe_plan(chapter_frames, fps):
    """Frames that must be I-frames so every chapter starts its own VOBU.

    The encoder runs with a fixed GOP (scene-cut I-frames disabled), so after
    each forced key frame the next ones follow every `gop` frames. The GOP
    right before a chapter is the remainder and may be shorter than the
    minimum VOBU length, in which case dvdauthor merges it with the chapter's
    GOP and the chapter lands early. We split the last few GOPs of such a
    segment evenly instead (each between `minimum` and `gop` frames).
    """
    gop, minimum = gop_limits(fps)
    keys = set()
    prev = 0
    for c in chapter_frames:
        if c <= 0:
            continue
        keys.add(c)
        seg = c - prev
        rem = seg % gop
        if rem and rem < minimum:
            m = 1
            while gop * m + rem <= seg:
                total = gop * m + rem
                n = -(-total // gop)
                if total // n >= minimum:
                    sizes = [total // n + (1 if i < total % n else 0) for i in range(n)]
                    pos = c
                    for size in reversed(sizes[1:]):
                        pos -= size
                        keys.add(pos)
                    break
                m += 1
        prev = c
    return sorted(keys)


FILM_FPS = (24000, 1001)


def clip_starts(title):
    """Where each clip of a title begins on the title's timeline (seconds)."""
    out, t = [], 0.0
    for c in title.clips:
        out.append(round(t, 6))
        t += c.duration or 0.0
    return out


def source_at(title, time):
    """(file, time inside it) for a moment of the title: titles made of clips
    map it to the clip playing then."""
    if not title.clips:
        return title.source, time
    starts = clip_starts(title)
    k = max(i for i, s in enumerate(starts) if s <= time + 1e-6) if starts else 0
    c = title.clips[k]
    if c.still:
        return c.source, 0.0
    return c.source, c.start + (time - starts[k])


def title_fps(title, disc):
    """Frame rate the title is encoded at: 23.976 for soft pulldown, else the disc's."""
    return FILM_FPS if getattr(title, "video_mode", None) == "pulldown" else disc.fps


def chapter_points(chapters, fps):
    """Chapter times snapped to frames, for encoding and authoring.

    Returns (keyframe_times, authoring_times). keyframe_times are the frames
    to force as I-frames (chapter starts plus helpers from keyframe_plan);
    authoring_times are passed to dvdauthor, which puts a chapter at the last
    VOBU starting at or before the given time, so we aim half a frame late.
    """
    num, den = fps
    frames = [math.ceil(t * num / den - 1e-6) for t in chapters]
    keys = [f * den / num for f in keyframe_plan(frames, fps)]
    marks = [0.0 if f == 0 else (f + 0.5) * den / num for f in frames]
    return keys, marks


def parse_bitrate(value):
    """bits/s from 192000, "192k", "5.5M"."""
    if isinstance(value, bool):
        raise ValueError("invalid bitrate")
    if isinstance(value, (int, float)):
        return int(value)
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([kKmM]?)", str(value).strip())
    if not m:
        raise ValueError(f"invalid bitrate {value!r}")
    mult = {"": 1, "k": 1000, "K": 1000, "m": 1_000_000, "M": 1_000_000}[m.group(2)]
    return int(round(float(m.group(1)) * mult))


def normalize_label(label):
    """ISO 9660 / DVD volume label: A-Z 0-9 _, at most 32 characters."""
    s = re.sub(r"[^A-Z0-9_]", "_", label.upper())
    s = re.sub(r"_+", "_", s).strip("_") or "DVD_VIDEO"
    return s[:32]


def parse_action(s):
    """'menu:x' -> ('menu', 'x', None); 'menu:x:b' -> ('menu', 'x', 'b') (button b
    highlighted); 'chapter:t:2' -> ('chapter', 't', 2); 'stop';
    'audio:2' -> ('audio', None, 2); 'subtitle:off' -> ('subtitle', None, 0);
    'playall' -> ('playall', None, None); 'playlist:p' -> ('playlist', 'p', None);
    'resume' -> ('resume', None, None); 'lastmenu' -> ('lastmenu', None, None)."""
    if s in ("stop", "playall", "resume", "lastmenu"):
        return (s, None, None)
    kind, _, rest = s.partition(":")
    if kind == "chapter":
        tid, _, n = rest.rpartition(":")
        return ("chapter", tid, int(n))
    if kind in ("audio", "subtitle"):
        return (kind, None, 0 if rest == "off" else int(rest))
    if kind == "menu":
        mid, _, button = rest.partition(":")
        return ("menu", mid, button or None)
    return (kind, rest, None)


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

TRANSITION_ACTIONS = ("menu", "title", "chapter", "playlist", "playall")


def transition_key(button):
    """What a button with a link transition does: buttons that play the same
    video and then do the same share one transition on the disc."""
    return (button.transition, button.action, button.override, button.audio, button.subtitle)


@dataclass
class Disc:
    label: str
    standard: str
    aspect: str
    target: str
    first_play: str
    font: str = None
    video_bitrate: int = None  # None = auto
    subtitle_style: dict = None
    title_key: str = None      # target of the remote's Title key (None = first menu)
    rom_files: list = field(default_factory=list)   # DVD-ROM content next to VIDEO_TS
    bluray_target: str = "BD25"   # disc size when building a Blu-ray

    @property
    def width(self):
        return STANDARDS[self.standard][0]

    @property
    def height(self):
        return STANDARDS[self.standard][1]

    @property
    def fps(self):
        return STANDARDS[self.standard][2]

    @property
    def capacity(self):
        return CAPACITY[self.target]

    @property
    def dar(self):
        a, b = self.aspect.split(":")
        return int(a) / int(b)


@dataclass
class AudioTrack:
    source: str          # file to take the audio from (default: the title source)
    stream: int = 0      # index among that file's audio streams
    lang: str = None     # ISO 639-1 code


@dataclass
class SubtitleTrack:
    file: str
    lang: str = None
    default: bool = False
    position: str = "bottom"
    color: str = None


@dataclass
class Clip:
    source: str
    start: float = 0.0       # "in" inside the file
    end: float = None        # "out" inside the file (None = its end)
    duration: float = None   # resolved from the file by build.inspect
    hold: float = None       # a still picture: seconds it is shown (None = a video)
    fit: str = "fit"         # a still picture: "fit" (whole, bars around) or "fill" (cropped)

    @property
    def still(self):
        return self.hold is not None


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")
STILL_DEFAULT = 5.0


def is_image(path):
    return os.path.splitext(path or "")[1].lower() in IMAGE_EXTS


@dataclass
class Title:
    id: str
    name: str
    source: str
    chapters: list
    audio_codec: str = "ac3"
    audio_bitrate: int = 192_000
    audio_channels: int = 2  # 2 = stereo, 6 = 5.1 (AC-3 only)
    end_action: str = "stop"
    number: int = 0  # 1-based title number on the disc
    audio_tracks: list = field(default_factory=list)
    subtitles: list = field(default_factory=list)
    aspect: str = None       # display aspect of this title (default: the disc's)
    titleset: int = 1        # DVD titleset (VTS) holding this title
    global_number: int = 0   # title number as players show it (VMGM order)
    remote_menu: str = None  # menu id the Menu key opens during this title
    slideshow: object = None  # slideshow.Slideshow when made from pictures
    video_bitrate: int = None   # this title's own video bitrate (None = shared)
    audio_passthrough: bool = False   # copy AC-3 from the sources
    chapter_names: list = field(default_factory=list)    # per chapter, or None
    chapter_posters: list = field(default_factory=list)  # thumbnail time per chapter, or None
    scan: str = "auto"       # "auto" | "progressive" | "interlaced" | "pulldown" | "ivtc"
    transcode: bool = True   # False: a DVD-compliant MPEG-2 source's picture is used as it is
    picture: str = None      # a sound-only source: the still shown meanwhile (None = black)
    clips: list = field(default_factory=list)   # Clip, when made of several videos
    clip_chapters: bool = False   # a chapter at every clip (set once clip lengths are known)
    video_mode: str = None   # what `scan` resolved to for the source (set by build.inspect)
    prohibit: list = field(default_factory=list)   # remote keys the title does not allow (uops.NAMES)

    @property
    def track_bps(self):
        # LPCM 48 kHz / 16 bit / stereo (5.1 is AC-3 only)
        return 1_536_000 if self.audio_codec == "lpcm" else self.audio_bitrate

    @property
    def audio_bps(self):
        """All audio tracks together."""
        return self.track_bps * max(1, len(self.audio_tracks))


@dataclass
class Text:
    text: str
    x: int
    y: int
    size: int
    color: str
    font: str = None           # own font file (None = the disc font)
    outline: str = None
    outline_width: int = 2
    shadow: str = None
    shadow_offset: int = 3


@dataclass
class Shape:
    x: int
    y: int
    w: int
    h: int
    color: str = "#00000080"


@dataclass
class Picture:
    """A picture on a menu that is not a button (a logo, a photo)."""
    file: str
    x: int
    y: int
    w: int
    h: int
    opacity: float = 1.0


@dataclass
class PlaylistItem:
    title_id: str
    first: int = 1        # first chapter (1-based)
    last: int = None      # last chapter, inclusive (None = to the end of the title)


@dataclass
class Playlist:
    id: str
    name: str
    items: list
    end_action: str = "stop"


@dataclass
class Thumb:
    title_id: str
    time: float
    x: int
    y: int
    w: int
    h: int
    animated: bool = False     # plays the chapter (motion chapter menus)


@dataclass
class Button:
    id: str
    label: str
    x: int
    y: int
    action: str
    size: int
    color: str
    nav: dict = field(default_factory=dict)
    thumb: Thumb = None
    image: str = None          # image button: picture instead of the label
    auto_activate: bool = False
    font: str = None
    outline: str = None
    outline_width: int = 2
    shadow: str = None
    shadow_offset: int = 3
    highlight_image: str = None  # picture whose opaque pixels are the highlight
    width: int = None          # its width on the 720-wide grid (None = natural)
    highlight: str = "frame"   # image buttons: "frame" | "shape"
    override: str = None       # end action of the title this button plays, instead of its own
    audio: int = None          # audio stream (1-based) to switch to with the action
    subtitle: int = None       # subtitle stream (1-based, 0 = off) to switch to with the action
    transition: str = None     # video played after the button is pressed, before its link


@dataclass
class Menu:
    id: str
    background: str
    background_color: str
    audio: str
    duration: float
    highlight_color: str
    select_color: str
    texts: list
    buttons: list
    generated: bool = False
    number: int = 0  # 1-based menu PGC number inside the titleset
    background_video: str = None
    loop: int = None           # None = forever, else plays before end_action
    loop_point: float = 0.0    # repeats start here (the part before is an intro)
    end_action: str = "stop"   # after the last loop
    default_button: str = None
    remember_button: bool = True
    shapes: list = field(default_factory=list)
    images: list = field(default_factory=list)    # Picture, over the shapes
    normal_color: str = None   # the buttons' shapes while not selected (None: not shown)
    fade_in: float = 0.0       # seconds of fade from black when the menu starts (played once)
    buttons_at_loop: bool = False  # buttons only from the loop point on (the intro plays out)
    loop_pgc: int = 0          # menu PGC with the buttons (number + 1 when the intro is apart)
    prohibit: list = field(default_factory=list)   # remote keys the menu does not allow (uops.NAMES)


@dataclass
class Project:
    path: str
    base_dir: str
    disc: Disc
    titles: list
    menus: list
    warnings: list = field(default_factory=list)
    playlists: list = field(default_factory=list)

    def title(self, tid):
        return next((t for t in self.titles if t.id == tid), None)

    def playlist(self, pid):
        return next((p for p in self.playlists if p.id == pid), None)

    @property
    def uses_playlists(self):
        return bool(self.playlists)

    def titleset_titles(self, n):
        return sorted((t for t in self.titles if t.titleset == n), key=lambda t: t.number)

    @property
    def titleset_count(self):
        return max(t.titleset for t in self.titles)

    def disc_for(self, title):
        """The disc settings with this title's aspect ratio (for encoding)."""
        return dataclasses.replace(self.disc, aspect=title.aspect)

    def menu(self, mid):
        return next((m for m in self.menus if m.id == mid), None)

    @property
    def root_menu(self):
        return self.menus[0] if self.menus else None

    @property
    def uses_remote_menu(self):
        return any(t.remote_menu for t in self.titles)

    @property
    def uses_playall(self):
        return "playall" in self.actions()

    @property
    def overrides(self):
        """End-action overrides used by buttons, in a fixed order (1-based
        numbers in the override register)."""
        return sorted({b.override for m in self.menus for b in m.buttons if b.override})

    @property
    def link_transitions(self):
        """The link transitions the disc plays: one per (transition video,
        action, override, audio, subtitle) of a button, in menu and button
        order (see transition_key)."""
        out = []
        for m in self.menus:
            for b in m.buttons:
                if b.transition and transition_key(b) not in out:
                    out.append(transition_key(b))
        return out

    @property
    def uses_last_menu(self):
        """Some title / playlist end action or override returns to the last menu."""
        ends = [t.end_action for t in self.titles] + [p.end_action for p in self.playlists] + \
            [b.override for m in self.menus for b in m.buttons if b.override]
        return "lastmenu" in ends and bool(self.menus)

    def actions(self):
        """Every action of the disc: first play, Title key, buttons and their
        overrides, menu, title and playlist end actions."""
        out = [self.disc.first_play, self.disc.title_key]
        for m in self.menus:
            out += [b.action for b in m.buttons] + [b.override for b in m.buttons]
            if m.loop is not None:
                out.append(m.end_action)
        out += [t.end_action for t in self.titles] + [p.end_action for p in self.playlists]
        return [a for a in out if a]

    @property
    def entry_buttons(self):
        """{menu id: {button ids}} that links open with that button highlighted."""
        out = {}
        for a in self.actions():
            kind, mid, button = parse_action(a)
            if kind == "menu" and button:
                out.setdefault(mid, set()).add(button)
        return out

    @property
    def uses_resume(self):
        return any(b.action == "resume" for m in self.menus for b in m.buttons)

    def playall_next(self, title):
        """Title after `title` in "Play all" order (project order), or None."""
        i = self.titles.index(title)
        return self.titles[i + 1] if i + 1 < len(self.titles) else None

    @property
    def audio_langs(self):
        """Language of each audio stream index across the titleset."""
        return _stream_langs([t.audio_tracks for t in self.titles])

    @property
    def subtitle_langs(self):
        return _stream_langs([t.subtitles for t in self.titles])


def _stream_langs(per_title):
    out = []
    for tracks in per_title:
        for i, tr in enumerate(tracks):
            if i >= len(out):
                out.append(tr.lang)
            elif out[i] is None:
                out[i] = tr.lang
    return out


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def load_schema():
    return json.loads(resources.files("oncemore").joinpath("project.schema.json")
                      .read_text(encoding="utf-8"))


def resolve_project_path(path):
    if os.path.isdir(path):
        path = os.path.join(path, PROJECT_FILENAME)
    return os.path.abspath(path)


def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ProjectError(f"Project file not found: {path}")
    except json.JSONDecodeError as e:
        raise ProjectError(f"{path}: invalid JSON at line {e.lineno} column {e.colno}: {e.msg}")


def load_project(path, check_files=True):
    """Load and validate a project. Raises ProjectError listing all issues."""
    path = resolve_project_path(path)
    data = read_json(path)
    return build_project(data, path, check_files=check_files)


def build_project(data, path, check_files=True):
    base = os.path.dirname(os.path.abspath(path))
    issues = [{"path": p, "message": m} for p, m in schemalite.validate(data, load_schema())]
    if issues:
        raise ProjectError(f"{path}: does not match the project schema", issues)
    b = _Builder(data, path, base, check_files)
    project = b.build()
    if b.issues:
        raise ProjectError(f"{path}: invalid project", b.issues)
    return project


class _Builder:
    def __init__(self, data, path, base, check_files):
        self.data = data
        self.path = path
        self.base = base
        self.check_files = check_files
        self.issues = []
        self.warnings = []

    def prohibit(self, where, obj):
        """A title's or a menu's prohibited remote keys (uops.NAMES), in that order."""
        from .uops import NAMES
        names = obj.get("prohibit") or []
        for n in names:
            if n not in NAMES:
                self.err(f"{where}.prohibit", f"{n!r} is not a remote key oncemore can turn off "
                                              f"({', '.join(NAMES)})")
        return [n for n in NAMES if n in names]

    def err(self, where, msg):
        self.issues.append({"path": where, "message": msg})

    def file(self, where, rel, kind="file"):
        if rel is None:
            return None
        p = os.path.normpath(os.path.join(self.base, os.path.expanduser(rel)))
        exists = os.path.exists(p) if kind == "any" else os.path.isfile(p)
        if self.check_files and not exists:
            self.err(where, f"file not found: {rel}")
        return p

    def build(self):
        d = self.data
        dd = d["disc"]
        label = normalize_label(dd["label"])
        if label != dd["label"]:
            self.warnings.append(f"disc.label normalised to {label!r}")
        vb = dd.get("video_bitrate", "auto")
        disc = Disc(
            label=label,
            standard=dd["standard"],
            aspect=dd["aspect"],
            target=dd.get("target", "DVD5"),
            first_play=dd.get("first_play"),
            title_key=dd.get("title_key"),
            rom_files=[self.file(f"disc.rom_files[{j}]", r, kind="any")
                       for j, r in enumerate(dd.get("rom_files", []))],
            font=self.file("disc.font", dd["font"]) if dd.get("font") else None,
            video_bitrate=None if vb == "auto" else parse_bitrate(vb),
            bluray_target=dd.get("bluray", {}).get("target", "BD25"),
        )
        for j, r in enumerate(disc.rom_files):
            if os.path.basename(r.rstrip(os.sep)).upper() in ("VIDEO_TS", "AUDIO_TS"):
                self.err(f"disc.rom_files[{j}]", "VIDEO_TS / AUDIO_TS are made by oncemore")
        k = STANDARDS[disc.standard][1] / 480
        style = {"size": round(30 * k), "color": "#FFFFFF", "outline": "#000000",
                 "outline_width": 3, "margin": round(36 * k)}
        style.update(dd.get("subtitle_style", {}))
        disc.subtitle_style = style
        if disc.video_bitrate is not None and not 1_000_000 <= disc.video_bitrate <= 8_000_000:
            self.err("disc.video_bitrate", "must be between 1M and 8M")

        titles = []
        self._disc = disc
        for i, t in enumerate(d["titles"]):
            titles.append(self.title(i, t))
        self.unique([t.id for t in titles], "titles")
        self._titles = {t.id: t for t in titles}

        menus = []
        for i, m in enumerate(d.get("menus", [])):
            menus.append(self.menu(i, m, disc))
        user_menu_ids = [m.id for m in menus]

        # first_play / default end actions need to know the menus
        if disc.first_play is None:
            disc.first_play = f"menu:{menus[0].id}" if menus else f"title:{titles[0].id}"
        default_menu = None
        if disc.first_play.startswith("menu:"):
            default_menu = disc.first_play
        elif menus:
            default_menu = f"menu:{menus[0].id}"

        for i, t in enumerate(d["titles"]):
            if "end_action" not in t:
                titles[i].end_action = default_menu or "stop"

        # chapter menus
        for i, t in enumerate(d["titles"]):
            spec = t.get("auto_chapter_menu")
            if spec:
                menus.extend(self.chapter_menus(i, titles[i], {} if spec is True else spec,
                                                disc, default_menu))
        self.unique([m.id for m in menus], "menus")

        # Menu order: the first-play menu (or first menu) becomes PGC 1, the
        # titleset "root" menu. The rest keep their order.
        if disc.first_play.startswith("menu:"):
            fid = disc.first_play[5:]
            menus.sort(key=lambda m: 0 if m.id == fid else 1)
        # (a menu whose buttons wait for its loop point is two PGCs: the intro,
        # then the buttons)
        n = 1
        for m in menus:
            m.number = n
            m.loop_pgc = n + 1 if m.buttons_at_loop else n
            n = m.loop_pgc + 1
        # DVD keeps one video/audio format per titleset: group titles by
        # (aspect, audio codec, channels); the first title's group is
        # titleset 1, which also holds the menus.
        groups = []
        for t in titles:
            t.aspect = t.aspect or disc.aspect
            key = (t.aspect, t.audio_codec, t.audio_channels)
            if key not in groups:
                groups.append(key)
            t.titleset = groups.index(key) + 1
        offset = 0
        for ts in range(1, len(groups) + 1):
            members = [t for t in titles if t.titleset == ts]
            for n, t in enumerate(members, 1):
                t.number = n
                t.global_number = offset + n
            offset += len(members)

        playlists = [self.playlist(i, pl) for i, pl in enumerate(d.get("playlists", []))]
        self.unique([pl.id for pl in playlists], "playlists")
        project = Project(self.path, self.base, disc, titles, menus, self.warnings, playlists)
        self.check_refs(project, user_menu_ids)
        return project

    def unique(self, ids, where):
        seen = set()
        for i in ids:
            if i in seen:
                self.err(where, f"duplicate id {i!r}")
            seen.add(i)

    def title(self, i, t):
        where = f"titles[{i}]"
        chapters, names, posters = [], [], []
        for j, c in enumerate(t.get("chapters", [])):
            spec = c if isinstance(c, dict) else {"time": c}
            try:
                chapters.append(parse_time(spec["time"]))
                posters.append(parse_time(spec["poster"]) if "poster" in spec else None)
            except ValueError as e:
                self.err(f"{where}.chapters[{j}]", str(e))
                continue
            names.append(spec.get("name") or None)
        if not chapters or chapters[0] != 0.0:
            if chapters and min(chapters) > 0:
                chapters.insert(0, 0.0)
                names.insert(0, None)
                posters.insert(0, None)
            elif not chapters:
                chapters, names, posters = [0.0], [None], [None]
        if any(b <= a for a, b in zip(chapters, chapters[1:])):
            self.err(f"{where}.chapters", "chapter times must be strictly increasing")
        audio = t.get("audio", {})
        codec = audio.get("codec", "ac3")
        channels = audio.get("channels", 2)
        bitrate = parse_bitrate(audio.get("bitrate", "448k" if channels == 6 else "192k"))
        if codec == "ac3" and not 64_000 <= bitrate <= 448_000:
            self.err(f"{where}.audio.bitrate", "AC-3 bitrate must be between 64k and 448k")
        if codec == "lpcm" and channels != 2:
            self.err(f"{where}.audio.channels", "5.1 needs AC-3; LPCM is stereo only")
        elif channels == 6 and bitrate < 384_000:
            self.warnings.append(f"{where}.audio.bitrate {bitrate // 1000}k is low for 5.1 "
                                 "(384k or 448k recommended)")
        if codec == "lpcm" and "bitrate" in audio:
            self.warnings.append(f"{where}.audio.bitrate is ignored for lpcm (fixed 1536k)")
        show = None
        clips = []
        if sum(k in t for k in ("source", "slideshow", "clips")) > 1:
            self.err(where, "give one of source, slideshow or clips")
        if "clips" in t:
            for j, c in enumerate(t["clips"]):
                cw = f"{where}.clips[{j}]"
                try:
                    start = parse_time(c.get("in", 0))
                    end = parse_time(c["out"]) if "out" in c else None
                except ValueError as e:
                    self.err(cw, str(e))
                    start, end = 0.0, None
                if end is not None and end <= start:
                    self.err(f"{cw}.out", "must be after in")
                clip = Clip(self.file(f"{cw}.source", c["source"]), start, end)
                if is_image(c["source"]):
                    if "in" in c or "out" in c:
                        self.err(cw, "a still picture has no in or out; give its duration")
                    try:
                        clip.hold = parse_time(c.get("duration", STILL_DEFAULT))
                    except ValueError as e:
                        self.err(f"{cw}.duration", str(e))
                        clip.hold = STILL_DEFAULT
                    if not 0.5 <= clip.hold <= 3600:
                        self.err(f"{cw}.duration", "must be from 0.5 s to 1 hour")
                    clip.start, clip.end, clip.fit = 0.0, None, c.get("fit", "fit")
                elif "duration" in c or "fit" in c:
                    self.err(cw, "duration and fit are for still pictures; a video is "
                                 "trimmed with in and out")
                clips.append(clip)
            source = clips[0].source
            if "audio_tracks" in t:
                self.err(f"{where}.audio_tracks", "a title made of clips uses the clips' own "
                         "sound (one track)")
            if audio.get("passthrough"):
                self.err(f"{where}.audio.passthrough", "clips are joined, so their sound is "
                         "encoded again")
        elif "slideshow" in t:
            show = self.slideshow(where, t["slideshow"])
            # the picture show is rendered into the cache; that file is the source
            tdisc = dataclasses.replace(self._disc, aspect=t.get("aspect") or self._disc.aspect)
            source = slideshow.output_path(self.base, show, tdisc)
            show.auto_chapters = "chapters" not in t
            if "chapters" not in t:
                chapters = show.starts()
                names, posters = [None] * len(chapters), [None] * len(chapters)
        else:
            source = self.file(f"{where}.source", t["source"])
        if "audio_tracks" in t:
            tracks = [AudioTrack(
                source=self.file(f"{where}.audio_tracks[{j}].source", a["source"])
                if a.get("source") else source,
                stream=a.get("stream", 0), lang=a.get("lang"))
                for j, a in enumerate(t["audio_tracks"])]
        else:
            tracks = [AudioTrack(source=source, stream=0, lang=audio.get("lang"))]
        subs = [SubtitleTrack(file=self.file(f"{where}.subtitles[{j}].file", sub["file"]),
                              lang=sub.get("lang"), default=bool(sub.get("default")),
                              position=sub.get("position", "bottom"), color=sub.get("color"))
                for j, sub in enumerate(t.get("subtitles", []))]
        if sum(1 for sub in subs if sub.default) > 1:
            self.err(f"{where}.subtitles", "only one subtitle track can be the default")
        title = Title(
            id=t["id"], name=t.get("name", t["id"]), source=source,
            chapters=chapters, audio_codec=codec, audio_bitrate=bitrate, audio_channels=channels,
            end_action=t.get("end_action", "stop"), audio_tracks=tracks, subtitles=subs,
            remote_menu=t.get("remote_menu"), chapter_names=names, chapter_posters=posters,
            slideshow=show, clips=clips, clip_chapters=bool(clips) and "chapters" not in t,
            video_bitrate=parse_bitrate(t["video_bitrate"]) if "video_bitrate" in t else None,
            audio_passthrough=bool(audio.get("passthrough")),
            aspect=t.get("aspect"),
            scan=t.get("scan", "auto"),
            transcode=t.get("transcode", True),
            picture=self.file(f"{where}.picture", t.get("picture")),
            prohibit=self.prohibit(where, t),
        )
        if title.picture and (clips or show):
            self.err(f"{where}.picture", "a picture is for a title from a sound file")
        if not title.transcode:
            if clips or show:
                self.err(f"{where}.transcode", "only a title from one video file can use its "
                                               "picture as it is")
            for key in ("video_bitrate", "scan"):
                if key in t:
                    self.err(f"{where}.{key}", "the picture is not encoded (transcode: false)")
        if title.scan in ("pulldown", "ivtc") and self._disc.standard != "NTSC":
            self.err(f"{where}.scan", "3:2 pulldown is for NTSC discs (PAL plays film at 25 fps)")
        if title.video_bitrate is not None and not 1_000_000 <= title.video_bitrate <= 8_000_000:
            self.err(f"{where}.video_bitrate", "must be between 1M and 8M")
        if title.audio_passthrough and codec != "ac3":
            self.err(f"{where}.audio.passthrough", "only AC-3 audio can be copied unchanged")
        if title.audio_bps > 8_800_000:
            self.err(f"{where}.audio_tracks",
                     f"{len(tracks)} {codec} tracks need {title.audio_bps / 1e6:.2f} Mbit/s; "
                     "DVD allows 9.8 Mbit/s in total and video needs at least 1")
        return title

    def menu(self, i, m, disc):
        where = f"menus[{i}]"
        size = m.get("font_size", DEFAULT_FONT_SIZE)
        tcolor = m.get("text_color", DEFAULT_TEXT)
        # elements switched off in the Layers panel (`hidden`) are not on the disc
        hidden = {b["id"] for b in m["buttons"] if b.get("hidden")}
        m = dict(m, buttons=[b for b in m["buttons"] if not b.get("hidden")],
                 texts=[t for t in m.get("texts", []) if not t.get("hidden")],
                 shapes=[s for s in m.get("shapes", []) if not s.get("hidden")],
                 images=[p for p in m.get("images", []) if not p.get("hidden")])
        if hidden:
            for b in m["buttons"]:
                if any(v in hidden for v in b.get("nav", {}).values()):
                    b = b.copy()
                    b["nav"] = {k: v for k, v in b["nav"].items() if v not in hidden}
                    m["buttons"] = [b if x["id"] == b["id"] else x for x in m["buttons"]]
            if m.get("default_button") in hidden:
                m = dict(m, default_button=None)
            if not m["buttons"]:
                self.err(f"{where}.buttons", "every button is hidden: a menu needs at least one")
        buttons = [Button(id=b["id"], label=b.get("label", ""), x=b["x"], y=b["y"],
                          action=b["action"], size=b.get("size", size),
                          color=b.get("color", tcolor), nav=dict(b.get("nav", {})),
                          image=self.file(f"{where}.buttons[{j}].image", b.get("image")),
                          auto_activate=bool(b.get("auto_activate")),
                          highlight_image=self.file(f"{where}.buttons[{j}].highlight_image",
                                                    b.get("highlight_image")),
                          **self.style(f"{where}.buttons[{j}]", b),
                          width=b.get("width"), highlight=b.get("highlight", "frame"),
                          override=b.get("override"), audio=b.get("audio"),
                          subtitle=b.get("subtitle"),
                          transition=self.file(f"{where}.buttons[{j}].transition",
                                               b.get("transition")))
                   for j, b in enumerate(m["buttons"])]
        for j, (b, spec) in enumerate(zip(buttons, m["buttons"])):
            if "thumbnail" in spec:
                b.thumb = self.thumbnail(f"{where}.buttons[{j}].thumbnail", b, spec["thumbnail"])
        texts = [Text(text=t["text"], x=t["x"], y=t["y"], size=t.get("size", size),
                      color=t.get("color", tcolor), **self.style(f"{where}.texts[{j}]", t))
                 for j, t in enumerate(m.get("texts", []))]
        for j, b in enumerate(buttons):
            if b.y >= disc.height:
                self.err(f"{where}.buttons[{j}].y", f"must be < {disc.height} for {disc.standard}")
        for j, t in enumerate(texts):
            if t.y >= disc.height:
                self.err(f"{where}.texts[{j}].y", f"must be < {disc.height} for {disc.standard}")
        self.unique([b.id for b in buttons], f"{where}.buttons")
        ids = {b.id for b in buttons}
        for j, b in enumerate(buttons):
            for k, v in b.nav.items():
                if v not in ids:
                    self.err(f"{where}.buttons[{j}].nav.{k}", f"no button {v!r} in this menu")
        loop = m.get("loop", "forever")
        loop = None if loop == "forever" else int(loop)
        loop_point = 0.0
        if "loop_point" in m:
            try:
                loop_point = parse_time(m["loop_point"])
            except ValueError as e:
                self.err(f"{where}.loop_point", str(e))
        fade_in = 0.0
        if "fade_in" in m:
            try:
                fade_in = parse_time(m["fade_in"])
            except ValueError as e:
                self.err(f"{where}.fade_in", str(e))
            if fade_in > 10:
                self.err(f"{where}.fade_in", "a fade-in is at most 10 s")
        # the fade plays once: repeats start after it at the earliest
        loop_point = max(loop_point, fade_in)
        if "end_action" in m and loop is None:
            self.warnings.append(f"{where}.end_action is only used with a loop count")
        if m.get("buttons_at_loop") and not loop_point:
            self.err(f"{where}.buttons_at_loop", "needs a loop point (or a fade-in) to wait for")
        if m.get("default_button") and m["default_button"] not in ids:
            self.err(f"{where}.default_button", f"no button {m['default_button']!r} in this menu")
        return Menu(
            id=m["id"],
            loop=loop, loop_point=loop_point, fade_in=fade_in, end_action=m.get("end_action", "stop"),
            default_button=m.get("default_button"),
            remember_button=m.get("remember_button", True),
            buttons_at_loop=bool(m.get("buttons_at_loop")) and loop_point > 0,
            prohibit=self.prohibit(where, m),
            shapes=[Shape(s["x"], s["y"], s["w"], s["h"], s.get("color", "#00000080"))
                    for s in m.get("shapes", [])],
            images=[Picture(self.file(f"{where}.images[{j}].file", p["file"]), p["x"], p["y"],
                            p["w"], p["h"], p.get("opacity", 1.0))
                    for j, p in enumerate(m.get("images", []))],
            background_video=self.file(f"{where}.background_video", m.get("background_video")),
            background=self.file(f"{where}.background", m.get("background")),
            background_color=m.get("background_color", "#000000"),
            audio=self.file(f"{where}.audio", m.get("audio")),
            duration=float(m.get("duration", 0)) or None,
            highlight_color=m.get("highlight_color", DEFAULT_HIGHLIGHT),
            select_color=m.get("select_color", DEFAULT_SELECT),
            normal_color=m.get("normal_color"),
            texts=texts, buttons=buttons,
        )

    def thumbnail(self, where, button, spec):
        """A button's own thumbnail: a frame of the title / chapter it plays."""
        kind, tid, num = parse_action(button.action)
        title = self._titles.get(tid) if kind in ("title", "chapter") else None
        if title is None:
            self.err(where, "a thumbnail needs a title:... or chapter:... action")
            return None
        chapter = (num or 1) - 1
        if chapter >= len(title.chapters):
            return None                       # (the action itself is reported)
        start = title.chapters[chapter]
        if "time" in spec:
            try:
                time = parse_time(spec["time"])
            except ValueError as e:
                self.err(f"{where}.time", str(e))
                time = start
        else:
            nxt = title.chapters[chapter + 1] if chapter + 1 < len(title.chapters) else start + 2
            time = start + min(1.0, (nxt - start) / 2)
        return Thumb(title.id, time, spec["x"], spec["y"], spec["w"], spec["h"],
                     animated=bool(spec.get("animated")))

    def slideshow(self, where, spec):
        slides = [slideshow.Slide(self.file(f"{where}.slideshow.slides[{j}].image", s["image"]),
                                  float(s.get("duration", 5)), s.get("fit"), s.get("transition"))
                  for j, s in enumerate(spec["slides"])]
        show = slideshow.Slideshow(
            slides=slides, transition=spec.get("transition", "crossfade"),
            transition_duration=float(spec.get("transition_duration", 1.0)),
            pan_zoom=bool(spec.get("pan_zoom")),
            audio=([self.file(f"{where}.slideshow.audio[{j}]", a)
                    for j, a in enumerate(spec["audio"])]
                   if isinstance(spec.get("audio"), list)
                   else self.file(f"{where}.slideshow.audio", spec.get("audio"))),
            background_color=spec.get("background_color", "#000000"),
            fit=spec.get("fit", "fit"), fit_to_audio=bool(spec.get("fit_to_audio")),
            advance=spec.get("advance", "auto"))
        if show.advance == "manual":
            # each picture a moment of video, then a still on the disc; cuts only
            if show.music:
                self.err(f"{where}.slideshow.audio", "a slideshow advanced by hand has no music")
            if spec.get("transition", "none") != "none" or any(
                    s.get("transition", "none") != "none" for s in spec["slides"]):
                self.err(f"{where}.slideshow.transition", "a slideshow advanced by hand "
                                                          "changes pictures with cuts")
            show.transition = "none"
            for s in slides:
                s.duration, s.transition = slideshow.MANUAL_SECONDS, None
        if show.fit_to_audio and not show.music:
            self.err(f"{where}.slideshow.fit_to_audio", "needs music (audio)")
        # (fitted to the music the durations are proportions; fit_to keeps each
        # longer than the fade)
        if show.fade and not show.fit_to_audio and any(s.duration <= show.fade for s in slides):
            self.err(f"{where}.slideshow.transition_duration",
                     "every slide must be longer than the cross-fade")
        return show

    def style(self, where, spec):
        """Per-element text style fields."""
        return {"font": self.file(f"{where}.font", spec.get("font")),
                "outline": spec.get("outline"), "outline_width": spec.get("outline_width", 2),
                "shadow": spec.get("shadow"), "shadow_offset": spec.get("shadow_offset", 3)}

    ITEM_RE = re.compile(r"^([A-Za-z0-9_-]{1,40})(?::([1-9][0-9]*)(?:-([1-9][0-9]*))?)?$")

    def playlist(self, i, pl):
        where = f"playlists[{i}]"
        items = []
        for j, spec in enumerate(pl["items"]):
            m = self.ITEM_RE.match(spec)
            if not m:
                self.err(f"{where}.items[{j}]", f"{spec!r} is not <title>, <title>:<n> or "
                                                 "<title>:<first>-<last>")
                continue
            tid, a, b = m.groups()
            if a is None:
                items.append(PlaylistItem(tid))
            else:
                items.append(PlaylistItem(tid, int(a), int(b) if b else int(a)))
        return Playlist(pl["id"], pl.get("name", pl["id"]), items, pl.get("end_action", "stop"))

    def chapter_menus(self, i, title, spec, disc, default_menu):
        """Expand auto_chapter_menu into one or more pages of thumbnails."""
        where = f"titles[{i}].auto_chapter_menu"
        base_id = spec.get("id", f"chapters_{title.id}")
        back = spec.get("back", default_menu)
        fmt = spec.get("label_format", "Chapter {n}")
        color = spec.get("text_color", DEFAULT_TEXT)
        H = disc.height
        k = H / 480
        thumb_w, thumb_h = disc.width // 4, H // 4
        cols = 3
        gap = (disc.width - 2 * 54 - cols * thumb_w) // (cols - 1)
        row_y = [round(84 * k), round(250 * k)]
        nav_y = round(420 * k)
        n = len(title.chapters)
        pages = [list(range(s, min(s + CHAPTERS_PER_PAGE, n)))
                 for s in range(0, n, CHAPTERS_PER_PAGE)]
        ids = [base_id] + [f"{base_id}_{p}" for p in range(2, len(pages) + 1)]
        heading = spec.get("title", title.name)
        if spec.get("animated_thumbnails") and not spec.get("background_video"):
            self.warnings.append(f"{where}.animated_thumbnails needs background_video; "
                                 "the thumbnails stay still")
        out = []
        for p, chaps in enumerate(pages):
            buttons = []
            for slot, ci in enumerate(chaps):
                col, row = slot % cols, slot // cols
                x = 54 + col * (thumb_w + gap)
                y = row_y[row]
                # grab the thumbnail a little after the chapter start (avoids
                # black frames at cuts); clamped to the media length later
                start = title.chapters[ci]
                nxt = title.chapters[ci + 1] if ci + 1 < n else start + 2.0
                poster = title.chapter_posters[ci] if ci < len(title.chapter_posters) else None
                name = title.chapter_names[ci] if ci < len(title.chapter_names) else None
                buttons.append(Button(
                    id=f"ch{ci + 1}", label=name or fmt.format(n=ci + 1), x=x,
                    y=y + thumb_h + 10, action=f"chapter:{title.id}:{ci + 1}", size=22,
                    color=color,
                    thumb=Thumb(title.id,
                                poster if poster is not None
                                else start + min(1.0, (nxt - start) / 2),
                                x, y, thumb_w, thumb_h,
                                animated=bool(spec.get("animated_thumbnails")))))
            nav_x = 54
            if back:
                buttons.append(Button(id="back", label=spec.get("back_label", "BACK"), x=nav_x,
                                      y=nav_y, action=back, size=26, color=color))
            if p > 0:
                buttons.append(Button(id="prev", label=spec.get("prev_label", "PREV"), x=400,
                                      y=nav_y, action=f"menu:{ids[p - 1]}", size=26, color=color))
            if p + 1 < len(pages):
                buttons.append(Button(id="next", label=spec.get("next_label", "NEXT"), x=560,
                                      y=nav_y, action=f"menu:{ids[p + 1]}", size=26, color=color))
            page_label = f"  ({p + 1}/{len(pages)})" if len(pages) > 1 else ""
            out.append(Menu(
                id=ids[p],
                background_video=self.file(f"{where}.background_video",
                                           spec.get("background_video")),
                background=self.file(f"{where}.background", spec.get("background")),
                background_color=spec.get("background_color", DEFAULT_BG),
                audio=self.file(f"{where}.audio", spec.get("audio")),
                duration=float(spec.get("duration", 0)) or None,
                highlight_color=spec.get("highlight_color", DEFAULT_HIGHLIGHT),
                select_color=spec.get("select_color", DEFAULT_SELECT),
                normal_color=spec.get("normal_color"),
                texts=[Text(heading + page_label, 54, round(30 * k), 32, color)],
                buttons=buttons, generated=True,
            ))
        return out

    def check_refs(self, project, user_menu_ids):
        def check(where, action, allow_chapter=True, allow_resume=False, allow_last=False):
            kind, target, num = parse_action(action)
            if kind == "resume" and not allow_resume:
                self.err(where, "resume is only for menu buttons")
            elif kind == "lastmenu" and not allow_last:
                self.err(where, "lastmenu is only for the end of titles and playlists "
                                "(and overrides)")
            elif kind == "lastmenu" and not project.menus:
                self.err(where, "lastmenu needs a menu")
            elif kind == "menu" and project.menu(target) is None:
                self.err(where, f"no menu with id {target!r}")
            elif kind == "menu" and num and num not in [b.id for b in project.menu(target).buttons]:
                self.err(where, f"menu {target!r} has no button {num!r}")
            elif kind == "audio" and num > len(project.audio_langs):
                self.err(where, f"no audio stream {num} (titles have "
                                f"{len(project.audio_langs)})")
            elif kind == "subtitle" and num > len(project.subtitle_langs):
                self.err(where, f"no subtitle stream {num} (titles have "
                                f"{len(project.subtitle_langs)})")
            elif kind == "playlist" and project.playlist(target) is None:
                self.err(where, f"no playlist with id {target!r}")
            elif kind in ("title", "chapter"):
                t = project.title(target)
                if t is None:
                    self.err(where, f"no title with id {target!r}")
                elif kind == "chapter":
                    if not allow_chapter:
                        self.err(where, "chapter actions are not allowed here")
                    elif num > len(t.chapters):
                        self.err(where, f"title {target!r} has only {len(t.chapters)} chapters")

        check("disc.first_play", project.disc.first_play)
        if project.disc.title_key:
            check("disc.title_key", project.disc.title_key)
            if not project.menus and project.disc.title_key:
                self.warnings.append("disc.title_key needs at least one menu; ignored")
        for i, t in enumerate(project.titles):
            check(f"titles[{i}].end_action", t.end_action, allow_last=True)
            if t.remote_menu and project.menu(t.remote_menu) is None:
                self.err(f"titles[{i}].remote_menu", f"no menu with id {t.remote_menu!r}")
        for m in project.menus:
            where = f"menus[{user_menu_ids.index(m.id)}]" if m.id in user_menu_ids and not m.generated \
                else f"menu {m.id!r}"
            for j, b in enumerate(m.buttons):
                check(f"{where}.buttons[{j}].action", b.action, allow_resume=True)
                for key in ("audio", "subtitle"):
                    n = getattr(b, key)
                    if n is None:
                        continue
                    if parse_action(b.action)[0] in ("audio", "subtitle"):
                        self.err(f"{where}.buttons[{j}].{key}",
                                 "already a stream button: use the action alone")
                    elif n:
                        check(f"{where}.buttons[{j}].{key}", f"{key}:{n}")
                if b.override:
                    if parse_action(b.action)[0] not in ("title", "chapter"):
                        self.err(f"{where}.buttons[{j}].override",
                                 "an override needs a title:... or chapter:... action")
                    check(f"{where}.buttons[{j}].override", b.override, allow_last=True)
                if b.transition:
                    if parse_action(b.action)[0] not in TRANSITION_ACTIONS:
                        self.err(f"{where}.buttons[{j}].transition",
                                 "a link transition needs a link to a menu, title, chapter, "
                                 "playlist or play all")
                    elif is_image(b.transition):
                        self.err(f"{where}.buttons[{j}].transition",
                                 "a link transition is a video (a still picture cannot play)")
            if m.loop is not None:
                check(f"{where}.end_action", m.end_action)
        for i, pl in enumerate(project.playlists):
            check(f"playlists[{i}].end_action", pl.end_action, allow_last=True)
            if not pl.items:
                self.err(f"playlists[{i}].items", "a playlist needs at least one item")
            for j, it in enumerate(pl.items):
                t = project.title(it.title_id)
                if t is None:
                    self.err(f"playlists[{i}].items[{j}]", f"no title with id {it.title_id!r}")
                    continue
                n = len(t.chapters)
                last = it.last or n
                if not it.first <= last <= n:
                    self.err(f"playlists[{i}].items[{j}]",
                             f"title {t.id!r} has chapters 1-{n}; {it.first}-{last} is not a range "
                             "of them")
                elif it.last == n:
                    it.last = None          # to the end: the title's own end
        if project.titles:
            from . import author
            if project.uses_resume and author.resume_reg(project) is None:
                self.err("menus", "a resume button needs one free player register, and "
                                  "this disc uses them all (fewer menus that remember "
                                  "their last button would free one)")
            if project.titleset_count > 1 and not project.menus and author.end_chapters(project):
                self.err("titles", "on a disc with several titlesets, an end action that goes "
                                   "to a chapter needs a menu (its route goes through the "
                                   "disc's title menu)")
            if project.entry_buttons and author.entry_reg(project) is None:
                self.err("menus", "links to a menu button need one free player register, "
                                  "and this disc uses them all (fewer menus that remember "
                                  "their last button would free one)")
            if project.uses_last_menu and author.last_menu_reg(project) is None:
                self.err("menus", "returning to the last menu needs one free player register, "
                                  "and this disc uses them all (fewer menus that remember "
                                  "their last button would free one)")
            if project.overrides and author.override_reg(project) is None:
                self.err("menus", "end-action overrides need one free player register, and "
                                  "this disc uses them all (fewer menus that remember "
                                  "their last button would free one)")
        for kind, attr in (("audio", "audio_tracks"), ("subtitle", "subtitles")):
            seen = {}
            for i, t in enumerate(project.titles):
                for j, tr in enumerate(getattr(t, attr)):
                    if tr.lang and seen.setdefault(j, tr.lang) != tr.lang:
                        self.err(f"titles[{i}].{attr}[{j}].lang",
                                 f"{kind} stream {j + 1} is {seen[j]!r} in another title; "
                                 "stream languages are shared by all titles on the disc")

