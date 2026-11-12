"""Sentinel Twin API server (FastAPI). Run: uvicorn app.main:app --reload"""
from __future__ import annotations

import hmac
import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from . import integrations  # noqa: E402
from .agents import LANGS, CaptureRefused, Team  # noqa: E402
from .drill import defense_drill  # noqa: E402
from .paypal import PayPal, PayPalError  # noqa: E402
from .redteam import ATTACKS, run_attack  # noqa: E402
from .twin import Twin, _public  # noqa: E402

STATIC = Path(__file__).resolve().parent.parent / "static"

twin = Twin(seed=int(os.getenv("TWIN_SEED", "3")))
twin.on_event = integrations.publish
twin.train(epochs=int(os.getenv("GAT_EPOCHS", "120")))
paypal = PayPal()
team = Team(twin, paypal)


def require_admin(x_admin_token: str | None = Header(default=None)):
    """If ADMIN_TOKEN is set (public deploys), admin actions need the X-Admin-Token header. Unset = open (local)."""
    tok = os.getenv("ADMIN_TOKEN", "").strip()
    if tok and not hmac.compare_digest((x_admin_token or "").encode(), tok.encode()):
        raise HTTPException(401, "admin token required: send the X-Admin-Token header")


ADMIN = [Depends(require_admin)]
_reset_lock = threading.Lock()
auto = {"on": os.getenv("AUTO_TRAFFIC", "1") == "1", "n": 3}

app = FastAPI(title="Sentinel Twin API", version="1.0.0",
              description="Digital twin + GAT risk engine + agent team on the PayPal developer platform.")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _traffic():
    while True:
        time.sleep(5)
        if auto["on"]:
            try:
                twin.tick(auto["n"], fraud_rate=0.12)
            except Exception as e:  # keep the simulator alive
                print("tick error", e)


threading.Thread(target=_traffic, daemon=True).start()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/healthz", include_in_schema=False)
def health():
    return {"ok": True}


# ------------------------------------------------------------------ config
@app.get("/api/config")
def config():
    return {"paypal_mode": paypal.mode, "paypal_client_id": paypal.client_id if paypal.live else "",
            "brain": team.brain.label, "model": team.brain.model,
            "languages": LANGS, "integrations": integrations.status, "auto_traffic": auto["on"],
            "buyer": team.buyer, "attacks": ATTACKS}


@app.get("/api/stats")
def stats():
    return twin.stats()


@app.get("/api/graph")
def graph(focus: str | None = None):
    return twin.graph_view(focus)


@app.get("/api/events")
def events(since: int = 0):
    return [e for e in twin.events if e["seq"] > since][-80:]


@app.get("/api/orders")
def orders(limit: int = 600):
    out = []
    for o in twin.orders[-limit:][::-1]:
        p = _public(o)
        p["buyer"] = twin.accounts[o["account"]].name
        p["merchant_name"] = twin.merchants[o["merchant"]]["name"]
        p["factors"] = "; ".join(o.get("factors") or [])
        out.append(p)
    return out


@app.get("/api/accounts")
def accounts():
    twin.refresh()
    by = {}
    for o in twin.orders:
        by.setdefault(o["account"], []).append(o["amount"])
    return [{"id": a.id, "name": a.name, "country": a.country, "age_days": a.age_days, "kyc": a.kyc,
             "email_domain": a.email.split("@")[1], "devices": len(a.devices), "ips": len(a.ips),
             "orders": len(by.get(a.id, [])), "spend": round(sum(by.get(a.id, [])), 2),
             "risk": round(twin.risk(a.id), 3), "status": a.status} for a in twin.accounts.values()]


@app.get("/api/account/{account_id}")
def account(account_id: str):
    if account_id not in twin.accounts:
        raise HTTPException(404, "unknown account")
    return {**twin.account_view(account_id), "linked": twin.linked_accounts(account_id)[:20]}


@app.get("/api/explain/{node_id}")
def explain(node_id: str):
    try:
        return twin.explain(node_id)
    except KeyError:
        raise HTTPException(404, "unknown node")


@app.get("/api/model")
def model():
    return twin.metrics


@app.post("/api/model/retrain", dependencies=ADMIN)
def retrain():
    m = twin.train(epochs=int(os.getenv("GAT_EPOCHS", "120")))
    twin._event("model", f"GAT retrained on {m['graph']['nodes']} nodes: test AUC {m['test_auc']}", level="ok")
    return m


class SimIn(BaseModel):
    n: int = 10
    fraud_rate: float = 0.15
    auto: bool | None = None


@app.post("/api/simulate")
def simulate(body: SimIn):
    if body.auto is not None:
        auto["on"] = body.auto
        return {"auto_traffic": auto["on"]}
    res = twin.tick(min(body.n, 100), body.fraud_rate)
    return {"orders": [_public(o) for o in res]}


