"""Tests for the MIMIT downloader (no network calls)."""

from datetime import date
from pathlib import Path

import pytest

from fuel_prices_italy.ingestion.mimit import parse_extraction_date, save_file

SAMPLE_PRICES = (
    b"Estrazione del 2026-11-11\n"
    b"idImpianto|descCarburante|prezzo|isSelf|dtComu\n"
    b"3464|Benzina|2.349|0|09/11/2026 20:00:07\n"
)


def test_parse_extraction_date() -> None:
    assert parse_extraction_date(SAMPLE_PRICES) == date(2026, 11, 11)


def test_parse_extraction_date_fails_on_unexpected_format() -> None:
    with pytest.raises(ValueError):
        parse_extraction_date(b"idImpianto|descCarburante|prezzo\n")


def test_save_file_uses_extraction_date(tmp_path: Path) -> None:
    target = save_file(SAMPLE_PRICES, tmp_path, "prices", force=False)
    assert target.name == "prices_2026-11-11.csv"
    assert target.read_bytes() == SAMPLE_PRICES


def test_save_file_is_idempotent(tmp_path: Path) -> None:
    first = save_file(SAMPLE_PRICES, tmp_path, "prices", force=False)
    first.write_bytes(b"edited")  # simulate an existing file
    second = save_file(SAMPLE_PRICES, tmp_path, "prices", force=False)
    assert second.read_bytes() == b"edited"  # not overwritten without --force


def test_save_file_force_overwrites(tmp_path: Path) -> None:
    target = save_file(SAMPLE_PRICES, tmp_path, "prices", force=False)
    target.write_bytes(b"edited")
    save_file(SAMPLE_PRICES, tmp_path, "prices", force=True)
    assert target.read_bytes() == SAMPLE_PRICES
