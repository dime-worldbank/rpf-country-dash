"""
Extracted data-loading functions for server_cache auto-population.

Each loader is registered with server_cache so that a cache miss on a
recycled process can self-heal without waiting for the fetch-once
Dash callbacks to re-fire.

Loaders that need a `countries` list obtain it by first loading the
expenditure_w_poverty key (which has no parameters).
"""
import json
import pandas as pd
from queries import QueryService
from components.func_operational_vs_capital_spending import prepare_prop_econ_by_func_df
import server_cache


def _db():
    return QueryService.get_instance()


def _countries():
    """Derive the countries list from expenditure_w_poverty (parameter-free)."""
    df = server_cache.get("expenditure_w_poverty")
    return sorted(df["country_name"].unique())


# ---------------------------------------------------------------------------
# Simple pass-through loaders (no transformation)
# ---------------------------------------------------------------------------

def load_expenditure_w_poverty():
    df = _db().get_expenditure_w_poverty_by_country_year()
    return df


def load_subnational_poverty_rate():
    return _db().get_subnational_poverty_rate(_countries())


def load_geo1_expenditure():
    return _db().get_expenditure_by_country_geo1_year()


def load_geo1_func_expenditure():
    return _db().expenditure_and_outcome_by_country_geo1_func_year()


def load_sub_func_expenditure():
    return _db().get_expenditure_by_country_sub_func_year()


def load_pefa():
    return _db().get_pefa(_countries())


def load_uhc_index():
    return _db().get_universal_health_coverage_index()


def load_health_private_expenditure():
    return _db().get_health_private_expenditure()


def load_health_sub_func_expenditure():
    return _db().get_expenditure_by_country_sub_func_year()


def load_learning_poverty():
    return _db().get_learning_poverty_rate()


def load_hd_index():
    return _db().get_hd_index(_countries())


def load_edu_private_expenditure():
    return _db().get_edu_private_expenditure()


# ---------------------------------------------------------------------------
# Transformation loaders
# ---------------------------------------------------------------------------

_AGG_DICT = {
    "expenditure": "sum",
    "budget": "sum",
    "real_expenditure": "sum",
    "domestic_funded_budget": "sum",
    "decentralized_expenditure": "sum",
    "central_expenditure": "sum",
    "per_capita_expenditure": "sum",
    "per_capita_real_expenditure": "sum",
}


def _load_func_econ_group():
    """Load and transform the func/econ group (4 keys from 1 DB call).

    All 4 keys are set atomically so that any key triggering this
    loader populates the others too, avoiding redundant DB calls.
    """
    # If another key already triggered this, all 4 are populated
    if server_cache.has("func_by_country_year"):
        return

    func_econ_df = _db().get_expenditure_by_country_func_econ_year()

    func_df = func_econ_df.groupby(
        ["country_name", "year", "func"], as_index=False
    ).agg(_AGG_DICT)
    func_df["expenditure_decentralization"] = (
        func_df["decentralized_expenditure"] / func_df["expenditure"]
    )
    func_df["real_domestic_funded_budget"] = (
        func_df["real_expenditure"] / func_df["expenditure"]
    ) * func_df["domestic_funded_budget"]

    econ_df = func_econ_df.groupby(
        ["country_name", "year", "econ"], as_index=False
    ).agg(_AGG_DICT)
    econ_df["expenditure_decentralization"] = (
        econ_df["decentralized_expenditure"] / econ_df["expenditure"]
    )

    prop_econ_by_func_df = prepare_prop_econ_by_func_df(func_econ_df, _AGG_DICT)

    # Set all 4 keys at once
    server_cache.set("func_econ_raw", func_econ_df)
    server_cache.set("func_by_country_year", func_df)
    server_cache.set("econ_by_country_year", econ_df)
    server_cache.set("prop_econ_by_func", prop_econ_by_func_df)


def load_func_econ_raw():
    _load_func_econ_group()
    return server_cache.get("func_econ_raw")


def load_func_by_country_year():
    _load_func_econ_group()
    return server_cache.get("func_by_country_year")


def load_econ_by_country_year():
    _load_func_econ_group()
    return server_cache.get("econ_by_country_year")


