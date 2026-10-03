# InsightIQ — Resume Bullet Points

Pick 3-5 depending on the role you're applying for. Swap numbers if you scale the dataset up.

**General / Data Analyst roles:**
- Built an end-to-end BI platform (InsightIQ) processing 20,000+ transactions across a
  normalized PostgreSQL schema, with an automated data-quality pipeline scoring and logging
  every cleaning transformation rather than silently modifying source data.
- Designed and built a 5-page Power BI dashboard with 15+ DAX measures covering executive,
  sales, customer, product, and AI-insight views, connected live to PostgreSQL.

**AI / ML-focused roles:**
- Built a churn prediction model (Logistic Regression + Random Forest, scikit-learn) and
  independently identified and fixed a data-leakage bug during development, improving the
  model from a meaningless ~100% accuracy to a realistic 0.83 ROC-AUC; locked the fix in
  with an automated regression test.
- Implemented RFM-based customer segmentation (5 segments) and a Z-score/IQR anomaly
  detection system across 5 business metrics, both using fully explainable, non-black-box methods.
- Designed a natural-language AI Business Copilot with a SQL-injection-safe query validator,
  tested against 9 destructive-query attack patterns with 100% correct rejection.

**Product / AI Product Manager roles:**
- Authored a full PRD (personas, user journeys, MoSCoW prioritization, MVP definition,
  success metrics) for an AI-powered BI product and shipped the MVP in a scoped 7-day build.
- Made and documented a deliberate build-vs-buy tradeoff (template-based SQL generation vs.
  an LLM API) prioritizing reliability and safety, with a stated migration path to an
  LLM-based approach.

**Backend / Full-stack roles:**
- Built a FastAPI backend exposing 17 endpoints across analytics, ML, and AI layers, and a
  Streamlit dashboard with 12 pages, both reading from a shared PostgreSQL database with no
  duplicated business logic.
- Wrote a 41-test pytest suite covering data-cleaning edge cases, SQL-injection safety, ML
  feature-selection correctness, and live database integration tests.

## One-line project summary (for a resume header / LinkedIn)
"InsightIQ — AI-powered business intelligence platform (Python, PostgreSQL, scikit-learn,
Streamlit, FastAPI, Power BI): data pipeline, ML churn prediction, anomaly detection, and a
SQL-injection-safe AI Copilot, with a 41-test suite and full technical/product documentation."
