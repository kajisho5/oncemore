"""The build pipeline: probe -> plan -> menus -> titles -> dvdauthor -> (ISO)."""

import dataclasses
import functools
import hashlib
import json
import os
import shutil

from . import author, encode, iso, lpcmfix, subtitles, tools
from . import menu as menu_module
from .errors import OncemoreError, ProjectError
from .menu import (MenuBuilder, check_element_fonts, display_width, find_font, link_font,
                   menu_seconds, menu_text)


def inspect(project, reporter=None):
    """Probe every source and plan the bitrate. Used by validate and build."""
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

    for i, t in enumerate(project.titles):
        info = probe(t.source)
        infos[t.id] = info
        where = f"titles[{i}]"
        for j, tr in enumerate(t.audio_tracks):
            have = probe(tr.source).get("audio_streams", 0)
            if tr.stream >= have and not (tr.source == t.source and tr.stream == 0):
                issues.append({"path": f"{where}.audio_tracks[{j}]",
                               "message": f"{os.path.basename(tr.source)} has {have} audio "
                                          f"stream(s); stream {tr.stream} does not exist"})
            elif t.audio_passthrough:
                a = (probe(tr.source).get("audio") or [{}] * (tr.stream + 1))[tr.stream]
                if a.get("codec") != "ac3" or a.get("rate") != 48000:
                    issues.append({"path": f"{where}.audio_tracks[{j}]",
                                   "message": f"{os.path.basename(tr.source)} audio stream "
                                              f"{tr.stream} is {a.get('codec')} "
                                              f"{a.get('rate')} Hz; only 48 kHz AC-3 can be "
                                              "copied (turn off audio.passthrough)"})
                elif a.get("channels") != t.audio_channels:
                    issues.append({"path": f"{where}.audio.channels",
                                   "message": f"the AC-3 source has {a.get('channels')} "
                                              f"channel(s); set audio.channels to "
                                              f"{a.get('channels')} to copy it"})
                elif a.get("bit_rate"):
                    t.audio_bitrate = max(t.audio_bitrate, a["bit_rate"])
            elif t.audio_channels == 6 and tr.stream == 0 \
                    and 0 < probe(tr.source).get("audio_channels", 0) < 6:
                warnings.append(f"{where}.audio_tracks[{j}]: {os.path.basename(tr.source)} has "
                                f"{probe(tr.source)['audio_channels']} channel(s); the 5.1 "
                                "track will only use the front speakers")
        for j, sub in enumerate(t.subtitles):
            cues[(t.id, j)] = subtitles.load_subtitles(sub.file)
            if not cues[(t.id, j)]:
                warnings.append(f"{where}.subtitles[{j}]: {os.path.basename(sub.file)} has no cues")
        if t.subtitles:
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
    for m in project.menus:
        if m.loop_point and m.loop_point >= menu_seconds(m, probe) - 0.5:
            issues.append({"path": f"menu {m.id!r}.loop_point",
                           "message": f"loop point {m.loop_point:.2f}s must be at least 0.5 s "
                                      f"before the end of the menu ({menu_seconds(m, probe):.2f}s)"})
    if issues:
        raise ProjectError("media check failed", issues)
    menu_total = sum(menu_seconds(m, probe) for m in project.menus)
    font = None
    text = menu_text(project) + "".join("".join(line for c in cs for line in c.lines)
                                        for cs in cues.values())
    if project.menus or cues:
        font = find_font(project.disc.font, text)
    check_element_fonts(project)
    plan = encode.plan_bitrate([(infos[t.id]["duration"], t.audio_bps, t.video_bitrate)
                                for t in project.titles],
                               project.disc.capacity, menu_total, project.disc.video_bitrate)
    plan["font"] = font
    plan["warnings"] = warnings + plan["warnings"]
    plan["_probes"] = probes
    plan["_cues"] = cues
    return infos, plan


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
                    "titleset": t.titleset, "global_number": t.global_number,
                    "video_bps": dict(zip([x.id for x in project.titles],
                                          plan.get("per_title", []))).get(t.id),
                    "audio_bps": t.audio_bps, "end_action": t.end_action,
                    "audio_tracks": [{"source": a.source, "stream": a.stream, "lang": a.lang}
                                     for a in t.audio_tracks],
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
    }


def add_subtitles(project, title, mpg, plan, work, reporter):
    """Render the title's SRT tracks and mux them in as subpicture streams."""
    subdir = os.path.join(work, "subs", title.id)
    os.makedirs(subdir, exist_ok=True)
    renderer = subtitles.SubtitleRenderer(project.disc, subdir, link_font(plan["font"], subdir),
                                          display_width(project.disc),
                                          project.disc.subtitle_style)
    xmls = []
    for j, sub in enumerate(title.subtitles):
        cues = plan["_cues"][(title.id, j)]
        reporter.step("subtitles", f"Rendering {len(cues)} subtitle(s) for '{title.id}' "
                      f"(stream {j + 1}{', ' + sub.lang if sub.lang else ''})", item=title.id)
        xmls.append(renderer.stream_xml(cues, sub.lang or "xx", j, sub.position, sub.color))
    return subtitles.mux_streams(mpg, xmls, subdir, project.disc.standard,
                                 os.path.join(work, "logs", f"spumux-{title.id}"))


# -- encode cache --------------------------------------------------------------
# Encoded titles and menus are kept in <project>/.oncemore-cache/encode, keyed
# by everything that changes their bytes (sources and their mtimes, settings,
# bitrate, ffmpeg version), so a rebuild only encodes what changed.
CACHE_VERSION = 1