def load_prop_econ_by_func():
    _load_func_econ_group()
    return server_cache.get("prop_econ_by_func")


def load_disputed_boundaries():
    countries = _countries()
    df_disputed = _db().get_disputed_boundaries(countries)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {"country": x[0], "region": x[2]},
                "geometry": json.loads(x[1]),
            }
            for x in zip(
                df_disputed.country_name,
                df_disputed.boundary,
                df_disputed.region_name,
            )
        ],
    }


def load_basic_country_info():
    countries = _countries()
    country_df = _db().get_basic_country_data(countries)
    country_info = country_df.set_index("country_name").T.to_dict()

    expenditure_df = server_cache.get("geo1_expenditure")[["country_name", "year"]]
    poverty_df = server_cache.get("subnational_poverty_rate")[
        ["country_name", "year", "poverty_rate"]
    ]

    expenditure_years = (
        expenditure_df.groupby("country_name")["year"]
        .apply(lambda x: sorted(x.unique()))
        .to_dict()
    )
    poverty_years = (
        poverty_df.groupby("country_name")["year"]
        .apply(lambda x: sorted(x.unique()))
        .to_dict()
    )

    poverty_level_stats = (
        pd.merge(country_df, poverty_df, on="country_name")
        .groupby("income_level")["poverty_rate"]
        .agg(["min", "max"])
        .reset_index()
    )
    poverty_level_stats = (
        poverty_level_stats.set_index("income_level").apply(tuple, axis=1).to_dict()
    )

    for country, years in expenditure_years.items():
        country_info[country]["expenditure_years"] = years

    for country, years in poverty_years.items():
        country_info[country]["poverty_years"] = years

    for country, info in country_info.items():
        country_income_level = info["income_level"]
        info["poverty_bounds"] = poverty_level_stats[country_income_level]

    return country_info


def load_subnat_boundaries():
    """Load all subnational boundaries for all countries in one DB call."""
    countries = _countries()
    df = _db().get_adm_boundaries(countries)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {"country": x[0], "region": x[1]},
                "geometry": json.loads(x[2]),
            }
            for x in zip(df.country_name, df.admin1_region, df.boundary)
        ],
    }


def load_health_public_expenditure():
    exp_by_func = server_cache.get("func_by_country_year")
    return exp_by_func[exp_by_func.func == "Health"]


def load_edu_public_expenditure():
    exp_by_func = server_cache.get("func_by_country_year")
    return exp_by_func[exp_by_func.func == "Education"]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_all():
    """Register all loaders with server_cache. Call once at module level."""
    # Simple pass-throughs
    server_cache.register("expenditure_w_poverty", load_expenditure_w_poverty)
    server_cache.register("subnational_poverty_rate", load_subnational_poverty_rate)
    server_cache.register("geo1_expenditure", load_geo1_expenditure)
    server_cache.register("geo1_func_expenditure", load_geo1_func_expenditure)
    server_cache.register("sub_func_expenditure", load_sub_func_expenditure)
    server_cache.register("pefa", load_pefa)
    server_cache.register("uhc_index", load_uhc_index)
    server_cache.register("health_private_expenditure", load_health_private_expenditure)
    server_cache.register("health_sub_func_expenditure", load_health_sub_func_expenditure)
    server_cache.register("learning_poverty", load_learning_poverty)
    server_cache.register("hd_index", load_hd_index)
    server_cache.register("edu_private_expenditure", load_edu_private_expenditure)

    # Transformation loaders
    server_cache.register("func_econ_raw", load_func_econ_raw)
    server_cache.register("func_by_country_year", load_func_by_country_year)
    server_cache.register("econ_by_country_year", load_econ_by_country_year)
    server_cache.register("prop_econ_by_func", load_prop_econ_by_func)
    server_cache.register("disputed_boundaries", load_disputed_boundaries)
    server_cache.register("subnat_boundaries", load_subnat_boundaries)
    server_cache.register("basic_country_info", load_basic_country_info)
    server_cache.register("health_public_expenditure", load_health_public_expenditure)
    server_cache.register("edu_public_expenditure", load_edu_public_expenditure)
