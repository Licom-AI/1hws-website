#!/usr/bin/env python3
"""Static-site generator for the HWS AI Club site (SEO build).

Reads site/data.json + site/data/videos-config.json and emits crawlable,
SEO-optimized static HTML: homepage, majors index, 42 per-major pages, plus
robots.txt, sitemap.xml, _headers, og-image, and the runtime js/videos.js.

Run:  python3 scripts/build_site.py
"""
import collections
import hashlib
import html
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = json.loads((SITE / "data.json").read_text(encoding="utf-8"))
VCONF = json.loads((SITE / "data" / "videos-config.json").read_text(encoding="utf-8"))

# --- One place to change when moving to a custom domain -----------------------
BASE_URL = "https://www.hwsaiclub.com"
COLLEGE = "Hobart and William Smith Colleges"
LOCATION = "Geneva, New York"
MEETING = "Every Sunday, 5-6 PM · Sanford Room"
MEETING_START, MEETING_END, MEETING_TZ = "17:00", "18:00", "America/New_York"

# Schema.org Event needs a concrete startDate to validate; a recurring series needs
# real bounds. These are the first and last Sunday meetings of the current term and
# are deliberately hand-maintained rather than computed from date.today() — a
# computed "next Sunday" would change the generated HTML every week and break the
# build's no-diff idempotency guarantee. Update once per semester.
TERM_FIRST_MEETING = "2026-08-30"
TERM_LAST_MEETING = "2026-12-13"
MEETING_UTC_OFFSET = "-04:00"  # America/New_York during the fall term (EDT)

# Where else this club exists on the web. schema.org sameAs is how an answer engine
# connects this site to the organisation that HWS and the local press already write
# about — without it the site is an unlinked island. Add profiles as they appear.
ORG_SAME_AS = [
    "https://hws.campuslabs.com/engage/organization/aiclub",
    "https://www.skool.com/hws-ai-club-7506",
]

# GA4 property for this site. The custom events it receives (prompt_copied,
# tutorial_video_click, join_community_click, join_cta_click, library_cta_click)
# are fired from site/js/site.js — see docs/ANALYTICS.md for the full event
# taxonomy and which events are configured as GA4 conversions.
GA_MEASUREMENT_ID = "G-0S5QWRS2Q6"

# Loaded early in <head> so pageviews are never missed on a fast-loading static
# page — but after <meta charset>, which the HTML spec wants within the first
# 1024 bytes. content_group is computed from the
# URL rather than threaded through every head() call site, so it stays a
# one-line addition here instead of touching every page builder.
GA_SNIPPET = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{ dataLayer.push(arguments); }}
  gtag('js', new Date());
  gtag('config', '{GA_MEASUREMENT_ID}', {{
    content_group: (function () {{
      var p = location.pathname;
      if (p === '/') return 'home';
      if (p === '/majors/') return 'majors_index';
      if (p.indexOf('/majors/') === 0) return 'major_page';
      if (p === '/tasks/') return 'tasks_index';
      if (p.indexOf('/tasks/') === 0) return 'task_page';
      if (p.indexOf('/founders/') === 0) return 'founder_page';
      if (p === '/resources/ai-at-hws/') return 'ai_resources';
      if (p === '/faq/') return 'faq';
      if (p === '/ai-policy/') return 'ai_policy';
      return 'other';
    }})()
  }});
</script>"""
BUILD_DATE = date.today().isoformat()

# AI crawlers/agents worth naming explicitly in robots.txt. The wildcard rule
# already allows them implicitly, but explicit allow rules are cheap insurance
# in a fast-moving space where a platform's default posture can change.
AI_BOTS = [
    "GPTBot", "ChatGPT-User", "OAI-SearchBot",   # OpenAI
    "ClaudeBot", "anthropic-ai",                  # Anthropic
    "PerplexityBot", "Perplexity-User",           # Perplexity
    "Google-Extended",                            # Google AI (Gemini / AI Overviews)
    "Applebot-Extended",                          # Apple Intelligence
    "cohere-ai",                                  # Cohere
    "CCBot",                                      # Common Crawl (widely used for LLM training)
    "Amazonbot",                                  # Amazon / Alexa
    "meta-externalagent",                         # Meta AI
    "Bytespider",                                 # ByteDance / Doubao
    "YouBot",                                     # You.com
    "DuckAssistBot",                              # DuckDuckGo AI assist
]

# The club's community hub. SKOOL_MEMBERS is shown on the homepage as social
# proof — it goes stale, so update it when it drifts (it is not fetched live).
SKOOL_URL = "https://www.skool.com/hws-ai-club-7506"
SKOOL_MEMBERS = 41

TEAM = [
    ("CS", "Connor Shibley", "President", "Passionate about making AI accessible to everyone", "team-avatar-1"),
    ("AK", "Amanda Kronowitz", "Vice President", "Exploring AI tools for research and projects", "team-avatar-2"),
    ("JD", "Josh Doolan", "AI Strategist", "Orchestrating the future of human-AI collaboration", "team-avatar-3"),
    ("JP", "Josh Powell", "Club Officer", "Helping more students at HWS get started with AI", "team-avatar-1"),
]

# Organisations that appear in founders' link rows. Kept out of schema.org sameAs,
# which is for other profiles *of the person* — these map to worksFor / memberOf.
LICOM = ("Licom AI", "https://licom.ai/")
SUNDAI = ("Sundai", "https://www.sundai.club/")
ORG_URLS = {LICOM[1], SUNDAI[1]}

# Sourced from research/founders/ — see each subject's README for the full bio drafts
# and the open questions still to confirm before this copy is treated as final.
# Each entry also generates its own page at /founders/<slug>/.
FOUNDERS = [
    {
        "slug": "dominic-schimizzi",
        "initials": "DS",
        "name": "Dominic Schimizzi",
        "role": "Co-Founder",
        "avatar": "team-avatar-2",
        "blurb": "Graduated HWS &rsquo;26; now AI Implementor at Metro Development Group",
        "meta": (
            "Dominic Schimizzi co-founded the HWS AI Club at Hobart and William Smith Colleges and "
            "is a founder and CSO of Licom AI. Economics major, class of 2026, and a national "
            "champion with Hobart hockey."
        ),
        "subtitle": "Co-Founder, HWS AI Club &middot; Founder &amp; CSO, Licom AI",
        # Drives schema.org Person.worksFor. (org, url) — url may be None when the
        # organisation has no canonical page we've verified.
        "worksFor": [LICOM, ("Metro Development Group", None)],
        # Falls back to the initials avatar if the file is missing (build prints a warning).
        "photo": "/assets/founders/dominic-schimizzi.jpg",
        "bio": [
            "Dominic co-founded the HWS AI Club and is a founder and CSO of Licom AI, the AI "
            "consulting agency he started with Zack Hanna. He graduated from Hobart and William "
            "Smith in 2026 with a degree in Economics.",
            "He also played forward for Hobart hockey, winning a national championship in 2024&ndash;25 "
            "and earning a place on the SUNYAC Commissioner&rsquo;s Academic Honor Roll.",
            "Dominic is the club&rsquo;s loudest advocate for AI literacy. In his article "
            "&ldquo;The Dangerous Gap,&rdquo; he argues that universities fail students by treating AI "
            "as something to ban rather than a skill to teach &mdash; because students are already "
            "using it, just without guidance. He now works as an AI Implementor at Metro Development "
            "Group in Tampa, at the intersection of two things he cares about: artificial intelligence "
            "and real estate development.",
        ],
        "facts": [
            ("Major", "Economics, class of 2026"),
            ("Hometown", "Greensburg, Pennsylvania"),
            ("Company", f'<a href="{LICOM[1]}" target="_blank" rel="noopener">Licom AI</a> &mdash; Founder &amp; CSO'),
            ("Currently", "AI Implementor, Metro Development Group"),
            ("Athletics", "Hobart Ice Hockey &middot; 2024&ndash;25 National Champion"),
        ],
        "highlights": [
            "Co-founded the club in August 2025",
            "Wrote &ldquo;The Dangerous Gap,&rdquo; the club&rsquo;s clearest public argument for AI literacy",
            "Spoke on the CrossRealms podcast about AI literacy for new graduates",
            "Led club sessions on agentic AI and chaining tools together",
        ],
        "links": [
            LICOM,
            ("LinkedIn", "https://www.linkedin.com/in/dominic-schimizzi/"),
            ("Hobart Athletics profile", "https://hwsathletics.com/sports/mens-ice-hockey/roster/dominic-schimizzi/22634"),
        ],
        # The one song he wants to be remembered by. Confirmed via Spotify's oEmbed
        # + og:description on the track page (title/artist/album), not hand-typed.
        "song": {
            "title": "End of Line",
            "artist": "Daft Punk",
            "album": "TRON: Legacy (Original Motion Picture Soundtrack)",
            "spotify_track_id": "09TlxralXOGX35LUutvw7I",
        },
    },
    {
        "slug": "zackary-hanna",
        "initials": "ZH",
        "name": "Zackary Hanna",
        "role": "Co-Founder",
        "avatar": "team-avatar-1",
        "blurb": "Transferred to Northeastern; building at Enlaye, a startup in the Harvard Innovation Labs",
        "meta": (
            "Zackary Hanna co-founded the HWS AI Club at Hobart and William Smith Colleges and is "
            "the founder and CEO of Licom AI, a B2B AI consulting and implementation agency. He "
            "studies at Northeastern University and sits on the board of Sundai."
        ),
        "subtitle": "Co-Founder, HWS AI Club &middot; Founder &amp; CEO, Licom AI",
        "worksFor": [LICOM, ("Enlaye", None)],
        "bio": [
            "Zack co-founded the HWS AI Club in August 2025 and is the founder and CEO of Licom AI, "
            "a B2B AI consulting and implementation agency he started from his dorm room and grew to "
            "a team of six. His client work spans full ERP platforms, logistics optimization, and AI "
            "voice agents.",
            "He now studies at Northeastern University. He co-founded the club while at Hobart and "
            "William Smith, where he held a Trustee Scholarship and sat on the Investment Club board, "
            "and in summer 2026 he joined Enlaye &mdash; an AI-native construction risk platform out "
            "of the Harvard Innovation Labs &mdash; as the only undergraduate on an all-Harvard team.",
            "He also sits on the board of Sundai, the Boston community out of MIT and Harvard that "
            "builds and launches AI prototypes every Sunday.",
            "His view, and the reason the club exists: the gap isn&rsquo;t knowledge, it&rsquo;s "
            "implementation. Most people know AI matters. Far fewer can make it work inside the way "
            "they actually study or run a business.",
        ],
        "school": ("Northeastern University", "https://www.northeastern.edu/"),
        "memberOf": SUNDAI,
        # Falls back to the initials avatar if the file is missing (build prints a warning).
        "photo": "/assets/founders/zackary-hanna.jpg",
        "facts": [
            ("Studying", "Northeastern University"),
            ("Hometown", "Huntington Beach, California"),
            ("Company", f'<a href="{LICOM[1]}" target="_blank" rel="noopener">Licom AI</a> &mdash; Founder &amp; CEO'),
            ("Board", f'<a href="{SUNDAI[1]}" target="_blank" rel="noopener">Sundai</a>'),
            ("Previously", "Hobart and William Smith Colleges"),
        ],
        "highlights": [
            "Co-founded the club in August 2025",
            "Built the club&rsquo;s AI curriculum and ran hands-on workshops",
            "Demoed OpenClaw &mdash; a personal agent wired into his Mac mini and driven over WhatsApp",
            "Brought in guest speakers, including Lee Jokl, AI strategy lead at T. Rowe Price and Unanet",
        ],
        "links": [
            LICOM,
            SUNDAI,
            ("Personal site", "https://www.zackhanna.com/"),
            ("LinkedIn", "https://www.linkedin.com/in/zackary-hanna-515138331/"),
        ],
        # The one song he wants to be remembered by. Title/artist confirmed via
        # Spotify's embed payload for this exact track id. "album" is optional and
        # deliberately omitted here — the caption renders without it.
        "song": {
            "title": "All The Vilest Things",
            "artist": "Marilyn Manson",
            "spotify_track_id": "3JoqnjCO80olWZrRNhBqVq",
        },
        "extra_photo": {
            "src": "/assets/founders/zackary-hanna-speaking.jpg",
            "width": 1440,
            "height": 1080,
            "alt": "Zackary Hanna speaking at an HWS AI Club session",
        },
    },
]

# Divisions, used for related-major linking and for grouping the /majors/ index.
#
# Every major page used to link all 41 others in one undifferentiated run, which
# told a crawler that Anthropology relates to Physics exactly as strongly as it
# relates to Anthropology & Sociology. Grouping gives the internal link graph a
# topical shape and stops each page spraying its authority 41 ways.
#
# Roughly HWS's own divisional structure; a major listed here must exist in
# data.json, and every major must appear exactly once (asserted at build time).
DIVISIONS = [
    ("Natural Sciences & Mathematics", [
        "biochemistry", "biology", "chemistry", "computer-science", "environmental-science",
        "geoscience", "mathematics", "physics", "psychological-science",
    ]),
    ("Social Sciences", [
        "anthropology", "anthropology-sociology", "economics", "educational-studies",
        "environmental-studies", "international-relations", "politics", "public-health-studies",
        "sociology", "business-management-and-entrepreneurship",
    ]),
    ("Humanities", [
        "classics", "english-and-creative-writing", "french-and-francophone-studies",
        "greek-and-roman-studies", "history", "philosophy", "religious-studies",
        "spanish-and-hispanic-studies", "writing-and-rhetoric",
    ]),
    ("Arts & Media", [
        "architectural-studies", "art-art-history", "art-studio-art", "dance",
        "media-society", "music", "theatre",
    ]),
    ("Interdisciplinary Studies", [
        "africana-studies", "american-studies", "asian-studies",
        "bodies-disability-and-justice", "gender-and-feminist-studies", "lgbtq-studies",
        "individual-major",
    ]),
]
DIVISION_OF = {slug: label for label, slugs in DIVISIONS for slug in slugs}

# Task hubs — the cross-cutting view of the same 840 use cases.
#
# The library is organised by major, but students search by task ("how do I use
# AI to summarize a reading"), not by department. These pages group every use
# case that shares a task archetype, across all 42 majors, which turns 840 rows
# that only existed inside 42 pages into a second, genuinely different set of
# landing pages — and gives major pages deep inbound links with descriptive
# anchor text instead of bare major names.
#
# `arch` must be a key produced by classify(). Archetypes below ~20 use cases are
# deliberately left out: a hub with six entries is a thin page, and "general" is
# a fallback bucket, not something anyone searches for.
TASK_HUBS = [
    {"arch": "explain", "slug": "explain-a-concept", "label": "Explain a concept",
     "h1": "Using AI to Explain Concepts You're Stuck On",
     "gerund": "explaining a concept",
     "blurb": "Turning something you half-understand into something you could teach back."},
    {"arch": "code", "slug": "write-and-debug-code", "label": "Write and debug code",
     "h1": "Using AI to Write and Debug Code",
     "gerund": "writing or debugging code",
     "blurb": "Getting a script working, and understanding why it broke in the first place."},
    {"arch": "compare", "slug": "compare-two-things", "label": "Compare two things",
     "h1": "Using AI to Compare Two Ideas, Texts, or Methods",
     "gerund": "comparing two things",
     "blurb": "Laying two things side by side and finding the difference that actually matters."},
    {"arch": "researchdesign", "slug": "design-a-study", "label": "Design a study",
     "h1": "Using AI to Design a Study or Research Project",
     "gerund": "designing a study",
     "blurb": "Pressure-testing a research design before you commit a semester to it."},
    {"arch": "summarize", "slug": "summarize-a-reading", "label": "Summarize a reading",
     "h1": "Using AI to Summarize Readings, Papers, and Lectures",
     "gerund": "summarizing a reading",
     "blurb": "Compressing something long into the parts you actually need."},
    {"arch": "brainstorm", "slug": "brainstorm-ideas", "label": "Brainstorm ideas",
     "h1": "Using AI to Brainstorm Topics and Angles",
     "gerund": "brainstorming ideas",
     "blurb": "Getting unstuck on what to write about, argue, or investigate."},
    {"arch": "studymode", "slug": "study-for-an-exam", "label": "Study for an exam",
     "h1": "Using AI to Study for Exams and Quizzes",
     "gerund": "studying for an exam",
     "blurb": "Being drilled on the material instead of handed the answers."},
    {"arch": "email", "slug": "draft-an-email", "label": "Draft an email",
     "h1": "Using AI to Draft Emails to Professors and Colleagues",
     "gerund": "drafting an email",
     "blurb": "Writing the awkward email you have been putting off for three days."},
    {"arch": "data", "slug": "analyze-data", "label": "Analyze data",
     "h1": "Using AI to Analyze and Interpret Data",
     "gerund": "analyzing data",
     "blurb": "Reading a dataset, a table, or a result you are not sure how to interpret."},
    {"arch": "customgpt", "slug": "build-a-custom-gpt", "label": "Build a custom GPT",
     "h1": "Using AI to Build a Custom GPT or Assistant",
     "gerund": "building a custom assistant",
     "blurb": "Setting up a reusable tool instead of retyping the same prompt every week."},
    {"arch": "litreview", "slug": "review-the-literature", "label": "Review the literature",
     "h1": "Using AI for Literature Reviews and Source Synthesis",
     "gerund": "reviewing the literature",
     "blurb": "Mapping what has already been said before you add to it."},
    {"arch": "studyplan", "slug": "make-a-study-plan", "label": "Make a study plan",
     "h1": "Using AI to Build a Study Plan That Holds",
     "gerund": "making a study plan",
     "blurb": "Turning a syllabus and a deadline into a week-by-week plan."},
    {"arch": "projectplan", "slug": "plan-a-project", "label": "Plan a project",
     "h1": "Using AI to Plan a Semester-Long Project",
     "gerund": "planning a project",
     "blurb": "Breaking something large into steps with dates attached."},
    {"arch": "outline", "slug": "outline-a-paper", "label": "Outline a paper",
     "h1": "Using AI to Outline a Paper or Presentation",
     "gerund": "outlining a paper",
     "blurb": "Getting the shape of an argument down before writing a word of it."},
    {"arch": "essay", "slug": "write-an-essay", "label": "Write an essay",
     "h1": "Using AI to Draft an Essay Without Outsourcing the Thinking",
     "gerund": "drafting an essay",
     "blurb": "Automating the typing while the argument stays yours."},
]


# ---------------------------------------------------------------------------
# Video resolution — mirrors js/videos.js (cross-checked by the verify step)
# ---------------------------------------------------------------------------
_RULES = [(k, re.compile(p, re.I)) for k, p in VCONF["rules"]]
_LEAD = VCONF["leadVerb"]
_SKILL = VCONF["skill"]
_OVERRIDES = VCONF["overrides"]
_VMETA = VCONF.get("videoMeta", {})
_VTEACH = VCONF.get("videoTeaches", {})
_PROMPTS = VCONF.get("promptPatterns", {})
_MAJOR_NAME = {m["slug"]: m["name"] for m in DATA["majors"]}


_ID_TO_ARCH = {v["id"]: k for k, v in _SKILL.items()}
# Override videos that aren't a skill archetype still imply a task type.
_EXTRA_ARCH = {
    "8qWtU51lxpM": "data", "A3WKdt_MNZQ": "code", "ADUrUGQgksY": "code",
    "-c5WEn18IeE": "code", "_4-pggUACz0": "code", "STJuR1zH8Ck": "general",
    "WVAbJbO2CgI": "language", "RDVUioXNMIk": "language",
}


def prompt_archetype(slug, uc):
    """Task type for the prompt. Honours overrides: if a card was hand-routed to
    (say) the image-analysis video, its task really is image analysis, so the
    prompt must match that — not whatever the title's keywords imply."""
    key = slug + "/" + str(uc["number"])
    if key in _OVERRIDES:
        vid = _OVERRIDES[key]
        arch = _ID_TO_ARCH.get(vid) or _EXTRA_ARCH.get(vid)
        if arch:
            return arch
    return classify(uc["title"], uc["description"])


