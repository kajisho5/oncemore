"""dvdauthor XML generation.

Layout (phase 1): one titleset holding every title and every menu.

* Menus are the titleset's menu PGCs, in project order except that the
  first-play menu is PGC 1, marked entry="root".
* Inside the menu domain buttons can reach any menu (LinkPGCN), any title
  (JumpVTS_TT) and any chapter (JumpVTS_PTT) directly.
* From a title only the *root* menu can be called (CallSS). To return to an
  arbitrary menu, the title's <post> stores the menu number in GPRM g1 and
  calls the root menu, whose <pre> dispatches on g1 and clears it.
* The VMGM first-play program uses the same trick to start on any menu.
* The VMGM "title" (top) menu has no video; it just jumps to the root menu.
"""

import os
from xml.sax.saxutils import quoteattr

from . import tools
from .project import chapter_points, format_time, parse_action

NAV_REG = "g1"


def _menu_number(project, mid):
    return project.menu(mid).number


def _title_number(project, tid):
    return project.title(tid).number


def button_command(project, action):
    """Command executed by a menu button (titleset menu domain)."""
    kind, target, num = parse_action(action)
    if kind == "menu":
        return f"jump menu {_menu_number(project, target)};"
    if kind == "title":
        return f"jump title {_title_number(project, target)};"
    if kind == "chapter":
        return f"jump title {_title_number(project, target)} chapter {num};"
    if kind == "audio":
        return f"audio = {num - 1};"
    if kind == "subtitle":
        # SPRM2: stream number in bits 0-5, bit 6 = display on
        return "subtitle = 0;" if num == 0 else f"subtitle = {64 + num - 1};"
    return "exit;"


def default_subtitle(project):
    """0-based subtitle stream to show from the start, or None."""
    for t in project.titles:
        for j, sub in enumerate(t.subtitles):
            if sub.default:
                return j
    return None


def end_command(project, action):
    """<post> of a title."""
    kind, target, _ = parse_action(action)
    if kind == "menu":
        n = _menu_number(project, target)
        return f"{NAV_REG} = {n if n != 1 else 0}; call menu entry root;"
    if kind == "title":
        return f"jump title {_title_number(project, target)};"
    return "exit;"


def first_play_command(project):
    kind, target, _ = parse_action(project.disc.first_play)
    sub = default_subtitle(project)
    pre = f"subtitle = {64 + sub}; " if sub is not None else ""
    if kind == "menu":
        n = _menu_number(project, target)
        return f"{pre}{NAV_REG} = {n if n != 1 else 0}; jump titleset 1 menu entry root;"
    return f"{pre}jump title {_title_number(project, target)};"


def video_tag(disc):
    ws = ' widescreen="nopanscan"' if disc.aspect == "16:9" else ""
    return f'<video format="{disc.standard.lower()}" aspect="{disc.aspect}"{ws}/>'


def audio_tags(project):
    """One <audio> per stream index used by any title."""
    codec = project.titles[0].audio_codec
    base = ('format="pcm" quant="16bps" samplerate="48khz" channels="2"' if codec == "lpcm"
            else 'format="ac3" channels="2"')
    langs = project.audio_langs or [None]
    return [f'<audio {base}' + (f' lang="{lang}"' if lang else "") + "/>" for lang in langs]


def subpicture_tags(project):
    return [f'<subpicture lang="{lang}"/>' if lang else "<subpicture/>"
            for lang in project.subtitle_langs]


def chapters_attr(chapters, fps):
    return ",".join(format_time(c) for c in chapter_points(chapters, fps)[1])


def build_xml(project, menu_files, title_files, dest):
    """menu_files / title_files: {id: path to the .mpg}."""
    disc = project.disc
    x = [f'<dvdauthor dest={quoteattr(dest)}>', "  <vmgm>",
         f"    <fpc>{first_play_command(project)}</fpc>"]
    if project.menus:
        x += ["    <menus>", f"      {video_tag(disc)}",
              f'      <pgc entry="title"><pre>{NAV_REG} = 0; jump titleset 1 menu entry root;</pre></pgc>',
              "    </menus>"]
    x += ["  </vmgm>", "  <titleset>"]
    if project.menus:
        x += ["    <menus>", f"      {video_tag(disc)}"]
        for m in project.menus:
            attrs = ' entry="root"' if m.number == 1 else ""
            x.append(f"      <pgc{attrs}>")
            if m.number == 1:
                others = [o for o in project.menus if o.number != 1]
                if others:
                    disp = " ".join(f"if ({NAV_REG} == {o.number}) {{ {NAV_REG} = 0; jump menu {o.number}; }}"
                                    for o in others)
                    x.append(f"        <pre>{disp}</pre>")
            for b in m.buttons:
                x.append(f"        <button name={quoteattr(b.id)}>{button_command(project, b.action)}</button>")
            x.append(f"        <vob file={quoteattr(menu_files[m.id])}/>")
            x.append("        <post>jump cell 1;</post>")
            x.append("      </pgc>")
        x.append("    </menus>")
    x += ["    <titles>", f"      {video_tag(disc)}"]
    x += [f"      {tag}" for tag in audio_tags(project) + subpicture_tags(project)]
    for t in project.titles:
        x.append("      <pgc>")
        x.append(f"        <vob file={quoteattr(title_files[t.id])} "
                 f'chapters="{chapters_attr(t.chapters, disc.fps)}"/>')
        x.append(f"        <post>{end_command(project, t.end_action)}</post>")
        x.append("      </pgc>")
    x += ["    </titles>", "  </titleset>", "</dvdauthor>", ""]
    return "\n".join(x)


def run_dvdauthor(xml_path, project, log):
    tools.require(["dvdauthor"])
    tools.run([tools.find("dvdauthor"), "-x", xml_path],
              env={"VIDEO_FORMAT": project.disc.standard}, log=log, what="dvdauthor")


def video_ts_size(dvd_dir):
    total = 0
    vts = os.path.join(dvd_dir, "VIDEO_TS")
    for name in os.listdir(vts):
        total += os.path.getsize(os.path.join(vts, name))
    return total
