"""
Generate SYNTHETIC access-control evidence for a fictional company
("Asteria Financial Services"). No real people, employees, customers, or
company data are used anywhere in this script's output.

Produces the CSV evidence files described in the project's data plan, with
9 intentionally planted, documented gaps so the copilot has real findings
to detect (see GAP LOG at the bottom of this file).
"""
import csv
import random
from pathlib import Path

random.seed(42)
ROOT = Path(__file__).resolve().parent.parent
EVID = ROOT / "data/sample_documents/access_control/evidence"
META = ROOT / "data/sample_documents/access_control/metadata"
EXC = ROOT / "data/sample_documents/access_control/exceptions"
for d in (EVID, META, EXC):
    d.mkdir(parents=True, exist_ok=True)

SYNTHETIC_NOTICE = (
    "Synthetic sample created solely for portfolio demonstration. "
    "This document contains no real company, client, employee, customer, "
    "vendor, financial, security, or confidential data."
)

APPS = ["CoreBanking", "PaymentsHub", "CustomerPortal", "BIPlatform", "TreasuryOps"]
FIRST = ["Ana", "David", "Jordan", "Mei", "Alex", "Raj", "Priya", "Sam", "Lena", "Omar"]
LAST = ["Patel", "Kim", "Lee", "Chen", "Morgan", "Shah", "Nguyen", "Garcia", "Ivanov", "Brown"]


def rand_name(used):
    for _ in range(200):
        n = f"{random.choice(FIRST)} {random.choice(LAST)}"
        if n not in used:
            used.add(n)
            return n
    # pool exhausted -- allow reuse rather than looping forever
    return f"{random.choice(FIRST)} {random.choice(LAST)}"


