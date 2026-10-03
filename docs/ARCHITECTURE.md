# InsightIQ — Architecture & Technical Documentation

## 1. Problem statement

Dashboards answer "what happened?" InsightIQ is built to also answer "why did it happen?",
"what's likely to happen next?", and "what should the business do?" — combining traditional
BI with AI-powered analytical reasoning over a company's own data, not general LLM knowledge.

## 2. Objective

Let business users upload data, get it cleaned and stored reliably, analyze it with SQL/Python,
visualize KPIs in Power BI, detect anomalies, predict churn, segment customers, ask natural-
language questions via an AI Copilot, and receive concrete, evidence-backed recommendations.

## 3. Target users

CEO/Executive, Sales Manager, Marketing Manager, Operations Manager, Business Analyst, Data Analyst.

## 4. Functional requirements (implemented)

Data upload (CSV), data quality scoring and cleaning with full audit trail, normalized
PostgreSQL schema, SQL/Python analytics (sales/customer/product/operations), a 5-page Power
BI dashboard, an AI Copilot answering 7 example question types, hierarchical root-cause
analysis, Z-score/IQR anomaly detection across 5 metrics, a churn prediction model with
honest evaluation metrics, RFM customer segmentation written back to the database, and a
rule-based recommendation engine.

## 5. Non-functional requirements

Read-only SQL enforced for all AI-generated queries (destructive keywords blocked at a
validator layer, tested against 8 attack patterns including SQL injection). Credentials
via environment variables, never hardcoded. Data transformations logged, never silent.
Test suite covering the highest-risk components (SQL safety, data cleaning, ML feature
selection) rather than 100% line coverage.

## 6. System architecture

```
CSV upload -> clean.py (quality audit + transform log) -> PostgreSQL
                                                              |
                        +---------------------+---------------+----------------+
                        |                     |                                |
                  analytics/ (SQL)        ml/ (scikit-learn)              ai/ (templates)
                        |                     |                                |
                        +---------+-----------+----------------+---------------+
                                  |                              |
                           Streamlit app                    FastAPI backend
                                  |                              |
                              Power BI  <---------------  (same PostgreSQL)
```

Every layer reads from the same PostgreSQL database; nothing is duplicated or cached
inconsistently between the dashboard, the API, and Power BI.

## 7. Database schema

**customers**: customer_id (PK), name, age, city, region, signup_date, customer_segment
**products**: product_id (PK), product_name, category, sub_category, cost, price
**orders**: order_id (PK), customer_id (FK), product_id (FK), order_date, quantity, revenue,
cost, discount, profit, region, payment_method, delivery_days, return_status

Indexes on orders(order_date, customer_id, product_id, region) and customers(region),
products(category) — chosen to match the actual query patterns in analytics/.
Full DDL: `database/schema.sql`.

## 8. Data dictionary (key derived fields)

| Field | Defined in | Meaning |
|---|---|---|
| customer_segment | ml/segmentation.py | RFM-based: High Value / Loyal / New / At Risk / Dormant / No Orders Yet |
| churned (label) | ml/churn_features.py | 1 if days since last order > 120 (CHURN_WINDOW_DAYS), else 0 |
| risk_category | ml/churn_model.py | Low/Medium/High Risk, from predicted churn probability thresholds (0.33, 0.66) |
| quality_score_pct | data_pipeline/clean.py | % of rows passing all validation checks, per table |

## 9. AI architecture

`ai/copilot.py` implements: Question -> keyword-based intent classification -> one of 5
parameterized SQL templates -> `validate_sql_is_safe()` gate -> execution -> structured
Answer/Evidence/Explanation/Recommendation/Confidence response. "Why did X change" routes to
`ai/root_cause.py` (region -> category -> payment method -> return status drill-down);
"what should we do" routes to `ai/recommendations.py` (5 independent rule functions, each
producing a Finding/Evidence/Impact/Action/Priority card or nothing).

**Design choice**: template-based rather than LLM-generated SQL, for reliability, zero
external API cost/dependency, and a structurally impossible-to-bypass safety guarantee.
The tradeoff is explicit: only the question shapes it was built for are answered; anything
else gets an honest "I don't have a template for that yet" rather than a guess.

## 10. ML methodology

**Churn model**: RFM-style features (frequency, monetary, avg_order_value, return_frequency,
customer_tenure_days, age, region) feed Logistic Regression and Random Forest; the better
model by ROC-AUC is kept. `recency_days` is deliberately **excluded** from the feature set
despite being computed — it's the literal basis of the churn label, so including it is data
leakage. An earlier version of this code did include it and scored a meaningless ~100%
accuracy; the corrected model scores a realistic 0.83 ROC-AUC. This is covered by a
regression test (`tests/test_churn_model.py::test_recency_days_excluded_from_features`) so
the bug can't silently return.

**Segmentation**: classic RFM quintile scoring (1-5 on Recency, Frequency, Monetary),
combined via a small rule set into 5 named segments, written back into
`customers.customer_segment`.

**Anomaly detection**: a day is flagged if EITHER a 14-day rolling Z-score exceeds 2.5, OR
the value falls outside the whole series' IQR fence — two independent, fully explainable
(no black-box) methods.

## 11. Power BI dashboard

5 pages: Executive Overview, Sales Intelligence, Customer Intelligence, Product Intelligence,
AI Insights. Connects directly to PostgreSQL; DAX measures documented in
`InsightIQ_PowerBI_DAX_Measures.txt`. Page 5's content is populated from
`ai/recommendations.py`'s output, not static text.

## 12. API reference

FastAPI app (`api/main.py`), interactive docs at `/docs` once running. Endpoint groups:
`/analytics/*` (sales, customers, products, operations), `/ai/*` (ask, root-cause,
recommendations), `/ml/*` (churn predictions/metrics, segments, anomalies), `/upload`.
17 endpoints, all tested with FastAPI's TestClient.

## 13. Installation

See `README.md`.

## 14. Testing

41 pytest tests across 4 files: cleaning-logic edge cases on hand-built dirty data, the AI
Copilot's SQL safety gate (8 destructive-query patterns + 1 injection payload, all rejected),
a regression test locking in the churn-model leakage fix, and live integration tests against
the analytics layer. Run: `pytest tests/ -v`.

## 15. Limitations

- Dataset is synthetic at a reduced scale (5K/300/20K) relative to the original spec's target.
- The AI Copilot only answers pre-built question shapes; it is not a general NL-to-SQL system.
- Churn label uses a single fixed 120-day inactivity window; a production system would likely
  validate this choice against actual business-defined churn rather than a chosen constant.
- No authentication/authorization layer — not built for multi-tenant or production deployment.
- Root-cause analysis is correlational (which segments moved), not causal (why they moved).

## 16. Future improvements

- Scale dataset generation to the full 50K/1K/100K+ spec.
- Swap the template-based copilot for an LLM-based SQL generator behind the existing safety gate.
- Add authentication and per-role dashboards (the 6 target personas currently share one view).
- Expand the churn model to compare against the business's actual definition of churn, not
  just the 120-day proxy used here.
- Add a scheduled/triggered re-run of the full pipeline instead of manual script execution.
