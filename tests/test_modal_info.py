import unittest
from components.source_metadata_popover import build_modal_info, CHART_METADATA


class TestBuildModalInfo(unittest.TestCase):
    """Test the build_modal_info function."""

    def setUp(self):
        """Create mock source_meta for testing."""
        self.source_meta = {
            "boost_source_urls": [
                {
                    "country_name": "Kenya",
                    "source_url": "https://boost.worldbank.org/kenya",
                    "earliest_year": 2010,
                    "latest_year": 2020,
                }
            ],
            "indicator_availability": [
                {
                    "country_name": "Kenya",
                    "indicator_key": "poverty_rate",
                    "earliest_year": 2012,
                    "latest_year": 2019,
                }
            ],
            "source_urls_by_country": {
                "Kenya": {
                    "boost": "https://boost.worldbank.org/kenya",
                    "poverty_rate": "https://pip.worldbank.org",
                }
            },
        }

    def test_build_modal_info_single_source(self):
        """Test building info for chart with single source."""
        chart_id = "overview-total"
        country = "Kenya"

        info = build_modal_info(chart_id, country, self.source_meta)

        # Verify structure
        self.assertEqual(info["_index"], chart_id)
        self.assertEqual(info["country_name"], country)
        self.assertIn("source_sections", info)
        self.assertEqual(len(info["source_sections"]), 1)

        # Verify section content
        section = info["source_sections"][0]
        self.assertEqual(section["label"], "BOOST Expenditure Data")
        self.assertEqual(section["source_name"], "World Bank BOOST")
        self.assertEqual(section["source_url"], "https://boost.worldbank.org/kenya")
        self.assertEqual(section["coverage"], "2010–2020")

    def test_build_modal_info_multiple_sources(self):
        """Test building info for chart with multiple sources."""
        chart_id = "overview-per-capita"
        country = "Kenya"

        info = build_modal_info(chart_id, country, self.source_meta)

        # Should have 2 sources: BOOST and poverty_rate
        self.assertEqual(len(info["source_sections"]), 2)

        # Verify first source (BOOST)
        boost_section = info["source_sections"][0]
        self.assertEqual(boost_section["label"], "BOOST Expenditure Data")
        self.assertEqual(boost_section["coverage"], "2010–2020")

        # Verify second source (poverty_rate)
        poverty_section = info["source_sections"][1]
        self.assertEqual(poverty_section["label"], "Poverty Rate")
        self.assertEqual(poverty_section["coverage"], "2012–2019")
        self.assertIsNotNone(poverty_section.get("description"))

    def test_build_modal_info_preserves_chart_meta(self):
        """Test that chart metadata is preserved in info dict."""
        chart_id = "overview-per-capita"
        country = "Kenya"

        info = build_modal_info(chart_id, country, self.source_meta)

        # Verify chart metadata is included (sources field from CHART_METADATA)
        self.assertIn("sources", info)
        self.assertEqual(info["sources"], CHART_METADATA[chart_id]["sources"])

    def test_build_modal_info_missing_country(self):
        """Test graceful handling when country has no coverage data."""
        chart_id = "overview-total"
        country = "UnknownCountry"

        info = build_modal_info(chart_id, country, self.source_meta)

        # Should still have structure but no coverage data
        self.assertEqual(info["_index"], chart_id)
        self.assertEqual(info["country_name"], country)
        section = info["source_sections"][0]
        self.assertNotIn("coverage", section)

    def test_build_modal_info_fallback_to_config_url(self):
        """Test that config source_url is used when not in pipeline."""
        chart_id = "education-total"
        country = "UnknownCountry"

        info = build_modal_info(chart_id, country, self.source_meta)

        # Should fall back to configured source_url
        section = info["source_sections"][0]
        self.assertIn("source_url", section)
        # BOOST has a configured source_url in CHART_METADATA
        self.assertEqual(
            section["source_url"],
            "https://www.worldbank.org/en/programs/boost-portal/country-data"
        )


if __name__ == "__main__":
    unittest.main()
