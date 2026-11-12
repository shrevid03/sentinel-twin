"""The OpenAI-compatible loop (Gemini / Groq / Ollama) drives real tools end to end."""
import json

import httpx

from app import agents
from app.paypal import PayPal
from app.twin import Twin


def _reply(content=None, calls=None):
    msg = {"role": "assistant", "content": content}
    if calls:
        msg["tool_calls"] = [{"id": f"c{i}", "type": "function",
                              "function": {"name": n, "arguments": json.dumps(a)}} for i, (n, a) in enumerate(calls)]
    return {"choices": [{"message": msg}]}


def test_openai_compatible_agent_checks_out(monkeypatch):
    script = [
        _reply(calls=[("get_mandate", {}), ("search_catalog", {"query": "coffee", "max_price": 40})]),
        _reply(calls=[("checkout", {"items": [{"sku": "SKU-COF-02", "qty": 1}]})]),
        _reply(content="Done, approve with PayPal."),
    ]
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        for t in body["tools"]:  # schemas must be Gemini-safe
            assert "additionalProperties" not in json.dumps(t)
        return httpx.Response(200, json=script[len(seen) - 1])

    twin = Twin(seed=3)
    twin.train(40)
    team = agents.Team(twin, PayPal())
    team.brain.provider, team.brain.model = "gemini", "test-model"
    team.brain.client = httpx.Client(base_url="http://x", transport=httpx.MockTransport(handler))
    out = team.concierge("t", "coffee gift under $40", "hi-IN")
    assert out["reply"] == "Done, approve with PayPal."
    assert out["checkout"]["total"] == 32.0
    assert seen[-1]["messages"][-1]["role"] == "tool"
