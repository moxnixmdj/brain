"""Fail-closed proof-carrying shadow evaluation lease.

This module MAY establish that an evaluation is structurally safe to collect into
escrow. It NEVER grants acceptance, promotion, terminal credit, or ordinary
fresh-reality authority.

The only intended optimization is to permit independently authorized,
precommitted benchmark collection to overlap causally unrelated zero-reality
work while keeping the result unavailable to the frozen candidate/planner until
the global reducer allows release.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime.generic_precommit_isolation_theorem_v1 import (
    verify_generic_isolation,
    verify_benchmark_thin_adapter,
)

SCHEMA = "PROJECT_BRAIN_TERMINAL_SHADOW_EXECUTION_LEASE_V1"


def evaluate_shadow_lease(
    isolation_receipt: Mapping[str, Any],
    thin_adapter: Mapping[str, Any],
    *,
    benchmark_id: str,
    candidate_epoch: str,
    zero_spend_guard_pass: bool,
    result_escrowed: bool,
    candidate_can_read_escrow: bool,
    planner_can_read_escrow: bool,
    benchmark_specific_shadow_authority: bool,
) -> dict[str, Any]:
    """Return whether collection may occur under a separate shadow authority.

    Important: a passing result authorizes collection into escrow only. It does
    not authorize result release, acceptance credit, promotion, or terminal
    claims.
    """
    reasons: list[str] = []
    benchmark_id = str(benchmark_id or "").strip()
    candidate_epoch = str(candidate_epoch or "").strip()

    if not benchmark_id:
        reasons.append("MISSING_BENCHMARK_ID")
    if not candidate_epoch:
        reasons.append("MISSING_CANDIDATE_EPOCH")

    iso = verify_generic_isolation(isolation_receipt)
    if not iso.get("generic_isolation_kernel_pass"):
        reasons.append("GENERIC_PRECOMMIT_ISOLATION_NOT_PROVED")

    adapter = verify_benchmark_thin_adapter(thin_adapter)
    if not adapter.get("benchmark_thin_adapter_pass"):
        reasons.append("BENCHMARK_THIN_ADAPTER_NOT_PROVED")

    if zero_spend_guard_pass is not True:
        reasons.append("ZERO_SPEND_GUARD_NOT_PROVED")
    if result_escrowed is not True:
        reasons.append("RESULT_NOT_ESCROWED")
    if candidate_can_read_escrow is not False:
        reasons.append("CANDIDATE_ESCROW_READ_PATH_NOT_EXCLUDED")
    if planner_can_read_escrow is not False:
        reasons.append("PLANNER_ESCROW_READ_PATH_NOT_EXCLUDED")
    if benchmark_specific_shadow_authority is not True:
        reasons.append("BENCHMARK_SPECIFIC_SHADOW_AUTHORITY_ABSENT")

    ready = not reasons
    return {
        "schema": SCHEMA,
        "benchmark_id": benchmark_id,
        "candidate_epoch": candidate_epoch,
        "shadow_collection_ready": ready,
        "reasons": reasons,
        "generic_isolation_pass": bool(iso.get("generic_isolation_kernel_pass")),
        "thin_adapter_pass": bool(adapter.get("benchmark_thin_adapter_pass")),
        "result_release_ready": False,
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
        "terminal_credit_authorized": False,
        "fresh_reality_authority_granted_by_this_module": False,
        "requires_global_fixed_point_before_result_release": True,
        "requires_separate_root_projection_activation": True,
    }
