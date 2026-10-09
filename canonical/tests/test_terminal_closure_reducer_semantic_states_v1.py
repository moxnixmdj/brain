import json

from canonical.runtime.terminal_closure_reducer import (
    REQUIRED_COUNTERS,
    REQUIRED_PREDICATES,
    _family_terminally_closed,
    _git_blob_sha,
    _target_family_identity_failures,
    evaluate_manifest,
)


def closed_decorated():
    return {
        "closure_state": (
            "WHOLE_SCOPE_PASS__STRICT_OPUS55_ACCEPTANCE_PASS__"
            "VERIFIED_OWNED_EQUAL_OR_BETTER"
        ),
        "opus55_acceptance_state": "PASS",
        "opus55_acceptance_calibrated": True,
        "ownership_status": "VERIFIED_OWNED_EQUAL_OR_BETTER",
        "unresolved": [],
    }


def test_decorated_semantically_closed_state_is_closed():
    assert _family_terminally_closed(closed_decorated()) is True


def test_bare_compact_pass_is_not_self_certifying():
    assert _family_terminally_closed({"closure_state": "PASS"}) is False


def test_compact_pass_with_semantic_closure_fields_is_closed():
    row = closed_decorated()
    row["closure_state"] = "PASS"
    assert _family_terminally_closed(row) is True


def test_open_acceptance_cannot_hide_behind_behavioral_pass_label():
    row = closed_decorated()
    row["closure_state"] = "BEHAVIORAL_PASS__OPUS55_ACCEPTANCE_OPEN"
    row["opus55_acceptance_state"] = "OPEN"
    assert _family_terminally_closed(row) is False


def test_unresolved_obligation_fails_closed():
    row = closed_decorated()
    row["unresolved"] = ["STILL_OPEN"]
    assert _family_terminally_closed(row) is False


def test_unverified_ownership_fails_closed():
    row = closed_decorated()
    row["ownership_status"] = "PROVISIONAL"
    assert _family_terminally_closed(row) is False


def test_quarantine_marker_fails_closed_even_with_other_pass_fields():
    row = closed_decorated()
    row["closure_state"] = "WHOLE_SCOPE_PASS__QUARANTINED"
    assert _family_terminally_closed(row) is False


TARGET_IDS = [
    "ADVANCED_AGENTIC_CODING",
    "COMPLEX_MULTI_TOOL_AGENCY",
    "PROFESSIONAL_KNOWLEDGE_WORK",
    "BUSINESS_WORKFLOW_AUTOMATION",
    "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING",
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "VISION_AND_DENSE_DOCUMENT_UNDERSTANDING",
    "COMPUTER_AND_BROWSER_USE",
    "FINANCIAL_ANALYSIS",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
    "SUBAGENT_DELEGATION_AND_COORDINATION",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
    "ARTIFACT_CREATION",
    "COMMUNICATION_AND_SYNTHESIS",
    "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
    "UNKNOWN_DOMAIN_ADAPTATION",
    "MULTI_CAPABILITY_COMPOSITION",
    "EXACT_SYMBOLIC_COMPUTATION",
]


def _target_envelope(ids=TARGET_IDS):
    return {
        "target_family_count": 19,
        "families": [{"id": fid} for fid in ids],
    }


def _closed_manifest(ids, binding):
    families = []
    for fid in ids:
        row = closed_decorated()
        row["id"] = fid
        families.append(row)
    return {
        "target_envelope": binding["path"],
        "target_envelope_binding": binding,
        "expected_family_count": 19,
        "actual_family_count": 19,
        "families": families,
        "counters": {name: 0 for name in REQUIRED_COUNTERS},
        "terminal_predicates": {name: True for name in REQUIRED_PREDICATES},
    }


def _write_target(tmp_path):
    path = tmp_path / "target.json"
    path.write_text(json.dumps(_target_envelope()), encoding="utf-8")
    return {
        "path": "target.json",
        "git_blob_sha": _git_blob_sha(path),
    }


def test_exact_target_family_identity_set_passes():
    assert _target_family_identity_failures(TARGET_IDS, _target_envelope()) == []


def test_same_cardinality_family_substitution_is_detected():
    mutated = list(TARGET_IDS)
    removed = mutated[-1]
    mutated[-1] = "INVENTED_REPLACEMENT"
    failures = _target_family_identity_failures(mutated, _target_envelope())
    assert f"REQUIRED_FAMILY_ID_MISSING:{removed}" in failures
    assert "UNRECOGNIZED_FAMILY_ID:INVENTED_REPLACEMENT" in failures


def test_terminal_reducer_rejects_same_count_family_substitution(tmp_path):
    binding = _write_target(tmp_path)
    baseline = evaluate_manifest(_closed_manifest(TARGET_IDS, binding), repo_root=tmp_path)
    assert baseline["achieved"] is True

    mutated = list(TARGET_IDS)
    removed = mutated[0]
    mutated[0] = "INVENTED_REPLACEMENT"
    out = evaluate_manifest(_closed_manifest(mutated, binding), repo_root=tmp_path)
    assert out["achieved"] is False
    assert f"REQUIRED_FAMILY_ID_MISSING:{removed}" in out["failed_predicates"]
    assert "UNRECOGNIZED_FAMILY_ID:INVENTED_REPLACEMENT" in out["failed_predicates"]


def test_terminal_reducer_rejects_stale_target_envelope_binding(tmp_path):
    binding = _write_target(tmp_path)
    binding["git_blob_sha"] = "0" * 40
    out = evaluate_manifest(_closed_manifest(TARGET_IDS, binding), repo_root=tmp_path)
    assert out["achieved"] is False
    assert "TARGET_ENVELOPE_UNBOUND:GIT_BLOB_SHA_MISMATCH" in out["failed_predicates"]
