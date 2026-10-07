import canonical.runtime.authenticated_positive_cover_compiler_v1 as cover


def _context(cid="c1"):
    return {
        "context_id": cid,
        "source_text": "Rule A applies.",
        "source_id": "source-1",
        "claims": [],
        "decision_basis": ["basis-1"],
        "policy_conditions": {"policy-a": {"op": "TRUE"}},
    }


def _covered(*args, **kwargs):
    return {
        "status": "COMMON_POLICY_CERTIFIED",
        "certified_common_policies": ["policy-a"],
        "authenticated_policy_adequacy": [{"policy_id": "policy-a"}],
        "rejected_policy_adequacy_bindings": [],
    }


def _unresolved(*args, **kwargs):
    return {
        "status": "UNRESOLVED",
        "certified_common_policies": [],
        "authenticated_policy_adequacy": [],
        "rejected_policy_adequacy_bindings": [],
    }


def test_full_declared_manifest_cover_passes_without_abc_credit(monkeypatch):
    monkeypatch.setattr(cover, "resolve_from_source_proof", _covered)
    out = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [_context()]}
    )
    assert out["pass"] is True
    assert out["covered_context_count"] == 1
    assert out["uncovered_context_ids"] == []
    assert out["scope_complete_proved"] is False
    assert out["abc_credit_authorized"] is False
    assert out["terminal_authority"] is False


def test_any_uncovered_context_fails_closed(monkeypatch):
    monkeypatch.setattr(cover, "resolve_from_source_proof", _unresolved)
    out = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [_context()]}
    )
    assert out["pass"] is False
    assert out["status"] == "PARTIAL_COVER__FAIL_CLOSED"
    assert out["uncovered_context_ids"] == ["c1"]


def test_duplicate_context_id_fails_closed(monkeypatch):
    monkeypatch.setattr(cover, "resolve_from_source_proof", _covered)
    out = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [_context(), _context()]}
    )
    assert out["pass"] is False
    assert out["reason"] == "CONTEXT_ID_INVALID_OR_DUPLICATE"


def test_common_policy_status_without_policy_id_does_not_cover(monkeypatch):
    def malformed(*args, **kwargs):
        return {
            "status": "COMMON_POLICY_CERTIFIED",
            "certified_common_policies": [],
        }

    monkeypatch.setattr(cover, "resolve_from_source_proof", malformed)
    out = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [_context()]}
    )
    assert out["pass"] is False
    assert out["uncovered_context_ids"] == ["c1"]


def test_resolver_exception_fails_closed(monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(cover, "resolve_from_source_proof", explode)
    out = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [_context()]}
    )
    assert out["pass"] is False
    assert out["reason"] == "RESOLVER_EXCEPTION"
    assert "RuntimeError:boom" in out["details"]["error"]


def test_manifest_digest_changes_when_source_text_changes(monkeypatch):
    monkeypatch.setattr(cover, "resolve_from_source_proof", _covered)
    a = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [_context()]}
    )
    changed = _context()
    changed["source_text"] = "Rule B applies."
    b = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [changed]}
    )
    assert a["manifest_sha256"] != b["manifest_sha256"]


def test_non_json_manifest_content_fails_closed_at_digest(monkeypatch):
    monkeypatch.setattr(cover, "resolve_from_source_proof", _covered)
    row = _context()
    row["typed_context"] = {"x": object()}
    out = cover.compile_positive_cover(
        {"scope_id": "scope-1", "contexts": [row]}
    )
    assert out["pass"] is False
    assert out["reason"] == "MANIFEST_NOT_CANONICAL_JSON"
