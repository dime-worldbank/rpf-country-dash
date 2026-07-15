# Source Registry — Dashboard Consumption (Contract-First) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the source-metadata popover to consume two normalized inputs — a `source_registry` (source facts) and an `indicator_source` bridge — instead of hardcoded per-source dicts, driving the whole thing from **fixtures** so the exact table contract the pipeline must produce is proven before any pipeline work.

**Architecture:** The popover keeps three concerns cleanly separated: **facts** (`source_registry`: id → name/publisher/url) come from the pipeline; **presentation** (i18n label/description keys, per-source country scoping) stays dashboard-side in a new `SOURCE_DISPLAY` map keyed by `source_id`; **wiring** (`CHART_METADATA`: chart → list of `source_id`) stays dashboard-side. Coverage years resolve `source_id → indicator_key(s)` through the `indicator_source` bridge. All new logic is exercised against in-memory fixtures via `unittest`; **no Databricks is required** to complete this plan. The real query loaders are authored but their DB round-trip is validated later, when the pipeline tables exist.

**Tech Stack:** Python, Dash, `unittest` (CI runs `python -m unittest discover tests/`), the `translations` package (`t(key, lang=None, **kwargs)`).

## Global Constraints

- Test framework is **`unittest`** (not pytest). CI: `.github/workflows/python-tests.yml` runs `python -m unittest discover tests/`.
- The popover's `source_meta` dict is assembled in `app.py::fetch_source_metadata_once`. This plan adds two keys to it: `source_registry` and `indicator_source`, each a **list of record dicts**.
- **Locked contract — the record shapes the pipeline MUST produce** (this is the deliverable that feeds the pipeline plan):
  - `source_registry`: `{"source_id": str, "name": str, "publisher": str, "url": str | None}`
  - `indicator_source`: `{"indicator_key": str, "source_id": str}`
- `source_id` values are the stable slugs from the spec (`imf_weo`, `imf_gfs`, `boost`, `pip_spid`, `pip_gsap`, `unesco_uis`, `who_gho`, `who_nha`, `pefa`, `world_bank_pip`, `world_bank_icp`, `global_data_lab`, `togo_dgb`).
- **Contract decision (URL resolution):** a source's URL is the registry's canonical `url`; `boost` keeps its per-country URL via the existing `boost_source_urls`. The old per-`indicator_key` `source_urls_by_country` map is no longer used for non-boost sources. Documented here so the pipeline doesn't preserve per-country URLs it doesn't need.
- Spec: `../specs/` in `mega-indicators` (`2026-07-15-source-registry-design.md`).

---

## File Structure

- Modify: `components/source_metadata_popover.py` — replace hardcoded per-source dicts with `SOURCE_DISPLAY` (id → i18n keys + scoping) and `CHART_METADATA` (chart → `[source_id]`); rewrite `get_coverage_years` and `build_modal_info` to consume the registry + bridge. Single responsibility: turn `(chart_id, country, source_meta, lang)` into rendered source sections.
- Modify: `tests/test_source_metadata_popover.py` — extend with fixture-based tests for the new resolution logic.
- Modify: `queries.py` — add `get_source_registry()` and `get_indicator_source()` (mirror `get_indicator_data_availability`).
- Modify: `data_mapping.py` — register the two new loaders (only if the dashboard loads them via `server_store`; otherwise they are read in `app.py`).
- Modify: `app.py::fetch_source_metadata_once` — add `source_registry` and `indicator_source` lists to the returned `source_meta` dict.

---

### Task 1: Coverage lookup by `source_id` through the bridge

Today `get_coverage_years(key, country, source_meta)` matches `key` against `indicator_availability[*].indicator_key` (or `"boost"`). The new popover keys sections by `source_id`, so coverage must resolve `source_id → indicator_key(s)` via the `indicator_source` bridge, then take the widest span across those indicators for the country.

**Files:**
- Modify: `components/source_metadata_popover.py` (function `get_coverage_years`)
- Test: `tests/test_source_metadata_popover.py`

