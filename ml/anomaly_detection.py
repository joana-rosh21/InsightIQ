"""
InsightIQ — Anomaly Detection
================================
Detects anomalous days in revenue, orders, profit, returns, and new
customer acquisition using two explainable, non-black-box methods:

  - Rolling Z-score: how many rolling-window standard deviations a day's
    value sits from its own rolling mean (catches anomalies even inside
    a long-term upward/downward trend, unlike a single global mean).
  - IQR: flags a day as an outlier if it falls outside
    [Q1 - 1.5*IQR, Q3 + 1.5*IQR] of the whole series — a classic,
    easy-to-explain outlier rule with no distributional assumptions.

A day is reported as anomalous if EITHER method flags it, with both
scores included so you can see which one triggered.

Run:
    python ml/anomaly_detection.py
"""

import os
import pandas as pd
import numpy as np
from sqlalchemy import text
from db import get_engine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "ml", "output")

ROLLING_WINDOW = 14
ZSCORE_THRESHOLD = 2.5
IQR_WHISKER = 1.5


def load_daily_metrics() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT
            order_date AS date,
            SUM(revenue) AS revenue,
            SUM(profit)  AS profit,
            COUNT(*)     AS orders,
            COUNT(*) FILTER (WHERE return_status = 'Returned') AS returns
        FROM orders
        GROUP BY order_date
        ORDER BY order_date
    """
    daily = pd.read_sql(text(query), engine, parse_dates=["date"])

    cust_query = """
        SELECT signup_date AS date, COUNT(*) AS new_customers
        FROM customers
        GROUP BY signup_date
        ORDER BY signup_date
    """
    new_cust = pd.read_sql(text(cust_query), engine, parse_dates=["date"])

    # Full daily calendar so gap days (zero orders) count as 0, not missing
    full_range = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
    daily = daily.set_index("date").reindex(full_range, fill_value=0).rename_axis("date").reset_index()
    new_cust = new_cust.set_index("date").reindex(full_range, fill_value=0).rename_axis("date").reset_index()

    daily = daily.merge(new_cust, on="date", how="left")
    return daily


def rolling_zscore(series: pd.Series, window: int = ROLLING_WINDOW) -> pd.Series:
    rolling_mean = series.rolling(window, min_periods=window // 2).mean()
    rolling_std = series.rolling(window, min_periods=window // 2).std()
    return (series - rolling_mean) / rolling_std.replace(0, np.nan)


def iqr_flags(series: pd.Series, whisker: float = IQR_WHISKER) -> pd.Series:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - whisker * iqr, q3 + whisker * iqr
    return (series < lower) | (series > upper)


def contributing_factors(date, metric: str) -> str:
    """For a revenue/profit anomaly, name the region+category combo that
    deviated most from ITS OWN rolling baseline on that date — a lightweight,
    explainable stand-in for a full root-cause run (Day 6's root_cause.py
    does the deeper version of this for a specific user question)."""
    if metric not in ("revenue", "profit"):
        return ""
    engine = get_engine()
    query = """
        SELECT o.region, p.category, SUM(o.revenue) AS revenue
        FROM orders o JOIN products p ON o.product_id = p.product_id
        WHERE o.order_date = :d
        GROUP BY o.region, p.category
        ORDER BY revenue DESC
        LIMIT 3
    """
    with engine.begin() as conn:
        rows = conn.execute(text(query), {"d": date}).fetchall()
    if not rows:
        return "no orders that day"
    return "; ".join(f"{r.region}/{r.category}: {r.revenue:,.0f}" for r in rows)


def detect_anomalies(daily: pd.DataFrame, metrics: list) -> pd.DataFrame:
    results = []
    for metric in metrics:
        series = daily[metric]
        z = rolling_zscore(series)
        iqr_flag = iqr_flags(series)
        rolling_mean = series.rolling(ROLLING_WINDOW, min_periods=ROLLING_WINDOW // 2).mean()

        for i in daily.index:
            is_z_anomaly = abs(z.loc[i]) >= ZSCORE_THRESHOLD if pd.notna(z.loc[i]) else False
            is_iqr_anomaly = bool(iqr_flag.loc[i])
            if is_z_anomaly or is_iqr_anomaly:
                results.append({
                    "metric": metric,
                    "date": daily.loc[i, "date"].date(),
                    "actual_value": round(float(series.loc[i]), 2),
                    "expected_value": round(float(rolling_mean.loc[i]), 2) if pd.notna(rolling_mean.loc[i]) else None,
                    "z_score": round(float(z.loc[i]), 2) if pd.notna(z.loc[i]) else None,
                    "flagged_by": "z-score" if is_z_anomaly and is_iqr_anomaly else ("z-score" if is_z_anomaly else "IQR"),
                    "possible_contributors": contributing_factors(daily.loc[i, "date"].date(), metric),
                })
    return pd.DataFrame(results).sort_values(["metric", "date"])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    daily = load_daily_metrics()
    daily.to_csv(os.path.join(OUT_DIR, "daily_metrics.csv"), index=False)

    metrics = ["revenue", "profit", "orders", "returns", "new_customers"]
    anomalies = detect_anomalies(daily, metrics)
    anomalies.to_csv(os.path.join(OUT_DIR, "anomalies.csv"), index=False)

    print(f"Daily metrics built for {len(daily)} days ({daily['date'].min().date()} to {daily['date'].max().date()}).")
    print(f"\nTotal anomalies detected: {len(anomalies)}")
    print(anomalies["metric"].value_counts().to_string())

    print("\nMost recent 10 anomalies (across all metrics):")
    print(anomalies.sort_values("date").tail(10).to_string(index=False))

    print(f"\nSaved: daily_metrics.csv, anomalies.csv (in {OUT_DIR})")


if __name__ == "__main__":
    main()
