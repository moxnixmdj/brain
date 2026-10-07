import json

from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context


def test_valid_raw_source_compiles_and_hashes_exact_bytes():
    raw = json.dumps({
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {
            "exception_holds": {"type": "BOOL", "value": True},
            "exposure_amount": {"type": "DECIMAL_STRING", "value": "125.50"},
        },
    }, separators=(",", ":"))
    out = compile_typed_context(raw, source_id="facts")
    assert out["status"] == "COMPILED", out
    assert out["field_count"] == 2
    assert out["typed_context"]["fields"]["exception_holds"]["value"] is True


def test_duplicate_json_key_fails_closed():
    raw = '{"schema_id":"X","fields":{"a":{"type":"BOOL","value":true},"a":{"type":"BOOL","value":false}}}'
    out = compile_typed_context(raw, source_id="facts")
    assert out["status"] == "FAIL_CLOSED"
    assert any(x.startswith("DUPLICATE_JSON_KEY:") for x in out["errors"])


def test_decimal_number_must_be_string_not_float():
    raw = '{"schema_id":"X","fields":{"amount":{"type":"DECIMAL_STRING","value":1.25}}}'
    out = compile_typed_context(raw, source_id="facts")
    assert out["status"] == "FAIL_CLOSED"
    assert "FIELD_VALUE_TYPE_MISMATCH:amount" in out["errors"]


def test_extra_top_level_authority_claim_is_rejected():
    raw = '{"schema_id":"X","fields":{"a":{"type":"BOOL","value":true}},"trusted":true}'
    out = compile_typed_context(raw, source_id="facts")
    assert out["status"] == "FAIL_CLOSED"
    assert "TYPED_CONTEXT_TOP_LEVEL_KEYS_INVALID" in out["errors"]


def test_invalid_field_name_fails_closed():
    raw = '{"schema_id":"X","fields":{"total exposure":{"type":"DECIMAL_STRING","value":"1"}}}'
    out = compile_typed_context(raw, source_id="facts")
    assert out["status"] == "FAIL_CLOSED"
    assert "FIELD_NAME_INVALID:total exposure" in out["errors"]
