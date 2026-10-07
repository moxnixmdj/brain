from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "cut": (
        "canonical/governance/ABC_CURRENT_BOUND_MINIMUM_IRREDUCIBLE_INFORMATION_CUT_20261007_V3.json",
        "861b19d662bb6f936fe3c8437f6daa5084c04475",
    ),
    "quotient": (
        "canonical/governance/U_INFORMATION_TRICHOTOMY_QUOTIENT_20261007_V1.json",
        "f1f7e616b5983991a3cf6639fae05cf74b7ae7c8",
    ),
    "verification": (
        "canonical/verification/U_INFORMATION_TRICHOTOMY_QUOTIENT_WOLFRAM_VERIFICATION_20261007_V1.json",
        "614fe85f602cd7edddd4329c374fa7e718dc52ae",
    ),
}


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("OBJECT_REQUIRED:" + str(path))
    return value


def verify() -> dict:
    errors: list[str] = []
    for key, (rel, expected) in SOURCES.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append("MISSING:" + key)
        elif blob_sha(path) != expected:
            errors.append("DRIFT:" + key)

    pointer = load(ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json")
    quotient = load(ROOT / SOURCES["quotient"][0])
    independent = load(ROOT / SOURCES["verification"][0])

    if pointer.get("schema") != "PROJECT_BRAIN_CURRENT_TERMINAL_AUTHORITY_POINTER_V32":
        errors.append("POINTER_SCHEMA")

    status = str(pointer.get("status", ""))
    if "__15_INFORMATION_WAKE_CLASSES__" not in status:
        errors.append("STATUS_INFORMATION_COUNT")
    if "__14_POSITIVE_REALITY_CLASSES__" not in status:
        errors.append("STATUS_REALITY_COUNT")
    if "__8_CURRENT_BOUND_ACCESS_EXECUTION_LANES__" not in status:
        errors.append("STATUS_LANE_COUNT")

    truth = pointer.get("live_truth", {})
    expected_counts = {
        "current_noncomposition_wake_class_count": 15,
        "current_positive_reality_class_count": 14,
        "current_minimum_access_execution_lane_count": 8,
        "open_ABC_refinement_family_count": 13,
        "current_information_regime_count": 3,
    }
    for key, value in expected_counts.items():
        if truth.get(key) != value:
            errors.append("LIVE_COUNT:" + key)

    partition = truth.get("current_information_regime_partition", {})
    if partition != {
        "E_AVAILABLE_OR_DERIVABLE_ACCEPTANCE": 7,
        "S_HIDDEN_OR_UNBOUND_TASK_SCOPE": 6,
        "H_HIDDEN_TARGET_RELATION": 2,
    }:
        errors.append("REGIME_PARTITION")

    if (sum(partition.values()) if partition else -1) != 15:
        errors.append("REGIME_SUM")

    if quotient.get("universe_count") != 15:
        errors.append("QUOTIENT_UNIVERSE")
    if quotient.get("structural_partition", {}).get("union_equals_current_15_wake_universe") is not True:
        errors.append("QUOTIENT_UNION")
    if independent.get("verified", {}).get("regimes_union_equals_current_wake_universe") is not True:
        errors.append("INDEPENDENT_UNION")
    if independent.get("verified", {}).get("regimes_pairwise_disjoint") is not True:
        errors.append("INDEPENDENT_DISJOINT")

    if truth.get("current_U_empty_proved") is not False:
        errors.append("U_OVERCLAIM")
    if truth.get("complete_selected_context_ABC_closed") is not False:
        errors.append("ABC_OVERCLAIM")
    if truth.get("D_finality_closed") is not False:
        errors.append("D_OVERCLAIM")
    if truth.get("terminal") is not False:
        errors.append("TERMINAL_OVERCLAIM")
    if pointer.get("accounting", {}).get("terminal_credit_delta") != 0:
        errors.append("CREDIT_OVERCLAIM")

    return {
        "pass": not errors,
        "errors": errors,
        "pointer_schema": pointer.get("schema"),
        "information_wakes": 15 if not errors else None,
        "information_regimes": 3 if not errors else None,
        "positive_reality_classes": 14 if not errors else None,
        "execution_lanes": 8 if not errors else None,
        "open_refinements": 13 if not errors else None,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
