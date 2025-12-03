import os
from dataclasses import dataclass
from typing import List, Optional

# Load .env automatically if present to simplify local runs.
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # If python-dotenv is not installed, just continue with existing env vars.
    pass


@dataclass
class Settings:
    client_id: str
    client_secret: str
    tenant_id: str
    user_email: str
    scopes: List[str]
    delegated_scopes: List[str]
    authority: str
    task_title_prefix: str
    request_timeout: float
    max_delete_per_run: int
    mail_plan_group_name: str
    mail_plan_title: str
    auth_mode: str
    notification_email: str
    cleanup_time_budget_seconds: float
    enable_old_cleanup: bool


def _require_env(key: str, default: Optional[str] = None) -> str:
    value = os.getenv(key, default)
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def load_settings() -> Settings:
    tenant_id = _require_env("TENANT_ID")
    request_timeout = float(_require_env("REQUEST_TIMEOUT_SECONDS"))
    max_delete_per_run = int(_require_env("MAX_DELETE_PER_RUN"))
    mail_plan_group_name = os.getenv("MAIL_PLAN_GROUP", "")
    auth_mode = _require_env("AUTH_MODE").lower()

    delegated_scopes_env = _require_env("DELEGATED_SCOPES")
    delegated_scopes = delegated_scopes_env.split()
    mail_plan_title = _require_env("MAIL_PLAN_TITLE")

    return Settings(
        client_id=_require_env("CLIENT_ID"),
        client_secret=_require_env("CLIENT_SECRET"),
        tenant_id=tenant_id,
        user_email=_require_env("USER_EMAIL"),
        scopes=[_require_env("APP_SCOPE")],
        delegated_scopes=delegated_scopes,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        # Default prefix mirrors plan title if not provided.
        task_title_prefix=os.getenv("TASK_TITLE_PREFIX", mail_plan_title),
        request_timeout=request_timeout,
        max_delete_per_run=max_delete_per_run,
        mail_plan_group_name=mail_plan_group_name,
        mail_plan_title=mail_plan_title,
        auth_mode=auth_mode,
        notification_email=_require_env("NOTIFICATION_EMAIL"),
        cleanup_time_budget_seconds=float(_require_env("CLEANUP_TIME_BUDGET_SECONDS")),
        enable_old_cleanup=os.getenv("ENABLE_OLD_CLEANUP", "false").lower() == "true",
    )