# ------------------------------------------------------------------ agents
class ChatIn(BaseModel):
    text: str
    session: str = "default"
    lang: str = "en-IN"


@app.post("/api/chat")
def chat(body: ChatIn):
    try:
        return team.concierge(body.session, body.text, body.lang)
    except Exception as e:
        raise HTTPException(500, f"agent error: {e}")


class InvIn(BaseModel):
    account: str | None = None
    lang: str = "en-IN"


@app.post("/api/investigate")
def investigate(body: InvIn):
    trace = []
    case = team.investigate(body.account, trace, body.lang)
    return {"case": case, "trace": trace}


@app.get("/api/cases")
def cases():
    return team.cases[::-1]


class RTIn(BaseModel):
    focus: str | None = None
    lang: str = "en-IN"


@app.post("/api/redteam")
def redteam(body: RTIn):
    trace = []
    run = team.red_team(trace, body.lang, body.focus)
    return {"run": run, "trace": trace}


class AttackIn(BaseModel):
    attack: str
    params: dict = {}


@app.post("/api/redteam/attack")
def attack(body: AttackIn):
    trace = []
    return {"result": run_attack(twin, body.attack, body.params, shopper_guard=lambda: team.injection_probe(trace)),
            "trace": trace}


class DrillIn(BaseModel):
    seed: int = 7
    apply: bool = False


LAST_DRILL: dict = {}


@app.post("/api/drill")
def drill(body: DrillIn, x_admin_token: str | None = Header(default=None)):
    """One-click defense drill: attack, search for a safer policy, replay the same attack, optionally apply."""
    if body.apply:  # applying changes the live policy: an admin action
        require_admin(x_admin_token)
    res = defense_drill(twin, seed=body.seed, apply=body.apply)
    team.last_attack_orders = [o for r in res["probes"] + res["adapted"] for o in r["orders"]]
    LAST_DRILL.clear()
    LAST_DRILL.update(res)
    return res


@app.get("/api/drill/latest")
def drill_latest():
    """Compact summary of the most recent defense drill for the command-center strip (null if none yet)."""
    if not LAST_DRILL:
        return None
    d = LAST_DRILL
    attacks = d.get("probes", []) + d.get("adapted", [])
    search = next((l.get("text", "") for l in d.get("log", []) if l.get("step") == "search"), "")
    return {
        "attacks": len(attacks),
        "attempted_usd": round(sum(r.get("fraud_usd", 0) for r in attacks), 2),
        "search": search,
        "chosen": bool(d.get("chosen")),
        "before_policy": d.get("before_policy"),
        "after_policy": d.get("after_policy"),
        "summary": d.get("summary", {}),
    }


@app.get("/api/compare")
def compare_get():
    """Rules only vs GAT + rules vs GAT + rules hardened, on the latest drill's orders (runs a drill if none yet)."""
    if not LAST_DRILL:
        drill(DrillIn(), None)
    return LAST_DRILL["compare"]


@app.post("/api/compare")
def compare_post(body: DrillIn):
    """Run a fresh drill (never applied) and return its rules-vs-graph comparison."""
    return drill(DrillIn(seed=body.seed, apply=False), None)["compare"]


@app.post("/api/reset", dependencies=ADMIN)
def reset():
    """Rebuild the demo from TWIN_SEED: fresh twin and GAT, default policy, empty mandate spend, holds,
    checkouts, receipts, proposed actions, audit trail, cases and red-team runs."""
    global twin, team
    with _reset_lock:
        t = Twin(seed=int(os.getenv("TWIN_SEED", "3")))
        t.on_event = integrations.publish
        t.train(epochs=int(os.getenv("GAT_EPOCHS", "120")))
        paypal.calls.clear()
        twin, team = t, Team(t, paypal)
        LAST_DRILL.clear()
        twin._event("system", "Demo reset: fresh twin, default policy, empty queues", level="info")
    return {"ok": True, "seed": int(os.getenv("TWIN_SEED", "3")), "policy": twin.policy}


@app.get("/api/redteam/runs")
def runs():
    return team.redteam_runs[::-1]


class PolicyIn(BaseModel):
    review_threshold: float = 0.5
    block_threshold: float = 0.8
    max_auto_amount: float = 1000
    review_new_device_over: float = 300
    review_spend_multiple: float = 0


@app.post("/api/whatif")
def whatif(body: PolicyIn, include_redteam: bool = True):
    return twin.what_if(body.model_dump(), extra_orders=team.last_attack_orders if include_redteam else None)


@app.post("/api/policy", dependencies=ADMIN)
def set_policy(body: PolicyIn):
    twin.policy = body.model_dump()
    twin._event("policy", f"Policy updated: review>={body.review_threshold}, block>={body.block_threshold}, "
                          f"auto-approve <= ${body.max_auto_amount:.0f}", level="warn")
    return twin.policy


