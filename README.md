# Smart Workspace Manager

Smart Workspace Manager is a local Streamlit application for organizing files and working with spreadsheet datasets. It combines file storage, SQLite metadata, XLSX-to-CSV conversion, CSV analysis and cleaning, chart creation, and HTML/PDF reporting in one service-oriented Python project.

The current repository contains the Phase 1 file-management and spreadsheet workflow through report generation, together with service-layer enforcement, logging, controlled errors, database/storage integration tests, and clean-environment release verification.

## Features

### File management

- Accept supported files up to the configured upload limit.
- Sanitize names and allocate unique stored filenames.
- Organize uploads by category and year/month.
- Search and filter files by name, category, and status.
- Download or delete managed files.
- Keep file deletion consistent with database commits and rollbacks.
- Record organization successes and failures in automation logs.

Supported extensions include CSV/Excel, documents, PDFs, images, audio, video, archives, presentations, structured data, and common source-code files. Files outside the main organizer categories are stored under `processed/others/`.

### CSV analysis

- Load UTF-8 and UTF-8 BOM CSV files within size, row, and column limits.
- Show a preview, dimensions, columns, pandas data types, missing-value counts, duplicate-row counts, and descriptive statistics.
- Apply numeric and text filters without changing the source CSV.
- Record analysis jobs with pending, completed, or failed status.

### CSV cleaning

- Remove duplicates using all columns or selected columns.
- Fill numeric nulls with the mean, median, or a constant.
- Fill text nulls with a chosen value.
- Drop rows containing nulls in all or selected columns.
- Combine operations in a predictable order and preview from the original data each time.
- Export independent CSV and Excel copies without modifying the organized source.
- Register cleaned CSV and XLSX exports as organized files so they are available to downstream tools.

### XLSX to CSV

- Select an organized XLSX workbook and one of its worksheets.
- Preview the worksheet before conversion.
- Enforce the configured workbook size, row, and column limits.
- Save each conversion as a UTF-8 BOM CSV under the dated spreadsheet directory.
- Register the generated CSV as an organized file for immediate use in the Analyzer, Cleaner, and Report pages.
- Download the latest converted CSV without changing the source workbook.

### Charts and reports

- Classify numeric, categorical, and existing pandas datetime columns.
- Build histogram, frequency/aggregated bar, line, and scatter charts.
- Validate columns, aggregations, row limits, and bar-category limits.
- Add, preview, and remove up to the configured number of report charts.
- Generate HTML and PDF outputs while keeping the chart list available for another report.
- Download the latest generated HTML and PDF files.
- Store separate report records for the HTML and PDF outputs.

## Application Pages

| Page             | Purpose                                                              |
| ---------------- | -------------------------------------------------------------------- |
| Dashboard        | View totals, category/status summaries, and recent files.            |
| File Upload      | Validate, upload, and organize a file.                               |
| File Library     | Search, filter, download, and delete managed files.                  |
| CSV Analyzer     | Inspect and filter an organized CSV while recording an analysis job. |
| CSV Cleaner      | Preview cleaning operations and export CSV/Excel results.            |
| Generate Reports | Configure charts and generate downloadable HTML/PDF reports.         |
| XLSX to CSV      | Preview and convert one XLSX worksheet into an organized CSV.        |

The Streamlit pages are UI orchestration only. They call backend services rather than repositories or the filesystem directly.

## Architecture

```text
Streamlit pages
      |
Backend services
      |
Repositories + SQLAlchemy models
      |
SQLite database + managed local storage
```

The main persisted relationships are:

```text
FileRecord
|-- AnalysisJob
`-- Report
```

An analysis job records a CSV analysis operation. A report records one generated output file. Reports are linked directly to their source file and are not linked to analysis jobs. Deleting a file record cascades to its analysis jobs and reports; the file service coordinates removal of the related physical files.

Additional independent tables store automation logs and non-secret application settings.

## Project Structure

```text
backend/
  config/          Environment settings
  database/        Engine, sessions, models, and repositories
  services/        Application workflows and validation
  utils/           File, path, time, validation, and logging helpers

