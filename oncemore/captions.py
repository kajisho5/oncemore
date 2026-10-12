"""Closed captions (line 21, CEA-608) on a DVD: dvdcc (DECISIONS §107),
copied into oncemore/_vendor/dvdcc from its PyPI release, with its errors
raised as oncemore's.

* `load`: the captions of a .scc file, or of subtitles (SubRip, WebVTT,
  ASS / SSA, a text script) sent as pop-on captions. Returns (schedule,
  notes).
* `inject_file`: writes a schedule into an MPEG-2 video stream, in place.

Captions are NTSC only (line 21 of a 525-line picture), on 29.97 fps
video, field 1 (CC1).
"""

from ._vendor.dvdcc import captions
from ._vendor.dvdcc.errors import CaptionError
from .errors import ProjectError


def load(path, offset=0.0, position="bottom", standard="NTSC"):
    try:
        return captions.load(path, offset, position, standard)
    except CaptionError as e:
        raise ProjectError(e.message) from e


def inject_file(path, schedule):
    return captions.inject_file(path, schedule)
