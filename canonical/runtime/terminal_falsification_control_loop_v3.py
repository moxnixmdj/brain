from __future__ import annotations

import copy
from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.terminal_falsification_control_loop_v2 import (
    compile_control_loop,
)

SCHEMA = "PROJECT_BRAIN_TERMINAL_UTILITY_QUOTIENT_CONTROL_REPAIR_V1"
OLD = "C_UNIVERSAL_OBSERVABLE_BEHAVIOR_DOMINANCE_BINDING_V1"
NEW = "C_TARGET_RELATIVE_UTILITY_QUOTIENT_DOMINANCE_AND_OWNERSHIP_V3"
LEMMA = "UTILITY_AND_EQUAL_OR_BETTER_ORDERING_WELL_FORMED"

EXPECTED = {
    "source_control": (
        "canonical/governance/TERMINAL_FALSIFICATION_CONTROL_LOOP_V2.json",
        "da8803584bc1e2bea672bcd1833e526ec489ac81",
    ),
    "truth_repair": (
        "canonical/governance/TERMINAL_FIRST_PRINCIPLES_THEORY_TOURNAMENT_20261006_V1.json",
        "7102f0d0fef813c209a54246bcf7e221d060572f",
    ),
    "independent_verification": (
        "canonical/verification/TERMINAL_THEOREM_MINIMALITY_FALSIFIER_INDEPENDENT_VERIFICATION_20261006_V1.json",
        "38486f2002c0d025fac73c36c43f86cdd2fee24d",
    ),
    "stochastic_truth_repair": (
        "canonical/governance/OUTCOME_FRONTIER_STOCHASTIC_RELIABILITY_COUNTERMODEL_V1.json",
        "14b4fad10884538ad2b5d73a9c1a6787aae965d5",
    ),
    "stochastic_independent_verification": (
        "canonical/verification/OUTCOME_FRONTIER_STOCHASTIC_COUNTERMODEL_INDEPENDENT_VERIFICATION_20261006_V1.json",
        "3b4c5e7bc9d1fc2b7f7a3aca22c5de6ff7ea65de",
    ),
}
REQUIRED_REFINEMENTS = [
    "TERMINAL_OUTCOME_SEMANTICS_MUST_BE_DISTRIBUTION_OR_RELIABILITY_BEARING_WHERE_STOCHASTIC_OUTCOMES_ARE_TERMINAL_RELEVANT",
    "POINT_SUPPORT_OR_BEST_REACHABLE_OUTCOME_IS_INSUFFICIENT",
    "ADMISSIBLE_TERMINAL_EVALUATOR_SET_OR_PARTIAL_ORDER_MUST_DECIDE_RELEVANT_TRADEOFFS",
    "PARETO_NONSCALAR_TRADEOFFS_MUST_NOT_COLLAPSE_PROBABILITY_MASS_TO_SUPPORT",
]

REQUIRED_LEMMAS = [
    "UTILITY_AND_EQUAL_OR_BETTER_ORDERING_WELL_FORMED",
    "TARGET_UTILITY_QUOTIENT_COMPLETENESS",
    "TARGET_CLASS_WEAK_DOMINANCE",
    "CONDITION_AND_COMPOSITION_CLOSURE",
    "RESOURCE_SAFETY_AND_AUTHORITY_NONREGRESSION",
    "DONOR_INDEPENDENT_BRAIN_OWNERSHIP",
]


class V3RepairError(ValueError):
    pass


def _binding(raw: Any, name: str) -> dict[str, str]:
    if not isinstance(raw, Mapping):
        raise V3RepairError(name + "_INVALID")
    path = raw.get("path")
    blob = raw.get("git_blob_sha")
    expected_path, expected_blob = EXPECTED[name]
    if path != expected_path or blob != expected_blob:
        raise V3RepairError(name + "_BINDING_MISMATCH")
    return {"path": str(path), "git_blob_sha": str(blob)}


def _fingerprint(inputs: list[Mapping[str, Any]]) -> str:
    rows = sorted(f"{x['path']}:{x['git_blob_sha']}" for x in inputs)
    return sha256("\n".join(rows).encode("utf-8")).hexdigest()


