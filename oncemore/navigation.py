"""Automatic up/down/left/right navigation between menu buttons.

Each button is a rectangle (x0, y0, x1, y1). For a direction we look at the
buttons lying entirely on that side (e.g. for "down": top edge at or below
our bottom edge) and pick the closest by centre distance, where sideways
distance counts double (so "down" prefers the button straight below over one
diagonally closer). When nothing lies in that direction we wrap
around to the far side, but only among buttons in the same column (up/down)
or row (left/right); otherwise the button keeps the focus.

Explicit `nav` entries on a button always win.
"""

DIRECTIONS = ("up", "down", "left", "right")


def _center(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def _overlap(a0, a1, b0, b1):
    return min(a1, b1) > max(a0, b0)


def _forward(direction, src, dst):
    """(distance along direction, sideways distance) or None if not ahead."""
    beyond = {"up": dst[3] <= src[1], "down": dst[1] >= src[3],
              "left": dst[2] <= src[0], "right": dst[0] >= src[2]}[direction]
    if not beyond:
        return None
    (sx, sy), (dx, dy) = _center(src), _center(dst)
    along = {"up": sy - dy, "down": dy - sy, "left": sx - dx, "right": dx - sx}[direction]
    side = abs(dx - sx) if direction in ("up", "down") else abs(dy - sy)
    return along, side


def _neighbour(direction, i, rects):
    best = None
    for j, r in enumerate(rects):
        if j == i:
            continue
        f = _forward(direction, rects[i], r)
        if f is None:
            continue
        score = (f[0] + 2 * f[1], f[1], j)
        if best is None or score < best[0]:
            best = (score, j)
    if best is not None:
        return best[1]
    # wrap around within the same column / row
    src = rects[i]
    vertical = direction in ("up", "down")
    cands = []
    for j, r in enumerate(rects):
        if j == i:
            continue
        aligned = _overlap(src[0], src[2], r[0], r[2]) if vertical else \
            _overlap(src[1], src[3], r[1], r[3])
        if not aligned:
            continue
        (sx, sy), (cx, cy) = _center(src), _center(r)
        # going "down" past the bottom wraps to the top-most, etc.
        key = {"down": cy, "up": -cy, "right": cx, "left": -cx}[direction]
        side = abs(cx - sx) if vertical else abs(cy - sy)
        cands.append((key, side, j))
    if cands:
        return min(cands)[2]
    return i


def compute(buttons):
    """`buttons`: list of (id, (x0, y0, x1, y1), overrides dict).

    Returns {id: {"up": id, "down": id, "left": id, "right": id}}.
    """
    ids = [b[0] for b in buttons]
    rects = [b[1] for b in buttons]
    result = {}
    for i, (bid, _, overrides) in enumerate(buttons):
        nav = {}
        for d in DIRECTIONS:
            if overrides and d in overrides:
                nav[d] = overrides[d]
            else:
                nav[d] = ids[_neighbour(d, i, rects)]
        result[bid] = nav
    return result
