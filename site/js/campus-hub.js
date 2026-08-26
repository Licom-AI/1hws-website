/* Progressive enhancement for /events/: validated live HWS events and filters. */
(function () {
  "use strict";

  var hub = document.querySelector(".campus-hub");
  var eventList = document.getElementById("campus-events-list");
  if (!hub || !eventList) return;

  var CAL_NS = "https://moderncampus.com/Data/cal/";
  var CALENDAR_ID = hub.getAttribute("data-calendar-id");
  var CALENDAR_PAGE = "https://www.hws.edu/news/calendar.aspx";
  var SNAPSHOT_URL = "/data/hws-events.json";
  var CACHE_KEY = "hws-campus-events-v1";
  var CACHE_TTL = 15 * 60 * 1000;
  var MIN_EVENTS = 10;
  var events = [];
  var windowDays = 30;

  var eventSearch = document.getElementById("event-search");
  var eventCategory = document.getElementById("event-category");
  var eventDate = document.getElementById("event-date");
  var loadMore = document.getElementById("events-load-more");
  var eventStatus = document.getElementById("event-results-status");
  var updateStatus = document.getElementById("campus-update-status");

  function track(name, params) {
    if (typeof window.gtag === "function") window.gtag("event", name, params || {});
  }

  function clean(value) {
    return String(value || "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim();
  }

  function approvedUrl(value) {
    try {
      var url = new URL(clean(value));
      var host = url.hostname.toLowerCase();
      var allowed = host === "hws.edu" || /\.hws\.edu$/.test(host) ||
        host === "hws.campuslabs.com" || host === "hws.joinhandshake.com" ||
        host === "forms.office.com" || host === "docs.google.com" || host === "www.givecampus.com";
      return url.protocol === "https:" && allowed ? url.href : null;
    } catch (err) {
      return null;
    }
  }

  function isoDate(value) {
    value = clean(value);
    if (/^20\d{2}-\d{2}-\d{2}$/.test(value)) {
      var day = new Date(value + "T00:00:00-04:00");
      return isNaN(day.getTime()) ? null : { value: value, date: day, allDay: true };
    }
    var instant = new Date(value);
    return isNaN(instant.getTime()) ? null : { value: instant.toISOString(), date: instant, allDay: false };
  }

  function calendarText(item, name) {
    var node = item.getElementsByTagNameNS(CAL_NS, name)[0];
    return clean(node ? node.textContent : "");
  }

  function parseRss(xmlText) {
    var xml = new DOMParser().parseFromString(xmlText, "application/xml");
    if (xml.querySelector("parsererror")) throw new Error("HWS calendar returned invalid XML");
    var normalized = [];

    Array.prototype.forEach.call(xml.querySelectorAll("item"), function (item) {
      var status = calendarText(item, "status").toUpperCase();
      if (status !== "CONFIRMED" && status !== "TENTATIVE") return;
      var start = isoDate(calendarText(item, "start"));
      var end = isoDate(calendarText(item, "end"));
      var id = calendarText(item, "guid");
      var titleNode = item.querySelector("title");
      var descriptionNode = item.querySelector("description");
      var linkNode = item.querySelector("link");
      var sourceUrl = approvedUrl(linkNode ? linkNode.textContent : "");
      if (!start || !end || start.allDay !== end.allDay || end.date < start.date ||
          !id || !titleNode || !clean(titleNode.textContent) || !sourceUrl) return;

      var place = calendarText(item, "location");
      var room = calendarText(item, "locationRoom");
      var location = place && room && place !== room ? place + ", " + room : (place || room);
      normalized.push({
        id: id,
        title: clean(titleNode.textContent),
        summary: clean(descriptionNode ? descriptionNode.textContent : ""),
        start: start.value,
        end: end.value,
        allDay: start.allDay,
        timezone: "America/New_York",
        category: calendarText(item, "calendar") || "HWS event",
        location: location,
        organizer: calendarText(item, "organizer"),
        status: status,
        sourceUrl: sourceUrl,
        ticketUrl: approvedUrl(calendarText(item, "ticketUrl"))
      });
    });

    var counts = {};
    normalized.forEach(function (event) { counts[event.id] = (counts[event.id] || 0) + 1; });
    normalized.forEach(function (event) {
      if (counts[event.id] > 1) event.id = event.id + "--" + event.start.replace(/[^0-9]/g, "");
    });
    return normalized.sort(function (a, b) { return a.start.localeCompare(b.start) || a.title.localeCompare(b.title); });
  }

  function validate(candidate) {
    if (!Array.isArray(candidate) || candidate.length < MIN_EVENTS) return false;
    var ids = {};
    return candidate.every(function (event) {
      var start = isoDate(event.start);
      var end = isoDate(event.end);
      var sourceUrl = approvedUrl(event.sourceUrl);
      if (!event.id || ids[event.id] || !clean(event.title) || !start || !end ||
          start.allDay !== Boolean(event.allDay) || end.date < start.date ||
          (event.status !== "CONFIRMED" && event.status !== "TENTATIVE") ||
          !sourceUrl || sourceUrl !== event.sourceUrl) return false;
      ids[event.id] = true;
      return true;
    });
  }

  function textElement(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    return node;
  }

  function sourceLink(url, label, kind) {
    var link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    link.setAttribute("data-campus-source", kind);
    link.textContent = label + " ↗";
    return link;
  }

  function easternParts(value) {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: "America/New_York", weekday: "long", year: "numeric", month: "long",
      day: "numeric", hour: "numeric", minute: "2-digit"
    }).format(new Date(value));
  }

  function displayRange(event) {
    if (event.allDay) {
      var dateOnly = new Date(event.start + "T12:00:00Z");
      return new Intl.DateTimeFormat("en-US", {
        timeZone: "America/New_York", weekday: "long", year: "numeric", month: "long", day: "numeric"
      }).format(dateOnly) + " · All day";
    }
    var start = easternParts(event.start);
    var end = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/New_York", hour: "numeric", minute: "2-digit"
    }).format(new Date(event.end));
    return start + "–" + end;
  }

  function googleCalendarUrl(event) {
    function compact(value, allDay) {
      return allDay ? value.replace(/-/g, "") : new Date(value).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
    }
    var url = new URL("https://calendar.google.com/calendar/render");
    url.searchParams.set("action", "TEMPLATE");
    url.searchParams.set("text", event.title);
    var calendarEnd = event.end;
    if (event.allDay) {
      var nextDay = new Date(calendarEnd + "T12:00:00Z");
      nextDay.setUTCDate(nextDay.getUTCDate() + 1);
      calendarEnd = nextDay.toISOString().slice(0, 10);
    }
    if (!event.allDay && new Date(event.end) <= new Date(event.start)) return null;
    url.searchParams.set("dates", compact(event.start, event.allDay) + "/" + compact(calendarEnd, event.allDay));
    url.searchParams.set("details", event.sourceUrl);
    if (event.location) url.searchParams.set("location", event.location);
    return url.href;
  }

  function eventCard(event) {
    var article = document.createElement("article");
    article.className = "campus-event-card";
    article.setAttribute("data-campus-event-id", event.id);
    article.setAttribute("data-start", event.start);
    article.setAttribute("data-category", event.category);
    article.appendChild(textElement("p", "campus-event-kicker", event.category));
    article.appendChild(textElement("h3", "", event.title));

    var meta = document.createElement("p");
    meta.className = "campus-event-meta";
    var time = document.createElement("time");
    time.dateTime = event.start;
    time.textContent = displayRange(event);
    meta.appendChild(time);
    if (event.location) meta.appendChild(textElement("span", "", event.location));
    if (event.organizer) meta.appendChild(textElement("span", "", event.organizer));
    article.appendChild(meta);

    var details = document.createElement("details");
    details.className = "campus-event-details";
    details.appendChild(textElement("summary", "", "Event details"));
    details.appendChild(textElement("p", "", event.summary || "No description was supplied by HWS."));
    var links = document.createElement("p");
    links.className = "campus-event-links";
    links.appendChild(sourceLink(event.sourceUrl, "Official details", "event"));
    if (event.ticketUrl) links.appendChild(sourceLink(event.ticketUrl, "Register or get tickets", "ticket"));
    var calendarUrl = googleCalendarUrl(event);
    if (calendarUrl) links.appendChild(sourceLink(calendarUrl, "Add to calendar", "calendar"));
    details.appendChild(links);
    article.appendChild(details);
    return article;
  }

  function render() {
    if (!events.length) return;
    var query = clean(eventSearch.value).toLowerCase();
    var category = eventCategory.value;
    var now = new Date();
    var cutoff = new Date(now.getTime() + windowDays * 86400000);
    var visible = events.filter(function (event) {
      var haystack = [event.title, event.summary, event.location, event.organizer].join(" ").toLowerCase();
      return new Date(event.end + (event.allDay ? "T23:59:59-04:00" : "")) >= now &&
        new Date(event.start + (event.allDay ? "T00:00:00-04:00" : "")) <= cutoff &&
        (!category || event.category === category) && (!query || haystack.indexOf(query) !== -1);
    });
    eventList.replaceChildren();
    visible.forEach(function (event) { eventList.appendChild(eventCard(event)); });
    if (!visible.length) eventList.appendChild(textElement("p", "campus-empty", "No events match these filters. Try a broader date range or keyword."));
    eventStatus.textContent = "Showing " + visible.length + " event" + (visible.length === 1 ? "" : "s") + " in the next " + windowDays + " days.";
    loadMore.hidden = windowDays >= 90;
  }

  function setEvents(candidate) {
    if (!validate(candidate)) return false;
    events = candidate;
    render();
    return true;
  }

  function filterChanged(control, type) {
    control.addEventListener(type, function () {
      if (control === eventDate) windowDays = Number(eventDate.value) || 30;
      render();
      track("campus_event_filter", {
        filter_type: control.id,
        query_present: Boolean(eventSearch.value.trim()),
        category: eventCategory.value || "all",
        days: windowDays
      });
    });
  }
  filterChanged(eventSearch, "input");
  filterChanged(eventCategory, "change");
  filterChanged(eventDate, "change");
  loadMore.addEventListener("click", function () {
    windowDays = Math.min(90, Math.max(30, windowDays) + 30);
    eventDate.value = String(windowDays);
    render();
    track("campus_event_filter", { filter_type: "load_more", days: windowDays });
  });

  eventList.addEventListener("toggle", function (event) {
    if (!event.target.matches("details") || !event.target.open) return;
    var card = event.target.closest("[data-campus-event-id]");
    track("campus_event_expand", { event_id: card ? card.getAttribute("data-campus-event-id") : null });
  }, true);

  document.addEventListener("click", function (event) {
    var link = event.target.closest && event.target.closest("[data-campus-source]");
    if (!link) return;
    track("campus_official_source_click", {
      source_type: link.getAttribute("data-campus-source"), link_url: link.href
    });
  });

  var clubSearch = document.getElementById("club-search");
  var clubCategory = document.getElementById("club-category");
  var clubList = document.getElementById("campus-clubs-list");
  var clubStatus = document.getElementById("club-results-status");
  function filterClubs() {
    if (!clubSearch || clubSearch.disabled) return;
    var query = clubSearch.value.trim().toLowerCase();
    var category = clubCategory.value;
    var cards = Array.prototype.slice.call(clubList.querySelectorAll("[data-club-name]"));
    var shown = 0;
    cards.forEach(function (card) {
      var match = (!query || card.getAttribute("data-club-name").toLowerCase().indexOf(query) !== -1) &&
        (!category || card.getAttribute("data-club-category") === category);
      card.hidden = !match;
      if (match) shown++;
    });
    clubStatus.textContent = "Showing " + shown + " club" + (shown === 1 ? "" : "s") + ".";
    track("campus_club_search", { query_present: Boolean(query), category: category || "all", results: shown });
  }
  if (clubSearch && !clubSearch.disabled) {
    clubSearch.addEventListener("input", filterClubs);
    clubCategory.addEventListener("change", filterClubs);
  }

  function snapshotStatus(retrievedAt) {
    var date = clean(retrievedAt).slice(0, 10) || "the latest build";
    updateStatus.textContent = "Showing the snapshot from " + date + ".";
  }

  function liveUrl() {
    function ymd(date) { return date.toISOString().slice(0, 10); }
    var start = new Date();
    var end = new Date(start.getTime() + 90 * 86400000);
    return "https://api.calendar.moderncampus.net/pubcalendar/" + encodeURIComponent(CALENDAR_ID) +
      "/rss?url=" + encodeURIComponent(CALENDAR_PAGE) + "&hash=true&text=true&start=" + ymd(start) + "&end=" + ymd(end);
  }

  function fetchLive() {
    try {
      var cached = JSON.parse(sessionStorage.getItem(CACHE_KEY) || "null");
      if (cached && Date.now() - cached.savedAt < CACHE_TTL && setEvents(cached.events)) {
        updateStatus.textContent = "Updated from HWS just now.";
        return Promise.resolve();
      }
    } catch (err) { /* Ignore corrupt or blocked session storage. */ }

    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 5000);
    return fetch(liveUrl(), { signal: controller.signal, headers: { Accept: "application/xml" } })
      .then(function (response) {
        if (!response.ok) throw new Error("HWS calendar request failed");
        return response.text();
      })
      .then(function (xml) {
        var candidate = parseRss(xml);
        if (!setEvents(candidate)) throw new Error("HWS calendar response did not pass validation");
        updateStatus.textContent = "Updated from HWS just now.";
        try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ savedAt: Date.now(), events: candidate })); } catch (err) { /* optional */ }
      })
      .catch(function () { snapshotStatus(hub.getAttribute("data-snapshot-retrieved")); })
      .finally(function () { clearTimeout(timer); });
  }

  fetch(SNAPSHOT_URL, { headers: { Accept: "application/json" } })
    .then(function (response) { if (!response.ok) throw new Error("snapshot unavailable"); return response.json(); })
    .then(function (snapshot) {
      if (setEvents(snapshot.events)) snapshotStatus(snapshot.source && snapshot.source.retrievedAt);
    })
    .catch(function () { /* The server-rendered 24-event fallback remains visible. */ })
    .then(fetchLive);
}());
