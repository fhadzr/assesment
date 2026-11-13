"""Task 3.2 verification: real providers offline."""

from __future__ import annotations

import httpx
import pytest

from rag.answering import GroqProvider, OllamaProvider, ProviderError, make_provider


def test_unknown_provider_rejected():
    with pytest.raises(ProviderError, match="unknown provider"):
        make_provider("gpt5")


def test_groq_requires_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="GROQ_API_KEY"):
        GroqProvider()


def test_groq_request_shape_and_usage(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    captured = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "answer [x § y]"}}],
                    "usage": {"total_tokens": 42}}

    monkeypatch.setattr(httpx, "post", lambda url, **kw: (captured.update(kw) or Resp()))
    out = GroqProvider().answer("prompt", [], "q")
    assert captured["headers"]["Authorization"] == "Bearer k"
    assert out["usage"]["tokens"] == 42
    assert out["usage"]["cost_basis"] == "metadata-available"


def test_groq_missing_metadata_null(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "answer"}}]}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: Resp())
    out = GroqProvider().answer("prompt", [], "q")
    assert out["usage"]["tokens"] is None
    assert out["usage"]["cost_basis"] == "metadata-unavailable"


def test_ollama_shape(monkeypatch):
    captured = {}

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "answer [x § y]", "eval_count": 10}

    monkeypatch.setattr(httpx, "post", lambda url, **kw: (captured.update(kw) or Resp()))
    out = OllamaProvider().answer("prompt", [], "q")
    assert captured["json"]["stream"] is False
    assert out["usage"]["cost_basis"] == "local-provider-no-metered-cost"
    assert out["usage"]["tokens"] == 10
