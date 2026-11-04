/*
  life/engine.js — Conway's Game of Life (rule B3/S23), with no drawing and no page code.

  ─── The rule ─────────────────────────────────────────────────────────────────────────
  The world is a grid of cells, each alive or dead. Every cell has eight neighbours (the
  cells touching it, diagonals included). All cells update together, once per generation:

      a dead cell with exactly 3 live neighbours is BORN          (B3)
      a live cell with 2 or 3 live neighbours SURVIVES           (S23)
      every other cell is dead in the next generation

  That's the whole of physics in this universe. Gliders, guns and computers come out of
  these few lines.

  ─── The grid used here ──────────────────────────────────────────────────────────────
  Real Life is played on an infinite plane. A program needs a finite grid, so we use a
  rectangle of GW × GH cells whose outermost ring is held dead ("a dead border").
  Nothing outside the rectangle exists. As long as no pattern reaches the border, this
  behaves exactly like the infinite plane. The scenes on this site are designed so their
  activity stays well inside the border (the offline tools check this).

  Coordinates: a scene describes cells in "view" coordinates (x, y), where 0 ≤ x < W and
  0 ≤ y < H is the part you see. The full grid is bigger, so gliders can start off-screen.
  The offsets (ox, oy) say where view (0, 0) sits inside the grid:

      grid column = x + ox      grid row = y + oy

  ─── Why sparse? ──────────────────────────────────────────────────────────────────────
  The obvious algorithm visits every cell every generation: O(GW·GH) work. Our biggest
  scene has a 502 × 477 grid (~240,000 cells) but only a few hundred live cells, so
  instead we visit live cells only:

      1. For each live cell, add 1 to the neighbour count of each of its 8 neighbours,
         remembering every cell we touched (the "candidates").
      2. Apply B3/S23 to each candidate. Only a candidate can be alive next generation:
         a cell with zero live neighbours that is itself dead stays dead.

  Work is proportional to the number of live cells, which is what makes 8× playback cheap.

  ─── Usage ────────────────────────────────────────────────────────────────────────────
      var g = new LifeEngine.Grid({ W: 100, H: 80, ox: 30, oy: 30, GW: 160, GH: 140 });
      g.load([[1, 0], [2, 1], [0, 2], [1, 2], [2, 2]]);     // a glider
      g.step();  g.gen;  g.population;  g.alive(1, 2);
      g.matches(expectedCells);                              // true if exactly those cells live

  Also exported: LifeEngine.parseRLE(text) and LifeEngine.toRLE(cells), for the standard
  run-length-encoded pattern format that Golly, LifeViewer and the LifeWiki use.
*/
(function (global) {
  'use strict';

  /**
   * A bounded Life grid with a dead border.
   * @param {{W:number,H:number,ox:number,oy:number,GW:number,GH:number}} dims
   */
  function Grid(dims) {
    this.W = dims.W; this.H = dims.H;            // visible window
    this.ox = dims.ox; this.oy = dims.oy;        // where view (0,0) sits in the grid
    this.GW = dims.GW; this.GH = dims.GH;        // full grid, border included
    var n = this.GW * this.GH;
    this.cell = new Uint8Array(n);               // 1 = alive
    this.count = new Uint8Array(n);              // scratch: neighbour counts
    this.seen = new Uint8Array(n);               // scratch: "already a candidate"
    this.born = new Int32Array(n);               // generation each cell last came alive
    this.died = new Int32Array(n);               // generation each cell last died
    this.live = new Int32Array(1024);            // indices of live cells
    this.nlive = 0;
    this.cand = new Int32Array(4096);            // candidate list for one step
    this.gen = 0;
    this.lastChanges = 0;                        // births + deaths in the most recent step
    this.clear();
  }

  Grid.prototype.index = function (x, y) { return (y + this.oy) * this.GW + (x + this.ox); };

  /** Is (x, y) inside the grid and off the dead border? */
  Grid.prototype.inside = function (x, y) {
    var gx = x + this.ox, gy = y + this.oy;
    return gx > 0 && gy > 0 && gx < this.GW - 1 && gy < this.GH - 1;
  };

  Grid.prototype.clear = function () {
    this.cell.fill(0); this.born.fill(-1e9); this.died.fill(-1e9);
    this.nlive = 0; this.gen = 0; this.lastChanges = 0;
  };

  /** Replace the pattern with the given [x, y] cells and reset the generation counter. */
  Grid.prototype.load = function (cells) {
    this.clear();
    for (var i = 0; i < cells.length; i++) this.set(cells[i][0], cells[i][1], 1);
  };

  Grid.prototype.alive = function (x, y) { return this.inside(x, y) && this.cell[this.index(x, y)] === 1; };

  /** Set one cell by hand (used for drawing). Keeps the live list in sync. */
  Grid.prototype.set = function (x, y, v) {
    if (!this.inside(x, y)) return;
    var k = this.index(x, y);
    if (this.cell[k] === v) return;
    this.cell[k] = v;
    if (v) { this.born[k] = this.gen; this._push(k); }
    else { this.died[k] = this.gen; this._rebuild(); }
  };

  Object.defineProperty(Grid.prototype, 'population', { get: function () { return this.nlive; } });

  /** Advance one generation. */
  Grid.prototype.step = function () {
    var GW = this.GW, GH = this.GH, cell = this.cell, count = this.count, seen = this.seen;
    var live = this.live, nlive = this.nlive, nc = 0, i, k;
    var self = this;
    function add(k) {                                         // count a neighbour, list k once
      count[k]++;
      if (!seen[k]) { seen[k] = 1; if (nc === self.cand.length) self._growCand(); self.cand[nc++] = k; }
    }
    // 1. every live cell adds 1 to its 8 neighbours (and is itself a candidate)
    for (i = 0; i < nlive; i++) {
      k = live[i];
      if (!seen[k]) { seen[k] = 1; if (nc === this.cand.length) this._growCand(); this.cand[nc++] = k; }
      add(k - GW - 1); add(k - GW); add(k - GW + 1);
      add(k - 1);                   add(k + 1);
      add(k + GW - 1); add(k + GW); add(k + GW + 1);
    }
    // 2. apply B3/S23 to the candidates; the border ring is always dead
    var cand = this.cand, next = 0, gen = this.gen + 1, changes = 0;
    if (live.length < nc) { live = this.live = new Int32Array(nc * 2); }
    var births = [], deaths = [];
    for (i = 0; i < nc; i++) {
      k = cand[i];
      var x = k % GW, y = (k - x) / GW;
      var n = count[k], was = cell[k];
      var now = (x > 0 && y > 0 && x < GW - 1 && y < GH - 1) && (n === 3 || (n === 2 && was === 1)) ? 1 : 0;
      if (now !== was) (now ? births : deaths).push(k);
      if (now) live[next++] = k;
      count[k] = 0; seen[k] = 0;                              // reset scratch for next time
    }
    // 3. commit all changes at once (every cell updates simultaneously)
    for (i = 0; i < births.length; i++) { cell[births[i]] = 1; this.born[births[i]] = gen; }
    for (i = 0; i < deaths.length; i++) { cell[deaths[i]] = 0; this.died[deaths[i]] = gen; }
    this.nlive = next; this.gen = gen;
    this.lastChanges = births.length + deaths.length;
  };

  /** Generations since (x, y) was born / died (Infinity if never). Used for colour and trails. */
  Grid.prototype.ageAt = function (x, y) { var b = this.born[this.index(x, y)]; return b < -1e8 ? Infinity : this.gen - b; };
  Grid.prototype.deadFor = function (x, y) { var d = this.died[this.index(x, y)]; return d < -1e8 ? Infinity : this.gen - d; };

  /** True if the live cells are exactly `cells` (an array of [x, y]). */
  Grid.prototype.matches = function (cells) {
    if (cells.length !== this.nlive) return false;
    for (var i = 0; i < cells.length; i++) if (!this.alive(cells[i][0], cells[i][1])) return false;
    return true;
  };

  /** Live cells as [x, y] pairs in view coordinates. */
  Grid.prototype.cells = function () {
    var out = [];
    for (var i = 0; i < this.nlive; i++) {
      var k = this.live[i], gx = k % this.GW, gy = (k - gx) / this.GW;
      out.push([gx - this.ox, gy - this.oy]);
    }
    return out;
  };

  /** A cheap fingerprint of the current pattern (used to notice when a soup stops changing). */
  Grid.prototype.hash = function () {
    var h = this.nlive >>> 0, l = Array.prototype.slice.call(this.live, 0, this.nlive).sort(function (a, b) { return a - b; });
    for (var i = 0; i < l.length; i++) h = (Math.imul(h, 31) + l[i]) >>> 0;
    return h;
  };

  Grid.prototype._push = function (k) {
    if (this.nlive === this.live.length) { var a = new Int32Array(this.live.length * 2); a.set(this.live); this.live = a; }
    this.live[this.nlive++] = k;
  };
  Grid.prototype._rebuild = function () {
    this.nlive = 0;
    for (var k = 0; k < this.cell.length; k++) if (this.cell[k]) this._push(k);
  };
  Grid.prototype._growCand = function () { var a = new Int32Array(this.cand.length * 2); a.set(this.cand); this.cand = a; };

  // ─── RLE: the standard Life pattern text format ───────────────────────────────────────
  //   "x = 3, y = 3, rule = B3/S23\nbo$2bo$3o!"  is a glider:
  //   b = dead, o = alive, $ = end of row, a number repeats what follows, ! = end.

  /** Parse RLE text into [x, y] cells (top-left of the pattern is 0, 0). */
  function parseRLE(text) {
    var body = text.split('\n').filter(function (l) { return l && l[0] !== '#' && !/^\s*x\s*=/.test(l); }).join('');
    var cells = [], x = 0, y = 0, num = '';
    for (var i = 0; i < body.length; i++) {
      var ch = body[i];
      if (ch >= '0' && ch <= '9') { num += ch; continue; }
      var n = num ? parseInt(num, 10) : 1; num = '';
      if (ch === 'b' || ch === '.') x += n;
      else if (ch === 'o' || ch === 'A') { for (var j = 0; j < n; j++) cells.push([x + j, y]); x += n; }
      else if (ch === '$') { y += n; x = 0; }
      else if (ch === '!') break;
    }
    return cells;
  }

  /** Encode [x, y] cells as RLE (shifted so the pattern's top-left is 0, 0). */
  function toRLE(cells, comment) {
    if (!cells.length) return 'x = 0, y = 0, rule = B3/S23\n!';
    var minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity, set = {};
    cells.forEach(function (c) {
      minx = Math.min(minx, c[0]); miny = Math.min(miny, c[1]);
      maxx = Math.max(maxx, c[0]); maxy = Math.max(maxy, c[1]); set[c[0] + ',' + c[1]] = 1;
    });
    var rows = [];
    for (var y = miny; y <= maxy; y++) {
      var row = '', run = 0, cur = '';
      for (var x = minx; x <= maxx + 1; x++) {
        var ch = x <= maxx && set[x + ',' + y] ? 'o' : 'b';
        if (ch === cur) run++;
        else { if (run) row += (run > 1 ? run : '') + cur; cur = ch; run = 1; }
      }
      rows.push(row.replace(/\d*b$/, ''));
    }
    var body = rows.join('$').replace(/(\$+)/g, function (m) { return m.length > 1 ? m.length + '$' : '$'; }) + '!';
    var lines = body.match(/.{1,70}/g).join('\n');
    return (comment ? '#C ' + comment + '\n' : '') +
      'x = ' + (maxx - minx + 1) + ', y = ' + (maxy - miny + 1) + ', rule = B3/S23\n' + lines;
  }

  global.LifeEngine = { Grid: Grid, parseRLE: parseRLE, toRLE: toRLE };
})(typeof window !== 'undefined' ? window : globalThis);
