"""verify_scenes.py — check every scene file independently of the tools that made it.

For each life/scenes/*.json with a stored final state, this rebuilds the grid described in
the file (size GW × GH, dead border, view offset ox, oy), loads `start`, runs exactly
`endGen` generations of B3/S23 with a plain dense numpy simulator, and compares the result
with `final`. It also checks that the final state is at rest (period 1), that nothing
touched the grid's border, and, for link scenes, that every link block is present from the
generation it claims to settle until the end.

    python verify_scenes.py            ->  turner-chain.json  OK ...  /  alife-edu.json  OK ...
"""
import glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

def step(g):
    n = sum(np.roll(np.roll(g, i, 0), j, 1) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0))
    out = ((n == 3) | (g & (n == 2))).astype(np.uint8)
    out[0, :] = out[-1, :] = 0; out[:, 0] = out[:, -1] = 0
    return out

def check(path):
    s = json.load(open(path))
    if 'final' not in s:
        return f'{os.path.basename(path):18s} skipped (made in the browser)'
    g = np.zeros((s['GH'], s['GW']), np.uint8)
    for x, y in s['start']:
        g[y + s['oy'], x + s['ox']] = 1
    touched_edge = False
    links = s.get('links', [])
    broken = []
    for t in range(1, s['endGen'] + 1):
        g = step(g)
        if g[1, :].any() or g[-2, :].any() or g[:, 1].any() or g[:, -2].any():
            touched_edge = True
        for b in links:
            if t >= b['t']:
                y, x = b['y'] + s['oy'], b['x'] + s['ox']
                if not (g[y:y + 2, x:x + 2].all() and g[y - 1:y + 3, x - 1:x + 3].sum() == 4):
                    broken.append((b['x'], b['y'], t)); b['t'] = 10 ** 9
    want = np.zeros_like(g)
    for x, y in s['final']:
        want[y + s['oy'], x + s['ox']] = 1
    ok = np.array_equal(g, want) and np.array_equal(step(g), g) and not touched_edge and not broken
    detail = f"{s['endGen']} generations, {int(g.sum())} live cells at rest"
    if touched_edge: detail += ', TOUCHED THE GRID EDGE'
    if broken: detail += f', link blocks disturbed: {broken}'
    return f"{os.path.basename(path):18s} {'OK  ' if ok else 'FAIL'} {detail}", ok

def main():
    results = [check(p) for p in sorted(glob.glob(os.path.join(HERE, '..', 'scenes', '*.json')))]
    allok = True
    for r in results:
        if isinstance(r, str):
            print(r)
        else:
            print(r[0]); allok &= r[1]
    sys.exit(0 if allok else 1)

if __name__ == '__main__':
    main()