def apply_repair(
    state: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        raise V3RepairError("STATE_INVALID")
    if not isinstance(overlay, Mapping) or overlay.get("schema") != SCHEMA:
        raise V3RepairError("OVERLAY_SCHEMA_INVALID")

    source = _binding(overlay.get("source_control"), "source_control")
    truth = _binding(overlay.get("truth_repair"), "truth_repair")
    verify = _binding(
        overlay.get("independent_verification"), "independent_verification"
    )
    stochastic = _binding(
        overlay.get("stochastic_truth_repair"), "stochastic_truth_repair"
    )
    stochastic_verify = _binding(
        overlay.get("stochastic_independent_verification"),
        "stochastic_independent_verification",
    )

    falsified = overlay.get("falsified_claim")
    successor = overlay.get("successor_claim")
    if not isinstance(falsified, Mapping):
        raise V3RepairError("FALSIFIED_CLAIM_INVALID")
    if not isinstance(successor, Mapping):
        raise V3RepairError("SUCCESSOR_CLAIM_INVALID")

    if falsified.get("id") != OLD:
        raise V3RepairError("FALSIFIED_CLAIM_ID_MISMATCH")
    if falsified.get("replacement_status") != "FALSIFIED":
        raise V3RepairError("FALSIFIED_STATUS_MISMATCH")
    fr = falsified.get("falsification_receipt")
    if not isinstance(fr, Mapping):
        raise V3RepairError("FALSIFICATION_RECEIPT_INVALID")
    if (
        fr.get("path") != verify["path"]
        or fr.get("git_blob_sha") != verify["git_blob_sha"]
    ):
        raise V3RepairError("FALSIFICATION_RECEIPT_MISMATCH")

    if successor.get("id") != NEW:
        raise V3RepairError("SUCCESSOR_ID_MISMATCH")
    if successor.get("successor_of") != OLD:
        raise V3RepairError("SUCCESSOR_PREDECESSOR_MISMATCH")
    if successor.get("lane") != "UNIVERSE_AUTHORITY":
        raise V3RepairError("SUCCESSOR_LANE_MISMATCH")
    if successor.get("status") != "ACTIVE":
        raise V3RepairError("SUCCESSOR_STATUS_MISMATCH")
    if successor.get("required_lemmas") != REQUIRED_LEMMAS:
        raise V3RepairError("SUCCESSOR_LEMMA_SET_OR_ORDER_MISMATCH")
    if successor.get("first_unresolved_lemma") != LEMMA:
        raise V3RepairError("SUCCESSOR_FIRST_LEMMA_MISMATCH")
    if successor.get("first_lemma_refinements") != REQUIRED_REFINEMENTS:
        raise V3RepairError("SUCCESSOR_FIRST_LEMMA_REFINEMENTS_MISMATCH")

    out = copy.deepcopy(dict(state))
    claims = out.get("claims")
    if not isinstance(claims, list):
        raise V3RepairError("STATE_CLAIMS_INVALID")

    ids = [c.get("id") for c in claims if isinstance(c, Mapping)]
    if ids.count(OLD) != 1:
        raise V3RepairError("OLD_CLAIM_NOT_EXACTLY_ONCE")
    if NEW in ids:
        raise V3RepairError("SUCCESSOR_ALREADY_PRESENT")

    for claim in claims:
        if isinstance(claim, dict) and claim.get("id") == OLD:
            if claim.get("status") != "ACTIVE":
                raise V3RepairError("OLD_CLAIM_NOT_ACTIVE_ON_BOUND_V2_STATE")
            claim["status"] = "FALSIFIED"
            claim["falsification_receipt"] = dict(fr)

    claims.append(copy.deepcopy(dict(successor)))

    inputs = out.get("authoritative_inputs")
    if not isinstance(inputs, list):
        raise V3RepairError("AUTHORITATIVE_INPUTS_INVALID")
    bound_rows = [dict(x) for x in inputs]
    existing_paths = {x.get("path") for x in bound_rows}
    for binding in (truth, verify, stochastic, stochastic_verify):
        if binding["path"] in existing_paths:
            raise V3RepairError("REPAIR_SOURCE_ALREADY_PRESENT:" + binding["path"])
        bound_rows.append(binding)
        existing_paths.add(binding["path"])
    out["authoritative_inputs"] = bound_rows
    out["frontier_fingerprint"] = _fingerprint(bound_rows)

    return out


def compile_control_loop_v3(
    state: Mapping[str, Any],
    overlay: Mapping[str, Any],
) -> dict[str, Any]:
    repaired = apply_repair(state, overlay)
    result = compile_control_loop(repaired)

    if OLD not in result.dead_claim_ids:
        raise V3RepairError("OLD_CLAIM_NOT_DEAD_AFTER_REPAIR")
    if OLD in result.unrepaired_dead_claim_ids:
        raise V3RepairError("OLD_CLAIM_NOT_REPAIRED_BY_SUCCESSOR")
    if not result.ordered_claim_ids or result.ordered_claim_ids[0] != NEW:
        raise V3RepairError("UTILITY_QUOTIENT_SUCCESSOR_NOT_FIRST")

    return {
        "status": "PASS__UTILITY_QUOTIENT_SUCCESSOR_IS_FIRST_UNIVERSE_AUTHORITY_CLAIM__ZERO_CREDIT",
        "terminal_ready": result.terminal_ready,
        "universe_complete": result.universe_complete,
        "ordered_claim_ids": list(result.ordered_claim_ids),
        "dead_claim_ids": list(result.dead_claim_ids),
        "unrepaired_dead_claim_ids": list(result.unrepaired_dead_claim_ids),
        "blocked_claim_ids": list(result.blocked_claim_ids),
        "frontier_fingerprint": result.frontier_fingerprint,
        "first_universe_claim": NEW,
        "first_unresolved_lemma": LEMMA,
        "first_subproblem": "DISTRIBUTION_AWARE_EQUAL_OR_BETTER_ORDERING",
        "proof_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }
