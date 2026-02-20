import pandas as pd
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_data():
    users = pd.read_csv(DATA_DIR / "users.csv")
    roles = pd.read_csv(DATA_DIR / "roles.csv")
    user_roles = pd.read_csv(DATA_DIR / "user_roles.csv")
    return users, roles, user_roles


# Simple Segregation of Duties (SoD) rules (you can add more later)
# If a user has BOTH roles in any pair -> flag risk
SOD_RULES = [
    {
        "rule_id": "SOD-001",
        "description": "AP Clerk must not also be AP Approver (payment processing conflict).",
        "role_names": ["AP Clerk", "AP Approver"],
        "severity": "HIGH",
    },
    {
        "rule_id": "SOD-002",
        "description": "Procurement Requestor must not also be Procurement Approver (approval conflict).",
        "role_names": ["Procurement Requestor", "Procurement Approver"],
        "severity": "HIGH",
    },
    {
        "rule_id": "SOD-003",
        "description": "Vendor Master Maintainer should not also be Inventory Receiver (master data + receiving conflict).",
        "role_names": ["Vendor Master Maintainer", "Inventory Receiver"],
        "severity": "MEDIUM",
    },
]


def analyze(users, roles, user_roles):
    # join roles onto user_roles so we can see role_name per user
    user_roles_named = user_roles.merge(roles, on="role_id", how="left")

    findings = []

    for rule in SOD_RULES:
        role_a, role_b = rule["role_names"]

        # find users who have role_a
        users_with_a = set(user_roles_named[user_roles_named["role_name"] == role_a]["user_id"])
        # find users who have role_b
        users_with_b = set(user_roles_named[user_roles_named["role_name"] == role_b]["user_id"])

        conflicted_users = users_with_a.intersection(users_with_b)

        for user_id in sorted(conflicted_users):
            user_row = users[users["user_id"] == user_id].iloc[0]
            findings.append(
                {
                    "rule_id": rule["rule_id"],
                    "severity": rule["severity"],
                    "description": rule["description"],
                    "user_id": user_id,
                    "full_name": user_row["full_name"],
                    "department": user_row["department"],
                    "location": user_row["location"],
                    "roles_in_conflict": f"{role_a} + {role_b}",
                }
            )

    return pd.DataFrame(findings)


def print_report(findings_df):
    print("\n=== EAGPCA: Access Governance Risk Report ===\n")

    if findings_df.empty:
        print("No SoD conflicts detected. ✅")
        return

    # summary
    summary = findings_df.groupby("severity").size().reset_index(name="count")
    print("Summary (conflicts by severity):")
    for _, row in summary.iterrows():
        print(f"  - {row['severity']}: {row['count']}")

    print("\nDetailed Findings:")
    for i, row in findings_df.iterrows():
        print(f"\n[{row['severity']}] {row['rule_id']} — {row['roles_in_conflict']}")
        print(f"User: {row['full_name']} ({row['user_id']}) | {row['department']} | {row['location']}")
        print(f"Why: {row['description']}")


def main():
    users, roles, user_roles = load_data()
    findings = analyze(users, roles, user_roles)
    print_report(findings)


if __name__ == "__main__":
    main()