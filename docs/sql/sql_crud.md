# SQL and SQLAlchemy Notes

## Purpose

Smart Workspace Manager uses SQLAlchemy ORM in the application. Raw SQL examples are kept as a learning reference for the equivalent database operations. Verification scripts use isolated temporary databases and do not modify the application database.

## Core Tables and Relationships

The Phase 2 metadata tables are:

- `users`: login identity and Argon2 password hash.

- `files`: one record for each managed source file.
- `analysis_jobs`: one record for each recorded CSV analysis operation.
- `reports`: one record for each generated HTML or PDF report file.
- `automation_logs`: persistent organization and workflow events.
- `settings`: non-secret application settings.

Files belong to users. Analysis jobs and reports belong directly to a file:

```text
users
`-- files.user_id
    |-- analysis_jobs.file_id
    `-- reports.file_id
```

There is no foreign-key relationship between `analysis_jobs` and `reports`.

Conceptual table definitions for the two file-owned records are:

```sql
CREATE TABLE analysis_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    status VARCHAR(30) NOT NULL,
    requested_options TEXT,
    summary TEXT,
    error_message TEXT,
    created_at DATETIME NOT NULL,
    completed_at DATETIME,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    report_type VARCHAR(30) NOT NULL,
    storage_path VARCHAR(500) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files (id) ON DELETE CASCADE
);
```

SQLite foreign-key enforcement is enabled for every application database connection.

Azure SQL uses the equivalent identity, foreign-key, index, and cascade
semantics through Alembic migrations.

## File CRUD

### Insert a File

```sql
INSERT INTO files (
    user_id,
    original_name,
    stored_name,
    extension,
    category,
    size_bytes,
    storage_path,
    status,
    created_at,
    updated_at
)
VALUES (
    :user_id,
    :original_name,
    :stored_name,
    :extension,
    :category,
    :size_bytes,
    :storage_path,
    :status,
    :created_at,
    :updated_at
);
```

SQLAlchemy repository equivalent: `create_file()`.

### Select a File by ID

```sql
SELECT *
FROM files
WHERE id = :file_id
  AND user_id = :user_id;
```

SQLAlchemy repository equivalent: `get_file_by_id()`.

### Select All Files

```sql
SELECT *
FROM files
WHERE user_id = :user_id
ORDER BY created_at DESC, id DESC;
```

SQLAlchemy repository equivalent: `get_all_files()`.

### Update a File

```sql
UPDATE files
SET
    stored_name = :stored_name,
    storage_path = :storage_path,
    category = :category,
    status = :status,
    updated_at = :updated_at
WHERE id = :file_id
  AND user_id = :user_id;
```

SQLAlchemy repository equivalents: `update_file()` and `update_file_location()`.

### Delete a File

```sql
DELETE FROM files
WHERE id = :file_id
  AND user_id = :user_id;
```

SQLAlchemy repository equivalent: `delete_file()`.

Deleting a file record cascades to its `analysis_jobs` and `reports` rows. The higher-level `delete_actual_file()` service also stages and removes the source and report files from storage, restoring them if the database transaction rolls back.

## File Search and Filtering

The repository builds a parameterized SQLAlchemy query with optional search, category, and status conditions. A simplified raw SQL equivalent is:

```sql
SELECT *
FROM files
WHERE (
    :search_term = ''
    OR original_name LIKE :search_pattern ESCAPE '\'
    OR stored_name LIKE :search_pattern ESCAPE '\'
)
AND user_id = :user_id
AND category IN (:categories)
AND status IN (:statuses)
ORDER BY updated_at DESC, id DESC;
```

SQLAlchemy repository equivalent: `query_files()`.

Actual `IN` parameters are expanded safely by SQLAlchemy rather than inserted into a query string.

## Dashboard Aggregations

### Count Files and Total Size

```sql
SELECT
    COUNT(id) AS total_files,
    COALESCE(SUM(size_bytes), 0) AS total_size_bytes
FROM files
WHERE user_id = :user_id;
```

SQLAlchemy repository equivalents: `count_files()` and `get_file_summary()`.

### Group by Category

```sql
SELECT
    category,
    COUNT(id) AS file_count,
    COALESCE(SUM(size_bytes), 0) AS total_size_bytes
FROM files
WHERE user_id = :user_id
GROUP BY category
ORDER BY file_count DESC, category ASC;
```

SQLAlchemy repository equivalent: `group_files_by_category()`.

### Group by Status

```sql
SELECT
    status,
    COUNT(id) AS file_count
FROM files
WHERE user_id = :user_id
GROUP BY status
ORDER BY status ASC;
```

SQLAlchemy repository equivalent: `group_files_by_status()`.

## Analysis Job Metadata

Create an analysis job before analysis and update it when the operation completes or fails:

```sql
INSERT INTO analysis_jobs (
    file_id,
    status,
    requested_options,
    created_at
)
VALUES (
    :file_id,
    'running',
    :requested_options,
    :created_at
);

UPDATE analysis_jobs
SET
    status = :status,
    summary = :summary,
    error_message = :error_message,
    completed_at = :completed_at
WHERE id = :job_id;
```

SQLAlchemy repository equivalents: `create_analysis_job()` and `update_analysis_job()`.

## Report Metadata

HTML and PDF outputs receive separate records. Each record points to the same source file but has its own type, path, and status:

```sql
INSERT INTO reports (
    file_id,
    report_type,
    storage_path,
    status,
    created_at
)
VALUES (
    :file_id,
    :report_type,
    :storage_path,
    'pending',
    :created_at
);

UPDATE reports
SET
    status = :status,
    storage_path = :storage_path
WHERE id = :report_id;
```

SQLAlchemy repository equivalents: `create_report()` and `update_report()`.

## Parameterized Queries

Placeholders such as `:file_id` receive values separately from SQL text. This prevents user input from changing the structure of the SQL statement. SQLAlchemy expressions and repository functions provide the same separation in application code.

## Transactions

Database operations run inside a SQLAlchemy session transaction:

- `flush()` sends pending SQL while keeping the transaction open.
- `commit()` permanently saves the transaction.
- `rollback()` cancels database changes.

Storage-changing services coordinate filesystem staging with the database transaction so failed deletions can restore moved files.

For obsolete metadata, deletion may remove the owned database row when the
physical file is already missing or its historical path is outside the current
managed root. No external path is touched.

## Ownership Join

A report is authorized through its source file owner:

```sql
SELECT r.*
FROM reports AS r
JOIN files AS f ON f.id = r.file_id
WHERE r.id = :report_id
  AND f.user_id = :user_id;
```

SQLAlchemy equivalent: `get_report_by_id()` loads the report and checks
`report.file.user_id`. Analysis-job authorization follows the same relationship.

## Verification Scripts

The scripts below compare selected raw SQL and SQLAlchemy results using isolated databases:

```powershell
python scripts/sql_verifications/sql_crud_verification.py
python scripts/sql_verifications/sql_query_verification.py
```

Automated integration coverage is located in `tests/integration/test_sql_verification.py`.
