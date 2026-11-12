"""Defense drill: the adaptive red team finds a gap, the what-if simulator picks a safer policy,
and the *same* seeded attack is replayed to prove it is now stopped.

Everything runs on one frozen fork of the twin, so the before and after numbers compare like with like,
and live traffic keeps flowing untouched until the winning policy is applied.
"""
from __future__ import annotations

import itertools
import time

from .redteam import run_attack

# What a false positive costs the merchant. A legit order sent to manual review costs analyst time plus
# checkout friction; a legit order blocked is a lost sale (the whole order value).
REVIEW_COST_USD = 4.0
MAX_LEGIT_REVIEW_RATE = 0.08  # never accept a policy that reviews more than 8% of good customers

PROBES = [  # round 1: the standard playbooks
    ("fraud_ring", {}), ("card_testing", {}), ("account_takeover", {}),
    ("synthetic_identity", {}), ("device_farm_evasion", {}),
]
ADAPT = {  # round 2: how the red team mutates a playbook that got caught
    "fraud_ring": {"size": 3, "shared_devices": 3, "amount": 60, "age_days": 200},
    "card_testing": {"probes": 4, "final_amount": 120},
    "account_takeover": {"amount": 250, "foreign": False},
    "synthetic_identity": {"warmup_orders": 8, "bust_amount": 250},
    "device_farm_evasion": {"size": 3, "amount": 80},
}
GRID = {
    "review_threshold": [0.5, 0.4, 0.3],
    "block_threshold": [0.8, 0.75],
    "max_auto_amount": [1000, 600, 400],
    "review_new_device_over": [300, 150, 100],
    "review_spend_multiple": [0, 4, 3, 2.5],
}


def _slim(r):
    return {k: r.get(k) for k in ("attack", "params", "seed", "fraud_usd", "stopped_usd", "evaded_usd",
                                  "detection_rate")} | {"orders": r.get("orders", [])}


def _cost(m):
    return round(m["good_blocked_usd"] + REVIEW_COST_USD * m["good_reviewed"], 2)


def _score(m):
    """Fraud dollars stopped minus what the false positives cost."""
    return round(m["fraud_caught_usd"] - _cost(m), 2)


def _metrics(m):
    legit = max(m["good_total"], 1)
    return {**m, "false_positive_cost_usd": _cost(m), "net_benefit_usd": _score(m),
            "legit_review_rate": round(m["good_reviewed"] / legit, 4),
            "legit_affected": m["good_reviewed"] + m["good_blocked"]}


