# Architecture

How `scripts/build_site.py` and `scripts/extract_data.py` actually work, at a level below
what [CLAUDE.md](../CLAUDE.md) and the [README](../README.md) cover. Read those first for
the overall pipeline; this is the function-by-function map for when you need to change
generator behavior itself, not just its input data.

For data shapes (`data.json`, `videos-config.json`) and how to edit content without
touching the generator, see [CONTENT_GUIDE.md](CONTENT_GUIDE.md). For what the build emits
and how to verify it, see [DEPLOYMENT.md](DEPLOYMENT.md).

## The two scripts

**`scripts/extract_data.py`** — spreadsheet to JSON, nothing else. Reads
`AI_Use_Cases_by_Major_HWS.xlsx`, asserts its shape (`Majors Index` sheet + 42 major
sheets, each with the exact header `["#", "Use Case", "Difficulty", "Level", "Description",
"HWS Program Page"]` and exactly 20 rows), slugifies major names, and writes
`site/data.json` and `site/js/data.js` (the same object, wrapped as
`window.HWS_AI_DATA = …` for the browser). Run only when the source `.xlsx` changes.

**`scripts/build_site.py`** — everything else. Loads `site/data.json` and
`site/data/videos-config.json` at import time (module-level `DATA`, `VCONF`), then `main()`
calls each `build_*` function in sequence. It has no CLI flags and no partial-build mode —
it always regenerates everything.

## Page builders

| Function | Emits |
| --- | --- |
| `build_home()` | `site/index.html` — hero, team (`TEAM` constant), founders (`FOUNDERS` constant), FAQ, Organization/Event/WebSite JSON-LD |
| `build_majors_index()` | `site/majors/index.html` — searchable grid of all 42 majors |
| `build_major(m, prev_m, next_m)` | `site/majors/<slug>/index.html` — one page per major, prev/next links, use-case cards |
| `build_tasks_index()` / `build_task_hub()` | `site/tasks/index.html` and `site/tasks/<slug>/index.html` — task-first routes to the same major-specific use cases |
| `build_ai_resources_page()` / `build_faq_page()` / `build_ai_policy_page()` | `site/resources/ai-at-hws/`, `site/faq/`, and `site/ai-policy/` — cited HWS resources, visible Q&A, and coursework guidance |
| `build_founder(f, others)` | `site/founders/<slug>/index.html` — one page per entry in `FOUNDERS`, `Person` JSON-LD |

Shared page furniture — `head()` (meta/OG/canonical/JSON-LD injection, plus the GA4 tag —
see [ANALYTICS.md](ANALYTICS.md)), `site_header()`,
`site_footer()`, `scripts()`, `breadcrumb(items)` — is composed into each page rather than
templated from a shared file; there is no template engine, just Python f-strings building
HTML strings directly. `esc()` (`html.escape`) is used at every point user-sourced or
spreadsheet-sourced text is interpolated — preserve that when adding new interpolations.

## Use-case card logic (the part that spans files)

This is the piece [CLAUDE.md](../CLAUDE.md#architecture) calls out as non-obvious. For one
use case (`slug`, `uc`) on a major page, in call order:

1. **`classify(title, description)`** → task archetype string (e.g. `"summarize"`,
   `"code"`). Checks the title's first word against `videos-config.json`'s `leadVerb` dict
   first (cheap, exact), then falls through to `rules` — an ordered list of
   `[archetype, regex]` pairs matched against the lowercased title+description.
2. **`prompt_archetype(slug, uc)`** → same as `classify()`, *unless* `"<slug>/<number>"` is
   a key in `videos-config.json`'s `overrides`, in which case it derives the archetype from
   the *overridden video* instead (via `_ID_TO_ARCH` / `_EXTRA_ARCH`), so the prompt matches
   what the video actually teaches rather than what the title's keywords implied.
3. **`video_id(slug, uc)`** → the archetype (from `classify`, not `prompt_archetype`) looked
   up in `videos-config.json`'s `skill` map, unless `overrides` hand-routes this exact use
   case to a different video id.
4. **`starter_prompt(slug, uc)`** → `promptPatterns[prompt_archetype(...)]` combined with
   the use case's own title/description/major name into one paste-ready prompt string. No
   use case's prompt is hand-written; all 840 are composed.
5. **`card_text(slug, uc)`** → looks up the resolved video's id in `videoTeaches` to append
   "The linked tutorial covers …" to the card description, and pulls a takeaway line from
   the same entry (falling back to `NEXT_STEPS[difficulty]`).

Note steps 2 and 3 can diverge: `prompt_archetype` follows an override to its *implied*
archetype, while `video_id` follows the *same* override directly to its video id. They're
consistent by construction (the override's video belongs to the archetype `prompt_archetype`
derives), but if you add a new override, add it to `_ID_TO_ARCH`/`_EXTRA_ARCH` too or the
prompt will silently fall back to `general`.

## Non-page build artifacts

Each is its own `build_*` function, all called from `main()`:

- `build_robots()` — `robots.txt`, with explicit `Allow` rules for the `AI_BOTS` list
  (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, etc.) in addition to the wildcard rule.
- `build_llms_txt()` — `site/llms.txt`, the [llmstxt.org](https://llmstxt.org) convention: a
  plain-language, prose site map for AI agents/assistants, distinct from `sitemap.xml`
  (machine sitemap) and `robots.txt` (crawl rules) even though all three enumerate the same
  pages.
- `build_sitemap()` — `sitemap.xml` from the homepage, majors, task hubs, AI-resource
  hub, FAQ, AI-coursework guide, and founders.
- `build_headers()` — legacy Netlify `_headers`. Vercel is the production host and does
  not consume this file; use page-level directives or approved Vercel configuration there.
- `build_videos_js()` — `site/js/videos.js`, a runtime-readable projection of
  `videos-config.json` for any client-side use.
- `build_og_image()` / `build_favicons()` — raster assets; see
  [DEPLOYMENT.md](DEPLOYMENT.md#raster-asset-fallback-chain) for the tool fallback chain.
- `build_manifest()` — `site.webmanifest`.

## JSON-LD conventions

Every page injects only the schema.org data it can keep accurate via `head()`'s `jsonld`
param. Types in use: `EducationalOrganization` + a current `Event` + `WebSite` (home),
`BreadcrumbList` (inner pages), and `Person` (founder pages, with verified `worksFor` /
`memberOf` details from the `FOUNDERS` constant). Visible Q&A stays in HTML, and the build
does not emit FAQPage, SearchAction, ItemList, or VideoObject markup. Keep that minimal
policy unless a real supported consumer and maintained facts justify an addition.

## Client-side JS (`site/js/site.js`)

Hand-written, not regenerated. Four independent, defensively-scoped behaviors, each a no-op
if its expected DOM isn't present: hash-router backward-compat (old `#/major/<slug>` links
redirect to `/majors/<slug>/`), the majors-index live search filter, the per-major
difficulty filter, and the starter-prompt copy button (three-tier fallback: async clipboard
→ `execCommand("copy")` → leave text selected for manual copy). Also handles the
`#uc-<number>` deep-link flash-highlight on major pages. The site is fully usable with JS
disabled — everything here is enhancement, not a dependency.
