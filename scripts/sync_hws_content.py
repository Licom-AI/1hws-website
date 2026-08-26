#!/usr/bin/env python3
"""Synchronize validated HWS calendar and club-directory snapshots.

Only documented/public HWS sources are read. Club publication is permission-gated
by ``site/data/hws-content-config.json``; when approval is disabled, club data can
be checked but is never written into the deployable ``site`` directory.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "site" / "data"
CONFIG_PATH = DATA_DIR / "hws-content-config.json"
EVENTS_PATH = DATA_DIR / "hws-events.json"
CLUBS_PATH = DATA_DIR / "hws-clubs.json"

CALENDAR_ID = "d4da22d5-7840-45cf-91c3-023390a85fc8"
CALENDAR_PAGE_URL = "https://www.hws.edu/news/calendar.aspx"
CALENDAR_API_URL = f"https://api.calendar.moderncampus.net/pubcalendar/{CALENDAR_ID}"
CLUBS_URL = "https://www.hws.edu/offices/student-engagement/clubs-and-organizations.aspx"
TIMEZONE_NAME = "America/New_York"
CAL_NS = "https://moderncampus.com/Data/cal/"
MIN_EVENTS = 10
MIN_CLUBS = 80
SUPPORTED_STATUSES = {"CONFIRMED", "TENTATIVE"}
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
INVALID_XML_REFERENCE = re.compile(
    r"&#(?:x0*(?:[0-8BCEF]|1[0-9A-F])|0*(?:[0-8]|1[1-2]|1[4-9]|2[0-9]|3[01]));",
    re.IGNORECASE,
)


class SnapshotValidationError(ValueError):
    """Raised before an invalid or undersized snapshot can replace good data."""


def clean_text(value: str | None) -> str:
    """Return normalized plain text with markup and controls removed."""
    value = unescape(value or "")
    value = TAG_RE.sub(" ", value)
    value = CONTROL_CHARS.sub(" ", value)
    value = WHITESPACE_RE.sub(" ", value).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", value)


def approved_url(value: str | None) -> str | None:
    """Keep only HTTPS URLs on explicitly approved institutional hosts."""
    value = clean_text(value)
    if not value:
        return None
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    allowed = (
        host == "hws.edu"
        or host.endswith(".hws.edu")
        or host == "hws.campuslabs.com"
        or host == "hws.joinhandshake.com"
        or host == "forms.office.com"
        or host == "docs.google.com"
        or host == "www.givecampus.com"
    )
    return value if parsed.scheme == "https" and allowed else None


def _strict_date(value: str) -> date:
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value):
        raise ValueError(f"malformed date: {value}")
    return date.fromisoformat(value)


def _normalized_event_time(value: str, zone: ZoneInfo) -> tuple[str, datetime, bool]:
    """Normalize a Modern Campus all-day date or ISO instant."""
    value = clean_text(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = _strict_date(value)
        local = datetime.combine(day, time.min, tzinfo=zone)
        return day.isoformat(), local, True

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    local = parsed.astimezone(zone)
    return local.isoformat(timespec="seconds"), local, False


def _child_text(node: ET.Element, name: str) -> str:
    child = node.find(f"{{{CAL_NS}}}{name}")
    return "" if child is None else "".join(child.itertext())


def parse_event_rss(xml_text: str, now: datetime | None = None) -> list[dict]:
    """Parse documented Modern Campus RSS into the normalized event model."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    zone = ZoneInfo(TIMEZONE_NAME)
    # A malformed XML control-character reference has appeared in source content;
    # remove only XML-forbidden references before parsing, then sanitize all text.
    xml_text = INVALID_XML_REFERENCE.sub(" ", xml_text)
    root = ET.fromstring(xml_text)
    records: list[dict] = []

    for item in root.findall("./channel/item"):
        status = clean_text(_child_text(item, "status")).upper()
        if status not in SUPPORTED_STATUSES:
            continue
        try:
            start, start_dt, all_day = _normalized_event_time(_child_text(item, "start"), zone)
            end, end_dt, end_all_day = _normalized_event_time(_child_text(item, "end"), zone)
        except (TypeError, ValueError):
            continue
        now_local = now.astimezone(zone)
        is_past = end_dt.date() < now_local.date() if end_all_day else end_dt < now_local
        if all_day != end_all_day or end_dt < start_dt or is_past:
            continue

        event_id = clean_text(_child_text(item, "guid"))
        title = clean_text(item.findtext("title"))
        source_url = approved_url(item.findtext("link"))
        if not event_id or not title or not source_url:
            continue

        location_parts = [clean_text(_child_text(item, "location")), clean_text(_child_text(item, "locationRoom"))]
        location = ", ".join(part for index, part in enumerate(location_parts) if part and part not in location_parts[:index])
        records.append({
            "id": event_id,
            "title": title,
            "summary": clean_text(item.findtext("description")),
            "start": start,
            "end": end,
            "allDay": all_day,
            "timezone": TIMEZONE_NAME,
            "category": clean_text(_child_text(item, "calendar")) or "HWS event",
            "location": location,
            "organizer": clean_text(_child_text(item, "organizer")),
            "status": status,
            "sourceUrl": source_url,
            "ticketUrl": approved_url(_child_text(item, "ticketUrl")),
        })

    # RSS uses one GUID for every occurrence of a recurring event. Preserve that
    # authority-derived GUID but append a stable start-time digest to each repeated
    # occurrence so DOM IDs, caches, and validation remain unambiguous.
    id_counts: dict[str, int] = {}
    for record in records:
        id_counts[record["id"]] = id_counts.get(record["id"], 0) + 1
    for record in records:
        if id_counts[record["id"]] > 1:
            base_id = record["id"]
            occurrence = sha256(record["start"].encode("utf-8")).hexdigest()[:12]
            record["id"] = f"{base_id}--{occurrence}"

    records.sort(key=lambda event: (event["start"], event["title"].casefold()))
    return records


