"""One DVD image per session, in batch (DECISIONS §140).

    oncemore batch <template project> sessions.csv -o <folder>

The template is an ordinary DVD project: its menus, titles and settings are
the same on every disc. The CSV has a header row and a row per session;
`{{column}}` in any text of the template (a title's source, its name, a menu
text, the disc label...) is replaced by that row's value. The `name` column
is required: the image is `<folder>/<name>.iso`. Paths stay relative to the
template's folder, so encoded menus are shared through its cache.

Every row is checked and its media probed before anything is encoded.
Each image is then built, read back and verified: its volume name is the
disc label,
and every VIDEO_TS file in the image (found through its ISO 9660 directory)
has the size and SHA-256 of the file that was authored. `manifest.json` in
the folder lists the images with their size and SHA-256. It is written
empty when the builds start and again after each image, so a stopped batch
still says what it finished.
"""

import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import struct

from . import __version__, build, discimage
from .errors import OncemoreError, ProjectError
from .project import build_project, read_json, resolve_project_path

SECTOR = 2048
MANIFEST = "manifest.json"
_PLACEHOLDER = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


def read_sessions(path):
    """The CSV's rows as dicts (header row first; UTF-8, with or without a BOM)."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            columns = [c.strip() for c in (reader.fieldnames or [])]
            rows = []
            for raw in reader:
                if None in raw:
                    raise OncemoreError(f"{path}: line {reader.line_num} has more fields "
                                        "than the header")
                if not any((v or "").strip() for v in raw.values()):
                    continue                                  # (a blank line)
                rows.append({k.strip(): (v or "").strip() for k, v in raw.items()})
    except FileNotFoundError:
        raise OncemoreError(f"{path}: file not found")
    except UnicodeDecodeError:
        raise OncemoreError(f"{path}: not UTF-8 text", hint="Save the CSV as UTF-8.")
    if "name" not in columns:
        raise OncemoreError(f"{path}: no `name` column",
                            hint="The header row names the columns; `name` is each image's "
                                 "file name (<name>.iso).")
    if not rows:
        raise OncemoreError(f"{path}: no sessions (only a header row)")
    return columns, rows


def fill(value, row):
    """`value` (the template's JSON) with each `{{column}}` replaced by the
    row's value. Returns (filled, columns missing from the row)."""
    missing = set()

    def text(s):
        def one(m):
            if m[1] not in row:
                missing.add(m[1])
                return m[0]
            return row[m[1]]
        return _PLACEHOLDER.sub(one, s)

    def walk(v):
        if isinstance(v, str):
            return text(v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(value), sorted(missing)


def plan(template, sessions, check_files=True):
    """Every row as a project, checked before anything is built. Returns
    [(row number, row, project)]; raises ProjectError naming each row's
    problems."""
    path = resolve_project_path(template)
    data = read_json(path)
    if not isinstance(data, dict):
        raise ProjectError(f"{path}: a project file is a JSON object")
    fmt = data.get("disc", {}).get("format", "dvd") if isinstance(data.get("disc"), dict) else "dvd"
    if fmt not in (None, "dvd"):
        raise OncemoreError(f"{path}: batch writes DVD images; this project is {fmt}",
                            hint='Use a DVD project (disc.format "dvd") as the template.')
    _, rows = read_sessions(sessions)
    out, issues, names = [], [], {}
    for n, row in enumerate(rows, 1):
        where = f"row {n} ({row['name'] or 'no name'})"
        if not _NAME.fullmatch(row["name"]):
            issues.append({"path": f"{where}.name", "message": "a file name of letters, digits, "
                           "'.', '_' and '-' (not starting with '.' or '-')"})
        elif row["name"].lower() in names:
            issues.append({"path": f"{where}.name",
                           "message": f"the same as row {names[row['name'].lower()]}"})
        else:
            names[row["name"].lower()] = n
        filled, missing = fill(data, row)
        if missing:
            issues.append({"path": where, "message": "the template uses "
                           + ", ".join(f"{{{{{c}}}}}" for c in missing) + ": no such column"})
            continue
        try:
            project = build_project(filled, path, check_files=check_files)
            if check_files:
                # (the media probed as the build will, on a copy: nothing encoded yet)
                build.inspect(build_project(filled, path), prepare=False)
        except ProjectError as e:
            issues += [{"path": f"{where}: {i['path']}", "message": i["message"]}
                       for i in e.issues] or [{"path": where, "message": e.message}]
            continue
        except OncemoreError as e:                   # (ffprobe cannot read a file...)
            issues.append({"path": where, "message": e.message})
            continue
        out.append((n, row, project))
    if issues:
        raise ProjectError(f"{sessions}: {len(issues)} problem(s) in the sessions", issues)
    return out


def _iso9660_files(f, directory="VIDEO_TS"):
    """{name: (sector, size)} of the files in a top-level directory of an
    image, read from its ISO 9660 Primary Volume Descriptor."""
    def records(sector, size):
        f.seek(sector * SECTOR)
        data, pos = f.read(size), 0
        while pos < len(data):
            n = data[pos]
            if n == 0:                                      # (rest of the sector is padding)
                pos = (pos // SECTOR + 1) * SECTOR
                continue
            r = data[pos:pos + n]
            ident = r[33:33 + r[32]]
            yield ident, struct.unpack_from("<I", r, 2)[0], struct.unpack_from("<I", r, 10)[0], \
                bool(r[25] & 2)
            pos += n

    f.seek(16 * SECTOR)
    pvd = f.read(SECTOR)
    if pvd[:6] != b"\x01CD001":
        raise OncemoreError("no ISO 9660 volume descriptor in the image")
    root = pvd[156:156 + 34]
    found = None
    for ident, sector, size, is_dir in records(struct.unpack_from("<I", root, 2)[0],
                                               struct.unpack_from("<I", root, 10)[0]):
        if is_dir and ident.decode("ascii", "replace").upper() == directory:
            found = (sector, size)
    if not found:
        raise OncemoreError(f"no {directory} folder in the image")
    files = {}
    for ident, sector, size, is_dir in records(*found):
        if not is_dir and ident not in (b"\x00", b"\x01"):
            files[ident.decode("ascii", "replace").split(";")[0].upper()] = (sector, size)
    return files


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify(image, disc_dir, label):
    """Read `image` back: its UDF volume name is `label`, and every file of
    `disc_dir`/VIDEO_TS is in it with the same size and SHA-256. Returns
    {"files", "video_ts_bytes"}; raises OncemoreError on any difference."""
    names = discimage.volume_names(image)
    if names["udf_volume"] != label:
        raise OncemoreError(f"{image}: volume name {names['udf_volume']!r}, not {label!r}")
    if os.path.getsize(image) % SECTOR:
        raise OncemoreError(f"{image}: not a whole number of 2048-byte sectors")
    src = os.path.join(disc_dir, "VIDEO_TS")
    want = sorted(os.listdir(src))
    total = 0
    with open(image, "rb") as f:
        found = _iso9660_files(f)
        if sorted(found) != [w.upper() for w in want]:
            raise OncemoreError(f"{image}: VIDEO_TS holds {', '.join(sorted(found))}, "
                                f"not {', '.join(want)}")
        for name in want:
            sector, size = found[name.upper()]
            path = os.path.join(src, name)
            if size != os.path.getsize(path):
                raise OncemoreError(f"{image}: VIDEO_TS/{name} is {size} bytes in the image, "
                                    f"{os.path.getsize(path)} authored")
            h, left = hashlib.sha256(), size
            f.seek(sector * SECTOR)
            while left:
                block = f.read(min(left, 1 << 20))
                if not block:
                    raise OncemoreError(f"{image}: VIDEO_TS/{name} runs past the image's end")
                h.update(block)
                left -= len(block)
            if h.hexdigest() != _sha256_file(path):
                raise OncemoreError(f"{image}: VIDEO_TS/{name} differs from the authored file")
            total += size
    return {"files": len(want), "video_ts_bytes": total}


def _write_manifest(path, manifest):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def run(template, sessions, out_dir, reporter, fast=False, cache=True):
    """Build, verify and list one image per session. Returns the manifest."""
    jobs = plan(template, sessions)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = os.path.join(out_dir, MANIFEST)
    manifest = {"oncemore": __version__,
                "created": datetime.datetime.now(datetime.timezone.utc)
                                   .replace(microsecond=0).isoformat(),
                "template": resolve_project_path(template),
                "sessions": os.path.abspath(sessions),
                "images": []}
    _write_manifest(manifest_path, manifest)          # (no earlier run's list stays)
    warnings = []
    for k, (n, row, project) in enumerate(jobs, 1):
        name = row["name"]
        reporter.step("batch", f"Session {k} of {len(jobs)}: {name}", item=name)
        image = os.path.join(out_dir, f"{name}.iso")
        build_dir = os.path.join(out_dir, f".{name}.oncemore-build")
        try:
            res = build.build_iso(project, image, reporter, fast=fast, keep_work=True,
                                  iso_tool="builtin", build_dir=build_dir, cache=cache)
            reporter.step("verify", f"Verifying {name}.iso", item=name)
            checked = verify(image, os.path.join(build_dir, "disc"), project.disc.label)
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)
        warnings += [f"{name}: {w}" for w in res.get("warnings", [])]   # (reported by the build)
        manifest["images"].append({
            "row": n, "name": name, "image": os.path.basename(image),
            "label": project.disc.label, "bytes": os.path.getsize(image),
            "sha256": _sha256_file(image), "titles": len(project.titles),
            "verified": checked})
        _write_manifest(manifest_path, manifest)
    return {"manifest": manifest_path, "images": manifest["images"], "warnings": warnings}
