"""Tasks 2.4 + 2.5 verification: providers offline."""

import json

import httpx
import pytest

from docintel.corpus.schema import FIELD_NAMES
from docintel.masking import mask_pii
from docintel.providers import (
    GroqProvider,
    MockProvider,
    OllamaProvider,
    ProviderError,
    make_provider,
)

MASKED = mask_pii(
    "INVOICE\nInvoice Number: INV-100001\nInvoice Date: 2026-03-15\n"
    "Issued By: Amberline Trading\nSub-Total: 3754.80 USD\nTax: 413.03 USD\n"
    "Total: 4167.83 USD\nCurrency: USD\nDue Date: 2026-03-22\n"
    "Billing contact: «PII_0»\nPhone: «PII_1»\nAccount ref: «PII_2»\n"
).text


def test_mock_provider_deterministic_and_schema_valid():
    p = MockProvider()
    a = p.extract(MASKED)
    b = p.extract(MASKED)
    assert a.fields == b.fields
    assert set(a.fields) == set(FIELD_NAMES)
    assert a.fields["invoice_number"] == "INV-100001"
    assert a.fields["subtotal"] == "3754.80"
    assert a.fields["total"] == "4167.83"
    assert a.usage["cost_basis"] == "mock-zero-by-construction"
    assert a.usage["tokens"] == 0


def test_mock_provider_offline_no_network(monkeypatch):
    called = []
    monkeypatch.setattr(httpx, "post", lambda *a, **k: called.append(a))
    MockProvider().extract(MASKED)
    assert called == []


def test_unknown_provider_rejected():
    with pytest.raises(ProviderError, match="unknown provider"):
        make_provider("gpt5")


def test_groq_requires_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="GROQ_API_KEY"):
        GroqProvider()


def test_groq_request_shape_and_key_handling(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [{"message": {"content": json.dumps({f: None for f in FIELD_NAMES})}}],
                "usage": {"total_tokens": 123, "prompt_tokens": 50, "completion_tokens": 73},
            }

    monkeypatch.setattr(httpx, "post", lambda url, **kw: (captured.update(kw) or FakeResp()))
    p = GroqProvider()
    out = p.extract(MASKED)
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "llama-3.3-70b-versatile"
    assert out.usage["tokens"] == 123
    assert out.usage["cost_basis"] == "metadata-available"


def test_groq_missing_metadata_reports_unavailable(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({f: None for f in FIELD_NAMES})}}]}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: FakeResp())
    out = GroqProvider().extract(MASKED)
    assert out.usage["tokens"] is None
    assert out.usage["cost_basis"] == "metadata-unavailable"


def test_ollama_request_shape(monkeypatch):
    captured = {}

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": json.dumps({f: None for f in FIELD_NAMES}), "eval_count": 10}

    monkeypatch.setattr(httpx, "post", lambda url, **kw: (captured.update(kw) or FakeResp()))
    out = OllamaProvider().extract(MASKED)
    assert captured["json"]["format"] == "json"
    assert out.usage["cost_basis"] == "local-provider-no-metered-cost"
    assert out.usage["tokens"] == 10
