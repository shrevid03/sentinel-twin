"""Tests always run offline: real keys in .env must never reach PayPal or an LLM from the test suite.

Setting the variables to "" before anything is imported wins over load_dotenv(), which never overrides
variables that already exist.
"""
import os

for _k in ("PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET", "PAYPAL_WEBHOOK_ID", "GEMINI_API_KEY", "GROQ_API_KEY",
           "ANTHROPIC_API_KEY", "LLM_PROVIDER", "ADMIN_TOKEN", "ELASTIC_URL", "ZAPIER_WEBHOOK_URL"):
    os.environ[_k] = ""
