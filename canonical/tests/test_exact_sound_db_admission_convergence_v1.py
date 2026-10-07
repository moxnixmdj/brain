from canonical.runtime.exact_sound_db_admission_convergence_v1 import (
    SCHEMA,
    SCOPE_ID,
    compile_region_set,
)


def _flattened():
    return {
        "schema": "PROJECT_BRAIN_EXACT_SOUND_DB_REGION_SET_ROOT_INPUT_V1",
        "regions": [
            {"id": "A", "source_path": "canonical/governance/a.json"},
            {"id": "B", "source_path": "canonical/governance/b.json"},
        ],
        "flattening_checks": {"region_count": 2},
    }


def _binding(region_id, source_path, suffix):
    a = (suffix * 40)[:40]
    b = ((suffix + "b") * 40)[:40]
    c = ((suffix + "c") * 40)[:40]
    d = ((suffix + "d") * 40)[:40]
    e = ((suffix + "e") * 40)[:40]
    # normalize to valid lowercase hex regardless of suffix choice
    vals = [
        ("1" if i == 0 else "2" if i == 1 else "3" if i == 2 else "4" if i == 3 else "5") * 40
        for i in range(5)
    ]
    return {
        "region_id": region_id,
        "scope_id": SCOPE_ID,
        "source_path": source_path,
        "source_artifact_blob_sha": vals[0],
        "route_id": f"route-{region_id}",
        "route_blob_sha": vals[1],
        "admission_predicate_id": f"predicate-{region_id}",
        "admission_predicate_path": f"canonical/runtime/{region_id.lower()}_predicate.py",
        "admission_predicate_blob_sha": vals[2],
        "adequacy_certificate_path": f"canonical/verification/{region_id}_adequacy.json",
        "adequacy_certificate_blob_sha": vals[3],
        "admission_soundness_receipt_path": f"canonical/verification/{region_id}_soundness.json",
        "admission_soundness_receipt_blob_sha": vals[4],
        "independent_verified": True,
        "exact_byte_bound": True,
        "brain_owned_route": True,
        "admission_implies_route_adequacy": True,
    }


def test_missing_bindings_are_the_only_output_frontier():
    out = compile_region_set(_flattened(), [])
    assert out["schema"] == SCHEMA
    assert out["pass"] is True
    assert out["status"] == "INCOMPLETE__EXACT_BINDINGS_REQUIRED"
    assert out["missing_region_count"] == 2
    assert out["complement_ready"] is False
    assert out["u_empty_authorized"] is False
    assert out["terminal_authority"] is False


def test_partial_binding_localizes_exact_remaining_region():
    a = _binding("A", "canonical/governance/a.json", "a")
    out = compile_region_set(_flattened(), [a])
    assert out["bound_region_count"] == 1
    assert out["missing_region_count"] == 1
    assert out["missing_bindings"][0]["region_id"] == "B"
    assert out["missing_bindings"][0]["missing"] == ["BINDING"]


def test_invalid_self_certifying_binding_fails_to_be_ready():
    a = _binding("A", "canonical/governance/a.json", "a")
    b = _binding("B", "canonical/governance/b.json", "b")
    b["independent_verified"] = False
    out = compile_region_set(_flattened(), [a, b])
    assert out["complement_ready"] is False
    assert out["missing_region_count"] == 1
    assert "NOT_PROVED:independent_verified" in out["missing_bindings"][0]["missing"]


def test_complete_content_bound_set_compiles_exact_digest_but_no_terminal_credit():
    a = _binding("A", "canonical/governance/a.json", "a")
    b = _binding("B", "canonical/governance/b.json", "b")
    out = compile_region_set(_flattened(), [a, b])
    assert out["pass"] is True
    assert out["complement_ready"] is True
    assert out["missing_region_count"] == 0
    assert out["predicate_set_sha256"].startswith("sha256:")
    assert out["u_empty_authorized"] is False
    assert out["abc_closed_authorized"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0


def test_unknown_region_binding_fails_closed():
    x = _binding("X", "canonical/governance/x.json", "a")
    out = compile_region_set(_flattened(), [x])
    assert out["pass"] is False
    assert out["reason"] == "UNKNOWN_REGION_BINDING"
