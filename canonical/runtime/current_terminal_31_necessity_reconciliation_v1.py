from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AUTH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
POINTER = ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
COVERAGE = ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V2.json"
FACTOR = ROOT / "canonical/runtime/terminal_frontier_factorizer_v1.py"
DELETE_THEOREM = ROOT / "canonical/governance/COMPOSITION_COMPONENT_SCOPED_PROOF_NECESSITY_COUNTERMODEL_20261006_V1.json"
DELETE_VERIFY = ROOT / "canonical/verification/COMPOSITION_COMPONENT_SCOPED_PROOF_NECESSITY_SPRITE_VERIFICATION_20261006_V1.json"
BASIS_VERIFY = ROOT / "canonical/verification/TERMINAL_31_OBLIGATION_BASIS_SPRITE_VERIFICATION_20261006_V1.json"

DELETED = "COMPOSITION_COMPONENT_SCOPED_PROOFS"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify() -> dict[str, object]:
    a = load(AUTH)
    p = load(POINTER)
    c = load(COVERAGE)
    dt = load(DELETE_THEOREM)
    dv = load(DELETE_VERIFY)
    bv = load(BASIS_VERIFY)
    factor_text = FACTOR.read_text(encoding="utf-8")

    assert a["truth"]["achieved"] is False
    assert "14/38_PROVED__24/38_OPEN" in a["truth"]["opus55_atomic_acceptance"]
    assert a["current_terminal_necessity_reconciliation"]["registry_atomic_unresolved"] == 24
    assert a["current_terminal_necessity_reconciliation"]["necessary_atomic_open"] == 23
    assert a["current_terminal_necessity_reconciliation"]["meta_open"] == 8
    assert a["current_terminal_necessity_reconciliation"]["total_necessary_open_truth_obligations"] == 31
    assert a["current_terminal_necessity_reconciliation"]["nonnecessary_unproved_registry_predicate"] == DELETED

    assert p["exact_state"]["unresolved_atomic"] == 24
    assert p["exact_state"]["registry_unresolved_atomic"] == 24
    assert p["exact_state"]["necessary_unresolved_atomic"] == 23
    assert p["exact_state"]["nonnecessary_unproved_atomic_count"] == 1
    assert p["exact_state"]["total_open_truth_obligations"] == 31
    assert p["current_necessity_basis"]["deleted_from_necessity_only"] == [DELETED]
    assert p["current_necessity_basis"]["registry_truth_preserved"] is True

    assert c["projection"]["truth_obligations"] == 31
    assert c["projection"]["truth_obligations_deleted"] == 1
    assert c["projection"]["truth_obligations_closed"] == 0
    assert c["projection"]["terminal"] is False
    assert c["deleted_obligations"][0]["id"] == DELETED

    assert DELETED not in factor_text
    assert dt["subject"]["predicate"] == DELETED
    assert dt["candidate_scheduler_effect_if_verified"]["delete_from_composition_specific_cut"] == DELETED
    assert dv["status"].startswith("INDEPENDENT_SPRITE_EXACT_BRANCH_BYTE_REPLAY_PASS")
    assert dv["candidate_effect"]["delete_from_composition_specific_terminal_cut_if_promoted"] == DELETED
    assert bv["status"].startswith("INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS")
    assert bv["recomputed_partition"]["truth_obligation_count"] == 31
    assert bv["recomputed_partition"]["truth_obligations_deleted"] == 1

    return {
        "status": "PASS__31_NECESSARY_TRUTHS_RECONCILED_WITH_24_OPEN_REGISTRY_PREDICATES",
        "registry_atomic_proved": 14,
        "registry_atomic_unresolved": 24,
        "necessary_atomic_open": 23,
        "meta_open": 8,
        "necessary_open_total": 31,
        "deleted_from_necessity_only": DELETED,
        "deleted_predicate_proved": False,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
