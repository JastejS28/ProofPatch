from uuid import uuid4

from app.repository import workspace


def test_cleanup_run_workspace(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        workspace,
        "get_workspace_root",
        lambda: tmp_path,
    )

    run_id = uuid4()

    run_workspace = (
        tmp_path
        / str(run_id)
    )

    run_workspace.mkdir()

    test_file = (
        run_workspace
        / "example.py"
    )

    test_file.write_text(
        "print('hello')",
        encoding="utf-8",
    )

    assert (
        run_workspace.exists()
        is True
    )

    cleaned = (
        workspace
        .cleanup_run_workspace(
            run_id
        )
    )

    assert cleaned is True

    assert (
        run_workspace.exists()
        is False
    )


def test_cleanup_missing_workspace(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        workspace,
        "get_workspace_root",
        lambda: tmp_path,
    )

    run_id = uuid4()

    cleaned = (
        workspace
        .cleanup_run_workspace(
            run_id
        )
    )

    assert cleaned is False