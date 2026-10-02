"""Brain-owned proof-carrying judgment control envelope.

A declared general cognition substrate may propose typed evidence, interpretations,
hypotheses, and a terminal act. This module recomputes the load-bearing checks with
Brain-owned deterministic components before any terminal judgment is permitted.

It does not infer arbitrary domain semantics or source truth by itself.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from canonical.runtime.source_traceable_semantic_ir import compile_semantic_ir
from canonical.runtime.semantic_identifiability_gate import adjudicate
from canonical.runtime.finite_identifiability import Experiment, Hypothesis, select_discriminator
from canonical.runtime.semantic_operator_counterfactuals import (
    compile_explicit_operator_contract,
    extract_semantic_operators,
    generate_counterfactual_obligations,
)
from canonical.runtime.bound_capabilities.evidence_decision_synthesis import (
    DecisionSynthesisError,
    synthesize,
)

SCHEMA = "PROJECT_BRAIN_JUDGMENT_CONTROL_ENVELOPE_V1"
MODES = {"FINANCE", "UNKNOWN_DOMAIN"}
DECISIONS = {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}

FINANCE_SUPERVISORY = "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE"
FINANCE_DOCUMENT = "DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"
UNKNOWN_TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
UNKNOWN_ABSTENTION = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"

LEAVES = {
    "FINANCE": {FINANCE_SUPERVISORY, FINANCE_DOCUMENT},
    "UNKNOWN_DOMAIN": {UNKNOWN_TRANSFER, UNKNOWN_ABSTENTION},
}

def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _required_ids(proposal: Mapping[str, Any], field: str, contributing: set[str], errors: list[str]) -> None:
    raw = proposal.get(field)
    if not isinstance(raw, list) or not raw or any(not _nonempty(x) for x in raw):
        errors.append(f"{field.upper()}_MISSING")
        return
    missing = sorted(set(raw) - contributing)
    if missing:
        errors.extend(f"{field.upper()}_NOT_CONTRIBUTING:{x}" for x in missing)

def _reconciliation_errors(rows: Any) -> list[str]:
    if rows is None:
        return []
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return ["RECONCILIATION_CHECKS_INVALID"]
    errors: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"RECONCILIATION_NOT_OBJECT:{i}")
            continue
        rid = str(row.get("id") or "").strip()
        if not rid:
            errors.append(f"RECONCILIATION_ID_MISSING:{i}")
            continue
        if rid in seen:
            errors.append(f"RECONCILIATION_ID_DUPLICATE:{rid}")
            continue
        seen.add(rid)
        try:
            lhs = Decimal(str(row["lhs"]))
            rhs = Decimal(str(row["rhs"]))
            tolerance = Decimal(str(row.get("tolerance", "0")))
        except (KeyError, InvalidOperation, ValueError):
            errors.append(f"RECONCILIATION_NUMBER_INVALID:{rid}")
            continue
        if not lhs.is_finite() or not rhs.is_finite() or not tolerance.is_finite() or tolerance < 0:
            errors.append(f"RECONCILIATION_NUMBER_INVALID:{rid}")
            continue
        if abs(lhs - rhs) > tolerance:
            errors.append(f"RECONCILIATION_MISMATCH:{rid}")
    return errors

def _finite_result(bundle: Mapping[str, Any]) -> dict[str, Any]:
    raw_h = bundle.get("hypotheses")
    raw_e = bundle.get("experiments")
    observations = bundle.get("observations", {})
    if not isinstance(raw_h, list) or not isinstance(raw_e, list) or not isinstance(observations, Mapping):
        return {"status": "FAIL_CLOSED", "errors": ["FINITE_MODEL_INVALID"]}
    try:
        hypotheses = [Hypothesis(str(x["id"]), x.get("payload")) for x in raw_h if isinstance(x, Mapping)]
        experiments = [
            Experiment(
                str(x["id"]),
                {str(k): str(v) for k, v in dict(x["outcomes"]).items()},
                float(x.get("cost", 1.0)),
            )
            for x in raw_e if isinstance(x, Mapping)
        ]
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "errors": [f"FINITE_MODEL_BUILD_ERROR:{type(exc).__name__}"]}
    return select_discriminator(hypotheses, experiments, dict(observations))

def _evaluate_bundle(bundle: Any, *, mode: str) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(bundle, Mapping):
        return {
            "pass": False,
            "errors": ["PROOF_BUNDLE_NOT_OBJECT"],
            "semantic_ir": {"status": "FAIL_CLOSED"},
            "operator_contract": {"pass": False},
            "semantic_identifiability": {"status": "FAIL_CLOSED"},
            "decision": {"status": "FAIL_CLOSED"},
            "finite_identifiability": {"status": "FAIL_CLOSED"},
        }

    if not _nonempty(bundle.get("source_text")):
        errors.append("SOURCE_TEXT_MISSING")
    semantic_ir = compile_semantic_ir(bundle.get("semantic_contract", {}))
    if semantic_ir.get("status") == "FAIL_CLOSED":
        errors.append("SEMANTIC_IR_FAIL_CLOSED")
    semantic_content_count = sum(
        len(semantic_ir.get(k) or [])
        for k in ("entities", "facts", "relations", "templates", "ambiguities", "conflicts")
    )
    if semantic_content_count == 0:
        errors.append("SEMANTIC_IR_CONTENT_EMPTY")

    try:
        operator = compile_explicit_operator_contract(
            bundle.get("source_text", ""),
            bindings=bundle.get("operator_bindings", []),
            scenarios=bundle.get("counterfactual_scenarios", []),
            source=str(bundle.get("source_id") or "judgment-source"),
        )
    except Exception as exc:
        operator = {"pass": False, "errors": [f"{type(exc).__name__}:{exc}"]}
    if operator.get("pass") is not True:
        errors.append("EXPLICIT_SEMANTIC_OPERATOR_CONTRACT_FAIL")

    try:
        ident = adjudicate(
            bundle.get("interpretations", []),
            authorized_context_ids=bundle.get("authorized_context_ids", []),
        )
    except Exception as exc:
        ident = {"status": "FAIL_CLOSED", "errors": [f"{type(exc).__name__}:{exc}"]}
    if ident.get("status") == "FAIL_CLOSED":
        errors.append("SEMANTIC_IDENTIFIABILITY_FAIL_CLOSED")

    try:
        decision = synthesize(bundle.get("decision_problem", {}))
    except Exception as exc:
        decision = {"status": "FAIL_CLOSED", "errors": [f"{type(exc).__name__}:{exc}"]}
        errors.append("EVIDENCE_DECISION_SYNTHESIS_FAIL_CLOSED")

    finite = _finite_result(bundle) if mode == "UNKNOWN_DOMAIN" else {"status": "NOT_APPLICABLE"}
    if finite.get("status") in {"FAIL_CLOSED", "MODEL_FALSIFIED"}:
        errors.append("FINITE_IDENTIFIABILITY_FAIL_CLOSED")

    return {
        "pass": not errors,
        "errors": sorted(set(errors)),
        "semantic_ir": semantic_ir,
        "operator_contract": operator,
        "semantic_identifiability": ident,
        "decision": decision,
        "finite_identifiability": finite,
    }

def bare_terminal_decision(proposal: Mapping[str, Any]) -> dict[str, Any]:
    decision = proposal.get("decision") if isinstance(proposal, Mapping) else None
    accepted = decision in DECISIONS
    return {"accepted": accepted, "status": "TERMINAL_ACCEPTED" if accepted else "BLOCKED",
            "errors": [] if accepted else ["DECISION_INVALID"]}

def configured_terminal_decision(proposal: Any, proof_bundle: Any, *, mode: str) -> dict[str, Any]:
    errors: list[str] = []
    if mode not in MODES:
        errors.append("MODE_INVALID")
    if not isinstance(proposal, Mapping):
        errors.append("PROPOSAL_NOT_OBJECT")
        proposal = {}
    decision_kind = proposal.get("decision")
    if decision_kind not in DECISIONS:
        errors.append("DECISION_INVALID")
    leaf_id = str(proposal.get("leaf_id") or "")
    if mode in LEAVES and leaf_id not in LEAVES[mode]:
        errors.append("LEAF_ID_INVALID_FOR_MODE")

    recomputed = _evaluate_bundle(proof_bundle, mode=mode)
    errors.extend(recomputed["errors"])
    semantic_ir = recomputed["semantic_ir"]
    ident = recomputed["semantic_identifiability"]
    decision = recomputed["decision"]
    finite = recomputed["finite_identifiability"]

    selected = decision.get("selected_alternative")
    rankings = decision.get("rankings") if isinstance(decision.get("rankings"), list) else []
    selected_row = next((x for x in rankings if isinstance(x, Mapping) and x.get("alternative") == selected), {})
    contributing = set(selected_row.get("contributing_evidence") or [])

    if decision_kind == "CONCLUDE":
        if semantic_ir.get("status") != "COMPILED":
            errors.append("CONCLUSION_WITH_UNRESOLVED_SEMANTIC_CONFLICT_OR_AMBIGUITY")
        if ident.get("status") != "UNIQUE":
            errors.append("FORCED_CONCLUSION_WITHOUT_UNIQUE_SEMANTIC_IDENTIFICATION")
        if decision.get("status") != "DECIDED":
            errors.append("CONCLUSION_WITHOUT_DETERMINISTIC_EVIDENCE_DECISION")
        proposed_selected = str(proposal.get("selected_alternative") or "")
        if not proposed_selected or proposed_selected != selected:
            errors.append("PROPOSED_CONCLUSION_DOES_NOT_MATCH_BRAIN_DECISION")

        if mode == "FINANCE":
            if leaf_id == FINANCE_SUPERVISORY:
                _required_ids(proposal, "rule_evidence_ids", contributing, errors)
                _required_ids(proposal, "exception_evidence_ids", contributing, errors)
            elif leaf_id == FINANCE_DOCUMENT:
                _required_ids(proposal, "fact_evidence_ids", contributing, errors)
                _required_ids(proposal, "cross_reference_evidence_ids", contributing, errors)
                _required_ids(proposal, "exception_evidence_ids", contributing, errors)
            errors.extend(_reconciliation_errors(proposal.get("reconciliation_checks")))
        elif mode == "UNKNOWN_DOMAIN":
            if finite.get("status") != "RESOLVED":
                errors.append("UNKNOWN_DOMAIN_CONCLUSION_WITHOUT_RESOLVED_VERSION_SPACE")
            if leaf_id == UNKNOWN_TRANSFER:
                _required_ids(proposal, "transfer_evidence_ids", contributing, errors)
                _required_ids(proposal, "negative_transfer_evidence_ids", contributing, errors)

    elif decision_kind == "ABSTAIN":
        finite_nonident = finite.get("status") == "NONIDENTIFIABLE_UNDER_AUTHORIZED_EXPERIMENTS"
        semantic_nonident = ident.get("status") == "AMBIGUOUS"
        semantic_unknowns = semantic_ir.get("status") == "COMPILED_WITH_UNKNOWNS"
        if not (finite_nonident or semantic_nonident or semantic_unknowns):
            errors.append("BLANKET_ABSTENTION_ON_IDENTIFIABLE_CASE")
        if not _nonempty(proposal.get("nonidentifiability_witness")):
            errors.append("ABSTENTION_WITNESS_MISSING")

    elif decision_kind == "REQUEST_DISCRIMINATOR":
        allowed: set[str] = set()
        if finite.get("status") == "SELECT_EXPERIMENT" and _nonempty(finite.get("experiment_id")):
            allowed.add(str(finite["experiment_id"]))
        if ident.get("status") == "AMBIGUOUS":
            for row in ident.get("ambiguity_witness") or []:
                if isinstance(row, Mapping) and _nonempty(row.get("discriminator")):
                    allowed.add(str(row["discriminator"]).strip())
        requested = str(proposal.get("discriminator") or "").strip()
        if not requested:
            errors.append("DISCRIMINATOR_MISSING")
        elif requested not in allowed:
            errors.append("DISCRIMINATOR_NOT_DERIVED_FROM_RECOMPUTED_IDENTIFIABILITY_GAP")

    return {
        "schema": SCHEMA,
        "accepted": not errors,
        "status": "TERMINAL_ACCEPTED" if not errors else "TERMINAL_BLOCKED",
        "errors": sorted(set(errors)),
        "mode": mode,
        "leaf_id": leaf_id,
        "decision": decision_kind,
        "recomputed_proof": recomputed,
        "rule": (
            "GENERAL_COGNITION_MAY_PROPOSE_TYPED_STRUCTURE__"
            "BRAIN_RECOMPUTES_PROVENANCE_EVIDENCE_IDENTIFIABILITY_COUNTERFACTUALS_AND_DECISION__"
            "CALLER_VERIFIED_BOOLEANS_HAVE_ZERO_AUTHORITY__TERMINAL_ACT_REQUIRES_PROOF_CARRYING_INPUT"
        ),
    }

def _operator_bundle(text: str, source_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ops = extract_semantic_operators(text, source=source_id)
    bindings = []
    for op in ops:
        row = {"operator_id": op.operator_id, "semantic_class": op.semantic_class}
        if op.bound_value is not None:
            row["bound_value"] = op.bound_value
        if op.semantic_class == "AMBIGUOUS_ANY":
            row["interpretations"] = ["existential", "universal"]
        bindings.append(row)
    scenarios = []
    for obligation in generate_counterfactual_obligations(text, source=source_id):
        if obligation.counterfactual_kind == "ANY_SEMANTICS_MUST_BE_DISAMBIGUATED":
            disposition = "DISAMBIGUATE"
        elif "ACCEPT" in obligation.counterfactual_kind:
            disposition = "ACCEPT"
        else:
            disposition = "REJECT"
        scenarios.append({
            "operator_id": obligation.operator_id,
            "counterfactual_kind": obligation.counterfactual_kind,
            "expected_disposition": disposition,
        })
    return bindings, scenarios

def _decision_problem(evidence_ids: Sequence[str], *, alternative: str) -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": "synthetic-judgment-materiality",
        "question": "Which terminal alternative is supported?",
        "alternatives": [{"id": alternative, "label": alternative}],
        "constraints": [],
        "evidence": [
            {
                "id": eid,
                "alternative": alternative,
                "relation": "SUPPORTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "group-" + eid,
                "claim": "synthetic proof item " + eid,
                "provenance": [{"source": "synthetic-authority", "ref": "section-" + eid}],
            }
            for eid in evidence_ids
        ],
        "policy": {
            "minimum_support_ratio": 1.0,
            "maximum_conflict_ratio": 0.0,
            "minimum_independent_support_groups": len(evidence_ids),
            "minimum_net_margin": 0.0,
        },
    }

def _base_bundle(text: str, source_id: str, evidence_ids: Sequence[str], alternative: str) -> dict[str, Any]:
    bindings, scenarios = _operator_bundle(text, source_id)
    return {
        "source_id": source_id,
        "source_text": text,
        "operator_bindings": bindings,
        "counterfactual_scenarios": scenarios,
        "semantic_contract": {
            "entities": [{"id": "subject", "type": "case", "source": {"span": [0, len(text)]}}],
            "facts": [{
                "subject": "subject",
                "predicate": "supported_terminal_alternative",
                "object": alternative,
                "source": {"span": [0, len(text)]},
            }],
            "relations": [], "templates": [], "ambiguities": [],
        },
        "interpretations": [{
            "id": "i1", "meaning": alternative,
            "consistent_with_source": True,
            "consistent_with_authorized_context": True,
            "materially_distinct": True,
            "discriminator": "",
        }],
        "authorized_context_ids": [source_id],
        "decision_problem": _decision_problem(evidence_ids, alternative=alternative),
    }

def evaluate_materiality_counterfactual() -> dict[str, Any]:
    finance_text = "Every applicable rule must not omit a material exception before execution."
    finance_good_bundle = _base_bundle(finance_text, "synthetic-finance", ["rule", "exception"], "APPLY_RULE")
    finance_bad_bundle = _base_bundle(finance_text, "synthetic-finance", ["rule"], "APPLY_RULE")
    finance_proposal = {
        "decision": "CONCLUDE", "leaf_id": FINANCE_SUPERVISORY,
        "selected_alternative": "APPLY_RULE",
        "rule_evidence_ids": ["rule"], "exception_evidence_ids": ["exception"],
        "reconciliation_checks": [],
    }

    unknown_text = "Every transfer must not ignore a negative-transfer check before conclusion."
    unknown_good_bundle = _base_bundle(
        unknown_text, "synthetic-unknown", ["transfer", "negative"], "TRANSFER_PRIMITIVE"
    )
    unknown_good_bundle.update({
        "hypotheses": [{"id": "h1"}, {"id": "h2"}],
        "experiments": [{"id": "probe", "outcomes": {"h1": "a", "h2": "b"}, "cost": 1.0}],
        "observations": {"probe": "a"},
    })
    unknown_bad_bundle = dict(unknown_good_bundle)
    unknown_bad_bundle["observations"] = {}
    unknown_proposal = {
        "decision": "CONCLUDE", "leaf_id": UNKNOWN_TRANSFER,
        "selected_alternative": "TRANSFER_PRIMITIVE",
        "transfer_evidence_ids": ["transfer"], "negative_transfer_evidence_ids": ["negative"],
    }

    bare_finance = bare_terminal_decision(finance_proposal)
    configured_finance_bad = configured_terminal_decision(finance_proposal, finance_bad_bundle, mode="FINANCE")
    configured_finance_good = configured_terminal_decision(finance_proposal, finance_good_bundle, mode="FINANCE")
    bare_unknown = bare_terminal_decision(unknown_proposal)
    configured_unknown_bad = configured_terminal_decision(unknown_proposal, unknown_bad_bundle, mode="UNKNOWN_DOMAIN")
    configured_unknown_good = configured_terminal_decision(unknown_proposal, unknown_good_bundle, mode="UNKNOWN_DOMAIN")

    passed = (
        bare_finance["accepted"] is True
        and configured_finance_bad["accepted"] is False
        and configured_finance_good["accepted"] is True
        and bare_unknown["accepted"] is True
        and configured_unknown_bad["accepted"] is False
        and configured_unknown_good["accepted"] is True
    )
    return {
        "schema": "PROJECT_BRAIN_JUDGMENT_CONTROL_MATERIALITY_COUNTERFACTUAL_V2",
        "status": (
            "PASS__PROOF_CARRYING_BRAIN_CONFIGURATION_MATERIALLY_CONTROLS_FINANCE_AND_UNKNOWN_DOMAIN_TERMINAL_JUDGMENT"
            if passed else "FAIL_CLOSED"
        ),
        "pass": passed,
        "finance": {
            "bare": bare_finance,
            "configured_missing_required_exception_evidence": configured_finance_bad,
            "configured_with_recomputed_proof": configured_finance_good,
        },
        "unknown_domain": {
            "bare": bare_unknown,
            "configured_with_unresolved_version_space": configured_unknown_bad,
            "configured_with_recomputed_proof": configured_unknown_good,
        },
        "configuration_material_control_proven": passed,
        "caller_verified_boolean_authority": False,
        "model_quality_compared": False,
        "benchmark_case_content_consumed": False,
        "hidden_oracle_case_content_consumed": False,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "scope_limit": (
            "PROVES_CAUSAL_TERMINAL_CONTROL_OF_PROOF_CARRYING_JUDGMENT_TRANSACTIONS_ONLY__"
            "DOES_NOT_PROVE_RAW_DOMAIN_SEMANTIC_EXTRACTION_SOURCE_TRUTH_FINANCE_OR_UNKNOWN_DIRECT_LEAF_PASS_OR_OPUS55_PARITY"
        ),
    }

if __name__ == "__main__":
    import json
    print(json.dumps(evaluate_materiality_counterfactual(), indent=2, sort_keys=True))
