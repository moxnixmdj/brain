"""Brain-owned fail-closed judgment control envelope.

This module does not generate domain judgments. A declared general cognition
substrate may propose a conclusion, abstention, or discriminator request.
The Brain-owned envelope decides whether that proposal is permitted to become
terminal output, using explicit evidence/identifiability/provenance predicates.

Scope:
- finance direct-judgment admission control
- unknown-domain transfer/abstention admission control
- deterministic configured-vs-bare materiality counterfactual

No benchmark or hidden-oracle case is consumed here.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_JUDGMENT_CONTROL_ENVELOPE_V1"
MODES = {"FINANCE", "UNKNOWN_DOMAIN"}
DECISIONS = {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}
IDENTIFIABILITY = {"UNIQUE", "AMBIGUOUS", "NONIDENTIFIABLE"}
FINITE_IDENTIFIABILITY = {"RESOLVED", "NONIDENTIFIABLE", "NOT_APPLICABLE"}

COMMON_REQUIRED_TRUE = (
    "brain_sources_bound",
    "source_traceability_pass",
    "provenance_complete",
    "requirement_coverage_pass",
    "counterexample_coverage_pass",
    "contradictions_exposed_or_resolved",
)

FINANCE_REQUIRED_TRUE = (
    "rule_applicability_verified",
    "material_exceptions_complete",
    "exact_reconciliation_pass",
)

UNKNOWN_REQUIRED_TRUE = (
    "transfer_provenance_verified",
    "negative_transfer_checked",
)

def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _true_errors(evidence: Mapping[str, Any], fields: tuple[str, ...]) -> list[str]:
    return [f"REQUIRED_VERIFIED_PREDICATE_FALSE_OR_UNKNOWN:{field}"
            for field in fields if evidence.get(field) is not True]

def _base_validate(proposal: Any, evidence: Any, mode: str) -> list[str]:
    errors: list[str] = []
    if mode not in MODES:
        errors.append("MODE_INVALID")
    if not isinstance(proposal, Mapping):
        errors.append("PROPOSAL_NOT_OBJECT")
        return errors
    if not isinstance(evidence, Mapping):
        errors.append("EVIDENCE_NOT_OBJECT")
        return errors
    if proposal.get("decision") not in DECISIONS:
        errors.append("DECISION_INVALID")
    if evidence.get("semantic_identifiability") not in IDENTIFIABILITY:
        errors.append("SEMANTIC_IDENTIFIABILITY_INVALID_OR_UNKNOWN")
    if evidence.get("finite_identifiability") not in FINITE_IDENTIFIABILITY:
        errors.append("FINITE_IDENTIFIABILITY_INVALID_OR_UNKNOWN")
    return errors

def bare_terminal_decision(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Minimal bare route used only for the materiality counterfactual."""
    decision = proposal.get("decision")
    accepted = decision in DECISIONS
    return {
        "accepted": accepted,
        "status": "TERMINAL_ACCEPTED" if accepted else "BLOCKED",
        "errors": [] if accepted else ["DECISION_INVALID"],
    }

