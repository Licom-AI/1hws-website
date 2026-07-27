/* ==========================================================================
   HWS AI Club — progressive enhancement for the static pages.
   Everything here is optional polish; the pages are fully usable without JS.
   ========================================================================== */
(function () {
  "use strict";

  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
    var hint = document.getElementById("search-hint");
    search.addEventListener("input", function () {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (c) {
        var match = c.textContent.toLowerCase().indexOf(q) !== -1;
        c.style.display = match ? "" : "none";
        if (match) shown++;
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
