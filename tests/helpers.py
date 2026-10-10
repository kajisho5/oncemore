import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*args, cwd=None, env=None, timeout=900):
    """Run `python -m oncemore ...`; return (returncode, stdout, stderr)."""
    full_env = dict(os.environ)
    full_env["PYTHONPATH"] = ROOT + os.pathsep + full_env.get("PYTHONPATH", "")
    if env:
        full_env.update(env)
    p = subprocess.run([sys.executable, "-m", "oncemore"] + list(args), cwd=cwd or ROOT,
                       env=full_env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def json_lines(text):
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def have(*names):
    return all(shutil.which(n) for n in names)


def read_rgba_png(path):
    """Pixels of an 8-bit RGBA / RGB PNG (as spuunmux writes them):
    (width, height, [(r, g, b, a), ...]). Stdlib only."""
    import struct
    import zlib
    with open(path, "rb") as f:
        data = f.read()
    pos, idat, w = 8, b"", None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if kind == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", body[:10])
            assert depth == 8 and ctype in (2, 6), (depth, ctype)
            bpp = 4 if ctype == 6 else 3
        elif kind == b"IDAT":
            idat += body
        pos += 12 + n
    raw, stride, prev, out = zlib.decompress(idat), w * bpp, bytearray(w * bpp), []
    for y in range(h):
        f, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a) & 255
            elif f == 2:
                line[i] = (line[i] + b) & 255
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += [tuple(line[i:i + bpp]) + ((255,) if bpp == 3 else ()) for i in range(0, stride, bpp)]
        prev = line
    return w, h, out
