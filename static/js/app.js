/* ============================================================
   MaendeLeo MIS — UI behaviors (tabs, sidebar, theme studio)
   ============================================================ */
(function () {
  'use strict';

  /* ---------- persistence helpers ---------- */
  var NKEY = 'mdl_nav', TABKEY = 'mdl_tab', TKEY = 'mdl_theme', MKEY = 'mdl_mode';
  function readJSON(k, fb) {
    try { var v = JSON.parse(localStorage.getItem(k)); return v === null ? fb : v; } catch (e) { return fb; }
  }
  var themeState = Object.assign({
    sidebar: null, header: null, accent: null, anim: true, speed: 220, compact: false
  }, readJSON(TKEY, {}));
  function saveTheme() { localStorage.setItem(TKEY, JSON.stringify(themeState)); }
  function navKey() {
    var a = document.querySelector('.nav-item.active');
    return a ? (a.dataset.nav || null) : null;
  }

  /* ---------- sidebar collapse / mobile ---------- */
  var app = document.getElementById('app');
  var collapseBtn = document.getElementById('collapseBtn');
  var menuBtn = document.getElementById('menuBtn');
  var sidebarOverlay = document.getElementById('sidebarOverlay');

  if (collapseBtn) collapseBtn.addEventListener('click', function () {
    app.classList.toggle('collapsed');
    themeState.compact = app.classList.contains('collapsed');
    saveTheme();
  });
  if (menuBtn) menuBtn.addEventListener('click', function () {
    if (window.innerWidth <= 1024) {
      app.classList.toggle('mobile-open');
      if (sidebarOverlay) sidebarOverlay.classList.toggle('open', app.classList.contains('mobile-open'));
    } else {
      app.classList.toggle('collapsed');
      themeState.compact = app.classList.contains('collapsed');
      saveTheme();
    }
  });
  if (sidebarOverlay) sidebarOverlay.addEventListener('click', function () {
    app.classList.remove('mobile-open');
    sidebarOverlay.classList.remove('open');
  });

  /* ---------- nav & menu persistence ---------- */
  var navItems = document.querySelectorAll('.nav-item');
  if (!navKey() && localStorage.getItem(NKEY)) {
    var savedNav = document.querySelector('.nav-item[data-nav="' + localStorage.getItem(NKEY) + '"]');
    if (savedNav) savedNav.classList.add('active');
  }
  navItems.forEach(function (el) {
    el.addEventListener('click', function () {
      if (el.dataset.nav) localStorage.setItem(NKEY, el.dataset.nav);
    });
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
        var key = navKey();
        if (key) localStorage.setItem(TABKEY, JSON.stringify({ k: key, tab: panelId }));
      });
    });
    var storedTab = readJSON(TABKEY, null);
    if (storedTab && storedTab.tab && storedTab.k === navKey()) {
      var container = bar.parentElement;
      btns.forEach(function (b) {
        var isActive = b.dataset.tab === storedTab.tab;
        b.classList.toggle('active', isActive);
        if (isActive) {
          container.querySelectorAll('.tab-panel').forEach(function (p) {
            p.classList.toggle('active', p.id === storedTab.tab);
          });
        }
      });
    }
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

  function applyColors(sidebar, header, accent) {
    if (sidebar) { root.setProperty('--sidebar-bg', sidebar); root.setProperty('--sidebar-bg-2', shade(sidebar, -14)); }
    if (header) { root.setProperty('--header-bg', header); root.setProperty('--header-text', textOn(header)); }
    if (accent) { root.setProperty('--accent', accent); root.setProperty('--accent-dim', shade(accent, 62)); }
  }

  /* ---------- appearance / light-dark mode ---------- */
  function currentMode() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }
  function computedVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  function syncModeUI() {
    var mode = currentMode();
    var icon = document.getElementById('modeIcon');
    if (icon) icon.className = 'fa-solid ' + (mode === 'dark' ? 'fa-sun' : 'fa-moon');
    var seg = document.getElementById('modeSeg');
    if (seg) {
      seg.querySelectorAll('.seg-btn').forEach(function (b) {
        b.classList.toggle('active', b.dataset.mode === mode);
      });
    }
  }
  function applyMode(mode) {
    document.documentElement.setAttribute('data-theme', mode);
    localStorage.setItem(MKEY, mode);
    if (!themeState.sidebar) { var ps = document.getElementById('pickSidebar'); if (ps) ps.value = computedVar('--sidebar-bg'); }
    if (!themeState.header) { var ph = document.getElementById('pickHeader'); if (ph) ph.value = computedVar('--header-bg'); }
    if (!themeState.accent) { var pa = document.getElementById('pickAccent'); if (pa) pa.value = computedVar('--accent'); }
    syncModeUI();
    syncPresetActive();
  }
  var modeBtn = document.getElementById('modeBtn');
  if (modeBtn) modeBtn.addEventListener('click', function () {
    applyMode(currentMode() === 'dark' ? 'light' : 'dark');
  });
  var modeSeg = document.getElementById('modeSeg');
  if (modeSeg) modeSeg.addEventListener('click', function (e) {
    var b = e.target.closest('.seg-btn');
    if (b && b.dataset.mode) applyMode(b.dataset.mode);
  });
  syncModeUI();

  var presets = [
    { name: 'Ledger Green', sidebar: '#173C34', header: '#FFFFFF', accent: '#D9A441' },
    { name: 'Sisal Navy', sidebar: '#122A45', header: '#FFFFFF', accent: '#4C8DFF' },
    { name: 'Harvest Clay', sidebar: '#3A2317', header: '#FFF9F2', accent: '#D97F4B' },
    { name: 'Baobab Charcoal', sidebar: '#20262B', header: '#FFFFFF', accent: '#4CAF88' },
    { name: 'Coastal Teal', sidebar: '#0E3E42', header: '#F4FBFA', accent: '#2FBFA0' },
    { name: 'Savanna Plum', sidebar: '#3B1F3A', header: '#FFFFFF', accent: '#E0A0D8' }
  ];
  var presetRow = document.getElementById('presetRow');
  function presetMatch(p) {
    return themeState.sidebar === p.sidebar && themeState.header === p.header && themeState.accent === p.accent;
  }
  function syncPresetActive() {
    if (!presetRow) return;
    var none = !themeState.sidebar && !themeState.header && !themeState.accent;
    presetRow.querySelectorAll('.swatch').forEach(function (s, i) {
      s.classList.toggle('active', (none && currentMode() === 'light') ? i === 0 : presetMatch(presets[i]));
    });
  }
  function syncPickers(sidebar, header, accent) {
    var ps = document.getElementById('pickSidebar'), ph = document.getElementById('pickHeader'), pa = document.getElementById('pickAccent');
    if (ps && sidebar) ps.value = sidebar;
    if (ph && header) ph.value = header;
    if (pa && accent) pa.value = accent;
  }
  function applyPreset(p) {
    themeState.sidebar = p.sidebar;
    themeState.header = p.header;
    themeState.accent = p.accent;
    applyColors(p.sidebar, p.header, p.accent);
    saveTheme();
    syncPickers(p.sidebar, p.header, p.accent);
    syncPresetActive();
  }

  if (presetRow) {
    presetRow.innerHTML = presets.map(function (p, i) {
      return '<div class="preset-item">' +
        '<div class="swatch" data-idx="' + i +
        '" style="background:linear-gradient(135deg, ' + p.sidebar + ' 50%, ' + p.accent + ' 50%);"></div>' +
        '<div class="preset-name">' + p.name + '</div></div>';
    }).join('');
    presetRow.addEventListener('click', function (e) {
      var sw = e.target.closest('.swatch');
      if (!sw) return;
      applyPreset(presets[sw.dataset.idx]);
    });
  }

  var pickSidebar = document.getElementById('pickSidebar');
  if (pickSidebar) {
    pickSidebar.value = themeState.sidebar || computedVar('--sidebar-bg') || '#173C34';
    pickSidebar.addEventListener('input', function (e) {
      themeState.sidebar = e.target.value;
      applyColors(themeState.sidebar, themeState.header, themeState.accent);
      saveTheme();
      syncPresetActive();
    });
  }
  var pickHeader = document.getElementById('pickHeader');
  if (pickHeader) {
    pickHeader.value = themeState.header || computedVar('--header-bg') || '#FFFFFF';
    pickHeader.addEventListener('input', function (e) {
      themeState.header = e.target.value;
      applyColors(themeState.sidebar, themeState.header, themeState.accent);
      saveTheme();
      syncPresetActive();
    });
  }
  var pickAccent = document.getElementById('pickAccent');
  if (pickAccent) {
    pickAccent.value = themeState.accent || computedVar('--accent') || '#D9A441';
    pickAccent.addEventListener('input', function (e) {
      themeState.accent = e.target.value;
      applyColors(themeState.sidebar, themeState.header, themeState.accent);
      saveTheme();
      syncPresetActive();
    });
  }

  var animToggle = document.getElementById('animToggle');
  if (animToggle) animToggle.addEventListener('click', function () {
    themeState.anim = !animToggle.classList.contains('on');
    animToggle.classList.toggle('on', themeState.anim);
    document.documentElement.setAttribute('data-anim', themeState.anim ? 'on' : 'off');
    saveTheme();
  });

  document.querySelectorAll('.speed-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.speed-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');
      themeState.speed = parseInt(btn.dataset.speed, 10);
      root.setProperty('--dur', themeState.speed + 'ms');
      saveTheme();
    });
  });

  var compactToggle = document.getElementById('compactToggle');
  if (compactToggle) compactToggle.addEventListener('click', function () {
    compactToggle.classList.toggle('on');
    if (app) {
      app.classList.toggle('collapsed', compactToggle.classList.contains('on'));
      themeState.compact = compactToggle.classList.contains('on');
      saveTheme();
    }
  });

  var resetTheme = document.getElementById('resetTheme');
  if (resetTheme) resetTheme.addEventListener('click', function () {
    localStorage.removeItem(TKEY);
    themeState = { sidebar: null, header: null, accent: null, anim: true, speed: 220, compact: false };
    ['--sidebar-bg', '--sidebar-bg-2', '--header-bg', '--header-text', '--accent', '--accent-dim'].forEach(function (v) {
      root.removeProperty(v);
    });
    root.setProperty('--dur', '220ms');
    document.documentElement.setAttribute('data-anim', 'on');
    if (animToggle) animToggle.classList.add('on');
    if (app) app.classList.remove('collapsed');
    if (compactToggle) compactToggle.classList.remove('on');
    document.querySelectorAll('.speed-btn').forEach(function (b) { b.classList.toggle('active', b.dataset.speed === '220'); });
    var rs = document.getElementById('pickSidebar'); if (rs) rs.value = computedVar('--sidebar-bg');
    var rh = document.getElementById('pickHeader'); if (rh) rh.value = computedVar('--header-bg');
    var ra = document.getElementById('pickAccent'); if (ra) ra.value = computedVar('--accent');
    syncPresetActive();
  });

  /* ---------- apply persisted theme on load ---------- */
  if (themeState.sidebar || themeState.header || themeState.accent) {
    applyColors(themeState.sidebar, themeState.header, themeState.accent);
  }
  if (themeState.speed) root.setProperty('--dur', themeState.speed + 'ms');
  document.documentElement.setAttribute('data-anim', themeState.anim ? 'on' : 'off');
  if (animToggle) animToggle.classList.toggle('on', themeState.anim);
  if (app && themeState.compact && window.innerWidth > 1024) app.classList.add('collapsed');
  if (compactToggle) compactToggle.classList.toggle('on', themeState.compact);
  document.querySelectorAll('.speed-btn').forEach(function (b) {
    b.classList.toggle('active', parseInt(b.dataset.speed, 10) === themeState.speed);
  });
  syncPresetActive();

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

  /* ---------- profile photo realtime upload ---------- */
  function csrfToken() {
    var m = document.cookie.match(/csrftoken=([\w-]+)/);
    if (m) return m[1];
    var inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : '';
  }
  function setProfilePhoto(url, t) {
    document.querySelectorAll('[data-avatar]').forEach(function (el) {
      var img = el.querySelector('img.av-img');
      var init = el.querySelector('.av-initials');
      if (img) { img.src = url + (t ? '?t=' + t : ''); img.style.display = ''; }
      if (init) init.style.display = 'none';
    });
  }

  var photoUpload = document.getElementById('photoUpload');
  var photoInput = document.getElementById('photoInput');
  if (photoUpload && photoInput) {
    photoUpload.addEventListener('click', function (e) {
      if (e.target.closest('.photo-btn')) photoInput.click();
    });
    photoInput.addEventListener('change', function () {
      var file = photoInput.files && photoInput.files[0];
      if (!file) return;
      if (!/^image\//.test(file.type)) { alert('Please choose an image file.'); photoInput.value = ''; return; }
      if (file.size > 5 * 1024 * 1024) { alert('Image is too large — maximum 5 MB.'); photoInput.value = ''; return; }

      var fd = new FormData();
      fd.append('photo', file);
      photoUpload.classList.add('uploading');
      fetch('/profile/photo/', {
        method: 'POST',
        body: fd,
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken() }
      })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          photoUpload.classList.remove('uploading');
          if (res.ok && res.d && res.d.ok) {
            setProfilePhoto(res.d.url, Date.now());
          } else {
            alert((res.d && res.d.error) || 'Upload failed. Please try again.');
            photoInput.value = '';
          }
        })
        .catch(function () {
          photoUpload.classList.remove('uploading');
          alert('Upload failed. Please try again.');
          photoInput.value = '';
        });
    });
  }
})();
