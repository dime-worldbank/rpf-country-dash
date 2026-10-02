import os
import threading
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from databricks import sql
import psycopg
from queries import QueryService, PUBLIC_ONLY

class TestQueryService(unittest.TestCase):

    def setUp(self):
        self.patcher = patch.object(QueryService, "execute_query")
        self.mock_execute_query = self.patcher.start()
        self.mock_table_df = pd.DataFrame({
            'country_name': ['Country1', 'Country2'],
            'year': [2020, 2021],
            'value': [100, 200]
        })
        self.mock_execute_query.return_value = self.mock_table_df

        self.query_service = QueryService.get_instance()

    def tearDown(self):
        # Reset the singleton instance after each test to avoid test interference
        QueryService._instance = None

        self.patcher.stop()


    def test_singleton_instance(self):
        instance1 = QueryService.get_instance()
        instance2 = QueryService.get_instance()
        self.assertIs(instance1, instance2)

    def test_init_country_whitelist_conditions_on_public_only(self):
        with patch("queries.PUBLIC_ONLY", False):
            service = QueryService()
            self.assertIsNone(service.country_whitelist)

        with patch("queries.PUBLIC_ONLY", True):
            service = QueryService()
            self.assertIsNotNone(service.country_whitelist)

    @patch("queries.PUBLIC_ONLY", False)
    def test_fetch_data_no_filter(self):
        df = self.query_service.fetch_data("SELECT * FROM test_table")
        pd.testing.assert_frame_equal(df, self.mock_table_df)

    @patch("queries.PUBLIC_ONLY", True)
    def test_fetch_data_applies_country_whitelist(self):
        # Mock country_whitelist
        self.query_service.country_whitelist = ["Country1"]

        df = self.query_service.fetch_data("SELECT * FROM test_table")
        expected_df = self.mock_table_df[self.mock_table_df['country_name'] == 'Country1']
        pd.testing.assert_frame_equal(df, expected_df)

    @patch("queries.PUBLIC_ONLY", True)
    def test_get_expenditure_w_poverty_by_country_year(self):
        self.query_service.country_whitelist = ["Country1"]
        self.mock_table_df['decentralized_expenditure'] = None

        df = self.query_service.get_expenditure_w_poverty_by_country_year()

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["country_name"], "Country1")
        self.assertEqual(df.iloc[0]["decentralized_expenditure"], 0)

    def test_get_indicator_data_availability_returns_all_columns(self):
        self.mock_execute_query.return_value = pd.DataFrame({
            "country_name": ["Albania", "Albania"],
            "indicator_key": ["poverty_rate", "pefa_by_pillar"],
            "earliest_year": [2012, 2016],
            "latest_year": [2020, 2022],
            "source_url": ["https://example.com/pip", "https://example.com/pefa"],
        })
        df = self.query_service.get_indicator_data_availability()
        self.assertEqual(len(df), 2)
        self.assertListEqual(
            list(df.columns),
            ["country_name", "indicator_key", "earliest_year", "latest_year", "source_url"],
        )

    @patch("queries.PUBLIC_ONLY", True)
    def test_get_indicator_data_availability_filters_by_whitelist(self):
        self.query_service.country_whitelist = ["Albania"]
        self.mock_execute_query.return_value = pd.DataFrame({
            "country_name": ["Albania", "Brazil"],
            "indicator_key": ["poverty_rate", "poverty_rate"],
            "earliest_year": [2012, 2010],
            "latest_year": [2020, 2021],
            "source_url": ["https://example.com/1", "https://example.com/2"],
        })
        df = self.query_service.get_indicator_data_availability()
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["country_name"], "Albania")

    def test_get_boost_source_urls_returns_all_columns(self):
        self.mock_execute_query.return_value = pd.DataFrame({
            "country_name": ["Albania", "Kenya"],
            "boost_source_url": ["https://example.com/alb", "https://example.com/ken"],
            "boost_earliest_year": [2010, 2012],
            "boost_latest_year": [2020, 2022],
        })
        df = self.query_service.get_boost_source_urls()
        self.assertEqual(len(df), 2)
        self.assertListEqual(
            list(df.columns),
            ["country_name", "boost_source_url", "boost_earliest_year", "boost_latest_year"],
        )

    @patch("queries.PUBLIC_ONLY", True)
    def test_get_boost_source_urls_filters_by_whitelist(self):
        self.query_service.country_whitelist = ["Kenya"]
        self.mock_execute_query.return_value = pd.DataFrame({
            "country_name": ["Albania", "Kenya"],
            "boost_source_url": ["https://example.com/alb", "https://example.com/ken"],
            "boost_earliest_year": [2010, 2012],
            "boost_latest_year": [2020, 2022],
        })
        df = self.query_service.get_boost_source_urls()
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["country_name"], "Kenya")


def _mock_connection(df=None):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.fetchall_arrow.return_value.to_pandas.return_value = (
        df if df is not None else pd.DataFrame({"x": [1]})
    )
    return conn


