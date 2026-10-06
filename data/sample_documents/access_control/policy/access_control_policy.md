> Synthetic sample created solely for portfolio demonstration. This document contains
> no real company, client, employee, customer, vendor, financial, security, or
> confidential data.

# Asteria Financial Services — Access Control Policy (ACP)
Policy owner: Information Security | Effective: 2025-01-01 | Review cycle: Annual

## ACP-01 — Privileged Access Review
Privileged access to production systems must be reviewed and approved by the
application owner or delegated reviewer no less than quarterly. Review evidence
must include the reviewer's decision (retain/revoke) and an approval date.
Maps to: AC-6 (Least Privilege), AC-2 (Account Management).

## ACP-02 — Termination Access Removal
Upon employee termination, all application and system access must be disabled
within 24 hours of the termination effective date. Exceptions require a
documented exception ticket referencing the affected account.
Maps to: AC-2 (Account Management).

## ACP-03 — Multi-Factor Authentication
Multi-factor authentication (MFA) is required for all remote access and all
privileged accounts. Any exception must have a documented expiration date and
must be automatically re-evaluated upon expiration.
Maps to: IA-2, IA-2(1) (Multi-factor Authentication to Privileged Accounts).

## ACP-04 — Service Account Ownership
Every service account must have a named human owner and must be
recertified at least annually. Accounts without a current owner of record
are considered non-compliant regardless of activity status.
Maps to: AC-2 (Account Management), IA-5 (Authenticator Management).

## ACP-05 — Emergency (Break-Glass) Access
Emergency access to production systems requires approval from a designated
manager and a documented post-use review within 5 business days.
Maps to: AC-2, AU-6 (Audit Record Review, Analysis, and Reporting).

## ACP-06 — Evidence Retention
Access review evidence, approvals, and exception records must be retained for
a minimum of seven years to support audit and regulatory inquiry.
Maps to: AU-6, AU-12 (Audit Record Generation).
