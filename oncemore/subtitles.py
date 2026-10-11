"""Subtitles: SRT / WebVTT / ASS -> DVD subpicture streams (muxed with vtskit).

Each cue is drawn with drawtext (white text, dark outline) on a transparent
square-pixel canvas, squeezed to DVD width exactly like menu text, read back
as RGBA and reduced to the 4 colours a DVD subpicture can hold:

  0 transparent, 1 fill, 2 outline, 3 anti-aliasing (between fill and outline)

The bitmaps are cropped to their bounding box and placed with an offset;
`mux_streams` turns them into subpicture packs of the title's program stream
(vtskit.subtitles, as spumux did) and gathers the title's palette, the 16
colours its subpictures draw with.

An image script's subtitles are pictures instead (Cue.image): read in their
own colours (a picture without transparency has its corner colour keyed
out), fitted to the frame and reduced to the colours the disc allows.
"""

import collections
import concurrent.futures
import dataclasses
import json
import os
import re
import subprocess
from dataclasses import dataclass
from xml.sax.saxutils import quoteattr

from . import png4, tools
from .errors import OncemoreError, ProjectError, ToolFailedError

_TIME = re.compile(r"(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})")
_TAG = re.compile(r"</?[a-zA-Z][^>]*>|\{\\[^}]*\}")


@dataclass
class Cue:
    start: float
    end: float
    lines: list
    position: str = None   # "top" | "bottom" | None (the track's / default)
    color: str = None      # "#RRGGBB" fill colour from the cue itself, or None
    style_color: str = None  # the subtitle file's style colour (after the track's)
    image: str = None      # an image script's picture (absolute path): no text


_AN = re.compile(r"\\an?(\d)")
_ASS_COLOR = re.compile(r"\\1?c&H([0-9A-Fa-f]{2,8})&?")
_FONT_COLOR = re.compile(r'<font[^>]*color\s*=\s*"?#?([0-9A-Fa-f]{6})"?', re.I)


def _style_of(text):
    r"""(position, colour) from override tags in a cue's text: ASS-style {\an8}
    (also common in SRT) and {\c&HBBGGRR&}, or SRT <font color="#RRGGBB">."""
    pos = color = None
    for block in re.findall(r"\{([^}]*)\}", text):
        m = _AN.search(block)
        if m:
            n = int(m.group(1))
            # \an7-9 = top (numpad layout); the legacy \a5-7,9-11 also mean top
            pos = "top" if (n in (7, 8, 9) if "an" in block else n >= 5) else "bottom"
        m = _ASS_COLOR.search(block)
        if m:
            bgr = m.group(1)[-6:].rjust(6, "0")
            color = "#" + (bgr[4:6] + bgr[2:4] + bgr[0:2]).upper()
    m = _FONT_COLOR.search(text)
    if m:
        color = "#" + m.group(1).upper()
    return pos, color

