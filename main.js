/* PostHog website analytics (added Oct 2026).
   Loads on every page because every page already includes main.js.
   Records pageviews, visitors, traffic sources, devices and clicks.
   The phc_ key below is a public project key — it is safe to be visible. */
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
posthog.init('phc_rg6iVEBgbirYoH76SaVRhMCa43uwjWztDfHiS8peBGJK', {
  api_host: 'https://us.i.posthog.com',
  person_profiles: 'identified_only',
  capture_pageview: true,
  capture_pageleave: true,
  enable_heatmaps: true
});

/* Exclude Serene's own visits. Open any page once with ?notrack=1 on each of
   your own phones/browsers and that browser stops being counted (it stays off
   until browser data is cleared). Undo with ?track=1. */
(function () {
  var q = new URLSearchParams(window.location.search);
  if (q.get('notrack') === '1') {
    posthog.opt_out_capturing();
    alert('Analytics is now OFF for this browser. Your visits will not be counted.');
  } else if (q.get('track') === '1') {
    posthog.opt_in_capturing();
    alert('Analytics is now ON for this browser.');
  }
})();

/* WhatsApp lead clicks: record every tap on a WhatsApp link (header button,
   floating button, CTA banners, blog posts, chatbot) as a "whatsapp_clicked"
   event, sent instantly so it isn't lost when the WhatsApp app opens. */
