from canonical.runtime.mission_semantic_authority_v1 import semantic_sha256, validate

SOURCE = {
    "real_objective": "BUILD",
    "optimization_objective": "MAX",
    "compounding_requirement": "COMPOUND",
    "knowledge_policy": "JIT",
    "opus_5_5_role": "CHECKPOINT",
    "benchmark_role": "INSTRUMENT",
    "checkpoint_rule": "NOT_TERMINAL",
    "correctness_rule": "FAIL_CLOSED",
    "spend_rule": "ZERO",
    "mission_terminality": "OPEN_ENDED",
    "option_preservation_requirement": "PRESERVE",
    "future_technology_compatibility": "NEUTRAL",
}


def pointer(extra=None):
    out = {
        "authoritative_source": {
            "path": "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
        },
        "real_objective": "BUILD",
        "opus_5_5_role": "CHECKPOINT",
    }
    if extra:
        out.update(extra)
    return out


def test_semantic_digest_ignores_pointer_auxiliary_fields():
    digest = semantic_sha256(SOURCE)
    a = validate(
        pointer({"current_assurance_closure_compiler": {"git_blob_sha": "a"}}),
        SOURCE,
        source_git_blob_sha="source",
        expected_source_git_blob_sha="source",
        expected_semantics_sha256=digest,
    )
    b = validate(
        pointer({"current_assurance_closure_compiler": {"git_blob_sha": "b"}}),
        SOURCE,
        source_git_blob_sha="source",
        expected_source_git_blob_sha="source",
        expected_semantics_sha256=digest,
    )
    assert a["pass"] is True
    assert b["pass"] is True
    assert a["mission_semantics_sha256"] == b["mission_semantics_sha256"]


def test_load_bearing_semantic_change_fails():
    digest = semantic_sha256(SOURCE)
    changed = dict(SOURCE)
    changed["correctness_rule"] = "WEAK"
    out = validate(
        pointer(),
        changed,
        source_git_blob_sha="source",
        expected_source_git_blob_sha="source",
        expected_semantics_sha256=digest,
    )
    assert out["pass"] is False
    assert "MISSION_SEMANTICS_DRIFT" in out["errors"]


def test_source_blob_drift_fails():
    out = validate(
        pointer(),
        SOURCE,
        source_git_blob_sha="new",
        expected_source_git_blob_sha="old",
        expected_semantics_sha256=semantic_sha256(SOURCE),
    )
    assert "MISSION_SOURCE_BLOB_DRIFT" in out["errors"]


def test_pointer_source_path_drift_fails():
    p = pointer()
    p["authoritative_source"]["path"] = "wrong"
    out = validate(
        p,
        SOURCE,
        source_git_blob_sha="source",
        expected_source_git_blob_sha="source",
        expected_semantics_sha256=semantic_sha256(SOURCE),
    )
    assert "MISSION_POINTER_SOURCE_PATH_DRIFT" in out["errors"]
