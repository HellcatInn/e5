from config import load_settings
from planner_agent import PlannerAgent


def main():
    settings = load_settings()
    agent = PlannerAgent(settings)

    user_id = agent.get_user_id()
    print(f"User ID for {settings.user_email}: {user_id}")

    messages = agent.list_messages(user_id, top=5)
    if not messages:
        print("No recent messages found.")
    for message in messages:
        print(f"Subject: {message['subject']}")
        print(f"From: {message['from']['emailAddress']['address']}")
        print(f"Received: {message['receivedDateTime']}")
        print("-" * 30)

    print("Planner structure:")
    for group in agent.list_groups():
        print(f"- Group: {group.get('displayName')} ({group.get('id')})")
        for plan in agent.list_plans(group["id"]):
            print(f"  - Plan: {plan.get('title')} ({plan.get('id')})")
            for bucket in agent.list_buckets(plan["id"]):
                print(f"    - Bucket: {bucket.get('name')} ({bucket.get('id')})")


if __name__ == "__main__":
    main()
