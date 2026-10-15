"""The build pipeline: probe -> plan -> menus -> titles -> VIDEO_TS (vtskit) -> (ISO)."""

import concurrent.futures
import dataclasses
import functools
import hashlib
import json
import os
import shutil
import tempfile
import threading

from . import (author, bdmenu, bluray, captions, clips, discimage, encode, iso, layerbreak,
               lpcmfix, settings, slideshow, subtitles, titlebuttons, tools, videots)
from . import menu as menu_module
from ._vendor.bdmvkit import pgs
from ._vendor.vtskit import VtsError
from ._vendor.vtskit import __version__ as vtskit_version
from ._vendor.vtskit import ps as vtskit_ps
from .errors import OncemoreError, ProjectError
from .project import button_times, parse_action, retime_thumbs, title_fps
from .menu import (MenuBuilder, check_element_fonts, display_width, find_font, link_font,
                   menu_seconds, menu_text)

# DTS without extensions (the source's bitrate is the core's); a DVD takes
# DTS up to 1536 kbit/s (1509.75k "full rate" is the usual)
DTS_PLAIN = ("DTS", "DTS-ES", "DTS 96/24")
# DTS-HD as ffprobe names it, and what a Blu-ray declares it as
DTS_HD = {"DTS-HD MA": "dtshd_ma", "DTS-HD MA + DTS:X": "dtshd_ma",
          "DTS-HD MA + DTS:X IMAX": "dtshd_ma", "DTS-HD HRA": "dtshd"}
DVD_DTS_MAX = 1_536_000
DVD_CHAPTERS = 99          # chapters (parts of title) a DVD title can have


def script_issues(project, bd=False):
    """The navigation scripts compiled where they run (vtskit.lang), so a
    script it cannot take is reported before anything is encoded. A
    Blu-ray has none."""
    used = [a for a in project.actions(scripts=False) if a.startswith("commands:")]
    if not used:
        return []
    if bd:
        return [{"path": "scripts", "message": "navigation scripts (commands:...) are for DVD; "
                                               "a Blu-ray and the web version have none yet"}]
    disc = videots.disc_of(project)
    out = []

    def compile_(where, text, domain, vts):
        try:
            disc.compile(text, domain, vts)
        except (VtsError, ValueError) as e:
            out.append({"path": where, "message": f"the script does not compile: {e}"})

    for m in project.menus:
        for j, b in enumerate(m.buttons):
            if b.action.startswith("commands:"):
                compile_(f"menu {m.id!r}.buttons[{j}]", author.menu_button_command(project, m, b),
                         "vtsm", 1)
        if m.loop is not None and m.end_action.startswith("commands:"):
            compile_(f"menu {m.id!r}.end_action", author.menu_post(project, m), "vtsm", 1)
    for i, t in enumerate(project.titles):
        ends = [t.end_action] + [pl.end_action for pl in project.playlists
                                 if any(it.title_id == t.id for it in pl.items)]
        if any(a.startswith("commands:") for a in ends):
            compile_(f"titles[{i}].end_action", author.end_command(project, t.end_action, t),
                     "vts", t.titleset)
        for j, b in enumerate(t.buttons):
            if b.action.startswith("commands:"):
                compile_(f"titles[{i}].buttons[{j}]", author.title_button_command(project, t, b.action),
                         "vts", t.titleset)
    return out


