"""The build pipeline: probe -> plan -> menus -> titles -> dvdauthor -> (ISO)."""

import json
import os
import shutil

from . import author, encode, iso, lpcmfix, tools
from .errors import OncemoreError, ProjectError
from .menu import MenuBuilder


def inspect(project, reporter=None):
    """Probe every source and plan the bitrate. Used by validate and build."""
    tools.require(["ffprobe"])
    issues = []
    infos = {}
    for i, t in enumerate(project.titles):
        info = encode.probe(t.source)
        infos[t.id] = info
        where = f"titles[{i}]"
        if not info.get("has_video"):
            issues.append({"path": f"{where}.source", "message": "no video stream"})
            continue
        if not info.get("duration"):
            issues.append({"path": f"{where}.source", "message": "cannot determine duration"})
            continue
        for j, c in enumerate(t.chapters):
            if c >= info["duration"]:
                issues.append({"path": f"{where}.chapters[{j}]",
                               "message": f"chapter at {c:.3f}s is beyond the end "
                                          f"({info['duration']:.3f}s)"})
    menu_files = []
    for i, m in enumerate(project.menus):
        for what, path in (("background", m.background), ("audio", m.audio)):
            if path:
                info = encode.probe(path)
                if what == "audio" and not info.get("has_audio"):
                    issues.append({"path": f"menu {m.id!r}.audio", "message": "no audio stream"})
                menu_files.append(path)
    if issues:
        raise ProjectError("media check failed", issues)
    menu_seconds = 0.0
    for m in project.menus:
        if m.duration:
            menu_seconds += m.duration
        elif m.audio:
            menu_seconds += min(encode.probe(m.audio).get("duration") or 5.0, 600.0)
        else:
            menu_seconds += 5.0
    font = None
    if project.menus:
        from .menu import find_font, menu_text
        font = find_font(project.disc.font, menu_text(project))
    plan = encode.plan_bitrate([(infos[t.id]["duration"], t.audio_bps) for t in project.titles],
                               project.disc.capacity, menu_seconds, project.disc.video_bitrate)
    plan["font"] = font
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
                    "audio_bps": t.audio_bps, "end_action": t.end_action}
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


def build(project, out_dir, reporter, fast=False, keep_work=False, work=None):
    """Author VIDEO_TS into out_dir. Returns a result dict."""
    tools.require(list(tools.REQUIRED), need_drawtext=bool(project.menus))
    out_dir = os.path.abspath(out_dir)
    work = work or os.path.join(out_dir, ".work")
    os.makedirs(work, exist_ok=True)
    logs = os.path.join(work, "logs")

    reporter.step("probe", "Checking sources")
    infos, plan = inspect(project, reporter)
    for w in project.warnings + plan["warnings"]:
        reporter.warn(w)
    vbps = plan["video_bps"]
    reporter.info(f"    video {vbps / 1e6:.2f} Mbit/s average, estimated "
                  f"{plan['estimated_bytes'] / 2**30:.2f} of {plan['capacity'] / 2**30:.2f} GiB")

    menu_files = {}
    if project.menus:
        mb = MenuBuilder(project, work, reporter)
        reporter.info(f"    menu font: {mb.font() and mb.font_source}")
        for m in project.menus:
            reporter.step("menu", f"Rendering menu '{m.id}'", item=m.id)
            assets = mb.prepare(m)
            mb.encode(m, assets, lambda f, mid=m.id: reporter.progress("menu", f, mid))
            menu_files[m.id] = assets.mpg

    title_files = {}
    os.makedirs(os.path.join(work, "titles"), exist_ok=True)
    for t in project.titles:
        reporter.step("encode", f"Encoding title '{t.id}' ({infos[t.id]['duration']:.1f}s, "
                      f"{'1-pass' if fast else '2-pass'})", item=t.id)
        out = os.path.join(work, "titles", f"{t.id}.mpg")
        encode.encode_title(t, infos[t.id], project.disc, vbps, out, work, two_pass=not fast,
                            on_progress=lambda f, tid=t.id: reporter.progress("encode", f, tid))
        if t.audio_codec == "lpcm":
            n = lpcmfix.fix_file(out)
            reporter.debug(f"fixed {n} LPCM packet headers in {t.id}")
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

    size = author.video_ts_size(out_dir)
    if size > project.disc.capacity:
        raise OncemoreError(f"VIDEO_TS is {size / 2**30:.2f} GiB, larger than "
                            f"{project.disc.target} ({project.disc.capacity / 2**30:.2f} GiB)",
                            hint="Set disc.video_bitrate lower or use DVD9.")
    result = summary(project, infos, plan)
    result.update({"video_ts": os.path.join(out_dir, "VIDEO_TS"), "bytes": size,
                   "files": sorted(os.listdir(os.path.join(out_dir, "VIDEO_TS")))})
    with open(os.path.join(work, "build.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    if keep_work:
        result["work_dir"] = work
    else:
        shutil.rmtree(work, ignore_errors=True)
    return result


def build_iso(project, out_iso, reporter, fast=False, keep_work=False, iso_tool="auto",
              build_dir=None):
    tools.require([], need_iso=True, iso_preference=iso_tool)
    out_iso = os.path.abspath(out_iso)
    if build_dir is None:
        stem = os.path.splitext(os.path.basename(out_iso))[0]
        build_dir = os.path.join(os.path.dirname(out_iso), f".{stem}.oncemore-build")
    build_dir = os.path.abspath(build_dir)
    disc_dir = os.path.join(build_dir, "disc")
    work = os.path.join(build_dir, ".work")
    result = build(project, disc_dir, reporter, fast=fast, keep_work=True, work=work)
    reporter.step("iso", f"Writing {os.path.basename(out_iso)}")
    info = iso.make_iso(disc_dir, out_iso, project.disc.label, iso_tool,
                        log=os.path.join(work, "logs", "iso.log"), reporter=reporter)
    result.update({"iso": info["path"], "iso_bytes": info["bytes"], "iso_tool": info["tool"],
                   "iso_udf": info["udf"]})
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
