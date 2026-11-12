"""Public-demo safety: admin actions need X-Admin-Token when ADMIN_TOKEN is set, and reset restores a clean demo."""
from fastapi.testclient import TestClient


def test_admin_token_and_reset(monkeypatch):
    monkeypatch.setenv("GAT_EPOCHS", "20")
    from app import main

    client = TestClient(main.app)
    hardened = {"review_threshold": 0.3, "block_threshold": 0.75, "max_auto_amount": 600,
                "review_new_device_over": 150, "review_spend_multiple": 4}

    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    assert client.post("/api/policy", json=hardened).status_code == 401
    assert client.post("/api/reset").status_code == 401
    assert client.post("/api/drill", json={"seed": 7, "apply": True}).status_code == 401
    assert client.post("/api/actions/ACT-X/approve", json={}).status_code == 401
    assert client.post("/api/policy", json=hardened, headers={"X-Admin-Token": "s3cret"}).status_code == 200
    assert main.twin.policy["review_threshold"] == 0.3

    # a visitor leaves state behind; reset (with the token) clears it
    client.post("/api/chat", json={"text": "Buy a gift for a coffee lover under $40", "lang": "en-IN"})
    assert main.team.checkouts
    r = client.post("/api/reset", headers={"X-Admin-Token": "s3cret"})
    assert r.status_code == 200
    assert main.twin.policy["review_threshold"] == 0.5
    assert not main.team.checkouts and not main.team.receipts and not main.team.actions
    assert main.team.mandate["spent"] == 0.0

    monkeypatch.setenv("ADMIN_TOKEN", "")  # unset = open, for local use
    assert client.post("/api/policy", json=hardened).status_code == 200
