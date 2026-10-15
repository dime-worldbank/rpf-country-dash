# RPF-Country-Dash
Dash app for displaying visualizations for RPF project

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

## Adding a new chart

A chart is four pieces: the data it reads, a figure builder, the layout and
callback that put it on a page, and its translations.
`components/budget_funding_execution.py` ("How is the budget financed?", wired
up in `pages/home.py`) is a complete example to copy from.

1. **Data.** Charts never query the database directly; they read DataFrames
   from `server_store.get("<key>")`. If the data isn't there yet, add a method
   to `QueryService` in `queries.py` and register a loader under a new key in
   `function_data_mapping` in `data_mapping.py`. The loader runs on the first
   `get` of the key and its result is cached (see *Persistent query cache*).
   Derived columns belong in a transformation loader in `data_mapping.py`,
   next to the existing ones, not in the chart code.

2. **Figure builder.** Write a pure function that takes a DataFrame and
   returns a `go.Figure`, e.g. `create_<chart>_figure(df, currency_code,
   lang="en")`, so it can be tested without Dash. House conventions, all in
   `utils.py` unless noted:
   - Filter with `filter_country_sort_year(df, country)` and return
     `empty_plot(t("error.<key>", lang))` when nothing is left.
   - Every visible string goes through `t()`: chart title (`chart.*`), axis
     labels (`axis.*`), trace names (`trace.*`), hover labels (`hover.*`).
   - Money values: format them with `add_currency_column` / `format_currency`
     into `customdata` and reference that in `hovertemplate`, so hover text is
     localized. Then scale the axis with
     `scale_currency_axes(fig, ["y"], peak, currency, lang)` and put the unit
     it returns in the axis title with `currency_axis_title` (or call
     `format_currency_yaxis`, which does both). Ticks stay plain numbers and
     the title says "milliards de FCFA". Year axes: `format_year_axis(fig)`.
   - Colours come from `viz_theme.py` (`QUALITATIVE`, `CENTRAL_COLOR`,
     `REGIONAL_COLOR`, ...). Fonts, grid lines and margins come from the global
     template, so don't set them per chart. `plot_bgcolor="white"`,
     `hovermode="x unified"` and `fixedrange=True` on value axes are the
     house style.
   - Finish with `return apply_locale(fig, lang)`, which sets the decimal
     separator for French and Portuguese.
   - Keep narrative text in a separate function that returns a string (or
     Dash components) built from `t("narrative.*")` templates; see *Narrative
     Generation* for the trend sentences.

3. **Layout.** In the page's `layout()`, add `chart_container("<chart-id>")`
   from `components/source_metadata_popover.py`. It creates the `dcc.Graph`
   with that id plus the ⓘ button. Add an `html.Div` next to it for the
   narrative, e.g. `id="<chart-id>-narrative"`. Register the chart's data
   sources under the same id in `CHART_METADATA` in that module, otherwise the
   ⓘ popover has nothing to show.

4. **Callback.** In the page module, render the figure (and narrative)
   whenever the shared data, country or language changes:

   ```python
   @callback(
       Output("<chart-id>", "figure"),
       Output("<chart-id>-narrative", "children"),
       Input("stored-data", "data"),
       Input("country-select", "value"),
       Input("stored-language", "data"),
   )
   def render_<chart>(data, country, lang):
       lang = lang or "en"
       if not data or not country:
           return dash.no_update, dash.no_update
       df = filter_country_sort_year(server_store.get("<key>"), country)
       currency_code = server_store.get("basic_country_info")[country]["currency_code"]
       return create_<chart>_figure(df, currency_code, lang=lang), <chart>_narrative(df, lang=lang)
   ```

   Add an `Input` for any control of its own (a `dbc.RadioItems` for nominal
   vs real, for instance). If the chart is the first to use a dataset, add a
   `dcc.Store(id="stored-data-<x>")` to the layout and a
   `fetch_<x>_data_once` callback like the ones at the top of
   `pages/home.py`, so the first visit triggers the load.

5. **Translations.** Add every new key to `translations/en.py`, `fr.py` and
   `pt.py` (see *Adding Translations* below). A key missing from a language
   silently falls back to English, so check the French and Portuguese pages.

6. **Tests.** Add a `unittest` case under `tests/`. Drive the render function
   with a `server_store.get` stand-in, a dict keyed like the real store (see
   `tests/test_budget_funding_execution.py`), and assert on `fig.data` and
   `fig.layout` rather than on pixels. Page modules call `dash.register_page`
   on import, so create `dash.Dash(__name__, use_pages=True, pages_folder="")`
   first, as `tests/test_public_private_figure.py` does. Then run
   `python -m unittest discover tests/`.

## Internationalization (i18n)

