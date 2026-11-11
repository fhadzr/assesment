"""Schema registry for the four synthetic relational tables.

Single source of truth: the generator, quality report, trainer, and both
inference surfaces all read this registry. The data-map doc is generated
from it (never hand-drawn).

Each FieldSpec documents: name, python type, role (key/feature/label/meta),
and PII class (none | identifier | quasi-identifier | sensitive).
PII classes:
  - identifier: unique person/device reference; must be pseudonymized in outputs
  - quasi-identifier: could identify in combination; keep out of logs
  - sensitive: fraud labels; fine to aggregate, never log per-row
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str  # "int" | "float" | "str" | "bool" | "iso8601"
    role: str  # "key" | "feature" | "label" | "meta"
    pii: str  # "none" | "identifier" | "quasi-identifier" | "sensitive"
    meaning: str


TABLES: dict[str, list[FieldSpec]] = {
    "customers": [
        FieldSpec("customer_id", "str", "key", "identifier",
                  "Synthetic unique customer token (CUST-xxxxxx); fabricated, no real referent"),
        FieldSpec("signup_ts", "iso8601", "meta", "none",
                  "Customer signup timestamp (UTC)"),
        FieldSpec("home_country", "str", "feature", "quasi-identifier",
                  "Two-letter country code of customer residence"),
        FieldSpec("account_age_days", "int", "feature", "none",
                  "Days between signup and dataset end"),
    ],
    "transactions": [
        FieldSpec("transaction_id", "str", "key", "identifier",
                  "Synthetic unique transaction token (TXN-xxxxxx)"),
        FieldSpec("customer_id", "str", "key", "identifier",
                  "Owning customer (CUST-xxxxxx); may dangle by injected defect"),
        FieldSpec("ts", "iso8601", "meta", "none",
                  "Transaction timestamp (UTC); temporal spine for splits and joins"),
        FieldSpec("amount", "float", "feature", "sensitive",
                  "Transaction amount in account currency"),
        FieldSpec("hour_of_day", "int", "feature", "none",
                  "Hour (0-23) derived from ts at generation time"),
        FieldSpec("is_foreign_merchant", "bool", "feature", "none",
                  "Merchant country differs from customer home country"),
        FieldSpec("channel", "str", "feature", "none",
                  "Payment channel: card | transfer | wallet"),
        FieldSpec("device_id", "str", "key", "identifier",
                  "Device used (DEV-xxxxxx); may dangle by injected defect"),
        FieldSpec("ground_truth_fraud", "bool", "label", "sensitive",
                  "Generator's latent fraud flag (ground truth; never an observed label)"),
        FieldSpec("blocked", "bool", "label", "sensitive",
                  "Noisy operational proxy label (false positives + misses)"),
        FieldSpec("confirmed_fraud", "bool", "label", "sensitive",
                  "Trusted sparse label: ground-truth fraud thinned by confirmed-rate; never derived from blocked"),
    ],
    "devices": [
        FieldSpec("device_id", "str", "key", "identifier",
                  "Synthetic unique device token (DEV-xxxxxx)"),
        FieldSpec("customer_id", "str", "key", "identifier",
                  "Owning customer; may dangle by injected defect"),
        FieldSpec("first_seen_ts", "iso8601", "meta", "none",
                  "First-seen timestamp; may be empty by injected defect"),
        FieldSpec("device_type", "str", "feature", "none",
                  "mobile | desktop | tablet"),
    ],
    "logins": [
        FieldSpec("login_id", "str", "key", "identifier",
                  "Synthetic unique login token (LOG-xxxxxx)"),
        FieldSpec("customer_id", "str", "key", "identifier",
                  "Logging-in customer; may dangle by injected defect"),
        FieldSpec("ts", "iso8601", "meta", "none",
                  "Login timestamp (UTC); may be empty by injected defect"),
        FieldSpec("login_ok", "bool", "feature", "none",
                  "Whether the login succeeded"),
        FieldSpec("device_id", "str", "key", "identifier",
                  "Device used for the login; may dangle by injected defect"),
    ],
}

FIELD_REGISTRY = TABLES

FEATURE_FIELDS: list[str] = [f.name for f in TABLES["transactions"] if f.role == "feature"]

LABEL_FIELDS: list[str] = [
    f.name for f in TABLES["transactions"] if f.role == "label" and f.name != "ground_truth_fraud"
]
