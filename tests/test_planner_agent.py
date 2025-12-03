import datetime

import pytest

from config import load_settings
import planner_agent
from planner_agent import PlannerAgent


@pytest.fixture
def env_vars(monkeypatch):
    monkeypatch.setenv("CLIENT_ID", "dummy-client-id")
    monkeypatch.setenv("CLIENT_SECRET", "dummy-secret")
    monkeypatch.setenv("TENANT_ID", "dummy-tenant")
    monkeypatch.setenv("USER_EMAIL", "user@example.com")
    monkeypatch.setenv("NOTIFICATION_EMAIL", "user@example.com")
    monkeypatch.setenv("APP_SCOPE", "https://graph.microsoft.com/.default")
    monkeypatch.setenv(
        "DELEGATED_SCOPES",
        "User.Read Chat.ReadWrite Chat.ReadWrite.All Chat.Create Chat.ReadBasic.All Mail.Send",
    )
    monkeypatch.setenv("MAIL_PLAN_TITLE", "邮箱检查")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("MAX_DELETE_PER_RUN", "500")
    monkeypatch.setenv("CLEANUP_TIME_BUDGET_SECONDS", "10")
    monkeypatch.setenv("AUTH_MODE", "app")
    # Stub GraphClient to avoid real network calls during PlannerAgent init.
    class _DummyGraphClient:
        def __init__(self, *_args, **_kwargs):
            pass
    monkeypatch.setattr(planner_agent, "GraphClient", _DummyGraphClient)
    yield


@pytest.fixture
def agent(env_vars):
    settings = load_settings()
    return PlannerAgent(settings)


def test_cleanup_keepalive_duplicates_keeps_latest(monkeypatch, agent):
    plan_context = {
        "plan_id": "plan-1",
        "plan": "邮箱检查",
        "group": "All Company",
        "group_id": "group-1",
    }
    buckets = [{"id": "bucket-1", "name": "待办事项"}]
    tasks = [
        {
            "id": "old",
            "title": "old task",
            "createdDateTime": "2024-11-01T10:00:00Z",
            "@odata.etag": "etag-old",
        },
        {
            "id": "new",
            "title": "new task",
            "createdDateTime": "2024-11-02T10:00:00Z",
            "@odata.etag": "etag-new",
        },
    ]
    deleted = []

    monkeypatch.setattr(agent, "list_buckets", lambda plan_id: buckets)
    monkeypatch.setattr(agent, "list_tasks", lambda bucket_id: tasks)
    monkeypatch.setattr(agent, "delete_task", lambda task_id, etag: deleted.append(task_id))

    removed = agent.cleanup_keepalive_duplicates(
        plan_title="邮箱检查", keep_latest=1, plan_context=plan_context
    )

    assert deleted == ["old"]
    assert removed and removed[0]["task_id"] == "old"


def test_cleanup_previous_week_tasks_respects_age(monkeypatch, agent):
    now = datetime.datetime.now(datetime.timezone.utc)
    week_ago = now - datetime.timedelta(days=8)
    recent = now - datetime.timedelta(days=1)

    plan_context = {
        "plan_id": "plan-1",
        "plan": "邮箱检查",
        "group": "All Company",
        "group_id": "group-1",
    }
    buckets = [{"id": "bucket-1", "name": "待办事项"}]
    tasks = [
        {
            "id": "old",
            "title": "old task",
            "createdDateTime": week_ago.isoformat(),
            "@odata.etag": "etag-old",
        },
        {
            "id": "recent",
            "title": "recent task",
            "createdDateTime": recent.isoformat(),
            "@odata.etag": "etag-recent",
        },
    ]
    deleted = []

    monkeypatch.setattr(agent, "list_buckets", lambda plan_id: buckets)
    monkeypatch.setattr(agent, "list_tasks", lambda bucket_id: tasks)
    monkeypatch.setattr(agent, "delete_task", lambda task_id, etag: deleted.append(task_id))

    removed = agent.cleanup_previous_week_tasks(
        plan_title="邮箱检查", plan_context=plan_context
    )

    assert deleted == ["old"]
    assert removed and removed[0]["task_id"] == "old"
