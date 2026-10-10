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
    """'menu:x' -> ('menu', 'x', None); 'chapter:t:2' -> ('chapter', 't', 2); 'stop';
    'audio:2' -> ('audio', None, 2); 'subtitle:off' -> ('subtitle', None, 0)."""
    if s == "stop":
        return ("stop", None, None)
    kind, _, rest = s.partition(":")
    if kind == "chapter":
        tid, _, n = rest.rpartition(":")
        return ("chapter", tid, int(n))
    if kind in ("audio", "subtitle"):
        return (kind, None, 0 if rest == "off" else int(rest))
    return (kind, rest, None)


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

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


@dataclass
class Title:
    id: str
    name: str
    source: str
    chapters: list
    audio_codec: str = "ac3"
    audio_bitrate: int = 192_000
    end_action: str = "stop"
    number: int = 0  # 1-based title number on the disc
    audio_tracks: list = field(default_factory=list)
    subtitles: list = field(default_factory=list)
    aspect: str = None       # display aspect of this title (default: the disc's)
    titleset: int = 1        # DVD titleset (VTS) holding this title
    global_number: int = 0   # title number as players show it (VMGM order)

    @property
    def track_bps(self):
        # LPCM 48 kHz / 16 bit / stereo
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


@dataclass
class Thumb:
    title_id: str
    time: float
    x: int
    y: int
    w: int
    h: int


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
    width: int = None          # its width on the 720-wide grid (None = natural)
    highlight: str = "frame"   # image buttons: "frame" | "shape"


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


