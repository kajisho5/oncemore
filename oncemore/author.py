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

Several titlesets (titles with another aspect ratio or audio codec):
* Menus stay in titleset 1. Buttons reach titles and chapters of other
  titlesets with `jump titleset N title K [chapter C]`, which dvdauthor
  routes through VMGM "jumppads" (`jumppad="yes"`).
* A title outside titleset 1 cannot call titleset 1's menus directly, so it
  stores the target menu in g1 and calls the VMGM title menu, which jumps to
  the root menu of titleset 1, whose dispatcher reads g1.

"Play all" (only emitted when a button or first play uses it):
* GPRM g2 is 1 while playing everything. The playall button / first play
  sets it and starts the first title; title and chapter buttons clear it.
* Each title's <post> first checks g2 and jumps to the next title in project
  order; the last title clears g2 and then follows its own end_action. So a
  title played on its own still returns where its end_action says.
"""

import os
from xml.sax.saxutils import quoteattr

from . import tools
from .project import chapter_points, format_time, parse_action

NAV_REG = "g1"
PLAYALL_REG = "g2"


def _menu_number(project, mid):
    return project.menu(mid).number


def _title_ref(project, tid, from_titleset):
    """`title K` within the current titleset, else `titleset N title K`."""
    t = project.title(tid)
    if t.titleset == from_titleset:
        return f"title {t.number}"
    return f"titleset {t.titleset} title {t.number}"


def button_command(project, action):
    """Command executed by a menu button (menu domain of titleset 1)."""
    kind, target, num = parse_action(action)
    single = f"{PLAYALL_REG} = 0; " if project.uses_playall else ""
    if kind == "menu":
        return f"jump menu {_menu_number(project, target)};"
    if kind == "playall":
        return f"{PLAYALL_REG} = 1; jump {_title_ref(project, project.titles[0].id, 1)};"
    if kind == "title":
        return f"{single}jump {_title_ref(project, target, 1)};"
    if kind == "chapter":
        return f"{single}jump {_title_ref(project, target, 1)} chapter {num};"
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


def end_command(project, action, title=None):
    """<post> of `title` (default: one in titleset 1)."""
    ts = title.titleset if title else 1
    if title is not None and project.uses_playall:
        nxt = project.playall_next(title)
        if nxt is None:
            pre = f"{PLAYALL_REG} = 0; "
        else:
            pre = f"if ({PLAYALL_REG} == 1) {{ jump {_title_ref(project, nxt.id, ts)}; }} "
        return pre + _end_command(project, action, ts)
    return _end_command(project, action, ts)


def _end_command(project, action, ts):
    kind, target, _ = parse_action(action)
    if kind == "menu":
        n = _menu_number(project, target)
        reg = f"{NAV_REG} = {n if n != 1 else 0};"
        if ts == 1:
            return f"{reg} call menu entry root;"
        return f"{reg} call vmgm menu entry title;"
    if kind == "title":
        return f"jump {_title_ref(project, target, ts)};"
    return "exit;"


def first_play_command(project):
    kind, target, _ = parse_action(project.disc.first_play)
    sub = default_subtitle(project)
    pre = f"subtitle = {64 + sub}; " if sub is not None else ""
    if kind == "menu":
        n = _menu_number(project, target)
        return f"{pre}{NAV_REG} = {n if n != 1 else 0}; jump titleset 1 menu entry root;"
    if kind == "playall":
        pre += f"{PLAYALL_REG} = 1; "
        target = project.titles[0].id
    t = project.title(target)
    if t.titleset == 1:
        return f"{pre}jump title {t.number};"
    return f"{pre}jump titleset {t.titleset} title {t.number};"


def video_tag(disc):
    ws = ' widescreen="nopanscan"' if disc.aspect == "16:9" else ""
    return f'<video format="{disc.standard.lower()}" aspect="{disc.aspect}"{ws}/>'


def audio_tags(project, titles=None):
    """One <audio> per stream index used by the titles of a titleset."""
    titles = titles or project.titles
    codec = titles[0].audio_codec
    base = ('format="pcm" quant="16bps" samplerate="48khz" channels="2"' if codec == "lpcm"
            else f'format="ac3" channels="{titles[0].audio_channels}"')
    n = max(len(t.audio_tracks) for t in titles) or 1
    langs = (project.audio_langs + [None] * n)[:n]
    return [f'<audio {base}' + (f' lang="{lang}"' if lang else "") + "/>" for lang in langs]


def subpicture_tags(project, titles=None):
    titles = titles or project.titles
    n = max(len(t.subtitles) for t in titles)
    return [f'<subpicture lang="{lang}"/>' if lang else "<subpicture/>"
            for lang in project.subtitle_langs[:n]]


def chapters_attr(chapters, fps):
    return ",".join(format_time(c) for c in chapter_points(chapters, fps)[1])


def build_xml(project, menu_files, title_files, dest):
    """menu_files / title_files: {id: path to the .mpg}."""
    disc = project.disc
    multi = project.titleset_count > 1
    jumppad = ' jumppad="yes"' if multi else ""
    x = [f'<dvdauthor dest={quoteattr(dest)}{jumppad}>', "  <vmgm>",
         f"    <fpc>{first_play_command(project)}</fpc>"]
    if project.menus:
        # With one titleset the top-menu button resets g1 (always the root
        # menu). With several, titles of other titlesets come back through
        # here with their target menu in g1, so it must survive.
        reset = "" if multi else f"{NAV_REG} = 0; "
        x += ["    <menus>", f"      {video_tag(disc)}",
              f'      <pgc entry="title"><pre>{reset}jump titleset 1 menu entry root;</pre></pgc>',
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
    for ts in range(1, project.titleset_count + 1):
        if ts > 1:
            x.append("  <titleset>")
        titles = project.titleset_titles(ts)
        x += ["    <titles>", f"      {video_tag(project.disc_for(titles[0]))}"]
        x += [f"      {tag}" for tag in audio_tags(project, titles)
              + subpicture_tags(project, titles)]
        for t in titles:
            x.append("      <pgc>")
            x.append(f"        <vob file={quoteattr(title_files[t.id])} "
                     f'chapters="{chapters_attr(t.chapters, disc.fps)}"/>')
            x.append(f"        <post>{end_command(project, t.end_action, t)}</post>")
            x.append("      </pgc>")
        x += ["    </titles>", "  </titleset>"]
    x += ["</dvdauthor>", ""]
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
