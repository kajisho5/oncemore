"""Command-line interface."""

import argparse
import json
import os
import shutil
import sys
import tempfile

from . import __version__, build, burn, graph, scaffold, tools, web
from .errors import OncemoreError, ProjectError
from .project import PROJECT_FILENAME, load_project
from .report import Reporter


def _gib(n):
    return f"{n / 2**30:.2f} GiB"


def cmd_doctor(args, rep):
    from .menu import drawtext_probe

    info = tools.doctor()
    info["drawtext_render"] = drawtext_probe()
    ok = all(r["path"] for r in info["tools"] if r["required"]) and info["iso_tool"] is not None
    drawtext = next((r.get("drawtext") for r in info["tools"] if r["name"] == "ffmpeg"), None)
    ok = ok and bool(drawtext) and info["drawtext_render"]["ok"]
    if info["iso_tool"] and not info["iso_udf"]:
        ok = False
    lines = [f"oncemore {__version__}  python {info['python']}  {info['platform']}", ""]
    for r in info["tools"]:
        mark = "ok " if r["path"] else ("-- " if not r["required"] else "!! ")
        extra = ""
        if r["name"] == "ffmpeg" and r["path"]:
            extra = "  drawtext: " + ("yes" if r.get("drawtext") else "NO (menu text needs it)")
        where = r["path"] or ("not found" + ("" if r["required"] else " (optional)"))
        lines.append(f"  {mark}{r['name']:<12} {r['version'] or '':<14} {where}{extra}")
    lines.append("  (the ISO tools are optional: oncemore writes UDF + ISO 9660 images itself)")
    dr = info["drawtext_render"]
    lines.append("")
    lines.append("  drawtext test render: " + ("ok" if dr["ok"] else "FAILED - " + dr["detail"]))
    if dr.get("font"):
        lines.append(f"  default menu font: {dr['font']}")
    udf = "UDF + ISO 9660" if info["iso_udf"] else "ISO 9660 only - not playable as an image"
    lines.append(f"  ISO backend: {info['iso_tool'] or 'none'}" + (f" ({udf})" if info["iso_tool"] else ""))
    if not ok:
        lines.append("")
        lines.append(f"  Install missing tools with:  {tools.install_hint()}")
    rep.result({"ready": ok, **info}, "\n".join(lines))
    return 0 if ok else 3


def cmd_init(args, rep):
    res = scaffold.init(args.dir, standard=args.standard, aspect=args.aspect, force=args.force,
                        reporter=rep)
    rel = os.path.relpath(res["project"])
    if rel.startswith(".."):
        rel = res["project"]
    rep.result(res, f"Created {rel}\n\nNext:\n  oncemore iso {rel} -o "
                    f"{os.path.basename(os.path.abspath(args.dir)) or 'disc'}.iso")
    return 0


def _navigation(project, rep):
    """Flowchart checks: warnings are reported, notes go to the result."""
    notes = graph.check(project)
    for n in notes:
        if n["level"] == "warning":
            rep.warn(f"{n['path']}: {n['message']}")
    return notes


def cmd_validate(args, rep):
    project = load_project(args.project, check_files=not args.no_media)
    if args.no_media:
        data = {"valid": True, "media_checked": False, "warnings": project.warnings,
                "titles": [t.id for t in project.titles], "menus": [m.id for m in project.menus]}
        for w in project.warnings:
            rep.warn(w)
        data["navigation"] = _navigation(project, rep)
        rep.result(data, "Project is valid (media not checked).")
        return 0
    infos, plan = build.inspect(project, rep)
    s = build.summary(project, infos, plan)
    s.update({"valid": True, "media_checked": True})
    for w in s["warnings"]:
        rep.warn(w)
    s["navigation"] = _navigation(project, rep)
    lines = [f"Project OK: {project.disc.label} ({project.disc.standard} {project.disc.aspect}, "
             f"{project.disc.target})", ""]
    for t in s["titles"]:
        lines.append(f"  title {t['number']} {t['id']:<10} {t['duration']:8.1f}s  "
                     f"{len(t['chapters'])} chapter(s)  {t['audio']}  -> {t['end_action']}")
    for m in s["menus"]:
        gen = " (generated)" if m["generated"] else ""
        lines.append(f"  menu  {m['number']} {m['id']:<10} {len(m['buttons'])} button(s){gen}")
    lines += ["", f"  video bitrate: {s['video_bps'] / 1e6:.2f} Mbit/s average",
              f"  estimated size: {_gib(s['estimated_bytes'])} of {_gib(s['capacity_bytes'])}"]
    rep.result(s, "\n".join(lines))
    return 0


