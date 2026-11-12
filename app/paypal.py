"""PayPal REST client for the sandbox (Orders v2, Payments v2 refunds, webhooks).

If PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not set the client runs in a
clearly labelled demo mode that returns the same response shapes, so the app
can still be explored without credentials.
"""
from __future__ import annotations

import os
import time
import uuid

import httpx

SANDBOX = "https://api-m.sandbox.paypal.com"


class PayPalError(Exception):
    pass


class PayPal:
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
        self.secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
        self.base = os.getenv("PAYPAL_API_BASE", SANDBOX)
        self.webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
        self.live = bool(self.client_id and self.secret)
        self._token = None
        self._token_exp = 0.0
        self._demo_orders: dict[str, dict] = {}
        self.calls: list[dict] = []  # recent API calls, shown in the UI

    @property
    def mode(self):
        return "sandbox" if self.live else "demo"

    # ------------------------------------------------------------ plumbing
    def _auth(self):
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        r = httpx.post(f"{self.base}/v1/oauth2/token", auth=(self.client_id, self.secret),
                       data={"grant_type": "client_credentials"}, timeout=20)
        if r.status_code != 200:
            raise PayPalError(f"PayPal auth failed ({r.status_code}): {r.text[:200]}")
        j = r.json()
        self._token, self._token_exp = j["access_token"], time.time() + j.get("expires_in", 3000)
        return self._token

    def _req(self, method, path, json=None, idem=True):
        headers = {"Authorization": f"Bearer {self._auth()}", "Content-Type": "application/json",
                   "Prefer": "return=representation"}
        if idem and method == "POST":
            headers["PayPal-Request-Id"] = str(uuid.uuid4())
        r = httpx.request(method, f"{self.base}{path}", json=json, headers=headers, timeout=30)
        self._log(method, path, r.status_code)
        if r.status_code >= 400:
            raise PayPalError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else {}

    def _log(self, method, path, status):
        self.calls.append({"t": time.strftime("%H:%M:%S"), "method": method, "path": path, "status": status,
                           "mode": self.mode})
        self.calls = self.calls[-50:]

    # -------------------------------------------------------------- orders
    def create_order(self, items, reference, description="Sentinel Twin agent checkout", return_url=None):
        total = round(sum(i["price"] * i.get("qty", 1) for i in items), 2)
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": reference[:256],
                "custom_id": reference[:127],
                "description": description[:127],
                "amount": {"currency_code": "USD", "value": f"{total:.2f}",
                           "breakdown": {"item_total": {"currency_code": "USD", "value": f"{total:.2f}"}}},
                "items": [{"name": i["name"][:127], "quantity": str(i.get("qty", 1)), "sku": i.get("sku", "")[:127],
                           "unit_amount": {"currency_code": "USD", "value": f"{i['price']:.2f}"},
                           "category": "PHYSICAL_GOODS"} for i in items],
            }],
        }
        if return_url:
            body["payment_source"] = {"paypal": {"experience_context": {
                "brand_name": "Sentinel Twin Demo Store", "user_action": "PAY_NOW",
                "shipping_preference": "NO_SHIPPING", "return_url": return_url, "cancel_url": return_url}}}
        if not self.live:
            oid = "DEMO-" + uuid.uuid4().hex[:12].upper()
            order = {"id": oid, "status": "CREATED", "intent": "CAPTURE", "purchase_units": body["purchase_units"],
                     "links": [{"rel": "approve", "href": f"/demo-approve/{oid}", "method": "GET"}]}
            self._demo_orders[oid] = order
            self._log("POST", "/v2/checkout/orders", 201)
            return order
        return self._req("POST", "/v2/checkout/orders", body)

    def get_order(self, order_id):
        if not self.live:
            self._log("GET", f"/v2/checkout/orders/{order_id}", 200)
            o = self._demo_orders.get(order_id)
            if not o:
                raise PayPalError(f"order {order_id} not found")
            return o
        return self._req("GET", f"/v2/checkout/orders/{order_id}")

    def capture_order(self, order_id):
        if not self.live:
            o = self.get_order(order_id)
            cap_id = "DEMOCAP-" + uuid.uuid4().hex[:10].upper()
            o["status"] = "COMPLETED"
            o["purchase_units"][0]["payments"] = {"captures": [{
                "id": cap_id, "status": "COMPLETED", "amount": o["purchase_units"][0]["amount"]}]}
            self._log("POST", f"/v2/checkout/orders/{order_id}/capture", 201)
            return o
        return self._req("POST", f"/v2/checkout/orders/{order_id}/capture", {})

    def refund_capture(self, capture_id, amount=None, note="Refund issued by Sentinel Twin investigator"):
        body = {"note_to_payer": note[:255]}
        if amount:
            body["amount"] = {"currency_code": "USD", "value": f"{float(amount):.2f}"}
        if not self.live:
            self._log("POST", f"/v2/payments/captures/{capture_id}/refund", 201)
            return {"id": "DEMOREF-" + uuid.uuid4().hex[:10].upper(), "status": "COMPLETED", **body}
        return self._req("POST", f"/v2/payments/captures/{capture_id}/refund", body)

    # ------------------------------------------------------------ webhooks
    def verify_webhook(self, headers, event):
        if not (self.live and self.webhook_id):
            return False
        body = {
            "auth_algo": headers.get("paypal-auth-algo"), "cert_url": headers.get("paypal-cert-url"),
            "transmission_id": headers.get("paypal-transmission-id"),
            "transmission_sig": headers.get("paypal-transmission-sig"),
            "transmission_time": headers.get("paypal-transmission-time"),
            "webhook_id": self.webhook_id, "webhook_event": event,
        }
        try:
            res = self._req("POST", "/v1/notifications/verify-webhook-signature", body, idem=False)
            return res.get("verification_status") == "SUCCESS"
        except PayPalError:
            return False


def capture_id_of(order):
    try:
        return order["purchase_units"][0]["payments"]["captures"][0]["id"]
    except (KeyError, IndexError, TypeError):
        return None