**Interfaces:**
- Consumes: `source_meta["indicator_source"]` (list of `{indicator_key, source_id}`), `source_meta["indicator_availability"]` (existing), `source_meta["boost_source_urls"]` (existing).
- Produces: `get_coverage_years(source_id, country, source_meta) -> (int|None, int|None)`. `source_id == "boost"` keeps its current special-case path.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_source_metadata_popover.py`:

```python
class TestCoverageBySourceId(unittest.TestCase):
    def setUp(self):
        self.source_meta = {
            "boost_source_urls": [
                {"country_name": "Kenya", "source_url": "u", "earliest_year": 2010, "latest_year": 2020},
            ],
            "indicator_availability": [
                {"country_name": "Kenya", "indicator_key": "global_data_lab_hd_index",
                 "earliest_year": 2012, "latest_year": 2018},
                {"country_name": "Kenya", "indicator_key": "global_data_lab_attendance",
                 "earliest_year": 2011, "latest_year": 2019},
            ],
            "indicator_source": [
                {"indicator_key": "global_data_lab_hd_index", "source_id": "global_data_lab"},
                {"indicator_key": "global_data_lab_attendance", "source_id": "global_data_lab"},
            ],
        }

    def test_source_feeding_two_indicators_takes_widest_span(self):
        start, end = get_coverage_years("global_data_lab", "Kenya", self.source_meta)
        self.assertEqual((start, end), (2011, 2019))  # min earliest, max latest across both indicators

    def test_boost_still_special_cased(self):
        start, end = get_coverage_years("boost", "Kenya", self.source_meta)
        self.assertEqual((start, end), (2010, 2020))

    def test_unknown_source_returns_none(self):
        self.assertEqual(get_coverage_years("nope", "Kenya", self.source_meta), (None, None))
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python -m unittest tests.test_source_metadata_popover.TestCoverageBySourceId -v`
Expected: FAIL — current `get_coverage_years` treats `source_id` as an `indicator_key`, so `global_data_lab` matches nothing → `(None, None)` instead of `(2011, 2019)`.

- [ ] **Step 3: Rewrite `get_coverage_years`**

Replace the function body in `components/source_metadata_popover.py` with:

```python
def get_coverage_years(source_id, country, source_meta):
    """Return ``(earliest_year, latest_year)`` for a source and country.

    ``"boost"`` reads from ``boost_source_urls``. Every other source resolves to
    its indicator(s) via the ``indicator_source`` bridge, then takes the widest
    year span across those indicators' rows in ``indicator_availability``.
    """
    if not country or not source_meta:
        return None, None

    if source_id == "boost":
        for row in source_meta.get("boost_source_urls", []):
            if row.get("country_name") == country:
                start = row.get("earliest_year")
                end = row.get("latest_year")
                start = max(int(start), START_YEAR) if start else None
                end = int(end) if end else None
                return start, end
        return None, None

    indicator_keys = {
        r["indicator_key"]
        for r in source_meta.get("indicator_source", [])
        if r.get("source_id") == source_id
    }
    if not indicator_keys:
        return None, None

    starts, ends = [], []
    for row in source_meta.get("indicator_availability", []):
        if row.get("country_name") == country and row.get("indicator_key") in indicator_keys:
            if row.get("earliest_year"):
                starts.append(max(int(row["earliest_year"]), START_YEAR))
            if row.get("latest_year"):
                ends.append(int(row["latest_year"]))

    return (min(starts) if starts else None, max(ends) if ends else None)
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m unittest tests.test_source_metadata_popover.TestCoverageBySourceId -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add components/source_metadata_popover.py tests/test_source_metadata_popover.py
git commit -m "feat: resolve popover coverage years by source_id via indicator_source bridge"
```

---

### Task 2: Registry-backed source section resolver

Introduce `SOURCE_DISPLAY` (dashboard-owned i18n keys + country scoping, keyed by `source_id`) and a resolver that combines it with the `source_registry` facts and coverage into a section dict.

**Files:**
- Modify: `components/source_metadata_popover.py`
- Test: `tests/test_source_metadata_popover.py`

**Interfaces:**
- Consumes: `source_meta["source_registry"]` (list of `{source_id, name, publisher, url}`), Task 1's `get_coverage_years`.
- Produces:
  - `SOURCE_DISPLAY: dict[str, dict]` — `source_id -> {"label_key": str, "description_key": str|None, "countries": list[str]|None}`.
  - `_resolve_source_section(source_id, country, source_meta, lang) -> dict|None` — returns `{"label","source_name","description","source_url","coverage"}`, or `None` if the source is country-scoped out.

- [ ] **Step 1: Write the failing test**

```python
from components.source_metadata_popover import _resolve_source_section, SOURCE_DISPLAY

