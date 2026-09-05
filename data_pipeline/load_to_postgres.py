"""
InsightIQ — Load Cleaned Data into PostgreSQL
================================================
Loads data/cleaned/{customers,products,orders}.csv into the insightiq
database created on Day 0, in FK-safe order (customers -> products -> orders),
then runs sanity queries to confirm the load matches the source files exactly.

Requires a .env file in the project root with DATABASE_URL set (see Day 0
setup guide). Run schema.sql first if you haven't already — this script
loads data, it does not create tables.

Run:
    python data_pipeline/load_to_postgres.py
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(BASE_DIR, "data", "cleaned")

load_dotenv(os.path.join(BASE_DIR, ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")

# Tables in FK-safe load order: customers and products have no dependencies,
# orders depends on both.
TABLES_IN_ORDER = ["customers", "products", "orders"]


def get_engine():
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not found. Check your .env file (see Day 0 setup guide).")
        sys.exit(1)
    return create_engine(DATABASE_URL)


def load_table(engine, table: str) -> int:
    path = os.path.join(CLEAN_DIR, f"{table}.csv")
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. Run data_pipeline/clean.py first.")
        sys.exit(1)

    df = pd.read_csv(path)

    with engine.begin() as conn:
        # Table already exists from schema.sql — append rows, keep the
        # explicit ids from the CSV so orders' FK references stay valid.
        df.to_sql(table, con=conn, if_exists="append", index=False, method="multi", chunksize=1000)

    return len(df)


def resync_sequence(engine, table: str, id_column: str):
    """
    Because we inserted explicit ids (not letting SERIAL generate them),
    the table's auto-increment sequence is still sitting at 1. Any future
    INSERT that omits the id would collide with existing rows. This resets
    the sequence to MAX(id) + 1 — standard practice after a bulk load with
    explicit keys. PostgreSQL-specific; harmless no-op risk is why we guard
    it in a try/except in case a table happens to be empty.
    """
    with engine.begin() as conn:
        conn.execute(text(f"""
            SELECT setval(
                pg_get_serial_sequence('{table}', '{id_column}'),
                COALESCE((SELECT MAX({id_column}) FROM {table}), 1)
            )
        """))


def run_sanity_checks(engine, expected_counts: dict):
    print("\n" + "=" * 60)
    print("SANITY CHECKS")
    print("=" * 60)

    all_passed = True
    with engine.begin() as conn:
        for table, expected in expected_counts.items():
            actual = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            status = "OK" if actual == expected else "MISMATCH"
            if actual != expected:
                all_passed = False
            print(f"  {table:<12} expected={expected:<8} actual={actual:<8} [{status}]")

        orphan_customers = conn.execute(text("""
            SELECT COUNT(*) FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
        """)).scalar()
        orphan_products = conn.execute(text("""
            SELECT COUNT(*) FROM orders o
            LEFT JOIN products p ON o.product_id = p.product_id
            WHERE p.product_id IS NULL
        """)).scalar()
        print(f"  orphaned FK (customer)  = {orphan_customers} [{'OK' if orphan_customers == 0 else 'FAIL'}]")
        print(f"  orphaned FK (product)   = {orphan_products} [{'OK' if orphan_products == 0 else 'FAIL'}]")
        if orphan_customers or orphan_products:
            all_passed = False

        total_revenue = conn.execute(text("SELECT SUM(revenue) FROM orders")).scalar()
        print(f"  total revenue in DB     = {total_revenue:,.2f}")

    print("\nRESULT:", "ALL CHECKS PASSED" if all_passed else "SOME CHECKS FAILED — review above")
    return all_passed


def main():
    engine = get_engine()

    print("Loading cleaned data into PostgreSQL...")
    counts = {}
    for table in TABLES_IN_ORDER:
        n = load_table(engine, table)
        counts[table] = n
        print(f"  loaded {n:,} rows into {table}")

    print("\nResyncing SERIAL sequences after explicit-id inserts...")
    resync_sequence(engine, "customers", "customer_id")
    resync_sequence(engine, "products", "product_id")
    resync_sequence(engine, "orders", "order_id")

    run_sanity_checks(engine, counts)


if __name__ == "__main__":
    main()
