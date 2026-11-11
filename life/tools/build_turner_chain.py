"""build_turner_chain.py — step 2 of the turner-chain scene (the one with link blocks).

Goal: a single glider starts in the corner of a 100 × 80 field. Scattered ahead of it are
one-time turners (from find_turner_reactions.py). It strikes them one after another, each
strike turning it onto a new path, and the debris left behind must include exactly four
2 × 2 blocks, well spread out, to become the page's links. The last collision absorbs
the glider so the field ends at rest.

Method: depth-first search with backtracking.
  * The glider is followed along its path. At each step we consider every turner reaction,
    in every orientation that matches the glider's direction, placed 4–25 diagonal steps
    ahead of it.
  * A placement is rejected at once if it would leave the field, if the glider's path to
    it crosses earlier debris, if it sits on an earlier path, or if a new block would land
    near the edge or near another block (link labels need room).
  * The rest are scored (a little randomness; prefer reactions that leave blocks; prefer
    outgoing gliders aimed back toward the middle; avoid 180° bounces) and tried best first.
  * Each accepted step is VERIFIED by simulating the whole pattern from generation 0 (exact
    Life on a 160 × 140 grid with a dead border) and checking that the result is exactly
    the expected debris plus the outgoing glider. Only then does the search go deeper.
  * After 5–8 turners a final reaction that brings the block count to exactly four is
    placed, and the pattern is run 300 more generations to confirm it stays at rest.

The random seed picks one of many possible chains. The page uses seed 24, which is the one
that `python build_turner_chain.py --seed 24` regenerates.

Output: out/turner_chain_<seed>.pkl with the starting pattern, final pattern, the time each
link block settles, and a log of every collision.
Runtime: seconds to a few minutes, depending on the seed.
"""
import argparse, os, pickle, random
from lifecore import *

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 100, 80                 # visible field, in cells
NBLOCK = 4                     # link blocks the run must leave behind
MINTURN, MAXTURN = 5, 8        # how many turners the glider hits before the final collision
MARGIN = 4                     # keep the action this far from the field's edge
BLOCK = parse("OO\nOO")
CX, CY = W / 2, H / 2

def load_reactions():
    R = pickle.load(open(os.path.join(HERE, 'out', 'turner_reactions.pkl'), 'rb'))
    uniq, seen = [], set()
    for r in R:
        k = (r['tgt'], r['ash'], r['gout'], r['kind'])
        if k not in seen:
            seen.add(k); uniq.append(r)
    for r in uniq:
        if r['kind'] != 'eat':
            rewind(r)
        r['env'] = envelope(r)
        r['nblk'] = len(blocks_of(r['ash']))
    return [r for r in uniq if r['kind'] == 'turn'], [r for r in uniq if r['kind'] in ('end', 'eat')]

def envelope(r):
    """Every cell the reaction touches (ignoring the outgoing glider once it is far away)."""
    cur = r['tgt'] | r['gin']; env = set(r['tgt'])
    for _ in range(r['T']):
        cur = run_cells(cur, 1)
        env |= {c for c in cur if max(abs(c[0]), abs(c[1])) < 14}
    return frozenset(env)

