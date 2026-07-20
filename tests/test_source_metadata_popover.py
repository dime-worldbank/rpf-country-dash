import unittest
from components.source_metadata_popover import (
    build_modal_info,
    build_modal_children,
    get_coverage_years,
    _resolve_source_section,
    _group_sections,
    CHART_METADATA,
)


def _collect_text(component):
    """Flatten a Dash component tree into a list of string leaves."""
    if isinstance(component, str):
        return [component]
    if isinstance(component, (list, tuple)):
        return [s for c in component for s in _collect_text(c)]
    children = getattr(component, "children", None)
    if children is not None:
        return _collect_text(children)
    return []


class TestSourceMetaContract(unittest.TestCase):
    """The fixture record shapes ARE the contract the pipeline must emit."""

    def test_registry_record_shape_and_url_resolution(self):
        registry = [{"source_id": "imf_weo", "name": "WEO", "publisher": "IMF",
                     "url": "https://imf.org/weo"}]
        self.assertEqual(set(registry[0]), {"source_id", "name", "publisher", "url"})

        meta = {"source_registry": registry, "indicator_availability": [], "boost_source_urls": []}
        section = _resolve_source_section({"source_id": "imf_weo"}, "Togo", meta, "en")
        # Facts (url) come from the registry; the labelled name comes from i18n.
        self.assertEqual(section["source_url"], "https://imf.org/weo")
        self.assertEqual(section["source_name"], "IMF — World Economic Outlook")


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
            # Bridge: chart indicator_key(s) → source_id(s). Charts resolve their
            # source sections through this, so every indicator a tested chart lists
            # must appear here (government_revenue_expenditure is multi-source).
            "indicator_source": [
                {"indicator_key": "boost", "source_id": "boost"},
                {"indicator_key": "poverty_rate", "source_id": "world_bank_pip"},
                {"indicator_key": "togo_revenue_budget", "source_id": "togo_dgb"},
                {"indicator_key": "government_revenue_expenditure", "source_id": "imf_weo"},
                {"indicator_key": "government_revenue_expenditure", "source_id": "imf_gfs"},
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

        # Verify chart metadata is included (indicators field from CHART_METADATA)
        self.assertIn("indicators", info)
        self.assertEqual(info["indicators"], CHART_METADATA[chart_id]["indicators"])

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


class TestSourceSectionGrouping(unittest.TestCase):
    """Multiple sources feeding one metric share heading/methodology/coverage."""

    def test_group_sections_merges_same_metric(self):
        """Sources with identical heading, methodology, and coverage collapse."""
        sections = [
            {"label": "Subnational Poverty Rate", "description": "m", "coverage": "2010–2023",
             "source_name": "World Bank — SPID"},
            {"label": "Subnational Poverty Rate", "description": "m", "coverage": "2010–2023",
             "source_name": "World Bank — GSAP"},
        ]
        groups = _group_sections(sections)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_group_sections_keeps_distinct_metrics_separate(self):
        """Sources with different headings stay in separate groups (e.g. WEO vs GFS)."""
        sections = [
            {"label": "WEO", "description": "a", "coverage": "2010–2023"},
            {"label": "GFS", "description": "b", "coverage": "2010–2023"},
        ]
        groups = _group_sections(sections)
        self.assertEqual(len(groups), 2)

    def test_multi_source_metric_shares_heading_repeats_source_rows(self):
        """A grouped metric shows heading/methodology/coverage once, and repeats
        the More-info and Source rows per source."""
        info = {
            "_index": "subnational-poverty",
            "country_name": "Togo",
            "source_sections": [
                {"label": "Subnational Poverty Rate", "description": "Thresholds vary.",
                 "coverage": "2010–2023", "source_name": "World Bank — SPID",
                 "source_url": "https://pipmaps.example/spid"},
                {"label": "Subnational Poverty Rate", "description": "Thresholds vary.",
                 "coverage": "2010–2023", "source_name": "World Bank — GSAP",
                 "source_url": "https://pipmaps.example/gsap"},
            ],
        }
        text = _collect_text(build_modal_children(info, lang="en"))
        # Shared fields appear exactly once despite two sources.
        self.assertEqual(text.count("Subnational Poverty Rate"), 1)
        self.assertEqual(text.count("Thresholds vary."), 1)
        self.assertEqual(text.count("2010–2023"), 1)
        # The Source row repeats per source, each with its own link.
        self.assertEqual(text.count("More info: "), 2)
        self.assertEqual(text.count("Source: "), 2)
        self.assertIn("World Bank — SPID", text)
        self.assertIn("World Bank — GSAP", text)
        self.assertIn("https://pipmaps.example/spid", text)
        self.assertIn("https://pipmaps.example/gsap", text)

    def test_single_source_metric_layout_unchanged(self):
        """A single-source metric renders one heading, one More-info, one Source."""
        info = {
            "_index": "overview-total",
            "country_name": "Kenya",
            "source_sections": [
                {"label": "BOOST Expenditure Data", "description": None,
                 "coverage": "2010–2020", "source_name": "World Bank — BOOST",
                 "source_url": "https://boost.example"},
            ],
        }
        text = _collect_text(build_modal_children(info, lang="en"))
        self.assertEqual(text.count("BOOST Expenditure Data"), 1)
        self.assertEqual(text.count("More info: "), 1)
        self.assertEqual(text.count("Source: "), 1)
        self.assertIn("World Bank — BOOST", text)


if __name__ == "__main__":
    unittest.main()
