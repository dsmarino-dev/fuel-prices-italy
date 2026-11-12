# Project notes

## 2026-11-12 – EIA API first test
- Brent daily spot series: `RBRTE`, route `petroleum/pri/spt`, unit $/BBL.
- Publication lag: on Nov 12 the latest available value was Nov 3 (9 days).
  EIA publishes daily values in weekly batches -> ingestion must always
  re-request the last 10-15 days and upsert (MERGE), never fetch "yesterday" only.
- No values on weekends/holidays (e.g. Oct 31 - Nov 1) -> forward-fill in silver
  before joining with daily pump prices.
