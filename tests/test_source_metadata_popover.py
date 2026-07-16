import unittest
from components.source_metadata_popover import (
    build_modal_info,
    get_coverage_years,
    CHART_METADATA,
)


class TestGetCoverageYears(unittest.TestCase):
    """Test the get_coverage_years function."""

    def setUp(self):
        """Create mock source_meta for testing."""
        self.source_meta = {
            "boost_source_urls": [
                {
                    "country_name": "Kenya",
                    "source_url": "https://boost.worldbank.org/kenya",
                    "earliest_year": 2010,
                    "latest_year": 2020,
                },
                {
                    "country_name": "Nigeria",
                    "source_url": "https://boost.worldbank.org/nigeria",
                    "earliest_year": 2005,
                    "latest_year": 2022,
                },
            ],
            "indicator_availability": [
                {
                    "country_name": "Kenya",
                    "indicator_key": "poverty_rate",
                    "earliest_year": 2012,
                    "latest_year": 2019,
                },
                {
                    "country_name": "Kenya",
                    "indicator_key": "pefa_by_pillar",
                    "earliest_year": 2011,
                    "latest_year": 2018,
                },
                {
                    "country_name": "Nigeria",
                    "indicator_key": "poverty_rate",
                    "earliest_year": 2010,
                    "latest_year": 2021,
                },
            ],
        }

    def test_get_coverage_years_boost(self):
        """Test getting BOOST coverage years."""
        start, end = get_coverage_years("boost", "Kenya", self.source_meta)
        self.assertEqual(start, 2010)
        self.assertEqual(end, 2020)

    def test_get_coverage_years_indicator(self):
        """Test getting indicator coverage years."""
        start, end = get_coverage_years("poverty_rate", "Kenya", self.source_meta)
        self.assertEqual(start, 2012)
        self.assertEqual(end, 2019)

    def test_get_coverage_years_multiple_indicators_same_country(self):
        """Test with multiple indicators for same country."""
        start, end = get_coverage_years("pefa_by_pillar", "Kenya", self.source_meta)
        self.assertEqual(start, 2011)
        self.assertEqual(end, 2018)

    def test_get_coverage_years_different_country(self):
        """Test coverage for different country."""
        start, end = get_coverage_years("boost", "Nigeria", self.source_meta)
        # Nigeria's earliest_year is 2005, but clamped to START_YEAR (2010)
        self.assertEqual(start, 2010)
        self.assertEqual(end, 2022)

    def test_get_coverage_years_missing_country(self):
        """Test when country not in source_meta."""
        start, end = get_coverage_years("boost", "UnknownCountry", self.source_meta)
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_coverage_years_missing_indicator(self):
        """Test when indicator not available for country."""
        start, end = get_coverage_years(
            "unknown_indicator", "Kenya", self.source_meta
        )
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_coverage_years_none_source_meta(self):
        """Test with None source_meta."""
        start, end = get_coverage_years("boost", "Kenya", None)
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_coverage_years_none_country(self):
        """Test with None country."""
        start, end = get_coverage_years("boost", None, self.source_meta)
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_coverage_years_missing_year_fields(self):
        """Test with missing earliest_year or latest_year."""
        source_meta_incomplete = {
            "boost_source_urls": [
                {
                    "country_name": "Kenya",
                    "source_url": "https://example.com",
                    # missing earliest_year and latest_year
                }
            ],
            "indicator_availability": [],
        }
        start, end = get_coverage_years("boost", "Kenya", source_meta_incomplete)
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_get_coverage_years_zero_year(self):
        """Test with year value of 0 (should be None)."""
        source_meta_zero = {
            "boost_source_urls": [
                {
                    "country_name": "Kenya",
                    "source_url": "https://example.com",
                    "earliest_year": 0,
                    "latest_year": 2020,
                }
            ],
            "indicator_availability": [],
        }
        start, end = get_coverage_years("boost", "Kenya", source_meta_zero)
        self.assertIsNone(start)
        self.assertEqual(end, 2020)

    def test_get_coverage_years_before_start_year_cutoff(self):
        """Test that earliest_year is clamped to START_YEAR (2010)."""
        source_meta_early = {
            "boost_source_urls": [
                {
                    "country_name": "Kenya",
                    "source_url": "https://example.com",
                    "earliest_year": 1990,  # Before cutoff
                    "latest_year": 2020,
                }
            ],
            "indicator_availability": [],
        }
        start, end = get_coverage_years("boost", "Kenya", source_meta_early)
        # Should be clamped to START_YEAR (2010)
        self.assertEqual(start, 2010)
        self.assertEqual(end, 2020)

    def test_get_coverage_years_after_start_year_cutoff(self):
        """Test that earliest_year is kept if after START_YEAR."""
        source_meta_recent = {
            "boost_source_urls": [
                {
                    "country_name": "Kenya",
                    "source_url": "https://example.com",
                    "earliest_year": 2015,  # After cutoff
                    "latest_year": 2020,
                }
            ],
            "indicator_availability": [],
        }
        start, end = get_coverage_years("boost", "Kenya", source_meta_recent)
        # Should keep the actual value since it's after 2010
        self.assertEqual(start, 2015)
        self.assertEqual(end, 2020)