frontend/
  streamlit_app.py Streamlit entry point
  ui_helpers.py    Shared page presentation/error helpers
  pages/           Seven numbered workflow pages

scripts/
  init_db.py       Create missing database tables
  migrate_database.py
                   Back up and upgrade an older SQLite database
  sql_verifications/
                   Isolated ORM and raw-SQL verification scripts

tests/
  unit/            Utilities, services, reports, charts, and UI boundaries
  integration/     Database, storage, migration, and workflow behavior

data/              Local runtime state; ignored by Git
docs/              Work plan, project notes, and SQL documentation
```

## Requirements

- Python 3.12
- PowerShell for the commands shown below
- Local filesystem access

The application uses Streamlit, SQLAlchemy, pandas, Plotly, Matplotlib, and openpyxl. Runtime dependencies are pinned in `requirements.txt`; test dependencies are pinned in `requirements-dev.txt`.

## Quick Start

Create and activate a virtual environment:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install development dependencies. This includes all application dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

For an application-only environment, install `requirements.txt` instead:

```powershell
python -m pip install -r requirements.txt
```

Create the local configuration and database:

```powershell
Copy-Item .env.example .env
python scripts/init_db.py
```

Start the application:

```powershell
python -m streamlit run frontend/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). Streamlit discovers the numbered pages under `frontend/pages/` automatically.

## Configuration

The application loads `.env` from the project root. The included `.env.example` is suitable for local development.

| Variable                | Purpose                                                               | Default example                       |
| ----------------------- | --------------------------------------------------------------------- | ------------------------------------- |
| `DATABASE_URL`          | SQLite database URL                                                   | `sqlite:///./data/smart_workspace.db` |
| `STORAGE_PROVIDER`      | Storage implementation; currently only local                          | `local`                               |
| `DATA_ROOT`             | Root for managed runtime files                                        | `./data`                              |
| `MAX_UPLOAD_SIZE_MB`    | Upload and CSV analysis size limit; maximum accepted setting is 10 MB | `10`                                  |
| `MAX_FILENAME_ATTEMPTS` | Attempts to allocate a unique stored name                             | `3`                                   |
| `LOG_LEVEL`             | Root application log level                                            | `INFO`                                |
| `MAX_CSV_ROWS`          | Maximum CSV rows loaded                                               | `50000`                               |
| `MAX_CSV_COLUMNS`       | Maximum CSV columns loaded                                            | `200`                                 |
| `MAX_CHART_ROWS`        | Maximum raw rows used by a chart                                      | `5000`                                |
| `MAX_BAR_CATEGORIES`    | Maximum categories in a bar chart                                     | `30`                                  |
| `MAX_REPORT_CHARTS`     | Maximum charts in one report                                          | `10`                                  |

`SECRET_KEY` is reserved for a future authentication phase and is not used. `MAX_CSV_ANALYSIS_SIZE_MB` remains in the example file for compatibility, but the current CSV size limit follows `MAX_UPLOAD_SIZE_MB`.

Do not commit `.env`, runtime databases, uploaded files, or generated reports.

## Database

Create all missing tables in a new database:

```powershell
python scripts/init_db.py
```

For a database created by an older version of the project, run the migration once:

```powershell
python scripts/migrate_database.py
```

The migration creates a timestamped database backup, upgrades analysis/report relationships, enables and verifies foreign-key integrity, normalizes legacy failure statuses, removes records for missing source files, and organizes valid files still left in uploads.

The database contains these tables:

| Table             | Purpose                                    |
| ----------------- | ------------------------------------------ |
| `files`           | Managed file metadata and storage location |
| `analysis_jobs`   | Recorded CSV analysis operations           |
| `reports`         | Generated HTML or PDF report metadata      |
| `automation_logs` | Durable organization activity records      |
| `settings`        | Non-secret application settings            |

## Runtime Storage

All managed paths are resolved beneath `DATA_ROOT`:

