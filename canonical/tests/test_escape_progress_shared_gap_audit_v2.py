from copy import deepcopy
import hashlib
import json
from pathlib import Path

from canonical.runtime.escape_progress_shared_gap_audit_v2 import (
    GAP_A,
    GAP_B,
    _sha,
    audit,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
BINDING_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V3.json"
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
