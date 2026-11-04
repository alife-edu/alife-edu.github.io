"""find_block_syntheses.py — step 1 of the ALIFE·EDU scene.

Question: which collisions of exactly two gliders leave exactly one 2 × 2 block and nothing
else? Each such collision can "print" one pixel of a word.

Two gliders can meet at right angles (one travelling SE, the other SW: "perp") or head-on
(SE against NW: "head"). We place a south-east glider at the origin, try the other glider
at every offset in a window and in all four of its phases, and run each pair until it is a
single, stable block (or clearly isn't).

LifeWiki's "2-glider collision" page lists all 71 distinct two-glider collisions; a handful
make a single block. Here those same few collisions turn up many times, once for each
amount the two gliders are "backed up" along their paths before meeting. That is useful
later: a family member that meets sooner keeps the reaction compact.

Each result records the two gliders relative to the block they make (block at 0..1, 0..1),
their directions, the generation the block is complete, and the "envelope": every cell the
reaction ever touches.

Output: out/block_syntheses.pkl.   Runtime: a few minutes.
"""
import os, pickle
from lifecore import *

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = parse("OO\nOO")
GSE = GLIDER_SE                              # moving (+1, +1)
GSW = tf(GLIDER_SE, (-1, 0, 0, 1))           # mirror image, moving (-1, +1)
GNW = tf(GLIDER_SE, (-1, 0, 0, -1))          # turned 180°, moving (-1, -1)

def main():
    found = {}
    for kind, other, odir in [('perp', GSW, (-1, 1)), ('head', GNW, (-1, -1))]:
        for ph in range(4):
            b0 = run_cells(other, ph)
            for dx in range(6, 30):
                for dy in range(-14, 15):
                    a, b = GSE, shift(b0, dx, dy)
                    if min(max(abs(x - u), abs(y - v)) for x, y in a for u, v in b) < 3:
                        continue                         # already touching at the start
                    cur = a | b; env = set(cur); res = None
                    for t in range(1, 160):
                        cur = run_cells(cur, 1); env |= cur
                        if len(cur) == 4 and norm(cur) == BLOCK and run_cells(cur, 1) == cur:
                            res = (t, cur); break
                        if not cur or len(cur) > 60:
                            break
                    if not res or run_cells(res[1], 40) != res[1]:
                        continue
                    t, blk = res
                    bx, by = minpos(blk)
                    found.setdefault((shift(a, -bx, -by), shift(b, -bx, -by)),
                                     dict(kind=kind, a=shift(a, -bx, -by), b=shift(b, -bx, -by), da=(1, 1), db=odir,
                                          t=t, env=shift(frozenset(env), -bx, -by)))
    res = list(found.values())
    print(len(res), 'two-glider collisions that leave a single block')
    for v in sorted(res, key=lambda v: v['t'])[:8]:
        print(f"  {v['kind']:4s} block complete after {v['t']:3d} generations, touches {len(v['env'])} cells")
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    pickle.dump(res, open(os.path.join(HERE, 'out', 'block_syntheses.pkl'), 'wb'))

if __name__ == '__main__':
    main()
