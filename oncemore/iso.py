"""ISO image creation.

DVD players and libdvdread (the library VLC, mpv and most software players
use) locate VIDEO_TS through the UDF file system, so a DVD-Video image needs
a UDF + ISO 9660 "bridge" layout. Backends, in `auto` order:

  hdiutil      macOS built-in: `makehybrid -udf -udf-version 1.02 -iso`
  genisoimage  `-dvd-video -udf` (Debian/Ubuntu package `genisoimage`)
  mkisofs      `-dvd-video -udf` (cdrtools; `brew install cdrtools`)
  xorriso      last resort only: it writes ISO 9660/Joliet but no UDF, so
               libdvdread-based players cannot open the image directly
               (it still works when mounted and opened as a folder).
"""

import os
import shutil

from . import tools, udfinfo
from .errors import OncemoreError

XORRISO_WARNING = (
    "xorriso cannot write UDF, so this ISO has only an ISO 9660 file system. "
    "VLC/mpv (libdvdread) and most DVD players will not open it as a disc image. "
    "Install genisoimage (Linux) / use hdiutil (macOS) for a playable image.")

DISC_ENTRIES = ("VIDEO_TS", "AUDIO_TS")


def _staging(dvd_dir):
    """Return a directory that contains only VIDEO_TS/AUDIO_TS (hard links)."""
    extra = [n for n in os.listdir(dvd_dir) if n not in DISC_ENTRIES]
    if not extra:
        return dvd_dir, None
    stage = dvd_dir.rstrip(os.sep) + ".iso-staging"
    shutil.rmtree(stage, ignore_errors=True)
    for sub in DISC_ENTRIES:
        src = os.path.join(dvd_dir, sub)
        dst = os.path.join(stage, sub)
        os.makedirs(dst)
        if not os.path.isdir(src):
            continue
        for name in sorted(os.listdir(src)):
            try:
                os.link(os.path.join(src, name), os.path.join(dst, name))
            except OSError:
                shutil.copy2(os.path.join(src, name), os.path.join(dst, name))
    return stage, stage


def command(name, path, src, out_iso, label):
    if name == "hdiutil":
        return [path, "makehybrid", "-quiet", "-o", out_iso, "-udf", "-udf-version", "1.02",
                "-iso", "-udf-volume-name", label, "-iso-volume-name", label,
                "-default-volume-name", label, src]
    if name in ("genisoimage", "mkisofs"):
        return [path, "-quiet", "-dvd-video", "-udf", "-V", label, "-o", out_iso, src]
    if name == "xorriso":
        return [path, "-as", "mkisofs", "-J", "-V", label, "-o", out_iso, src]
    raise OncemoreError(f"unknown ISO tool {name!r}")


def make_iso(dvd_dir, out_iso, label, tool="auto", log=None, reporter=None):
    if not os.path.isdir(os.path.join(dvd_dir, "VIDEO_TS")):
        raise OncemoreError(f"{dvd_dir} has no VIDEO_TS directory")
    tools.require([], need_iso=True, iso_preference=tool)
    name, path = tools.iso_tool(tool)
    out_iso = os.path.abspath(out_iso)
    os.makedirs(os.path.dirname(out_iso) or ".", exist_ok=True)
    if os.path.exists(out_iso):
        os.remove(out_iso)
    os.makedirs(os.path.join(dvd_dir, "AUDIO_TS"), exist_ok=True)
    src, cleanup = _staging(dvd_dir)
    warnings = []
    if name == "xorriso":
        warnings.append(XORRISO_WARNING)
        if reporter:
            reporter.warn(XORRISO_WARNING)
    try:
        tools.run(command(name, path, src, out_iso, label), log=log, what=name)
    finally:
        if cleanup:
            shutil.rmtree(cleanup, ignore_errors=True)
    if not os.path.isfile(out_iso):
        # some hdiutil versions append an extension
        for ext in (".iso", ".cdr"):
            if os.path.isfile(out_iso + ext):
                os.replace(out_iso + ext, out_iso)
                break
    if not os.path.isfile(out_iso):
        raise OncemoreError(f"{name} did not produce {out_iso}")
    names = udfinfo.volume_names(out_iso)
    if name != "xorriso" and names["udf_volume"] != label:
        msg = (f"{name} wrote UDF volume name {names['udf_volume']!r} instead of {label!r}; "
               "players show the UDF name as the disc title")
        warnings.append(msg)
        if reporter:
            reporter.warn(msg)
    return {"tool": name, "path": out_iso, "bytes": os.path.getsize(out_iso),
            "udf": name != "xorriso", "volume_names": names, "warnings": warnings}
