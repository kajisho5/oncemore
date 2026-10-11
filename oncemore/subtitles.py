"""Subtitles: SRT / WebVTT / ASS -> DVD subpicture stream (spumux).

Each cue is drawn with drawtext (white text, dark outline) on a transparent
square-pixel canvas, squeezed to DVD width exactly like menu text, read back
as RGBA and reduced to the 4 colours a DVD subpicture can hold:

  0 transparent, 1 fill, 2 outline, 3 anti-aliasing (between fill and outline)

The bitmaps are cropped to their bounding box and handed to spumux with an
offset, one spumux pass per subtitle stream.
"""

import concurrent.futures
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


PARSERS = {".srt": parse_srt, ".vtt": parse_vtt, ".ass": parse_ass, ".ssa": parse_ass}


def load_subtitles(path):
    parse = PARSERS.get(os.path.splitext(path)[1].lower(), parse_srt)
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
    for n, c in enumerate(cues, 1):
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

    def stream_xml(self, cues, lang, index, position="bottom", color=None):
        """Render every cue and write the spumux XML for one stream. `position`
        and `color` are the track's defaults; cues may override them."""
        base = f"sub{index}_{lang}"
        jobs = {}
        workers = min(8, os.cpu_count() or 2)
        with concurrent.futures.ThreadPoolExecutor(workers) as pool:
            for n, cue in enumerate(cues):
                jobs[n] = pool.submit(self.render, cue, f"{base}_{n:05d}", position)
            results = {n: f.result() for n, f in jobs.items()}

        def palette(fill):
            return [(0, 0, 0, 0), png4.parse_color(fill), png4.parse_color(self.style["outline"]),
                    _mix(fill, self.style["outline"])]
        lines = [f'<subpictures format="{self.disc.standard}">', "  <stream>"]
        for n, cue in enumerate(cues):
            canvas, x, y = results[n]
            if canvas is None:
                continue
            name = f"{base}_{n:05d}.png"
            png4.write_indexed_png(os.path.join(self.work, name), canvas,
                                   palette(cue.color or color or cue.style_color
                                           or self.style["color"]))
            lines.append(f'    <spu start="{_ts(cue.start)}" end="{_ts(cue.end)}" '
                         f'image={quoteattr(name)} xoffset="{x}" yoffset="{y}"/>')
        lines += ["  </stream>", "</subpictures>", ""]
        path = os.path.join(self.work, f"{base}.spumux.xml")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path


def _mix(a, b):
    ca, cb = png4.parse_color(a), png4.parse_color(b)
    return tuple((x + y) // 2 for x, y in zip(ca[:3], cb[:3])) + (255,)


_OPAQUE = bytes(1 if a >= 96 else 0 for a in range(256))


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


def mux_streams(title_mpg, stream_xmls, work, standard, log_prefix):
    """Run spumux once per stream; returns the final .mpg path."""
    spumux = tools.find("spumux")
    cur = title_mpg
    for i, xml in enumerate(stream_xmls):
        nxt = os.path.splitext(title_mpg)[0] + f".s{i}.mpg"
        with open(cur, "rb") as fin, open(nxt, "wb") as fout:
            tools.run([spumux, "-s", str(i), os.path.basename(xml)], cwd=work,
                      env={"VIDEO_FORMAT": standard}, stdin=fin, stdout=fout,
                      log=f"{log_prefix}-s{i}.log", what=f"spumux (subtitle stream {i})")
        if cur != title_mpg:
            os.remove(cur)
        cur = nxt
    return cur
