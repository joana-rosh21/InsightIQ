"""
InsightIQ — Customer Segmentation (RFM)
==========================================
Scores every customer on Recency, Frequency, Monetary value (1-5 quintile
scores each), combines them into 5 named segments, and writes the result
back into customers.customer_segment in PostgreSQL — the column Day 1's
schema created and deliberately left blank for this step.

Run (after churn_features.py, which this reuses the raw RFM numbers from):
    python ml/segmentation.py
"""

import os
import pandas as pd
from sqlalchemy import text
from db import get_engine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "ml", "output")

SEGMENT_DESCRIPTIONS = {
    "High Value":  "Recent, frequent, big spenders — the core revenue base. Protect with priority service and early access to new products.",
    "Loyal":       "Frequent, consistent purchasers who aren't necessarily top spenders. Reward consistency to push them toward High Value.",
    "New":         "Recent first-time or early-stage buyers with limited order history. Focus on onboarding and a strong second-purchase experience.",
    "At Risk":     "Used to buy frequently/well but haven't ordered recently — the clearest re-engagement target before they go Dormant.",
    "Dormant":     "Long inactive, low historical frequency and spend. Lowest-cost segment to deprioritize in favor of the other four.",
}


def compute_rfm() -> pd.DataFrame:
    engine = get_engine()
    query = """
        WITH ref AS (SELECT MAX(order_date) AS max_date FROM orders)
        SELECT
            c.customer_id,
            (ref.max_date - MAX(o.order_date)) AS recency_days,
            COUNT(*)                            AS frequency,
            SUM(o.revenue)                       AS monetary
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        CROSS JOIN ref
        GROUP BY c.customer_id, ref.max_date
    """
    df = pd.read_sql(text(query), engine)
    if pd.api.types.is_timedelta64_dtype(df["recency_days"]):
        df["recency_days"] = df["recency_days"].dt.days
    else:
        df["recency_days"] = df["recency_days"].astype(int)
    return df


def score_rfm(df: pd.DataFrame) -> pd.DataFrame:
    # Recency: LOWER days-since-last-order is better -> reverse the quintile so 5 = most recent
    df["R_score"] = pd.qcut(df["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    # Frequency and Monetary: HIGHER is better -> 5 = highest
    df["F_score"] = pd.qcut(df["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["M_score"] = pd.qcut(df["monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df["rfm_score"] = df["R_score"] + df["F_score"] + df["M_score"]
    return df


def assign_segment(row) -> str:
    r, f, m = row["R_score"], row["F_score"], row["M_score"]

    if r >= 4 and f >= 4 and m >= 4:
        return "High Value"
    if f >= 4 and r >= 3:
        return "Loyal"
    if r >= 4 and f <= 2:
        return "New"
    if r <= 2 and f >= 3:
        return "At Risk"
    return "Dormant"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    df = compute_rfm()
    df = score_rfm(df)
    df["segment"] = df.apply(assign_segment, axis=1)

    # Save the per-customer result for the app/dashboard
    out_cols = ["customer_id", "recency_days", "frequency", "monetary",
                "R_score", "F_score", "M_score", "segment"]
    df[out_cols].to_csv(os.path.join(OUT_DIR, "customer_segments.csv"), index=False)

    # Segment profile summary — averages per segment, for docs/ and the AI copilot
    profile = df.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_recency_days=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
    ).round(1).reset_index()
    profile["description"] = profile["segment"].map(SEGMENT_DESCRIPTIONS)
    profile.to_csv(os.path.join(OUT_DIR, "segment_profile.csv"), index=False)

    # Write customer_segment back into PostgreSQL
    engine = get_engine()
    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("UPDATE customers SET customer_segment = :seg WHERE customer_id = :cid"),
                {"seg": row["segment"], "cid": int(row["customer_id"])}
            )
        # Any customer with zero orders never appears in the RFM query above —
        # label them explicitly rather than leaving customer_segment blank.
        result = conn.execute(text(
            "UPDATE customers SET customer_segment = 'No Orders Yet' WHERE customer_segment IS NULL"
        ))

    print(f"Segmented {len(df):,} customers with at least one order.")
    print(f"Additionally labeled {result.rowcount} zero-order customers as 'No Orders Yet'.")
    print("\nSegment sizes:")
    print(df["segment"].value_counts().to_string())
    print("\nSegment profile:")
    print(profile.drop(columns="description").to_string(index=False))
    print("\nSegment descriptions:")
    for seg, desc in SEGMENT_DESCRIPTIONS.items():
        print(f"  {seg}: {desc}")
    print(f"\nSaved: customer_segments.csv, segment_profile.csv (in {OUT_DIR})")
    print("customers.customer_segment updated in PostgreSQL.")


if __name__ == "__main__":
    main()