@patch("queries.PUBLIC_ONLY", False)
class TestQueryServiceConnection(unittest.TestCase):

    def setUp(self):
        self.connect_patcher = patch("queries.sql.connect")
        self.mock_connect = self.connect_patcher.start()
        self.service = QueryService()

    def tearDown(self):
        self.connect_patcher.stop()

    def test_falls_back_to_access_token_when_oauth_fails(self):
        token_conn = _mock_connection()
        self.mock_connect.side_effect = [Exception("oauth failed"), token_conn]

        with patch.dict(os.environ, {"DATABRICKS_ACCESS_TOKEN": "tok"}):
            self.service.execute_query("SELECT 1", persistent=False)

        self.assertEqual(self.mock_connect.call_count, 2)
        self.assertEqual(self.mock_connect.call_args.kwargs["access_token"], "tok")



    def test_connection_reused_within_thread_but_not_shared_across_threads(self):
        self.mock_connect.side_effect = lambda **kwargs: _mock_connection()
        conns = {}

        def run(name):
            self.service.execute_query("SELECT 1", persistent=False)
            self.service.execute_query("SELECT 2", persistent=False)
            conns[name] = self.service._local.conn

        threads = [threading.Thread(target=run, args=(i,)) for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(self.mock_connect.call_count, 2)
        self.assertIsNot(conns[0], conns[1])

    def test_reconnects_and_retries_on_databricks_error(self):
        stale_conn = _mock_connection()
        stale_conn.cursor.return_value.__enter__.return_value.execute.side_effect = (
            sql.exc.ServerOperationError("Invalid SessionHandle")
        )
        expected = pd.DataFrame({"x": [42]})
        self.mock_connect.side_effect = [stale_conn, _mock_connection(expected)]

        df = self.service.execute_query("SELECT 1", persistent=False)

        pd.testing.assert_frame_equal(df, expected)
        stale_conn.close.assert_called_once()
        self.assertEqual(self.mock_connect.call_count, 2)

    def test_does_not_retry_non_databricks_errors(self):
        conn = _mock_connection()
        conn.cursor.return_value.__enter__.return_value.execute.side_effect = ValueError("bug")
        self.mock_connect.return_value = conn

        with self.assertRaises(ValueError):
            self.service.execute_query("SELECT 1", persistent=False)

        self.mock_connect.assert_called_once()
        conn.close.assert_not_called()

if __name__ == "__main__":
    unittest.main()


def _pg_connection(rows, columns, type_codes):
    conn = MagicMock()
    cursor = conn.cursor.return_value.__enter__.return_value
    cursor.description = [MagicMock(type_code=code) for code in type_codes]
    for desc, name in zip(cursor.description, columns):
        desc.name = name
    cursor.fetchall.return_value = rows
    return conn


@patch("queries.PUBLIC_ONLY", False)
@patch("queries.DB_BACKEND", "postgres")
@patch.dict(os.environ, {"POSTGRES_DSN": "postgresql://u:p@db/prd_mega"})
class TestQueryServicePostgres(unittest.TestCase):

    @patch("queries.sql.connect")
    @patch("queries.psycopg.connect")
    def test_connects_to_postgres_dsn(self, pg_connect, dbx_connect):
        pg_connect.return_value = _pg_connection([(1,)], ["x"], [20])

        QueryService().execute_query("SELECT 1", persistent=False)

        pg_connect.assert_called_once_with("postgresql://u:p@db/prd_mega", autocommit=True)
        dbx_connect.assert_not_called()

    @patch("queries.psycopg.connect")
    def test_returns_dataframe_with_column_names(self, pg_connect):
        pg_connect.return_value = _pg_connection(
            [("Togo", 2021), ("Togo", 2022)], ["country_name", "year"], [25, 20])

        df = QueryService().execute_query("SELECT country_name, year FROM t", persistent=False)

        pd.testing.assert_frame_equal(
            df, pd.DataFrame({"country_name": ["Togo", "Togo"], "year": [2021, 2022]}))

    @patch("queries.psycopg.connect")
    def test_null_numeric_column_is_float_nan(self, pg_connect):
        pg_connect.return_value = _pg_connection([(None,), (None,)], ["decentralized"], [701])

        df = QueryService().execute_query("SELECT decentralized FROM t", persistent=False)

        self.assertEqual(df["decentralized"].dtype, "float64")
        self.assertTrue(df["decentralized"].isna().all())

    @patch("queries.psycopg.connect")
    def test_reconnects_once_when_the_connection_dropped(self, pg_connect):
        stale = _pg_connection([], ["x"], [20])
        stale.cursor.return_value.__enter__.return_value.execute.side_effect = (
            psycopg.OperationalError("server closed the connection unexpectedly"))
        pg_connect.side_effect = [stale, _pg_connection([(42,)], ["x"], [20])]

        df = QueryService().execute_query("SELECT 1", persistent=False)

        self.assertEqual(df["x"].tolist(), [42])
        self.assertEqual(pg_connect.call_count, 2)

