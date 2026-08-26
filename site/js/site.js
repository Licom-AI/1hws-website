/* ==========================================================================
   HWS AI Club — progressive enhancement for the static pages.
   Everything here is optional polish; the pages are fully usable without JS.
   ========================================================================== */
(function () {
  "use strict";

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- GA4 event helper ----
     Wraps gtag() so a blocked/missing analytics script (ad blockers, consent
     tools) never breaks the feature it's attached to. See docs/ANALYTICS.md
     for the full event list and which of these are configured as GA4
     conversions. */
  function track(name, params) {
    if (typeof window.gtag === "function") window.gtag("event", name, params || {});
  }

  function currentMajorSlug() {
    var m = location.pathname.match(/^\/majors\/([^/]+)\/?/);
    return m ? m[1] : null;
  }

  /* ---- CTA clicks: join intent, library entry, and the real conversion ----
     Any element with data-cta is tracked generically, so a new CTA only needs
     the attribute — no JS change. skool-join is the site's real conversion
     (clicking through to the club's actual community); everything else is a
     softer intent/engagement signal. */
  document.addEventListener("click", function (e) {
    var el = e.target.closest && e.target.closest("[data-cta]");
    if (!el) return;
    var cta = el.getAttribute("data-cta");
    if (cta === "skool-join") {
      track("join_community_click", { link_url: el.getAttribute("href"), location: cta });
    } else if (cta === "founder-link") {
      track("founder_link_click", {
        founder: el.getAttribute("data-founder"),
        link_label: el.getAttribute("data-link-label"),
        link_url: el.getAttribute("href")
      });
    } else if (cta.indexOf("founder") !== -1) {
      track("founder_card_click", { founder: el.getAttribute("data-founder"), location: cta });
    } else if (cta.indexOf("browse") !== -1 || cta.indexOf("library") !== -1) {
      track("library_cta_click", { location: cta });
    } else {
      track("join_cta_click", { location: cta });
    }
  });

  /* ---- Tutorial video clicks: which use case's linked video actually gets watched ---- */
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest(".uc-watch");
    if (!a) return;
    var card = a.closest(".usecase-card");
    track("tutorial_video_click", {
      major: currentMajorSlug(),
      use_case_number: card ? card.getAttribute("data-uc") : null,
      difficulty: card ? card.getAttribute("data-difficulty") : null,
      video_title: a.getAttribute("data-video-title"),
      link_url: a.getAttribute("href")
    });
  });

  /* ---- Founder song embed: real play / near-complete tracking ----
     Uses Spotify's own iFrame API (playback_update events) rather than
     guessing from clicks — a click on the embed can't be observed directly
     since it's cross-origin, but the API exposes real transport state. Loads
     only on pages that actually have a song embed, and never breaks the
     embed itself if Spotify's API is unavailable or changes shape. */
  (function spotifyTracking() {
    var placeholders = Array.prototype.slice.call(document.querySelectorAll("[data-spotify-uri]"));
    if (!placeholders.length) return;

    window.onSpotifyIframeApiReady = function (IFrameAPI) {
      placeholders.forEach(function (el) {
        var founder = el.getAttribute("data-founder");
        var songTitle = el.getAttribute("data-song-title");
        var songArtist = el.getAttribute("data-song-artist");
        var hasPlayed = false;
        var hasCompleted = false;

        try {
          IFrameAPI.createController(
            el,
            { uri: el.getAttribute("data-spotify-uri"), width: "100%", height: "152" },
            function (controller) {
              controller.addListener("playback_update", function (e) {
                var d = (e && e.data) || {};
                if (!d.isPaused && !hasPlayed) {
                  hasPlayed = true;
                  track("song_played", { founder: founder, song_title: songTitle, song_artist: songArtist });
                }
                if (!hasCompleted && d.duration > 0 && d.position / d.duration >= 0.9) {
                  hasCompleted = true;
                  track("song_completed", { founder: founder, song_title: songTitle, song_artist: songArtist });
                }
              });
            }
          );
        } catch (err) { /* Spotify API shape changed — embed still works, tracking just no-ops */ }
      });
    };

    var script = document.createElement("script");
    script.src = "https://open.spotify.com/embed/iframe-api/v1";
    script.async = true;
    document.head.appendChild(script);
  })();

  /* ---- Backward-compat: old hash-router links still work ----
     e.g. /#/major/history  ->  /majors/history/   |   /#/majors -> /majors/ */
  (function hashCompat() {
    var h = window.location.hash;
    if (!h || h.indexOf("#/") !== 0) return;
    var m = h.match(/^#\/major\/([^/]+)(?:\/(\d+))?$/);
    if (m) {
      window.location.replace("/majors/" + m[1] + "/" + (m[2] ? "#uc-" + m[2] : ""));
    } else if (h === "#/majors") {
      window.location.replace("/majors/");
    } else if (h === "#/about" || h === "#/") {
      window.location.replace("/" + (h === "#/about" ? "#about" : ""));
    }
  })();

  /* ---- Majors index: live search filter over the static list ---- */
  var search = document.getElementById("major-search");
  var grid = document.getElementById("majors-grid");
  if (search && grid) {
    var cards = Array.prototype.slice.call(grid.querySelectorAll(".major-card"));
    var divisions = Array.prototype.slice.call(grid.querySelectorAll(".major-division"));
    var hint = document.getElementById("search-hint");
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (c) {
        var match = c.textContent.toLowerCase().indexOf(q) !== -1;
        c.style.display = match ? "" : "none";
        if (match) shown++;
      });
      /* The list is grouped under division headings, so a heading with every
         card filtered out would otherwise sit there looking like a dead section. */
      divisions.forEach(function (d) {
        var any = Array.prototype.some.call(d.querySelectorAll(".major-card"), function (c) {
          return c.style.display !== "none";
        });
        d.style.display = any ? "" : "none";
      });
      if (hint) {
        hint.textContent = q
          ? shown + " major" + (shown === 1 ? "" : "s") + " found."
          : "Type to filter, or browse all " + cards.length + " majors below.";
      }
    });
    search.addEventListener("keydown", function (e) {
      if (e.key !== "Enter") return;
      var visible = cards.filter(function (c) { return c.style.display !== "none"; });
      if (visible.length === 1) window.location.href = visible[0].getAttribute("href");
    });

    /* Honour ?q= so a shared filtered-majors URL opens in the expected state. */
    try {
      var q0 = new URLSearchParams(window.location.search).get("q");
      if (q0) {
        search.value = q0;
        search.dispatchEvent(new Event("input"));
      }
    } catch (err) { /* older browser: the list just renders unfiltered */ }
  }

  /* ---- Major page: difficulty filter ---- */
  var filterBar = document.querySelector(".difficulty-filter");
  var ucGrid = document.getElementById("usecases-grid");
  if (filterBar && ucGrid) {
    var ucCards = Array.prototype.slice.call(ucGrid.querySelectorAll(".usecase-card"));
    filterBar.addEventListener("click", function (e) {
      var btn = e.target.closest(".filter-btn");
      if (!btn) return;
      var f = btn.getAttribute("data-filter");
      filterBar.querySelectorAll(".filter-btn").forEach(function (b) {
        b.setAttribute("aria-pressed", b === btn ? "true" : "false");
      });
      ucCards.forEach(function (c) {
        c.style.display = (f === "All" || c.getAttribute("data-difficulty") === f) ? "" : "none";
      });
    });
  }

  /* ---- Copy the starter prompt (progressive: the text is always visible) ---- */
  document.addEventListener("click", function (e) {
    var btn = e.target.closest && e.target.closest(".uc-copy");
    if (!btn) return;
    var pre = document.getElementById(btn.getAttribute("data-copy"));
    if (!pre) return;
    var text = pre.textContent;
    var card = btn.closest(".usecase-card");

    // Fired on click intent, not on confirmed clipboard success: a copy that
    // silently fails still means the student engaged with this exact prompt.
    track("prompt_copied", {
      major: currentMajorSlug(),
      use_case_number: card ? card.getAttribute("data-uc") : null,
      difficulty: card ? card.getAttribute("data-difficulty") : null
    });

    function flash(label) {
      var prev = btn.getAttribute("data-label") || "Copy";
      btn.setAttribute("data-label", prev);
      btn.textContent = label;
      btn.setAttribute("data-copied", "1");
      setTimeout(function () {
        btn.textContent = prev;
        btn.removeAttribute("data-copied");
      }, 2000);
    }

    // Tier 1: async clipboard. Tier 2: select + execCommand. Tier 3: leave it
    // selected so the user can press Cmd/Ctrl+C. Something always works.
    function fallback() {
      var ok = false;
      selectText(pre);
      try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
      flash(ok ? "Copied" : "Press ⌘C");
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flash("Copied"); }, fallback);
    } else {
      fallback();
    }
  });

  function selectText(el) {
    try {
      var r = document.createRange();
      r.selectNodeContents(el);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
    } catch (err) { /* selection unsupported — text is still visible to copy */ }
  }

  /* ---- Deep-link flash: /majors/<slug>/#uc-7 highlights that card ---- */
  (function flashTarget() {
    var h = window.location.hash;
    if (!/^#uc-\d+$/.test(h)) return;
    var el = document.getElementById(h.slice(1));
    if (!el || !el.classList.contains("usecase-card")) return;
    setTimeout(function () {
      el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
      el.classList.add("uc-flash");
      setTimeout(function () { el.classList.remove("uc-flash"); }, 4000);
    }, 120);
  })();
})();