def rewind(r):
    """Shorten a reaction to the first generation at which it is just ash + a clean glider,
    and move the recorded output glider back to that moment."""
    cur = r['tgt'] | r['gin']; states = [cur]
    for _ in range(r['T']):
        cur = run_cells(cur, 1); states.append(cur)
    T = r['T']
    if not r['gout']:
        for t in range(T + 1):
            if states[t] == r['ash']:
                r['T'] = t; return
        return
    d, best = r['dout'], T
    for j in range(1, T // 4):
        t = T - 4 * j
        g = shift(r['gout'], -j * d[0], -j * d[1])
        if states[t] == r['ash'] | g and not (dilate(g, 2) & r['ash']):
            best = t
        else:
            break
    j = (T - best) // 4
    r['T'] = best; r['gout'] = shift(r['gout'], -j * d[0], -j * d[1])

def blocks_of(cells):
    return [c for c in components(cells, 1) if norm(c) == BLOCK]

def inside(cells, m=MARGIN):
    return all(m <= x < W - m and m <= y < H - m for x, y in cells)

def simulate(cells, gens):
    pad = 30
    g = to_grid(cells, W + 2 * pad, H + 2 * pad, pad, pad)
    for _ in range(gens):
        g = step(g)
    return from_grid(g, pad, pad)

def room(g, d):
    """Diagonal steps a glider can travel before leaving the margin box."""
    n = 0
    while n < 200 and inside(shift(g, n * d[0], n * d[1])):
        n += 1
    return n

def sweep_list(g, maxm):
    """sweep_list(g)[m] = every cell the glider covers in its next m+1 diagonal steps."""
    out, acc, cur = [], set(), g
    for _ in range(maxm + 2):
        for _p in range(4):
            cur = run_cells(cur, 1); acc |= cur
        out.append(frozenset(acc))
    return out

def candidates(state, TURNS, ENDS):
    """Every reaction, in every orientation whose incoming glider travels the way ours does,
    placed so that our glider meets it after k generations plus m diagonal steps."""
    gl, d = state['glider'], state['dir']
    out = []
    for r in TURNS + ENDS:
        for s in SYMS:
            if tfv((1, 1), s) != d:
                continue
            gin = tf(r['gin'], s)
            for k in range(4):                       # match the glider's phase
                a = run_cells(gl, k)
                if norm(a) != norm(gin):
                    continue
                v0 = (minpos(a)[0] - minpos(gin)[0], minpos(a)[1] - minpos(gin)[1])
                for m in range(4, 26):
                    out.append((r, s, k, m, (v0[0] + m * d[0], v0[1] + m * d[1])))
    return out

def place(r, s, v):
    T = lambda c: shift(tf(c, s), *v)
    return dict(tgt=T(r['tgt']), ash=T(r['ash']), env=T(r['env']),
                gout=T(r['gout']) if r['gout'] else None,
                dout=tfv(r['dout'], s) if r['dout'] else None)

def build(st, targets, ash, blocks, paths, envs, log, g0, depth, TURNS, ENDS, recent=frozenset()):
    nb = len(blocks)
    sw = sweep_list(st['glider'], 26)
    occupied = frozenset().union(*paths, *envs) if (paths or envs) else frozenset()
    ex = frozenset(ash)
    older = ex - recent                                   # the newest debris may be close by
    oldblk = frozenset().union(*[b for b in blocks if not (b & recent)]) if blocks else frozenset()
    exd = dilate(older, 3) | dilate(oldblk, 5) | dilate(recent, 1)
    pool = []
    for r, s, k, m, v in candidates(st, TURNS, ENDS):
        is_end = r['kind'] != 'turn'
        if is_end and (depth < MINTURN or nb + r['nblk'] != NBLOCK): continue
        if not is_end and depth >= MAXTURN: continue
        if nb + r['nblk'] > NBLOCK: continue
        P = place(r, s, v)
        if not inside(P['env'] | P['tgt']): continue
        if P['gout'] and (not inside(P['gout']) or room(P['gout'], P['dout']) < 14): continue
        if sw[m] & exd: continue                          # path to the turner crosses debris
        if dilate(P['tgt'], 4) & (occupied | ex): continue
        if dilate(P['env'], 2) & ex: continue
        newb = blocks_of(P['ash'])
        bad = False                                       # link blocks: off the edge, spread out
        for b in newb:
            bx, by = minpos(b)
            if not (8 <= bx <= W - 10 and 6 <= by <= H - 8): bad = True
            for ob in blocks + [o for o in newb if o is not b]:
                ox, oy = minpos(ob)
                if max(abs(ox - bx), abs(oy - by)) < 16: bad = True
            if dilate(b, 4) & occupied: bad = True
        if bad: continue
        sc = random.random() * 3
        need, left = NBLOCK - nb, MAXTURN - depth
        sc += len(newb) * (2.5 if need >= left - 1 else 1.0)
        if P['gout']:
            d = P['dout']; cx, cy = minpos(P['gout'])
            sc += ((CX - cx) * d[0] + (CY - cy) * d[1]) / max(W, H)
            if d == (-st['dir'][0], -st['dir'][1]): sc -= 1.0
            sc += min(m, 14) / 14
        pool.append((sc, r, s, k, m, v, P, newb))
    pool.sort(key=lambda p: -p[0])
    tried = 0
    for sc, r, s, k, m, v, P, newb in pool[:40]:
        newt = targets + [P['tgt']]
        tnow = st['t'] + k + 4 * m + r['T']
        start = g0 | frozenset().union(*newt)
        exp = frozenset(ash) | P['ash'] | (P['gout'] or frozenset())
        if simulate(start, tnow) != exp:                  # the exact check
            continue
        tried += 1
        entry = dict(name=r['name'], kind=r['kind'], t_hit=st['t'] + k + 4 * m, t_done=tnow,
                     ash=len(P['ash']), dir=P['dout'], blocks=[sorted(b) for b in newb])
        if r['kind'] != 'turn':
            if simulate(start, tnow + 300) != exp: continue
            return dict(start=start, g0=g0, end_t=tnow, final=exp, log=log + [entry],
                        blocks=[sorted(b) for b in blocks + newb])
        nst = dict(glider=P['gout'], dir=P['dout'], t=tnow)
        out = build(nst, newt, ash | P['ash'], blocks + newb, paths + [sw[m]], envs + [P['env']],
                    log + [entry], g0, depth + 1, TURNS, ENDS, frozenset(P['ash']))
        if out: return out
        if tried >= 2: break
    return None

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--seed', type=int, default=24)
    ap.add_argument('--attempts', type=int, default=30)
    a = ap.parse_args()
    random.seed(a.seed)
    TURNS, ENDS = load_reactions()
    for attempt in range(a.attempts):
        g0 = shift(GLIDER_SE, MARGIN + 1, MARGIN + 1 + random.randint(0, 10))
        res = build(dict(glider=g0, dir=(1, 1), t=0), [], set(), [], [], [], [], g0, 0, TURNS, ENDS)
        if res:
            print(f'attempt {attempt}: found a chain that rests at generation {res["end_t"]}')
            for l in res['log']:
                print(f"  gen {l['t_hit']:5d}  {l['kind']:4s} {l['name']:9s}  leaves {len(l['blocks'])} link block(s)")
            out = os.path.join(HERE, 'out', f'turner_chain_{a.seed}.pkl')
            pickle.dump(res, open(out, 'wb'))
            print('saved', out)
            return
        print(f'attempt {attempt}: no chain', flush=True)

if __name__ == '__main__':
    main()
