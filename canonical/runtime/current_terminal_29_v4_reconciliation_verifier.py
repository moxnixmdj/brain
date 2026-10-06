from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import terminal_frontier_factorizer_v2 as factorizer
from canonical.runtime import terminal_coverage_partition_compiler_v2 as compiler

PATHS = {
    "pointer": ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json",
    "authority": ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "coverage": ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V4.json",
    "factorizer": ROOT / "canonical/runtime/terminal_frontier_factorizer_v2.py",
    "compiler": ROOT / "canonical/runtime/terminal_coverage_partition_compiler_v2.py",
    "verification": ROOT / "canonical/verification/TERMINAL_29_OBLIGATION_BASIS_WOLFRAM_VERIFICATION_20261006_V1.json",
}

DELETED = {
    "COMPOSITION_COMPONENT_SCOPED_PROOFS",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
}
ROUTES = {"J": 0, "G": 0, "T": 0, "D": 15, "U": 14}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify() -> dict[str, object]:
    p = load(PATHS["pointer"])
    a = load(PATHS["authority"])
    c = load(PATHS["coverage"])
    w = load(PATHS["verification"])
    f = factorizer.factorize()
    cp = compiler.compile_partition()

    # Runtime truth basis.
    assert len(factorizer.ATOMIC) == 21
    assert len(factorizer.META) == 8
    assert "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES" not in factorizer.ATOMIC
    assert "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES" not in factorizer.UNIVERSAL_SCOPE_ATOMS
    assert f["truth_obligation_count"] == 29
    assert f["truth_obligations_deleted"] == 3
    assert cp["truth_obligation_count"] == 29
    assert cp["route_counts"] == ROUTES
    assert cp["truth_obligations_deleted"] == 3
    assert cp["truth_obligations_closed_by_routing_alone"] == 0
    assert cp["terminal_credit_delta"] == 0

    # Independent basis receipt and coverage projection.
    assert w["status"].startswith("INDEPENDENT_WOLFRAM_EXACT_SET_AND_ROUTING_RECOMPUTATION_PASS__29_TOTAL__D15_U14")
    assert c["projection"]["truth_obligations"] == 29
    assert c["projection"]["route_counts"] == ROUTES
    assert c["projection"]["truth_obligations_deleted"] == 3
    assert c["projection"]["terminal"] is False
    assert {row["id"] for row in c["deleted_obligations"]} == DELETED

    # Pointer exact currentness.
    assert "29_OPEN" in p["status"]
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
    assert loop["governance_git_blob_sha"] == git_blob_sha(PATHS["coverage"])
    assert loop["independent_replay_git_blob_sha"] == git_blob_sha(PATHS["verification"])
    assert loop["route_counts"] == ROUTES
    assert loop["deleted_obligation_count"] == 3
    assert loop["open_truth_obligation_count"] == 29
    assert loop["root2_touching_count"] == 17
    assert loop["root3_touching_count"] == 7
    assert loop["current_schedule"] == c["critical_path"]

    repair = p["current_truth_basis_repair"]
    assert repair["coverage_partition"]["git_blob_sha"] == git_blob_sha(PATHS["coverage"])
    assert repair["factorizer"]["git_blob_sha"] == git_blob_sha(PATHS["factorizer"])
    assert repair["compiler"]["git_blob_sha"] == git_blob_sha(PATHS["compiler"])
    assert repair["independent_verification"]["git_blob_sha"] == git_blob_sha(PATHS["verification"])
    assert repair["truth_obligations_deleted"] == 3
    assert repair["historical_registry"]["current_load_bearing_atomic_open"] == 21
    assert repair["root_transport"]["current_root2_touching"] == 17
    assert repair["root_transport"]["current_root3_touching"] == 7
    assert {row["id"] for row in repair["deleted_obligations"]} == DELETED

    # Authority consumes the pointer, it does not invent a parallel count.
    assert "29_TOTAL_OPEN_TRUTH_OBLIGATIONS" in a["status"]
    assert a["truth"]["achieved"] is False
    assert "21_LOAD_BEARING_ATOMIC_OPEN_PLUS_8_META_OPEN__29_TOTAL" in a["truth"]["global_open_truth"]

    ge = a["global_truth_envelope"]
    assert ge["total_open_truth_obligations"] == 29
    assert ge["load_bearing_atomic_open"] == 21
    assert ge["deleted_nonindependent_or_nonnecessary_atomic_count"] == 3
    assert ge["root2_touching_count"] == 17
    assert ge["root3_touching_count"] == 7
    assert ge["active_pointer"]["git_blob_sha"] == git_blob_sha(PATHS["pointer"])
    assert ge["terminal"] is False

    sp = a.get("scheduler_projection", a.get("v22_scheduler_projection"))
    assert sp["git_blob_sha"] == git_blob_sha(PATHS["pointer"])
    assert sp["exact_state"]["unresolved_atomic"] == 21
    assert sp["exact_state"]["meta_envelope_open_count"] == 8
    assert sp["exact_state"]["total_open_truth_obligations"] == 29
    assert sp["exact_state"]["terminal"] is False

    routing = a["current_routing"]
    assert routing["git_blob_sha"] == git_blob_sha(PATHS["coverage"])
    assert routing["factorizer"]["git_blob_sha"] == git_blob_sha(PATHS["factorizer"])
    assert routing["compiler"]["git_blob_sha"] == git_blob_sha(PATHS["compiler"])
    assert routing["independent_verification"]["git_blob_sha"] == git_blob_sha(PATHS["verification"])
    assert routing["projection"] == ROUTES
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
        "status": "PASS__CURRENT_TERMINAL_CONTROL_REBOUND_TO_VERIFIED_29_V4_BASIS",
        "load_bearing_atomic_open": 21,
        "meta_open": 8,
        "open_truth_obligations": 29,
        "route_counts": ROUTES,
        "root2_touching": 17,
        "root3_touching": 7,
        "deleted_obligations": sorted(DELETED),
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
