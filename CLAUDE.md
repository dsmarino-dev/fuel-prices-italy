# CLAUDE.md

Context for Claude Code working in this repository. Keep it up to date when
decisions change. Day-to-day findings and the improvements backlog live in
`NOTES.md`.

## Working agreement (read first)

This is a **learning and portfolio project**. The owner, Davide, is moving from
Business Intelligence Engineering (strong SQL, data modeling, AWS) to Data
Engineering, and must be able to explain every line in a job interview.

- **Coach, don't autopilot.** Explain the *why* before writing code. Prefer small,
  reviewable steps over large changes.
- **Davide runs the commands** (tests, downloads, git). Suggest them; don't chain
  many actions without checking in.
- **Ask before** adding dependencies, changing the architecture, or touching
  more than a few files at once.
- **Conversation in Italian, everything in the repo in English**: code, comments,
  docstrings, table/column names, commit messages, README, NOTES.
- When something is a non-obvious data finding or design decision, suggest an
  entry for `NOTES.md` (it becomes the README "Challenges" section).

## Project goal

A daily data pipeline on Italian fuel prices that:

1. collects the daily price snapshot of every Italian fuel station (MIMIT open data);
2. compares pump prices with the cost of crude oil (Brent via EIA, EUR/USD via ECB);
3. measures how reliable the published prices are.

Final analyses (gold layer):

- **Motorway and territory**: motorway premium vs ordinary roads (daily medians,
  also by region); deviation of each province and brand from the national median
  on the same day.
- **Data reliability**: age of each price (extraction date minus reported date) in
  freshness bands, plus anomaly rules (out of range, far from provincial median,
  typos, self-service pricier than full service, isolated spikes, orphan records)
  → reliability index by province and brand. A "suspicious" price is not
  necessarily wrong: say so.
- **Rockets and feathers**: pump price minus crude cost and taxes = supply-chain
  margin over time; how many days pump prices take to follow Brent up vs down.

## Data sources

| Source | Type | Notes |
| --- | --- | --- |
| MIMIT stations | CSV, `https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv` | UTF-8, ~24k rows |
| MIMIT prices | CSV, `https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv` | ASCII, ~93k rows/day |
| EIA Brent spot | REST API, route `petroleum/pri/spt`, series `RBRTE`, key in `.env` as `EIA_API_KEY` | $/BBL, daily values published weekly |
| ECB EUR/USD | SDMX API, `https://data-api.ecb.europa.eu/service`, flow `EXR`, key `D.USD.EUR.SP00.A` | No key; business days only |

MIMIT file format (verified 2026-11):

- Line 1 is metadata: `Estrazione del YYYY-MM-DD`. The header is on line 2.
- The extraction date is the **logical date** of the data: snapshot of prices in
  force at ~08:00 that day. Files are published with a delay of 1+ day.
  Never shift it by a day.
- Delimiter `|` since 2026-02-10; quarterly archive files use a different one.
- `dtComu` format is `dd/MM/yyyy HH:mm:ss` → always parse with an explicit format.
- Text fields can have trailing spaces → trim in staging.
- Some prices are years old (oldest seen: 2013) → input for the reliability index.

Other source quirks:

- EIA: always re-request the last 10–15 days and upsert (late-arriving data).
- ECB and EIA have no weekend/holiday values → forward-fill in silver before
  joining with daily pump prices.
- 1 barrel ≈ 158.987 litres.

## Architecture

Medallion layers, same design locally and on Databricks:

- **bronze**: raw data as received, all text, plus metadata columns
  (`source_file`, `extraction_date`, `loaded_at`). Written by Python loaders.
- **silver**: cleaned and conformed (English names, types, dedup, anomaly flags,
  SCD2 history of stations). dbt `staging` + `intermediate` models.
- **gold**: facts, dimensions and the three analyses. dbt `marts` models.

Local engine: **DuckDB** (`fuel_prices.duckdb`, git-ignored). Only one process can
write to the DuckDB file at a time: close the loader before running dbt.
Week 3 moves the same models to Databricks (Unity Catalog schemas
`bronze`/`silver`/`gold`, Auto Loader, Delta, Lakeflow).

## Naming conventions

- dbt model prefixes: `stg_` (staging), `int_` (intermediate), `fct_` (facts),
  `dim_` (dimensions). Planned: `stg_prices`, `stg_stations`, `fct_daily_prices`,
  `fct_daily_crude_cost`, `dim_stations`, `dim_fuel_types`, `dim_date`.
- Column mapping from MIMIT:

| MIMIT | English | Type |
| --- | --- | --- |
| `idImpianto` | `station_id` | integer |
| `Gestore` | `operator_name` | text |
| `Bandiera` | `brand` | text |
| `Tipo Impianto` | `station_type` | text (Stradale / Autostradale) |
| `Nome Impianto` | `station_name` | text |
| `Indirizzo` | `address` | text |
| `Comune` | `municipality` | text |
| `Provincia` | `province_code` | text |
| `Latitudine` / `Longitudine` | `latitude` / `longitude` | decimal |
| `descCarburante` | `fuel_type` | text |
| `prezzo` | `price_eur_per_liter` | decimal |
| `isSelf` | `is_self_service` | boolean |
| `dtComu` | `reported_at` | timestamp |

- Raw files: `data/raw/<dataset>_<extraction-date>.csv`
  (e.g. `prices_2026-11-15.csv`).

## Repository layout

```
src/fuel_prices_italy/
  ingestion/mimit.py     MIMIT downloader (CLI: download-mimit)
tests/                   pytest, no network calls (use sample bytes / saved responses)
data/                    git-ignored: raw files, DuckDB file, logs
NOTES.md                 findings, decisions, backlog
```

## Stack and commands

- Python 3.12 managed by **uv** (`pyproject.toml` + `uv.lock`); never use the
  system Python or conda for this project.
- `uv sync` – install/align the environment
- `uv run pytest -v` – tests
- `uv run ruff check . && uv run ruff format .` – lint and format
- `uv run download-mimit` – download today's MIMIT snapshot (idempotent; `--force` to overwrite)
- Type checking: Pyright in `standard` mode (configured in `pyproject.toml`).

## Rules

- **Secrets** live only in `.env` (git-ignored) locally, Databricks secrets on
  Databricks, Airflow connections/variables in Airflow. Never print, log or
  commit them.
- **Idempotency**: every ingestion step must be safe to re-run (skip or upsert,
  never duplicate).
- **Tests** never call the network.
- Write files atomically (temp file + rename).
- Keep `data/` out of git; the code that downloads data is versioned, not the data.

## Learning plan (6 weeks, current position: week 1)

1. dbt on DuckDB: staging, star schema, tests, incremental models, snapshots.
2. Python ingestion (MIMIT, EIA, ECB clients) + PySpark (needs Java) on history.
3. Databricks Free Edition: Unity Catalog, Auto Loader, MERGE, dbt-databricks, Lakeflow.
4. Airflow 3 (Astro CLI): three DAGs with different cadences, Docker, GitHub Actions CI.
5. The three analyses, Databricks SQL dashboard, optimization, final README.
6. Databricks Data Engineer Associate exam, CV, interview prep.
