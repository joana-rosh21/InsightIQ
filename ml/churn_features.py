"""
InsightIQ — Churn Feature Engineering
========================================
Builds a one-row-per-customer RFM-style feature table from the orders
table, plus the churn label the model will be trained to predict.

Label definition: a customer is "churned" if their most recent order is
more than CHURN_WINDOW_DAYS before the latest order date anywhere in the
dataset. This must stay consistent with whatever window you use in
analytics/customers.py's churn_rate() and in Power BI's Churn Rate %
measure — all three are supposed to describe the same thing.

Run:
    python ml/churn_features.py
"""

import os
import pandas as pd
from sqlalchemy import text
from db import get_engine

# Keep this in sync with Day 3's customers.py churn_rate() argument and the
# DAX "Churn Rate % (90-day)" measure. 90 days was too aggressive for this
# dataset's order frequency (~4 orders/customer over 24 months) — 120 gives
# a more usable class balance for the model without changing the meaning.
CHURN_WINDOW_DAYS = 120

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "output")


def build_feature_table() -> pd.DataFrame:
    engine = get_engine()
    query = """
        WITH ref AS (
            SELECT MAX(order_date) AS max_date FROM orders
        ),
        agg AS (
            SELECT
                o.customer_id,
                COUNT(*)                                            AS frequency,
                SUM(o.revenue)                                      AS monetary,
                AVG(o.revenue)                                      AS avg_order_value,
                MAX(o.order_date)                                   AS last_order_date,
                MIN(o.order_date)                                   AS first_order_date,
                COUNT(*) FILTER (WHERE o.return_status = 'Returned')::float
                    / COUNT(*)                                      AS return_frequency
            FROM orders o
            GROUP BY o.customer_id
        )
        SELECT
            c.customer_id,
            c.region,
            c.age,
            agg.frequency,
            agg.monetary,
            agg.avg_order_value,
            agg.return_frequency,
            (ref.max_date - agg.last_order_date)                    AS recency_days,
            (agg.last_order_date - agg.first_order_date)             AS customer_tenure_days,
            CASE WHEN (ref.max_date - agg.last_order_date) > :window
                 THEN 1 ELSE 0 END                                  AS churned
        FROM customers c
        JOIN agg ON c.customer_id = agg.customer_id
        CROSS JOIN ref
    """
    df = pd.read_sql(text(query), engine, params={"window": CHURN_WINDOW_DAYS})

    # SQLAlchemy returns interval/date-diff columns as Timedelta on some drivers — normalize to int days
    for col in ["recency_days", "customer_tenure_days"]:
        if pd.api.types.is_timedelta64_dtype(df[col]):
            df[col] = df[col].dt.days
        else:
            df[col] = df[col].astype(int)

    return df


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    features = build_feature_table()
    out_path = os.path.join(OUT_DIR, "churn_features.csv")
    features.to_csv(out_path, index=False)

    print(f"Feature table built for {len(features):,} customers (customers with at least one order).")
    print(f"Churn window: {CHURN_WINDOW_DAYS} days")
    print(f"Churned: {features['churned'].sum():,} ({features['churned'].mean():.1%})")
    print(f"Active : {(1 - features['churned']).sum():,} ({1 - features['churned'].mean():.1%})")
    print(f"\nSaved to: {out_path}")
    print("\nFeature summary:")
    print(features[["frequency", "monetary", "avg_order_value", "return_frequency",
                     "recency_days", "customer_tenure_days"]].describe().round(2).to_string())


if __name__ == "__main__":
    main()
