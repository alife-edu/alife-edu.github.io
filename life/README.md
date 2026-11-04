# The Life panel

The ALife-Edu home page has a small window of Conway's Game of Life next to its headline.
A single glider bounces off a row of tiny still lifes and leaves four blocks behind, and
those blocks are the page's links. Another tab writes **ALIFE / EDU** using 142 gliders
that collide in pairs. A third shows a random soup you can draw on.

This folder holds all of it, separate from the rest of the website, so you can read it,
run it, change it, or reuse it. Nothing here depends on the site.

| | |
|---|---|
| **Try it** | [`playground.html`](playground.html) is the panel on its own page, with a Step button and every starting pattern in RLE. |
| **Read the code** | Start with [`engine.js`](engine.js) (the rule, about 100 lines of logic), then [`panel.js`](panel.js). |
| **See how the scenes were found** | [`tools/`](tools/) has the search programs, explained in [How the scenes were made](#how-the-scenes-were-made). |

- [What's in this folder](#whats-in-this-folder)
- [Running it yourself](#running-it-yourself)
- [The Game of Life in one paragraph](#the-game-of-life-in-one-paragraph)
- [How the browser code works](#how-the-browser-code-works)
- [How the scenes were made](#how-the-scenes-were-made)
- [Why you can trust it's real Life](#why-you-can-trust-its-real-life)
- [Scene files](#scene-files)
- [Using the panel on another page](#using-the-panel-on-another-page)
- [The slow-salvo experiment](#the-slow-salvo-experiment)
- [Sources](#sources)

## What's in this folder

```
life/
├── engine.js          The Game of Life rule (B3/S23) on a bounded grid. No drawing, no page code.
├── panel.js           The viewer: canvas, scene tabs, play/pause, speed, link blocks.
├── panel.css          The viewer's styles, all driven by CSS custom properties.
├── playground.html    A standalone page with the panel and nothing else from the site.
├── scenes/
│   ├── turner-chain.json   One glider, eight one-time turners, four link blocks.
│   ├── alife-edu.json      142 gliders that collide into the words ALIFE / EDU.
│   └── soup.json           Settings for the random soup (it is generated in the browser).
└── tools/             Python programs that found and verified the scenes.
    ├── lifecore.py              Shared helpers: patterns as sets, a simulator, object recognition.
    ├── find_turner_reactions.py Step 1 of the turner chain: what happens when a glider hits a still life?
    ├── build_turner_chain.py    Step 2: chain those reactions into a single glider's journey.
    ├── find_block_syntheses.py  Step 1 of ALIFE·EDU: which pairs of gliders make exactly one block?
    ├── spell_with_gliders.py    Step 2: schedule glider pairs so the blocks spell text.
    ├── slow_salvo_search.py     An experiment: build a letter with gliders from one direction only.
    ├── export_scenes.py         Write the scene JSON files from the search results.
    └── verify_scenes.py         Re-run every scene with an independent simulator and check it.
```

On the site, three small files connect the panel to the home page. They're outside this
folder because they're about the site, not about Life:

- `_includes/life-panel.html` drops the panel into the hero and supplies the four link buttons.
- `_includes/life-nav-modals.html` holds the dialogs those buttons open. The Events and Archive dialogs are generated from `_events/`.
- `js/home-life-links.js` listens for the panel's `life:link` event and opens the right dialog.

## Running it yourself

**In the browser.** Browsers refuse to load the scene files from a `file://` address, so serve
the folder with any small web server:

```sh
cd life
python3 -m http.server
# then open http://localhost:8000/playground.html
```

**The tools.** You need Python 3 with `numpy` (`pip install numpy`). Run them from `life/tools/`.
Intermediate results go in `life/tools/out/`, which git ignores.

```sh
cd life/tools
python find_turner_reactions.py                 # ~2 min
python build_turner_chain.py --seed 24          # seconds; regenerates the home page's chain exactly
python find_block_syntheses.py                  # ~3 min
python spell_with_gliders.py --lines ALIFE/EDU  # ~6 min; regenerates ALIFE / EDU exactly
python export_scenes.py                         # writes ../scenes/*.json
python verify_scenes.py                         # checks them
```

Try other seeds, other words (`--lines LIFE/IS/ODD`, using the letters in `FONT`), or edit
the scoring in `build_turner_chain.py` and see what chains you get.

## The Game of Life in one paragraph

The world is a grid of square cells, each alive or dead. Each cell has eight neighbours.
Every generation, all cells update at once. A dead cell with exactly **3** live neighbours is
born, and a live cell with **2 or 3** live neighbours survives. Every other cell is dead in
the next generation. That rule is written **B3/S23**. John Conway devised it, and Martin
Gardner introduced it to the world in *Scientific American* in October 1970. A few patterns
come up again and again on this page:

- **Still lifes** never change. The **block** (2×2) is the most common one. Others here are the **boat**, **ship**, **beehive**, **loaf** and the **eater** (also called the fishhook).
- **Oscillators** repeat with some period. The **blinker** is three cells in a row that flip between horizontal and vertical.
- **Spaceships** move. The **glider** is five cells that move one cell diagonally every four generations.

## How the browser code works

### `engine.js`: the rule

A real Life universe is infinite, but a program needs a finite grid. The engine uses a
rectangle of `GW × GH` cells whose outer ring is held dead. As long as nothing reaches that
ring, this behaves exactly like the infinite plane, and the tools check that it never does.
Each scene names the part you see (`W × H`, 100 × 80 here) and where it sits in the full
grid (`ox`, `oy`). That's how 142 gliders can start out of sight.

The obvious way to compute a generation is to look at every cell. The ALIFE·EDU grid is 502 × 477,
which is about 240,000 cells, but only a few hundred are ever alive. So the engine works from the live
cells instead. Each live cell adds one to the neighbour count of each of its eight neighbours,
and only cells that were touched can be alive next generation. The cost grows with the number
of live cells rather than the size of the grid, which is why 8× playback is cheap. All births
and deaths are computed before any are applied, because every cell must update at the same instant.

The engine also records, for every cell, the generation it was last born and last died. The
panel uses that to colour new cells and draw the fading trails behind gliders.

### `panel.js`: the viewer

The panel loads the scene files, builds its own canvas and controls, and runs a loop.

- **Timing.** A precomputed scene plays in a fixed number of seconds at 1×. The speed buttons
  scale that from ¼× to 8×. Each animation frame runs as many generations as the elapsed time
  allows, capped at 400 per frame. Nothing runs when the panel is off-screen or the tab is hidden.
- **Drawing.** Only the visible window is drawn. A cell born in the last few generations is
  drawn in the "live" colour, and settled cells in a quieter one, so moving things stand out.
- **Link blocks.** A scene of kind `links` lists some of its final blocks with the generation
  each one settles. At that generation the panel puts a real `<button>` exactly over the block's
  four cells and stops drawing them on the canvas. A label is placed on whichever side (right,
  left, above or below) keeps it inside the panel and clear of the other labels. Clicking fires
  a `life:link` event, and the page decides what that means.
- **The check.** When a precomputed run reaches its last generation, the panel compares every
  live cell with the scene's stored `final` state and shows ✓ or ✗.
- **Soups.** The soup is generated from a seeded random-number generator (`mulberry32`), so
  seed 7 is the same soup for everyone. It's considered settled once it repeats with period 1
  or 2 for 40 generations.

## How the scenes were made

Both precomputed scenes were found by search: try many possibilities, simulate them, and keep
what works. None of the starting patterns was drawn by hand.

### Turner chain: one glider, eight turners, four links

**The idea.** A *one-time turner* is a small still life that, when a glider hits it, sends a
glider off in a new direction and is destroyed in the process. It's called *dirty* if it leaves
debris ("ash") behind. Line a few up and one glider can tour the window. If some of the ash is
2×2 blocks, those blocks can become links.

**Step 1: [`find_turner_reactions.py`](tools/find_turner_reactions.py).** Fire a glider at each
of 14 common still lifes, in every orientation, along 29 neighbouring lanes, and sort the outcomes.
- **turn** means exactly one glider comes out and the rest is still. The boat, ship, eater, long boat and carrier all do this.
- **end** means the glider is absorbed and something new is left.
- **eat** means the glider is absorbed and the target survives. The eater does this, which is how it got its name.

This rediscovers reactions catalogued on LifeWiki's [one-time turner](https://conwaylife.com/wiki/One-time_turner)
and [collisions with common objects](https://conwaylife.com/wiki/Collisions_of_a_glider_with_common_objects)
pages. Notably, a glider hitting a lone **block** never gives a clean turn.

**Step 2: [`build_turner_chain.py`](tools/build_turner_chain.py).** This is a depth-first search
with backtracking. At each point it follows the glider's path and considers every turner in every
orientation that fits, placed 4–25 diagonal steps ahead. It throws out placements that leave the
window, cross old debris or lie on an earlier path, or that would put a link block too close to
the edge or to another block. It then tries the rest, best first. The score adds randomness and
favours reactions that leave blocks and outgoing gliders aimed back toward the middle. Each
accepted step is verified by simulating the whole pattern from generation 0. After 5–8 turners, a
final collision that brings the count to exactly four blocks ends the run, and 300 more generations
confirm it stays at rest.

The random seed picks which chain you get; the home page uses `--seed 24`. Its glider turns off
a boat, two eaters and a carrier, and each of those leaves one link block. Then three more eaters
and a long boat turn it without leaving blocks, and a final long boat absorbs it. The whole run is
1,463 generations.

### ALIFE·EDU: 142 gliders writing in blocks

**The idea.** Building objects by crashing gliders together is called
[glider synthesis](https://conwaylife.com/wiki/Glider_synthesis). There are exactly
[71 distinct ways two gliders can collide](https://conwaylife.com/wiki/2-glider_collision), and a
few of them leave a single block. A block can serve as one pixel of a letter, so a word is a list
of pixels, each made by two gliders arriving at the right place at the right time.

**Step 1: [`find_block_syntheses.py`](tools/find_block_syntheses.py).** This tries gliders meeting
at right angles and head-on, at every offset and phase, and keeps the pairs that end as exactly
one block. Mark Niemiec's table of [objects buildable with 2 gliders](https://conwaylife.com/ref/mniemiec/glider-2.htm)
shows the same collisions.

**Step 2: [`spell_with_gliders.py`](tools/spell_with_gliders.py).** The text uses a 3×5 pixel font
with pixels 5 cells apart. ALIFE is 40 pixels and EDU is 31. For each pixel in turn:

1. Try every block-making collision in all 8 orientations, centred on the pixel. Reject any whose
   cells would leave the window or brush a finished block.
2. Move both gliders back along their paths until they start outside the window. That sets the
   earliest generation the collision can happen.
3. **Check it against the space-time history of everything placed so far.** At every generation,
   each cell of the new pair must be at least 3 cells (in Chebyshev distance) from every live cell
   already in the pattern. Two cells that far apart share no neighbour, so neither can affect the
   other. If that holds at every generation, the new pair behaves exactly as it would alone, and
   so does everything else. Gliders may cross the same spot at different times. For the last 16
   generations before a collision, the letter's own nearby blocks may be closer, and that final
   approach is simulated exactly instead.
4. If nothing fits, try arriving 4, 8, … up to 240 generations later, and if still nothing fits,
   give up.

**Build order matters**, because a glider can't fly through letters that already exist. Writing
ALIFE column by column from the left lets its gliders arrive from the right, where nothing is
built yet. Building EDU from its top row down lets its gliders arrive from below. A first attempt
that went letter by letter got stuck, because the gliders for each new letter had to cross the
previous one.

At the end, the full 710-cell starting pattern is simulated from generation 0 on its 502 × 477
grid, and the result must be exactly the 71 blocks.

### Soup

Twenty by twenty cells, each alive with probability ½, chosen by a seeded random-number generator.
This is the same kind of starting pattern the Life community's census,
[Catagolue](https://catagolue.hatsya.com/), runs by the billion to see what the rule tends to make.

## Why you can trust it's real Life

- The browser applies only B3/S23 after generation 0. No cell is ever placed by the animation
  code. The only exception is drawing on the Soup tab, which is you editing the pattern.
- Every precomputed scene stores its final state. The panel checks against it at the end of the
  run, and `tools/verify_scenes.py` checks it again with a different, deliberately plain simulator.
- The playground shows each starting pattern as RLE, the standard text format. Paste it into
  [Golly](https://golly.sourceforge.io/) or [LifeViewer](https://conwaylife.com/wiki/LifeViewer),
  run it for `endGen` generations, and you'll get the same picture.
- The tools regenerate the exact published scenes from scratch with the seeds shown above.

## Scene files

Each scene is a JSON object.

| key | meaning |
|---|---|
| `id`, `kind`, `title` | Identity. `kind` is `links` (a run with link blocks), `run` (a run), or `soup` (generated in the browser). |
| `description`, `label` | Caption text, and an accessible description of the canvas. |
| `rule` | Always `B3/S23`. |
| `W`, `H` | The visible window, in cells. |
| `GW`, `GH`, `ox`, `oy` | The full grid, and where the window's (0, 0) sits in it. The grid's outer ring is dead. |
| `start` | Live cells at generation 0, as `[x, y]` in window coordinates (they can be negative, outside the window). |
| `endGen`, `final` | The generation the run ends, and the exact live cells then. |
| `seconds` | How long the run takes at 1× speed. |
| `links` | (`links` scenes) `[{x, y, t}]`: the top-left cell of each link block and the generation it settles. |
| `collisions`, `pixels`, `stats` | Extra detail for the curious: what was hit when, when each pixel appeared, counts. |
| `provenance` | Which tools, with which arguments, produced it. |
| `soup`, `density`, `gps` | (`soup` scenes) square size, fill probability, generations per second at 1×. |

## Using the panel on another page

```html
<link rel="stylesheet" href="life/panel.css">
<div data-life-panel data-scenes="life/scenes/turner-chain.json life/scenes/soup.json" data-extras="step rle">
  <button data-life-link="first">First link</button>   <!-- optional: one per link block -->
</div>
<script src="life/engine.js"></script>
<script src="life/panel.js"></script>
<script>
  document.addEventListener('life:link', e => console.log('clicked', e.detail.id, e.detail.block));
</script>
```

- `data-scenes` lists the scene files, in tab order.
- `data-extras="step rle"` adds a Step button and an RLE box.
- `data-autoplay="false"` stops it from starting on its own.
- To recolour it, set `--life-bg`, `--life-live`, `--life-link` and the other properties listed at the top of `panel.css`.
- `engine.js` works on its own too, for example in Node, with `new LifeEngine.Grid({...})`.

## The slow-salvo experiment

The ALIFE·EDU gliders come from every direction and are timed to meet in pairs. The Life
community's classic, harder way to build things is a [**slow salvo**](https://conwaylife.com/wiki/Salvo).
Every glider comes from the same direction, one at a time, and each reaction finishes before the
next glider arrives. It is conjectured that anything glider-constructible can be built this way
starting from a single block. Adam P. Goucher's [slmake](https://conwaylife.com/wiki/Slmake)
(now [slsparse](https://conwaylife.com/wiki/Tutorials/slsparse)) compiles such recipes for real
constructions.

[`tools/slow_salvo_search.py`](tools/slow_salvo_search.py) is a first attempt at a slow salvo for a
single letter A. It's a beam search over settled patterns, scored by how many of the letter's ten
blocks are in place. Allowing period-2 debris between gliders (a "p2 slow salvo") made a big
difference: a lone block has only three clean one-glider outcomes when everything must stay still.
It moves, it becomes a honey farm, or it disappears.

Most of the work is simulating trial gliders, so the script uses three tricks:

- **A reaction cache.** A glider usually hits one small group of objects, and the outcome depends
  only on that group's shape and the glider's lane and phase relative to it. Each combination is
  simulated once, alone, and reused wherever it is safe: the incoming lane, every cell the
  reaction touches, and the paths of any escaping gliders must stay at least 3 cells from
  everything else. `--benchmark` checks the cache against full simulation (identical results on
  24 test patterns).
- **Early stopping**, and a small simulation box that takes escaping gliders out as they leave.
- **Many cores** with `--workers`.

Together these make each pattern about 23 times faster to expand than the first version, on one
core. A real two-core run went from about two minutes per glider to about 17 seconds.

So far the search places 3 or 4 of the 10 blocks within 20 gliders and then stalls. The bottleneck
is now the strategy, not the speed: a greedy beam keeps chasing the next block instead of setting
up the debris that later blocks need. Real slow-salvo compilers build a target from the far end,
keeping a single working "elbow" object to aim at. Contributions welcome.

## Sources

**The rule and its objects**
- Martin Gardner, "Mathematical Games: The fantastic combinations of John Conway's new solitaire game 'life'", *Scientific American* 223 (October 1970), 120–123.
- LifeWiki, [Conway's Game of Life](https://conwaylife.com/wiki/Conway%27s_Game_of_Life), [Glider](https://conwaylife.com/wiki/Glider), [Block](https://conwaylife.com/wiki/Block), [Eater 1](https://conwaylife.com/wiki/Eater_1).
- Stephen Silver et al., [Life Lexicon](https://conwaylife.com/ref/lexicon/lex.htm), for names and definitions of objects and reactions.

**Collisions, turners and synthesis (the methods behind the scenes)**
- LifeWiki, [2-glider collision](https://conwaylife.com/wiki/2-glider_collision): all 71 collisions of two gliders and what they make.
- Mark Niemiec, [Life objects buildable with 2 gliders](https://conwaylife.com/ref/mniemiec/glider-2.htm).
- LifeWiki, [Collisions of a glider with common objects](https://conwaylife.com/wiki/Collisions_of_a_glider_with_common_objects).
- LifeWiki, [One-time turner](https://conwaylife.com/wiki/One-time_turner) and [Tutorials/Seed building](https://conwaylife.com/wiki/Tutorials/Seed_building): turners and splitters as building parts.
- LifeWiki, [Glider synthesis](https://conwaylife.com/wiki/Glider_synthesis): building objects from glider collisions.
- LifeWiki, [Kickback reaction](https://conwaylife.com/wiki/Kickback_reaction/Snippet), [Block pull](https://conwaylife.com/wiki/Block_pull) and [Sliding block memory](https://conwaylife.com/wiki/Sliding_block_memory): single-glider reactions that move or redirect things.

**Slow salvos**
- LifeWiki, [Salvo](https://conwaylife.com/wiki/Salvo): slow, p1 and p2 slow salvos, and the conjecture that a block plus a slow salvo can build anything glider-constructible.
- LifeWiki, [slmake](https://conwaylife.com/wiki/Slmake) and [Tutorials/slsparse](https://conwaylife.com/wiki/Tutorials/slsparse): Adam P. Goucher's slow-salvo compiler (2017).
- "[Building arbitrary Life patterns in 15 gliders](https://biggieblog.com/building-arbitrary-life-patterns-in-15-gliders/)", an accessible account of seed constellations, slow salvos and universal construction.

**Related ideas: text and Life**
- H. A. Verrill, "[Conway Still Life Drawing](https://archive.bridgesmathart.org/2022/bridges2022-199.html)", *Proceedings of Bridges 2022*, 199–206: dense still lifes shaped like letters and other forms.
- Dean Hickerson and Eric Angelini's "Life integers" (2007): numbers whose digits form patterns that build objects. See the [ConwayLife forum thread](https://conwaylife.com/forums/viewtopic.php?p=58809) and [List of integer constructions](https://conwaylife.com/wiki/List_of_integer_constructions).
- Text as a starting pattern, which then dissolves: [Your Name in Life](https://www.creativebloq.com/javascript/hypnotic-site-turns-your-name-artificial-life-31411009), and the forum thread "[How your username evolves](https://conwaylife.com/forums/viewtopic.php?p=29029)".

**Software for checking**
- [Golly](https://golly.sourceforge.io/), the standard Life simulator; [LifeViewer](https://conwaylife.com/wiki/LifeViewer), the in-browser viewer used on LifeWiki.
- [Catagolue](https://catagolue.hatsya.com/), the census of what random soups become.
