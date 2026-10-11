#!/usr/bin/env python3
"""Update oncemore's copy of vtskit from a checkout of its repository.

    python tools/vendor_vtskit.py ../vtskit

copies vtskit/*.py of that checkout (its tests stay upstream) into
oncemore/_vendor/vtskit, replaces COPYING.LESSER, and writes UPSTREAM with
the checkout's commit. The checkout must be clean and on a commit that its
origin has, so that UPSTREAM names a commit anyone can fetch. Run
oncemore's tests afterwards.
"""

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(os.path.dirname(HERE), "oncemore", "_vendor", "vtskit")


def git(checkout, *args):
    return subprocess.run(["git", "-C", checkout, *args], check=True, capture_output=True, text=True).stdout.strip()


def main(argv):
    if len(argv) != 2 or not os.path.isdir(os.path.join(argv[1], "vtskit")):
        print(__doc__, file=sys.stderr)
        return 2
    checkout = os.path.abspath(argv[1])
    if git(checkout, "status", "--porcelain", "--", "vtskit", "COPYING.LESSER"):
        print("the vtskit checkout has uncommitted changes in vtskit/ or COPYING.LESSER", file=sys.stderr)
        return 1
    commit = git(checkout, "rev-parse", "HEAD")
    branch = git(checkout, "rev-parse", "--abbrev-ref", "HEAD")
    remote = git(checkout, "branch", "-r", "--contains", commit)
    if not remote:
        print(f"commit {commit[:12]} is not on any remote branch: push it first", file=sys.stderr)
        return 1
    kept = {"UPSTREAM"}
    for name in os.listdir(VENDOR):
        if name not in kept and name != "__pycache__":
            path = os.path.join(VENDOR, name)
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    copied = []
    for name in sorted(os.listdir(os.path.join(checkout, "vtskit"))):
        if name.endswith(".py"):
            shutil.copy(os.path.join(checkout, "vtskit", name), os.path.join(VENDOR, name))
            copied.append(name)
    shutil.copy(os.path.join(checkout, "COPYING.LESSER"), os.path.join(VENDOR, "COPYING.LESSER"))
    where = "main" if branch == "main" else branch
    with open(os.path.join(VENDOR, "UPSTREAM"), "w", encoding="utf-8") as f:
        f.write("vtskit, https://github.com/kajisho5/vtskit (LGPL-3.0-or-later, see COPYING.LESSER)\n"
                f"copied from commit {commit} ({where})\n"
                "the package vtskit/ only; its tests stay upstream\n")
    print(f"copied {len(copied)} modules from vtskit {commit[:12]} ({where}) into {os.path.relpath(VENDOR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
