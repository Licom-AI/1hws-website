# AGENTS.md

Entry point for any AI coding agent working in this repository (tool-agnostic version of
[CLAUDE.md](CLAUDE.md), which contains the identical guidance for Claude Code specifically).

## What this is

The public website for the **HWS AI Club** (Hobart and William Smith Colleges). A plain
static HTML/CSS/JS site — no framework, no npm, no client-side build step. All content
generation happens in Python at build time; the browser only ever receives flat files.
Live at https://www.hwsaiclub.com/. Vercel is the production host; the old
`hws-ai-club.netlify.app` host exists only to permanently redirect legacy URLs.

Read [README.md](README.md) first for the project pitch and the content-editing table.
Then, depending on the task:
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how `build_site.py` works, function by function
- [docs/CONTENT_GUIDE.md](docs/CONTENT_GUIDE.md) — data file schemas, how to change content safely
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — generated artifacts, Vercel, legacy redirects, verifying a build
- [docs/ANALYTICS.md](docs/ANALYTICS.md) — GA4 setup, event taxonomy, what's tracked and why

## Commands

```bash
python3 scripts/build_site.py      # rebuild everything from source data (idempotent)
python3 scripts/extract_data.py    # re-import AI_Use_Cases_by_Major_HWS.xlsx (needs openpyxl)
python -m unittest tests.test_seo_migration  # migration/schema regression checks
# Deploy through the configured Vercel project after reviewing the generated site/ diff.
# Deploy the legacy Netlify configuration only when maintaining the old-host redirect.
```

No linter or node/npm toolchain. The standard-library regression checks cover the custom
domain migration and minimal-schema policy. After any change, rebuild and confirm
`git diff` on `site/` is either empty (no content change) or exactly what you intended —
that's the whole verification loop. `extract_data.py` and `build_site.py` both `assert` on
their expected shapes (42 majors, 20 use cases each, every output file present); a failed
assertion is the signal, not a false alarm to work around.

## The one thing to know before editing anything

**`site/majors/**`, `site/index.html`, `site/founders/**`, and `site/js/videos.js` are
generated.** Editing them directly is invisible work erased by the next build. The real
inputs are `site/data.json` (via the xlsx), `site/data/videos-config.json` (video/prompt
config), `scripts/build_site.py`'s constants block (team, founders, meeting info), and
`site/css/styles.css` / `site/js/site.js` (hand-written, not regenerated). Full pipeline
diagram and the video/prompt resolution logic (which spans `build_site.py` +
`videos-config.json` together) are in [CLAUDE.md](CLAUDE.md#architecture) and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