def starter_prompt(slug, uc):
    """A ready-to-paste prompt tailored to this exact use case.

    Composed from the card's own title/description/major plus a per-archetype
    instruction pattern, so it stays specific without hand-writing 840 strings.
    Keyed on the *task* archetype (classify), not the video, because the prompt
    describes what the student is doing — not what the tutorial shows.
    """
    arch = prompt_archetype(slug, uc)
    instructions = _PROMPTS.get(arch) or _PROMPTS.get("general", "")
    major = _MAJOR_NAME.get(slug, "college")
    art = "an" if major[:1].upper() in "AEIOU" else "a"
    task = uc["title"].rstrip(". ")
    detail = uc["description"].rstrip(". ")
    # The closing line is a genuine prompt improvement — grounding a model in the
    # field it is answering for measurably sharpens terminology and examples — and
    # it also means the shared instruction block is no longer the last thing on
    # the page, so no two majors' prompts read identically end to end.
    grounding = (f"Keep the terminology, examples, and level of detail appropriate for an "
                 f"undergraduate {major} course.")
    return (f"I'm {art} {major} student at HWS. My task: {task} — {detail}.\n\n"
            f"{instructions}\n\n{grounding}")


def card_text(slug, uc):
    """Compose honest card copy: the task, what the linked video actually teaches,
    and what the student walks away with. Keeps site/data.json canonical — swap a
    video in videos-config.json and every card using it re-describes itself.

    The method/takeaway strings come from videoTeaches, which has 38 entries
    serving all 840 use cases — so each one was previously reproduced verbatim on
    roughly 22 cards, and every one of those sentences appeared identically on all
    42 major pages. Both are now composed with the major woven into the same
    sentence rather than appended as a new one, which is what a duplicate-content
    check actually measures.
    """
    t = _VTEACH.get(video_id(slug, uc), {})
    major = _MAJOR_NAME.get(slug, "your major")
    desc = uc["description"].rstrip(". ")
    method, takeaway = t.get("method"), t.get("takeaway")
    if method:
        desc = (f"{desc}. The linked tutorial covers {method}, and the starter prompt "
                f"below already frames it for {major}.")
    else:
        desc = f"{desc}."
    if takeaway:
        tail = TAKEAWAY_TAIL.get(uc["difficulty"], "").format(major=major)
        nxt = f"{takeaway.rstrip('. ')} — {tail}" if tail else takeaway
    else:
        nxt = NEXT_STEPS.get(uc["difficulty"], "")
    return desc, nxt


def _join_titles(titles):
    """'A', 'B' and 'C' — for prose answers, not lists."""
    titles = [t.rstrip(". ").lower() for t in titles]
    if len(titles) <= 1:
        return titles[0] if titles else ""
    return ", ".join(titles[:-1]) + " and " + titles[-1]


