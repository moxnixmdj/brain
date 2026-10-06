from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
AUTHORITY = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
COVERAGE = ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json"
FACTOR = ROOT / "canonical/runtime/terminal_frontier_factorizer_v1.py"

DELETED = {
    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
}
EXPECTED_ROUTES = {"J": 0, "G": 0, "T": 0, "D": 15, "U": 15}

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def load_factorizer():
    spec = importlib.util.spec_from_file_location("factorizer30", FACTOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

def verify() -> dict:
    p = load(POINTER)
    a = load(AUTHORITY)
    c = load(COVERAGE)
    f = load_factorizer()
    compiled = f.factorize()

    assert compiled["atomic_count"] == 22
    assert compiled["meta_count"] == 8
    assert compiled["truth_obligation_count"] == 30
    assert compiled["truth_obligations_deleted"] == 2
    assert not (DELETED & set(f.ATOMIC))
    assert "ARTIFACT_AA_BRIEFCASE_GE_1822" not in set(f.TARGET_TUPLE_ATOMS)

    assert c["projection"]["truth_obligations"] == 30
    assert c["projection"]["route_counts"] == EXPECTED_ROUTES
    assert c["projection"]["truth_obligations_deleted"] == 2
    assert c["projection"]["truth_obligations_closed"] == 0
    assert c["projection"]["terminal"] is False
    assert {row["id"] for row in c["deleted_obligations"]} == DELETED
    aa = next(row for row in c["deleted_obligations"] if row["id"] == "ARTIFACT_AA_BRIEFCASE_GE_1822")
    assert aa["representative_predicate"] == "PROWORK_AA_BRIEFCASE_GE_1822"
    assert aa["family_aliases"]["ARTIFACT_CREATION"] == "PROWORK_AA_BRIEFCASE_GE_1822"

    s = p["exact_state"]
    assert s["proved_atomic"] == 14
    assert s["unresolved_atomic"] == 22
    assert s["historical_atomic_registry_count"] == 38
    assert s["deleted_nonnecessary_atomic_count"] == 2
    assert s["current_load_bearing_atomic_count"] == 36
    assert s["meta_envelope_open_count"] == 8
    assert s["total_open_truth_obligations"] == 30
    assert s["root1_positive_gap_count"] == 0
    assert s["root2_touching_count"] == 17
    assert s["root3_touching_count"] == 8
    assert s["terminal"] is False

    loop = p["terminal_falsification_control_loop"]
    assert loop["governance"] == "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json"
    assert loop["route_counts"] == EXPECTED_ROUTES
    assert loop["open_truth_obligation_count"] == 30
    assert loop["deleted_obligation_count"] == 2
    assert loop["root2_touching_count"] == 17
    assert loop["root3_touching_count"] == 8
    assert loop["current_schedule"] == c["critical_path"]

    routing = a["current_routing"]
    assert routing["path"] == "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V3.json"
    assert routing["projection"] == EXPECTED_ROUTES
    assert routing["load_bearing_atomic_open"] == 22
    assert routing["meta_open"] == 8
    assert routing["truth_obligations_preserved"] == 30
    assert routing["truth_obligations_deleted"] == 2

    roots = a["current_load_bearing_root_partition"]
    assert roots["load_bearing_unresolved_atomic"] == 22
    assert roots["root2_only"] == 14
    assert roots["root3_only"] == 5
    assert roots["root2_and_root3"] == 3
    assert roots["root2_touching"] == 17
    assert roots["root3_touching"] == 8
    assert roots["terminal"] is False

    assert {row["id"] for row in a["current_basis_deletions"]} == DELETED
    assert a["global_truth_envelope"]["total_open_truth_obligations"] == 30
    assert a["global_truth_envelope"]["root2_touching_count"] == 17
    assert a["global_truth_envelope"]["root3_touching_count"] == 8
    assert a["truth"]["achieved"] is False

    return {
        "status": "PASS__CURRENT_AUTHORITY_REBOUND_TO_VERIFIED_30_OBLIGATION_BASIS",
        "load_bearing_atomic_open": 22,
        "meta_open": 8,
        "open_truth_obligations": 30,
        "route_counts": EXPECTED_ROUTES,
        "root2_touching": 17,
        "root3_touching": 8,
        "deleted_obligations": sorted(DELETED),
        "terminal": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
