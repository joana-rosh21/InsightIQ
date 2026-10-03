"""
Tests for ai/copilot.py's validate_sql_is_safe() — the single gate every
query (template-generated today, potentially LLM-generated later) must
pass before touching the database. This is the most important test file
in the whole suite: a failure here means a destructive query could reach
the database.
"""

import pytest
import copilot


@pytest.mark.parametrize("sql,expected", [
    ("SELECT * FROM orders", True),
    ("SELECT region, SUM(revenue) FROM orders GROUP BY region", True),
    ("WITH recent AS (SELECT * FROM orders) SELECT * FROM recent", True),
    ("  select * from customers  ", True),  # lowercase + leading/trailing whitespace
])
def test_safe_select_queries_pass(sql, expected):
    assert copilot.validate_sql_is_safe(sql) == expected


@pytest.mark.parametrize("sql", [
    "DROP TABLE orders",
    "DELETE FROM customers",
    "UPDATE orders SET revenue = 0",
    "INSERT INTO orders VALUES (1,2,3)",
    "ALTER TABLE customers DROP COLUMN age",
    "TRUNCATE orders",
    "CREATE TABLE evil (x int)",
    "GRANT ALL ON orders TO public",
])
def test_destructive_queries_are_rejected(sql):
    assert copilot.validate_sql_is_safe(sql) is False


def test_sql_injection_style_payload_is_rejected():
    payload = "SELECT * FROM orders; DROP TABLE orders;--"
    assert copilot.validate_sql_is_safe(payload) is False


def test_non_select_statement_without_forbidden_keyword_still_rejected():
    # Doesn't contain a forbidden keyword, but also isn't a SELECT/WITH —
    # the validator should reject on the "must start with SELECT/WITH" rule.
    assert copilot.validate_sql_is_safe("EXPLAIN SELECT * FROM orders") is False


def test_run_safe_query_raises_on_unsafe_sql():
    with pytest.raises(ValueError):
        copilot.run_safe_query("DROP TABLE orders")


def test_all_six_spec_example_questions_get_a_non_error_response():
    """Every example question from the master spec should route somewhere
    sensible — either a real answer or an honest routing note, never a
    silent crash."""
    questions = [
        "What were our best-selling products?",
        "Which region performed worst?",
        "Which products are losing money?",
        "Which customers are likely to churn?",
        "Compare this month with last month.",
        "Why did revenue decline?",
        "What should management do next?",
    ]
    for q in questions:
        result = copilot.ask(q)
        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0
