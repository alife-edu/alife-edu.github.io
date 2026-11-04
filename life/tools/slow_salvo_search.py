"""slow_salvo_search.py — EXPERIMENTAL: build a letter from one block with a slow salvo.

The ALIFE·EDU scene uses gliders from every direction, timed to meet in pairs. The Life
community's harder, classic challenge is the SLOW SALVO: every glider comes from the same
direction, one at a time, and each reaction is allowed to settle completely before the next
glider arrives, so the exact timing between gliders doesn't matter. It's conjectured that
anything glider-constructible can be built this way starting from a single block (LifeWiki,
"Salvo"); Adam P. Goucher's slmake compiles such recipes for real constructions.

This script searches for one: gliders travelling SE (arriving from the NW) that turn a
single block into a letter made of blocks 5 cells apart (an "A" by default).

  * State: the settled pattern between gliders. We allow period-2 debris (blinkers etc.)
    as well as still lifes: a "p2 slow salvo". A lone block has only three clean outcomes
    when everything must be still (it moves, it becomes a honey farm, or it disappears),
    so allowing p2 helps a lot.
  * Move: one glider on any lane that can reach the pattern, in any of its 4 phases. The
    reaction is run for 288 generations; it must settle, nothing may reach the edge of the
    working box, and any glider it throws off must not head NW, back into the stream.
    All candidate shots at a pattern are simulated together as one numpy batch.
  * Search: beam search. Each pattern is scored by how many target blocks it already has
    (the letter may land anywhere, so we score the best-fitting position), minus a penalty
    for leftover debris and its distance from the blocks still missing. The best BEAM
    patterns are kept at each depth (one depth = one more glider).

Status: this is an open experiment. Our first runs placed 3 of the A's 10 blocks within
about 10 gliders; finishing a whole letter may need a much larger beam, a better score,
or the reaction libraries real slow-salvo compilers use. Results are saved as it goes.

Usage:  python slow_salvo_search.py --beam 200 --workers 24 --depth 150
Output: out/slow_salvo_<tag>.pkl (best so far) and out/slow_salvo_<tag>_solved.pkl.
"""
import argparse, os, pickle, random, time
from multiprocessing import Pool
import numpy as np
from lifecore import *

HERE = os.path.dirname(os.path.abspath(__file__))
PITCH = 5
BLOCK = parse("OO\nOO")
MAXGEN = 288
M = 26                                      # empty margin around the working box
PH = [run_cells(GLIDER_SE, p) for p in range(4)]
TPOS = []                                   # set in main()

def bstep(B):
    """One generation for a whole batch of grids at once. The outer two rings are cleared
    every generation, so a glider that leaves the box simply disappears."""
    n = (B[:, :-2, :-2] + B[:, :-2, 1:-1] + B[:, :-2, 2:] + B[:, 1:-1, :-2] + B[:, 1:-1, 2:]
         + B[:, 2:, :-2] + B[:, 2:, 1:-1] + B[:, 2:, 2:])
    c = B[:, 1:-1, 1:-1]
    out = np.zeros_like(B)
    out[:, 1:-1, 1:-1] = (n == 3) | ((c == 1) & (n == 2))
    out[:, :2, :] = 0; out[:, -2:, :] = 0; out[:, :, :2] = 0; out[:, :, -2:] = 0
    return out

