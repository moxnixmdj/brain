from copy import deepcopy
import hashlib
import json
from pathlib import Path

from canonical.runtime.escape_progress_shared_gap_audit_v3 import (
    GAP_A,
    GAP_B,
    _current_binding_path,
    _sha,
    audit,
    audit_repo,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
BINDING_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V5.json"
MANIFEST = json.loads(MANIFEST_PATH.read_text())
BINDING = json.loads(BINDING_PATH.read_text())


def _seal(row):
    material = dict(row)
    material["proof_sha256"] = _sha(material)
    return material


def _proofs(manifest=MANIFEST):
    out = {}
    for row in manifest["rows"]:
        oid = row["obligation_id"]
        if row["route_group"] == GAP_A:
            out[oid] = _seal(
                {
                    "obligation_id": oid,
                    "route_group": GAP_A,
                    "currently_acquirable": True,
                    "finite_outcome_ids": ["yes", "no"],
                    "outcome_map_complete": True,
                    "decision_region_size_before": 2,
                    "max_nonterminal_decision_region_size_after": 1,
                    "authenticated_truth_preserving": True,
                    "safe": True,
                }
            )
        else:
            out[oid] = _seal(
                {
                    "obligation_id": oid,
                    "route_group": GAP_B,
                    "verified_action_id": "verified:" + oid,
                    "action_executable_now": True,
                    "progress_measure": {
                        "kind": "FINITE_NATURAL_RANK",
                        "current_rank": 2,
                        "minimum_rank": 0,
                        "well_founded": True,
                    },
                    "allowed_outcomes": [
                        {"outcome_id": "done", "terminal": True, "strictly_decreases_measure": False},
                        {"outcome_id": "progress", "terminal": False, "strictly_decreases_measure": True},
                    ],
                    "safe": True,
                }
            )
    return out


def _git_blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _terminal_proof(oid):
    return _seal({
        "obligation_id": oid,
        "route_group": GAP_A,
        "resolution_mode": "TERMINAL_COMMON_POLICY",
        "currently_available": True,
        "common_policy_id": "policy:scope-complete:" + oid,
        "authenticated_scope_complete_certificate": True,
        "brain_owned": True,
        "adequate_over_entire_current_decision_region": True,
        "safe_over_entire_current_decision_region": True,
        "resource_admissible": True,
    })


def test_current_successor_truth_stays_open_without_row_proofs():
    result = audit(MANIFEST, BINDING)
    assert result["pass"] is True
    assert result["cc_r3_proved"] is False
    assert result["row_count"] == 13
    assert result["open_row_count"] == 13
    assert result["gap_a_count"] == 10
    assert result["gap_b_count"] == 3
    assert result["terminal_credit_delta"] == 0


def test_finance_index_is_gap_a_after_causal_reclassification():
    row = next(x for x in MANIFEST["rows"] if x["obligation_id"] == "FINANCE_ACCOUNTING_INDEX_GE_61")
    assert row["route_group"] == GAP_A


def test_complete_content_addressed_row_proofs_close_syntactic_cc_r3_gate():
    result = audit(MANIFEST, BINDING, _proofs())
    assert result["pass"] is True
    assert result["cc_r3_proved"] is True
    assert result["closed_row_count"] == 13
    assert result["open_row_count"] == 0
    assert result["open_predicates"] == []


def test_gap_a_without_strict_shrink_remains_open():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_A)
    proof = dict(proofs[oid])
    proof.pop("proof_sha256")
    proof["max_nonterminal_decision_region_size_after"] = proof["decision_region_size_before"]
    proofs[oid] = _seal(proof)
    result = audit(MANIFEST, BINDING, proofs)
    assert result["pass"] is True
    assert result["cc_r3_proved"] is False
    assert f"{oid}:STRICT_DECISION_REGION_SHRINK_NOT_PROVED" in result["open_predicates"]


def test_gap_b_nonprogress_outcome_remains_open():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_B)
    proof = dict(proofs[oid])
    proof.pop("proof_sha256")
    proof["allowed_outcomes"] = [
        {"outcome_id": "stuck", "terminal": False, "strictly_decreases_measure": False}
    ]
    proofs[oid] = _seal(proof)
    result = audit(MANIFEST, BINDING, proofs)
    assert result["pass"] is True
    assert result["cc_r3_proved"] is False
    assert any("OUTCOME_NOT_EXACTLY_TERMINAL_OR_DECREASING" in x for x in result["open_predicates"])


def test_unknown_route_group_fails_closed():
    manifest = deepcopy(MANIFEST)
    manifest["rows"][0]["route_group"] = "UNKNOWN"
    result = audit(manifest, BINDING, _proofs())
    assert result["pass"] is False
    assert result["cc_r3_proved"] is False
    assert any("UNKNOWN_ROUTE_GROUP" in x for x in result["errors"])