def major_faq(slug, m):
    """Genuine question/answer pairs for one major, composed from its own data.

    This replaces the previous behaviour of marking up all 20 use-case titles as
    schema.org Question entities. A title like "Explain natural selection to a
    peer" is an imperative task, not a question, and Google requires FAQPage
    markup to be real Q&A that is *visible on the page* — the old markup was
    neither, and duplicated the ItemList on the same page besides.

    Every answer here is built from values unique to this major (its difficulty
    split, its own use-case titles, the tutorials it actually links), so the 42
    pages stay distinct instead of converging on shared boilerplate.
    """
    name = m["name"]
    ucs = m["useCases"]
    by_diff = {d: [u for u in ucs if u["difficulty"] == d] for d in ("Easy", "Medium", "Hard")}
    easy = [u["title"] for u in by_diff["Easy"][:3]]
    mixed = [u["title"] for u in (by_diff["Medium"] or by_diff["Easy"])[:2]]
    hardest = (by_diff["Hard"] or by_diff["Medium"] or ucs)[-1]["title"]
    split = ", ".join(f"{len(by_diff[d])} {d.lower()}" for d in ("Easy", "Medium", "Hard") if by_diff[d])
    n_videos = len({video_id(slug, uc) for uc in ucs})

    return [
        (
            f"How can {name} students use AI at HWS?",
            f"This page lists {len(ucs)} practical AI use cases written specifically for {name} "
            f"students at {COLLEGE} — {split} by difficulty. They range from everyday coursework "
            f"help such as {_join_titles(easy[:2])} through to project-scale work like "
            f"{hardest.rstrip('. ').lower()}. Each one comes with a starter prompt you can paste "
            f"straight into ChatGPT, Claude, or Gemini.",
        ),
        (
            f"Which AI use cases should a {name} major try first?",
            f"Start with the {len(by_diff['Easy'])} rated Easy — they need no setup and work on the "
            f"first try. For {name} that means {_join_titles(easy)}. Once those feel routine, move "
            f"up to the Medium tier, which includes {_join_titles(mixed)}.",
        ),
        (
            f"What do I need to start using AI as a {name} student?",
            f"A free account with ChatGPT, Claude, or Gemini is the whole list — no coding, no paid "
            f"subscription, and nothing to install. The {len(ucs)} {name} use cases here draw on "
            f"{n_videos} tutorial videos between them, and each card ships with a starter prompt "
            f"already framed for {name} coursework, so the first thing you do is paste, not write.",
        ),
        (
            f"Is it OK to use AI for {name} coursework at HWS?",
            f"Your {name} professor decides, and the answer changes from course to course and even "
            f"between assignments — so read the syllabus before any of this touches graded work. "
            f"Everything on this page is a study aid: a use case like \"{hardest.rstrip('. ')}\" "
            f"exists to get you through {name} material faster, not to produce something you submit "
            f"as your own. If the syllabus is silent, ask before you use it.",
        ),
    ]


def faq_items_html(pairs, indent="    "):
    """Visible Q&A content for readers and answer engines."""
    return "\n".join(
        f'{indent}<div class="faq-item">\n'
        f'{indent}  <h3 class="faq-q">{esc(q)}</h3>\n'
        f'{indent}  <p class="faq-a">{esc(a)}</p>\n'
        f'{indent}</div>'
        for q, a in pairs
    )


def faq_html(pairs, heading, heading_id="faq"):
    """A whole FAQ section, for inner pages that aren't built from lp-section."""
    return (
        f'  <section class="faq-section" id="{heading_id}">\n'
        f'    <h2>{esc(heading)}</h2>\n'
        f'    <div class="faq-list">\n'
        f'{faq_items_html(pairs, "      ")}\n'
        f'    </div>\n'
        f'  </section>'
    )


def classify(title, description):
    lead = (title or "").strip().split()[0].lower() if (title or "").strip() else ""
    if lead in _LEAD:
        return _LEAD[lead]
    text = ((title or "") + " " + (description or "")).lower()
    for key, rx in _RULES:
        if rx.search(text):
            return key
    return "general"


def video_id(slug, uc):
    key = slug + "/" + str(uc["number"])
    if key in _OVERRIDES:
        return _OVERRIDES[key]
    cls = classify(uc["title"], uc["description"])
    return (_SKILL.get(cls) or _SKILL["general"])["id"]


def video_url(slug, uc):
    return "https://www.youtube.com/watch?v=" + video_id(slug, uc)


NEXT_STEPS = {
    "Easy": "Just open ChatGPT, Claude, or Gemini and try it now.",
    "Medium": "Try it yourself, then double-check the output against your course material or notes.",
    "Hard": "Attempt it, then review the result with a professor or TA before relying on it.",
}

# Closes the "what you'll take away" line. Escalates with difficulty exactly as
# NEXT_STEPS does, and names the major, so the sentence differs across pages
# instead of repeating one of 38 shared strings on all 42 of them.
TAKEAWAY_TAIL = {
    "Easy": "enough to use on {major} work this week.",
    "Medium": "worth checking against your {major} course material before you lean on it.",
    "Hard": "bring the result to a {major} professor or TA before it goes near graded work.",
}
BADGE_CLASS = {"Easy": "badge-easy", "Medium": "badge-medium", "Hard": "badge-hard"}

BRAIN_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>'
    '<path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>'
    '<path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/></svg>'
)
ICONS = {
    "tools": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 4V2m0 20v-2m5-5h2M2 15h2m13.657-8.657 1.414-1.414M4.929 19.071l1.414-1.414m0-11.314L4.93 4.929m14.142 14.142-1.414-1.414"/><circle cx="15" cy="15" r="3"/></svg>',
    "book": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    "rocket": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>',
}


def esc(s):
    return html.escape(str(s), quote=True)


