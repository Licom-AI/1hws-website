# HWS AI Club SEO and AEO Optimization Plan

**Prepared:** August 26, 2026
**Site:** https://www.hwsaiclub.com/
**Organization:** HWS AI Club at Hobart and William Smith Colleges
**Primary objective:** Increase awareness among HWS students
**Primary conversion:** Outbound click to join the Skool community
**Status:** Plan for approval. No website implementation is authorized by this document.

## Executive decision

The first priority is to complete the domain migration. The live `www` site tells search engines that all 46 public HTML pages belong to the old Netlify hostname, the published live sitemap lists the old hostname, and the old Netlify pages still return `200 OK`. This splits ownership signals and is already visible in search: the custom homepage appears for branded queries, while an old Netlify `/majors/` URL appears for the join query. Whether that sitemap has been submitted in GSC is not yet verified.

The recommended order is:

1. Make every generated URL signal use `https://www.hwsaiclub.com` and permanently redirect every old Netlify path to the matching new path.
2. Connect this OpenSEO project to Google Search Console (GSC), establish the first-party baseline, submit the corrected sitemap, and inspect representative URLs.
3. Review and reconcile the structured-data cleanup based on repository commit `0cfc791` with the concurrent local working-tree changes, then deploy only the approved source/generated diff and simplify the remaining markup to the few entities that provide truthful, supported value.
4. Improve the campus answer and joining journey, beginning with a stable join destination and a curated “AI at HWS” resource page.
5. Expand major pages according to GSC demand, beginning with the four major phrases for which OpenSEO returned measurable U.S. demand.
6. Build authority through relevant, editorial HWS citations and maintain recurring rank, conversion, indexation, and AI-answer monitoring.

No traffic, conversion, index-count, or backlink-growth forecast is included because the required first-party GSC baseline is not connected to OpenSEO yet.

## Evidence rules used in this plan

| Label | Meaning |
| --- | --- |
| **OpenSEO evidence** | Data returned by the installed OpenSEO MCP on August 26, 2026. |
| **GSC evidence** | First-party Google data. None was available because the new OpenSEO project is not yet connected to GSC. |
| **Live verification** | Direct HTTP/HTML checks against the production custom domain and old Netlify domain. |
| **Repository verification** | Source and generated-file inspection at local `HEAD` commit `0cfc791`. Additional uncommitted structured-data changes were present in the working tree; they are concurrent work, not changes made or approved by this plan. |
| **Directional** | Useful for prioritization but not a complete count or durable measurement, such as a `site:` query or a small SERP sample. |
| **Recommendation** | Proposed work, not a measured fact. |

Search-volume values are U.S./English estimates returned by OpenSEO. A missing value is reported as **unknown**, not zero. Third-party ranking and backlink databases can lag or omit a new/small site; GSC is the authority for the site's Google performance.

## OpenSEO project and integration status

