# SQL and SQLAlchemy Verification

## 1. Purpose

The Smart Workspace Manager uses SQLAlchemy ORM in the real
application. Raw SQL is used separately to understand and verify
the equivalent database operations.

## 2. Verification Databases

- `tmp_path/SQL_verification/orm_verification.db`
- `tmp_path/SQL_verification/sql_verification.db`

The real application database is not modified during verification.

## 3. CREATE TABLE Equivalent

The `FileRecord` SQLAlchemy model represents the `files` table.

Important mappings:

- `primary_key=True` → `PRIMARY KEY`
- `autoincrement=True` → automatically generated ID
- `nullable=False` → `NOT NULL`
- `unique=True` → `UNIQUE`

## 4. INSERT

### Raw SQL

```sql
INSERT INTO files (
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

### SQLAlchemy Equivalent

`create_file()`

### Verification

The same file metadata is inserted into both verification databases.
The saved records are read, normalised, and compared.

## 5. SELECT by ID

### Raw SQL

```sql
SELECT *
FROM files
WHERE id = :file_id;
```

### SQLAlchemy Equivalent

`read_file_by_id()`

### Verification

The raw SQL query and repository function both return one file
record matching the primary-key value, or no record when the ID
does not exist.

## 6. SELECT All

### Raw SQL

```sql
SELECT *
FROM files
ORDER BY created_at DESC, id DESC;
```

### SQLAlchemy Equivalent

`get_all_files()`

### Verification

Both approaches return file records ordered from newest to oldest.
The descending ID provides deterministic ordering when records share
the same `created_at` timestamp.

## 7. UPDATE

### Raw SQL

```sql
UPDATE files
SET
    stored_name = :stored_name,
    storage_path = :storage_path,
    category = :category,
    status = :status,
    updated_at = :updated_at
WHERE id = :file_id;
```

### SQLAlchemy Equivalent

`update_file()`

### Verification

The verification updates the same fields through raw SQL and
through the repository function, then normalises the results and
confirms both records contain the same values.

## 8. DELETE

### Raw SQL

```sql
DELETE FROM files
WHERE id = :file_id;
```

### SQLAlchemy Equivalent

`delete_file()`

### Verification

Both approaches delete by primary key. After deletion,
`read_file_by_id()` and the raw SQL select-by-ID query should both
return no record.

## 9. Parameterised Queries

Named placeholders such as `:file_id` receive values separately
through `session.execute()`. This avoids unsafe string-built queries.

## 10. Transactions

Raw SQL is executed immediately inside the current transaction.
`commit()` permanently saves changes, while `rollback()` cancels them.

## 11. Why the Application Uses SQLAlchemy

SQLAlchemy provides:

- reusable ORM models
- database-independent connection handling
- sessions and transactions
- easier repository functions
- future SQLite-to-Azure-SQL support

Raw SQL remains useful for understanding queries, debugging,
verification, joins, filtering, and aggregation.
