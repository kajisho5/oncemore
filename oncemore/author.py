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
  the root menu of titleset 1, whose dispatcher reads g1. Their own (empty)
  root menu does the same, so the remote's Menu key works there too.

Registers: g0 playlist state (which item of which playlist is playing, 0 =
none), g1 target menu (consumed by the root menu, then 0), g2 play-all flag,
g3 Menu-key target of the playing title (`remote_menu`), g4 loop counter of
the current menu, g5-g11 last button used in menus 1-7, g12 the chapter at
which the current playlist item ends (0 = the end of the title).
g13-g15 are dvdauthor's scratch registers (multi-statement buttons and
expressions), so they stay untouched. A multi-statement button that does not
jump falls through into the next button's code in dvdauthor's dispatcher, so
only buttons that leave the menu get the "remember" prefix.
An end-action override on a button (`override`, Encore-style: "play this title,
then go there instead of its own end action") is a number in the next free
register: the button sets it, every other way of starting a title clears it,
and each title's <post> first checks it (and clears it) before its usual end.
"Return to the last menu" (`lastmenu`, for title / playlist end actions and
overrides) keeps the number of the menu shown last in the next free
register (each menu's <pre> sets it) and routes there like any menu end
action; before any menu was shown it is 0, so the Menu-key target / first
menu opens.
A resume button (`resume`, only when one is used) takes the first register
nobody else uses (`resume_reg`) as a flag: 1 while a title is playing (its
<pre>), 0 once it ended (its <post>). The button resumes the title the
Menu / Title key left (the player's resume information) when the flag is
1, and otherwise plays the first title from the start, since a player has
nothing to resume at the start of the disc or after a title ended.
A link to a particular button of a menu (`menu:<id>:<button>`) puts that
button (k * 1024) in the next free register (`entry_reg`) before it jumps;
the menus such links reach check it in their <pre> after their usual
default / remembered button, highlight it and clear it. A menu whose
buttons wait for the loop point checks it in the intro and again, then
clears it, in the PGC with the buttons.
A link transition (a button's `transition`) is a menu PGC of its own after
the menus' (`transition_pgcs`): the button jumps there, the video plays
without buttons, and its <post> does what the button would have done
(streams, override, link). It stays in the menu domain, so a menu-to-menu
dissolve never leaves the menus, and "last menu" is still the one whose
button was pressed.
The VMGM title menu is what the Title / Top Menu key opens: g1 == 0 there
means the key was pressed (routes always set g1), so `disc.title_key` applies.

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
from .project import chapter_points, format_time, parse_action, title_fps, transition_key

NAV_REG = "g1"
PLAYALL_REG = "g2"
MENUKEY_REG = "g3"
LOOP_REG = "g4"
STATE_REG = "g0"
ITEM_END_REG = "g12"
PLAYLIST_ROUTE = 1000   # g1 value: "continue the playlist" (VMGM, between titlesets)
CHAPTER_ROUTE = 2000    # g1 value 2000 + k: "play end_chapters()[k]" (VMGM, between titlesets)


def button_reg(menu):
    """Register remembering the last button of `menu`, or None."""
    if menu.remember_button and menu.number <= 7:
        return f"g{4 + menu.number}"
    return None


def _free_regs(project):
    """Registers this project's navigation leaves free, in the order they are
    handed out (resume flag first, then the override)."""
    used = {NAV_REG}
    if project.uses_playlists:
        used |= {STATE_REG, ITEM_END_REG}
    if project.uses_playall:
        used.add(PLAYALL_REG)
    if project.uses_remote_menu:
        used.add(MENUKEY_REG)
    if any(m.loop is not None for m in project.menus):
        used.add(LOOP_REG)
    used |= {button_reg(m) for m in project.menus} - {None}
    return [f"g{n}" for n in (12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 0) if f"g{n}" not in used]


def resume_reg(project):
    """Register flagging "a title was interrupted" for resume buttons, or None."""
    free = _free_regs(project) if project.uses_resume else []
    return free[0] if free else None


def override_reg(project):
    """Register holding the end-action override of the playing title (0 =
    none, k = project.overrides[k - 1]), or None."""
    if not project.overrides:
        return None
    free = _free_regs(project)[1 if project.uses_resume else 0:]
    return free[0] if free else None


def last_menu_reg(project):
    """Register holding the number of the menu shown last (for `lastmenu`
    end actions; each menu's pre sets it), or None."""
    if not project.uses_last_menu:
        return None
    free = _free_regs(project)[int(project.uses_resume) + int(bool(project.overrides)):]
    return free[0] if free else None


def entry_reg(project):
    """Register carrying the button a link highlights in the menu it opens
    (0 = the menu's own choice), or None."""
    if not project.entry_buttons:
        return None
    k = int(project.uses_resume) + int(bool(project.overrides)) + int(project.uses_last_menu)
    free = _free_regs(project)[k:]
    return free[0] if free else None


def _entry(project, mid, button):
    """Commands before a jump to menu `mid` that highlight `button` there."""
    if not button:
        return ""
    ids = [b.id for b in project.menu(mid).buttons]
    return f"{entry_reg(project)} = {(ids.index(button) + 1) * 1024}; "


def _single(project):
    """Commands that end play-all / playlist mode (and any end-action
    override) before a single play."""
    cmd = (f"{PLAYALL_REG} = 0; " if project.uses_playall else "") + _no_override(project)
    if project.uses_playlists:
        cmd += f"{STATE_REG} = 0; {ITEM_END_REG} = 0; "
    return cmd


# -- playlists ---------------------------------------------------------------
# Every item of every playlist is a state number (g0). Starting an item sets
# g0 and g12 (its last chapter, unless it runs to the end of the title) and
# jumps to its first chapter. A chapter cell of a title has the one-instruction
# cell command "if (g12 == k) jump pgc tail" when some item ends there; the
# title's post then moves g0 to the next item (or ends the playlist).

def playlist_states(project):
    """[(state, playlist, index, item)] for every playlist item, states from 1."""
    out = []
    for pl in project.playlists:
        for i, it in enumerate(pl.items):
            out.append((len(out) + 1, pl, i, it))
    return out


def _item_jump(project, item, domain, ts=1):
    """Jump to the first chapter of `item` from a menu of titleset 1
    ("menu"), a title of titleset `ts` ("title") or the VMGM ("vmgm")."""
    t = project.title(item.title_id)
    chap = f" chapter {item.first}" if item.first > 1 else ""
    if domain == "vmgm":
        return f"jump titleset {t.titleset} title {t.number}{chap};"
    return f"jump {_title_ref(project, t.id, ts)}{chap};"


def _item_start(project, state, item):
    return f"{STATE_REG} = {state}; {ITEM_END_REG} = {item.last or 0}; "


def _no_override(project):
    return f"{override_reg(project)} = 0; " if project.overrides else ""


def playlist_start(project, pid, domain):
    state, _, _, item = next(x for x in playlist_states(project) if x[1].id == pid)
    flag = (f"{PLAYALL_REG} = 0; " if project.uses_playall else "") + _no_override(project)
    return flag + _item_start(project, state, item) + _item_jump(project, item, domain)


def playlist_dispatch(project, title):
    """Title post commands continuing the playlists whose current item is
    `title`: next item, or the playlist's end action."""
    states = playlist_states(project)
    cmds = []
    for state, pl, i, it in states:
        if it.title_id != title.id:
            continue
        if i + 1 < len(pl.items):
            nxt = pl.items[i + 1]
            go = _item_start(project, state + 1, nxt)
            if project.title(nxt.title_id).titleset == title.titleset:
                go += _item_jump(project, nxt, "title", title.titleset)
            else:
                go += f"{NAV_REG} = {PLAYLIST_ROUTE}; call vmgm menu entry title;"
        else:
            go = (f"{STATE_REG} = 0; {ITEM_END_REG} = 0; "
                  + _end_command(project, pl.end_action, title.titleset))
        cmds.append(f"if ({STATE_REG} == {state}) {{ {go} }}")
    return " ".join(cmds)


def item_end_chapters(project, title):
    """Chapters of `title` at which some playlist item stops early."""
    return sorted({it.last for _, _, _, it in playlist_states(project)
                   if it.title_id == title.id and it.last})


def _menu_number(project, mid):
    return project.menu(mid).number


def _title_ref(project, tid, from_titleset):
    """`title K` within the current titleset, else `titleset N title K`."""
    t = project.title(tid)
    if t.titleset == from_titleset:
        return f"title {t.number}"
    return f"titleset {t.titleset} title {t.number}"


def button_command(project, action, menu=None, override=None):
    """Command executed by a menu button (menu domain of titleset 1). With
    `menu`, the button first records itself as that menu's last button;
    `override` replaces the end action of the title it plays."""
    reg = button_reg(menu) if menu is not None else None
    if override:
        kind, target, num = parse_action(action)
        chap = f" chapter {num}" if kind == "chapter" else ""
        k, o = project.overrides.index(override) + 1, override_reg(project)
        single = _single(project).replace(f"{o} = 0; ", "")
        cmd = f"{single}{o} = {k}; jump {_title_ref(project, target, 1)}{chap};"
    else:
        cmd = _menu_domain_command(project, action)
    leaves = parse_action(action)[0] not in ("audio", "subtitle")
    return f"{reg} = button; {cmd}" if reg and leaves else cmd


def _menu_domain_command(project, action):
    kind, target, num = parse_action(action)
    single = _single(project)
    if kind == "menu":
        return f"{_entry(project, target, num)}jump menu {_menu_number(project, target)};"
    if kind == "playlist":
        return playlist_start(project, target, "menu")
    if kind == "playall":
        reset = f"{STATE_REG} = 0; {ITEM_END_REG} = 0; " if project.uses_playlists else ""
        reset += _no_override(project)
        return f"{reset}{PLAYALL_REG} = 1; jump {_title_ref(project, project.titles[0].id, 1)};"
    if kind == "resume":
        first = f"{single}jump {_title_ref(project, project.titles[0].id, 1)};"
        return f"if ({resume_reg(project)} == 1) {{ resume; }} {first}"
    if kind == "title":
        return f"{single}jump {_title_ref(project, target, 1)};"
    if kind == "chapter":
        return f"{single}jump {_title_ref(project, target, 1)} chapter {num};"
    if kind == "audio":
        return f"audio = {num - 1};"
    if kind == "subtitle":
        return _subtitle_set(num)
    return "exit;"


def _subtitle_set(num):
    # SPRM2: stream number in bits 0-5, bit 6 = display on
    return "subtitle = 0;" if num == 0 else f"subtitle = {64 + num - 1};"


def stream_prefix(button):
    """Audio / subtitle switches a button makes along with its action."""
    return _streams(button.audio, button.subtitle)


def _streams(audio, subtitle):
    out = f"audio = {audio - 1}; " if audio else ""
    return out + (_subtitle_set(subtitle) + " " if subtitle is not None else "")


def transition_pgcs(project):
    """{transition key: menu PGC number} of the link transitions, after the
    menus' own PGCs (see project.transition_key)."""
    if not project.menus:
        return {}
    first = max(m.loop_pgc for m in project.menus) + 1
    return {key: first + k for k, key in enumerate(project.link_transitions)}


def menu_button_command(project, menu, button):
    """What a button of `menu` does: its streams and action, or, with a link
    transition, a jump to the transition (which then does them)."""
    if button.transition:
        reg = button_reg(menu)
        go = f"jump menu {transition_pgcs(project)[transition_key(button)]};"
        return f"{reg} = button; {go}" if reg else go
    return f"{stream_prefix(button)}{button_command(project, button.action, menu, button.override)}"


def transition_post(project, key):
    """<post> of a link transition: what the button does after it."""
    _, action, override, audio, subtitle = key
    return f"{_streams(audio, subtitle)}{button_command(project, action, None, override)}"


def default_subtitle(project):
    """0-based subtitle stream to show from the start, or None."""
    for t in project.titles:
        for j, sub in enumerate(t.subtitles):
            if sub.default:
                return j
    return None


def end_command(project, action, title=None):
    """<post> of `title` (default: one in titleset 1)."""
    lists = playlist_dispatch(project, title) if title is not None else ""
    rest = _post_rest(project, action, title)
    rest = f"{lists} {rest}" if lists else rest
    if title is not None and project.overrides:
        o = override_reg(project)
        rest = " ".join(f"if ({o} == {k}) {{ {o} = 0; {_end_command(project, act, title.titleset)} }}"
                        for k, act in enumerate(project.overrides, 1)) + " " + rest
    if title is not None and project.uses_resume:
        rest = f"{resume_reg(project)} = 0; {rest}"   # ended: nothing to resume
    return rest


def _post_rest(project, action, title):
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
    kind, target, num = parse_action(action)
    if kind == "menu":
        reg = f"{_entry(project, target, num)}{NAV_REG} = {_menu_number(project, target)};"
        if ts == 1:
            return f"{reg} call menu entry root;"
        return f"{reg} call vmgm menu entry title;"
    if kind == "title":
        return f"jump {_title_ref(project, target, ts)};"
    if kind == "chapter":
        t = project.title(target)
        if num == 1:
            return f"jump {_title_ref(project, target, ts)};"
        if t.titleset == ts:
            return f"jump title {t.number} chapter {num};"
        # (a title cannot jump to a chapter of another titleset: the VMGM can)
        k = end_chapters(project).index((target, num))
        return f"{NAV_REG} = {CHAPTER_ROUTE + k}; call vmgm menu entry title;"
    if kind == "playlist":
        state, _, _, item = next(x for x in playlist_states(project) if x[1].id == target)
        flag = (f"{PLAYALL_REG} = 0; " if project.uses_playall else "") + _no_override(project)
        go = flag + _item_start(project, state, item)
        if project.title(item.title_id).titleset == ts:
            return go + _item_jump(project, item, "title", ts)
        return go + f"{NAV_REG} = {PLAYLIST_ROUTE}; call vmgm menu entry title;"
    if kind == "playall":
        return f"{PLAYALL_REG} = 1; jump {_title_ref(project, project.titles[0].id, ts)};"
    if kind == "lastmenu":
        reg = f"{NAV_REG} = {last_menu_reg(project)};"
        if ts == 1:
            return f"{reg} call menu entry root;"
        # (through the VMGM, where g1 == 0 means the Title key: before any
        # menu was shown, the Menu-key target or the first menu, as the
        # Menu key from this titleset)
        none = (f"if ({NAV_REG} == 0) {{ {NAV_REG} = {MENUKEY_REG}; }} "
                if project.uses_remote_menu else "")
        return (f"{reg} {none}if ({NAV_REG} == 0) {{ {NAV_REG} = 1; }} "
                "call vmgm menu entry title;")
    return "exit;"


def end_chapters(project):
    """(title id, chapter) that title / playlist end actions and overrides
    go to, in a fixed order (their VMGM routes)."""
    ends = [t.end_action for t in project.titles] + [p.end_action for p in project.playlists] + \
        project.overrides
    out = []
    for a in ends:
        kind, tid, n = parse_action(a)
        if kind == "chapter" and n > 1 and (tid, n) not in out:
            out.append((tid, n))
    return out


def first_play_command(project):
    kind, target, num = parse_action(project.disc.first_play)
    sub = default_subtitle(project)
    pre = f"subtitle = {64 + sub}; " if sub is not None else ""
    if kind == "menu":
        n = _menu_number(project, target)
        return f"{pre}{_entry(project, target, num)}{NAV_REG} = {n}; jump titleset 1 menu entry root;"
    if kind == "playlist":
        return pre + playlist_start(project, target, "vmgm")
    if kind == "playall":
        pre += f"{PLAYALL_REG} = 1; "
        target = project.titles[0].id
    t = project.title(target)
    if t.titleset == 1:
        return f"{pre}jump title {t.number};"
    return f"{pre}jump titleset {t.titleset} title {t.number};"


def title_pre(project, title):
    """<pre> of a title: remember which menu the Menu key should open, and
    that there is something to resume."""
    cmds = []
    if project.uses_remote_menu:
        n = _menu_number(project, title.remote_menu) if title.remote_menu else 1
        cmds.append(f"{MENUKEY_REG} = {n};")
    if project.uses_resume:
        cmds.append(f"{resume_reg(project)} = 1;")
    return " ".join(cmds) or None


def vmgm_title_command(project):
    """The VMGM title menu: Title key, and the route from other titlesets."""
    cmds = []
    if project.uses_playlists:
        # a playlist continuing in another titleset
        go = " ".join(f"if ({STATE_REG} == {state}) {{ {_item_jump(project, it, 'vmgm')} }}"
                      for state, _, _, it in playlist_states(project))
        cmds.append(f"if ({NAV_REG} == {PLAYLIST_ROUTE}) {{ {NAV_REG} = 0; {go} }}")
    for k, (tid, n) in enumerate(end_chapters(project) if project.titleset_count > 1 else []):
        t = project.title(tid)
        cmds.append(f"if ({NAV_REG} == {CHAPTER_ROUTE + k}) {{ {NAV_REG} = 0; "
                    f"jump titleset {t.titleset} title {t.number} chapter {n}; }}")
    if project.uses_remote_menu:
        cmds.append(f"{MENUKEY_REG} = 0;")
    tk = project.disc.title_key
    if tk and parse_action(tk)[0] == "playlist":
        cmds.append(f"if ({NAV_REG} == 0) {{ {playlist_start(project, parse_action(tk)[1], 'vmgm')} }}")
    elif tk:
        kind, target, num = parse_action(tk)
        if kind == "menu" and (_menu_number(project, target) != 1 or num):
            cmds.append(f"if ({NAV_REG} == 0) {{ {_entry(project, target, num)}"
                        f"{NAV_REG} = {_menu_number(project, target)}; }}")
        elif kind in ("title", "playall"):
            t = project.titles[0] if kind == "playall" else project.title(target)
            flag = (f"{PLAYALL_REG} = {1 if kind == 'playall' else 0}; "
                    if project.uses_playall else "")
            if project.uses_playlists:
                flag = f"{STATE_REG} = 0; {ITEM_END_REG} = 0; " + flag
            flag += _no_override(project)
            cmds.append(f"if ({NAV_REG} == 0) {{ {flag}jump title {t.global_number}; }}")
    cmds.append("jump titleset 1 menu entry root;")
    return " ".join(cmds)


def menu_pre(project, menu):
    cmds = _menu_pre(project, menu)
    if project.uses_last_menu and first_button_on_entry(project, menu) and menu.buttons:
        # the last-menu bookkeeping alone: keep what dvdauthor does for a menu
        # without pre commands (it highlights button 1)
        cmds.append("button = 1024;")
    return " ".join(cmds)


def first_button_on_entry(project, menu):
    """Whether entering `menu` always highlights button 1: dvdauthor sets it
    in a menu without pre commands of its own."""
    if menu.buttons_at_loop:
        return not _button_pre(project, menu)       # the buttons' own PGC
    own = [c for c in _menu_pre(project, menu)
           if not c.startswith(f"{last_menu_reg(project)} = ")]
    return not own


def _menu_pre(project, menu):
    cmds = []
    if menu.number == 1:
        if project.uses_remote_menu:
            # Menu key from a title: g1 is 0, the title left its target in g3
            cmds.append(f"if ({NAV_REG} == 0) {{ {NAV_REG} = {MENUKEY_REG}; }} {MENUKEY_REG} = 0;")
        cmds += [f"if ({NAV_REG} == {o.number}) {{ {NAV_REG} = 0; jump menu {o.number}; }}"
                 for o in project.menus if o.number != 1]
        cmds.append(f"{NAV_REG} = 0;")
    if project.uses_last_menu:
        cmds.append(f"{last_menu_reg(project)} = {menu.number};")
    if menu.loop is not None:
        cmds.append(f"{LOOP_REG} = 0;")
    # (with the buttons in a PGC of their own, that one takes the link's button)
    return cmds + _button_pre(project, menu, clear=not menu.buttons_at_loop)


def _button_pre(project, menu, clear=True):
    """The commands choosing the button highlighted as the menu starts: the
    default or remembered one, or the one a link asks for (then cleared)."""
    ids = [b.id for b in menu.buttons]
    default = (ids.index(menu.default_button) + 1) if menu.default_button else 1
    reg = button_reg(menu)
    if reg:
        cmds = [f"if ({reg} != 0) {{ button = {reg}; }} else {{ button = {default * 1024}; }}"]
    elif menu.default_button:
        cmds = [f"button = {default * 1024};"]
    else:
        cmds = []
    if menu.id in project.entry_buttons:
        e = entry_reg(project)
        # (a pre without a button of its own would keep whatever SPRM 8 held)
        cmds = (cmds or [f"button = {default * 1024};"]) + [f"if ({e} != 0) {{ button = {e}; }}"]
        if clear:
            cmds.append(f"{e} = 0;")
    return cmds


def menu_post(project, menu):
    cell = 2 if menu.loop_point and not menu.buttons_at_loop else 1
    if menu.loop is None:
        return f"jump cell {cell};"
    return (f"{LOOP_REG} += 1; if ({LOOP_REG} lt {menu.loop}) {{ jump cell {cell}; }} "
            + _menu_domain_command(project, menu.end_action))


def menu_vob(menu, path):
    if not menu.loop_point or menu.buttons_at_loop:
        return f"<vob file={quoteattr(path)}/>"
    lp = format_time(menu.loop_point)
    return (f'<vob file={quoteattr(path)}><cell start="0" end="{lp}" chapter="1"/>'
            f'<cell start="{lp}"/></vob>')


def title_vob(project, title, path):
    """The title's <vob>: chapter marks, or explicit chapter cells when a
    playlist item stops at the end of one of them."""
    ends = item_end_chapters(project, title)
    fps = title_fps(title, project.disc)
    points = chapter_points(title.chapters, fps)[1]
    # a slideshow advanced by hand: every chapter (picture) ends in a still
    held = bool(title.slideshow and title.slideshow.advance == "manual")
    if not ends and not held:
        return f'<vob file={quoteattr(path)} chapters="{chapters_attr(title.chapters, fps)}"/>'
    pause = ' pause="inf"' if held else ""
    cells = []
    for k, start in enumerate(points, 1):
        end = f' end="{format_time(points[k])}"' if k < len(points) else ""
        cmd = f"if ({ITEM_END_REG} == {k}) jump pgc tail;" if k in ends else ""
        cells.append(f'<cell start="{format_time(start)}"{end} chapter="1"{pause}>{cmd}</cell>')
    return f"<vob file={quoteattr(path)}>{''.join(cells)}</vob>"


def video_tag(disc, caption=False):
    ws = ' widescreen="nopanscan"' if disc.aspect == "16:9" else ""
    # (line-21 captions in the titles: the IFO says so, for players that look)
    cc = ' caption="field1"' if caption else ""
    return f'<video format="{disc.standard.lower()}" aspect="{disc.aspect}"{ws}{cc}/>'


def audio_tags(project, titles=None):
    """One <audio> per stream index used by the titles of a titleset."""
    titles = titles or project.titles
    codec = titles[0].audio_codec
    base = ('format="pcm" quant="16bps" samplerate="48khz" channels="2"' if codec == "lpcm"
            else f'format="{codec}" channels="{titles[0].audio_channels}"')
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


def build_xml(project, menu_files, title_files, dest, transition_files=None):
    """menu_files / title_files: {id: path to the .mpg}; transition_files:
    {transition video: path to its .mpg}."""
    disc = project.disc
    multi = project.titleset_count > 1
    jumppad = ' jumppad="yes"' if multi else ""
    x = [f'<dvdauthor dest={quoteattr(dest)}{jumppad}>', "  <vmgm>",
         f"    <fpc>{first_play_command(project)}</fpc>"]
    if project.menus:
        # With one titleset the top-menu button resets g1 (always the root
        # menu). With several, titles of other titlesets come back through
        # here with their target menu in g1, so it must survive.
        x += ["    <menus>", f"      {video_tag(disc)}",
              f'      <pgc entry="title"><pre>{vmgm_title_command(project)}</pre></pgc>',
              "    </menus>"]
    x += ["  </vmgm>", "  <titleset>"]
    if project.menus:
        x += ["    <menus>", f"      {video_tag(disc)}"]
        for m in project.menus:
            attrs = ' entry="root"' if m.number == 1 else ""
            x.append(f"      <pgc{attrs}>")
            pre = menu_pre(project, m)
            if pre:
                x.append(f"        <pre>{pre}</pre>")
            if m.buttons_at_loop:
                # the intro, without buttons, then the program chain that has them
                intro, loop = menu_files[m.id]
                x.append(f"        <vob file={quoteattr(intro)}/>")
                x.append(f"        <post>jump menu {m.loop_pgc};</post>")
                x.append("      </pgc>")
                x.append("      <pgc>")
                again = _button_pre(project, m)
                if again:
                    # (a menu PGC without <pre> would get button 1 from dvdauthor)
                    x.append(f"        <pre>{' '.join(again)}</pre>")
            for b in m.buttons:
                x.append(f"        <button name={quoteattr(b.id)}>"
                         f"{menu_button_command(project, m, b)}</button>")
            x.append(f"        {menu_vob(m, loop if m.buttons_at_loop else menu_files[m.id])}")
            x.append(f"        <post>{menu_post(project, m)}</post>")
            x.append("      </pgc>")
        for key in transition_pgcs(project):
            x += ["      <pgc>", f"        <vob file={quoteattr(transition_files[key[0]])}/>",
                  f"        <post>{transition_post(project, key)}</post>", "      </pgc>"]
        x.append("    </menus>")
    for ts in range(1, project.titleset_count + 1):
        if ts > 1:
            x.append("  <titleset>")
        titles = project.titleset_titles(ts)
        if ts > 1 and project.menus:
            # the remote's Menu key: back to titleset 1 through the VMGM
            target = f"{NAV_REG} = {MENUKEY_REG}; if ({NAV_REG} == 0) {{ {NAV_REG} = 1; }}" \
                if project.uses_remote_menu else f"{NAV_REG} = 1;"
            x += ["    <menus>", f"      {video_tag(project.disc_for(titles[0]))}",
                  f'      <pgc entry="root"><pre>{target} jump vmgm menu entry title;</pre></pgc>',
                  "    </menus>"]
        x += ["    <titles>", f"      {video_tag(project.disc_for(titles[0]), any(t.captions for t in titles))}"]
        x += [f"      {tag}" for tag in audio_tags(project, titles)
              + subpicture_tags(project, titles)]
        for t in titles:
            x.append("      <pgc>")
            pre = title_pre(project, t)
            if pre:
                x.append(f"        <pre>{pre}</pre>")
            x.append(f"        {title_vob(project, t, title_files[t.id])}")
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
