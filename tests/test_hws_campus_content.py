"""Tests for the permission-gated HWS campus events and clubs hub."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts import sync_hws_content as sync


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class EventFeedTests(unittest.TestCase):
    def setUp(self):
        self.xml = (FIXTURES / "hws-calendar.xml").read_text(encoding="utf-8")
        self.now = datetime(2026, 8, 26, tzinfo=timezone.utc)

    def test_parses_all_day_timed_recurring_and_dst_events(self):
        events = sync.parse_event_rss(self.xml, now=self.now)
        self.assertEqual(["all-day", "timed"], [event["id"] for event in events])

        all_day, timed = events
        self.assertTrue(all_day["allDay"])
        self.assertEqual("2026-09-01", all_day["start"])
        self.assertEqual("America/New_York", all_day["timezone"])
        self.assertEqual("Welcome HWS students.", all_day["summary"])

        self.assertFalse(timed["allDay"])
        self.assertEqual("2026-11-02T17:00:00-05:00", timed["start"])
        self.assertEqual("Rosenberg Hall, Room 101", timed["location"])
        self.assertEqual("https://events.hws.edu/register/workshop", timed["ticketUrl"])

    def test_rejects_cancelled_and_observed_0202_date(self):
        events = sync.parse_event_rss(self.xml, now=self.now)
        ids = {event["id"] for event in events}
        self.assertNotIn("cancelled", ids)
        self.assertNotIn("bad-date", ids)

    def test_duplicate_ids_fail_complete_snapshot_validation(self):
        events = sync.parse_event_rss(self.xml, now=self.now)
        with self.assertRaises(sync.SnapshotValidationError):
            sync.validate_events(events + [events[0]], minimum=1, now=self.now)

    def test_past_events_fail_complete_snapshot_validation(self):
        events = sync.parse_event_rss(self.xml, now=self.now)
        past = dict(events[0], start="2025-01-01", end="2025-01-02")
        with self.assertRaises(sync.SnapshotValidationError):
            sync.validate_events([past], minimum=1, now=self.now)

    def test_undersized_snapshot_never_replaces_previous_valid_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "events.json"
            previous = {"source": {"recordCount": 10}, "events": [{"id": "keep"}]}
            target.write_text(json.dumps(previous), encoding="utf-8")

            with self.assertRaises(sync.SnapshotValidationError):
                sync.save_events_snapshot(target, [], "https://example.hws.edu/feed", minimum=10)

            self.assertEqual(previous, json.loads(target.read_text(encoding="utf-8")))


class ClubDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.html = (FIXTURES / "hws-clubs.html").read_text(encoding="utf-8")

    def test_parses_only_directory_section_and_normalizes_nested_markup(self):
        clubs = sync.parse_clubs_html(self.html)
        by_name = {club["name"]: club for club in clubs}

        self.assertNotIn("Wrong Club", by_name)
        self.assertIn("AI Club", by_name)
        self.assertTrue(by_name["AI Club"]["isAiClub"])
        self.assertIsNone(by_name["AI Club"]["officialUrl"])
        self.assertEqual("Pre-professional clubs", by_name["Finance Society"]["category"])
        self.assertIsNone(by_name["Nested Unsafe Club"]["officialUrl"])
        self.assertEqual(1, [club["name"] for club in clubs].count("Campus Kitchens"))

    def test_undersized_club_download_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "clubs.json"
            target.write_text('{"clubs":[{"name":"Keep Me"}]}', encoding="utf-8")
            with self.assertRaises(sync.SnapshotValidationError):
                sync.save_clubs_snapshot(target, [], "https://www.hws.edu/clubs", minimum=80)
            self.assertIn("Keep Me", target.read_text(encoding="utf-8"))


class GeneratedCampusHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["python", "scripts/build_site.py"], cwd=ROOT, check=True, capture_output=True)
        cls.page = (ROOT / "site" / "events" / "index.html").read_text(encoding="utf-8")

    def test_page_contains_hub_controls_sources_attribution_and_skool(self):
        for expected in (
            "HWS Events Calendar",
            'id="event-search"',
            'id="event-category"',
            'id="events-calendar"',
            'id="calendar-prev"',
            'id="calendar-today"',
            'id="calendar-next"',
            'id="calendar-month-label"',
            'id="calendar-grid"',
            'id="events-mobile-agenda"',
            'id="event-dialog"',
            'id="event-dialog-close"',
            'class="event-fallback-agenda"',
            "HWS clubs and organizations",
            'id="club-search"',
            'id="club-category"',
            "Campus information is sourced from Hobart and William Smith Colleges.",
            "https://www.hws.edu/news/calendar.aspx",
            "https://www.hws.edu/offices/student-engagement/clubs-and-organizations.aspx",
            'data-cta="skool-join"',
            'src="/js/campus-hub.js"',
        ):
            self.assertIn(expected, self.page)
        self.assertNotIn('id="event-date"', self.page)
        self.assertNotIn('id="events-load-more"', self.page)

    def test_calendar_comes_before_club_meeting(self):
        calendar_pos = self.page.index('id="upcoming-hws-events"')
        club_meeting_pos = self.page.index('id="ai-club-meeting"')
        self.assertLess(calendar_pos, club_meeting_pos)
        self.assertNotIn('class="events-hero"', self.page)
        self.assertIn('<h1 id="upcoming-hws-events">HWS Events Calendar</h1>', self.page)

    def test_static_fallback_contains_exactly_twenty_four_events(self):
        self.assertEqual(24, self.page.count('class="event-fallback-item"'))

    def test_club_mirror_is_permission_gated_by_default(self):
        config = json.loads((ROOT / "site" / "data" / "hws-content-config.json").read_text(encoding="utf-8"))
        self.assertFalse(config["publishClubDirectory"])
        self.assertIn("Written HWS approval is required before this directory is published", self.page)

    def test_imported_events_do_not_create_event_jsonld(self):
        self.assertEqual(1, self.page.count('"@type": "Event"'))
        self.assertNotIn('"@type": "FAQPage"', self.page)
        self.assertNotIn('"@type": "ItemList"', self.page)

    def test_title_canonical_and_static_content_are_present(self):
        self.assertIn("<title>HWS Events Calendar &amp; Campus Activities | HWS AI Club</title>", self.page)
        self.assertIn('<link rel="canonical" href="https://www.hwsaiclub.com/events/">', self.page)
        self.assertIn('<h1 id="upcoming-hws-events">HWS Events Calendar</h1>', self.page)
        self.assertIn("Find upcoming HWS events at Hobart and William Smith Colleges", self.page)
        self.assertIn("Where can I find upcoming HWS events?", self.page)
        self.assertIn("Is this the HWS academic calendar?", self.page)
        self.assertIn("Where can HWS students find clubs and activities?", self.page)
        self.assertIn("https://www.hws.edu/catalogue/default.aspx", self.page)
        self.assertIn('data-campus-event-id=', self.page)
        self.assertIn('<time datetime=', self.page)

    def test_runtime_never_injects_source_html(self):
        javascript = (ROOT / "site" / "js" / "campus-hub.js").read_text(encoding="utf-8")
        self.assertNotIn(".innerHTML", javascript)
        self.assertIn("textContent", javascript)
        self.assertIn("AbortController", javascript)

    def test_runtime_has_calendar_dialog_and_progressive_enhancement_contracts(self):
        javascript = (ROOT / "site" / "js" / "campus-hub.js").read_text(encoding="utf-8")
        for expected in (
            "showModal",
            'event.key === "Escape"',
            "dialogOpener.focus",
            'filter_type: "month_navigation"',
            "active_month",
            "renderMobileAgenda",
            "renderMonthGrid",
            "eventDayKeys",
            "mondayFirstMonthMatrix",
            "shiftMonth",
            "trapFallbackFocus",
            'classList.add("calendar-enhanced")',
        ):
            self.assertIn(expected, javascript)

        accepted_pos = javascript.index('classList.add("calendar-enhanced")')
        set_events_pos = javascript.index("function setEvents")
        self.assertGreater(accepted_pos, set_events_pos)

    def test_runtime_documents_inclusive_and_exclusive_date_placement(self):
        javascript = (ROOT / "site" / "js" / "campus-hub.js").read_text(encoding="utf-8")
        self.assertIn("all-day end dates are inclusive", javascript)
        self.assertIn("timed end dates are exclusive", javascript)
        self.assertIn("end.getTime() - 1", javascript)


if __name__ == "__main__":
    unittest.main()
