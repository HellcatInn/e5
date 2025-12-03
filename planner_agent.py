from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import time

from config import Settings, load_settings
from graph_client import GraphClient

# Helper

def parse_graph_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def budget_exceeded(start: float, budget: float) -> bool:
    return budget > 0 and (time.monotonic() - start) > budget


class PlannerAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = GraphClient(settings)

    def _build_task_title(self, plan: Dict) -> str:
        plan_title = plan.get("title") or "plan"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        prefix = self.settings.task_title_prefix or plan_title
        return f"{prefix}-{timestamp}"

    # Graph accessors
    def get_user_id(self, user_email: Optional[str] = None) -> str:
        email = user_email or self.settings.user_email
        response = self.client.get(
            "users", params={"$filter": f"userPrincipalName eq '{email}'"}
        )
        users = response.json().get("value", [])
        if not users:
            raise ValueError(f"No user found for email {email}")
        return users[0]["id"]

    def list_messages(self, user_id: str, top: int = 10) -> List[Dict]:
        response = self.client.get(f"users/{user_id}/messages", params={"$top": top})
        return response.json().get("value", [])

    def inbox_overview(self, user_id: str) -> Dict:
        response = self.client.get(
            f"users/{user_id}/mailFolders/Inbox",
            params={"$select": "displayName,totalItemCount,unreadItemCount"},
        )
        return response.json()

    def inbox_recent_messages(self, user_id: str, top: int = 5) -> List[Dict]:
        response = self.client.get(
            f"users/{user_id}/mailFolders/Inbox/messages",
            params={
                "$top": top,
                "$orderby": "receivedDateTime desc",
                "$select": "subject,from,isRead,receivedDateTime",
            },
        )
        return response.json().get("value", [])

    def list_groups(self) -> List[Dict]:
        response = self.client.get("groups")
        return response.json().get("value", [])

    def delete_group(self, group_id: str) -> None:
        self.client.delete(f"groups/{group_id}")

    def list_plans(self, group_id: str) -> List[Dict]:
        response = self.client.get(f"groups/{group_id}/planner/plans")
        return response.json().get("value", [])

    def create_plan(self, group_id: str, plan_title: str) -> Dict:
        response = self.client.post(
            "planner/plans",
            json={"owner": group_id, "title": plan_title},
        )
        return response.json()

    def list_buckets(self, plan_id: str) -> List[Dict]:
        response = self.client.get(f"planner/plans/{plan_id}/buckets")
        return response.json().get("value", [])

    def create_bucket(self, plan_id: str, name: str = "待办事项") -> Dict:
        response = self.client.post(
            "planner/buckets",
            json={"name": name, "planId": plan_id, "orderHint": " !"},
        )
        return response.json()

    def list_tasks(self, bucket_id: str) -> List[Dict]:
        response = self.client.get(f"planner/buckets/{bucket_id}/tasks")
        return response.json().get("value", [])

    def create_task(self, plan_id: str, bucket_id: str, title: str) -> Dict:
        response = self.client.post(
            "planner/tasks",
            json={"planId": plan_id, "bucketId": bucket_id, "title": title},
        )
        return response.json()

    def delete_task(self, task_id: str, etag: str) -> None:
        self.client.delete(
            f"planner/tasks/{task_id}",
            headers={"If-Match": etag},
        )

    def get_task_details(self, task_id: str) -> Dict:
        response = self.client.get(f"planner/tasks/{task_id}/details")
        return response.json()

    def update_task_description(self, task_id: str, etag: str, description: str) -> Dict:
        response = self.client.patch(
            f"planner/tasks/{task_id}/details",
            headers={"If-Match": etag},
            json={"description": description},
        )
        return response.json() if response.text else {}

    # Workflows
    def find_plan(self, plan_title: str) -> Optional[Tuple[Dict, Dict]]:
        for group in self.list_groups():
            for plan in self.list_plans(group["id"]):
                if plan.get("title") == plan_title:
                    return group, plan
        return None

    def ensure_plan_and_bucket(self, plan_title: str) -> Tuple[Dict, Dict, Dict]:
        located = self.find_plan(plan_title)
        if located:
            group, plan = located
        else:
            group = self.list_groups()[0] if self.list_groups() else None
            if not group:
                raise ValueError("No group available to create plan")
            plan = self.create_plan(group["id"], plan_title)

        bucket = self.list_buckets(plan["id"])
        bucket = bucket[0] if bucket else self.create_bucket(plan["id"])
        return group, plan, bucket

    def create_mailbox_summary_task(self, plan_title: str, recent_top: int = 5) -> Dict:
        user_id = self.get_user_id()
        overview = self.inbox_overview(user_id)
        recent = self.inbox_recent_messages(user_id, top=recent_top)

        unread = overview.get("unreadItemCount", 0)
        total = overview.get("totalItemCount", 0)
        latest_subject = recent[0]["subject"] if recent else "无最新邮件"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        title = f"{plan_title}-{timestamp} 未读:{unread} 总:{total} 最新:{latest_subject[:30]}"

        group, plan, bucket = self.ensure_plan_and_bucket(plan_title)

        task = self.create_task(plan["id"], bucket["id"], title)
        return {
            "group": group.get("displayName"),
            "group_id": group.get("id"),
            "plan": plan.get("title"),
            "plan_id": plan.get("id"),
            "bucket": bucket.get("name"),
            "bucket_id": bucket.get("id"),
            "task_id": task.get("id"),
            "title": title,
            "unread": unread,
            "total": total,
            "recent": [
                {
                    "subject": m.get("subject"),
                    "from": m.get("from", {}).get("emailAddress", {}).get("address", "unknown"),
                    "received": m.get("receivedDateTime"),
                    "isRead": m.get("isRead"),
                }
                for m in recent
            ],
        }

    def create_mailbox_summary_task_with_notes(self, plan_title: str, recent_top: int = 5) -> Dict:
        result = self.create_mailbox_summary_task(plan_title=plan_title, recent_top=recent_top)
        details = self.get_task_details(result["task_id"])
        etag = details.get("@odata.etag")
        if etag:
            lines = [
                f"未读: {result['unread']} / 总: {result['total']}",
                f"位置: 组 {result['group']} / 计划 {result['plan']} / 桶 {result['bucket']}",
                "最近邮件:",
            ]
            for msg in result["recent"]:
                lines.append(
                    f" - {'已读' if msg['isRead'] else '未读'} | {msg['received']} | {msg['from']} | {msg['subject']}"
                )
            description = "\n".join(lines)
            try:
                self.update_task_description(result["task_id"], etag, description)
                result["notes_written"] = True
            except Exception as exc:
                print(f"写入任务备注失败: {exc}")
                result["notes_written"] = False
                result["notes_error"] = str(exc)
        else:
            result["notes_written"] = False
        return result

    def cleanup_previous_week_tasks(
        self, plan_title: Optional[str] = None, plan_context: Optional[Dict[str, str]] = None
    ) -> List[Dict]:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(days=7)
        removed: List[Dict] = []
        delete_limit = self.settings.max_delete_per_run
        start = time.monotonic()
        budget = self.settings.cleanup_time_budget_seconds
        if budget <= 0:
            print("过期任务清理被禁用。")
            return removed

        groups_to_check = []
        if plan_context and plan_context.get("plan_id"):
            groups_to_check.append(
                (
                    {"displayName": plan_context.get("group", ""), "id": plan_context.get("group_id")},
                    {"title": plan_context.get("plan", plan_title), "id": plan_context.get("plan_id")},
                )
            )
        elif plan_title:
            located = self.find_plan(plan_title)
            if not located:
                print(f"未找到计划 {plan_title}，跳过过期任务清理。")
                return []
            groups_to_check.append(located)
        else:
            for group in self.list_groups():
                for plan in self.list_plans(group["id"]):
                    groups_to_check.append((group, plan))

        for group, plan in groups_to_check:
            if budget_exceeded(start, budget):
                print("过期任务清理超出时间预算，停止。")
                return removed
            for bucket in self.list_buckets(plan["id"]):
                if budget_exceeded(start, budget):
                    print("过期任务清理超出时间预算，停止。")
                    return removed
                tasks = self.list_tasks(bucket["id"])
                print(
                    f"检查任务: 组[{group.get('displayName')}] 计划[{plan.get('title')}] 桶[{bucket.get('name')}] "
                    f"共 {len(tasks)} 条"
                )
                for task in tasks:
                    if budget_exceeded(start, budget):
                        print("过期任务清理超出时间预算，停止。")
                        return removed
                    title = task.get("title", "")
                    created_at_raw = task.get("createdDateTime")
                    etag = task.get("@odata.etag")
                    if not created_at_raw or not etag:
                        continue

                    created_at = parse_graph_datetime(created_at_raw)
                    if created_at < threshold:
                        try:
                            self.delete_task(task["id"], etag)
                            removed.append(
                                {
                                    "group": group.get("displayName"),
                                    "plan": plan.get("title"),
                                    "bucket": bucket.get("name"),
                                    "task_id": task.get("id"),
                                    "title": title,
                                    "created_at": created_at_raw,
                                }
                            )
                        except Exception as exc:
                            print(
                                f"Delete failed for task {task.get('id')} "
                                f"({title}) in plan {plan.get('title')}: {exc}"
                            )
                    if len(removed) >= delete_limit:
                        print(
                            f"已删除 {len(removed)} 条，达到本次上限 {delete_limit}，稍后再次运行继续清理。"
                        )
                        return removed
        return removed

    def cleanup_keepalive_duplicates(
        self,
        plan_title: Optional[str] = None,
        keep_latest: int = 1,
        plan_context: Optional[Dict[str, str]] = None,
    ) -> List[Dict]:
        """
        Remove older keepalive tasks in the specified plan, keeping only the latest N
        (default 1) by creation time across all buckets.
        """
        target_plan = plan_title or self.settings.mail_plan_title
        plan_id = None
        group_name = None
        if plan_context and plan_context.get("plan_id"):
            plan_id = plan_context["plan_id"]
            group_name = plan_context.get("group")
        else:
            located = self.find_plan(target_plan)
            if not located:
                print(f"未找到计划 {target_plan}，跳过重复任务清理。")
                return []
            target_group, plan = located
            plan_id = plan.get("id")
            group_name = target_group.get("displayName")
        tasks_meta: List[Dict] = []
        removed: List[Dict] = []
        delete_limit = self.settings.max_delete_per_run
        start = time.monotonic()
        budget = self.settings.cleanup_time_budget_seconds

        for bucket in self.list_buckets(plan_id):
            if budget_exceeded(start, budget):
                print("重复任务清理超出时间预算，停止。")
                return removed
            for task in self.list_tasks(bucket["id"]):
                if budget_exceeded(start, budget):
                    print("重复任务清理超出时间预算，停止。")
                    return removed
                created_raw = task.get("createdDateTime")
                etag = task.get("@odata.etag")
                if not created_raw or not etag:
                    continue
                try:
                    created_dt = parse_graph_datetime(created_raw)
                except Exception:
                    continue
                tasks_meta.append(
                    {
                        "created_dt": created_dt,
                        "created_raw": created_raw,
                        "task": task,
                        "etag": etag,
                        "bucket": bucket.get("name"),
                        "plan": target_plan,
                        "group": group_name or "",
                    }
                )

        tasks_meta.sort(key=lambda item: item["created_dt"], reverse=True)
        to_delete = tasks_meta[keep_latest:]

        for item in to_delete:
            if len(removed) >= delete_limit:
                print(
                    f"已删除 {len(removed)} 条重复任务，达到上限 {delete_limit}，稍后再次运行继续清理。"
                )
                break
            task = item["task"]
            try:
                self.delete_task(task["id"], item["etag"])
                removed.append(
                    {
                        "group": item["group"],
                        "plan": item["plan"],
                        "bucket": item["bucket"],
                        "task_id": task.get("id"),
                        "title": task.get("title"),
                        "created_at": item["created_raw"],
                    }
                )
            except Exception as exc:
                print(
                    f"Delete failed for duplicate task {task.get('id')} "
                    f"({task.get('title')}) in plan {item['plan']}: {exc}"
                )
        return removed

    def delete_all_planner_groups(self) -> List[Dict]:
        """
        删除所有包含 Planner 计划的组，返回删除的组信息。
        """
        deleted: List[Dict] = []
        for group in self.list_groups():
            plans = self.list_plans(group["id"])
            if not plans:
                continue
            try:
                self.delete_group(group["id"])
                deleted.append(
                    {
                        "group_id": group.get("id"),
                        "group_name": group.get("displayName"),
                        "plan_count": len(plans),
                    }
                )
            except Exception as exc:
                print(
                    f"Delete failed for group {group.get('displayName')} "
                    f"({group.get('id')}): {exc}"
                )
        return deleted


