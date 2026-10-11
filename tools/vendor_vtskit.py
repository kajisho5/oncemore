#!/usr/bin/env python3
"""Update oncemore's copy of vtskit, from PyPI or from a checkout of its
repository.

    python tools/vendor_vtskit.py --pypi 0.1.0
    python tools/vendor_vtskit.py --pypi            (the latest release)
    python tools/vendor_vtskit.py ../vtskit

From PyPI: the release's wheel is downloaded, checked against the SHA-256
PyPI publishes for it, and its vtskit/*.py and COPYING.LESSER are copied;
UPSTREAM names the version and the wheel's digest.

From a checkout: vtskit/*.py of that checkout (its tests stay upstream) are
copied, and UPSTREAM names the checkout's commit. The checkout must be
clean and on a commit that its origin has, so that UPSTREAM names a commit
anyone can fetch.

Either way the copy goes into oncemore/_vendor/vtskit, replacing what is
there. Run oncemore's tests afterwards.
"""

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(os.path.dirname(HERE), "oncemore", "_vendor", "vtskit")
REPO = "https://github.com/kajisho5/vtskit"
PYPI = "https://pypi.org/pypi/vtskit"
HEADER = f"vtskit, {REPO} (LGPL-3.0-or-later, see COPYING.LESSER)\n"


def git(checkout, *args):
    return subprocess.run(["git", "-C", checkout, *args], check=True, capture_output=True, text=True).stdout.strip()


def _clear(vendor):
    for name in os.listdir(vendor):
        if name != "__pycache__":
            path = os.path.join(vendor, name)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)


def from_checkout(checkout, vendor=VENDOR):
    if git(checkout, "status", "--porcelain", "--", "vtskit", "COPYING.LESSER"):
        raise SystemExit("the vtskit checkout has uncommitted changes in vtskit/ or COPYING.LESSER")
    commit = git(checkout, "rev-parse", "HEAD")
    branch = git(checkout, "rev-parse", "--abbrev-ref", "HEAD")
    if not git(checkout, "branch", "-r", "--contains", commit):
        raise SystemExit(f"commit {commit[:12]} is not on any remote branch: push it first")
    _clear(vendor)
    copied = []
    for name in sorted(os.listdir(os.path.join(checkout, "vtskit"))):
        if name.endswith(".py"):
            shutil.copy(os.path.join(checkout, "vtskit", name), os.path.join(vendor, name))
            copied.append(name)
    shutil.copy(os.path.join(checkout, "COPYING.LESSER"), os.path.join(vendor, "COPYING.LESSER"))
    where = "main" if branch == "main" else branch
    with open(os.path.join(vendor, "UPSTREAM"), "w", encoding="utf-8") as f:
        f.write(HEADER + f"copied from commit {commit} ({where})\n"
                "the package vtskit/ only; its tests stay upstream\n")
    return f"copied {len(copied)} modules from vtskit {commit[:12]} ({where})"


def from_wheel(data, version, filename, vendor=VENDOR):
    """Copy the package and its licence out of a wheel's bytes."""
    digest = hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        modules = sorted(n for n in names if re.fullmatch(r"vtskit/[^/]+\.py", n))
        licence = [n for n in names if re.fullmatch(r"vtskit-[^/]+\.dist-info/(licenses/)?COPYING\.LESSER", n)]
        if not modules or "vtskit/__init__.py" not in modules or not licence:
            raise SystemExit(f"{filename}: no vtskit package or no COPYING.LESSER in it")
        init = z.read("vtskit/__init__.py").decode("utf-8")
        m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init, re.M)
        if not m or m[1] != version:
            raise SystemExit(f"{filename}: vtskit/__init__.py says {m and m[1]!r}, not {version!r}")
        _clear(vendor)
        for name in modules:
            with open(os.path.join(vendor, os.path.basename(name)), "wb") as f:
                f.write(z.read(name))
        with open(os.path.join(vendor, "COPYING.LESSER"), "wb") as f:
            f.write(z.read(licence[0]))
    with open(os.path.join(vendor, "UPSTREAM"), "w", encoding="utf-8") as f:
        f.write(HEADER + f"copied from PyPI vtskit {version} ({filename}, sha256 {digest})\n"
                "the package vtskit/ only; its tests stay upstream\n")
    return f"copied {len(modules)} modules from vtskit {version} on PyPI"


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def from_pypi(version=None, vendor=VENDOR):
    info = json.loads(_get(f"{PYPI}/{version}/json" if version else f"{PYPI}/json"))
    version = info["info"]["version"]
    wheels = [u for u in info["urls"] if u["packagetype"] == "bdist_wheel"]
    if not wheels:
        raise SystemExit(f"vtskit {version} has no wheel on PyPI")
    wheel = wheels[0]
    data = _get(wheel["url"])
    if hashlib.sha256(data).hexdigest() != wheel["digests"]["sha256"]:
        raise SystemExit(f"{wheel['filename']}: its SHA-256 is not the one PyPI publishes")
    return from_wheel(data, version, wheel["filename"], vendor)


def main(argv):
    args = argv[1:]
    if args[:1] == ["--pypi"] and len(args) <= 2:
        done = from_pypi(args[1] if len(args) == 2 else None)
    elif len(args) == 1 and os.path.isdir(os.path.join(args[0], "vtskit")):
        done = from_checkout(os.path.abspath(args[0]))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    print(f"{done} into {os.path.relpath(VENDOR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
