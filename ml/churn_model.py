"""
InsightIQ — Churn Prediction Model
=====================================
Trains Logistic Regression and Random Forest on the feature table from
churn_features.py, evaluates both, keeps the better one, and scores every
customer with a churn probability + risk category.

Run (after churn_features.py):
    python ml/churn_model.py
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "ml", "output")

NUMERIC_FEATURES = ["frequency", "monetary", "avg_order_value", "return_frequency",
                     "customer_tenure_days", "age"]
CATEGORICAL_FEATURES = ["region"]
TARGET = "churned"

# recency_days is deliberately EXCLUDED from the feature set even though
# churn_features.py computes it: the churn label itself is defined as
# "recency_days > CHURN_WINDOW_DAYS", so including it as a feature is
# data leakage — the model would just learn to threshold its own answer
# key and report a meaningless ~100% accuracy. Real churn prediction has
# to work from behavioral history (order frequency, spend, tenure, returns),
# not from a restatement of the label.

RANDOM_STATE = 42


def load_features() -> pd.DataFrame:
    path = os.path.join(OUT_DIR, "churn_features.csv")
    if not os.path.exists(path):
        raise FileNotFoundError("Run ml/churn_features.py first — churn_features.csv not found.")
    return pd.read_csv(path)


def build_pipeline(model) -> Pipeline:
    preprocess = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    return Pipeline([("preprocess", preprocess), ("model", model)])


def evaluate(name, pipeline, X_test, y_test) -> dict:
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    metrics = {
        "model": name,
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
        "f1_score": round(f1_score(y_test, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
    }
    cm = confusion_matrix(y_test, y_pred).tolist()
    metrics["confusion_matrix"] = cm  # [[TN, FP], [FN, TP]]
    return metrics


def risk_category(prob: float) -> str:
    if prob < 0.33:
        return "Low Risk"
    if prob < 0.66:
        return "Medium Risk"
    return "High Risk"


def main():
    df = load_features()
    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )

    candidates = {
        "logistic_regression": build_pipeline(LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
        "random_forest": build_pipeline(RandomForestClassifier(
            n_estimators=200, max_depth=8, random_state=RANDOM_STATE, class_weight="balanced"
        )),
    }

    results = []
    for name, pipeline in candidates.items():
        pipeline.fit(X_train, y_train)
        metrics = evaluate(name, pipeline, X_test, y_test)
        results.append((name, pipeline, metrics))
        print(f"\n{name.upper().replace('_', ' ')}")
        for k, v in metrics.items():
            if k not in ("model", "confusion_matrix"):
                print(f"  {k:<10}: {v}")
        print(f"  confusion matrix [[TN,FP],[FN,TP]]: {metrics['confusion_matrix']}")

    # Pick the best model by ROC-AUC — a more honest selector than accuracy
    # alone on a dataset that isn't perfectly balanced.
    best_name, best_pipeline, best_metrics = max(results, key=lambda r: r[2]["roc_auc"])
    print(f"\nBest model by ROC-AUC: {best_name} (ROC-AUC = {best_metrics['roc_auc']})")

    # Feature importance / coefficients, for the "important contributing
    # factors" the spec asks for per customer risk score
    if best_name == "random_forest":
        importances = best_pipeline.named_steps["model"].feature_importances_
        feature_names = (
            NUMERIC_FEATURES +
            list(best_pipeline.named_steps["preprocess"]
                 .named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES))
        )
        importance_df = pd.DataFrame({"feature": feature_names, "importance": importances}) \
            .sort_values("importance", ascending=False)
    else:
        coefs = best_pipeline.named_steps["model"].coef_[0]
        feature_names = (
            NUMERIC_FEATURES +
            list(best_pipeline.named_steps["preprocess"]
                 .named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES))
        )
        importance_df = pd.DataFrame({"feature": feature_names, "importance": np.abs(coefs)}) \
            .sort_values("importance", ascending=False)

    print("\nTop contributing factors:")
    print(importance_df.head(6).to_string(index=False))

    # Score every customer (not just the test split) for the app/dashboard
    all_proba = best_pipeline.predict_proba(X)[:, 1]
    scored = df[["customer_id", "region"]].copy()
    scored["churn_probability"] = all_proba.round(4)
    scored["risk_category"] = scored["churn_probability"].apply(risk_category)

    os.makedirs(OUT_DIR, exist_ok=True)
    scored.to_csv(os.path.join(OUT_DIR, "churn_predictions.csv"), index=False)
    importance_df.to_csv(os.path.join(OUT_DIR, "churn_feature_impact.csv"), index=False)
    joblib.dump(best_pipeline, os.path.join(OUT_DIR, "churn_model.joblib"))

    with open(os.path.join(OUT_DIR, "churn_metrics.json"), "w") as f:
        json.dump({"selected_model": best_name, "test_metrics": {k: v for r in results for k, v in [(r[0], r[2])]}}, f, indent=2)

    print(f"\nRisk category breakdown (all {len(scored):,} scored customers):")
    print(scored["risk_category"].value_counts().to_string())
    print(f"\nSaved: churn_predictions.csv, churn_feature_impact.csv, churn_model.joblib, churn_metrics.json")
    print(f"All in: {OUT_DIR}")


if __name__ == "__main__":
    main()
