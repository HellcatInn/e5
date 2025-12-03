"""
邮箱检查脚本：汇总邮箱状态并创建Planner任务，将摘要写入任务备注。
"""

from config import load_settings
from planner_agent import PlannerAgent


def main():
    settings = load_settings()
    agent = PlannerAgent(settings)

    result = agent.create_mailbox_summary_task(plan_title="邮箱检查", recent_top=5)

    print(
        f"创建邮箱检查任务 '{result['title']}' -> "
        f"组 '{result['group']}' / 计划 '{result['plan']}' / 桶 '{result['bucket']}' "
        f"(ID: {result['task_id']})"
    )
    print(f"未读: {result['unread']} / 总邮件: {result['total']}")
    print("最近邮件：")
    if not result["recent"]:
        print(" - 无")
    for msg in result["recent"]:
        print(
            f" - {'已读' if msg['isRead'] else '未读'} | "
            f"{msg['received']} | {msg['from']} | {msg['subject']}"
        )

    # 将摘要写入任务描述
    details = agent.get_task_details(result["task_id"])
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
        agent.update_task_description(result["task_id"], etag, description)
        print("已写入任务备注。")
    else:
        print("未获取到任务etag，备注未写入。")


if __name__ == "__main__":
    main()
