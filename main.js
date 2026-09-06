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
     needed for new projects. Add data-pinned="true" to Serene's own
     new-launch spotlight write-ups (as opposed to the regular ERA
     listings) to always keep them first, ahead of the TOP-date sort,
     regardless of what the visitor picks in the Sort by TOP dropdown. */
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

      var pinned = cards.filter(function (card) { return card.getAttribute('data-pinned') === 'true'; });
      var rest = cards.filter(function (card) { return card.getAttribute('data-pinned') !== 'true'; });

      rest.sort(function (a, b) {
        var topA = parseFloat(a.getAttribute('data-top')) || 0;
        var topB = parseFloat(b.getAttribute('data-top')) || 0;
        return (topSort && topSort.value === 'desc') ? topB - topA : topA - topB;
      });

      var ordered = pinned.concat(rest);
      ordered.forEach(function (card) { launchGrid.appendChild(card); });

      ordered.forEach(function (card) {
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

  /* Subscribe form (currently on index.html only) — posts to the SAME Google
     Apps Script Web App used by the calculator, contact form and upgrade
     checklist (see GAS_WEBHOOK_URL in those pages). That one script now
     handles both: it tells this request apart by formType: 'subscribe'
     below, and files it into a separate "Subscribers" tab in the same
     Google Sheet. No-op on any page without a #subscribeForm. */
  var SUBSCRIBE_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbzxomLsd_yvi8pEaXvHK3qddAPdnX7889wnjU4i5AoxXIv7dQv7h973bZ9gwQq_1dk/exec";
  var subscribeForm = document.getElementById('subscribeForm');
  if (subscribeForm) {
    var subscribeEmail = document.getElementById('subscribeEmail');
    var subscribeBtn = document.getElementById('subscribeBtn');
    var subscribeSuccess = document.getElementById('subscribeSuccess');
    var subscribeError = document.getElementById('subscribeError');

    subscribeForm.addEventListener('submit', function (e) {
      e.preventDefault();
      subscribeSuccess.classList.remove('show');
      subscribeError.classList.remove('show');

      var email = subscribeEmail.value.trim();
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        subscribeError.textContent = 'Please enter a valid email address.';
        subscribeError.classList.add('show');
        return;
      }

      if (!SUBSCRIBE_WEBHOOK_URL || SUBSCRIBE_WEBHOOK_URL.indexOf('PASTE_YOUR') === 0) {
        subscribeError.textContent = "Subscriptions aren't connected yet — please WhatsApp Serene directly for now.";
        subscribeError.classList.add('show');
        return;
      }

      subscribeBtn.disabled = true;
      subscribeBtn.textContent = 'Subscribing...';

      fetch(SUBSCRIBE_WEBHOOK_URL, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'text/plain' },
        body: JSON.stringify({ formType: 'subscribe', email: email, source: window.location.pathname, page: window.location.href })
      })
        .then(function () {
          subscribeSuccess.classList.add('show');
          subscribeForm.reset();
        })
        .catch(function () {
          subscribeError.textContent = 'Something went wrong — please try again or WhatsApp Serene directly.';
          subscribeError.classList.add('show');
        })
        .finally(function () {
          subscribeBtn.disabled = false;
          subscribeBtn.textContent = 'Subscribe';
        });
    });
  }

  /* Click-to-enlarge lightbox for any .enlargeable-img (currently: the two
     lease decay infographics). Add the class to any future image to get the
     same behavior. No-op on any page without .enlargeable-img / #infographicLightbox. */
  var enlargeableImgs = document.querySelectorAll('.enlargeable-img');
  var infographicLightbox = document.getElementById('infographicLightbox');
  if (enlargeableImgs.length && infographicLightbox) {
    var lightboxClose = document.getElementById('lightboxClose');
    var lightboxImg = document.getElementById('lightboxImg');

    function openInfographicLightbox(src, alt) {
      if (lightboxImg) {
        lightboxImg.src = src;
        lightboxImg.alt = alt || '';
      }
      infographicLightbox.hidden = false;
      document.body.style.overflow = 'hidden';
    }
    function closeInfographicLightbox() {
      infographicLightbox.hidden = true;
      document.body.style.overflow = '';
    }

    enlargeableImgs.forEach(function (img) {
      img.addEventListener('click', function () {
        openInfographicLightbox(img.src, img.alt);
      });
    });
    if (lightboxClose) {
      lightboxClose.addEventListener('click', function (e) {
        e.stopPropagation();
        closeInfographicLightbox();
      });
    }
    infographicLightbox.addEventListener('click', function () {
      closeInfographicLightbox();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeInfographicLightbox();
    });
  }
});