class _ClubDirectoryParser(HTMLParser):
    """Small purpose-built parser restricted to ``section#campusevents``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_directory = False
        self.section_level = 0
        self.in_heading = False
        self.heading_parts: list[str] = []
        self.category = ""
        self.li_stack: list[dict] = []
        self.clubs: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "section":
            if not self.in_directory and attrs_dict.get("id") == "campusevents":
                self.in_directory = True
                self.section_level = 1
                return
            if self.in_directory:
                self.section_level += 1
        if not self.in_directory:
            return
        if tag == "h4":
            self.in_heading = True
            self.heading_parts = []
        elif tag == "li":
            self.li_stack.append({"parts": [], "href": None, "category": self.category})
        elif tag == "a" and self.li_stack:
            self.li_stack[-1]["href"] = attrs_dict.get("href")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_directory:
            return
        if tag == "h4" and self.in_heading:
            self.category = clean_text(" ".join(self.heading_parts))
            self.in_heading = False
        elif tag == "li" and self.li_stack:
            raw = self.li_stack.pop()
            name = clean_text(" ".join(raw["parts"]))
            if name and raw["category"]:
                self.clubs.append({
                    "name": name,
                    "category": raw["category"],
                    "officialUrl": approved_url(raw["href"]),
                    "isAiClub": name.casefold() in {"ai club", "hws ai club", "artificial intelligence club"},
                })
        if tag == "section":
            self.section_level -= 1
            if self.section_level == 0:
                self.in_directory = False

    def handle_data(self, data: str) -> None:
        if not self.in_directory:
            return
        if self.in_heading:
            self.heading_parts.append(data)
        elif self.li_stack:
            # Add to the innermost list item only so malformed nested lists do not
            # concatenate child club names into their parents.
            self.li_stack[-1]["parts"].append(data)


def parse_clubs_html(html_text: str) -> list[dict]:
    parser = _ClubDirectoryParser()
    parser.feed(CONTROL_CHARS.sub(" ", html_text))
    unique: dict[str, dict] = {}
    for club in parser.clubs:
        unique.setdefault(club["name"].casefold(), club)
    return sorted(unique.values(), key=lambda club: (club["category"].casefold(), club["name"].casefold()))


def validate_events(events: Iterable[dict], minimum: int = MIN_EVENTS, now: datetime | None = None) -> list[dict]:
    records = list(events)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if len(records) < minimum:
        raise SnapshotValidationError(f"event snapshot has {len(records)} records; minimum is {minimum}")
    ids = [record.get("id") for record in records]
    if len(ids) != len(set(ids)):
        raise SnapshotValidationError("event snapshot contains duplicate IDs")
    required = {"id", "title", "start", "end", "allDay", "timezone", "category", "status", "sourceUrl"}
    for record in records:
        if not required.issubset(record) or record.get("status") not in SUPPORTED_STATUSES:
            raise SnapshotValidationError(f"invalid event record: {record.get('id', '<missing id>')}")
        try:
            _, start_dt, start_all_day = _normalized_event_time(record["start"], ZoneInfo(TIMEZONE_NAME))
            _, end_dt, end_all_day = _normalized_event_time(record["end"], ZoneInfo(TIMEZONE_NAME))
        except (TypeError, ValueError) as exc:
            raise SnapshotValidationError(f"invalid event date for {record['id']}") from exc
        now_local = now.astimezone(ZoneInfo(TIMEZONE_NAME))
        is_past = end_dt.date() < now_local.date() if end_all_day else end_dt < now_local
        if start_all_day != bool(record["allDay"]) or end_all_day != bool(record["allDay"]) or end_dt < start_dt or is_past:
            raise SnapshotValidationError(f"past or inconsistent event date for {record['id']}")
        if approved_url(record.get("sourceUrl")) != record.get("sourceUrl"):
            raise SnapshotValidationError(f"unapproved event URL for {record['id']}")
    return records


def validate_clubs(clubs: Iterable[dict], minimum: int = MIN_CLUBS, minimum_categories: int = 14) -> list[dict]:
    records = list(clubs)
    if len(records) < minimum:
        raise SnapshotValidationError(f"club snapshot has {len(records)} records; minimum is {minimum}")
    names = [clean_text(record.get("name")) for record in records]
    if any(not name for name in names) or len(names) != len({name.casefold() for name in names}):
        raise SnapshotValidationError("club snapshot contains missing or duplicate names")
    if any(not clean_text(record.get("category")) for record in records):
        raise SnapshotValidationError("club snapshot contains a missing category")
    categories = {clean_text(record["category"]).casefold() for record in records}
    if len(categories) < minimum_categories:
        raise SnapshotValidationError(
            f"club snapshot has {len(categories)} categories; minimum is {minimum_categories}"
        )
    return records


def _atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _source_metadata(source_url: str, records: list[dict], source_hash: str | None = None) -> dict:
    if source_hash is None:
        canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        source_hash = sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "url": source_url,
        "retrievedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "recordCount": len(records),
        "sha256": source_hash,
    }


def save_events_snapshot(path: Path, events: Iterable[dict], source_url: str, minimum: int = MIN_EVENTS,
                         source_hash: str | None = None) -> None:
    records = validate_events(events, minimum=minimum)
    _atomic_json_write(path, {"source": _source_metadata(source_url, records, source_hash), "events": records})


def save_clubs_snapshot(path: Path, clubs: Iterable[dict], source_url: str, minimum: int = MIN_CLUBS,
                        source_hash: str | None = None) -> None:
    records = validate_clubs(clubs, minimum=minimum)
    _atomic_json_write(path, {"source": _source_metadata(source_url, records, source_hash), "clubs": records})


def _download(url: str, timeout: float = 15.0) -> str:
    request = Request(url, headers={"User-Agent": "HWS-AI-Club-content-sync/1.0 (+https://www.hwsaiclub.com/)"})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            charset = response.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")


def _event_feed_url(today: date | None = None) -> str:
    today = today or date.today()
    end = today + timedelta(days=90)
    page = quote(CALENDAR_PAGE_URL, safe="")
    return (
        f"{CALENDAR_API_URL}/rss?url={page}&hash=true&text=true"
        f"&start={today.isoformat()}&end={end.isoformat()}"
    )


def _config() -> dict:
    if not CONFIG_PATH.exists():
        return {"publishClubDirectory": False}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def sync_events(check_only: bool = False) -> int:
    source_url = _event_feed_url()
    raw = _download(source_url)
    records = validate_events(parse_event_rss(raw), minimum=MIN_EVENTS)
    if not check_only:
        save_events_snapshot(EVENTS_PATH, records, source_url, source_hash=sha256(raw.encode("utf-8")).hexdigest())
    print(f"events: validated {len(records)} upcoming records" + (" (check only)" if check_only else ""))
    return len(records)


def sync_clubs(check_only: bool = False) -> int:
    raw = _download(CLUBS_URL)
    records = validate_clubs(parse_clubs_html(raw), minimum=MIN_CLUBS)
    approved = bool(_config().get("publishClubDirectory"))
    if not check_only and not approved:
        print("clubs: validated source, but publication is disabled pending written HWS approval")
    elif not check_only:
        save_clubs_snapshot(CLUBS_PATH, records, CLUBS_URL, source_hash=sha256(raw.encode("utf-8")).hexdigest())
    else:
        print(f"clubs: validated {len(records)} records (check only; nothing written)")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--events-only", action="store_true", help="sync/check only calendar events")
    mode.add_argument("--clubs-only", action="store_true", help="sync/check only the clubs directory")
    parser.add_argument("--check", action="store_true", help="download and validate without replacing snapshots")
    args = parser.parse_args()

    try:
        if args.clubs_only:
            sync_clubs(check_only=args.check)
        elif args.events_only:
            sync_events(check_only=args.check)
        else:
            sync_events(check_only=args.check)
            sync_clubs(check_only=True if not _config().get("publishClubDirectory") else args.check)
    except (ET.ParseError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"sync failed; existing snapshots were preserved: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
