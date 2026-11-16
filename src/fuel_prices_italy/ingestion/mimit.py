"""Download the daily MIMIT fuel price files.

MIMIT (Italian Ministry of Enterprises and Made in Italy) publishes two CSV files
every morning:

- the registry of active stations (anagrafica degli impianti attivi)
- the prices reported by each station (prezzo alle 8 di mattina)

The first line of each file is metadata, e.g. "Estrazione del 2026-11-11".
That date (not the download date) is the logical date of the data, so it is
used in the saved file name: ``stations_2026-11-11.csv``, ``prices_2026-11-11.csv``.

Usage:
    uv run download-mimit                 # save into data/raw
    uv run download-mimit --dest other/   # custom folder
    uv run download-mimit --force         # overwrite files that already exist
"""

from __future__ import annotations

import argparse
import logging
import re
import time
from datetime import date
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

MIMIT_URLS: dict[str, str] = {
    "stations": "https://www.mimit.gov.it/images/exportCSV/anagrafica_impianti_attivi.csv",
    "prices": "https://www.mimit.gov.it/images/exportCSV/prezzo_alle_8.csv",
}

DEFAULT_DEST = Path("data/raw")
EXTRACTION_DATE_PATTERN = re.compile(rb"Estrazione del (\d{4}-\d{2}-\d{2})")
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 60


def parse_extraction_date(content: bytes) -> date:
    """Return the extraction date found on the first line of a MIMIT file.

    Raises ValueError if the first line does not contain the expected metadata,
    which usually means the file format has changed.
    """
    first_line = content.split(b"\n", 1)[0]
    match = EXTRACTION_DATE_PATTERN.search(first_line)
    if match is None:
        raise ValueError(
            f"Extraction date not found on the first line: {first_line[:80]!r}"
        )
    return date.fromisoformat(match.group(1).decode("ascii"))


def download(url: str) -> bytes:
    """Download a file, retrying with a growing pause on network errors."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.content
        except requests.RequestException as error:
            if attempt == MAX_ATTEMPTS:
                raise
            wait = 5 * attempt
            logger.warning(
                "Attempt %d/%d failed for %s (%s). Retrying in %ds.",
                attempt,
                MAX_ATTEMPTS,
                url,
                error,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError("unreachable")  # keeps type checkers happy


def save_file(content: bytes, dest_dir: Path, dataset: str, force: bool) -> Path:
    """Save a downloaded file as <dataset>_<extraction-date>.csv.

    The function is idempotent: if the file for that date already exists it is
    left untouched (unless force=True), so running the script twice is safe.
    """
    extraction_date = parse_extraction_date(content)
    target = dest_dir / f"{dataset}_{extraction_date.isoformat()}.csv"

    if target.exists() and not force:
        logger.info("Skipped %s: already exists (use --force to overwrite).", target)
        return target

    dest_dir.mkdir(parents=True, exist_ok=True)
    # Write to a temporary file first, then rename: a crash mid-write never
    # leaves a half-written CSV with a valid-looking name.
    tmp = target.with_suffix(".csv.tmp")
    tmp.write_bytes(content)
    tmp.replace(target)
    logger.info("Saved %s (%.1f MB).", target, len(content) / 1_000_000)
    return target


def run(dest_dir: Path = DEFAULT_DEST, force: bool = False) -> list[Path]:
    """Download all MIMIT datasets and return the paths of the saved files."""
    saved = []
    for dataset, url in MIMIT_URLS.items():
        logger.info("Downloading %s from %s", dataset, url)
        content = download(url)
        saved.append(save_file(content, dest_dir, dataset, force))
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download the daily MIMIT fuel price files."
    )
    parser.add_argument(
        "--dest", type=Path, default=DEFAULT_DEST, help="destination folder"
    )
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    run(args.dest, args.force)


if __name__ == "__main__":
    main()
