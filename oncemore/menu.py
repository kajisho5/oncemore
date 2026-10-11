"""Still menus: background + burned-in labels (ffmpeg drawtext), button
highlights as 2-bit subpictures (written to the disc by vtskit), and preview
images.

Coordinates in the project are DVD storage pixels (720 x 480/576). DVD pixels
are not square, so we draw everything on a square-pixel "display" canvas
(e.g. 854x480 for NTSC 16:9) and squeeze it to 720 wide at the end. That keeps
text and thumbnails correctly proportioned on screen.

Button rectangles come from where the label pixels actually land: each label
is rendered alone with the same filter chain, read back as raw 8-bit gray and
scanned for its bounding box and glyph mask.
"""

import glob
import math
import json
import os
import shutil
import struct
import subprocess
import unicodedata
from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

from . import clips, encode, fontcheck, navigation, png4, tools
from .errors import OncemoreError, ProjectError, ToolFailedError
from .project import source_at

# Font search order. Japanese-capable fonts first so labels can be Japanese.
_MAC_FONT_DIRS = ("/System/Library/Fonts", "/Library/Fonts",
                  os.path.expanduser("~/Library/Fonts"))
_MAC_FONT_NAMES = (
    "ヒラギノ角ゴシック W6.ttc", "ヒラギノ角ゴシック W5.ttc", "ヒラギノ角ゴシック W4.ttc",
    "ヒラギノ角ゴシック W3.ttc", "Hiragino Sans GB.ttc", "ヒラギノ丸ゴ ProN W4.ttc",
)
_NOTO_GLOBS = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/**/NotoSansCJK*-Bold.tt[cf]",
    "/usr/share/fonts/**/NotoSansCJK*.tt[cf]",
    "/usr/share/fonts/**/NotoSansJP-*.[ot]tf",
    os.path.expanduser("~/Library/Fonts/NotoSansCJK*.tt[cf]"),
    os.path.expanduser("~/Library/Fonts/NotoSansJP*.[ot]tf"),
    "/opt/homebrew/share/fonts/**/NotoSansCJK*.tt[cf]",
)
_FALLBACK_GLOBS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/**/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/**/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)


def _font_candidates():
    """Auto-detection order, as paths (may contain duplicates)."""
    for d in _MAC_FONT_DIRS:
        try:
            names = {unicodedata.normalize("NFC", n): n for n in os.listdir(d)}
        except OSError:
            continue
        for want in _MAC_FONT_NAMES:
            real = names.get(unicodedata.normalize("NFC", want))
            if real:
                yield os.path.join(d, real)
    for pattern in _NOTO_GLOBS + _FALLBACK_GLOBS:
        yield from sorted(glob.glob(pattern, recursive=True))
    fc = shutil.which("fc-match")
    if fc:
        for q in ("Noto Sans CJK JP:bold", "sans-serif:bold"):
            try:
                p = subprocess.run([fc, "-f", "%{file}", q], capture_output=True, text=True,
                                   timeout=20).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                p = ""
            if p and os.path.isfile(p):
                yield p


def _missing(path, text):
    """Characters of `text` the font lacks; None if the font cannot be inspected."""
    try:
        return fontcheck.missing(path, text)
    except (OSError, fontcheck.FontError, struct.error):
        return None


def _quote_chars(chars, limit=12):
    shown = " ".join(chars[:limit])
    return shown + (f" (+{len(chars) - limit} more)" if len(chars) > limit else "")


def find_font(explicit=None, text=""):
    """Path of the font used for menu text.

    drawtext has no glyph fallback (missing characters become empty boxes and
    ffmpeg still succeeds), so the chosen font must cover every character of
    `text`. An explicit font that does not is an error; auto-detection picks
    the first candidate that covers everything.
    """
    explicit = explicit or (os.environ.get("ONCEMORE_FONT") or None)
    if explicit:
        if not os.path.isfile(explicit):
            raise OncemoreError(f"font not found: {explicit}")
        lack = _missing(explicit, text)
        if lack:
            raise OncemoreError(
                f"font {explicit} has no glyphs for: {_quote_chars(lack)}",
                hint="drawtext would draw them as empty boxes. Choose a font that covers "
                     "these characters (disc.font or ONCEMORE_FONT).")
        return explicit
    seen = set()
    best = None  # (number of missing chars, path)
    for path in _font_candidates():
        if path in seen:
            continue
        seen.add(path)
        lack = _missing(path, text)
        if lack == []:
            return path
        if lack is not None and (best is None or len(lack) < len(best[0])):
            best = (lack, path)
    if best is None:
        raise OncemoreError("no usable font found for menu text",
                            hint="Set disc.font in the project, or ONCEMORE_FONT, to a "
                                 ".ttf/.otf/.ttc file.")
    raise OncemoreError(
        f"no installed font can draw: {_quote_chars(best[0])} (closest: {best[1]})",
        hint="Install a font that covers them (for Japanese: Noto Sans CJK, e.g. "
             "'sudo apt-get install fonts-noto-cjk') or set disc.font. Emoji are not "
             "supported by drawtext.")


def check_element_fonts(project):
    """Texts and buttons with their own font: that font must exist and cover
    their characters (drawtext has no fallback)."""
    for m in project.menus:
        for el in list(m.texts) + [b for b in m.buttons if not b.image]:
            if not el.font:
                continue
            text = el.text if hasattr(el, "text") else el.label
            if not os.path.isfile(el.font):
                raise OncemoreError(f"menu {m.id!r}: font not found: {el.font}")
            lack = _missing(el.font, text)
            if lack:
                raise OncemoreError(f"menu {m.id!r}: font {os.path.basename(el.font)} has no "
                                    f"glyphs for: {_quote_chars(lack)}",
                                    hint="Pick a font that covers these characters.")


