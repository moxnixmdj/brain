from canonical.runtime.osworld_v21_receipt_dataflow_v1 import (
    materialize_explicit_references,
    resolve_named_scalar,
)


def row(result):
    return {
        "web_app_result": {
            "type": "WEB_APP_OP",
            "ok": True,
            "app": "synthetic",
            "operation": "observe",
            "result": result,
        }
    }


def test_unique_named_scalar_binds_with_provenance():
    out = resolve_named_scalar([row({"profile": {"email": "alice@example.com"}})], "email")
    assert out["pass"] is True
    assert out["value"] == "alice@example.com"
    assert out["provenance"][0]["source"] == "web_app_result"
    assert out["provenance"][0]["path"][-1] == "email"


def test_same_value_repeated_is_not_ambiguous():
    out = resolve_named_scalar([
        row({"email": "alice@example.com"}),
        row({"contact": {"email": "alice@example.com"}}),
    ], "email")
    assert out["pass"] is True
    assert out["value"] == "alice@example.com"
    assert len(out["provenance"]) == 2


def test_distinct_values_fail_closed_as_ambiguous():
    out = resolve_named_scalar([
        row({"email": "alice@example.com"}),
        row({"email": "bob@example.com"}),
    ], "email")
    assert out["pass"] is False
    assert out["status"] == "OPEN__FIELD_AMBIGUOUS"
    assert out["candidate_count"] == 2


def test_missing_field_fails_closed():
    out = resolve_named_scalar([row({"name": "Alice"})], "email")
    assert out["pass"] is False
    assert out["status"] == "OPEN__FIELD_NOT_FOUND"


def test_sensitive_field_is_never_materialized():
    out = resolve_named_scalar([row({"api_token": "secret-value"})], "api token")
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED__SENSITIVE_FIELD"


def test_explicit_previous_step_reference_materializes_as_quoted_data():
    out = materialize_explicit_references(
        'Create "contact.txt" containing the email from the previous step',
        [row({"email": "alice@example.com"})],
    )
    assert out["pass"] is True
    assert out["text"] == 'Create "contact.txt" containing "alice@example.com"'
    assert out["bindings"][0]["field"] == "email"


def test_ordinary_the_email_without_provenance_phrase_is_not_rewritten():
    text = 'Create "contact.txt" containing the email'
    out = materialize_explicit_references(text, [row({"email": "alice@example.com"})])
    assert out["pass"] is True
    assert out["status"] == "NO_EXPLICIT_REFERENCE"
    assert out["text"] == text