This application supports **English**, **French**, and **Brazilian Portuguese** with full internationalization:

- **UI:** Language selector in the application header
- **Narratives:** Automated spending and outcome narratives generated in both languages
- **Metadata:** All chart titles, labels, and help text translated

### Supported Languages

| Code | Language |
|------|----------|
| `en` | English |
| `fr` | Français |
| `pt` | Português (Brasil) |

### Using Different Languages

Select your preferred language from the language dropdown in the application header. The choice lasts for the browser session; each new visit opens in the language set by `DEFAULT_LANGUAGE` (en, fr or pt; default en).

### For Developers: Working with Translations

**Translation Files:**
- `translations/__init__.py` - Translation system and grammar helpers (genitive, preposition, elision, article stripping)
- `translations/en.py` - English translations (40KB)
- `translations/fr.py` - French translations with grammatical properties (50KB)
- `translations/pt.py` - Brazilian Portuguese translations with grammatical properties

**Grammar Helpers for French and Portuguese:**

The `translations/__init__.py` module provides language-specific grammar functions:
- `genitive(lang, name)` - Handles "of X" constructions, including French `de/du/des` and Portuguese `de/da/do/das/dos`
- `preposition(lang, noun_or_meta)` - Handles location expressions such as French `en/au/aux` and Portuguese `em/na/no/nas/nos`
- `elide_que(lang, name)` - Handles French `que` vs `qu'` elision before vowels
- `strip_article(lang, name)` - Removes leading articles for dropdown labels

**Adding Translations:**

1. Add English key-value pair to `translations/en.py`
2. Add French translation to `translations/fr.py` and Brazilian Portuguese translation to `translations/pt.py`
   - **All `sector.*`, `country.*`, and `func.*` entries that need grammar MUST use dict format with grammatical properties** to support dynamic prepositions:
     ```python
     "sector.health": {"name": "santé", "plural": False, "feminine": True},
     "func.example": {"name": "exemple", "plural": False, "feminine": False},
     "country.Kenya": {"name": "o Quênia", "plural": False, "feminine": False, "article": "o"},
     ```
   - **For metrics used in trend-narrative**, use dict format with grammatical properties:
     ```python
     "metric.example": {
         "name": "les dépenses",
         "plural": True,
         "feminine": True
     }
     ```
   - Plain string values are acceptable for other content that doesn't need grammatical agreement
3. Use `t("key.name", lang)` to access translations in code
4. For nouns used after "de/of", wrap with `genitive(lang, name)`
5. For language-specific prepositions, use `preposition(lang, noun_or_meta)` with sector/func/country metadata

**Testing Translations:**

Narratives are generated via the `trend-narrative` package. To test:
1. Set language to French or Portuguese in the UI
2. Verify narrative text renders correctly with proper:
   - Verb agreement (singular/plural)
   - Decimal separators (comma in French and Portuguese: 0,52; period in English: 0.52)
   - Article contractions (for example, French `du/de/des`, Portuguese `do/da/dos/das`)
   - Genitive constructions

### Narrative Generation

This app generates automated narratives about government spending using the `trend-narrative` package. English and French are generated directly by that package. For Portuguese, the app first tries `trend-narrative` with `pt`, then `ptbr`; only if those language codes are unsupported does it fall back to English for the package-generated narrative fragment while the surrounding dashboard text remains Portuguese.

#### Segment Narratives

Analyze spending trends over time (e.g., "between 2015 and 2020, real expenditure increased 50%")

**Supported Metrics:**
- Real expenditure
- Per capita spending
- Total real expenditure

#### Relationship Narratives

Analyze correlations between spending and outcomes (e.g., "spending and health outcomes show a strong positive pattern")

**Supported Outcomes:**
- **Health:** UHC coverage index
- **Education:** School attendance, Learning poverty rate

#### Example French Narrative Output

```
Après prise en compte de l'inflation, entre 2015 et 2020, les dépenses 
réelles ont augmenté de 50,00 (+50,00 %), maintenant une trajectoire constante.
```

Narratives respect language-specific formatting where package support is available. Portuguese dashboard templates and app-generated numbers use comma decimals and Portuguese article/preposition helpers; package-generated trend fragments use Portuguese output if `trend-narrative` accepts `pt` or `ptbr`, otherwise English fallback.

## PostgreSQL instead of Databricks

```bash
DB_BACKEND=postgres
POSTGRES_DSN=postgresql://user:password@host:5432/prd_mega
```

The queries are unchanged: the database must be named `prd_mega` and hold the
`boost` and `indicator` schemas with the same tables as Databricks. With
`AUTH_ENABLED=1` it also needs the `sboost4` schema, whose
`dashboard_user_credentials` table holds the login credentials (see
`QueryService.get_user_credentials`).

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