def _t(m):
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_srt(text, vtt=False):
    """Parse SubRip (or, with vtt=True, WebVTT) text into a sorted list of
    non-overlapping Cues."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if vtt:
        text = _VTT_TIME.sub(lambda m: "00:" + m.group(0), text)   # MM:SS.mmm -> H:MM:SS.mmm
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.split("\n")
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        times = _TIME.findall(lines[idx])
        if len(times) < 2:
            raise ValueError(f"bad SRT timing line: {lines[idx]!r}")
        start = _t(_TIME.match(":".join(times[0][:3]) + "," + times[0][3]))
        end = _t(_TIME.match(":".join(times[1][:3]) + "," + times[1][3]))
        raw_body = lines[idx + 1:]
        pos, color = _style_of("\n".join(raw_body))
        if pos is None and vtt:
            m = re.search(r"\bline:(-?\d+(?:\.\d+)?)(%?)", lines[idx])
            if m:
                v = float(m.group(1))
                pos = "top" if (0 <= v < 50 if m.group(2) else 0 <= v < 6) else "bottom"
        body = [_TAG.sub("", l).strip() for l in raw_body]
        body = [l for l in body if l]
        if body and end > start:
            cues.append(Cue(start, end, body, pos, color))
    return _tidy(cues)


def _tidy(cues):
    cues.sort(key=lambda c: c.start)
    # a subpicture stream shows one image at a time: clip overlaps
    for a, b in zip(cues, cues[1:]):
        if a.end > b.start:
            a.end = b.start
    return [c for c in cues if c.end - c.start >= 0.04]


_VTT_TIME = re.compile(r"(?<![\d:])\d{1,2}:\d{2}\.\d{3}")


def parse_vtt(text):
    if not text.lstrip("\ufeff").startswith("WEBVTT"):
        raise ValueError("not a WebVTT file (no WEBVTT header)")
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    keep = [b for b in blocks if "-->" in b]          # drop header, NOTE and STYLE blocks
    return parse_srt("\n\n".join(keep), vtt=True)


def parse_ass(text):
    """Dialogue lines of an ASS / SSA script (styles: alignment and colour)."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    styles, fmt, sfmt, cues = {}, None, None, []
    section = ""
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("["):
            section = line.lower()
            continue
        key, _, val = line.partition(":")
        if "styles" in section and key == "Format":
            sfmt = [x.strip().lower() for x in val.split(",")]
        elif "styles" in section and key == "Style" and sfmt:
            f = dict(zip(sfmt, [x.strip() for x in val.split(",", len(sfmt) - 1)]))
            align = int(f.get("alignment", "2") or 2)
            colour = f.get("primarycolour", "")
            styles[f.get("name", "")] = (
                "top" if align in (7, 8, 9) else None,
                _style_of("{\\c" + colour + "&}")[1] if colour.startswith("&H") else None)
        elif "events" in section and key == "Format":
            fmt = [x.strip().lower() for x in val.split(",")]
        elif "events" in section and key == "Dialogue" and fmt:
            f = dict(zip(fmt, [x.strip() for x in val.split(",", len(fmt) - 1)]))
            try:
                start = _t(_TIME.match(f["start"].replace(".", ",") + "0"))
                end = _t(_TIME.match(f["end"].replace(".", ",") + "0"))
            except (KeyError, AttributeError):
                raise ValueError(f"bad ASS dialogue line: {line[:60]!r}")
            raw = f.get("text", "")
            spos, scol = styles.get(f.get("style", ""), (None, None))
            pos, color = _style_of(raw)
            body = re.sub(r"\{[^}]*\}", "", raw).replace("\\h", " ")
            body = [l.strip() for l in re.split(r"\\[Nn]", body) if l.strip()]
            if body and end > start:
                cues.append(Cue(start, end, body, pos or spos, color, scol))
    if fmt is None:
        raise ValueError("no [Events] Format line: not an ASS / SSA script")
    return _tidy(cues)


# -- text scripts ---------------------------------------------------------------
# The plain subtitle script of disc authoring tools: a number, the start and
# end timecode, the text; lines after it (up to the next numbered line) are
# more lines of the same subtitle. Spaces or tabs between the fields.
#   1 00;00;02;02 00;00;03;15 The cat never came back.
#   She just walked away.
# Timecode: hh;mm;ss;ff is NTSC drop frame; hh:mm:ss:ff counts frames of 30
# (NTSC, non drop frame) or 25 (PAL); leading zeros may be left out. A time
# hh:mm:ss,mmm (or .mmm) is read too.
_TC = TIMECODE = re.compile(r"^(\d{1,2})([:;])(\d{1,2})([:;])(\d{1,2})([:;.,])(\d{1,3})$")
_SCRIPT_LINE = re.compile(r"^\s*(\d+)[ \t]+(\S+)[ \t]+(\S+)(?:[ \t]+(.*))?$")
# an image script: the same lines with a picture file instead of the text
#   1 00;00;02;02 00;00;03;15 sub0001.png
IMAGE_FILE = re.compile(r"\.(png|bmp|tiff?|jpe?g|webp)$", re.I)


