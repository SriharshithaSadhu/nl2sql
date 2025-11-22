# Dev smoke test for core NL→SQL flows without launching Streamlit.
# - Creates a small SQLite DB with two related tables
# - Uses functions from app.py to exercise schema extraction, FK detection,
#   template-based SQL generation (single and multi-table), and execution.
# - Prints concise results so we can verify behavior quickly.

import os
import sqlite3
import tempfile
import pandas as pd

# Ensure repository root is on sys.path so we can import core
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# Import from the decoupled core module (no Streamlit dependency)
import core as app


def build_demo_db(path: str):
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    # Create tables
    cur.execute("CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, customer_id INTEGER, total REAL)")

    # Seed data
    cur.executemany("INSERT INTO customers (id, name) VALUES (?, ?)", [
        (1, "Alice"),
        (2, "Bob"),
        (3, "Charlie"),
    ])
    cur.executemany("INSERT INTO orders (id, customer_id, total) VALUES (?, ?, ?)", [
        (101, 1, 120.0),
        (102, 1, 80.0),
        (103, 2, 50.0),
        (104, 3, 200.0),
    ])

    conn.commit()
    conn.close()


def run_case(question: str, db_path: str):
    schema = app.extract_schema(db_path)
    schema_str = app.format_schema_for_model(schema)

    # Try template/fast-path generation; tokenizer/model unused if template matches
    sql = app.generate_sql(question, schema_str, tokenizer=None, model=None, db_path=db_path)
    df, err = app.execute_sql(sql, db_path)

    print("Question:", question)
    print("SQL:", sql)
    if err:
        print("Error:", err)
    else:
        print("Rows:", 0 if df is None else len(df))
        if df is not None:
            print(df.head().to_string(index=False))
    print("-" * 60)


def main():
    tmp_db = os.path.join(tempfile.gettempdir(), "dev_smoketest.sqlite")
    if os.path.exists(tmp_db):
        os.remove(tmp_db)
    build_demo_db(tmp_db)

    print("DB path:", tmp_db)
    print("Schema:", app.extract_schema(tmp_db))
    print("FKs:", app.detect_foreign_keys(tmp_db))
    print("=" * 60)

    # Single-table
    run_case("Show all customers", tmp_db)
    run_case("Count orders", tmp_db)

    # Multi-table JOIN via heuristic FK (orders.customer_id -> customers.id)
    run_case("Count orders by customer", tmp_db)
    run_case("Show orders with customer details", tmp_db)


if __name__ == "__main__":
    main()
