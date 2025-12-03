import argparse

from planner_agent import run_keepalive_cycle


def main():
    parser = argparse.ArgumentParser(
        description="统一入口：创建邮箱检查任务并清理重复/过期记录，或删除Planner组"
    )
    parser.add_argument(
        "command",
        choices=["keepalive", "delete_groups"],
        help=(
            "keepalive: 创建一次邮箱检查任务，同时只保留最新一条并清理7天前的旧任务；"
            "delete_groups: 删除所有包含Planner计划的组"
        ),
    )
    args = parser.parse_args()

    if args.command == "keepalive":
        run_keepalive_cycle()
    elif args.command == "delete_groups":
        from config import load_settings
        from planner_agent import PlannerAgent

        settings = load_settings()
        agent = PlannerAgent(settings)
        deleted = agent.delete_all_planner_groups()
        if not deleted:
            print("未找到包含Planner计划的组，未删除任何组。")
        else:
            print("已删除以下组：")
            for item in deleted:
                print(
                    f"- {item['group_name']} ({item['group_id']}), 计划数量: {item['plan_count']}"
                )


if __name__ == "__main__":
    main()
