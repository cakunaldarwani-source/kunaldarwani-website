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

/* "Send a query" form (Contact page): same form as indiansalahkar.com. Leads go to Bitrix24 through
   https://indiansalahkar.com/enquiry, which marks them as kunaldarwani.com (CA firm) leads.
   If sending fails, the visitor can send the same details on WhatsApp. */
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  $$("[data-enquiry]").forEach(function (form) {
    var data = window.__ENQ__ || { items: [], popular: [], other: 604 };
    var card = form.parentNode, done = $(".enq-done", card);
    var q = $("#enq-q", form), drop = $(".enq-drop", form), chipsEl = $(".enq-chips", form), box = $(".enq-box", form);
    var details = $("#enq-details", form), err = $(".enq-err", form), go = $(".enq-go", form);
    var phone = $("#enq-phone", form), email = $("#enq-email", form), nameIn = $("#enq-name", form);
    var sel = [], opts = [], active = -1;
    var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    var norm = function (s) { return String(s || "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim(); };
    var byName = function (n) { n = norm(n); for (var i = 0; i < data.items.length; i++) if (norm(data.items[i].n) === n) return data.items[i]; return null; };
    var has = function (n) { return sel.some(function (s) { return norm(s.n) === norm(n); }); };

    function add(item) { if (!has(item.n)) sel.push(item); q.value = ""; err.hidden = true; paint(); close(); q.focus(); }
    function addCustom() { var t = q.value.trim().slice(0, 100); if (t.length >= 2) add({ n: t, b: data.other, custom: true }); }
    function paint() {
      chipsEl.innerHTML = sel.map(function (s, i) {
        return '<span class="enq-chip' + (s.custom ? " is-custom" : "") + '">' + (s.custom ? "Other: " : "") + esc(s.n) +
          '<button type="button" data-i="' + i + '" aria-label="Remove ' + esc(s.n) + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button></span>';
      }).join("");
      q.placeholder = sel.length ? "Add another…" : "Search e.g. ITR, GST return, audit";
    }
    function matches(text) {
      var t = norm(text);
      if (!t) return data.popular.map(byName).filter(function (x) { return x && !has(x.n); });
      var words = t.split(" "), out = [];
      data.items.forEach(function (it) {
        if (has(it.n)) return;
        var n = norm(it.n), hay = n + " " + norm(it.g) + " " + norm(it.k), score = 0;
        if (n.indexOf(t) === 0) score = 4;
        else if ((" " + n).indexOf(" " + t) > -1) score = 3;
        else if (n.indexOf(t) > -1) score = 2;
        else if (words.every(function (w) { return hay.indexOf(w) > -1; })) score = 1;
        if (score) out.push([score, it]);
      });
      out.sort(function (a, b) { return b[0] - a[0]; });
      return out.slice(0, 7).map(function (x) { return x[1]; });
    }
    function render() {
      var text = q.value.trim();
      opts = matches(text); active = -1;
      var html = '<div class="enq-h">' + (text ? (opts.length ? "Matching services" : "Not listed?") : "Common queries") + "</div>";
      html += opts.map(function (it, i) {
        return '<button type="button" role="option" class="enq-o" data-o="' + i + '"><span>' + esc(it.n) + "</span><small>" + esc(it.g) + "</small></button>";
      }).join("");
      if (text.length >= 2) html += '<button type="button" role="option" class="enq-o enq-custom" data-custom><span class="plus">+</span><span>Not listed? Send <b>“' + esc(text) + '”</b> as my query topic</span></button>';
      drop.innerHTML = html; drop.hidden = false; q.setAttribute("aria-expanded", "true");
    }
    function close() { drop.hidden = true; q.setAttribute("aria-expanded", "false"); }
    function move(d) {
      var b = $$(".enq-o", drop);
      if (!b.length) return;
      active = (active + d + b.length) % b.length;
      b.forEach(function (x, i) { x.classList.toggle("active", i === active); });
      b[active].scrollIntoView({ block: "nearest" });
    }
    q.addEventListener("input", render);
    q.addEventListener("focus", render);
    q.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); if (drop.hidden) render(); move(e.key === "ArrowDown" ? 1 : -1); }
      else if (e.key === "Enter") {
        e.preventDefault();
        var b = $$(".enq-o", drop)[active];
        if (b) b.click(); else if (q.value.trim() && opts.length) add(opts[0]); else addCustom();
      } else if (e.key === "Escape") close();
      else if (e.key === "Backspace" && !q.value && sel.length) { sel.pop(); paint(); }
    });
    drop.addEventListener("mousedown", function (e) { e.preventDefault(); });
    drop.addEventListener("click", function (e) {
      var b = e.target.closest(".enq-o");
      if (!b) return;
      if (b.hasAttribute("data-custom")) addCustom(); else add(opts[+b.dataset.o]);
    });
    chipsEl.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-i]");
      if (b) { sel.splice(+b.dataset.i, 1); paint(); q.focus(); }
    });
    box.addEventListener("click", function (e) { if (e.target === box || e.target === chipsEl) q.focus(); });
    document.addEventListener("click", function (e) { if (!form.contains(e.target)) close(); });
    phone.addEventListener("input", function () {
      var d = phone.value.replace(/\D/g, "");
      if (d.length > 10) d = d.replace(/^(91|0)/, "");
      phone.value = d.slice(0, 10);
    });
    var preset = new URLSearchParams(location.search).get("service");
    if (preset) { var hit = data.items.filter(function (i) { return i.s === preset; })[0]; if (hit) sel.push(hit); }
    paint();

    function fail(msg, wa) {
      err.innerHTML = esc(msg) + (wa ? ' <a href="' + wa + '" target="_blank" rel="noopener">Send it on WhatsApp instead</a>' : "");
      err.hidden = false;
    }
    function waLink(v) {
      var lines = ["Hello, I have a query regarding: " + v.services.map(function (s) { return s.n; }).join(", "),
                   "Name: " + v.name, "Phone: +91 " + v.phone];
      if (v.email) lines.push("E-mail: " + v.email);
      if (v.details) lines.push(v.details);
      return "https://wa.me/" + form.dataset.wa + "?text=" + encodeURIComponent(lines.join("\n"));
    }
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (q.value.trim().length >= 2) { if (opts.length && norm(opts[0].n) === norm(q.value)) add(opts[0]); else addCustom(); }
      var v = { name: nameIn.value.trim(), phone: phone.value, email: email.value.trim(), details: details.value.trim(),
                services: sel.map(function (s) { return { n: s.n, b: s.b, custom: !!s.custom }; }),
                page: form.dataset.page || location.pathname, referrer: document.referrer.slice(0, 300),
                website: ($('input[name="website"]', form) || {}).value || "" };
      var p = new URLSearchParams(location.search);
      ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"].forEach(function (k) { if (p.get(k)) v[k] = p.get(k).slice(0, 100); });
      if (v.name.length < 2) { fail("Please enter your name."); nameIn.focus(); return; }
      if (!/^[6-9]\d{9}$/.test(v.phone)) { fail("Please enter a valid 10-digit mobile number."); phone.focus(); return; }
      if (v.email && !/^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(v.email)) { fail("That e-mail looks incomplete. Correct it or leave it blank."); email.focus(); return; }
      if (!sel.length) { fail("Choose what your query relates to, or type it and pick 'Not listed'."); q.focus(); return; }
      err.hidden = true; go.disabled = true; go.textContent = "Sending…";
      var ctl = window.AbortController ? new AbortController() : null;
      if (ctl) setTimeout(function () { ctl.abort(); }, 5000);
      fetch(form.dataset.endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(v), signal: ctl ? ctl.signal : undefined })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok || !j.ok) throw new Error(j.error || "failed"); return j; }); })
        .then(function () {
          form.hidden = true; done.hidden = false;
          var first = v.name.split(" ")[0];
          $("[data-enq-first]", done).textContent = first ? ", " + first : "";
          $("[data-enq-wa]", done).href = waLink(v);
          card.scrollIntoView({ block: "nearest", behavior: "smooth" });
        })
        .catch(function (x) {
          fail(x && x.message && x.message !== "failed" && x.message.indexOf("fetch") < 0 && x.name !== "AbortError" ? x.message : "We couldn't send this online just now.", waLink(v));
        })
        .then(function () { go.disabled = false; go.textContent = "Send query"; });
    });
  });
})();
