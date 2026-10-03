"""
Tests for data_pipeline/clean.py's detection logic, using small
hand-built DataFrames rather than the full synthetic dataset — these
are meant to isolate and prove each check works on both the normal
case and the edge case, independent of what Day 1's generator produces.
"""

from datetime import date
import pandas as pd
import pytest
import clean


# ---------------------------------------------------------------------------
# flag_out_of_range
# ---------------------------------------------------------------------------
def test_flag_out_of_range_catches_low_and_high():
    df = pd.DataFrame({"age": [10, 25, 150, 40]})
    mask = clean.flag_out_of_range(df, "age", lo=12, hi=100)
    assert list(mask) == [True, False, True, False]


def test_flag_out_of_range_no_violations():
    df = pd.DataFrame({"quantity": [1, 2, 3, 4]})
    mask = clean.flag_out_of_range(df, "quantity", lo=1)
    assert mask.sum() == 0


# ---------------------------------------------------------------------------
# flag_invalid_dates
# ---------------------------------------------------------------------------
def test_flag_invalid_dates_catches_future_and_unparseable():
    df = pd.DataFrame({"signup_date": ["2024-01-01", "2099-01-01", "not-a-date", "2023-06-15"]})
    mask = clean.flag_invalid_dates(df, "signup_date", date(2000, 1, 1), date(2026, 1, 1))
    assert list(mask) == [False, True, True, False]


# ---------------------------------------------------------------------------
# flag_invalid_category
# ---------------------------------------------------------------------------
def test_flag_invalid_category():
    df = pd.DataFrame({"region": ["North", "South", "Atlantis", "East"]})
    mask = clean.flag_invalid_category(df, "region", {"North", "South", "East", "West", "Central"})
    assert list(mask) == [False, False, True, False]


# ---------------------------------------------------------------------------
# detect_outliers_iqr
# ---------------------------------------------------------------------------
def test_detect_outliers_iqr_flags_extreme_value():
    df = pd.DataFrame({"price": [10, 11, 12, 9, 10, 11, 10000]})
    mask = clean.detect_outliers_iqr(df, "price")
    assert mask.iloc[-1] == True  # noqa: E712 — the 10000 should be flagged
    assert mask.iloc[:-1].sum() == 0  # the rest should not be


# ---------------------------------------------------------------------------
# quality_score
# ---------------------------------------------------------------------------
def test_quality_score_perfect():
    assert clean.quality_score(total=100, invalid=0) == 100.0


def test_quality_score_half_invalid():
    assert clean.quality_score(total=100, invalid=50) == 50.0


def test_quality_score_zero_rows():
    assert clean.quality_score(total=0, invalid=0) == 0.0


# ---------------------------------------------------------------------------
# Full clean_customers() pipeline, on a deliberately dirty small table —
# mirrors the manual dirty-data test run during Day 2 development, now
# codified as an automated regression test.
# ---------------------------------------------------------------------------
def test_clean_customers_end_to_end():
    dirty = pd.DataFrame({
        "customer_id": [1, 2, 3, 3],          # 3 is a duplicate key
        "name": [" Alice ", "Bob", "Carol", "Carol"],
        "age": [30, 200, 25, 25],              # row 2 (age=200) is impossible
        "city": ["Chennai", "Delhi", "Pune", "Pune"],
        "region": ["South", "North", "Atlantis", "Atlantis"],  # row 3 invalid region
        "signup_date": ["2024-01-01", "2024-02-01", "2099-01-01", "2099-01-01"],  # row 3 future date
        "customer_segment": ["", "", "", ""],
    })

    cleaned, rejected, report = clean.clean_customers(dirty.copy())

    # Row 1 (Alice) is the only fully clean row
    assert report["total_rows"] == 4
    assert report["valid_rows"] == 1
    assert report["invalid_rows"] == 3
    assert report["quality_score_pct"] == 25.0
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["name"] == "Alice"  # whitespace was trimmed, logged, not silently hidden
