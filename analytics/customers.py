"""
InsightIQ — Customer Analytics
=================================
Run this file directly for a quick smoke test of every function:
    python analytics/customers.py
"""

import pandas as pd
from sqlalchemy import text
from db import get_engine


def total_customers() -> int:
    engine = get_engine()
    with engine.begin() as conn:
        return int(conn.execute(text("SELECT COUNT(*) FROM customers")).scalar())


def new_customers_by_month() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT DATE_TRUNC('month', signup_date)::date AS month,
               COUNT(*) AS new_customers
        FROM customers
        GROUP BY 1
        ORDER BY 1
    """
    return pd.read_sql(text(query), engine)


def returning_customers() -> int:
    """Customers with more than one order."""
    engine = get_engine()
    query = """
        SELECT COUNT(*) FROM (
            SELECT customer_id FROM orders
            GROUP BY customer_id HAVING COUNT(*) > 1
        ) t
    """
    with engine.begin() as conn:
        return int(conn.execute(text(query)).scalar())


def retention_rate() -> float:
    """% of customers who placed more than one order, of all customers who ordered at least once."""
    engine = get_engine()
    query = """
        SELECT
            COUNT(*) FILTER (WHERE order_count > 1) AS returning,
            COUNT(*) AS total_ordering_customers
        FROM (
            SELECT customer_id, COUNT(*) AS order_count
            FROM orders GROUP BY customer_id
        ) t
    """
    with engine.begin() as conn:
        row = conn.execute(text(query)).fetchone()
    returning, total = row[0], row[1]
    return round(100 * returning / total, 2) if total else 0.0


def churn_rate(inactivity_days: int = 90) -> float:
    """
    % of customers whose most recent order is more than `inactivity_days`
    before the latest order date in the whole dataset (i.e. relative to
    "now" = the most recent activity in the data, not the calendar date —
    keeps this reproducible regardless of when you run it).
    """
    engine = get_engine()
    query = """
        WITH last_order AS (
            SELECT customer_id, MAX(order_date) AS last_order_date
            FROM orders GROUP BY customer_id
        ),
        reference AS (
            SELECT MAX(order_date) AS max_date FROM orders
        )
        SELECT
            COUNT(*) FILTER (WHERE last_order_date < reference.max_date - (:days || ' days')::interval) AS churned,
            COUNT(*) AS total
        FROM last_order, reference
    """
    with engine.begin() as conn:
        row = conn.execute(text(query), {"days": inactivity_days}).fetchone()
    churned, total = row[0], row[1]
    return round(100 * churned / total, 2) if total else 0.0


def customer_lifetime_value() -> pd.DataFrame:
    """Total revenue and profit generated per customer, sorted highest first."""
    engine = get_engine()
    query = """
        SELECT c.customer_id, c.name, c.region,
               COALESCE(SUM(o.revenue), 0) AS lifetime_revenue,
               COALESCE(SUM(o.profit), 0)  AS lifetime_profit,
               COUNT(o.order_id) AS total_orders
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.name, c.region
        ORDER BY lifetime_revenue DESC
    """
    return pd.read_sql(text(query), engine)


def average_purchase_frequency() -> float:
    """Average number of orders per customer, among customers who ordered at least once."""
    engine = get_engine()
    query = """
        SELECT AVG(order_count) FROM (
            SELECT customer_id, COUNT(*) AS order_count
            FROM orders GROUP BY customer_id
        ) t
    """
    with engine.begin() as conn:
        result = conn.execute(text(query)).scalar()
    return round(float(result), 2) if result else 0.0


if __name__ == "__main__":
    print("Total customers          :", total_customers())
    print("Returning customers      :", returning_customers())
    print("Retention rate           :", f"{retention_rate()}%")
    print("Churn rate (90-day)      :", f"{churn_rate(90)}%")
    print("Avg purchase frequency   :", average_purchase_frequency())
    print("\nNew customers by month (last 6):")
    print(new_customers_by_month().tail(6).to_string(index=False))
    print("\nTop 5 customers by lifetime value:")
    print(customer_lifetime_value().head(5).to_string(index=False))
