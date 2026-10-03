# InsightIQ — 5-Minute Demo Script

**Setup before you start**: PostgreSQL running with data loaded, Streamlit app running
(`streamlit run app/streamlit_app.py`), Power BI dashboard open in a second window.

---

**[0:00–0:30] Open with the problem**
"Most dashboards tell you what happened. InsightIQ also tells you why it happened, what's
likely to happen next, and what to actually do about it." Open Streamlit's Home page —
point out the 4 headline metrics load from a live PostgreSQL database, not a static file.

**[0:30–1:30] Executive Dashboard**
Switch to Executive Dashboard page. Point at the monthly revenue/profit trend line — note
the Oct-Dec seasonal pattern. "This isn't random synthetic noise — I deliberately built
realistic seasonality, regional differences, and a customer churn pattern into the data
generator, so every downstream model has something real to find."

**[1:30–2:30] AI Copilot — the centerpiece**
Switch to AI Copilot page. Type: *"Which region performed worst?"* — show the real answer
with evidence, explanation, recommendation, and a stated confidence level. Then type:
*"Why did revenue decline?"* — show it correctly routes to root-cause analysis instead of
forcing a wrong answer out of a simple lookup. Mention: "Every query this generates is
checked against a safety validator before touching the database — I tested it against 9
destructive-query patterns including a SQL-injection payload, and all 9 were correctly
rejected."

**[2:30–3:15] Churn Prediction — the honesty story**
Switch to Churn Prediction page. Show the model metrics (ROC-AUC 0.83). "Worth mentioning:
an earlier version of this model accidentally included the exact variable used to define the
churn label as an input feature — it scored a suspicious ~100% accuracy, which is a classic
data-leakage red flag. I caught it, fixed it, and locked it in with a regression test so it
can't silently come back." (This is the single best interview moment in the whole demo —
say it confidently, it shows real ML judgment.)

**[3:15–4:00] Power BI — the business view**
Switch to Power BI. Walk through Page 1 (Executive Overview) and Page 5 (AI Insights) —
point out Page 5's content comes directly from the recommendation engine's real output, not
placeholder text.

**[4:00–4:45] Recommendations**
Back in Streamlit, open Recommendations page. Point at the top card: "This is the South
region's Electronics category declining — the recommendation engine found this completely
independently of the data generator, which is good end-to-end proof the whole pipeline
actually hangs together rather than being disconnected demo pieces."

**[4:45–5:00] Close**
"Everything here — the data pipeline, the analytics, the ML, the AI layer — runs against one
live database and actually agrees with itself. Happy to go deeper into any layer: the
database schema, the ML methodology, or the AI safety design."

---

## Anticipated questions and good answers

**"Why not just use GPT to generate the SQL?"**
Reliability and safety — a template layer can never emit a malformed or destructive query.
The validator that guards it is designed so an LLM-based generator could sit behind the same
gate later without changing the safety guarantee.

**"Is this real data?"**
Synthetic, generated with realistic patterns (seasonality, regional variance, a deliberate
churn cohort, a planted regional decline) specifically so every downstream model has
something genuine to detect — not just random numbers with a nice chart wrapped around them.

**"How would this scale to the full 100K+ row spec?"**
Three constants in `data_pipeline/generate_data.py` — the architecture doesn't change.