def inspect(project, reporter=None, prepare=True, bd=False):
    """Probe every source and plan the bitrate. Used by validate and build.
    With prepare=False slideshows that are not rendered yet are planned from
    their settings instead of being rendered (for a quick status). bd: plan
    for a Blu-ray instead of a DVD."""
    tools.require(["ffprobe"])
    issues = []
    infos = {}
    probes = {}
    cues = {}
    warnings = []

    def probe(path):
        if path not in probes:
            probes[path] = encode.probe(path)
        return probes[path]

    issues += script_issues(project, bd)
    if not bd:
        for i, pl in enumerate(project.playlists):
            if pl.order != "sequential":
                warnings.append(f"playlists[{i}].order: a DVD plays the items as listed "
                                f"({pl.order} is for Blu-ray and the web version)")
    for i, t in enumerate(project.titles):
        where = f"titles[{i}]"
        if t.slideshow:
            # (fitted to its music: the durations, source and chapters follow it)
            slideshow.apply(t, project.disc_for(t), probe)
            retime_thumbs(project, t)
            if slideshow.overrun(t.slideshow):
                show = t.slideshow
                warnings.append(f"{where}.slideshow: {len(show.slides)} pictures need at least "
                                f"{show.duration:.1f}s; the music ({show.music_length:.1f}s) "
                                "ends before them")
        n = len(t.chapters)
        if not bd and n > DVD_CHAPTERS:
            # a DVD title has at most 99 chapters (a Blu-ray 999)
            if t.slideshow and t.slideshow.advance == "manual":
                issues.append({"path": f"{where}.slideshow",
                               "message": f"a slideshow advanced by hand has at most "
                                          f"{DVD_CHAPTERS} pictures on a DVD (this one has {n}; "
                                          "a Blu-ray takes 999)"})
            else:
                warnings.append(f"{where}: a DVD title has at most {DVD_CHAPTERS} chapters; "
                                f"chapters {DVD_CHAPTERS + 1}-{n} are part of chapter "
                                f"{DVD_CHAPTERS}")
                t.chapters = t.chapters[:DVD_CHAPTERS]
                t.chapter_names = t.chapter_names[:DVD_CHAPTERS]
                t.chapter_posters = t.chapter_posters[:DVD_CHAPTERS]
        if t.slideshow and not prepare and not os.path.isfile(t.source):
            w, h = slideshow.canvas(project.disc_for(t))
            num, den = project.disc.fps
            infos[t.id] = {"duration": t.slideshow.duration, "has_video": True, "width": w,
                           "height": h, "sar": 1, "fps": num / den, "unrendered": True,
                           "audio_streams": 1 if t.slideshow.audio else 0}
            continue
        if t.slideshow:
            slideshow.ensure(t, project.disc_for(t),
                             os.path.join(os.path.dirname(t.source), f"{t.id}.log"), reporter)
        if t.clips:
            info = _clip_info(project, t, probe, issues, where)
        else:
            info = probe(t.source)
            if not info.get("has_video") and info.get("has_audio"):
                # music: the sound, with a still picture (or black) to look at
                info = encode.sound_only(info, t, project.disc_for(t))
            elif t.picture:
                warnings.append(f"{where}.picture: the source has a picture of its own; "
                                "the still is not used")
            if info.get("has_video") and info.get("fps"):
                t.video_mode = encode.video_mode(t, info, project.disc)
        infos[t.id] = info
        t.dts_hd, t.audio_peak_bps = [None] * len(t.audio_tracks), 0
        peaks = [None] * len(t.audio_tracks)
        for j, tr in enumerate(t.audio_tracks):
            have = probe(tr.source).get("audio_streams", 0)
            if tr.stream >= have and not (tr.source == t.source and tr.stream == 0):
                issues.append({"path": f"{where}.audio_tracks[{j}]",
                               "message": f"{os.path.basename(tr.source)} has {have} audio "
                                          f"stream(s); stream {tr.stream} does not exist"})
            elif t.audio_passthrough:
                a = (probe(tr.source).get("audio") or [{}] * (tr.stream + 1))[tr.stream]
                name = "DTS" if t.audio_codec == "dts" else "AC-3"
                # a Blu-ray keeps DTS-HD whole (at 48, 96 or 192 kHz, over its
                # 48 kHz core); elsewhere a DTS source gives its core
                hd = bd and t.audio_codec == "dts" and DTS_HD.get(a.get("profile"))
                multi = t.audio_codec == "dts"        # (DTS: 6 is "5.1 or more")
                if t.audio_codec == "dts" and a.get("profile") == "DTS Express":
                    issues.append({"path": f"{where}.audio_tracks[{j}]",
                                   "message": f"{os.path.basename(tr.source)} audio stream "
                                              f"{tr.stream} is DTS Express, which has no DTS "
                                              "core to copy (choose AC-3 or LPCM to encode it)"})
                elif a.get("codec") != t.audio_codec or \
                        a.get("rate") not in ((48000, 96000, 192000) if hd else (48000,)):
                    issues.append({"path": f"{where}.audio_tracks[{j}]",
                                   "message": f"{os.path.basename(tr.source)} audio stream "
                                              f"{tr.stream} is {a.get('codec')} "
                                              f"{a.get('rate')} Hz; only 48 kHz {name} can be "
                                              "copied" + (" (DTS-HD at 96 or 192 kHz too, on a "
                                                          "Blu-ray; choose AC-3 or LPCM to "
                                                          "encode it)"
                                                          if t.audio_codec == "dts" else
                                                          " (turn off audio.passthrough)")})
                elif (a.get("channels") != t.audio_channels) if not multi else \
                        ((a.get("channels") or 0) > 2) != (t.audio_channels > 2):
                    want = a.get("channels") if not multi else \
                        (6 if (a.get("channels") or 0) > 2 else 2)
                    issues.append({"path": f"{where}.audio.channels",
                                   "message": f"the {name} source has {a.get('channels')} "
                                              f"channel(s); set audio.channels to "
                                              f"{want} to copy it"})
                elif hd:
                    rates = encode.audio_rates(tr.source, tr.stream)
                    if not rates:
                        issues.append({"path": f"{where}.audio_tracks[{j}]",
                                       "message": f"{os.path.basename(tr.source)}: the DTS-HD "
                                                  "stream's packets cannot be read"})
                        continue
                    t.dts_hd[j] = (hd, a["rate"])
                    t.audio_bitrate = max(t.audio_bitrate, rates[0])
                    peaks[j] = rates[1]
                elif t.audio_codec == "dts":
                    # (the DTS core is what goes on the disc: DTS-HD extensions
                    # are dropped, encode.DTS_CORE)
                    if a.get("bit_rate") and (a.get("profile") or "DTS") in DTS_PLAIN:
                        t.audio_bitrate = a["bit_rate"]
                    if not bd and t.audio_bitrate > DVD_DTS_MAX:
                        issues.append({"path": f"{where}.audio_tracks[{j}]",
                                       "message": f"{os.path.basename(tr.source)}: DTS at "
                                                  f"{t.audio_bitrate // 1000}k; a DVD takes "
                                                  "DTS up to 1536k"})
                elif a.get("bit_rate"):
                    t.audio_bitrate = max(t.audio_bitrate, a["bit_rate"])
            elif t.audio_channels == 6 and tr.stream == 0 \
                    and 0 < probe(tr.source).get("audio_channels", 0) < 6:
                warnings.append(f"{where}.audio_tracks[{j}]: {os.path.basename(tr.source)} has "
                                f"{probe(tr.source)['audio_channels']} channel(s); the 5.1 "
                                "track will only use the front speakers")
        if any(t.dts_hd):
            # (with DTS-HD the picture leaves room for the sound's peaks:
            # bluray.title_max_bps)
            t.audio_peak_bps = sum(p or t.audio_bitrate for p in peaks)
        if t.captions and bd:
            warnings.append(f"{where}.captions: closed captions are for DVD and are left out here")
        elif t.captions:
            film = t.video_mode == "pulldown" or (not t.transcode and info.get("has_video")
                                                  and encode.is_film(info, project.disc_for(t)))
            if film:
                issues.append({"path": f"{where}.captions",
                               "message": "closed captions need 29.97 fps video; this title is "
                                          "film with 3:2 pulldown (set scan to interlaced)"})
            else:
                try:
                    for note in captions.load(t.captions, t.captions_offset)[1]:
                        warnings.append(f"{where}.captions: {note}")
                except ProjectError as e:
                    issues.append({"path": f"{where}.captions", "message": e.message})
        if t.audio_codec == "dts" and not bd:
            warnings.append(f"{where}.audio.codec: DTS only: a DVD player without a DTS decoder "
                            "plays no sound unless it passes DTS on to an amplifier (DVDs "
                            "normally carry an AC-3 or LPCM track too)")
        for j, path in enumerate(t.angles):
            a = probe(path)
            if bd:
                warnings.append(f"{where}.angles: angles are for DVD and are left out here")
                break
            if not a.get("has_video") or not a.get("duration"):
                issues.append({"path": f"{where}.angles[{j}]", "message": "no video stream"})
            elif info.get("duration") and a["duration"] < info["duration"] - 0.05:
                issues.append({"path": f"{where}.angles[{j}]",
                               "message": f"{os.path.basename(path)} is {a['duration']:.2f}s, shorter "
                                          f"than the title ({info['duration']:.2f}s); every angle "
                                          "plays as long as the source"})
        for j, sub in enumerate(t.subtitles):
            cues[(t.id, j)] = subtitles.shifted(
                subtitles.load_subtitles(sub.file, project.disc.standard), sub.offset)
            if not cues[(t.id, j)]:
                warnings.append(f"{where}.subtitles[{j}]: {os.path.basename(sub.file)} has no cues")
        if t.subtitles and not bd:
            need = subtitles.palette_size([(sub.color, cues[(t.id, j)])
                                           for j, sub in enumerate(t.subtitles)],
                                          project.disc.subtitle_style)
            if need > 16:
                issues.append({"path": f"{where}.subtitles",
                               "message": f"the subtitles use too many text colours ({need} "
                                          "subpicture colours; a DVD title has 16): use fewer"})
        if not info.get("has_video"):
            issues.append({"path": f"{where}.source", "message": "no video stream"})
            continue
        if not info.get("duration"):
            issues.append({"path": f"{where}.source", "message": "cannot determine duration"})
            continue
        if not t.transcode and bd:
            # a Blu-ray H.264 picture is copied; any other is encoded anyway
            # (the setting is about the DVD's MPEG-2 as much)
            src = dict(info, gop=encode.longest_gop(t.source))
            if src.get("codec") == "h264":
                src["fields"] = bluray.coded_for_fields(t.source)
            why = bluray.copy_compliance(src, title_fps(t, project.disc), project.disc)
            t.bd_copy = not why
            room = bluray.title_max_bps(t, bluray.MAX_VIDEO_BPS)
            if t.bd_copy and t.audio_peak_bps and encode.source_video_bps(info) > room:
                warnings.append(f"{where}.audio: the copied picture "
                                f"({encode.source_video_bps(info) / 1e6:.1f} Mbit/s) and the "
                                f"DTS-HD sound (up to {t.audio_peak_bps / 1e6:.1f}) may be more "
                                "than a player reads; set transcode to encode the picture "
                                f"at up to {room / 1e6:.1f} Mbit/s")
            if why:
                warnings.append(f"{where}.transcode: the picture is encoded for the Blu-ray "
                                f"anyway: {'; '.join(why)}")
        elif not t.transcode:
            def track_bps(tr):
                if t.audio_passthrough:                 # (copied: its own rate)
                    streams = probe(tr.source).get("audio") or [{}]
                    return streams[min(tr.stream, len(streams) - 1)].get("bit_rate") or 448_000
                return 1_536_000 if t.audio_codec == "lpcm" else t.audio_bitrate
            audio_bps = sum(track_bps(tr) for tr in t.audio_tracks)
            info = dict(info, gop=encode.longest_gop(t.source))
            for why in encode.dvd_compliance(info, project.disc_for(t), audio_bps):
                issues.append({"path": f"{where}.transcode",
                               "message": f"cannot use the picture as it is: {why}"})
        for j in range(len(t.subtitles)):
            late = [c for c in cues[(t.id, j)] if c.start >= info["duration"]]
            if late:
                warnings.append(f"{where}.subtitles[{j}]: {len(late)} cue(s) start after the "
                                "end of the video and will not show")
        for j, c in enumerate(t.chapters):
            if c >= info["duration"]:
                issues.append({"path": f"{where}.chapters[{j}]",
                               "message": f"chapter at {c:.3f}s is beyond the end "
                                          f"({info['duration']:.3f}s)"})
        for j, b in enumerate(t.buttons):
            if bd:
                issues.append({"path": f"{where}.buttons", "message": "buttons over a title are for "
                               "DVD; a Blu-ray title has none yet"})
                break
            if b.start >= info["duration"]:
                issues.append({"path": f"{where}.buttons[{j}].start",
                               "message": f"the button starts at {b.start:.3f}s, after the end "
                                          f"({info['duration']:.3f}s)"})
            elif b.end is not None and b.end > info["duration"]:
                warnings.append(f"{where}.buttons[{j}]: ends at {b.end:.3f}s, after the title "
                                f"({info['duration']:.3f}s); shown to its end")
    for i, m in enumerate(project.menus):
        for what, path in (("background", m.background), ("audio", m.audio),
                           ("background_video", m.background_video)):
            if not path:
                continue
            info = probe(path)
            if what == "audio" and not info.get("has_audio"):
                issues.append({"path": f"menu {m.id!r}.audio", "message": "no audio stream"})
            if what == "background_video" and not (info.get("has_video") and info.get("duration")):
                issues.append({"path": f"menu {m.id!r}.background_video",
                               "message": "not a video with a known duration"})
    for path in sorted({key[0] for key in project.link_transitions}):
        info = probe(path)
        if not (info.get("has_video") and info.get("duration")):
            issues.append({"path": f"transition {os.path.basename(path)!r}",
                           "message": "a link transition must be a video with a known duration"})
    for m in project.menus:
        if m.loop_point and m.loop_point >= menu_seconds(m, probe) - 0.5:
            what = "fade_in" if m.fade_in == m.loop_point else "loop_point"
            name = "the fade-in ending at" if what == "fade_in" else "loop point"
            issues.append({"path": f"menu {m.id!r}.{what}",
                           "message": f"{name} {m.loop_point:.2f}s must be at least 0.5 s "
                                      f"before the end of the menu ({menu_seconds(m, probe):.2f}s)"})
    if issues:
        raise ProjectError("media check failed", issues)
    menu_total = sum(menu_seconds(m, probe) for m in project.menus) + \
        sum(probe(key[0])["duration"] for key in project.link_transitions)   # (one copy each)
    font = None
    text = menu_text(project) + "".join("".join(line for c in cs for line in c.lines)
                                        for cs in cues.values())
    if project.menus or cues:
        font = find_font(project.disc.font, text)
    check_element_fonts(project, font)
    if prepare:
        overlapping = button_overlaps(project, font)
        if overlapping:
            raise ProjectError("menu check failed", overlapping)
    if bd:
        # (a picture used as it is keeps its own rate)
        plan = bluray.plan([(infos[t.id]["duration"], t.audio_bps) +
                            ((encode.source_video_bps(infos[t.id]),) if t.bd_copy else ())
                            for t in project.titles],
                           bluray.CAPACITY[project.disc.bluray_target])
        plan.update(video_bps=plan["max_bps"], per_title=[plan["max_bps"]] * len(project.titles))
    else:
        # (a picture used as it is keeps its own rate)
        plan = encode.plan_bitrate([(infos[t.id]["duration"], t.audio_bps,
                                     t.video_bitrate if t.transcode
                                     else encode.source_video_bps(infos[t.id]))
                                    for t in project.titles],
                                   project.disc.capacity, menu_total, project.disc.video_bitrate)
    plan["font"] = font
    plan["warnings"] = warnings + plan["warnings"]
    plan["_probes"] = probes
    plan["_cues"] = cues
    return infos, plan


