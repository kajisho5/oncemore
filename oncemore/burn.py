"""Writing a built disc image to a DVD (Build > Output: DVD disc, `oncemore burn`).

macOS uses `hdiutil burn` with -forceclose, so the disc is closed (no later
sessions), as DVD players expect. Elsewhere it is growisofs (dvd+rw-tools)
with -dvd-compat, which also closes the disc. Windows has its own "Burn disc
image" for the ISO.
"""

import os
import sys

from . import tools
from .errors import MissingToolsError, OncemoreError

DEVICES = ("/dev/dvd", "/dev/sr0")   # where Linux usually has the first DVD writer


def command(iso, device=None):
    """The command that writes `iso` (an absolute path) to a DVD."""
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
    return [exe, "-dvd-compat", "-Z", f"{device}={iso}"]


def burn(iso, rep, device=None, log=None):
    """Write the disc image `iso` to a blank DVD in the writer."""
    iso = os.path.abspath(iso)
    if not os.path.isfile(iso):
        raise OncemoreError(f"no disc image at {iso}")
    cmd = command(iso, device)
    rep.step("burn", "Burning the disc")
    tools.run(cmd, log=log, what="burning the disc")
    return {"burned": iso, "device": device}