class TestResolveSourceSection(unittest.TestCase):
    def setUp(self):
        self.source_meta = {
            "source_registry": [
                {"source_id": "imf_weo", "name": "World Economic Outlook — General Government",
                 "publisher": "IMF", "url": "https://imf.org/weo"},
                {"source_id": "togo_dgb", "name": "Budget Execution Report",
                 "publisher": "Togo DGB", "url": None},
            ],
            "indicator_source": [{"indicator_key": "government_revenue_expenditure", "source_id": "imf_weo"}],
            "indicator_availability": [
                {"country_name": "Togo", "indicator_key": "government_revenue_expenditure",
                 "earliest_year": 2010, "latest_year": 2023},
            ],
            "boost_source_urls": [],
        }

    def test_resolves_facts_and_coverage(self):
        SOURCE_DISPLAY["imf_weo"] = {"label_key": "source.imf_weo.label", "description_key": None, "countries": None}
        section = _resolve_source_section("imf_weo", "Togo", self.source_meta, "en")
        self.assertEqual(section["source_url"], "https://imf.org/weo")
        self.assertEqual(section["coverage"], "2010–2023")

    def test_country_scoped_out_returns_none(self):
        SOURCE_DISPLAY["togo_dgb"] = {"label_key": "source.togo_dgb.label", "description_key": None, "countries": ["Togo"]}
        self.assertIsNone(_resolve_source_section("togo_dgb", "Kenya", self.source_meta, "en"))
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python -m unittest tests.test_source_metadata_popover.TestResolveSourceSection -v`
Expected: FAIL — `_resolve_source_section` and `SOURCE_DISPLAY` do not exist (`ImportError`).

- [ ] **Step 3: Implement `SOURCE_DISPLAY` and the resolver**

Add near the top of `components/source_metadata_popover.py` (replacing the old per-source dicts `_BOOST`, `_IMF_WEO`, … as they are migrated):

```python
# Dashboard-owned presentation for each source, keyed by source_id. Facts
# (name/publisher/url) come from source_registry; only i18n keys and per-source
# country scoping live here.
SOURCE_DISPLAY = {
    "boost":           {"label_key": "source.boost.label",          "description_key": None,                          "countries": None},
    "imf_weo":         {"label_key": "source.imf_weo.label",        "description_key": "source.imf_weo.description",  "countries": None},
    "imf_gfs":         {"label_key": "source.imf_gfs.label",        "description_key": "source.imf_gfs.description",  "countries": None},
    "togo_dgb":        {"label_key": "source.togo_dgb.label",       "description_key": "source.togo_dgb.description", "countries": ["Togo"]},
    "world_bank_pip":  {"label_key": "source.poverty_rate.label",   "description_key": "source.poverty_rate.description", "countries": None},
    "pip_spid":        {"label_key": "source.subnational_poverty.label", "description_key": "source.subnational_poverty.description", "countries": None},
    "pip_gsap":        {"label_key": "source.subnational_poverty.label", "description_key": "source.subnational_poverty.description", "countries": None},
    "world_bank_icp":  {"label_key": "source.edu_private.label",    "description_key": "source.edu_private.description", "countries": None},
    "unesco_uis":      {"label_key": "source.learning_poverty.label", "description_key": None,                        "countries": None},
    "who_gho":         {"label_key": "source.uhc.label",            "description_key": None,                          "countries": None},
    "who_nha":         {"label_key": "source.health_private.label", "description_key": "source.health_private.description", "countries": None},
    "pefa":            {"label_key": "source.pefa.label",           "description_key": "source.pefa.description",     "countries": None},
    "global_data_lab": {"label_key": "source.hd_index.label",       "description_key": None,                          "countries": None},
}


def _registry_lookup(source_id, source_meta):
    """Return the source_registry record for source_id, or an empty dict."""
    for row in source_meta.get("source_registry", []):
        if row.get("source_id") == source_id:
            return row
    return {}