def _clip_info(project, t, probe, issues, where):
    """The probe-like info of a title made of clips: the clips' lengths
    resolved from their files, the first clip's picture format, and the
    title's chapters (one per clip unless given)."""
    modes = set()
    for j, c in enumerate(t.clips):
        info = probe(c.source)
        cw = f"{where}.clips[{j}]"
        dur = info.get("duration") or 0.0
        if not info.get("has_video"):
            issues.append({"path": f"{cw}.source", "message": "no video stream"})
        elif c.still:
            continue                    # (a picture takes whatever scan its neighbours have)
        elif c.start >= dur > 0:
            issues.append({"path": f"{cw}.in", "message": f"starts after the end of the "
                                                          f"file ({dur:.3f}s)"})
        if info.get("has_video") and info.get("fps"):
            modes.add(encode.video_mode(t, info, project.disc))
    # clips of different kinds are all made progressive, so they can be joined
    t.video_mode = modes.pop() if len(modes) == 1 else "progressive"
    total = clips.apply(project, t, probe)
    # the title's picture format: its first video (pictures have none of their own)
    first = dict(probe(next((c for c in t.clips if not c.still), t.clips[0]).source))
    first.update(duration=total, path=None,
                 has_video=all(probe(c.source).get("has_video") for c in t.clips),
                 has_audio=any(probe(c.source).get("has_audio") for c in t.clips))
    return first


