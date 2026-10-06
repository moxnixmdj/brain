from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V1.json"
AUTHORITY = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"
COVERAGE = ROOT / "canonical/governance/CURRENT_TERMINAL_COVERAGE_PARTITION_V1.json"

OLD = "C_UNIVERSAL_OBSERVABLE_BEHAVIOR_DOMINANCE_BINDING_V1"
EXPECTED_COUNTS = {"J": 0, "G": 0, "T": 0, "D": 16, "U": 16}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify() -> dict[str, object]:
    p = load(POINTER)
    a = load(AUTHORITY)
    c = load(COVERAGE)

    assert p["exact_state"]["proved_atomic"] == 14
    assert p["exact_state"]["unresolved_atomic"] == 24
    assert p["exact_state"]["meta_envelope_open_count"] == 8
    assert p["exact_state"]["total_open_truth_obligations"] == 32
    assert p["exact_state"]["terminal"] is False

    route_counts = p["terminal_falsification_control_loop"]["route_counts"]
    assert route_counts == EXPECTED_COUNTS
    assert sum(route_counts.values()) == 32
    assert c["projection"]["route_counts"] == EXPECTED_COUNTS
    assert c["projection"]["truth_obligations"] == 32
    assert c["projection"]["truth_obligations_deleted"] == 0
    assert c["projection"]["truth_obligations_closed"] == 0
    assert c["projection"]["terminal"] is False

    live_schedule = p["terminal_falsification_control_loop"]["current_schedule"]
    assert live_schedule == c["critical_path"]
    assert OLD not in live_schedule
    assert OLD not in p["next"]
    assert OLD in p["legacy_terminal_falsification_control_loop"]["current_schedule"]

    repair = p["post_v22_routing_repair"]
    assert repair["truth_obligations_deleted"] == 0
    assert repair["truth_obligations_closed"] == 0
    assert repair["terminal_credit_delta"] == 0
    assert repair["acceptance_credit_delta"] == 0
    assert repair["family_credit_delta"] == 0
    assert repair["capability_credit_delta"] == 0
    assert repair["ownership_credit_delta"] == 0

    assert a["status"].startswith("ACTIVE_FAIL_CLOSED")
    assert a["current_routing"]["projection"] == EXPECTED_COUNTS
    assert a["current_routing"]["truth_obligations_preserved"] == 32
    assert a["current_routing"]["truth_obligations_deleted"] == 0
    assert a["current_routing"]["terminal_credit_delta"] == 0
    assert OLD not in a["next"]

    return {
        "status": "PASS__POST_V7_CURRENT_ROUTING_REPAIRED__32_TRUTHS_PRESERVED__ZERO_CREDIT",
        "old_falsified_route_removed_from_live_schedule": True,
        "route_counts": route_counts,
        "truth_obligations": 32,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
