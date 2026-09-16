from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

from sqlalchemy import Connection, bindparam, create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from backend.database.db import Base, enable_sqlite_foreign_keys
from backend.database.models import FileRecord
from backend.database.repositories import count_files, get_all_files, get_file_summary, get_recent_files, group_files_by_category, query_files

VERIFICATION_USER_ID = 1


def escape_like_pattern(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def seed_query_data(connection: Connection) -> None:
    connection.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash, created_at)
            VALUES (:id, :email, :password_hash, CURRENT_TIMESTAMP)
            """
        ),
        {
            "id": VERIFICATION_USER_ID,
            "email": "query-verification@example.com",
            "password_hash": "verification-only",
        },
    )

    sample_files = [
        {
            "original_name": "sales_2026.csv",
            "stored_name": "test_sales_2026.csv",
            "extension": "csv",
            "category": "spreadsheets",
            "size_bytes": 1_200,
            "storage_path": (
                "data/processed/spreadsheets/2026/07/"
                "test_sales_2026.csv"
            ),
            "status": "organized",
        },
        {
            "original_name": "student_report.xlsx",
            "stored_name": "test_student_report.xlsx",
            "extension": "xlsx",
            "category": "spreadsheets",
            "size_bytes": 2_500,
            "storage_path": (
                "data/processed/spreadsheets/2026/07/"
                "test_student_report.xlsx"
            ),
            "status": "organized",
        },
        {
            "original_name": "research_report.pdf",
            "stored_name": "test_research_report.pdf",
            "extension": "pdf",
            "category": "pdf",
            "size_bytes": 5_000,
            "storage_path": (
                "data/processed/pdf/2026/07/"
                "test_research_report.pdf"
            ),
            "status": "organized",
        },
        {
            "original_name": "profile_photo.png",
            "stored_name": "test_profile_photo.png",
            "extension": "png",
            "category": "images",
            "size_bytes": 3_200,
            "storage_path": (
                "data/processed/images/2026/07/"
                "test_profile_photo.png"
            ),
            "status": "organized",
        },
        {
            "original_name": "notes.txt",
            "stored_name": "test_notes.txt",
            "extension": "txt",
            "category": "documents",
            "size_bytes": 600,
            "storage_path": "data/uploads/test_notes.txt",
            "status": "uploaded",
        },
        {
            "original_name": "backup.zip",
            "stored_name": "test_backup.zip",
            "extension": "zip",
            "category": "others",
            "size_bytes": 8_000,
            "storage_path": "data/uploads/test_backup.zip",
            "status": "failed",
        },
    ]

    insert_query = text(
        """
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
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """
    )

    for sample_file in sample_files:
        sample_file["user_id"] = VERIFICATION_USER_ID

    # Passing a list of dictionaries performs parameterized executemany
    connection.execute(insert_query, sample_files)


def list_files_sql(connection: Connection, user_id: int) -> list[dict]:
    query = text("""
        SELECT*
        FROM files
        WHERE user_id = :user_id
        ORDER BY created_at DESC, id DESC;
    """)

    results: list = connection.execute(
        query,
        {"user_id": user_id},
    ).mappings().all()

    return [dict(row) for row in results]


def search_files_sql(
    connection: Connection,
    user_id: int,
    search_term: str,
) -> list[dict]:
    search_pattern = f"%{escape_like_pattern(search_term.strip())}%"
    query = text("""
        SELECT *
        FROM files
        WHERE user_id = :user_id
          AND (
            LOWER(original_name) LIKE LOWER(:search_pattern) ESCAPE '\\'
            OR LOWER(stored_name) LIKE LOWER(:search_pattern) ESCAPE '\\'
          )
        ORDER BY updated_at DESC, id DESC;
    """)

    results: list = connection.execute(
        query,
        {"user_id": user_id, "search_pattern": search_pattern},
    ).mappings().all()

    return [dict(row) for row in results]


def filter_files_by_category_sql(
    connection: Connection,
    user_id: int,
    selected_category: str,
) -> list[dict]:

    query = text("""
        SELECT *
        FROM files
        WHERE user_id = :user_id AND category = :selected_category
        ORDER BY updated_at DESC, id DESC;
    """)

    results = connection.execute(
        query,
        {"user_id": user_id, "selected_category": selected_category},
    ).mappings().all()

    return [dict(row) for row in results]

def filter_files_by_status_sql(
    connection: Connection,
    user_id: int,
    selected_status: str,
) -> list[dict]:

    query = text("""
        SELECT *
        FROM files
        WHERE user_id = :user_id AND status = :selected_status
        ORDER BY updated_at DESC, id DESC;
    """)

    results = connection.execute(
        query,
        {"user_id": user_id, "selected_status": selected_status},
    ).mappings().all()

    return [dict(row) for row in results]


def query_files_combined_sql(
    connection: Connection,
    user_id: int,
    search_term: str | None = None,
    category: str | list[str] | None = None,
    status: str | list[str] | None = None,
) -> list[dict]:
    cleaned_search_term = search_term.strip() if search_term else None
    category_values = normalize_filter_values(category)
    status_values = normalize_filter_values(status)
    where_clauses: list[str] = ["user_id = :user_id"]
    parameters: dict = {"user_id": user_id}

    if cleaned_search_term:
        where_clauses.append(
            """
            (
                LOWER(original_name) LIKE LOWER(:search_pattern) ESCAPE '\\'
                OR LOWER(stored_name) LIKE LOWER(:search_pattern) ESCAPE '\\'
            )
            """
        )
        parameters["search_pattern"] = (
            f"%{escape_like_pattern(cleaned_search_term)}%"
        )

    if category_values:
        where_clauses.append("category IN :category_values")
        parameters["category_values"] = category_values

    if status_values:
        where_clauses.append("status IN :status_values")
        parameters["status_values"] = status_values

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + "\n        AND ".join(where_clauses)

    query = text(f"""
        SELECT *
        FROM files
        {where_sql}
        ORDER BY updated_at DESC, id DESC;
    """)

    if category_values:
        query = query.bindparams(bindparam("category_values", expanding=True))

    if status_values:
        query = query.bindparams(bindparam("status_values", expanding=True))

    rows = connection.execute(query, parameters).mappings().all()

    return [dict(row) for row in rows]


def count_files_sql(connection: Connection, user_id: int) -> int:

    query = text("""
        SELECT COUNT(*) AS total_files
        FROM files
        WHERE user_id = :user_id;
    """)

    result = connection.execute(query, {"user_id": user_id}).scalar_one()

    return result


def get_file_summary_sql(connection: Connection, user_id: int) -> dict:

    query = text("""
        SELECT
            COUNT(*) AS total_files,
            COALESCE(SUM(size_bytes), 0) AS total_size_bytes
        FROM files
        WHERE user_id = :user_id;
    """)

    result = connection.execute(
        query,
        {"user_id": user_id},
    ).mappings().one()

    return dict(result)

def group_files_by_category_sql(
    connection: Connection,
    user_id: int,
) -> list[dict]:

    query = text("""
        SELECT
            category,
            COUNT(*) AS file_count,
            COALESCE(SUM(size_bytes), 0) AS total_size_bytes
        FROM files
        WHERE user_id = :user_id
        GROUP BY category
        ORDER BY file_count DESC, category ASC;
    """)

    results = connection.execute(
        query,
        {"user_id": user_id},
    ).mappings().all()

    return [dict(row) for row in results]


def get_recent_files_sql(
    connection: Connection,
    user_id: int,
    limit: int = 5,
) -> list[dict]:

    query = text("""
        SELECT *
        FROM files
        WHERE user_id = :user_id
        ORDER BY updated_at DESC, id DESC
        LIMIT :limit_value;
    """)

    results = connection.execute(
        query,
        {"user_id": user_id, "limit_value": limit},
    ).mappings().all()

    return [dict(row) for row in results]


def normalize_sql_file_rows(
    rows: list[dict],
) -> list[dict]:
    return [
        {
            "id": row["id"],
            "user_id": row["user_id"],
            "original_name": row["original_name"],
            "stored_name": row["stored_name"],
            "extension": row["extension"],
            "category": row["category"],
            "size_bytes": row["size_bytes"],
            "storage_path": row["storage_path"],
            "status": row["status"],
        }
        for row in rows
    ]


def normalize_filter_values(
    values: str | list[str] | None,
) -> list[str]:
    if values is None:
        return []

    if isinstance(values, str):
        values = [values]

    return [
        value.strip()
        for value in values
        if value and value.strip()
    ]


def normalize_orm_file_records(
    records: list[FileRecord],
) -> list[dict]:
    return [
        {
            "id": record.id,
            "user_id": record.user_id,
            "original_name": record.original_name,
            "stored_name": record.stored_name,
            "extension": record.extension,
            "category": record.category,
            "size_bytes": record.size_bytes,
            "storage_path": record.storage_path,
            "status": record.status,
        }
        for record in records
    ]



def compare_sql_and_orm_outputs(
    connection: Connection,
    session: Session,
) -> None:
    # 1. List all files
    raw_files = normalize_sql_file_rows(
        list_files_sql(connection, VERIFICATION_USER_ID)
    )

    orm_files = normalize_orm_file_records(
        get_all_files(session, VERIFICATION_USER_ID)
    )

    assert raw_files == orm_files
    print("PASS: List all files")

    # 2. Search by term
    raw_search = normalize_sql_file_rows(
        search_files_sql(
            connection=connection,
            user_id=VERIFICATION_USER_ID,
            search_term="report",
        )
    )

    orm_search = normalize_orm_file_records(
        query_files(
            session=session,
            user_id=VERIFICATION_USER_ID,
            search_term="report",
        )
    )

    assert raw_search == orm_search
    print("PASS: Search by term")

    for literal_search_term in ("%", "_"):
        raw_literal_search = normalize_sql_file_rows(
            search_files_sql(
                connection=connection,
                user_id=VERIFICATION_USER_ID,
                search_term=literal_search_term,
            )
        )
        orm_literal_search = normalize_orm_file_records(
            query_files(
                session=session,
                user_id=VERIFICATION_USER_ID,
                search_term=literal_search_term,
            )
        )
        assert raw_literal_search == orm_literal_search
    print("PASS: Search treats wildcard characters literally")

    # 3. Filter by category
    raw_category = normalize_sql_file_rows(
        filter_files_by_category_sql(
            connection=connection,
            user_id=VERIFICATION_USER_ID,
            selected_category="spreadsheets",
        )
    )

    orm_category = normalize_orm_file_records(
        query_files(
            session=session,
            user_id=VERIFICATION_USER_ID,
            category="spreadsheets",
        )
    )

    assert raw_category == orm_category
    print("PASS: Filter by category")

    # 4. Filter by status
    raw_status = normalize_sql_file_rows(
        filter_files_by_status_sql(
            connection=connection,
            user_id=VERIFICATION_USER_ID,
            selected_status="organized",
        )
    )

    orm_status = normalize_orm_file_records(
        query_files(
            session=session,
            user_id=VERIFICATION_USER_ID,
            status="organized",
        )
    )

    assert raw_status == orm_status
    print("PASS: Filter by status")

    # 5. Combined search and filters
    raw_combined = normalize_sql_file_rows(
        query_files_combined_sql(
            connection=connection,
            user_id=VERIFICATION_USER_ID,
            search_term="report",
            category="pdf",
            status="organized",
        )
    )

    orm_combined = normalize_orm_file_records(
        query_files(
            session=session,
            user_id=VERIFICATION_USER_ID,
            search_term="report",
            category="pdf",
            status="organized",
        )
    )

    assert raw_combined == orm_combined
    print("PASS: Combined search and filters")

    # 6. Combined multiple category and status filters
    raw_multi_filter = normalize_sql_file_rows(
        query_files_combined_sql(
            connection=connection,
            user_id=VERIFICATION_USER_ID,
            category=["spreadsheets", "pdf"],
            status=["organized"],
        )
    )

    orm_multi_filter = normalize_orm_file_records(
        query_files(
            session=session,
            user_id=VERIFICATION_USER_ID,
            category=["spreadsheets", "pdf"],
            status=["organized"],
        )
    )

    assert raw_multi_filter == orm_multi_filter
    print("PASS: Combined multiple category and status filters")

    # 7. Count files
    raw_count = count_files_sql(connection, VERIFICATION_USER_ID)
    orm_count = count_files(session, VERIFICATION_USER_ID)

    assert raw_count == orm_count
    print("PASS: File count")

    # 8. File summary
    raw_summary = get_file_summary_sql(connection, VERIFICATION_USER_ID)
    orm_summary = get_file_summary(session, VERIFICATION_USER_ID)

    assert raw_summary == orm_summary
    print("PASS: File summary")

    # 9. Group by category
    raw_grouped = group_files_by_category_sql(connection, VERIFICATION_USER_ID)
    orm_grouped = group_files_by_category(session, VERIFICATION_USER_ID)

    assert raw_grouped == orm_grouped
    print("PASS: Group by category")

    # 10. Recent files
    raw_recent = normalize_sql_file_rows(
        get_recent_files_sql(
            connection=connection,
            user_id=VERIFICATION_USER_ID,
            limit=3,
        )
    )

    orm_recent = normalize_orm_file_records(
        get_recent_files(
            session=session,
            user_id=VERIFICATION_USER_ID,
            limit=3,
        )
    )

    assert raw_recent == orm_recent
    print("PASS: Recent files")







def run_query_verification(db_path: Path | str | None = None) -> bool:
    if db_path is None:
        verification_directory = PROJECT_ROOT / "data" / "SQL_verification"
    else:
        verification_directory = Path(db_path) / "SQL_verification"

    verification_directory.mkdir(parents=True, exist_ok=True)

    sql_database_path = verification_directory / "sql_query_verification.db"
    orm_database_path = verification_directory / "orm_query_verification.db"

    def ensure_verification_database(
        database_path: Path,
        expected_filename: str,
    ) -> Path:
        resolved_path = database_path.resolve()
        if (
            resolved_path.parent.name.lower() != "sql_verification"
            or resolved_path.name != expected_filename
        ):
            raise ValueError("Refusing to reset a non-verification database.")
        return resolved_path

    sql_database_path = ensure_verification_database(
        sql_database_path,
        "sql_query_verification.db",
    )
    orm_database_path = ensure_verification_database(
        orm_database_path,
        "orm_query_verification.db",
    )

    sql_verification_engine = create_engine(
        f"sqlite:///{sql_database_path}",
        echo=True,
    )
    enable_sqlite_foreign_keys(sql_verification_engine)
    orm_verification_engine = create_engine(
        f"sqlite:///{orm_database_path}",
        echo=True,
    )
    enable_sqlite_foreign_keys(orm_verification_engine)

    Base.metadata.drop_all(bind=sql_verification_engine)
    Base.metadata.drop_all(bind=orm_verification_engine)
    Base.metadata.create_all(bind=sql_verification_engine)
    Base.metadata.create_all(bind=orm_verification_engine)

    # Seed both dedicated databases with identical records.
    with sql_verification_engine.begin() as connection:
        seed_query_data(connection)
    with orm_verification_engine.begin() as connection:
        seed_query_data(connection)

    VerificationSessionLocal = sessionmaker(
        bind=orm_verification_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    try:
        # Compare raw SQL results with ORM results from the matching database.
        with sql_verification_engine.connect() as connection:
            with VerificationSessionLocal() as session:
                compare_sql_and_orm_outputs(
                    connection=connection,
                    session=session,
                )
    except Exception as error:
        print(f"\nQuery verification error: {error}")
        return False
    finally:
        sql_verification_engine.dispose()
        orm_verification_engine.dispose()

    print("\nAll raw SQL and SQLAlchemy query outputs match.")
    return True


if __name__ == "__main__":
    run_query_verification()
