import os
import time
import logging
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config, oauth_service_principal
from databricks.sdk import WorkspaceClient

from query_cache import PersistentQueryCache


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

PUBLIC_ONLY = os.getenv("PUBLIC_ONLY", "False").lower() in ("true", "1", "yes")
BOOST_SCHEMA = os.getenv("BOOST_SCHEMA", "boost")
INDICATOR_SCHEMA = os.getenv("INDICATOR_SCHEMA", "indicator")
# Cache tuning (env overrides optional). Invalidation is via the
# external refresh endpoint in server.py.
QUERY_CACHE_DIR = os.getenv("QUERY_CACHE_DIR", "./cache/queries")
QUERY_CACHE_MAX_ENTRIES = int(os.getenv("QUERY_CACHE_MAX_ENTRIES", "256"))
SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")

def credentials_provider():
    print("Initializing credential provider...")
    config = Config(
        host = f"https://{SERVER_HOSTNAME}",
        client_id     = os.getenv("DATABRICKS_CLIENT_ID"),
        client_secret = os.getenv("DATABRICKS_CLIENT_SECRET"))
    return oauth_service_principal(config)


class QueryService:
    _instance = None

    @staticmethod
    def get_instance():
        if QueryService._instance is None:
            QueryService._instance = QueryService()
        return QueryService._instance

    def __init__(self):
        self._cache = PersistentQueryCache(
            cache_dir=QUERY_CACHE_DIR,
            max_entries=QUERY_CACHE_MAX_ENTRIES,
        )

        self.country_whitelist = None
        if PUBLIC_ONLY:
            query = f"""
                SELECT country_name, boost_source_url
                FROM prd_mega.{BOOST_SCHEMA}.data_availability
                WHERE boost_public = 'Yes'
            """
            self.country_whitelist = self.execute_query(query)["country_name"].tolist()

    def clear_cache(self):
        self._cache.clear()

    def execute_query(self, query, persistent: bool = True):
        """Run `query` and return a DataFrame. `persistent=False` bypasses
        the disk cache (used for credentials)."""
        if persistent:
            cached = self._cache.get(query)
            if cached is not None:
                return cached

        start = time.time()
        with sql.connect(
            server_hostname = SERVER_HOSTNAME,
            http_path = os.getenv("DATABRICKS_HTTP_PATH"),
            credentials_provider=credentials_provider,
        ) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            df = cursor.fetchall_arrow().to_pandas()

        logging.info(f"DB MISS (queried) took {time.time() - start:.2f} sec. query: {query}")

        if persistent:
            self._cache.set(query, df)
        return df.copy(deep=True)

    def fetch_data(self, query):
        df = self.execute_query(query)
        return self._apply_country_whitelist_filter(df)

    def _apply_country_whitelist_filter(self, df):
        if self.country_whitelist is not None and "country_name" in df.columns:
            return df[df["country_name"].isin(self.country_whitelist)]
        return df

    def get_expenditure_w_poverty_by_country_year(self):
        query = f"""
            SELECT *
            FROM prd_mega.{BOOST_SCHEMA}.pov_expenditure_by_country_year
        """
        df = self.fetch_data(query)
        df.loc[:, "decentralized_expenditure"] = df["decentralized_expenditure"].fillna(
            0
        )
        return df

    def get_edu_private_expenditure(self):
        query = f"""
            SELECT country_name, year, real_expenditure
            FROM prd_mega.{BOOST_SCHEMA}.edu_private_expenditure_by_country_year
        """
        return self.fetch_data(query)

    def get_hd_index(self, countries):
        country_list = "', '".join(countries)
        query = f"""
            SELECT * FROM prd_mega.{INDICATOR_SCHEMA}.global_data_lab_hd_index
            WHERE country_name IN ('{country_list}')
            ORDER BY country_name, year
        """
        return self.fetch_data(query)

    def get_learning_poverty_rate(self):
        query = f"""
            SELECT * FROM prd_mega.{INDICATOR_SCHEMA}.learning_poverty_rate
        """
        return self.fetch_data(query)

    def get_expenditure_by_country_func_econ_year(self):
        query = f"""
            SELECT * FROM prd_mega.{BOOST_SCHEMA}.expenditure_by_country_func_econ_year
        """
        return self.fetch_data(query)

    def get_expenditure_by_country_sub_func_year(self):
        query = f"""
            SELECT country_name, geo0, year, func, latest_year, func_sub, expenditure, real_expenditure
            FROM prd_mega.{BOOST_SCHEMA}.expenditure_by_country_geo0_func_sub_year
        """
        return self.fetch_data(query)

    def get_basic_country_data(self, countries):
        country_list = "', '".join(countries)
        query = f"""
            SELECT country_name, display_lon, display_lat, zoom, income_level, currency_name, currency_code
            FROM prd_mega.{INDICATOR_SCHEMA}.country
            WHERE country_name IN ('{country_list}')
        """
        return self.fetch_data(query)

    def get_expenditure_by_country_geo1_year(self):
        query = f"""
            SELECT country_name, year, adm1_name, expenditure, per_capita_expenditure
            FROM prd_mega.{BOOST_SCHEMA}.expenditure_by_country_geo1_year
        """
        return self.fetch_data(query)

    def get_adm_boundaries(self, countries):
        country_list = "', '".join(countries)
        query = f"""
            SELECT country_name, admin1_region, boundary
            FROM prd_mega.{INDICATOR_SCHEMA}.admin1_boundaries_gold
            WHERE country_name IN ('{country_list}')
        """
        return self.fetch_data(query)

    def get_disputed_boundaries(self, countries):
        country_list = "', '".join(countries)
        query = f"""
            SELECT country_name, boundary, region_name
            FROM prd_mega.{INDICATOR_SCHEMA}.admin0_disputed_boundaries_gold
            WHERE country_name IN ('{country_list}')
        """
        return self.fetch_data(query)

    def get_subnational_poverty_rate(self, countries):
        country_list = "', '".join(countries)
        query = f"""
            SELECT * FROM prd_mega.{INDICATOR_SCHEMA}.subnational_poverty_rate
            WHERE country_name IN ('{country_list}')
        """
        return self.fetch_data(query)

    def get_universal_health_coverage_index(self):
        query = f"""
            SELECT * FROM prd_mega.{INDICATOR_SCHEMA}.universal_health_coverage_index_gho
        """
        return self.fetch_data(query)

    def get_health_private_expenditure(self):
        query = f"""
            SELECT country_name, year, real_expenditure
            FROM prd_mega.{BOOST_SCHEMA}.health_private_expenditure_by_country_year
        """
        return self.fetch_data(query)

    def expenditure_and_outcome_by_country_geo1_func_year(self):
        query = f"""
            SELECT * FROM prd_mega.{BOOST_SCHEMA}.expenditure_and_outcome_by_country_geo1_func_year
        """
        return self.fetch_data(query)

    def get_pefa(self, countries):
        country_list = "', '".join(countries)
        query = f"""
            SELECT * FROM prd_mega.{INDICATOR_SCHEMA}.pefa_by_pillar
            WHERE country_name IN ('{country_list}')
            ORDER BY country_name, year
        """
        return self.fetch_data(query)

    def get_user_credentials(self):
        query = f"""
            SELECT username, salted_password
            FROM prd_mega.sboost4.dashboard_user_credentials
        """
        df = self.execute_query(query, persistent=False)
        return dict(zip(df["username"], df["salted_password"]))


    def get_indicator_data_availability(self):
        query = f"""
            SELECT country_name, indicator_key, earliest_year, latest_year, source_url
            FROM prd_mega.{INDICATOR_SCHEMA}.indicator_data_availability
        """
        return self.fetch_data(query)

    def get_boost_source_urls(self):
        query = f"""
            SELECT
                country_name,
                boost_source_url AS source_url,
                boost_earliest_year AS earliest_year,
                boost_latest_year AS latest_year
            FROM prd_mega.{BOOST_SCHEMA}.data_availability
        """
        return self.fetch_data(query)
