"""Blu-ray menus (DECISIONS §56).

Every menu of the project becomes an HDMV interactive title. Its picture is
the DVD menu drawn again at HD size (the menu builder working on a copy of
the menu scaled to 1920 x 1080), encoded as a short clip that the playlist
holds as a still (or plays and repeats, for menus with motion or music).
Its buttons travel with the clip as an Interactive Graphics stream: one
interactive composition with a button per menu button, each pointing at
its highlight in the selected and activated colours (and in the normal
colour when the menu has one) and carrying the commands of its action.

The highlights are the DVD menu's own button shapes (label glyphs, frames,
underlines, highlight pictures), so a menu looks and behaves the same on
both discs; on Blu-ray the colours are full colour with their opacity.

A title's Menu-key menu (remote_menu) is its pop-up menu on Blu-ray: the
menu drawn without its background on a transparent picture, each button's
area of it (normal) and the same with the highlight shapes painted over
(selected, activated) as the objects of a pop-up interactive composition,
muxed into the title's clip (popup_stream).

The stream (composition, palette, objects) and the stream-type patch are
bdmvkit's (igs, DECISIONS §110); the buttons' pictures are drawn here.
"""

import dataclasses
import os

from . import bluray, encode, png4, tools
from ._vendor.bdmvkit import igs
from ._vendor.bdmvkit.errors import BdmvError
from ._vendor.bdmvkit.igs import patch_ig_stream_type
from .errors import OncemoreError
from .menu import MenuBuilder, animated
from .project import Disc

STILL_SECONDS = 1.0            # a still menu's clip; the playlist holds its last picture


class HDDisc(Disc):
    """The disc settings with the 16:9 HD frame (for drawing menus)."""

    @property
    def width(self):
        return bluray.frame_size(self)[0]

    @property
    def height(self):
        return bluray.frame_size(self)[1]

    @property
    def dar(self):
        return 16 / 9


def hd_disc(disc):
    fields = {f.name: getattr(disc, f.name) for f in dataclasses.fields(disc)}
    fields["aspect"] = "16:9"
    return HDDisc(**fields)


def frame_map(disc):
    """(kx, ox, ky): menu coordinates (720 x 480/576 storage pixels) to HD:
    x' = ox + x * kx, y' = y * ky. A 4:3 menu sits pillarboxed in the frame."""
    fw, fh = bluray.frame_size(disc)
    ky = fh / disc.height
    if disc.aspect == "4:3":
        kx = fh * 4 / 3 / 720
        return kx, round((fw - 720 * kx) / 2), ky
    return fw / 720, 0, ky


def scale_menu(menu, disc, probe):
    """A copy of `menu` laid out on the HD frame. `probe(path)` reads a
    picture's size (image buttons without a width keep the size they have
    on the DVD menu)."""
    kx, ox, ky = frame_map(disc)
    sx_dvd = (round(disc.height * disc.dar / 2) * 2) / disc.width

    def X(x):
        return round(ox + x * kx)

    def W(w):
        return max(1, round(w * kx))

    def Y(y):
        return round(y * ky)

    def moved(a):
        # (an animation's distance on the HD frame)
        return a and dataclasses.replace(a, dx=round(a.dx * kx), dy=round(a.dy * ky))

    def styled(el, **kw):
        return dataclasses.replace(
            el, size=max(4, round(el.size * ky)),
            outline_width=max(1, round(el.outline_width * ky)) if el.outline else el.outline_width,
            shadow_offset=max(1, round(el.shadow_offset * ky)),
            letter_spacing=round(el.letter_spacing * ky), **kw)

    buttons = []
    for b in menu.buttons:
        width = b.width
        picture = b.image or b.highlight_image
        if width is None and picture:
            info = probe(picture)
            width = max(8, round(info["width"] / sx_dvd))
        thumb = b.thumb and dataclasses.replace(b.thumb, x=X(b.thumb.x), y=Y(b.thumb.y),
                                                w=W(b.thumb.w), h=Y(b.thumb.h))
        area = b.area and dataclasses.replace(b.area, x=X(b.area.x), y=Y(b.area.y),
                                              w=W(b.area.w), h=Y(b.area.h))
        buttons.append(styled(b, x=X(b.x), y=Y(b.y), width=W(width) if width else None,
                              thumb=thumb, area=area))
    return dataclasses.replace(
        menu, buttons=buttons,
        texts=[styled(t, x=X(t.x), y=Y(t.y), line_spacing=round(t.line_spacing * ky),
                      width=t.width and W(t.width), height=t.height and Y(t.height),
                      animate=moved(t.animate))
               for t in menu.texts],
        shapes=[dataclasses.replace(s, x=X(s.x), y=Y(s.y), w=W(s.w), h=Y(s.h))
                for s in menu.shapes],
        images=[dataclasses.replace(p, x=X(p.x), y=Y(p.y), w=W(p.w), h=Y(p.h),
                                    animate=moved(p.animate))
                for p in menu.images])


