/*
  Home page hero: a Gray–Scott reaction–diffusion culture in the "mitosis"
  regime (Pearson's type λ), drawn in the site's teal accent.
  Spots grow and divide until they fill the dish; now and then a region is
  slowly culled so the colony keeps recolonising instead of freezing.

  Click the culture to add a seed. Pauses when off-screen or in a background
  tab; with prefers-reduced-motion it shows a still frame and only animates
  briefly after a click.
*/
(function () {
  var canvas = document.querySelector('.hero-life');
  if (!canvas || !canvas.getContext) return;

  var F = 0.0367, K = 0.0649, DU = 1.0, DV = 0.5;
  var CELL = 4;              // CSS pixels per simulation cell
  var STEPS_PER_FRAME = 8;
  var WARMUP_STEPS = 700;    // so the first frame already shows a colony
  var CULL_EVERY = 420;      // frames between culls (~7 s at 60 fps)

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  // page background (#0e0e0c) → deep teal → accent teal (#3dcba0) → pale mint
  var STOPS = [[14,14,12],[12,40,34],[20,88,72],[38,150,118],[61,203,160],[150,232,208],[226,248,240]];
  var lut = new Uint8ClampedArray(256 * 3);
  for (var i = 0; i < 256; i++) {
    var t = i / 255 * (STOPS.length - 1);
    var j = Math.min(Math.floor(t), STOPS.length - 2), f = t - j;
    for (var c = 0; c < 3; c++) lut[i * 3 + c] = STOPS[j][c] + (STOPS[j + 1][c] - STOPS[j][c]) * f;
  }

  var ctx = canvas.getContext('2d');
  var off = document.createElement('canvas');
  var octx = off.getContext('2d');
  var w, h, u, v, nu, nv, xm, xp, img;
  var frame = 0, cull = null, visible = true, burstUntil = 0, rafId = 0;

  function seed(cx, cy, r) {
    for (var y = cy - r; y <= cy + r; y++) {
      for (var x = cx - r; x <= cx + r; x++) {
        var k = ((y + h) % h) * w + ((x + w) % w);
        u[k] = 0.5 + Math.random() * 0.05;
        v[k] = 0.25 + Math.random() * 0.05;
      }
    }
  }

  function init() {
    var rect = canvas.getBoundingClientRect();
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(rect.width * dpr));
    canvas.height = Math.max(1, Math.round(rect.height * dpr));
    w = Math.max(48, Math.round(rect.width / CELL));
    h = Math.max(36, Math.round(rect.height / CELL));
    u = new Float32Array(w * h).fill(1);
    v = new Float32Array(w * h);
    nu = new Float32Array(w * h);
    nv = new Float32Array(w * h);
    xm = new Int32Array(w); xp = new Int32Array(w);
    for (var x = 0; x < w; x++) { xm[x] = (x - 1 + w) % w; xp[x] = (x + 1) % w; }
    off.width = w; off.height = h;
    img = octx.createImageData(w, h);
    var seeds = Math.max(4, Math.round(w * h / 700));
    for (var s = 0; s < seeds; s++) seed((Math.random() * w) | 0, (Math.random() * h) | 0, 3);
    for (var n = 0; n < WARMUP_STEPS; n++) step();
    frame = 0; cull = null;
    draw();
  }

  function step() {
    for (var y = 0; y < h; y++) {
      var row = y * w, up = ((y - 1 + h) % h) * w, dn = ((y + 1) % h) * w;
      for (var x = 0; x < w; x++) {
        var k = row + x, l = xm[x], r = xp[x];
        var uc = u[k], vc = v[k];
        // 9-point Laplacian: 0.2 orthogonal, 0.05 diagonal, -1 centre
        var lu = 0.2 * (u[row + l] + u[row + r] + u[up + x] + u[dn + x])
               + 0.05 * (u[up + l] + u[up + r] + u[dn + l] + u[dn + r]) - uc;
        var lv = 0.2 * (v[row + l] + v[row + r] + v[up + x] + v[dn + x])
               + 0.05 * (v[up + l] + v[up + r] + v[dn + l] + v[dn + r]) - vc;
        var uvv = uc * vc * vc;
        nu[k] = uc + DU * lu - uvv + F * (1 - uc);
        nv[k] = vc + DV * lv + uvv - (F + K) * vc;
      }
    }
    var tu = u; u = nu; nu = tu;
    var tv = v; v = nv; nv = tv;
  }

  function applyCull() {
    if (!cull) return;
    var r2 = cull.r * cull.r;
    for (var y = -cull.r; y <= cull.r; y++) {
      for (var x = -cull.r; x <= cull.r; x++) {
        if (x * x + y * y > r2) continue;
        var k = ((cull.y + y + h) % h) * w + ((cull.x + x + w) % w);
        v[k] *= 0.93;
        u[k] += (1 - u[k]) * 0.07;
      }
    }
    if (--cull.frames <= 0) cull = null;
  }

  function draw() {
    var d = img.data;
    for (var k = 0, p = 0; k < w * h; k++, p += 4) {
      // peak v is ~0.4; cap below the palest stop so spots stay teal, not white
      var t = v[k] / 0.52;
      t = t <= 0 ? 0 : t >= 1 ? 230 : (Math.pow(t, 0.8) * 230) | 0;
      d[p] = lut[t * 3]; d[p + 1] = lut[t * 3 + 1]; d[p + 2] = lut[t * 3 + 2]; d[p + 3] = 255;
    }
    octx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(off, 0, 0, canvas.width, canvas.height);
  }

  function shouldRun() {
    if (!visible || document.hidden) return false;
    return !reduceMotion.matches || performance.now() < burstUntil;
  }

  function tick() {
    rafId = 0;
    if (!shouldRun()) return;
    for (var n = 0; n < STEPS_PER_FRAME; n++) { step(); applyCull(); }
    if (++frame % CULL_EVERY === 0 && !reduceMotion.matches) {
      cull = { x: (Math.random() * w) | 0, y: (Math.random() * h) | 0, r: Math.round(h * 0.28), frames: 40 };
    }
    draw();
    rafId = requestAnimationFrame(tick);
  }

  function start() { if (!rafId && shouldRun()) rafId = requestAnimationFrame(tick); }

  canvas.addEventListener('pointerdown', function (e) {
    var rect = canvas.getBoundingClientRect();
    seed(Math.floor((e.clientX - rect.left) / rect.width * w), Math.floor((e.clientY - rect.top) / rect.height * h), 4);
    burstUntil = performance.now() + 5000;
    draw();
    start();
  });

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      start();
    }).observe(canvas);
  }
  document.addEventListener('visibilitychange', start);
  if (reduceMotion.addEventListener) reduceMotion.addEventListener('change', start);

  var resizeTimer = 0, lastWidth = 0;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      var width = canvas.getBoundingClientRect().width;
      if (Math.abs(width - lastWidth) > 40) { lastWidth = width; init(); start(); }
    }, 250);
  });

  lastWidth = canvas.getBoundingClientRect().width;
  init();
  start();
})();
