# HWS Events Calendar-First Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/events/` card wall with a calendar-first monthly event browser, responsive mobile agenda, and accessible event-detail dialog while preserving the validated HWS data pipeline and no-JavaScript fallback.

**Architecture:** `scripts/build_site.py` will generate the calendar shell, semantic controls, first-24-event fallback agenda, and reusable dialog. `site/js/campus-hub.js` will retain source validation and live refresh while adding month/filter state plus isolated calendar, agenda, day-overflow, and dialog renderers. `site/css/styles.css` will implement the selected calendar-first visual direction and responsive breakpoint without adding dependencies.

**Tech Stack:** Python 3 static generator, vanilla HTML/CSS/JavaScript, Python `unittest`, Node syntax checking, no npm packages.

---

## File structure

- Modify `tests/test_hws_campus_content.py`: generated hierarchy, calendar controls,
  fallback agenda, dialog, schema, and runtime-safety regressions.
- Modify `scripts/build_site.py`: page order and generated calendar/dialog/fallback markup.
- Modify `site/js/campus-hub.js`: current-month state, Eastern date helpers, renderers,
  dialog focus behavior, filtering, analytics, and existing live refresh integration.
- Modify `site/css/styles.css`: calendar header, month grid, pills, mobile agenda, dialog,
  empty state, focus, and reduced-motion styles.
- Modify `docs/ANALYTICS.md`: month-navigation parameter and modal-open wording.
- Modify `docs/ARCHITECTURE.md`: calendar-first progressive-enhancement behavior.
- Regenerate `site/events/index.html` and `site/data/lastmod.json` only through
  `python scripts/build_site.py`.

### Task 1: Lock the generated calendar contract with failing tests

**Files:**
- Modify: `tests/test_hws_campus_content.py`
- Test: `tests/test_hws_campus_content.py`

- [ ] **Step 1: Add section-order and structure assertions**

Add tests that require:

```python
calendar_pos = self.page.index('id="upcoming-hws-events"')
club_meeting_pos = self.page.index('id="ai-club-meeting"')
self.assertLess(calendar_pos, club_meeting_pos)
for expected in (
    'id="events-calendar"',
    'id="calendar-prev"',
    'id="calendar-today"',
    'id="calendar-next"',
    'id="calendar-month-label"',
    'id="calendar-grid"',
    'id="events-mobile-agenda"',
    'id="event-dialog"',
    'id="event-dialog-close"',
    'class="event-fallback-agenda"',
):
    self.assertIn(expected, self.page)
self.assertNotIn('id="event-date"', self.page)
self.assertNotIn('id="events-load-more"', self.page)
```

- [ ] **Step 2: Add fallback and safety assertions**

Require exactly 24 server-rendered fallback records, one controlled Event JSON-LD node,
no imported Event schema, no `.innerHTML`, and runtime references to `showModal`, Escape,
focus restoration, month navigation analytics, and mobile agenda rendering.

- [ ] **Step 3: Run the focused tests and confirm RED**

Run:

```bash
python -m unittest tests.test_hws_campus_content.GeneratedCampusHubTests
```

Expected: failures for missing calendar controls/dialog and incorrect section order.

- [ ] **Step 4: Commit the failing tests**

```bash
git add tests/test_hws_campus_content.py
git commit -m "test: define calendar-first events contract"
```

### Task 2: Generate the calendar-first page shell

**Files:**
- Modify: `scripts/build_site.py`
- Test: `tests/test_hws_campus_content.py`
- Regenerate: `site/events/index.html`
- Regenerate: `site/data/lastmod.json`

- [ ] **Step 1: Replace card fallback helper with compact agenda rows**

Keep the existing escaped event data and official links, but generate compact
`article.event-fallback-item` rows inside `.event-fallback-agenda`. Every row keeps
`data-campus-event-id`, `<time datetime>`, title, category, time, location, organizer,
description disclosure, official source, ticket, and valid calendar link.

- [ ] **Step 2: Reorder `build_events_page()`**

Generate this order:

```html
<header class="events-hero">...</header>
<section id="upcoming-hws-events" class="calendar-shell">...</section>
<section class="campus-club-meeting" aria-labelledby="ai-club-meeting">...</section>
<section aria-labelledby="hws-clubs-directory">...</section>
<aside class="campus-source-notice">...</aside>
```