# ---------------------------------------------------------------------------
# Shared chrome
# ---------------------------------------------------------------------------
def head(title, description, canonical_path, jsonld):
    canonical = BASE_URL + canonical_path
    blocks = "\n".join(
        '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"
        for obj in jsonld
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{GA_SNIPPET}
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="author" content="HWS AI Club">
<meta property="og:type" content="website">
<meta property="og:site_name" content="HWS AI Club">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{BASE_URL}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{BASE_URL}/og-image.png">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/styles.css">
{blocks}
</head>"""


def site_header():
    return f"""<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header">
  <div class="site-header-inner">
    <a class="wordmark" href="/">
      <span class="logo-tile" aria-hidden="true">{BRAIN_SVG}</span>
      <span class="wordmark-name">AI @ HWS</span>
    </a>
    <nav class="site-nav" aria-label="Primary">
      <a href="/#about">About</a>
      <a href="/majors/">By Major</a>
      <a href="/tasks/">By Task</a>
      <a href="/resources/ai-at-hws/">Resources</a>
      <a href="/faq/">FAQ</a>
      <a href="/#founders">Meet The Founders</a>
      <a class="nav-cta" href="{SKOOL_URL}" target="_blank" rel="noopener" data-cta="skool-join">Join Us</a>
    </nav>
  </div>
</header>"""


def site_footer():
    return f"""<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <span class="logo-tile logo-tile-sm" aria-hidden="true">{BRAIN_SVG}</span>
      <div>
        <p class="footer-title">HWS AI Club</p>
        <p class="footer-tagline">AI for Everyone at {COLLEGE}</p>
      </div>
    </div>
    <nav class="footer-nav" aria-label="Footer">
      <a href="/#about">About</a>
      <a href="/#join">Events</a>
      <a href="/#team">Team</a>
      <a href="/majors/">By Major</a>
      <a href="/tasks/">By Task</a>
      <a href="/resources/ai-at-hws/">Resources</a>
      <a href="/faq/">FAQ</a>
      <a href="/ai-policy/">AI &amp; Coursework</a>
      <a href="/#community">Community</a>
      <a href="/#founders">Meet The Founders</a>
    </nav>
    <div class="footer-legal">
      <p class="footer-integrity"><strong>Check your course policy first.</strong> AI rules differ by class and
      professor &mdash; confirm what&rsquo;s allowed before using any of these on graded work.</p>
      <p>&copy; {date.today().year} HWS AI Club. A student organization at {COLLEGE} in {LOCATION}.
      Tutorial videos are third-party content and are not affiliated with or endorsed by {COLLEGE}.</p>
      <p>Making AI accessible to the HWS community</p>
    </div>
  </div>
</footer>"""


def scripts():
    return '<script src="/js/site.js" defer></script>'


# Stable @id anchors. Every JSON-LD node the site emits more than once refers to
# the same URI, so crawlers merge them into one entity instead of reading a dozen
# unrelated organisations that happen to share a name.
ORG_ID = BASE_URL + "/#organization"
WEBSITE_ID = BASE_URL + "/#website"

ORG_JSONLD = {
    "@context": "https://schema.org",
    "@type": "EducationalOrganization",
    "@id": ORG_ID,
    "name": "HWS AI Club",
    "alternateName": ["Hobart and William Smith AI Club", "AI @ HWS", "HWS Artificial Intelligence Club"],
    "url": BASE_URL + "/",
    # Must be raster: Google's logo parser rejects SVG. build_favicons() writes this.
    "logo": {"@type": "ImageObject", "url": BASE_URL + "/assets/logo-512.png", "width": 512, "height": 512},
    "image": BASE_URL + "/og-image.png",
    "sameAs": ORG_SAME_AS,
    "description": f"Student-run AI literacy club at {COLLEGE} helping every major learn to use AI well.",
    "location": {
        "@type": "Place",
        "name": COLLEGE,
        "address": {"@type": "PostalAddress", "addressLocality": "Geneva", "addressRegion": "NY", "addressCountry": "US"},
    },
    "areaServed": COLLEGE,
}

EVENT_JSONLD = {
    "@context": "https://schema.org",
    "@type": "Event",
    "@id": BASE_URL + "/#weekly-meeting",
    "name": "HWS AI Club Weekly Meeting",
    "description": "Beginner-friendly weekly AI workshop and meeting for HWS AI Club, open to all majors and class years — no experience required.",
    # startDate/endDate are required for validation; the Schedule below carries the
    # recurrence. Both bound the current term — see TERM_FIRST_MEETING.
    "startDate": f"{TERM_FIRST_MEETING}T{MEETING_START}:00{MEETING_UTC_OFFSET}",
    "endDate": f"{TERM_FIRST_MEETING}T{MEETING_END}:00{MEETING_UTC_OFFSET}",
    "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
    "eventStatus": "https://schema.org/EventScheduled",
    "isAccessibleForFree": True,
    "location": {
        "@type": "Place",
        "name": "Sanford Room, " + COLLEGE,
        "address": {"@type": "PostalAddress", "addressLocality": "Geneva", "addressRegion": "NY", "addressCountry": "US"},
    },
    "organizer": {"@id": ORG_ID},
    "eventSchedule": {
        "@type": "Schedule",
        "repeatFrequency": "P1W",
        "byDay": "https://schema.org/Sunday",
        "startDate": TERM_FIRST_MEETING,
        "endDate": TERM_LAST_MEETING,
        "startTime": MEETING_START,
        "endTime": MEETING_END,
        "scheduleTimezone": MEETING_TZ,
    },
}


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------
# Feeds visible questions on the homepage and the first seven entries of /faq/.
# These are deliberately HTML-only: FAQ rich results are not available to normal
# organizations, and answer quality comes from clear, maintainable copy instead.
HOME_FAQ = [
    ("What is the HWS AI Club?",
     f"HWS AI Club is a student-run organization at {COLLEGE} that helps students of every major learn to use AI tools well, with hands-on workshops and a library of 840 AI use cases across all 42 majors."),
    ("Do I need coding experience to join?",
     "No. The club is beginner-friendly and requires no coding or prior AI experience — just curiosity."),
    ("When and where does the HWS AI Club meet?",
     f"The club meets {MEETING} at {COLLEGE}. All majors and class years are welcome."),
    ("Is the HWS AI Club free to join?",
     "Yes. The club is completely free, with no application required — just show up to a meeting."),
    ("What majors can join the HWS AI Club?",
     f"All 42 majors offered at {COLLEGE}. The club's use-case library has 20 AI use cases tailored to each individual major."),
    ("Do I need a laptop or special software to join?",
     "No special software — just a free account with a tool like ChatGPT, Claude, or Gemini. Bringing a laptop helps, but it isn't required."),
    ("How do I join the HWS AI Club's online community?",
     f"Through the club's free Skool community at {SKOOL_URL}, which is open to every HWS student for classroom material, discussion, and the events calendar."),
]


def team_cards():
    out = []
    for initials, name, role, bio, avclass in TEAM:
        out.append(
            f'<article class="card team-card"><span class="team-avatar {avclass}" aria-hidden="true">{initials}</span>'
            f"<h3>{esc(name)}</h3><p class=\"team-role\">{esc(role)}</p><p class=\"team-bio\">{esc(bio)}</p></article>"
        )
    return "\n".join(out)


_PHOTO_WARNED = set()


def founder_photo(f):
    """Path to the founder's photo, or None if it isn't on disk yet. Warns once."""
    if not f.get("photo"):
        return None
    if (SITE / f["photo"].lstrip("/")).exists():
        return f["photo"]
    if f["slug"] not in _PHOTO_WARNED:
        _PHOTO_WARNED.add(f["slug"])
        print(f"  ! {f['name']}: no photo at site{f['photo']} - using initials avatar")
    return None


def founder_avatar(f, extra_class="", eager=False):
    """Photo if one exists, else the initials tile. Same shape either way.

    eager=True is for the founder-page hero, which is the LCP element on that
    page — lazy-loading it defers the largest paint behind the rest of the page.
    Everywhere else the avatar is below the fold and stays lazy."""
    cls = f"team-avatar {extra_class} {f['avatar']}".strip()
    photo = founder_photo(f)
    if photo:
        loading = ('loading="eager" fetchpriority="high"' if eager
                   else 'loading="lazy" fetchpriority="auto"')
        return (f'<img class="{cls} founder-photo" src="{photo}" alt="{esc(f["name"])}" '
                f'width="256" height="256" {loading} decoding="async">')
    return f'<span class="{cls}" aria-hidden="true">{f["initials"]}</span>'


def founder_cards():
    """Founder cards link through to their own page. Hand-authored copy in FOUNDERS
    carries intentional HTML entities, so blurb/subtitle are emitted unescaped."""
    out = []
    for f in FOUNDERS:
        out.append(
            f'<a class="card team-card founder-card" href="/founders/{f["slug"]}/" '
            f'data-cta="founder-card" data-founder="{f["slug"]}">'
            f'{founder_avatar(f)}'
            f'<h3>{esc(f["name"])}</h3>'
            f'<p class="team-role">{esc(f["role"])}</p>'
            f'<p class="team-bio">{f["blurb"]}</p>'
            f'<span class="founder-more">Read more <span aria-hidden="true">&rarr;</span></span></a>'
        )
    return "\n".join(out)


def build_home():
    title = "HWS AI Club | AI Workshops and Resources for HWS Students"
    desc = ("Free, student-run AI workshops and 840 practical use cases for HWS students in every major. "
            "No coding experience required; join the Skool community.")
    faq_pairs = HOME_FAQ

    # The homepage previously linked to zero major pages — every one of the 42 was
    # two clicks deep behind /majors/, and five of the six nav items were homepage
    # fragments, so the homepage absorbed nearly all internal link equity and
    # passed almost none of it on. One representative major per division, plus the
    # task hubs, gives the crawler a real path down into the site.
    home_major_links = " · ".join(
        f'<a href="/majors/{s}/">{esc(_MAJOR_NAME[s])}</a>'
        for s in (slugs[0] for _, slugs in DIVISIONS) if s in _MAJOR_NAME
    )
    home_task_links = " · ".join(
        f'<a href="/tasks/{h["slug"]}/">{esc(h["label"])}</a>' for h in TASK_HUBS[:8]
    )
    faq_home_html = faq_items_html(faq_pairs, "        ")
    website = {"@context": "https://schema.org", "@type": "WebSite",
               "@id": WEBSITE_ID,
               "name": "HWS AI Club",
               "alternateName": "AI @ HWS",
               "url": BASE_URL + "/",
               "publisher": {"@id": ORG_ID}}

    body = f"""<body class="view-home">
{site_header()}
<main id="main">
  <section class="lp-hero">
    <div class="hero-blob hero-blob-1" aria-hidden="true"></div>
    <div class="hero-blob hero-blob-2" aria-hidden="true"></div>
    <div class="hero-blob hero-blob-3" aria-hidden="true"></div>
    <div class="hero-tile" aria-hidden="true">{BRAIN_SVG}</div>
    <div class="section-inner">
      <h1 class="hero-title">AI for Everyone at Hobart and William Smith</h1>
      <p class="hero-sub">The student-run AI club at {COLLEGE} (HWS). Learn practical AI skills to excel as a student and future professional &mdash; no coding required.</p>
      <div class="hero-actions">
        <a class="btn-primary" href="{SKOOL_URL}" target="_blank" rel="noopener" data-cta="skool-join">Join the Club <span aria-hidden="true">&#8599;</span></a>
        <a class="btn-secondary" href="/majors/" data-cta="hero-browse">Browse Use Cases</a>
      </div>
      <p class="hero-meeting">{MEETING}</p>
    </div>
  </section>

  <section class="lp-section" id="about">
    <div class="section-inner">
      <h2 class="section-title">What We Do</h2>
      <p class="section-sub">We make AI accessible and practical for every student at Hobart and William Smith Colleges</p>
      <p class="wwd-definition"><strong>HWS AI Club</strong> is a free, student-run AI literacy club at {COLLEGE} in {LOCATION}, open to students in all 42 majors. The club teaches practical, no-code AI skills through weekly workshops and a library of 840 major-specific AI use cases.</p>
      <div class="wwd-grid">
        <article class="card"><span class="icon-tile" aria-hidden="true">{ICONS['tools']}</span><h3>AI Tools Mastery</h3><p>Learn ChatGPT, Claude, Gemini, Midjourney, and cutting-edge AI tools that are transforming how we work and create.</p></article>
        <article class="card"><span class="icon-tile" aria-hidden="true">{ICONS['book']}</span><h3>Smarter Studying</h3><p>AI-powered research, writing, and learning techniques to help you excel in your HWS coursework.</p></article>
        <article class="card"><span class="icon-tile" aria-hidden="true">{ICONS['rocket']}</span><h3>Career Ready</h3><p>Use AI to boost productivity and stand out professionally in the modern job market.</p></article>
      </div>
      <p class="wwd-summary">In short: come with zero AI experience, leave knowing how to use ChatGPT, Claude, and Gemini for your specific major &mdash; every Sunday, free.</p>
    </div>
  </section>

  <section class="lp-section">
    <div class="section-inner split">
      <div>
        <h2>No Experience Needed</h2>
        <p class="split-lede">Whether you&rsquo;re completely new to AI or already experimenting with tools, our club is designed to meet you where you are.</p>
        <ul class="check-list">
          <li><span class="check-dot" aria-hidden="true">&#10003;</span>Beginner-friendly workshops every week</li>
          <li><span class="check-dot" aria-hidden="true">&#10003;</span>Hands-on practice with real AI tools</li>
          <li><span class="check-dot" aria-hidden="true">&#10003;</span>Connect with fellow HWS students exploring AI</li>
          <li><span class="check-dot" aria-hidden="true">&#10003;</span>Guest speakers from the tech industry</li>
          <li><span class="check-dot" aria-hidden="true">&#10003;</span>Build a portfolio of AI-enhanced projects</li>
        </ul>
        <a class="btn-primary" href="{SKOOL_URL}" target="_blank" rel="noopener" data-cta="skool-join">Get Started Today <span aria-hidden="true">&#8599;</span></a>
      </div>
      <div class="tile-stack">
        <div class="photo-tile">Workshop Session</div>
        <div class="photo-tile">AI Tools Demo</div>
        <div class="photo-tile">Team Projects</div>
      </div>
    </div>
  </section>

  <section class="lp-section lp-library" id="library">
    <div class="section-inner">
      <h2 class="section-title">The Use-Case Library</h2>
      <p class="section-sub">Real AI use cases for your exact major at HWS &mdash; rated by difficulty, each naming the exact tutorial it links to and what you&rsquo;ll take away.</p>
      <div class="library-stats">
        <div class="library-stat"><strong>42</strong><span>Majors covered</span></div>
        <div class="library-stat"><strong>840</strong><span>Use cases</span></div>
        <div class="library-stat"><strong>3</strong><span>Difficulty levels</span></div>
      </div>
      <div class="home-major-links">
        <p class="home-major-lead">Jump straight in:</p>
        <p class="siblings">{home_major_links}</p>
      </div>
      <div class="library-cta"><a class="btn-primary" href="/majors/" data-cta="library-browse">Find your major &rarr;</a></div>
    </div>
  </section>

  <section class="lp-section lp-tasks">
    <div class="section-inner">
      <h2 class="section-title">Or start from what you need to do</h2>
      <p class="section-sub">The same 840 use cases, grouped by task instead of by department &mdash; because most people arrive with a problem, not a major.</p>
      <p class="siblings">{home_task_links}</p>
      <div class="library-cta"><a class="btn-secondary" href="/tasks/">Browse all {len(TASK_HUBS)} tasks &rarr;</a></div>
    </div>
  </section>

  <section class="lp-section" id="team">
    <div class="section-inner">
      <h2 class="section-title">Meet the Team</h2>
      <p class="section-sub">HWS students passionate about making AI accessible to everyone</p>
      <div class="team-grid">
{team_cards()}
      </div>
    </div>
  </section>

  <section class="lp-section lp-join" id="join">
    <div class="section-inner">
      <h2 class="section-title">Ready to Join?</h2>
      <p class="join-sub">No experience, no application &mdash; just show up. Open to all majors and class years at {COLLEGE}.</p>
      <p class="join-meeting">{MEETING}</p>
      <a class="btn-primary" href="{SKOOL_URL}" target="_blank" rel="noopener" data-cta="skool-join">Join the Skool community <span aria-hidden="true">&#8599;</span></a>
      <a class="btn-secondary" href="/majors/" data-cta="join-section-majors">Start with your major&rsquo;s use cases &rarr;</a>
    </div>
  </section>

  <section class="lp-section lp-skool" id="community">
    <div class="section-inner">
      <h2 class="section-title">Join the Community</h2>
      <p class="section-sub">The club&rsquo;s hub lives on Skool &mdash; the official community for learning material and club activities, all in one place.</p>
      <figure class="skool-photo">
        <img src="/assets/community/club-session.jpg" width="1280" height="1280" loading="lazy" decoding="async"
             alt="HWS AI Club members at a weekly meeting">
      </figure>
      <div class="wwd-grid skool-grid">
        <article class="card"><span class="icon-tile" aria-hidden="true">{ICONS['book']}</span><h3>Classroom &amp; learning material</h3><p>Video walkthroughs and course material covering AI fundamentals, Claude API, MCP, and building AI agents with Make.com.</p></article>
        <article class="card"><span class="icon-tile" aria-hidden="true">{ICONS['tools']}</span><h3>Workshops &amp; discussion</h3><p>Ask questions, share what you&rsquo;re building, and get help from other students working through the same tools.</p></article>
        <article class="card"><span class="icon-tile" aria-hidden="true">{ICONS['rocket']}</span><h3>Calendar &amp; club activities</h3><p>Meetings, guest speakers, and events &mdash; so you always know what&rsquo;s coming up and never miss a session.</p></article>
      </div>
      <div class="skool-cta">
        <a class="btn-primary" href="{SKOOL_URL}" target="_blank" rel="noopener" data-cta="skool-join">Join the Skool community <span aria-hidden="true">&#8599;</span></a>
        <p class="skool-meta">Free to join &middot; {SKOOL_MEMBERS} members &middot; Open to every HWS student</p>
      </div>
    </div>
  </section>

  <section class="lp-section" id="founders">
    <div class="section-inner">
      <h2 class="section-title">Meet the Founders</h2>
      <p class="section-sub">The students who started HWS AI Club</p>
      <div class="team-grid">
{founder_cards()}
      </div>
      <figure class="founders-photo">
        <img src="/assets/founders/founders-together.jpg" width="633" height="900" loading="lazy" decoding="async"
             alt="Zackary Hanna and Dominic Schimizzi, co-founders of the HWS AI Club">
      </figure>
    </div>
  </section>
  <section class="lp-section lp-faq" id="faq">
    <div class="section-inner">
      <h2 class="section-title">Common questions</h2>
      <p class="section-sub">Everything students ask before their first meeting</p>
      <div class="faq-list">
{faq_home_html}
      </div>
    </div>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    (SITE / "index.html").write_text(head(title, desc, "/", [ORG_JSONLD, website, EVENT_JSONLD]) + "\n" + body + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Majors index
# ---------------------------------------------------------------------------
def build_majors_index():
    title = "AI Use Cases by Major | HWS AI Club"
    desc = ("20 practical AI use cases for each of 42 HWS majors. Choose your major for tutorials, "
            "starter prompts, and responsible-use guidance.")
    # Grouped by division rather than one flat run of 42. The page previously had
    # a single h1 and no subheadings at all, so 42 topic entities sat in bare
    # <span>s carrying no heading weight and no relationship to each other.
    by_slug = {m["slug"]: m for m in DATA["majors"]}
    groups = []
    for label, slugs in DIVISIONS:
        items = "\n".join(
            f'    <a class="major-card" href="/majors/{esc(by_slug[s]["slug"])}/" data-division="{esc(label)}">'
            f'<span>{esc(by_slug[s]["name"])}</span>'
            f'<span class="arrow" aria-hidden="true">&rarr;</span></a>'
            for s in slugs if s in by_slug
        )
        groups.append(
            f'  <section class="major-division">\n'
            f'    <h2 class="division-title">{esc(label)}</h2>\n'
            f'    <div class="majors-grid">\n{items}\n    </div>\n'
            f'  </section>'
        )
    cards = "\n".join(groups)
    crumbs = breadcrumb([("Home", "/"), ("All Majors", "/majors/")])
    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / All Majors</nav>
  <h1>AI Use Cases by Major</h1>
  <p class="page-lede">Every major at {COLLEGE} has 20 practical AI use cases &mdash; rated Easy, Medium, or Hard, each naming the exact tutorial it links to and what you&rsquo;ll take away. Pick yours to get started.</p>
  <div class="search-wrap">
    <input type="search" id="major-search" class="search-input" placeholder="Search for your major…" aria-label="Search majors">
    <p class="search-hint" id="search-hint">Type to filter, or browse all 42 majors below.</p>
  </div>
  <div id="majors-grid">
{cards}
  </div>
  <section class="sibling-majors">
    <h2>Not sure which major to pick?</h2>
    <p class="siblings-all"><a href="/tasks/">Browse the same use cases by task instead &rarr;</a></p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    (SITE / "majors").mkdir(exist_ok=True)
    (SITE / "majors" / "index.html").write_text(
        head(title, desc, "/majors/", [crumbs]) + "\n" + body + "\n", encoding="utf-8"
    )


def breadcrumb(items):
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": BASE_URL + path}
            for i, (name, path) in enumerate(items)
        ],
    }


