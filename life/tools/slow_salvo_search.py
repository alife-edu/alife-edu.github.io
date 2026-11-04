"""slow_salvo_search.py — EXPERIMENTAL: build a letter from one block with a slow salvo.

The ALIFE·EDU scene uses gliders from every direction, timed to meet in pairs. The Life
community's harder, classic challenge is the SLOW SALVO: every glider comes from the same
direction, one at a time, and each reaction settles completely before the next glider
arrives, so the exact timing between gliders doesn't matter. It's conjectured that anything
glider-constructible can be built this way starting from a single block (LifeWiki, "Salvo");
Adam P. Goucher's slmake compiles such recipes for real constructions.

This script searches for one: gliders travelling SE (arriving from the NW) that turn a
single block into a letter made of blocks 5 cells apart (an "A" by default).

  * State: the settled pattern between gliders. We allow period-2 debris (blinkers etc.)
    as well as still lifes: a "p2 slow salvo". A lone block has only three clean outcomes
    when everything must be still (it moves, it becomes a honey farm, or it disappears),
    so allowing p2 helps a lot.
  * Move: one glider on any lane that reaches the pattern, in any of its 4 phases. The
    reaction must settle within 288 generations, and any glider it throws off must leave
    cleanly and not head NW, back into the stream.
  * Search: beam search. Each pattern is scored by how many target blocks it already has
    (the letter may land anywhere, so we score the best-fitting position), minus a penalty
    for leftover debris and its distance from the blocks still missing. The best BEAM
    patterns are kept at each depth (one depth = one more glider).

Making it fast — the three ideas, in order of how much they help:

  1. A REACTION CACHE. A glider nearly always hits just one small object (a "cluster":
     cells within 2 of each other). What happens then depends only on that object's shape
     and on the glider's lane and phase relative to it, not on where the object is or
     what else is around. So each (shape, lane, phase) is simulated once, alone, and the
     outcome is remembered: the debris it leaves, every cell it touches on the way (its
     "envelope"), and any gliders it throws off. For a whole pattern, the result is the
     cached one, moved into place, PROVIDED nothing else is close: the incoming glider's
     lane, the envelope, and the paths of escaping gliders must all stay at least 3 cells
     from every other object (cells that far apart can't influence each other). When
     that fails, the shot is simulated in full instead.
  2. EARLY STOPPING. A reaction is finished as soon as what's left is still or period 2
     plus cleanly escaping gliders, usually within 100 generations, not 288.
  3. MANY CORES. Patterns in the beam are expanded in parallel (--workers).

Status: an open experiment. Runs so far place 3 or 4 of the A's 10 blocks within about 20
gliders, then stall: the limit is now the strategy, not the speed. Results are saved as it goes.

Speed: --benchmark checks the cache against full simulation (identical results on its test
patterns). Each expansion is about 23x faster than the first, cache-less version, on one core.

Usage:  python slow_salvo_search.py --beam 200 --workers 24 --depth 150
        python slow_salvo_search.py --benchmark       # cache vs full simulation, and a check
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
CHECK = 8                                   # look for "settled" every this many generations
PH = [run_cells(GLIDER_SE, p) for p in range(4)]
TPOS = []                                   # target block positions, set in main()

# ── simulating a batch of reactions ────────────────────────────────────────────────────

def bstep(B):
    """One generation for a stack of grids at once (shape: count × rows × columns)."""
    n = (B[:, :-2, :-2] + B[:, :-2, 1:-1] + B[:, :-2, 2:] + B[:, 1:-1, :-2] + B[:, 1:-1, 2:]
         + B[:, 2:, :-2] + B[:, 2:, 1:-1] + B[:, 2:, 2:])
    c = B[:, 1:-1, 1:-1]
    out = np.zeros_like(B)
    out[:, 1:-1, 1:-1] = (n == 3) | ((c == 1) & (n == 2))
    return out

def settled(cells):
    """If `cells` is period-1/2 debris plus gliders leaving cleanly (none heading NW),
    return (debris, [(glider cells, direction)]); otherwise None."""
    gl, st, ot = classify(cells)
    debris = frozenset().union(*(st + ot)) if (st or ot) else frozenset()
    if run_cells(debris, 2) != debris:
        return None
    for g, d in gl:
        if d == (-1, -1):
            return 'NW'
        if debris and ray_hits(g, d, debris):
            return None                       # still in contact, or will crash into the debris
    return debris, gl

def ray_hits(g, d, cells, margin=6):
    """Will glider g, travelling in direction d, pass within ~3 cells of any of `cells`?"""
    gx = sum(x for x, y in g) / len(g); gy = sum(y for x, y in g) / len(g)
    for x, y in cells:
        rx, ry = x - gx, y - gy
        if rx * d[0] + ry * d[1] > -4 and abs(rx * d[1] - ry * d[0]) <= margin:
            return True
    return False

BAND = 10                                   # escaping gliders are taken out in this edge band

def run_batch(starts, margin=26):
    """Simulate several patterns (lists of cells, same frame) until each settles.

    The box is kept small: a glider that reaches the outer BAND cells, heading outward and
    not NW, is recorded and removed (it has escaped). Anything else reaching the band
    means the reaction is too big, and it's abandoned. Returns, per pattern, None or
    (debris, gliders that escaped or are escaping, envelope of every cell touched, gens)."""
    allx = [x for s in starts for x, y in s]; ally = [y for s in starts for x, y in s]
    x0, y0 = min(allx) - margin, min(ally) - margin
    w, h = max(allx) - x0 + margin + 1, max(ally) - y0 + margin + 1
    n = len(starts)
    B = np.zeros((n, h, w), np.uint8)
    for i, s in enumerate(starts):
        for x, y in s:
            B[i, y - y0, x - x0] = 1
    band = np.ones((h, w), bool); band[BAND:-BAND, BAND:-BAND] = False
    env = B.copy()
    active = np.arange(n)
    out = [None] * n
    escaped = [[] for _ in range(n)]
    prev2 = None
    for t in range(1, MAXGEN + 1):
        if t % CHECK == CHECK - 2:
            prev2 = B.copy()
        B = bstep(B)
        np.maximum(env, B, out=env)
        if t % CHECK:
            continue
        failed = np.zeros(len(active), bool)
        done = np.zeros(len(active), bool)
        inband = (B & band).reshape(len(active), -1).any(1)
        for j in np.nonzero(inband)[0]:                     # something reached the edge band
            yy, xx = np.nonzero(B[j] & band)
            near = frozenset((int(x), int(y)) for x, y in zip(xx, yy))
            yy, xx = np.nonzero(B[j])
            allc = frozenset((int(x), int(y)) for x, y in zip(xx, yy))
            for comp in components(allc, 2):
                if not (comp & near):
                    continue
                k = norm(comp)
                if k not in GLIDER_SHAPES:
                    failed[j] = True; break
                d = GLIDER_SHAPES[k][0]
                cx = sum(x for x, y in comp) / 5; cy = sum(y for x, y in comp) / 5
                outward = ((d[0] < 0 and cx < BAND) or (d[0] > 0 and cx > w - BAND) or
                           (d[1] < 0 and cy < BAND) or (d[1] > 0 and cy > h - BAND))
                if d == (-1, -1) or not outward:
                    failed[j] = True; break
                for x, y in comp:
                    B[j, y, x] = 0
                escaped[active[j]].append((shift(comp, x0, y0), d))
        if t >= 16:
            diff = (B != prev2).reshape(len(active), -1).sum(1)
            for j in np.nonzero(~failed & (diff <= 30))[0]:  # quiet enough to be worth a look
                yy, xx = np.nonzero(B[j])
                cells = frozenset((int(x) + x0, int(y) + y0) for x, y in zip(xx, yy))
                r = settled(cells)
                if r is None:
                    continue
                done[j] = True
                if r != 'NW':
                    ey, ex = np.nonzero(env[j])
                    out[active[j]] = (r[0], r[1] + escaped[active[j]],
                                      frozenset((int(x) + x0, int(y) + y0) for x, y in zip(ex, ey)), t)
        stop = done | failed
        if stop.any():
            keep = ~stop
            B, env, active, prev2 = B[keep], env[keep], active[keep], prev2[keep] if prev2 is not None else None
            if not len(active):
                break
    return out

# ── placing gliders ────────────────────────────────────────────────────────────────────

def place(state, lane, ph):
    """A SE-travelling glider in phase ph whose corner cell is on `lane` (x − y),
    just up-left of the pattern. Moving it further back along its lane, by whole
    diagonal steps, only delays it, and timing doesn't matter in a slow salvo."""
    s0 = min(x + y for x, y in state)
    g = PH[ph]; mx, my = minpos(g)
    S = s0 - 10
    if (S - lane) % 2:
        S -= 1
    return shift(g, (lane + S) // 2 - mx, (S - lane) // 2 - my)

def lanes_of(cells):
    return {x - y for x, y in cells}

# ── the reaction cache ─────────────────────────────────────────────────────────────────

GROUP = 5            # objects within this distance count as one target for the cache
CACHE = {}           # (shape, lane relative to shape, phase) -> (debris, gliders, envelope) or None
STATS = dict(hit=0, miss=0, full=0)

def fill_cache(shape, keys):
    """Simulate a shape alone against several (lane, phase) shots, in one batch."""
    gl = [place(shape, L, ph) for L, ph in keys]
    res = run_batch([shape | g for g in gl])
    for (L, ph), r in zip(keys, res):
        CACHE[(shape, L, ph)] = None if r is None else r[:3]
    STATS['miss'] += len(keys)

def expand(state):
    """Fire every glider that can reach `state`; return [((lane, ph), glider, result)]."""
    clusters = components(state, GROUP)                     # objects this close act as one target
    info = [(c, minpos(c), lanes_of(c), min(x + y for x, y in c)) for c in clusters]
    lo = min(min(l) for _, _, l, _ in info) - 5
    hi = max(max(l) for _, _, l, _ in info) + 5
    plan, need = [], {}
    for L in range(lo, hi + 1):
        for ph in range(4):
            g = place(state, L, ph)
            gl = lanes_of(g); a, b = min(gl) - 5, max(gl) + 5
            hit = [i for i, (_, _, l, s) in enumerate(info) if any(a <= q <= b for q in l)]
            if not hit:
                continue                                    # misses everything
            first = min(hit, key=lambda i: info[i][3])
            c, (mx, my), _, _ = info[first]
            shape = norm(c)
            key = (shape, L - (mx - my), ph)
            plan.append((L, ph, g, first, key))
            if key not in CACHE:
                need.setdefault(shape, set()).add(key[1:])
    for shape, keys in need.items():
        fill_cache(shape, sorted(keys))
    results, fallback = [], []
    for L, ph, g, first, key in plan:
        r = CACHE[key]
        c, (mx, my), _, _ = info[first]
        others = frozenset().union(*[info[i][0] for i in range(len(info)) if i != first]) if len(info) > 1 else frozenset()
        if r is None:                                       # messy alone, or a glider heads NW:
            if others and dilate(c, 12) & others:           # a neighbour might tame it, so simulate
                fallback.append((L, ph, g))
            continue
        debris, gliders, env = r
        if others:
            env_w = shift(env, mx, my)
            near = dilate(env_w, 3) & others
            gl_band = lanes_of(g); a, b = min(gl_band) - 4, max(gl_band) + 4
            front = max(x + y for x, y in env_w)
            on_path = any(a <= x - y <= b and x + y <= front for x, y in others)
            rays = any(ray_hits(shift(gc, mx, my), d, others) for gc, d in gliders)
            if near or on_path or rays:
                fallback.append((L, ph, g)); continue
        STATS['hit'] += 1
        res = (state - c) | shift(debris, mx, my)
        if not res or res == state or run_cells(res, 1) == state:
            continue
        results.append(((L, ph), g, res))
    if fallback:                                            # simulate these shots in full
        STATS['full'] += len(fallback)
        out = run_batch([state | g for _, _, g in fallback])
        for (L, ph, g), r in zip(fallback, out):
            if r is None:
                continue
            res = r[0]
            if not res or res == state or run_cells(res, 1) == state:
                continue
            results.append(((L, ph), g, res))
    return results

# ── scoring and search ─────────────────────────────────────────────────────────────────

def score(state):
    comps = components(state, 1)
    bl = [minpos(c) for c in comps if len(c) == 4 and norm(c) == BLOCK]
    bset, best = set(bl), (0, (0, 0))
    for bx, by in bl:                                   # best position for the letter
        for tx, ty in TPOS:
            off = (bx - tx, by - ty)
            m = sum((px + off[0], py + off[1]) in bset for px, py in TPOS)
            if m > best[0]:
                best = (m, off)
    m, off = best
    want = set((px + off[0], py + off[1]) for px, py in TPOS)
    junk = [c for c in comps if not (len(c) == 4 and norm(c) == BLOCK and minpos(c) in want)]
    missing = [p for p in want if p not in bset]
    s = 12 * m - 0.12 * sum(len(c) for c in junk)
    for c in junk:                                      # debris should sit where blocks are missing
        cx = sum(x for x, y in c) / len(c); cy = sum(y for x, y in c) / len(c)
        s -= 0.15 * (min(abs(cx - ux - .5) + abs(cy - uy - .5) for ux, uy in missing) if missing else 15)
    if run_cells(state, 1) != state:
        s -= 1.0                                        # oscillating debris counts against
    return s, m, len(junk)

def _init(tpos):
    global TPOS
    TPOS = tpos

def _expand(st):
    r = expand(st)
    return r, dict(STATS)

def search(a):
    nt = len(TPOS)
    out = os.path.join(HERE, 'out', f'slow_salvo_{a.tag}')
    beam, seen, best, t0 = [(0.0, BLOCK, [])], {BLOCK}, None, time.time()
    with Pool(a.workers, initializer=_init, initargs=(TPOS,)) as pool:
        for depth in range(1, a.depth + 1):
            outs = pool.map(_expand, [st for _, st, _ in beam], chunksize=1)
            stats = [o[1] for o in outs]
            cand = []
            for (sc, st, hist), (res, _) in zip(beam, outs):
                for shot, g, r in res:
                    if r in seen:
                        continue
                    seen.add(r)
                    s, m, j = score(r)
                    cand.append([s + random.random() * 0.4, r, hist + [(shot, st)], m, j])
            if not cand:
                print('dead end at depth', depth); break
            cand.sort(key=lambda c: -c[0])
            beam = [(c[0], c[1], c[2]) for c in cand[:a.beam]]
            top = cand[0]
            if best is None or (top[3], -top[4]) > (best[3], -best[4]):
                best = top
            hits = sum(s['hit'] for s in stats); full = sum(s['full'] for s in stats)
            print(f'depth {depth:3d}: {len(cand):5d} new patterns, best has {top[3]}/{nt} blocks + {top[4]} '
                  f'other objects | best ever {best[3]}/{nt} | {time.time() - t0:.0f}s '
                  f'(cache answered {hits / max(1, hits + full):.0%} of shots)', flush=True)
            pickle.dump(dict(best=best[:5], depth=depth, glyph=a.glyph), open(out + '.pkl', 'wb'))
            done = [c for c in cand if c[3] == nt and c[4] == 0]
            if done:
                print('SOLVED with', len(done[0][2]), 'gliders')
                pickle.dump(dict(solution=done[0][:5], glyph=a.glyph), open(out + '_solved.pkl', 'wb'))
                return

def full_expand(state):
    """Reference: every shot simulated in full, no cache (used by --benchmark)."""
    lanes = sorted(lanes_of(state))
    shots = [(L, ph) for L in range(lanes[0] - 5, lanes[-1] + 6) for ph in range(4)]
    gl = [place(state, L, ph) for L, ph in shots]
    res = run_batch([state | g for g in gl])
    out = set()
    for (L, ph), r in zip(shots, res):
        if r and r[0] and r[0] != state and run_cells(r[0], 1) != state:
            out.add(((L, ph), r[0]))
    return out

def benchmark():
    """Build some realistic patterns with a short search, then compare the cached expansion
    with full simulation: same results? how much faster?"""
    random.seed(3)
    states, frontier = [], [BLOCK]
    for _ in range(4):
        nxt = []
        for st in frontier:
            nxt += [r for _, _, r in expand(st)]
        random.shuffle(nxt)
        frontier = nxt[:6]
        states += frontier
    CACHE.clear()
    t = time.time(); full = [full_expand(s) for s in states]; tf = time.time() - t
    t = time.time(); fast = [set((sh, r) for sh, g, r in expand(s)) for s in states]; tc1 = time.time() - t
    t = time.time(); fast2 = [set((sh, r) for sh, g, r in expand(s)) for s in states]; tc2 = time.time() - t
    same = sum(a == b for a, b in zip(full, fast))
    extra = sum(len(b - a) for a, b in zip(full, fast)); missing = sum(len(a - b) for a, b in zip(full, fast))
    print(f'{len(states)} patterns: identical results for {same}; cache found {extra} extra, missed {missing}')
    print(f'full simulation {tf:.1f}s | with cache, cold {tc1:.1f}s, warm {tc2:.1f}s | speed-up warm {tf / tc2:.0f}x')

def main():
    global TPOS
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--glyph', default='.#./#.#/###/#.#/#.#', help='rows of # and . separated by /')
    ap.add_argument('--beam', type=int, default=60)
    ap.add_argument('--depth', type=int, default=120)
    ap.add_argument('--workers', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--tag', default='A')
    ap.add_argument('--benchmark', action='store_true')
    a = ap.parse_args()
    TPOS = [(c * PITCH, r * PITCH) for r, row in enumerate(a.glyph.split('/')) for c, v in enumerate(row) if v == '#']
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    if a.benchmark:
        return benchmark()
    random.seed(a.seed)
    search(a)

if __name__ == '__main__':
    main()
