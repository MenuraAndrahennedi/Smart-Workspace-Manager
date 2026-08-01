# Smart Workspace Manager

Smart Workspace Manager is a local file-management and CSV data workspace built as a phased Python learning project. The current Phase 1 application uses Streamlit, SQLite, SQLAlchemy, pandas, Plotly, Matplotlib, and pytest.

The project is complete through **Day 11: charts and reports**. Day 12 will add a small, clearly scoped machine-learning demonstration. Phase 2 is planned to introduce FastAPI, React, authentication, authorization, Azure SQL, and deployment workflows.

## Features

### File management

- Validate and upload files up to the configured size limit.
- Generate safe, unique stored filenames.
- Organize files into managed category and date folders.
- Search and filter the file library by name, category, and status.
- Download or delete managed files.
- Restore staged files when a database deletion is rolled back.
- Record organization success and failure events.

### CSV analysis

- Analyze organized CSV files within configured row, column, and size limits.
- Preview rows, shape, column names, data types, and descriptive statistics.
- Count missing values and duplicate rows.
- Select columns and apply basic numeric or text filters.
- Record each analysis operation as an analysis job.

### CSV cleaning

- Remove duplicate rows using all or selected columns.
- Fill numeric missing values with the mean, median, or a constant.
- Fill text missing values with a chosen value.
- Remove rows containing remaining missing values.
- Preview the result without changing the original file.
- Export cleaned data as CSV and Excel files.

### Charts and reports

- Detect numeric, categorical, and pandas datetime columns.
- Offer valid histogram, bar, line, and scatter chart configurations.
- Validate chart columns, row limits, category limits, and aggregations.
- Add, preview, and remove up to the configured number of report charts.
- Generate a new HTML and PDF report without clearing the current chart list.
- Download the most recently generated HTML and PDF reports.
- Store separate report metadata records for both output files.

## Application Pages

| Page | Purpose |
| --- | --- |
| Dashboard | View file totals, category/status summaries, and recent files. |
| File Upload | Upload and organize a validated file. |
| File Library | Search, filter, download, and delete managed files. |
| CSV Analyzer | Inspect an organized CSV and record an analysis job. |
| CSV Cleaner | Preview cleaning operations and export CSV/Excel copies. |
| Generate Reports | Build charts and generate downloadable HTML/PDF reports. |

## Architecture

Streamlit pages handle user interaction and call reusable backend services. Services implement validation and workflows, repositories handle SQLAlchemy database access, and models define persisted metadata.

```text
Streamlit pages
      |
Backend services
      |
Repositories and SQLAlchemy models
      |
SQLite database + local data storage
```

The main database relationships are independent children of a file:

```text
FileRecord
|-- AnalysisJob
`-- Report
```

An analysis job records a CSV analysis operation. A report records one generated output file. Reports are not linked to analysis jobs. Deleting a file record cascades to its analysis jobs and reports, while the file service also removes associated files from storage.

## Project Structure

```text
backend/
  config/          Environment and application settings
  database/        Engine, models, sessions, and repositories
  services/        File, analysis, cleaning, chart, and report workflows
  utils/           Validation, paths, constants, and logging

frontend/
  streamlit_app.py Streamlit entry point
  pages/           Dashboard and workflow pages

scripts/
  init_db.py       Create missing database tables
  migrate_database.py
                   Back up and upgrade an existing SQLite database
  sql_verifications/
                   Isolated ORM and raw-SQL learning checks

tests/
  unit/            Reusable service and utility tests
  integration/     Database, storage, migration, and workflow tests

data/              Local runtime database and generated files
```

## Requirements

- Python 3.12
- A PowerShell terminal for the commands below
- Local filesystem access

## Local Setup

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install application and development dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Review `.env` before starting the application. The default configuration uses `data/smart_workspace.db` and local storage under `data/`.

## Configuration

| Variable | Purpose | Example |
| --- | --- | --- |
| `DATABASE_URL` | SQLite database URL | `sqlite:///./data/smart_workspace.db` |
| `STORAGE_PROVIDER` | Storage implementation | `local` |
| `DATA_ROOT` | Runtime data directory | `./data` |
| `MAX_UPLOAD_SIZE_MB` | Maximum uploaded file size | `10` |
| `MAX_FILENAME_ATTEMPTS` | Attempts to allocate a unique filename | `3` |
| `LOG_LEVEL` | Application logging level | `INFO` |
| `MAX_CSV_ROWS` | Maximum CSV rows loaded for analysis | `50000` |
| `MAX_CSV_COLUMNS` | Maximum CSV columns loaded for analysis | `200` |
| `MAX_CHART_ROWS` | Maximum raw rows in a chart | `5000` |
| `MAX_BAR_CATEGORIES` | Maximum categories in a bar chart | `30` |
| `MAX_REPORT_CHARTS` | Maximum charts in one report | `10` |

Keep `.env` and all real secrets out of Git. `SECRET_KEY` is reserved for a later authentication phase and is not currently used by Phase 1.

## Database Setup

For a new local database, create all missing tables:

```powershell
python scripts/init_db.py
```

For an existing database created with an older schema, run the migration once:

```powershell
python scripts/migrate_database.py
```

The migration creates a timestamped backup under `data/backups/`, upgrades the analysis/report relationships, validates database integrity, normalizes legacy automation statuses, and removes database records whose source files no longer exist.

## Run the Application

```powershell
streamlit run frontend/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). Streamlit automatically discovers the numbered page files under `frontend/pages/`.

## Run Tests

Run the complete suite:

```powershell
python -m pytest -q
```

Run only unit or integration tests:

```powershell
python -m pytest tests/unit -q
python -m pytest tests/integration -q
```

The current Day 11 baseline is **128 passing tests**.

## Runtime Data

Generated runtime content is stored below `data/`:

```text
data/
  backups/          Database migration backups
  processed/        Organized and cleaned files
  reports/html/     Interactive HTML reports
  reports/pdf/      Static PDF reports
  uploads/          Temporary uploaded files
  smart_workspace.db
```

Runtime databases, uploads, processed files, reports, models, and `.env` are ignored by Git.

## Known Limitations

- Storage and the database are local only.
- There is no authentication or per-user ownership yet.
- CSV date values are not automatically parsed; line charts recognize only columns already loaded as pandas datetime or numeric columns.
- HTML reports load Plotly JavaScript from a CDN and need internet access for interactive charts.
- PDF charts are static.
- CSV analysis and charting intentionally enforce configured limits.
- The machine-learning demo, API, React frontend, and Azure deployment belong to later work-plan days.

## Additional Documentation

- [SQL and SQLAlchemy notes](docs/sql/sql_crud.md)
- [Complete work plan](docs/UPDATED_Smart_Workspace_Manager_Complete_Work_Plan.pdf)
- [Project documentation](docs/UPDATED_Smart_Workspace_Manager_Project_Document.pdf)
- [Folder structure documentation](docs/Smart_Workspace_Manager_Folder_Structure_Documentation.pdf)
