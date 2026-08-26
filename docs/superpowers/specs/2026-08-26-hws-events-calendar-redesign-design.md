# HWS Events Calendar-First Redesign

**Date:** 2026-08-26
**Status:** Approved for implementation
**Route:** `/events/`

## Context

The current HWS campus hub presents upcoming events as a large two-column card list below
the HWS AI Club meeting promotion. The page contains accurate, validated event data and a
working live-refresh pipeline, but its hierarchy makes campus event discovery feel
secondary and forces students to scan many oversized cards.

The redesign makes campus events the primary experience and presents them as a familiar
monthly calendar. The user selected the calendar-first direction from three visual
alternatives and approved the interaction, architecture, accessibility, fallback, and
testing design.

## Goals

- Put upcoming HWS campus events at the top of the page.
- Default to a full current-month calendar with previous, Today, and next controls.
- Let students search and filter the calendar without leaving the page.
- Open an event in a focused detail modal instead of expanding a large card inline.
- Use a chronological, day-grouped agenda on phones rather than compressing the month grid.
- Preserve the validated static snapshot, live Modern Campus refresh, safe text insertion,
  official-source links, analytics, SEO controls, and club-directory permission gate.

## Non-goals

- No new backend, framework, npm dependency, or client-side build step.
- No separate thin pages for imported events.
- No Event JSON-LD for campus events the club does not control.
- No change to club-directory publication approval or HWS source ownership.
- No attempt to reproduce the official HWS calendar design or branding.

## Page hierarchy

The generated page order will be:

1. Breadcrumb, `HWS Campus Events and Clubs` title, and short direct-answer introduction.
2. Calendar-first `Upcoming HWS events` section.
3. HWS AI Club weekly meeting and Skool conversion card.
4. Permission-gated HWS clubs and organizations section.
5. Source, update, correction, and affiliation notice.

The calendar section begins with a compact dark-to-violet header containing the official
source label, section title, explanatory text, and live/snapshot freshness status. Search,
category, and month controls sit directly beneath that header.

## Desktop and tablet calendar

At widths of 721px and above, the main event browser is a seven-column month grid:

- Week begins Monday.
- The first row names Monday through Sunday.
- Leading and trailing cells from adjacent months remain visible but visually muted.
- The active month defaults to the current month in `America/New_York`.
- Previous, Today, and next buttons change the active month without changing pages.
- Each day cell shows the date number and up to three matching event buttons.
- A `+ N more` button appears when a day has additional matching events.
- Clicking an event opens that event's modal.
- Clicking `+ N more` opens the reusable dialog in day-agenda mode. Selecting an event
  switches that same dialog into event-detail mode; a Back control returns to the day list.
  The interface never nests dialogs.
- Multi-day and all-day events appear on each applicable calendar date but resolve to one
  canonical event object and one modal record.

Modern Campus all-day end dates are treated as inclusive because the source presents and
describes them that way. Timed event ends are treated as exclusive for calendar placement;
an event ending exactly at midnight does not appear again on the following date.

Event pills use a restrained category color palette. Color is decorative only: every pill
includes its event title, and the modal includes the textual category.

## Mobile agenda

Below 721px, the month grid is replaced with a chronological agenda grouped by day:

- The same month navigation, search, category filter, and event state remain active.
- Only days containing matching events are shown.
- Each group has a prominent date heading followed by compact event buttons.
- Buttons include title, time/all-day state, and location when available.
- Selecting an event opens the same modal used on larger screens.
- An empty month retains the header and controls and shows a helpful empty state.

This avoids horizontal scrolling and avoids shrinking seven columns into unreadable phone
cells.

## Event detail modal

The page contains one reusable native `<dialog>` element when supported, with a defensive
fallback to an ARIA dialog presentation for older browsers. Opening an event populates the
dialog with DOM APIs and `textContent`; external values never enter raw `innerHTML`.

The modal includes:

- Category
- Event title
- Eastern date and time or all-day range
- Location
- Organizer
- Plain-text description
- Official details link
- Registration or ticket link when available and allowlisted
- Add-to-calendar link when the event has a usable duration

Accessibility behavior:

- Every calendar event is a native button with an informative accessible name.
- Opening moves focus to the dialog heading or close button.
- Tab focus remains within the modal while open.
- Escape, backdrop click, and the close button dismiss the modal.
- Closing restores focus to the event button that opened it.
- Background scrolling is disabled while open.
- Reduced-motion users receive no modal or month-transition animation.

## Data and state

The existing data pipeline remains authoritative:

1. `scripts/sync_hws_content.py` writes the validated static snapshot.
2. `scripts/build_site.py` server-renders a no-JavaScript agenda containing the first 24
   upcoming events.
3. `site/js/campus-hub.js` loads the complete same-origin snapshot.
4. The script attempts the existing five-second live Modern Campus RSS refresh.
5. A live response replaces snapshot state only after complete validation.
6. Valid live data remains cached in `sessionStorage` for 15 minutes.

Browser state contains:

- `events`: the validated event array
- `activeMonth`: `YYYY-MM` in Eastern time
- `query`: normalized search text
- `category`: selected category or all
- `selectedDay`: the day-overflow context, when open
- `selectedEventId`: the event modal context, when open

Filtering is applied before month rendering. Search matches title, summary, location, and
organizer. Category matches the source category exactly. Month navigation replaces the old
rolling 7/30/60/90-day selector and load-more button.

## Rendering boundaries

`site/js/campus-hub.js` remains dependency-free but is reorganized into clear functions:

- Source normalization and validation
- Eastern date/month helpers
- Filtered event selection
- Month-grid construction
- Mobile-agenda construction
- Day-overflow rendering
- Modal population and focus management
- Analytics dispatch

All source-controlled HTML structure remains generated by `scripts/build_site.py`.
JavaScript progressively enhances that structure and may replace the fallback agenda only
after validated data is available.

## Failure and empty states

- Live request timeout, network failure, XML failure, or invalid response: retain the
  static/local snapshot and display its retrieval date.
- Local snapshot request failure: retain the server-rendered first 24 events.
- No events in the active month: keep the calendar shell and show `No HWS events found for
  this month.`
- No filter matches: show `No events match these filters.` with a clear-filters button.
- Missing description/location/organizer: omit the missing row rather than showing a fake
  value.
- Invalid or zero-duration event: omit add-to-calendar while retaining official details.

## HWS AI Club and clubs sections

The HWS AI Club weekly meeting card moves immediately below the calendar. It remains
visually distinct, includes the existing controlled Event JSON-LD, and retains the direct
Skool CTA.

The clubs section remains below the club meeting. When publication approval is false, it
continues to show the official directory link and permission notice rather than mirrored
records. No source or permission behavior changes in this redesign.

## SEO and analytics

- Keep the current self-canonical title, description, sitemap entry, and `llms.txt` entry.
- Keep exactly one Event JSON-LD object for the club-controlled weekly meeting.
- Do not add Event, FAQPage, or ItemList markup for imported calendar content.
- Preserve `campus_event_filter`, `campus_event_expand`,
  `campus_official_source_click`, and `join_community_click`.
- Record month navigation through `campus_event_filter` with
  `filter_type: "month_navigation"` and active month.
- Record event modal opens through `campus_event_expand`; the existing event-interest KPI
  definition remains valid.

## Files affected

- `scripts/build_site.py`: reorder page sections and generate the calendar shell,
  no-JavaScript agenda, modal, controls, and semantic labels.
- `site/js/campus-hub.js`: calendar state, month navigation, responsive rendering, day
  overflow, modal behavior, and revised analytics.
- `site/css/styles.css`: calendar-first visual system, event pills, responsive agenda,
  modal, focus states, empty states, and reduced motion.
- `tests/test_hws_campus_content.py`: generated structure, section order, modal/calendar
  controls, no-JavaScript fallback, source-safety, and schema assertions.
- `site/events/index.html`: regenerated artifact.
- `site/data/lastmod.json`: regenerated event-page content hash.

No generated file will be edited directly.

## Verification and acceptance

Automated verification:

```bash
python scripts/sync_hws_content.py --check
python -m unittest tests.test_seo_migration tests.test_hws_campus_content
python scripts/build_site.py
node --check site/js/campus-hub.js
git diff --check
git diff -- site/
```

Manual acceptance:

- Upcoming campus events are the first major section on `/events/`.
- Desktop/tablet opens on the current Eastern month with Monday-first columns.
- Previous, Today, and next controls work across year boundaries.
- Search and category filters update both desktop and mobile representations.
- Busy days show `+ N more` and expose all matching events.
- Clicking an event opens the correct modal and official links.
- Escape, close button, focus restoration, and keyboard traversal work.
- Mobile shows the day-grouped agenda with no horizontal calendar scrolling.
- JavaScript disabled leaves the first 24 server-rendered events usable.
- Live API unavailable leaves the snapshot and controls usable.
- HWS AI Club and clubs sections remain below the calendar.
- Imported campus events still produce no Event JSON-LD.
