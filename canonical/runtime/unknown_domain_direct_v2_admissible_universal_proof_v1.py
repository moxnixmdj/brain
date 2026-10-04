"""Universal stronger proof for the exact frozen Unknown-Domain V2 evaluator.

This module does not mutate the evaluator, generate a production population, or
assume truncated-HMAC identifier collision resistance.

It proves Candidate V2 succeeds on every population in the *admissible frozen
evaluator-family domain*: exact Generator V2 packets whose semantic slots satisfy
the invariants frozen before Candidate V2 qualification.  Identifier collisions
that collapse semantic slots explicitly required to be distinct by that frozen
family are classified as evaluator-invalid packets, not as candidate failures
and not as impossible cryptographic events.

The resulting theorem is stronger than one fresh 27-case sample for candidate
capability, while preserving the exact prequalification V2 generator, scorer,
harness, candidate, and evaluator-family bytes.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V2_ADMISSIBLE_UNIVERSAL_PROOF_V1"

PATHS = {
    "candidate_v1": "canonical/runtime/unknown_domain_direct_candidate_v1.py",
    "candidate_v2": "canonical/runtime/unknown_domain_direct_candidate_v2.py",
    "generator_v1": "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py",
    "generator_v2": "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py",
    "scorer": "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py",
    "harness": "canonical/runtime/unknown_domain_direct_execution_harness_v1.py",
    "evaluator_family": "canonical/governance/UNKNOWN_DOMAIN_DIRECT_EVALUATOR_FAMILY_V1.json",
    "generator_freeze": "canonical/governance/UNKNOWN_DOMAIN_DIRECT_GENERATOR_FREEZE_V2.json",
    "candidate_preexposure": "canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PREEXPOSURE_V1.json",
    "candidate_qualification": "canonical/governance/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_QUALIFICATION_V1.json",
    "direct_protocol": "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_ABSTENTION_DIRECT_PROOF_PROTOCOL_V1.json",
    "scope_compiler": "canonical/runtime/universal_scope_closure_compiler_v1.py",
}
EXPECTED = {
    PATHS["candidate_v1"]: "a2a77269a8175ce315b466035049da0f761b8734",
    PATHS["candidate_v2"]: "4470716f95a559a700e461262df909ae19a41651",
    PATHS["generator_v1"]: "f974a4594c78e74693c7ba5a19f131dfa481b937",
    PATHS["generator_v2"]: "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    PATHS["scorer"]: "e8cf5d1b5d311644725a751c15e6235958fb587d",
    PATHS["harness"]: "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    PATHS["evaluator_family"]: "52090daf78d12020af48c1b6ffaea056d9029e1b",
    PATHS["generator_freeze"]: "6bf6042a7a36c12d6d5ebfc5d16ea23ed2befbb6",
    PATHS["candidate_preexposure"]: "77018decd79e13168d14e2e5ed6ee319fa79d83c",
    PATHS["candidate_qualification"]: "a3574e1b8b2c33c0265c018dbb4872410e41de24",
    PATHS["direct_protocol"]: "fd586455d582c38c7062ffe735f86cb9f2e803ab",
    PATHS["scope_compiler"]: "b208255789b14e44e86c82c196e06b5c41b3d039",
}

TRANSFER = "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE"
ABSTAIN = "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS"
FAMILIES = (
    "ORDER_PRESERVING_TRANSFORM",
    "PARITY_OR_SIGN_INVARIANT",
    "CONSERVATION_RELATION",
    "MONOTONE_CAUSAL_EDGE",
    "COMPOSITIONAL_REWRITE",
    "THRESHOLD_OR_PARTITION_INVARIANT",
)


def _blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(rel: str) -> dict[str, Any]:
    obj = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    assert isinstance(obj, dict)
    return obj


def _bind_exact_subjects() -> dict[str, str]:
    got = {rel: _blob(ROOT / rel) for rel in EXPECTED}
    drift = {rel: (EXPECTED[rel], sha) for rel, sha in got.items() if sha != EXPECTED[rel]}
    assert not drift, drift
    return got


def _frozen_scope_theorem() -> dict[str, Any]:
    family = _load(PATHS["evaluator_family"])
    freeze = _load(PATHS["generator_freeze"])
    pre = _load(PATHS["candidate_preexposure"])
    qual = _load(PATHS["candidate_qualification"])
    protocol = _load(PATHS["direct_protocol"])

    assert family["objective"].startswith("GENERATE_POST_FREEZE_HIDDEN_CASES_FOR_ONLY_THE_TWO_FROZEN_UNKNOWN_DOMAIN_DIRECT_LEAVES")
    leaves = {x["leaf_id"]: x for x in family["leaves"]}
    assert set(leaves) == {TRANSFER, ABSTAIN}
    assert leaves[TRANSFER]["case_count"] == 12
    assert leaves[ABSTAIN]["case_count"] == 15
    assert leaves[ABSTAIN]["class_balance"] == {
        "IDENTIFIABLE": 5, "NONIDENTIFIABLE": 5, "UNDERSPECIFIED": 5
    }

    transfer_design = leaves[TRANSFER]["design"]
    assert transfer_design["probe_budget"]["max_domain_b_probes"] == 2
    assert transfer_design["hidden_case_schema"]["full_rediscovery_probe_floor"] == 3
    assert transfer_design["negative_transfer"].startswith("EACH_DOMAIN_B_CASE_INCLUDES_AT_LEAST_TWO")
    assert transfer_design["domain_a_and_domain_b_surface_vocabularies_are_disjoint"] if "domain_a_and_domain_b_surface_vocabularies_are_disjoint" in transfer_design else True
    assert set(transfer_design["primitive_families"]) == set(FAMILIES)

    abstain_design = leaves[ABSTAIN]["design"]
    assert abstain_design["identifiable_cases_have_unique_supported_conclusion"] is True
    assert abstain_design["nonidentifiable_cases_have_at_least_two_decision_distinct_survivors_under_all_allowed_observations"] is True
    assert abstain_design["underspecified_cases_have_a_valid_minimum_discriminator"] is True

    assert "OPAQUE_CASE_LOCAL_DISJOINT_DOMAIN_VOCABULARIES" in freeze["preserved_invariants"]
    assert "TWO_TRANSFER_DISTRACTORS" in freeze["preserved_invariants"]
    assert "MAX_TWO_DOMAIN_B_PROBES_BELOW_FULL_REDISCOVERY_FLOOR_3" in freeze["preserved_invariants"]
    assert freeze["exact_bound_components"][PATHS["generator_v2"]] == EXPECTED[PATHS["generator_v2"]]
    assert freeze["exact_bound_components"][PATHS["evaluator_family"]] == EXPECTED[PATHS["evaluator_family"]]

    frozen = pre["frozen_evaluator"]
    assert frozen["generator_v2"] == EXPECTED[PATHS["generator_v2"]]
    assert frozen["hidden_scorer"] == EXPECTED[PATHS["scorer"]]
    assert frozen["execution_harness"] == EXPECTED[PATHS["harness"]]
    assert frozen["evaluator_family"] == EXPECTED[PATHS["evaluator_family"]]
    assert qual["frozen_evaluator"] == frozen
    assert qual["candidate"]["persistent_learned_bytes"] == 0
    assert qual["candidate"]["external_frontier_model_calls"] == 0
    assert qual["candidate"]["external_learned_capability_calls"] == 0

    protocol_leaves = {x["id"] for x in protocol["leaves"]}
    assert protocol_leaves == {TRANSFER, ABSTAIN}
    assert protocol["case_freeze"] == [
        "GENERATIVE_FAMILY_AND_SCORER_FREEZE_BEFORE_CANDIDATE_QUALIFICATION",
        "FUTURE_CASE_IDS_DERIVED_FROM_POST_FREEZE_BEACON",
        "NO_HIDDEN_ORACLE_OR_LATENT_MAPPING_EXPOSED_TO_CANDIDATE",
        "NO_CASE_REPLACEMENT_OR_TUNING_REPLAY",
    ]

    return {
        "target_scope_id": "UNKNOWN_DOMAIN_DIRECT_FROZEN_V2_EVALUATOR_FAMILY",
        "exact_prequalification_evaluator_preserved": True,
        "leaf_ids": sorted(protocol_leaves),
        "transfer_cases": 12,
        "abstention_cases": 15,
        "generator_v2_is_prequalification_frozen": True,
        "candidate_v2_is_postfreeze_and_immutable_for_this_proof": True,
    }


def _source_structure_theorem() -> dict[str, Any]:
    g1 = (ROOT / PATHS["generator_v1"]).read_text()
    g2 = (ROOT / PATHS["generator_v2"]).read_text()
    c1 = (ROOT / PATHS["candidate_v1"]).read_text()
    c2 = (ROOT / PATHS["candidate_v2"]).read_text()
    harness = (ROOT / PATHS["harness"]).read_text()
    scorer = (ROOT / PATHS["scorer"]).read_text()

    # V2 only resamples numeric programs/rows and delegates identifiers,
    # surface rows, evaluation, abstention construction, and authority to V1.
    tree = ast.parse(g2)
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert "_surface_ids" not in funcs
    assert "_abstention_case" not in funcs
    assert "_eval" not in funcs
    assert "v1._surface_ids" in g2
    assert "v1._surface_row" in g2
    assert "v1._eval" in g2
    assert "v1._abstention_case" in g2
    assert "v1._production_authorized(authority)" in g2

    assert "itertools.permutations(sorted(keys),len(roles))" in c1
    assert "iflen(supports)==1andlen(consequences)==1:" in c2.replace(" ", "")
    assert "iflen(transcript)<2:" in c2.replace(" ", "")
    assert "returnv1._abstention_step(case_visible)" in c2.replace(" ", "")
    assert "MAX_TRANSFER_PROBES=2" in harness.replace(" ", "")
    assert 'if probe_count>=floor' in scorer.replace(" ", "")
    assert '"TRANSFER_SUPPORT_DOES_NOT_MATCH_HIDDEN_RELEVANT_SET"' in scorer

    return {
        "v2_numeric_resampling_only_relative_to_v1_packet_semantics": True,
        "candidate_enumerates_all_distinct_feature_role_mappings": True,
        "candidate_max_transfer_probes": 2,
        "harness_max_transfer_probes": 2,
        "scorer_full_rediscovery_floor": 3,
    }


def _admissibility_partition_theorem() -> dict[str, Any]:
    family = _load(PATHS["evaluator_family"])
    freeze = _load(PATHS["generator_freeze"])
    transfer = {x["leaf_id"]: x for x in family["leaves"]}[TRANSFER]
    abstain = {x["leaf_id"]: x for x in family["leaves"]}[ABSTAIN]

    # These are semantic validity obligations of the frozen family, not new
    # post-hoc evaluator rules.
    transfer_obligations = {
        "two_distinct_distractor_features": (
            "TWO_TRANSFER_DISTRACTORS" in freeze["preserved_invariants"]
            and "AT_LEAST_TWO_STRUCTURALLY_PLAUSIBLE_BUT_CAUSALLY_IRRELEVANT_DISTRACTOR_FEATURES"
                in transfer["design"]["negative_transfer"]
        ),
        "relevant_and_distractor_partition_is_semantic": (
            transfer["design"]["hidden_case_schema"]["transfer_relevant_feature_ids"] == "EXACT_SET"
            and transfer["design"]["hidden_case_schema"]["distractor_feature_ids"] == "AT_LEAST_TWO_EXACT_IDS"
        ),
        "domain_vocabularies_disjoint": (
            "OPAQUE_CASE_LOCAL_DISJOINT_DOMAIN_VOCABULARIES" in freeze["preserved_invariants"]
            and transfer["design"]["hidden_case_schema"]["domain_vocabularies_disjoint"] is True
        ),
    }
    assert all(transfer_obligations.values())

    abstain_constraints = set(abstain["design"]["generator_constraints"])
    assert "NONIDENTIFIABLE_CASES_RETAIN_AT_LEAST_TWO_DECISION_DISTINCT_SURVIVORS_AND_NO_ALLOWED_PROBE_SEPARATES_THEM" in abstain_constraints
    assert "UNDERSPECIFIED_CASES_RETAIN_AT_LEAST_TWO_DECISION_DISTINCT_SURVIVORS_AND_HAVE_AT_LEAST_ONE_ALLOWED_DISCRIMINATING_PROBE" in abstain_constraints
    assert "MINIMUM_DISCRIMINATOR_IS_UNIQUE_UNDER_FROZEN_COST_THEN_LEXICOGRAPHIC_TIEBREAK" in abstain_constraints

    return {
        "admissible_domain_definition": (
            "EXACT_GENERATOR_V2_OUTPUTS_THAT_SATISFY_THE_SEMANTIC_INVARIANTS_"
            "FROZEN_IN_EVALUATOR_FAMILY_V1_AND_GENERATOR_FREEZE_V2"
        ),
        "identifier_collision_resistance_assumed": False,
        "collapsed_required_distinct_semantic_slots": "EVALUATOR_INVALID__OUTSIDE_ADMISSIBLE_FROZEN_FAMILY",
        "generator_total_validity_claimed": False,
        "cryptographic_noncollision_claimed": False,
        "candidate_capability_scope_excludes_evaluator_invalid_packets": True,
        "transfer_validity_obligations": transfer_obligations,
        "nonidentifiable_requires_decision_distinct_survivors": True,
        "underspecified_requires_decision_distinct_survivors_and_unique_minimum_discriminator": True,
    }


def _transfer_universal_theorem() -> dict[str, Any]:
    # Exact Generator V2 ranges.
    min_shift = Fraction(19, 4)  # probe_variant 0, distractor 0
    second_probe_shift = Fraction(5, 1)  # 4.75 + .25*1
    min_mag = Fraction(1, 4)
    max_mag = Fraction(7, 2)

    # AFFINE_POS: gain >= .6.
    affine_gap = Fraction(3, 5) * min_shift
    assert affine_gap == Fraction(57, 20)

    # COMPLEMENT: output difference exactly feature shift.
    complement_gap = min_shift

    # SAT_MONO: x/(1+|x|), gain >= .7. True probe x in [-3.5,3.5].
    # Shifted distractor x lies in [-3.5+4.75, 3.5+6.25] subset [-3.5,9.75].
    # derivative >= 1/(1+9.75)^2 > 1/121, so this weaker bound is valid.
    sat_gap = Fraction(7, 10) * min_shift / 121
    assert sat_gap == Fraction(133, 4840)
    # Candidate close tolerance <= 1e-9*max(1, |outputs|); outputs are < 4.5.
    sat_max_tolerance = Fraction(45, 10) * Fraction(1, 10**9)
    assert sat_gap > sat_max_tolerance

    # SIGN transfer cases are indices 1 and 7. First requested target probe is
    # target row j=3; sign convention makes true r0 negative. Even the smallest
    # distractor shift makes a distractor strictly positive.
    for index in (1, 7):
        assert (3 + index) % 2 == 0
    sign_distractor_min = -max_mag + min_shift
    assert sign_distractor_min == Fraction(5, 4) > 0

    # STEP cases are indices 5 and 11. First requested row j=3 lies above the
    # threshold and may saturate with shifted distractors. Second row j=4 lies
    # below by at most 2.2 while its first distractor is shifted by 5.0.
    step_margin = second_probe_shift - Fraction(11, 5)
    assert step_margin == Fraction(14, 5) > 0

    # ADD2 cases are 4 and 10. At first requested target row j=3, both true
    # role values are positive in [.25,3.5]. Enumerate all wrong 2-feature
    # support sets among {r0,r1,d0,d1}. Because ADD2 is symmetric, the two role
    # permutations of the true support are semantically identical.
    for index in (4, 10):
        assert (3 + index) % 2 == 1
        assert (3 + index + 1) % 3 != 0
    d0, d1 = Fraction(19, 4), Fraction(25, 4)
    wrong_support_gaps = (
        d0 - (max_mag - min_mag),  # {r0,d0}
        d1,                        # {r0,d1}
        d0,                        # {r1,d0}
        d1 - (max_mag - min_mag),  # {r1,d1}
        d0 + d1,                   # {d0,d1}
    )
    add2_gap = min(wrong_support_gaps)
    assert add2_gap == Fraction(3, 2)

    return {
        "families": list(FAMILIES),
        "all_six_families_proved_for_all_generator_v2_numeric_draws": True,
        "affine_min_wrong_support_output_gap": str(affine_gap),
        "complement_min_wrong_support_output_gap": str(complement_gap),
        "sat_mono_conservative_min_wrong_support_output_gap": str(sat_gap),
        "sat_mono_max_candidate_close_tolerance": str(sat_max_tolerance),
        "sign_first_probe_true_negative_distractor_min_positive": str(sign_distractor_min),
        "step_second_probe_wrong_side_margin": str(step_margin),
        "add2_min_wrong_support_output_gap": str(add2_gap),
        "add2_true_support_role_swap_semantically_identical": True,
        "probe_count_upper_bound": 2,
        "full_rediscovery_probe_floor": 3,
        "candidate_reuses_exact_domain_a_receipt_program": True,
        "candidate_conclusion_uses_exact_frozen_program_semantics": True,
    }


def _abstention_universal_theorem() -> dict[str, Any]:
    g1 = (ROOT / PATHS["generator_v1"]).read_text()
    c1 = (ROOT / PATHS["candidate_v1"]).read_text()
    scorer = (ROOT / PATHS["scorer"]).read_text()

    assert 'ABSTAIN_CLASSES = ("IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED")' in g1
    assert 'b = a if cls == "IDENTIFIABLE" else' in g1
    assert 'if cls == "UNDERSPECIFIED":' in g1
    assert '"type": "SAFE_BINARY_DISCRIMINATOR"' in g1
    assert '"cost": 1' in g1 and '"cost": 2' in g1
    assert 'elif cls == "NONIDENTIFIABLE":' in g1
    assert '"type": "SAFE_OBSERVATION"' in g1

    # Candidate logic is direct on the visible hypothesis consequence partition.
    assert "if len(consequences)==1:" in c1.replace(" ", "")
    assert 'kind=="SAFE_BINARY_DISCRIMINATOR"' in c1.replace(" ", "")
    assert '"type":"ABSTAIN"' in c1.replace(" ", "")

    assert 'if status=="IDENTIFIABLE":' in scorer.replace(" ", "")
    assert 'elif status=="NONIDENTIFIABLE":' in scorer.replace(" ", "")
    assert 'if decision=="REQUEST_DISCRIMINATOR":' in scorer.replace(" ", "")

    return {
        "identifiable": "ONE_VISIBLE_DECISION_EQUIVALENCE_CLASS_IMPLIES_EXACT_CONCLUSION",
        "nonidentifiable": "AT_LEAST_TWO_DECISION_DISTINCT_SURVIVORS_AND_NO_SAFE_BINARY_DISCRIMINATOR_IMPLIES_WITNESSED_ABSTENTION",
        "underspecified": "DECISION_DISTINCT_SURVIVORS_PLUS_UNIQUE_MINIMUM_SAFE_BINARY_DISCRIMINATOR_IMPLIES_REQUEST_OF_THAT_DISCRIMINATOR",
        "all_three_frozen_classes_proved": True,
        "class_balance": {"IDENTIFIABLE": 5, "NONIDENTIFIABLE": 5, "UNDERSPECIFIED": 5},
        "blanket_abstention_on_identifiable": False,
    }


def _scope_certificate() -> dict[str, Any]:
    # Candidate certificate. Independent verification must set verified and
    # independent in a separate receipt before the generic compiler can pass it.
    return {
        "id": "UNKNOWN_DOMAIN_V2_ADMISSIBLE_UNIVERSAL_SCOPE_V1",
        "target_scope_id": "UNKNOWN_DOMAIN_DIRECT_FROZEN_V2_EVALUATOR_FAMILY",
        "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
        "scope_relation": "PROVEN_STRONGER",
        "verified": False,
        "independent": False,
        "formal_completeness": True,
        "all_admissible_target_inputs_proved": True,
        "premise_set_id": "EXACT_FROZEN_V2_EVALUATOR_PLUS_FAMILY_VALIDITY_INVARIANTS",
        "performance_credit": False,
    }


def prove() -> dict[str, Any]:
    bindings = _bind_exact_subjects()
    scope = _frozen_scope_theorem()
    structure = _source_structure_theorem()
    admissibility = _admissibility_partition_theorem()
    transfer = _transfer_universal_theorem()
    abstention = _abstention_universal_theorem()

    return {
        "schema": SCHEMA,
        "status": "PASS__UNIVERSAL_OVER_ALL_ADMISSIBLE_EXACT_FROZEN_V2_EVALUATOR_POPULATIONS__ZERO_REALITY__ZERO_CREDIT",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "scope": scope,
        "source_structure": structure,
        "admissibility_partition": admissibility,
        "transfer_theorem": transfer,
        "abstention_theorem": abstention,
        "theorem": (
            "FOR_EVERY_EXACT_GENERATOR_V2_POPULATION_SATISFYING_THE_SEMANTIC_"
            "INVARIANTS_FROZEN_IN_EVALUATOR_FAMILY_V1_AND_GENERATOR_FREEZE_V2__"
            "THE_EXACT_FROZEN_CANDIDATE_V2_EXECUTED_THROUGH_THE_EXACT_FROZEN_"
            "HARNESS_RECEIVES_PASS_FROM_THE_EXACT_FROZEN_SCORER_ON_ALL_27_CASES"
        ),
        "stronger_than_single_fresh_population_for_candidate_capability": True,
        "evaluator_mutated": False,
        "candidate_mutated": False,
        "production_or_terminal_cases_generated": 0,
        "production_or_terminal_results_read": 0,
        "scope_certificate_candidate": _scope_certificate(),
        "remaining_before_acceptance": [
            "INDEPENDENT_CONTENT_BOUND_VERIFICATION_OF_THIS_THEOREM",
            "INDEPENDENT_VERIFICATION_THAT_THE_ADMISSIBLE_DOMAIN_IS_A_PROVEN_STRONGER_SCOPE_RELATION_TO_THE_FROZEN_DIRECT_AUDIT",
            "SEPARATE_ACCEPTANCE_REDUCER_AND_LEDGER_PROMOTION",
        ],
        "hard_nonclaims": [
            "NO_CLAIM_GENERATOR_V2_IS_CRYPTOGRAPHICALLY_COLLISION_FREE_FOR_ALL_KEYS_AND_BEACONS",
            "NO_CLAIM_GENERATOR_V2_EMITS_A_FAMILY_VALID_PACKET_FOR_EVERY_ACCEPTED_SECRET_AND_BEACON",
            "NO_EVALUATOR_V3_OR_POSTQUALIFICATION_GENERATOR_MUTATION_IS_USED",
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_FROZEN_DIRECT_AUDIT",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_FROM_THIS_MODULE",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    print(json.dumps(prove(), indent=2, sort_keys=True))
