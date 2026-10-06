"""
Simple mock role-based auth for the demo, per the project's nonfunctional
requirement: "Role-based permissions in the demo, even if implemented with
simple mock users." Real auth (OAuth/SSO) is out of scope for a portfolio
project and would replace this module wholesale, not extend it.
"""
from fastapi import Header, HTTPException

MOCK_USERS = {
    "analyst1": "analyst",
    "reviewer1": "reviewer",
    "manager1": "compliance_manager",
}


def get_current_user(x_user_id: str = Header(default="analyst1")):
    role = MOCK_USERS.get(x_user_id)
    if role is None:
        raise HTTPException(status_code=401, detail=f"Unknown mock user '{x_user_id}'. Try: {list(MOCK_USERS)}")
    return {"user_id": x_user_id, "role": role}


def require_reviewer(user: dict):
    if user["role"] not in ("reviewer", "compliance_manager"):
        raise HTTPException(status_code=403, detail="Only reviewer/compliance_manager roles can submit review decisions.")
