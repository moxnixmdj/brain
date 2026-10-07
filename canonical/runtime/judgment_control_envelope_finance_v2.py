"""Stricter finance judgment route with deterministic raw-source coverage.

This wrapper preserves the already-certified judgment_control_envelope_v1 bytes and
adds a fail-closed finance-only conclusion gate. It grants no semantic completeness
credit: every deterministic source unit must be bound to evidence that actually
contributes to the selected Brain decision, while correctness of each binding remains
an explicit proof obligation.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.finance_source_coverage_certificate_v1 import verify_finance_source_coverage
from canonical.runtime.judgment_control_envelope_v1 import configured_terminal_decision as _base_decision


def configured_terminal_decision(
    proposal: Any,
    proof_bundle: Any,
    *,
    mode: str,
) -> dict[str, Any]:
    out = _base_decision(proposal, proof_bundle, mode=mode)
    result = dict(out)
    result["finance_source_coverage"] = {
        "status": "NOT_APPLICABLE",
        "pass": True,
        "errors": [],
    }

    if mode != "FINANCE" or not isinstance(proposal, Mapping) or proposal.get("decision") != "CONCLUDE":
        return result

    recomputed = result.get("recomputed_proof")
    if not isinstance(recomputed, Mapping):
        coverage = {
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["RECOMPUTED_PROOF_MISSING"],
        }
    else:
        decision = recomputed.get("decision")
        decision = decision if isinstance(decision, Mapping) else {}
        selected = decision.get("selected_alternative")
        rankings = decision.get("rankings")
        rankings = rankings if isinstance(rankings, list) else []
        selected_row = next(
            (
                row for row in rankings
                if isinstance(row, Mapping) and row.get("alternative") == selected
            ),
            {},
        )
        contributing = set(selected_row.get("contributing_evidence") or [])
        leaf_id = str(result.get("leaf_id") or proposal.get("leaf_id") or "")
        coverage = verify_finance_source_coverage(
            proof_bundle,
            contributing_evidence=contributing,
            leaf_id=leaf_id,
        )

    result["finance_source_coverage"] = coverage
    if coverage.get("pass") is not True:
        errors = set(result.get("errors") or [])
        errors.add("FINANCE_SOURCE_COVERAGE_FAIL_CLOSED")
        errors.update(coverage.get("errors") or [])
        result["errors"] = sorted(errors)
        result["accepted"] = False
        result["status"] = "TERMINAL_BLOCKED"

    return result
