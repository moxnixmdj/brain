from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
AUTHORITY = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
COVERAGE = ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json"
FACTOR = ROOT / "canonical/runtime/terminal_frontier_factorizer_v1.py"
COMP_DELETED = "COMPOSITION_COMPONENT_SCOPED_PROOFS"
AA_ALIAS = "ARTIFACT_AA_BRIEFCASE_GE_1822"
AA_REP = "PROWORK_AA_BRIEFCASE_GE_1822"
EXPECTED = {"J": 0, "G": 0, "T": 0, "D": 15, "U": 15}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_factorizer():
    spec = importlib.util.spec_from_file_location("factorizer", FACTOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def verify() -> dict[str, object]:
    p, a, c = load(POINTER), load(AUTHORITY), load(COVERAGE)
    f = load_factorizer()
    compiled = f.factorize()

    assert compiled["atomic_count"] == 22
    assert compiled["meta_count"] == 8
    assert compiled["truth_obligation_count"] == 30
    assert compiled["truth_obligations_deleted"] == 2
    assert COMP_DELETED not in set(f.ATOMIC)
    assert AA_ALIAS not in set(f.ATOMIC)
    assert AA_REP in set(f.ATOMIC)

    assert c["projection"]["truth_obligations"] == 30
    assert c["projection"]["route_counts"] == EXPECTED
    assert sum(EXPECTED.values()) == 30
    assert c["projection"]["truth_obligations_deleted"] == 2
    assert c["projection"]["truth_obligations_closed"] == 0
    assert c["projection"]["terminal"] is False
    assert {x["id"] for x in c["deleted_obligations"]} == {COMP_DELETED, AA_ALIAS}

    s = p["exact_state"]
    assert s["proved_atomic"] == 14
    assert s["unresolved_atomic"] == 22
    assert s["historical_atomic_registry_count"] == 38
    assert s["deleted_nonnecessary_atomic_count"] == 1
    assert s["deleted_duplicate_alias_atomic_count"] == 1
    assert s["current_load_bearing_atomic_count"] == 36
    assert s["meta_envelope_open_count"] == 8
    assert s["total_open_truth_obligations"] == 30
    assert s["root1_positive_gap_count"] == 0
    assert s["root2_touching_count"] == 17
    assert s["root3_touching_count"] == 8
    assert s["terminal"] is False

    loop = p["terminal_falsification_control_loop"]
    assert loop["governance"] == "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json"
    assert loop["governance_git_blob_sha"] == "f282c807330955ef72f17a565d940815e0497017"
    assert loop["route_counts"] == EXPECTED
    assert loop["open_truth_obligation_count"] == 30
    assert loop["deleted_obligation_count"] == 2
    assert "NOT_PROOF" in loop["route_count_interpretation"]
    assert loop["current_schedule"] == c["critical_path"]

    ar = a["current_routing"]
    assert ar["projection"] == EXPECTED
    assert ar["load_bearing_atomic_open"] == 22
    assert ar["meta_open"] == 8
    assert ar["truth_obligations_preserved"] == 30
    assert ar["truth_obligations_deleted"] == 2
    assert ar["root2_touching"] == 17
    assert ar["root3_touching"] == 8
    assert {x["id"] for x in a["current_basis_deletions"]} == {COMP_DELETED, AA_ALIAS}

    return {
        "status": "PASS__CURRENT_POINTER_REBOUND_TO_VERIFIED_30_OBLIGATION_BASIS",
        "load_bearing_atomic_open": 22,
        "meta_open": 8,
        "open_truth_obligations": 30,
        "route_counts": EXPECTED,
        "root2_touching": 17,
        "root3_touching": 8,
        "deleted_truths": [COMP_DELETED, AA_ALIAS],
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
