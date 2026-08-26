# HWS AI Club — website

The website for the AI Club at **Hobart and William Smith Colleges** (Geneva, New York).
It publishes **840 AI use cases across 42 majors** — 20 per major — where every use case
carries a copy-paste starter prompt and links to a specific, hand-verified tutorial video.

**Live:** https://www.hwsaiclub.com/

No framework, no build dependencies beyond Python. The site is plain static HTML/CSS/JS,
generated from data files so that content and presentation stay separate.

---

## How the site is built

```
AI_Use_Cases_by_Major_HWS.xlsx      the original use-case spreadsheet
        │
        │  scripts/extract_data.py
        ▼
site/data.json  +  site/js/data.js  canonical use-case data
        │
        │  scripts/build_site.py     (also reads site/data/videos-config.json)
        ▼
site/index.html · site/majors/index.html · site/majors/<slug>/index.html ×42
site/js/videos.js · sitemap.xml · robots.txt · _headers · og-image.*
```

`site/data/videos-config.json` is the single source of truth for video mapping: which
tutorial each use case links to, what that video teaches, and the starter-prompt pattern
per task archetype. It feeds **both** the Python generator and the generated
`site/js/videos.js`, and the two are cross-checked so they can't drift apart.

## Rebuilding

```bash
python3 scripts/build_site.py
```

Regenerates the homepage, majors, task hubs, FAQ, AI-coursework guide, founder pages,
`js/videos.js`, `sitemap.xml`, `robots.txt`, and legacy `_headers`.
Re-running it on an unchanged repo produces no diff.

Run the focused migration/schema regression checks with:

```bash
python -m unittest tests.test_seo_migration
```

To re-import from the spreadsheet (only needed when the xlsx itself changes):

```bash
python3 scripts/extract_data.py    # requires openpyxl
```

## Deploying

Vercel is the production host. After rebuilding and reviewing the generated `site/` diff,
deploy through the configured Vercel project. The repository has no Vercel CLI command or
`vercel.json` because the production project settings own that configuration.

`netlify.toml` is retained only to serve a permanent, path-preserving redirect from
`https://hws-ai-club.netlify.app/*` to `https://www.hwsaiclub.com/:splat`. Do not deploy
Netlify as the primary site.

## Editing content

| To change | Edit |
| --- | --- |
| A use-case title, description, or difficulty | `site/data.json` |
| Which video a use case links to, or its starter prompt | `site/data/videos-config.json` |
| Team roster, meeting time, site-wide copy | constants at the top of `scripts/build_site.py` |
| Styling | `site/css/styles.css` |
| Interactive behaviour (filters, copy button, deep links) | `site/js/site.js` |

**Do not edit `site/majors/**`, `site/index.html`, or `site/js/videos.js` by hand** —
they are generated, and the next build overwrites them. Change the source, then rebuild.

## Layout

```
scripts/
  build_site.py        static-site generator
  extract_data.py      spreadsheet → data.json / data.js
site/
  index.html           homepage            (generated)
  majors/              42 major pages      (generated)
  js/site.js           progressive enhancement (hand-written)
  js/videos.js         video resolver      (generated)
  css/styles.css       styles              (hand-written)
  data.json            use-case data       (generated from the xlsx)
  data/videos-config.json  video + prompt config (hand-maintained)
```

## For AI agents

Start at [AGENTS.md](AGENTS.md) (or [CLAUDE.md](CLAUDE.md) for Claude Code specifically).
Deeper references live in [docs/](docs/): [ARCHITECTURE.md](docs/ARCHITECTURE.md) (how the
generator works), [CONTENT_GUIDE.md](docs/CONTENT_GUIDE.md) (data schemas), and
[DEPLOYMENT.md](docs/DEPLOYMENT.md) (build artifacts, Vercel and legacy redirects, verification), and
[ANALYTICS.md](docs/ANALYTICS.md) (GA4 event taxonomy).

## A note on the videos

Every linked tutorial was watched end-to-end before being attached to a use case, and each
card names the video's real title, channel and year. The videos are third-party YouTube
content and are not affiliated with or endorsed by the club or the colleges.