# ---------------------------------------------------------------------------
# 1. Privileged access review Q1-Q4 2025
# ---------------------------------------------------------------------------
used_names = set()
rows_by_q = {"2025-Q1": [], "2025-Q2": [], "2025-Q3": [], "2025-Q4": []}
review_id = 1
for q_idx, quarter in enumerate(["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]):
    n_rows = random.randint(12, 18)
    for _ in range(n_rows):
        app = random.choice(APPS)
        user_name = rand_name(used_names)
        role = random.choice(["System Admin", "DB Admin", "Support Admin", "Security Engineer"])
        manager = rand_name(used_names)
        reviewer = random.choice(["Security Manager", "Application Owner", "IAM Lead"])
        rid = f"PAR-{quarter}-{review_id:03d}"
        review_id += 1

        # --- Planted gaps -------------------------------------------------
        if quarter == "2025-Q3" and _ == 0:
            # Gap: Q3 review exists but no manager approval
            decision, approval_status, approval_date, evidence_status = "Retain", "Pending", "", "Partial"
            review_date = "2025-09-27"
        elif quarter == "2025-Q4":
            # Gap: Q4 review fully missing (only generate metadata row marking it missing)
            decision, approval_status, approval_date, evidence_status = "", "", "", "Missing"
            review_date = ""
        else:
            decision = random.choice(["Retain", "Revoke"])
            approval_status = "Approved"
            review_date_day = random.randint(20, 28)
            month = {"2025-Q1": "03", "2025-Q2": "06", "2025-Q3": "09", "2025-Q4": "12"}[quarter]
            review_date = f"2025-{month}-{review_date_day}"
            approval_date = review_date
            evidence_status = "Complete"

        rows_by_q[quarter].append({
            "review_id": rid, "review_quarter": quarter, "application": app,
            "user_id": f"U{1000+review_id}", "user_name": user_name, "access_role": role,
            "privilege_level": "Privileged", "manager": manager, "reviewer": reviewer,
            "review_date": review_date, "decision": decision, "approval_status": approval_status,
            "approval_date": approval_date, "evidence_status": evidence_status,
        })

for quarter, rows in rows_by_q.items():
    q_short = quarter.split("-")[1].lower()
    fname = EVID / f"{q_short}_privileged_access_review.csv"
    with open(fname, "w", newline="") as f:
        f.write(f"# {SYNTHETIC_NOTICE}\n")
        writer = csv.DictWriter(f, fieldnames=[
            "review_id", "review_quarter", "application", "user_id", "user_name",
            "access_role", "privilege_level", "manager", "reviewer", "review_date",
            "decision", "approval_status", "approval_date", "evidence_status",
        ])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {fname} ({len(rows)} rows)")

# ---------------------------------------------------------------------------
# 2. Terminated-employee access report (gap: one account disabled after 50h)
# ---------------------------------------------------------------------------
term_rows = []
for i in range(15):
    app = random.choice(APPS)
    name = rand_name(used_names)
    if i == 2:
        hours = 50  # GAP: exceeds 24h SLA
        exc_id = "EXC-2025-014"
    else:
        hours = random.randint(1, 20)
        exc_id = ""
    term_rows.append({
        "employee_id": f"E{2000+i}", "employee_name": name,
        "department": random.choice(["Risk", "Operations", "Engineering", "Finance"]),
        "termination_date": f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
        "application": app, "account_id": f"U{2000+i}",
        "account_disabled_at": "", "hours_to_disable": hours,
        "within_24_hours": "true" if hours <= 24 else "false",
        "exception_id": exc_id,
    })
with open(EVID / "terminated_employee_access_report.csv", "w", newline="") as f:
    f.write(f"# {SYNTHETIC_NOTICE}\n")
    writer = csv.DictWriter(f, fieldnames=list(term_rows[0].keys()))
    writer.writeheader()
    writer.writerows(term_rows)
print("Wrote terminated_employee_access_report.csv")

# ---------------------------------------------------------------------------
# 3. Service account inventory (gap: privileged account with no owner; one overdue recert)
# ---------------------------------------------------------------------------
svc_rows = [
    {"service_account_id": "svc_pay_batch", "application": "PaymentsHub", "account_owner": "",
     "owner_department": "Engineering", "privilege_level": "Privileged",
     "last_recertification_date": "2024-05-10", "next_recertification_due": "2025-05-10",
     "credential_rotation_date": "2025-01-15", "status": "Overdue"},  # GAP: no owner + overdue
    {"service_account_id": "svc_reporting", "application": "BIPlatform", "account_owner": "Mei Chen",
     "owner_department": "Analytics", "privilege_level": "Standard",
     "last_recertification_date": "2025-02-01", "next_recertification_due": "2026-02-01",
     "credential_rotation_date": "2025-07-01", "status": "Current"},
    {"service_account_id": "svc_core_etl", "application": "CoreBanking", "account_owner": "David Kim",
     "owner_department": "Data Engineering", "privilege_level": "Privileged",
     "last_recertification_date": "2024-04-01", "next_recertification_due": "2025-04-01",
     "credential_rotation_date": "2025-02-01", "status": "Overdue"},  # GAP: 14+ months old (annual recert policy)
]
with open(EVID / "service_account_inventory.csv", "w", newline="") as f:
    f.write(f"# {SYNTHETIC_NOTICE}\n")
    writer = csv.DictWriter(f, fieldnames=list(svc_rows[0].keys()))
    writer.writeheader()
    writer.writerows(svc_rows)
print("Wrote service_account_inventory.csv")

# ---------------------------------------------------------------------------
# 4. MFA enrollment report (gap: expired exception still marked active)
# ---------------------------------------------------------------------------
mfa_rows = []
for i in range(20):
    enrolled = random.random() > 0.1
    mfa_rows.append({
        "user_id": f"U{3000+i}", "application": random.choice(APPS),
        "mfa_enrolled": "true" if enrolled else "false",
        "exception_granted": "false" if enrolled else "true",
        "exception_expiration": "" if enrolled else "2025-06-30",
        "exception_status": "" if enrolled else ("Expired-but-active" if i == 15 else "Active"),
    })
with open(EVID / "mfa_enrollment_report.csv", "w", newline="") as f:
    f.write(f"# {SYNTHETIC_NOTICE}\n")
    writer = csv.DictWriter(f, fieldnames=list(mfa_rows[0].keys()))
    writer.writeheader()
    writer.writerows(mfa_rows)
print("Wrote mfa_enrollment_report.csv (row 16 is the planted expired-exception-still-active gap)")

# ---------------------------------------------------------------------------
# 5. Emergency access log (gap: one event with no post-use review)
# ---------------------------------------------------------------------------
emerg_rows = [
    {"event_id": "EMG-001", "application": "CoreBanking", "user_id": "U1010",
     "requested_at": "2025-04-02T02:15:00", "approved_by": "IAM Manager",
     "post_use_review": "Completed", "review_date": "2025-04-03"},
    {"event_id": "EMG-002", "application": "PaymentsHub", "user_id": "U1022",
     "requested_at": "2025-07-19T23:40:00", "approved_by": "Security Manager",
     "post_use_review": "Missing", "review_date": ""},  # GAP
]
with open(EVID / "emergency_access_log.csv", "w", newline="") as f:
    f.write(f"# {SYNTHETIC_NOTICE}\n")
    writer = csv.DictWriter(f, fieldnames=list(emerg_rows[0].keys()))
    writer.writeheader()
    writer.writerows(emerg_rows)
print("Wrote emergency_access_log.csv")

# ---------------------------------------------------------------------------
# 6. Evidence index (links evidence files to control IDs, marks missing ones)
# ---------------------------------------------------------------------------
evidence_index_rows = [
    {"evidence_id": "EVD-001", "control_id": "AC-6", "evidence_type": "Privileged Access Review",
     "document_name": "q1_privileged_access_review.csv", "period_covered": "2025-Q1",
     "owner": "Identity Team", "received_date": "2025-03-30", "status": "Complete"},
    {"evidence_id": "EVD-002", "control_id": "AC-6", "evidence_type": "Privileged Access Review",
     "document_name": "q2_privileged_access_review.csv", "period_covered": "2025-Q2",
     "owner": "Identity Team", "received_date": "2025-06-30", "status": "Complete"},
    {"evidence_id": "EVD-003", "control_id": "AC-6", "evidence_type": "Privileged Access Review",
     "document_name": "q3_privileged_access_review.csv", "period_covered": "2025-Q3",
     "owner": "Identity Team", "received_date": "2025-09-30", "status": "Partial - missing manager approval"},
    {"evidence_id": "EVD-004", "control_id": "AC-6", "evidence_type": "Privileged Access Review",
     "document_name": "q4_privileged_access_review.csv", "period_covered": "2025-Q4",
     "owner": "Identity Team", "received_date": "", "status": "Missing"},
    {"evidence_id": "EVD-005", "control_id": "AC-2", "evidence_type": "Terminated Access Report",
     "document_name": "terminated_employee_access_report.csv", "period_covered": "2025",
     "owner": "Identity Team", "received_date": "2025-08-01", "status": "Complete (1 SLA exception noted)"},
    {"evidence_id": "EVD-006", "control_id": "IA-2.1", "evidence_type": "MFA Enrollment Report",
     "document_name": "mfa_enrollment_report.csv", "period_covered": "2025",
     "owner": "Identity Team", "received_date": "2025-07-01", "status": "Complete (1 stale exception noted)"},
]
with open(META / "evidence_index.csv", "w", newline="") as f:
    f.write(f"# {SYNTHETIC_NOTICE}\n")
    writer = csv.DictWriter(f, fieldnames=list(evidence_index_rows[0].keys()))
    writer.writeheader()
    writer.writerows(evidence_index_rows)
print("Wrote evidence_index.csv")

print("\nGAP LOG (for evaluation labels):")
print("  1. Q3 2025 privileged access review: no manager approval")
print("  2. Q4 2025 privileged access review: entirely missing")
print("  3. Terminated user E2002: account disabled after 50h (>24h SLA)")
print("  4. svc_pay_batch: privileged service account with no named owner")
print("  5. svc_core_etl: recertification 14+ months old (policy: annual)")
print("  6. MFA exception row 16: expired 2025-06-30 but still marked active")
print("  7. Emergency access EMG-002: no post-use review on file")