class MandateIn(BaseModel):
    per_order_limit: float
    monthly_budget: float
    blocked_categories: list[str] = []


@app.get("/api/mandate")
def get_mandate():
    return team.mandate


@app.post("/api/mandate")
def set_mandate(body: MandateIn):
    team.mandate.update(body.model_dump())
    return team.mandate


# ------------------------------------------------------------------ paypal
@app.post("/api/paypal/orders/{order_id}/capture")
def capture(order_id: str):
    try:
        res = team.capture(order_id)
    except CaptureRefused as e:
        raise HTTPException(e.status, e.detail)
    except PayPalError as e:
        raise HTTPException(502, str(e))
    return {"status": res.get("status"), "id": res.get("id"), "mode": paypal.mode,
            "duplicate": bool(res.get("duplicate"))}


# ------------------------------------------------------------ human review
class ReviewIn(BaseModel):
    reviewer: str = "merchant"
    note: str = ""


@app.get("/api/actions")
def actions():
    """The review queue: investigator proposals, held agent checkouts, and the audit trail."""
    return {"actions": list(team.actions.values())[::-1], "holds": list(team.holds.values())[::-1],
            "audit": team.audit[::-1]}


def _review(fn, item_id, *args):
    try:
        return fn(item_id, *args)
    except KeyError:
        raise HTTPException(404, f"unknown id {item_id}")
    except CaptureRefused as e:
        raise HTTPException(e.status, e.detail)


@app.post("/api/actions/{action_id}/approve", dependencies=ADMIN)
def approve_action(action_id: str, body: ReviewIn):
    return _review(team.decide_action, action_id, True, body.reviewer, body.note)


@app.post("/api/actions/{action_id}/reject", dependencies=ADMIN)
def reject_action(action_id: str, body: ReviewIn):
    return _review(team.decide_action, action_id, False, body.reviewer, body.note)


@app.post("/api/holds/{hold_id}/release", dependencies=ADMIN)
def release_hold(hold_id: str, body: ReviewIn):
    return _review(team.decide_hold, hold_id, True, body.reviewer, body.note)


@app.post("/api/holds/{hold_id}/reject", dependencies=ADMIN)
def reject_hold(hold_id: str, body: ReviewIn):
    return _review(team.decide_hold, hold_id, False, body.reviewer, body.note)


@app.get("/api/receipts")
def receipts():
    return list(team.receipts.values())[::-1]


@app.get("/api/receipts/{receipt_id}")
def receipt(receipt_id: str):
    """A decision receipt by receipt id, PayPal order id or hold id."""
    r = team.receipts.get(receipt_id)
    if not r:
        co = team.checkouts.get(receipt_id) or team.holds.get(receipt_id)
        r = team.receipts.get((co or {}).get("receipt_id"))
    if not r:
        raise HTTPException(404, "unknown receipt")
    return r


@app.get("/api/paypal/calls")
def paypal_calls():
    return paypal.calls[::-1]


@app.get("/api/checkouts")
def checkouts():
    return list(team.checkouts.values())[::-1]


@app.post("/api/paypal/webhook")
async def webhook(request: Request, bg: BackgroundTasks):
    event = await request.json()
    verified = paypal.verify_webhook({k.lower(): v for k, v in request.headers.items()}, event)
    etype = event.get("event_type", "UNKNOWN")
    res = event.get("resource", {}) or {}
    # Only a PayPal-verified webhook may change state. ALLOW_UNVERIFIED_WEBHOOKS=1 is a local testing switch
    # that works only in demo mode (no PayPal keys), so a live deployment can never be driven by forged events.
    trusted = verified or (not paypal.live and os.getenv("ALLOW_UNVERIFIED_WEBHOOKS", "0") == "1")
    if not trusted:
        twin._event("paypal", f"Webhook {etype} ignored: signature not verified", level="warn")
        return {"received": True, "verified": False, "processed": False}
    twin._event("paypal", f"Webhook {etype} ({'verified' if verified else 'unverified, demo testing'})",
                level="bad" if "DISPUTE" in etype else "info")
    if "DISPUTE" in etype:
        # a buyer dispute is ground truth arriving from PayPal: label it and open an investigation
        ids = {t.get("seller_transaction_id") for t in res.get("disputed_transactions", [])}
        for o in twin.orders:
            if o.get("capture_id") in ids:
                o["fraud"] = True
                bg.add_task(team.investigate, o["account"])
    if etype == "PAYMENT.CAPTURE.REFUNDED":
        for o in twin.orders:
            if o.get("capture_id") == res.get("id"):
                o["status"] = "refunded"
    return {"received": True, "verified": verified, "processed": True}
