"""
InsightIQ — Sales Analytics
=============================
SQL-backed sales metrics. Every function returns either a single number or a
pandas DataFrame, ready to feed straight into Streamlit tables/charts or the
Power BI data model.

Run this file directly for a quick smoke test of every function against the
live database:
    python analytics/sales.py
"""

import pandas as pd
from sqlalchemy import text
from db import get_engine


def total_revenue(start=None, end=None) -> float:
    engine = get_engine()
    where = _date_where(start, end)
    query = f"SELECT COALESCE(SUM(revenue), 0) FROM orders {where}"
    with engine.begin() as conn:
        return float(conn.execute(text(query)).scalar())


def total_profit(start=None, end=None) -> float:
    engine = get_engine()
    where = _date_where(start, end)
    query = f"SELECT COALESCE(SUM(profit), 0) FROM orders {where}"
    with engine.begin() as conn:
        return float(conn.execute(text(query)).scalar())


def profit_margin(start=None, end=None) -> float:
    """Overall profit margin as a percentage of revenue."""
    rev = total_revenue(start, end)
    profit = total_profit(start, end)
    return round(100 * profit / rev, 2) if rev else 0.0


def average_order_value(start=None, end=None) -> float:
    engine = get_engine()
    where = _date_where(start, end)
    query = f"SELECT COALESCE(AVG(revenue), 0) FROM orders {where}"
    with engine.begin() as conn:
        return round(float(conn.execute(text(query)).scalar()), 2)


def monthly_revenue() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT DATE_TRUNC('month', order_date)::date AS month,
               SUM(revenue) AS revenue,
               SUM(profit)  AS profit,
               COUNT(*)     AS orders
        FROM orders
        GROUP BY 1
        ORDER BY 1
    """
    return pd.read_sql(text(query), engine)


def quarterly_revenue() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT DATE_TRUNC('quarter', order_date)::date AS quarter,
               SUM(revenue) AS revenue,
               SUM(profit)  AS profit,
               COUNT(*)     AS orders
        FROM orders
        GROUP BY 1
        ORDER BY 1
    """
    return pd.read_sql(text(query), engine)


def revenue_growth_mom() -> pd.DataFrame:
    """Month-over-month revenue growth %, computed from monthly_revenue()."""
    df = monthly_revenue()
    df["revenue_growth_pct"] = (df["revenue"].pct_change() * 100).round(2)
    return df[["month", "revenue", "revenue_growth_pct"]]


def revenue_by_region() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT region,
               SUM(revenue) AS revenue,
               SUM(profit)  AS profit,
               COUNT(*)     AS orders
        FROM orders
        GROUP BY region
        ORDER BY revenue DESC
    """
    return pd.read_sql(text(query), engine)


def revenue_by_product(top_n: int = 10) -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT p.product_name, p.category,
               SUM(o.revenue) AS revenue,
               SUM(o.profit)  AS profit,
               COUNT(*)       AS orders
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        ORDER BY revenue DESC
        LIMIT :n
    """
    return pd.read_sql(text(query), engine, params={"n": top_n})


def discount_analysis() -> pd.DataFrame:
    """Revenue and order volume by discount bracket — useful for Power BI's discount-analysis chart."""
    engine = get_engine()
    query = """
        SELECT
            CASE
                WHEN discount = 0 THEN 'No discount'
                WHEN discount <= 0.10 THEN '1-10%'
                WHEN discount <= 0.20 THEN '11-20%'
                ELSE '21%+'
            END AS discount_bracket,
            COUNT(*) AS orders,
            SUM(revenue) AS revenue,
            AVG(profit)  AS avg_profit_per_order
        FROM orders
        GROUP BY 1
        ORDER BY MIN(discount)
    """
    return pd.read_sql(text(query), engine)


def _date_where(start, end) -> str:
    if not start and not end:
        return ""
    if start and end:
        return f"WHERE order_date BETWEEN '{start}' AND '{end}'"
    if start:
        return f"WHERE order_date >= '{start}'"
    return f"WHERE order_date <= '{end}'"


if __name__ == "__main__":
    print("Total revenue      :", f"{total_revenue():,.2f}")
    print("Total profit        :", f"{total_profit():,.2f}")
    print("Profit margin       :", f"{profit_margin()}%")
    print("Average order value :", f"{average_order_value():,.2f}")
    print("\nMonthly revenue (last 6 months):")
    print(monthly_revenue().tail(6).to_string(index=False))
    print("\nRevenue growth MoM (last 6 months):")
    print(revenue_growth_mom().tail(6).to_string(index=False))
    print("\nRevenue by region:")
    print(revenue_by_region().to_string(index=False))
    print("\nTop 5 products by revenue:")
    print(revenue_by_product(5).to_string(index=False))
    print("\nDiscount analysis:")
    print(discount_analysis().to_string(index=False))
