/*
  Home page hero: Conway's Game of Life (B3/S23) in a panel beside the headline.

  Three scenes, chosen with the tabs under the panel:
    chain  – one glider ricochets off one-time turners and leaves four 2×2 blocks.
             Each block is swapped for a real <button> the moment it settles, and
             opens a modal with links into the site.
    spell  – about 140 gliders fly in from outside the panel; each pair collides into
             one block, and the blocks spell ALIFE over EDU.
    soup   – a random 20×20 soup that runs until it settles. Click or drag to draw.

  The chain and spell scenes were found offline by search and verified by simulation
  (see _data/life_scenes.json). Nothing is scripted after generation 0: the page only
  applies the Life rule, then checks its final state against the stored one. The one
  thing it "knows" in advance is when each link block settles.

  Pauses when off-screen or in a background tab. With prefers-reduced-motion the
  chain scene opens at rest, and nothing plays until asked.
*/
(function () {
  'use strict';
  var root = document.querySelector('.life-panel');
  var dataEl = document.getElementById('life-data');
  if (!root || !dataEl) return;
  var DATA = JSON.parse(dataEl.textContent);

  var stage = root.querySelector('.life-stage');
  var canvas = root.querySelector('canvas');
  var ctx = canvas.getContext('2d');
  var genEl = root.querySelector('[data-life="gen"]');
  var speedEl = root.querySelector('[data-life="speed"]');
  var playBtn = root.querySelector('[data-life="play"]');
  var tabs = Array.prototype.slice.call(root.querySelectorAll('[data-scene-tab]'));
  var caps = Array.prototype.slice.call(root.querySelectorAll('[data-scene-cap]'));
  var soupTools = root.querySelector('[data-life="soup-tools"]');
  var buttons = Array.prototype.slice.call(stage.querySelectorAll('.life-block'));
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  var SPEEDS = [0.25, 0.5, 1, 2, 4, 8];
  var speedIdx = 2;
  var NUM = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];

  var css = getComputedStyle(document.documentElement);
  function tok(n, fb) { return (css.getPropertyValue(n) || '').trim() || fb; }
  var COL = {
    bg: tok('--bg', '#0e0e0c'), cell: tok('--life-cell', '#8d8a82'), live: tok('--life-live', '#3dcba0'),
    word: tok('--text', '#f0ede6'), grid: tok('--life-grid', 'rgba(255,255,255,0.035)')
  };

  // ── engine: sparse B3/S23 on a bounded grid whose outer ring is held dead ──
  var S = null;              // current scene definition
  var W, H, OX, OY, GW, GH;
  var grid, cnt, born, died, mark, live = [], nlive = 0, gen = 0;
  var shown = 0, verified = null, settled = false;
  var hist = [];             // soup: recent state hashes, to detect rest

  function alloc() {
    var n = GW * GH;
    grid = new Uint8Array(n); cnt = new Uint8Array(n);
    born = new Int32Array(n).fill(-1e9); died = new Int32Array(n).fill(-1e9);
    mark = new Uint8Array(n);
    live = new Int32Array(Math.max(1024, n >> 3)); nlive = 0;
  }
  function setLive(k) {
    if (grid[k]) return;
    grid[k] = 1;
    if (nlive === live.length) { var nl = new Int32Array(live.length * 2); nl.set(live); live = nl; }
    live[nlive++] = k;
  }
  function rebuildLive() {
    nlive = 0;
    for (var k = 0; k < grid.length; k++) if (grid[k]) {
      if (nlive === live.length) { var nl = new Int32Array(live.length * 2); nl.set(live); live = nl; }
      live[nlive++] = k;
    }
  }
  var touched = new Int32Array(4096), ntouched = 0;
  function touch(k) {
    if (cnt[k]++ === 0 && !mark[k]) {
      mark[k] = 1;
      if (ntouched === touched.length) { var nt = new Int32Array(touched.length * 2); nt.set(touched); touched = nt; }
      touched[ntouched++] = k;
    }
  }
  function step() {
    gen++;
    ntouched = 0;
    var i, k;
    for (i = 0; i < nlive; i++) {
      k = live[i];
      if (!mark[k]) {           // the cell itself is a candidate even with 0 neighbours
        mark[k] = 1;
        if (ntouched === touched.length) { var nt = new Int32Array(touched.length * 2); nt.set(touched); touched = nt; }
        touched[ntouched++] = k;
      }
      touch(k - GW - 1); touch(k - GW); touch(k - GW + 1); touch(k - 1);
      touch(k + 1); touch(k + GW - 1); touch(k + GW); touch(k + GW + 1);
    }
    var nn = 0, out = live.length >= ntouched ? live : new Int32Array(ntouched * 2);
    var changes = [];
    for (i = 0; i < ntouched; i++) {
      k = touched[i];
      var c = cnt[k], was = grid[k];
      var x = k % GW, y = (k / GW) | 0;
      var v = (x > 0 && y > 0 && x < GW - 1 && y < GH - 1) && (c === 3 || (c === 2 && was)) ? 1 : 0;
      if (v !== was) changes.push(k);
      if (v) out[nn++] = k;
      cnt[k] = 0; mark[k] = 0;
    }
    for (i = 0; i < changes.length; i++) {
      k = changes[i];
      if (grid[k]) { grid[k] = 0; died[k] = gen; } else { grid[k] = 1; born[k] = gen; }
    }
    live = out; nlive = nn;
    if (S.kind === 'chain') {
      while (shown < S.blocks.length && S.blocks[shown].t <= gen) reveal(shown++, true);
    }
    if (S.final && gen === S.endGen) check();
    if (S.kind === 'soup') watchSoup(changes.length);
  }
  function idx(x, y) { return (y + OY) * GW + (x + OX); }

  function check() {
    var want = {}, n = 0, ok = true;
    S.final.forEach(function (c) { want[idx(c[0], c[1])] = 1; });
    for (var i = 0; i < nlive; i++) { n++; if (!want[live[i]]) ok = false; }
    verified = ok && n === S.final.length;
    settled = true;
  }

  // soup: at rest once the pattern repeats with period 1 or 2 for 40 generations
  var restRun = 0;
  function watchSoup(nchanges) {
    var h = nlive * 2654435761 >>> 0;
    for (var i = 0; i < nlive; i += 7) h = (h ^ (live[i] * 2246822519)) >>> 0;
    hist.push(h); if (hist.length > 3) hist.shift();
    var rep = nchanges === 0 || (hist.length === 3 && hist[0] === hist[2]);
    restRun = rep ? restRun + 1 : 0;
    if (restRun >= 40) settled = true;
  }

  // ── scenes ──
  var sceneIdx = 0, seed = 1;
  function load(i) {
    S = DATA.scenes[i]; sceneIdx = i;
    W = S.W; H = S.H; OX = S.ox; OY = S.oy; GW = S.GW; GH = S.GH;
    alloc(); gen = 0; shown = 0; verified = null; settled = false; hist = []; restRun = 0;
    if (S.kind === 'soup') makeSoup(); else S.start.forEach(function (c) { setLive(idx(c[0], c[1])); });
    tabs.forEach(function (t, j) { t.setAttribute('aria-selected', j === i ? 'true' : 'false'); t.tabIndex = j === i ? 0 : -1; });
    caps.forEach(function (c) { c.hidden = c.getAttribute('data-scene-cap') !== S.id; });
    if (soupTools) soupTools.hidden = S.kind !== 'soup';
    stage.classList.toggle('is-drawable', S.kind === 'soup');
    stage.setAttribute('aria-label', S.label || 'Game of Life');
    var n = root.querySelector('[data-life="turners"]');
    if (n && S.turners) n.textContent = NUM[S.turners] || S.turners;
    var g = root.querySelector('[data-life="gliders"]');
    if (g && S.gliders) g.textContent = S.gliders;
    buttons.forEach(function (b) { b.classList.add('is-pending'); b.classList.remove('born'); b.tabIndex = -1; b.setAttribute('aria-hidden', 'true'); });
    if (S.kind === 'chain') positionButtons();
  }
  function makeSoup() {
    var r = mulberry32(seed), n = S.soup, x0 = ((W - n) / 2) | 0, y0 = ((H - n) / 2) | 0;
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) if (r() < 0.5) setLive(idx(x0 + x, y0 + y));
    var sl = root.querySelector('[data-life="soup-seed"]'); if (sl) sl.textContent = seed;
  }
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      var t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  // ── link blocks (chain scene) ──
  function positionButtons() {
    buttons.forEach(function (b, k) {
      var bl = S.blocks[k]; if (!bl) return;
      b.style.left = (bl.x / W * 100) + '%'; b.style.top = (bl.y / H * 100) + '%';
      b.style.width = (2 / W * 100) + '%'; b.style.height = (2 / H * 100) + '%';
    });
  }
  function reveal(k, animate) {
    var b = buttons[k]; if (!b) return;
    b.classList.remove('is-pending'); b.tabIndex = 0; b.removeAttribute('aria-hidden');
    placeLabels();
    if (animate && !reduce.matches) { b.classList.remove('born'); void b.offsetWidth; b.classList.add('born'); }
  }
  // Put each visible label on whichever side of its block keeps it inside the panel and
  // clear of the other labels and blocks. Re-run on every reveal and resize.
  function placeLabels() {
    var sr = stage.getBoundingClientRect();
    var placed = [];
    var squares = buttons.filter(function (b) { return !b.classList.contains('is-pending'); }).map(function (b) {
      var r = b.getBoundingClientRect(); return { l: r.left - sr.left - 6, t: r.top - sr.top - 6, r: r.right - sr.left + 6, b: r.bottom - sr.top + 6, el: b };
    });
    var SIDES = ['right', 'left', 'above', 'below'];
    buttons.forEach(function (b) {
      if (b.classList.contains('is-pending')) return;
      var lbl = b.querySelector('.lbl');
      var br = b.getBoundingClientRect(), lw = lbl.offsetWidth, lh = lbl.offsetHeight, gap = 7;
      var cx = (br.left + br.right) / 2 - sr.left, cy = (br.top + br.bottom) / 2 - sr.top;
      var best = null;
      for (var s = 0; s < SIDES.length; s++) {
        var side = SIDES[s], rect;
        if (side === 'right') rect = { l: br.right - sr.left + gap, t: cy - lh / 2 };
        if (side === 'left') rect = { l: br.left - sr.left - gap - lw, t: cy - lh / 2 };
        if (side === 'above') rect = { l: cx - lw / 2, t: br.top - sr.top - gap - lh };
        if (side === 'below') rect = { l: cx - lw / 2, t: br.bottom - sr.top + gap };
        rect.r = rect.l + lw; rect.b = rect.t + lh;
        var cost = 0;
        if (rect.l < 2 || rect.t < 2 || rect.r > sr.width - 2 || rect.b > sr.height - 2) cost += 100;
        placed.forEach(function (p) { cost += 50 * overlap(rect, p); });
        squares.forEach(function (q) { if (q.el !== b) cost += 30 * overlap(rect, q); });
        cost += s * 0.5;                       // prefer right, then left, above, below
        if (!best || cost < best.cost) best = { cost: cost, side: side, rect: rect };
      }
      b.setAttribute('data-side', best.side);
      placed.push(best.rect);
    });
  }
  function overlap(a, b) {
    var x = Math.min(a.r, b.r) - Math.max(a.l, b.l), y = Math.min(a.b, b.b) - Math.max(a.t, b.t);
    return x > 0 && y > 0 ? 1 : 0;
  }

  // ── drawing ──
  var dpr = 1, cw = 0, ch = 0;
  function resize() {
    var r = stage.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    cw = r.width; ch = r.height;
    canvas.width = Math.round(cw * dpr); canvas.height = Math.round(ch * dpr);
    if (S && S.kind === 'chain') placeLabels();
    draw();
  }
  function rgba(hex, a) {
    var n = parseInt(hex.replace('#', ''), 16);
    return 'rgba(' + (n >> 16 & 255) + ',' + (n >> 8 & 255) + ',' + (n & 255) + ',' + a + ')';
  }
  var hidden = {};          // cells drawn as HTML buttons instead
  function draw() {
    if (!S || !cw) return;
    var sx = cw / W, sy = ch / H;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = COL.bg; ctx.fillRect(0, 0, cw, ch);
    if (sx >= 4) {
      ctx.strokeStyle = COL.grid; ctx.lineWidth = 1; ctx.beginPath();
      for (var gx = 1; gx < W; gx++) { var px = Math.round(gx * sx) + 0.5; ctx.moveTo(px, 0); ctx.lineTo(px, ch); }
      for (var gy = 1; gy < H; gy++) { var py = Math.round(gy * sy) + 0.5; ctx.moveTo(0, py); ctx.lineTo(cw, py); }
      ctx.stroke();
    }
    hidden = {};
    if (S.kind === 'chain') for (var b = 0; b < shown; b++) {
      var bl = S.blocks[b];
      hidden[idx(bl.x, bl.y)] = hidden[idx(bl.x + 1, bl.y)] = hidden[idx(bl.x, bl.y + 1)] = hidden[idx(bl.x + 1, bl.y + 1)] = 1;
    }
    var gap = sx >= 5 ? 1 : 0, TRAIL = reduce.matches ? 0 : 28;
    var restCol = S.kind === 'spell' ? COL.word : COL.cell;
    var trailCol = rgba(COL.live, 1);
    for (var y = 0; y < H; y++) {
      var row = (y + OY) * GW + OX;
      var y0 = Math.round(y * sy), hh = Math.round((y + 1) * sy) - y0 - gap;
      for (var x = 0; x < W; x++) {
        var k = row + x;
        var x0 = Math.round(x * sx), ww = Math.round((x + 1) * sx) - x0 - gap;
        if (grid[k]) {
          if (hidden[k]) continue;
          ctx.globalAlpha = 1;
          ctx.fillStyle = !settled && born[k] > 0 && gen - born[k] < 5 ? COL.live : restCol;
          ctx.fillRect(x0, y0, ww, hh);
        } else if (TRAIL && died[k] > 0) {
          var a = gen - died[k];
          if (a > 0 && a < TRAIL) {
            ctx.globalAlpha = 0.28 * (1 - a / TRAIL);
            ctx.fillStyle = trailCol; ctx.fillRect(x0, y0, ww, hh);
          }
        }
      }
    }
    ctx.globalAlpha = 1;
    updateReadout();
  }
  function updateReadout() {
    var txt;
    if (S.kind === 'soup') txt = (settled ? 'at rest · ' : '') + 'gen ' + gen + ' · ' + nlive + ' cells';
    else if (gen >= S.endGen) txt = 'at rest · gen ' + gen + (verified ? ' ✓' : verified === false ? ' ✗' : '');
    else txt = 'gen ' + gen + ' / ' + S.endGen;
    genEl.textContent = txt;
    if (verified) genEl.title = 'Final state matches the stored, independently computed run';
    else genEl.removeAttribute('title');
  }

  // ── loop ──
  var running = false, visible = true, acc = 0, last = 0, raf = 0;
  function gps() {
    var base = S.kind === 'soup' ? S.gps : S.endGen / S.seconds;
    return base * SPEEDS[speedIdx];
  }
  function done() { return S.kind === 'soup' ? settled : gen >= S.endGen; }
  function frame(now) {
    raf = 0;
    if (!running || !visible || document.hidden) { last = 0; return; }
    var dt = last ? Math.min(0.1, (now - last) / 1000) : 0; last = now;
    acc += dt * gps();
    var budget = 400;                          // cap work per frame at high speed
    while (acc >= 1 && !done() && budget-- > 0) { step(); acc -= 1; }
    if (budget <= 0) acc = 0;
    draw();
    if (done()) { running = false; syncPlay(); return; }
    raf = requestAnimationFrame(frame);
  }
  function play() {
    if (done()) start(sceneIdx, true);
    running = true; last = 0; syncPlay();
    if (!raf) raf = requestAnimationFrame(frame);
  }
  function pause() { running = false; syncPlay(); }
  function syncPlay() {
    var p = running;
    playBtn.setAttribute('aria-pressed', p ? 'false' : 'true');
    playBtn.setAttribute('aria-label', p ? 'Pause' : (done() ? 'Replay' : 'Play'));
    playBtn.textContent = p ? 'Pause' : (done() ? 'Replay' : 'Play');
  }
  function start(i, animate) {
    running = false;
    load(i); acc = 0;
    if (!animate) { if (S.kind !== 'soup') { while (gen < S.endGen) step(); finishReveal(); } draw(); syncPlay(); return; }
    draw(); play();
  }
  function finishReveal() { buttons.forEach(function (b) { b.classList.remove('born'); }); }
  function setSpeed(d) {
    speedIdx = Math.max(0, Math.min(SPEEDS.length - 1, speedIdx + d));
    var s = SPEEDS[speedIdx];
    speedEl.textContent = (s < 1 ? (s === 0.25 ? '¼' : '½') : s) + '×';
    root.querySelector('[data-life="slower"]').disabled = speedIdx === 0;
    root.querySelector('[data-life="faster"]').disabled = speedIdx === SPEEDS.length - 1;
  }

  // ── controls ──
  playBtn.addEventListener('click', function () { running ? pause() : play(); });
  root.querySelector('[data-life="slower"]').addEventListener('click', function () { setSpeed(-1); });
  root.querySelector('[data-life="faster"]').addEventListener('click', function () { setSpeed(1); });
  tabs.forEach(function (t, j) {
    t.addEventListener('click', function () { start(j, !reduce.matches); });
    t.addEventListener('keydown', function (e) {
      var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      var n = (j + d + tabs.length) % tabs.length; tabs[n].focus(); start(n, !reduce.matches);
    });
  });
  var newSoup = root.querySelector('[data-life="soup-new"]');
  if (newSoup) newSoup.addEventListener('click', function () { seed++; start(sceneIdx, true); });
  var clearBtn = root.querySelector('[data-life="soup-clear"]');
  if (clearBtn) clearBtn.addEventListener('click', function () {
    running = false; load(sceneIdx);
    grid.fill(0); nlive = 0; born.fill(-1e9); died.fill(-1e9); settled = true; draw(); syncPlay();
  });

  // drawing on the soup scene
  var painting = -1;
  function cellAt(e) {
    var r = stage.getBoundingClientRect();
    return [Math.floor((e.clientX - r.left) / r.width * W), Math.floor((e.clientY - r.top) / r.height * H)];
  }
  stage.addEventListener('pointerdown', function (e) {
    if (S.kind !== 'soup' || e.target.closest('.life-block')) return;
    var c = cellAt(e), k = idx(c[0], c[1]);
    painting = grid[k] ? 0 : 1; paint(c);
    stage.setPointerCapture(e.pointerId); e.preventDefault();
  });
  stage.addEventListener('pointermove', function (e) { if (painting >= 0) paint(cellAt(e)); });
  stage.addEventListener('pointerup', function () {
    if (painting < 0) return;
    painting = -1; settled = false; restRun = 0; hist = [];
    if (!running) play();
  });
  function paint(c) {
    if (c[0] < 0 || c[1] < 0 || c[0] >= W || c[1] >= H) return;
    var k = idx(c[0], c[1]);
    if (painting === 1 && !grid[k]) { grid[k] = 1; born[k] = gen; rebuildLive(); }
    if (painting === 0 && grid[k]) { grid[k] = 0; died[k] = gen; rebuildLive(); }
    draw();
  }

  // ── link modals ──
  buttons.forEach(function (b, k) {
    b.addEventListener('click', function () {
      var d = document.getElementById(b.getAttribute('data-dialog'));
      if (!d) return;
      var o = d.querySelector('.bm-origin');
      if (o && S.blocks[k]) o.textContent = 'Block ' + (k + 1) + ' of 4 · settled at generation ' + S.blocks[k].t;
      d.showModal();
    });
  });
  Array.prototype.forEach.call(document.querySelectorAll('dialog.block-modal'), function (d) {
    d.querySelector('.bm-close').addEventListener('click', function () { d.close(); });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
    Array.prototype.forEach.call(d.querySelectorAll('[data-close]'), function (a) {
      a.addEventListener('click', function () { d.close(); });
    });
  });

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (e) { visible = e[0].isIntersecting; if (running && !raf) raf = requestAnimationFrame(frame); }).observe(stage);
  }
  document.addEventListener('visibilitychange', function () { if (running && !raf) raf = requestAnimationFrame(frame); });
  var rt = 0;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(resize, 120); });

  // headless self-check, handy from the console: lifeCheck() -> [true, true]
  window.lifeCheck = function () {
    var keep = sceneIdx, out = [];
    DATA.scenes.forEach(function (sc, j) {
      if (!sc.final) return;
      load(j); while (gen < sc.endGen) step(); out.push(verified);
    });
    start(keep, false);
    return out;
  };

  setSpeed(0);
  resize();
  start(0, !reduce.matches);
})();
