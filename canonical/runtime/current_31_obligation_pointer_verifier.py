from __future__ import annotations

import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
AUTHORITY = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
COVERAGE = ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V2.json"
FACTOR = ROOT / "canonical/runtime/terminal_frontier_factorizer_v1.py"

DELETED = "COMPOSITION_COMPONENT_SCOPED_PROOFS"
EXPECTED = {"J": 0, "G": 0, "T": 0, "D": 16, "U": 15}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_factorizer():
    spec = importlib.util.spec_from_file_location("factorizer", FACTOR)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def verify() -> dict[str, object]:
    p = load(POINTER)
    a = load(AUTHORITY)
    c = load(COVERAGE)
    f = load_factorizer()
    compiled = f.factorize()

    assert compiled["atomic_count"] == 23
    assert compiled["meta_count"] == 8
    assert compiled["truth_obligation_count"] == 31
    assert compiled["truth_obligations_deleted"] == 1
    assert DELETED not in set(f.ATOMIC)

    assert c["projection"]["truth_obligations"] == 31
    assert c["projection"]["route_counts"] == EXPECTED
    assert sum(EXPECTED.values()) == 31
    assert c["projection"]["truth_obligations_deleted"] == 1
    assert c["projection"]["truth_obligations_closed"] == 0
    assert c["projection"]["terminal"] is False
    assert c["deleted_obligations"][0]["id"] == DELETED

    s = p["exact_state"]
    assert s["proved_atomic"] == 14
    assert s["unresolved_atomic"] == 23
    assert s["historical_atomic_registry_count"] == 38
    assert s["deleted_nonnecessary_atomic_count"] == 1
    assert s["current_load_bearing_atomic_count"] == 37
    assert s["meta_envelope_open_count"] == 8
    assert s["total_open_truth_obligations"] == 31
    assert s["root1_positive_gap_count"] == 0
    assert s["root2_touching_count"] == 18
    assert s["root3_touching_count"] == 8
    assert s["terminal"] is False

    loop = p["terminal_falsification_control_loop"]
    assert loop["governance"] == "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V2.json"
    assert loop["route_counts"] == EXPECTED
    assert loop["open_truth_obligation_count"] == 31
    assert loop["deleted_obligation_count"] == 1
    assert "NOT_ROUTE_IMPOSSIBILITY" in loop["route_count_interpretation"]
    assert loop["current_schedule"] == c["critical_path"]

    assert a["current_routing"]["projection"] == EXPECTED
    assert a["current_routing"]["load_bearing_atomic_open"] == 23
    assert a["current_routing"]["meta_open"] == 8
    assert a["current_routing"]["truth_obligations_preserved"] == 31
    assert a["current_routing"]["truth_obligations_deleted"] == 1
    assert a["current_basis_deletion"]["id"] == DELETED

    root = p["current_truth_basis_repair"]["historical_root_cause_state"]
    assert root["old_root3_touching_count"] == 9
    assert root["current_load_bearing_root3_touching_count"] == 8
    assert root["root2_touching_unchanged"] == 18

    return {
        "status": "PASS__CURRENT_POINTER_REBOUND_TO_VERIFIED_31_OBLIGATION_BASIS",
        "load_bearing_atomic_open": 23,
        "meta_open": 8,
        "open_truth_obligations": 31,
        "route_counts": EXPECTED,
        "root2_touching": 18,
        "root3_touching": 8,
        "deleted_obligation": DELETED,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
