import logging
from types import SimpleNamespace

import pytest

from backend.database import db
from backend.database.db import SESSION_FINALIZED_KEY
from frontend import ui_helpers


@pytest.mark.parametrize(
    ("selected_options", "previous_options", "expected"),
    [
        (["All", "Images"], ["All"], ["Images"]),
        (["Images", "Documents"], ["Images"], ["Images", "Documents"]),
        (["Images", "All"], ["Images"], ["All"]),
        ([], ["All"], ["All"]),
        (["All"], ["All"], ["All"]),
    ],
)
def test_normalize_exclusive_all_selection(
    selected_options,
    previous_options,
    expected,
):
    assert ui_helpers.normalize_exclusive_all_selection(
        selected_options,
        previous_options,
    ) == expected


def test_commit_session_changes_marks_successful_session_finalized():
    session = SimpleNamespace(
        commit_calls=0,
        info={},
        commit=lambda: setattr(session, "commit_calls", session.commit_calls + 1),
    )

    result = ui_helpers.commit_session_changes(
        session,
        logging.getLogger("test"),
        "Could not save changes.",
    )

    assert result is True
    assert session.commit_calls == 1
    assert session.info[SESSION_FINALIZED_KEY] is True


def test_commit_session_changes_rolls_back_and_shows_safe_error(monkeypatch):
    calls = {"rollback": 0, "error": []}

    def fail_commit():
        raise RuntimeError("private database details")

    session = SimpleNamespace(
        info={},
        commit=fail_commit,
        rollback=lambda: calls.update(rollback=calls["rollback"] + 1),
    )
    logger = SimpleNamespace(exception=lambda *args: None)
    monkeypatch.setattr(
        ui_helpers.st,
        "error",
        lambda message: calls["error"].append(message),
    )

    result = ui_helpers.commit_session_changes(
        session,
        logger,
        "Could not save changes.",
    )

    assert result is False
    assert calls["rollback"] == 1
    assert calls["error"] == ["Could not save changes."]
    assert "private database details" not in calls["error"][0]
    assert session.info[SESSION_FINALIZED_KEY] is True


def test_db_context_does_not_commit_an_explicitly_finalized_session(monkeypatch):
    calls = {"commit": 0, "close": 0}
    session = SimpleNamespace(
        info={},
        commit=lambda: calls.update(commit=calls["commit"] + 1),
        rollback=lambda: None,
        close=lambda: calls.update(close=calls["close"] + 1),
    )
    monkeypatch.setattr(db, "SessionLocal", lambda: session)

    with db.get_db_session() as active_session:
        active_session.info[SESSION_FINALIZED_KEY] = True

    assert calls == {"commit": 0, "close": 1}
