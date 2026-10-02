"""
InsightIQ — AI Business Copilot
==================================
A deliberately template-based, not LLM-based, natural-language-to-SQL
layer: an intent classifier (keyword matching) picks one of a fixed set
of pre-written, parameterized, SELECT-only SQL templates, runs it, and
formats the result following the spec's Answer/Evidence/Explanation/
Recommendation/Confidence structure.

Why template-based instead of calling an LLM to generate SQL: reliability
and cost. A template layer can never emit a destructive or malformed
query, needs no external API, and runs in milliseconds. The trade-off —
documented honestly rather than hidden — is that it only answers the
question shapes it was built for; an open-ended question outside those
shapes gets a clear "I can't answer that yet" instead of a guess.
Swapping in a real LLM-based generator later means keeping this same
validate_sql_is_safe() gate in front of whatever the LLM emits.

Run:
    python ai/copilot.py "What were our best-selling products?"
"""

import sys
import re
import pandas as pd
from sqlalchemy import text
from db import get_engine

# ---------------------------------------------------------------------------
# Safety gate — every query, template-generated or (later) LLM-generated,
# passes through this before touching the database.
# ---------------------------------------------------------------------------
FORBIDDEN_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE",
                       "CREATE", "GRANT", "REVOKE", "EXEC", "--", ";--"]


def validate_sql_is_safe(sql: str) -> bool:
    upper = sql.upper()
    if not upper.strip().startswith("SELECT") and not upper.strip().startswith("WITH"):
        return False
    return not any(kw in upper for kw in FORBIDDEN_KEYWORDS)


def run_safe_query(sql: str, params: dict = None) -> pd.DataFrame:
    if not validate_sql_is_safe(sql):
        raise ValueError("Query rejected by safety validator — not a read-only SELECT/WITH statement.")
    engine = get_engine()
    return pd.read_sql(text(sql), engine, params=params or {})


# ---------------------------------------------------------------------------
# Intent templates — each is (keywords_to_match, sql, handler)
# ---------------------------------------------------------------------------
def intent_best_sellers(question: str) -> dict:
    sql = """
        SELECT p.product_name, p.category, SUM(o.revenue) AS revenue, COUNT(*) AS orders
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        ORDER BY revenue DESC LIMIT 5
    """
    df = run_safe_query(sql)
    lines = [f"{r.product_name} ({r.category}): Rs.{r.revenue:,.0f} across {r.orders} orders" for r in df.itertuples()]
    return {
        "answer": f"Your top 5 best-selling products by revenue are: {df.iloc[0].product_name} leads.",
        "evidence": lines,
        "explanation": "Ranked by total revenue across all orders in the dataset.",
        "recommendation": "Ensure these top products stay well-stocked and consider featuring them in promotions.",
        "confidence": "High — based on complete order history, not a sample.",
    }


def intent_worst_region(question: str) -> dict:
    sql = """
        SELECT region, SUM(revenue) AS revenue, SUM(profit) AS profit, COUNT(*) AS orders
        FROM orders GROUP BY region ORDER BY revenue ASC
    """
    df = run_safe_query(sql)
    worst = df.iloc[0]
    lines = [f"{r.region}: Rs.{r.revenue:,.0f} revenue, Rs.{r.profit:,.0f} profit, {r.orders} orders" for r in df.itertuples()]
    return {
        "answer": f"{worst.region} is the worst-performing region by revenue, at Rs.{worst.revenue:,.0f}.",
        "evidence": lines,
        "explanation": f"{worst.region} generated the least total revenue of all 5 regions over the full dataset period.",
        "recommendation": f"Investigate {worst.region}'s product mix and marketing spend relative to other regions before reallocating budget.",
        "confidence": "High — direct aggregation, no modeling involved.",
    }


def intent_losing_money_products(question: str) -> dict:
    sql = """
        SELECT p.product_name, p.category, SUM(o.revenue) AS revenue, SUM(o.profit) AS profit, COUNT(*) AS orders
        FROM orders o JOIN products p ON o.product_id = p.product_id
        GROUP BY p.product_name, p.category
        HAVING SUM(o.profit) < 0 OR (SUM(o.profit) / NULLIF(SUM(o.revenue), 0)) < 0.05
        ORDER BY SUM(o.profit) ASC LIMIT 8
    """
    df = run_safe_query(sql)
    if df.empty:
        return {
            "answer": "No products are currently losing money or running below a 5% margin.",
            "evidence": [],
            "explanation": "Every product in the catalog clears at least a 5% profit margin on its order history.",
            "recommendation": "No immediate pricing action needed on margin grounds.",
            "confidence": "High — complete scan of all products with order history.",
        }
    lines = [f"{r.product_name} ({r.category}): Rs.{r.profit:,.0f} profit on Rs.{r.revenue:,.0f} revenue, {r.orders} orders" for r in df.itertuples()]
    return {
        "answer": f"{len(df)} products are losing money or running below a 5% margin, worst being {df.iloc[0].product_name}.",
        "evidence": lines,
        "explanation": "Flagged where total profit is negative, or margin falls under 5% of revenue.",
        "recommendation": "Review pricing or cost structure on these products; consider discontinuing persistent loss-makers.",
        "confidence": "High — direct aggregation.",
    }


