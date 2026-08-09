/* ============================================================
   MaendeLeo MIS — UI behaviors (tabs, sidebar, theme studio)
   ============================================================ */
(function () {
  'use strict';

  /* ---------- sidebar collapse / mobile ---------- */
  var app = document.getElementById('app');
  var collapseBtn = document.getElementById('collapseBtn');
  var menuBtn = document.getElementById('menuBtn');
  var sidebarOverlay = document.getElementById('sidebarOverlay');

  if (collapseBtn) collapseBtn.addEventListener('click', function () { app.classList.toggle('collapsed'); });
  if (menuBtn) menuBtn.addEventListener('click', function () {
    if (window.innerWidth <= 1024) {
      app.classList.toggle('mobile-open');
      if (sidebarOverlay) sidebarOverlay.classList.toggle('open', app.classList.contains('mobile-open'));
    } else {
      app.classList.toggle('collapsed');
    }
  });
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', function () {
    app.classList.remove('mobile-open');
    sidebarOverlay.classList.remove('open');
  });

  /* ---------- tabs within views ---------- */
  document.querySelectorAll('.tabbar').forEach(function (bar) {
    var btns = bar.querySelectorAll('.tab-btn');
    btns.forEach(function (btn) {
      btn.addEventListener('click', function () {
        btns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var panelId = btn.dataset.tab;
        var container = bar.parentElement;
        container.querySelectorAll('.tab-panel').forEach(function (p) {
          p.classList.toggle('active', p.id === panelId);
        });
      });
    });
  });

  /* ---------- modal helpers ---------- */
  window.openModal = function (id) {
    var m = document.getElementById(id);
    if (m) m.classList.add('open');
  };
  window.closeModal = function (id) {
    var m = document.getElementById(id);
    if (m) m.classList.remove('open');
  };
  document.querySelectorAll('.modal-overlay').forEach(function (ov) {
    ov.addEventListener('click', function (e) {
      if (e.target === ov) ov.classList.remove('open');
    });
  });

  /* ---------- notifications dropdown ---------- */
  var notifBtn = document.getElementById('notifBtn');
  var notifPanel = document.getElementById('notifPanel');
  if (notifBtn && notifPanel) {
    notifBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      notifPanel.classList.toggle('open');
      var up = document.getElementById('userPanel');
      if (up) up.classList.remove('open');
    });
    document.addEventListener('click', function (e) {
      if (!notifPanel.contains(e.target)) notifPanel.classList.remove('open');
    });
  }

  /* ---------- user profile dropdown ---------- */
  var userBtn = document.getElementById('userBtn');
  var userPanel = document.getElementById('userPanel');
  if (userBtn && userPanel) {
    userBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      userPanel.classList.toggle('open');
      if (notifPanel) notifPanel.classList.remove('open');
    });
    document.addEventListener('click', function (e) {
      if (!userPanel.contains(e.target)) userPanel.classList.remove('open');
    });
  }

  /* ---------- auto-dismiss flash messages ---------- */
  setTimeout(function () {
    document.querySelectorAll('.msg').forEach(function (m) {
      m.style.transition = 'opacity .5s';
      m.style.opacity = '0';
      setTimeout(function () { m.remove(); }, 550);
    });
  }, 5000);

  /* ---------- global search: submits on Enter ---------- */
  var globalSearch = document.getElementById('globalSearch');
  if (globalSearch) {
    globalSearch.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var q = globalSearch.value.trim();
        if (q) window.location.href = '/customers/?q=' + encodeURIComponent(q);
      }
    });
  }

  /* ---------- theme studio ---------- */
  var drawer = document.getElementById('drawer');
  var drawerOverlay = document.getElementById('drawerOverlay');
  var root = document.documentElement.style;

  function openDrawer() { if (drawer) { drawer.classList.add('open'); drawerOverlay.classList.add('open'); } }
  function closeDrawer() { if (drawer) { drawer.classList.remove('open'); drawerOverlay.classList.remove('open'); } }
  window.openDrawer = openDrawer;
  window.closeDrawer = closeDrawer;

  var themeBtn = document.getElementById('themeBtn');
  if (themeBtn) themeBtn.addEventListener('click', openDrawer);
  var drawerClose = document.getElementById('drawerClose');
  if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
  if (drawerOverlay) drawerOverlay.addEventListener('click', closeDrawer);

  function shade(hex, percent) {
    hex = hex.replace('#', '');
    if (hex.length !== 6) return '#' + hex;
    var num = parseInt(hex, 16), r = (num >> 16) + Math.round(2.55 * percent),
        g = ((num >> 8) & 0xff) + Math.round(2.55 * percent), b = (num & 0xff) + Math.round(2.55 * percent);
    r = Math.min(255, Math.max(0, r)); g = Math.min(255, Math.max(0, g)); b = Math.min(255, Math.max(0, b));
    return '#' + (1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1);
  }
  function textOn(hex) {
    hex = hex.replace('#', '');
    if (hex.length !== 6) return '#17241F';
    var num = parseInt(hex, 16), r = (num >> 16) & 0xff, g = ((num >> 8) & 0xff), b = num & 0xff;
    return ((0.299 * r + 0.587 * g + 0.114 * b) / 255) > 0.6 ? '#17241F' : '#F5F6F3';
  }

  var presets = [
    { name: 'Ledger Green', sidebar: '#173C34', header: '#FFFFFF', accent: '#D9A441' },
    { name: 'Sisal Navy', sidebar: '#122A45', header: '#FFFFFF', accent: '#4C8DFF' },
    { name: 'Harvest Clay', sidebar: '#3A2317', header: '#FFF9F2', accent: '#D97F4B' },
    { name: 'Baobab Charcoal', sidebar: '#20262B', header: '#FFFFFF', accent: '#4CAF88' },
    { name: 'Coastal Teal', sidebar: '#0E3E42', header: '#F4FBFA', accent: '#2FBFA0' },
    { name: 'Savanna Plum', sidebar: '#3B1F3A', header: '#FFFFFF', accent: '#E0A0D8' }
  ];
  var presetRow = document.getElementById('presetRow');
  if (presetRow) {
    presetRow.innerHTML = presets.map(function (p, i) {
      return '<div class="preset-item">' +
        '<div class="swatch' + (i === 0 ? ' active' : '') + '" data-idx="' + i +
        '" style="background:linear-gradient(135deg, ' + p.sidebar + ' 50%, ' + p.accent + ' 50%);"></div>' +
        '<div class="preset-name">' + p.name + '</div></div>';
    }).join('');

    presetRow.addEventListener('click', function (e) {
      var sw = e.target.closest('.swatch');
      if (!sw) return;
      presetRow.querySelectorAll('.swatch').forEach(function (s) { s.classList.remove('active'); });
      sw.classList.add('active');
      applyTheme(presets[sw.dataset.idx]);
    });
  }

  function applyTheme(p) {
    root.setProperty('--sidebar-bg', p.sidebar);
    root.setProperty('--sidebar-bg-2', shade(p.sidebar, -14));
    root.setProperty('--header-bg', p.header);
    root.setProperty('--header-text', textOn(p.header));
    root.setProperty('--accent', p.accent);
    root.setProperty('--accent-dim', shade(p.accent, 62));
    var ps = document.getElementById('pickSidebar'), ph = document.getElementById('pickHeader'), pa = document.getElementById('pickAccent');
    if (ps) ps.value = p.sidebar;
    if (ph) ph.value = p.header;
    if (pa) pa.value = p.accent;
  }

  var pickSidebar = document.getElementById('pickSidebar');
  if (pickSidebar) pickSidebar.addEventListener('input', function (e) {
    root.setProperty('--sidebar-bg', e.target.value);
    root.setProperty('--sidebar-bg-2', shade(e.target.value, -14));
    if (presetRow) presetRow.querySelectorAll('.swatch').forEach(function (s) { s.classList.remove('active'); });
  });
  var pickHeader = document.getElementById('pickHeader');
  if (pickHeader) pickHeader.addEventListener('input', function (e) {
    root.setProperty('--header-bg', e.target.value);
    root.setProperty('--header-text', textOn(e.target.value));
  });
  var pickAccent = document.getElementById('pickAccent');
  if (pickAccent) pickAccent.addEventListener('input', function (e) {
    root.setProperty('--accent', e.target.value);
    root.setProperty('--accent-dim', shade(e.target.value, 62));
  });

  var animToggle = document.getElementById('animToggle');
  if (animToggle) animToggle.addEventListener('click', function () {
    animToggle.classList.toggle('on');
    document.documentElement.setAttribute('data-anim', animToggle.classList.contains('on') ? 'on' : 'off');
  });

  document.querySelectorAll('.speed-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.speed-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      root.setProperty('--dur', btn.dataset.speed + 'ms');
    });
  });

  var compactToggle = document.getElementById('compactToggle');
  if (compactToggle) compactToggle.addEventListener('click', function () {
    compactToggle.classList.toggle('on');
    if (app) app.classList.toggle('collapsed');
  });

  var resetTheme = document.getElementById('resetTheme');
  if (resetTheme) resetTheme.addEventListener('click', function () {
    applyTheme(presets[0]);
    if (presetRow) presetRow.querySelectorAll('.swatch').forEach(function (s, i) { s.classList.toggle('active', i === 0); });
    root.setProperty('--dur', '220ms');
    document.querySelectorAll('.speed-btn').forEach(function (b) { b.classList.toggle('active', b.dataset.speed === '220'); });
    if (animToggle) { animToggle.classList.add('on'); document.documentElement.setAttribute('data-anim', 'on'); }
    if (app) app.classList.remove('collapsed');
    if (compactToggle) compactToggle.classList.remove('on');
  });

  /* ---------- splash redirect ---------- */
  var splashRedirect = document.getElementById('splashRedirect');
  if (splashRedirect) {
    setTimeout(function () { window.location.href = splashRedirect.dataset.url; }, 2600);
  }

  /* ---------- demo account dropdown ---------- */
  var demoBtn = document.getElementById('demoDropdownBtn');
  var demoMenu = document.getElementById('demoDropdownMenu');
  if (demoBtn && demoMenu) {
    function setDemoOpen(open) {
      demoMenu.hidden = !open;
      demoBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      var caret = demoBtn.querySelector('.demo-caret');
      if (caret) caret.classList.toggle('demo-caret-open', open);
    }
    demoBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      setDemoOpen(demoMenu.hidden);
    });
    document.addEventListener('click', function () { setDemoOpen(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setDemoOpen(false);
    });
  }

  /* ---------- demo account quick login ---------- */
  document.querySelectorAll('.demo-user').forEach(function (el) {
    el.addEventListener('click', function () {
      var u = document.getElementById('id_username');
      var p = document.getElementById('id_password');
      if (u) u.value = el.dataset.user;
      if (p) { p.value = el.dataset.pw; p.focus(); }
      if (demoMenu) setDemoOpen(false);
    });
  });
})();