def cmd_simulate(args, rep):
    """Press remote keys on the project without building it."""
    from .simulate import Simulator, SimError
    project = load_project(args.project, check_files=False)
    layouts = None
    if not args.simple_layout:
        from .menu import MenuBuilder
        work = tempfile.mkdtemp(prefix="oncemore-sim-")
        try:
            mb = MenuBuilder(project, work)
            layouts = {m.id: [{"id": g.id, "rect": g.rect, "nav": g.nav, "auto": g.auto,
                               "action": g.action} for g in mb.layout(m)]
                       for m in project.menus}
        finally:
            shutil.rmtree(work, ignore_errors=True)
    if any(t.clips for t in project.titles):
        from . import clips, encode
        clips.apply_all(project, encode.probe)     # a chapter at every clip
    sim = Simulator(project, layouts)
    state = sim.start()
    steps = [{"key": None, "view": list(sim.view(state)), "log": state["log"]}]
    for key in [k for k in (args.keys or "").split(",") if k.strip()]:
        try:
            sim.press(state, key.strip())
        except SimError as e:
            raise OncemoreError(str(e))
        steps.append({"key": key.strip(), "view": list(sim.view(state)), "log": state["log"]})

    def show(v):
        if v[0] == "menu":
            m = project.menu(v[1])
            return f"menu {v[1]}, button {m.buttons[v[2] - 1].id if m.buttons else '-'}"
        if v[0] == "title":
            return f"title {v[1]}, chapter {v[2]}"
        return "stopped"
    lines = [f"{'start' if s['key'] is None else s['key']:>8}  {show(s['view'])}" for s in steps]
    rep.result({"steps": steps, "state": state}, "\n".join(lines))
    return 0


def cmd_import_psd(args, rep):
    """Add (or update) a menu from a layered Photoshop file."""
    from . import psdmenu
    from .project import build_project, read_json
    path = args.project
    if os.path.isdir(path):
        path = os.path.join(path, PROJECT_FILENAME)
    if not os.path.isfile(path):
        raise OncemoreError(f"{args.project}: project file not found")
    base = os.path.dirname(os.path.abspath(path))
    psd_path = args.psd if os.path.isfile(args.psd) else os.path.join(base, args.psd)
    if not os.path.isfile(psd_path):
        raise OncemoreError(f"{args.psd}: file not found")
    data = read_json(path)
    menu, notes = psdmenu.import_psd(psd_path, data, args.menu,
                                     os.path.join(base, "media", "psd"), base)
    menus = data.setdefault("menus", [])
    i = next((k for k, m in enumerate(menus) if m.get("id") == args.menu), None)
    if i is None:
        menus.append(menu)
    else:
        menus[i] = menu
    if args.first_play:
        data["disc"]["first_play"] = f"menu:{args.menu}"
    build_project(data, path)                  # refuse to save a broken project
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    for n in notes:
        (rep.warn if n["level"] == "warning" else rep.info)(n["message"])
    rep.result({"menu": args.menu, "buttons": [b["id"] for b in menu["buttons"]],
                "notes": notes},
               f"Menu '{args.menu}' {'updated' if i is not None else 'added'} with "
               f"{len(menu['buttons'])} button(s): "
               + ", ".join(f"{b['id']} -> {b['action']}" for b in menu["buttons"]))
    return 0


