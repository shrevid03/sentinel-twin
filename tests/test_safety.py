"""Regression tests for the payment safety guarantees the project claims."""
import pytest

from app import agents
from app.paypal import PayPal
from app.twin import Twin

CART = [{"sku": "SKU-COF-02", "qty": 1}]  # $32 pour-over set


@pytest.fixture(scope="module")
def trained_twin():
    twin = Twin(seed=3)
    twin.train(40)
    return twin


@pytest.fixture
def team(trained_twin):
    trained_twin.policy = {**trained_twin.policy}
    return agents.Team(trained_twin, PayPal())


def test_review_decision_never_creates_a_paypal_order(team):
    team.twin.policy = {**team.twin.policy, "review_threshold": 0.0, "block_threshold": 1.01}
    calls_before = len(team.pp.calls)
    out = team.guarded_checkout(CART)
    assert out["status"] == "held_for_review"
    assert "paypal_order_id" not in out
    assert team.checkouts == {}
    assert len(team.pp.calls) == calls_before  # PayPal was never called


def test_block_decision_never_creates_a_paypal_order(team):
    team.twin.policy = {**team.twin.policy, "review_threshold": 0.0, "block_threshold": 0.0}
    out = team.guarded_checkout(CART)
    assert out["status"] == "blocked_by_risk_engine"
    assert team.checkouts == {}


def _approved_checkout(team):
    team.twin.policy = {**team.twin.policy, "review_threshold": 1.01, "block_threshold": 1.01}
    out = team.guarded_checkout(CART)
    assert out["status"] == "awaiting_buyer_approval"
    return out["paypal_order_id"]


def test_repeat_capture_charges_once_and_counts_spend_once(team):
    oid = _approved_checkout(team)
    first = team.capture(oid)
    second = team.capture(oid)
    assert first["status"] == "COMPLETED"
    assert second["status"] == "COMPLETED" and second["duplicate"] is True
    assert team.mandate["spent"] == 32.0
    captures = [c for c in team.pp.calls if c["path"].endswith("/capture")]
    assert len(captures) == 1


def test_capture_rechecks_mandate(team):
    oid = _approved_checkout(team)
    team.mandate["monthly_budget"] = 10.0  # budget shrank after the order was created
    with pytest.raises(agents.CaptureRefused) as e:
        team.capture(oid)
    assert e.value.status == 409
    assert team.mandate["spent"] == 0.0


def test_unknown_order_cannot_be_captured(team):
    with pytest.raises(agents.CaptureRefused) as e:
        team.capture("DEMO-NOT-OURS")
    assert e.value.status == 404


def test_unverified_webhook_changes_nothing(monkeypatch):
    monkeypatch.setenv("GAT_EPOCHS", "20")
    monkeypatch.setenv("AUTO_TRAFFIC", "0")
    from fastapi.testclient import TestClient

    from app import main

    monkeypatch.setenv("ALLOW_UNVERIFIED_WEBHOOKS", "0")  # after import: main loads .env on import

    order = main.twin.orders[0]
    order["capture_id"], order["status"], order["fraud"] = "CAP-TEST-1", "captured", False
    client = TestClient(main.app)
    dispute = {"event_type": "CUSTOMER.DISPUTE.CREATED",
               "resource": {"disputed_transactions": [{"seller_transaction_id": "CAP-TEST-1"}]}}
    refund = {"event_type": "PAYMENT.CAPTURE.REFUNDED", "resource": {"id": "CAP-TEST-1"}}
    for ev in (dispute, refund):
        r = client.post("/api/paypal/webhook", json=ev)
        assert r.status_code == 200 and r.json()["processed"] is False
    assert order["fraud"] is False and order["status"] == "captured"
