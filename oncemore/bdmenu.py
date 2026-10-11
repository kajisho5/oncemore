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
"""

import dataclasses
import os
import struct

from . import bluray, encode, pgs, png4
from .errors import OncemoreError
from .menu import MenuBuilder
from .project import Disc

ICS, PDS, ODS, END = 0x18, 0x14, 0x15, 0x80
NO_OBJECT = 0xFFFF
STILL_SECONDS = 1.0            # a still menu's clip; the playlist holds its last picture


class HDDisc(Disc):
    """The disc settings with the 16:9 HD frame (for drawing menus)."""

    @property
    def width(self):
        return bluray.WIDTH

    @property
    def height(self):
        return bluray.HEIGHT

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
    ky = bluray.HEIGHT / disc.height
    if disc.aspect == "4:3":
        kx = bluray.HEIGHT * 4 / 3 / 720
        return kx, round((bluray.WIDTH - 720 * kx) / 2), ky
    return bluray.WIDTH / 720, 0, ky


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

    def styled(el, **kw):
        return dataclasses.replace(
            el, size=max(4, round(el.size * ky)),
            outline_width=max(1, round(el.outline_width * ky)) if el.outline else el.outline_width,
            shadow_offset=max(1, round(el.shadow_offset * ky)), **kw)

    buttons = []
    for b in menu.buttons:
        width = b.width
        picture = b.image or b.highlight_image
        if width is None and picture:
            info = probe(picture)
            width = max(8, round(info["width"] / sx_dvd))
        thumb = b.thumb and dataclasses.replace(b.thumb, x=X(b.thumb.x), y=Y(b.thumb.y),
                                                w=W(b.thumb.w), h=Y(b.thumb.h))
        buttons.append(styled(b, x=X(b.x), y=Y(b.y), width=W(width) if width else None,
                              thumb=thumb))
    return dataclasses.replace(
        menu, buttons=buttons,
        texts=[styled(t, x=X(t.x), y=Y(t.y)) for t in menu.texts],
        shapes=[dataclasses.replace(s, x=X(s.x), y=Y(s.y), w=W(s.w), h=Y(s.h))
                for s in menu.shapes],
        images=[dataclasses.replace(p, x=X(p.x), y=Y(p.y), w=W(p.w), h=Y(p.h))
                for p in menu.images])


def hd_project(project, probe):
    """The project with an HD disc and every menu scaled to it."""
    return dataclasses.replace(project, disc=hd_disc(project.disc),
                               menus=[scale_menu(m, project.disc, probe) for m in project.menus])


# --------------------------------------------------------------------------
# the Interactive Graphics stream
# --------------------------------------------------------------------------

def _colour(index, color):
    r, g, b, a = png4.parse_color(color)
    y, cb, cr = pgs.ycbcr((r, g, b))
    return (index, y, cr, cb, a)


def _segment(kind, data):
    return b"PG" + struct.pack(">IIBH", 0, 0, kind, len(data)) + data


def _objects(oid, w, h, pixels):
    """ODS segment(s) of one object (split when longer than a segment)."""
    coded = pgs.rle(pixels, w, h)
    data = (len(coded) + 4).to_bytes(3, "big") + struct.pack(">HH", w, h) + coded
    size = pgs.MAX_SEGMENT - 4
    chunks = [data[i:i + size] for i in range(0, len(data), size)]
    out = b""
    for k, chunk in enumerate(chunks):
        flags = (0x80 if k == 0 else 0) | (0x40 if k == len(chunks) - 1 else 0)
        out += _segment(ODS, struct.pack(">HBB", oid, 0, flags) + chunk)
    return out


def ig_stream(menu, geoms, canvas, commands, frame_rate, follow_selection=False):
    """The menu's buttons as an IG stream (.sup layout: "PG" segments).

    geoms: the builder's ButtonGeom list (HD pixels), canvas: its highlight
    canvas (index 1 where a button's shape is); commands(button) -> its
    navigation commands; frame_rate: the video's frame rate code;
    follow_selection: no default button, the selected one (PSR 10) is kept."""
    index = {g.id: k for k, g in enumerate(geoms)}
    by_id = {b.id: b for b in menu.buttons}
    palette = [(0, 16, 128, 128, 0), _colour(1, menu.highlight_color),
               _colour(2, menu.select_color)]
    if menu.normal_color:
        palette.append(_colour(3, menu.normal_color))
    states = [(1, 1), (2, 2)] + ([(0, 3)] if menu.normal_color else [])
    objects, buttons = b"", b""
    W = canvas.width
    for k, g in enumerate(geoms):
        x0, y0, x1, y1 = g.rect
        w, h = x1 - x0 + 1, y1 - y0 + 1
        crop = b"".join(bytes(canvas.pixels[(y0 + yy) * W + x0:(y0 + yy) * W + x0 + w])
                        for yy in range(h))
        ids = {}
        for slot, idx in states:            # slot: 0 normal, 1 selected, 2 activated
            oid = 3 * k + slot
            # (the canvas marks the shape with 1; each state draws it in its own colour)
            objects += _objects(oid, w, h, crop.translate(bytes([0, idx]) + bytes(254)))
            ids[slot] = oid
        nav = [index.get(g.nav.get(d), k) for d in ("up", "down", "left", "right")]
        cmds = commands(by_id[g.id])
        normal = ids.get(0, NO_OBJECT)
        button = struct.pack(">HHBHH", k, NO_OBJECT, 0x80 if g.auto else 0, x0, y0)
        button += struct.pack(">HHHH", *nav)
        button += struct.pack(">HHB", normal, normal, 0)
        button += struct.pack(">BHHB", 0xFF, ids[1], ids[1], 0)
        button += struct.pack(">BHH", 0xFF, ids[2], ids[2])
        button += struct.pack(">H", len(cmds)) + b"".join(cmds)
        # one button per overlap group: buttons do not overlap
        buttons += struct.pack(">HB", k, 1) + button
    # a menu links open on a particular button: the player's selection (which
    # its movie object sets) decides, not a fixed default
    default = 0xFFFF if follow_selection else index.get(menu.default_button, 0)
    page = struct.pack(">BB", 0, 0) + bytes(8)           # page 0, no user-operation mask
    page += bytes([0, 0]) + bytes([0, 0])                  # no in / out effects
    page += struct.pack(">BHHBB", 0, default, NO_OBJECT, 0, len(geoms)) + buttons
    body = bytes([0x00]) + bytes(10)                       # multiplexed, always on; no timeouts
    body += (0).to_bytes(3, "big") + bytes([1]) + page     # no user time-out; one page
    ics = struct.pack(">HHB", bluray.WIDTH, bluray.HEIGHT, frame_rate << 4)
    ics += struct.pack(">HB", 0, 0x80)                     # composition 0, epoch start
    ics += bytes([0xC0]) + len(body).to_bytes(3, "big") + body
    if len(ics) > pgs.MAX_SEGMENT:
        raise OncemoreError(f"menu {menu.id!r}: too many button commands for one composition")
    pds = bytes([0, 0]) + b"".join(bytes(e) for e in palette)
    return _segment(ICS, ics) + _segment(PDS, pds) + objects + _segment(END, b"")


# --------------------------------------------------------------------------
# the menu clip
# --------------------------------------------------------------------------

def patch_ig_stream_type(path, pmt_pid=bluray.PMT_PID, pid=bluray.IG_PID):
    """ffmpeg muxes the IG stream as a PGS stream (stream type 0x90): mark it
    0x91 in every PMT of the clip (and fix the section CRC)."""
    with open(path, "r+b") as f:
        data = bytearray(f.read())
        for off in range(0, len(data), 192):
            p = off + 4
            if (data[p + 1] & 0x1F) << 8 | data[p + 2] != pmt_pid or not data[p + 1] & 0x40:
                continue
            q = p + 4
            if data[p + 3] & 0x20:
                q += 1 + data[q]
            q += 1 + data[q]                                # pointer field
            length = (data[q + 1] & 0x0F) << 8 | data[q + 2]
            end = q + 3 + length - 4
            info = (data[q + 10] & 0x0F) << 8 | data[q + 11]
            e = q + 12 + info
            while e < end:
                es_pid = (data[e + 1] & 0x1F) << 8 | data[e + 2]
                if es_pid == pid:
                    data[e] = bluray.CODING_IG
                e += 5 + ((data[e + 3] & 0x0F) << 8 | data[e + 4])
            data[end:end + 4] = _crc32(bytes(data[q:end])).to_bytes(4, "big")
        f.seek(0)
        f.write(data)


def _crc32(data):
    """MPEG-2 section CRC (polynomial 0x04C11DB7, no reflection)."""
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b << 24
        for _ in range(8):
            crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if crc & 0x80000000 else \
                (crc << 1) & 0xFFFFFFFF
    return crc


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
    video_format, frame_rate = bluray.FORMATS[fps]
    sup = os.path.join(mb.work, f"{menu.id}.ig.sup")
    with open(sup, "wb") as f:
        f.write(ig_stream(menu, geoms, canvas, commands, frame_rate,
                          follow_selection=menu.id in project.entry_buttons))
    music = menu.audio or (menu.background_video if menu.background_video and
                           mb._probe(menu.background_video).get("has_audio") else None)
    still = not (menu.background_video or music or menu.fade_in)
    dur = STILL_SECONDS if still else mb.menu_duration(menu)
    num, den = fps
    finish = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setsar=1"
    if menu.fade_in and not still:
        finish = f"fade=t=in:st=0:d={menu.fade_in:.3f}," + finish
    if menu.background_video:
        inputs, graph = mb.compose(menu)
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
    video = bluray.stream_video_args(fps, max_bps, fast, keys)
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
    return {"m2ts": m2ts, "still": still, "loop_point": menu.loop_point if not still else 0,
            "audio": bool(music)}


def unsupported(project):
    """What the Blu-ray menus leave out (reported as build warnings)."""
    out = []
    for m in project.menus:
        if m.loop is not None:
            out.append(f"menu {m.id!r}: on Blu-ray it repeats until a button is pressed "
                       "(no loop count or end action)")
        if any(b.override for b in m.buttons):
            out.append(f"menu {m.id!r}: end-action overrides are DVD-only")
    if any(t.remote_menu for t in project.titles):
        out.append("the Menu key during a title opens the top menu on Blu-ray "
                   "(no menu per title)")
    return out
