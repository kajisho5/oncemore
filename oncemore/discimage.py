"""Disc images: udfkit's writers (DECISIONS §106), copied into
oncemore/_vendor/udfkit from its PyPI release, with their errors raised as
oncemore's.

* `write_dvd`: a DVD-Video image (UDF 1.02 + ISO 9660), VIDEO_TS files where
  their IFO files say; `shift` moves VIDEO_TS for the layer break.
* `plan_dvd`: where write_dvd would put things, without writing.
* `write_bluray`: a Blu-ray image (UDF 2.50 with a metadata partition).
* `volume_names`: the volume names an image carries.
"""

import contextlib

from ._vendor.udfkit import bluray, dvd, info
from ._vendor.udfkit.errors import UdfError
from .errors import OncemoreError


@contextlib.contextmanager
def _as_oncemore():
    try:
        yield
    except UdfError as e:
        raise OncemoreError(str(e)) from e


def write_dvd(src_dir, out_path, label, **kw):
    with _as_oncemore():
        return dvd.write_image(src_dir, out_path, label, **kw)


def plan_dvd(src_dir):
    with _as_oncemore():
        return dvd.plan_image(src_dir)


def write_bluray(src_dir, out_path, label, **kw):
    with _as_oncemore():
        return bluray.write_image(src_dir, out_path, label, **kw)


def volume_names(path):
    with _as_oncemore():
        return info.volume_names(path)
