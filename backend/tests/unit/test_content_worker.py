from unittest.mock import MagicMock

from app.workers.content import publish_due_task


def test_publish_due_sets_published_string_status(monkeypatch):
    row = MagicMock()
    db = MagicMock()
    db.scalars.return_value.all.return_value = [row]
    monkeypatch.setattr("app.workers.content.SessionLocal", lambda: db)

    count = publish_due_task.run()

    assert count == 1
    assert row.status == "published"
    assert row.published_at is not None


def test_generate_content_task_is_registered():
    from app.workers.content import generate_content_task

    assert generate_content_task.name == "content.generate"
