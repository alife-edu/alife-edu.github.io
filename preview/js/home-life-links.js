/*
  Site glue for the home page's Game of Life panel (life/panel.js).

  The panel fires a `life:link` event when someone clicks one of its link blocks. Each
  block's button carries data-life-link="<dialog id>", so here we open that <dialog>
  (defined in _includes/life-nav-modals.html) and note which block opened it.
*/
(function () {
  'use strict';
  document.addEventListener('life:link', function (e) {
    var d = document.getElementById(e.detail.id);
    if (!d || !d.showModal) return;
    var origin = d.querySelector('.bm-origin');
    if (origin && e.detail.block) {
      origin.textContent = 'Block ' + (e.detail.index + 1) + ' of 4 \u00b7 settled at generation ' + e.detail.block.t;
    }
    d.showModal();
  });

  // Other controls on the page (the home cards and the colour key) open a dialog directly.
  // Plain clicks only: a modified click (new tab) still follows the link's href.
  Array.prototype.forEach.call(document.querySelectorAll('[data-open-dialog]'), function (b) {
    b.addEventListener('click', function (e) {
      if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var d = document.getElementById(b.getAttribute('data-open-dialog'));
      if (!d || !d.showModal) return;
      e.preventDefault();
      var origin = d.querySelector('.bm-origin');
      if (origin) origin.textContent = d.getAttribute('data-name');
      d.showModal();
    });
  });

  // Close buttons, clicks on the backdrop, and in-page links inside a dialog close it.
  Array.prototype.forEach.call(document.querySelectorAll('dialog.block-modal'), function (d) {
    d.querySelector('.bm-close').addEventListener('click', function () { d.close(); });
    d.addEventListener('click', function (e) { if (e.target === d) d.close(); });
    Array.prototype.forEach.call(d.querySelectorAll('[data-close]'), function (a) {
      a.addEventListener('click', function () { d.close(); });
    });
  });
})();
