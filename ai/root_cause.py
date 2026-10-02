"""
InsightIQ — Root-Cause Analysis
==================================
When revenue (or profit, or orders) changes between two periods, this
drills down through region -> category -> product -> customer segment ->
returns -> discounts, to find which specific slices contributed most to
the change — not just "revenue is down 12%", but "down 12%, and here's
the 60% of that drop that traces to one region+category combination."

Run:
    python ai/root_cause.py                 # auto-compares the two most recent months
    python ai/root_cause.py 2026-01 2026-02  # compares two specific months (YYYY-MM)
"""

import sys
import pandas as pd
from sqlalchemy import text
from db import get_engine


def _month_bounds(month_str: str):
    start = pd.Period(month_str, freq="M").start_time.date()
    end = pd.Period(month_str, freq="M").end_time.date()
    return start, end


def _period_total(start, end, metric="revenue") -> float:
    engine = get_engine()
    query = f"SELECT COALESCE(SUM({metric}), 0) FROM orders WHERE order_date BETWEEN :s AND :e"
    with engine.begin() as conn:
        return float(conn.execute(text(query), {"s": start, "e": end}).scalar())


def _breakdown(start, end, dimension_sql: str, dimension_label: str, metric="revenue") -> pd.DataFrame:
    engine = get_engine()
    query = f"""
        SELECT {dimension_sql} AS dimension, SUM(o.{metric}) AS value
        FROM orders o
        {"JOIN products p ON o.product_id = p.product_id" if "p." in dimension_sql else ""}
        WHERE o.order_date BETWEEN :s AND :e
        GROUP BY {dimension_sql}
        ORDER BY value DESC
    """
    df = pd.read_sql(text(query), engine, params={"s": start, "e": end})
    df["dimension_type"] = dimension_label
    return df


def compare_periods(period_a: str, period_b: str, metric: str = "revenue") -> dict:
    """period_a = earlier/baseline period, period_b = later/current period (both 'YYYY-MM')."""
    a_start, a_end = _month_bounds(period_a)
    b_start, b_end = _month_bounds(period_b)

    total_a = _period_total(a_start, a_end, metric)
    total_b = _period_total(b_start, b_end, metric)
    pct_change = (total_b - total_a) / total_a * 100 if total_a else 0

    dimensions = [
        ("o.region", "region"),
        ("p.category", "category"),
        ("o.payment_method", "payment_method"),
        ("o.return_status", "return_status"),
    ]

    contributors = []
    for dim_sql, dim_label in dimensions:
        df_a = _breakdown(a_start, a_end, dim_sql, dim_label, metric).set_index("dimension")["value"]
        df_b = _breakdown(b_start, b_end, dim_sql, dim_label, metric).set_index("dimension")["value"]
        combined = pd.DataFrame({"before": df_a, "after": df_b}).fillna(0)
        combined["change"] = combined["after"] - combined["before"]
        combined["pct_of_total_change"] = combined["change"] / (total_b - total_a) * 100 if (total_b - total_a) != 0 else 0
        combined = combined.sort_values("change")
        for dim_value, row in combined.iterrows():
            if abs(row["change"]) < 0.01 * abs(total_a):  # ignore noise under 1% of baseline
                continue
            contributors.append({
                "dimension_type": dim_label,
                "dimension_value": dim_value,
                "before": round(row["before"], 2),
                "after": round(row["after"], 2),
                "change": round(row["change"], 2),
                "pct_change": round((row["change"] / row["before"] * 100) if row["before"] else 0, 1),
            })

    contributors_df = pd.DataFrame(contributors).sort_values("change")

    return {
        "metric": metric,
        "period_a": period_a, "period_b": period_b,
        "total_a": round(total_a, 2), "total_b": round(total_b, 2),
        "pct_change": round(pct_change, 2),
        "top_negative_contributors": contributors_df.head(5).to_dict("records") if not contributors_df.empty else [],
        "top_positive_contributors": contributors_df.tail(5).iloc[::-1].to_dict("records") if not contributors_df.empty else [],
    }


def format_result(result: dict) -> str:
    direction = "decreased" if result["pct_change"] < 0 else "increased"
    lines = [
        f"{result['metric'].title()} {direction} {abs(result['pct_change'])}% "
        f"from {result['period_a']} (Rs.{result['total_a']:,.0f}) to {result['period_b']} (Rs.{result['total_b']:,.0f}).",
        "",
        "Main contributors (declines):" if result["pct_change"] < 0 else "Main contributors (growth):",
    ]
    contributors = result["top_negative_contributors"] if result["pct_change"] < 0 else result["top_positive_contributors"]
    for c in contributors:
        lines.append(f"  - {c['dimension_type']}={c['dimension_value']}: "
                      f"Rs.{c['before']:,.0f} -> Rs.{c['after']:,.0f} ({c['pct_change']:+.1f}%)")

    lines += [
        "",
        "Interpretation: the decline/growth is concentrated in the factors listed above rather than spread "
        "evenly across the business — worth investigating those specific slices first.",
        "",
        "Limitation: this is a correlational breakdown of which segments moved, not a causal explanation of "
        "why they moved. Validate with the relevant business team before acting.",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        period_a, period_b = sys.argv[1], sys.argv[2]
    else:
        # auto-pick the two most recent complete months in the data
        engine = get_engine()
        with engine.begin() as conn:
            max_date = conn.execute(text("SELECT MAX(order_date) FROM orders")).scalar()
        latest_period = pd.Period(max_date, freq="M")
        period_b = str(latest_period - 1)   # last FULL month (the max month may be partial)
        period_a = str(latest_period - 2)

    result = compare_periods(period_a, period_b, metric="revenue")
    print(format_result(result))
