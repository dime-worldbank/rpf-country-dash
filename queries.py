import os
import time
import logging
import threading
import pandas as pd
from databricks import sql
from databricks.sdk.core import Config, oauth_service_principal
from databricks.sdk import WorkspaceClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

PUBLIC_ONLY = os.getenv("PUBLIC_ONLY", "False").lower() in ("true", "1", "yes")
BOOST_SCHEMA = os.getenv("BOOST_SCHEMA", "boost")
INDICATOR_SCHEMA = os.getenv("INDICATOR_SCHEMA", "indicator")
# Cache tuning (env overrides optional)
QUERY_CACHE_TTL_SECONDS = int(os.getenv("QUERY_CACHE_TTL_SECONDS", "300"))  # 5 min
QUERY_CACHE_MAX_ENTRIES = int(os.getenv("QUERY_CACHE_MAX_ENTRIES", "256"))
SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_ACCESS_TOKEN = os.getenv("DATABRICKS_ACCESS_TOKEN")

def credentials_provider():
    logging.info("Initializing credential provider...")
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
        # Simple TTL cache: {query: (expires_at_epoch, dataframe)}
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = QUERY_CACHE_TTL_SECONDS
        self._cache_max_entries = QUERY_CACHE_MAX_ENTRIES

        # Connection management
        self._conn = None
        self._conn_lock = threading.Lock()

        self.country_whitelist = None
        if PUBLIC_ONLY:
            query = f"""
                SELECT country_name, boost_source_url
                FROM prd_mega.{BOOST_SCHEMA}.data_availability
                WHERE boost_public = 'Yes'
            """
            self.country_whitelist = self.execute_query(query)["country_name"].tolist()

    # ---- Connection management ------------------------------------------------
    def _create_connection(self):
        http_path = os.getenv("DATABRICKS_HTTP_PATH")
        try:
            conn = sql.connect(
                server_hostname=SERVER_HOSTNAME,
                http_path=http_path,
                credentials_provider=credentials_provider,
            )
            logging.info("Connected using service principal OAuth")
            return conn
        except Exception as e:
            if DATABRICKS_ACCESS_TOKEN:
                logging.warning("Service principal auth failed: %s. Falling back to access token.", e)
                conn = sql.connect(
                    server_hostname=SERVER_HOSTNAME,
                    http_path=http_path,
                    access_token=DATABRICKS_ACCESS_TOKEN,
                )
                logging.info("Connected using access token")
                return conn
            else:
                raise

    def _get_connection(self):
        with self._conn_lock:
            if self._conn is None:
                self._conn = self._create_connection()
            return self._conn

    def _close_connection(self):
        with self._conn_lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

    # ---- Cache helpers -------------------------------------------------------
    def _cache_get(self, key):
        now = time.time()
        with self._cache_lock:
            hit = self._cache.get(key)
            if not hit:
                return None
            expires_at, df = hit
            if now >= expires_at:
                # expired; remove and miss
                del self._cache[key]
                return None
            return df

    def _cache_set(self, key, df):
        expires_at = time.time() + self._cache_ttl
        with self._cache_lock:
            # Evict oldest one if we exceed max size (simple FIFO)
            if len(self._cache) >= self._cache_max_entries:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[key] = (expires_at, df)

    def clear_cache(self):
        with self._cache_lock:
            self._cache.clear()
        logging.info("Query cache cleared")

    def invalidate_query(self, query: str):
        with self._cache_lock:
            removed = self._cache.pop(query, None) is not None
        if removed:
            logging.info("Invalidated cache for query: %s", query)

    # ---- Cached databricks query ---------------------------------------------
    def execute_query(self, query):
        """
        Executes a query and returns the result as a pandas DataFrame.
        """
        cached = self._cache_get(query)
        if cached is not None:
            logging.info("CACHE HIT for query (TTL=%ss): %s", self._cache_ttl, query)
            return cached.copy(deep=True)

        start = time.time()
        try:
            df = self._execute_with_connection(query)
        except Exception as e:
            logging.warning("Query failed, reconnecting: %s", e)
            self._close_connection()
            df = self._execute_with_connection(query)

        logging.info(f"DB MISS (queried) took {time.time() - start:.2f} sec. query: {query}")

        self._cache_set(query, df)
        return df.copy(deep=True)

    def _execute_with_connection(self, query):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

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
        df = self.execute_query(query)
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