def test_binding_partition_count_drift_fails_closed():
    binding = deepcopy(BINDING)
    binding["shared_gaps"][GAP_A]["obligation_count"] = 9
    binding["shared_gaps"][GAP_B]["obligation_count"] = 4
    result = audit(MANIFEST, binding, _proofs())
    assert result["pass"] is False
    assert any("GAP_A_COUNT_MISMATCH" in x for x in result["errors"])
    assert any("GAP_B_COUNT_MISMATCH" in x for x in result["errors"])


def test_declared_partition_total_must_stay_thirteen():
    binding = deepcopy(BINDING)
    binding["shared_gaps"][GAP_A]["obligation_count"] = 10
    binding["shared_gaps"][GAP_B]["obligation_count"] = 4
    result = audit(MANIFEST, binding, _proofs())
    assert result["pass"] is False
    assert "DECLARED_SHARED_GAP_TOTAL_NOT_13" in result["errors"]


def test_finance_reversion_to_gap_b_mutation_is_killed():
    manifest = deepcopy(MANIFEST)
    next(x for x in manifest["rows"] if x["obligation_id"] == "FINANCE_ACCOUNTING_INDEX_GE_61")["route_group"] = GAP_B
    result = audit(manifest, BINDING, _proofs(manifest))
    assert result["pass"] is False
    assert "GAP_A_COUNT_MISMATCH:manifest=9:binding=10" in result["errors"]
    assert "GAP_B_COUNT_MISMATCH:manifest=4:binding=3" in result["errors"]


def test_hardcoded_historical_9_4_count_logic_is_absent():
    source = (ROOT / "canonical/runtime/escape_progress_shared_gap_audit_v2.py").read_text()
    assert "group_counts[GAP_A] != 9" not in source
    assert "group_counts[GAP_B] != 4" not in source
    assert "GAP_A_COUNT_NOT_9" not in source
    assert "GAP_B_COUNT_NOT_4" not in source
    result = audit(MANIFEST, BINDING)
    assert result["pass"] is True
    assert (result["gap_a_count"], result["gap_b_count"]) == (10, 3)


def test_frozen_v1_history_is_byte_identical():
    assert _git_blob_sha(ROOT / "canonical/runtime/escape_progress_shared_gap_audit_v1.py") == "53fb708e755561696f57b39705b04cefcaa2233b"
    assert _git_blob_sha(ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V1.json") == "4ebe25308bf9816d4eeaea415b37b9ec152604c0"


def test_gap_a_terminal_common_policy_mode_closes_one_row_without_fake_shrink():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_A)
    proofs[oid] = _terminal_proof(oid)
    result = audit(MANIFEST, BINDING, proofs)
    row = next(x for x in result["rows"] if x["obligation_id"] == oid)
    assert row["closed"] is True
    assert result["cc_r3_proved"] is True
    assert result["open_predicates"] == []


def test_gap_a_terminal_mode_without_region_wide_safety_remains_open():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_A)
    proof = dict(_terminal_proof(oid))
    proof.pop("proof_sha256")
    proof["safe_over_entire_current_decision_region"] = False
    proofs[oid] = _seal(proof)
    result = audit(MANIFEST, BINDING, proofs)
    assert result["cc_r3_proved"] is False
    assert f"{oid}:COMMON_POLICY_REGION_SAFETY_NOT_PROVED" in result["open_predicates"]


def test_gap_a_terminal_mode_without_scope_complete_authentication_remains_open():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_A)
    proof = dict(_terminal_proof(oid))
    proof.pop("proof_sha256")
    proof["authenticated_scope_complete_certificate"] = False
    proofs[oid] = _seal(proof)
    result = audit(MANIFEST, BINDING, proofs)
    assert result["cc_r3_proved"] is False
    assert f"{oid}:SCOPE_COMPLETE_TERMINAL_CERTIFICATE_NOT_AUTHENTICATED" in result["open_predicates"]


def test_gap_a_terminal_mode_cannot_fake_strict_shrink_fields():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_A)
    proof = dict(_terminal_proof(oid))
    proof.pop("proof_sha256")
    proof["finite_outcome_ids"] = ["fake"]
    proof["outcome_map_complete"] = True
    proof["max_nonterminal_decision_region_size_after"] = 1
    proofs[oid] = _seal(proof)
    result = audit(MANIFEST, BINDING, proofs)
    assert result["cc_r3_proved"] is False
    assert f"{oid}:TERMINAL_MODE_MUST_NOT_ENCODE_FAKE_DISCRIMINATOR_SHRINK" in result["open_predicates"]


