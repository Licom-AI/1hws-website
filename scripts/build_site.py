#!/usr/bin/env python3
"""Static-site generator for the HWS AI Club site (SEO build).

Reads site/data.json + site/data/videos-config.json and emits crawlable,
SEO-optimized static HTML: homepage, majors index, 42 per-major pages, plus
robots.txt, sitemap.xml, _headers, og-image, and the runtime js/videos.js.

Run:  python3 scripts/build_site.py
"""
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
BASE_URL = "https://hws-ai-club.netlify.app"
COLLEGE = "Hobart and William Smith Colleges"
LOCATION = "Geneva, New York"
MEETING = "Every Sunday, 5-6 PM · Sanford Room"
MEETING_START, MEETING_END, MEETING_TZ = "17:00", "18:00", "America/New_York"
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
            "title": "The Arsonist",
            "artist": "Marilyn Manson",
            "spotify_track_id": "7uXhNhHb8BFQB0l54BI8N7",
        },
    },
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
    return f"I'm {art} {major} student at HWS. My task: {task} — {detail}.\n\n{instructions}"


def card_text(slug, uc):
    """Compose honest card copy: the task, what the linked video actually teaches,
    and what the student walks away with. Keeps site/data.json canonical — swap a
    video in videos-config.json and every card using it re-describes itself."""
    t = _VTEACH.get(video_id(slug, uc), {})
    desc = uc["description"].rstrip(". ")
    method, takeaway = t.get("method"), t.get("takeaway")
    if method:
        desc = f"{desc}. The linked tutorial covers {method}."
    else:
        desc = f"{desc}."
    return desc, (takeaway or NEXT_STEPS.get(uc["difficulty"], ""))


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
      <a href="/#team">Team</a>
      <a href="/majors/">Use Cases</a>
      <a href="/#community">Community</a>
      <a href="/#founders">Meet The Founders</a>
      <a class="nav-cta" href="/#join">Join Us</a>
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
      <a href="/majors/">Use Cases</a>
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
    return '<script src="/js/site.js"></script>'


ORG_JSONLD = {
    "@context": "https://schema.org",
    "@type": "EducationalOrganization",
    "name": "HWS AI Club",
    "alternateName": ["Hobart and William Smith AI Club", "AI @ HWS", "HWS Artificial Intelligence Club"],
    "url": BASE_URL + "/",
    "logo": BASE_URL + "/assets/favicon.svg",
    "description": f"Student-run AI literacy club at {COLLEGE} helping every major learn to use AI well.",
    "parentOrganization": {
        "@type": "CollegeOrUniversity",
        "name": COLLEGE,
        "url": "https://www.hws.edu/",
    },
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
    "name": "HWS AI Club Weekly Meeting",
    "description": "Beginner-friendly weekly AI workshop and meeting for HWS AI Club, open to all majors and class years — no experience required.",
    "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
    "eventStatus": "https://schema.org/EventScheduled",
    "location": {
        "@type": "Place",
        "name": "Sanford Room, " + COLLEGE,
        "address": {"@type": "PostalAddress", "addressLocality": "Geneva", "addressRegion": "NY", "addressCountry": "US"},
    },
    "organizer": {"@type": "Organization", "name": "HWS AI Club", "url": BASE_URL + "/"},
    "eventSchedule": {
        "@type": "Schedule",
        "repeatFrequency": "P1W",
        "byDay": "https://schema.org/Sunday",
        "startTime": MEETING_START,
        "endTime": MEETING_END,
        "scheduleTimezone": MEETING_TZ,
    },
}


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------
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


def founder_avatar(f, extra_class=""):
    """Photo if one exists, else the initials tile. Same shape either way."""
    cls = f"team-avatar {extra_class} {f['avatar']}".strip()
    photo = founder_photo(f)
    if photo:
        return (f'<img class="{cls} founder-photo" src="{photo}" alt="{esc(f["name"])}" '
                f'width="256" height="256" loading="lazy" decoding="async">')
    return f'<span class="{cls}" aria-hidden="true">{f["initials"]}</span>'


def founder_cards():
    """Founder cards link through to their own page. Hand-authored copy in FOUNDERS
    carries intentional HTML entities, so blurb/subtitle are emitted unescaped."""
    out = []
    for f in FOUNDERS:
        out.append(
            f'<a class="card team-card founder-card" href="/founders/{f["slug"]}/">'
            f'{founder_avatar(f)}'
            f'<h3>{esc(f["name"])}</h3>'
            f'<p class="team-role">{esc(f["role"])}</p>'
            f'<p class="team-bio">{f["blurb"]}</p>'
            f'<span class="founder-more">Read more <span aria-hidden="true">&rarr;</span></span></a>'
        )
    return "\n".join(out)