def run_keepalive_cycle() -> None:
    settings = load_settings()
    agent = PlannerAgent(settings)

    # Only mailbox check plan
    mail_result = agent.create_mailbox_summary_task_with_notes(
        plan_title=settings.mail_plan_title, recent_top=5
    )
    print(
        f"邮箱检查任务 '{mail_result['title']}' -> "
        f"组 '{mail_result['group']}' / 计划 '{mail_result['plan']}' / 桶 '{mail_result['bucket']}' "
        f"(ID: {mail_result['task_id']})"
    )
    print(f"未读: {mail_result['unread']} / 总邮件: {mail_result['total']}")
    if mail_result.get("notes_written"):
        print("邮箱摘要已写入任务备注。")
    else:
        print("邮箱摘要未写入备注（缺少etag）。")

    try:
        duplicates_removed = agent.cleanup_keepalive_duplicates(
            plan_title=settings.mail_plan_title, keep_latest=1, plan_context=mail_result
        )
        if duplicates_removed:
            for item in duplicates_removed:
                print(
                    f"删除重复任务 '{item['title']}' 创建于 {item['created_at']} "
                    f"位置 组 '{item['group']}' / 计划 '{item['plan']}' / 桶 '{item['bucket']}'"
                )
        else:
            print("没有发现需要删除的重复邮箱检查任务。")
    except Exception as exc:
        print(f"删除重复邮箱检查任务时失败: {exc}")

    if settings.enable_old_cleanup:
        try:
            removed = agent.cleanup_previous_week_tasks(
                plan_title=settings.mail_plan_title, plan_context=mail_result
            )
            print(f"Removed {len(removed)} tasks older than 7 days in plan {settings.mail_plan_title}.")
        except Exception as exc:
            print(f"清理7天前任务失败: {exc}")
    else:
        print("已跳过7天前任务清理（ENABLE_OLD_CLEANUP 未开启）。")


if __name__ == "__main__":
    run_keepalive_cycle()
