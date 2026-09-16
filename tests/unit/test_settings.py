import pytest

from backend.config.settings import get_upload_size, get_valid_frontend_origins


def test_upload_size_reads_the_requested_environment_variable(monkeypatch):
    monkeypatch.setenv("TEST_ANALYSIS_SIZE_MB", "7")

    assert get_upload_size("TEST_ANALYSIS_SIZE_MB") == 7


def test_frontend_origins_accept_multiple_explicit_origins(monkeypatch):
    monkeypatch.setenv(
        "TEST_FRONTEND_ORIGINS",
        "http://localhost:5173/, https://workspace.azurestaticapps.net",
    )

    assert get_valid_frontend_origins("TEST_FRONTEND_ORIGINS") == [
        "http://localhost:5173",
        "https://workspace.azurestaticapps.net",
    ]


def test_frontend_origins_support_legacy_variable(monkeypatch):
    monkeypatch.delenv("TEST_FRONTEND_ORIGINS", raising=False)
    monkeypatch.setenv("TEST_FRONTEND_ORIGIN", "http://localhost:5173")

    assert get_valid_frontend_origins(
        "TEST_FRONTEND_ORIGINS",
        legacy_name="TEST_FRONTEND_ORIGIN",
    ) == ["http://localhost:5173"]


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "workspace.azurestaticapps.net",
        "https://user:password@workspace.example.com",
        "https://workspace.example.com/path",
    ],
)
def test_frontend_origins_reject_invalid_values(monkeypatch, value):
    monkeypatch.setenv("TEST_FRONTEND_ORIGINS", value)

    with pytest.raises(ValueError, match="invalid frontend origin"):
        get_valid_frontend_origins("TEST_FRONTEND_ORIGINS")
