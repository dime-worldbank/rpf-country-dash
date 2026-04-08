# RPF-Country-Dash
Dash app for displaying visualizations fro RPF project

## Development

First `git clone` this repo.

Then prepare .env: `cp .env.example .env`

Then generate and obtain your access token from databricks following this instruction: https://docs.databricks.com/en/dev-tools/auth/pat.html
Get connection details for the SQL Warehouse compute resource which is used for providing the database connection: https://docs.databricks.com/en/integrations/compute-details.html

Export the obtained information to the following environment variables, update them in .env file:

```bash
DATABRICKS_CLIENT_ID="YOUR_CLIENT_ID_HERE"
DATABRICKS_CLIENT_SECRET="YOUR_CLIENT_SECRET_HERE"
DATABRICKS_HTTP_PATH="YOUR_HTTP_PATH_HERE"
DATABRICKS_SERVER_HOSTNAME="YOUR_SERVER_HOSTNAME_HERE"
```

Then to setup and verify the app works locally:

```bash
pip install -r requirements.txt
dotenv run -- python app.py
open http://127.0.0.1:8050/
```
You should see the data app.

### Tests

To run the python unit tests:

```
python -m unittest discover tests/
```

Make sure all tests pass locally before sending a PR.

## Development within docker container
1. Edit .env to update your environment variables after copying the sample env file. (Do not use quotations around the values)

```bash
cp .env.example .env
```

2. Run the following commands

```bash
docker build . --tag dash
docker run -p 8080:8080 -v ./:/dash-app  --env-file .env dash
```

## Deployment

To deploy a version of the app with authentication enabled, post deployment set the following env vars:
```
AUTH_ENABLED=1
SECRET_KEY=yoursecretkey
```

The app will read usernames and salted passwords from the database, so be sure to configure them there: see `QueryService.get_user_credentials`. You may use [scripts/hash_password.py](scripts/hash_password.py) to hash passwords.

## Persistent query cache

Databricks queries are slow, so the app caches results on local disk as parquet
files. The cache survives worker/process restarts so users rarely wait on a
cold query.

The cache is intentionally long-lived and is invalidated by an **external
refresh endpoint** that the upstream data pipeline calls after loading new
data. The refresh clears the cache and pre-warms it by re-running every
parameterless "global" query in `QueryService.PREWARM_QUERY_NAMES`, so the
first visitor after a data refresh also gets instant page loads.

### Env vars

| Name | Default | Purpose |
|---|---|---|
| `QUERY_CACHE_DIR` | `./cache/queries` | Directory where parquet cache files live. On Posit Connect this sits in the content working directory. |
| `QUERY_CACHE_TTL_SECONDS` | `86400` | Safety ceiling in seconds. The refresh endpoint is the primary invalidator. |
| `QUERY_CACHE_MAX_ENTRIES` | `256` | In-memory LRU ceiling. The on-disk cache is unbounded within the dir. |
| `CACHE_REFRESH_TOKEN` | *(unset)* | Shared secret for the refresh endpoint. If unset, the endpoint returns `503`. |

### Endpoints

Set `CACHE_REFRESH_TOKEN` to a strong random value and have the pipeline call:

```bash
curl -X POST \
  -H "X-Refresh-Token: $CACHE_REFRESH_TOKEN" \
  https://<your-posit-connect-host>/<content-path>/api/cache/refresh
```

Response is JSON with per-query status and timing. HTTP `200` = all queries
refreshed, `207` = partial failure (inspect `queries[].status`), `401` = bad
token, `503` = endpoint disabled (token env var unset).

A companion `GET /api/cache/status` (same `X-Refresh-Token` header) lists
currently cached entries with row counts and file sizes — handy for pipeline
verification.