def cmd_clean(args, rep):
    """Delete what oncemore keeps to rebuild fast (encoded titles and menus,
    rendered slideshows and clips, playback previews)."""
    path = os.path.abspath(args.project)
    base = path if os.path.isdir(path) else os.path.dirname(path)
    if not os.path.exists(path) or not os.path.isfile(os.path.join(base, PROJECT_FILENAME)):
        raise OncemoreError(f"{args.project}: project file not found")
    cache = os.path.join(base, ".oncemore-cache")
    size = 0
    for root, _, files in os.walk(cache):
        for f in files:
            try:
                size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    shutil.rmtree(cache, ignore_errors=True)
    rep.result({"removed": cache, "bytes": size},
               f"Removed {cache} ({size / 2**20:.1f} MiB); the next build encodes everything again")
    return 0


def cmd_build(args, rep):
    project = load_project(args.project)
    if args.format == "web":
        res = web.build_web(project, args.output, rep, fast=args.fast, keep_work=args.keep_work)
        rep.result(res, f"Web version written to {res['web']} (open {res['index']}, "
                        f"{_gib(res['bytes'])})")
        return 0
    if args.format == "bluray":
        res = build.build_bluray(project, args.output, rep, fast=args.fast,
                                 keep_work=args.keep_work, cache=not args.no_cache)
        rep.result(res, f"BDMV written to {res['bdmv']} ({_gib(res['bytes'])})")
        return 0
    res = build.build(project, args.output, rep, fast=args.fast, keep_work=args.keep_work,
                      cache=not args.no_cache)
    rep.result(res, f"VIDEO_TS written to {res['video_ts']} ({_gib(res['bytes'])})")
    return 0


def cmd_iso(args, rep):
    project = load_project(args.project)
    if args.format == "bluray":
        if args.iso_tool not in ("auto", "builtin"):
            raise OncemoreError("Blu-ray images are written by the built-in UDF 2.50 writer",
                                hint="Leave out --iso-tool.")
        res = build.build_bluray_iso(project, args.output, rep, fast=args.fast,
                                     keep_work=args.keep_work, build_dir=args.build_dir,
                                     cache=not args.no_cache)
        rep.result(res, f"Blu-ray image written to {res['iso']} ({_gib(res['iso_bytes'])}, "
                        "UDF 2.50)")
        return 0
    res = build.build_iso(project, args.output, rep, fast=args.fast, keep_work=args.keep_work,
                          iso_tool=args.iso_tool, build_dir=args.build_dir,
                          cache=not args.no_cache)
    rep.result(res, f"ISO written to {res['iso']} ({_gib(res['iso_bytes'])}, {res['iso_tool']})")
    return 0


def cmd_burn(args, rep):
    res = burn.burn(args.iso, rep, device=args.device)
    rep.result(res, f"{res['burned']} written to the DVD")
    return 0


def cmd_transcode(args, rep):
    project = load_project(args.project)
    if args.status:
        st = build.encode_status(project, fast=args.fast)
        lines = [f"  {'transcoded' if ok else 'not yet   '}  {tid}" for tid, ok in st.items()]
        rep.result({"titles": st}, "\n".join(lines))
        return 0
    res = build.transcode(project, rep, args.title or None, fast=args.fast)
    n = sum(1 for v in res["titles"].values() if v == "transcoded")
    rep.result(res, f"{n} title(s) transcoded, {len(res['titles']) - n} already up to date")
    return 0


