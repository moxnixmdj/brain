import hashlib

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.finance_certified_unless_evidence_role_gate_v1 import (
    derive_roles,
    validate_supervisory_proposal_roles,
)


TEXT = "Apply Rule A unless Exception B applies."


def span_binding(eid, start, end):
    return {
        "evidence_id": eid,
        "start": start,
        "end": end,
        "text_sha256": hashlib.sha256(TEXT[start:end].encode()).hexdigest(),
    }


def bindings():
    p = parse_scope(TEXT, source="s")["parse"]
    return [
        span_binding("rule", *p["left_span"]),
        span_binding("exception", *p["right_span"]),
    ]


def test_roles_derive_from_source_spans():
    out = derive_roles(TEXT, source_id="s", evidence_bindings=bindings())
    assert out["pass"] is True, out
    assert out["derived_roles"]["rule"] == "ORDINARY_BRANCH_EVIDENCE"
    assert out["derived_roles"]["exception"] == "EXCEPTION_BRANCH_EVIDENCE"


def test_swapped_caller_labels_fail_closed():
    roles = derive_roles(TEXT, source_id="s", evidence_bindings=bindings())
    out = validate_supervisory_proposal_roles(
        {
            "rule_evidence_ids": ["exception"],
            "exception_evidence_ids": ["rule"],
        },
        roles,
    )
    assert out["pass"] is False
    assert any(x.startswith("RULE_EVIDENCE_NOT_DERIVED") for x in out["errors"])
    assert any(x.startswith("EXCEPTION_EVIDENCE_NOT_DERIVED") for x in out["errors"])


def test_correct_caller_labels_pass():
    roles = derive_roles(TEXT, source_id="s", evidence_bindings=bindings())
    out = validate_supervisory_proposal_roles(
        {
            "rule_evidence_ids": ["rule"],
            "exception_evidence_ids": ["exception"],
        },
        roles,
    )
    assert out["pass"] is True, out


def test_span_crossing_operator_fails_closed():
    p = parse_scope(TEXT, source="s")["parse"]
    start = p["left_span"][1] - 2
    end = p["right_span"][0] + 2
    out = derive_roles(
        TEXT,
        source_id="s",
        evidence_bindings=[span_binding("cross", start, end)],
    )
    assert out["pass"] is False
    assert any("NOT_CONTAINED_IN_ONE_CERTIFIED_BRANCH" in x for x in out["errors"])


def test_wrong_hash_fails_closed():
    p = parse_scope(TEXT, source="s")["parse"]
    row = span_binding("rule", *p["left_span"])
    row["text_sha256"] = "0" * 64
    out = derive_roles(TEXT, source_id="s", evidence_bindings=[row])
    assert out["pass"] is False
    assert any("HASH_MISMATCH" in x for x in out["errors"])


def test_non_unless_source_not_admitted():
    out = derive_roles(
        "Apply Rule A if condition C.",
        source_id="s",
        evidence_bindings=[],
    )
    assert out["pass"] is False
    assert "SOURCE_NOT_IN_CERTIFIED_SINGLE_UNLESS_FRAGMENT" in out["errors"]
