from scripts.sql_verification import run_crud_verification


def test_orm_and_raw_sql_crud_operations_match(tmp_path) -> None:
    assert run_crud_verification(tmp_path) is True