"""The defense drill finds a breach, picks a safer policy within the false-positive budget, and proves it."""
from app.drill import MAX_LEGIT_REVIEW_RATE, defense_drill
from app.redteam import run_attack
from app.twin import Twin


def _twin():
    twin = Twin(seed=3)
    twin.train(epochs=60)
    for _ in range(40):
        twin.tick()
    return twin


def test_drill_finds_breach_and_fixes_it():
    twin = _twin()
    res = defense_drill(twin, seed=7, apply=True)
    s = res["summary"]
    assert s["breach_evaded_before_usd"] > 0
    assert res["chosen"] is not None
    assert s["breach_evaded_after_usd"] < s["breach_evaded_before_usd"]
    assert res["chosen"]["legit_review_rate"] <= MAX_LEGIT_REVIEW_RATE
    assert twin.policy == res["after_policy"]
    # held-out: the same unseen attacks under both policies, on the same frozen twin
    assert s["fresh_evaded_before_usd"] is not None and s["fresh_evaded_after_usd"] <= s["fresh_evaded_before_usd"]
    for r in res["verify"]:
        assert abs(r["blocked_usd"] + r["reviewed_usd"] - r["stopped_usd"]) < 0.05


def test_same_seed_replays_identical_attack():
    twin = _twin()
    a = run_attack(twin, "synthetic_identity", {"warmup_orders": 8, "bust_amount": 250}, seed=11)
    b = run_attack(twin, "synthetic_identity", {"warmup_orders": 8, "bust_amount": 250}, seed=11)
    assert [o["amount"] for o in a["orders"]] == [o["amount"] for o in b["orders"]]


def test_compare_engines_on_identical_orders():
    twin = _twin()
    res = defense_drill(twin, seed=7)
    c = res["compare"]
    assert set(c["engines"]) == {"rules_only", "gat_rules", "gat_rules_hardened"}
    totals = {e["fraud_total_usd"] for e in c["engines"].values()}
    assert len(totals) == 1  # every engine saw the same orders
    for e in c["engines"].values():
        assert abs(e["fraud_intercepted_usd"] + e["fraud_missed_usd"] - e["fraud_total_usd"]) < 0.05
    u = c["unseen_attacks"]
    assert u["gat_rules_hardened"]["intercepted_usd"] >= u["gat_rules"]["intercepted_usd"]
    assert c["account_auc"]["test_accounts"] > 0


def test_adaptations_explain_themselves():
    from app.redteam import why_adapted
    prev = {"attack": "fraud_ring", "detection_rate": 0.92,
            "params": {"size": 6, "shared_devices": 2, "amount": 400, "age_days": 10}}
    new = {"attack": "fraud_ring", "params": {"size": 3, "shared_devices": 3, "amount": 60, "age_days": 200}}
    text = why_adapted(prev, new)
    assert text.startswith("fraud_ring intercepted at 92%")
    assert "smaller amounts" in text and "older accounts" in text
    twin = _twin()
    res = defense_drill(twin, seed=7)
    assert res["adapted"] and all(a["why_adapted"] and a["decided_by"] for a in res["adapted"])


def test_red_team_records_who_decided():
    from app import agents
    from app.paypal import PayPal
    team = agents.Team(_twin(), PayPal())
    team.brain.client, team.brain.provider = None, "demo"  # never call a real LLM from tests
    run = team.red_team()
    adapted = [r for r in run["results"] if r.get("why_adapted")]
    assert adapted and all(r["decided_by"] == "scripted fallback" for r in run["results"])