def _resolve_source_section(source_id, country, source_meta, lang="en"):
    """Combine SOURCE_DISPLAY + source_registry facts + coverage into a section
    dict, or None when the source is scoped to other countries."""
    display = SOURCE_DISPLAY.get(source_id, {})
    scoped = display.get("countries")
    if scoped and country not in scoped:
        return None

    registry = _registry_lookup(source_id, source_meta)
    description_key = display.get("description_key")
    section = {
        "label": t(display.get("label_key", ""), lang) if display.get("label_key") else registry.get("name", ""),
        "source_name": registry.get("publisher", ""),
        "description": t(description_key, lang) if description_key else None,
        "source_url": registry.get("url"),
    }
    start, end = get_coverage_years(source_id, country, source_meta)
    if start and end:
        section["coverage"] = f"{start}–{end}"
    return section
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m unittest tests.test_source_metadata_popover.TestResolveSourceSection -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add components/source_metadata_popover.py tests/test_source_metadata_popover.py
git commit -m "feat: add SOURCE_DISPLAY + registry-backed source section resolver"
```

---

### Task 3: `CHART_METADATA` → source_id lists; `build_modal_info` uses the resolver

**Files:**
- Modify: `components/source_metadata_popover.py` (`CHART_METADATA`, `build_modal_info`)
- Test: `tests/test_source_metadata_popover.py`

**Interfaces:**
- Consumes: `SOURCE_DISPLAY`, `_resolve_source_section` (Task 2).
- Produces: `CHART_METADATA[chart] = {"sources": [source_id, ...], "info_key": str|None}`; `build_modal_info(chart_id, country, source_meta, lang)` unchanged signature, now builds `source_sections` via `_resolve_source_section`, dropping any that resolve to `None`.

- [ ] **Step 1: Write the failing test** (multi-source chart)

```python
class TestBuildModalInfoWithRegistry(unittest.TestCase):
    def setUp(self):
        self.source_meta = {
            "source_registry": [
                {"source_id": "imf_weo", "name": "WEO", "publisher": "IMF", "url": "https://imf.org/weo"},
                {"source_id": "imf_gfs", "name": "GFS", "publisher": "IMF", "url": "https://imf.org/gfs"},
                {"source_id": "togo_dgb", "name": "DGB", "publisher": "Togo DGB", "url": None},
            ],
            "indicator_source": [
                {"indicator_key": "government_revenue_expenditure", "source_id": "imf_weo"},
                {"indicator_key": "government_revenue_expenditure", "source_id": "imf_gfs"},
            ],
            "indicator_availability": [], "boost_source_urls": [],
        }

    def test_togo_only_source_dropped_for_other_country(self):
        info = build_modal_info("revenue-expenditure-combined", "Kenya", self.source_meta, "en")
        labels = [s["source_name"] for s in info["source_sections"]]
        self.assertIn("IMF", labels)
        self.assertNotIn("Togo DGB", labels)  # togo_dgb scoped to Togo only

    def test_all_imf_sources_present_for_togo(self):
        info = build_modal_info("revenue-expenditure-combined", "Togo", self.source_meta, "en")
        self.assertEqual(len(info["source_sections"]), 3)
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python -m unittest tests.test_source_metadata_popover.TestBuildModalInfoWithRegistry -v`
Expected: FAIL — `CHART_METADATA["revenue-expenditure-combined"]["sources"]` still holds old dicts, `build_modal_info` reads `src["key"]`.

- [ ] **Step 3: Convert `CHART_METADATA` to source_id lists**

Replace every `"sources": [_X, _Y]` entry with `source_id` strings. Full replacement for `CHART_METADATA`:

```python
CHART_METADATA = {
    "overview-total": {"sources": ["boost"]},
    "overview-per-capita": {"sources": ["boost", "world_bank_pip"]},
    "functional-breakdown": {"sources": ["boost"]},
    "func-growth": {"sources": ["boost"]},
    "economic-breakdown": {"sources": ["boost"]},
    "pefa-overall": {"sources": ["pefa", "world_bank_pip"]},
    "pefa-by-pillar": {"sources": ["pefa"]},
    "revenue-expenditure-combined": {
        "info_key": "chart.revenue_expenditure_combined.info",
        "sources": ["togo_dgb", "imf_gfs", "imf_weo"],
    },
    "subnational-spending": {"sources": ["boost"]},
    "subnational-poverty": {"sources": ["pip_spid", "pip_gsap"]},
    "education-public-private": {"sources": ["boost", "world_bank_icp"]},
    "education-total": {"sources": ["boost"]},
    "education-outcome": {"sources": ["boost", "unesco_uis", "global_data_lab"]},
    "econ-breakdown-func-edu": {"sources": ["boost"]},
    "education-central-vs-regional": {"sources": ["boost"]},
    "education-sub-func": {"sources": ["boost"]},
    "education-expenditure-map": {"sources": ["boost"]},
    "education-outcome-map": {"sources": ["global_data_lab"]},
    "education-subnational": {"sources": ["boost", "global_data_lab"]},
    "health-public-private": {"sources": ["boost", "who_nha"]},
    "health-total": {"sources": ["boost"]},
    "health-outcome": {"sources": ["boost", "who_gho"]},
    "econ-breakdown-func-health": {"sources": ["boost"]},
    "health-central-vs-regional": {"sources": ["boost"]},
    "health-sub-func": {"sources": ["boost"]},
    "health-expenditure-map": {"sources": ["boost"]},
    "health-outcome-map": {"sources": ["who_gho"]},
    "health-subnational": {"sources": ["boost", "who_gho"]},
}
```

Note: `education-outcome` previously used `_ATTENDANCE` (Global Data Lab attendance) and `_LEARNING_POVERTY`. Attendance maps to `global_data_lab`; learning poverty's popover label maps to `unesco_uis` in `SOURCE_DISPLAY`. Confirm these two labels read acceptably in the rendered modal during Task 5 review.

- [ ] **Step 4: Rewrite `build_modal_info`**

Replace `build_modal_info` body with:

```python
def build_modal_info(chart_id, country, source_meta, lang="en"):
    """Build the info dict for a chart's source modal from the registry + bridge."""
    chart_meta = CHART_METADATA.get(chart_id, {})
    source_sections = []
    for source_id in chart_meta.get("sources", []):
        section = _resolve_source_section(source_id, country, source_meta, lang)
        if section is not None:
            source_sections.append(section)

    info_key = chart_meta.get("info_key")
    return {
        **chart_meta,
        "_index": chart_id,
        "country_name": country,
        "source_sections": source_sections,
        "info": t(info_key, lang) if info_key else None,
    }