def button_overlaps(project, font=None):
    """Issues for menu buttons whose areas overlap: the remote could not
    tell them apart, and making the menu refuses them. Found here, with the
    menus laid out as the build lays them out, so Check reports them and a
    build stops before anything is encoded."""
    issues = []
    if not project.menus:
        return issues
    work = tempfile.mkdtemp(prefix="oncemore-check-")
    try:
        mb = MenuBuilder(project, work, font=font)
        for i, m in enumerate(project.menus):
            pairs = []
            mb.layout(m, pairs)
            for a, b in pairs:
                issues.append({"path": f"menus[{i}].buttons",
                               "message": f"menu {m.id!r}: buttons {a!r} and {b!r} overlap; "
                                          "move them apart"})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return issues


def summary(project, infos, plan):
    return {
        "disc": {"label": project.disc.label, "standard": project.disc.standard,
                 "aspect": project.disc.aspect, "target": project.disc.target,
                 "first_play": project.disc.first_play},
        "titles": [{"id": t.id, "number": t.number, "name": t.name, "source": t.source,
                    "duration": round(infos[t.id]["duration"], 3),
                    "input": f"{infos[t.id]['width']}x{infos[t.id]['height']}"
                             f"@{float(infos[t.id]['fps'] or 0):.3f}",
                    "chapters": t.chapters, "audio": t.audio_codec,
                    "audio_channels": t.audio_channels, "aspect": t.aspect,
                    "scan": t.video_mode,
                    "titleset": t.titleset, "global_number": t.global_number,
                    "video_bps": dict(zip([x.id for x in project.titles],
                                          plan.get("per_title", []))).get(t.id),
                    "audio_bps": t.audio_bps, "end_action": t.end_action,
                    "audio_tracks": [{"source": a.source, "stream": a.stream, "lang": a.lang}
                                     for a in t.audio_tracks],
                    "clips": [{"source": c.source, "in": c.start, "out": c.end,
                               "duration": round(c.duration or 0.0, 6)} for c in t.clips],
                    "subtitles": [{"file": u.file, "lang": u.lang, "default": u.default,
                                   "cues": len(plan.get("_cues", {}).get((t.id, j), []))}
                                  for j, u in enumerate(t.subtitles)]}
                   for t in project.titles],
        "menus": [{"id": m.id, "number": m.number, "generated": m.generated,
                   "buttons": [{"id": b.id, "label": b.label, "action": b.action}
                               for b in m.buttons]}
                  for m in project.menus],
        "font": plan.get("font"),
        "video_bps": plan["video_bps"],
        "estimated_bytes": plan["estimated_bytes"],
        "capacity_bytes": plan["capacity"],
        "total_seconds": round(plan["total_seconds"], 3),
        "warnings": list(project.warnings) + plan["warnings"],
        "budget": budget(project, infos, plan),
    }


def budget(project, infos, plan):
    """Where the disc's space goes, before anything is encoded: each title's
    length, video and audio rates and bytes, the menus, the disc's own
    files, and what is left."""
    b = plan.get("budget") or {"titles": [0] * len(project.titles), "menus": 0, "other": 0}
    rates = plan.get("per_title") or [plan["video_bps"]] * len(project.titles)
    titles = [{"id": t.id, "name": t.name, "seconds": round(infos[t.id]["duration"], 3),
               "video_bps": v, "audio_bps": t.audio_bps, "bytes": n}
              for t, v, n in zip(project.titles, rates, b["titles"])]
    used = sum(b["titles"]) + b["menus"] + b["other"]
    return {"titles": titles, "menus": b["menus"], "other": b["other"],
            "free": max(0, plan["capacity"] - used), "capacity": plan["capacity"]}


def add_subtitles(project, title, mpg, plan, work, reporter, cues_id=None):
    """Render the title's SRT tracks and mux them in as subpicture streams:
    (the muxed .mpg, the title's subpicture palette). `cues_id`: the title
    whose cues these are (an angle's stream takes its title's)."""
    cues_id = cues_id or title.id
    subdir = os.path.join(work, "subs", title.id)
    os.makedirs(subdir, exist_ok=True)
    renderer = subtitles.SubtitleRenderer(project.disc, subdir, link_font(plan["font"], subdir),
                                          display_width(project.disc),
                                          project.disc.subtitle_style)
    xmls = []
    for j, sub in enumerate(title.subtitles):
        cues = plan["_cues"][(cues_id, j)]
        reporter.step("subtitles", f"Rendering {len(cues)} subtitle(s) for '{title.id}' "
                      f"(stream {j + 1}{', ' + sub.lang if sub.lang else ''})", item=title.id)
        xmls.append(renderer.stream_xml(cues, sub.lang or "xx", j, sub.position, sub.color))
    # (a title's subpictures share 16 colours, transparent included: text
    # colours are counted before the build, pictures' own only once drawn)
    if len(renderer.colours) > 15:
        raise ProjectError("media check failed", [{
            "path": f"titles[{project.titles.index(title)}].subtitles",
            "message": f"the subtitles use {len(renderer.colours) + 1} subpicture colours (a DVD "
                       "title has 16): use fewer colours in the subtitle pictures"}])
    return subtitles.mux_streams(mpg, xmls, subdir, project.disc.standard)


# -- encode cache --------------------------------------------------------------
# Encoded titles and menus are kept in <project>/.oncemore-cache/encode, keyed
# by everything that changes their bytes (sources and their mtimes, settings,
# bitrate, ffmpeg version), so a rebuild only encodes what changed.
# (2: a menu's stream is kept without its button subpicture, which vtskit adds)
CACHE_VERSION = 2


@functools.lru_cache(maxsize=None)
def _code_signature():
    """The encoding code itself is part of every key: a new oncemore that
    encodes differently never reuses old results."""
    from . import pulldown, project as project_module
    h = hashlib.sha256()
    for mod in (encode, menu_module, lpcmfix, bluray, bdmenu, clips, pulldown, project_module):
        with open(mod.__file__, "rb") as f:
            h.update(f.read())
    return h.hexdigest()[:16]


_tool_version = functools.lru_cache(maxsize=None)(tools.version)


def _file_sig(path):
    try:
        st = os.stat(path)
        return [os.path.realpath(path), st.st_size, int(st.st_mtime)]
    except OSError:
        return [path, None, None]


