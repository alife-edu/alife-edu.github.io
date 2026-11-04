"""find_turner_reactions.py — step 1 of the turner-chain scene.

Question: when a single glider hits a small still life, what can happen?

We try it, by brute force. For each of 14 common still lifes, in each of its distinct
orientations (Life treats rotations and reflections alike, see lifecore.SYMS), we fire a
glider travelling south-east (+1, +1) along each of 29 parallel lanes, run 280 generations
on a 128 × 128 box, and sort the outcome:

  turn  exactly one glider comes out (in any direction, not just passing by) and what is
        left behind ("ash") is a still life. The still life was a ONE-TIME TURNER: it was
        used up turning the glider. If the ash is non-empty it was a "dirty" turner.
  end   no glider comes out and the ash is a still life different from the target. These
        are possible final collisions for a chain.
  eat   no glider comes out and the target is restored: the target was an EATER.

Anything else (messy explosions, oscillators, several gliders, debris reaching the box
edge) is discarded. We only try the glider's first phase: shifting the lane already gives
plenty of distinct collisions, and every kept reaction is re-verified later anyway.

Output: out/turner_reactions.pkl, a list of dicts with the target, incoming glider, output
glider and direction, ash, and the number of generations simulated.

Background: these are the reactions catalogued on LifeWiki's "Collisions of a glider with
common objects" and "One-time turner" pages; this script simply rediscovers the ones we need.
Runtime: about a minute.
"""
import os, pickle, time
from collections import Counter
from lifecore import *

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'turner_reactions.pkl')

STILL_LIFES = {
    'block': "OO\nOO",
    'beehive': ".OO.\nO..O\n.OO.",
    'loaf': ".OO.\nO..O\n.O.O\n..O.",
    'boat': "OO.\nO.O\n.O.",
    'ship': "OO.\nO.O\n.OO",
    'tub': ".O.\nO.O\n.O.",
    'pond': ".OO.\nO..O\nO..O\n.OO.",
    'eater': "OO..\nO.O.\n..O.\n..OO",          # eater 1, also called the fishhook
    'longboat': "OO..\nO.O.\n.O.O\n..O.",
    'barge': ".O..\nO.O.\n.O.O\n..O.",
    'snake': "OO.O\nO.OO",
    'carrier': "OO..\nO..O\n..OO",
    'mango': ".OO..\nO..O.\n.O..O\n..OO.",
    'integral': "OO...\nO.O..\n..O..\n..O.O\n...OO",
}

def orientations():
    """Each still life in each of its distinct orientations (a block has 1, an eater 8)."""
    seen = set()
    for name, pic in STILL_LIFES.items():
        base = parse(pic)
        for sym in SYMS:
            n = norm(tf(base, sym))
            if n not in seen:
                seen.add(n)
                yield name, n

def main():
    N, O, T = 128, 64, 280
    results = []
    t0 = time.time()
    for name, tgt in orientations():
        for lane in range(-14, 15):
            g = shift(GLIDER_SE, -16 + lane, -16)           # up-left of the target, on `lane`
            if min(max(abs(x - a), abs(y - b)) for x, y in g for a, b in tgt) < 4:
                continue                                    # too close to count as "incoming"
            grid = to_grid(tgt | g, N, N, O, O)
            for _ in range(T):
                grid = step(grid)
            if grid[1:3, :].any() or grid[-3:-1, :].any() or grid[:, 1:3].any() or grid[:, -3:-1].any():
                continue                                    # reached the edge: too messy
            gl, st, ot = classify(from_grid(grid, O, O))
            if ot:
                continue                                    # oscillators or unsettled debris
            ash = frozenset().union(*st) if st else frozenset()
            if run_cells(ash, 1) != ash:
                continue                                    # ash pieces interact with each other
            rec = dict(name=name, tgt=tgt, gin=g, T=T, gout=None, dout=None, ash=ash, nobj=len(st))
            if len(gl) == 1:
                gcells, d = gl[0]
                if d == (1, 1) and ash == tgt:
                    continue                                # the glider missed
                dist = min(max(abs(x - a), abs(y - b)) for x, y in gcells for a, b in ash) if ash else 99
                if dist < 6:
                    continue
                results.append(dict(rec, kind='turn', gout=gcells, dout=d))
            elif not gl and ash and ash != tgt:
                results.append(dict(rec, kind='end'))
            elif not gl and ash == tgt:
                results.append(dict(rec, kind='eat'))
        print(f'{name:9s} {len(results):4d} reactions so far  ({time.time() - t0:.0f}s)', flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pickle.dump(results, open(OUT, 'wb'))
    print('saved', OUT)
    print(Counter((r['kind'], r['name']) for r in results))

if __name__ == '__main__':
    main()