def build_home():
    title = f"HWS AI Club — AI for Every Major at {COLLEGE}"
    desc = (
        f"The student-run AI club at {COLLEGE} (HWS) in {LOCATION}. Learn practical AI skills with 840 "
        "use cases across all 42 majors — no coding required. Free, open to everyone."
    )
    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": "What is the HWS AI Club?",
             "acceptedAnswer": {"@type": "Answer", "text": f"HWS AI Club is a student-run organization at {COLLEGE} that helps students of every major learn to use AI tools well, with hands-on workshops and a library of 840 AI use cases across all 42 majors."}},
            {"@type": "Question", "name": "Do I need coding experience to join?",
             "acceptedAnswer": {"@type": "Answer", "text": "No. The club is beginner-friendly and requires no coding or prior AI experience — just curiosity."}},
            {"@type": "Question", "name": "When and where does the HWS AI Club meet?",
             "acceptedAnswer": {"@type": "Answer", "text": f"The club meets {MEETING} at {COLLEGE}. All majors and class years are welcome."}},
            {"@type": "Question", "name": "Is the HWS AI Club free to join?",
             "acceptedAnswer": {"@type": "Answer", "text": "Yes. The club is completely free, with no application required — just show up to a meeting."}},
            {"@type": "Question", "name": "What majors can join the HWS AI Club?",
             "acceptedAnswer": {"@type": "Answer", "text": f"All 42 majors offered at {COLLEGE}. The club's use-case library has 20 AI use cases tailored to each individual major."}},
            {"@type": "Question", "name": "Do I need a laptop or special software to join?",
             "acceptedAnswer": {"@type": "Answer", "text": "No special software — just a free account with a tool like ChatGPT, Claude, or Gemini. Bringing a laptop helps, but it isn't required."}},
            {"@type": "Question", "name": "How do I join the HWS AI Club's online community?",
             "acceptedAnswer": {"@type": "Answer", "text": f"Through the club's free Skool community at {SKOOL_URL}, which is open to every HWS student for classroom material, discussion, and the events calendar."}},
        ],
    }
    website = {"@context": "https://schema.org", "@type": "WebSite", "name": "HWS AI Club",
               "url": BASE_URL + "/",
               "potentialAction": {"@type": "SearchAction",
                                   "target": BASE_URL + "/majors/?q={search_term_string}",
                                   "query-input": "required name=search_term_string"}}

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
        <a class="btn-primary" href="/#join">Join the Club</a>
        <a class="btn-secondary" href="/majors/">Browse Use Cases</a>
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
        <a class="btn-primary" href="/#join">Get Started Today</a>
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
      <div class="library-cta"><a class="btn-primary" href="/majors/">Find your major &rarr;</a></div>
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
      <a class="btn-secondary" href="/majors/">Start with your major&rsquo;s use cases &rarr;</a>
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
        <a class="btn-primary" href="{SKOOL_URL}" target="_blank" rel="noopener">Join the Skool community <span aria-hidden="true">&#8599;</span></a>
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
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    (SITE / "index.html").write_text(head(title, desc, "/", [ORG_JSONLD, website, faq, EVENT_JSONLD]) + "\n" + body + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Majors index
# ---------------------------------------------------------------------------
def build_majors_index():
    title = f"AI Use Cases by Major — HWS AI Club | {COLLEGE}"
    desc = (
        f"Browse AI use cases for all 42 majors at {COLLEGE} (HWS). Pick your major to see 20 practical, "
        "difficulty-rated AI use cases with tutorial videos."
    )
    cards = "\n".join(
        f'<a class="major-card" href="/majors/{esc(m["slug"])}/"><span>{esc(m["name"])}</span>'
        f'<span class="arrow" aria-hidden="true">&rarr;</span></a>'
        for m in DATA["majors"]
    )
    itemlist = {
        "@context": "https://schema.org", "@type": "ItemList", "name": "AI Use Cases by Major at HWS",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": m["name"], "url": f"{BASE_URL}/majors/{m['slug']}/"}
            for i, m in enumerate(DATA["majors"])
        ],
    }
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
  <div class="majors-grid" id="majors-grid">
{cards}
  </div>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    (SITE / "majors").mkdir(exist_ok=True)
    (SITE / "majors" / "index.html").write_text(
        head(title, desc, "/majors/", [crumbs, itemlist]) + "\n" + body + "\n", encoding="utf-8"
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


def video_jsonld(slug, m):
    """One VideoObject per distinct tutorial linked from this major's use cases
    (several cards on a page often point at the same video — dedupe by id)."""
    seen = {}
    for uc in m["useCases"]:
        vid = video_id(slug, uc)
        if vid in seen:
            continue
        meta = _VMETA.get(vid)
        if not meta:
            continue
        raw_date = meta.get("date") or ""
        obj = {
            "@context": "https://schema.org",
            "@type": "VideoObject",
            "name": meta.get("title", "AI tutorial video"),
            "description": meta.get("title", "AI tutorial video"),
            "thumbnailUrl": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "contentUrl": f"https://www.youtube.com/watch?v={vid}",
            "embedUrl": f"https://www.youtube.com/embed/{vid}",
        }
        if meta.get("channel"):
            obj["creator"] = {"@type": "Person", "name": meta["channel"]}
        if len(raw_date) == 8:
            obj["uploadDate"] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        seen[vid] = obj
    return list(seen.values())


def build_major(m, prev_m, next_m):
    slug, name = m["slug"], m["name"]
    title = f"AI Use Cases for {name} Majors | HWS AI Club ({COLLEGE})"
    desc = (
        f"20 practical AI use cases for {name} students at {COLLEGE} (HWS) — rated by difficulty, "
        "each naming the exact tutorial video it links to and what you take away. From summarizing readings to advanced projects."
    )
    cards = "\n".join(uc_card(slug, uc) for uc in m["useCases"])
    filters = "".join(
        f'<button type="button" class="filter-btn" data-filter="{f}" aria-pressed="{"true" if f=="All" else "false"}">{f}</button>'
        for f in ["All", "Easy", "Medium", "Hard"]
    )
    siblings = " · ".join(
        f'<a href="/majors/{mm["slug"]}/">{esc(mm["name"])}</a>' for mm in DATA["majors"] if mm["slug"] != slug
    )
    crumbs = breadcrumb([("Home", "/"), ("All Majors", "/majors/"), (name, f"/majors/{slug}/")])
    itemlist = {
        "@context": "https://schema.org", "@type": "ItemList",
        "name": f"AI Use Cases for {name} at HWS",
        "itemListElement": [
            {"@type": "ListItem", "position": uc["number"], "name": uc["title"],
             "description": card_text(slug, uc)[0]}
            for uc in m["useCases"]
        ],
    }
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": uc["title"],
             "acceptedAnswer": {"@type": "Answer", "text": card_text(slug, uc)[0]}}
            for uc in m["useCases"]
        ],
    }
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
  <p class="page-lede">20 practical, difficulty-rated ways {esc(name)} students at {COLLEGE} can use AI &mdash; each naming the exact tutorial it links to and what you&rsquo;ll take away. Click any card to watch it.</p>
  <p class="policy-note"><strong>Before you use these on graded work:</strong> check your professor&rsquo;s policy on AI.
  It differs by course, and these examples are study aids &mdash; not permission.</p>
  <h2 class="usecases-heading">All {esc(name)} AI use cases</h2>
  <div class="difficulty-filter" role="group" aria-label="Filter by difficulty">{filters}</div>
  <div class="usecases-grid" id="usecases-grid">
{cards}
  </div>
  <nav class="major-pager" aria-label="More majors">{nav_more}</nav>
  <section class="sibling-majors">
    <h2>Explore AI use cases for other majors at HWS</h2>
    <p class="siblings">{siblings}</p>
  </section>
