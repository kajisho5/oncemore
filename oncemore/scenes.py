"""Scene changes in a video, as chapter suggestions.

ffmpeg's scene score (how much a picture differs from the one before, 0 to
1) is computed on a small copy of the picture; the pictures scoring over
the threshold are cuts. Cuts closer together than `min_gap` seconds (to
the start or to the cut kept before them) are dropped, so a flash or a
quick montage does not become a run of chapters.
"""

import re
import subprocess

from . import tools
from .errors import OncemoreError

SENSITIVITY = {"low": 0.5, "medium": 0.35, "high": 0.2}
_TIME = re.compile(r"pts_time:\s*([0-9]+(?:\.[0-9]+)?)")


def detect(path, threshold=SENSITIVITY["medium"], min_gap=10.0, start=0.0, end=None):
    """Times (seconds from the file's start) of the cuts in `path` between
    `start` and `end`, at least `min_gap` apart and from `start`."""
    if not 0 < threshold < 1:
        raise ValueError("the scene threshold is between 0 and 1")
    tools.require(["ffmpeg"])
    cmd = [tools.find("ffmpeg"), "-hide_banner", "-nostdin"]
    # (reading only that part of the file: both as input options)
    if start:
        cmd += ["-ss", f"{start:.3f}"]
    if end is not None:
        cmd += ["-t", f"{max(0.0, end - start):.3f}"]
    cmd += ["-i", path]
    cmd += ["-an", "-sn", "-dn", "-vf",
            f"scale=320:-2,select='gt(scene\\,{threshold:.3f})',showinfo", "-f", "null", "-"]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=3600)
    if p.returncode != 0:
        raise OncemoreError(f"cannot read {path} for scene changes",
                            details={"output": tools.tail(p.stderr)})
    out, last = [], start or 0.0
    for line in p.stderr.splitlines():
        if "Parsed_showinfo" not in line:
            continue
        m = _TIME.search(line)
        if not m:
            continue
        # (with -ss before -i the times start at 0 again)
        t = float(m.group(1)) + (start or 0.0)
        if t - last >= min_gap:
            out.append(round(t, 3))
            last = t
    return out