- [ ] **Step 3: Generate the calendar controls and containers**

The calendar section must contain:

```html
<input id="event-search" type="search">
<select id="event-category">...</select>
<button id="calendar-prev" type="button" aria-label="Previous month">...</button>
<button id="calendar-today" type="button">Today</button>
<button id="calendar-next" type="button" aria-label="Next month">...</button>
<h3 id="calendar-month-label" aria-live="polite"></h3>
<div id="calendar-grid" role="grid" aria-labelledby="calendar-month-label"></div>
<div id="events-mobile-agenda" class="events-mobile-agenda"></div>
<div class="event-fallback-agenda">...24 rows...</div>
```

- [ ] **Step 4: Generate one reusable event dialog**

Add a `<dialog id="event-dialog" aria-labelledby="event-dialog-title">` with stable
children for back, close, category, title, date, location, organizer, description, and
links. It starts empty and hidden until JavaScript populates it.

- [ ] **Step 5: Build and confirm the focused tests move toward GREEN**

```bash
python scripts/build_site.py
python -m unittest tests.test_hws_campus_content.GeneratedCampusHubTests
```

Expected: generated-structure tests pass; runtime behavior assertions may still fail.

- [ ] **Step 6: Commit generator and generated artifacts**

```bash
git add scripts/build_site.py site/events/index.html site/data/lastmod.json
git commit -m "feat: generate calendar-first events shell"
```

### Task 3: Implement month, filter, and dialog behavior

**Files:**
- Modify: `site/js/campus-hub.js`
- Test: `tests/test_hws_campus_content.py`

- [ ] **Step 1: Preserve validation/live-refresh functions and replace list rendering state**

Use one state object:

```javascript
var state = {
  events: [],
  activeMonth: easternMonthKey(new Date()),
  query: "",
  category: "",
  selectedDay: null,
  selectedEventId: null
};
```

Keep RSS parsing, URL allowlisting, snapshot validation, 15-minute `sessionStorage`, and
five-second abort behavior unchanged. Do not hide or replace `.event-fallback-agenda`
merely because JavaScript initialized. Add the enhanced-state class and hide the fallback
only after `setEvents(candidate)` accepts a complete local or live dataset; if both data
requests fail, the server-rendered agenda remains visible.

- [ ] **Step 2: Add pure Eastern date helpers**

Implement helpers for `YYYY-MM`, Monday-first month matrices, inclusive all-day expansion,
exclusive timed-end placement, and grouping filtered events by Eastern calendar day.

- [ ] **Step 3: Render the desktop month grid without source HTML injection**

Use `document.createElement`, `textContent`, and native buttons. Render seven weekday
headers, 35 or 42 day cells, up to three event pills per day, and `+ N more` buttons.
Adjacent-month cells are marked with `.is-outside-month`.

- [ ] **Step 4: Render the mobile day-grouped agenda**

Build date sections containing compact event buttons with title, time, and location. CSS
controls which renderer is visible; JavaScript keeps both synchronized from the same
filtered state.

- [ ] **Step 5: Implement the reusable dialog modes**

`openEventDialog(id, opener)` populates event detail fields and calls `showModal()` when
available. `openDayDialog(day, opener)` lists every event for that day inside the same
dialog. Selecting one switches the dialog to event mode; Back returns to day mode.

When native `showModal()` is unavailable, remove `hidden`, add `role="dialog"` and
`aria-modal="true"`, move focus to the close button or dialog heading, and install a Tab /
Shift+Tab focus loop over the dialog's current focusable controls. In both native and
fallback modes, close on the close button, Escape/cancel, or backdrop click; remove the
fallback ARIA/keyboard state, restore focus to the opener, and toggle a body scroll-lock
class only while the dialog is open.

- [ ] **Step 6: Wire search, category, and month navigation**

Search and category changes rerender both views. Previous/next move one month across year
boundaries. Today resets to the current Eastern month. Track filter use with:

```javascript
track("campus_event_filter", {
  filter_type: "month_navigation",
  active_month: state.activeMonth
});
```

Track every event-detail open with the existing `campus_event_expand` event.