```

- [ ] **Step 5: Delete the now-dead per-source dicts and update imports**

Remove the old `_BOOST`, `_BOOST_EDU`, …, `_TOGO_DGB` module-level dicts (superseded by `SOURCE_DISPLAY`). Run the full popover test module.

Run: `python -m unittest tests.test_source_metadata_popover -v`
Expected: PASS — including pre-existing tests. Any pre-existing test asserting the old `_X` dict shape must be updated to the new resolver (update it in this step, do not delete coverage).

- [ ] **Step 6: Commit**

```bash
git add components/source_metadata_popover.py tests/test_source_metadata_popover.py
git commit -m "feat: drive popover from source_id lists + registry resolver"
```

---

### Task 4: Query loaders + inject registry/bridge into `source_meta`

Author the DB loaders and thread the two new lists into `source_meta`. The query round-trip can't run until the pipeline tables exist; this task's test covers the **assembly** logic with fixtures, not the SQL.

**Files:**
- Modify: `queries.py` (add `get_source_registry`, `get_indicator_source`)
- Modify: `app.py::fetch_source_metadata_once`
- Test: `tests/test_source_metadata_popover.py` (assembly-shape test with a fake db)

**Interfaces:**
- Consumes: `INDICATOR_SCHEMA` (already imported in `queries.py`).
- Produces: `source_meta` gains `"source_registry": [...]` and `"indicator_source": [...]` (record lists matching the locked contract).

- [ ] **Step 1: Add the loaders to `queries.py`**

Mirror `get_indicator_data_availability` (queries.py:215):

```python
    def get_source_registry(self):
        query = f"""
            SELECT source_id, name, publisher, url
            FROM prd_mega.{INDICATOR_SCHEMA}.source_registry
        """
        return self.fetch_data(query)

    def get_indicator_source(self):
        query = f"""
            SELECT indicator_key, source_id
            FROM prd_mega.{INDICATOR_SCHEMA}.indicator_source
        """
        return self.fetch_data(query)
```

- [ ] **Step 2: Thread them into `fetch_source_metadata_once`**

In `app.py::fetch_source_metadata_once`, after the existing `indicator_df` / `boost_urls_df` loads, add:

```python
        registry_df = db.get_source_registry()
        indicator_source_df = db.get_indicator_source()
```

and add to the returned dict:

```python
            "source_registry": registry_df.to_dict("records"),
            "indicator_source": indicator_source_df.to_dict("records"),
