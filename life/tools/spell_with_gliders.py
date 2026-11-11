"""spell_with_gliders.py — step 2 of the ALIFE·EDU scene.

Goal: text drawn in 2 × 2 blocks ("pixels" 5 cells apart, in a 3 × 5 font), where every
block is made by two gliders that collide (find_block_syntheses.py), and every glider
starts OUTSIDE the visible 100 × 80 field. Watching it, you see gliders stream in from all
sides and write the words.

Method, for each pixel in a chosen order (ALIFE left to right, then EDU top to bottom):

  1. Try each of the block-making collisions, in all 8 orientations, centred on the pixel.
     Discard it if its envelope leaves the field or comes within 1 cell of a finished block.
  2. Back both gliders up along their paths until they are outside the field. That fixes
     the earliest generation T at which the collision can happen; arrivals are also kept
     at least 8 generations apart so the text appears in order.
  3. Check it against the SPACE-TIME HISTORY of everything already placed: for every
     generation t, every cell of the new pair must be at Chebyshev distance ≥ 3 from every
     live cell of the existing pattern. Two cells that far apart have no neighbour in
     common, so neither can influence the other that generation; if that holds at every
     generation, the pair evolves exactly as it would alone, and so does everything else.
     (Gliders may cross the same spot at different times; that's fine.)
     Exception: in the last 16 generations before the collision, blocks within 14 cells
     (the letter's own pixels) are allowed closer, and that final approach is instead
     simulated exactly together with those blocks.
  4. If no collision fits, try arriving 4, 8, … up to 240 generations later.
  5. Add the pair's trajectory to the history and move to the next pixel.

The build order matters, because a glider can't fly through finished letters: writing
columns left to right lets gliders arrive from the right, where nothing exists yet, and
building EDU from its top row down lets its gliders arrive from below.

Finally the whole pattern (about 140 gliders) is simulated from generation 0 on a grid
large enough to hold every starting glider, and the result must be exactly the text.

Output: out/spell_<LINES>_<order>_<seed>.pkl.   Runtime: about 6 minutes for ALIFE/EDU.
"""
import argparse, os, pickle, random, time
from lifecore import *

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 100, 80
PITCH = 5            # pixel spacing: a 2 × 2 block plus 3 empty cells
LINE_GAP = 2         # empty pixel rows between lines of text
DT = 8               # minimum generations between successive collisions
MAXDELAY = 240
APPROACH = 16
BLK = parse("OO\nOO")

FONT = {             # a 3 × 5 pixel font, just the letters we need
    'A': [".#.", "#.#", "###", "#.#", "#.#"],
    'L': ["#..", "#..", "#..", "#..", "###"],
    'I': ["#", "#", "#", "#", "#"],
    'F': ["###", "#..", "##.", "#..", "#.."],
    'E': ["###", "#..", "##.", "#..", "###"],
    'D': ["##.", "#.#", "#.#", "#.#", "##."],
    'U': ["#.#", "#.#", "#.#", "#.#", "###"],
}

def layout(lines):
    """Pixel positions (x, y, letter index, line index), each line centred."""
    targets, nl = [], len(lines)
    hpx = (5 * nl + LINE_GAP * (nl - 1) - 1) * PITCH + 2
    y0, li = (H - hpx) // 2, 0
    for ln, word in enumerate(lines):
        cols = sum(len(FONT[c][0]) for c in word) + len(word) - 1
        x0 = (W - ((cols - 1) * PITCH + 2)) // 2
        yb, cx = y0 + ln * (5 + LINE_GAP) * PITCH, 0
        for ch in word:
            for r, row in enumerate(FONT[ch]):
                for c, v in enumerate(row):
                    if v == '#':
                        targets.append((x0 + (cx + c) * PITCH, yb + r * PITCH, li, ln))
            cx += len(FONT[ch][0]) + 1; li += 1
    return targets

def load_collisions():
    """Every block-making collision in all 8 orientations, with its isolated evolution."""
    SYN = pickle.load(open(os.path.join(HERE, 'out', 'block_syntheses.pkl'), 'rb'))
    C, seen = [], set()
    for s in sorted(SYN, key=lambda s: s['t']):
        for sym in SYMS:
            ox, oy = minpos(tf(BLK, sym))
            a = shift(tf(s['a'], sym), -ox, -oy); b = shift(tf(s['b'], sym), -ox, -oy)
            if (a, b) in seen:
                continue
            seen.add((a, b))
            evo, cur = [a | b], a | b
            for _ in range(s['t'] + 2):
                cur = run_cells(cur, 1); evo.append(cur)
            C.append(dict(a=a, b=b, da=tfv(s['da'], sym), db=tfv(s['db'], sym), t=s['t'] + 2, evo=evo,
                          env=frozenset().union(*evo),
                          ph_a=[run_cells(a, r) for r in range(4)], ph_b=[run_cells(b, r) for r in range(4)]))
    return C

def in_view(cells, m=2):
    return any(-m <= x < W + m and -m <= y < H + m for x, y in cells)

def steps_out(g, d):
    """Diagonal steps to back a glider up until it is entirely outside the field."""
    k = 0
    while in_view(shift(g, -k * d[0], -k * d[1])):
        k += 1
    return k