# ---------------------------------------------------------------------------
# Per-major pages
# ---------------------------------------------------------------------------
def uc_card(slug, uc):
    badge = BADGE_CLASS.get(uc["difficulty"], "badge-easy")
    desc_text, nxt = card_text(slug, uc)
    url = video_url(slug, uc)
    meta = _VMETA.get(video_id(slug, uc), {})
    vtitle = meta.get("title") or "Watch a how-to tutorial"
    vchan, vyear = meta.get("channel", ""), (meta.get("date") or "")[:4]
    byline = " · ".join(x for x in (vchan, vyear) if x)
    pid = f"p-{slug}-{uc['number']}"
    prompt = starter_prompt(slug, uc)
    return (
        f'<article class="usecase-card" id="uc-{uc["number"]}" data-uc="{uc["number"]}" '
        f'data-difficulty="{esc(uc["difficulty"])}">'
        f'<span class="badge {badge}">{esc(uc["difficulty"])}</span>'
        f'<h3>{esc(uc["title"])}</h3>'
        f'<p class="description">{esc(desc_text)}</p>'
        f'<p class="next-steps"><strong>What you&#39;ll take away</strong>{esc(nxt)}</p>'
        f'<div class="uc-prompt">'
        f'<div class="uc-prompt-head">'
        f'<span class="uc-prompt-label">Starter prompt &mdash; paste into ChatGPT</span>'
        f'<button type="button" class="uc-copy" data-copy="{pid}" '
        f'aria-label="Copy the starter prompt for {esc(uc["title"])}">Copy</button>'
        f'</div>'
        f'<pre class="uc-prompt-text" id="{pid}">{esc(prompt)}</pre>'
        f'</div>'
        f'<a class="uc-watch" href="{esc(url)}" target="_blank" rel="noopener" '
        f'data-video-title="{esc(vtitle)}" '
        f'aria-label="Watch &quot;{esc(vtitle)}&quot; on YouTube (opens in a new tab)">'
        f'<span class="uc-watch-play" aria-hidden="true">&#9654;</span>'
        f'<span class="uc-watch-txt">'
        f'<span class="uc-watch-title">{esc(vtitle)}</span>'
        f'<span class="uc-watch-meta">{esc(byline)}</span>'
        f'</span>'
        f'<span class="uc-watch-ext" aria-hidden="true">&#8599;</span>'
        f'</a>'
        "</article>"
    )


# NOTE: this file used to emit one schema.org VideoObject per distinct tutorial
# linked from a major page. That markup was removed deliberately, not lost.
#
# The tutorials are third-party YouTube videos that the site links to but does not
# host and does not embed — there is no iframe anywhere in the generated HTML.
# Google's video structured-data guidelines require the video be playable on the
# page carrying the markup, so ~13 VideoObjects x 42 pages was a guideline
# violation with no upside; the hqdefault.jpg thumbnails (480px) also sat well
# under the 1200px minimum, so the nodes would have failed validation regardless.
#
# Video titles, channels and dates are still shown to readers on each card via
# _VMETA in uc_card() — that part is honest and stays.