def configured_terminal_decision(
    proposal: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    """Fail closed unless the evidence permits the proposed terminal act."""
    errors = _base_validate(proposal, evidence, mode)
    if errors:
        return {
            "schema": SCHEMA,
            "accepted": False,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "mode": mode,
        }

    decision = proposal["decision"]
    sem = evidence["semantic_identifiability"]
    finite = evidence["finite_identifiability"]

    errors.extend(_true_errors(evidence, COMMON_REQUIRED_TRUE))

    if decision == "CONCLUDE":
        if sem != "UNIQUE":
            errors.append("FORCED_CONCLUSION_WITHOUT_UNIQUE_SEMANTIC_IDENTIFICATION")
        if not isinstance(proposal.get("claim_ids"), list) or not proposal["claim_ids"]:
            errors.append("CONCLUSION_CLAIMS_MISSING")
        if not isinstance(proposal.get("source_refs"), list) or not proposal["source_refs"]:
            errors.append("CONCLUSION_SOURCE_REFS_MISSING")

        if mode == "FINANCE":
            errors.extend(_true_errors(evidence, FINANCE_REQUIRED_TRUE))
        elif mode == "UNKNOWN_DOMAIN":
            errors.extend(_true_errors(evidence, UNKNOWN_REQUIRED_TRUE))
            if finite != "RESOLVED":
                errors.append("UNKNOWN_DOMAIN_CONCLUSION_WITHOUT_RESOLVED_VERSION_SPACE")

    elif decision == "ABSTAIN":
        justified = (
            sem in {"AMBIGUOUS", "NONIDENTIFIABLE"}
            or finite == "NONIDENTIFIABLE"
        )
        if not justified:
            errors.append("BLANKET_ABSTENTION_ON_IDENTIFIABLE_CASE")
        if not _nonempty(proposal.get("nonidentifiability_witness")):
            errors.append("ABSTENTION_WITNESS_MISSING")

    elif decision == "REQUEST_DISCRIMINATOR":
        justified = (
            sem in {"AMBIGUOUS", "NONIDENTIFIABLE"}
            or finite == "NONIDENTIFIABLE"
        )
        if not justified:
            errors.append("DISCRIMINATOR_REQUEST_WITHOUT_IDENTIFIABILITY_GAP")
        if not _nonempty(proposal.get("discriminator")):
            errors.append("DISCRIMINATOR_MISSING")
        if evidence.get("discriminator_authorized") is not True:
            errors.append("DISCRIMINATOR_NOT_AUTHORIZED")

    return {
        "schema": SCHEMA,
        "accepted": not errors,
        "status": "TERMINAL_ACCEPTED" if not errors else "TERMINAL_BLOCKED",
        "errors": sorted(set(errors)),
        "mode": mode,
        "decision": decision,
        "rule": (
            "GENERAL_COGNITION_MAY_PROPOSE__BRAIN_OWNS_TERMINAL_JUDGMENT_CONTROL__"
            "UNIQUE_SUPPORTED_CONCLUSIONS_ONLY__AMBIGUITY_REQUIRES_WITNESSED_ABSTENTION_"
            "OR_AUTHORIZED_DISCRIMINATOR__ZERO_UNSUPPORTED_TERMINAL_CLAIMS"
        ),
    }

def _common_good() -> dict[str, Any]:
    return {
        "brain_sources_bound": True,
        "source_traceability_pass": True,
        "provenance_complete": True,
        "requirement_coverage_pass": True,
        "counterexample_coverage_pass": True,
        "contradictions_exposed_or_resolved": True,
        "semantic_identifiability": "UNIQUE",
        "finite_identifiability": "NOT_APPLICABLE",
        "discriminator_authorized": False,
    }

def evaluate_materiality_counterfactual() -> dict[str, Any]:
    """Hold proposals fixed and change only Brain-owned control evidence."""
    finance_proposal = {
        "decision": "CONCLUDE",
        "claim_ids": ["synthetic-finance-claim"],
        "source_refs": ["synthetic-authority:section-1"],
    }
    finance_bad = _common_good()
    finance_bad.update({
        "rule_applicability_verified": False,
        "material_exceptions_complete": False,
        "exact_reconciliation_pass": True,
    })
    finance_good = _common_good()
    finance_good.update({
        "rule_applicability_verified": True,
        "material_exceptions_complete": True,
        "exact_reconciliation_pass": True,
    })

    unknown_proposal = {
        "decision": "CONCLUDE",
        "claim_ids": ["synthetic-transfer-claim"],
        "source_refs": ["synthetic-domain-a:receipt-1", "synthetic-domain-b:observation-1"],
    }
    unknown_bad = _common_good()
    unknown_bad.update({
        "semantic_identifiability": "AMBIGUOUS",
        "finite_identifiability": "NONIDENTIFIABLE",
        "transfer_provenance_verified": False,
        "negative_transfer_checked": True,
    })
    unknown_good = _common_good()
    unknown_good.update({
        "semantic_identifiability": "UNIQUE",
        "finite_identifiability": "RESOLVED",
        "transfer_provenance_verified": True,
        "negative_transfer_checked": True,
    })

    bare_finance = bare_terminal_decision(finance_proposal)
    configured_finance_bad = configured_terminal_decision(
        finance_proposal, finance_bad, mode="FINANCE"
    )
    configured_finance_good = configured_terminal_decision(
        finance_proposal, finance_good, mode="FINANCE"
    )

    bare_unknown = bare_terminal_decision(unknown_proposal)
    configured_unknown_bad = configured_terminal_decision(
        unknown_proposal, unknown_bad, mode="UNKNOWN_DOMAIN"
    )
    configured_unknown_good = configured_terminal_decision(
        unknown_proposal, unknown_good, mode="UNKNOWN_DOMAIN"
    )

    passed = (
        bare_finance["accepted"] is True
        and configured_finance_bad["accepted"] is False
        and configured_finance_good["accepted"] is True
        and bare_unknown["accepted"] is True
        and configured_unknown_bad["accepted"] is False
        and configured_unknown_good["accepted"] is True
    )

    return {
        "schema": "PROJECT_BRAIN_JUDGMENT_CONTROL_MATERIALITY_COUNTERFACTUAL_V1",
        "status": (
            "PASS__BRAIN_CONFIGURATION_MATERIALLY_CONTROLS_FINANCE_AND_UNKNOWN_DOMAIN_TERMINAL_JUDGMENT"
            if passed else "FAIL_CLOSED"
        ),
        "pass": passed,
        "same_proposal_stream_within_each_mode": True,
        "finance": {
            "bare": bare_finance,
            "configured_with_unverified_semantics": configured_finance_bad,
            "configured_after_verified_evidence": configured_finance_good,
        },
        "unknown_domain": {
            "bare": bare_unknown,
            "configured_with_nonidentifiable_transfer": configured_unknown_bad,
            "configured_after_resolved_transfer": configured_unknown_good,
        },
        "configuration_material_control_proven": passed,
        "model_quality_compared": False,
        "benchmark_case_content_consumed": False,
        "hidden_oracle_case_content_consumed": False,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "scope_limit": (
            "PROVES_CAUSAL_TERMINAL_CONTROL_AND_FAIL_CLOSED_JUDGMENT_DISCIPLINE_ONLY__"
            "DOES_NOT_PROVE_FINANCE_OR_UNKNOWN_DOMAIN_ACCEPTANCE_LEAVES_OR_OPUS55_PARITY"
        ),
    }

if __name__ == "__main__":
    import json
    print(json.dumps(evaluate_materiality_counterfactual(), indent=2, sort_keys=True))
