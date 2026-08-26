# Analytics (GA4)

GA4 is wired in via `gtag.js` directly — no Google Tag Manager, no consent management
platform. That's a deliberate fit for what this site is: a static, no-backend club site
with no user accounts, no checkout, and (currently) no EU-targeted campaigns requiring
Consent Mode. See [CLAUDE.md](../CLAUDE.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for how
the generator works in general; this doc covers only the analytics layer.

## Where it lives in code

- **`GA_MEASUREMENT_ID`** and **`GA_SNIPPET`** — constants near the top of
  `scripts/build_site.py`, right after `BASE_URL`. `GA_SNIPPET` is the literal `gtag.js`
  loader plus a `content_group` classifier computed from `location.pathname`
  (`home` / `majors_index` / `major_page` / `tasks_index` / `task_page` / `events` /
  `academic_calendar` / `ai_resources` / `faq` / `ai_policy` / `founder_page` / `other`).
- **`head()`** (`scripts/build_site.py`) — injects `{GA_SNIPPET}` immediately after the
  `<head>` tag, before every other tag, on every page. This is the single point of control:
  change the measurement ID or the snippet once here, rebuild, and it's live on every
  generated page.
- **`site/js/site.js`** — fires the custom events below via a small `track()` wrapper
  (`if (typeof window.gtag === "function") …`), so a blocked or missing `gtag.js` (ad
  blockers, privacy browsers) never breaks the feature it's attached to. The site's actual
  functionality — copying a prompt, following a link — never depends on analytics succeeding.

`site/js/campus-hub.js` progressively refreshes `/events/` from the documented HWS
calendar feed and tracks campus-hub filters, month navigation, event-dialog opens, official-source exits, and
permission-approved club searches. The static snapshot remains usable when analytics or
the live feed is blocked.

To change the measurement ID: edit `GA_MEASUREMENT_ID` in `scripts/build_site.py`, then
`python3 scripts/build_site.py`.

## Event taxonomy

Beyond GA4's automatic `page_view` (and Enhanced Measurement's automatic `scroll` /
`click` (outbound) / `file_download`, which should be left on in the GA4 UI — see
[Automatic events](#automatic-events-check-these-in-the-ga4-ui) below), thirteen custom events
cover the actions that actually matter for a club recruiting site: did someone get real
value from the use-case library, did they take a step toward joining, and — per founder,
individually — did their page get looked at, clicked into, and actually engaged with.

| Event | Fired when | Key params | Type |
| --- | --- | --- | --- |
| `prompt_copied` | Clicking "Copy" on any use case's starter prompt | `major`, `use_case_number`, `difficulty` | **Conversion** — this is the site's core "aha" moment |
| `tutorial_video_click` | Clicking a use case's "Watch" link | `major`, `use_case_number`, `difficulty`, `video_title`, `link_url` | Engagement |
| `join_cta_click` | Clicking any "Join the Club" / "Get Started Today" / nav "Join Us" button (all link to the in-page `#join` section) | `location` (`hero-join` \| `no-experience-join` \| `nav-join` \| `join-section-majors`) | Micro-conversion / intent |
| `library_cta_click` | Clicking "Browse Use Cases" / "Find your major" (entry points into `/majors/`) | `location` (`hero-browse` \| `library-browse`) | Micro-conversion |
| `join_community_click` | Clicking "Join the Skool community" — the actual outbound signup | `link_url`, `location: "skool-join"` | **Conversion** — the real signup action |
| `founder_card_click` | Clicking a founder card on the homepage, or the "next founder" pager on a founder page | `founder` (slug), `location` (`founder-card` \| `founder-pager`) | Engagement — see [Founder pages](#founder-pages) below |
| `founder_link_click` | Clicking one of a founder's outbound links (LinkedIn, Licom AI, Sundai, school) | `founder` (slug), `link_label`, `link_url` | Engagement |
| `song_played` | Pressing play on a founder's "remembered by" Spotify embed | `founder` (slug), `song_title`, `song_artist` | Engagement |
| `song_completed` | Listening to ≥90% of that song (mirrors the site's scroll-depth threshold) | `founder` (slug), `song_title`, `song_artist` | Engagement |
| `campus_event_filter` | Changing an event keyword/category filter or navigating calendar months | `filter_type`, `query_present`, `category`, `active_month`; month navigation also includes `navigation_type` | Hub engagement |
| `campus_event_expand` | Opening an imported HWS event in the reusable details dialog | `event_id`, `active_month` | Event-interest signal |
| `campus_official_source_click` | Following an official event, registration, calendar, or club-directory link | `source_type`, `link_url` | Source exit / assisted journey |
| `campus_club_search` | Searching or filtering the approved club directory | `query_present`, `category`, `results` | Club-discovery engagement |

### Founder pages

Every interaction on a founder page is tracked individually, with a `founder` param
(`dominic-schimizzi` \| `zackary-hanna`) on every custom event, so Zack's and Dom's pages
can be filtered and compared separately in GA4 — not just lumped into one "founder page"
bucket:

- **`page_view`** (automatic), tagged `content_group: "founder_page"` — raw visits, any
  entry point (homepage card, direct link, search).
- **`founder_card_click`** — the click that *leads there*: the homepage "Meet the Founders"
  card, or the "next founder" pager at the bottom of a founder page. Distinguishes "the
  card got clicked" from someone landing on the page directly.
- **`founder_link_click`** — each outbound link on the page (LinkedIn, Licom AI, Sundai,
  school), with which link specifically (`link_label`). Layered on top of, not a duplicate
  of, Enhanced Measurement's generic outbound-click event — that one only tells you *a*
  link left the site; this tells you *which* founder and *which* link.
- **`song_played`** / **`song_completed`** — real Spotify playback state, not a click
  guess: the embed is cross-origin, so a plain click listener on the page can't see inside
  it. `site.js` instead loads Spotify's own iFrame API (`open.spotify.com/embed/iframe-api/v1`)
  and listens to its `playback_update` events, firing `song_played` on the first
  paused→playing transition and `song_completed` once position/duration crosses 90%. If
  Spotify's API is blocked or its shape changes, the code fails silently (wrapped in
  try/catch) — the embed itself still works, tracking just no-ops.

The CTA events are generic, attribute-driven, and extensible: any element with `data-cta="..."`
is picked up automatically by the delegated click handler in `site.js` — adding a new CTA
never requires a JS change, only the attribute on the new element (see `uc_card()`,
`site_header()`, `founder_cards()`, and `build_founder()` in `scripts/build_site.py` for
the existing `data-cta` values).

Naming follows `object_action` snake_case, matching standard GA4/GTM convention, so these
read naturally next to GA4's own automatic events (`page_view`, `scroll`, `click`).

## Configure in the GA4 UI (not in code)

These can't be set from the repo — they're GA4 property settings, done once at
analytics.google.com for property `G-0S5QWRS2Q6`:

1. **Register custom dimensions** (Admin → Custom definitions → Create custom dimension) —
   **do this first**, or the per-founder (and per-major, per-video) breakdowns won't show up
   anywhere in Reports/Explore. GA4 captures event params automatically, but only exposes
   them in the UI once registered. Register at minimum: `founder`, `major`,
   `use_case_number`, `difficulty`, `video_title`, `link_label`, `song_title`, `location`
   — event-scoped, matching the parameter name exactly (case-sensitive). This is what lets
   you build a report or Exploration and split any of these events by `founder` to compare
   Zack's page against Dom's.
2. **Mark conversions** (Admin → Events → toggle "Mark as conversion"):
   `prompt_copied` and `join_community_click`. Don't mark the other seven engagement/intent
   events as conversions — GA4 caps conversions at 30 per property, and diluting the
   conversion list with micro-signals makes Google Ads/Analytics optimization worse, not better.
3. **Confirm Enhanced Measurement** is on (Admin → Data Streams → your stream → Enhanced
   measurement): page views, scrolls, and outbound clicks should be enabled. Outbound click
   tracking is what covers the HWS program-page links and any other external link *not*
   already captured by one of the custom events above — leave it on rather than
   building another custom event to duplicate it.
4. **Internal traffic filter**, once the club has regular contributors testing the site, so
   dev/maintainer visits don't skew the (currently small) traffic numbers: Admin → Data
   Filters → Internal Traffic.

### Automatic events (check these in the GA4 UI)
`page_view`, `scroll` (90% depth), `click` (outbound — any link to a different domain,
including YouTube tutorial links, the HWS program-page links, and the Skool link before it's
even clicked-tracked by `join_community_click`), and `file_download`. These require no code
here; they come from Enhanced Measurement being enabled on the data stream.

## What was deliberately left out, and why

- **No Google Tag Manager.** This is a hand-written static site with one script file and no
  marketing team iterating on tags independently of a deploy — a GTM container would add a
  layer of indirection with no one to benefit from it. If that changes (e.g. a marketer
  needs to add pixels without a code change), migrate the `data-cta` pattern into GTM
  triggers directly; the attributes already do the hard part.
- **No Consent Mode / CMP.** This is a US college club with no EU ad campaigns or
  GDPR-scoped audience today. If the club ever runs EU-facing campaigns or a CMP becomes a
  requirement, that's an explicit follow-up — don't default consent to "denied" without a
  real consent banner, since that would silently zero out all analytics.
- **No `user_id`.** There are no accounts on this site — nothing to key a `user_id` to.
- **No majors-library search/filter tracking.** Those controls still fire on every
  keystroke/click without a defined decision. Campus-hub filters are tracked because the
  approved measurement plan explicitly uses them to measure event and organization demand.

## Campus-hub measurement definitions

- **Hub impressions:** GA4 `page_view` events where `content_group = events`.
- **Organic entrances:** hub impressions whose session default channel group is Organic
  Search and whose landing page is `/events/`.
- **Filter usage:** sessions with at least one `campus_event_filter` or
  `campus_club_search`; use sessions, not raw keystrokes, for the headline rate.
- **Event expansion rate:** sessions that open at least one event-detail dialog (`campus_event_expand`) divided by hub sessions.
- **Official-source exit rate:** hub sessions with `campus_official_source_click` divided by
  hub sessions; break down by `source_type` rather than treating every exit as equivalent.
- **Assisted Skool conversion:** sessions with a campus-hub engagement event followed by
  `join_community_click` in the same session. GA4 measures the click-through, not completed
  Skool membership; actual membership requires a separate Skool-side count.

Review these monthly alongside snapshot age and sync failures. Do not report membership,
event attendance, or club interest from proxy events as if they were confirmed outcomes.