def cmd_preview(args, rep):
    from .menu import MenuBuilder

    project = load_project(args.project)
    tools.require(["ffmpeg", "ffprobe"], need_drawtext=True)
    menu_id = args.menu or (project.root_menu.id if project.root_menu else None)
    menu = project.menu(menu_id) if menu_id else None
    if menu is None:
        ids = ", ".join(m.id for m in project.menus) or "none"
        raise OncemoreError(f"no menu {menu_id!r} (menus: {ids})")
    work = tempfile.mkdtemp(prefix="oncemore-preview-")
    try:
        res = MenuBuilder(project, work, rep).preview(menu, args.output, button=args.button,
                                                      state=args.state, outline=args.outline)
    finally:
        if args.keep_work:
            rep.info(f"work files kept in {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    rep.result(res, f"Preview of menu '{menu.id}' written to {res['path']}")
    return 0


def cmd_gui(args, rep):
    from .gui.server import serve

    path = os.path.abspath(args.project)
    if os.path.isfile(path):
        path = os.path.dirname(path)
    return serve(path, port=args.port, open_browser=not args.no_browser, reporter=rep)


def cmd_mcp(args, rep):
    from .mcp import serve
    return serve(args.root)


def make_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="machine-readable JSON Lines output on stdout")
    common.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS)

    p = argparse.ArgumentParser(
        prog="oncemore", parents=[common],
        description="DVD-Video authoring: menus, chapters, ISO - once more.")
    p.add_argument("--version", action="version", version=f"oncemore {__version__}")
    sub = p.add_subparsers(dest="command", metavar="<command>")
    sub.required = True

    s = sub.add_parser("init", parents=[common], help="create a sample project")
    s.add_argument("dir")
    s.add_argument("--standard", choices=["NTSC", "PAL"], default="NTSC")
    s.add_argument("--aspect", choices=["16:9", "4:3"], default="16:9")
    s.add_argument("--force", action="store_true", help="overwrite an existing project file")
    s.set_defaults(func=cmd_init)

    proj_help = f"project file or directory containing {PROJECT_FILENAME}"
    s = sub.add_parser("validate", parents=[common], help="check project, media and size")
    s.add_argument("project", help=proj_help)
    s.add_argument("--no-media", action="store_true", help="only check the JSON (no file checks, no ffprobe)")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("import-psd", parents=[common],
                       help="make a menu from a layered Photoshop file")
    s.add_argument("project", help=proj_help)
    s.add_argument("psd", help="the .psd / .psb file")
    s.add_argument("--menu", required=True, help="id of the menu to add or update")
    s.add_argument("--first-play", action="store_true",
                   help="also make it the menu the disc starts with")
    s.set_defaults(func=cmd_import_psd)

    s = sub.add_parser("simulate", parents=[common],
                       help="press remote-control keys on the project (no encoding)")
    s.add_argument("project", help=proj_help)
    s.add_argument("--keys", default="",
                   help="comma-separated keys: up, down, left, right, enter, menu, title, "
                        "next, prev, play, end, timeout, select:<button>")
    s.add_argument("--simple-layout", action="store_true",
                   help="lay buttons out in a column instead of measuring the labels "
                        "(no ffmpeg needed; arrow keys may differ from the disc)")
    s.set_defaults(func=cmd_simulate)

    def build_opts(sp):
        sp.add_argument("--fast", action="store_true", help="1-pass encoding (default: 2-pass)")
        sp.add_argument("--keep-work", action="store_true",
                        help="keep intermediate files (.work/) after success")
        sp.add_argument("--no-cache", action="store_true",
                        help="encode everything again (default: reuse unchanged titles and "
                             "menus from <project>/.oncemore-cache)")

    s = sub.add_parser("build", parents=[common],
                       help="author VIDEO_TS (or a Blu-ray BDMV) into a directory")
    s.add_argument("project", help=proj_help)
    s.add_argument("-o", "--output", required=True, help="output directory")
    s.add_argument("--format", choices=["dvd", "bluray", "web"], default="dvd",
                   help="dvd = VIDEO_TS (default); bluray = BDMV in HD; web = a folder a "
                        "browser plays as the disc (index.html, MP4 titles, the menus)")
    build_opts(s)
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("iso", parents=[common], help="build and write an ISO image")
    s.add_argument("project", help=proj_help)
    s.add_argument("-o", "--output", required=True, help="output .iso file")
    s.add_argument("--iso-tool", default="auto",
                   choices=["auto", "builtin", "hdiutil", "genisoimage", "mkisofs", "xorriso"],
                   help="auto = the built-in writer (UDF 1.02 + ISO 9660, nothing to install)")
    s.add_argument("--build-dir", help="where to author VIDEO_TS (default: next to the ISO)")
    s.add_argument("--format", choices=["dvd", "bluray"], default="dvd",
                   help="dvd (default) or bluray: a Blu-ray image (UDF 2.50, built-in writer)")
    build_opts(s)
    s.set_defaults(func=cmd_iso)

    s = sub.add_parser("burn", parents=[common], help="write a disc image to a blank DVD")
    s.add_argument("iso", help="the .iso made by `oncemore iso`")
    s.add_argument("--device", help="DVD writer (macOS: as `hdiutil burn -list` names it; "
                                    "elsewhere e.g. /dev/sr0; default: the first one)")
    s.set_defaults(func=cmd_burn)

    s = sub.add_parser("clean", parents=[common],
                       help="delete the encode cache (<project>/.oncemore-cache)")
    s.add_argument("project", help=proj_help)
    s.set_defaults(func=cmd_clean)

    s = sub.add_parser("transcode", parents=[common],
                       help="encode titles now; the next build or iso reuses them")
    s.add_argument("project", help=proj_help)
    s.add_argument("--title", action="append", metavar="ID",
                   help="only this title (repeat for several; default: all)")
    s.add_argument("--fast", action="store_true",
                   help="1-pass encoding (use the same choice as the build)")
    s.add_argument("--status", action="store_true",
                   help="only show which titles are transcoded")
    s.set_defaults(func=cmd_transcode)

    s = sub.add_parser("preview-menu", parents=[common], help="render a menu to PNG")
    s.add_argument("project", help=proj_help)
    s.add_argument("--menu", help="menu id (default: the first-play/root menu)")
    s.add_argument("-o", "--output", required=True, help="output .png")
    s.add_argument("--button", help="button to show highlighted (default: first)")
    s.add_argument("--state", choices=["highlight", "select", "normal"], default="highlight")
    s.add_argument("--outline", action="store_true", help="draw every button's hit area")
    s.add_argument("--keep-work", action="store_true")
    s.set_defaults(func=cmd_preview)

    s = sub.add_parser("gui", parents=[common], help="open the authoring GUI in your browser")
    s.add_argument("project", nargs="?", default=".",
                   help="project folder (created if missing; default: current folder)")
    s.add_argument("--port", type=int, default=0, help="port (default: any free port)")
    s.add_argument("--no-browser", action="store_true", help="only print the URL")
    s.set_defaults(func=cmd_gui)

    s = sub.add_parser("doctor", parents=[common], help="check external tools")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("mcp", parents=[common],
                       help="serve oncemore's tools to AI assistants (MCP over stdio)")
    s.add_argument("--root", action="append", metavar="DIR",
                   help="a folder the assistant may use, with everything in it (repeat for "
                        "several; default: your home folder)")
    s.set_defaults(func=cmd_mcp)
    return p


def main(argv=None):
    args = make_parser().parse_args(argv)
    rep = Reporter(json_mode=getattr(args, "json", False), verbose=getattr(args, "verbose", False))
    try:
        return args.func(args, rep)
    except ProjectError as e:
        rep.error(e.message, e.hint, issues=e.issues)
        return e.exit_code
    except OncemoreError as e:
        rep.error(e.message, e.hint, **e.details)
        return e.exit_code
    except KeyboardInterrupt:
        rep.error("interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
