"""VIDEO_TS written by vtskit (oncemore/_vendor/vtskit), in place of dvdauthor.

The project's navigation stays in dvdauthor's command language, as
oncemore.author writes it (its XML is kept in the work folder as a readable
record); vtskit.lang compiles each text for the domain it runs in. The
menus' buttons (their areas, arrow keys and the shapes that light up) come
from oncemore.menu's layout; the subtitles are muxed by oncemore.subtitles
with vtskit; the remote keys a title or menu turns off and the menus'
button offsets go straight into the IFOs and navigation packs.

Layout (as author.build_xml describes it): the menus in titleset 1, numbered
as the project does (an intro and its loop as two program chains, link
transitions after the menus), a root menu of commands alone in every other
titleset, the video manager's title menu of commands alone, and the pad
program chains dvdauthor calls jumppads where a menu jumps to a chapter of
another titleset.
"""

import os

from . import author, uops
from .project import chapter_points, title_fps
from ._vendor.vtskit import lang, spu, titleset, vmg
from ._vendor.vtskit.menu import Button, Menu
from ._vendor.vtskit.titleset import Audio, Subpicture, Title

PROVIDER = "oncemore"


def ycc(colour):
    """(Y, Cr, Cb, contrast) of "#RRGGBB" or "#RRGGBBAA" (BT.601, as spumux
    converts them: alpha >> 4 is the contrast)."""
    from . import png4
    r, g, b, a = png4.parse_color(colour)

    def clamp(v):
        return max(0, min(255, int(round(v))))
    y = 16 + (65.738 * r + 129.057 * g + 25.064 * b) / 256
    cr = 128 + (112.439 * r - 94.154 * g - 18.285 * b) / 256
    cb = 128 + (-37.945 * r - 74.494 * g + 112.439 * b) / 256
    return clamp(y), clamp(cr), clamp(cb), a >> 4


def disc_of(project):
    """The vtskit.lang.Disc describing the project's titles and menus."""
    titles = {(t.titleset, t.number): t.global_number for t in project.titles}
    vmgm = lang.Menus(1, {"title": 1}) if project.menus else lang.Menus()
    sets = {}
    for ts in range(1, project.titleset_count + 1):
        if not project.menus:
            sets[ts] = lang.Menus()
        elif ts == 1:
            count = max(m.loop_pgc for m in project.menus) + len(project.link_transitions)
            sets[ts] = lang.Menus(count, {"root": 1})
        else:
            sets[ts] = lang.Menus(1, {"root": 1})
    return lang.Disc(titles, vmgm, sets)


def _menu(project, disc, m, stream, geoms, overlay, buttons_texts, pre, post, cells=(0.0,),
          entry=None):
    """A vtskit Menu of a project menu's program chain."""
    commands, post_cmds = disc.menu(buttons_texts, post, "vtsm", 1) if geoms else ([], disc.compile(post, "vtsm", 1))
    ids = [g.id for g in geoms]
    buttons = []
    for g, cmd in zip(geoms, commands):
        nav = {d: ids.index(g.nav[d]) + 1 for d in ("up", "down", "left", "right") if g.nav.get(d) in ids}
        buttons.append(Button(tuple(g.rect), cmd, nav.get("up", 0), nav.get("down", 0), nav.get("left", 0),
                              nav.get("right", 0), auto=g.auto))
    hl, sel = ycc(m.highlight_color), ycc(m.select_color)
    return Menu(stream, buttons, overlay, hl, sel, ycc(m.normal_color) if m.normal_color else None, cells,
                pre=disc.compile(pre, "vtsm", 1) if pre else (), post=post_cmds, entry=entry,
                button_offset=m.button_offset if geoms else 0, uops=uops.dvd_mask(m.prohibit))


