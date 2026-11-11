# Case 1 Data Map

Generated from `fraud/data/schema.py` (the registry is authoritative; regenerate
this table from the code, never edit by hand while they disagree).

PII classes: **identifier** (pseudonymize in all outputs), **quasi-identifier**
(keep out of logs), **sensitive** (aggregate only), **none**.

## customers

| Field | Type | Role | PII class | Meaning |
| --- | --- | --- | --- | --- |
| customer_id | str | key | identifier | Synthetic unique customer token (CUST-xxxxxx); fabricated, no real referent |
| signup_ts | iso8601 | meta | none | Customer signup timestamp (UTC) |
| home_country | str | feature | quasi-identifier | Two-letter country code of customer residence |
| account_age_days | int | feature | none | Days between signup and dataset end |

## transactions

| Field | Type | Role | PII class | Meaning |
| --- | --- | --- | --- | --- |
| transaction_id | str | key | identifier | Synthetic unique transaction token (TXN-xxxxxx) |
| customer_id | str | key | identifier | Owning customer (CUST-xxxxxx); may dangle by injected defect |
| ts | iso8601 | meta | none | Transaction timestamp (UTC); temporal spine for splits and joins |
| amount | float | feature | sensitive | Transaction amount in account currency |
| hour_of_day | int | feature | none | Hour (0-23) derived from ts at generation time |
| is_foreign_merchant | bool | feature | none | Merchant country differs from customer home country |
| channel | str | feature | none | Payment channel: card \| transfer \| wallet |
| device_id | str | key | identifier | Device used (DEV-xxxxxx); may dangle by injected defect |
| ground_truth_fraud | bool | label | sensitive | Generator's latent fraud flag (ground truth; never an observed label) |
| blocked | bool | label | sensitive | Noisy operational proxy label (false positives + misses) |
| confirmed_fraud | bool | label | sensitive | Trusted sparse label: ground-truth fraud thinned by confirmed-rate; never derived from blocked |

## devices

| Field | Type | Role | PII class | Meaning |
| --- | --- | --- | --- | --- |
| device_id | str | key | identifier | Synthetic unique device token (DEV-xxxxxx) |
| customer_id | str | key | identifier | Owning customer; may dangle by injected defect |
| first_seen_ts | iso8601 | meta | none | First-seen timestamp; may be empty by injected defect |
| device_type | str | feature | none | mobile \| desktop \| tablet |

## logins

| Field | Type | Role | PII class | Meaning |
| --- | --- | --- | --- | --- |
| login_id | str | key | identifier | Synthetic unique login token (LOG-xxxxxx) |
| customer_id | str | key | identifier | Logging-in customer; may dangle by injected defect |
| ts | iso8601 | meta | none | Login timestamp (UTC); may be empty by injected defect |
| login_ok | bool | feature | none | Whether the login succeeded |
| device_id | str | key | identifier | Device used for the login; may dangle by injected defect |

## Label semantics (summary — full policy in label_policy.md)

- `ground_truth_fraud` — latent generator flag; ground truth for signal validation only.
- `blocked` — noisy proxy: ~80% of fraud caught + false positives on the high-amount legitimate tail. **Training label.**
- `confirmed_fraud` — sparse trusted subset of ground truth (~50% thinning at default). **Primary evaluation label.** Never derived from or converted to `blocked`.
