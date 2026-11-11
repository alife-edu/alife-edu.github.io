// Light/dark toggle. The site is dark by default; the nav's theme button switches to
// light by setting data-theme="light" on <html>. The choice is kept in localStorage,
// and _includes/head.html applies it before the page draws so there's no flash of dark.
(function () {
  var root = document.documentElement;
  var btn = document.querySelector('.theme-toggle');
  if (!btn) return;

  function sync() {
    var light = root.getAttribute('data-theme') === 'light';
    btn.setAttribute('aria-pressed', light ? 'true' : 'false');
    btn.setAttribute('title', light ? 'Switch to dark mode' : 'Switch to light mode');
  }

  btn.addEventListener('click', function () {
    var light = root.getAttribute('data-theme') !== 'light';
    if (light) root.setAttribute('data-theme', 'light'); else root.removeAttribute('data-theme');
    try { localStorage.setItem('theme', light ? 'light' : 'dark'); } catch (e) {}
    sync();
  });
  sync();
})();
