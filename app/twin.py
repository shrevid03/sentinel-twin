"""The digital twin: a live graph model of a PayPal merchant ecosystem.

Every buyer account, device, IP address and merchant is a node. Edges link an
account to the devices and IPs it uses and to the merchants it buys from.
Orders created through the app (and PayPal sandbox webhooks) are mirrored into
the twin, a GAT scores every account from its neighbourhood, and the twin can
be forked so red-team attacks and what-if policies run without touching the
real state.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import threading
import time
from dataclasses import dataclass, field

import numpy as np

from .gat import GAT, auc

COUNTRIES = ["US", "US", "US", "IN", "GB", "DE", "CA", "AU", "FR", "BR"]
RISKY_COUNTRIES = ["NG", "RU", "VN", "RO"]
EMAIL_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "icloud.com", "proton.me"]
DISPOSABLE = ["mailinator.com", "tempmail.dev", "10minute.email"]
FIRST = ["Ava", "Liam", "Noah", "Mia", "Zoe", "Arjun", "Priya", "Sofia", "Leo", "Emma", "Kai", "Isha",
         "Omar", "Lena", "Maya", "Ravi", "Nina", "Jon", "Tara", "Ben", "Aria", "Dev", "Ella", "Sam"]
LAST = ["Shah", "Kim", "Lopez", "Patel", "Nguyen", "Smith", "Rossi", "Khan", "Meyer", "Silva",
        "Brown", "Iyer", "Cohen", "Ali", "Wong", "Park"]
MERCHANTS = [
    ("M-01", "Brewline Coffee Co.", "coffee"), ("M-02", "Pixel Forge Electronics", "electronics"),
    ("M-03", "Northleaf Books", "books"), ("M-04", "Atlas Outdoor Gear", "outdoor"),
    ("M-05", "Lumen Home Studio", "home"), ("M-06", "Kinetic Sportswear", "apparel"),
    ("M-07", "GiftCard Galaxy", "gift_cards"), ("M-08", "Verde Plant Shop", "plants"),
    ("M-09", "Orbit Gaming Store", "gaming"), ("M-10", "Saffron Kitchen Supply", "kitchen"),
]
FEATURES = ["is_account", "is_device", "is_ip", "is_merchant", "account_age", "order_count",
            "avg_amount", "max_amount", "velocity", "device_count", "ip_count", "geo_mismatch",
            "kyc_verified", "disposable_email", "degree"]

DEFAULT_POLICY = {"review_threshold": 0.5, "block_threshold": 0.8, "max_auto_amount": 1000.0,
                  "review_new_device_over": 300.0, "review_spend_multiple": 0.0}


@dataclass
class Account:
    id: str
    name: str
    country: str
    age_days: int
    email: str
    kyc: bool
    fraud: bool = False
    segment: str = "legit"
    status: str = "active"
    devices: set = field(default_factory=set)
    ips: set = field(default_factory=set)


class Twin:
    def __init__(self, seed: int = 11):
        self.rng = random.Random(seed)
        self.lock = threading.RLock()
        self.clock = 0.0  # simulated minutes
        self.accounts: dict[str, Account] = {}
        self.devices: set[str] = set()
        self.ips: dict[str, str] = {}  # ip -> country
        self.merchants = {m[0]: {"id": m[0], "name": m[1], "category": m[2]} for m in MERCHANTS}
        self.orders: list[dict] = []
        self.events: list[dict] = []
        self.policy = dict(DEFAULT_POLICY)
        self.model: GAT | None = None
        self.metrics: dict = {}
        self._probs: dict[str, float] = {}
        self._dirty = True
        self._n = {"A": 0, "D": 0, "IP": 0, "O": 0}
        self._populate()

    # ----------------------------------------------------------- id helpers
    def _next(self, kind):
        self._n[kind] += 1
        return f"{kind}-{self._n[kind]:03d}" if kind != "O" else f"ORD-{self._n[kind]:05d}"

    def new_device(self):
        d = self._next("D")
        self.devices.add(d)
        return d

    def new_ip(self, country):
        ip = self._next("IP")
        self.ips[ip] = country
        return ip

    def new_account(self, *, country=None, age_days=None, fraud=False, segment="legit",
                    disposable=False, kyc=None, name=None):
        r = self.rng
        aid = self._next("A")
        name = name or f"{r.choice(FIRST)} {r.choice(LAST)}"
        dom = r.choice(DISPOSABLE) if disposable else r.choice(EMAIL_DOMAINS)
        acc = Account(
            id=aid, name=name, country=country or r.choice(COUNTRIES),
            age_days=age_days if age_days is not None else int(r.expovariate(1 / 500)) + 3,
            email=f"{name.split()[0].lower()}.{aid[-3:]}@{dom}",
            kyc=(r.random() < 0.85) if kyc is None else kyc, fraud=fraud, segment=segment,
        )
        self.accounts[aid] = acc
        self._dirty = True
        return acc

    # ------------------------------------------------------- initial world
    # ------------------------------------------------------ policy version
    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, value):
        self._policy = dict(value)
        self._policy_applied_at = time.strftime("%Y-%m-%d %H:%M:%S")

    def policy_version(self):
        """Short content hash of the live decision policy plus when it was applied (for receipts)."""
        h = hashlib.sha256(json.dumps(self._policy, sort_keys=True).encode()).hexdigest()[:8]
        return {"hash": h, "applied_at": getattr(self, "_policy_applied_at", None), "policy": dict(self._policy)}

    def _populate(self):
        r = self.rng
        cafe_ips = [self.new_ip("US"), self.new_ip("GB")]  # shared public wifi: hard negatives
        households = []
        for _ in range(170):
            if households and r.random() < 0.2:  # family members share a device and IP
                fam = r.choice(households)
                acc = self.new_account(country=fam.country)
                acc.devices |= set(list(fam.devices)[:1])
                acc.ips |= set(fam.ips)
            else:
                acc = self.new_account()
                acc.devices.add(self.new_device())
                if r.random() < 0.3:
                    acc.devices.add(self.new_device())
                acc.ips.add(self.new_ip(acc.country))
                households.append(acc)
            if r.random() < 0.12:
                acc.ips.add(r.choice(cafe_ips))
            for _ in range(r.randint(1, 6)):
                self._hist_order(acc, r.choice(list(acc.devices)), r.choice(list(acc.ips)))
        for ring in range(5):
            self.spawn_ring(size=r.randint(5, 8), label=f"ring-{ring + 1}", history=True)
        for _ in range(10):  # low-and-slow synthetic identities: look clean alone
            acc = self.new_account(age_days=r.randint(60, 300), fraud=True, segment="synthetic", kyc=True)
            acc.devices.add(self.new_device())
            acc.ips.add(self.new_ip(acc.country))
            for _ in range(r.randint(2, 4)):
                self._hist_order(acc, next(iter(acc.devices)), next(iter(acc.ips)),
                                 amount=r.uniform(80, 400), fraud=True)
        self.orders.sort(key=lambda o: o["ts"])

    def spawn_ring(self, size=6, label="ring", history=False, shared_devices=2, shared_ips=2,
                   country=None, age_range=(1, 40), amount_range=(150, 900), disposable_rate=0.6):
        r = self.rng
        devs = [self.new_device() for _ in range(shared_devices)]
        ipc = country or r.choice(RISKY_COUNTRIES + ["US"])
        ips = [self.new_ip(ipc) for _ in range(shared_ips)]
        members = []
        for _ in range(size):
            acc = self.new_account(country=r.choice(COUNTRIES), age_days=r.randint(*age_range), fraud=True,
                                   segment=label, disposable=r.random() < disposable_rate, kyc=r.random() < 0.3)
            acc.devices.update(r.sample(devs, k=min(len(devs), r.randint(1, 2))))
            acc.ips.update(r.sample(ips, k=min(len(ips), r.randint(1, 2))))
            members.append(acc)
            if history:
                for _ in range(r.randint(2, 5)):
                    self._hist_order(acc, r.choice(list(acc.devices)), r.choice(list(acc.ips)),
                                     amount=r.uniform(*amount_range), fraud=True,
                                     merchant=r.choice(["M-02", "M-07", "M-09", "M-02"]))
        return members, devs, ips

    def _hist_order(self, acc, device, ip, amount=None, fraud=False, merchant=None):
        r = self.rng
        amount = amount or round(r.lognormvariate(3.6, 0.7), 2)
        self.orders.append({
            "id": self._next("O"), "account": acc.id, "merchant": merchant or r.choice(list(self.merchants)),
            "amount": round(min(amount, 4000), 2), "ts": -r.uniform(0, 60 * 24 * 30), "device": device, "ip": ip,
            "ip_country": self.ips.get(ip, acc.country), "status": "captured", "risk": None, "decision": "approve",
            "fraud": fraud, "source": "history", "paypal_order_id": None, "factors": [],
        })

    # --------------------------------------------------------------- graph
    def _account_orders(self):
        by = {}
        for o in self.orders:
            if o["status"] != "blocked":
                by.setdefault(o["account"], []).append(o)
        return by

    def build_graph(self, extra=None):
        """Return node ids, feature matrix X and adjacency mask.

        extra: optional dict(account, device, ip, merchant, amount) for a tentative
        order that is scored without being committed.
        """
        accs = list(self.accounts.values())
        nodes = [a.id for a in accs] + sorted(self.devices) + sorted(self.ips) + list(self.merchants)
        idx = {n: i for i, n in enumerate(nodes)}
        N = len(nodes)
        mask = np.eye(N, dtype=bool)
        by = self._account_orders()
        if extra:
            by = dict(by)
            by[extra["account"]] = by.get(extra["account"], []) + [
                {"amount": extra["amount"], "ts": self.clock, "merchant": extra["merchant"],
                 "ip_country": self.ips.get(extra["ip"], "US")}]

        def link(a, b):
            i, j = idx[a], idx[b]
            mask[i, j] = mask[j, i] = True

        for a in accs:
            devs, ips = set(a.devices), set(a.ips)
            if extra and extra["account"] == a.id:
                devs.add(extra["device"])
                ips.add(extra["ip"])
            for d in devs:
                link(a.id, d)
            for ip in ips:
                link(a.id, ip)
            for o in by.get(a.id, []):
                link(a.id, o["merchant"])

        X = np.zeros((N, len(FEATURES)))
        X[:, 0] = [1 if n.startswith("A-") else 0 for n in nodes]
        for i, a in enumerate(accs):
            os_ = by.get(a.id, [])
            amts = [o["amount"] for o in os_] or [0]
            recent = sum(1 for o in os_ if o["ts"] > self.clock - 60)
            mism = np.mean([o["ip_country"] != a.country for o in os_]) if os_ else 0
            n_dev = len(a.devices) + (1 if extra and extra["account"] == a.id and extra["device"] not in a.devices else 0)
            X[i, 4:14] = [math.log1p(a.age_days) / math.log1p(2000), math.log1p(len(os_)) / 3,
                          math.log1p(np.mean(amts)) / 8, math.log1p(max(amts)) / 8, min(recent / 5, 1),
                          n_dev / 4, len(a.ips) / 4, mism, float(a.kyc),
                          float(a.email.split("@")[1] in DISPOSABLE)]
        deg = mask.sum(axis=1) - 1
        X[:, 14] = np.log1p(deg) / 5
        nA = len(accs)
        for i in range(nA, N):
            n = nodes[i]
            X[i, 1] = n.startswith("D-")
            X[i, 2] = n.startswith("IP-")
            X[i, 3] = n.startswith("M-")
            if not X[i, 3]:  # devices / IPs summarise the accounts behind them
                nb = np.where(mask[i, :nA])[0]
                if len(nb):
                    X[i, 4:14] = X[nb, 4:14].mean(axis=0)
        return nodes, idx, X, mask

    # --------------------------------------------------------------- model
    def train(self, epochs=150):
        with self.lock:
            nodes, idx, X, mask = self.build_graph()
            accs = [n for n in nodes if n.startswith("A-")]
            y = np.zeros(len(nodes), dtype=int)
            for a in accs:
                y[idx[a]] = int(self.accounts[a].fraud)
            rr = np.random.default_rng(5)
            pos = rr.permutation([idx[a] for a in accs if self.accounts[a].fraud])
            neg = rr.permutation([idx[a] for a in accs if not self.accounts[a].fraud])

            def split(arr):
                a, b = int(len(arr) * 0.6), int(len(arr) * 0.8)
                return arr[:a], arr[a:b], arr[b:]

            (ptr, pva, pte), (ntr, nva, nte) = split(pos), split(neg)
            tr, va, te = np.r_[ptr, ntr], np.r_[pva, nva], np.r_[pte, nte]
            self._split = {"X": X, "y": y, "tr": tr, "va": va, "te": te}
            self.model = GAT(len(FEATURES), hidden=8, heads=4)
            hist = self.model.fit(X, mask, y, tr, va, epochs=epochs)
            P = self.model.predict_proba(X, mask)
            te_pred = P[te] >= 0.5
            tp = int(np.sum(te_pred & (y[te] == 1)))
            self.metrics = {
                "test_auc": round(auc(y[te], P[te]), 4),
                "precision": round(tp / max(int(te_pred.sum()), 1), 3),
                "recall": round(tp / max(int((y[te] == 1).sum()), 1), 3),
                "train_nodes": int(len(tr)), "test_nodes": int(len(te)), "history": hist,
                "graph": {"nodes": len(nodes), "edges": int((mask.sum() - len(nodes)) / 2)},
                "heads": self.model.n_heads, "features": FEATURES,
            }
            self._dirty = True
            self.refresh()
            by = self._account_orders()
            for o in self.orders:  # back-fill scores on mirrored history so what-if has traffic to replay
                if o.get("risk") is None:
                    others = [x["amount"] for x in by.get(o["account"], []) if x is not o]
                    o["spend_ratio"] = round(o["amount"] / ((np.mean(others) if others else 60.0) + 20), 2)
                    o["risk"] = round(self._probs.get(o["account"], 0) * 0.95, 3)
                    o["decision"] = self.decide(o["risk"], o["amount"], False)
            return self.metrics

    def refresh(self):
        with self.lock:
            if not self._dirty or self.model is None:
                return
            nodes, idx, X, mask = self.build_graph()
            P = self.model.predict_proba(X, mask)
            self._probs = {n: float(P[i]) for i, n in enumerate(nodes)}
            # devices and IPs inherit the strongest risk among their accounts
            nA = sum(1 for n in nodes if n.startswith("A-"))
            for i in range(nA, len(nodes)):
                nb = np.where(mask[i, :nA])[0]
                if len(nb) and not nodes[i].startswith("M-"):
                    self._probs[nodes[i]] = float(np.max(P[nb]))
            self._graph_cache = (nodes, idx, mask)
            self._dirty = False

    def risk(self, node):
        self.refresh()
        return self._probs.get(node, 0.0)

    def explain(self, node_id, top=6):
        """Which neighbours did the GAT attend to when scoring this node?"""
        with self.lock:
            self.refresh()
            nodes, idx, X, mask = self.build_graph()
            self.model.forward(X, mask)
            i = idx[node_id]
            a1 = np.mean([a[i] for a in self.model.attn1], axis=0)
            a2 = self.model.attn2[i]
            att = 0.5 * a1 + 0.5 * a2
            per_head = [a[i] for a in self.model.attn1]
            nb = [j for j in np.argsort(-att) if mask[i, j] and j != i][:top]
            out = []
            for j in nb:
                nid = nodes[j]
                shared = int(mask[j, : len(self.accounts)].sum()) - (1 if nid.startswith("A-") else 0)
                out.append({"node": nid, "type": _ntype(nid), "attention": round(float(att[j]), 4),
                            "head_attention": [round(float(h[j]), 3) for h in per_head],
                            "risk": round(self._probs.get(nid, 0), 3), "accounts_linked": shared})
            feats = {f: round(float(X[i, k]), 3) for k, f in enumerate(FEATURES) if k >= 4}
            return {"node": node_id, "risk": round(self._probs.get(node_id, 0), 3),
                    "self_attention": round(float(att[i]), 4), "top_neighbors": out, "features": feats}

    # ------------------------------------------------------------- orders
    def score_order(self, account, merchant, amount, device, ip):
        """Score a tentative order: GAT on the would-be graph + transaction signals."""
        with self.lock:
            acc = self.accounts[account]
            nodes, idx, X, mask = self.build_graph(
                extra={"account": account, "device": device, "ip": ip, "merchant": merchant, "amount": amount})
            P = self.model.predict_proba(X, mask)
            g_now = float(P[idx[account]])
            before = self.risk(account)
            dev_others = [a for a in self.accounts.values() if device in a.devices and a.id != account]
            dev_risk = max((self._probs.get(a.id, 0) for a in dev_others), default=0.0)
            hist = [o for o in self.orders if o["account"] == account and o["status"] != "blocked"]
            avg = np.mean([o["amount"] for o in hist]) if hist else 60.0
            velocity = sum(1 for o in hist if o["ts"] > self.clock - 60)
            new_device = device not in acc.devices
            geo = self.ips.get(ip, acc.country) != acc.country
            factors = []
            t = 0.0
            if new_device:
                t += 0.25
                factors.append("new device for this account")
            if geo:
                t += 0.25
                factors.append(f"IP country {self.ips.get(ip)} differs from account country {acc.country}")
            ratio = amount / (avg + 20)
            if ratio > 2:
                t += 0.2 * min(ratio / 6, 1)
                factors.append(f"amount is {ratio:.1f}x this buyer's usual spend")
            if velocity >= 3:
                t += 0.15 * min(velocity / 6, 1)
                factors.append(f"{velocity} orders in the last hour")
            if acc.age_days < 7:
                t += 0.15
                factors.append(f"account is only {acc.age_days} days old")
            if acc.status == "frozen":
                t = 1.0
                factors.append("account is frozen by an investigator")
            g = max(g_now, 0.9 * dev_risk)
            if dev_risk > 0.5:
                factors.append(f"device shared with {len(dev_others)} account(s), highest GAT risk {dev_risk:.2f}")
            if g_now - before > 0.1:
                factors.append(f"GAT risk jumps {before:.2f} -> {g_now:.2f} once this order's links are added")
            elif g_now > 0.5:
                factors.append(f"GAT flags this account's neighbourhood ({g_now:.2f})")
            risk = 1 - (1 - g) * (1 - min(t, 1) * 0.75)
            return {"risk": round(float(risk), 3), "spend_ratio": round(float(ratio), 2), "gat_risk": round(g_now, 3), "gat_before": round(before, 3),
                    "device_risk": round(dev_risk, 3), "txn_score": round(min(t, 1), 3), "factors": factors}

    def decide(self, risk, amount, new_device, policy=None, spend_ratio=0.0):
        p = {**DEFAULT_POLICY, **(policy or self.policy)}
        if risk >= p["block_threshold"]:
            return "block"
        if risk >= p["review_threshold"] or amount > p["max_auto_amount"] or (
                new_device and amount > p["review_new_device_over"]) or (
                p["review_spend_multiple"] and spend_ratio >= p["review_spend_multiple"]):
            return "review"
        return "approve"

    def place_order(self, account, merchant, amount, device=None, ip=None, source="simulated",
                    fraud=None, paypal_order_id=None, items=None):
        with self.lock:
            acc = self.accounts[account]
            device = device or next(iter(acc.devices), None) or self.new_device()
            ip = ip or next(iter(acc.ips), None) or self.new_ip(acc.country)
            if device not in self.devices:
                self.devices.add(device)
            if ip not in self.ips:
                self.ips[ip] = acc.country
            s = self.score_order(account, merchant, amount, device, ip)
            new_device = device not in acc.devices
            decision = self.decide(s["risk"], amount, new_device, spend_ratio=s["spend_ratio"])
            order = {
                "id": self._next("O"), "account": account, "merchant": merchant, "amount": round(amount, 2),
                "ts": self.clock, "device": device, "ip": ip, "ip_country": self.ips[ip],
                "status": {"approve": "approved", "review": "review", "block": "blocked"}[decision],
                "risk": s["risk"], "gat_risk": s["gat_risk"], "txn_score": s["txn_score"], "decision": decision,
                "fraud": acc.fraud if fraud is None else fraud, "source": source,
                "paypal_order_id": paypal_order_id, "factors": s["factors"], "new_device": new_device, "spend_ratio": s["spend_ratio"],
                "items": items or [], "new_device_flag": new_device,
            }
            self.orders.append(order)
            if decision != "block":
                acc.devices.add(device)
                acc.ips.add(ip)
            self._dirty = True
            self._event("order", f"{order['id']} {acc.name} ${amount:.2f} at {self.merchants[merchant]['name']}"
                                 f" -> {decision.upper()} (risk {s['risk']:.2f})", order=order["id"],
                        level={"approve": "ok", "review": "warn", "block": "bad"}[decision])
            return order

    def _event(self, kind, text, level="info", **kw):
        self._seq = getattr(self, "_seq", 0) + 1
        ev = {"seq": self._seq, "ts": round(self.clock, 1), "kind": kind, "text": text, "level": level, **kw}
        self.events.append(ev)
        self.events = self.events[-300:]
        if getattr(self, "on_event", None):
            self.on_event(ev)

    # --------------------------------------------------------- simulation
    def tick(self, n=6, fraud_rate=0.15):
        """Advance the twin by a few minutes of synthetic live traffic."""
        r = self.rng
        out = []
        with self.lock:
            self.clock += r.uniform(3, 8)
            legit = [a for a in self.accounts.values() if not a.fraud and a.status == "active"]
            bad = [a for a in self.accounts.values() if a.fraud and a.status == "active"]
            for _ in range(n):
                if bad and r.random() < fraud_rate:
                    a = r.choice(bad)
                    amt = r.uniform(120, 900)
                    m = r.choice(["M-02", "M-07", "M-09"])
                else:
                    a = r.choice(legit)
                    amt = round(r.lognormvariate(3.6, 0.6), 2)
                    m = r.choice(list(self.merchants))
                    roll = r.random()
                    if roll < 0.06:  # real customers make the odd big purchase
                        amt = round(amt * r.uniform(3, 8), 2)
                    elif roll < 0.10:  # and buy from a new phone
                        out.append(self.place_order(a.id, m, round(amt * r.uniform(1, 6), 2), self.new_device(),
                                                    r.choice(list(a.ips))))
                        continue
                out.append(self.place_order(a.id, m, amt, r.choice(list(a.devices)), r.choice(list(a.ips))))
        return out

    def what_if(self, policy, last_n=400, extra_orders=None):
        """Replay recent scored orders (plus red-team attack orders) under a proposed policy."""
        scored = [o for o in self.orders if o.get("risk") is not None][-last_n:] + list(extra_orders or [])

        def run(p):
            res = {"approved": 0, "review": 0, "blocked": 0, "fraud_caught_usd": 0.0, "fraud_missed_usd": 0.0,
                   "good_blocked_usd": 0.0, "good_reviewed": 0, "fraud_total_usd": 0.0,
                   "good_blocked": 0, "good_total": 0, "fraud_blocked_usd": 0.0, "fraud_reviewed_usd": 0.0}
            for o in scored:
                d = self.decide(o["risk"], o["amount"], o.get("new_device", False), p, o.get("spend_ratio", 0))
                res[{"approve": "approved", "review": "review", "block": "blocked"}[d]] += 1
                if o["fraud"]:
                    res["fraud_total_usd"] += o["amount"]
                    if d == "approve":
                        res["fraud_missed_usd"] += o["amount"]
                    else:  # "caught" = intercepted: blocked or sent to review
                        res["fraud_caught_usd"] += o["amount"]
                        res["fraud_blocked_usd" if d == "block" else "fraud_reviewed_usd"] += o["amount"]
                else:
                    res["good_total"] += 1
                    if d == "block":
                        res["good_blocked_usd"] += o["amount"]
                        res["good_blocked"] += 1
                    if d == "review":
                        res["good_reviewed"] += 1
            for k in list(res):
                if k.endswith("usd"):
                    res[k] = round(res[k], 2)
            res["catch_rate"] = round(res["fraud_caught_usd"] / max(res["fraud_total_usd"], 1), 3)
            return res

        merged = {**self.policy, **policy}
        return {"orders_replayed": len(scored), "attack_orders": len(extra_orders or []), "current": run(self.policy), "proposed": run(merged),
                "current_policy": self.policy, "proposed_policy": merged}

    # ------------------------------------------------- rules vs graph
    def compare_engines(self, extra_orders=None, hardened_policy=None, last_n=400, review_cost=4.0):
        """Replay the same orders through (a) rules only, (b) GAT + rules, (c) GAT + rules under a hardened policy.

        Only orders scored live (with a stored rules score) are used, so every engine sees identical inputs.
        "Intercepted" = blocked or sent to review; blocked and reviewed fraud dollars are reported separately.
        """
        recent = [o for o in self.orders if o.get("txn_score") is not None][-last_n:]
        orders = recent + [o for o in (extra_orders or []) if o.get("txn_score") is not None]
        engines = {
            "rules_only": (lambda o: o["txn_score"], dict(DEFAULT_POLICY)),  # rules at full 0-1 scale: the fairest baseline
            "gat_rules": (lambda o: o["risk"], dict(DEFAULT_POLICY)),
        }
        if hardened_policy:
            engines["gat_rules_hardened"] = (lambda o: o["risk"], {**DEFAULT_POLICY, **hardened_policy})

        def kind(o):
            return o.get("attack") or ("live fraud traffic" if o["fraud"] else None)

        out = {"orders": len(orders), "attack_orders": len(orders) - len(recent), "review_cost_usd": review_cost,
               "engines": {}, "by_attack": {}}
        for name, (score, pol) in engines.items():
            m = {"fraud_total_usd": 0.0, "fraud_blocked_usd": 0.0, "fraud_reviewed_usd": 0.0, "fraud_missed_usd": 0.0,
                 "good_total": 0, "good_reviewed": 0, "good_blocked": 0, "good_blocked_usd": 0.0}
            per = {}
            for o in orders:
                d = self.decide(score(o), o["amount"], o.get("new_device", False), pol, o.get("spend_ratio", 0))
                if o["fraud"]:
                    m["fraud_total_usd"] += o["amount"]
                    key = {"block": "fraud_blocked_usd", "review": "fraud_reviewed_usd", "approve": "fraud_missed_usd"}[d]
                    m[key] += o["amount"]
                    k = kind(o)
                    pk = per.setdefault(k, {"total_usd": 0.0, "intercepted_usd": 0.0})
                    pk["total_usd"] += o["amount"]
                    if d != "approve":
                        pk["intercepted_usd"] += o["amount"]
                else:
                    m["good_total"] += 1
                    if d == "review":
                        m["good_reviewed"] += 1
                    elif d == "block":
                        m["good_blocked"] += 1
                        m["good_blocked_usd"] += o["amount"]
            m = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in m.items()}
            m["fraud_intercepted_usd"] = round(m["fraud_blocked_usd"] + m["fraud_reviewed_usd"], 2)
            m["intercept_rate"] = round(m["fraud_intercepted_usd"] / max(m["fraud_total_usd"], 1), 3)
            m["false_positive_cost_usd"] = round(m["good_blocked_usd"] + review_cost * m["good_reviewed"], 2)
            out["engines"][name] = m
            for k, v in per.items():
                out["by_attack"].setdefault(k, {"total_usd": round(v["total_usd"], 2)})[name] = round(
                    v["intercepted_usd"] / max(v["total_usd"], 1e-9), 3)
        # the honest headline: red-team attack orders only (fresh accounts the GAT never saw a label for)
        unseen = {}
        for name, (score, pol) in engines.items():
            tot = icp = 0.0
            for o in orders:
                if o.get("attack") and o["fraud"]:
                    tot += o["amount"]
                    if self.decide(score(o), o["amount"], o.get("new_device", False), pol,
                                   o.get("spend_ratio", 0)) != "approve":
                        icp += o["amount"]
            unseen[name] = {"total_usd": round(tot, 2), "intercepted_usd": round(icp, 2),
                            "intercept_rate": round(icp / max(tot, 1e-9), 3)}
        out["unseen_attacks"] = unseen
        out["account_auc"] = self.account_auc()
        return out

    def account_auc(self):
        """Held-out account AUC: the same node features with no graph (logistic regression) vs the GAT."""
        sp = getattr(self, "_split", None)
        if not sp or self.model is None:
            return None
        X, y, tr, te = sp["X"], sp["y"], sp["tr"], sp["te"]
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6
        Z = (X - mu) / sd
        w, b = np.zeros(X.shape[1]), 0.0
        for _ in range(800):  # plain logistic regression, L2, gradient descent
            p = 1 / (1 + np.exp(-(Z[tr] @ w + b)))
            g = p - y[tr]
            w -= 0.1 * (Z[tr].T @ g / len(tr) + 1e-3 * w)
            b -= 0.1 * g.mean()
        rules_p = 1 / (1 + np.exp(-(Z[te] @ w + b)))
        return {"test_accounts": int(len(te)), "features_only_no_graph": round(float(auc(y[te], rules_p)), 4),
                "gat": self.metrics.get("test_auc")}

    # ------------------------------------------------------ investigation
    def linked_accounts(self, account, hops=2):
        acc = self.accounts[account]
        seen, frontier, via = {account}, [acc], {}
        for _ in range(hops):
            nxt = []
            for a in frontier:
                for b in self.accounts.values():
                    if b.id in seen:
                        continue
                    shared = (a.devices & b.devices) | (a.ips & b.ips)
                    if shared:
                        seen.add(b.id)
                        via[b.id] = sorted(shared)
                        nxt.append(b)
            frontier = nxt
        return [{"account": b, "name": self.accounts[b].name, "shared": via[b], "risk": round(self.risk(b), 3),
                 "status": self.accounts[b].status, "age_days": self.accounts[b].age_days} for b in via]

    def account_view(self, account):
        a = self.accounts[account]
        orders = [o for o in self.orders if o["account"] == account]
        return {"id": a.id, "name": a.name, "country": a.country, "age_days": a.age_days, "email": a.email,
                "kyc_verified": a.kyc, "status": a.status, "devices": sorted(a.devices), "ips": sorted(a.ips),
                "risk": round(self.risk(account), 3), "order_count": len(orders),
                "total_spend": round(sum(o["amount"] for o in orders), 2),
                "recent_orders": [_public(o) for o in orders[-8:]]}

    def freeze(self, account, reason=""):
        with self.lock:
            self.accounts[account].status = "frozen"
            self._event("action", f"{account} restricted (merchant-side, simulated): {reason}", level="bad")

    def flagged(self, k=10):
        self.refresh()
        accs = [a for a in self.accounts.values() if a.status == "active"]
        accs.sort(key=lambda a: -self._probs.get(a.id, 0))
        return [{"account": a.id, "name": a.name, "risk": round(self._probs.get(a.id, 0), 3),
                 "age_days": a.age_days, "devices": len(a.devices)} for a in accs[:k]]

    # -------------------------------------------------------------- views
    def stats(self):
        self.refresh()
        live = [o for o in self.orders if o["source"] != "history"]
        acc_risk = [self._probs.get(a, 0) for a in self.accounts]
        return {
            "accounts": len(self.accounts), "devices": len(self.devices), "ips": len(self.ips),
            "merchants": len(self.merchants), "orders": len(self.orders), "live_orders": len(live),
            "approved": sum(o["decision"] == "approve" for o in live),
            "review": sum(o["decision"] == "review" for o in live),
            "blocked": sum(o["decision"] == "block" for o in live),
            "blocked_usd": round(sum(o["amount"] for o in live if o["decision"] == "block"), 2),
            "high_risk_accounts": int(sum(p >= 0.5 for p in acc_risk)),
            "frozen": sum(a.status == "frozen" for a in self.accounts.values()),
            "clock_min": round(self.clock, 1), "model": {k: v for k, v in self.metrics.items() if k != "history"},
            "policy": self.policy,
        }

    def graph_view(self, focus=None, max_accounts=140):
        self.refresh()
        if focus and focus in self.accounts:
            ids = {focus} | {x["account"] for x in self.linked_accounts(focus, hops=2)}
        else:
            ranked = sorted(self.accounts.values(), key=lambda a: -self._probs.get(a.id, 0))
            top = ranked[:60]
            rest = self.rng.sample(ranked[60:], k=min(max_accounts - 60, len(ranked) - 60))
            ids = {a.id for a in top + rest}
        nodes, edges, seen = [], [], set()
        for aid in ids:
            a = self.accounts[aid]
            nodes.append({"id": aid, "label": a.name.split()[0], "type": "account",
                          "risk": round(self._probs.get(aid, 0), 3), "status": a.status})
            for d in a.devices | a.ips:
                if d not in seen:
                    seen.add(d)
                    nodes.append({"id": d, "label": d, "type": _ntype(d), "risk": round(self._probs.get(d, 0), 3)})
                edges.append({"from": aid, "to": d})
        return {"nodes": nodes, "edges": edges}

    def fork(self):
        with self.lock:
            # Never touch the live twin's lock or hook while copying: other request threads may be
            # using them. The memo makes deepcopy give the fork a fresh lock and no event hook.
            memo = {id(self.lock): threading.RLock()}
            hook = getattr(self, "on_event", None)
            if hook is not None:
                memo[id(hook)] = None
            twin = copy.deepcopy(self, memo)
            twin.on_event = None
            return twin


def _ntype(n):
    return "account" if n.startswith("A-") else "device" if n.startswith("D-") else "ip" if n.startswith(
        "IP-") else "merchant"


def _public(o):
    return {k: o.get(k) for k in ("id", "account", "merchant", "amount", "status", "decision", "risk", "source",
                                  "paypal_order_id", "device", "ip", "ip_country", "factors", "ts")}
