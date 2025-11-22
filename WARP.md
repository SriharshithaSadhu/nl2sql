# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

Project overview
- AskDB: a Streamlit app that converts natural-language questions into read-only SQL, executes them against a user-supplied CSV/SQLite database, and presents results with optional Plotly charts and a natural-language summary.

Prerequisites
- Python: 3.11.x
- No test or lint configuration detected (no tests/, pytest.ini, tox.ini, ruff/flake8 config, or pre-commit found).
- No build-system stanza in pyproject; install dependencies directly rather than pip install .

Environment setup
- Create and activate a virtual environment, then install dependencies listed in pyproject.toml.

PowerShell (Windows):
- python -m venv .venv
- .\\.venv\\Scripts\\Activate.ps1
- python -m pip install -U pip
- pip install "bcrypt>=5.0.0" "openpyxl>=3.1.5" "pandas>=2.3.3" "plotly>=6.4.0" "psycopg2-binary>=2.9.11" "sentencepiece>=0.2.1" "sqlalchemy>=2.0.44" "torch>=2.9.0" "transformers>=4.57.1" "xlrd>=2.0.2"

bash/zsh (macOS/Linux):
- python3 -m venv .venv
- source .venv/bin/activate
- python -m pip install -U pip
- pip install "bcrypt>=5.0.0" "openpyxl>=3.1.5" "pandas>=2.3.3" "plotly>=6.4.0" "psycopg2-binary>=2.9.11" "sentencepiece>=0.2.1" "sqlalchemy>=2.0.44" "streamlit>=1.51.0" "torch>=2.9.0" "transformers>=4.57.1" "xlrd>=2.0.2"

Run the app
- Entry point: app.py in the repo root.
- Start Streamlit on port 5000:
  - streamlit run app.py --server.port 5000

Database configuration
- Auth/chat backend:
  - DATABASE_URL (SQLAlchemy) is read from the environment. If unset, the app now falls back automatically to a local SQLite file at ./askdb_auth.sqlite3 for development.
- User-uploaded data backend:
  - A temporary SQLite file is created automatically at the OS temp directory (e.g., uploaded_db.sqlite) each time files are uploaded.

Smoke test (no UI)
- A developer smoke test is available to verify core flows without launching Streamlit:
  - python scripts/dev_smoketest.py

Notes
- No tests detected; single-test invocation is not applicable. If a test suite is later added (e.g., pytest), update this file with commands to run all tests and a single test node.
- No linter/formatter configuration detected; if added (e.g., ruff/black/flake8), update this file with the appropriate commands.

High-level architecture
- Core logic is decoupled in core.py (schema extraction, FK detection, template generation, SQL repair/exec). Streamlit UI lives in app.py.
- Data layer: Accepts CSV/Excel or existing SQLite DB. CSV/Excel are converted to SQLite. Schema extraction displays tables/columns; FK detection uses PRAGMA + heuristics.
- NL→SQL generation: Template fast-paths for common patterns; AI fallback via T5 (Hugging Face) using schema-aware prompts when needed.
- Safety and execution: Only read-only queries (SELECT/WITH). Queries are validated to block mutations before executing against SQLite.
- Result summarization: Uses t5-small to summarize tabular query results into plain English.
- Presentation: Streamlit UI renders results, optional Plotly visualizations for numeric data, and maintains a query history and schema graph.

Pulled-in guidance
- README.md contains the authoritative instructions for running the app and a concise architecture summary; the relevant parts are reflected above.
