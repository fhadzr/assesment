"""Task 1.1 verification: every field of all four tables documented and typed."""

from fraud.data.schema import TABLES

EXPECTED_TABLES = {"customers", "transactions", "devices", "logins"}
VALID_TYPES = {"int", "float", "str", "bool", "iso8601"}
VALID_ROLES = {"key", "feature", "label", "meta"}
VALID_PII = {"none", "identifier", "quasi-identifier", "sensitive"}


def test_four_tables_present():
    assert set(TABLES) == EXPECTED_TABLES


def test_every_field_documented_and_typed():
    for table, fields in TABLES.items():
        assert fields, f"{table} has no fields"
        for f in fields:
            assert f.name, f"{table}.{f} missing name"
            assert f.type in VALID_TYPES, f"{table}.{f.name}: bad type {f.type}"
            assert f.role in VALID_ROLES, f"{table}.{f.name}: bad role {f.role}"
            assert f.pii in VALID_PII, f"{table}.{f.name}: bad pii {f.pii}"
            assert len(f.meaning) > 10, f"{table}.{f.name}: meaning too thin"


def test_transactions_carry_both_label_columns_and_ground_truth():
    names = [f.name for f in TABLES["transactions"]]
    assert {"blocked", "confirmed_fraud", "ground_truth_fraud"} <= set(names)
    # label semantics documented distinctly
    blocked = next(f for f in TABLES["transactions"] if f.name == "blocked")
    confirmed = next(f for f in TABLES["transactions"] if f.name == "confirmed_fraud")
    assert "proxy" in blocked.meaning.lower()
    assert "never derived from blocked" in confirmed.meaning.lower()


def test_temporal_spine_fields_exist():
    for table, field in (("transactions", "ts"), ("logins", "ts"), ("devices", "first_seen_ts")):
        assert field in [f.name for f in TABLES[table]]
