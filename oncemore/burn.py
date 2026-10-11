"""Writing a built disc image to a DVD (Build > Output: DVD disc, `oncemore burn`).

macOS uses `hdiutil burn` with -forceclose, so the disc is closed (no later
sessions), as DVD players expect. Elsewhere it is growisofs (dvd+rw-tools)
with -dvd-compat, which also closes the disc. Windows has its own "Burn disc
image" for the ISO.

A dual-layer image is given its layer break (growisofs
-use-the-force-luke=break:N): the one the build chose, or else the first
chapter that can be one (layerbreak.py). hdiutil has no such option and
chooses the place itself.
"""

import os
import sys

from . import layerbreak, tools
from .errors import MissingToolsError, OncemoreError

DEVICES = ("/dev/dvd", "/dev/sr0")   # where Linux usually has the first DVD writer


def command(iso, device=None, layer_break=None):
    """The command that writes `iso` (an absolute path) to a DVD, with the
    layer break at sector `layer_break` (growisofs)."""
    if tools.is_macos():
        cmd = [tools.find("hdiutil") or "hdiutil", "burn", iso, "-forceclose"]
        return cmd + ["-device", device] if device else cmd
    if sys.platform.startswith("win"):
        raise OncemoreError("oncemore cannot burn discs on Windows",
                            hint="Right-click the .iso in Explorer and choose "
                                 "\"Burn disc image\".")
    exe = tools.find("growisofs")
    if exe is None:
        raise MissingToolsError("burning a DVD needs growisofs",
                                hint="Install dvd+rw-tools (Debian / Ubuntu: "
                                     "sudo apt install growisofs).")
    if device is None:
        device = next((d for d in DEVICES if os.path.exists(d)), None)
        if device is None:
            raise OncemoreError("no DVD writer found (looked for " + ", ".join(DEVICES) + ")",
                                hint="Connect a DVD writer, or name its device.")
    lb = [f"-use-the-force-luke=break:{layer_break}"] if layer_break else []
    return [exe, "-dvd-compat", *lb, "-Z", f"{device}={iso}"]


def find_layer_break(iso, rep=None):
    """The first chapter of a dual-layer DVD image that can be its layer
    break (its sector), or None for an image that fits on one layer or is
    not a DVD-Video image."""
    try:
        chapters, total = layerbreak.iso_chapters(iso)
    except (OncemoreError, OSError, IndexError, KeyError, ValueError):
        return None
    if not layerbreak.needed(total):
        return None
    try:
        return layerbreak.pick(chapters, total)[1]
    except OncemoreError as e:
        if rep:
            rep.warn(f"{e.message}; the writer will put the layer break in the middle")
        return None


def burn(iso, rep, device=None, log=None, layer_break="auto"):
    """Write the disc image `iso` to a blank DVD in the writer. `layer_break`:
    a sector, "auto" (found in the image) or None."""
    iso = os.path.abspath(iso)
    if not os.path.isfile(iso):
        raise OncemoreError(f"no disc image at {iso}")
    if layer_break == "auto":
        layer_break = find_layer_break(iso, rep)
    if layer_break and tools.is_macos():
        rep.warn("hdiutil chooses the layer break of a dual-layer disc itself")
    cmd = command(iso, device, layer_break)
    rep.step("burn", "Burning the disc")
    tools.run(cmd, log=log, what="burning the disc")
    return {"burned": iso, "device": device, "burn_layer_break": layer_break}