def defense_drill(twin, seed=7, apply=False, log=None):
    log = log if log is not None else []
    t0 = time.time()
    base = twin.fork()  # one frozen snapshot for the whole drill
    before_policy = dict(base.policy)

    def say(step, text):
        log.append({"step": step, "text": text})

    # ---- 1. probe, then adapt the attacks that were caught
    probes = [run_attack(base, k, p, seed=seed + i) for i, (k, p) in enumerate(PROBES)]
    for r in probes:
        say("attack", f"{r['attack']}: {r['detection_rate']:.0%} of ${r['fraud_usd']:,.0f} stopped")
    adapted = []
    for i, r in enumerate(probes):
        if r["detection_rate"] >= 0.8 and r["attack"] in ADAPT:
            a = run_attack(base, r["attack"], ADAPT[r["attack"]], seed=seed + 100 + i)
            adapted.append(a)
            say("adapt", f"{a['attack']} caught, mutated to {a['params']}: ${a['evaded_usd']:,.0f} got through")
    breaches = [r for r in probes + adapted if r["evaded_usd"] > 0]
    breaches.sort(key=lambda r: -r["evaded_usd"])
    attack_orders = [o for r in probes + adapted for o in r["orders"]]

    # ---- 2. search policies on replayed traffic + the attack orders, pricing false positives
    candidates = []
    keys = list(GRID)
    for combo in itertools.product(*GRID.values()):
        pol = dict(zip(keys, combo))
        if pol["block_threshold"] <= pol["review_threshold"]:
            continue
        m = _metrics(base.what_if(pol, extra_orders=attack_orders)["proposed"])
        candidates.append({"policy": {**before_policy, **pol}, **m})
    baseline = _metrics(base.what_if(before_policy, extra_orders=attack_orders)["proposed"])
    ok = [c for c in candidates if c["legit_review_rate"] <= MAX_LEGIT_REVIEW_RATE]
    # best net benefit; on ties prefer fewer false positives, then the smallest change from today's policy
    ok.sort(key=lambda c: (-c["net_benefit_usd"], c["false_positive_cost_usd"],
                           sum(c["policy"][k] != before_policy.get(k) for k in GRID)))
    best = ok[0] if ok and ok[0]["net_benefit_usd"] > baseline["net_benefit_usd"] else None
    say("search", f"tested {len(candidates)} policies; {len(ok)} keep legit reviews under "
                  f"{MAX_LEGIT_REVIEW_RATE:.0%}")

    # ---- 3. replay the identical breaching attacks under the chosen policy, plus fresh variants
    verify, fresh = [], []
    if best:
        hardened = base.fork()
        hardened.policy = dict(best["policy"])
        for r in breaches:
            verify.append(run_attack(hardened, r["attack"], r["params"], seed=r["seed"]))
        # held-out check: same playbooks, new random draws the policy was never tuned on
        for i, r in enumerate(breaches):
            fresh.append(run_attack(hardened, r["attack"], r["params"], seed=seed + 1000 + i))
        say("verify", f"same attacks replayed: ${sum(v['evaded_usd'] for v in verify):,.0f} got through "
                      f"(was ${sum(b['evaded_usd'] for b in breaches):,.0f})")

    def tot(rs, k):
        return round(sum(r[k] for r in rs), 2)

    applied = False
    if best and apply:
        twin.policy = dict(best["policy"])
        applied = True
        twin._event("policy", "Defense drill applied a hardened policy: "
                    + ", ".join(f"{k}={v}" for k, v in best["policy"].items() if before_policy.get(k) != v),
                    level="warn")
    twin._event("drill", f"Defense drill: red team got ${tot(breaches, 'evaded_usd'):,.0f} through; "
                         + (f"after the fix ${tot(verify, 'evaded_usd'):,.0f}" if best else "no safer policy found"),
                level="ok" if best else "warn")
    return {
        "seed": seed, "seconds": round(time.time() - t0, 1), "log": log,
        "review_cost_usd": REVIEW_COST_USD, "max_legit_review_rate": MAX_LEGIT_REVIEW_RATE,
        "probes": [_slim(r) for r in probes], "adapted": [_slim(r) for r in adapted],
        "breaches": [_slim(r) for r in breaches],
        "before_policy": before_policy, "after_policy": best["policy"] if best else None,
        "baseline": baseline, "chosen": best,
        "top_candidates": [{k: c[k] for k in ("policy", "catch_rate", "fraud_caught_usd", "good_reviewed",
                                               "good_blocked_usd", "false_positive_cost_usd", "net_benefit_usd",
                                               "legit_review_rate")} for c in ok[:6]],
        "verify": [_slim(r) for r in verify], "fresh": [_slim(r) for r in fresh],
        "summary": {
            "breach_evaded_before_usd": tot(breaches, "evaded_usd"),
            "breach_evaded_after_usd": tot(verify, "evaded_usd") if best else None,
            "fresh_evaded_after_usd": tot(fresh, "evaded_usd") if best else None,
            "fresh_attempted_usd": tot(fresh, "fraud_usd") if best else None,
            "catch_rate_before": baseline["catch_rate"], "catch_rate_after": best["catch_rate"] if best else None,
            "fp_cost_before_usd": baseline["false_positive_cost_usd"],
            "fp_cost_after_usd": best["false_positive_cost_usd"] if best else None,
            "legit_reviewed_before": baseline["good_reviewed"],
            "legit_reviewed_after": best["good_reviewed"] if best else None,
            "legit_blocked_before_usd": baseline["good_blocked_usd"],
            "legit_blocked_after_usd": best["good_blocked_usd"] if best else None,
            "legit_orders": baseline["good_total"], "applied": applied,
        },
    }