```text
data/
  backups/                    Migration backups
  logs/smart_workspace.log   Rotating application log
  processed/
    spreadsheets/YYYY/MM/    Organized spreadsheets and converted CSV files
    images/YYYY/MM/           Organized images
    documents/YYYY/MM/        Documents and presentations
    pdf/YYYY/MM/              Organized PDF files
    others/YYYY/MM/           Other supported file types
    cleaned/
      csv/YYYY/MM/            Cleaned CSV exports
      excel/YYYY/MM/          Cleaned Excel exports
  reports/
    html/YYYY/MM/             Interactive HTML reports
    pdf/YYYY/MM/              Static PDF reports
  uploads/                    Temporary upload location
  smart_workspace.db         Default SQLite database
```

Deletion first stages physical files below an internal `.trash` directory. Files are finalized after a successful database commit or restored after a rollback. Path validation prevents reads, moves, downloads, and deletes outside the configured data root.

## Logging and Errors

Application logs are written to stderr and `data/logs/smart_workspace.log` using UTC timestamps. The file rotates at 5 MB and retains three backups. Supported `LOG_LEVEL` values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, and `NOTSET`.

Services raise controlled domain errors for expected validation failures. Streamlit pages show concise user-facing messages while unexpected exceptions are logged with traceback details instead of exposing internal paths or stack traces in the UI.

## Tests

Run the complete suite:

```powershell
python -m pytest -q
```

Run one test group:

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
```

Optional coverage report:

```powershell
python -m pytest --cov=backend --cov=frontend --cov-report=term-missing
```

The current verified baseline is **186 passing tests**. Coverage includes configuration and path utilities, repository CRUD and filters, upload/organization workflows, database cascades and rollback behavior, XLSX worksheet conversion and cleanup, CSV analysis and cleaning, every chart type, report generation and cleanup, logging, user-facing helpers, and the Streamlit service-layer boundary.

The integration tests use temporary databases and data roots; they do not use the real application database or managed files.

## Release Verification

Before a release, verify dependency reproducibility in a temporary Python 3.12 environment:

```powershell
python -m venv .venv-release-test
.\.venv-release-test\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip check
python -m pytest -q
python -m streamlit run frontend/streamlit_app.py
```

After the checks finish, deactivate and remove only that temporary environment:

```powershell
deactivate
Remove-Item -LiteralPath .venv-release-test -Recurse -Force
```

This clean-environment check was completed successfully with the current pinned requirements.

## SQL Verification

The learning-oriented SQL scripts run against isolated databases:

```powershell
python scripts/sql_verifications/sql_crud_verification.py
python scripts/sql_verifications/sql_query_verification.py
```

See [SQL and SQLAlchemy notes](docs/sql/sql_crud.md) for the corresponding examples and explanations.

## Known Limitations

- Storage and SQLite are local only.
- There is no authentication, authorization, or per-user ownership.
- CSV date strings are not parsed automatically; line charts recognize numeric columns and columns already typed as pandas datetime.
- XLSX conversion supports `.xlsx` workbooks and converts one worksheet at a time.
- HTML reports load Plotly JavaScript from a CDN, so interactive charts need internet access when the saved report is opened.
- PDF report charts are static.
- Large CSV and chart workloads are intentionally restricted by configuration limits.
- The API, React client, Azure SQL, and deployment workflows are future work.

## Project Status

- Core file, database, organization, dashboard, library, XLSX conversion, CSV analysis, cleaning, visualization, and reporting workflows are implemented.
- Day 13-style hardening is present: pages call services, reusable errors are controlled, logging is configured, critical storage/database paths have integration tests, and a clean dependency installation has been verified.
- FastAPI, React, authentication, authorization, cloud storage, Azure SQL, and deployment remain Phase 2 plans.

## Documentation

- [Complete work plan](docs/UPDATED_Smart_Workspace_Manager_Complete_Work_Plan.pdf)
- [Project documentation](docs/UPDATED_Smart_Workspace_Manager_Project_Document.pdf)
- [Folder structure documentation](docs/Smart_Workspace_Manager_Folder_Structure_Documentation.pdf)
- [SQL and SQLAlchemy notes](docs/sql/sql_crud.md)
