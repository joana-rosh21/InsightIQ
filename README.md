# InsightIQ — AI-Powered Business Intelligence & Decision Copilot

**From Data → Insights → Decisions**

An end-to-end BI and AI decision-support platform: synthetic e-commerce data → cleaning →
PostgreSQL → SQL/Python analytics → Power BI → ML (churn prediction + RFM segmentation) →
anomaly detection → an AI Business Copilot → root-cause analysis → recommendations.

## Scope note

This was built as a 7-day portfolio project. To make that timeline realistic, scope was
deliberately reduced from a full production spec:

- **Dataset**: 5,000 customers / 300 products / 20,000 orders (not 50K/1K/100K+) — same
  generation logic, smaller volume. Change three constants in `data_pipeline/generate_data.py`
  to scale up.
- **AI Copilot**: a rule-based intent classifier + parameterized SQL templates, not a full
  LLM-SQL-generation pipeline. Chosen deliberately for reliability, zero external API
  dependency, and to guarantee no destructive query can ever be generated. The safety gate
  (`ai/copilot.py::validate_sql_is_safe`) is designed so an LLM-based generator could be
  dropped in later behind the same gate.
- **Testing & docs**: a focused pytest suite on the parts that matter most (data cleaning,
  SQL safety, churn model feature selection, live analytics), not exhaustive coverage.

## Stack

Python · PostgreSQL · Pandas · Scikit-learn · Streamlit · FastAPI · Power BI

## Project structure

```
InsightIQ/
  database/           schema.sql
  data_pipeline/       generate_data.py, clean.py, load_to_postgres.py
  analytics/            sales.py, customers.py, products.py, operations.py, db.py
  ml/                    churn_features.py, churn_model.py, segmentation.py,
                         anomaly_detection.py, db.py, output/ (generated)
  ai/                    copilot.py, root_cause.py, recommendations.py, db.py
  app/                   streamlit_app.py
  api/                    main.py
  powerbi/               InsightIQ_Dashboard.pbix
  tests/                  test_clean.py, test_copilot_safety.py, test_churn_model.py,
                          test_analytics.py, conftest.py
  docs/                   ARCHITECTURE.md, PRD.md, DEMO_SCRIPT.md, RESUME_BULLETS.md
  data/                   generated CSVs (gitignored)
  .env                    DATABASE_URL (gitignored, never commit)
  requirements.txt
```

## Setup

1. Install Python 3.11+, PostgreSQL 15+, and create a database named `insightiq`.
2. `python -m venv venv && source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3. `pip install -r requirements.txt`
4. Create `.env` in the project root:
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/insightiq
   ```
   Use the `+psycopg2` form explicitly — newer SQLAlchemy versions can otherwise try to use
   a different driver that isn't installed.

## Running the full pipeline

```bash
psql -U postgres -d insightiq -f database/schema.sql
python data_pipeline/generate_data.py
python data_pipeline/clean.py
python data_pipeline/load_to_postgres.py
python ml/churn_features.py
python ml/churn_model.py
python ml/segmentation.py
python ml/anomaly_detection.py
python ai/recommendations.py
```

## Running the apps

```bash
streamlit run app/streamlit_app.py        # dashboard: http://localhost:8501
uvicorn api.main:app --reload             # API + docs: http://localhost:8000/docs
```

## Running the tests

```bash
pytest tests/ -v
```

41 tests covering data-cleaning edge cases, the AI Copilot's SQL safety gate (including a
SQL-injection-style payload), a regression test against a real data-leakage bug caught
during development (see `docs/ARCHITECTURE.md`), and live integration tests against the
analytics layer.

## Power BI

Open `powerbi/InsightIQ_Dashboard.pbix` in Power BI Desktop. Measures are documented in
`InsightIQ_PowerBI_DAX_Measures.txt`. Connect to the same PostgreSQL database as above.

## Further documentation

- `docs/ARCHITECTURE.md` — problem statement, system architecture, database schema, data
  dictionary, AI/ML methodology, API reference, limitations, future improvements
- `docs/PRD.md` — product requirements, personas, MVP scope, prioritization
- `docs/DEMO_SCRIPT.md` — a 5-minute walkthrough script
- `docs/RESUME_BULLETS.md` — resume-ready bullet points for this project
