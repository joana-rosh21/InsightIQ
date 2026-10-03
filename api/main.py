"""
InsightIQ — FastAPI Backend
==============================
Thin route handlers over the same analytics/ml/ai modules the Streamlit
app uses — no business logic lives here, only request/response wiring.
Swagger UI (interactive API docs) is available automatically at /docs
once this is running.

Run:
    uvicorn api.main:app --reload
Then visit:
    http://localhost:8000/docs
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for pkg in ["analytics", "ml", "ai"]:
    sys.path.insert(0, os.path.join(BASE_DIR, pkg))

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel

import sales as sales_mod
import customers as customers_mod
import products as products_mod
import operations as operations_mod
import copilot as copilot_mod
import root_cause as root_cause_mod
import recommendations as recommendations_mod

ML_OUTPUT = os.path.join(BASE_DIR, "ml", "output")

app = FastAPI(
    title="InsightIQ API",
    description="AI-powered business intelligence — analytics, ML, and AI copilot endpoints.",
    version="1.0.0",
)


class QuestionRequest(BaseModel):
    question: str


class RootCauseRequest(BaseModel):
    period_a: str  # "YYYY-MM"
    period_b: str  # "YYYY-MM"
    metric: str = "revenue"


def _read_json(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{os.path.basename(path)} not found — run the generating script first.")
    with open(path) as f:
        return json.load(f)


def _read_csv_records(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{os.path.basename(path)} not found — run the generating script first.")
    return pd.read_csv(path).to_dict("records")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "InsightIQ API"}


# ---------------------------------------------------------------------------
# Data upload (Day 2's clean.py / load_to_postgres.py do the real work —
# this endpoint accepts a file and reports what would need to happen next,
# matching the scoped-down Day 7 plan rather than running a full pipeline
# synchronously inside a request)
# ---------------------------------------------------------------------------
@app.post("/upload", tags=["data"])
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted.")
    contents = await file.read()
    save_path = os.path.join(BASE_DIR, "data", "uploads", file.filename)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(contents)
    df = pd.read_csv(save_path)
    return {
        "filename": file.filename,
        "rows": len(df),
        "columns": list(df.columns),
        "saved_to": save_path,
        "next_step": "Run data_pipeline/clean.py then data_pipeline/load_to_postgres.py to validate and load this file.",
    }


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
@app.get("/analytics/sales/summary", tags=["analytics"])
def sales_summary():
    return {
        "total_revenue": sales_mod.total_revenue(),
        "total_profit": sales_mod.total_profit(),
        "profit_margin_pct": sales_mod.profit_margin(),
        "average_order_value": sales_mod.average_order_value(),
    }


@app.get("/analytics/sales/monthly", tags=["analytics"])
def sales_monthly():
    return sales_mod.monthly_revenue().to_dict("records")


@app.get("/analytics/sales/by-region", tags=["analytics"])
def sales_by_region():
    return sales_mod.revenue_by_region().to_dict("records")


@app.get("/analytics/customers/summary", tags=["analytics"])
def customers_summary():
    return {
        "total_customers": customers_mod.total_customers(),
        "retention_rate_pct": customers_mod.retention_rate(),
        "churn_rate_90d_pct": customers_mod.churn_rate(90),
        "avg_purchase_frequency": customers_mod.average_purchase_frequency(),
    }


@app.get("/analytics/products/top", tags=["analytics"])
def products_top(n: int = 10):
    return products_mod.top_products(n).to_dict("records")


@app.get("/analytics/products/category-performance", tags=["analytics"])
def category_performance():
    return products_mod.category_performance().to_dict("records")


@app.get("/analytics/operations/summary", tags=["analytics"])
def operations_summary():
    return {
        "avg_delivery_days": operations_mod.average_delivery_time(),
        "return_rate_pct": operations_mod.return_rate(),
        "cancellation_rate_pct": operations_mod.cancellation_rate(),
    }


# ---------------------------------------------------------------------------
# AI Copilot
# ---------------------------------------------------------------------------
@app.post("/ai/ask", tags=["ai"])
def ai_ask(request: QuestionRequest):
    return copilot_mod.ask(request.question)


@app.post("/ai/root-cause", tags=["ai"])
def ai_root_cause(request: RootCauseRequest):
    try:
        return root_cause_mod.compare_periods(request.period_a, request.period_b, request.metric)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/ai/recommendations", tags=["ai"])
def ai_recommendations():
    return _read_json(os.path.join(ML_OUTPUT, "recommendations.json"))


# ---------------------------------------------------------------------------
# ML
# ---------------------------------------------------------------------------
@app.get("/ml/churn/predictions", tags=["ml"])
def churn_predictions(risk_category: str = None):
    records = _read_csv_records(os.path.join(ML_OUTPUT, "churn_predictions.csv"))
    if risk_category:
        records = [r for r in records if r["risk_category"] == risk_category]
    return records


@app.get("/ml/churn/metrics", tags=["ml"])
def churn_metrics():
    return _read_json(os.path.join(ML_OUTPUT, "churn_metrics.json"))


@app.get("/ml/segments", tags=["ml"])
def customer_segments():
    return _read_csv_records(os.path.join(ML_OUTPUT, "customer_segments.csv"))


@app.get("/ml/anomalies", tags=["ml"])
def anomalies(metric: str = None):
    records = _read_csv_records(os.path.join(ML_OUTPUT, "anomalies.csv"))
    if metric:
        records = [r for r in records if r["metric"] == metric]
    return records
