#!/usr/bin/env python3
"""Update oncemore's copy of one of its libraries (vtskit, udfkit, bdmvkit,
dvdcc), from PyPI or from a checkout of its repository.

    python tools/vendor.py udfkit --pypi 0.1.0
    python tools/vendor.py udfkit --pypi            (the latest release)
    python tools/vendor.py udfkit ../udfkit         (a checkout)

The libraries are worked on, tested and released in their own
repositories; oncemore takes a release (DECISIONS §105).

From PyPI: the release's wheel is downloaded, checked against the SHA-256
PyPI publishes for it and against the version inside it, and the package's
*.py and its licence files are copied; UPSTREAM names the version and the
wheel's digest.

From a checkout (for work not released yet): the package's *.py of that
checkout (its tests stay upstream) are copied, and UPSTREAM names the
checkout's commit. The checkout must be clean and on a commit that its
origin has, so that UPSTREAM names a commit anyone can fetch.

Either way the copy goes into oncemore/_vendor/<library>, replacing what is
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
VENDOR_ROOT = os.path.join(os.path.dirname(HERE), "oncemore", "_vendor")

# each library: its licence and the licence files that go with the copy
LIBRARIES = {
    "vtskit": ("LGPL-3.0-or-later", ["COPYING.LESSER"]),
    "udfkit": ("Apache-2.0", ["LICENSE", "NOTICE"]),
    "bdmvkit": ("LGPL-3.0-or-later", ["COPYING", "COPYING.LESSER"]),
    "dvdcc": ("Apache-2.0", ["LICENSE", "NOTICE"]),
}


def header(name):
    licence, files = LIBRARIES[name]
    return (f"{name}, https://github.com/kajisho5/{name} "
            f"({licence}, see {' and '.join(files)})\n")


def git(checkout, *args):
    return subprocess.run(["git", "-C", checkout, *args], check=True, capture_output=True, text=True).stdout.strip()


def _clear(vendor):
    os.makedirs(vendor, exist_ok=True)
    for entry in os.listdir(vendor):
        if entry != "__pycache__":
            path = os.path.join(vendor, entry)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)


def from_checkout(name, checkout, vendor=None):
    vendor = vendor or os.path.join(VENDOR_ROOT, name)
    files = LIBRARIES[name][1]
    if git(checkout, "status", "--porcelain", "--", name, *files):
        raise SystemExit(f"the {name} checkout has uncommitted changes in {name}/ or its licence")
    commit = git(checkout, "rev-parse", "HEAD")
    branch = git(checkout, "rev-parse", "--abbrev-ref", "HEAD")
    if not git(checkout, "branch", "-r", "--contains", commit):
        raise SystemExit(f"commit {commit[:12]} is not on any remote branch: push it first")
    _clear(vendor)
    copied = []
    for entry in sorted(os.listdir(os.path.join(checkout, name))):
        if entry.endswith(".py"):
            shutil.copy(os.path.join(checkout, name, entry), os.path.join(vendor, entry))
            copied.append(entry)
    for f in files:
        shutil.copy(os.path.join(checkout, f), os.path.join(vendor, f))
    where = "main" if branch == "main" else branch
    with open(os.path.join(vendor, "UPSTREAM"), "w", encoding="utf-8") as f:
        f.write(header(name) + f"copied from commit {commit} ({where})\n"
                f"the package {name}/ only; its tests stay upstream\n")
    return f"copied {len(copied)} modules from {name} {commit[:12]} ({where})"


def from_wheel(name, data, version, filename, vendor=None):
    """Copy the package and its licence files out of a wheel's bytes."""
    vendor = vendor or os.path.join(VENDOR_ROOT, name)
    files = LIBRARIES[name][1]
    digest = hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        modules = sorted(n for n in names if re.fullmatch(rf"{name}/[^/]+\.py", n))
        licences = {}
        for f in files:
            found = [n for n in names if re.fullmatch(rf"{name}-[^/]+\.dist-info/(licenses/)?{re.escape(f)}", n)]
            if found:
                licences[f] = found[0]
        if f"{name}/__init__.py" not in modules or len(licences) != len(files):
            missing = [f for f in files if f not in licences]
            raise SystemExit(f"{filename}: no {name} package, or no {', '.join(missing) or 'package'} in it")
        init = z.read(f"{name}/__init__.py").decode("utf-8")
        m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init, re.M)
        if not m or m[1] != version:
            raise SystemExit(f"{filename}: {name}/__init__.py says {m and m[1]!r}, not {version!r}")
        _clear(vendor)
        for n in modules:
            with open(os.path.join(vendor, os.path.basename(n)), "wb") as f:
                f.write(z.read(n))
        for f, n in licences.items():
            with open(os.path.join(vendor, f), "wb") as out:
                out.write(z.read(n))
    with open(os.path.join(vendor, "UPSTREAM"), "w", encoding="utf-8") as f:
        f.write(header(name) + f"copied from PyPI {name} {version} ({filename}, sha256 {digest})\n"
                f"the package {name}/ only; its tests stay upstream\n")
    return f"copied {len(modules)} modules from {name} {version} on PyPI"


def _get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def from_pypi(name, version=None, vendor=None):
    base = f"https://pypi.org/pypi/{name}"
    info = json.loads(_get(f"{base}/{version}/json" if version else f"{base}/json"))
    version = info["info"]["version"]
    wheels = [u for u in info["urls"] if u["packagetype"] == "bdist_wheel"]
    if not wheels:
        raise SystemExit(f"{name} {version} has no wheel on PyPI")
    wheel = wheels[0]
    data = _get(wheel["url"])
    if hashlib.sha256(data).hexdigest() != wheel["digests"]["sha256"]:
        raise SystemExit(f"{wheel['filename']}: its SHA-256 is not the one PyPI publishes")
    return from_wheel(name, data, version, wheel["filename"], vendor)


def main(argv):
    args = argv[1:]
    if not args or args[0] not in LIBRARIES:
        print(__doc__, file=sys.stderr)
        return 2
    name, rest = args[0], args[1:]
    if rest[:1] == ["--pypi"] and len(rest) <= 2:
        done = from_pypi(name, rest[1] if len(rest) == 2 else None)
    elif len(rest) == 1 and os.path.isdir(os.path.join(rest[0], name)):
        done = from_checkout(name, os.path.abspath(rest[0]))
    else:
        print(__doc__, file=sys.stderr)
        return 2
    print(f"{done} into {os.path.relpath(os.path.join(VENDOR_ROOT, name))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
