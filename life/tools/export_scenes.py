"""export_scenes.py — turn search results into the scene files the web panel reads.

    python export_scenes.py --chain out/turner_chain_24.pkl --spell out/spell_ALIFE_EDU_lines_1.pkl

writes life/scenes/turner-chain.json, life/scenes/alife-edu.json and life/scenes/soup.json.
See life/README.md ("Scene files") for the format. Run verify_scenes.py afterwards.
"""
import argparse, json, os, pickle
from lifecore import *

HERE = os.path.dirname(os.path.abspath(__file__))
SCENES = os.path.join(HERE, '..', 'scenes')
W, H = 100, 80

def grid_for(cells, pad=4):
    """A grid just big enough for every starting cell, plus `pad`, and the view."""
    xs = [x for x, y in cells]; ys = [y for x, y in cells]
    ox = -min(min(xs), 0) + pad; oy = -min(min(ys), 0) + pad
    return dict(ox=ox, oy=oy, GW=max(max(xs), W) + ox + pad + 1, GH=max(max(ys), H) + oy + pad + 1)

def cells(s):
    return [list(c) for c in sorted(s)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chain', default=os.path.join(HERE, 'out', 'turner_chain_24.pkl'))
    ap.add_argument('--chain-args', default='--seed 24')
    ap.add_argument('--spell', default=os.path.join(HERE, 'out', 'spell_ALIFE_EDU_lines_1.pkl'))
    ap.add_argument('--spell-args', default='--lines ALIFE/EDU --order lines --seed 1')
    a = ap.parse_args()
    os.makedirs(SCENES, exist_ok=True)

    c = pickle.load(open(a.chain, 'rb'))
    links = [dict(x=min(p[0] for p in b), y=min(p[1] for p in b), t=l['t_done']) for l in c['log'] for b in l['blocks']]
    turners = sum(1 for l in c['log'] if l['kind'] == 'turn')
    chain = dict(
        format='alife-edu life scene 1', id='chain', kind='links', title='Turner chain', rule='B3/S23',
        description=f'One glider strikes {turners} one-time turners and leaves four blocks behind. Each block is a link.',
        label=f'Game of Life: one glider and {turners} one-time turners leave four link blocks',
        W=W, H=H, ox=30, oy=30, GW=W + 60, GH=H + 60, seconds=24, endGen=c['end_t'],
        start=cells(c['start']), final=cells(c['final']), links=links,
        stats=dict(turners=turners, cells=len(c['start'])),
        collisions=[dict(gen=l['t_hit'], kind=l['kind'], target=l['name']) for l in c['log']],
        provenance=dict(tools=['tools/find_turner_reactions.py', 'tools/build_turner_chain.py ' + a.chain_args]))

    s = pickle.load(open(a.spell, 'rb'))
    ng = len(s['start']) // 5
    spell = dict(
        format='alife-edu life scene 1', id='alife', kind='run', title='ALIFE·EDU', rule='B3/S23',
        description=f'{ng} gliders fly in from outside the panel. Each pair collides into one block, and the blocks spell ALIFE over EDU.',
        label=f'Game of Life: {ng} gliders collide into {len(s["blocks"])} blocks that spell ALIFE over EDU',
        W=W, H=H, **grid_for(s['start']), seconds=30, endGen=s['end'],
        start=cells(s['start']), final=cells(frozenset().union(*s['blocks'])),
        stats=dict(gliders=ng, blocks=len(s['blocks'])),
        pixels=[dict(x=l['x'], y=l['y'], t=l['t']) for l in s['log']],
        provenance=dict(tools=['tools/find_block_syntheses.py', 'tools/spell_with_gliders.py ' + a.spell_args]))

    soup = dict(
        format='alife-edu life scene 1', id='soup', kind='soup', title='Soup', rule='B3/S23',
        description='A random 20×20 soup, run until it settles. Click or drag to draw cells.',
        label='Game of Life: a random soup; click or drag to draw cells',
        W=W, H=H, ox=30, oy=30, GW=W + 60, GH=H + 60, soup=20, density=0.5, gps=24)

    for name, sc in [('turner-chain.json', chain), ('alife-edu.json', spell), ('soup.json', soup)]:
        path = os.path.join(SCENES, name)
        with open(path, 'w') as f:
            # one key per line, but cell lists on one line each, so diffs stay readable
            f.write('{\n' + ',\n'.join(f'  {json.dumps(k)}: {json.dumps(v, separators=(",", ":"), ensure_ascii=False)}'
                                       for k, v in sc.items()) + '\n}\n')
        print('wrote', os.path.relpath(path, os.path.join(HERE, '..')), os.path.getsize(path), 'bytes')

if __name__ == '__main__':
    main()
