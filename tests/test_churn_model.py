"""
Tests for ml/churn_model.py's feature selection — specifically a
regression test for the data-leakage bug caught during Day 5 development
(recency_days was briefly included as a model feature despite being the
literal definition of the churn label, producing a meaningless ~100%
accuracy). This test exists so that bug can never silently come back.
"""

import churn_model


def test_recency_days_excluded_from_features():
    """recency_days must NEVER appear in the model's feature set — it's
    used to construct the churn label itself (churned = recency_days >
    CHURN_WINDOW_DAYS), so including it as a feature is data leakage."""
    assert "recency_days" not in churn_model.NUMERIC_FEATURES


def test_target_excluded_from_features():
    assert churn_model.TARGET not in churn_model.NUMERIC_FEATURES
    assert churn_model.TARGET not in churn_model.CATEGORICAL_FEATURES


def test_expected_features_present():
    expected = {"frequency", "monetary", "avg_order_value", "return_frequency",
                "customer_tenure_days", "age"}
    assert expected.issubset(set(churn_model.NUMERIC_FEATURES))


def test_risk_category_thresholds():
    assert churn_model.risk_category(0.10) == "Low Risk"
    assert churn_model.risk_category(0.32) == "Low Risk"
    assert churn_model.risk_category(0.33) == "Medium Risk"
    assert churn_model.risk_category(0.65) == "Medium Risk"
    assert churn_model.risk_category(0.66) == "High Risk"
    assert churn_model.risk_category(0.99) == "High Risk"


def test_build_pipeline_returns_sklearn_pipeline():
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    pipeline = churn_model.build_pipeline(LogisticRegression())
    assert isinstance(pipeline, Pipeline)
    assert "preprocess" in pipeline.named_steps
    assert "model" in pipeline.named_steps
