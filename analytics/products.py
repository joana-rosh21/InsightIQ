"""
InsightIQ — Product Analytics
================================
Run this file directly for a quick smoke test of every function:
    python analytics/products.py
"""

import pandas as pd
from sqlalchemy import text
from db import get_engine


def top_products(n: int = 10, by: str = "revenue") -> pd.DataFrame:
    col = {"revenue": "SUM(o.revenue)", "profit": "SUM(o.profit)", "orders": "COUNT(*)"}.get(by, "SUM(o.revenue)")
    engine = get_engine()
    query = f"""
        SELECT p.product_name, p.category,
               SUM(o.revenue) AS revenue, SUM(o.profit) AS profit, COUNT(*) AS orders
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        ORDER BY {col} DESC
        LIMIT :n
    """
    return pd.read_sql(text(query), engine, params={"n": n})


def bottom_products(n: int = 10) -> pd.DataFrame:
    """Lowest-revenue products that still have at least one order (products with zero orders
    are a data-catalog issue, not a sales-performance one, so they're excluded here)."""
    engine = get_engine()
    query = """
        SELECT p.product_name, p.category,
               SUM(o.revenue) AS revenue, SUM(o.profit) AS profit, COUNT(*) AS orders
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        ORDER BY revenue ASC
        LIMIT :n
    """
    return pd.read_sql(text(query), engine, params={"n": n})


def most_profitable_products(n: int = 10) -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT p.product_name, p.category,
               SUM(o.profit) AS total_profit,
               ROUND(100.0 * SUM(o.profit) / NULLIF(SUM(o.revenue), 0), 2) AS margin_pct
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        ORDER BY total_profit DESC
        LIMIT :n
    """
    return pd.read_sql(text(query), engine, params={"n": n})


def low_margin_products(n: int = 10) -> pd.DataFrame:
    """Products with the thinnest profit margin, among products with a meaningful order volume
    (at least 5 orders) so a single fluky order doesn't dominate the ranking."""
    engine = get_engine()
    query = """
        SELECT p.product_name, p.category,
               SUM(o.revenue) AS revenue,
               ROUND(100.0 * SUM(o.profit) / NULLIF(SUM(o.revenue), 0), 2) AS margin_pct,
               COUNT(*) AS orders
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        HAVING COUNT(*) >= 5
        ORDER BY margin_pct ASC
        LIMIT :n
    """
    return pd.read_sql(text(query), engine, params={"n": n})


def return_rate_by_product(n: int = 10) -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT p.product_name, p.category,
               COUNT(*) AS total_orders,
               COUNT(*) FILTER (WHERE o.return_status = 'Returned') AS returned_orders,
               ROUND(100.0 * COUNT(*) FILTER (WHERE o.return_status = 'Returned') / COUNT(*), 2) AS return_rate_pct
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        HAVING COUNT(*) >= 5
        ORDER BY return_rate_pct DESC
        LIMIT :n
    """
    return pd.read_sql(text(query), engine, params={"n": n})


def category_performance() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT p.category,
               SUM(o.revenue) AS revenue,
               SUM(o.profit)  AS profit,
               COUNT(*)       AS orders,
               ROUND(100.0 * COUNT(*) FILTER (WHERE o.return_status = 'Returned') / COUNT(*), 2) AS return_rate_pct
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.category
        ORDER BY revenue DESC
    """
    return pd.read_sql(text(query), engine)


if __name__ == "__main__":
    print("Top 5 products by revenue:")
    print(top_products(5).to_string(index=False))
    print("\nBottom 5 products by revenue:")
    print(bottom_products(5).to_string(index=False))
    print("\nTop 5 most profitable products:")
    print(most_profitable_products(5).to_string(index=False))
    print("\nTop 5 lowest-margin products (min 5 orders):")
    print(low_margin_products(5).to_string(index=False))
    print("\nTop 5 highest-return-rate products (min 5 orders):")
    print(return_rate_by_product(5).to_string(index=False))
    print("\nCategory performance:")
    print(category_performance().to_string(index=False))