def hd_project(project, probe):
    """The project with an HD disc and every menu scaled to it."""
    return dataclasses.replace(project, disc=hd_disc(project.disc),
                               menus=[scale_menu(m, project.disc, probe) for m in project.menus])


# --------------------------------------------------------------------------
# the Interactive Graphics stream
# --------------------------------------------------------------------------

def _over(top, look):
    """`top` (r, g, b, a) painted over the RGBA pixel `look`."""
    a = top[3] / 255
    la = look[3] / 255
    out_a = a + la * (1 - a)
    if out_a <= 0:
        return (0, 0, 0, 0)
    rgb = [round((t * a + c * la * (1 - a)) / out_a) for t, c in zip(top[:3], look[:3])]
    return (*rgb, round(out_a * 255))


def straight(px):
    """An RGBA pixel drawn over transparent black (what drawtext and overlay
    make: colour already multiplied by alpha) with its colour restored."""
    r, g, b, a = px
    if 0 < a < 255:
        return (min(255, round(r * 255 / a)), min(255, round(g * 255 / a)),
                min(255, round(b * 255 / a)), a)
    return tuple(px)


def popup_states(menu, geoms, canvas, look):
    """For each button: its area of the transparent menu picture `look`
    (RGBA bytes, canvas size, drawn over transparent black) as it is, and
    with the highlight shapes in the highlight and select colours painted
    over it: [(normal, selected, activated)] RGBA bytes."""
    W = canvas.width
    hl, sel = png4.parse_color(menu.highlight_color), png4.parse_color(menu.select_color)
    out = []
    for g in geoms:
        x0, y0, x1, y1 = g.rect
        w = x1 - x0 + 1
        normal, selected, activated = bytearray(), bytearray(), bytearray()
        for yy in range(y0, y1 + 1):
            row = look[(yy * W + x0) * 4:(yy * W + x1 + 1) * 4]
            shape = canvas.pixels[yy * W + x0:yy * W + x0 + w]
            for i in range(w):
                px = straight(row[4 * i:4 * i + 4])
                normal += bytes(px)
                if shape[i]:
                    selected += bytes(_over(hl, px))
                    activated += bytes(_over(sel, px))
                else:
                    selected += bytes(px)
                    activated += bytes(px)
        out.append((bytes(normal), bytes(selected), bytes(activated)))
    return out


def ig_stream(menu, geoms, canvas, commands, frame_rate, follow_selection=False, look=None):
    """The menu's buttons as an IG stream (.sup layout: "PG" segments), made
    by bdmvkit (igs.ig_stream) from each button's state pictures.

    geoms: the builder's ButtonGeom list (HD pixels), canvas: its highlight
    canvas (index 1 where a button's shape is), drawn in the highlight,
    select and normal colours; commands(button) -> its navigation commands;
    frame_rate: the video's frame rate code; follow_selection: no default
    button, the selected one (PSR 10) is kept. look: a pop-up menu: the
    menu's transparent RGBA picture, whose button areas are the buttons (see
    popup_states)."""
    by_id = {b.id: b for b in menu.buttons}
    ids = {g.id for g in geoms}
    W = canvas.width
    states = [menu.normal_color, menu.highlight_color, menu.select_color]
    crops = popup_states(menu, geoms, canvas, look) if look is not None else None
    buttons = []
    for k, g in enumerate(geoms):
        x0, y0, x1, y1 = g.rect
        w, h = x1 - x0 + 1, y1 - y0 + 1
        if crops:
            normal, selected, activated = crops[k]
        else:
            shape = b"".join(bytes(canvas.pixels[(y0 + yy) * W + x0:(y0 + yy) * W + x0 + w])
                             for yy in range(h))
            # (the canvas marks the shape with 1; each state draws it in its own
            # colour; no normal colour: nothing until selected)
            normal, selected, activated = [
                c and b"".join(bytes(png4.parse_color(c)) if p else bytes(4) for p in shape)
                for c in states]
        nav = {d: g.nav[d] if g.nav.get(d) in ids else g.id
               for d in ("up", "down", "left", "right")}
        buttons.append(igs.Button(g.id, x0, y0, w, h, selected, activated, normal,
                                  commands(by_id[g.id]), nav, bool(g.auto)))
    # a menu links open on a particular button: the player's selection (which
    # its movie object sets) decides, not a fixed default
    default = menu.default_button if menu.default_button in ids else None
    try:
        return igs.ig_stream(buttons, frame_rate, default=default, popup=look is not None,
                             button_offset=menu.button_offset,
                             follow_selection=follow_selection,
                             size=(canvas.width, canvas.height))
    except BdmvError as e:
        raise OncemoreError(f"menu {menu.id!r}: {e.message}") from e


# --------------------------------------------------------------------------
# the menu clip
# --------------------------------------------------------------------------


