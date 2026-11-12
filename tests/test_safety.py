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


def test_every_agent_checkout_gets_a_receipt(team):
    oid = _approved_checkout(team)
    co = team.checkouts[oid]
    rc = team.receipts[co["receipt_id"]]
    assert rc["outcome"] == "paypal_order_created" and rc["paypal"]["order_id"] == oid
    assert all(c["pass"] for c in rc["mandate_checks"])
    assert rc["risk"]["policy_version"]["hash"] and rc["risk"]["decision"] == "approve"
    team.capture(oid)
    assert rc["paypal"]["status"] == "COMPLETED" and rc["paypal"]["capture_id"]
    team.twin.policy = {**team.twin.policy, "review_threshold": 0.0, "block_threshold": 1.01}
    held = team.guarded_checkout(CART)
    hr = team.receipts[held["receipt_id"]]
    assert hr["outcome"] == "held_for_review" and hr["paypal"] is None and hr["review"]["status"] == "pending"
    rejected = team.guarded_checkout([{"sku": "SKU-GFT-02", "qty": 5}])
    rr = team.receipts[rejected["receipt_id"]]
    assert rr["outcome"] == "rejected_by_mandate_guard" and not all(c["pass"] for c in rr["mandate_checks"])


def test_investigator_only_proposes_refunds_and_freezes(team):
    oid = _approved_checkout(team)
    team.capture(oid)
    tw_order = next(o for o in team.twin.orders if o["paypal_order_id"] == oid)
    case = {"id": "CASE-T", "actions": []}
    tools = team.investigator_tools(case)
    refunds_before = sum(1 for c in team.pp.calls if "/refund" in c["path"])
    out = tools["refund_order"]["fn"](order_id=tw_order["id"], reason="test")
    assert out["status"].startswith("proposed")
    assert tw_order["status"] == "captured"  # nothing happened yet
    assert sum(1 for c in team.pp.calls if "/refund" in c["path"]) == refunds_before
    target = team.buyer
    fr = tools["freeze_account"]["fn"](account_id=target, reason="test")
    assert team.twin.accounts[target].status == "active"

    # reject leaves state unchanged
    team.decide_action(fr["action_id"], False, "alice", "not enough evidence")
    assert team.twin.accounts[target].status == "active"
    assert team.actions[fr["action_id"]]["status"] == "rejected"

    # approve executes exactly once
    a1 = team.decide_action(out["action_id"], True, "alice", "confirmed")
    a2 = team.decide_action(out["action_id"], True, "bob", "again")
    assert a1["status"] == "approved" and a2.get("duplicate") is True
    assert tw_order["status"] == "refunded"
    assert sum(1 for c in team.pp.calls if "/refund" in c["path"]) == refunds_before + 1
    assert [e["reviewer"] for e in team.audit] == ["alice", "alice"]


def test_held_checkout_needs_a_reviewer(team):
    team.twin.policy = {**team.twin.policy, "review_threshold": 0.0, "block_threshold": 1.01}
    h1 = team.guarded_checkout(CART)["hold_id"]
    h2 = team.guarded_checkout(CART)["hold_id"]
    assert team.checkouts == {}
    rejected = team.decide_hold(h2, False, "alice", "looks off")
    assert rejected["status"] == "rejected" and team.checkouts == {}
    released = team.decide_hold(h1, True, "alice", "known customer")
    assert released["status"] == "released" and released["paypal_order_id"] in team.checkouts
    again = team.decide_hold(h1, True, "bob")
    assert again.get("duplicate") is True and len(team.checkouts) == 1
    rc = team.receipts[team.holds[h1]["receipt_id"]]
    assert rc["outcome"] == "released_by_reviewer" and rc["review"]["reviewer"] == "alice"
