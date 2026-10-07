from __future__ import annotations

import hashlib
from typing import Any, Mapping

from canonical.runtime import judgment_control_envelope_v1 as base
from canonical.runtime.bound_capabilities.evidence_decision_synthesis import (
    DecisionSynthesisError,
    synthesize,
)
from canonical.runtime.finance_source_coverage_certificate_v1 import (
    verify_finance_source_coverage,
)

SCHEMA = "PROJECT_BRAIN_JUDGMENT_COMMON_POLICY_REGION_GATE_V1"
REGION_SCHEMA = "PROJECT_BRAIN_COMMON_POLICY_REGION_PROOF_V1"
UNIQUE_ERROR = "FORCED_CONCLUSION_WITHOUT_UNIQUE_SEMANTIC_IDENTIFICATION"


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fail(base_result: Mapping[str, Any], reason: str, extra: Any = None) -> dict[str, Any]:
    out = dict(base_result)
    out["accepted"] = False
    out["status"] = "TERMINAL_BLOCKED"
    gate = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
    if extra is not None:
        gate["detail"] = extra
    out["common_policy_region_gate"] = gate
    return out


def _selected_contributing(decision: Mapping[str, Any]) -> set[str]:
    selected = decision.get("selected_alternative")
    rankings = decision.get("rankings")
    if not isinstance(rankings, list):
        return set()
    row = next(
        (
            x
            for x in rankings
            if isinstance(x, Mapping) and x.get("alternative") == selected
        ),
        {},
    )
    return {str(x) for x in (row.get("contributing_evidence") or [])}


