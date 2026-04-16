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

Databricks queries are slow, so results are cached on local disk as parquet
files. The cache survives worker/process restarts, so users rarely wait on a
cold query. Credential queries bypass the disk cache (`persistent=False`).

Invalidation is driven by an external clear endpoint. The upstream data
pipeline calls it after loading new data; the endpoint clears both the parquet
cache and the in-memory `server_store` so the next dashboard visitor sees
fresh data. Repopulation is lazy — the first visitor after a clear pays the
DB cost; everyone after them hits the cache.

### Env vars

| Name | Default | Purpose |
|---|---|---|
| `QUERY_CACHE_DIR` | `./cache/queries` | Directory where parquet files live. |
| `QUERY_CACHE_TTL_SECONDS` | `604800` (7 days) | Safety ceiling. The clear endpoint is the primary invalidator. |
| `QUERY_CACHE_MAX_ENTRIES` | `256` | In-memory LRU ceiling. The on-disk cache is unbounded within the dir. |
| `CACHE_REFRESH_TOKEN` | *(unset)* | Shared secret for the clear endpoint. If unset, the endpoint returns `503`. |

### Endpoint

Set `CACHE_REFRESH_TOKEN` to a strong random value and have the pipeline call:

```bash
curl -X POST \
  -H "X-Refresh-Token: $CACHE_REFRESH_TOKEN" \
  https://<host>/api/cache/clear
```

Response is `{"status": "ok", "cleared_at": <epoch>}`. HTTP `200` = cleared,
`401` = bad token, `503` = endpoint disabled (token env var unset).