```

- [ ] **Step 3: Write the assembly-shape test**

This asserts the record shapes match the locked contract, using a fake db (no Databricks):

```python
class TestSourceMetaContract(unittest.TestCase):
    def test_record_shapes_match_locked_contract(self):
        registry = [{"source_id": "imf_weo", "name": "WEO", "publisher": "IMF", "url": "https://imf.org/weo"}]
        bridge = [{"indicator_key": "government_revenue_expenditure", "source_id": "imf_weo"}]
        self.assertEqual(set(registry[0]), {"source_id", "name", "publisher", "url"})
        self.assertEqual(set(bridge[0]), {"indicator_key", "source_id"})
        # And the popover consumes exactly these keys:
        meta = {"source_registry": registry, "indicator_source": bridge,
                "indicator_availability": [], "boost_source_urls": []}
        section = _resolve_source_section("imf_weo", "Togo", meta, "en")
        self.assertEqual(section["source_url"], "https://imf.org/weo")
```

- [ ] **Step 4: Run the full suite**

Run: `python -m unittest discover tests/ -v`
Expected: PASS (new + existing). `queries.py`/`app.py` DB paths are untested here by design.

- [ ] **Step 5: Commit**

```bash
git add queries.py app.py tests/test_source_metadata_popover.py
git commit -m "feat: load source_registry + indicator_source into popover source_meta"
```

---

### Task 5: Lock the contract + record what the pipeline must produce

**Files:**
- Modify: `docs/superpowers/plans/2026-07-15-source-registry-dashboard.md` (this file — check off the contract), or add a short `docs/source-registry-contract.md`.

- [ ] **Step 1: Confirm the fixtures ARE the contract**

Verify the fixture record shapes used across Tasks 1–4 exactly match the Global Constraints "Locked contract" block. They are the authoritative statement of what `mega-indicators` `source_registry` / `indicator_source` must emit (column names and types). No code change if they already match.

- [ ] **Step 2: Manual render check (optional, needs the app running)**

If a dev environment with data is available, run the app and open a couple of source modals (`revenue-expenditure-combined`, `education-outcome`) to confirm labels/URLs/coverage read correctly. If not available, defer to the wire-up plan.

- [ ] **Step 3: Note contract in the pipeline plan**

Cross-reference: the `mega-indicators` pipeline plan (`docs/superpowers/plans/2026-07-15-source-registry-pipeline.md`) already emits `source_registry(source_id,name,publisher,url)` and `indicator_source(indicator_key,source_id)` — confirm column names match this plan's contract exactly. They do; if a name changes here, update the pipeline plan.

---

## Out of Scope (follow-on: wire-up plan, after pipeline ships)

- Replace the `split_imf_sources` string-matching in `components/fiscal_balance.py` — **blocked** on the pipeline splitting `government_revenue_expenditure` into single-source tables.
- Delete `WEO_SOURCE` / `GFS_SOO_SOURCE` / `IMF_GOVERNMENT_REVENUE_EXPENDITURE_SOURCES` from `constants.py` — done in the wire-up plan alongside the `split_imf_sources` change.
- Register loaders in `data_mapping.py` / `server_store` if the app moves to lazy `server_store` loading for these (currently loaded eagerly in `app.py`).
- Remove the per-`indicator_key` `source_urls_by_country` map for non-boost sources once the registry URL path is confirmed in production.
- End-to-end validation against the real Databricks tables (needs the pipeline plan deployed).

## Self-Review

- **Spec coverage:** Implements the dashboard-consumption half of the spec — popover reads `source_registry` (facts) + `indicator_source` (bridge), SPID/GSAP as separate sources, `government_revenue_expenditure → {imf_weo, imf_gfs}`, i18n kept dashboard-side keyed by `source_id`. `split_imf_sources` and constant deletion are correctly deferred (blocked on the table split).
- **Placeholder scan:** No TBD/TODO. `togo_dgb.url = None` is intentional data. The "optional render check" (Task 5 Step 2) is explicitly conditional, not a placeholder.
- **Type consistency:** `get_coverage_years(source_id, ...)`, `_resolve_source_section(...)`, `SOURCE_DISPLAY`, `_registry_lookup`, `build_modal_info(...)` names and section keys (`label`, `source_name`, `description`, `source_url`, `coverage`) are consistent across Tasks 1–4 and match the existing `_build_source_section` consumer (unchanged). Contract record keys are identical everywhere.