def configured_terminal_decision(
    proposal: Any,
    proof_bundle: Any,
    *,
    mode: str,
) -> dict[str, Any]:
    """Conservative extension of judgment-control v1.

    V1 remains authoritative for every condition except one known overconstraint:
    when CONCLUDE is blocked *only* because multiple surviving interpretations are
    not unique, this wrapper may repair that single error iff every surviving
    interpretation independently recomputes to the same proposed selected policy
    under the existing Brain-owned typed decision synthesizer and all finance
    source/evidence/reconciliation checks remain satisfied for every interpretation.

    This component does not establish completeness or truth of the supplied
    interpretation set. That upstream semantic-boundary obligation remains open.
    """
    v1 = base.configured_terminal_decision(proposal, proof_bundle, mode=mode)
    if v1.get("accepted") is True:
        out = dict(v1)
        out["common_policy_region_gate"] = {
            "schema": SCHEMA,
            "pass": True,
            "status": "NOT_NEEDED__V1_ALREADY_ACCEPTED",
            "terminal_authority": False,
            "capability_credit_delta": 0,
        }
        return out

    if not isinstance(proposal, Mapping) or proposal.get("decision") != "CONCLUDE":
        return _fail(v1, "ONLY_CONCLUDE_UNIQUE_OVERCONSTRAINT_IS_REPAIRABLE")

    errors = set(str(x) for x in (v1.get("errors") or []))
    if errors != {UNIQUE_ERROR}:
        return _fail(
            v1,
            "V1_HAS_NONREPAIRABLE_ERRORS",
            {"errors": sorted(errors)},
        )

    recomputed = v1.get("recomputed_proof")
    if not isinstance(recomputed, Mapping):
        return _fail(v1, "RECOMPUTED_PROOF_MISSING")
    ident = recomputed.get("semantic_identifiability")
    if not isinstance(ident, Mapping) or ident.get("status") != "AMBIGUOUS":
        return _fail(v1, "AMBIGUOUS_IDENTIFIABILITY_REQUIRED")

    witnesses = ident.get("ambiguity_witness")
    if not isinstance(witnesses, list) or len(witnesses) < 2:
        return _fail(v1, "SURVIVING_INTERPRETATIONS_REQUIRED")

    expected: dict[str, str] = {}
    for i, row in enumerate(witnesses):
        if not isinstance(row, Mapping):
            return _fail(v1, f"INTERPRETATION_WITNESS_INVALID:{i}")
        iid = str(row.get("id") or "").strip()
        meaning = str(row.get("meaning") or "").strip()
        if not iid or not meaning or iid in expected:
            return _fail(v1, f"INTERPRETATION_ID_OR_MEANING_INVALID:{i}")
        expected[iid] = _sha_text(meaning)

    if not isinstance(proof_bundle, Mapping):
        return _fail(v1, "PROOF_BUNDLE_REQUIRED")
    region = proof_bundle.get("common_policy_region")
    if not isinstance(region, Mapping) or region.get("schema") != REGION_SCHEMA:
        return _fail(v1, "COMMON_POLICY_REGION_PROOF_REQUIRED")

    rows = region.get("interpretation_decision_problems")
    if not isinstance(rows, list):
        return _fail(v1, "INTERPRETATION_DECISION_PROBLEMS_REQUIRED")

    by_id: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            return _fail(v1, f"REGION_ROW_INVALID:{i}")
        iid = str(row.get("interpretation_id") or "").strip()
        if not iid or iid in by_id:
            return _fail(v1, f"REGION_INTERPRETATION_ID_INVALID:{i}")
        by_id[iid] = row

    if set(by_id) != set(expected):
        return _fail(
            v1,
            "REGION_INTERPRETATION_DOMAIN_MISMATCH",
            {
                "missing": sorted(set(expected) - set(by_id)),
                "extra": sorted(set(by_id) - set(expected)),
            },
        )

    proposed = str(proposal.get("selected_alternative") or "").strip()
    if not proposed:
        return _fail(v1, "PROPOSED_SELECTED_ALTERNATIVE_REQUIRED")

    leaf_id = str(proposal.get("leaf_id") or "")
    per_interpretation = []
    for iid in sorted(expected):
        row = by_id[iid]
        if row.get("meaning_sha256") != expected[iid]:
            return _fail(v1, f"INTERPRETATION_MEANING_BINDING_MISMATCH:{iid}")
        problem = row.get("decision_problem")
        try:
            decision = synthesize(problem)
        except DecisionSynthesisError as exc:
            return _fail(v1, f"INTERPRETATION_DECISION_INVALID:{iid}:{exc}")

        if decision.get("status") != "DECIDED":
            return _fail(
                v1,
                f"INTERPRETATION_POLICY_NOT_DECIDED:{iid}",
                {"status": decision.get("status")},
            )
        if decision.get("selected_alternative") != proposed:
            return _fail(
                v1,
                "NO_COMMON_POLICY_OVER_SURVIVING_INTERPRETATIONS",
                {
                    "interpretation_id": iid,
                    "selected": decision.get("selected_alternative"),
                    "proposed": proposed,
                },
            )

        contributing = _selected_contributing(decision)
        if mode == "FINANCE":
            coverage = verify_finance_source_coverage(
                proof_bundle,
                contributing_evidence=contributing,
                leaf_id=leaf_id,
            )
            if coverage.get("pass") is not True:
                return _fail(
                    v1,
                    f"INTERPRETATION_FINANCE_SOURCE_COVERAGE_FAILED:{iid}",
                    {"errors": coverage.get("errors") or []},
                )
            local_errors: list[str] = []
            if leaf_id == base.FINANCE_SUPERVISORY:
                base._required_ids(proposal, "rule_evidence_ids", contributing, local_errors)
                base._required_ids(proposal, "exception_evidence_ids", contributing, local_errors)
            elif leaf_id == base.FINANCE_DOCUMENT:
                base._required_ids(proposal, "fact_evidence_ids", contributing, local_errors)
                base._required_ids(proposal, "cross_reference_evidence_ids", contributing, local_errors)
                base._required_ids(proposal, "exception_evidence_ids", contributing, local_errors)
            local_errors.extend(base._reconciliation_errors(proposal.get("reconciliation_checks")))
            if local_errors:
                return _fail(
                    v1,
                    f"INTERPRETATION_FINANCE_LOAD_BEARING_CHECK_FAILED:{iid}",
                    {"errors": sorted(set(local_errors))},
                )

        per_interpretation.append(
            {
                "interpretation_id": iid,
                "meaning_sha256": expected[iid],
                "decision_input_sha256": decision.get("input_sha256"),
                "selected_alternative": decision.get("selected_alternative"),
                "constraint_states": {
                    str(x.get("alternative")): x.get("constraint_state")
                    for x in (decision.get("rankings") or [])
                    if isinstance(x, Mapping)
                },
                "contributing_evidence": sorted(contributing),
            }
        )

    out = dict(v1)
    out["accepted"] = True
    out["status"] = "TERMINAL_ACCEPTED"
    out["errors"] = []
    out["common_policy_region_gate"] = {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__COMMON_RECOMPUTED_POLICY_OVER_ALL_SURVIVING_INTERPRETATIONS",
        "repaired_v1_error": UNIQUE_ERROR,
        "selected_policy_id": proposed,
        "surviving_interpretation_count": len(per_interpretation),
        "per_interpretation": per_interpretation,
        "all_other_v1_checks_preserved": True,
        "interpretation_set_completeness_self_certified": False,
        "remaining_upstream_obligation": (
            "PROVE_THE_SURVIVING_INTERPRETATION_OR_CONSTRAINT_SET_IS_SOUNDLY_COMPLETE_"
            "FOR_THE_BOUND_POLICY_RELEVANT_SEMANTIC_BASIS_OR_USE_A_DIRECT_E2E_CERTIFICATE"
        ),
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
    return out
