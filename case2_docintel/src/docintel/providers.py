"""LLM provider abstraction (tasks 2.4 + 2.5).

Protocol: providers turn masked document text into a structured record of the
eight required fields, plus a usage/cost metadata dict.

Providers:
  - MockProvider: deterministic regex parsing of the (masked) text; zero-token
    usage by construction; fully offline. Default for all automated tests.
  - OllamaProvider: local HTTP (localhost:11434), JSON mode, real usage metadata.
  - GroqProvider: external OpenAI-compatible API, key from env GROQ_API_KEY only,
    real usage metadata from the response.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx

from docintel.corpus.schema import CURRENCIES, DATE_FORMATS, FIELD_NAMES

VALID_PROVIDERS = ("mock", "ollama", "groq")


@dataclass
class ExtractionOutput:
    fields: dict[str, str | None]
    usage: dict  # tokens + cost + basis


class ProviderError(Exception):
    pass


def _parse_date(text: str) -> str | None:
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d %b %Y"):
        m = re.search(r"\b\d{2,4}[-/ ].{0,4}[-/ ]\d{2,4}\b|\b\d{1,2} \w{3} \d{4}\b", text)
        if m:
            for f in DATE_FORMATS:
                try:
                    return datetime.strptime(m.group(0), f).strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


class MockProvider:
    """Deterministic regex extractor on masked text — exercises the real pipeline."""

    name = "mock"

    def __init__(self, **kwargs):
        pass

    def extract(self, masked_text: str) -> ExtractionOutput:
        fields: dict[str, str | None] = {}
        # invoice number
        m = re.search(r"INV-\d{6}", masked_text)
        fields["invoice_number"] = m.group(0) if m else None
        # dates: find date-like tokens after issue/due markers
        fields["invoice_date"] = self._date_near(masked_text, "Issue Date:|Invoice Date:|Date of Issue:")
        fields["due_date"] = self._date_near(masked_text, "Due Date:|Pay By:|Payment Due:")
        # vendor: line after vendor label
        fields["vendor_name"] = self._after(masked_text, "From:|Vendor:|Issued By:")
        # money
        fields["subtotal"] = self._money_near(masked_text, "Subtotal:|Net Amount:|Sub-Total:")
        fields["tax"] = self._money_near(masked_text, "Tax:|VAT:|Sales Tax:")
        fields["total"] = self._money_near(masked_text, "(?<!Sub-)Total:|Grand Total:|Amount Due:")
        # currency: 3-letter code from money tokens or standalone
        m = re.search(r"\b(USD|EUR|IDR|SGD)\b", masked_text)
        fields["currency"] = m.group(1) if m else None
        return ExtractionOutput(
            fields=fields,
            usage={"tokens": 0, "cost": 0.0, "cost_basis": "mock-zero-by-construction", "provider": "mock"},
        )

    @staticmethod
    def _date_near(text: str, label_re: str) -> str | None:
        m = re.search(rf"(?:{label_re})\s*([0-9/\- a-zA-Z]+)", text)
        if not m:
            return None
        return _parse_date(m.group(1))

    @staticmethod
    def _after(text: str, label_re: str) -> str | None:
        m = re.search(rf"(?:{label_re})\s*([^\n]+)", text)
        if not m:
            return None
        return m.group(1).strip().split("  ")[0].strip() or None

    @staticmethod
    def _money_near(text: str, label_re: str) -> str | None:
        m = re.search(rf"(?:{label_re})\s*([0-9]+\.[0-9]{{2}})", text)
        return m.group(1) if m else None


class OllamaProvider:
    """Local Ollama (localhost:11434), JSON mode, real usage metadata."""

    name = "ollama"

    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def extract(self, masked_text: str) -> ExtractionOutput:
        payload = {
            "model": self.model,
            "prompt": self._prompt(masked_text),
            "format": "json",
            "stream": False,
        }
        try:
            r = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=60.0)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"ollama request failed: {exc}") from exc
        try:
            fields = json.loads(data.get("response", "{}"))
        except json.JSONDecodeError as exc:
            raise ProviderError("ollama response was not valid JSON") from exc
        usage = {
            "tokens": data.get("eval_count"),
            "prompt_tokens": data.get("prompt_eval_count"),
            "cost": None,  # Ollama is local; cost basis documented, not invented
            "cost_basis": "local-provider-no-metered-cost",
            "provider": "ollama",
            "model": self.model,
        }
        return ExtractionOutput(fields={f: fields.get(f) for f in FIELD_NAMES}, usage=usage)

    @staticmethod
    def _prompt(masked_text: str) -> str:
        return (
            "Extract the invoice fields from the text below. Return ONLY JSON with keys "
            f"{list(FIELD_NAMES)}. Use null for any missing field. Normalize dates to "
            "yyyy-mm-dd, amounts to decimal strings with 2 places, currency to a 3-letter "
            "code.\n\n" + masked_text
        )


class GroqProvider:
    """External OpenAI-compatible API; key from GROQ_API_KEY env only."""

    name = "groq"

    def __init__(self, model: str = "llama-3.3-70b-versatile", base_url: str = "https://api.groq.com/openai/v1"):
        self.model = model
        self.base_url = base_url
        self.key = os.environ.get("GROQ_API_KEY")
        if not self.key:
            raise ProviderError("GROQ_API_KEY environment variable is not set; no fallback to mock")

    def extract(self, masked_text: str) -> ExtractionOutput:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": self._prompt(masked_text)}],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.key}"}
        try:
            r = httpx.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=60.0)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as exc:
            raise ProviderError(f"groq request failed: {exc}") from exc
        try:
            fields = json.loads(data["choices"][0]["message"]["content"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise ProviderError("groq response did not contain valid structured JSON") from exc
        usage_meta = data.get("usage") or {}
        return ExtractionOutput(
            fields={f: fields.get(f) for f in FIELD_NAMES},
            usage={
                "tokens": usage_meta.get("total_tokens"),
                "prompt_tokens": usage_meta.get("prompt_tokens"),
                "completion_tokens": usage_meta.get("completion_tokens"),
                "cost": None,  # cost computed in evaluate.py from real usage + rate table
                "cost_basis": "metadata-available" if usage_meta else "metadata-unavailable",
                "provider": "groq",
                "model": self.model,
            },
        )

    @staticmethod
    def _prompt(masked_text: str) -> str:
        return OllamaProvider._prompt(masked_text)


PROVIDER_FACTORY = {
    "mock": MockProvider,
    "ollama": OllamaProvider,
    "groq": GroqProvider,
}


def make_provider(name: str, **kwargs):
    if name not in VALID_PROVIDERS:
        raise ProviderError(f"unknown provider '{name}'; valid: {sorted(VALID_PROVIDERS)}")
    return PROVIDER_FACTORY[name](**kwargs)
