(function () {
  'use strict';
  var body = document.body;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- Hero video: reduced motion + robust Safari autoplay ---------- */
  (function () {
    var v = document.querySelector('.hero-bg');
    if (!v) return;
    if (reduce) { v.removeAttribute('autoplay'); try { v.pause(); } catch (e) {} return; }
    v.muted = true; v.defaultMuted = true; v.playsInline = true;
    var tryPlay = function () { var p = v.play(); if (p && p.catch) p.catch(function () {}); };
    tryPlay();
    ['loadeddata', 'canplay', 'loadedmetadata'].forEach(function (ev) { v.addEventListener(ev, tryPlay, { once: true }); });
    ['touchstart', 'click'].forEach(function (ev) { document.addEventListener(ev, tryPlay, { once: true, passive: true }); });
  })();

  /* ---------- Mobile menu ---------- */
  var burger = document.querySelector('.burger');
  function setMenu(open) {
    body.classList.toggle('menu-open', open);
    if (burger) {
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    }
  }
  if (burger) burger.addEventListener('click', function () { setMenu(!body.classList.contains('menu-open')); });
  document.querySelectorAll('[data-close-menu], .drawer a').forEach(function (el) {
    el.addEventListener('click', function () { setMenu(false); });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setMenu(false); });

  /* ---------- Nav scrolled state ---------- */
  var nav = document.getElementById('nav');
  function onScrollNav() { if (nav) nav.classList.toggle('scrolled', window.scrollY > 8); }
  onScrollNav();
  window.addEventListener('scroll', onScrollNav, { passive: true });

  /* ---------- Count-up ---------- */
  function countUp(el) {
    var target = parseFloat(el.getAttribute('data-count')) || 0;
    var pre = el.getAttribute('data-prefix') || '';
    var suf = el.getAttribute('data-suffix') || '';
    if (reduce || target === 0) { el.textContent = pre + target.toLocaleString('ru-RU') + suf; return; }
    var dur = 1100, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = pre + Math.round(target * eased).toLocaleString('ru-RU') + suf;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  /* ---------- Reveal + count triggers ---------- */
  var animEls = document.querySelectorAll('[data-anim], [data-stagger]');
  if (reduce || !('IntersectionObserver' in window)) {
    animEls.forEach(function (el) { el.classList.add('in'); });
    document.querySelectorAll('[data-count]').forEach(countUp);
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.add('in');
        en.target.querySelectorAll('[data-count]').forEach(countUp);
        io.unobserve(en.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    animEls.forEach(function (el) { io.observe(el); });
  }

  /* ---------- Hero scroll transition (parallax + fade) ---------- */
  var heroBg = document.querySelector('.hero-bg');
  var heroContent = document.querySelector('.hero-content');
  var cue = document.querySelector('.scroll-cue');
  if ((heroBg || heroContent) && !reduce) {
    var ticking = false;
    var onHero = function () {
      var h = window.innerHeight || 700;
      var y = window.scrollY;
      var p = Math.min(y / h, 1);
      if (heroContent) {
        heroContent.style.opacity = String(Math.max(1 - p * 1.5, 0));
        heroContent.style.transform = 'translateY(' + (y * 0.25) + 'px)';
      }
      if (heroBg) heroBg.style.transform = 'scale(' + (1 + p * 0.12) + ')';
      if (cue) cue.style.opacity = String(Math.max(1 - p * 4, 0));
      ticking = false;
    };
    onHero();
    window.addEventListener('scroll', function () {
      if (ticking) return; ticking = true; requestAnimationFrame(onHero);
    }, { passive: true });
  }

  /* ---------- Модальная форма записи ---------- */
  (function () {
    var modal = document.getElementById('leadModal');
    if (!modal) return;
    function open() {
      modal.hidden = false; body.classList.add('modal-open');
      var f = modal.querySelector('input[name="phone"], input[name="name"]');
      if (f) setTimeout(function () { f.focus(); }, 60);
    }
    function close() { modal.hidden = true; body.classList.remove('modal-open'); }
    document.addEventListener('click', function (e) {
      var a = e.target.closest('a[href$="#zayavka"]');
      if (a) { e.preventDefault(); setMenu(false); open(); return; }
      if (e.target.closest('[data-modal-close]')) close();
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !modal.hidden) close(); });
  })();

  /* ---------- Phone mask ---------- */
  document.querySelectorAll('input[type="tel"]').forEach(function (inp) {
    inp.addEventListener('input', function () {
      var d = inp.value.replace(/\D/g, '').replace(/^8/, '7').replace(/^([^7])/, '7$1').slice(0, 11);
      var out = '+7';
      if (d.length > 1) out += ' (' + d.slice(1, 4);
      if (d.length >= 4) out += ') ' + d.slice(4, 7);
      if (d.length >= 7) out += '-' + d.slice(7, 9);
      if (d.length >= 9) out += '-' + d.slice(9, 11);
      inp.value = out;
    });
  });

  /* ---------- Catalog search (hub / dtype): filter index → model links ---------- */
  (function () {
    var input = document.querySelector('[data-aipapa-search]');
    var dataEl = document.getElementById('aipapa-search-data');
    if (!input || !dataEl) return;
    var idx = []; try { idx = JSON.parse(dataEl.textContent); } catch (e) { return; }
    var box = input.parentNode.querySelector('.model-search-results');
    var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); };
    var render = function () {
      var q = input.value.trim().toLowerCase();
      if (q.length < 2) { box.hidden = true; box.innerHTML = ''; return; }
      var terms = q.split(/\s+/);
      var m = idx.filter(function (it) { var l = it.l.toLowerCase(); return terms.every(function (t) { return l.indexOf(t) >= 0; }); });
      box.hidden = false;
      if (!m.length) { box.innerHTML = '<div class="msr-empty">Ничего не найдено</div>'; return; }
      box.innerHTML = m.slice(0, 40).map(function (it) {
        return '<a class="msr-item" href="/remont/' + it.t + '/' + it.b + '/' + it.s + '/">' + esc(it.l) + '</a>';
      }).join('');
    };
    input.addEventListener('input', render);
  })();

  /* ---------- Card filter (brand page): hide non-matching cards ---------- */
  (function () {
    var input = document.querySelector('[data-filter-cards]');
    if (!input) return;
    var container = document.querySelector(input.getAttribute('data-filter-cards'));
    if (!container) return;
    var cards = [].slice.call(container.querySelectorAll('.model-card'));
    var empty = container.querySelector('.model-empty');
    input.addEventListener('input', function () {
      var q = input.value.trim().toLowerCase();
      var terms = q.split(/\s+/);
      var shown = 0;
      cards.forEach(function (c) {
        var n = c.getAttribute('data-name') || '';
        var ok = !q || terms.every(function (t) { return n.indexOf(t) >= 0; });
        c.style.display = ok ? '' : 'none';
        if (ok) shown++;
      });
      if (empty) empty.hidden = shown > 0;
    });
  })();

  /* ---------- Lead form (demo) ---------- */
  /* ---------- Cookie-уведомление ---------- */
  (function () {
    var bar = document.getElementById('cookieBar');
    if (!bar) return;
    var KEY = 'aipapa_cookie_ok';
    var stored;
    try { stored = localStorage.getItem(KEY); } catch (e) { stored = '1'; }
    if (!stored) { bar.hidden = false; requestAnimationFrame(function () { bar.classList.add('is-shown'); }); }
    var ok = document.getElementById('cookieAccept');
    if (ok) ok.addEventListener('click', function () {
      try { localStorage.setItem(KEY, '1'); } catch (e) {}
      bar.classList.remove('is-shown');
      setTimeout(function () { bar.hidden = true; }, 300);
    });
  })();

  document.querySelectorAll('.consent-check input').forEach(function (cb) {
    cb.addEventListener('change', function () {
      var lbl = cb.closest('.consent-check');
      if (lbl && cb.checked) lbl.classList.remove('is-error');
    });
  });
  document.querySelectorAll('.lead-form').forEach(function (form) {
    if (!form.querySelector('[name="website"]')) {
      var hp = document.createElement('input');
      hp.name = 'website'; hp.tabIndex = -1; hp.setAttribute('autocomplete', 'off');
      hp.style.cssText = 'position:absolute;left:-9999px;opacity:0;height:0;width:0';
      form.appendChild(hp);
    }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      var phone = form.querySelector('input[type="tel"]');
      if (phone && phone.value.replace(/\D/g, '').length < 11) { phone.focus(); return; }
      var consent = form.querySelector('input[name="consent"]');
      if (consent && !consent.checked) {
        var lbl = consent.closest('.consent-check');
        if (lbl) lbl.classList.add('is-error');
        consent.focus();
        return;
      }
      var orig = btn ? btn.textContent : '';
      if (btn) { btn.disabled = true; btn.textContent = 'Отправляем…'; }
      var fd = new FormData(form);
      fd.set('action', 'aipapa_repair_lead');
      if (window.AIPAPA && AIPAPA.nonce) fd.set('aipapa_nonce', AIPAPA.nonce);
      fd.append('page', location.href);
      var url = (window.AIPAPA && AIPAPA.ajax) ? AIPAPA.ajax : '/wp-admin/admin-ajax.php';
      fetch(url, { method: 'POST', body: fd, credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d && d.success) {
            if (btn) { btn.textContent = (d.data && d.data.msg) || 'Заявка принята, перезвоним!'; btn.style.opacity = '.85'; }
            form.reset();
          } else {
            if (btn) { btn.disabled = false; btn.textContent = orig; }
            alert((d && d.data && d.data.msg) || 'Не удалось отправить. Позвоните нам, пожалуйста.');
          }
        })
        .catch(function () {
          if (btn) { btn.disabled = false; btn.textContent = orig; }
          alert('Ошибка сети. Позвоните нам, пожалуйста.');
        });
    });
  });
})();
