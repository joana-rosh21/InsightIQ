"""
InsightIQ — Operations Analytics
===================================
Run this file directly for a quick smoke test of every function:
    python analytics/operations.py
"""

import pandas as pd
from sqlalchemy import text
from db import get_engine


def average_delivery_time() -> float:
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text("SELECT AVG(delivery_days) FROM orders")).scalar()
    return round(float(result), 2) if result else 0.0


def cancellation_rate() -> float:
    engine = get_engine()
    query = """
        SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE return_status = 'Cancelled') / COUNT(*), 2)
        FROM orders
    """
    with engine.begin() as conn:
        result = conn.execute(text(query)).scalar()
    return float(result) if result else 0.0


def return_rate() -> float:
    engine = get_engine()
    query = """
        SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE return_status = 'Returned') / COUNT(*), 2)
        FROM orders
    """
    with engine.begin() as conn:
        result = conn.execute(text(query)).scalar()
    return float(result) if result else 0.0


def regional_operational_performance() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT region,
               ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
               ROUND(100.0 * COUNT(*) FILTER (WHERE return_status = 'Returned') / COUNT(*), 2) AS return_rate_pct,
               ROUND(100.0 * COUNT(*) FILTER (WHERE return_status = 'Cancelled') / COUNT(*), 2) AS cancellation_rate_pct,
               COUNT(*) AS total_orders
        FROM orders
        GROUP BY region
        ORDER BY avg_delivery_days ASC
    """
    return pd.read_sql(text(query), engine)


def delivery_time_by_category() -> pd.DataFrame:
    """Delivery performance broken down by product category — helps separate
    'this region is slow' from 'this category is slow to fulfill everywhere'."""
    engine = get_engine()
    query = """
        SELECT p.category,
               ROUND(AVG(o.delivery_days), 2) AS avg_delivery_days,
               COUNT(*) AS orders
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.category
        ORDER BY avg_delivery_days DESC
    """
    return pd.read_sql(text(query), engine)


if __name__ == "__main__":
    print("Average delivery time :", f"{average_delivery_time()} days")
    print("Cancellation rate     :", f"{cancellation_rate()}%")
    print("Return rate           :", f"{return_rate()}%")
    print("\nRegional operational performance:")
    print(regional_operational_performance().to_string(index=False))
    print("\nDelivery time by category:")
    print(delivery_time_by_category().to_string(index=False))
