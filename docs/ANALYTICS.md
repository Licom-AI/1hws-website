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
  (`home` / `majors_index` / `major_page` / `founder_page` / `other`).
- **`head()`** (`scripts/build_site.py`) — injects `{GA_SNIPPET}` immediately after the
  `<head>` tag, before every other tag, on every page. This is the single point of control:
  change the measurement ID or the snippet once here, rebuild, and it's live on all 46 pages.
- **`site/js/site.js`** — fires the custom events below via a small `track()` wrapper
  (`if (typeof window.gtag === "function") …`), so a blocked or missing `gtag.js` (ad
  blockers, privacy browsers) never breaks the feature it's attached to. The site's actual
  functionality — copying a prompt, following a link — never depends on analytics succeeding.

To change the measurement ID: edit `GA_MEASUREMENT_ID` in `scripts/build_site.py`, then
`python3 scripts/build_site.py`.

## Event taxonomy

Beyond GA4's automatic `page_view` (and Enhanced Measurement's automatic `scroll` /
`click` (outbound) / `file_download`, which should be left on in the GA4 UI — see
[Automatic events](#automatic-events-check-these-in-the-ga4-ui) below), six custom events
cover the actions that actually matter for a club recruiting site: did someone get real
value from the use-case library, did they take a step toward joining, and did the founder
pages get looked at.

| Event | Fired when | Key params | Type |
| --- | --- | --- | --- |
| `prompt_copied` | Clicking "Copy" on any use case's starter prompt | `major`, `use_case_number`, `difficulty` | **Conversion** — this is the site's core "aha" moment |
| `tutorial_video_click` | Clicking a use case's "Watch" link | `major`, `use_case_number`, `difficulty`, `video_title`, `link_url` | Engagement |
| `join_cta_click` | Clicking any "Join the Club" / "Get Started Today" / nav "Join Us" button (all link to the in-page `#join` section) | `location` (`hero-join` \| `no-experience-join` \| `nav-join` \| `join-section-majors`) | Micro-conversion / intent |
| `library_cta_click` | Clicking "Browse Use Cases" / "Find your major" (entry points into `/majors/`) | `location` (`hero-browse` \| `library-browse`) | Micro-conversion |
| `join_community_click` | Clicking "Join the Skool community" — the actual outbound signup | `link_url`, `location: "skool-join"` | **Conversion** — the real signup action |
| `founder_card_click` | Clicking a founder card on the homepage, or the "next founder" pager on a founder page | `founder` (slug), `location` (`founder-card` \| `founder-pager`) | Engagement — see [Founder pages](#founder-pages) below |

### Founder pages

Two layers cover the founder pages (`/founders/dominic-schimizzi/`, `/founders/zackary-hanna/`):

- **`page_view`** (automatic) fires when either page loads, tagged `content_group:
  "founder_page"` — this answers "how many people viewed a founder page," from any entry
  point (homepage card, direct link, search).
- **`founder_card_click`** (custom) fires on the *click that leads there* — the founder
  card on the homepage's "Meet the Founders" section, and the "next founder" pager link at
  the bottom of a founder page. This answers "did the homepage cards actually get clicked,"
  which `page_view` alone can't distinguish from someone landing on the page directly.

The outbound links *on* a founder page (LinkedIn, Licom AI, Sundai, school site) aren't
separately custom-tracked — they're external links, so GA4 Enhanced Measurement's automatic
outbound-click tracking already covers them without any code here.

All six are generic, attribute-driven, and extensible: any element with `data-cta="..."`
on it is picked up automatically by the delegated click handler in `site.js` — adding a new
CTA never requires a JS change, only the attribute on the new element (see `uc_card()`,
`site_header()`, and `build_home()` in `scripts/build_site.py` for the existing
`data-cta` values).

Naming follows `object_action` snake_case, matching standard GA4/GTM convention, so these
read naturally next to GA4's own automatic events (`page_view`, `scroll`, `click`).

## Configure in the GA4 UI (not in code)

These can't be set from the repo — they're GA4 property settings, done once at
analytics.google.com for property `G-0S5QWRS2Q6`:

1. **Mark conversions** (Admin → Events → toggle "Mark as conversion"):
   `prompt_copied` and `join_community_click`. Don't mark the four intent/engagement events
   as conversions — GA4 caps conversions at 30 per property, and diluting the conversion
   list with micro-signals makes Google Ads/Analytics optimization worse, not better.
2. **Confirm Enhanced Measurement** is on (Admin → Data Streams → your stream → Enhanced
   measurement): page views, scrolls, and outbound clicks should be enabled. Outbound click
   tracking is what covers the HWS program-page links and any other external link *not*
   already captured by one of the six custom events above — leave it on rather than
   building a sixth custom event to duplicate it.
3. **Internal traffic filter**, once the club has regular contributors testing the site, so
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
- **No search/filter-interaction tracking** (the majors-index live search, the per-major
  difficulty filter). These fire on every keystroke/click with no natural conversion
  boundary; tracking them would add event volume without a decision they'd inform. Revisit
  only if a specific question comes up (e.g. "do people use the difficulty filter at all").