</main>
{site_footer()}
{scripts()}
</body>
</html>"""
    d = SITE / "majors" / slug
    d.mkdir(parents=True, exist_ok=True)
    jsonld = [crumbs, itemlist, faq] + video_jsonld(slug, m)
    (d / "index.html").write_text(head(title, desc, f"/majors/{slug}/", jsonld) + "\n" + body + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Per-founder pages
# ---------------------------------------------------------------------------
def build_founder(f, others):
    slug, name = f["slug"], f["name"]
    title = f"{name} — {f['role']}, HWS AI Club | {COLLEGE}"
    affiliation = [{"@type": "EducationalOrganization", "name": "HWS AI Club", "url": BASE_URL + "/"}]
    if f.get("school"):  # currently enrolled — affiliation, not alumniOf
        affiliation.append({"@type": "CollegeOrUniversity", "name": f["school"][0], "url": f["school"][1]})
    person = {
        "@context": "https://schema.org", "@type": "Person",
        "name": name,
        "url": f"{BASE_URL}/founders/{slug}/",
        "jobTitle": f["role"],
        "description": f["meta"],
        "affiliation": affiliation if len(affiliation) > 1 else affiliation[0],
        "alumniOf": {"@type": "CollegeOrUniversity", "name": COLLEGE, "url": "https://www.hws.edu/"},
        "worksFor": {"@type": "Organization", "name": LICOM[0], "url": LICOM[1]},
        "sameAs": [url for _, url in f["links"] if url not in ORG_URLS],
    }
    if f.get("memberOf"):
        person["memberOf"] = {"@type": "Organization", "name": f["memberOf"][0], "url": f["memberOf"][1]}
    if founder_photo(f):
        person["image"] = BASE_URL + f["photo"]
    crumbs = breadcrumb([("Home", "/"), ("Founders", "/#founders"), (name, f"/founders/{slug}/")])

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
        f'<a class="founder-link" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)} '
        f'<span aria-hidden="true">&#8599;</span></a>'
        for label, url in f["links"]
    )
    siblings = "".join(
        f'<a class="pager next" href="/founders/{o["slug"]}/">{esc(o["name"])} &rarr;</a>'
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
        <iframe style="border-radius:12px" src="https://open.spotify.com/embed/track/{esc(s['spotify_track_id'])}?utm_source=generator"
                width="100%" height="152" frameborder="0" allowfullscreen
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                loading="lazy" title="Spotify player: {esc(s['title'])} by {esc(s['artist'])}"></iframe>
      </div>"""

    body = f"""<body class="view-inner">
{site_header()}
<main id="main" class="page">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> / <a href="/#founders">Founders</a> / {esc(name)}</nav>
  <div class="founder-hero">
    {founder_avatar(f, "founder-avatar")}
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
      </div>{song_html}
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
        head(title, f["meta"], f"/founders/{slug}/", [crumbs, person]) + "\n" + body + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# robots / sitemap / headers / og-image / videos.js
# ---------------------------------------------------------------------------
def build_robots():
    lines = ["User-agent: *", "Allow: /", "Disallow: /showcase.html",
              "Disallow: /data.json", "Disallow: /data/videos-config.json", ""]
    for bot in AI_BOTS:
        lines += [f"User-agent: {bot}", "Allow: /", ""]
    lines.append("Sitemap: " + BASE_URL + "/sitemap.xml")
    (SITE / "robots.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_llms_txt():
    """llms.txt (emerging llmstxt.org convention) — a plain-language map of the
    site for AI agents/assistants that consult it, mirroring what's in robots.txt
    + sitemap.xml but in a format meant to be read, not just crawled."""
    majors = "\n".join(f"- [{m['name']}]({BASE_URL}/majors/{m['slug']}/)" for m in DATA["majors"])
    founders = "\n".join(f"- [{f['name']}, {f['role']}]({BASE_URL}/founders/{f['slug']}/)" for f in FOUNDERS)
    text = f"""# HWS AI Club

