"""Regression checks for the domain migration and minimal-schema policy.

Run with: python -m unittest tests.test_seo_migration
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_site.py"
NETLIFY = ROOT / "netlify.toml"
PREFERRED_ORIGIN = "https://www.hwsaiclub.com"
LEGACY_ORIGIN = "https://hws-ai-club.netlify.app"


class SeoMigrationSourceTests(unittest.TestCase):
    def setUp(self):
        self.builder = BUILDER.read_text(encoding="utf-8")
        self.netlify = NETLIFY.read_text(encoding="utf-8")

    def test_builder_uses_the_preferred_custom_domain(self):
        self.assertIn(f'BASE_URL = "{PREFERRED_ORIGIN}"', self.builder)
        self.assertNotIn(f'BASE_URL = "{LEGACY_ORIGIN}"', self.builder)

    def test_legacy_netlify_host_redirects_path_for_path(self):
        self.assertIn('from = "https://hws-ai-club.netlify.app/*"', self.netlify)
        self.assertIn('to = "https://www.hwsaiclub.com/:splat"', self.netlify)
        self.assertIn('status = 301', self.netlify)
        self.assertIn('force = true', self.netlify)

    def test_retired_search_action_markup_is_not_generated(self):
        self.assertNotIn('"@type": "SearchAction"', self.builder)

    def test_low_value_faq_and_item_list_markup_is_not_generated(self):
        self.assertNotIn('"@type": "FAQPage"', self.builder)
        self.assertNotIn('"@type": "ItemList"', self.builder)

    def test_college_entity_does_not_use_an_unverified_external_identifier(self):
        self.assertNotIn('COLLEGE_ID = "https://www.hws.edu/#organization"', self.builder)

    def test_ai_at_hws_resource_hub_is_generated_and_cited(self):
        self.assertIn('def build_ai_resources_page():', self.builder)
        self.assertIn('"/resources/ai-at-hws/"', self.builder)
        self.assertIn('https://library.hws.edu/ai_tools', self.builder)
        self.assertIn('https://careerservices.hws.edu/resources/using-ai-in-your-career-development/', self.builder)

    def test_generated_metadata_stays_concise(self):
        violations = []
        for page in (ROOT / "site").rglob("index.html"):
            rendered = page.read_text(encoding="utf-8")
            title = re.search(r"<title>(.*?)</title>", rendered).group(1)
            description = re.search(r'<meta name="description" content="(.*?)">', rendered).group(1)
            if len(title) > 70 or len(description) > 160:
                violations.append(f"{page.relative_to(ROOT)} ({len(title)}/{len(description)})")
        self.assertEqual([], violations, "metadata exceeds the 70/160 review thresholds: " + ", ".join(violations))

    def test_primary_join_entrypoints_lead_directly_to_skool(self):
        homepage = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        for stale_cta in ("nav-join", "hero-join", "no-experience-join"):
            self.assertNotIn(f'data-cta="{stale_cta}"', homepage)

        join_section = re.search(
            r'<section class="lp-section lp-join" id="join">(.*?)</section>',
            homepage,
            re.DOTALL,
        ).group(1)
        self.assertIn('href="https://www.skool.com/hws-ai-club-7506"', join_section)
        self.assertIn('data-cta="skool-join"', join_section)


if __name__ == "__main__":
    unittest.main()