@dataclass
class Project:
    path: str
    base_dir: str
    disc: Disc
    titles: list
    menus: list
    warnings: list = field(default_factory=list)

    def title(self, tid):
        return next((t for t in self.titles if t.id == tid), None)

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

    def err(self, where, msg):
        self.issues.append({"path": where, "message": msg})

    def file(self, where, rel):
        if rel is None:
            return None
        p = os.path.normpath(os.path.join(self.base, os.path.expanduser(rel)))
        if self.check_files and not os.path.isfile(p):
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
            font=self.file("disc.font", dd["font"]) if dd.get("font") else None,
            video_bitrate=None if vb == "auto" else parse_bitrate(vb),
        )
        k = STANDARDS[disc.standard][1] / 480
        style = {"size": round(30 * k), "color": "#FFFFFF", "outline": "#000000",
                 "outline_width": 3, "margin": round(36 * k)}
        style.update(dd.get("subtitle_style", {}))
        disc.subtitle_style = style
        if disc.video_bitrate is not None and not 1_000_000 <= disc.video_bitrate <= 8_000_000:
            self.err("disc.video_bitrate", "must be between 1M and 8M")

        titles = []
        for i, t in enumerate(d["titles"]):
            titles.append(self.title(i, t))
        self.unique([t.id for t in titles], "titles")

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
        for n, m in enumerate(menus, 1):
            m.number = n
        # DVD keeps one video/audio format per titleset: group titles by
        # (aspect, audio codec); the first title's group is titleset 1, which
        # also holds the menus.
        groups = []
        for t in titles:
            t.aspect = t.aspect or disc.aspect
            key = (t.aspect, t.audio_codec)
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

        project = Project(self.path, self.base, disc, titles, menus, self.warnings)
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
        chapters = []
        for j, c in enumerate(t.get("chapters", [])):
            try:
                chapters.append(parse_time(c))
            except ValueError as e:
                self.err(f"{where}.chapters[{j}]", str(e))
        if not chapters or chapters[0] != 0.0:
            if chapters and min(chapters) > 0:
                chapters.insert(0, 0.0)
            elif not chapters:
                chapters = [0.0]
        if any(b <= a for a, b in zip(chapters, chapters[1:])):
            self.err(f"{where}.chapters", "chapter times must be strictly increasing")
        audio = t.get("audio", {})
        codec = audio.get("codec", "ac3")
        bitrate = parse_bitrate(audio.get("bitrate", "192k"))
        if codec == "ac3" and not 64_000 <= bitrate <= 448_000:
            self.err(f"{where}.audio.bitrate", "AC-3 bitrate must be between 64k and 448k")
        if codec == "lpcm" and "bitrate" in audio:
            self.warnings.append(f"{where}.audio.bitrate is ignored for lpcm (fixed 1536k)")
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
                              lang=sub.get("lang"), default=bool(sub.get("default")))
                for j, sub in enumerate(t.get("subtitles", []))]
        if sum(1 for sub in subs if sub.default) > 1:
            self.err(f"{where}.subtitles", "only one subtitle track can be the default")
        title = Title(
            id=t["id"], name=t.get("name", t["id"]), source=source,
            chapters=chapters, audio_codec=codec, audio_bitrate=bitrate,
            end_action=t.get("end_action", "stop"), audio_tracks=tracks, subtitles=subs,
            aspect=t.get("aspect"),
        )
        if title.audio_bps > 8_800_000:
            self.err(f"{where}.audio_tracks",
                     f"{len(tracks)} {codec} tracks need {title.audio_bps / 1e6:.2f} Mbit/s; "
                     "DVD allows 9.8 Mbit/s in total and video needs at least 1")
        return title

    def menu(self, i, m, disc):
        where = f"menus[{i}]"
        size = m.get("font_size", DEFAULT_FONT_SIZE)
        tcolor = m.get("text_color", DEFAULT_TEXT)
        buttons = [Button(id=b["id"], label=b.get("label", ""), x=b["x"], y=b["y"],
                          action=b["action"], size=b.get("size", size),
                          color=b.get("color", tcolor), nav=dict(b.get("nav", {})),
                          image=self.file(f"{where}.buttons[{j}].image", b.get("image")),
                          width=b.get("width"), highlight=b.get("highlight", "frame"))
                   for j, b in enumerate(m["buttons"])]
        texts = [Text(text=t["text"], x=t["x"], y=t["y"], size=t.get("size", size),
                      color=t.get("color", tcolor)) for t in m.get("texts", [])]
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
        return Menu(
            id=m["id"],
            background_video=self.file(f"{where}.background_video", m.get("background_video")),
            background=self.file(f"{where}.background", m.get("background")),
            background_color=m.get("background_color", "#000000"),
            audio=self.file(f"{where}.audio", m.get("audio")),
            duration=float(m.get("duration", 0)) or None,
            highlight_color=m.get("highlight_color", DEFAULT_HIGHLIGHT),
            select_color=m.get("select_color", DEFAULT_SELECT),
            texts=texts, buttons=buttons,
        )

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
                buttons.append(Button(
                    id=f"ch{ci + 1}", label=fmt.format(n=ci + 1), x=x, y=y + thumb_h + 10,
                    action=f"chapter:{title.id}:{ci + 1}", size=22, color=color,
                    thumb=Thumb(title.id, start + min(1.0, (nxt - start) / 2),
                                x, y, thumb_w, thumb_h)))
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
                background=self.file(f"{where}.background", spec.get("background")),
                background_color=spec.get("background_color", DEFAULT_BG),
                audio=self.file(f"{where}.audio", spec.get("audio")),
                duration=float(spec.get("duration", 0)) or None,
                highlight_color=spec.get("highlight_color", DEFAULT_HIGHLIGHT),
                select_color=spec.get("select_color", DEFAULT_SELECT),
                texts=[Text(heading + page_label, 54, round(30 * k), 32, color)],
                buttons=buttons, generated=True,
            ))
        return out

    def check_refs(self, project, user_menu_ids):
        def check(where, action, allow_chapter=True):
            kind, target, num = parse_action(action)
            if kind == "menu" and project.menu(target) is None:
                self.err(where, f"no menu with id {target!r}")
            elif kind == "audio" and num > len(project.audio_langs):
                self.err(where, f"no audio stream {num} (titles have "
                                f"{len(project.audio_langs)})")
            elif kind == "subtitle" and num > len(project.subtitle_langs):
                self.err(where, f"no subtitle stream {num} (titles have "
                                f"{len(project.subtitle_langs)})")
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
        for i, t in enumerate(project.titles):
            check(f"titles[{i}].end_action", t.end_action)
        for m in project.menus:
            where = f"menus[{user_menu_ids.index(m.id)}]" if m.id in user_menu_ids and not m.generated \
                else f"menu {m.id!r}"
            for j, b in enumerate(m.buttons):
                check(f"{where}.buttons[{j}].action", b.action)
        for kind, attr in (("audio", "audio_tracks"), ("subtitle", "subtitles")):
            seen = {}
            for i, t in enumerate(project.titles):
                for j, tr in enumerate(getattr(t, attr)):
                    if tr.lang and seen.setdefault(j, tr.lang) != tr.lang:
                        self.err(f"titles[{i}].{attr}[{j}].lang",
                                 f"{kind} stream {j + 1} is {seen[j]!r} in another title; "
                                 "stream languages are shared by all titles on the disc")