def write(project, menu_files, title_files, dest, transition_files=None, layouts=None, palettes=None):
    """Write <dest>/VIDEO_TS. `menu_files` / `title_files`: {id: path to the
    .mpg} (a menu with its buttons after the loop point: (intro, loop));
    `transition_files`: {transition video: its .mpg}; `layouts`: {menu id:
    (its ButtonGeoms, the canvas of their shapes)}; `palettes`: {title id:
    its subtitles' colours (Y, Cr, Cb)}. Returns the files written."""
    disc = disc_of(project)
    video_ts = os.path.join(dest, "VIDEO_TS")
    layouts = layouts or {}
    palettes = palettes or {}
    W, H = project.disc.width, project.disc.height
    pan_scan = project.disc.aspect != "16:9"           # 16:9: widescreen="nopanscan"

    # titleset 1's menus, by program chain number
    chains = {}
    for m in project.menus:
        geoms, canvas = layouts[m.id]
        overlay = spu.Overlay(W, H, bytes(1 if p else 0 for p in canvas.pixels)) if geoms else None
        texts = [author.menu_button_command(project, m, b) for b in m.buttons]
        pre = author.menu_pre(project, m)
        post = author.menu_post(project, m)
        entry = "root" if m.number == 1 else None
        if m.buttons_at_loop:
            intro, loop = menu_files[m.id]
            chains[m.number] = _menu(project, disc, m, intro, [], None, [], pre,
                                     f"jump menu {m.loop_pgc};", entry=entry)
            again = " ".join(author._button_pre(project, m))
            chains[m.loop_pgc] = _menu(project, disc, m, loop, geoms, overlay, texts, again, post)
        else:
            cells = (0.0, m.loop_point) if m.loop_point else (0.0,)
            chains[m.number] = _menu(project, disc, m, menu_files[m.id], geoms, overlay, texts, pre, post,
                                     cells, entry)
    for key, pgcn in author.transition_pgcs(project).items():
        chains[pgcn] = Menu(transition_files[key[0]],
                            post=disc.compile(author.transition_post(project, key), "vtsm", 1))
    if chains and sorted(chains) != list(range(1, len(chains) + 1)):
        raise ValueError(f"menu program chains are not numbered in order: {sorted(chains)}")

    # every titleset's titles and menus, compiled before the pads are made
    sets = []
    for ts in range(1, project.titleset_count + 1):
        titles = project.titleset_titles(ts)
        menus = [chains[n] for n in sorted(chains)] if ts == 1 else []
        if ts > 1 and project.menus:
            target = (f"{author.NAV_REG} = {author.MENUKEY_REG}; if ({author.NAV_REG} == 0) {{ {author.NAV_REG} = 1; }}"
                      if project.uses_remote_menu else f"{author.NAV_REG} = 1;")
            menus.append(Menu(None, pre=disc.compile(f"{target} jump vmgm menu entry title;", "vtsm", ts),
                              entry="root"))
        n_audio = max(len(t.audio_tracks) for t in titles) or 1
        langs = (project.audio_langs + [None] * n_audio)[:n_audio]
        channels = 2 if titles[0].audio_codec == "lpcm" else titles[0].audio_channels
        audio = tuple(Audio(lang, channels) for lang in langs)
        sub_langs = project.subtitle_langs
        vts_titles = []
        for t in titles:
            fps = title_fps(t, project.disc)
            points = chapter_points(t.chapters, fps)[1]
            held = bool(t.slideshow and t.slideshow.advance == "manual")
            ends = author.item_end_chapters(project, t)
            pre = author.title_pre(project, t)
            cell_commands = {k: disc.compile(f"if ({author.ITEM_END_REG} == {k}) jump pgc tail;", "vts", ts)[0]
                             for k in ends}
            vts_titles.append(Title(
                title_files[t.id], tuple(points), audio[:max(1, len(t.audio_tracks))],
                tuple(Subpicture(sub_langs[j] if j < len(sub_langs) else None) for j in range(len(t.subtitles))),
                palette=tuple(palettes.get(t.id, ())),
                pre=disc.compile(pre, "vts", ts) if pre else (),
                post=disc.compile(author.end_command(project, t.end_action, t), "vts", ts),
                cell_commands=cell_commands,
                stills={k: None for k in range(1, len(points) + 1)} if held else {},
                uops=uops.dvd_mask(t.prohibit)))
        sets.append((ts, vts_titles, menus, any(t.captions for t in titles)))
    first_play = disc.compile(author.first_play_command(project), "fp")
    vmgm_menus = []
    if project.menus:
        vmgm_menus.append(Menu(None, pre=disc.compile(author.vmgm_title_command(project), "vmgm"), entry="title"))
    vmgm_menus += [Menu(None, pre=pad) for pad in disc.vmgm_pads()]

    written = []
    files = []
    for ts, vts_titles, menus, captions in sets:
        pad = disc.vts_pad(ts)
        if pad is not None:
            menus = menus + [Menu(None, pre=pad, entry="ptt")]
        result = titleset.write(video_ts, ts, vts_titles, menus, pan_scan=pan_scan, letterbox=True,
                                captions=(captions, False))
        written.append(result)
        files += result.files
    vmg.write(video_ts, written, menus=vmgm_menus, first_play=first_play, provider=PROVIDER,
              pan_scan=pan_scan, letterbox=True)
    files += ["VIDEO_TS.IFO", "VIDEO_TS.BUP"] + (["VIDEO_TS.VOB"] if os.path.exists(os.path.join(video_ts, "VIDEO_TS.VOB")) else [])
    return sorted(files)
