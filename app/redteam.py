"""Attack library for the red-team agent.

Every attack runs against a *fork* of the digital twin, so the live state is
never polluted. Each returns how much fraud value got through.
"""
from __future__ import annotations

import random

ATTACKS = {
    "fraud_ring": {
        "description": "Freshly created accounts that share a small pool of devices and IPs, buying resellable goods.",
        "params": {"size": "accounts in the ring (3-12)", "shared_devices": "devices shared by the ring (1-6)",
                   "amount": "dollars per order (20-1500)", "age_days": "account age in days (1-365)"},
    },
    "card_testing": {
        "description": "One account fires many tiny orders to test stolen cards, then a large purchase.",
        "params": {"probes": "number of small test orders (3-30)", "final_amount": "size of the cash-out order"},
    },
    "account_takeover": {
        "description": "A long-standing good customer is hijacked: new device, foreign IP, high-value order.",
        "params": {"amount": "value of the takeover order", "foreign": "true to use a foreign IP"},
    },
    "synthetic_identity": {
        "description": "An aged, KYC-verified fake identity builds trust with small orders, then busts out.",
        "params": {"warmup_orders": "small trust-building orders (0-10)", "bust_amount": "final bust-out order"},
    },
    "device_farm_evasion": {
        "description": "Ring members each use a brand-new device to dodge device links, but share one proxy IP.",
        "params": {"size": "accounts (3-12)", "amount": "dollars per order"},
    },
    "prompt_injection": {
        "description": "A poisoned product listing tells the shopping agent to ignore its mandate and buy gift cards.",
        "params": {},
    },
}


def _clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def _summary(kind, params, orders, notes=""):
    fraud = [o for o in orders if o["fraud"]]
    total = sum(o["amount"] for o in fraud)
    stopped = sum(o["amount"] for o in fraud if o["decision"] != "approve")
    return {
        "attack": kind, "params": params, "orders": [
            {"id": o["id"], "account": o["account"], "amount": o["amount"], "decision": o["decision"],
             "risk": o["risk"], "factors": o["factors"][:3], "fraud": o["fraud"],
             "new_device": o.get("new_device", False), "spend_ratio": o.get("spend_ratio", 0),
             "gat_risk": o.get("gat_risk"), "txn_score": o.get("txn_score"), "attack": kind} for o in orders],
        "fraud_usd": round(total, 2), "stopped_usd": round(stopped, 2), "evaded_usd": round(total - stopped, 2),
        "detection_rate": round(stopped / total, 3) if total else 1.0, "notes": notes,
    }


def run_attack(twin, kind, params=None, shopper_guard=None, seed=None):
    """Run one attack on a forked twin. Returns a result summary."""
    p = dict(params or {})
    t = twin.fork()
    if seed is not None:  # a fixed seed replays the identical attack
        t.rng = random.Random(seed)
    r = t.rng
    orders = []
    if kind == "fraud_ring":
        size = int(_clamp(p.get("size"), 3, 12, 6))
        sd = int(_clamp(p.get("shared_devices"), 1, 6, 2))
        amt = _clamp(p.get("amount"), 20, 1500, 400)
        age = int(_clamp(p.get("age_days"), 1, 365, 10))
        members, _, _ = t.spawn_ring(size=size, label="redteam-ring", shared_devices=sd, age_range=(age, age + 5))
        for m in members:
            orders.append(t.place_order(m.id, r.choice(["M-02", "M-07", "M-09"]), amt * r.uniform(0.85, 1.15),
                                        source="redteam"))
        p = {"size": size, "shared_devices": sd, "amount": amt, "age_days": age}
    elif kind == "card_testing":
        n = int(_clamp(p.get("probes"), 3, 30, 12))
        final = _clamp(p.get("final_amount"), 50, 3000, 800)
        acc = t.new_account(age_days=2, fraud=True, segment="redteam-cardtest", disposable=True, kyc=False)
        acc.devices.add(t.new_device())
        acc.ips.add(t.new_ip("VN"))
        for _ in range(n):
            orders.append(t.place_order(acc.id, "M-07", r.uniform(1, 5), source="redteam"))
            t.clock += 0.5
        orders.append(t.place_order(acc.id, "M-02", final, source="redteam"))
        p = {"probes": n, "final_amount": final}
    elif kind == "account_takeover":
        amt = _clamp(p.get("amount"), 50, 5000, 1200)
        foreign = str(p.get("foreign", True)).lower() not in ("false", "0", "no")
        victims = [a for a in t.accounts.values() if not a.fraud and a.age_days > 365]
        victim = r.choice(victims)
        dev = t.new_device()
        ip = t.new_ip(r.choice(["RU", "NG", "RO"]) if foreign else victim.country)
        o = t.place_order(victim.id, "M-02", amt, device=dev, ip=ip, source="redteam", fraud=True)
        orders.append(o)
        p = {"amount": amt, "foreign": foreign, "victim": victim.id}
    elif kind == "synthetic_identity":
        warm = int(_clamp(p.get("warmup_orders"), 0, 10, 4))
        bust = _clamp(p.get("bust_amount"), 100, 5000, 1500)
        acc = t.new_account(age_days=r.randint(200, 400), fraud=True, segment="redteam-synthetic", kyc=True)
        dev, ip = t.new_device(), t.new_ip(acc.country)
        acc.devices.add(dev)
        acc.ips.add(ip)
        for _ in range(warm):
            orders.append(t.place_order(acc.id, r.choice(list(t.merchants)), r.uniform(15, 60), source="redteam"))
            t.clock += 90
        orders.append(t.place_order(acc.id, "M-02", bust, source="redteam"))
        p = {"warmup_orders": warm, "bust_amount": bust}
    elif kind == "device_farm_evasion":
        size = int(_clamp(p.get("size"), 3, 12, 6))
        amt = _clamp(p.get("amount"), 20, 1500, 350)
        proxy = t.new_ip("US")
        for _ in range(size):
            acc = t.new_account(age_days=r.randint(3, 20), fraud=True, segment="redteam-farm", disposable=True)
            acc.devices.add(t.new_device())
            acc.ips.add(proxy)
            orders.append(t.place_order(acc.id, "M-09", amt * r.uniform(0.9, 1.1), source="redteam"))
        p = {"size": size, "amount": amt}
    elif kind == "prompt_injection":
        if shopper_guard is None:
            return {"attack": kind, "error": "no shopper guard available"}
        res = shopper_guard()
        return {"attack": kind, "params": {}, "orders": [], "fraud_usd": res.get("attempted_usd", 0),
                "stopped_usd": res.get("stopped_usd", 0), "evaded_usd": res.get("evaded_usd", 0),
                "detection_rate": res.get("detection_rate", 1.0), "notes": res.get("notes", ""),
                "agent_trace": res.get("trace", [])}
    else:
        return {"attack": kind, "error": f"unknown attack. Choose from {list(ATTACKS)}"}
    out = _summary(kind, p, orders)
    out["seed"] = seed
    return out


def scorecard(results):
    total = sum(r.get("fraud_usd", 0) for r in results)
    stopped = sum(r.get("stopped_usd", 0) for r in results)
    return {"attacks_run": len(results), "fraud_attempted_usd": round(total, 2), "stopped_usd": round(stopped, 2),
            "evaded_usd": round(total - stopped, 2),
            "resilience": round(stopped / total, 3) if total else 1.0,
            "weakest": sorted(({"attack": r["attack"], "detection_rate": r.get("detection_rate", 1)}
                               for r in results if "error" not in r), key=lambda x: x["detection_rate"])[:3]}
