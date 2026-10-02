"""
InsightIQ — Recommendation Engine
====================================
Scans the live database for a fixed set of business-relevant conditions
and turns each one that fires into a structured Finding/Evidence/Impact/
Action/Priority card, following the spec's format exactly. Every number
in a card comes directly from a query — nothing is invented, and any
estimate is explicitly labeled as such.

Run:
    python ai/recommendations.py
"""

import os
import json
import pandas as pd
from sqlalchemy import text
from db import get_engine

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "ml", "output")

PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def rec_at_risk_customers() -> dict:
    engine = get_engine()
    query = """
        SELECT COUNT(*) AS n, AVG(cs.monetary) AS avg_value
        FROM customers c
        JOIN (
            SELECT customer_id, SUM(revenue) AS monetary FROM orders GROUP BY customer_id
        ) cs ON c.customer_id = cs.customer_id
        WHERE c.customer_segment = 'At Risk'
    """
    with engine.begin() as conn:
        row = conn.execute(text(query)).fetchone()
    if not row or row.n == 0:
        return None
    est_value_at_stake = row.n * row.avg_value
    return {
        "finding": f"{row.n} customers are in the 'At Risk' segment — previously active, high-value buyers who have gone quiet.",
        "evidence": f"Average historical spend per At Risk customer is Rs.{row.avg_value:,.0f}, comparable to the Loyal segment (ml/segmentation.py, Day 5).",
        "impact": f"Estimated revenue at stake if this segment fully churns: ~Rs.{est_value_at_stake:,.0f} (ESTIMATE: historical average spend x customer count, not a guaranteed loss).",
        "action": "Launch a targeted retention campaign (personalized offer or outreach) for the At Risk segment before they lapse into Dormant.",
        "priority": "High",
    }


def rec_unprofitable_products() -> dict:
    engine = get_engine()
    query = """
        SELECT p.product_name, p.category, SUM(o.profit) AS profit, SUM(o.revenue) AS revenue
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        HAVING SUM(o.profit) < 0
        ORDER BY profit ASC
    """
    df = pd.read_sql(text(query), engine)
    if df.empty:
        return None
    worst = df.iloc[0]
    return {
        "finding": f"{len(df)} product(s) are net loss-making across their full order history, worst being {worst.product_name} ({worst.category}).",
        "evidence": f"{worst.product_name}: Rs.{worst.revenue:,.0f} total revenue against Rs.{abs(worst.profit):,.0f} net loss.",
        "impact": f"Combined loss across all {len(df)} flagged products: Rs.{abs(df['profit'].sum()):,.0f}.",
        "action": "Review cost/pricing on these specific products; discontinue or renegotiate supplier cost if margin can't be fixed.",
        "priority": "Critical" if len(df) > 3 else "High",
    }


def rec_regional_decline() -> dict:
    """Flags a region+category combination whose most recent month is sharply below its own prior average."""
    engine = get_engine()
    query = """
        SELECT o.region, p.category, DATE_TRUNC('month', o.order_date)::date AS month, SUM(o.revenue) AS revenue
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY o.region, p.category, DATE_TRUNC('month', o.order_date)
    """
    df = pd.read_sql(text(query), engine)
    df["month"] = pd.to_datetime(df["month"])
    latest_month = df["month"].max()
    prior_months = df[df["month"] < latest_month]
    baseline = prior_months.groupby(["region", "category"])["revenue"].mean().rename("baseline_avg")
    latest = df[df["month"] == latest_month].set_index(["region", "category"])["revenue"]
    combined = pd.concat([baseline, latest.rename("latest")], axis=1).dropna()
    combined["pct_vs_baseline"] = (combined["latest"] - combined["baseline_avg"]) / combined["baseline_avg"] * 100
    worst = combined.sort_values("pct_vs_baseline").iloc[0]
    worst_region, worst_category = combined.sort_values("pct_vs_baseline").index[0]

    if worst["pct_vs_baseline"] > -20:
        return None  # nothing dropped enough to be worth flagging

    return {
        "finding": f"{worst_region} region's {worst_category} revenue is {abs(worst['pct_vs_baseline']):.0f}% below its own historical monthly average in the most recent month.",
        "evidence": f"Latest month: Rs.{worst['latest']:,.0f} vs historical average Rs.{worst['baseline_avg']:,.0f}.",
        "impact": "A localized, category-specific decline, not a business-wide trend — isolating it early limits how far it spreads to adjacent regions/categories.",
        "action": f"Investigate {worst_region}'s {worst_category} supply, local marketing spend, and competitor activity specifically; don't apply a company-wide fix to a localized problem.",
        "priority": "High",
    }


def rec_high_return_category() -> dict:
    engine = get_engine()
    query = """
        SELECT p.category,
               COUNT(*) FILTER (WHERE o.return_status = 'Returned')::float / COUNT(*) AS return_rate,
               COUNT(*) AS orders
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.category
        ORDER BY return_rate DESC LIMIT 1
    """
    with engine.begin() as conn:
        row = conn.execute(text(query)).fetchone()
    if not row or row.return_rate < 0.10:
        return None
    return {
        "finding": f"{row.category} has the highest return rate of any category, at {row.return_rate:.1%}.",
        "evidence": f"Based on {row.orders:,} orders in the category.",
        "impact": "High returns increase fulfillment and logistics cost per net sale and may signal a sizing/quality/description mismatch.",
        "action": f"Audit {row.category} product listings for sizing accuracy and description clarity; consider a size-guide or fit-quiz feature if sizing-related.",
        "priority": "Medium",
    }


def rec_slow_delivery_region() -> dict:
    engine = get_engine()
    query = """
        SELECT region, AVG(delivery_days) AS avg_days
        FROM orders GROUP BY region ORDER BY avg_days DESC LIMIT 1
    """
    with engine.begin() as conn:
        row = conn.execute(text(query)).fetchone()
    if not row or row.avg_days < 4:
        return None
    return {
        "finding": f"{row.region} has the slowest average delivery time of any region, at {row.avg_days:.1f} days.",
        "evidence": "Based on the full orders history for that region.",
        "impact": "Slower delivery is a common driver of cart abandonment and return rate on future orders, though this dataset doesn't directly prove that link for this region.",
        "action": f"Review fulfillment/logistics partners serving {row.region}; a dedicated regional warehouse or courier change may be warranted if volume justifies it.",
        "priority": "Medium",
    }


RULES = [rec_unprofitable_products, rec_regional_decline, rec_at_risk_customers,
         rec_high_return_category, rec_slow_delivery_region]


def generate_recommendations() -> list:
    cards = [rule() for rule in RULES]
    cards = [c for c in cards if c is not None]
    cards.sort(key=lambda c: PRIORITY_ORDER.get(c["priority"], 9))
    return cards


def format_card(card: dict) -> str:
    return (
        f"[{card['priority'].upper()}]\n"
        f"Finding: {card['finding']}\n"
        f"Evidence: {card['evidence']}\n"
        f"Impact: {card['impact']}\n"
        f"Action: {card['action']}"
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cards = generate_recommendations()

    with open(os.path.join(OUT_DIR, "recommendations.json"), "w") as f:
        json.dump(cards, f, indent=2)

    print(f"{len(cards)} recommendation(s) generated.\n")
    for card in cards:
        print(format_card(card))
        print()

    print(f"Saved: recommendations.json (in {OUT_DIR})")


if __name__ == "__main__":
    main()
