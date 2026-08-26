/* Progressive enhancement for /events/: validated HWS data, calendar, agenda, and dialog. */
(function () {
  "use strict";

  var hub = document.querySelector(".campus-hub");
  var calendarGrid = document.getElementById("calendar-grid");
  var mobileAgenda = document.getElementById("events-mobile-agenda");
  if (!hub || !calendarGrid || !mobileAgenda) return;

  var CAL_NS = "https://moderncampus.com/Data/cal/";
  var CALENDAR_ID = hub.getAttribute("data-calendar-id");
  var CALENDAR_PAGE = "https://www.hws.edu/news/calendar.aspx";
  var SNAPSHOT_URL = "/data/hws-events.json";
  var CACHE_KEY = "hws-campus-events-v2";
  var CACHE_TTL = 15 * 60 * 1000;
  var MIN_EVENTS = 10;
  var EASTERN = "America/New_York";
  var WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

  var eventSearch = document.getElementById("event-search");
  var eventCategory = document.getElementById("event-category");
  var eventStatus = document.getElementById("event-results-status");
  var updateStatus = document.getElementById("campus-update-status");
  var monthLabel = document.getElementById("calendar-month-label");
  var previousMonth = document.getElementById("calendar-prev");
  var todayButton = document.getElementById("calendar-today");
  var nextMonth = document.getElementById("calendar-next");

  var dialog = document.getElementById("event-dialog");
  var dialogBack = document.getElementById("event-dialog-back");
  var dialogClose = document.getElementById("event-dialog-close");
  var dialogCategory = document.getElementById("event-dialog-category");
  var dialogTitle = document.getElementById("event-dialog-title");
  var dialogDate = document.getElementById("event-dialog-date");
  var dialogLocationRow = document.getElementById("event-dialog-location-row");
  var dialogLocation = document.getElementById("event-dialog-location");
  var dialogOrganizerRow = document.getElementById("event-dialog-organizer-row");
  var dialogOrganizer = document.getElementById("event-dialog-organizer");
  var dialogDescription = document.getElementById("event-dialog-description");
  var dialogDayList = document.getElementById("event-dialog-day-list");
  var dialogLinks = document.getElementById("event-dialog-links");

  var state = {
    events: [],
    activeMonth: easternMonthKey(new Date()),
    query: "",
    category: "",
    selectedDay: null,
    selectedEventId: null
  };
  var dialogOpener = null;
  var dialogReturnDay = null;
  var usingFallbackDialog = false;

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
      var day = new Date(value + "T12:00:00Z");
      return isNaN(day.getTime()) ? null : { value: value, date: day, allDay: true };
    }
    var instant = new Date(value);
    return isNaN(instant.getTime()) ? null : { value: instant.toISOString(), date: instant, allDay: false };
  }

  function easternDateParts(value) {
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: EASTERN, year: "numeric", month: "2-digit", day: "2-digit"
    }).formatToParts(value instanceof Date ? value : new Date(value));
    var result = {};
    parts.forEach(function (part) { if (part.type !== "literal") result[part.type] = part.value; });
    return result;
  }

  function easternDayKey(value) {
    var parts = easternDateParts(value);
    return parts.year + "-" + parts.month + "-" + parts.day;
  }

  function easternMonthKey(value) {
    return easternDayKey(value).slice(0, 7);
  }

  function dayKeyDate(dayKey) {
    var pieces = dayKey.split("-").map(Number);
    return new Date(Date.UTC(pieces[0], pieces[1] - 1, pieces[2], 12));
  }

  function addDayKey(dayKey, amount) {
    var date = dayKeyDate(dayKey);
    date.setUTCDate(date.getUTCDate() + amount);
    return date.toISOString().slice(0, 10);
  }

  function shiftMonth(monthKey, amount) {
    var pieces = monthKey.split("-").map(Number);
    var date = new Date(Date.UTC(pieces[0], pieces[1] - 1 + amount, 1));
    return date.toISOString().slice(0, 7);
  }

  function mondayFirstMonthMatrix(monthKey) {
    var first = dayKeyDate(monthKey + "-01");
    var mondayOffset = (first.getUTCDay() + 6) % 7;
    var firstCell = new Date(first.getTime());
    firstCell.setUTCDate(firstCell.getUTCDate() - mondayOffset);
    var cells = [];
    for (var index = 0; index < 42; index++) {
      var date = new Date(firstCell.getTime());
      date.setUTCDate(date.getUTCDate() + index);
      cells.push(date.toISOString().slice(0, 10));
    }
    return cells;
  }

  function eventDayKeys(event) {
    var first = event.allDay ? event.start : easternDayKey(event.start);
    var last;
    if (event.allDay) {
      // Modern Campus all-day end dates are inclusive.
      last = event.end;
    } else {
      // Modern Campus timed end dates are exclusive; midnight belongs to the prior day.
      var end = new Date(event.end);
      last = easternDayKey(new Date(end.getTime() - 1));
    }
    var keys = [];
    var cursor = first;
    for (var guard = 0; cursor <= last && guard < 370; guard++) {
      keys.push(cursor);
      cursor = addDayKey(cursor, 1);
    }
    return keys;
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
      normalized.push({
        id: id,
        title: clean(titleNode.textContent),
        summary: clean(descriptionNode ? descriptionNode.textContent : ""),
        start: start.value,
        end: end.value,
        allDay: start.allDay,
        timezone: EASTERN,
        category: calendarText(item, "calendar") || "HWS event",
        location: place && room && place !== room ? place + ", " + room : (place || room),
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
    return normalized.sort(eventSort);
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

  function textElement(tag, className, value) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = value;
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

  function eventSort(a, b) {
    return a.start.localeCompare(b.start) || a.title.localeCompare(b.title);
  }

  function filteredEvents() {
    return state.events.filter(function (event) {
      var haystack = [event.title, event.summary, event.location, event.organizer].join(" ").toLowerCase();
      return (!state.category || event.category === state.category) &&
        (!state.query || haystack.indexOf(state.query) !== -1);
    });
  }

  function groupEvents(events) {
    var groups = {};
    events.forEach(function (event) {
      eventDayKeys(event).forEach(function (key) {
        if (!groups[key]) groups[key] = [];
        groups[key].push(event);
      });
    });
    Object.keys(groups).forEach(function (key) { groups[key].sort(eventSort); });
    return groups;
  }

  function monthName(monthKey) {
    return new Intl.DateTimeFormat("en-US", { month: "long", year: "numeric", timeZone: "UTC" })
      .format(dayKeyDate(monthKey + "-01"));
  }

  function dayHeading(dayKey) {
    return new Intl.DateTimeFormat("en-US", {
      weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC"
    }).format(dayKeyDate(dayKey));
  }

  function timeLabel(event) {
    if (event.allDay) return "All day";
    return new Intl.DateTimeFormat("en-US", {
      timeZone: EASTERN, hour: "numeric", minute: "2-digit"
    }).format(new Date(event.start));
  }

  function displayRange(event) {
    if (event.allDay) {
      var startLabel = new Intl.DateTimeFormat("en-US", {
        weekday: "long", month: "long", day: "numeric", year: "numeric", timeZone: "UTC"
      }).format(dayKeyDate(event.start));
      if (event.end === event.start) return startLabel + " · All day";
      var endLabel = new Intl.DateTimeFormat("en-US", {
        month: "long", day: "numeric", year: "numeric", timeZone: "UTC"
      }).format(dayKeyDate(event.end));
      return startLabel + "–" + endLabel + " · All day";
    }
    var start = new Intl.DateTimeFormat("en-US", {
      timeZone: EASTERN, weekday: "long", month: "long", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit"
    }).format(new Date(event.start));
    var end = new Intl.DateTimeFormat("en-US", {
      timeZone: EASTERN, hour: "numeric", minute: "2-digit"
    }).format(new Date(event.end));
    return start + "–" + end;
  }

  function googleCalendarUrl(event) {
    function compact(value, allDay) {
      return allDay ? value.replace(/-/g, "") : new Date(value).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
    }
    if (!event.allDay && new Date(event.end) <= new Date(event.start)) return null;
    var calendarEnd = event.end;
    if (event.allDay) calendarEnd = addDayKey(event.end, 1);
    var url = new URL("https://calendar.google.com/calendar/render");
    url.searchParams.set("action", "TEMPLATE");
    url.searchParams.set("text", event.title);
    url.searchParams.set("dates", compact(event.start, event.allDay) + "/" + compact(calendarEnd, event.allDay));
    url.searchParams.set("details", event.sourceUrl);
    if (event.location) url.searchParams.set("location", event.location);
    return url.href;
  }

  function eventButton(event, className, dayKey) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.setAttribute("data-event-id", event.id);
    if (dayKey) button.setAttribute("data-day-key", dayKey);
    button.setAttribute("aria-label", event.title + ", " + displayRange(event));
    button.appendChild(textElement("span", "calendar-event-time", timeLabel(event)));
    button.appendChild(textElement("span", "calendar-event-title", event.title));
    return button;
  }

  function emptyState(filteredCount) {
    var wrapper = document.createElement("div");
    wrapper.className = "calendar-empty";
    var hasFilters = Boolean(state.query || state.category);
    wrapper.appendChild(textElement("p", "", hasFilters ?
      "No events match those filters in this month." : "No HWS events are listed for this month yet."));
    if (hasFilters) {
      var clear = textElement("button", "calendar-clear-filters", "Clear filters");
      clear.type = "button";
      clear.addEventListener("click", function () {
        state.query = "";
        state.category = "";
        eventSearch.value = "";
        eventCategory.value = "";
        render();
      });
      wrapper.appendChild(clear);
    }
    wrapper.setAttribute("data-filtered-count", String(filteredCount));
    return wrapper;
  }

  function renderMonthGrid(groups, monthEvents) {
    calendarGrid.replaceChildren();
    WEEKDAYS.forEach(function (weekday) {
      calendarGrid.appendChild(textElement("div", "calendar-weekday", weekday.slice(0, 3)));
    });
    mondayFirstMonthMatrix(state.activeMonth).forEach(function (dayKey) {
      var cell = document.createElement("div");
      cell.className = "calendar-day" + (dayKey.slice(0, 7) === state.activeMonth ? "" : " is-outside-month");
      cell.setAttribute("role", "gridcell");
      cell.setAttribute("aria-label", dayHeading(dayKey));
      cell.appendChild(textElement("span", "calendar-day-number", String(Number(dayKey.slice(8)))));
      var dayEvents = groups[dayKey] || [];
      dayEvents.slice(0, 3).forEach(function (event) {
        cell.appendChild(eventButton(event, "calendar-event-pill", dayKey));
      });
      if (dayEvents.length > 3) {
        var more = textElement("button", "calendar-more", "+ " + (dayEvents.length - 3) + " more");
        more.type = "button";
        more.setAttribute("data-day-key", dayKey);
        more.setAttribute("aria-label", "Show all " + dayEvents.length + " events on " + dayHeading(dayKey));
        cell.appendChild(more);
      }
      calendarGrid.appendChild(cell);
    });
    if (!monthEvents.length) calendarGrid.appendChild(emptyState(0));
  }

  function renderMobileAgenda(groups, monthEvents) {
    mobileAgenda.replaceChildren();
    if (!monthEvents.length) {
      mobileAgenda.appendChild(emptyState(0));
      return;
    }
    Object.keys(groups).filter(function (key) { return key.slice(0, 7) === state.activeMonth; })
      .sort().forEach(function (dayKey) {
        var section = document.createElement("section");
        section.className = "agenda-day";
        section.appendChild(textElement("h3", "agenda-day-heading", dayHeading(dayKey)));
        groups[dayKey].forEach(function (event) {
          var button = eventButton(event, "agenda-event", dayKey);
          if (event.location) button.appendChild(textElement("span", "agenda-event-location", event.location));
          section.appendChild(button);
        });
        mobileAgenda.appendChild(section);
      });
  }

  function render() {
    if (!state.events.length) return;
    var filtered = filteredEvents();
    var groups = groupEvents(filtered);
    var monthEvents = filtered.filter(function (event) {
      return eventDayKeys(event).some(function (key) { return key.slice(0, 7) === state.activeMonth; });
    });
    monthLabel.textContent = monthName(state.activeMonth);
    renderMonthGrid(groups, monthEvents);
    renderMobileAgenda(groups, monthEvents);
    eventStatus.textContent = monthEvents.length + " event" + (monthEvents.length === 1 ? "" : "s") +
      " in " + monthName(state.activeMonth) + (state.query || state.category ? " match your filters." : ".");
  }

  function setEvents(candidate) {
    if (!validate(candidate)) return false;
    state.events = candidate.slice().sort(eventSort);
    render();
    hub.classList.add("calendar-enhanced");
    return true;
  }

  function eventById(id) {
    return state.events.find(function (event) { return event.id === id; });
  }

  function dialogFocusable() {
    return Array.prototype.slice.call(dialog.querySelectorAll(
      'button:not([hidden]):not([disabled]), a[href]:not([hidden]), [tabindex]:not([tabindex="-1"]):not([hidden])'
    )).filter(function (node) { return node.offsetParent !== null; });
  }

  function trapFallbackFocus(event) {
    if (!usingFallbackDialog) return;
    if (event.key === "Escape") {
      event.preventDefault();
      closeEventDialog();
      return;
    }
    if (event.key !== "Tab") return;
    var focusable = dialogFocusable();
    if (!focusable.length) return;
    var first = focusable[0];
    var last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function showEventDialog(opener) {
    dialogOpener = opener || document.activeElement;
    dialog.hidden = false;
    document.body.classList.add("dialog-open");
    usingFallbackDialog = typeof dialog.showModal !== "function";
    if (usingFallbackDialog) {
      dialog.setAttribute("open", "");
      dialog.setAttribute("role", "dialog");
      dialog.setAttribute("aria-modal", "true");
      dialog.classList.add("event-dialog-fallback");
      document.addEventListener("keydown", trapFallbackFocus);
    } else if (!dialog.open) {
      dialog.showModal();
    }
    window.requestAnimationFrame(function () { dialogClose.focus(); });
  }

  function finishDialogClose() {
    dialog.hidden = true;
    dialog.removeAttribute("open");
    dialog.classList.remove("event-dialog-fallback");
    if (usingFallbackDialog) {
      dialog.removeAttribute("role");
      dialog.removeAttribute("aria-modal");
      document.removeEventListener("keydown", trapFallbackFocus);
    }
    usingFallbackDialog = false;
    document.body.classList.remove("dialog-open");
    state.selectedDay = null;
    state.selectedEventId = null;
    if (dialogOpener && typeof dialogOpener.focus === "function") dialogOpener.focus();
    dialogOpener = null;
  }

  function closeEventDialog() {
    if (!usingFallbackDialog && dialog.open && typeof dialog.close === "function") dialog.close();
    else finishDialogClose();
  }

  function resetDialogContent() {
    dialogCategory.textContent = "";
    dialogTitle.textContent = "";
    dialogDate.textContent = "";
    dialogDescription.textContent = "";
    dialogLocation.textContent = "";
    dialogOrganizer.textContent = "";
    dialogLocationRow.hidden = true;
    dialogOrganizerRow.hidden = true;
    dialogDayList.hidden = true;
    dialogDayList.replaceChildren();
    dialogLinks.replaceChildren();
  }

  function populateEventDialog(event) {
    resetDialogContent();
    state.selectedEventId = event.id;
    dialogCategory.textContent = event.category;
    dialogTitle.textContent = event.title;
    dialogDate.textContent = displayRange(event);
    dialogDescription.textContent = event.summary || "No description was supplied by HWS.";
    if (event.location) {
      dialogLocation.textContent = event.location;
      dialogLocationRow.hidden = false;
    }
    if (event.organizer) {
      dialogOrganizer.textContent = event.organizer;
      dialogOrganizerRow.hidden = false;
    }
    dialogLinks.appendChild(sourceLink(event.sourceUrl, "Official details", "event"));
    if (event.ticketUrl) dialogLinks.appendChild(sourceLink(event.ticketUrl, "Register or get tickets", "ticket"));
    var calendarUrl = googleCalendarUrl(event);
    if (calendarUrl) dialogLinks.appendChild(sourceLink(calendarUrl, "Add to calendar", "calendar"));
    dialogBack.hidden = !dialogReturnDay;
  }

  function openEventDialog(id, opener, returnDay) {
    var event = eventById(id);
    if (!event) return;
    dialogReturnDay = returnDay || null;
    populateEventDialog(event);
    track("campus_event_expand", { event_id: event.id, active_month: state.activeMonth });
    if (dialog.hidden || !dialog.open) showEventDialog(opener);
    else dialogClose.focus();
  }

  function populateDayDialog(dayKey) {
    resetDialogContent();
    state.selectedDay = dayKey;
    state.selectedEventId = null;
    dialogReturnDay = null;
    dialogBack.hidden = true;
    dialogCategory.textContent = "HWS events";
    dialogTitle.textContent = dayHeading(dayKey);
    var dayEvents = groupEvents(filteredEvents())[dayKey] || [];
    dialogDate.textContent = dayEvents.length + " event" + (dayEvents.length === 1 ? "" : "s");
    dialogDayList.hidden = false;
    dayEvents.forEach(function (event) {
      var button = eventButton(event, "event-dialog-day-event", dayKey);
      if (event.location) button.appendChild(textElement("span", "agenda-event-location", event.location));
      dialogDayList.appendChild(button);
    });
  }

  function openDayDialog(dayKey, opener) {
    populateDayDialog(dayKey);
    showEventDialog(opener);
  }

  function eventActivation(event) {
    var button = event.target.closest && event.target.closest("[data-event-id], .calendar-more");
    if (!button) return;
    if (button.hasAttribute("data-event-id")) {
      openEventDialog(button.getAttribute("data-event-id"), button, button.getAttribute("data-day-key"));
    } else {
      openDayDialog(button.getAttribute("data-day-key"), button);
    }
  }
  calendarGrid.addEventListener("click", eventActivation);
  mobileAgenda.addEventListener("click", eventActivation);
  dialogDayList.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-event-id]");
    if (button) openEventDialog(button.getAttribute("data-event-id"), dialogOpener, button.getAttribute("data-day-key"));
  });

  dialogBack.addEventListener("click", function () {
    if (dialogReturnDay) {
      var day = dialogReturnDay;
      populateDayDialog(day);
      dialogClose.focus();
    }
  });
  dialogClose.addEventListener("click", closeEventDialog);
  dialog.addEventListener("cancel", function (event) {
    event.preventDefault();
    closeEventDialog();
  });
  dialog.addEventListener("close", finishDialogClose);
  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) closeEventDialog();
  });

  function filterChanged(control, type) {
    control.addEventListener(type, function () {
      state.query = clean(eventSearch.value).toLowerCase();
      state.category = eventCategory.value;
      render();
      track("campus_event_filter", {
        filter_type: control.id,
        query_present: Boolean(state.query),
        category: state.category || "all",
        active_month: state.activeMonth
      });
    });
  }
  filterChanged(eventSearch, "input");
  filterChanged(eventCategory, "change");

  function navigateMonth(amount, type) {
    state.activeMonth = amount === 0 ? easternMonthKey(new Date()) : shiftMonth(state.activeMonth, amount);
    render();
    track("campus_event_filter", {
      filter_type: "month_navigation",
      navigation_type: type,
      active_month: state.activeMonth
    });
  }
  previousMonth.addEventListener("click", function () { navigateMonth(-1, "previous"); });
  todayButton.addEventListener("click", function () { navigateMonth(0, "today"); });
  nextMonth.addEventListener("click", function () { navigateMonth(1, "next"); });

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
    .catch(function () { /* Keep the server-rendered fallback until validated data is accepted. */ })
    .then(fetchLive);
}());