def timecode_seconds(tc, standard="NTSC"):
    """Seconds from a timecode of the disc's `standard`."""
    m = _TC.match(str(tc).strip())
    if not m:
        raise ValueError(f"{tc!r} is not a timecode (hh;mm;ss;ff or hh:mm:ss:ff)")
    h, mi, s, last, f = int(m[1]), int(m[3]), int(m[5]), m[6], m[7]
    if mi > 59 or s > 59:
        raise ValueError(f"{tc!r}: minutes and seconds go to 59")
    if last in ".,":
        return h * 3600 + mi * 60 + s + int(f.ljust(3, "0")) / 1000
    f = int(f)
    drop = ";" in (m[2], m[4], last)
    base = 30 if drop or standard == "NTSC" else 25
    if f >= base:
        raise ValueError(f"{tc!r}: frame {f} of {base}")
    frames = (h * 3600 + mi * 60 + s) * base + f
    if drop:
        # two frame numbers are left out every minute, except every tenth
        minutes = h * 60 + mi
        frames -= 2 * (minutes - minutes // 10)
    return frames * 1001 / 30000 if base == 30 else frames / 25


def seconds_timecode(t, standard="NTSC"):
    """The timecode of a moment: drop frame on NTSC (;), frames of 25 on PAL (:)."""
    if standard != "NTSC":
        frames = int(round(t * 25))
        f, s = frames % 25, frames // 25
        return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"
    frames = int(round(t * 30000 / 1001))
    # (drop frame: 17982 frames per ten minutes, 1798 in each but the first minute)
    tens, rest = divmod(frames, 17982)
    frames += 18 * tens + (2 * ((rest - 2) // 1798) if rest > 1 else 0)
    f, s = frames % 30, frames // 30
    return f"{s // 3600:02d};{s // 60 % 60:02d};{s % 60:02d};{f:02d}"


def parse_text_script(text, standard="NTSC", base=None):
    """Cues of a text script. With `base` (the script's folder), a subtitle
    whose text is just a picture file's name (relative to it) is that
    picture: an image script."""
    cues, cur = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        m = _SCRIPT_LINE.match(line)
        if m and _TC.match(m[2]) and _TC.match(m[3]):
            try:
                start, end = timecode_seconds(m[2], standard), timecode_seconds(m[3], standard)
            except ValueError as e:
                raise ValueError(f"line {n}: {e}")
            if end <= start:
                raise ValueError(f"line {n}: subtitle {m[1]} ends before it starts")
            cur = Cue(start, end, [m[4].strip()] if m[4] and m[4].strip() else [])
            cues.append(cur)
        elif line and cur is not None:
            cur.lines.append(line)
        elif line:
            raise ValueError(f"line {n}: expected \"number start end text\", got {line[:40]!r}")
    if not cues:
        raise ValueError("no subtitles (lines of number, start and end timecode, text)")
    if base is not None:
        for n, c in enumerate(cues, 1):
            if len(c.lines) == 1 and IMAGE_FILE.search(c.lines[0]):
                path = os.path.normpath(os.path.join(base, c.lines[0]))
                if not os.path.isfile(path):
                    raise ValueError(f"subtitle {n}: picture {c.lines[0]!r} not found next to "
                                     "the script")
                c.image, c.lines = path, []
    return _tidy([c for c in cues if c.lines or c.image])


def to_text_script(cues, standard="NTSC"):
    """Cues -> a text script (no positions or colours: a script has none)."""
    out = []
    for n, c in enumerate(cues, 1):
        # (a picture: its file name, as an image script has it)
        lines = [os.path.basename(c.image)] if c.image else list(c.lines) or [""]
        out.append(f"{n}\t{seconds_timecode(c.start, standard)}\t"
                   f"{seconds_timecode(c.end, standard)}\t{lines[0]}")
        out += lines[1:]
    return "\n".join(out) + "\n"


def shifted(cues, offset):
    """Cues `offset` seconds earlier (a script timed against a source's own
    timecode, e.g. one starting at 01;00;00;00); what ends before 0 goes."""
    if not offset:
        return cues
    out = []
    for c in cues:
        if c.end - offset > 0:
            out.append(dataclasses.replace(c, start=max(0.0, c.start - offset),
                                           end=c.end - offset))
    return out


PARSERS = {".srt": parse_srt, ".vtt": parse_vtt, ".ass": parse_ass, ".ssa": parse_ass,
           ".txt": parse_text_script}


def load_subtitles(path, standard="NTSC"):
    """Cues of a subtitle file (timecodes of a text script are the disc
    `standard`'s)."""
    ext = os.path.splitext(path)[1].lower()
    parse = PARSERS.get(ext, parse_srt)
    if ext == ".txt":
        base = os.path.dirname(os.path.abspath(path))
        parse = lambda text: parse_text_script(text, standard, base)     # noqa: E731
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "cp932", "latin-1"):
        try:
            return parse(raw.decode(enc))
        except UnicodeDecodeError:
            continue
        except ValueError as e:
            raise ProjectError(f"{path}: {e}")
    raise ProjectError(f"{path}: cannot decode subtitle file")


load_srt = load_subtitles   # older name


def to_srt(cues):
    """Cues -> SubRip text (the app's subtitle editor saves SRT)."""
    def ts(t):
        ms = int(round(t * 1000))
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        sec, ms = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    out = []
    # (an image script's pictures have no text for SubRip)
    for n, c in enumerate([c for c in cues if c.lines], 1):
        lines = list(c.lines)
        if c.position == "top":
            lines[0] = "{\\an8}" + lines[0]
        if c.color:
            lines = [f'<font color="{c.color}">{l}</font>' for l in lines]
        out.append(f"{n}\n{ts(c.start)} --> {ts(c.end)}\n" + "\n".join(lines) + "\n")
    return "\n".join(out)


def _ts(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:06.3f}"


class SubtitleRenderer:
    """Renders cues for one disc format with one font (relative to `work`)."""

    def __init__(self, disc, work, font_name, display_width, style):
        self.disc = disc
        self.work = work
        self.font = font_name
        self.dw = display_width
        self.style = style
        self.ffmpeg = tools.find("ffmpeg")
        self.colours = set()      # every visible subpicture colour drawn (DVD: 15 at most)

    def _filter(self, cue, base, position="bottom"):
        st = self.style
        size, gap = st["size"], int(st["size"] * 1.25)
        H = self.disc.height
        n = len(cue.lines)
        parts = []
        for i in range(n):
            tf = f"{base}.l{i}.txt"
            with open(os.path.join(self.work, tf), "w", encoding="utf-8") as f:
                f.write(cue.lines[i])
            if (cue.position or position) == "top":
                y = st["margin"] + i * gap
            else:
                y = H - st["margin"] - (n - i) * gap
            # always white on black here: the quantiser sorts pixels by brightness,
            # and the real colours go into the PNG palette (see stream_xml)
            parts.append(
                f"drawtext=fontfile={self.font}:textfile={tf}:expansion=none:fontsize={size}:"
                f"fontcolor=white:borderw={st['outline_width']}:"
                f"bordercolor=black:x=(w-text_w)/2:y={y}")
        parts.append(f"scale={self.disc.width}:{H}:flags=lanczos,format=rgba")
        return ",".join(parts)

    def render(self, cue, base, position="bottom"):
        """Return (canvas, x, y) — the cropped 2-bit bitmap and its offset."""
        return quantise(self.render_rgba(cue, base, position), self.disc.width,
                        self.disc.height)

    def render_picture(self, cue, base, position="bottom"):
        """An image script's picture as (canvas, x, y, palette): its own
        colours, at most three besides transparent (a DVD subpicture's)."""
        idx, w, h, x, y, colours = reduce_colours(self.image_rgba(cue, position),
                                                  self.disc.width, self.disc.height, 3, even=True)
        if idx is None:
            return None, 0, 0, None
        c = png4.Canvas(w, h)
        c.pixels[:] = idx
        return c, x, y, [(0, 0, 0, 0)] + colours + [(0, 0, 0, 0)] * (3 - len(colours))

    def render_rgba(self, cue, base, position="bottom"):
        """The cue drawn white with a black outline on a transparent frame
        (RGBA bytes, disc width x height)."""
        W, H = self.disc.width, self.disc.height
        cmd = [self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
               f"color=c=black@0.0:s={self.dw}x{H}:r=1:d=1,format=rgba",
               "-vf", self._filter(cue, base, position), "-frames:v", "1", "-f", "rawvideo",
               "-pix_fmt", "rgba", "pipe:1"]
        p = subprocess.run(cmd, cwd=self.work, capture_output=True, timeout=300)
        if p.returncode != 0 or len(p.stdout) < W * H * 4:
            raise ToolFailedError("ffmpeg could not render a subtitle",
                                  details={"output": tools.tail(p.stderr.decode("utf-8", "replace"))})
        return p.stdout[:W * H * 4]

    def image_rgba(self, cue, position="bottom"):
        """An image script's picture on a transparent frame (RGBA bytes, disc
        width x height): a picture the size of a video frame (480, 576, 720
        or 1080 lines, at least as wide as high) fills the frame; a smaller
        one keeps its size (in square pixels) and is centred at the bottom
        (or top) margin. One with no transparency has the colour of its top
        left corner keyed out, as subtitle pictures usually do."""
        W, H = self.disc.width, self.disc.height
        w, h, rgba = read_picture(cue.image)
        alpha = rgba[3::4]
        key = rgba[:3] if alpha.count(255) == len(alpha) else None
        chain = ["format=rgba"]
        if key:
            chain.append(f"colorkey=0x{key.hex()}:0.01:0")
        if h in (480, 576, 720, 1080) and w >= h:
            chain.append(f"scale={W}:{H}:flags=bicubic")
        else:
            # square pixels to the frame's (DVD pixels are not square)
            sw = max(2, round(w * W / self.dw))
            k = min(1.0, (W - 8) / sw, (H - 8) / h)
            sw, sh = max(2, round(sw * k)), max(2, round(h * k))
            margin = self.style["margin"]
            top = (cue.position or position) == "top"
            y = min(margin, H - sh) if top else max(0, H - margin - sh)
            chain += [f"scale={sw}:{sh}:flags=bicubic",
                      f"pad={W}:{H}:{(W - sw) // 2}:{y}:color=black@0.0"]
        cmd = [self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", cue.image,
               "-vf", ",".join(chain), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba",
               "pipe:1"]
        p = subprocess.run(cmd, capture_output=True, timeout=300)
        if p.returncode != 0 or len(p.stdout) < W * H * 4:
            raise ToolFailedError(f"ffmpeg could not read {os.path.basename(cue.image)}",
                                  details={"output": tools.tail(p.stderr.decode("utf-8", "replace"))})
        return p.stdout[:W * H * 4]

    def stream_xml(self, cues, lang, index, position="bottom", color=None):
        """Render every cue and write the spumux XML for one stream. `position`
        and `color` are the track's defaults; cues may override them."""
        base = f"sub{index}_{lang}"
        jobs = {}
        workers = min(8, os.cpu_count() or 2)
        with concurrent.futures.ThreadPoolExecutor(workers) as pool:
            for n, cue in enumerate(cues):
                jobs[n] = pool.submit(self.render_picture if cue.image else self.render, cue,
                                      f"{base}_{n:05d}", position)
            results = {n: f.result() for n, f in jobs.items()}

        def palette(fill):
            return [(0, 0, 0, 0), png4.parse_color(fill), png4.parse_color(self.style["outline"]),
                    _mix(fill, self.style["outline"])]
        lines = [f'<subpictures format="{self.disc.standard}">', "  <stream>"]
        for n, cue in enumerate(cues):
            canvas, x, y, *own = results[n]
            if canvas is None:
                continue
            name = f"{base}_{n:05d}.png"
            colours = own[0] if own else palette(cue.color or color or cue.style_color
                                                 or self.style["color"])
            self.colours.update(c for c in colours if c[3])
            png4.write_indexed_png(os.path.join(self.work, name), canvas, colours)
            lines.append(f'    <spu start="{_ts(cue.start)}" end="{_ts(cue.end)}" '
                         f'image={quoteattr(name)} xoffset="{x}" yoffset="{y}"/>')
        lines += ["  </stream>", "</subpictures>", ""]
        path = os.path.join(self.work, f"{base}.spumux.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path


def read_picture(path):
    """(width, height, RGBA bytes) of a picture file, at its own size."""
    ffprobe = tools.find("ffprobe")
    p = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "json", path],
                       capture_output=True, text=True, timeout=120)
    try:
        s = json.loads(p.stdout)["streams"][0]
        w, h = int(s["width"]), int(s["height"])
    except (ValueError, KeyError, IndexError):
        raise ProjectError(f"{path}: not a picture ffmpeg can read")
    q = subprocess.run([tools.find("ffmpeg"), "-hide_banner", "-nostdin", "-v", "error", "-i",
                        path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"],
                       capture_output=True, timeout=300)
    if q.returncode != 0 or len(q.stdout) < w * h * 4:
        raise ProjectError(f"{path}: not a picture ffmpeg can read")
    return w, h, q.stdout[:w * h * 4]


def reduce_colours(rgba, W, H, most, even=False, alpha_steps=None):
    """A picture (RGBA bytes, W x H) cropped to what is visible and reduced
    to at most `most` colours: (index bytes, w, h, x, y, [(r, g, b, a)]),
    index 0 transparent and k the k-th colour; (None, ...) when nothing
    shows. The commonest colours are kept and every other pixel takes the
    nearest of them. Opacity is all or nothing, or with `alpha_steps` kept
    in that many steps; `even` starts the crop on even lines and columns
    (a DVD subpicture's)."""
    alpha = rgba[3::4]
    vis = alpha.translate(_OPAQUE if alpha_steps is None else _SEEN)
    first, last = vis.find(1), vis.rfind(1)
    if first < 0:
        return None, 0, 0, 0, 0, []
    y0, y1 = first // W, last // W
    x0, x1 = W, -1
    for yy in range(y0, y1 + 1):
        row = vis[yy * W:(yy + 1) * W]
        a, b = row.find(1), row.rfind(1)
        if a >= 0:
            x0, x1 = min(x0, a), max(x1, b)
    if even:
        x0, y0 = x0 - x0 % 2, y0 - y0 % 2
    w, h = x1 - x0 + 1, y1 - y0 + 1
    if even:
        w, h = min(w + w % 2, W - x0), min(h + h % 2, H - y0)
    pixels = []
    for yy in range(y0, y0 + h):
        for xx in range(x0, x0 + w):
            i = yy * W + xx
            if not vis[i]:
                pixels.append(None)
                continue
            j = 4 * i
            a = 255 if alpha_steps is None else \
                min(255, round(round(alpha[i] * (alpha_steps - 1) / 255) * 255 / (alpha_steps - 1)))
            pixels.append((rgba[j], rgba[j + 1], rgba[j + 2], a))
    counts = collections.Counter(p for p in pixels if p)
    keep = [c for c, _ in counts.most_common(most)]
    index = {c: k for k, c in enumerate(keep, 1)}

    def nearest(c):
        k = min(range(len(keep)), key=lambda k: sum((u - v) ** 2 for u, v in zip(c, keep[k])))
        index[c] = k + 1
        return k + 1
    idx = bytes(0 if p is None else index.get(p) or nearest(p) for p in pixels)
    return idx, w, h, x0, y0, keep


def _mix(a, b):
    ca, cb = png4.parse_color(a), png4.parse_color(b)
    return tuple((x + y) // 2 for x, y in zip(ca[:3], cb[:3])) + (255,)


_OPAQUE = bytes(1 if a >= 96 else 0 for a in range(256))
_SEEN = bytes(1 if a >= 16 else 0 for a in range(256))


def quantise(rgba, W, H):
    """RGBA bytes -> (Canvas cropped to content, x, y) or (None, 0, 0)."""
    mask = rgba[3::4].translate(_OPAQUE)       # C-speed: 1 where visible
    first, last = mask.find(1), mask.rfind(1)
    if first < 0:
        return None, 0, 0
    y0, y1 = first // W, last // W
    x0, x1 = W, -1
    for y in range(y0, y1 + 1):
        row = mask[y * W:(y + 1) * W]
        a, b = row.find(1), row.rfind(1)
        if a >= 0:
            x0, x1 = min(x0, a), max(x1, b)
    x0 -= x0 % 2
    y0 -= y0 % 2
    w = x1 - x0 + 1
    h = y1 - y0 + 1
    w, h = min(w + w % 2, W - x0), min(h + h % 2, H - y0)
    c = png4.Canvas(w, h)
    px = c.pixels
    for yy in range(h):
        base = (y0 + yy) * W + x0
        for xx in range(w):
            i = base + xx
            if not mask[i]:
                continue
            j = 4 * i
            lum = (rgba[j] * 299 + rgba[j + 1] * 587 + rgba[j + 2] * 114) // 1000
            px[yy * w + xx] = 1 if lum >= 170 else (2 if lum <= 85 else 3)
    return c, x0, y0


def palette_size(tracks_cues, style):
    """Distinct subpicture colours a title needs: transparent, the outline,
    and a fill + anti-aliasing colour per text colour its cues are drawn in
    (as render_cue picks it; a colour no cue is drawn in takes no room).
    DVD allows 16."""
    fills = {(c.color or color or c.style_color or style["color"]).upper()
             for color, cues in tracks_cues for c in cues}
    return 2 + 2 * len(fills)


def mux_streams(title_mpg, stream_xmls, work, standard, log_prefix=None):
    """Mux the streams described by `stream_xmls` (what stream_xml wrote, in
    stream order) into the title: returns (the final .mpg path, the title's
    subpicture palette as (Y, Cr, Cb) in the order the units name them)."""
    from . import png4
    from ._vendor.vtskit import spu as vspu, subtitles as vsubs
    from .videots import ycc
    palette = []          # (r, g, b) in order of first use

    def entry(rgb):
        if rgb not in palette:
            palette.append(rgb)
        return palette.index(rgb)
    streams = {}
    for i, xml in enumerate(stream_xmls):
        cues = []
        with open(xml, encoding="utf-8") as f:
            for m in _SPU_TAG.finditer(f.read()):
                attrs = dict(_ATTR.findall(m.group(1)))
                with open(os.path.join(os.path.dirname(xml), attrs["image"]), "rb") as pf:
                    canvas, colours = png4.read_indexed_png(pf.read())
                codes = [0, 0, 0, 0]
                contrasts = [0, 0, 0, 0]
                for k, (r, g, b, a) in enumerate(colours[:4]):
                    if a:
                        codes[k] = entry((r, g, b))
                        contrasts[k] = a >> 4
                picture = vspu.Overlay(canvas.width, canvas.height, bytes(canvas.pixels))
                cues.append(vsubs.Cue(_seconds(attrs["start"]), _seconds(attrs["end"]), picture,
                                      int(attrs["xoffset"]), int(attrs["yoffset"]), tuple(codes),
                                      tuple(contrasts)))
        streams[i] = cues
    if len(palette) > 16:
        raise ProjectError("media check failed", [{
            "path": "titles", "message": f"the subtitles use {len(palette)} subpicture colours (a DVD "
                                         "title has 16)"}])
    with open(title_mpg, "rb") as f:
        data = f.read()
    out = os.path.splitext(title_mpg)[0] + ".subs.mpg"
    with open(out, "wb") as f:
        f.write(vsubs.mux(data, streams))
    return out, [ycc("#%02X%02X%02X" % rgb)[:3] for rgb in palette]


_SPU_TAG = re.compile(r"<spu\b([^>]*)/>")
_ATTR = re.compile(r'(\w+)="([^"]*)"')


def _seconds(ts):
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)