def drawtext_probe():
    """Render one frame with drawtext for real. Some builds list the filter
    in `-filters` but cannot draw (no font backend, or a crash)."""
    ffmpeg = tools.find("ffmpeg")
    if not ffmpeg or not tools.has_drawtext():
        return {"ok": False, "detail": "drawtext filter not available"}
    try:
        font = find_font(text="Ag")
    except OncemoreError as e:
        return {"ok": False, "detail": e.message}
    import tempfile
    with tempfile.TemporaryDirectory(prefix="oncemore-doctor-") as d:
        link = os.path.join(d, "font" + (os.path.splitext(font)[1] or ".ttf"))
        try:
            os.symlink(font, link)
        except OSError:
            shutil.copyfile(font, link)
        with open(os.path.join(d, "t.txt"), "w") as f:
            f.write("Ag")
        cmd = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
               "color=c=black:s=64x32:d=1", "-vf",
               f"drawtext=fontfile={os.path.basename(link)}:textfile=t.txt:fontsize=24:"
               "fontcolor=white:x=2:y=2,format=gray", "-frames:v", "1", "-f", "rawvideo",
               "pipe:1"]
        try:
            p = subprocess.run(cmd, cwd=d, capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "detail": str(e), "font": font}
    if p.returncode != 0 or not any(b > 128 for b in p.stdout):
        return {"ok": False, "font": font,
                "detail": tools.tail(p.stderr.decode("utf-8", "replace"), 3) or "nothing drawn"}
    return {"ok": True, "font": font}


def link_font(src, directory):
    """Make `src` available as font.<ext> inside `directory`; return that name."""
    ext = os.path.splitext(src)[1].lower() or ".ttf"
    link = os.path.join(directory, "font" + ext)
    if os.path.lexists(link):
        os.remove(link)
    try:
        os.symlink(src, link)
    except OSError:
        shutil.copyfile(src, link)
    return os.path.basename(link)


def menu_seconds(menu, probe):
    """Loop length of a menu: explicit, else the video / music length (1-600 s),
    else 5 s. `probe` is a callable path -> probe dict."""
    if menu.duration:
        return float(menu.duration)
    for path in (menu.background_video, menu.audio):
        if path:
            d = probe(path).get("duration")
            if d:
                return min(max(d, 1.0), 600.0)
    return 5.0


def menu_text(project):
    """All text drawn on the project's menus."""
    parts = []
    for m in project.menus:
        parts += [t.text for t in m.texts if not t.font] + \
            [b.label for b in m.buttons if not b.image and not b.font]
    return "".join(parts)


# --------------------------------------------------------------------------

@dataclass
class ButtonGeom:
    id: str
    rect: tuple            # (x0, y0, x1, y1) storage pixels, y0/y1 even
    shape: list            # list of Mask objects + rects drawn in highlight colour
    action: str
    nav: dict = field(default_factory=dict)
    auto: bool = False     # auto-activate: runs as soon as it is selected


@dataclass
class MenuAssets:
    menu_id: str
    base_png: str
    highlight_png: str
    select_png: str
    buttons: list          # ButtonGeom in DVD button order
    buttons_json: str = None   # the buttons' areas, keys and actions, as written (a record)
    mpg: str = None
    normal_png: str = None  # the buttons while not selected (menu.normal_color)
    intro_mpg: str = None   # buttons_at_loop: the part before the loop point, no buttons


def display_width(disc):
    """Square-pixel width of the frame (854 for NTSC 16:9, 640 for NTSC 4:3, ...)."""
    return int(round(disc.height * disc.dar / 2.0)) * 2


def _hex(color):
    r, g, b, a = png4.parse_color(color)
    return f"0x{r:02X}{g:02X}{b:02X}@{a / 255:.3f}"


