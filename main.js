/* Shared across every page: mobile nav toggle + footer year */
document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.getElementById('navToggle');
  var links = document.getElementById('navLinks');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      links.classList.toggle('open');
    });
  }
  var yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* Nav "Tools" dropdown (Affordability Calculator + Upgrade Checklist):
     hover already reveals it on desktop via CSS, but a click/tap toggle is
     needed for touchscreens and keyboard users, and for mobile where the
     nav is already a vertical list. */
  var navDropdowns = document.querySelectorAll('.nav-dropdown');
  navDropdowns.forEach(function (dropdown) {
    var toggleBtn = dropdown.querySelector('.nav-dropdown-toggle');
    if (!toggleBtn) return;
    toggleBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      dropdown.classList.toggle('open');
    });
  });
  document.addEventListener('click', function (e) {
    navDropdowns.forEach(function (dropdown) {
      if (!dropdown.contains(e.target)) dropdown.classList.remove('open');
    });
  });

  /* Blog page only: auto-sort posts newest-first by each row's data-date
     attribute (YYYY-MM-DD), so Serene can paste a new post anywhere in
     blog.html and it lands in the right place automatically — no manual
     reordering needed. No-op on every other page (no .blog-list there). */
  var blogList = document.querySelector('.blog-list');
  if (blogList) {
    var rows = Array.prototype.slice.call(blogList.querySelectorAll('.blog-row'));
    rows.sort(function (a, b) {
      var dateA = a.getAttribute('data-date') || '';
      var dateB = b.getAttribute('data-date') || '';
      return dateB.localeCompare(dateA); // ISO dates sort correctly as strings
    });
    rows.forEach(function (row) { blogList.appendChild(row); });
  }

  /* New Launches page only: region/tenure filter chips + TOP-date sort.
     No-op on every other page (no #launchGrid there). Add data-region
     ("CCR"/"RCR"/"OCR"), data-tenure ("leasehold"/"freehold") and
     data-top (year.quarter, e.g. "2029.3" for TOP Q3 2029) to any new
     .launch-card and it's picked up automatically — no script changes
     needed for new projects. */
  var launchGrid = document.getElementById('launchGrid');
  if (launchGrid) {
    var regionButtons = Array.prototype.slice.call(document.querySelectorAll('[data-filter-region]'));
    var tenureButtons = Array.prototype.slice.call(document.querySelectorAll('[data-filter-tenure]'));
    var topSort = document.getElementById('topSort');
    var noResults = document.getElementById('noLaunchResults');
    var activeRegion = 'all';
    var activeTenure = 'all';

    function applyLaunchFilters() {
      var cards = Array.prototype.slice.call(launchGrid.querySelectorAll('.launch-card'));
      var visibleCount = 0;

      cards.sort(function (a, b) {
        var topA = parseFloat(a.getAttribute('data-top')) || 0;
        var topB = parseFloat(b.getAttribute('data-top')) || 0;
        return (topSort && topSort.value === 'desc') ? topB - topA : topA - topB;
      });
      cards.forEach(function (card) { launchGrid.appendChild(card); });

      cards.forEach(function (card) {
        var regionMatch = activeRegion === 'all' || card.getAttribute('data-region') === activeRegion;
        var tenureMatch = activeTenure === 'all' || card.getAttribute('data-tenure') === activeTenure;
        var show = regionMatch && tenureMatch;
        card.style.display = show ? '' : 'none';
        if (show) visibleCount++;
      });

      if (noResults) noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }

    regionButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        regionButtons.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        activeRegion = btn.getAttribute('data-filter-region');
        applyLaunchFilters();
      });
    });

    tenureButtons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        tenureButtons.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        activeTenure = btn.getAttribute('data-filter-tenure');
        applyLaunchFilters();
      });
    });

    if (topSort) topSort.addEventListener('change', applyLaunchFilters);

    applyLaunchFilters();
  }
});
