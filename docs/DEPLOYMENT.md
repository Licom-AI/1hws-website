# Deployment & Build Verification

What `scripts/build_site.py` emits beyond HTML pages, how Vercel serves it, and how to
confirm a change is correct before calling it done. See [ARCHITECTURE.md](ARCHITECTURE.md)
for what each builder function does internally, and [CONTENT_GUIDE.md](CONTENT_GUIDE.md)
for the data files that drive content.

## Vercel production and legacy Netlify redirects

Vercel serves the production site at `https://www.hwsaiclub.com/`. The generated HTML is
the deployable artifact; rebuild it locally and review the `site/` diff before deploying
through the configured Vercel project. The repository intentionally does not guess at a
Vercel CLI command, project identifier, or output-directory setting owned by that project.

The old `https://hws-ai-club.netlify.app` hostname remains active only for migration. Its
`netlify.toml` configuration publishes `site/` and permanently redirects each legacy path
to the equivalent preferred URL. Keep that redirect for at least one year. Do not use
Netlify as the primary production deployment.

Vercel does not consume Netlify's generated `site/_headers`; page-level meta directives
such as `showcase.html`'s `noindex` are the portable controls. Configure any Vercel-only
headers in the Vercel project or a deliberately approved `vercel.json`.

## What a full build writes

Running `python3 scripts/build_site.py` regenerates, in order (see `main()`):

- `site/index.html`, `site/majors/index.html`, `site/majors/<slug>/index.html` ×42,
  `site/tasks/index.html`, 15 task-hub pages, `site/faq/index.html`,
  `site/ai-policy/index.html`, `site/resources/ai-at-hws/index.html`, and
  `site/founders/<slug>/index.html` ×2
- `site/robots.txt` — includes explicit `Allow` rules for named AI bots (`AI_BOTS` in
  `build_site.py`: GPTBot, ClaudeBot, PerplexityBot, Google-Extended, Applebot-Extended,
  cohere-ai, CCBot, …) in addition to the general wildcard allow
- `site/llms.txt` — the [llmstxt.org](https://llmstxt.org) convention, a prose map of the
  site for AI agents that consult it directly (independent of `sitemap.xml`/`robots.txt`)
- `site/sitemap.xml` — every major + founder page, generated from `DATA["majors"]` and
  `FOUNDERS`
- `site/_headers` — legacy Netlify response headers; not consumed by Vercel
- `site/js/videos.js` — runtime projection of `videos-config.json`
- `site/og-image.png` (+ the `.svg` source), favicons, `site/site.webmanifest`

The function ends with its own assertions (42 major pages exist, both founder pages exist)
and prints a one-line summary of what was written, including which raster tools were used
for the OG image and favicons — read that summary; it's the build telling you whether it
degraded gracefully or ran with full fidelity.

## Raster asset fallback chain

`build_og_image()` and `build_favicons()` (via `_rasterize()`) need to turn the brand
SVG/gradient into PNGs, and try, in order:

1. **OG image**: `Pillow` only (`_og_png_pillow()`) — hand-draws the 1200×630 card,
   including a cross-platform TrueType font search (macOS/Windows/Linux paths). If no
   TrueType font is found anywhere, it raises rather than silently rendering with an
   illegible bitmap fallback font.
2. **Favicons**: external SVG rasterizers first — `cairosvg`, `rsvg-convert`, ImageMagick's
   `magick` or `convert`, whichever is first found on `PATH` — then `_icon_pillow()`, which
   redraws the same rounded gradient tile as `assets/favicon.svg` without needing an SVG
   library at all.

If nothing is available, the corresponding `build_*` function returns a `"failed (...)"`
status string instead of raising, and the overall build still completes — check the printed
summary to see whether that happened. Installing `Pillow` (`pip install Pillow`) covers
both paths without needing any system SVG tool.

## Verifying a change

Beyond the focused regression suite, verification is: rebuild, then read the diff.

```bash
python -m unittest tests.test_seo_migration
python3 scripts/build_site.py
git status --short
git diff --stat
```

The regression suite checks the preferred-domain source, legacy path-preserving redirect,
and minimal structured-data policy. The build assertions and generated-file review remain
the source of truth for the rest of the static site.

- **Content-only change** (edited `data.json`, `videos-config.json`, or a constant in
  `build_site.py`): expect a diff limited to the generated files that actually depend on
  what you changed — e.g. editing one use case's description should only touch that one
  major's page and the corresponding entry in `site/data/lastmod.json` / `sitemap.xml`.
- **No change at all**: re-running the build on an untouched repo must produce **zero
  diff**. If it doesn't, something in the generator is non-deterministic (check for
  anything keyed off wall-clock time or dict ordering) — that's a bug in `build_site.py`,
  not expected behavior.
- **Generator change** (edited a `build_*` function): rebuild and spot-check the affected
  page(s) render correctly; there's no visual regression tooling, so this is a manual read
  of the generated HTML or a local `open site/index.html` / static file server.

`sitemap.xml`'s `<lastmod>` values come from `site/data/lastmod.json`, which records a
content hash for each generated route. A date advances only when that route's rendered
content changes; review changes to this state file along with the affected page.