class MenuBuilder:
    def __init__(self, project, work, reporter=None, font=None):
        self.project = project
        self.font_path = font
        self.disc = project.disc
        self.work = os.path.join(work, "menus")
        self.logs = os.path.join(work, "logs")
        os.makedirs(self.work, exist_ok=True)
        self.reporter = reporter
        self.ffmpeg = tools.find("ffmpeg")
        self.dw = display_width(self.disc)
        self.sx = self.dw / self.disc.width  # storage -> display x factor
        self._font_link = None
        self._font_links = {}      # own fonts of elements: path -> linked name
        self._probe_cache = {}
        self._glyphs = {}          # rendered texts: their glyph masks
        self._align_warned = False

    # -- font ------------------------------------------------------------------
    def font(self):
        """Font copied/linked into the work dir under an ASCII name, so the
        filter graph never has to escape spaces or Japanese characters."""
        if self._font_link is None:
            src = self.font_path or find_font(self.disc.font, menu_text(self.project))
            ext = os.path.splitext(src)[1].lower() or ".ttf"
            link = os.path.join(self.work, "font" + ext)
            if os.path.lexists(link):
                os.remove(link)
            try:
                os.symlink(src, link)
            except OSError:
                shutil.copyfile(src, link)
            self._font_link = os.path.basename(link)
            self.font_source = src
        return self._font_link

    def _textfile(self, name, text):
        path = os.path.join(self.work, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return name

    def font_for(self, el=None):
        """Linked font name for a text/button (its own font, or the disc's)."""
        path = getattr(el, "font", None)
        if not path:
            return self.font()
        if path not in self._font_links:
            ext = os.path.splitext(path)[1].lower() or ".ttf"
            link = os.path.join(self.work, f"font{len(self._font_links) + 1}{ext}")
            if os.path.lexists(link):
                os.remove(link)
            try:
                os.symlink(path, link)
            except OSError:
                shutil.copyfile(path, link)
            self._font_links[path] = os.path.basename(link)
        return self._font_links[path]

    def _drawtext(self, textfile, x, y, size, color, el=None, style=True):
        # x/y are storage pixels; the canvas is display pixels
        f = (f"drawtext=fontfile={self.font_for(el)}:textfile={textfile}:expansion=none:"
             f"fontsize={size}:fontcolor={_hex(color)}:x={round(x * self.sx)}:y={y}")
        if style and getattr(el, "outline", None):
            f += f":borderw={el.outline_width}:bordercolor={_hex(el.outline)}"
        if style and getattr(el, "shadow", None):
            f += (f":shadowx={el.shadow_offset}:shadowy={el.shadow_offset}"
                  f":shadowcolor={_hex(el.shadow)}")
        if getattr(el, "line_spacing", 0):
            f += f":line_spacing={el.line_spacing}"
        if getattr(el, "align", "left") != "left" and "\n" in getattr(el, "text", ""):
            if tools.drawtext_option("text_align", self.ffmpeg):
                f += f":text_align={'C' if el.align == 'center' else 'R'}"
            elif not self._align_warned:
                self._align_warned = True
                if self.reporter:
                    self.reporter.warn("this ffmpeg's drawtext cannot align lines (text_align "
                                       "came in ffmpeg 6.1): paragraphs are drawn left-aligned")
        return f

    def _squeeze(self):
        return f"scale={self.disc.width}:{self.disc.height}:flags=lanczos,setsar=1"

    # -- measuring ---------------------------------------------------------------
    def measure(self, menu_id, button):
        """Render one label alone; return its glyph Mask (storage pixels)."""
        mask = self.glyphs(f"{menu_id}.{button.id}.label", button.label, button)
        if mask.bbox() is None:
            raise ProjectError(f"menu {menu_id!r}: label of button {button.id!r} is empty "
                               "or entirely off-screen")
        return mask

    def glyphs(self, name, text, el):
        """The glyph Mask (storage pixels) of `text` drawn as `el` places it,
        without its outline or shadow."""
        key = (name, text, el.x, el.y, el.size, getattr(el, "font", None),
               getattr(el, "align", None), getattr(el, "line_spacing", 0))
        if key in self._glyphs:
            return self._glyphs[key]
        tf = self._textfile(f"{name}.txt", text)
        W, H = self.disc.width, self.disc.height
        vf = (self._drawtext(tf, el.x, el.y, el.size, "#FFFFFF", el,
                             style=False) + "," + self._squeeze() + ",format=gray")
        cmd = [self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
               f"color=c=black:s={self.dw}x{H}:r=1:d=1", "-vf", vf, "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
        p = subprocess.run(cmd, cwd=self.work, capture_output=True, timeout=300)
        if p.returncode != 0 or len(p.stdout) < W * H:
            raise ToolFailedError("ffmpeg could not render menu text",
                                  details={"output": tools.tail(p.stderr.decode("utf-8", "replace"))})
        mask = self._glyphs[key] = png4.Mask.from_gray(p.stdout[:W * H], W, H, threshold=110)
        return mask

    def image_box(self, menu_id, button, path=None):
        """(display width, height, storage width) of an image button's picture
        (or of `path`, e.g. its highlight picture, placed the same way)."""
        path = path or button.image
        info = self._probe(path)
        nw, nh = info.get("width"), info.get("height")
        if not (nw and nh):
            raise ProjectError(f"menu {menu_id!r}: button {button.id!r}: cannot read "
                               f"{os.path.basename(path)} as a picture")
        sw = button.width or max(8, round(nw / self.sx))
        dwid = max(2, round(sw * self.sx))
        h = max(2, round(dwid * nh / nw))
        if button.x + sw > self.disc.width or button.y + h > self.disc.height:
            raise ProjectError(f"menu {menu_id!r}: image of button {button.id!r} "
                               f"({sw}x{h} at {button.x},{button.y}) runs off the "
                               f"{self.disc.width}x{self.disc.height} menu; make it smaller "
                               "or move it")
        return dwid, h, sw

    def image_mask(self, menu_id, button, path=None):
        """Opaque pixels of an image button (or of `path` placed like it), in
        storage pixels."""
        path = path or button.image
        dwid, h, _ = self.image_box(menu_id, button, path)
        W, H = self.disc.width, self.disc.height
        graph = (f"[1:v]scale={dwid}:{h},format=rgba,alphaextract[a];"
                 f"[0:v][a]overlay={round(button.x * self.sx)}:{button.y},"
                 + self._squeeze() + ",format=gray")
        cmd = [self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
               f"color=c=black:s={self.dw}x{H}:r=1:d=1", "-i", path,
               "-filter_complex", graph, "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
        p = subprocess.run(cmd, cwd=self.work, capture_output=True, timeout=300)
        if p.returncode != 0 or len(p.stdout) < W * H:
            raise ToolFailedError("ffmpeg could not read a button image",
                                  details={"output": tools.tail(p.stderr.decode("utf-8", "replace"))})
        mask = png4.Mask.from_gray(p.stdout[:W * H], W, H, threshold=128)
        if mask.bbox() is None:
            raise ProjectError(f"menu {menu_id!r}: image of button {button.id!r} is fully "
                               "transparent; use highlight \"frame\"")
        return mask

    # -- turned / mirrored objects ------------------------------------------------
    # An object with a rotation or a flip is drawn on a layer of its own:
    # the layer is cut to a square around the object's centre (large enough
    # for any turn), mirrored, turned about that centre and laid back. The
    # turn is in display pixels, as the person sees the menu.
    @staticmethod
    def turned(el):
        return bool(getattr(el, "rotate", 0)) or bool(getattr(el, "flip", None))

    @staticmethod
    def _turn(el, fill):
        f = []
        if el.flip in ("horizontal", "both"):
            f.append("hflip")
        if el.flip in ("vertical", "both"):
            f.append("vflip")
        if el.rotate:
            f.append(f"rotate=a={math.radians(el.rotate):.6f}:c={fill}")
        return ",".join(f)

    def pivot(self, menu_id, el, kind, i=None):
        """(centre x, centre y, radius) of an object, in whole display
        pixels: what it turns about, and half the side of its square."""
        margin = 4
        if kind in ("shape", "image"):
            w, h = el.w * self.sx, el.h
            cx, cy = el.x * self.sx + w / 2, el.y + h / 2
        elif kind == "button" and (el.image or (el.highlight_image and not el.label)):
            dwid, h, _ = self.image_box(menu_id, el, el.image or el.highlight_image)
            w, cx, cy = dwid, el.x * self.sx + dwid / 2, el.y + h / 2
            margin += 4                     # (its highlight frame)
        else:
            name = f"{menu_id}.{el.id}.label" if kind == "button" else f"{menu_id}.text{i}"
            text = el.label if kind == "button" else el.text
            box = self.glyphs(name, text, el).bbox()
            if box is None:
                raise ProjectError(f"menu {menu_id!r}: a turned text is empty or off-screen")
            x0, y0, x1, y1 = box
            w, h = (x1 - x0 + 1) * self.sx, y1 - y0 + 1
            cx, cy = (x0 + x1 + 1) / 2 * self.sx, (y0 + y1 + 1) / 2
            margin += (el.outline_width if el.outline else 0) + \
                (el.shadow_offset if el.shadow else 0) + 8      # (+ a button's underline)
        return round(cx), round(cy), math.ceil(math.hypot(w, h) / 2) + margin

    def turned_layer(self, source, el, pivot):
        """Filter chain turning `source` (an RGBA picture of the whole menu
        with the object where it stands) about the object's centre. Returns
        (chain, x, y): the turned square and where it goes."""
        cx, cy, r = pivot
        chain = (f"{source},pad={self.dw + 2 * r}:{self.disc.height + 2 * r}:{r}:{r}:"
                 f"color=0x00000000,crop={2 * r}:{2 * r}:{cx}:{cy},{self._turn(el, '0x00000000')}")
        return chain, cx - r, cy - r

    def turned_mask(self, name, el, shapes, pivot):
        """Highlight shapes (storage pixels) turned like their button."""
        W, H = self.disc.width, self.disc.height
        c = png4.Canvas(W, H)
        for sh in shapes:
            if isinstance(sh, png4.Mask):
                c.blit_mask(sh, 1)
            elif sh[0] == "fill":
                c.fill_rect(*sh[1], 1)
            elif sh[0] == "frame":
                c.stroke_rect(*sh[1], 1, width=3)
        src = os.path.join(self.work, f"{name}.turn.png")
        png4.write_indexed_png(src, c, [(0, 0, 0, 255), (255, 255, 255, 255)])
        cx, cy, r = pivot
        graph = (f"[1:v]scale={self.dw}:{H}:flags=neighbor,format=gray,"
                 f"pad={self.dw + 2 * r}:{H + 2 * r}:{r}:{r}:color=black,"
                 f"crop={2 * r}:{2 * r}:{cx}:{cy},{self._turn(el, 'black')}[t];"
                 f"[0:v][t]overlay={cx - r}:{cy - r}," + self._squeeze() + ",format=gray")
        cmd = [self.ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
               f"color=c=black:s={self.dw}x{H}:r=1:d=1", "-i", src,
               "-filter_complex", graph, "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
        p = subprocess.run(cmd, cwd=self.work, capture_output=True, timeout=300)
        if p.returncode != 0 or len(p.stdout) < W * H:
            raise ToolFailedError("ffmpeg could not turn a button's highlight",
                                  details={"output": tools.tail(p.stderr.decode("utf-8", "replace"))})
        return png4.Mask.from_gray(p.stdout[:W * H], W, H, threshold=110)

    # -- geometry ----------------------------------------------------------------
    def layout(self, menu, overlaps=None):
        """Button areas, highlight shapes and routing. Overlapping buttons are
        an error, unless `overlaps` (a list) is given to collect them (the
        app outlines them)."""
        W, H = self.disc.width, self.disc.height
        geoms = []
        for b in menu.buttons:
            if b.highlight_image:
                hl = self.image_mask(menu.id, b, b.highlight_image)
                hb = hl.bbox()
                if hb is None:
                    raise ProjectError(f"menu {menu.id!r}: highlight picture of button "
                                       f"{b.id!r} is fully transparent")
                if b.image:
                    _, h, sw = self.image_box(menu.id, b)
                    body = (b.x, b.y, b.x + sw - 1, b.y + h - 1)
                elif b.label:
                    body = self.measure(menu.id, b).bbox()
                else:
                    body = hb        # an area of the background (e.g. from Photoshop)
                if b.thumb:
                    t = b.thumb
                    body = (min(body[0], t.x), min(body[1], t.y),
                            max(body[2], t.x + t.w), max(body[3], t.y + t.h))
                x0, y0 = max(0, min(body[0], hb[0]) - 2), max(0, min(body[1], hb[1]) - 2)
                x1, y1 = min(W - 1, max(body[2], hb[2]) + 2), min(H - 2, max(body[3], hb[3]) + 2)
                y0 -= y0 % 2
                y1 += y1 % 2
                geoms.append(ButtonGeom(b.id, (x0, y0, x1, y1), [hl], b.action,
                                        auto=b.auto_activate))
                continue
            if b.image:
                _, h, sw = self.image_box(menu.id, b)
                if b.highlight == "shape":
                    mask = self.image_mask(menu.id, b)
                    shapes = [mask]
                    x0, y0, x1, y1 = mask.bbox()
                else:
                    frame = (b.x - 4, b.y - 4, b.x + sw + 3, b.y + h + 3)
                    shapes = [("frame", frame)]
                    x0, y0, x1, y1 = frame
                x0, y0 = max(0, x0 - 2), max(0, y0 - 2)
                x1, y1 = min(W - 1, x1 + 2), min(H - 2, y1 + 2)
                y0 -= y0 % 2
                y1 += y1 % 2
                geoms.append(ButtonGeom(b.id, (x0, y0, x1, y1), shapes, b.action,
                                        auto=b.auto_activate))
                continue
            mask = self.measure(menu.id, b)
            x0, y0, x1, y1 = mask.bbox()
            shapes = [mask]
            if b.thumb:
                t = b.thumb
                frame = (t.x - 4, t.y - 4, t.x + t.w + 4, t.y + t.h + 4)
                shapes.append(("frame", frame))
                x0, y0 = min(x0, frame[0]), min(y0, frame[1])
                x1, y1 = max(x1, frame[2]), max(y1, frame[3])
            else:
                ul = (x0, y1 + 3, x1, y1 + 6)
                shapes.append(("fill", ul))
                y1 = ul[3]
            x0, y0 = max(0, x0 - 6), max(0, y0 - 4)
            x1, y1 = min(W - 1, x1 + 6), min(H - 2, y1 + 4)
            y0 -= y0 % 2
            y1 += y1 % 2
            geoms.append(ButtonGeom(b.id, (x0, y0, x1, y1), shapes, b.action,
                                    auto=b.auto_activate))
        for g, b in zip(geoms, menu.buttons):
            if self.turned(b):
                self._turn_geom(menu, g, b)
        for i, a in enumerate(geoms):
            for b in geoms[i + 1:]:
                if a.rect[0] < b.rect[2] and b.rect[0] < a.rect[2] and \
                        a.rect[1] < b.rect[3] and b.rect[1] < a.rect[3]:
                    if overlaps is not None:
                        overlaps.append([a.id, b.id])
                        continue
                    raise ProjectError(
                        f"menu {menu.id!r}: buttons {a.id!r} and {b.id!r} overlap "
                        f"({a.rect} vs {b.rect}); move them apart")
        nav = navigation.compute([(g.id, g.rect, b.nav) for g, b in zip(geoms, menu.buttons)])
        for g in geoms:
            g.nav = nav[g.id]
        return geoms

    def _turn_geom(self, menu, g, b):
        """A turned button: its highlight turned with it (not its thumbnail's
        frame, which stays where the thumbnail is)."""
        W, H = self.disc.width, self.disc.height
        frame = None
        if b.thumb:
            t = b.thumb
            frame = ("frame", (t.x - 4, t.y - 4, t.x + t.w + 4, t.y + t.h + 4))
        body = [sh for sh in g.shape if not (frame and not isinstance(sh, png4.Mask)
                                              and tuple(sh) == frame)]
        mask = self.turned_mask(f"{menu.id}.{b.id}", b, body,
                                self.pivot(menu.id, b, "button"))
        box = mask.bbox()
        if box is None:
            raise ProjectError(f"menu {menu.id!r}: button {b.id!r} is turned entirely "
                               "off the menu")
        x0, y0, x1, y1 = box
        shapes = [mask]
        if frame and frame in [tuple(sh) for sh in g.shape if not isinstance(sh, png4.Mask)]:
            shapes.append(frame)
            f = frame[1]
            x0, y0, x1, y1 = min(x0, f[0]), min(y0, f[1]), max(x1, f[2]), max(y1, f[3])
        x0, y0 = max(0, x0 - 4), max(0, y0 - 4)
        x1, y1 = min(W - 1, x1 + 4), min(H - 2, y1 + 4)
        y0 -= y0 % 2
        y1 += y1 % 2
        g.rect, g.shape = (x0, y0, x1, y1), shapes

    def highlight_canvas(self, geoms, only=None, outline=False, index_of=None):
        """The buttons' shapes on a canvas, in palette index 1 (or
        index_of(geom); 0 leaves a button out)."""
        c = png4.Canvas(self.disc.width, self.disc.height)
        for g in geoms:
            if only is not None and g.id != only:
                continue
            idx = index_of(g) if index_of else 1
            for s in g.shape if idx else ():
                if isinstance(s, png4.Mask):
                    c.blit_mask(s, idx)
                elif s[0] == "fill":
                    c.fill_rect(*s[1], idx)
                elif s[0] == "frame":
                    c.stroke_rect(*s[1], idx, width=3)
            if outline:
                c.stroke_rect(g.rect[0], g.rect[1], g.rect[2] + 1, g.rect[3] + 1, 2, width=1)
        return c

    def state_canvas(self, menu, geoms, state, button=None, every=False, outline=False):
        """What the subpicture shows: index 1 = the button(s) in `state`
        (highlight / select), 3 = the other buttons in the normal colour (when
        the menu has one), 2 = outlines. state "normal": every button in the
        normal colour; "none": no subpicture at all."""
        active = set()
        if state in ("highlight", "select"):
            active = {g.id for g in geoms} if every else {button}
        show_normal = bool(menu.normal_color) and state != "none"
        return self.highlight_canvas(geoms, outline=outline,
                                     index_of=lambda g: 1 if g.id in active else (3 if show_normal else 0))

    def state_palette(self, menu, color):
        return [(0, 0, 0, 0), png4.parse_color(color or "#00000000"), (0, 255, 255, 255),
                png4.parse_color(menu.normal_color or "#00000000")]

    # -- rendering ---------------------------------------------------------------
    def _probe(self, path):
        if path not in self._probe_cache:
            self._probe_cache[path] = encode.probe(path)
        return self._probe_cache[path]

    def thumbnails(self, menu):
        out = []
        for b in menu.buttons:
            if not b.thumb:
                continue
            t = b.thumb
            title = self.project.title(t.title_id)
            if any(c.duration is None for c in title.clips):    # (no build resolved them)
                clips.resolve(title, self.project.disc_for(title), self._probe)
            # a title made of clips: the file and moment playing at that time
            source, at = source_at(title, t.time)
            info = self._probe(source)
            size = (int(round(t.w * self.sx / 2)) * 2, t.h)
            path = os.path.join(self.work, f"{menu.id}.{b.id}.thumb.png")
            if not info.get("has_video") and info.get("has_audio"):
                # a title from a sound file: its still picture, or black
                if title.picture:
                    pic = self._probe(title.picture)
                    encode.extract_thumbnail(title.picture, pic, self.project.disc_for(title),
                                             0.0, size, path,
                                             os.path.join(self.logs, f"thumb-{menu.id}-{b.id}.log"))
                else:
                    png4.write_indexed_png(path, png4.Canvas(*size), [(0, 0, 0, 255)])
                out.append((path, round(t.x * self.sx), t.y))
                continue
            if t.animated and menu.background_video:
                # a moving thumbnail: the chapter itself, fitted like the title
                w, h = size
                start = max(0.0, min(at, (info.get("duration") or at + 1) - 1.0))
                num, den = self.disc.fps
                dur = self.menu_duration(menu)
                # every input finite: the clip is read for the menu's length only
                # and held on its last frame if the chapter is shorter
                vf = (encode.fit_filter(info, self.project.disc_for(title), fps=False)
                      + f",scale=iw*sar:ih,setsar=1,scale={w}:{h}:force_original_aspect_ratio="
                        f"decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={num}/{den},"
                        f"tpad=stop_mode=clone:stop_duration={dur:.3f}")
                out.append((source, round(t.x * self.sx), t.y, vf,
                            ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}"]))
                continue
            encode.extract_thumbnail(source, info, self.project.disc_for(title), at,
                                     size, path,
                                     os.path.join(self.logs, f"thumb-{menu.id}-{b.id}.log"))
            out.append((path, round(t.x * self.sx), t.y))
        return out

    def compose(self, menu, transparent=False):
        """ffmpeg inputs + filter_complex drawing the menu, ending in [out].

        Input 0 is the background: a still image, a colour, or (motion menu)
        a video converted to the disc frame rate. Thumbnails are single
        images; overlay keeps showing their last frame, so the same graph
        works for one frame or a whole video. transparent: no background at
        all, the rest drawn on a transparent RGBA picture (a pop-up menu).
        """
        H = self.disc.height
        inputs = []
        if transparent:
            # (rgba chosen in the source itself, or its alpha is lost)
            inputs += ["-f", "lavfi", "-i", f"color=c=black@0.0:s={self.dw}x{H}:d=1,format=rgba"]
            bg = "[0:v]format=rgba"
        elif menu.background_video:
            num, den = self.disc.fps
            inputs += ["-i", menu.background_video]
            # tpad: hold the last frame if `duration` is longer than the video
            bg = (f"[0:v]fps={num}/{den},"
                  f"tpad=stop_mode=clone:stop_duration={self.menu_duration(menu):.3f},"
                  f"scale={self.dw}:{H}:force_original_aspect_ratio=decrease,"
                  f"pad={self.dw}:{H}:(ow-iw)/2:(oh-ih)/2:color={_hex(menu.background_color)},"
                  f"setsar=1,format=rgb24")
        elif menu.background:
            inputs += ["-i", menu.background]
            bg = (f"[0:v]scale={self.dw}:{H}:force_original_aspect_ratio=decrease,"
                  f"pad={self.dw}:{H}:(ow-iw)/2:(oh-ih)/2:color={_hex(menu.background_color)},"
                  f"setsar=1,format=rgb24")
        else:
            inputs += ["-f", "lavfi", "-i", f"color=c={_hex(menu.background_color)}:s={self.dw}x{H}:d=1"]
            bg = "[0:v]format=rgb24"
        chains = [bg + "[bg0]"]
        cur = "bg0"
        if any(self.turned(s) for s in menu.shapes) or (menu.shapes and transparent):
            # (drawbox leaves the alpha alone, and cannot turn: shapes are
            # overlaid instead)
            for k, s in enumerate(menu.shapes):
                w, h = max(1, round(s.w * self.sx)), s.h
                x, y, turn = round(s.x * self.sx), s.y, ""
                if self.turned(s):
                    cx, cy, r = self.pivot(menu.id, s, "shape")
                    turn = (f",pad={2 * r}:{2 * r}:(ow-iw)/2:(oh-ih)/2:color=0x00000000,"
                            + self._turn(s, "0x00000000"))
                    x, y = cx - r, cy - r
                chains.append(f"color=c={_hex(s.color)}:s={w}x{h}:d=1,format=rgba{turn}[shape{k}]")
                chains.append(f"[{cur}][shape{k}]overlay={x}:{y}[shp{k}]")
                cur = f"shp{k}"
        elif menu.shapes:
            boxes = ",".join(
                f"drawbox=x={round(s.x * self.sx)}:y={s.y}:w={max(1, round(s.w * self.sx))}:"
                f"h={s.h}:color={_hex(s.color)}:t=fill" for s in menu.shapes)
            chains.append(f"[{cur}]{boxes}[shp]")
            cur = "shp"

        def placed(path, el, kind, x, y, pre):
            if not self.turned(el):
                return (path, x, y, pre)
            cx, cy, r = self.pivot(menu.id, el, kind)
            return (path, cx - r, cy - r, f"{pre},pad={2 * r}:{2 * r}:(ow-iw)/2:(oh-ih)/2:"
                                          f"color=0x00000000,{self._turn(el, '0x00000000')}")
        overlays = []
        for p in menu.images:
            fade = f",colorchannelmixer=aa={p.opacity:.3f}" if p.opacity < 1 else ""
            overlays.append(placed(p.file, p, "image", round(p.x * self.sx), p.y,
                                   f"scale={max(1, round(p.w * self.sx))}:{p.h},format=rgba{fade}"))
        overlays += list(self.thumbnails(menu))
        for b in menu.buttons:
            if b.image:
                dwid, h, _ = self.image_box(menu.id, b)
                overlays.append(placed(b.image, b, "button", round(b.x * self.sx), b.y,
                                       f"scale={dwid}:{h},format=rgba"))
        for i, (path, x, y, *rest) in enumerate(overlays, 1):
            pre = rest[0] if rest else None
            opts = rest[1] if len(rest) > 1 else []
            inputs += list(opts) + ["-i", path]
            src = f"[{i}:v]"
            if pre:
                chains.append(f"{src}{pre}[im{i}]")
                src = f"[im{i}]"
            chains.append(f"[{cur}]{src}overlay={x}:{y}[bg{i}]")
            cur = f"bg{i}"
        draws, turned = [], []
        for i, t in enumerate(menu.texts):
            tf = self._textfile(f"{menu.id}.text{i}.txt", t.text)
            text = self._drawtext(tf, t.x, t.y, t.size, t.color, t)
            if self.turned(t):
                turned.append((text, t, self.pivot(menu.id, t, "text", i)))
            else:
                draws.append(text)
        for b in menu.buttons:
            if b.image or not b.label:
                continue
            tf = self._textfile(f"{menu.id}.{b.id}.label.txt", b.label)
            text = self._drawtext(tf, b.x, b.y, b.size, b.color, b)
            if self.turned(b):
                turned.append((text, b, self.pivot(menu.id, b, "button")))
            else:
                draws.append(text)
        if draws:
            chains.append(f"[{cur}]" + ",".join(draws) + "[txt]")
            cur = "txt"
        for k, (text, el, pivot) in enumerate(turned):
            # (drawn alone on a clear layer of the menu's size, then turned)
            chain, x, y = self.turned_layer(
                f"color=c=0x00000000:s={self.dw}x{H}:d=1,format=rgba,{text}", el, pivot)
            chains.append(f"{chain}[turn{k}]")
            chains.append(f"[{cur}][turn{k}]overlay={x}:{y}[tl{k}]")
            cur = f"tl{k}"
        chains.append(f"[{cur}]{self._squeeze()}[out]")
        return inputs, ";".join(chains)

    def render_base(self, menu):
        """First frame of the menu -> <id>.base.png (720 x H)."""
        inputs, graph = self.compose(menu)
        out = os.path.join(self.work, f"{menu.id}.base.png")
        tools.run([self.ffmpeg, "-hide_banner", "-nostdin", "-y"] + inputs +
                  ["-filter_complex", graph, "-map", "[out]", "-frames:v", "1",
                   "-update", "1", out],
                  cwd=self.work, log=os.path.join(self.logs, f"menu-{menu.id}-base.log"),
                  what=f"ffmpeg (menu {menu.id} background)", timeout=600)
        return out

    def prepare(self, menu):
        """Everything needed to preview or encode `menu`."""
        geoms = self.layout(menu)
        base = self.render_base(menu)
        canvas = self.highlight_canvas(geoms)
        hl = os.path.join(self.work, f"{menu.id}.highlight.png")
        sel = os.path.join(self.work, f"{menu.id}.select.png")
        png4.write_indexed_png(hl, canvas, [(0, 0, 0, 0), png4.parse_color(menu.highlight_color)])
        png4.write_indexed_png(sel, canvas, [(0, 0, 0, 0), png4.parse_color(menu.select_color)])
        normal = None
        if menu.normal_color:
            # the same shapes in the "normal" colour: the subpicture shown on
            # every button that is not selected (a DVD player swaps in the
            # highlight / select colours inside the selected button)
            normal = os.path.join(self.work, f"{menu.id}.normal.png")
            png4.write_indexed_png(normal, canvas, [(0, 0, 0, 0), png4.parse_color(menu.normal_color)])
        return MenuAssets(menu.id, base, hl, sel, geoms, normal_png=normal)

    def buttons_json(self, assets):
        """A record of the menu's buttons as the disc gets them: areas,
        arrow keys, actions (<id>.buttons.json in the work folder)."""
        path = os.path.join(self.work, f"{assets.menu_id}.buttons.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"menu": assets.menu_id, "normal": assets.normal_png is not None,
                       "buttons": [{"id": g.id, "rect": list(g.rect), "nav": g.nav, "auto": g.auto,
                                    "action": g.action} for g in assets.buttons]}, f, indent=1)
        return path

    def menu_duration(self, menu):
        return menu_seconds(menu, self._probe)

    def encode(self, menu, assets, on_progress=None):
        """Encode the still menu (looping length); the button subpicture is
        added when the disc is written (videots)."""
        dur = self.menu_duration(menu)
        num, den = self.disc.fps
        target = "ntsc-dvd" if self.disc.standard == "NTSC" else "pal-dvd"
        a, b = self.disc.aspect.split(":")
        finish = f"scale=out_color_matrix=bt601:out_range=tv,format=yuv420p,setdar={a}/{b}"
        if menu.fade_in:
            # from black, once: the loop point is at the end of the fade or later
            finish = f"fade=t=in:st=0:d={menu.fade_in:.3f}," + finish
        afade = f",afade=t=in:st=0:d={menu.fade_in:.3f}" if menu.fade_in else ""
        if menu.background_video:
            # motion menu: draw the menu onto every frame of the video
            inputs, graph = self.compose(menu)
            args = inputs
            n = len([x for x in inputs if x == "-i"])
            graph = graph.replace("[out]", "[menu]") + f";[menu]{finish}[v]"
            vmap, vbps = "[v]", encode.MOTION_MENU_VIDEO_BPS
        else:
            args = ["-loop", "1", "-framerate", f"{num}/{den}", "-t", f"{dur:.3f}",
                    "-i", os.path.basename(assets.base_png)]
            n, graph, vmap, vbps = 1, f"[0:v]{finish}[v]", "[v]", encode.MENU_VIDEO_BPS
        if menu.audio:
            args += ["-i", menu.audio]
            graph += f";[{n}:a:0]aresample=48000{afade},apad[a]"
        elif menu.background_video and self._probe(menu.background_video).get("has_audio"):
            graph += f";[0:a:0]aresample=48000{afade},apad[a]"
        else:
            graph += ";anullsrc=channel_layout=stereo:sample_rate=48000[a]"
        args += ["-filter_complex", graph, "-map", vmap, "-map", "[a]",
                 "-target", target, "-aspect", self.disc.aspect,
                 "-b:v", str(vbps), "-maxrate", "8000000", "-bufsize", "1835008"]
        args += encode._color_args(self.disc)
        args += encode.audio_args("ac3", 192_000)
        raw = os.path.join(self.work, f"{menu.id}.raw.mpg")
        log = os.path.join(self.logs, f"menu-{menu.id}.log")
        if menu.buttons_at_loop:
            # two parts: the intro on its own (a DVD shows buttons for a whole
            # program chain, so they wait in the next one), then the loop
            lp = menu.loop_point
            intro = os.path.join(self.work, f"{menu.id}.intro.mpg")
            encode.run_ffmpeg(args + ["-t", f"{lp:.3f}", os.path.basename(intro)], dur, log,
                              lambda f: on_progress and on_progress(f * lp / dur),
                              cwd=self.work, what=f"ffmpeg (menu {menu.id}, intro)")
            encode.run_ffmpeg(args + ["-ss", f"{lp:.3f}", "-t", f"{dur - lp:.3f}",
                                      os.path.basename(raw)], dur, log, on_progress,
                              cwd=self.work, what=f"ffmpeg (menu {menu.id})")
            assets.intro_mpg = intro
        else:
            args += ["-t", f"{dur:.3f}"]
            if menu.loop_point:
                # repeats start at a cell boundary, which needs a GOP (VOBU) there
                args += ["-force_key_frames", f"{menu.loop_point:.3f}"]
            encode.run_ffmpeg(args + [os.path.basename(raw)], dur, log, on_progress,
                              cwd=self.work, what=f"ffmpeg (menu {menu.id})")
        out = os.path.join(self.work, f"{menu.id}.mpg")
        os.replace(raw, out)
        assets.buttons_json = self.buttons_json(assets)
        assets.mpg = out
        return out

    def encode_transition(self, path, out, on_progress=None):
        """A link transition as a menu video (no buttons): the disc's picture,
        its sound (or silence) in AC-3 like the menus'."""
        info = self._probe(path)
        dur = info["duration"]
        target = "ntsc-dvd" if self.disc.standard == "NTSC" else "pal-dvd"
        graph = f"[0:v:0]{encode.fit_filter(info, self.disc)},format=yuv420p[v]"
        if info.get("has_audio"):
            graph += ";[0:a:0]aresample=48000,apad[a]"
        else:
            graph += ";anullsrc=channel_layout=stereo:sample_rate=48000[a]"
        args = ["-i", path, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                "-target", target, "-aspect", self.disc.aspect,
                "-b:v", str(encode.MOTION_MENU_VIDEO_BPS), "-maxrate", "8000000",
                "-bufsize", "1835008"]
        args += encode._color_args(self.disc) + encode.audio_args("ac3", 192_000)
        encode.run_ffmpeg(args + ["-t", f"{dur:.3f}", out], dur,
                          os.path.join(self.logs, f"transition-{os.path.basename(out)}.log"),
                          on_progress, cwd=self.work,
                          what=f"ffmpeg (transition {os.path.basename(path)})")
        return out

    # -- preview -----------------------------------------------------------------
    def preview(self, menu, out_png, button=None, state="highlight", outline=False, every=False):
        """Write a square-pixel PNG of the menu as a viewer would see it.
        every=True shows all buttons in `state` at once (normal / highlight /
        select), to check the highlights of the whole menu."""
        assets = self.prepare(menu)
        ids = [g.id for g in assets.buttons]
        if button is None:
            button = ids[0]
        if button not in ids:
            raise OncemoreError(f"menu {menu.id!r} has no button {button!r} "
                                f"(buttons: {', '.join(ids)})")
        canvas = self.state_canvas(menu, assets.buttons, state, button, every=every, outline=outline)
        color = {"highlight": menu.highlight_color, "select": menu.select_color}.get(state)
        overlay = os.path.join(self.work, f"{menu.id}.preview-overlay.png")
        png4.write_indexed_png(overlay, canvas, self.state_palette(menu, color))
        H = self.disc.height
        flt = (f"[0:v][1:v]overlay=0:0,scale={self.dw}:{H}:flags=lanczos,setsar=1[out]")
        os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
        tools.run([self.ffmpeg, "-hide_banner", "-nostdin", "-y", "-i", assets.base_png,
                   "-i", overlay, "-filter_complex", flt, "-map", "[out]", "-frames:v", "1",
                   "-update", "1", os.path.abspath(out_png)],
                  log=os.path.join(self.logs, f"preview-{menu.id}.log"),
                  what="ffmpeg (preview)")
        return {"menu": menu.id, "button": button, "state": state, "path": os.path.abspath(out_png),
                "buttons": [{"id": g.id, "rect": list(g.rect), "action": g.action, "nav": g.nav}
                            for g in assets.buttons],
                "size": [self.dw, H]}