def pair_at(c, bx, by, T, t):
    """Cells of a placed pair at generation t, if its collision starts at generation T.
    Before T the two gliders are just translated copies of themselves (a glider moves one
    diagonal cell every 4 generations, cycling through 4 phases); after T, its recorded
    isolated evolution."""
    tau = t - T
    if tau >= 0:
        return shift(c['evo'][min(tau, len(c['evo']) - 1)], bx, by)
    m = (-tau + 3) // 4; r = tau + 4 * m
    return (shift(c['ph_a'][r], bx - m * c['da'][0], by - m * c['da'][1]) |
            shift(c['ph_b'][r], bx - m * c['db'][0], by - m * c['db'][1]))

NB = [(i, j) for i in range(-2, 3) for j in range(-2, 3)]
def clear(c, bx, by, T, hist, near):
    """Step 3 of the method (see the top of this file)."""
    tend = max(T + c['t'], len(hist) - 1)
    ts = T - APPROACH
    for t in range(0, tend + 1):
        h = hist[min(t, len(hist) - 1)]
        if not h:
            continue
        if t >= ts and near:
            h = h - near
        for x, y in pair_at(c, bx, by, T, t):
            for i, j in NB:
                if (x + i, y + j) in h:
                    return False
    if near:
        cur = near | pair_at(c, bx, by, T, ts)
        for _ in range(APPROACH + c['t'] + 6):
            cur = run_cells(cur, 1)
        if cur != near | shift(BLK, bx, by):
            return False
    return True

def build(order, C):
    hist = [frozenset()]          # hist[t] = live cells of everything placed so far, at gen t
    starts, blocks, log = [], [], []
    tprev, t0 = -DT, time.time()
    for (bx, by, li, ln) in order:
        others = frozenset().union(*blocks) if blocks else frozenset()
        od = dilate(others, 1) if others else frozenset()
        near = frozenset().union(*[b for b in blocks
                                   if max(abs(minpos(b)[0] - bx), abs(minpos(b)[1] - by)) <= 14]) if blocks else frozenset()
        pool = []
        for c in C:
            env = shift(c['env'], bx, by)
            if not all(0 <= x < W and 0 <= y < H for x, y in env) or env & od:
                continue
            kmin = max(steps_out(shift(c['a'], bx, by), c['da']), steps_out(shift(c['b'], bx, by), c['db']))
            T0 = max(4 * kmin, ((tprev + DT + 3) // 4) * 4)
            pool.append((T0 + random.random() * 4, c, T0))
        pool.sort(key=lambda p: p[0])
        got = None
        for extra in range(0, MAXDELAY + 1, 4):
            for _, c, T0 in pool:
                if clear(c, bx, by, T0 + extra, hist, near):
                    got = (c, T0 + extra); break
            if got:
                break
        if not got:
            print('stuck at pixel', bx, by, 'after', len(log), 'blocks', flush=True)
            return None
        c, T = got
        tdone = T + c['t']
        L, last = max(len(hist), tdone + 1), hist[-1]
        hist = [(hist[t] if t < len(hist) else last) | pair_at(c, bx, by, T, t) for t in range(L)]
        starts.append(pair_at(c, bx, by, T, 0))
        blocks.append(shift(BLK, bx, by)); tprev = T
        log.append(dict(x=bx, y=by, letter=li, line=ln, t=tdone))
        print(f'{len(log):3d} pixel ({bx:2d},{by:2d})  collision at gen {T:4d}, block done {tdone:4d}  ({time.time() - t0:.0f}s)', flush=True)
    return dict(start=frozenset().union(*starts), blocks=blocks, log=log, end=len(hist) - 1 + 8)

def sim(cells, gens):
    xs = [x for x, y in cells]; ys = [y for x, y in cells]
    P = 4; ox = -min(min(xs), 0) + P; oy = -min(min(ys), 0) + P
    g = to_grid(cells, max(max(xs), W) + ox + P + 1, max(max(ys), H) + oy + P + 1, ox, oy)
    for _ in range(gens):
        g = step(g)
    return from_grid(g, ox, oy)

def make_order(targets, kind):
    t = targets[:]
    if kind == 'lines':          # first line by columns, left to right; later lines by rows, top down
        t.sort(key=lambda p: (p[3], p[0] if p[3] == 0 else p[1], p[1] if p[3] == 0 else p[0]))
    elif kind == 'lines_cols':
        t.sort(key=lambda p: (p[3], p[0], p[1]))
    elif kind == 'cols':
        t.sort(key=lambda p: (p[0], p[1]))
    return t

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--lines', default='ALIFE/EDU', help='text, lines separated by /')
    ap.add_argument('--order', default='lines', choices=['lines', 'lines_cols', 'cols'])
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    random.seed(a.seed)
    lines = a.lines.split('/')
    targets = layout(lines)
    C = load_collisions()
    print(len(targets), 'pixels;', len(C), 'collision placements to choose from')
    res = build(make_order(targets, a.order), C)
    if not res:
        return
    fin = sim(res['start'], res['end'])
    ok = fin == frozenset().union(*res['blocks']) and run_cells(fin, 1) == fin
    print('full simulation matches the text:', ok, '|', len(res['start']) // 5, 'gliders, at rest by generation', res['end'])
    if ok:
        out = os.path.join(HERE, 'out', f'spell_{"_".join(lines)}_{a.order}_{a.seed}.pkl')
        pickle.dump(res, open(out, 'wb'))
        print('saved', out)

if __name__ == '__main__':
    main()
