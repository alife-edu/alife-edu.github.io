/*
  life/panel.js — an interactive viewer for Life scenes. Needs life/engine.js first.

  ─── What it does ────────────────────────────────────────────────────────────────────
  Finds every element with a `data-life-panel` attribute, loads the scene files listed in
  its `data-scenes` attribute (space-separated URLs of JSON files, see life/scenes/), and
  builds inside it:

      a canvas that draws the visible window of the grid
      a tab per scene, Play/Pause, slower/faster (¼× … 8×), and optionally Step
      a caption (the scene's description) and a readout (generation, check result)

  It knows nothing about the website around it. Scenes of kind "links" mark some of their
  final 2×2 blocks as links; when one settles, the panel lays a real <button> over its
  four cells. Clicking it fires a `life:link` event on the panel element:

      panel.addEventListener('life:link', function (e) {
        e.detail.index   // 0, 1, 2 … which link block
        e.detail.id      // the data-life-link value of the button supplied for it, if any
        e.detail.block   // { x, y, t } its cells and the generation it settled
      });

  If the page supplies buttons inside the panel element, like
      <button data-life-link="events">Upcoming events</button>
  they are used, in order, for the link blocks (their text becomes the label). Otherwise
  the panel makes plain "Block 1", "Block 2" … buttons.

  Attributes on the panel element:
      data-scenes="a.json b.json"    scene files, in tab order (required)
      data-extras="step rle"          extra controls: a Step button, an RLE box
      data-autoplay="false"           don't start playing on load

  ─── Scene kinds ─────────────────────────────────────────────────────────────────────
      "links"   a precomputed run with link blocks (the turner chain)
      "run"     a precomputed run (the ALIFE·EDU synthesis)
      "soup"    a random soup made in the browser; you can draw on it

  For precomputed runs the file stores the final state. When the run reaches endGen the
  panel compares the live cells with it and shows ✓ or ✗: a check, in your browser, that
  the animation really is the Life rule applied to the starting pattern.

  ─── Accessibility and courtesy ─────────────────────────────────────────────────────
  Pauses when scrolled off-screen or in a background tab. With prefers-reduced-motion the
  first scene opens already finished (its link blocks ready) and nothing plays unasked.
*/
(function () {
  'use strict';
  if (!window.LifeEngine) { console.error('life/panel.js needs life/engine.js loaded first'); return; }

  var SPEEDS = [0.25, 0.5, 1, 2, 4, 8];
  var SPEED_LABEL = ['\u00bc\u00d7', '\u00bd\u00d7', '1\u00d7', '2\u00d7', '4\u00d7', '8\u00d7'];
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  function el(tag, attrs, text) {
    var e = document.createElement(tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text != null) e.textContent = text;
    return e;
  }

  function Panel(root, scenes) {
    this.root = root; this.scenes = scenes;
    this.extras = (root.getAttribute('data-extras') || '').split(/\s+/);
    this.speedIdx = 2; this.running = false; this.visible = true;
    this.acc = 0; this.last = 0; this.raf = 0; this.soupSeed = 1;
    this.build();
    var self = this;
    this.frame = function (now) { self._frame(now); };
    window.addEventListener('resize', function () { clearTimeout(self._rt); self._rt = setTimeout(function () { self.resize(); }, 120); });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (e) { self.visible = e[0].isIntersecting; self.kick(); }).observe(this.stage);
    }
    document.addEventListener('visibilitychange', function () { self.kick(); });
    this.resize();
    var auto = root.getAttribute('data-autoplay') !== 'false' && !reduceMotion.matches;
    this.show(0, auto);
  }

  // ─── building the DOM ──────────────────────────────────────────────────────────────
  Panel.prototype.build = function () {
    var root = this.root, self = this;
    root.classList.add('life-panel');
    this.linkButtons = Array.prototype.slice.call(root.querySelectorAll('[data-life-link]'));
    this.captions = Array.prototype.slice.call(root.querySelectorAll('[data-scene-cap]'));

    this.stage = el('div', { 'class': 'life-stage' });
    this.canvas = el('canvas', { 'aria-hidden': 'true' });
    this.stage.appendChild(this.canvas);
    this.ctx = this.canvas.getContext('2d');

    var bar = el('div', { 'class': 'life-bar' });
    this.tabs = el('div', { 'class': 'life-tabs', role: 'tablist', 'aria-label': 'Scenes' });
    this.scenes.forEach(function (s, i) {
      var b = el('button', { type: 'button', role: 'tab' }, s.title || s.id);
      b.addEventListener('click', function () { self.show(i, !reduceMotion.matches); });
      b.addEventListener('keydown', function (e) {
        var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (!d) return;
        e.preventDefault();
        var n = (i + d + self.scenes.length) % self.scenes.length;
        self.tabs.children[n].focus(); self.show(n, !reduceMotion.matches);
      });
      self.tabs.appendChild(b);
    });
    var ctl = el('div', { 'class': 'life-controls', role: 'group', 'aria-label': 'Playback' });
    this.playBtn = el('button', { type: 'button' }, 'Pause');
    this.slowBtn = el('button', { type: 'button', 'aria-label': 'Slower' }, '\u2212');
    this.speedOut = el('span', { 'class': 'life-speed', 'aria-live': 'polite' }, '1\u00d7');
    this.fastBtn = el('button', { type: 'button', 'aria-label': 'Faster' }, '+');
    ctl.appendChild(this.playBtn); ctl.appendChild(this.slowBtn); ctl.appendChild(this.speedOut); ctl.appendChild(this.fastBtn);
    if (this.extras.indexOf('step') >= 0) {
      this.stepBtn = el('button', { type: 'button' }, 'Step');
      this.stepBtn.addEventListener('click', function () { self.pause(); if (!self.done()) { self.step(); self.draw(); } });
      ctl.appendChild(this.stepBtn);
    }
    bar.appendChild(this.tabs); bar.appendChild(ctl);
    this.playBtn.addEventListener('click', function () { self.running ? self.pause() : self.play(); });
    this.slowBtn.addEventListener('click', function () { self.setSpeed(-1); });
    this.fastBtn.addEventListener('click', function () { self.setSpeed(1); });

    var cap = el('div', { 'class': 'life-caption' });
    this.desc = el('p', { 'class': 'life-desc' });
    this.soupTools = el('span', { 'class': 'life-soup-tools' });
    var nb = el('button', { type: 'button' }, 'New soup'), cb = el('button', { type: 'button' }, 'Clear');
    this.seedOut = el('span', { 'class': 'life-seed' });
    this.soupTools.appendChild(nb); this.soupTools.appendChild(cb); this.soupTools.appendChild(this.seedOut);
    nb.addEventListener('click', function () { self.soupSeed++; self.show(self.idx, true); });
    cb.addEventListener('click', function () { self.pause(); self.grid.clear(); self.settled = true; self.draw(); self.syncPlay(); });
    this.readout = el('p', { 'class': 'life-readout' });
    this.genOut = el('span');
    this.readout.appendChild(this.genOut);
    this.readout.appendChild(document.createTextNode(" \u00b7 Conway's Game of Life, B3/S23"));
    cap.appendChild(this.desc);
    this.captions.forEach(function (c) { cap.appendChild(c); });
    cap.appendChild(this.readout);
    if (this.extras.indexOf('rle') >= 0) {
      var det = el('details', { 'class': 'life-rle' });
      det.appendChild(el('summary', {}, 'Starting pattern as RLE (paste into Golly or LifeViewer)'));
      this.rleBox = el('textarea', { readonly: '', rows: '6', 'aria-label': 'Starting pattern in RLE format', spellcheck: 'false' });
      det.appendChild(this.rleBox); cap.appendChild(det);
    }

    // link buttons: use the page's, or make our own
    var maxLinks = Math.max.apply(null, this.scenes.map(function (s) { return (s.links || []).length; }).concat([0]));
    for (var i = this.linkButtons.length; i < maxLinks; i++) {
      var b = el('button', {}, 'Block ' + (i + 1)); this.linkButtons.push(b);
    }
    this.linkButtons.forEach(function (b, i) {
      var label = b.textContent.trim();
      b.textContent = '';
      b.type = 'button';
      b.className = 'life-block is-pending';
      b.appendChild(el('span', { 'class': 'sq' }));
      b.appendChild(el('span', { 'class': 'lbl' }, label));
      b.tabIndex = -1; b.setAttribute('aria-hidden', 'true');
      b.addEventListener('click', function () {
        var s = self.scene;
        root.dispatchEvent(new CustomEvent('life:link', {
          bubbles: true,
          detail: { index: i, id: b.getAttribute('data-life-link'), block: s.links && s.links[i], scene: s.id }
        }));
      });
      self.stage.appendChild(b);
    });

    root.innerHTML = '';
    root.appendChild(this.stage); root.appendChild(bar); root.appendChild(cap);

    // drawing on soups
    this.painting = -1;
    this.stage.addEventListener('pointerdown', function (e) {
      if (self.scene.kind !== 'soup' || e.target.closest('.life-block')) return;
      var c = self.cellAt(e);
      self.painting = self.grid.alive(c[0], c[1]) ? 0 : 1;
      self.paint(c); self.stage.setPointerCapture(e.pointerId); e.preventDefault();
    });
    this.stage.addEventListener('pointermove', function (e) { if (self.painting >= 0) self.paint(self.cellAt(e)); });
    this.stage.addEventListener('pointerup', function () {
      if (self.painting < 0) return;
      self.painting = -1; self.settled = false; self.restRun = 0; self.hashes = [];
      if (!self.running) self.play();
    });
    this.setSpeed(0);
  };

  // ─── scenes ────────────────────────────────────────────────────────────────────────
  Panel.prototype.show = function (i, animate) {
    this.pause();
    var s = this.scene = this.scenes[i]; this.idx = i;
    this.grid = new LifeEngine.Grid(s);
    this.settled = false; this.verified = null; this.revealed = 0; this.restRun = 0; this.hashes = [];
    if (s.kind === 'soup') this.makeSoup(); else this.grid.load(s.start);
    // tabs, captions, tools
    for (var j = 0; j < this.tabs.children.length; j++) {
      this.tabs.children[j].setAttribute('aria-selected', j === i ? 'true' : 'false');
      this.tabs.children[j].tabIndex = j === i ? 0 : -1;
    }
    var own = this.captions.filter(function (c) { return c.getAttribute('data-scene-cap') === s.id; });
    this.captions.forEach(function (c) { c.hidden = own.indexOf(c) < 0; });
    this.desc.hidden = own.length > 0;
    this.desc.textContent = s.description || '';
    var where = own[0] || this.desc;
    if (s.kind === 'soup') where.appendChild(this.soupTools);
    this.soupTools.hidden = s.kind !== 'soup';
    this.stage.classList.toggle('is-drawable', s.kind === 'soup');
    this.stage.setAttribute('role', 'img');
    this.stage.setAttribute('aria-label', s.label || s.title || 'Game of Life');
    if (this.rleBox) this.rleBox.value = s.kind === 'soup' ? LifeEngine.toRLE(this.grid.cells(), 'soup seed ' + this.soupSeed)
      : LifeEngine.toRLE(s.start, (s.title || s.id) + ' \u2014 run ' + s.endGen + ' generations');
    // link blocks
    var links = s.links || [];
    this.linkButtons.forEach(function (b, k) {
      b.classList.add('is-pending'); b.classList.remove('born'); b.tabIndex = -1; b.setAttribute('aria-hidden', 'true');
      var bl = links[k]; if (!bl) return;
      b.style.left = (bl.x / s.W * 100) + '%'; b.style.top = (bl.y / s.H * 100) + '%';
      b.style.width = (2 / s.W * 100) + '%'; b.style.height = (2 / s.H * 100) + '%';
    });
    this.acc = 0;
    if (animate) { this.draw(); this.play(); }
    else {
      if (s.kind !== 'soup') { while (!this.done()) this.step(); }
      this.linkButtons.forEach(function (b) { b.classList.remove('born'); });
      this.draw(); this.syncPlay();
    }
  };

  Panel.prototype.makeSoup = function () {
    var s = this.scene, rnd = mulberry32(this.soupSeed), n = s.soup || 20;
    var x0 = ((s.W - n) / 2) | 0, y0 = ((s.H - n) / 2) | 0;
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) if (rnd() < (s.density || 0.5)) this.grid.set(x0 + x, y0 + y, 1);
    this.grid.gen = 0;
    this.seedOut.textContent = 'seed ' + this.soupSeed;
  };

  // A tiny seeded random-number generator, so "soup 7" is the same soup for everyone.
  function mulberry32(a) {
    return function () {
      a |= 0; a = a + 0x6D2B79F5 | 0;
      var t = Math.imul(a ^ a >>> 15, 1 | a);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }

  Panel.prototype.done = function () {
    return this.scene.kind === 'soup' ? this.settled : this.grid.gen >= this.scene.endGen;
  };

  Panel.prototype.step = function () {
    var g = this.grid, s = this.scene;
    g.step();
    var links = s.links || [];
    while (this.revealed < links.length && links[this.revealed].t <= g.gen) this.reveal(this.revealed++);
    if (s.final && g.gen === s.endGen) { this.verified = g.matches(s.final); this.settled = true; }
    if (s.kind === 'soup') {
      // at rest once the pattern repeats with period 1 or 2 for 40 generations
      var h = g.hash(); this.hashes.push(h); if (this.hashes.length > 3) this.hashes.shift();
      var rep = g.lastChanges === 0 || (this.hashes.length === 3 && this.hashes[0] === this.hashes[2]);
      this.restRun = rep ? this.restRun + 1 : 0;
      if (this.restRun >= 40) this.settled = true;
    }
  };

  // ─── link blocks ───────────────────────────────────────────────────────────────────
  Panel.prototype.reveal = function (k) {
    var b = this.linkButtons[k]; if (!b) return;
    b.classList.remove('is-pending'); b.tabIndex = 0; b.removeAttribute('aria-hidden');
    this.placeLabels();
    if (!reduceMotion.matches) { b.classList.remove('born'); void b.offsetWidth; b.classList.add('born'); }
  };

  // Put each visible label on whichever side of its block (right, left, above, below)
  // keeps it inside the panel and clear of the other labels and blocks.
  Panel.prototype.placeLabels = function () {
    var sr = this.stage.getBoundingClientRect();
    var shown = this.linkButtons.filter(function (b) { return !b.classList.contains('is-pending'); });
    var squares = shown.map(function (b) {
      var r = b.getBoundingClientRect();
      return { l: r.left - sr.left - 6, t: r.top - sr.top - 6, r: r.right - sr.left + 6, b: r.bottom - sr.top + 6, el: b };
    });
    var placed = [], SIDES = ['right', 'left', 'above', 'below'];
    function hit(a, b) { return Math.min(a.r, b.r) > Math.max(a.l, b.l) && Math.min(a.b, b.b) > Math.max(a.t, b.t); }
    shown.forEach(function (b) {
      var lbl = b.querySelector('.lbl'), br = b.getBoundingClientRect(), lw = lbl.offsetWidth, lh = lbl.offsetHeight, gap = 7;
      var cx = (br.left + br.right) / 2 - sr.left, cy = (br.top + br.bottom) / 2 - sr.top, best = null;
      SIDES.forEach(function (side, si) {
        var r = side === 'right' ? { l: br.right - sr.left + gap, t: cy - lh / 2 }
              : side === 'left' ? { l: br.left - sr.left - gap - lw, t: cy - lh / 2 }
              : side === 'above' ? { l: cx - lw / 2, t: br.top - sr.top - gap - lh }
              : { l: cx - lw / 2, t: br.bottom - sr.top + gap };
        r.r = r.l + lw; r.b = r.t + lh;
        var cost = si * 0.5;
        if (r.l < 2 || r.t < 2 || r.r > sr.width - 2 || r.b > sr.height - 2) cost += 100;
        placed.forEach(function (p) { if (hit(r, p)) cost += 50; });
        squares.forEach(function (q) { if (q.el !== b && hit(r, q)) cost += 30; });
        if (!best || cost < best.cost) best = { cost: cost, side: side, rect: r };
      });
      b.setAttribute('data-side', best.side);
      placed.push(best.rect);
    });
  };

  // ─── drawing ───────────────────────────────────────────────────────────────────────
  Panel.prototype.resize = function () {
    var r = this.stage.getBoundingClientRect();
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.cw = r.width; this.ch = r.height;
    this.canvas.width = Math.round(this.cw * this.dpr); this.canvas.height = Math.round(this.ch * this.dpr);
    var cs = getComputedStyle(this.root);
    function tok(n, fb) { return (cs.getPropertyValue(n) || '').trim() || fb; }
    this.col = {
      bg: tok('--life-bg', '#0e0e0c'), still: tok('--life-cell', '#8d8a82'), word: tok('--life-word', '#f0ede6'),
      live: tok('--life-live', '#3dcba0'), grid: tok('--life-grid', 'rgba(255,255,255,0.035)')
    };
    if (this.scene) { this.placeLabels(); this.draw(); }
  };

  Panel.prototype.draw = function () {
    var s = this.scene, g = this.grid, ctx = this.ctx, W = s.W, H = s.H, cw = this.cw, ch = this.ch;
    if (!cw) return;
    var sx = cw / W, sy = ch / H, c = this.col;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.fillStyle = c.bg; ctx.fillRect(0, 0, cw, ch);
    if (sx >= 4) {                                           // faint lattice
      ctx.strokeStyle = c.grid; ctx.lineWidth = 1; ctx.beginPath();
      for (var gx = 1; gx < W; gx++) { var px = Math.round(gx * sx) + 0.5; ctx.moveTo(px, 0); ctx.lineTo(px, ch); }
      for (var gy = 1; gy < H; gy++) { var py = Math.round(gy * sy) + 0.5; ctx.moveTo(0, py); ctx.lineTo(cw, py); }
      ctx.stroke();
    }
    var hide = {};                                           // cells shown as link buttons instead
    for (var b = 0; b < this.revealed; b++) {
      var bl = s.links[b];
      hide[bl.x + ',' + bl.y] = hide[(bl.x + 1) + ',' + bl.y] = hide[bl.x + ',' + (bl.y + 1)] = hide[(bl.x + 1) + ',' + (bl.y + 1)] = 1;
    }
    var gap = sx >= 5 ? 1 : 0, TRAIL = reduceMotion.matches ? 0 : 28;
    var rest = s.kind === 'run' ? c.word : c.still;
    for (var y = 0; y < H; y++) {
      var y0 = Math.round(y * sy), hh = Math.round((y + 1) * sy) - y0 - gap;
      for (var x = 0; x < W; x++) {
        var x0 = Math.round(x * sx), ww = Math.round((x + 1) * sx) - x0 - gap;
        if (g.alive(x, y)) {
          if (hide[x + ',' + y]) continue;
          // cells born in the last few generations are "moving"; the rest have settled
          ctx.globalAlpha = 1;
          ctx.fillStyle = !this.settled && g.ageAt(x, y) < 5 && g.gen > 0 ? c.live : rest;
          ctx.fillRect(x0, y0, ww, hh);
        } else if (TRAIL) {
          var a = g.deadFor(x, y);                           // fading trail where cells died
          if (a > 0 && a < TRAIL) {
            ctx.globalAlpha = 0.28 * (1 - a / TRAIL); ctx.fillStyle = c.live; ctx.fillRect(x0, y0, ww, hh);
          }
        }
      }
    }
    ctx.globalAlpha = 1;
    var txt;
    if (s.kind === 'soup') txt = (this.settled ? 'at rest \u00b7 ' : '') + 'gen ' + g.gen + ' \u00b7 ' + g.population + ' cells';
    else if (this.done()) txt = 'at rest \u00b7 gen ' + g.gen + (this.verified ? ' \u2713' : this.verified === false ? ' \u2717' : '');
    else txt = 'gen ' + g.gen + ' / ' + s.endGen;
    this.genOut.textContent = txt;
    if (this.verified) this.genOut.title = 'The final state matches the one stored in the scene file';
    else this.genOut.removeAttribute('title');
  };

  Panel.prototype.cellAt = function (e) {
    var r = this.stage.getBoundingClientRect(), s = this.scene;
    return [Math.floor((e.clientX - r.left) / r.width * s.W), Math.floor((e.clientY - r.top) / r.height * s.H)];
  };
  Panel.prototype.paint = function (c) {
    var s = this.scene;
    if (c[0] < 0 || c[1] < 0 || c[0] >= s.W || c[1] >= s.H) return;
    this.grid.set(c[0], c[1], this.painting); this.draw();
  };

  // ─── playback ──────────────────────────────────────────────────────────────────────
  // Precomputed runs last `seconds` at 1×; soups run at `gps` generations per second.
  Panel.prototype.gps = function () {
    var s = this.scene;
    return (s.kind === 'soup' ? (s.gps || 24) : s.endGen / (s.seconds || 24)) * SPEEDS[this.speedIdx];
  };
  Panel.prototype._frame = function (now) {
    this.raf = 0;
    if (!this.running || !this.visible || document.hidden) { this.last = 0; return; }
    var dt = this.last ? Math.min(0.1, (now - this.last) / 1000) : 0; this.last = now;
    this.acc += dt * this.gps();
    var budget = 400;                                        // never more than 400 steps a frame
    while (this.acc >= 1 && !this.done() && budget-- > 0) { this.step(); this.acc -= 1; }
    if (budget <= 0) this.acc = 0;
    this.draw();
    if (this.done()) { this.running = false; this.syncPlay(); return; }
    this.raf = requestAnimationFrame(this.frame);
  };
  Panel.prototype.kick = function () { if (this.running && !this.raf) this.raf = requestAnimationFrame(this.frame); };
  Panel.prototype.play = function () {
    if (this.done()) { this.show(this.idx, true); return; }
    this.running = true; this.last = 0; this.syncPlay(); this.kick();
  };
  Panel.prototype.pause = function () { this.running = false; this.syncPlay(); };
  Panel.prototype.syncPlay = function () {
    if (!this.scene) return;
    var t = this.running ? 'Pause' : (this.done() ? 'Replay' : 'Play');
    this.playBtn.textContent = t;
  };
  Panel.prototype.setSpeed = function (d) {
    this.speedIdx = Math.max(0, Math.min(SPEEDS.length - 1, this.speedIdx + d));
    this.speedOut.textContent = SPEED_LABEL[this.speedIdx];
    this.slowBtn.disabled = this.speedIdx === 0;
    this.fastBtn.disabled = this.speedIdx === SPEEDS.length - 1;
  };

  /** Re-run every precomputed scene to its end, headlessly; returns [true, true] if all match. */
  Panel.prototype.verifyAll = function () {
    var out = this.scenes.filter(function (s) { return s.final; }).map(function (s) {
      var g = new LifeEngine.Grid(s); g.load(s.start);
      while (g.gen < s.endGen) g.step();
      return g.matches(s.final);
    });
    return out;
  };

  // ─── start-up ──────────────────────────────────────────────────────────────────────
  function mount(root) {
    var urls = (root.getAttribute('data-scenes') || '').trim().split(/\s+/).filter(Boolean);
    return Promise.all(urls.map(function (u) {
      return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + ': ' + r.status); return r.json(); });
    })).then(function (scenes) {
      var p = new Panel(root, scenes);
      root.lifePanel = p;
      root.dispatchEvent(new CustomEvent('life:ready', { bubbles: true, detail: { panel: p } }));
      return p;
    }).catch(function (err) {
      console.error('Life panel: could not load scenes.', err);
      root.classList.add('life-panel--error');
      var msg = el('p', { 'class': 'life-error' }, 'The Game of Life scenes could not be loaded.' +
        (location.protocol === 'file:' ? ' Browsers block loading files from file:// \u2014 serve this folder, e.g. "python3 -m http.server", and open it from http://localhost.' : ''));
      root.appendChild(msg);
    });
  }

  window.LifePanel = { mount: mount, Panel: Panel };
  function init() { Array.prototype.forEach.call(document.querySelectorAll('[data-life-panel]'), mount); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