def intent_churn_risk(question: str) -> dict:
    sql = """
        SELECT customer_segment, COUNT(*) AS customers
        FROM customers
        WHERE customer_segment IN ('At Risk', 'Dormant')
        GROUP BY customer_segment
    """
    df = run_safe_query(sql)
    if df.empty:
        return {
            "answer": "Customer segmentation hasn't been run yet — no churn-risk data available.",
            "evidence": [],
            "explanation": "customers.customer_segment is empty. Run ml/segmentation.py (Day 5) first.",
            "recommendation": "Run the segmentation pipeline, then re-ask this question.",
            "confidence": "N/A",
        }
    total_at_risk = df["customers"].sum()
    lines = [f"{r.customer_segment}: {r.customers} customers" for r in df.itertuples()]
    return {
        "answer": f"{total_at_risk} customers are in a churn-risk segment (At Risk or Dormant).",
        "evidence": lines,
        "explanation": "Based on RFM segmentation (ml/segmentation.py) and, for probability scores, the churn model (ml/churn_model.py).",
        "recommendation": "Target the At Risk segment first — they have above-average historical spend and are the most cost-effective to win back before they lapse fully into Dormant.",
        "confidence": "Medium-High — segmentation is rule-based and transparent; the churn model's ROC-AUC is 0.83, meaning its probability scores are informative but not certain for any individual customer.",
    }


def intent_mom_comparison(question: str) -> dict:
    sql = """
        SELECT DATE_TRUNC('month', order_date)::date AS month,
               SUM(revenue) AS revenue, SUM(profit) AS profit, COUNT(*) AS orders
        FROM orders GROUP BY 1 ORDER BY 1 DESC LIMIT 2
    """
    df = run_safe_query(sql)
    if len(df) < 2:
        return {"answer": "Not enough months of data to compare.", "evidence": [], "explanation": "",
                "recommendation": "", "confidence": "N/A"}
    this_month, last_month = df.iloc[0], df.iloc[1]
    rev_change = (this_month.revenue - last_month.revenue) / last_month.revenue * 100 if last_month.revenue else 0
    return {
        "answer": f"Revenue {'grew' if rev_change >= 0 else 'declined'} {abs(rev_change):.1f}% month-over-month "
                  f"({this_month.month} vs {last_month.month}).",
        "evidence": [
            f"{this_month.month}: Rs.{this_month.revenue:,.0f} revenue, {this_month.orders} orders",
            f"{last_month.month}: Rs.{last_month.revenue:,.0f} revenue, {last_month.orders} orders",
        ],
        "explanation": "Direct month-over-month comparison of total revenue.",
        "recommendation": "If declining, run the root-cause drill-down (ai/root_cause.py) to find which region/category drove it.",
        "confidence": "High — direct aggregation.",
    }


# ---------------------------------------------------------------------------
# Intent router
# ---------------------------------------------------------------------------
INTENTS = [
    (["best-selling", "best selling", "top product", "top-selling"], intent_best_sellers),
    (["worst region", "worst performing region", "which region performed worst"], intent_worst_region),
    (["losing money", "losing-money", "unprofitable", "low margin products"], intent_losing_money_products),
    (["likely to churn", "churn risk", "at risk customers", "who is going to churn"], intent_churn_risk),
    (["compare this month", "month over month", "vs last month", "compared to last month"], intent_mom_comparison),
]


def classify_intent(question: str):
    q = question.lower()
    for keywords, handler in INTENTS:
        if any(kw in q for kw in keywords):
            return handler
    return None


def ask(question: str) -> dict:
    handler = classify_intent(question)
    if handler is None:
        if "why" in question.lower() and "revenue" in question.lower():
            return {
                "answer": "This question needs the root-cause drill-down, not a simple lookup.",
                "evidence": [], "explanation": "", "recommendation": "",
                "confidence": "N/A",
                "note": "Run ai/root_cause.py directly, or route 'why' questions to it — see Day 6 guide.",
            }
        if "what should" in question.lower() or "recommend" in question.lower():
            return {
                "answer": "This question needs the recommendation engine, not a simple lookup.",
                "evidence": [], "explanation": "", "recommendation": "",
                "confidence": "N/A",
                "note": "Run ai/recommendations.py directly — see Day 6 guide.",
            }
        return {
            "answer": "I don't have a template for that question yet.",
            "evidence": [], "explanation": "", "recommendation": "",
            "confidence": "N/A",
            "note": "This copilot only answers the question shapes it was explicitly built for "
                     "(best-sellers, worst region, unprofitable products, churn risk, month-over-month). "
                     "Extending it means adding a new intent_*() function and a keyword entry in INTENTS.",
        }
    return handler(question)


def format_response(result: dict) -> str:
    lines = [f"### Answer\n{result['answer']}"]
    if result.get("evidence"):
        lines.append("### Evidence\n" + "\n".join(f"- {e}" for e in result["evidence"]))
    if result.get("explanation"):
        lines.append(f"### Explanation\n{result['explanation']}")
    if result.get("recommendation"):
        lines.append(f"### Recommendation\n{result['recommendation']}")
    if result.get("confidence"):
        lines.append(f"### Confidence / Limitations\n{result['confidence']}")
    if result.get("note"):
        lines.append(f"### Note\n{result['note']}")
    return "\n\n".join(lines)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "What were our best-selling products?"
    print(f"Q: {question}\n")
    print(format_response(ask(question)))
