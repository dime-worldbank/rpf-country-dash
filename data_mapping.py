"""
Mapping of server_store cache keys to the functions that produce the data.

server_store reads `function_data_mapping` on a cache miss so that a
recycled process can self-heal without waiting for the fetch-once
Dash callbacks to re-fire. Nothing here runs at import time.

Functions that need a `countries` list obtain it by first looking up
the expenditure_w_poverty key (which has no parameters).
"""
import json
import pandas as pd
from queries import QueryService
from components.func_operational_vs_capital_spending import prepare_prop_econ_by_func_df
import server_store


def _db():
    return QueryService.get_instance()


def _countries():
    """Derive the countries list from expenditure_w_poverty (parameter-free)."""
    df = server_store.lookup("expenditure_w_poverty")
    return sorted(df["country_name"].unique())


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
    if server_store.has("func_by_country_year"):
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
    server_store.set("func_econ_raw", func_econ_df)
    server_store.set("func_by_country_year", func_df)
    server_store.set("econ_by_country_year", econ_df)
    server_store.set("prop_econ_by_func", prop_econ_by_func_df)


def load_func_econ_raw():
    _load_func_econ_group()
    return server_store.lookup("func_econ_raw")


def load_func_by_country_year():
    _load_func_econ_group()
    return server_store.lookup("func_by_country_year")


def load_econ_by_country_year():
    _load_func_econ_group()
    return server_store.lookup("econ_by_country_year")


def load_prop_econ_by_func():
    _load_func_econ_group()
    return server_store.lookup("prop_econ_by_func")


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

    expenditure_df = server_store.lookup("geo1_expenditure")[["country_name", "year"]]
    poverty_df = server_store.lookup("subnational_poverty_rate")[
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
    exp_by_func = server_store.lookup("func_by_country_year")
    return exp_by_func[exp_by_func.func == "Health"]


def load_edu_public_expenditure():
    exp_by_func = server_store.lookup("func_by_country_year")
    return exp_by_func[exp_by_func.func == "Education"]


# ---------------------------------------------------------------------------
# Mapping of cache keys to the function that produces the data.
# server_store uses this to auto-populate a key on cache miss.
# ---------------------------------------------------------------------------

function_data_mapping = {
    # Simple pass-throughs
    "expenditure_w_poverty": lambda: _db().get_expenditure_w_poverty_by_country_year(),
    "subnational_poverty_rate": lambda: _db().get_subnational_poverty_rate(_countries()),
    "geo1_expenditure": lambda: _db().get_expenditure_by_country_geo1_year(),
    "geo1_func_expenditure": lambda: _db().expenditure_and_outcome_by_country_geo1_func_year(),
    "sub_func_expenditure": lambda: _db().get_expenditure_by_country_sub_func_year(),
    "pefa": lambda: _db().get_pefa(_countries()),
    "uhc_index": lambda: _db().get_universal_health_coverage_index(),
    "health_private_expenditure": lambda: _db().get_health_private_expenditure(),
    "learning_poverty": lambda: _db().get_learning_poverty_rate(),
    "hd_index": lambda: _db().get_hd_index(_countries()),
    "edu_private_expenditure": lambda: _db().get_edu_private_expenditure(),
    # Transformation loaders
    "func_econ_raw": load_func_econ_raw,
    "func_by_country_year": load_func_by_country_year,
    "econ_by_country_year": load_econ_by_country_year,
    "prop_econ_by_func": load_prop_econ_by_func,
    "disputed_boundaries": load_disputed_boundaries,
    "subnat_boundaries": load_subnat_boundaries,
    "basic_country_info": load_basic_country_info,
    "health_public_expenditure": load_health_public_expenditure,
    "edu_public_expenditure": load_edu_public_expenditure,
}
