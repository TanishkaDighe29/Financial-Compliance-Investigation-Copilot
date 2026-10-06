"""Phase 3: persistence, reviewer workflow, and audit trail."""
from fastapi.testclient import TestClient
from backend.app.main import app


def test_investigation_creates_reviewable_finding_with_audit_trail():
    with TestClient(app) as c:
        r = c.post(
            "/investigations",
            json={"question": "Was the Q3 2025 privileged-access review completed and approved for CoreBanking?"},
            headers={"X-User-Id": "analyst1"},
        )
        assert r.status_code == 200
        data = r.json()
        finding_id = data["finding_id"]

        # shows up in reviewer queue
        queue = c.get("/findings?status=pending_review", headers={"X-User-Id": "reviewer1"}).json()
        assert any(f["finding_id"] == finding_id for f in queue["findings"])

        # analyst cannot review their own finding
        forbidden = c.post(f"/findings/{finding_id}/review", json={"decision": "accept"},
                            headers={"X-User-Id": "analyst1"})
        assert forbidden.status_code == 403

        # reviewer can
        accepted = c.post(f"/findings/{finding_id}/review",
                           json={"decision": "accept", "comment": "Confirmed."},
                           headers={"X-User-Id": "reviewer1"})
        assert accepted.status_code == 200
        assert accepted.json()["status"] == "accepted"

        # audit trail captures both events, in order
        events = c.get(f"/audit-log?investigation_id={data['investigation_id']}",
                        headers={"X-User-Id": "manager1"}).json()["events"]
        assert [e["event_type"] for e in events] == ["investigation_created", "review_submitted"]


def test_unknown_mock_user_is_rejected():
    with TestClient(app) as c:
        r = c.post("/investigations", json={"question": "test"}, headers={"X-User-Id": "not_a_real_user"})
        assert r.status_code == 401
