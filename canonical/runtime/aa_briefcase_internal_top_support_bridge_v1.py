from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_INTERNAL_TOP_SUPPORT_BRIDGE_V1"
TARGET_BENCHMARK = "AA-Briefcase"
TARGET_VERSION = "1.1"
TARGET_TASK_COUNT = 91
TARGET_DIMENSIONS = frozenset({"RUBRIC", "ANALYTICAL_QUALITY", "PRESENTATION"})


class BridgeError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _require_bool(obj: Mapping[str, Any], key: str) -> bool:
    value = obj.get(key)
    if value is not True:
        raise BridgeError(key.upper() + "_NOT_PROVED")
    return True


def verify_internal_top_support_bridge(
    source_top_law: Mapping[str, Any],
    coverage_binding: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(source_top_law, Mapping):
        raise BridgeError("SOURCE_TOP_LAW_NOT_OBJECT")
    if not isinstance(coverage_binding, Mapping):
        raise BridgeError("COVERAGE_BINDING_NOT_OBJECT")

    _require_bool(source_top_law, "top_law_proved")
    _require_bool(source_top_law, "independent_or_formal")
    _require_bool(source_top_law, "top_law_universal_over_source_domain")

    source_domain_sha256 = str(source_top_law.get("source_domain_sha256") or "")
    if len(source_domain_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_domain_sha256):
        raise BridgeError("SOURCE_DOMAIN_SHA256_INVALID")

    if coverage_binding.get("benchmark") != TARGET_BENCHMARK:
        raise BridgeError("BENCHMARK_MISMATCH")
    if coverage_binding.get("benchmark_version") != TARGET_VERSION:
        raise BridgeError("BENCHMARK_VERSION_MISMATCH")
    if coverage_binding.get("official_task_count") != TARGET_TASK_COUNT:
        raise BridgeError("OFFICIAL_TASK_COUNT_MISMATCH")
    if coverage_binding.get("source_domain_sha256") != source_domain_sha256:
        raise BridgeError("SOURCE_DOMAIN_BINDING_MISMATCH")

    _require_bool(coverage_binding, "source_domain_exact_or_superset_of_target")
    _require_bool(coverage_binding, "all_official_tasks_covered")
    _require_bool(coverage_binding, "every_load_bearing_dimension_covered")
    _require_bool(coverage_binding, "independent_or_formal")

    raw_dims = coverage_binding.get("load_bearing_dimensions")
    if not isinstance(raw_dims, list):
        raise BridgeError("LOAD_BEARING_DIMENSIONS_INVALID")
    dims = frozenset(str(x) for x in raw_dims)
    if dims != TARGET_DIMENSIONS:
        raise BridgeError("LOAD_BEARING_DIMENSIONS_INCOMPLETE")

    if coverage_binding.get("private_task_contents_inferred") is not False:
        raise BridgeError("PRIVATE_TASK_CONTENT_INFERENCE_FORBIDDEN")

    bridge_material = {
        "source_domain_sha256": source_domain_sha256,
        "benchmark": TARGET_BENCHMARK,
        "benchmark_version": TARGET_VERSION,
        "official_task_count": TARGET_TASK_COUNT,
        "load_bearing_dimensions": sorted(TARGET_DIMENSIONS),
        "coverage_binding_sha256": _sha(dict(coverage_binding)),
    }

    return {
        "schema": SCHEMA,
        "status": "PASS__AA_MATERIAL_TOP_SUPPORT_SCOPE_BRIDGED",
        "aa_material_top_support_proved": True,
        "target_distribution_required_for_material_order": False,
        "private_task_contents_required": False,
        "bridge_sha256": _sha(bridge_material),
        "bridge_material": bridge_material,
        "hard_nonclaims": [
            "THIS_BRIDGE_DOES_NOT_PROVE_REALIZED_PAIRWISE_JUDGE_OUTCOMES",
            "THIS_BRIDGE_DOES_NOT_PROVE_A_FROZEN_CROWD_BT_ELO_FLOOR",
            "THIS_BRIDGE_DOES_NOT_BY_ITSELF_CERTIFY_AA_BRIEFCASE_GE_1822",
        ],
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }


def current_selected_cell_probe() -> dict[str, Any]:
    """Encode the known 30-case professional top-law boundary.

    The source law is real and population-complete for its selected cell,
    but it is not universal over a source domain that is proved to contain
    all official AA-Briefcase tasks. The bridge must therefore fail closed.
    """
    source = {
        "top_law_proved": True,
        "independent_or_formal": True,
        "top_law_universal_over_source_domain": False,
        "source_domain_sha256": "0" * 64,
    }
    coverage = {
        "benchmark": TARGET_BENCHMARK,
        "benchmark_version": TARGET_VERSION,
        "official_task_count": TARGET_TASK_COUNT,
        "source_domain_sha256": "0" * 64,
        "source_domain_exact_or_superset_of_target": False,
        "all_official_tasks_covered": False,
        "every_load_bearing_dimension_covered": False,
        "independent_or_formal": False,
        "load_bearing_dimensions": sorted(TARGET_DIMENSIONS),
        "private_task_contents_inferred": False,
    }
    try:
        verify_internal_top_support_bridge(source, coverage)
    except BridgeError as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": str(exc),
            "known_selected_cell_top_law_preserved": True,
            "aa_material_top_support_proved": False,
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
        }
    raise AssertionError("CURRENT_SELECTED_CELL_MUST_NOT_BRIDGE_TO_AA")