def popup_stream(project, menu, work, font, commands, frame_rate):
    """`menu` (of the HD project) as a pop-up menu: drawn without its
    background, its buttons an IG stream with a pop-up composition (.sup)."""
    mb = MenuBuilder(project, work, font=font)
    geoms = mb.layout(menu)
    canvas = mb.highlight_canvas(geoms)
    inputs, graph = mb.compose(menu, transparent=True)
    raw = os.path.join(mb.work, f"{menu.id}.popup.rgba")
    tools.run([mb.ffmpeg, "-hide_banner", "-nostdin", "-y"] + inputs +
              ["-filter_complex", graph, "-map", "[out]", "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "rgba", raw],
              cwd=mb.work, log=os.path.join(mb.logs, f"menu-{menu.id}-popup.log"),
              what=f"ffmpeg (pop-up menu {menu.id})", timeout=600)
    with open(raw, "rb") as f:
        look = f.read()
    if len(look) != canvas.width * canvas.height * 4:
        raise OncemoreError(f"menu {menu.id!r}: the pop-up picture has the wrong size")
    sup = os.path.join(mb.work, f"{menu.id}.popup.sup")
    with open(sup, "wb") as f:
        f.write(ig_stream(menu, geoms, canvas, commands, frame_rate, look=look))
    return sup


def encode_menu(project, menu, work, font, commands, max_bps, fast=False, on_progress=None,
                probe=None):
    """Draw and encode one menu as a Blu-ray menu clip.

    project / menu: the HD project and its (scaled) menu (hd_project).
    Returns {"m2ts", "still", "loop_point", "audio"}."""
    mb = MenuBuilder(project, work, font=font)
    geoms = mb.layout(menu)
    canvas = mb.highlight_canvas(geoms)
    disc = project.disc
    fps = disc.fps
    video_format, frame_rate = bluray.bd_format(fps, disc)
    sup = os.path.join(mb.work, f"{menu.id}.ig.sup")
    with open(sup, "wb") as f:
        f.write(ig_stream(menu, geoms, canvas, commands, frame_rate,
                          follow_selection=menu.id in project.entry_buttons))
    music = menu.audio or (menu.background_video if menu.background_video and
                           mb._probe(menu.background_video).get("has_audio") else None)
    still = not (menu.background_video or music or menu.fade_in or animated(menu))
    dur = STILL_SECONDS if still else mb.menu_duration(menu)
    num, den = bluray.bd_fps(fps, disc)
    finish = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setsar=1"
    if menu.fade_in and not still:
        finish = f"fade=t=in:st=0:d={menu.fade_in:.3f}," + finish
    if menu.background_video or animated(menu):
        inputs, graph = mb.compose(menu, animate=True)
        graph = graph.replace("[out]", "[menu]") + f";[menu]{finish}[v]"
    else:
        base = mb.render_base(menu)
        inputs = ["-loop", "1", "-framerate", f"{num}/{den}", "-t", f"{dur:.3f}", "-i", base]
        graph = f"[0:v]{finish}[v]"
    n = inputs.count("-i")
    maps = ["-map", "[v]"]
    audio = []
    if music:
        if menu.audio:
            inputs += ["-i", menu.audio]
            src = f"[{n}:a:0]"
            n += 1
        else:
            src = "[0:a:0]"
        afade = f",afade=t=in:st=0:d={menu.fade_in:.3f}" if menu.fade_in else ""
        graph += f";{src}aresample=48000{afade},apad[a]"
        maps += ["-map", "[a]"]
        audio = ["-c:a", "ac3", "-b:a", "192000", "-ac", "2", "-streamid", f"1:{bluray.AUDIO_PID}"]
    if menu.buttons_at_loop and not still:
        # the composition at the loop point: no buttons during the intro
        inputs += ["-itsoffset", f"{menu.loop_point:.3f}"]
    inputs += ["-f", "sup", "-i", sup]
    maps += ["-map", f"{n}:0"]
    keys = [menu.loop_point] if menu.loop_point and not still else []
    video = bluray.stream_video_args(fps, max_bps, fast, keys, disc)
    m2ts = os.path.join(mb.work, f"{menu.id}.m2ts")
    ig_index = 2 if music else 1
    encode.run_ffmpeg(inputs + ["-filter_complex", graph] + maps + video + audio +
                      ["-c:s", "copy", "-streamid", f"0:{bluray.VIDEO_PID}",
                       "-streamid", f"{ig_index}:{bluray.IG_PID}", "-t", f"{dur:.3f}",
                       "-f", "mpegts", "-mpegts_m2ts_mode", "1",
                       "-mpegts_pmt_start_pid", str(bluray.PMT_PID), m2ts],
                      dur, os.path.join(work, "logs", f"menu-{menu.id}-bd.log"), on_progress,
                      cwd=mb.work, what=f"ffmpeg (menu {menu.id})")
    patch_ig_stream_type(m2ts)
    out = {"m2ts": m2ts, "still": still, "loop_point": menu.loop_point if not still else 0,
           "audio": bool(music)}
    if still and menu.loop is not None:
        # a still menu that times out: its picture is held for its length
        out["still_time"] = max(1, min(65535, round(mb.menu_duration(menu))))
    return out


def unsupported(project):
    """What the Blu-ray menus leave out (reported as build warnings)."""
    return []
