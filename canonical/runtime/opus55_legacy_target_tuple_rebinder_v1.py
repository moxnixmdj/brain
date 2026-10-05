from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

EXPECTED = {
    "CODING_TB4_GE_66_4": 66.4,
    "CHARTOGRAPHY_TOOLS_GE_89": 89.0,
    "HLE_TOOLS_GE_67_7": 67.7,
    "OSWORLD_2_1_PARTIAL_GE_81_8": 81.8,
    "CODING_FRONTIERCODE_GE_54_4": 54.4,
    "PROWORK_GDPVAL_GE_1846": 1846,
    "PROWORK_AA_BRIEFCASE_GE_1822": 1822,
    "ARTIFACT_AA_BRIEFCASE_GE_1822": 1822,
    "AUTOMATIONBENCH_GE_40": 40.0,
    "TB_SCIENCE_GE_58_7": 63.33333333333333,
}
REQUIRED_TUPLE_FIELDS = {
    "benchmark","benchmark_version","model","effort",
    "evaluator","harness","fallback_policy","unit",
}

class TargetRebindError(ValueError):
    pass

def validate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        raise TargetRebindError("DOCUMENT_NOT_OBJECT")
    rows = doc.get("bindings")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise TargetRebindError("BINDINGS_NOT_LIST")
    by = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise TargetRebindError("BINDING_NOT_OBJECT")
        pid = row.get("predicate_id")
        if pid in by:
            raise TargetRebindError("DUPLICATE_PREDICATE:" + str(pid))
        by[pid] = row
    if set(by) != set(EXPECTED):
        raise TargetRebindError("LEGACY_PREDICATE_SET_DRIFT")
    for pid, expected in EXPECTED.items():
        row = by[pid]
        if row.get("effective_target_value") != expected:
            raise TargetRebindError("TARGET_VALUE_DRIFT:" + pid)
        tup = row.get("target_tuple")
        if not isinstance(tup, Mapping) or not REQUIRED_TUPLE_FIELDS.issubset(tup):
            raise TargetRebindError("TARGET_TUPLE_INCOMPLETE:" + pid)
        for field in REQUIRED_TUPLE_FIELDS:
            if not tup.get(field):
                raise TargetRebindError("TARGET_TUPLE_EMPTY:" + pid + ":" + field)
        if row.get("target_source_role") == "LIVE_BOARD_REBASE":
            raise TargetRebindError("LIVE_BOARD_REBASE_FORBIDDEN:" + pid)
        if row.get("score_execution_authority") is not False:
            raise TargetRebindError("SCORE_EXECUTION_AUTHORITY_FORBIDDEN:" + pid)
    aa1 = by["PROWORK_AA_BRIEFCASE_GE_1822"]
    aa2 = by["ARTIFACT_AA_BRIEFCASE_GE_1822"]
    if aa1.get("target_tuple_id") != aa2.get("target_tuple_id"):
        raise TargetRebindError("AA_BRIEFCASE_TUPLE_REUSE_MISSING")
    if aa1.get("rating_pool_snapshot") != "FROZEN_PUBLICATION_SNAPSHOT_2026_09_22":
        raise TargetRebindError("AA_BRIEFCASE_RATING_POOL_NOT_FROZEN")
    tb = by["TB_SCIENCE_GE_58_7"]
    if tb.get("predicate_label_target_value") != 58.7:
        raise TargetRebindError("TB_SCIENCE_LABEL_TARGET_DRIFT")
    if tb.get("route_id") != "PUBLIC_CURRENT_HARNESS":
        raise TargetRebindError("TB_SCIENCE_ROUTE_NOT_PRELOCKED_PUBLIC_CURRENT")
    if int(tb.get("consumed_brain_slots", 0)) <= 0:
        raise TargetRebindError("TB_SCIENCE_CONSUMED_HISTORY_NOT_PRESERVED")
    accounting = doc.get("accounting")
    if not isinstance(accounting, Mapping) or accounting.get("acceptance_credit_delta") != 0:
        raise TargetRebindError("NONZERO_ACCEPTANCE_CREDIT")
    return {
        "status": "PASS__TEN_LEGACY_PREDICATES_BOUND_TO_NINE_FROZEN_TARGET_TUPLES__ZERO_CREDIT",
        "bound_predicates": sorted(by),
        "unique_target_tuple_count": len({row.get("target_tuple_id") for row in rows}),
        "remaining_unbound_legacy": 0,
        "acceptance_credit_delta": 0,
        "score_execution_authority": False,
        "promotion_authority": False,
    }
