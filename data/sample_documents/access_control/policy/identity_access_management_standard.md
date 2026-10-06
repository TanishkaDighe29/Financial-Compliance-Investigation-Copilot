> Synthetic sample created solely for portfolio demonstration. This document contains
> no real company, client, employee, customer, vendor, financial, security, or
> confidential data.

# Asteria Financial Services — Identity and Access Management (IAM) Standard
Owner: IAM Team | Supersedes: v1.2 | Effective: 2025-01-01

## 1. Scope
Applies to CoreBanking, PaymentsHub, CustomerPortal, BIPlatform, and TreasuryOps.

## 2. Account Lifecycle
- New accounts require manager approval and a documented business justification.
- Access must follow least privilege (AC-6): users receive only the entitlements
  required for their role.
- Separation of duties (AC-5) must be enforced between transaction initiation
  and approval roles in CoreBanking and PaymentsHub.

## 3. Authentication
- Standard users: password + MFA (IA-2).
- Privileged users: MFA to privileged accounts is mandatory, no exceptions
  without a time-boxed, documented waiver (IA-2(1)).

## 4. Remote Access
Remote access requires VPN plus MFA and is logged for audit review (AC-17).

## 5. Recertification
All privileged and service accounts are recertified on a schedule defined by
account criticality; privileged human accounts quarterly, service accounts
annually, per ACP-01 and ACP-04.