def build_major(m, prev_m, next_m):
    slug, name = m["slug"], m["name"]
    ucs = m["useCases"]
    by_diff = {d: [u for u in ucs if u["difficulty"] == d] for d in ("Easy", "Medium", "Hard")}
    title = f"AI for {name} Students | HWS AI Club"
    # Built from this major's own easiest and hardest use cases. The previous
    # description varied only by {name} and closed with an identical clause on all
    # 42 pages, which reads to a crawler as 42 duplicate descriptions.
    first_easy = (by_diff["Easy"] or ucs)[0]["title"].rstrip(". ")
    last_hard = (by_diff["Hard"] or by_diff["Medium"] or ucs)[-1]["title"].rstrip(". ")
    # Kept under ~160 characters so Google doesn't truncate it mid-sentence. The
    # sample title is what makes each of the 42 descriptions distinct, so it is
    # only dropped when a long major name leaves no room for it.
    stem = (f"{len(ucs)} AI use cases for {name} students at HWS, Easy to Hard — "
            f"each with a tutorial and a starter prompt.")
    if len(esc(stem)) > 140:
        stem = (f"Practical AI use cases for {name} students at HWS, with tutorials "
                "and starter prompts.")
    # A real sample title is what makes each description distinct, so for long
    # major names try the shorter titles rather than dropping the sample.
    samples = sorted((u["title"].rstrip(". ") for u in (by_diff["Easy"] or ucs)), key=len)
    samples = [first_easy] + [s for s in samples if s != first_easy]
    desc = stem
    for s in samples:
        if len(esc(f"{stem} Try: {s}.")) <= 160:
            desc = f"{stem} Try: {s}."
            break
    cards = "\n".join(uc_card(slug, uc) for uc in m["useCases"])
    filters = "".join(
        f'<button type="button" class="filter-btn" data-filter="{f}" aria-pressed="{"true" if f=="All" else "false"}">{f}</button>'
        for f in ["All", "Easy", "Medium", "Hard"]
    )
    division = DIVISION_OF.get(slug)
    related = [mm for mm in DATA["majors"]
               if mm["slug"] != slug and DIVISION_OF.get(mm["slug"]) == division]
    siblings = " · ".join(f'<a href="/majors/{mm["slug"]}/">{esc(mm["name"])}</a>' for mm in related)
    crumbs = breadcrumb([("Home", "/"), ("All Majors", "/majors/"), (name, f"/majors/{slug}/")])
    faq_pairs = major_faq(slug, m)

    # Lede built from this major's own numbers and titles rather than one shared
    # sentence with {name} substituted in. n_videos genuinely varies (12-14).
    n_videos = len({video_id(slug, uc) for uc in ucs})
    split = ", ".join(f"{len(by_diff[d])} {d.lower()}" for d in ("Easy", "Medium", "Hard") if by_diff[d])
    lede = (
        f"{len(ucs)} practical, difficulty-rated ways {esc(name)} students at {COLLEGE} can use AI "
        f"&mdash; {split}. They start at &ldquo;{esc(first_easy)}&rdquo; and run up to "
        f"&ldquo;{esc(last_hard)}&rdquo;, drawing on {n_videos} tutorials between them. Every card "
        f"carries a starter prompt already written for {esc(name)}, so you can copy it and go."
    )
    nav_more = ""
    if prev_m:
        nav_more += f'<a class="pager prev" href="/majors/{prev_m["slug"]}/">&larr; {esc(prev_m["name"])}</a>'
    if next_m:
        nav_more += f'<a class="pager next" href="/majors/{next_m["slug"]}/">{esc(next_m["name"])} &rarr;</a>'

    program = esc(m["programLink"])
    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/majors/">All Majors</a> / {esc(name)}</nav>
  <div class="major-title-row">
    <h1>AI Use Cases for {esc(name)} at HWS</h1>
    <a class="program-link" href="{program}" target="_blank" rel="noopener">Learn more about the {esc(name)} program <span aria-hidden="true">&#8599;</span></a>
  </div>
  <p class="page-lede">{lede}</p>
  <p class="policy-note"><strong>Before you use these on graded work:</strong> check your professor&rsquo;s policy on AI.
  It differs by course, and these examples are study aids &mdash; not permission.</p>
  <h2 class="usecases-heading">All {esc(name)} AI use cases</h2>
  <div class="difficulty-filter" role="group" aria-label="Filter by difficulty">{filters}</div>
  <div class="usecases-grid" id="usecases-grid">
{cards}
  </div>
  <nav class="major-pager" aria-label="More majors">{nav_more}</nav>
{faq_html(faq_pairs, f"{name} AI questions, answered")}
  <section class="sibling-majors">
    <h2>Other {esc(division)} majors at HWS</h2>
    <p class="siblings">{siblings}</p>
    <p class="siblings-all"><a href="/majors/">Browse AI use cases for all 42 HWS majors &rarr;</a></p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    d = SITE / "majors" / slug
    d.mkdir(parents=True, exist_ok=True)
    jsonld = [crumbs]
    (d / "index.html").write_text(head(title, desc, f"/majors/{slug}/", jsonld) + "\n" + body + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Standalone pages: FAQ and the AI coursework policy guide
# ---------------------------------------------------------------------------
def build_faq_page():
    """The homepage FAQ plus the questions that only matter once someone is
    seriously considering joining. A dedicated URL so it can rank and be cited on
    its own, rather than living as an anchor on a page about something else."""
    pairs = HOME_FAQ + [
        ("Who runs the HWS AI Club?",
         f"The club was co-founded in August 2025 by Dominic Schimizzi and Zackary Hanna, and is run "
         f"by a student officer team. It is a registered student organisation at {COLLEGE} and is "
         f"open to all students regardless of major or class year."),
        ("Do I have to come every week?",
         "No. Meetings are drop-in — come to the ones that look useful and skip the rest. Nothing in "
         "the use-case library depends on having attended anything."),
        ("Is the use-case library only for HWS students?",
         f"The 840 use cases are written around the 42 majors offered at {COLLEGE}, so the examples "
         "and terminology are specific to those programmes. Anyone can read and use them, but a "
         "student in a similarly-named major elsewhere will get more out of them than someone in a "
         "field HWS does not offer."),
        ("What is the difference between the Easy, Medium, and Hard ratings?",
         "Easy means you can do it right now in one prompt with no setup — 420 of the 840 are rated "
         "this way. Medium means the output needs checking against your course material before you "
         "rely on it (252). Hard means it is project-scale work you should review with a professor "
         "or TA before it goes anywhere graded (168)."),
        ("Does the club teach you to code?",
         "Not primarily. The focus is on using AI tools well, which for most majors involves no code "
         "at all. Computer Science and the other quantitative majors do have code-specific use cases, "
         "but they are a minority of the library."),
    ]
    crumbs = breadcrumb([("Home", "/"), ("FAQ", "/faq/")])
    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / FAQ</nav>
  <h1>HWS AI Club: Frequently Asked Questions</h1>
  <p class="page-lede">Everything students ask before their first meeting &mdash; what the club is,
  what it costs, what you need to bring, and what the use-case library actually contains.</p>
{faq_html(pairs, "Questions and answers", "questions")}
  <section class="sibling-majors">
    <h2>Still deciding?</h2>
    <p class="siblings"><a href="/majors/">Browse AI use cases for your major</a> &middot;
    <a href="/ai-policy/">Read about AI and coursework at HWS</a> &middot;
    <a href="/#join">Join the club</a></p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    (SITE / "faq").mkdir(exist_ok=True)
    (SITE / "faq" / "index.html").write_text(
        head("HWS AI Club FAQ — Meetings, Membership, and the Use-Case Library",
             "Answers to what the HWS AI Club is, when it meets, what it costs, whether you need "
             "coding experience, and how the 840-use-case library is organised.",
             "/faq/", [crumbs]) + "\n" + body + "\n",
        encoding="utf-8")


def build_ai_policy_page():
    """Academic-integrity guidance. This is the question every student actually
    has before they touch any of this, and nothing on the site answered it at
    length — the major pages carry a one-line warning and nothing more.

    Deliberately does not state what HWS policy *is*: that is set per course by
    the instructor, and asserting a college-wide rule the club does not set would
    be both wrong and irresponsible."""
    pairs = [
        ("Is using AI for coursework allowed at HWS?",
         "There is no single answer, and anyone who gives you one is guessing. AI policy at "
         f"{COLLEGE} is set by the instructor, course by course. Some syllabi encourage AI for "
         "brainstorming and revision, some allow it with disclosure, some prohibit it for graded "
         "work entirely. The syllabus is the authority; when it is silent, ask before you use it."),
        ("What counts as an acceptable use?",
         "As a rule of thumb, uses where the thinking stays yours: having a concept explained until "
         "it clicks, being quizzed on terms, getting feedback on a draft you wrote, turning a "
         "syllabus into a study plan. These are the same things a tutor or study group would do, and "
         "they leave the work — and the understanding — with you."),
        ("What counts as academic dishonesty?",
         "Submitting AI-generated work as your own is plagiarism at essentially every institution, "
         "and it does not stop being plagiarism because a machine wrote it rather than a person. The "
         "line most policies draw is authorship: if the ideas, argument, and words handed in are not "
         "yours, you have crossed it, whatever tool produced them."),
        ("Do I have to disclose that I used AI?",
         "Often yes, and increasingly it is the default expectation. Some courses require a note on "
         "what you used and how; some require nothing. Disclosure costs you very little and removes "
         "the ambiguity entirely, so when the syllabus does not specify, disclosing is the safer of "
         "the two mistakes to make."),
        ("Can professors detect AI writing?",
         "AI-detection tools are unreliable in both directions — they miss real AI text and they "
         "flag human writing, disproportionately from multilingual writers. That is an argument for "
         "not relying on them, not an argument that using AI dishonestly is safe. Instructors also "
         "notice work that does not sound like the student who wrote everything else."),
        ("How does the club's use-case library handle this?",
         "Every one of the 840 use cases is written as a study aid rather than a substitute for "
         "doing the work, and each is rated by how much checking the output needs: Easy is usable "
         "as-is, Medium should be verified against your course material, and Hard should be reviewed "
         "with a professor or TA before it goes near graded work. Every major page carries the same "
         "warning to check the syllabus first."),
    ]
    crumbs = breadcrumb([("Home", "/"), ("AI and coursework", "/ai-policy/")])
    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / AI and coursework</nav>
  <h1>Using AI on Coursework at HWS: What&rsquo;s Actually Allowed</h1>
  <p class="page-lede">The question every student has before touching any of this. The honest answer
  is that it depends on your professor &mdash; but there is a lot more to say than that, and knowing
  where the lines usually fall makes the conversation with your instructor much shorter.</p>
  <p class="policy-note"><strong>The HWS AI Club does not set academic policy.</strong> Nothing on this
  page overrides your syllabus or your instructor. Where the two disagree, your instructor is right.</p>
{faq_html(pairs, "AI and academic integrity at HWS", "policy")}
  <section class="sibling-majors">
    <h2>Next</h2>
    <p class="siblings"><a href="/majors/">Browse AI use cases for your major</a> &middot;
    <a href="/tasks/">Browse by task</a> &middot;
    <a href="/faq/">Club FAQ</a></p>
    <p class="siblings-all"><a href="https://www.hws.edu/academics/catalogue/" target="_blank" rel="noopener">HWS academic catalogue and policies &#8599;</a></p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    (SITE / "ai-policy").mkdir(exist_ok=True)
    (SITE / "ai-policy" / "index.html").write_text(
        head("Using AI on Coursework at HWS: What's Allowed | HWS AI Club",
             "AI policy at HWS is set per course by your instructor. What usually counts as an "
             "acceptable study aid, what counts as academic dishonesty, and when to disclose.",
             "/ai-policy/", [crumbs]) + "\n" + body + "\n",
        encoding="utf-8")


def build_ai_resources_page():
    """A maintained, answerable map of trustworthy AI help available to HWS students.

    The club complements official services rather than speaking for them. Each link
    is a first-party HWS or verified club source, so the page can support campus
    discovery without blurring academic policy, career guidance, and club events.
    """
    crumbs = breadcrumb([("Home", "/"), ("AI resources at HWS", "/resources/ai-at-hws/")])
    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / AI resources at HWS</nav>
  <h1>AI Resources for HWS Students</h1>
  <p class="page-lede">A starting point for using AI thoughtfully at Hobart and William Smith Colleges:
  official campus guidance, career support, library tools, and the HWS AI Club&rsquo;s hands-on community.</p>
  <p class="policy-note"><strong>Start with your course.</strong> Your syllabus and instructor set the rules for
  graded work. The club can help you learn tools, but it does not set college or course policy.</p>
  <section class="sibling-majors">
    <h2>Official HWS resources</h2>
    <ul class="check-list">
      <li><span class="check-dot" aria-hidden="true">&#10003;</span><a href="https://library.hws.edu/ai_tools" target="_blank" rel="noopener">HWS Library AI tools guide</a> &mdash; library-selected tools and research support.</li>
      <li><span class="check-dot" aria-hidden="true">&#10003;</span><a href="https://careerservices.hws.edu/resources/using-ai-in-your-career-development/" target="_blank" rel="noopener">Career Services: using AI in career development</a> &mdash; practical career-search and professional-use guidance.</li>
      <li><span class="check-dot" aria-hidden="true">&#10003;</span><a href="https://careerservices.hws.edu/channels/technology-data-artificial-science/" target="_blank" rel="noopener">Technology, Data &amp; AI career channel</a> &mdash; opportunities and career resources from HWS Career Services.</li>
      <li><span class="check-dot" aria-hidden="true">&#10003;</span><a href="https://www.hws.edu/academics/catalogue/" target="_blank" rel="noopener">HWS academic catalogue and policies</a> &mdash; institutional reference material; confirm assignment-specific expectations with your instructor.</li>
    </ul>
  </section>
  <section class="sibling-majors">
    <h2>Learn with the club</h2>
    <p>HWS AI Club is free, open to every major, and meets {MEETING}. Use the library for a major-specific
    starting point, then bring questions to a workshop or the community.</p>
    <p class="siblings"><a href="/majors/">Browse 840 AI use cases by major</a> &middot;
    <a href="/tasks/">Browse them by task</a> &middot;
    <a href="/ai-policy/">Read the coursework guide</a></p>
    <p class="siblings-all"><a class="btn-primary" href="{SKOOL_URL}" target="_blank" rel="noopener" data-cta="skool-join">Join the Skool community <span aria-hidden="true">&#8599;</span></a></p>
  </section>
  <section class="sibling-majors">
    <h2>How to use this page</h2>
    <p>Use official HWS resources for institutional and course-specific guidance. Use the club&rsquo;s pages for
    practical prompts, workshops, and peer learning. This page was last reviewed when the site was built;
    report a stale link to the club before relying on it.</p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    d = SITE / "resources" / "ai-at-hws"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(
        head("AI Resources for HWS Students | HWS AI Club",
             "Find trustworthy AI resources for HWS students: library tools, Career Services guidance, "
             "coursework help, practical workshops, and the HWS AI Club community.",
             "/resources/ai-at-hws/", [crumbs]) + "\n" + body + "\n",
        encoding="utf-8")


# ---------------------------------------------------------------------------
# Task hubs — the same 840 use cases, sliced by task instead of by major
# ---------------------------------------------------------------------------
def task_members(arch):
    """Every use case whose archetype is `arch`, grouped by division then major.

    Returns [(division, [(major_dict, [use_case, ...]), ...]), ...] in DIVISIONS
    order, skipping divisions and majors with nothing to show."""
    out = []
    for label, slugs in DIVISIONS:
        majors = []
        for slug in slugs:
            m = next((x for x in DATA["majors"] if x["slug"] == slug), None)
            if not m:
                continue
            hits = [uc for uc in m["useCases"] if prompt_archetype(slug, uc) == arch]
            if hits:
                majors.append((m, hits))
        if majors:
            out.append((label, majors))
    return out


def build_task_hub(hub, prev_h, next_h):
    arch, slug, name = hub["arch"], hub["slug"], hub["label"]
    groups = task_members(arch)
    total = sum(len(h) for _, ms in groups for _, h in ms)
    n_majors = sum(len(ms) for _, ms in groups)
    by_diff = collections.Counter(
        uc["difficulty"] for _, ms in groups for _, hits in ms for uc in hits
    )
    split = ", ".join(f"{by_diff[d]} {d.lower()}" for d in ("Easy", "Medium", "Hard") if by_diff[d])

    title = f"AI for {hub['label']} | HWS AI Club"
    # Built up sentence by sentence and stopped before 160 rather than sliced, so
    # it never truncates mid-word the way a hard [:160] does.
    desc = f"{total} ways students in {n_majors} HWS majors use AI for {hub['gerund']}, rated Easy to Hard."
    for extra in (hub["blurb"], "Each links a tutorial and a starter prompt."):
        if len(desc) + 1 + len(extra) <= 160:
            desc = f"{desc} {extra}"

    sections = []
    for label, majors in groups:
        rows = []
        for m, hits in majors:
            links = " · ".join(
                f'<a href="/majors/{m["slug"]}/#uc-{uc["number"]}">{esc(uc["title"])}</a> '
                f'<span class="task-diff task-diff-{uc["difficulty"].lower()}">{uc["difficulty"]}</span>'
                for uc in hits
            )
            rows.append(
                f'      <li class="task-major"><a class="task-major-name" href="/majors/{m["slug"]}/">'
                f'{esc(m["name"])}</a> <span class="task-links">{links}</span></li>'
            )
        sections.append(
            f'    <h3>{esc(label)}</h3>\n    <ul class="task-list">\n' + "\n".join(rows) + "\n    </ul>"
        )
    body_sections = "\n".join(sections)

    faq_pairs = [
        (f"How do HWS students use AI for {hub['gerund']}?",
         f"{total} use cases across {n_majors} of the 42 majors at {COLLEGE} come down to this one "
         f"task — {split} by difficulty. {hub['blurb']} Every entry below links to the use case on "
         f"its major's page, where it comes with a tutorial and a starter prompt written for that field."),
        (f"Which AI tool is best for {hub['gerund']}?",
         "Any of the free general-purpose assistants — ChatGPT, Claude, or Gemini — handles this. "
         "The starter prompts here are written to work in all three, so pick whichever you already "
         "have an account for rather than shopping for a specialist tool."),
        (f"Is it allowed to use AI for {hub['gerund']} at HWS?",
         "That is your professor's call and it varies by course and by assignment. Check the "
         "syllabus first. These are study aids meant to help you learn faster, not a route to work "
         "you submit as your own — when the syllabus does not say, ask before you use it."),
    ]

    crumbs = breadcrumb([("Home", "/"), ("AI Tasks", "/tasks/"), (name, f"/tasks/{slug}/")])
    nav_more = ""
    if prev_h:
        nav_more += f'<a class="pager prev" href="/tasks/{prev_h["slug"]}/">&larr; {esc(prev_h["label"])}</a>'
    if next_h:
        nav_more += f'<a class="pager next" href="/tasks/{next_h["slug"]}/">{esc(next_h["label"])} &rarr;</a>'

    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/tasks/">AI Tasks</a> / {esc(name)}</nav>
  <h1>{esc(hub["h1"])}</h1>
  <p class="page-lede">{esc(hub["blurb"])} {total} use cases across {n_majors} HWS majors come down to
  this one task &mdash; {split}. Each links straight to the card on its major&rsquo;s page, where it
  carries a tutorial and a starter prompt already written for that field.</p>
  <p class="policy-note"><strong>Before you use these on graded work:</strong> check your professor&rsquo;s policy on AI.
  It differs by course, and these examples are study aids &mdash; not permission.</p>
  <h2>Every {esc(name.lower())} use case, by division</h2>
{body_sections}
  <nav class="major-pager" aria-label="More tasks">{nav_more}</nav>
{faq_html(faq_pairs, f"Questions about {esc(name.lower())} with AI")}
  <section class="sibling-majors">
    <h2>Other things students use AI for</h2>
    <p class="siblings">{" · ".join(f'<a href="/tasks/{h["slug"]}/">{esc(h["label"])}</a>' for h in TASK_HUBS if h["slug"] != slug)}</p>
    <p class="siblings-all"><a href="/majors/">Or browse AI use cases by major &rarr;</a></p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    d = SITE / "tasks" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(
        head(title, desc, f"/tasks/{slug}/", [crumbs])
        + "\n" + body + "\n", encoding="utf-8")
    return total


def build_tasks_index():
    title = "What Students Use AI For — 15 Tasks Across 42 Majors | HWS AI Club"
    desc = ("Browse HWS AI Club's 840 use cases by task instead of by major — explaining concepts, "
            "summarizing readings, studying for exams, writing code, and 11 more.")
    cards = []
    for h in TASK_HUBS:
        n = sum(len(hits) for _, ms in task_members(h["arch"]) for _, hits in ms)
        cards.append(
            f'<a class="major-card task-card" href="/tasks/{h["slug"]}/">'
            f'<span>{esc(h["label"])}</span>'
            f'<span class="task-card-meta">{n} use cases</span></a>'
        )
    crumbs = breadcrumb([("Home", "/"), ("AI Tasks", "/tasks/")])
    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / AI Tasks</nav>
  <h1>What HWS Students Actually Use AI For</h1>
  <p class="page-lede">The use-case library is organised by major, but most people arrive with a task
  in mind rather than a department. These {len(TASK_HUBS)} pages cut the same 840 use cases the other
  way &mdash; every major&rsquo;s take on the same job, side by side.</p>
  <div class="majors-grid">
{chr(10).join("    " + c for c in cards)}
  </div>
  <section class="sibling-majors">
    <h2>Prefer to browse by subject?</h2>
    <p class="siblings-all"><a href="/majors/">AI use cases for all 42 HWS majors &rarr;</a></p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    (SITE / "tasks").mkdir(exist_ok=True)
    (SITE / "tasks" / "index.html").write_text(
        head(title, desc, "/tasks/", [crumbs]) + "\n" + body + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-founder pages
# ---------------------------------------------------------------------------
def build_founder(f, others):
    slug, name = f["slug"], f["name"]
    title = f"{name} | HWS AI Club"
    description = (f"Meet {name}, {f['role']} of HWS AI Club, and learn about the student-led "
                   "organization's practical AI resources for HWS students.")
    affiliation = [{"@id": ORG_ID}]
    if f.get("school"):  # currently enrolled — affiliation, not alumniOf
        affiliation.append({"@type": "CollegeOrUniversity", "name": f["school"][0], "url": f["school"][1]})
    # worksFor comes from the founder's own record. It used to be hardcoded to
    # Licom AI for both, which published a factual error for Dominic — his current
    # role is at Metro Development Group.
    works = [{"@type": "Organization", "name": org, **({"url": url} if url else {})}
             for org, url in f.get("worksFor", [])]
    person = {
        "@context": "https://schema.org", "@type": "Person",
        "@id": f"{BASE_URL}/founders/{slug}/#person",
        "name": name,
        "url": f"{BASE_URL}/founders/{slug}/",
        "jobTitle": f["role"],
        "description": f["meta"],
        "affiliation": affiliation if len(affiliation) > 1 else affiliation[0],
        "sameAs": [url for _, url in f["links"] if url not in ORG_URLS],
    }
    if works:
        person["worksFor"] = works if len(works) > 1 else works[0]
    if f.get("memberOf"):
        person["memberOf"] = {"@type": "Organization", "name": f["memberOf"][0], "url": f["memberOf"][1]}
    if founder_photo(f):
        person["image"] = BASE_URL + f["photo"]
    # Two levels, not three: there is no /founders/ index page, and a fragment URL
    # like /#founders resolves to the homepage, which makes the middle crumb a
    # duplicate of the first as far as a validator is concerned.
    crumbs = breadcrumb([("Home", "/"), (name, f"/founders/{slug}/")])

    paras = "\n      ".join(f"<p>{p}</p>" for p in f["bio"])
    facts = "\n        ".join(
        f'<div class="founder-fact"><dt>{label}</dt><dd>{value}</dd></div>'
        for label, value in f["facts"]
    )
    highlights = "\n        ".join(
        f'<li><span class="check-dot" aria-hidden="true">&#10003;</span>{h}</li>'
        for h in f["highlights"]
    )
    links = "\n        ".join(
        f'<a class="founder-link" href="{esc(url)}" target="_blank" rel="noopener" '
        f'data-cta="founder-link" data-founder="{slug}" data-link-label="{esc(label)}">{esc(label)} '
        f'<span aria-hidden="true">&#8599;</span></a>'
        for label, url in f["links"]
    )
    siblings = "".join(
        f'<a class="pager next" href="/founders/{o["slug"]}/" '
        f'data-cta="founder-pager" data-founder="{o["slug"]}">{esc(o["name"])} &rarr;</a>'
        for o in others
    )

    song_html = ""
    if f.get("song"):
        s = f["song"]
        first_name = name.split()[0]
        album_part = f" &mdash; {esc(s['album'])}" if s.get("album") else ""
        song_html = f"""
      <h2>The Song {esc(first_name)} Wants to Be Remembered By</h2>
      <p class="founder-song-caption">&ldquo;{esc(s['title'])}&rdquo; by {esc(s['artist'])}{album_part}.</p>
      <div class="founder-song">
        <div id="spotify-embed-{slug}" class="spotify-embed-placeholder"
             data-spotify-uri="spotify:track:{esc(s['spotify_track_id'])}"
             data-founder="{slug}" data-song-title="{esc(s['title'])}" data-song-artist="{esc(s['artist'])}">
          <noscript>
            <a href="https://open.spotify.com/track/{esc(s['spotify_track_id'])}" target="_blank" rel="noopener">
              Listen to &ldquo;{esc(s['title'])}&rdquo; by {esc(s['artist'])} on Spotify &#8599;</a>
          </noscript>
        </div>
      </div>"""

    photo_html = ""
    if f.get("extra_photo"):
        p = f["extra_photo"]
        photo_html = f"""
      <figure class="founder-extra-photo">
        <img src="{esc(p['src'])}" width="{p['width']}" height="{p['height']}" loading="lazy" decoding="async"
             alt="{esc(p['alt'])}">
      </figure>"""

    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / {esc(name)}</nav>
  <div class="founder-hero">
    {founder_avatar(f, "founder-avatar", eager=True)}
    <div>
      <h1>{esc(name)}</h1>
      <p class="founder-subtitle">{f["subtitle"]}</p>
    </div>
  </div>
  <div class="founder-body">
    <div class="founder-prose">
      {paras}
      <h2>At the club</h2>
      <ul class="check-list">
        {highlights}
      </ul>
      <div class="founder-links">
        {links}
      </div>{song_html}{photo_html}
    </div>
    <aside class="founder-side" aria-label="Quick facts">
      <dl class="founder-facts">
        {facts}
      </dl>
    </aside>
  </div>
  <nav class="major-pager" aria-label="More founders">{siblings}</nav>
  <section class="sibling-majors">
    <h2>Explore the club</h2>
    <p class="siblings"><a href="/#about">What we do</a> &middot; <a href="/majors/">AI use cases for all 42 majors</a> &middot; <a href="/#join">Join the club</a></p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    d = SITE / "founders" / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.html").write_text(
        head(title, description, f"/founders/{slug}/", [crumbs, person]) + "\n" + body + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# robots / sitemap / headers / og-image / videos.js
# ---------------------------------------------------------------------------
DISALLOW = ["/showcase.html", "/data.json", "/data/"]


def build_robots():
    """robots.txt.

    The disallow list is repeated inside every named group on purpose. A crawler
    obeys exactly one group — the most specific one matching its token — and
    ignores the rest, so the AI bots below were previously matching their own
    "Allow: /" group and never seeing the * group's Disallow lines at all. The
    effect was the opposite of what naming them was meant to achieve.
    """
    def group(agent):
        return [f"User-agent: {agent}", "Allow: /"] + [f"Disallow: {p}" for p in DISALLOW] + [""]

    lines = group("*")
    for bot in AI_BOTS:
        lines += group(bot)
    lines.append("Sitemap: " + BASE_URL + "/sitemap.xml")
    (SITE / "robots.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_llms_txt():
    """llms.txt (emerging llmstxt.org convention) — a plain-language map of the
    site for AI agents/assistants that consult it, mirroring what's in robots.txt
    + sitemap.xml but in a format meant to be read, not just crawled."""
    majors = "\n".join(f"- [{m['name']}]({BASE_URL}/majors/{m['slug']}/)" for m in DATA["majors"])
    founders = "\n".join(f"- [{f['name']}, {f['role']}]({BASE_URL}/founders/{f['slug']}/)" for f in FOUNDERS)
    tasks = "\n".join(f"- [{h['label']}]({BASE_URL}/tasks/{h['slug']}/): {h['blurb']}" for h in TASK_HUBS)
    text = f"""# HWS AI Club

> Student-run AI literacy club at {COLLEGE} (HWS) in {LOCATION}. Free and open to \
students in all 42 majors, no coding experience required. {MEETING}.

HWS AI Club maintains a library of 840 practical AI use cases — 20 per major, rated \
Easy, Medium, or Hard — across all 42 majors offered at HWS. Each use case names a \
specific tutorial video and includes a ready-to-paste starter prompt.

## Key pages

- [Homepage]({BASE_URL}/): what the club does, the team, and how to join.
- [All Majors]({BASE_URL}/majors/): directory of all 42 majors with AI use cases.
- [AI Tasks]({BASE_URL}/tasks/): the same 840 use cases grouped by task rather than by major.
- [AI resources at HWS]({BASE_URL}/resources/ai-at-hws/): official campus resources alongside club workshops and practical guides.
- [FAQ]({BASE_URL}/faq/): what the club is, when it meets, what it costs, what you need.
- [AI and coursework]({BASE_URL}/ai-policy/): what is and isn't allowed academically, and why \
that is set per course by the instructor rather than college-wide.
- [Sitemap]({BASE_URL}/sitemap.xml)

## Tasks

{tasks}

## Majors

{majors}

## Founders

{founders}
"""
    (SITE / "llms.txt").write_text(text, encoding="utf-8")


LASTMOD_DB = SITE / "data" / "lastmod.json"


def build_sitemap():
    """Sitemap with per-page lastmod derived from each page's own content hash.

    lastmod used to be date.today() on every URL, which meant all 46 dates
    changed on every build regardless of whether anything changed. Google ignores
    a blanket-uniform lastmod, so the signal was dead — and it also meant the
    build was not idempotent across days, breaking the repo's own no-diff check.

    Here each page's rendered bytes are hashed and the date is only advanced when
    that hash actually moves. The map is committed alongside the site so the date
    survives across machines and CI. <priority> is gone: Google has said for years
    that it ignores it.
    """
    pages = [("/", SITE / "index.html")]
    pages += [("/majors/", SITE / "majors" / "index.html")]
    pages += [(f"/majors/{m['slug']}/", SITE / "majors" / m["slug"] / "index.html") for m in DATA["majors"]]
    pages += [("/tasks/", SITE / "tasks" / "index.html")]
    pages += [(f"/tasks/{h['slug']}/", SITE / "tasks" / h["slug"] / "index.html") for h in TASK_HUBS]
    pages += [("/resources/ai-at-hws/", SITE / "resources" / "ai-at-hws" / "index.html"),
              ("/faq/", SITE / "faq" / "index.html"), ("/ai-policy/", SITE / "ai-policy" / "index.html")]
    pages += [(f"/founders/{f['slug']}/", SITE / "founders" / f["slug"] / "index.html") for f in FOUNDERS]

    try:
        db = json.loads(LASTMOD_DB.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        db = {}

    out = {}
    items = []
    for path, fp in pages:
        digest = hashlib.sha256(fp.read_bytes()).hexdigest()[:16] if fp.exists() else ""
        prev = db.get(path)
        # Same content as last build → keep the date it already had.
        date_str = prev["date"] if prev and prev.get("hash") == digest else BUILD_DATE
        out[path] = {"hash": digest, "date": date_str}
        items.append(f"  <url><loc>{BASE_URL}{path}</loc><lastmod>{date_str}</lastmod></url>")

    LASTMOD_DB.parent.mkdir(parents=True, exist_ok=True)
    LASTMOD_DB.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(items) + "\n</urlset>\n",
        encoding="utf-8",
    )
    return len(items)


def build_headers():
    """Netlify _headers. Long-lived immutable caching is deliberately NOT set on
    /css/ and /js/ — those filenames carry no content hash, so a year-long
    immutable cache would strand visitors on stale CSS after a deploy. The
    fingerprinted image assets are safe to cache hard."""
    (SITE / "_headers").write_text(
        "/*\n"
        "  X-Robots-Tag: all\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
        "\n"
        "/assets/*\n"
        "  Cache-Control: public, max-age=604800\n"
        "\n"
        "/css/*\n"
        "  Cache-Control: public, max-age=3600, must-revalidate\n"
        "\n"
        "/js/*\n"
        "  Cache-Control: public, max-age=3600, must-revalidate\n"
        "\n"
        "/showcase.html\n"
        "  X-Robots-Tag: noindex\n",
        encoding="utf-8",
    )


def build_videos_js():
    """Regenerate runtime resolver from the config so it never diverges."""
    cfg = json.dumps({"skill": VCONF["skill"], "overrides": VCONF["overrides"],
                      "leadVerb": VCONF["leadVerb"], "rules": VCONF["rules"]}, ensure_ascii=False)
    js = (
        "/* GENERATED by scripts/build_site.py from data/videos-config.json — do not edit by hand. */\n"
        "(function (root) {\n  \"use strict\";\n"
        "  var CFG = " + cfg + ";\n"
        "  var rules = CFG.rules.map(function (r) { return [r[0], new RegExp(r[1], \"i\")]; });\n"
        "  function classify(title, description) {\n"
        "    var lead = (title || \"\").trim().split(/\\s+/)[0].toLowerCase();\n"
        "    if (CFG.leadVerb[lead]) return CFG.leadVerb[lead];\n"
        "    var text = ((title || \"\") + \" \" + (description || \"\")).toLowerCase();\n"
        "    for (var i = 0; i < rules.length; i++) { if (rules[i][1].test(text)) return rules[i][0]; }\n"
        "    return \"general\";\n  }\n"
        "  root.HWS_VIDEOS = { skill: CFG.skill, overrides: CFG.overrides, classify: classify };\n"
        "  if (typeof module !== \"undefined\" && module.exports) module.exports = root.HWS_VIDEOS;\n"
        "})(typeof window !== \"undefined\" ? window : globalThis);\n"
    )
    (SITE / "js" / "videos.js").write_text(js, encoding="utf-8")


def build_og_image():
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#faf5ff"/><stop offset="1" stop-color="#eff6ff"/></linearGradient>
    <linearGradient id="tile" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#7c3aed"/><stop offset="1" stop-color="#3b82f6"/></linearGradient></defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="80" y="86" width="120" height="120" rx="30" fill="url(#tile)"/>
  <g transform="translate(116 122) scale(2)" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
    <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>
    <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/></g>
  <text x="230" y="170" font-family="Inter, Arial, sans-serif" font-size="42" font-weight="800" fill="#0f172a">HWS AI Club</text>
  <text x="80" y="340" font-family="Inter, Arial, sans-serif" font-size="76" font-weight="800" fill="#0f172a">AI for Everyone at</text>
  <text x="80" y="428" font-family="Inter, Arial, sans-serif" font-size="76" font-weight="800" fill="#7c3aed">Hobart &amp; William Smith</text>
  <text x="80" y="512" font-family="Inter, Arial, sans-serif" font-size="34" font-weight="500" fill="#64748b">840 AI use cases across all 42 majors · no coding required</text>
</svg>"""
    (SITE / "og-image.svg").write_text(svg, encoding="utf-8")
    # Rasterize to PNG (social crawlers prefer PNG/JPG). Prefer an SVG tool; else
    # render an equivalent 1200x630 card with Pillow.
    png = SITE / "og-image.png"
    src = SITE / "og-image.svg"
    for cmd in (["cairosvg", str(src), "-o", str(png)],
                ["rsvg-convert", str(src), "-o", str(png)],
                ["magick", str(src), str(png)],
                ["convert", str(src), str(png)]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return "png (svg tool)"
            except Exception:
                continue
    try:
        return _og_png_pillow(png)
    except Exception as e:  # noqa
        return "svg-only (" + type(e).__name__ + ")"


def _og_png_pillow(png):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 1200, 630
    img = Image.new("RGB", (W, H), "#f3f0fb")
    px = img.load()
    for y in range(H):  # diagonal purple->blue wash
        for x in range(0, W, 2):
            t = (x / W + y / H) / 2
            r = int(0xfa + t * (0xef - 0xfa)); g = int(0xf5 + t * (0xf6 - 0xf5)); b = int(0xff + t * (0xff - 0xff))
            px[x, y] = (r, g, b)
            if x + 1 < W:
                px[x + 1, y] = (r, g, b)

    draw = ImageDraw.Draw(img)

    def font(sz, bold=True):
        # Cross-platform: without a real TTF, Pillow falls back to a tiny bitmap font
        # and the OG card renders effectively blank. Cover macOS, Windows and Linux.
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for name in candidates:
            try:
                return ImageFont.truetype(name, sz)
            except Exception:
                continue
        raise RuntimeError("no TrueType font found for og-image; refusing to render with bitmap fallback")

    # brand tile
    tile = Image.new("RGB", (120, 120), "#5a2fd0")
    tp = tile.load()
    for y in range(120):
        for x in range(120):
            t = (x + y) / 240
            tp[x, y] = (int(0x7c + t * (0x3b - 0x7c)), int(0x3a + t * (0x82 - 0x3a)), int(0xed + t * (0xf6 - 0xed)))
    mask = Image.new("L", (120, 120), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 119, 119], radius=30, fill=255)
    img.paste(tile, (80, 86), mask)
    d2 = ImageDraw.Draw(img)
    d2.text((120, 128), "AI", font=font(56), fill="#ffffff")

    draw.text((230, 120), "HWS AI Club", font=font(42), fill="#0f172a")
    draw.text((80, 250), "AI for Everyone at", font=font(76), fill="#0f172a")
    draw.text((80, 340), "Hobart & William Smith", font=font(76), fill="#7c3aed")
    draw.text((80, 470), "840 AI use cases across all 42 majors  ·  no coding required",
              font=font(32, bold=False), fill="#64748b")
    img.save(png, "PNG")
    return "png (pillow)"


def _rasterize(src, out, size):
    """Rasterize an SVG to a square PNG at `size`px, trying installed SVG tools
    before falling back to a hand-drawn Pillow tile (mirrors build_og_image)."""
    for cmd in (
        ["cairosvg", str(src), "-o", str(out), "-W", str(size), "-H", str(size)],
        ["rsvg-convert", str(src), "-o", str(out), "-w", str(size), "-h", str(size)],
        ["magick", str(src), "-resize", f"{size}x{size}", str(out)],
        ["convert", str(src), "-resize", f"{size}x{size}", str(out)],
    ):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                return "svg tool"
            except Exception:
                continue
    try:
        return _icon_pillow(out, size)
    except Exception as e:  # noqa
        return "failed (" + type(e).__name__ + ")"


def _icon_pillow(out, size):
    """Fallback: redraw the favicon's rounded gradient tile directly (no SVG
    rasterizer available). Same brand gradient as assets/favicon.svg."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x / size + y / size) / 2
            px[x, y] = (int(0x7c + t * (0x3b - 0x7c)), int(0x3a + t * (0x82 - 0x3a)), int(0xed + t * (0xf6 - 0xed)), 255)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=max(2, size // 4), fill=255)
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask)
    bg.save(out, "PNG")
    return "png (pillow fallback)"


def build_favicons():
    """PNG/ICO favicon fallback + apple-touch-icon, rasterized from the existing
    assets/favicon.svg so there's one source of truth for the brand mark."""
    src = SITE / "assets" / "favicon.svg"
    # logo-512.png exists for schema.org Organization.logo, which Google will not
    # accept as SVG and wants at >=112px. Same source mark as the favicons.
    sizes = {"favicon-16x16.png": 16, "favicon-32x32.png": 32,
             "apple-touch-icon.png": 180, "logo-512.png": 512}
    for name, size in sizes.items():
        _rasterize(src, SITE / "assets" / name, size)
    try:
        from PIL import Image

        base = Image.open(SITE / "assets" / "apple-touch-icon.png").convert("RGBA")
        base.save(SITE / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
        return "png + ico"
    except Exception as e:  # noqa
        return "png only, ico failed (" + type(e).__name__ + ")"


def build_manifest():
    manifest = {
        "name": "HWS AI Club",
        "short_name": "HWS AI Club",
        "description": f"AI use cases and workshops for every major at {COLLEGE}.",
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#7c3aed",
        "background_color": "#faf5ff",
        "icons": [
            {"src": "/assets/favicon-16x16.png", "sizes": "16x16", "type": "image/png"},
            {"src": "/assets/favicon-32x32.png", "sizes": "32x32", "type": "image/png"},
            {"src": "/assets/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"},
        ],
    }
    (SITE / "site.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main():
    build_home()
    build_majors_index()
    majors = DATA["majors"]
    for i, m in enumerate(majors):
        build_major(m, majors[i - 1] if i > 0 else None, majors[i + 1] if i + 1 < len(majors) else None)
    build_tasks_index()
    for i, h in enumerate(TASK_HUBS):
        build_task_hub(h, TASK_HUBS[i - 1] if i > 0 else None,
                       TASK_HUBS[i + 1] if i + 1 < len(TASK_HUBS) else None)
    build_faq_page()
    build_ai_policy_page()
    build_ai_resources_page()
    for f in FOUNDERS:
        build_founder(f, [o for o in FOUNDERS if o["slug"] != f["slug"]])
    build_robots()
    build_llms_txt()
    n = build_sitemap()
    build_headers()
    build_videos_js()
    og = build_og_image()
    ico = build_favicons()
    build_manifest()

    assert len(majors) == 42, "expected 42 majors"
    # DIVISIONS drives related-major linking and the /majors/ grouping, so a major
    # missing from it would silently lose its internal links.
    slugs = {m["slug"] for m in majors}
    mapped = [s for _, ss in DIVISIONS for s in ss]
    assert len(mapped) == len(set(mapped)), f"major listed twice in DIVISIONS: {sorted(s for s in mapped if mapped.count(s) > 1)}"
    assert set(mapped) == slugs, (
        f"DIVISIONS out of sync with data.json — missing: {sorted(slugs - set(mapped))}, "
        f"unknown: {sorted(set(mapped) - slugs)}"
    )
    for m in majors:
        assert (SITE / "majors" / m["slug"] / "index.html").exists()
    for f in FOUNDERS:
        assert (SITE / "founders" / f["slug"] / "index.html").exists()
    for h in TASK_HUBS:
        assert (SITE / "tasks" / h["slug"] / "index.html").exists()
    for p in ("tasks/index.html", "resources/ai-at-hws/index.html", "faq/index.html", "ai-policy/index.html"):
        assert (SITE / p).exists(), f"missing {p}"
    # Every task hub must resolve to a real archetype, or it would render empty.
    for h in TASK_HUBS:
        assert task_members(h["arch"]), f"task hub '{h['slug']}' matched no use cases"
    print("HWS AI Club static build complete")
    print(f"  homepage + majors index + {len(majors)} major pages + {len(FOUNDERS)} founder pages")
    print(f"  tasks index + {len(TASK_HUBS)} task hubs + AI resources + faq + ai-policy")
    print(f"  sitemap: {n} urls | robots.txt (+ AI bot allow rules), llms.txt, _headers written")
    print(f"  js/videos.js regenerated from config | og-image: {og} | favicons: {ico} | manifest written")


if __name__ == "__main__":
    main()
