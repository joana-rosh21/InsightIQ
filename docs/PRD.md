# InsightIQ — Product Requirements Document

## Problem statement
Business dashboards typically answer "what happened" but not "why", "what's next", or "what
should we do about it." InsightIQ combines BI with AI-powered reasoning over a company's own
data to close that gap.

## User personas
- **Executive (CEO)** — wants a 30-second read on revenue/profit/growth health.
- **Sales Manager** — wants regional/product performance and what's driving changes.
- **Marketing Manager** — wants customer segments and churn risk to target campaigns.
- **Operations Manager** — wants delivery/return/cancellation performance by region.
- **Business/Data Analyst** — wants to ask ad-hoc questions and drill into root causes
  without writing SQL by hand every time.

## User journeys
1. Analyst uploads a new month of order data -> sees a data-quality score before trusting it.
2. Executive opens Power BI Page 1 -> sees revenue dipped -> asks the AI Copilot why.
3. Marketing manager opens Customer Intelligence -> filters to "At Risk" segment -> exports
   the list for a retention campaign.
4. Operations manager checks Product Intelligence -> spots a high-return category -> gets a
   recommendation card with a concrete next action.

## User stories
- As an executive, I want one page with every headline KPI so I don't have to ask an analyst.
- As an analyst, I want to ask "why did revenue decline" in plain English and get a real,
  data-backed answer instead of re-running the same pivot table every month.
- As a marketing manager, I want customers automatically segmented so I don't have to
  manually build an RFM model in a spreadsheet.
- As anyone using this system, I want to trust that no question I ask can accidentally
  damage the underlying data.

## Functional requirements
Data upload & quality scoring, PostgreSQL storage, SQL/Python analytics, Power BI dashboard,
AI Copilot (fixed question set), root-cause drill-down, anomaly detection, churn prediction,
customer segmentation, recommendation engine, Streamlit app, FastAPI backend.

## Feature prioritization (MoSCoW)

| Priority | Features |
|---|---|
| **Must have** | Data cleaning + quality score, PostgreSQL schema, core sales/customer/product analytics, Executive Overview dashboard page, SQL-injection-safe AI Copilot |
| **Should have** | Root-cause drill-down, churn prediction, RFM segmentation, anomaly detection, remaining 4 Power BI pages |
| **Could have** | Recommendation engine, FastAPI backend, full pytest suite |
| **Won't have (this version)** | Full 100K+ row dataset, LLM-based SQL generation, multi-tenant auth, scheduled pipeline runs |

## MVP definition
A user can: load a dataset, see its quality score, view headline KPIs in Power BI, ask the
AI Copilot one of the 7 supported question types, and get a real answer backed by actual
numbers from their own data — with zero risk of the AI Copilot ever running a destructive
query. Everything in "Should have" and below is enhancement on top of that MVP.

## Success metrics
- AI Copilot answers all 7 spec example questions correctly (achieved: 7/7).
- Zero destructive queries pass the SQL safety validator (achieved: 0/9 attack patterns passed).
- Data quality score computed and displayed before any analysis runs on new data.
- Churn model reports honest, non-perfect metrics — ROC-AUC between 0.7-0.9 is the target
  band for a usable-but-realistic model (achieved: 0.83).

## Risks
- A template-based AI Copilot can't answer arbitrary questions — mitigated by an honest
  "I don't support that yet" fallback rather than a wrong guess.
- Synthetic data at reduced scale may understate real-world data quality issues — mitigated
  by testing the cleaning pipeline separately against deliberately corrupted data.
- A single churn-window definition (120 days) may not match actual business churn — flagged
  explicitly in docs/ARCHITECTURE.md's Limitations section rather than presented as ground truth.

## Future roadmap
Scale to full data volume -> LLM-based SQL generation behind the existing safety gate ->
role-based dashboards per persona -> scheduled pipeline automation -> A/B-tested retention
campaigns informed by the segmentation output.
