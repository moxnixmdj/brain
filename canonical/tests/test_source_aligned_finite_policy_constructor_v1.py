import json

from canonical.runtime.source_aligned_finite_policy_constructor_v1 import (
    CONTRACT_SCHEMA,
    solve,
)


def contract():
    return {
        "schema": CONTRACT_SCHEMA,
        "source_text": (
            'name must equal "Alice". '
            "score must be at least 1. "
            "passed must be true."
        ),
        "source_id": "root-task",
        "field_schema": {
            "name": {"type": "enum", "dimension": "dimensionless"},
            "score": {"type": "number", "dimension": "score"},
            "passed": {"type": "boolean", "dimension": "dimensionless"},
        },
        "candidate_domains": {
            "name": ["Alice", "Bob"],
            "score": [0, 2],
            "passed": [False, True],
        },
        "max_candidates": 100,
    }


def raw(x=None):
    return json.dumps(contract() if x is None else x, separators=(",", ":"))


def test_positive_witness_is_constructed_and_reverified():
    out = solve(raw())
    assert out["pass"] is True, out
    assert out["policy_adequacy_proved"] is True
    assert out["selected_candidate"] == {
        "name": "Alice",
        "passed": True,
        "score": 2,
    }
    assert out["v2_reverification"]["pass"] is True
    assert out["proposal_domain_global_completeness_required_for_positive_adequacy"] is False
    assert out["negative_impossibility_authorized"] is False


def test_incomplete_domain_can_still_prove_positive_witness():
    x = contract()
    x["candidate_domains"] = {
        "name": ["Alice"],
        "score": [2],
        "passed": [True],
    }
    out = solve(raw(x))
    assert out["pass"] is True, out
    assert out["declared_candidate_count"] == 1
    assert out["policy_adequacy_proved"] is True


def test_no_witness_in_declared_domain_is_unknown_not_impossibility():
    x = contract()
    x["candidate_domains"]["name"] = ["Bob"]
    out = solve(raw(x))
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__NO_POSITIVE_ADEQUACY_WITNESS"
    assert out["negative_impossibility_authorized"] is False


def test_unsupported_normative_language_blocks_before_search():
    x = contract()
    x["source_text"] += " report must explain strategic implications."
    out = solve(raw(x))
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__ROOT_TASK_NOT_IN_STRICT_CONTROLLED_ACCEPTANCE_CLASS"


def test_ignored_narrative_is_not_silently_dropped():
    x = contract()
    x["source_text"] = 'For the executive audience. name must equal "Alice".'
    out = solve(raw(x))
    assert out["pass"] is False
    assert out["reason"] == "UNCOMPILED_SOURCE_SEGMENT_PRESENT"


def test_caller_target_effect_or_verifier_injection_is_rejected():
    x = contract()
    x["target_effect"] = "OPUS55_PARITY_VERIFIED"
    out = solve(raw(x))
    assert out["pass"] is False
    assert out["reason"] == "CONTRACT_KEYS_INVALID"


def test_duplicate_root_key_fails_closed():
    good = raw()
    forged = good[:-1] + ',"max_candidates":1}'
    out = solve(forged)
    assert out["pass"] is False
    assert out["reason"] == "DUPLICATE_JSON_KEY:max_candidates"


def test_decimal_sentence_segmentation_bug_fails_closed_not_unsound_pass():
    x = contract()
    x["source_text"] = "score must be at least 0.5."
    x["field_schema"] = {
        "score": {"type": "number", "dimension": "score"},
    }
    x["candidate_domains"] = {"score": [0.1, 0.75]}
    out = solve(raw(x))
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__ROOT_TASK_NOT_IN_STRICT_CONTROLLED_ACCEPTANCE_CLASS"