def _cache_key(kind, payload):
    blob = json.dumps({"v": CACHE_VERSION, "code": _code_signature(), "kind": kind,
                       "ffmpeg": _tool_version("ffmpeg"), "vtskit": vtskit_version,
                       **payload}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def _cache_get(cache, key, dest):
    if not cache:
        return False
    src = os.path.join(cache, key + ".mpg")
    if not os.path.isfile(src):
        return False
    _link_or_copy(src, dest)
    return True


def _cache_put(cache, key, path):
    """Keep `path` as the cache entry `key`. Each writer fills a file of its
    own and renames it into place, so two builds storing the same entry at
    once (the app and the command line) never leave a cut-off one."""
    if cache:
        os.makedirs(cache, exist_ok=True)
        tmp = os.path.join(cache, f"{key}.{os.getpid()}-{threading.get_ident()}.part")
        try:
            _link_or_copy(path, tmp)
            os.replace(tmp, os.path.join(cache, key + ".mpg"))
        finally:
            if os.path.lexists(tmp):
                os.remove(tmp)


def _link_or_copy(src, dst):
    if os.path.lexists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def picture_count(mpg):
    """How many pictures an encoded title's program stream has."""
    with vtskit_ps.Mapped(mpg) as data:
        return len(vtskit_ps.scan(data).pictures)


def title_cache_key(project, title, info, vbps, fast):
    disc = project.disc_for(title)
    return _cache_key("title", {
        "source": _file_sig(title.source),
        "clips": [clips.clip_key(c, _file_sig(c.source)) for c in title.clips],
        "info": {k: info.get(k) for k in (
            "width", "height", "sar", "fps", "duration", "interlaced", "field_order", "frames")},
        "tracks": [(_file_sig(tr.source), tr.stream) for tr in title.audio_tracks],
        "disc": [disc.standard, disc.aspect, disc.width, disc.height],
        "chapters": title.chapters, "vbps": vbps, "fast": fast, "scan": title.video_mode,
        **({"button_times": button_times(title)} if title.buttons else {}),
        "ivtc": encode.is_ivtc(title),
        "audio": [title.audio_codec, title.audio_bitrate, title.audio_channels,
                  title.audio_passthrough],
        **({"dts_hd": title.dts_hd} if any(title.dts_hd) else {}),
        **({"captions": [_file_sig(title.captions), title.captions_offset]}
           if title.captions else {}),
        **({} if title.transcode else {"copy": True}),
        # (a sound-only title: the picture shown with it)
        **({"still": _file_sig(info["still"]) if info["still"] else "black"}
           if "still" in info else {})})


def encode_cache_dir(project):
    return os.path.join(settings.cache_dir(project.base_dir), "encode")


def encode_status(project, fast=False):
    """{title id: True when its encoded picture and sound are in the encode
    cache for the current plan}, without encoding or rendering anything."""
    infos, plan = inspect(project, prepare=False)
    cache = encode_cache_dir(project)
    out = {}
    for t, vbps in zip(project.titles, plan["per_title"]):
        if infos[t.id].get("unrendered"):
            out[t.id] = False
            continue
        key = title_cache_key(project, t, infos[t.id], vbps, fast)
        out[t.id] = os.path.isfile(os.path.join(cache, key + ".mpg"))
    return out


def transcode(project, reporter, title_ids=None, fast=False):
    """Encode titles ahead of the build ("transcode now"): the results go to
    the encode cache, where the build finds them. A title stays transcoded
    while its source, its settings and the disc's bitrate plan are the same."""
    tools.require(["ffmpeg", "ffprobe"])
    reporter.step("probe", "Checking sources")
    infos, plan = inspect(project, reporter)
    cache = encode_cache_dir(project)
    title_bps = dict(zip([t.id for t in project.titles], plan["per_title"]))
    wanted = [t for t in project.titles if title_ids is None or t.id in title_ids]
    unknown = set(title_ids or []) - {t.id for t in project.titles}
    if unknown:
        raise OncemoreError(f"no title {sorted(unknown)[0]!r}")
    done = {}
    work = tempfile.mkdtemp(prefix="oncemore-transcode-")
    try:
        os.makedirs(os.path.join(work, "logs"))
        for t in wanted:
            key = title_cache_key(project, t, infos[t.id], title_bps[t.id], fast)
            if os.path.isfile(os.path.join(cache, key + ".mpg")):
                reporter.step("encode", f"Title '{t.id}' already transcoded", item=t.id)
                done[t.id] = "cached"
                continue
            reporter.step("encode", f"Transcoding title '{t.id}' ({infos[t.id]['duration']:.1f}s, "
                          f"{title_bps[t.id] / 1e6:.2f} Mbit/s)", item=t.id)
            out = os.path.join(work, f"{t.id}.mpg")
            encode.encode_title(t, infos[t.id], project.disc_for(t), title_bps[t.id], out, work,
                                two_pass=not fast,
                                on_progress=lambda f, tid=t.id: reporter.progress("encode", f, tid),
                                probes=plan["_probes"])
            if t.audio_codec == "lpcm":
                lpcmfix.fix_file(out)
            _cache_put(cache, key, out)
            os.remove(out)
            done[t.id] = "transcoded"
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"titles": done, "cache": cache}


def menu_cache_key(project, menu, font):
    files = [menu.background, menu.background_video, menu.audio, font] + \
        [b.image for b in menu.buttons] + [b.highlight_image for b in menu.buttons] + \
        [p.file for p in menu.images] + \
        [el.font for el in list(menu.texts) + list(menu.buttons)] + \
        [project.title(b.thumb.title_id).source for b in menu.buttons if b.thumb] + \
        [b.thumb.mask_image for b in menu.buttons if b.thumb and b.thumb.mask_image]
    # a thumbnail shows the clip playing at its time, or a sound title's picture
    thumbs = [[[clips.clip_key(c, _file_sig(c.source)) for c in t.clips],
               _file_sig(t.picture) if t.picture else None]
              for t in (project.title(b.thumb.title_id) for b in menu.buttons if b.thumb)]
    return _cache_key("menu", {
        "thumbs": thumbs,
        "menu": dataclasses.asdict(menu), "files": [_file_sig(f) for f in files if f],
        "disc": [project.disc.standard, project.disc.aspect],
        "titles": {t.id: [t.aspect, t.titleset] for t in project.titles}})


