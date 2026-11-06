(function () {
  // Disclaimer gate (ICAI practice): shown once per browser session until the visitor agrees.
  var gate = document.getElementById('gate');
  var agreed = false;
  try { agreed = sessionStorage.getItem('kdco-agree') === '1'; } catch (e) {}
  if (gate && !agreed) {
    gate.hidden = false;
    document.getElementById('gate-agree').addEventListener('click', function () {
      try { sessionStorage.setItem('kdco-agree', '1'); } catch (e) {}
      gate.hidden = true;
    });
  }

  // Mobile nav strip: bring the current page's link into view, drop the edge fade at the end.
  var nav = document.getElementById('nav');
  if (nav) {
    var cur = nav.querySelector('[aria-current="page"]');
    if (cur && nav.scrollWidth > nav.clientWidth) nav.scrollLeft = Math.max(0, cur.offsetLeft - nav.offsetLeft - 16);
    var edge = function () { nav.classList.toggle('at-end', nav.scrollLeft + nav.clientWidth >= nav.scrollWidth - 4); };
    nav.addEventListener('scroll', edge, { passive: true }); edge();
  }

  // Compliance dates: hide past items on home ledger, dim them in the calendar table.
  var today = new Date(); today.setHours(0, 0, 0, 0);
  function d(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  document.querySelectorAll('.ledger-list').forEach(function (list) {
    var n = +list.getAttribute('data-upcoming') || 6, shown = 0;
    list.querySelectorAll('li').forEach(function (li) {
      var future = d(li.getAttribute('data-date')) >= today;
      if (future && shown < n) { shown++; } else { li.hidden = true; }
    });
  });
  document.querySelectorAll('.cal tr[data-date]').forEach(function (tr) {
    if (d(tr.getAttribute('data-date')) < today) tr.classList.add('is-past');
  });

  // Updates source filter
  var sChips = document.querySelectorAll('[data-src-filter]');
  sChips.forEach(function (c) {
    c.addEventListener('click', function () {
      sChips.forEach(function (x) { x.classList.toggle('is-on', x === c); });
      var f = c.getAttribute('data-src-filter');
      document.querySelectorAll('.upd-list li[data-src]').forEach(function (li) {
        li.hidden = !(f === 'all' || li.getAttribute('data-src') === f);
      });
    });
  });

  // Blog filter
  var chips = document.querySelectorAll('.filter [data-filter]');
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      chips.forEach(function (x) { x.classList.toggle('is-on', x === c); });
      var f = c.getAttribute('data-filter');
      document.querySelectorAll('.post-row').forEach(function (r) {
        r.hidden = !(f === 'all' || r.getAttribute('data-cat') === f);
      });
    });
  });
})();
