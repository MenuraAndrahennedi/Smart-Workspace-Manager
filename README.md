# Smart Workspace Manager

Smart Workspace Manager is a Python learning project for building a file-management and data-workspace application in phases.

Phase 1 uses Streamlit, SQLite, SQLAlchemy, reusable backend services, and pytest. Phase 2 will later add FastAPI, React, authentication, and Azure deployment.

## Current Status

The project currently includes:

- Streamlit app entry point
- Dashboard with file totals, category/status summaries, and recent files
- File upload page
- Upload validation
- Safe stored filename generation
- Local storage setup
- Automatic file organization into managed categories
- Automation logs for organization success and failure events
- Searchable, multi-filter File Library
- Deferred file downloads and confirmed deletion
- Safe source/report deletion with rollback restoration
- SQLite database models and repositories
- Cascading file, analysis-job, and report relationships
- ORM and raw-SQL verification scripts using isolated databases
- Unit and integration tests

## Project Structure

```text
backend/
  config/          Environment/settings loading
  database/        SQLAlchemy engine, models, repositories
  services/        File, storage, and automation workflows
  utils/           Validators, path helpers, logging, constants

frontend/
  streamlit_app.py Streamlit entry point
  pages/           Streamlit pages

scripts/
  init_db.py       Creates database tables
  migrate_day7_database.py
                   Backs up and upgrades a pre-Day-8 SQLite database
  sql_verifications/
                   Isolated ORM and raw-SQL verification scripts

tests/
  unit/            Unit tests
  integration/     Integration tests
```

## Setup

Create and activate a Python 3.12 virtual environment.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies.

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Create a local `.env` file from `.env.example`, then adjust values if needed.

```powershell
Copy-Item .env.example .env
```

## Initialize Database

```powershell
python scripts/init_db.py
```

For a database created before the Day 7 cascade changes, run the
backed-up migration once:

```powershell
python scripts/migrate_day7_database.py
```

## Run Tests

```powershell
python -m pytest tests -q
```

## Run Streamlit App

```powershell
streamlit run frontend/streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

## Notes

- Runtime files are stored under `data/`.
- Uploaded files, generated reports, models, local databases, and `.env` are ignored by Git.
- Secrets should stay in `.env` or deployment environment variables, not in source code.
- Current storage support is local filesystem storage only.
