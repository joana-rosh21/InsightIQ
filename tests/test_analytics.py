"""
Integration tests for the analytics/ layer — these run real SQL against
the live PostgreSQL database (same one data_pipeline/load_to_postgres.py
loads into), so they double as a "is my database set up correctly" check.
If these fail, check your .env / DATABASE_URL and that Day 1-2's pipeline
has actually been run.
"""

import pytest
import sales
import customers
import products
import operations


def test_total_revenue_is_positive():
    assert sales.total_revenue() > 0


def test_total_revenue_matches_profit_plus_cost_relationship():
    """Sanity check: profit should always be less than revenue (cost > 0
    on every product per the schema's CHECK constraint)."""
    revenue = sales.total_revenue()
    profit = sales.total_profit()
    assert 0 < profit < revenue


def test_profit_margin_is_a_reasonable_percentage():
    margin = sales.profit_margin()
    assert 0 <= margin <= 100


def test_monthly_revenue_returns_nonempty_dataframe():
    df = sales.monthly_revenue()
    assert len(df) > 0
    assert set(["month", "revenue", "profit", "orders"]).issubset(df.columns)


def test_revenue_by_region_covers_all_five_regions():
    df = sales.revenue_by_region()
    regions = set(df["region"])
    assert regions == {"North", "South", "East", "West", "Central"}


def test_total_customers_matches_schema_expectation():
    # Matches the Day 1 generator's N_CUSTOMERS constant — update this
    # test if you regenerate the dataset at a different scale.
    assert customers.total_customers() == 5000


def test_retention_rate_is_a_percentage():
    rate = customers.retention_rate()
    assert 0 <= rate <= 100


def test_churn_rate_is_a_percentage():
    rate = customers.churn_rate(90)
    assert 0 <= rate <= 100


def test_category_performance_nonempty():
    df = products.category_performance()
    assert len(df) > 0
    assert "return_rate_pct" in df.columns


def test_average_delivery_time_is_positive():
    assert operations.average_delivery_time() > 0


def test_return_rate_is_a_percentage():
    rate = operations.return_rate()
    assert 0 <= rate <= 100
