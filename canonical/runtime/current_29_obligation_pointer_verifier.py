from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
POINTER = ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
AUTHORITY = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
COVERAGE = ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json"
RECEIPT = ROOT / "canonical/verification/TERMINAL_29_OBLIGATION_BASIS_SPRITE_VERIFICATION_20261006_V1.json"

DELETED = {
    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
}
EXPECTED_ROUTES = {"J": 0, "G": 0, "T": 0, "D": 15, "U": 14}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))



def verify() -> dict:
    p = load(POINTER)
    a = load(AUTHORITY)
    c = load(COVERAGE)
    r = load(RECEIPT)
    from canonical.runtime import terminal_frontier_factorizer_v1 as f
    from canonical.runtime import terminal_coverage_partition_compiler_v1 as cp

    fact = f.factorize()
    part = cp.compile_partition()

    assert fact["atomic_count"] == 21
    assert fact["meta_count"] == 8
    assert fact["truth_obligation_count"] == 29
    assert fact["truth_obligations_deleted"] == 3
    assert not (DELETED & set(f.ATOMIC))
    assert "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES" not in f.UNIVERSAL_SCOPE_ATOMS

    assert part["truth_obligation_count"] == 29
    assert part["truth_obligations_deleted"] == 3
    assert part["route_counts"] == EXPECTED_ROUTES
    assert part["truth_obligations_closed_by_routing_alone"] == 0
    assert part["terminal_credit_delta"] == 0

    assert c["projection"]["truth_obligations"] == 29
    assert c["projection"]["route_counts"] == EXPECTED_ROUTES
    assert c["projection"]["truth_obligations_deleted"] == 3
    assert c["projection"]["truth_obligations_closed"] == 0
    assert c["projection"]["terminal"] is False
    assert {row["id"] for row in c["deleted_obligations"]} == DELETED

    assert r["status"].startswith("INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS__12_OF_12")
    assert r["recomputed_partition"]["truth_obligation_count"] == 29
    assert r["recomputed_partition"]["route_counts"] == EXPECTED_ROUTES
    assert r["recomputed_partition"]["root2_touching"] == 17
    assert r["recomputed_partition"]["root3_touching"] == 7

    s = p["exact_state"]
    assert s["proved_atomic"] == 14
    assert s["unresolved_atomic"] == 21
    assert s["historical_atomic_registry_count"] == 38
    assert s["deleted_nonnecessary_atomic_count"] == 3
    assert s["current_load_bearing_atomic_count"] == 35
    assert s["meta_envelope_open_count"] == 8
    assert s["total_open_truth_obligations"] == 29
    assert s["root2_touching_count"] == 17
    assert s["root3_touching_count"] == 7
    assert s["terminal"] is False

    gc = p["global_compression"]
    assert gc["atomic_open_predicates"] == 21
    assert gc["meta_open_obligations"] == 8
    assert gc["total_open_truth_obligations"] == 29
    assert gc["truth_obligations_deleted"] == 3
    assert gc["terminal_control_loop"].endswith("CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json")

    loop = p["terminal_falsification_control_loop"]
    assert loop["governance"].endswith("CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json")
    assert loop["route_counts"] == EXPECTED_ROUTES
    assert loop["open_truth_obligation_count"] == 29
    assert loop["deleted_obligation_count"] == 3
    assert loop["root2_touching_count"] == 17
    assert loop["root3_touching_count"] == 7
    assert loop["current_schedule"] == c["critical_path"]

    tr = p["current_truth_basis_repair"]
    assert tr["truth_obligations_deleted"] == 3
    assert tr["historical_registry"]["current_load_bearing_atomic_open"] == 21
    assert tr["historical_registry"]["deleted_nonindependent_or_nonnecessary_atomic_count"] == 3
    assert tr["root_transport"]["current_root2_touching"] == 17
    assert tr["root_transport"]["current_root3_touching"] == 7
    assert {row["id"] for row in tr["deleted_obligations"]} == DELETED

    assert a["truth"]["achieved"] is False
    assert "21_LOAD_BEARING_ATOMIC_OPEN_PLUS_8_META_OPEN__29_TOTAL" in a["truth"]["global_open_truth"]

    ge = a["global_truth_envelope"]
    assert ge["total_open_truth_obligations"] == 29
    assert ge["load_bearing_atomic_open"] == 21
    assert ge["deleted_nonindependent_or_nonnecessary_atomic_count"] == 3
    assert ge["root2_touching_count"] == 17
    assert ge["root3_touching_count"] == 7
    assert ge["terminal"] is False

    sp = a["v22_scheduler_projection"]["exact_state"]
    assert sp["unresolved_atomic"] == 21
    assert sp["meta_envelope_open_count"] == 8
    assert sp["total_open_truth_obligations"] == 29
    assert sp["terminal"] is False

    routing = a["current_routing"]
    assert routing["path"].endswith("CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json")
    assert routing["projection"] == EXPECTED_ROUTES
    assert routing["load_bearing_atomic_open"] == 21
    assert routing["meta_open"] == 8
    assert routing["truth_obligations_preserved"] == 29
    assert routing["truth_obligations_deleted"] == 3

    roots = a["current_load_bearing_root_partition"]
    assert roots["load_bearing_unresolved_atomic"] == 21
    assert roots["root2_only"] == 14
    assert roots["root3_only"] == 4
    assert roots["root2_and_root3"] == 3
    assert roots["root2_touching"] == 17
    assert roots["root3_touching"] == 7
    assert roots["terminal"] is False

    assert {row["id"] for row in a["current_basis_deletions"]} == DELETED

    return {
        "status": "PASS__CURRENT_AUTHORITY_REBOUND_TO_VERIFIED_29_OBLIGATION_BASIS",
        "load_bearing_atomic_open": 21,
        "meta_open": 8,
        "open_truth_obligations": 29,
        "route_counts": EXPECTED_ROUTES,
        "root2_touching": 17,
        "root3_touching": 7,
        "deleted_obligations": sorted(DELETED),
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