document.addEventListener('click', function (e) {
  var link = e.target.closest && e.target.closest('a[href*="wa.me"], a[href*="whatsapp.com"]');
  if (!link) return;
  var where = link.classList.contains('fab-wa') ? 'floating button'
    : link.closest('header') ? 'header'
    : link.closest('.cta-banner') ? 'cta banner'
    : link.closest('footer') ? 'footer'
    : 'page content';
  posthog.capture('whatsapp_clicked', {
    button_text: (link.textContent || '').trim().slice(0, 60) || '(icon)',
    button_location: where,
    page_path: window.location.pathname
  }, { send_instantly: true, transport: 'sendBeacon' });
}, true);

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

  /* Add "Market Map" to the Tools menu on every page from here, so the
     other HTML pages don't each need editing. Skipped where the page
     already has the link written in (market-map.html itself). */
  document.querySelectorAll('.nav-dropdown-menu').forEach(function (menu) {
    if (menu.querySelector('a[href="market-map.html"]')) return;
    var mm = document.createElement('a');
    mm.href = 'market-map.html';
    mm.textContent = 'Market Map';
    menu.appendChild(mm);
  });

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
     regardless of what the visitor picks in the Sort by TOP dropdown.
     Cards between the ERA:START / ERA:END markers in new-launches.html are
     rewritten every week by scripts/update_new_launches.py and also carry
     data-launch (YYYY-MM-DD), data-status ("selling"/"upcoming") and
     data-ptype ("condo"/"ec"/"landed") for the Status / Type filters. */
  var launchGrid = document.getElementById('launchGrid');
  if (launchGrid) {
    var regionButtons = Array.prototype.slice.call(document.querySelectorAll('[data-filter-region]'));
    var tenureButtons = Array.prototype.slice.call(document.querySelectorAll('[data-filter-tenure]'));
    var statusButtons = Array.prototype.slice.call(document.querySelectorAll('[data-filter-status]'));
    var ptypeButtons = Array.prototype.slice.call(document.querySelectorAll('[data-filter-ptype]'));
    var topSort = document.getElementById('topSort');
    var noResults = document.getElementById('noLaunchResults');
    var activeRegion = 'all';
    var activeTenure = 'all';
    var activeStatus = 'all';
    var activePtype = 'all';

    function applyLaunchFilters() {
      var cards = Array.prototype.slice.call(launchGrid.querySelectorAll('.launch-card'));
      var visibleCount = 0;

      var pinned = cards.filter(function (card) { return card.getAttribute('data-pinned') === 'true'; });
      var rest = cards.filter(function (card) { return card.getAttribute('data-pinned') !== 'true'; });

      var sortBy = topSort ? topSort.value : 'asc';
      rest.sort(function (a, b) {
        if (sortBy === 'launch') {
          /* newest launch first; cards without a launch date go last */
          return (b.getAttribute('data-launch') || '').localeCompare(a.getAttribute('data-launch') || '');
        }
        var topA = parseFloat(a.getAttribute('data-top')) || 0;
        var topB = parseFloat(b.getAttribute('data-top')) || 0;
        return sortBy === 'desc' ? topB - topA : topA - topB;
      });

      var ordered = pinned.concat(rest);
      ordered.forEach(function (card) { launchGrid.appendChild(card); });

      ordered.forEach(function (card) {
        var regionMatch = activeRegion === 'all' || card.getAttribute('data-region') === activeRegion;
        var tenureMatch = activeTenure === 'all' || card.getAttribute('data-tenure') === activeTenure;
        var statusMatch = activeStatus === 'all' || card.getAttribute('data-status') === activeStatus || card.getAttribute('data-pinned') === 'true';
        var ptypeMatch = activePtype === 'all' || (card.getAttribute('data-ptype') || 'condo') === activePtype;
        var show = regionMatch && tenureMatch && statusMatch && ptypeMatch;
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

    function bindChips(buttons, attr, set) {
      buttons.forEach(function (btn) {
        btn.addEventListener('click', function () {
          buttons.forEach(function (b) { b.classList.remove('active'); });
          btn.classList.add('active');
          set(btn.getAttribute(attr));
          applyLaunchFilters();
        });
      });
    }
    bindChips(statusButtons, 'data-filter-status', function (v) { activeStatus = v; });
    bindChips(ptypeButtons, 'data-filter-ptype', function (v) { activePtype = v; });

    if (topSort) topSort.addEventListener('change', applyLaunchFilters);

    applyLaunchFilters();
  }

  /* Subscribe form (on subscribers.html only) — posts to the SAME Google
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

      // Subscribers page only: which topics were ticked, and who referred them (?ref=Name).
      // Both go into the existing "Source" column, so the Google Apps Script needs no change.
      var source = window.location.pathname;
      var topicBoxes = document.querySelectorAll('input[name="subscribeTopic"]');
      if (topicBoxes.length) {
        var topics = [];
        topicBoxes.forEach(function (box) { if (box.checked) topics.push(box.value); });
        if (!topics.length) {
          subscribeError.textContent = 'Please tick at least one: Blog updates or Newsletter.';
          subscribeError.classList.add('show');
          return;
        }
        source += ' · ' + topics.join(' + ');
      }
      var referrer = getReferrer();
      if (referrer) source += ' · referred by: ' + referrer;

      subscribeBtn.disabled = true;
      subscribeBtn.textContent = 'Subscribing...';

      fetch(SUBSCRIBE_WEBHOOK_URL, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'text/plain' },
        body: JSON.stringify({ formType: 'subscribe', email: email, source: source, page: window.location.href })
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

  /* Referrals (subscribers.html). A friend's link looks like subscribers.html?ref=Jane%20Tan —
     the name is shown on arrival and sent along with their subscription. */
  function getReferrer() {
    var ref = new URLSearchParams(window.location.search).get('ref');
    return ref ? ref.replace(/[<>]/g, '').trim().slice(0, 60) : '';
  }

  var referredBy = document.getElementById('referredBy');
  if (referredBy && getReferrer()) {
    referredBy.textContent = getReferrer() + ' invited you to subscribe.';
    referredBy.hidden = false;
  }

  var refName = document.getElementById('refName');
  if (refName) {
    var refLink = document.getElementById('refLink');
    var refCopy = document.getElementById('refCopy');
    var refWhatsApp = document.getElementById('refWhatsApp');
    var pageUrl = 'https://sereneleeproperty.com/subscribers.html';

    var updateRefLink = function () {
      var name = refName.value.trim();
      var link = name ? pageUrl + '?ref=' + encodeURIComponent(name) : pageUrl;
      refLink.value = link;
      refWhatsApp.href = 'https://wa.me/?text=' + encodeURIComponent(
        "I've been reading Serene Lee's Singapore property guides — subscribe here for new guides and new launch updates: " + link
      );
    };
    refName.addEventListener('input', updateRefLink);
    updateRefLink();

    refCopy.addEventListener('click', function () {
      var done = function () {
        refCopy.textContent = 'Copied!';
        setTimeout(function () { refCopy.textContent = 'Copy link'; }, 2000);
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(refLink.value).then(done, function () { refLink.select(); });
      } else {
        refLink.select();
        document.execCommand('copy');
        done();
      }
    });
  }

  /* "Refer someone" form (subscribers.html) — saved to the "Referrals" tab of the
     same Google Sheet (formType: 'referral'), and Serene gets an email alert. */
  var referralForm = document.getElementById('referralForm');
  if (referralForm) {
    var refSubmit = document.getElementById('refSubmit');
    var refSuccess = document.getElementById('refSuccess');
    var refError = document.getElementById('refError');
    var val = function (id) { return document.getElementById(id).value.trim(); };

    referralForm.addEventListener('submit', function (e) {
      e.preventDefault();
      refSuccess.classList.remove('show');
      refError.classList.remove('show');

      var problem =
        !val('refYourName') ? 'Please enter your name.' :
        !val('refYourContact') ? 'Please enter your phone or email, so Serene knows who referred.' :
        !val('refFriendName') ? "Please enter your friend's name." :
        !/^\+?[\d\s-]{8,}$/.test(val('refFriendPhone')) ? "Please enter your friend's phone number." :
        val('refFriendEmail') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val('refFriendEmail')) ? "Please check your friend's email address." :
        !document.getElementById('refConsent').checked ? 'Please confirm your friend has agreed to be contacted.' :
        '';
      if (problem) {
        refError.textContent = problem;
        refError.classList.add('show');
        return;
      }

      refSubmit.disabled = true;
      refSubmit.textContent = 'Sending...';

      fetch(SUBSCRIBE_WEBHOOK_URL, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'text/plain' },
        body: JSON.stringify({
          formType: 'referral',
          referrerName: val('refYourName'),
          referrerContact: val('refYourContact'),
          friendName: val('refFriendName'),
          friendPhone: val('refFriendPhone'),
          friendEmail: val('refFriendEmail'),
          lookingTo: val('refLookingTo'),
          notes: val('refNotes'),
          consent: true,
          page: window.location.href
        })
      })
        .then(function () {
          refSuccess.classList.add('show');
          referralForm.reset();
        })
        .catch(function () {
          refError.textContent = 'Something went wrong — please try again, or WhatsApp Serene directly.';
          refError.classList.add('show');
        })
        .finally(function () {
          refSubmit.disabled = false;
          refSubmit.textContent = 'Send referral';
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