- [ ] **Step 7: Add no-results and clear-filter behavior**

Distinguish an empty month from filters that remove all events. Show a clear-filters
button only for the latter.

- [ ] **Step 8: Run tests and syntax checks**

```bash
node --check site/js/campus-hub.js
python -m unittest tests.test_hws_campus_content
```

Expected: PASS. The tests must also assert source contracts for Monday-first grid helpers,
year-boundary month navigation, inclusive all-day expansion, midnight-exclusive timed
ends, fallback focus trapping, and retaining the static agenda until validated data is
accepted.

- [ ] **Step 9: Commit runtime behavior**

```bash
git add site/js/campus-hub.js tests/test_hws_campus_content.py
git commit -m "feat: add responsive HWS events calendar interactions"
```

### Task 4: Apply the selected visual redesign

**Files:**
- Modify: `site/css/styles.css`
- Regenerate: `site/events/index.html`

- [ ] **Step 1: Replace card-wall styles with the calendar visual system**

Add styles for `.events-hero`, `.calendar-shell`, `.calendar-toolbar`, `.calendar-grid`,
`.calendar-day`, `.calendar-event-pill`, `.calendar-more`, and category accents. Use the
existing violet/slate tokens and preserve readable contrast.

- [ ] **Step 2: Style the dialog and focus states**

Add a constrained, scrollable dialog panel, fixed backdrop, sticky close affordance,
visible `:focus-visible` outlines, body scroll lock, and link/action hierarchy.

- [ ] **Step 3: Add responsive agenda behavior**

At `max-width: 720px`, hide the month grid and display `.events-mobile-agenda`; stack
filters and month controls without horizontal scrolling. At larger widths, hide the
mobile agenda and fallback agenda after JavaScript enhances the page.

- [ ] **Step 4: Add reduced-motion handling**

Ensure modal and month changes do not animate under `prefers-reduced-motion: reduce`.

- [ ] **Step 5: Rebuild and inspect the generated diff**

```bash
python scripts/build_site.py
git diff --check
git diff -- site/events/index.html site/data/lastmod.json site/css/styles.css
```

Expected: calendar-first event-page changes only.

- [ ] **Step 6: Commit the visual redesign**

```bash
git add site/css/styles.css site/events/index.html site/data/lastmod.json
git commit -m "style: redesign events page around monthly calendar"
```

### Task 5: Update documentation and verify the complete feature

**Files:**
- Modify: `docs/ANALYTICS.md`
- Modify: `docs/ARCHITECTURE.md`
- Test: `tests/test_seo_migration.py`
- Test: `tests/test_hws_campus_content.py`

- [ ] **Step 1: Update analytics and architecture documentation**

Document `active_month` on `campus_event_filter`, event-modal opens under
`campus_event_expand`, the desktop/month and mobile/agenda split, and the retained static
fallback/live-refresh order.

- [ ] **Step 2: Run the exact source and regression checks**

```bash
python scripts/sync_hws_content.py --check
python -m unittest tests.test_seo_migration tests.test_hws_campus_content
python scripts/build_site.py
node --check site/js/campus-hub.js
git diff --check
git diff -- site/
```

Expected: 22 or more tests pass, live sources validate, build succeeds, JS syntax passes,
and generated diff is limited to the intended event-page artifacts.

- [ ] **Step 3: Verify consecutive-build idempotency**

Hash `site/events/index.html` and `site/data/lastmod.json`, rebuild, and confirm the hashes
are unchanged.

- [ ] **Step 4: Run manual localhost acceptance**

On the existing localhost server, verify desktop month navigation, mobile agenda at a
narrow viewport, search/category filtering, busy-day overflow, modal close/Escape/focus
restoration, live-source failure fallback, and official-source links.

- [ ] **Step 5: Commit documentation and any final test adjustments**

```bash
git add docs/ANALYTICS.md docs/ARCHITECTURE.md tests/test_hws_campus_content.py
git commit -m "docs: describe calendar-first events experience"
```

- [ ] **Step 6: Merge the verified branch to local `main` and refresh localhost**

Fast-forward local `main`, rerun the complete test command on the merged tree, remove the
temporary worktree/branch, and confirm `http://127.0.0.1:8888/events/` returns HTTP 200.