| Item | Status | Evidence / next action |
| --- | --- | --- |
| OpenSEO MCP | Connected | Hosted account `zh@licom.ai`; MCP scope confirmed with `whoami`. |
| Project | Created | `HWS AI Club`, project ID `ea176d55-59ff-4588-a827-c0c8ed195781`, U.S./English market. [OpenSEO project](https://app.openseo.so/p/ea176d55-59ff-4588-a827-c0c8ed195781) |
| Shared project context | Complete | Audience, goal, positioning, writing preferences, key pages, domain migration, baseline, and research logs saved. Comparable clubs were not saved as “competitors” because they are a proposed comparison set pending approval. |
| GSC verification | User-confirmed | The property is verified in Google, but verification does not automatically attach it to a newly created OpenSEO project. |
| GSC in OpenSEO | **Not connected** | All three attempted reads returned `reason: not_connected`. Connect at [OpenSEO Search Performance](https://app.openseo.so/p/ea176d55-59ff-4588-a827-c0c8ed195781/search-performance), then select the verified property that covers the preferred `www` URLs—ideally `sc-domain:hwsaiclub.com`, otherwise the verified `https://www.hwsaiclub.com/` URL-prefix property. |
| GA4 in OpenSEO | Not assessed | GA4 code exists in the repository, but the request centered on GSC. Connect GA4 in the same project before conversion reporting if not already available. |

### GSC intake to run immediately after connection

Use OpenSEO `get_search_console_performance` for:

- last 16 months and last 3 months by `query`;
- last 16 months and last 3 months by `page`;
- `query + page` to identify cannibalization and map campus demand to landing pages;
- `device` and `country` only after the core baseline, because the primary audience is small and segmentation can become noisy;
- positions 5–20 filtered client-side to identify striking-distance opportunities;
- branded versus non-branded query groups using an explicit query list, not assumptions.

Then use OpenSEO `inspect_urls` on the homepage, majors hub, four priority major pages, both founder pages, and corresponding old Netlify URLs where the connected property permits it. Record Google's selected canonical, crawl date, coverage state, and rich-result verdict. URL Inspection is the source of truth for indexation diagnosis; a `site:` query is not.

## Current baseline and verified findings

### Technical and migration baseline

| Finding | Evidence | Interpretation |
| --- | --- | --- |
| Custom apex redirects to `www` | **Live verification:** `https://hwsaiclub.com/` returns `308` to `https://www.hwsaiclub.com/` with no intermediate hop. | Correct. Vercel recommends `www` as primary and a redirect from the apex. Keep this behavior. |
| All public HTML pages canonicalize to Netlify | **OpenSEO audit:** 46 `canonicalized-page` findings across 46/46 crawled pages. **Live verification:** homepage and Economics page both publish old-host canonicals. | Critical migration conflict. The preferred custom URLs tell Google to consolidate elsewhere. |
| Old Netlify content is still accessible | **Live verification:** old homepage and old Economics page each return `200 OK`, not a redirect. | Search engines can crawl two live versions. The old host must redirect path-for-path. |
| Sitemap contains only old-host URLs | **OpenSEO page inventory:** all 46 custom URLs show `inSitemap: false`. **Repository/live verification:** `site/sitemap.xml` uses Netlify URLs. | Submit a corrected custom-domain sitemap only after generation is fixed and deployed. |
| Other generated URL signals use the old host | **Repository/live verification:** canonical, Open Graph URL/image, Twitter image, JSON-LD IDs/URLs, `robots.txt` sitemap directive, `sitemap.xml`, and `llms.txt` all derive from `BASE_URL`. | One source correction in `scripts/build_site.py` should regenerate the complete set. |
| All 46 pages returned `200` and were crawlable | **OpenSEO audit:** 46/46 pages fetched, `isIndexable: true`; no broken page, server error, missing H1, missing title, or missing description issue was reported. | The site has a healthy crawlable foundation once canonical ownership is corrected. |
| Titles exceed the audit threshold | **OpenSEO audit:** 46 `title-too-long` informational findings. | Optimize templates after migration; this is not equivalent to a penalty. Preserve clarity over arbitrary character limits. |
| Meta descriptions exceed the audit threshold | **OpenSEO audit:** 46 `meta-description-too-long` informational findings; homepage was 199 characters and many major pages were roughly 238–250. | Rewrite for concise campus intent and clearer calls to action after migration. |
| Hosting documentation is stale | **Repository verification:** `AGENTS.md`, `CLAUDE.md`, `README.md`, and `docs/DEPLOYMENT.md` still describe Netlify as production. No `vercel.json` exists. | Update documentation and record the actual Vercel project/root-directory workflow. Retain Netlify configuration only for the old-host redirects if that site remains under control. |

The [Google site-move guide](https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes) recommends direct permanent redirects, new self-canonicals, a new sitemap, URL testing, GSC monitoring, and keeping redirects for at least one year. [Netlify's domain-level redirect syntax](https://docs.netlify.com/manage/routing/redirects/redirect-options/#domain-level-redirects) supports a forced wildcard redirect that preserves the path. [Vercel recommends](https://vercel.com/docs/domains/working-with-domains/deploying-and-redirecting) the current apex-to-`www` arrangement.

### Current rankings and indexation signals

| Query / check | OpenSEO result on August 26, 2026 | Caveat |
| --- | --- | --- |
| Domain ranked-keyword dataset | No ranked keyword rows for `hwsaiclub.com`. | Third-party database absence is not proof of no rankings. Live SERPs below found branded rankings. |
| `HWS AI Club` | Custom homepage at position 7. HWS Engage was 1, HWS clubs page 2, LinkedIn 4. | U.S./English live SERP snapshot; rankings vary. |
| `Does HWS have an AI club` | Custom homepage at position 10. | The answer exists, but authoritative HWS/Engage/Skool sources outrank it. |
| `How do I join the HWS AI Club` | Custom site absent from top 20; old Netlify `/majors/` appeared at 16. | Strong evidence that migration cleanup and a clearer join destination are needed. |
| `Where can HWS students learn to use AI` | Custom homepage at position 10. | HWS institutional resources dominate the answer set. |
| `What AI resources exist for HWS students` | Custom site absent from top 20. | A curated campus resource page is an opportunity. |
| `AI for biology/economics/computer science students` | No HWS page in top 20 for any of the three tested queries. | All three SERPs contained commercial tools, publishers, universities, and AI Overview results. |
| `site:hwsaiclub.com` | Homepage and two founder pages returned; no major pages. | Directional only. Do not call this “three indexed pages”; confirm in GSC Page Indexing and URL Inspection. |
| `site:hwsaiclub.com/majors/` | No organic result returned. | Directional only; reinforces the need for GSC inspection after the canonical fix. |
| `site:hws-ai-club.netlify.app` | OpenSEO provider returned an internal search-engine error. | No conclusion about old-host index count. |

### Keyword evidence

OpenSEO evaluated eight campus/branded phrases and all 42 “AI for [major] students” phrases. It returned metric rows for only four major phrases:

| Keyword | U.S. monthly volume | KD | Intent | Initial destination |
| --- | ---: | ---: | --- | --- |
| `AI for biology students` | 10 | unknown | Commercial | `/majors/biology/` |
| `AI for computer science students` | 10 | unknown | Informational | `/majors/computer-science/` |
| `AI for economics students` | 10 | unknown | Commercial | `/majors/economics/` |
| `AI for psychology students` | 10 | unknown | Informational | `/majors/psychological-science/` |

The remaining major and branded phrases are **unknown**, not zero-volume. Campus awareness may also produce meaningful direct, referral, and branded demand too small for national keyword tools to report.

Broader OpenSEO discovery used the seeds `AI for college students` and `college AI club`. Both used the provider's fallback ideas source and produced noisy lists that were manually filtered. Relevant examples were:

| Keyword | U.S. monthly volume | KD | Intent | Use in this plan |
| --- | ---: | ---: | --- | --- |
| `AI for students` | 1,300 | 15 | Commercial | Theme signal; do not target generically without the HWS-specific value. |
| `best AI for studying` | 1,300 | 18 | Commercial | Support a responsible studying/resource section, not a thin “best tools” list. |
| `AI tools for students` | 1,000 | 29 | Commercial | Secondary phrase for the campus resource hub. |
| `AI prompt examples` | 1,000 | 2 | Informational | Relevant to the existing prompt library and its unique first-party examples. |
| `AI workshop` | 1,000 | 26 | Informational | Relevant to club/event content when actual workshop details are current. |
| `AI study guide` | 720 | 16 | Informational | Potential content format; use only if the club can add original guidance. |
| `best AI tools for students` | 720 | 36 | Commercial | Higher competition and commodity intent; not an early target. |
| `AI fluency` | 880 | 38 | Informational | Positioning language, not an immediate standalone page. |

### Authority and backlink baseline

OpenSEO's overview reported 2 backlinks and 2 referring domains. However, its referring-domain list and detailed backlink profile returned zero rows after spam/lost/broken filtering. This is internally inconsistent, so the defensible baseline is: **two aggregate backlinks were reported, but no individual referring source was validated**. Confirm with GSC Links and, if needed, another backlink provider before measuring growth.

Several high-value campus citations already exist without necessarily linking to the custom site:

- [HWS Engage AI Club profile](https://hws.campuslabs.com/engage/organization/aiclub) describes the club and provides a contact email; it ranks first for `HWS AI Club`.
- [HWS Clubs and Organizations](https://www.hws.edu/offices/student-engagement/clubs-and-organizations.aspx) lists “AI Club” as plain text among pre-professional clubs.
- [HWS Pre-Professional Clubs](https://careerservices.hws.edu/resources/hws-pre-professional-clubs/) lists “AI Club” as plain text.
- [HWS's Waymo event story](https://www.hws.edu/news/2025/the-future-of-mobility.aspx) describes the club, its leaders, and its responsible-AI mission, but the club name is not an obvious link to the custom site.
- [HWS Career Services' AI guide](https://careerservices.hws.edu/resources/using-ai-in-your-career-development/) and [Technology, Data & AI career channel](https://careerservices.hws.edu/channels/technology-data-artificial-science/) are strong topical neighbors.
- [HWS Library's AI tools guide](https://library.hws.edu/ai_tools) appeared in OpenSEO SERPs for campus AI-resource questions.

### Structured-data baseline

There are two distinct states:

1. **Live site at audit time:** the Economics page contained 18 JSON-LD blocks: BreadcrumbList, ItemList, one FAQPage built from 20 imperative use-case titles, and 15 VideoObject nodes for linked third-party YouTube videos. It did not embed or host those videos.
2. **Repository baseline at `HEAD` `0cfc791`:** the committed generator and generated major pages replace the 20 pseudo-questions with four visible, genuine Q&As and remove all VideoObject nodes. Each committed major page contains three blocks: BreadcrumbList, ItemList, and FAQPage. This cleanup was not yet reflected on the live page checked afterward. The local working tree also contains additional concurrent edits to the generator and generated major pages; those edits must be reviewed as a separate source/generated diff before deployment.

Implications:

- The live FAQPage markup is misleading because commands such as “Explain an economic concept” are not genuine questions and the full marked-up Q&A was not visible as such. The repository correction is directionally right.
- Google's [FAQ rich-result policy](https://developers.google.com/search/blog/2023/08/howto-faq-changes) limits regular FAQ rich results to authoritative government and health sites. Valid FAQ markup is not harmful, but it offers no expected visible Google benefit here.
- Google's [VideoObject documentation](https://developers.google.com/search/docs/appearance/structured-data/video) requires the video to be watchable on the page. Linked third-party videos do not qualify. The repository removal should be retained.
- Google's sitelinks search box was retired in November 2024. Google says unsupported `SearchAction` markup does not cause an error, but it has no search-box benefit and may be removed; keep the `WebSite` node for site-name understanding. See [Google's retirement notice](https://developers.google.com/search/blog/2024/10/sitelinks-search-box).
- Large JSON-LD is not a ranking strategy. Google's current [generative AI guidance](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide) says there is no special AEO schema requirement, warns against overfocusing on structured data, and says `llms.txt` neither helps nor harms Google visibility.

## Prioritized action register

### Critical

| ID | Action | Type | Source / systems | Acceptance criteria |
| --- | --- | --- | --- | --- |
| C1 | Change `BASE_URL` to `https://www.hwsaiclub.com` and regenerate every artifact. | One-time | `scripts/build_site.py`; generated HTML, `robots.txt`, `sitemap.xml`, `llms.txt` | All 46 HTML pages self-canonicalize on `www`; all OG, image, JSON-LD, sitemap, robots, and llms URLs use `www`; `rg "hws-ai-club.netlify.app" site scripts` finds only an intentional redirect rule or migration documentation. |
| C2 | Permanently redirect the old Netlify host path-for-path to the custom host. | One-time, maintain indefinitely if practical | `netlify.toml` and Netlify deployment | Root, `/majors/`, two sampled majors, founders, assets, query strings, and a 404-path test produce the intended direct result; all real old URLs return one `301`/permanent hop to their matching `www` URL, never the homepage indiscriminately. |
| C3 | Connect GSC to the OpenSEO project and capture the baseline before interpreting growth. | One-time setup; recurring reads | OpenSEO integration, GSC | Query/page/query+page datasets return successfully; representative URL Inspection results and sitemap status are saved; no `not_connected` response. |
| C4 | Submit the new sitemap and complete GSC migration controls. | One-time, monitor | GSC | New sitemap is accepted; verify old and new properties where possible; use Change of Address for the old Netlify property if Google permits it; monitor old decline/new rise. |

Recommended Netlify rule for approval and testing:

```toml
[[redirects]]
  from = "https://hws-ai-club.netlify.app/*"
  to = "https://www.hwsaiclub.com/:splat"
  status = 301
  force = true
```

Keep it for at least one year; indefinite retention is better for old links and bookmarks. Confirm the old Netlify site is still controlled by this account before deploying the rule.

### High

| ID | Action | Type | Source / systems | Acceptance criteria |
| --- | --- | --- | --- | --- |
| H1 | Review, reconcile, deploy, and validate the structured-data cleanup based on `0cfc791` and the concurrent working-tree changes. | One-time | Existing `scripts/build_site.py`, generated major pages, CSS/JS/assets | The approved source diff is explicit; generated output follows from it; live major pages have zero VideoObject nodes; visible Q&A exactly matches any retained FAQ markup; Rich Results Test/Schema validator shows no critical errors. |
| H2 | Adopt a minimal structured-data policy. | One-time, review annually | `scripts/build_site.py` | Homepage: Organization + WebSite, and Event only while facts are current. Major pages: BreadcrumbList; remove generic ItemList and likely FAQPage JSON-LD while retaining useful visible Q&A. Founder pages: verified Person + BreadcrumbList. No invented third-party `@id`, unsupported SearchAction, or unverifiable dates/relationships. |
| H3 | Rewrite title and meta-description templates around intent and readability. | One-time, recurring tests | `scripts/build_site.py` constants and builder functions | Unique, concise titles/descriptions for home, majors hub, major pages, founders, join/resource pages; no truncation-driven loss of the primary phrase; rerun OpenSEO audit. |
| H4 | Create a stable, answerable joining destination or make the homepage join section addressable and complete. | One-time, update each term | `scripts/build_site.py`; optionally generated `site/join/index.html` | Page/section states who can join, cost, current meeting time/place, no-experience requirement, and direct Skool action; facts are visible in HTML and match entity/event data. |
| H5 | Reduce Skool funnel friction and verify analytics. | One-time, recurring optimization | `scripts/build_site.py`, `site/js/site.js`, GA4 | Primary CTA either goes directly to Skool or to one clear join step; `join_community_click` fires exactly once; GA4 marks it as a key event; mobile and keyboard journeys pass. |
| H6 | Publish a curated “AI at HWS” resource hub that complements institutional resources. | One-time, update quarterly | `scripts/build_site.py`; generated `site/resources/ai-at-hws/index.html` | Answers the two missing AEO questions, cites HWS Library/Career Services/Digital Learning/club resources, distinguishes club content from official policy, and links to joining and major pages. |

### Medium

| ID | Action | Type | Source / systems | Acceptance criteria |
| --- | --- | --- | --- | --- |
| M1 | Improve the first four measurable major pages: Biology, Computer Science, Economics, Psychological Science. | One-time pilots, recurring updates | `site/data.json` or spreadsheet source for factual use-case copy; `site/data/videos-config.json` for video/prompt mapping; `scripts/build_site.py` for page framing | Each page adds a concise original introduction, responsible-use caveat, genuine major questions, HWS program link, and internal links; no thin generic “best tools” copy. |
| M2 | Add campus entity corroboration and sameAs links only where they identify the same organization. | One-time, monitor | `scripts/build_site.py` | Use HWS Engage, LinkedIn, and Skool if confirmed current. Do not assert HWS endorsement beyond official listings. Use a stable club `@id`; do not invent an HWS-owned fragment identifier. |
| M3 | Earn editorial campus links. | Recurring campaign | External HWS/CampusLabs pages; no repository change except destination quality | HWS Engage website field points to `www`; clubs/pre-professional pages link contextually; relevant Career Services/Library/news pages link only when editorially useful. |
| M4 | Update deployment and architecture documentation for Vercel. | One-time | `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/DEPLOYMENT.md`, `docs/ARCHITECTURE.md`, possibly `docs/ANALYTICS.md` | No production instruction calls Netlify the primary host; Vercel root/output/deploy behavior is documented; Netlify's sole migration role is explicit. |
| M5 | Build a manual OpenSEO rank tracker after keyword approval. | Setup, recurring | OpenSEO | Estimate cost first; user approves keyword set and schedule; initial manual run captured on mobile and desktop only if useful. Do not create a paid schedule silently. |

### Low

| ID | Action | Type | Source / systems | Acceptance criteria |
| --- | --- | --- | --- | --- |
| L1 | Retain `llms.txt` only if maintaining it remains effortless. | Recurring | `scripts/build_site.py`, generated `site/llms.txt` | Correct `www` links and facts; no claim that it improves Google ranking or AI visibility. |
| L2 | Review AI-bot-specific robots rules. | Annual | `scripts/build_site.py` | Wildcard Googlebot access remains clear; bot rules reflect the club's actual training/citation preferences. Note that `Google-Extended` is not the control for Google Search AI feature eligibility. |
| L3 | Reassess generic ItemList and founder schema. | Annual | `scripts/build_site.py` | Keep only accurate, maintainable properties with a named consumer or entity-understanding purpose. |
| L4 | Evaluate Core Web Vitals after migration. | Recurring | GSC CWV, optional OpenSEO Lighthouse | Use field data when available; do not create a performance project based only on lab scores. |

## Exact repository impact

### Source files that may be changed after approval

| File | Planned responsibility |
| --- | --- |
| `scripts/build_site.py` | Preferred domain, metadata templates, minimal JSON-LD, new join/resource page builders, robots/sitemap/llms generation, current meeting/entity facts. This is the primary source of truth. |
| `netlify.toml` | Forced domain-level path-preserving redirects from the old Netlify hostname to `www`. Keep Vercel as production. |
| `site/data.json` or `AI_Use_Cases_by_Major_HWS.xlsx` + `scripts/extract_data.py` | Major/use-case factual improvements. Follow the repository's current canonical source decision; do not hand-edit generated page HTML. |
| `site/data/videos-config.json` | Only if tutorial mapping, titles, prompt patterns, or factual video metadata must change. Removing schema alone does not require changing this file. |
| `site/css/styles.css` | Styling for approved visible Q&A, join page/resource hub, and CTA hierarchy. Existing committed FAQ styles should be reused. |
| `site/js/site.js` | CTA analytics or interaction changes only. Preserve the current progressive-enhancement and single-event behavior. |
| `AGENTS.md`, `CLAUDE.md`, `README.md` | Correct live domain, hosting, deployment, and source-of-truth guidance. |
| `docs/DEPLOYMENT.md`, `docs/ARCHITECTURE.md`, `docs/ANALYTICS.md` | Vercel verification, redirect ownership, generated outputs, schema policy, and conversion reporting. |

`vercel.json` should not be added merely for appearance. The current apex redirect already works from Vercel project settings. Add a repository config only if a required Vercel behavior cannot be managed reliably in the project settings and the team wants it version-controlled.

### Generated outputs expected to change

These must be regenerated, never edited directly:

- `site/index.html`
- `site/majors/index.html`
- `site/majors/*/index.html` (42 pages)
- `site/founders/*/index.html` (2 pages)
- proposed `site/join/index.html` and `site/resources/ai-at-hws/index.html`, if approved
- `site/robots.txt`
- `site/sitemap.xml`
- `site/llms.txt`
- possibly `site/_headers` if the legacy Netlify/header strategy changes
- generated assets only if logo/OG image source changes

`site/js/videos.js` should remain unchanged unless `videos-config.json` changes. The expected generated diff must be explained by an approved source change.

## Technical SEO correction design

### 1. Canonical and migration cutover

1. Change the generator's `BASE_URL` to `https://www.hwsaiclub.com`.
2. Rebuild locally; verify all generated canonicals, OG URLs/images, JSON-LD IDs/URLs, sitemap locations, robots sitemap directive, and llms links.
3. Deploy the custom-domain build to Vercel.
4. Deploy the forced wildcard redirect to the old Netlify site.
5. Test root and path parity with `curl -I`, including query strings and trailing slashes. Avoid a redirect chain through the apex.
6. Submit `https://www.hwsaiclub.com/sitemap.xml` in the custom-domain GSC property.
7. Verify the old Netlify URL-prefix property if possible and use GSC Change of Address if Google exposes it for that property type.
8. Request recrawl of the homepage, majors hub, four priority majors, and any page that formerly appeared under Netlify.
9. Monitor old versus new URL impressions weekly until stable; keep redirects at least 12 months.

Do not `noindex` the old host before Google processes the redirects. Google must be able to crawl the old URLs and see the permanent move.

### 2. Metadata templates

Use primary intent first and remove repeated long institutional boilerplate. Draft patterns to test, not final copy:

- Homepage title: `HWS AI Club | AI Workshops and Resources for HWS Students`
- Majors hub: `AI Use Cases by Major | HWS AI Club`
- Major page: `AI for {Major} Students at HWS | 20 Practical Use Cases`
- Join page: `Join the HWS AI Club | Free Weekly Workshops`
- Resource hub: `AI Resources for HWS Students | HWS AI Club`

Descriptions should state audience, distinctive resource, responsible-use cue, and next action in natural language. OpenSEO's 70–160-character heuristic is a review aid, not an algorithmic rule.

### 3. Minimal structured-data policy

Recommended end state:

| Page type | Keep | Remove / avoid |
| --- | --- | --- |
| Homepage | `WebSite` with `name`, `alternateName`, `url`; club `Organization`/appropriate subtype with verified `sameAs`; current `Event` only while dates/location are accurate | `SearchAction`; stale event dates; unverified founding month; invented HWS-owned `@id`; sitewide FAQ markup for rich-result hopes |
| Majors index | `BreadcrumbList`; optional lightweight `ItemList` only if a consumer is named | Repeated organization nodes |
| Major page | `BreadcrumbList` | `VideoObject` for links; 20-item generic `ItemList`; `FAQPage` unless a real consumer justifies it. Keep visible Q&A in HTML. |
| Founder page | `Person` and `BreadcrumbList`, using verified facts and profile links | Unsupported employment, affiliation, or alumni claims; unrelated organizations in `sameAs` |
| Join page | Usually `BreadcrumbList`; reference the homepage organization `@id`; Event only if it describes the visible current event | Duplicate organization definitions and stale schedules |

The 512px raster logo committed in `0cfc791` is acceptable if crawlable and representative. Google's [Organization logo guidance](https://developers.google.com/search/docs/appearance/structured-data/organization) requires at least 112×112 pixels and a Google Images-supported format; do not document “SVG is rejected” as a universal rule without validation.

### 4. Sitemap, robots, and Vercel behavior

- Sitemap: include only canonical, indexable `www` URLs. Add new join/resource pages if approved. Consider removing `<lastmod>` unless it reflects actual page modification; the current build date changes all entries regardless of content changes.
- Robots: keep public pages crawlable. `showcase.html` already has a page-level `noindex`; Vercel does not consume Netlify `_headers`, so page-level directives are the portable control.
- AI bots: document the distinction between search crawling, model training, and user-agent retrieval. Explicit `Allow` rules do not create citations.
- `llms.txt`: keep accurate or remove; do not make it a critical AEO task. Google explicitly says it ignores it for Search and generative Search features.

## AEO, entity, and citation strategy

### Answer architecture

Answer engines need crawlable, corroborated facts more than extra schema. Create one stable, visible answer source for each fact:

| Question | Primary owned answer | Corroborating source | Required answer elements |
| --- | --- | --- | --- |
| Does HWS have an AI club? | Homepage | HWS Engage; HWS Clubs and Organizations | Yes; student-run; open to all HWS majors; responsible, practical AI literacy. |
| How do I join the HWS AI Club? | Join page or stable `/#community` section | HWS Engage; Skool | Direct Skool URL, eligibility, cost, current meeting details, no experience required. |
| Where can HWS students learn to use AI? | “AI at HWS” resource hub | HWS Library, Career Services, Digital Learning, club | Separate official college services from club workshops/resources. |
| What AI resources exist for HWS students? | Resource hub | HWS institutional pages | Curated, dated list with source links and a clear owner/update cadence. |
| How can [major] students at HWS use AI? | Corresponding major page | HWS program page; course-policy reminder | Concrete use cases, starter prompts, provenance, limits, and a join CTA. |

### Entity policy

- Use one stable club identifier on the preferred domain, such as `https://www.hwsaiclub.com/#organization`.
- Link only profiles that identify the same club: HWS Engage, verified LinkedIn, and Skool. Confirm each before adding.
- Describe HWS as the parent institution only to the extent supported by the official student-organization listing. Use `name` and `url`; avoid asserting an external `@id` that HWS itself has not published.
- Keep club, college, founders, sponsors, and associated businesses as distinct entities. Do not use `sameAs` for sponsorships, employment, or loose associations.
- Display last-reviewed dates on resource/join content when facts can change.
- Add author/editor responsibility for substantive guidance where practical, especially responsible-use content.

### Citation strategy

The goal is not fabricated “mentions.” It is a consistent factual graph:

1. Owned page states a fact clearly.
2. Official HWS/Engage/Skool pages corroborate the fact and, where editorially appropriate, link to the owned detail page.
3. Club social profiles use the same preferred URL, name, description, and join destination.
4. News/event pages link to relevant evidence rather than being asked for generic promotional links.
5. AI-answer tests record both correctness and which sources were cited.

## Campus-focused keyword and content map

| Cluster | Primary intent | Destination | Priority | Evidence / content requirement |
| --- | --- | --- | --- | --- |
| HWS AI Club entity | `HWS AI Club`, `Hobart and William Smith AI Club`, `AI club HWS` | Homepage | Critical | Custom homepage currently ranks 7 for `HWS AI Club`; strengthen preferred-domain ownership and corroboration. |
| Joining | `join HWS AI Club`, `How do I join the HWS AI Club?`, meetings, cost, eligibility | `/join/` or durable homepage section | High | Custom site absent top 20 for tested join question; old Netlify URL ranked 16. |
| Campus AI resources | `AI resources HWS students`, `Where can HWS students learn to use AI?`, `AI at Hobart and William Smith` | `/resources/ai-at-hws/` | High | Custom homepage ranks 10 for “where,” absent top 20 for “what resources.” Cite institutional sources. |
| Major library | `AI use cases by major`, `AI for HWS students`, `AI prompts for students` | `/majors/` | High | Unique asset: 840 use cases across 42 majors. Explain methodology and responsible use. |
| Biology | `AI for biology students` + HWS modifier | `/majors/biology/` | High pilot | OpenSEO: volume 10, KD unknown, commercial. Compete on HWS specificity and responsible use, not homework solving. |
| Computer Science | `AI for computer science students` + HWS modifier | `/majors/computer-science/` | High pilot | OpenSEO: volume 10, KD unknown, informational. SERP favors university/education sources and tools. |
| Economics | `AI for economics students` + HWS modifier | `/majors/economics/` | High pilot | OpenSEO: volume 10, KD unknown, commercial. SERP dominated by solvers/tools; differentiate with learning and method validation. |
| Psychological Science | `AI for psychology students` + HWS modifier | `/majors/psychological-science/` | High pilot | OpenSEO: volume 10, KD unknown, informational. Use ethical/privacy/research-method boundaries. |
| Remaining 38 majors | `AI for [major] students`, HWS-specific questions | Existing major pages | Medium, data-led | Volume unknown. Prioritize by GSC impressions, page engagement, club demand, and faculty/student input, not alphabetical bulk expansion. |
| Responsible use | `use AI responsibly at HWS`, course AI rules, privacy, citations | Resource hub + reusable visible section | High | Never present club guidance as official course policy. Point students to syllabus/professor and official resources. |
| Workshops and events | `AI workshop HWS`, `AI workshop` | Join/events content | Medium | OpenSEO broad term: volume 1,000, KD 26. Publish only real, current workshops with dates and outcomes. |

Each major page should remain genuinely distinct. Its unique value is the selected use cases, prompts, HWS program context, and field-specific limits—not mechanical swapping of the major name into a generic introduction.

## Comparable-club and search-competitor research

The competitive set has three categories and should not be conflated:

| Category | Examples surfaced | What to learn | What not to copy |
| --- | --- | --- | --- |
| Official college club pages | [Marist AI Club](https://www.marist.edu/clubs/ai-club), [Northeastern AI NU](https://www.khoury.northeastern.edu/clubs_and_orgs/artificial-intelligence-club/), [MSU AI Club](https://datascience.msu.edu/Student_Clubs/ai_club.aspx), [UF AI student groups](https://ai.ufl.edu/for-our-students/student-groups/) | Clear mission, meeting/join process, leadership/contact, activities, inclusive audience, institutional corroboration, links to broader campus opportunities. | Institutional scale or programs HWS AI Club does not provide. |
| Independent student-club sites | AI Club at William & Mary, University of Oregon AI association, AI Club UA | Student voice, project/event archives, direct community links. | Unverified claims, stale calendars, or overly technical positioning that excludes non-CS majors. |
| SERP competitors for student AI intent | Mindgrasp, OneGoal, Reddit, student-tool publishers, university guides | Searchers want tools, studying help, prompt examples, and subject-specific answers. | Homework-solver framing, affiliate lists, or commodity “best tools” pages. |

OpenSEO `find_serp_competitors` used six queries and returned a directional list led by general student-tool/resource sites. Each returned domain overlapped only one query, so the output is too sparse for market-share conclusions. Live SERPs were more useful for identifying comparable university clubs. After GSC connection, rerun the landscape with a refined 8–10-query set and analyze no more than the top 3–5 relevant domains before spending additional credits.

The official comparable-club pages support this practical feature comparison:

| Comparable | Join/contact path | Meeting details | Audience/offer | Institutional corroboration lesson |
| --- | --- | --- | --- | --- |
| Marist AI Club | Board and social links are visible. | Publishes meeting information. | Mission and club activities are explicit. | A concise official page can answer identity, contact, and attendance questions together. |
| Northeastern AI NU | Open-join language, links, and email are visible. | Activity details are available. | Explicitly multidisciplinary and inclusive. | State who can join and what participation looks like, not only what AI is. |
| Michigan State AI Club | Direct contact email. | Limited detail on the surfaced page. | Concise student value proposition. | Even a short institutional page can corroborate the entity when contact and purpose are clear. |
| University of Florida AI student groups | Routes students into groups and the broader campus AI ecosystem. | Group-specific rather than a single club schedule. | Connects clubs with courses, research, and internships. | The HWS resource hub should connect—not impersonate—the college's wider AI resources. |

This is a feature comparison, not a traffic, authority, or performance ranking; no comparable-club metrics were available from GSC.

## Ethical authority and backlink plan

### Priority campus opportunities

| Prospect | Current evidence | Ethical ask | Destination |
| --- | --- | --- | --- |
| HWS Engage AI Club profile | Ranks first for branded query; contains club description and contact email. | Add/update the official website field to `https://www.hwsaiclub.com/`; align meeting and join details. | Homepage or join page |
| HWS Clubs and Organizations | AI Club is plain text while many clubs link to Engage. | Ask Student Engagement to link “AI Club” to the Engage profile or custom site according to their editorial convention. | Engage or homepage |
| HWS Pre-Professional Clubs | AI Club is plain text. | Offer a concise verified description and ask whether a contextual link to the club/join page helps students. | Join page |
| HWS Career Services AI guide / AI career channel | Strong topical fit and current student guidance. | Propose the major-specific library or resource hub as a complementary student-club resource, with a clear non-official disclaimer. | Resource hub or majors hub |
| HWS Library AI tools guide | Appears for AI-resource questions. | Ask librarians to review the club resource hub; request inclusion only if it meets their quality criteria. Link back to the library as the authoritative resource. | Resource hub |
| HWS Waymo news story | Names and quotes the club but does not obviously link to its site. | Ask the web/news editor whether the first club mention can link to the canonical club site. Do not request retroactive promotional copy. | Homepage |
| Selected HWS major/program pages | Every club major page already links outward to the program. | Pilot with the four measurable majors. Ask whether faculty/program staff consider the page a useful optional student resource; no mass reciprocal-link campaign. | Specific major page |

### Guardrails

- Personalize each request around the exact page and student benefit.
- Do not buy links, trade links at scale, submit to low-quality directories, or automate mass outreach.
- Do not imply HWS endorsement, official academic policy, or faculty approval without written confirmation.
- Do not ask editors to link to thin or migration-conflicted pages; complete the critical fixes first.
- Record the editor/contact path and outcome. Use only public contact information and do not invent addresses.
- Measure verified, relevant referring pages—especially `hws.edu`, `library.hws.edu`, `careerservices.hws.edu`, and HWS Engage—not raw backlink volume.

## Skool conversion plan

### Funnel definition

```text
Search / AI answer / campus referral
              ↓
Relevant owned landing page
              ↓
Understands audience, value, safety, meeting, and cost
              ↓
Clicks “Join the Skool community”
              ↓
Skool membership completed (currently not observable on-site)
```

`join_community_click` is the primary measurable website conversion, but it is a proxy for completed membership. A confirmed join KPI requires a Skool-side report, referral parameter, or a privacy-safe manual reconciliation.

### Recommended changes

- Put one primary “Join the HWS AI Club” action above the fold. Test a direct Skool link against a concise join page; do not force two scroll/click steps by default.
- State “free,” “open to HWS students,” “no coding experience required,” and current meeting details adjacent to the CTA.
- Replace the manually maintained exact member count if it cannot be updated reliably; stale social proof harms trust.
- Use one consistent CTA label and destination across navigation, homepage, major pages, and resource content.
- Preserve `rel="noopener"` for new tabs and provide an accessible external-link cue.
- Verify `join_community_click` fires once with `location` and `link_url`; keep `join_cta_click` as a micro-conversion only when it represents an intermediate step.
- In GA4, register needed custom dimensions and mark `join_community_click` as a key event. Segment by `session default channel group = Organic Search` and landing-page group.
- If Skool accepts and reports UTM parameters, use a stable owned-source campaign convention; otherwise do not add unmeasurable parameter clutter.

## Rank tracking and AI-visibility prompt set

### Proposed OpenSEO rank tracker

Create only after keyword approval and cost estimation. Start manual or monthly, not daily, because the audience is campus-specific and the site is early in migration.

**Brand/campus set**

1. HWS AI Club
2. Hobart and William Smith AI Club
3. AI club HWS
4. Does HWS have an AI club
5. Join HWS AI Club
6. HWS AI resources
7. AI resources for HWS students
8. Where can HWS students learn AI
9. AI workshops HWS
10. Artificial intelligence Hobart and William Smith Colleges

**Major set**

11. AI for biology students
12. AI for computer science students
13. AI for economics students
14. AI for psychology students
15. AI for public health students
16. AI for environmental science students
17. AI for business students
18. AI for writing students
19. AI for international relations students

**Broader discovery set**

20. AI for college students
21. AI tools for students
22. AI prompt examples
23. AI workshop

Use Geneva, New York location granularity for campus-intent terms if OpenSEO accepts it; retain U.S./English for broader non-campus terms. Use mobile first and add desktop only if device differences are actionable. Before creating the tracker, call `estimate_rank_tracker_cost`, show the one-run and scheduled monthly estimate, obtain approval, then create/add/run. Keep the final list small enough to make monthly review useful.

### AEO baseline status and AI-answer prompt set

**Measured answer-engine baseline:** not available on August 26, 2026. The installed OpenSEO MCP exposes Google SERP, keyword, backlink, audit, rank-tracking, and GSC tools, but no tool that runs prompts across answer engines or records their citations. No club-mention rate, owned-citation rate, or answer-accuracy percentage is therefore claimed.

The current question-based **search proxy** is:

| Baseline question | OpenSEO Google SERP proxy | Answer-engine citation status |
| --- | --- | --- |
| Does HWS have an AI club? | Custom homepage at position 10. | Not measured. |
| How do I join the HWS AI Club? | Custom site absent from top 20; old Netlify `/majors/` at 16. | Not measured. |
| Where can HWS students learn to use AI? | Custom homepage at position 10. | Not measured. |
| What AI resources exist for HWS students? | Custom site absent from top 20. | Not measured. |
| How can [major] students at HWS use AI? | No HWS result in the top 20 for the Biology, Economics, or Computer Science variants tested. | Not measured. |

This proxy shows answerability and domain-contamination risks in search; it does **not** show what an answer engine says or cites. Before the first migration deployment, run and archive the manual prompt set below so the pre-change AEO baseline cannot be contaminated by the fixes. Repeat the identical set after recrawl and monthly thereafter.

Run the same prompts in a clean, documented session on the selected answer engines. Record date, engine/model, logged-in state, answer text or screenshot, cited URLs, and whether web search was enabled.

**Core prompts**

1. Does HWS have an AI club?
2. How do I join the HWS AI Club?
3. Where can HWS students learn to use AI?
4. What AI resources exist for HWS students?
5. When and where does the HWS AI Club meet?
6. Is the HWS AI Club free and open to all majors?
7. What should HWS students know before using AI on coursework?
8. Who runs the HWS AI Club?
9. What AI workshops are available to HWS students?
10. What is the official website for the HWS AI Club?

**Major template**

11. How can a [major] student at HWS use AI responsibly?
12. What AI resources are available for [major] students at Hobart and William Smith Colleges?
13. Give practical AI use cases for an HWS [major] student and cite sources.

Run the major template first for Biology, Computer Science, Economics, and Psychological Science, then expand according to GSC impressions and student demand.

### AI-visibility measurements

| Metric | Definition |
| --- | --- |
| Club mention rate | Prompts whose answer correctly mentions HWS AI Club ÷ prompts tested. |
| Owned citation rate | Prompts citing `www.hwsaiclub.com` ÷ prompts tested. |
| Authoritative corroboration rate | Prompts citing an appropriate HWS/Engage/Library/Career Services source ÷ prompts tested. |
| Critical-fact accuracy | Answers with correct organization, audience, join URL, and current meeting facts ÷ applicable prompts. |
| Old-domain contamination | Prompts citing `hws-ai-club.netlify.app` ÷ prompts tested. Target is zero after migration processing. |
| Major-page citation coverage | Tested major prompts citing the matching owned major page ÷ major prompts tested. |

Do not combine these into an opaque “AI visibility score.” Report the components and sample size.

## KPIs and measurement definitions

### One-time migration quality gates

| KPI | Definition | Post-fix criterion |
| --- | --- | --- |
| Self-canonical coverage | Canonical `www` pages with matching self-canonical ÷ canonical pages tested | 100% |
| New-host sitemap coverage | Canonical indexable `www` URLs present in sitemap ÷ canonical indexable URLs | 100% |
| Old-host redirect coverage | Known old URLs returning one permanent path-preserving redirect ÷ old URLs tested | 100% |
| Old-host 200 count | Tested old content URLs still returning content | 0 |
| Structured-data critical errors | Critical errors in representative Rich Results Test/Schema validation | 0 |
| Generated old-host references | Unintended old-host occurrences in `site/` after build | 0 |

### Recurring acquisition KPIs

- **GSC branded clicks/impressions/CTR/average position:** explicit brand-query filter; report 28 days versus previous 28 days and year over year only when comparable data exists.
- **GSC non-branded campus clicks/impressions:** approved campus-intent query set excluding brand terms.
- **Major-page visibility:** clicks, impressions, CTR, average position, and number of major pages receiving impressions.
- **Valid indexed canonical pages:** GSC Page Indexing plus representative URL inspections; do not use `site:` result counts as the KPI.
- **Search appearance:** standard results and any available generative AI reporting in GSC; use the reporting available in the connected property rather than assumptions.

### Recurring conversion KPIs

- **Organic Skool click conversion rate:** unique eligible organic sessions with at least one `join_community_click` ÷ eligible organic sessions. Do not divide raw click-event count by sessions, because repeat clicks could produce a rate above 100%.
- **Join CTA progression:** visitors who click an intermediate join CTA and then click Skool ÷ visitors who click the intermediate join CTA.
- **Prompt value rate:** `prompt_copied` users ÷ major-page users, segmented by major.
- **Confirmed membership conversion:** new memberships attributable to the website ÷ unique Skool clickers, only if Skool attribution becomes available.
- **Landing-page assisted conversions:** organic landing-page sessions that later fire `join_community_click` in the same session.

### Recurring authority KPIs

- Count of verified relevant referring pages, with a separate count for HWS-controlled domains/subdomains.
- Percentage of priority institutional listings using the preferred `www` URL.
- Lost/broken authoritative links requiring repair.
- Referral sessions and Skool clicks from campus referring pages.

No numeric growth target should be approved until 28 complete post-migration days are captured. Then set targets from the observed baseline and club capacity.

## 30/60/90-day roadmap

### Days 0–30: consolidate and measure

**Pre-change baseline checkpoint**

- Connect GSC and GA4 to the OpenSEO project.
- Capture pre-cutover GSC exports/readouts where available.
- Run and archive the manual AI-answer prompt baseline before any deployment; keep the existing OpenSEO question-SERP results as a separate search proxy.
- Resolve which concurrent working-tree changes belong to approved migration work and which require a later release.

**Release 1 — migration signals only**

- Implement C1, C2, and C4: source domain correction, deterministic rebuild, Vercel deployment, path-preserving old-Netlify redirects, corrected sitemap submission, and URL Inspection.
- Keep this deployment limited to canonical/domain outputs and the redirect configuration so migration effects are attributable.
- Pass the live redirect/canonical/sitemap checks and start the weekly migration dashboard before the next release.

**Release 2 — structured data**

- Review and reconcile the `0cfc791` baseline with the concurrent working-tree diff.
- Deploy the invalid VideoObject and pseudo-FAQ cleanup as an isolated release after Release 1 passes its live checks.
- Remove obsolete SearchAction and establish the minimal schema policy; validate representative page types.

**Release 3 — metadata, measurement, and documentation**

- Rewrite metadata templates only after migration and schema checkpoints are recorded.
- Correct repository hosting/deployment documentation.
- Verify GA4 key events and the Skool click path.

**Recurring starts**

- Weekly migration dashboard: old/new impressions, canonical status, sitemap errors, indexed-page movement, redirect tests.
- Weekly live checks of meeting/join facts.
- Repeat the pre-change AI-answer prompt baseline after Google recrawls the critical pages; keep both dated runs.

**Day-30 deliverable**

A migration report containing GSC baselines, URL Inspection evidence, corrected audit results, redirect matrix, schema validation, and the first conversion baseline. Do not declare the migration complete merely because deployment succeeded.

### Days 31–60: improve answers and conversion

**One-time/pilot**

- Publish or finalize the join destination and “AI at HWS” resource hub.
- Improve the Biology, Computer Science, Economics, and Psychological Science pages.
- Align HWS Engage, LinkedIn, Skool, and owned-site entity facts/URLs.
- Send personalized outreach to HWS Engage, Student Engagement, Career Services, Library, and the Waymo story editor after destination pages pass quality review.
- Create the approved OpenSEO manual/monthly rank tracker.

**Recurring**

- Review GSC striking-distance queries and query-page mapping every two weeks.
- Review Skool click conversion by landing-page group monthly.
- Run AI-answer prompts monthly and log citations/accuracy.

**Day-60 deliverable**

A campus visibility report: query growth, priority page performance, link outcomes, conversion path, and AI-answer citation changes. Identify the next four majors from evidence.

### Days 61–90: expand what works

**One-time/expansion**

- Improve the next evidence-selected major pages; do not bulk rewrite all 42 without proof of value.
- Add original workshop recaps, student examples, or responsible-use guidance only where the club can supply first-hand value.
- Repair or update external profiles that still use Netlify.
- Refine internal links from homepage/resource/join pages to winning major pages.

**Recurring**

- Monthly OpenSEO rank check and GSC/GA4 report.
- Monthly AI-answer prompt run.
- Quarterly content and link audit.
- Termly meeting/event/entity fact review.

**Day-90 deliverable**

A decision report that separates migration recovery from content gains, documents confirmed joins or click proxies, and recommends the next quarter based on GSC demand and club capacity.

## OpenSEO workflow by phase

| Phase | OpenSEO sequence | Write-back / approval rule |
| --- | --- | --- |
| Setup | `whoami` → `list_projects` → `create_project` → `get_project_context` → `update_project_context` | Completed. Durable facts and research log are saved. |
| GSC baseline | Connect integration → `get_search_console_performance` by query/page/query+page → `inspect_urls` → optional `get_search_opportunities` after GA4 connection | GSC connection requires user OAuth/property selection. Save findings, not raw invented conclusions. |
| Technical validation | `run_site_audit` at 50-page budget → `get_audit_status` → `get_audit_issues` → `get_audit_pages` | Initial audit completed. Rerun after cutover and compare issue types/counts. |
| Keyword research | GSC striking distance first → `get_keyword_metrics` for known terms → `research_keywords` for gaps → `get_serp_results` for intent | Do not save/tag keywords until the user approves the shortlist. |
| Competitive landscape | `find_serp_competitors` on refined query set → representative `get_serp_results` → top 3–5 `get_domain_overview`/`get_ranked_keywords` only if useful | Comparable clubs are not yet saved as competitors. Confirm the roster first. |
| Link prospecting | Own `get_backlinks_overview`/profile → competitor profiles where relevant → `get_serp_results` for resource queries → browser verification/contact discovery | Attribute OpenSEO versus web findings. Never invent contacts or mass outreach. |
| Rank tracking | `get_rank_tracker` → `estimate_rank_tracker_cost` → approval → `create_rank_tracker` → add approved keywords → `run_rank_tracker` | A scheduled tracker creates recurring spend. Show estimates and obtain approval first. |
| AEO baseline | Preserve OpenSEO question-SERP snapshots as the search proxy → manually run the fixed prompt set before deployment → repeat after recrawl → log answer/citations separately | OpenSEO exposes no answer-engine prompt runner in the installed MCP, so do not label SERP positions as answer-engine citations or invent a visibility score. |
| Reporting | GSC performance + GA4 organic landing pages/key events + rank tracker + audit spot checks + manual AI prompt log | Monthly report; quarterly strategy reset. |

## Verification checklist for any approved repository change

Repository rules require source-first changes and a deterministic rebuild.

```powershell
python scripts/build_site.py
git status --short
git diff --stat
git diff -- site/
rg -n "hws-ai-club\.netlify\.app" scripts site netlify.toml README.md AGENTS.md CLAUDE.md docs
rg -n '"@type": "(VideoObject|FAQPage|SearchAction)"' site
```

Expected review:

1. Builder exits successfully and retains the 42-major/20-use-case assertions.
2. Generated diffs match approved source changes; no generated page was edited by hand.
3. All custom-domain canonicals are self-referential and all sitemap URLs use `www`.
4. Old Netlify references remain only in the intentional redirect rule and migration history.
5. No VideoObject is emitted unless a video is actually watchable on that page.
6. Any marked-up Q&A is visible and identical; preferably keep Q&A as HTML and remove low-value FAQPage JSON-LD.
7. SearchAction is absent; WebSite remains valid for site name.
8. Titles/descriptions are unique and readable on representative page types.
9. Live Vercel checks after deployment confirm status, headers, canonicals, and content.
10. Netlify root and representative paths return direct permanent redirects.
11. GSC URL Inspection confirms declared and Google-selected canonicals after recrawl.
12. OpenSEO audit is rerun and the prior 46 canonical conflicts are gone.

The sitemap currently changes every `<lastmod>` to the build date even when content is unchanged. Treat that as a known generator behavior during diff review and consider correcting it so `<lastmod>` represents actual modification.

## Reporting cadence

| Cadence | Report |
| --- | --- |
| Weekly for first 6 weeks | Redirect checks, GSC sitemap/coverage/canonical changes, old/new URL impressions, live meeting/join accuracy, critical errors. |
| Every two weeks for first 60 days | GSC striking-distance and query-page review; priority-major content decisions. |
| Monthly | Rank tracker, organic landing pages, branded/non-branded GSC performance, Skool click conversion, prompt-copy engagement, verified links, AI-answer prompt results. |
| Quarterly | Full technical crawl, content pruning/expansion, competitor SERP refresh, backlink review, AEO/entity fact audit, KPI and roadmap reset. |
| Each academic term | Meeting/event dates, officers, Skool destination, member-count display, organization profiles, and Event structured data. |

Every report must include the date range, comparison period, source, filters, and data limitations. Keep OpenSEO estimates, GSC first-party data, GA4 behavior, and manual AI-answer observations in separate sections.

## Approval sequence

Recommended approvals are deliberately staged:

1. Approve critical migration and GSC connection work.
2. Approve the reconciled structured-data source/generated diff plus the minimal-schema policy before deployment.
3. Approve join/resource page and Skool funnel changes.
4. Approve the four-page major pilot and campus outreach.
5. Approve the final rank-tracking keyword set and schedule after seeing the OpenSEO cost estimate.

This sequence follows Google's advice to avoid combining a domain move with unrelated large redesigns. It makes migration effects, content effects, and conversion effects separately measurable.
