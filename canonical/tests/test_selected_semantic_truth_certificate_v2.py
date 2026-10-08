from __future__ import annotations

from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule
from canonical.runtime.selected_semantic_truth_certificate_v2 import evaluate
from canonical.tests.test_selected_semantic_truth_certificate_v1 import (
    SOURCE_PREDICATE_ID,
    payload as v1_payload,
)

SOURCE = "The operator must archive the record."
ALIAS = "ARCHIVE_RULE_APPLIES"


def deontic_claim(source: str = SOURCE):
    parsed = parse_deontic_rule(source, source="policy")
    assert parsed["status"] == "PARSED"
    scope = parsed.get("scope")
    return {
        "claim_id": "selected",
        "kind": "DEONTIC_RULE",
        "rule_id": parsed["rule_id"],
        "relation": parsed["relation"],
        "subject_span": parsed["subject_span"],
        "action_span": parsed["action_span"],
        "scope_id": scope.get("scope_id") if isinstance(scope, dict) else None,
        "scope_relation": scope.get("relation") if isinstance(scope, dict) else None,
        "condition_span": scope.get("condition_span") if isinstance(scope, dict) else None,
    }


def deontic_payload(source: str = SOURCE, *, alias: str = ALIAS):
    return {
        "predicate_id": alias,
        "target_claim_id": "selected",
        "source_text": source,
        "source_id": "policy",
        "claims": [deontic_claim(source)],
    }


def test_exact_deontic_rule_mints_source_bound_true_predicate():
    out = evaluate(deontic_payload())
    assert out["pass"] is True, out
    assert out["predicate_truth"] == "TRUE"
    assert out["truth_basis"] == "EXACT_SOURCE_BOUND_DEONTIC_RULE_PRESENCE"
    assert out["predicate_id"].startswith("source-deontic-rule-sha256:")
    assert out["requested_predicate_id"] == ALIAS
    assert out["requested_predicate_id_authority"] is False
    assert out["truthful_precommitment_observation"] is True


def test_deontic_predicate_identity_is_stable_across_caller_aliases():
    a = evaluate(deontic_payload(alias="ALIAS_A"))
    b = evaluate(deontic_payload(alias="ALIAS_B"))
    assert a["pass"] is True and b["pass"] is True
    assert a["predicate_id"] == b["predicate_id"]
    assert a["requested_predicate_id"] != b["requested_predicate_id"]


def test_mismatched_deontic_claim_remains_unknown_not_false():
    p = deontic_payload()
    p["claims"][0]["relation"] = "PROHIBITED"
    out = evaluate(p)
    assert out["pass"] is False
    assert out["predicate_truth"] == "UNKNOWN"
    assert out["truthful_precommitment_observation"] is False


def test_source_outside_controlled_deontic_fragment_remains_unknown():
    source = "The operator and auditor must archive the record."
    parsed = parse_deontic_rule(source, source="policy")
    assert parsed["status"] == "UNRESOLVED"
    p = deontic_payload()
    p["source_text"] = source
    out = evaluate(p)
    assert out["pass"] is False
    assert out["predicate_truth"] == "UNKNOWN"
    assert out["truthful_precommitment_observation"] is False


def test_duplicate_claim_ids_fail_closed():
    p = deontic_payload()
    p["claims"] = p["claims"] + [dict(p["claims"][0])]
    out = evaluate(p)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert out["predicate_truth"] == "UNKNOWN"


def test_v1_raw_typed_true_path_is_preserved_exactly():
    out = evaluate(v1_payload("130.00", True))
    assert out["pass"] is True
    assert out["predicate_truth"] == "TRUE"
    assert out["predicate_id"] == SOURCE_PREDICATE_ID


def test_v1_raw_typed_false_path_is_preserved_exactly():
    out = evaluate(v1_payload("100.00", False))
    assert out["pass"] is True
    assert out["predicate_truth"] == "FALSE"
    assert out["predicate_id"] == SOURCE_PREDICATE_ID


def test_deontic_truth_never_mints_outer_authority():
    out = evaluate(deontic_payload())
    assert out["pass"] is True
    for key in (
        "policy_adequacy_authority",
        "db_admission_authority",
        "u_empty_authority",
        "terminal_authority",
    ):
        assert out[key] is False
    assert out["terminal_credit_delta"] == 0