class TestBuildModalInfo(unittest.TestCase):
    """Test the build_modal_info function."""

    def setUp(self):
        """Create mock source_meta for testing."""
        self.source_meta = {
            "source_registry": [
                {"source_id": "boost", "name": "BOOST", "publisher": "World Bank",
                 "url": "https://www.worldbank.org/en/programs/boost-portal/country-data"},
                {"source_id": "world_bank_pip", "name": "Poverty and Inequality Platform",
                 "publisher": "World Bank", "url": "https://pip.worldbank.org"},
                {"source_id": "imf_weo", "name": "World Economic Outlook", "publisher": "IMF",
                 "url": "https://www.imf.org/en/Publications/WEO"},
                {"source_id": "imf_gfs", "name": "Government Finance Statistics", "publisher": "IMF",
                 "url": "https://data.imf.org/en/datasets/IMF.STA:GFS_SOO"},
                {"source_id": "togo_dgb", "name": "Budget Execution Report", "publisher": "Togo DGB",
                 "url": None},
            ],
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

        # Verify section content — source line is now "publisher — name"
        section = info["source_sections"][0]
        self.assertEqual(section["label"], "BOOST Expenditure Data")
        self.assertEqual(section["source_name"], "World Bank — BOOST")
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

    def test_build_modal_info_boost_url_falls_back_to_registry(self):
        """When no per-country BOOST url exists, the registry url is used (no config fallback)."""
        chart_id = "education-total"
        country = "UnknownCountry"

        info = build_modal_info(chart_id, country, self.source_meta)

        section = info["source_sections"][0]
        self.assertEqual(
            section["source_url"],
            "https://www.worldbank.org/en/programs/boost-portal/country-data"
        )

    def test_build_modal_info_french(self):
        """Labels + descriptions are localized; the source line is localized publisher — name."""
        info = build_modal_info("overview-per-capita", "Kenya", self.source_meta, lang="fr")

        # BOOST section - French
        boost_section = info["source_sections"][0]
        self.assertEqual(boost_section["label"], "Données de dépenses BOOST")
        self.assertEqual(boost_section["source_name"], "Banque mondiale — BOOST")

        # Poverty rate section - French with description
        poverty_section = info["source_sections"][1]
        self.assertEqual(poverty_section["label"], "Taux de pauvreté")
        self.assertIn("Banque mondiale", poverty_section["source_name"])
        self.assertIsNotNone(poverty_section.get("description"))
        self.assertIn("seuils de pauvreté", poverty_section["description"])

    def test_build_modal_info_default_lang_is_english(self):
        """Omitting lang should produce English output (backward compat)."""
        info = build_modal_info("overview-total", "Kenya", self.source_meta)
        section = info["source_sections"][0]
        self.assertEqual(section["label"], "BOOST Expenditure Data")
        self.assertEqual(section["source_name"], "World Bank — BOOST")

    def test_build_modal_info_country_scoped_source_included(self):
        """A source with a ``countries`` whitelist shows when the current country is in it."""
        info = build_modal_info("revenue-expenditure-combined", "Togo", self.source_meta)
        source_names = [s["source_name"] for s in info["source_sections"]]
        # togo_dgb has countries=["Togo"]; its localized publisher shows for Togo.
        self.assertEqual(len(info["source_sections"]), 3)
        self.assertTrue(any("Togo" in n for n in source_names))

    def test_build_modal_info_country_scoped_source_excluded(self):
        """A source with a ``countries`` whitelist is filtered out for other countries."""
        info = build_modal_info("revenue-expenditure-combined", "Kenya", self.source_meta)
        source_names = [s["source_name"] for s in info["source_sections"]]
        # togo_dgb has countries=["Togo"]; should NOT appear for Kenya.
        self.assertFalse(any("Togo" in n for n in source_names))
        # Un-scoped IMF sources still appear (both WEO and GFS).
        self.assertEqual(len(info["source_sections"]), 2)

    def test_build_modal_info_chart_level_info(self):
        """Charts with ``info_key`` produce a translated chart-level ``info`` string."""
        info_en = build_modal_info("revenue-expenditure-combined", "Togo", self.source_meta, lang="en")
        self.assertIsNotNone(info_en.get("info"))
        self.assertIn("composite view", info_en["info"].lower())

        info_fr = build_modal_info("revenue-expenditure-combined", "Togo", self.source_meta, lang="fr")
        self.assertIsNotNone(info_fr.get("info"))
        self.assertIn("vue composite", info_fr["info"].lower())

    def test_build_modal_info_no_chart_level_info(self):
        """Charts without ``info_key`` return ``info=None``."""
        info = build_modal_info("overview-total", "Kenya", self.source_meta)
        self.assertIsNone(info.get("info"))


if __name__ == "__main__":
    unittest.main()
