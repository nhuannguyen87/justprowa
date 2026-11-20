// Small progressive enhancements – the site works without JavaScript.
(function () {
  // Request-type help text under the tabs
  var tabs = document.querySelectorAll('.radio-tabs input');
  var want = new URLSearchParams(location.search).get('type');
  var pre = want && document.querySelector('.radio-tabs input[value="' + CSS.escape(want) + '"]');
  if (pre) pre.checked = true;
  function showHelp() {
    var v = (document.querySelector('.radio-tabs input:checked') || {}).value;
    document.querySelectorAll('.kind-help').forEach(function (p) { p.style.display = p.dataset.for === v ? 'block' : 'none'; });
  }
  tabs.forEach(function (t) { t.addEventListener('change', showHelp); }); showHelp();

  // File previews
  var file = document.querySelector('input[data-preview]'), box = document.getElementById('thumbs');
  if (file && box) file.addEventListener('change', function () {
    box.innerHTML = '';
    Array.prototype.slice.call(file.files, 0, 8).forEach(function (f) {
      var d = document.createElement('div'); d.className = 't';
      if (f.type.indexOf('image/') === 0) d.style.backgroundImage = 'url(' + URL.createObjectURL(f) + ')';
      else d.textContent = f.name;
      box.appendChild(d);
    });
    if (file.files.length > 8) { var w = document.createElement('div'); w.className = 'ferr'; w.textContent = 'Only the first 8 files can be sent.'; box.appendChild(w); }
  });

  // Plan service picker: limit to N choices
  var form = document.querySelector('form[data-pick]');
  if (form) {
    var max = +form.dataset.pick, boxes = form.querySelectorAll('.pickitem input'), counter = form.querySelector('.pickcount');
    function sync() {
      var n = form.querySelectorAll('.pickitem input:checked').length;
      boxes.forEach(function (b) { var off = !b.checked && n >= max; b.disabled = off; b.closest('.pickitem').classList.toggle('off', off); });
      if (counter) counter.textContent = n + ' / ' + max + ' chosen';
    }
    boxes.forEach(function (b) { b.addEventListener('change', sync); }); sync();
  }

  // Work carousel arrows
  document.querySelectorAll('[data-carousel]').forEach(function (c) {
    var row = c.querySelector('.scroller');
    c.querySelectorAll('.arrow').forEach(function (a) {
      a.addEventListener('click', function () { row.scrollBy({ left: +a.dataset.dir * row.clientWidth, behavior: 'smooth' }); });
    });
  });

  // Close mobile menu after choosing a link
  document.querySelectorAll('nav.main a').forEach(function (a) { a.addEventListener('click', function () { var t = document.getElementById('navtoggle'); if (t) t.checked = false; }); });

  // Disable submit buttons on send (avoid double submits)
  document.querySelectorAll('form').forEach(function (f) {
    f.addEventListener('submit', function () { var b = f.querySelector('button[type=submit]'); if (b) setTimeout(function () { b.disabled = true; b.style.opacity = .7; }, 0); });
  });

})();
