import ast
from pathlib import Path


def test_streamlit_pages_do_not_bypass_service_layer():
    frontend_directory = Path(__file__).resolve().parents[2] / "frontend"
    frontend_files = [
        frontend_directory / "streamlit_app.py",
        frontend_directory / "ui_helpers.py",
        *frontend_directory.joinpath("pages").glob("*.py"),
    ]
    forbidden_code = (
        "backend.database.repositories",
        ".read_bytes(",
        ".select_dtypes(",
        "sys.path.append(",
    )

    violations = []
    for frontend_path in frontend_files:
        page_code = frontend_path.read_text(encoding="utf-8")
        for forbidden_text in forbidden_code:
            if forbidden_text in page_code:
                violations.append(f"{frontend_path.name}: {forbidden_text}")

    assert violations == []


def test_unexpected_streamlit_errors_are_logged():
    frontend_directory = Path(__file__).resolve().parents[2] / "frontend"
    frontend_files = [
        frontend_directory / "ui_helpers.py",
        *frontend_directory.joinpath("pages").glob("*.py"),
    ]
    violations = []

    for frontend_path in frontend_files:
        tree = ast.parse(frontend_path.read_text(encoding="utf-8"))
        for handler in (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
        ):
            logs_exception = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id.endswith("logger")
                and node.func.attr == "exception"
                for statement in handler.body
                for node in ast.walk(statement)
            )
            if not logs_exception:
                violations.append(f"{frontend_path.name}:{handler.lineno}")

    assert violations == []
