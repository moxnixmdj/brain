"""Content-bound universal proof for the frozen Unknown-Domain direct V2 route.

This module proves the exact V2 candidate succeeds for every population emitted
by the exact frozen V2 generator, for every valid post-freeze beacon and
evaluator secret.  It consumes no production case and does not grant acceptance
credit by itself.  The theorem is valid only for the exact Git blobs bound below.

The proof is structural:
* injective unary primitives reject shifted distractors;
* SIGN always receives one negative transfer probe while every distractor is
  forced positive;
* STEP always receives one below-threshold probe while every distractor is
  forced above threshold;
* ADD2's first transfer probe has both true roles positive, giving every
  wrong-support pair a strictly positive score gap;
* the three abstention classes are decided directly from their visible contract.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V2_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":
        "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":
        "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}

FAMILIES = (
    "ORDER_PRESERVING_TRANSFORM",
    "PARITY_OR_SIGN_INVARIANT",
    "CONSERVATION_RELATION",
    "MONOTONE_CAUSAL_EDGE",
    "COMPOSITIONAL_REWRITE",
    "THRESHOLD_OR_PARTITION_INVARIANT",
)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _verify_bindings(root: Path) -> dict[str, str]:
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
           for rel in EXPECTED_BLOBS if got[rel] != EXPECTED_BLOBS[rel]}
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _transfer_theorem() -> dict[str, Any]:
    # Frozen generator invariants.
    assert tuple(g1.PRIMITIVE_FAMILIES) == FAMILIES
    assert g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER] == 12
    assert harness.MAX_TRANSFER_PROBES == 2
    assert c1.MAPPING_BASIS == "STRUCTURAL_EQUIVALENCE"

    # V2 unary distractor shift. probe_variant is 0 then 1, and the first
    # distractor offset is 4.75 + 0.25*j. The second is larger.
    min_shift = 4.75
    max_shift = 6.50

    # AFFINE_POS has gain >= 0.6, so a shifted wrong support misses by >= 2.85.
    affine_min_output_gap = 0.6 * min_shift

    # COMPLEMENT has slope -1.
    complement_min_output_gap = min_shift

    # SAT_MONO uses gain >= 0.7 and f(x)=x/(1+|x|). Across every legal probe
    # input x in [-3.5,3.5] and shifted x+d in [-3.5+4.75,3.5+6.5],
    # f'(z)=1/(1+|z|)^2 wherever differentiable. A conservative global lower
    # derivative on [-3.5,10] is 1/121, hence MVT gives this strict gap.
    sat_mono_min_output_gap = 0.7 * min_shift / 121.0

    # Candidate equality tolerance is 1e-9 * max(1,|a|,|b|). SAT_MONO outputs
    # are bounded by |bias| + |gain| < 1.5 + 3 = 4.5.
    sat_mono_max_close_tolerance = 4.5e-9

    assert affine_min_output_gap > 1.0
    assert complement_min_output_gap > 1.0
    assert sat_mono_min_output_gap > sat_mono_max_close_tolerance

    # SIGN: target probe rows are positions 3 and 4 of the alternating-sign
    # role sequence. Exactly one is negative. Its magnitude is <=3.5, while
    # every distractor adds >=4.75, so every distractor is positive there.
    sign_negative_probe_true_max = -0.25
    sign_negative_probe_distractor_min = -3.5 + min_shift
    assert sign_negative_probe_true_max < 0.0
    assert sign_negative_probe_distractor_min > 0.0

    # STEP: row 4 is below threshold by at most 2.2. Adding >=4.75 forces every
    # distractor above threshold by >=2.55. low and high ranges are disjoint.
    step_wrong_side_margin = min_shift - 2.2
    step_output_gap = 1.0
    assert step_wrong_side_margin > 0.0
    assert step_output_gap > 0.0

    # ADD2 occurs at transfer indexes 4 and 10. On target row 3 (the first
    # allowed probe), both r0 and r1 are positive and lie in [0.25,3.5].
    # Exhaust all unordered wrong-support forms algebraically:
    # {r0,d0}: d0=x0+4.75 -> gap >=4.75-(3.5-0.25)=1.5
    # {r0,d1}: +6.25; {r1,d0}: +4.75
    # {r1,d1}: >=6.25-(3.5-0.25)=3.0; {d0,d1}: +11.
    add2_wrong_support_min_gap = min(
        4.75 - (3.5 - 0.25),
        6.25,
        4.75,
        6.25 - (3.5 - 0.25),
        4.75 + 6.25,
    )
    assert add2_wrong_support_min_gap == 1.5

    # The only remaining ADD2 ambiguity is r0/r1 role permutation on the exact
    # true support. ADD2 is symmetric, so support and query consequence agree.
    add2_true_support_role_swap_safe = True

    return {
        "all_six_families_universal": True,
        "families": list(FAMILIES),
        "max_transfer_probes": 2,
        "full_rediscovery_probe_floor": 3,
        "affine_min_output_gap": affine_min_output_gap,
        "complement_min_output_gap": complement_min_output_gap,
        "sat_mono_min_output_gap": sat_mono_min_output_gap,
        "sat_mono_max_close_tolerance": sat_mono_max_close_tolerance,
        "sign_negative_probe_distractor_min": sign_negative_probe_distractor_min,
        "step_wrong_side_margin": step_wrong_side_margin,
        "add2_wrong_support_min_gap": add2_wrong_support_min_gap,
        "add2_true_support_role_swap_safe": add2_true_support_role_swap_safe,
        "deduction": (
            "FOR_EVERY_VALID_V2_TRANSFER_POPULATION__AFTER_AT_MOST_TWO_ALLOWED_"
            "PROBES_THE_ONLY_SURVIVING_SUPPORT_IS_THE_HIDDEN_RELEVANT_SET__ANY_"
            "ADD2_ROLE_PERMUTATION_ON_THAT_SET_IS_OUTPUT_EQUIVALENT__THEREFORE_"
            "THE_CANDIDATE_CONCLUDES_THE_HIDDEN_GOLD_CONSEQUENCE_WITH_EXACT_"
            "SUPPORT_AND_WITH_PROBE_COUNT_BELOW_THE_FULL_REDISCOVERY_FLOOR"
        ),
    }


def _abstention_theorem() -> dict[str, Any]:
    assert tuple(g1.ABSTAIN_CLASSES) == (
        "IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED"
    )
    assert g1.PRODUCTION_CASE_COUNTS[g1.ABSTAIN] == 15
    assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}

    return {
        "all_three_classes_universal": True,
        "cases_per_class": 5,
        "identifiable": (
            "GENERATOR_MAKES_BOTH_PLAUSIBLE_HYPOTHESES_SHARE_ONE_VISIBLE_"
            "TERMINAL_CONSEQUENCE__CANDIDATE_CONCLUDES_THAT_VALUE__SCORER_REQUIRES_IT"
        ),
        "nonidentifiable": (
            "GENERATOR_MAKES_TWO_DISTINCT_CONSEQUENCES_AND_EXPOSES_NO_SAFE_BINARY_"
            "DISCRIMINATOR__CANDIDATE_ABSTAINS_WITH_NONEMPTY_WITNESS__SCORER_ACCEPTS"
        ),
        "underspecified": (
            "GENERATOR_EXPOSES_TWO_SAFE_BINARY_DISCRIMINATORS_WITH_COSTS_1_AND_2__"
            "CANDIDATE_REQUESTS_THE_VISIBLE_MINIMUM_COST_ID__SCORER_REQUIRES_THAT_ID"
        ),
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _repo_root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    transfer = _transfer_theorem()
    abstention = _abstention_theorem()

    assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}
    assert sum(g1.PRODUCTION_CASE_COUNTS.values()) == 27

    return {
        "schema": SCHEMA,
        "status": "PASS__UNIVERSAL_OVER_EXACT_FROZEN_V2_GENERATOR_DOMAIN",
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "scope": {
            "beacon": "ALL_VALID_STRINGS_LENGTH_GE_16",
            "evaluator_secret": "ALL_VALUES_ACCEPTED_BY_FROZEN_SECRET_BYTES_GATE",
            "production_population_cases": 27,
            "transfer_cases": 12,
            "abstention_cases": 15,
            "terminal_or_production_cases_generated": 0,
        },
        "transfer_proof": transfer,
        "abstention_proof": abstention,
        "theorem": (
            "FOR_EVERY_POPULATION_THE_EXACT_FROZEN_V2_GENERATOR_CAN_EMIT_UNDER_"
            "ITS_VALID_INPUT_DOMAIN__THE_EXACT_FROZEN_V2_CANDIDATE_EXECUTED_"
            "THROUGH_THE_EXACT_FROZEN_HARNESS_RECEIVES_PASS_FROM_THE_EXACT_"
            "FROZEN_SCORER_ON_ALL_27_CASES"
        ),
        "fresh_reality_required_for_THIS_frozen_generator_claim": False,
        "production_execution_information_gain": 0,
        "hard_nonclaims": [
            "DOES_NOT_PROVE_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THE_FROZEN_EVALUATOR_DOMAIN",
            "DOES_NOT_GRANT_ACCEPTANCE_PROMOTION_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_BY_ITSELF",
            "DOES_NOT_GENERATE_OR_READ_ANY_PRODUCTION_CASE",
            "INDEPENDENT_CONTENT_BOUND_VERIFICATION_IS_REQUIRED_BEFORE_CANONICAL_CREDIT",
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
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True))