@functools.lru_cache(maxsize=None)
def _code_signature():
    """The encoding code itself is part of every key: a new oncemore that
    encodes differently never reuses old results."""
    h = hashlib.sha256()
    for mod in (encode, menu_module, lpcmfix):
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
                       "ffmpeg": _tool_version("ffmpeg"), "spumux": _tool_version("spumux"),
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
    if cache:
        os.makedirs(cache, exist_ok=True)
        tmp = os.path.join(cache, key + ".part")
        _link_or_copy(path, tmp)
        os.replace(tmp, os.path.join(cache, key + ".mpg"))


def _link_or_copy(src, dst):
    if os.path.lexists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copyfile(src, dst)


def title_cache_key(project, title, info, vbps, fast):
    disc = project.disc_for(title)
    return _cache_key("title", {
        "source": _file_sig(title.source), "info": {k: info.get(k) for k in (
            "width", "height", "sar", "fps", "duration", "interlaced", "field_order")},
        "tracks": [(_file_sig(tr.source), tr.stream) for tr in title.audio_tracks],
        "disc": [disc.standard, disc.aspect, disc.width, disc.height],
        "chapters": title.chapters, "vbps": vbps, "fast": fast,
        "audio": [title.audio_codec, title.audio_bitrate, title.audio_channels,
                  title.audio_passthrough]})


def menu_cache_key(project, menu, font):
    files = [menu.background, menu.background_video, menu.audio, font] + \
        [b.image for b in menu.buttons] + [b.highlight_image for b in menu.buttons] + \
        [el.font for el in list(menu.texts) + list(menu.buttons)] + \
        [project.title(b.thumb.title_id).source for b in menu.buttons if b.thumb]
    return _cache_key("menu", {
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
    cache = os.path.join(project.base_dir, ".oncemore-cache", "encode") if cache else None
    reporter.info(f"    video {vbps / 1e6:.2f} Mbit/s average, estimated "
                  f"{plan['estimated_bytes'] / 2**30:.2f} of {plan['capacity'] / 2**30:.2f} GiB")

    menu_files = {}
    if project.menus:
        mb = MenuBuilder(project, work, reporter, font=plan["font"])
        reporter.info(f"    menu font: {mb.font() and mb.font_source}")
        for m in project.menus:
            key = menu_cache_key(project, m, plan["font"])
            out = os.path.join(mb.work, f"{m.id}.mpg")
            if _cache_get(cache, key, out):
                reporter.step("menu", f"Menu '{m.id}' unchanged (cached)", item=m.id)
                menu_files[m.id] = out
                continue
            reporter.step("menu", f"Rendering menu '{m.id}'", item=m.id)
            assets = mb.prepare(m)
            mb.encode(m, assets, lambda f, mid=m.id: reporter.progress("menu", f, mid))
            _cache_put(cache, key, assets.mpg)
            menu_files[m.id] = assets.mpg

    title_files = {}
    os.makedirs(os.path.join(work, "titles"), exist_ok=True)
    for t in project.titles:
        out = os.path.join(work, "titles", f"{t.id}.mpg")
        key = title_cache_key(project, t, infos[t.id], title_bps[t.id], fast)
        if _cache_get(cache, key, out):
            reporter.step("encode", f"Title '{t.id}' unchanged (cached)", item=t.id)
        else:
            reporter.step("encode", f"Encoding title '{t.id}' ({infos[t.id]['duration']:.1f}s, "
                          f"{title_bps[t.id] / 1e6:.2f} Mbit/s, "
                          f"{'1-pass' if fast else '2-pass'})", item=t.id)
            encode.encode_title(t, infos[t.id], project.disc_for(t), title_bps[t.id], out, work,
                                two_pass=not fast,
                                on_progress=lambda f, tid=t.id: reporter.progress("encode", f, tid),
                                probes=plan["_probes"])
            if t.audio_codec == "lpcm":
                n = lpcmfix.fix_file(out)
                reporter.debug(f"fixed {n} LPCM packet headers in {t.id}")
            _cache_put(cache, key, out)
        if t.subtitles:
            out = add_subtitles(project, t, out, plan, work, reporter)
        title_files[t.id] = out

    reporter.step("author", "Authoring VIDEO_TS (dvdauthor)")
    for sub in ("VIDEO_TS", "AUDIO_TS"):
        p = os.path.join(out_dir, sub)
        if os.path.isdir(p):
            shutil.rmtree(p)
    xml = author.build_xml(project, menu_files, title_files, out_dir)
    xml_path = os.path.join(work, "dvdauthor.xml")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml)
    author.run_dvdauthor(xml_path, project, os.path.join(logs, "dvdauthor.log"))
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
    info = iso.make_iso(disc_dir, out_iso, project.disc.label, iso_tool,
                        log=os.path.join(work, "logs", "iso.log"), reporter=reporter)
    result.update({"iso": info["path"], "iso_bytes": info["bytes"], "iso_tool": info["tool"],
                   "iso_udf": info["udf"], "volume_names": info["volume_names"]})
    result["warnings"] = result["warnings"] + info["warnings"]
    result.pop("work_dir", None)
    if info["bytes"] > project.disc.capacity:
        raise OncemoreError(f"ISO is {info['bytes'] / 2**30:.2f} GiB, larger than "
                            f"{project.disc.target}")
    if keep_work:
        result["build_dir"] = build_dir
    else:
        shutil.rmtree(build_dir, ignore_errors=True)
    return result
