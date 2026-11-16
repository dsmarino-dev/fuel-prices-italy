# Project notes

## 2026-11-12 – EIA API first test
- Brent daily spot series: `RBRTE`, route `petroleum/pri/spt`, unit $/BBL.
- Publication lag: on Nov 12 the latest available value was Nov 3 (9 days).
  EIA publishes daily values in weekly batches -> ingestion must always
  re-request the last 10-15 days and upsert (MERGE), never fetch "yesterday" only.
- No values on weekends/holidays (e.g. Oct 31 - Nov 1) -> forward-fill in silver
  before joining with daily pump prices.

## 2026-11-12 – MIMIT files first inspection
- Source URLs: images/exportCSV/anagrafica_impianti_attivi.csv and prezzo_alle_8.csv
- Line 1 is metadata ("Estrazione del YYYY-MM-DD"), header is on line 2.
  -> skip line 1 but keep its date as the logical `extraction_date`
     (file downloaded on Nov 12 contains data extracted on Nov 11).
- Delimiter is `|` (format changed on 2026-02-10; archive files differ).
- Stations file is UTF-8, prices file is ASCII.
- ~23.9k stations and ~92.7k price rows per day.
- `dtComu` uses dd/MM/yyyy HH:mm:ss -> parse with explicit format.
- Trailing spaces in text fields (e.g. address) -> trim in staging.
- Prices can be stale: example row reported on Nov 9 appears in Nov 11 extraction.

## 2026-11-16 – Meaning of the extraction date
- "Estrazione del 2026-11-11" = snapshot of prices in force at 08:00 on Nov 11:
  latest `dtComu` in the file is 2026-11-11 08:06; nothing after that.
- The file is published with a delay (on Nov 16 at 17:30 the latest snapshot was Nov 15).
  This is publication lag, not a date error: the extraction date is the correct
  logical date -> no +1 day shift.
- Downloader is idempotent, so it can run several times a day until a new
  extraction date appears (Airflow sensor in week 4).
- Oldest price in the Nov 11 snapshot was reported on 2013-05-23:
  some "active" stations have never updated their prices -> reliability index.

## Backlog – improvements to do later
- [ ] **Schedule the MIMIT download on the Mac (launchd)** until Airflow takes over
      in week 4: run `uv run download-mimit` twice a day (e.g. 10:00 and 20:00),
      log to `data/logs/`. launchd runs missed jobs on wake, unlike cron.
      Goal: accumulate daily snapshots now, so week-5 analyses have more history.
- [ ] **Avoid full downloads when nothing changed** (week 2): the downloader fetches
      the whole file (~3-4 MB each) before it can read the extraction date and skip.
      Options: HTTP `Range` request for the first bytes, or `Last-Modified`/`ETag` headers.
- [ ] **Backfill Nov 12-14 from the MIMIT quarterly archive** (daily files were not
      downloaded on those days); archive files use a different delimiter.
