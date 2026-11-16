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