> Student-run AI literacy club at {COLLEGE} (HWS) in {LOCATION}. Free and open to \
students in all 42 majors, no coding experience required. {MEETING}.

HWS AI Club maintains a library of 840 practical AI use cases — 20 per major, rated \
Easy, Medium, or Hard — across all 42 majors offered at HWS. Each use case names a \
specific tutorial video and includes a ready-to-paste starter prompt.

## Key pages

- [Homepage]({BASE_URL}/): what the club does, the team, and how to join.
- [All Majors]({BASE_URL}/majors/): directory of all 42 majors with AI use cases.
- [Sitemap]({BASE_URL}/sitemap.xml)

## Majors

{majors}

## Founders

{founders}
"""
    (SITE / "llms.txt").write_text(text, encoding="utf-8")


def build_sitemap():
    urls = [("/", "1.0"), ("/majors/", "0.9")]
    urls += [(f"/majors/{m['slug']}/", "0.8") for m in DATA["majors"]]
    urls += [(f"/founders/{f['slug']}/", "0.6") for f in FOUNDERS]
    items = "\n".join(
        f"  <url><loc>{BASE_URL}{p}</loc><lastmod>{BUILD_DATE}</lastmod><priority>{pr}</priority></url>"
        for p, pr in urls
    )
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + items + "\n</urlset>\n",
        encoding="utf-8",
    )
    return len(urls)


def build_headers():
    (SITE / "_headers").write_text(
        "/*\n  X-Robots-Tag: all\n\n/showcase.html\n  X-Robots-Tag: noindex\n", encoding="utf-8"
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
    sizes = {"favicon-16x16.png": 16, "favicon-32x32.png": 32, "apple-touch-icon.png": 180}
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
    for m in majors:
        assert (SITE / "majors" / m["slug"] / "index.html").exists()
    for f in FOUNDERS:
        assert (SITE / "founders" / f["slug"] / "index.html").exists()
    print("HWS AI Club static build complete")
    print(f"  homepage + majors index + {len(majors)} major pages + {len(FOUNDERS)} founder pages")
    print(f"  sitemap: {n} urls | robots.txt (+ AI bot allow rules), llms.txt, _headers written")
    print(f"  js/videos.js regenerated from config | og-image: {og} | favicons: {ico} | manifest written")


if __name__ == "__main__":
    main()
