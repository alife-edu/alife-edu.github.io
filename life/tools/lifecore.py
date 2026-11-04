"""lifecore.py — the small Game of Life toolkit shared by every tool in this folder.

Patterns are Python frozensets of (x, y) cells, which makes them easy to compare, hash,
shift and combine (`a | b` is "both patterns together"). Two simulators are provided:

  run_cells(cells, n)  — sparse and exact on the infinite plane. Fine for small patterns.
  step(grid)           — one generation of a numpy 0/1 array whose outer ring is held dead,
                         the same rule the web page's engine uses. Fast for big patterns.

Rule: B3/S23. A dead cell with exactly 3 live neighbours is born; a live cell with 2 or 3
live neighbours survives; every other cell is dead next generation.
"""
from collections import Counter
import numpy as np

# ── building and moving patterns ────────────────────────────────────────────────────────

def parse(s):
    """Text picture -> cells. 'O' (or * o #) is alive, anything else dead."""
    return frozenset((x, y) for y, row in enumerate(s.strip().split('\n'))
                     for x, ch in enumerate(row.strip()) if ch in 'O*o#')

def minpos(cells):
    return (min(x for x, y in cells), min(y for x, y in cells))

def norm(cells):
    """Shift a pattern so its bounding box starts at (0, 0) — its shape, ignoring position."""
    if not cells:
        return frozenset()
    mx, my = minpos(cells)
    return frozenset((x - mx, y - my) for x, y in cells)

def shift(cells, dx, dy):
    return frozenset((x + dx, y + dy) for x, y in cells)

# The 8 symmetries of the square grid, as matrices (a, b, c, d): (x, y) -> (ax+by, cx+dy).
# The first four are rotations, the last four reflections. Life's rule treats all eight the
# same, so any reaction found once can be used in all eight orientations.
SYMS = [(1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0),
        (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0)]

def tf(cells, s):
    a, b, c, d = s
    return frozenset((a * x + b * y, c * x + d * y) for x, y in cells)

def tfv(v, s):
    a, b, c, d = s
    return (a * v[0] + b * v[1], c * v[0] + d * v[1])

# ── simulation ──────────────────────────────────────────────────────────────────────────

def run_cells(cells, gens):
    """Exact Life on the infinite plane: count neighbours of live cells, apply B3/S23."""
    cur = set(cells)
    for _ in range(gens):
        cnt = Counter((x + i, y + j) for x, y in cur
                      for i in (-1, 0, 1) for j in (-1, 0, 1) if i or j)
        cur = {c for c, n in cnt.items() if n == 3 or (n == 2 and c in cur)}
    return frozenset(cur)

def step(g):
    """One generation of a numpy 0/1 grid. The outer ring is forced dead afterwards, so the
    grid is a closed box (np.roll's wrap-around only ever brings in that dead ring)."""
    n = sum(np.roll(np.roll(g, i, 0), j, 1) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0))
    out = ((n == 3) | (g & (n == 2))).astype(np.uint8)
    out[0, :] = out[-1, :] = 0
    out[:, 0] = out[:, -1] = 0
    return out

def to_grid(cells, W, H, ox=0, oy=0):
    """Cells -> numpy array of size H x W, with cell (x, y) at column x+ox, row y+oy."""
    g = np.zeros((H, W), np.uint8)
    for x, y in cells:
        X, Y = x + ox, y + oy
        if 0 < X < W - 1 and 0 < Y < H - 1:
            g[Y, X] = 1
    return g

def from_grid(g, ox=0, oy=0):
    ys, xs = np.nonzero(g)
    return frozenset((int(x) - ox, int(y) - oy) for x, y in zip(xs, ys))

# ── recognising objects ─────────────────────────────────────────────────────────────────

GLIDER_SE = parse(""".O.
..O
OOO""")                                     # travels one cell right and down every 4 generations

GLIDER_SHAPES = {}                          # every glider shape -> (direction, phase)
for _s in SYMS[:4]:
    _g, _d = tf(GLIDER_SE, _s), tfv((1, 1), _s)
    for _p in range(4):
        GLIDER_SHAPES[norm(_g)] = (_d, _p)
        _g = run_cells(_g, 1)

def components(cells, gap=2):
    """Split a pattern into clusters: cells within Chebyshev distance `gap` are joined."""
    cells = list(cells)
    idx = {c: i for i, c in enumerate(cells)}
    parent = list(range(len(cells)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for (x, y), i in idx.items():
        for dx in range(-gap, gap + 1):
            for dy in range(-gap, gap + 1):
                j = idx.get((x + dx, y + dy))
                if j is not None:
                    a, b = find(i), find(j)
                    if a != b:
                        parent[a] = b
    groups = {}
    for c, i in idx.items():
        groups.setdefault(find(i), set()).add(c)
    return [frozenset(g) for g in groups.values()]

def classify(cells):
    """-> (gliders [(cells, direction)], still lifes [cells], everything else [cells])."""
    gl, st, ot = [], [], []
    for comp in components(cells, 2):
        n = norm(comp)
        if n in GLIDER_SHAPES:
            gl.append((comp, GLIDER_SHAPES[n][0]))
        elif run_cells(comp, 1) == comp:
            st.append(comp)
        else:
            ot.append(comp)
    return gl, st, ot

def dilate(cells, k):
    """Every cell within Chebyshev distance k of the pattern."""
    return frozenset((x + i, y + j) for x, y in cells for i in range(-k, k + 1) for j in range(-k, k + 1))

def rle(cells):
    """Cells -> RLE text, the standard pattern format of Golly and the LifeWiki."""
    import re
    mx, my = minpos(cells)
    W = max(x for x, y in cells) - mx + 1
    H = max(y for x, y in cells) - my + 1
    def enc(row):
        out, i = '', 0
        while i < len(row):
            j = i
            while j < len(row) and row[j] == row[i]:
                j += 1
            out += (str(j - i) if j - i > 1 else '') + row[i]; i = j
        return out
    rows = [enc(''.join('o' if (x + mx, y + my) in cells else 'b' for x in range(W)).rstrip('b'))
            for y in range(H)]
    body = re.sub(r'\${2,}', lambda m: f"{len(m.group(0))}$", '$'.join(rows) + '!')
    return f"x = {W}, y = {H}, rule = B3/S23\n" + '\n'.join(body[i:i + 70] for i in range(0, len(body), 70))