def test_gap_a_strict_mode_cannot_mix_terminal_certificate_fields():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_A)
    proof = dict(proofs[oid])
    proof.pop("proof_sha256")
    proof["common_policy_id"] = "policy:forbidden-mix"
    proofs[oid] = _seal(proof)
    result = audit(MANIFEST, BINDING, proofs)
    assert result["cc_r3_proved"] is False
    assert f"{oid}:STRICT_MODE_MUST_NOT_MIX_TERMINAL_CERTIFICATE_FIELDS" in result["open_predicates"]


def test_invalid_gap_a_resolution_mode_remains_open():
    proofs = _proofs()
    oid = next(row["obligation_id"] for row in MANIFEST["rows"] if row["route_group"] == GAP_A)
    proof = dict(proofs[oid])
    proof.pop("proof_sha256")
    proof["resolution_mode"] = "MAGIC"
    proofs[oid] = _seal(proof)
    result = audit(MANIFEST, BINDING, proofs)
    assert result["cc_r3_proved"] is False
    assert f"{oid}:GAP_A_RESOLUTION_MODE_INVALID" in result["open_predicates"]


def test_v2_audit_and_v3_binding_history_remain_byte_identical():
    assert _git_blob_sha(ROOT / "canonical/runtime/escape_progress_shared_gap_audit_v2.py") == "4023b1d9cdd40b1217e1947ea81aee606f3ce52b"
    assert _git_blob_sha(ROOT / "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V3.json") == "ecab2da83c1f21a2a9723221a74bc94514a04f32"


def test_audit_repo_resolves_current_binding_from_live_classifier():
    classifier = json.loads(
        (ROOT / "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json").read_text()
    )
    current = {
        row["residual_id"]: row["existing_binding"]
        for row in classifier["classifications"]
        if row.get("residual_id")
        in {
            "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
            "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
        }
    }
    assert set(current) == {
        "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
        "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
    }
    assert len(set(current.values())) == 1
    expected_rel = next(iter(current.values()))
    expected = ROOT / expected_rel
    resolved = _current_binding_path(ROOT)
    assert resolved == expected.resolve()
    result = audit_repo(ROOT)
    assert result["pass"] is True
    assert result["cc_r3_proved"] is False
    assert result["gap_a_count"] == 10
    assert result["gap_b_count"] == 3
    assert result["current_binding_path"] == expected_rel


def test_current_binding_gap_a_gap_b_divergence_fails_closed():
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        gov = root / "canonical/governance"
        gov.mkdir(parents=True)
        classifier = {
            "classifications": [
                {
                    "residual_id": "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
                    "existing_binding": "canonical/governance/A.json",
                },
                {
                    "residual_id": "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
                    "existing_binding": "canonical/governance/B.json",
                },
            ]
        }
        (gov / "CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json").write_text(
            json.dumps(classifier), encoding="utf-8"
        )
        try:
            _current_binding_path(root)
        except ValueError as exc:
            assert str(exc) == "CURRENT_GAP_BINDING_DIVERGENCE"
        else:
            raise AssertionError("divergent current Gap A/B bindings must fail closed")


def test_current_binding_path_escape_fails_closed():
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        gov = root / "canonical/governance"
        gov.mkdir(parents=True)
        classifier = {
            "classifications": [
                {
                    "residual_id": "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
                    "existing_binding": "../escape.json",
                },
                {
                    "residual_id": "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
                    "existing_binding": "../escape.json",
                },
            ]
        }
        (gov / "CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json").write_text(
            json.dumps(classifier), encoding="utf-8"
        )
        try:
            _current_binding_path(root)
        except ValueError as exc:
            assert str(exc) == "CURRENT_GAP_BINDING_PATH_INVALID"
        else:
            raise AssertionError("path escape must fail closed")


def test_current_binding_content_addresses_live_audit_stack():
    binding_path = _current_binding_path(ROOT)
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    audit_ref = binding["successor_executable_audit"]

    assert audit_ref["path"] == "canonical/runtime/escape_progress_shared_gap_audit_v3.py"
    assert audit_ref["git_blob_sha"] == _git_blob_sha(ROOT / audit_ref["path"])

    tests_ref = audit_ref["tests"]
    assert tests_ref["path"] == "canonical/tests/test_escape_progress_shared_gap_audit_v3.py"
    assert tests_ref["git_blob_sha"] == _git_blob_sha(ROOT / tests_ref["path"])

    verification_ref = audit_ref["verification"]
    assert verification_ref["path"] == "canonical/verification/ESCAPE_V3_DYNAMIC_CURRENT_BINDING_REPAIR_VERIFY_20261010_V1.json"
    assert verification_ref["git_blob_sha"] == _git_blob_sha(ROOT / verification_ref["path"])