def build(project, out_dir, reporter, fast=False, keep_work=False, work=None, cache=True):
    """Author VIDEO_TS into out_dir. Returns a result dict. With `cache`,
    encoded titles and menus are reused from <project>/.oncemore-cache."""
    tools.require(list(tools.REQUIRED),
                  need_drawtext=bool(project.menus) or any(t.subtitles for t in project.titles))
    out_dir = os.path.abspath(out_dir)
    work = work or os.path.join(out_dir, ".work")
    os.makedirs(work, exist_ok=True)
    logs = os.path.join(work, "logs")

    reporter.step("probe", "Checking sources")
    infos, plan = inspect(project, reporter)
    for w in project.warnings + plan["warnings"]:
        reporter.warn(w)
    vbps = plan["video_bps"]
    title_bps = dict(zip([t.id for t in project.titles], plan["per_title"]))
    # --no-cache encodes everything again and keeps that (a stale entry is replaced)
    store = encode_cache_dir(project)
    cache = store if cache else None
    reporter.info(f"    video {vbps / 1e6:.2f} Mbit/s average, estimated "
                  f"{plan['estimated_bytes'] / 2**30:.2f} of {plan['capacity'] / 2**30:.2f} GiB")

    menu_files = {}
    layouts = {}                  # menu id -> (its buttons' geometry, the canvas of their shapes)
    if project.menus:
        mb = MenuBuilder(project, work, reporter, font=plan["font"])
        reporter.info(f"    menu font: {mb.font() and mb.font_source}")
        for m in project.menus:
            key = menu_cache_key(project, m, plan["font"])
            out = os.path.join(mb.work, f"{m.id}.mpg")
            intro = os.path.join(mb.work, f"{m.id}.intro.mpg")
            if _cache_get(cache, key, out) and \
                    (not m.buttons_at_loop or _cache_get(cache, key + "-intro", intro)):
                reporter.step("menu", f"Menu '{m.id}' unchanged (cached)", item=m.id)
                menu_files[m.id] = (intro, out) if m.buttons_at_loop else out
                # (the buttons are laid out again: the disc gets them from here, not the cache)
                geoms = mb.layout(m)
                layouts[m.id] = (geoms, mb.highlight_canvas(geoms))
                mb.buttons_json(menu_module.MenuAssets(m.id, None, None, None, geoms,
                                                       normal_png=m.normal_color))
                continue
            reporter.step("menu", f"Rendering menu '{m.id}'", item=m.id)
            assets = mb.prepare(m)
            mb.encode(m, assets, lambda f, mid=m.id: reporter.progress("menu", f, mid))
            layouts[m.id] = (assets.buttons, mb.highlight_canvas(assets.buttons))
            _cache_put(store, key, assets.mpg)
            if assets.intro_mpg:
                _cache_put(store, key + "-intro", assets.intro_mpg)
                menu_files[m.id] = (assets.intro_mpg, assets.mpg)
            else:
                menu_files[m.id] = assets.mpg

    transition_files = {}
    for k, path in enumerate(sorted({key[0] for key in project.link_transitions}), 1):
        out = os.path.join(mb.work, f"transition{k}.mpg")
        key = _cache_key("transition", {"file": _file_sig(path),
                                        "disc": [project.disc.standard, project.disc.aspect]})
        name = os.path.basename(path)
        if _cache_get(cache, key, out):
            reporter.step("menu", f"Transition '{name}' unchanged (cached)", item=name)
        else:
            reporter.step("menu", f"Encoding transition '{name}'", item=name)
            mb.encode_transition(path, out, lambda f, n=name: reporter.progress("menu", f, n))
            _cache_put(store, key, out)
        transition_files[path] = out

    title_files = {}
    angle_files = {}              # title id -> the streams of its angles 2, 3, ...
    palettes = {}                 # title id -> its subtitles' colours
    os.makedirs(os.path.join(work, "titles"), exist_ok=True)
    for t in project.titles:
        # the title, then each of its angles: the same settings and sound, its
        # own picture, cut to the title's length and to exactly as many
        # frames (what `-t` alone cuts differs by a frame between ffmpeg
        # versions), so that the streams have the same GOPs
        versions = [(t, infos[t.id])]
        for k, path in enumerate(t.angles, 2):
            versions.append((dataclasses.replace(t, id=f"{t.id}-angle{k}", source=path),
                             dict(plan["_probes"].get(path) or encode.probe(path),
                                  duration=infos[t.id]["duration"])))
        frames = None                 # pictures in the title's stream, for its angles
        for v, info in versions:
            out = os.path.join(work, "titles", f"{v.id}.mpg")
            if frames is not None:
                info = dict(info, frames=frames)
            key = title_cache_key(project, v, info, title_bps[t.id], fast)
            if _cache_get(cache, key, out):
                reporter.step("encode", f"Title '{v.id}' unchanged (cached)", item=t.id)
            else:
                reporter.step("encode", f"Encoding title '{v.id}' ({info['duration']:.1f}s, "
                              f"{title_bps[t.id] / 1e6:.2f} Mbit/s, "
                              f"{'1-pass' if fast else '2-pass'})", item=t.id)
                encode.encode_title(v, info, project.disc_for(t), title_bps[t.id], out, work,
                                    two_pass=not fast,
                                    on_progress=lambda f, tid=t.id: reporter.progress("encode", f, tid),
                                    probes=plan["_probes"], frames=info.get("frames"))
                if t.audio_codec == "lpcm":
                    n = lpcmfix.fix_file(out)
                    reporter.debug(f"fixed {n} LPCM packet headers in {v.id}")
                _cache_put(store, key, out)
            if t.subtitles:
                out, palettes[t.id] = add_subtitles(project, v, out, plan, work, reporter, cues_id=t.id)
            if t.buttons:
                reporter.step("subtitles", f"Adding the buttons over '{v.id}'", item=t.id)
                out = titlebuttons.mux(v, out, title_fps(t, project.disc), infos[t.id]["duration"],
                                       project.disc.width, project.disc.height)
            if v is t:
                title_files[t.id] = out
                if t.angles:
                    frames = picture_count(out)
            else:
                angle_files.setdefault(t.id, []).append(out)

    reporter.step("author", "Writing VIDEO_TS (vtskit)")
    for sub in ("VIDEO_TS", "AUDIO_TS"):
        p = os.path.join(out_dir, sub)
        if os.path.isdir(p):
            shutil.rmtree(p)
    # the navigation as dvdauthor's XML: a readable record (nothing runs it)
    with open(os.path.join(work, "navigation.xml"), "w", encoding="utf-8") as f:
        f.write(author.build_xml(project, menu_files, title_files, out_dir, transition_files))
    try:
        videots.write(project, menu_files, title_files, out_dir, transition_files, layouts, palettes,
                      angle_files)
    except VtsError as e:
        raise OncemoreError(f"writing VIDEO_TS: {e}")
    os.makedirs(os.path.join(out_dir, "AUDIO_TS"), exist_ok=True)
    rom = copy_rom_files(project, out_dir)

    size = author.video_ts_size(out_dir)
    if size > project.disc.capacity:
        raise OncemoreError(f"VIDEO_TS is {size / 2**30:.2f} GiB, larger than "
                            f"{project.disc.target} ({project.disc.capacity / 2**30:.2f} GiB)",
                            hint="Set disc.video_bitrate lower or use DVD9.")
    result = summary(project, infos, plan)
    result.update({"video_ts": os.path.join(out_dir, "VIDEO_TS"), "bytes": size + rom,
                   "files": sorted(os.listdir(os.path.join(out_dir, "VIDEO_TS")))})
    with open(os.path.join(work, "build.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    if keep_work:
        result["work_dir"] = work
    else:
        shutil.rmtree(work, ignore_errors=True)
    return result


def build_bluray(project, out_dir, reporter, fast=False, keep_work=False, work=None, cache=True):
    """Write a Blu-ray BDMV folder (and CERTIFICATE) into out_dir: every title
    in HD with its chapters, the project's playlists and "play all", first
    play and the titles' end actions, subtitles as PGS streams, menus as
    interactive titles (DECISIONS §53, §56)."""
    tools.require(["ffmpeg", "ffprobe"], need_drawtext=bool(project.menus) or
                  any(t.subtitles for t in project.titles))
    out_dir = os.path.abspath(out_dir)
    work = work or os.path.join(out_dir, ".work")
    os.makedirs(os.path.join(work, "logs"), exist_ok=True)
    reporter.step("probe", "Checking sources")
    infos, plan = inspect(project, reporter, bd=True)
    warnings = project.warnings + plan["warnings"] + bdmenu.unsupported(project)
    plan["warnings"] = warnings
    for w in warnings:
        reporter.warn(w)
    capacity = bluray.CAPACITY[project.disc.bluray_target]
    reporter.info(f"    video up to {plan['max_bps'] / 1e6:.1f} Mbit/s, at most "
                  f"{plan['estimated_bytes'] / 2**30:.2f} of {capacity / 2**30:.2f} GiB "
                  f"({project.disc.bluray_target})")
    # --no-cache encodes everything again and keeps that (a stale entry is replaced)
    store = encode_cache_dir(project)
    cache = store if cache else None
    os.makedirs(os.path.join(work, "titles"), exist_ok=True)
    nav = bluray.Nav(project) if project.menus else None
    hd = bdmenu.hd_project(project, lambda path: plan["_probes"].get(path)
                           or encode.probe(path)) if project.menus else None
    popups = {}
    for m_id in sorted({t.remote_menu for t in project.titles if t.remote_menu}):
        # a title's Menu-key menu: its pop-up menu, over the picture
        reporter.step("menu", f"Rendering pop-up menu '{m_id}'", item=m_id)

        def popup_commands(b):
            stays = parse_action(b.action)[0] in ("audio", "subtitle")
            return nav.button(b) + ([bluray.popup_off()] if stays else [])
        popups[m_id] = bdmenu.popup_stream(
            hd, hd.menu(m_id), work, plan["font"], popup_commands,
            bluray.bd_format(project.disc.fps, project.disc)[1])
    clips = {}
    for t in project.titles:
        out = os.path.join(work, "titles", f"{t.id}.m2ts")
        sups = bluray_subtitles(project, t, plan, work, reporter) if t.subtitles else []
        popup = popups.get(t.remote_menu)
        vbps = bluray.title_max_bps(t, plan["max_bps"])      # (room for DTS-HD's peaks)
        key = _cache_key("bluray-title", {
            "title": title_cache_key(project, t, infos[t.id], vbps, fast),
            "frame": project.disc.bluray_video,
            "subtitles": [_digest(p) for p in sups],
            **({"popup": _digest(popup)} if popup else {})})
        if _cache_get(cache, key, out):
            reporter.step("encode", f"Title '{t.id}' unchanged (cached)", item=t.id)
        else:
            reporter.step("encode", f"Encoding title '{t.id}' in HD "
                          f"({infos[t.id]['duration']:.1f}s"
                          f"{', picture copied' if t.bd_copy else ''})", item=t.id)
            bluray.encode_title(t, infos[t.id], project.disc, vbps, out, work,
                                fast=fast, probes=plan["_probes"], sups=sups, popup=popup,
                                on_progress=lambda f, tid=t.id: reporter.progress("encode", f, tid))
            if popup:
                bdmenu.patch_ig_stream_type(out)
            _cache_put(store, key, out)
        clips[t.id] = out
    menus = {}
    if project.menus:
        for m in hd.menus:
            reporter.step("menu", f"Rendering menu '{m.id}' in HD", item=m.id)
            menus[m.id] = bdmenu.encode_menu(
                hd, m, work, plan["font"], nav.button, plan["max_bps"], fast=fast,
                on_progress=lambda f, mid=m.id: reporter.progress("menu", f, mid))
    transitions = {}
    for k, path in enumerate(sorted({key[0] for key in project.link_transitions}), 1):
        out = os.path.join(work, "titles", f"transition{k}.m2ts")
        name = os.path.basename(path)
        key = _cache_key("bluray-transition", {"file": _file_sig(path), "fps": project.disc.fps,
                                               "frame": project.disc.bluray_video,
                                               "max_bps": plan["max_bps"], "fast": fast})
        if _cache_get(cache, key, out):
            reporter.step("menu", f"Transition '{name}' unchanged (cached)", item=name)
        else:
            reporter.step("menu", f"Encoding transition '{name}' in HD", item=name)
            bluray.encode_transition(path, plan["_probes"].get(path) or encode.probe(path),
                                     project.disc, plan["max_bps"], out, work, fast=fast,
                                     on_progress=lambda f, n=name: reporter.progress("menu", f, n))
            _cache_put(store, key, out)
        transitions[path] = out
    reporter.step("author", "Writing BDMV")
    for sub in ("BDMV", "CERTIFICATE"):
        p = os.path.join(out_dir, sub)
        if os.path.isdir(p):
            shutil.rmtree(p)
    disc = bluray.write_bdmv(project, clips, out_dir, menus,
                             popups={t.id for t in project.titles if t.remote_menu},
                             transitions=transitions)
    rom = copy_rom_files(project, out_dir)
    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(os.path.join(out_dir, "BDMV")) for f in fs)
    if size > capacity:
        raise OncemoreError(f"BDMV is {size / 2**30:.2f} GiB, larger than "
                            f"{project.disc.bluray_target} ({capacity / 2**30:.2f} GiB)",
                            hint="Use BD50 or shorter titles.")
    result = summary(project, infos, plan)
    result["disc"]["format"] = "bluray"
    result["disc"]["target"] = project.disc.bluray_target
    result.update({"bdmv": os.path.join(out_dir, "BDMV"), "bytes": size + rom,
                   "bd_titles": disc["titles"], "playlists": disc["playlists"]})
    if keep_work:
        result["work_dir"] = work
    else:
        shutil.rmtree(work, ignore_errors=True)
    return result


def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def bluray_subtitles(project, title, plan, work, reporter):
    """Render a title's subtitle tracks as PGS streams for the HD frame (the
    disc's subtitle style scaled up from its standard). Returns .sup paths."""
    subdir = os.path.join(work, "subs", title.id)
    os.makedirs(subdir, exist_ok=True)
    hd = bluray.hd_frame(project.disc)
    k = hd.height / project.disc.height
    style = dict(project.disc.subtitle_style)
    for key in ("size", "margin", "outline_width"):
        style[key] = round(style[key] * k)
    renderer = subtitles.SubtitleRenderer(hd, subdir, link_font(plan["font"], subdir),
                                          display_width(hd), style)
    sups = []
    for j, sub in enumerate(title.subtitles):
        cues = plan["_cues"][(title.id, j)]
        reporter.step("subtitles", f"Rendering {len(cues)} subtitle(s) for '{title.id}' "
                      f"(stream {j + 1}{', ' + sub.lang if sub.lang else ''})", item=title.id)
        times = pgs.timeline(cues)
        workers = min(8, os.cpu_count() or 2)
        def draw(nc):
            n, cue = nc
            if cue.image:
                # a picture in its own colours (a PGS palette holds 255)
                idx, w, h, x, y, colours = subtitles.reduce_colours(
                    renderer.image_rgba(cue, sub.position), hd.width, hd.height, 255,
                    alpha_steps=pgs.STEPS)
                return (None if idx is None else (idx, w, h, x, y)), pgs.picture_palette(colours)
            fill = cue.color or sub.color or cue.style_color or style["color"]
            return (pgs.indexed(renderer.render_rgba(cue, f"pg{j}_{n:05d}", sub.position),
                                hd.width, hd.height), pgs.palette(fill, style["outline"]))
        with concurrent.futures.ThreadPoolExecutor(workers) as pool:
            frames = list(pool.map(draw, enumerate(cues)))
        pictures = []
        for span, (pic, entries) in zip(times, frames):
            if span is None:
                continue
            pictures.append((span[0], span[1], pic, entries))
        sups.append(pgs.write_sup(os.path.join(subdir, f"track{j}.sup"), pictures,
                                  (hd.width, hd.height)))
    return sups


def build_bluray_iso(project, out_iso, reporter, fast=False, keep_work=False, build_dir=None,
                     cache=True):
    """A Blu-ray disc image: the BDMV folder (build_bluray) written as UDF 2.50
    by the built-in writer."""
    out_iso = os.path.abspath(out_iso)
    if build_dir is None:
        stem = os.path.splitext(os.path.basename(out_iso))[0]
        build_dir = os.path.join(os.path.dirname(out_iso), f".{stem}.oncemore-build")
    build_dir = os.path.abspath(build_dir)
    disc_dir = os.path.join(build_dir, "disc")
    work = os.path.join(build_dir, ".work")
    result = build_bluray(project, disc_dir, reporter, fast=fast, keep_work=True, work=work,
                          cache=cache)
    reporter.step("iso", f"Writing {os.path.basename(out_iso)}")
    info = discimage.write_bluray(disc_dir, out_iso, project.disc.label,
                                  on_progress=lambda f: reporter.progress("iso", f))
    result.update({"iso": info["path"], "iso_bytes": info["bytes"], "iso_tool": "builtin",
                   "iso_udf": info["udf_revision"]})
    result.pop("work_dir", None)
    capacity = bluray.CAPACITY[project.disc.bluray_target]
    if info["bytes"] > capacity:
        raise OncemoreError(f"the image is {info['bytes'] / 2**30:.2f} GiB, larger than "
                            f"{project.disc.bluray_target}", hint="Use BD50 or shorter titles.")
    if keep_work:
        result["build_dir"] = build_dir
    else:
        shutil.rmtree(build_dir, ignore_errors=True)
    return result


def copy_rom_files(project, out_dir):
    """DVD-ROM content: copy disc.rom_files next to VIDEO_TS. Returns bytes."""
    total = 0
    for src in project.disc.rom_files:
        dst = os.path.join(out_dir, os.path.basename(src.rstrip(os.sep)))
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        elif os.path.exists(dst):
            os.remove(dst)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
            total += sum(os.path.getsize(os.path.join(r, f))
                         for r, _, fs in os.walk(dst) for f in fs)
        else:
            shutil.copy2(src, dst)
            total += os.path.getsize(dst)
    return total


def _layer_break_want(project):
    """disc.layer_break as (titleset, title number, chapter), or None (auto)."""
    if not project.disc.layer_break:
        return None
    tid, ch = project.disc.layer_break
    t = project.title(tid)
    return t.titleset, t.number, ch


def _layer_break_shift(project, disc_dir, iso_tool):
    """Sectors the built-in writer moves VIDEO_TS by so the layer break
    chapter starts on an ECC block (0 for the other ISO tools, or when the
    disc fits on one layer or no chapter would do: layer_break says so)."""
    if tools.iso_tool(iso_tool)[0] != "builtin":
        return 0
    plan = discimage.plan_dvd(disc_dir)
    if not layerbreak.needed(plan["total"]):
        return 0
    found = layerbreak.chapters(layerbreak.read_folder(os.path.join(disc_dir, "VIDEO_TS")))
    chapters = [(v, t, c, plan["video_ts"] + s) for v, t, c, s in found]
    try:
        return layerbreak.pick(chapters, plan["total"], _layer_break_want(project),
                               shift_ok=True)[2]
    except OncemoreError:
        return 0


def layer_break(project, image, reporter, warnings):
    """The layer break of a dual-layer image: {"sector", "title", "chapter",
    "layer0_sectors", "layer1_sectors"}, or None when it fits on one layer.
    A chosen chapter that cannot be the break is an error; with "auto" and
    no chapter that works, a warning (the disc writer then picks the middle)."""
    chapters, total = layerbreak.iso_chapters(image)
    if not layerbreak.needed(total):
        return None
    want = _layer_break_want(project)
    try:
        c, sector, _ = layerbreak.pick(chapters, total, want)
    except OncemoreError as e:
        if want:
            raise OncemoreError(e.message, hint="Choose a chapter nearer the middle of the disc "
                                "(Disc > Layer break), or \"auto\". The built-in ISO writer "
                                "puts any chapter on an ECC block; other ISO tools may not.")
        msg = f"{e.message}; the disc writer will put the layer break in the middle of the disc"
        warnings.append(msg)
        reporter.warn(msg)
        return None
    title = next(t for t in project.titles if (t.titleset, t.number) == c[:2])
    return {"sector": sector, "title": title.id, "chapter": c[2],
            "layer0_sectors": sector, "layer1_sectors": total - sector}


def build_iso(project, out_iso, reporter, fast=False, keep_work=False, iso_tool="auto",
              build_dir=None, cache=True):
    tools.require([], need_iso=True, iso_preference=iso_tool)
    out_iso = os.path.abspath(out_iso)
    if build_dir is None:
        stem = os.path.splitext(os.path.basename(out_iso))[0]
        build_dir = os.path.join(os.path.dirname(out_iso), f".{stem}.oncemore-build")
    build_dir = os.path.abspath(build_dir)
    disc_dir = os.path.join(build_dir, "disc")
    work = os.path.join(build_dir, ".work")
    result = build(project, disc_dir, reporter, fast=fast, keep_work=True, work=work, cache=cache)
    reporter.step("iso", f"Writing {os.path.basename(out_iso)}")
    dual = project.disc.target == "DVD9"
    shift = _layer_break_shift(project, disc_dir, iso_tool) if dual else 0
    info = iso.make_iso(disc_dir, out_iso, project.disc.label, iso_tool,
                        log=os.path.join(work, "logs", "iso.log"), reporter=reporter, shift=shift)
    result.update({"iso": info["path"], "iso_bytes": info["bytes"], "iso_tool": info["tool"],
                   "iso_udf": info["udf"], "volume_names": info["volume_names"]})
    result["warnings"] = result["warnings"] + info["warnings"]
    if dual:
        result["layer_break"] = layer_break(project, out_iso, reporter, result["warnings"])
    result.pop("work_dir", None)
    if info["bytes"] > project.disc.capacity:
        raise OncemoreError(f"ISO is {info['bytes'] / 2**30:.2f} GiB, larger than "
                            f"{project.disc.target}")
    if keep_work:
        result["build_dir"] = build_dir
    else:
        shutil.rmtree(build_dir, ignore_errors=True)
    return result
