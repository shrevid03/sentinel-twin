"""Channel3 live products: mapped into the catalog, guarded by the same mandate, demo fallback on error."""
import httpx
import pytest

from app import agents, catalog, channel3
from app.paypal import PayPal
from app.twin import Twin

RESPONSE = {"products": [
    {"id": "p1", "title": "Hario V60 ceramic coffee dripper", "description": "Pour-over coffee brewer",
     "brands": [{"id": "b1", "name": "Hario"}],
     "images": [{"url": "https://img.example/raw.jpg", "cleaned_url": "https://img.example/clean.jpg", "is_main_image": True}],
     "offers": [{"url": "https://shop-a.example/v60", "domain": "shop-a.example",
                 "price": {"price": 29.5, "currency": "USD"}, "availability": "InStock"},
                {"url": "https://shop-b.example/v60", "domain": "shop-b.example",
                 "price": {"price": 24.0, "currency": "USD"}, "availability": "OutOfStock"}]},
    {"id": "p2", "title": "Coffee shop e-gift card $25", "description": "Redeem online",
     "brands": [], "images": [],
     "offers": [{"url": "https://cafe.example/gc", "domain": "cafe.example",
                 "price": {"price": 25.0, "currency": "USD"}, "availability": "InStock"}]},
]}


class FakeResp:
    def __init__(self, data): self.data = data
    def raise_for_status(self): pass
    def json(self): return self.data


@pytest.fixture(scope="module")
def trained_twin():
    twin = Twin(seed=3)
    twin.train(40)
    return twin


@pytest.fixture
def team(trained_twin, monkeypatch):
    monkeypatch.setenv("CHANNEL3_API_KEY", "test-key")
    trained_twin.policy = {**trained_twin.policy, "review_threshold": 0.99, "block_threshold": 1.01}
    return agents.Team(trained_twin, PayPal())


def test_live_product_checks_out_and_gift_card_is_blocked(team, monkeypatch):
    sent = {}

    def fake_post(url, json, headers, timeout):
        sent.update(url=url, body=json, headers=headers)
        return FakeResp(RESPONSE)

    monkeypatch.setattr(channel3.httpx, "post", fake_post)
    out = team.shopper_tools()["search_catalog"]["fn"]("coffee gift", 40)
    live = [r for r in out["results"] if r["source"] == "channel3"]
    assert [r["sku"] for r in live] == ["C3-p1", "C3-p2"]
    assert any(r["source"] == "demo" for r in out["results"])  # demo items still listed after live ones
    v60 = live[0]
    assert v60["price"] == 29.5 and v60["merchant"] == "shop-a.example"  # cheapest in-stock USD offer
    assert v60["image"] == "https://img.example/clean.jpg" and v60["category"] == "coffee"
    assert sent["headers"]["x-api-key"] == "test-key" and sent["body"]["filters"]["price"]["max_price"] == 40

    ok = team.guarded_checkout([{"sku": "C3-p1", "qty": 1}])
    assert ok["status"] == "awaiting_buyer_approval"
    assert team.checkouts[ok["paypal_order_id"]]["cart"][0]["name"] == v60["name"]

    gc = team.guarded_checkout([{"sku": "C3-p2", "qty": 1}])
    assert live[1]["category"] == "gift_cards"
    assert gc["status"] == "rejected_by_mandate_guard"


def test_channel3_error_falls_back_to_demo_catalog(team, monkeypatch):
    def boom(*a, **k): raise httpx.ConnectTimeout("timeout")
    monkeypatch.setattr(channel3.httpx, "post", boom)
    out = team.shopper_tools()["search_catalog"]["fn"]("coffee", 40)
    assert out["results"] and all(r["source"] == "demo" for r in out["results"])
    assert "demo catalog" in out["note"]


def test_poisoned_probe_ignores_channel3(team, monkeypatch):
    monkeypatch.setattr(channel3.httpx, "post", lambda *a, **k: pytest.fail("red-team probe must not call Channel3"))
    out = team.shopper_tools(poisoned=True)["search_catalog"]["fn"]("gift")
    assert any(r["sku"] == "SKU-EVIL-01" for r in out["results"])
    assert catalog.by_sku("C3-unknown") is None


def test_demo_brain_buys_channel3_product_from_unknown_domain(team, monkeypatch):
    """Regression: a live product's retailer domain is not a twin merchant (was KeyError 'williams-sonoma.com')."""
    resp = {"products": [{"id": "ws1", "title": "Pour-over coffee kettle gift", "description": "for coffee lovers",
                          "brands": [], "images": [{"url": "https://img.example/k.jpg", "is_main_image": True}],
                          "offers": [{"url": "https://www.williams-sonoma.com/k", "domain": "williams-sonoma.com",
                                      "price": {"price": 34.95, "currency": "USD"}, "availability": "InStock"}]}]}
    monkeypatch.setattr(channel3.httpx, "post", lambda *a, **k: FakeResp(resp))
    out = team.concierge("t-ws", "Buy a gift for a coffee lover under $40", "en-IN")
    assert out["checkout"] and out["checkout"]["cart"][0]["sku"] == "C3-ws1"
    assert "williams-sonoma.com" in out["reply"]
