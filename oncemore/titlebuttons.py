"""Buttons over a title's picture (DVD), written by vtskit.

A title's buttons (project.TitleButton) each show from a start to an end.
The title is cut into stretches over which the same buttons show
(project.button_stretches); each stretch is one vtskit.menu.TitleButtons:
its highlight information goes into the navigation packs of the VOBUs that
play during it, and its overlay (code 1 over the buttons' areas, drawn by
nothing until a button is selected) into subpicture stream 0 as a forced
subpicture. The times the buttons change are frame times and start VOBUs
(encode forces key frames there, as at chapters), so stretches meet where
VOBUs do (and where a frame's time and a VOBU's start differ, vtskit gives
the VOBU the stretch covering more of it).

The arrow keys go between the buttons of a stretch as between a menu's
(oncemore.navigation: the nearest button that way). A button's action is
compiled for the title's domain (author.title_button_command); one that
takes several commands runs them from the title's post commands, as
dvdauthor arranges (vtskit.lang).
"""

import os

from . import author, navigation
from .project import button_stretches, frame_at
from ._vendor.vtskit import menu as vmenu
from ._vendor.vtskit import ps as vps
from ._vendor.vtskit import subtitles as vsubs


def _snap(t, fps):
    """A time at the start of its frame."""
    num, den = fps
    return frame_at(t, fps) * den / num


def stretches(title, fps):
    """[(start, end or None, [TitleButton])] over which the same buttons
    show, times on frames."""
    out = []
    for a, b in button_stretches(title):
        shown = [x for x in title.buttons
                 if x.start <= a and (x.end is None or b is not None and x.end >= b)]
        out.append((_snap(a, fps), None if b is None else _snap(b, fps), shown))
    return out


def colours(title):
    """The title's palette for its buttons: (Y, Cr, Cb) of the highlight and
    the selection, and their contrasts."""
    from .videots import ycc
    hl, sel = ycc(title.button_highlight), ycc(title.button_select)
    return (hl[:3], sel[:3]), (hl[3], sel[3])


def vts_buttons(title, fps, commands):
    """The vtskit TitleButtons of the title, `commands` being the command
    of each of title.buttons (vtskit.lang.Disc.menu)."""
    _, (hl, sel) = colours(title)
    command = {b.id: c for b, c in zip(title.buttons, commands)}
    out = []
    for start, end, shown in stretches(title, fps):
        rects = {b.id: (b.x, b.y, b.x + b.width, b.y + b.height) for b in shown}
        nav = navigation.compute([(b.id, rects[b.id], None) for b in shown])
        number = {b.id: k for k, b in enumerate(shown, 1)}
        buttons = [vmenu.Button(rects[b.id], command[b.id],
                                *(number[nav[b.id][d]] for d in navigation.DIRECTIONS))
                   for b in shown]
        out.append(vmenu.TitleButtons(start, end, buttons, highlight=(0, hl), select=(1, sel)))
    return out


def compile_buttons(project, disc, title, post):
    """(the command of each button, the title's post commands): the
    buttons' commands in the title's domain, the post text after a
    dispatcher when a button needs several commands."""
    texts = [author.title_button_command(project, title, b.action) for b in title.buttons]
    return disc.menu(texts, post, "vts", title.titleset)


def mux(title, mpg, fps, length, width, height):
    """The title's stream with the buttons' overlays in subpicture stream 0
    (one forced subpicture a stretch): the path of the new stream."""
    cues = [b.cue(width, height, length) for b in vts_buttons(title, fps, [bytes(8)] * len(title.buttons))]
    out = os.path.splitext(mpg)[0] + ".buttons.mpg"
    with vps.Mapped(mpg) as data, open(out, "wb") as f:
        vsubs.mux(data, {0: cues}, out=f)
    return out