def place(state, lane, ph):
    """A SE-travelling glider on `lane` (x − y of its corner), just up-left of the pattern."""
    s0 = min(x + y for x, y in state)
    g = PH[ph]; mx, my = minpos(g)
    S = s0 - 10
    if (S - lane) % 2: S -= 1
    return shift(g, (lane + S) // 2 - mx, (S - lane) // 2 - my)

def expand(state):
    """Fire every possible glider at `state`; return the shots that settle cleanly."""
    xs = [x for x, y in state]; ys = [y for x, y in state]
    lanes = sorted({x - y for x, y in state})
    shots = [(L, ph) for L in range(lanes[0] - 5, lanes[-1] + 6) for ph in range(4)]
    gl = [place(state, L, ph) for L, ph in shots]
    allx = xs + [x for g in gl for x, y in g]; ally = ys + [y for g in gl for x, y in g]
    x0, y0 = min(allx) - M, min(ally) - M
    w, h = max(allx) - x0 + M + 1, max(ally) - y0 + M + 1
    B = np.zeros((len(shots), h, w), np.uint8)
    for x, y in state: B[:, y - y0, x - x0] = 1
    for i, g in enumerate(gl):
        for x, y in g: B[i, y - y0, x - x0] = 1
    for _ in range(MAXGEN):
        B = bstep(B)
    ok = (B == bstep(bstep(B))).reshape(len(shots), -1).all(1)     # period 1 or 2 now
    out = []
    for i in np.nonzero(ok)[0]:
        yy, xx = np.nonzero(B[i])
        if len(yy) == 0 or len(yy) > 160: continue
        res = frozenset((int(x) + x0, int(y) + y0) for x, y in zip(xx, yy))
        if res == state or run_cells(res, 1) == state: continue          # the glider missed
        if xx.min() < 8 or yy.min() < 8 or xx.max() > w - 9 or yy.max() > h - 9: continue
        out.append((shots[i], gl[i], res))
    return out

def escaped_ok(args):
    """Re-run one shot exactly, without the vanishing edge: no glider may head NW, and the
    debris must match what the batch run found."""
    state, glider, res = args
    cur = state | glider
    for _ in range(MAXGEN):
        cur = run_cells(cur, 1)
    gl, st, ot = classify(cur)
    if any(d == (-1, -1) for _, d in gl): return False
    rest = frozenset().union(*(st + ot)) if (st or ot) else frozenset()
    return rest == res

def score(state):
    comps = components(state, 1)
    bl = [minpos(c) for c in comps if len(c) == 4 and norm(c) == BLOCK]
    bset, best = set(bl), (0, (0, 0))
    for bx, by in bl:                                   # best position for the letter
        for tx, ty in TPOS:
            off = (bx - tx, by - ty)
            m = sum((px + off[0], py + off[1]) in bset for px, py in TPOS)
            if m > best[0]: best = (m, off)
    m, off = best
    want = set((px + off[0], py + off[1]) for px, py in TPOS)
    junk = [c for c in comps if not (len(c) == 4 and norm(c) == BLOCK and minpos(c) in want)]
    missing = [p for p in want if p not in bset]
    s = 12 * m - 0.12 * sum(len(c) for c in junk)
    for c in junk:                                      # debris should sit where blocks are missing
        cx = sum(x for x, y in c) / len(c); cy = sum(y for x, y in c) / len(c)
        s -= 0.15 * (min(abs(cx - ux - .5) + abs(cy - uy - .5) for ux, uy in missing) if missing else 15)
    if run_cells(state, 1) != state: s -= 1.0           # oscillating debris counts against
    return s, m, len(junk)

def main():
    global TPOS
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--glyph', default='.#./#.#/###/#.#/#.#', help='rows of # and . separated by /')
    ap.add_argument('--beam', type=int, default=60)
    ap.add_argument('--depth', type=int, default=120)
    ap.add_argument('--workers', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--tag', default='A')
    a = ap.parse_args()
    TPOS = [(c * PITCH, r * PITCH) for r, row in enumerate(a.glyph.split('/')) for c, v in enumerate(row) if v == '#']
    random.seed(a.seed)
    nt = len(TPOS)
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    out = os.path.join(HERE, 'out', f'slow_salvo_{a.tag}')
    beam, seen, best, t0 = [(0.0, BLOCK, [])], {BLOCK}, None, time.time()
    with Pool(a.workers, initializer=_init, initargs=(TPOS,)) as pool:
        for depth in range(1, a.depth + 1):
            results = pool.map(expand, [st for _, st, _ in beam], chunksize=1)
            cand = []
            for (sc, st, hist), res in zip(beam, results):
                for shot, g, r in res:
                    if r in seen: continue
                    seen.add(r)
                    s, m, j = score(r)
                    cand.append([s + random.random() * 0.4, r, hist + [(shot, st)], m, j, st, g])
            if not cand:
                print('dead end at depth', depth); break
            cand.sort(key=lambda c: -c[0])
            top = cand[:a.beam * 2]
            oks = pool.map(escaped_ok, [(c[5], c[6], c[1]) for c in top], chunksize=4)
            keep = [c for c, ok in zip(top, oks) if ok][:a.beam]
            if not keep:
                print('dead end at depth', depth); break
            beam = [(c[0], c[1], c[2]) for c in keep]
            if best is None or (keep[0][3], -keep[0][4]) > (best[3], -best[4]): best = keep[0]
            print(f'depth {depth:3d}: {len(cand):5d} new patterns, best has {keep[0][3]}/{nt} blocks '
                  f'+ {keep[0][4]} other objects | best ever {best[3]}/{nt} | {time.time() - t0:.0f}s', flush=True)
            pickle.dump(dict(best=best[:5], depth=depth, glyph=a.glyph), open(out + '.pkl', 'wb'))
            done = [c for c in keep if c[3] == nt and c[4] == 0]
            if done:
                print('SOLVED with', len(done[0][2]), 'gliders')
                pickle.dump(dict(solution=done[0][:5], glyph=a.glyph), open(out + '_solved.pkl', 'wb'))
                return

def _init(tpos):
    global TPOS
    TPOS = tpos

if __name__ == '__main__':
    main()
