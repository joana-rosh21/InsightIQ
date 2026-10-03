"""
InsightIQ — Streamlit Dashboard
==================================
12 pages wired directly to the analytics/, ml/, and ai/ modules built on
Days 3, 5, and 6 — this file contains almost no business logic of its
own, it just calls those modules and renders the result.

Run:
    streamlit run app/streamlit_app.py
"""

import os
import sys
import json
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Make analytics/, ml/, ai/ importable as plain modules (each uses a bare
# `from db import get_engine`, so each package's own folder must be on
# sys.path — this keeps Days 3/5/6's files completely unmodified).
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for pkg in ["analytics", "ml", "ai"]:
    sys.path.insert(0, os.path.join(BASE_DIR, pkg))

import sales as sales_mod
import customers as customers_mod
import products as products_mod
import operations as operations_mod
import copilot as copilot_mod

ML_OUTPUT = os.path.join(BASE_DIR, "ml", "output")
DATA_DIR = os.path.join(BASE_DIR, "data")

st.set_page_config(page_title="InsightIQ", layout="wide", page_icon="📊")

PAGES = [
    "Home", "Data Upload", "Data Quality", "Executive Dashboard",
    "Sales Analytics", "Customer Analytics", "Product Analytics",
    "AI Copilot", "Churn Prediction", "Anomaly Detection",
    "Recommendations", "About Project",
]


def _read_csv_safe(path, **kwargs):
    if os.path.exists(path):
        return pd.read_csv(path, **kwargs)
    return None


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_home():
    st.title("📊 InsightIQ")
    st.caption("From Data → Insights → Decisions")
    st.markdown(
        "AI-powered business intelligence and decision-support platform. "
        "Use the sidebar to move between data pipeline status, analytics, "
        "ML predictions, and the AI Business Copilot."
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Revenue", f"Rs.{sales_mod.total_revenue():,.0f}")
    col2.metric("Total Customers", f"{customers_mod.total_customers():,}")
    col3.metric("Avg Order Value", f"Rs.{sales_mod.average_order_value():,.0f}")
    col4.metric("Profit Margin", f"{sales_mod.profit_margin()}%")


def page_data_upload():
    st.title("📤 Data Upload")
    st.markdown(
        "Upload a CSV matching the customers / products / orders schema. "
        "In this scoped build, uploads are previewed here; running them "
        "through the full cleaning + load pipeline is a `data_pipeline/clean.py` "
        "and `load_to_postgres.py` run from the command line (Day 2)."
    )
    uploaded = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        st.success(f"Loaded {len(df):,} rows, {len(df.columns)} columns.")
        st.dataframe(df.head(20), width="stretch")
        st.write("Column types:")
        st.dataframe(df.dtypes.astype(str).rename("dtype"), width="stretch")


def page_data_quality():
    st.title("✅ Data Quality")
    report_path = os.path.join(DATA_DIR, "quality_report.json")
    if not os.path.exists(report_path):
        st.warning("No quality_report.json found — run `python data_pipeline/clean.py` first.")
        return
    with open(report_path) as f:
        report = json.load(f)

    st.metric("Overall Quality Score", f"{report['overall_quality_score_pct']}%")
    cols = st.columns(3)
    for col, table in zip(cols, ["customers", "products", "orders"]):
        rep = report[table]
        with col:
            st.subheader(table.title())
            st.metric("Quality Score", f"{rep['quality_score_pct']}%")
            st.write(f"Total rows: {rep['total_rows']:,}")
            st.write(f"Valid rows: {rep['valid_rows']:,}")
            st.write(f"Invalid rows: {rep['invalid_rows']:,}")
            st.write(f"Duplicates: {rep['duplicate_records']:,}")

    log_path = os.path.join(DATA_DIR, "transformation_log.csv")
    log_df = _read_csv_safe(log_path)
    if log_df is not None and len(log_df):
        st.subheader("Transformation Log")
        st.dataframe(log_df, width="stretch")


def page_executive_dashboard():
    st.title("🏢 Executive Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Revenue", f"Rs.{sales_mod.total_revenue():,.0f}")
    c2.metric("Profit", f"Rs.{sales_mod.total_profit():,.0f}")
    c3.metric("Orders", f"{_order_count():,}")
    c4.metric("Customers", f"{customers_mod.total_customers():,}")

    c5, c6, c7 = st.columns(3)
    c5.metric("Retention Rate", f"{customers_mod.retention_rate()}%")
    c6.metric("Churn Rate (90d)", f"{customers_mod.churn_rate(90)}%")
    c7.metric("Avg Order Value", f"Rs.{sales_mod.average_order_value():,.0f}")

    st.subheader("Monthly Revenue & Profit Trend")
    monthly = sales_mod.monthly_revenue()
    st.line_chart(monthly.set_index("month")[["revenue", "profit"]])


def _order_count():
    return int(sales_mod.monthly_revenue()["orders"].sum())


def page_sales_analytics():
    st.title("💰 Sales Analytics")
    st.subheader("Revenue by Region")
    st.bar_chart(sales_mod.revenue_by_region().set_index("region")["revenue"])

    st.subheader("Top 10 Products by Revenue")
    st.dataframe(sales_mod.revenue_by_product(10), width="stretch")

    st.subheader("Discount Analysis")
    st.dataframe(sales_mod.discount_analysis(), width="stretch")

    st.subheader("Revenue Growth Month-over-Month")
    st.dataframe(sales_mod.revenue_growth_mom().tail(12), width="stretch")


def page_customer_analytics():
    st.title("👥 Customer Analytics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Customers", f"{customers_mod.total_customers():,}")
    c2.metric("Retention Rate", f"{customers_mod.retention_rate()}%")
    c3.metric("Avg Purchase Frequency", f"{customers_mod.average_purchase_frequency()}")

    seg_df = _read_csv_safe(os.path.join(ML_OUTPUT, "customer_segments.csv"))
    if seg_df is not None:
        st.subheader("Segment Distribution")
        seg_counts = seg_df["segment"].value_counts()
        st.bar_chart(seg_counts)
    else:
        st.info("Run `python ml/segmentation.py` to populate customer segments.")

    st.subheader("Top 15 Customers by Lifetime Value")
    st.dataframe(customers_mod.customer_lifetime_value().head(15), width="stretch")


def page_product_analytics():
    st.title("📦 Product Analytics")
    st.subheader("Category Performance")
    st.dataframe(products_mod.category_performance(), width="stretch")

    t1, t2 = st.columns(2)
    with t1:
        st.subheader("Top 10 Products")
        st.dataframe(products_mod.top_products(10), width="stretch")
    with t2:
        st.subheader("Bottom 10 Products")
        st.dataframe(products_mod.bottom_products(10), width="stretch")

    st.subheader("Highest Return-Rate Products")
    st.dataframe(products_mod.return_rate_by_product(10), width="stretch")


def page_ai_copilot():
    st.title("🤖 AI Business Copilot")
    st.caption("Template-based NL-to-SQL — answers the question shapes it was explicitly built for.")
    examples = [
        "What were our best-selling products?",
        "Which region performed worst?",
        "Which products are losing money?",
        "Which customers are likely to churn?",
        "Compare this month with last month.",
    ]
    question = st.selectbox("Pick an example, or type your own below:", [""] + examples)
    typed = st.text_input("Your question:", value=question)
    if st.button("Ask") and typed:
        result = copilot_mod.ask(typed)
        st.markdown(f"### Answer\n{result['answer']}")
        if result.get("evidence"):
            st.markdown("### Evidence")
            for e in result["evidence"]:
                st.markdown(f"- {e}")
        if result.get("explanation"):
            st.markdown(f"### Explanation\n{result['explanation']}")
        if result.get("recommendation"):
            st.markdown(f"### Recommendation\n{result['recommendation']}")
        if result.get("confidence"):
            st.markdown(f"### Confidence / Limitations\n{result['confidence']}")
        if result.get("note"):
            st.info(result["note"])


def page_churn_prediction():
    st.title("⚠️ Churn Prediction")
    pred_df = _read_csv_safe(os.path.join(ML_OUTPUT, "churn_predictions.csv"))
    if pred_df is None:
        st.warning("Run `python ml/churn_model.py` first.")
        return

    metrics_path = os.path.join(ML_OUTPUT, "churn_metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            metrics = json.load(f)
        m = metrics["test_metrics"][metrics["selected_model"]]
        st.caption(f"Model: {metrics['selected_model']} — "
                   f"Accuracy {m['accuracy']}, Precision {m['precision']}, "
                   f"Recall {m['recall']}, F1 {m['f1_score']}, ROC-AUC {m['roc_auc']}")

    st.subheader("Risk Category Breakdown")
    st.bar_chart(pred_df["risk_category"].value_counts())

    risk_filter = st.multiselect("Filter by risk category", pred_df["risk_category"].unique().tolist(),
                                  default=pred_df["risk_category"].unique().tolist())
    st.dataframe(
        pred_df[pred_df["risk_category"].isin(risk_filter)].sort_values("churn_probability", ascending=False),
        width="stretch",
    )


def page_anomaly_detection():
    st.title("🔍 Anomaly Detection")
    anomalies_df = _read_csv_safe(os.path.join(ML_OUTPUT, "anomalies.csv"))
    if anomalies_df is None:
        st.warning("Run `python ml/anomaly_detection.py` first.")
        return

    metric_filter = st.selectbox("Metric", ["All"] + sorted(anomalies_df["metric"].unique().tolist()))
    display_df = anomalies_df if metric_filter == "All" else anomalies_df[anomalies_df["metric"] == metric_filter]
    st.dataframe(display_df.sort_values("date", ascending=False), width="stretch")
    st.caption(f"{len(display_df)} anomalies shown, flagged by rolling Z-score (>=2.5) or IQR.")


def page_recommendations():
    st.title("💡 Recommendations")
    rec_path = os.path.join(ML_OUTPUT, "recommendations.json")
    if not os.path.exists(rec_path):
        st.warning("Run `python ai/recommendations.py` first.")
        return
    with open(rec_path) as f:
        cards = json.load(f)

    priority_colors = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
    for card in cards:
        with st.container(border=True):
            st.markdown(f"{priority_colors.get(card['priority'], '⚪')} **{card['priority']}**")
            st.markdown(f"**Finding:** {card['finding']}")
            st.markdown(f"**Evidence:** {card['evidence']}")
            st.markdown(f"**Impact:** {card['impact']}")
            st.markdown(f"**Action:** {card['action']}")


def page_about():
    st.title("ℹ️ About InsightIQ")
    st.markdown("""
**InsightIQ** is an AI-powered business intelligence and decision-support platform
built end-to-end: synthetic data generation → cleaning → PostgreSQL →
SQL/Python analytics → Power BI → ML (churn + segmentation) → anomaly
detection → an AI Business Copilot → root-cause analysis → recommendations.

**Stack:** Python, PostgreSQL, Pandas, Scikit-learn, Streamlit, FastAPI, Power BI.

**Scope note:** built as a 7-day portfolio project with a deliberately
reduced data volume (5K customers / 300 products / 20K orders) and a
template-based AI layer rather than full LLM-SQL generation — see the
project README for the full reasoning behind those choices.
""")


ROUTES = {
    "Home": page_home,
    "Data Upload": page_data_upload,
    "Data Quality": page_data_quality,
    "Executive Dashboard": page_executive_dashboard,
    "Sales Analytics": page_sales_analytics,
    "Customer Analytics": page_customer_analytics,
    "Product Analytics": page_product_analytics,
    "AI Copilot": page_ai_copilot,
    "Churn Prediction": page_churn_prediction,
    "Anomaly Detection": page_anomaly_detection,
    "Recommendations": page_recommendations,
    "About Project": page_about,
}


def main():
    st.sidebar.title("InsightIQ")
    selection = st.sidebar.radio("Navigate", PAGES)
    ROUTES[selection]()


if __name__ == "__main__":
    main()
