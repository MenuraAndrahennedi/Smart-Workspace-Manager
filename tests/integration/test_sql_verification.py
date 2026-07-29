from scripts.sql_verifications.sql_crud_verification import run_crud_verification
from scripts.sql_verifications.sql_query_verification import run_query_verification


def test_orm_and_raw_sql_crud_operations_match(tmp_path) -> None:
    assert run_crud_verification(tmp_path) is True


def test_orm_and_raw_sql_query_outputs_match(tmp_path) -> None:
    assert run_query_verification(tmp_path) is True

    verification_directory = tmp_path / "SQL_verification"
    assert (verification_directory / "sql_query_verification.db").is_file()
    assert (verification_directory / "orm_query_verification.db").is_file()
