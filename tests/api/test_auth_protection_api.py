import pytest


PROTECTED_REQUESTS = [
    ("get", "/api/files/", {}),
    ("get", "/api/files/1", {}),
    ("delete", "/api/files/1", {}),
    (
        "post",
        "/api/files/upload",
        {"files": {"file": ("sample.csv", b"value\n1\n", "text/csv")}},
    ),
    ("get", "/api/files/1/download", {}),
    ("get", "/api/dashboard/", {}),
    ("get", "/api/analyzer/analyzable_files", {}),
    ("post", "/api/analyzer/analysis/1", {}),
    ("get", "/api/analyzer/analysis_job/1", {}),
    (
        "get",
        "/api/analyzer/files/1/filter",
        {"params": {"selected_columns": "value"}},
    ),
    ("post", "/api/cleaning/1", {"json": {}}),
    (
        "post",
        "/api/cleaning/save_cleaning_results/1",
        {"json": [{"value": 1}]},
    ),
    ("post", "/api/reports/1", {"json": {"chart_configurations": []}}),
    ("get", "/api/reports/files/1", {}),
    ("get", "/api/reports/1/download", {}),
    ("get", "/api/reports/1", {}),
    ("get", "/api/xlsx/files", {}),
    ("get", "/api/xlsx/files/1/sheets", {}),
    (
        "post",
        "/api/xlsx/files/1/convert",
        {"json": {"sheet_name": "Sheet1"}},
    ),
]


@pytest.mark.parametrize(("method", "url", "kwargs"), PROTECTED_REQUESTS)
def test_protected_routes_require_authentication(
    unauthenticated_client,
    method,
    url,
    kwargs,
):
    response = unauthenticated_client.request(method, url, **kwargs)

    assert response.status_code == 401
