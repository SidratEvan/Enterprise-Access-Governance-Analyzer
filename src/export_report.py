import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


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


def load_data():
    users = pd.read_csv(DATA_DIR / "users.csv")
    roles = pd.read_csv(DATA_DIR / "roles.csv")
    user_roles = pd.read_csv(DATA_DIR / "user_roles.csv")
    return users, roles, user_roles


def analyze(users, roles, user_roles):
    user_roles_named = user_roles.merge(roles, on="role_id", how="left")
    findings = []

    for rule in SOD_RULES:
        role_a, role_b = rule["role_names"]
        users_with_a = set(user_roles_named[user_roles_named["role_name"] == role_a]["user_id"])
        users_with_b = set(user_roles_named[user_roles_named["role_name"] == role_b]["user_id"])
        conflicted_users = users_with_a.intersection(users_with_b)

        for user_id in sorted(conflicted_users):
            user_row = users[users["user_id"] == user_id].iloc[0]
            findings.append(
                {
                    "rule_id": rule["rule_id"],
                    "severity": rule["severity"],
                    "roles_in_conflict": f"{role_a} + {role_b}",
                    "user_id": user_id,
                    "full_name": user_row["full_name"],
                    "department": user_row["department"],
                    "location": user_row["location"],
                    "why_it_matters": rule["description"],
                    "recommended_fix": "Separate duties (remove one role) OR add compensating control (2nd approval).",
                }
            )

    return pd.DataFrame(findings)


def build_summary(findings_df):
    if findings_df.empty:
        return pd.DataFrame([{"severity": "NONE", "count": 0}])

    summary = findings_df.groupby("severity").size().reset_index(name="count")
    summary = summary.sort_values(by="count", ascending=False)
    return summary


def export_excel(findings_df, summary_df):
    REPORTS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    out_path = REPORTS_DIR / f"EAGPCA_Compliance_Report_{timestamp}.xlsx"

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        findings_df.to_excel(writer, sheet_name="Findings", index=False)

        # Auto-fit columns (simple approach)
        for sheet_name in ["Summary", "Findings"]:
            ws = writer.book[sheet_name]
            for col in ws.columns:
                max_len = 0
                col_letter = col[0].column_letter
                for cell in col:
                    if cell.value is not None:
                        max_len = max(max_len, len(str(cell.value)))
                ws.column_dimensions[col_letter].width = min(max_len + 2, 55)

    return out_path


def main():
    users, roles, user_roles = load_data()
    findings = analyze(users, roles, user_roles)
    summary = build_summary(findings)

    out_path = export_excel(findings, summary)

    print("\n✅ Excel report created:")
    print(out_path)


if __name__ == "__main__":
    main()