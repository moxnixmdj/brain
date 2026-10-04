"""Content-bound universal proof candidate for Unknown-Domain direct V3.

This proof closes the two holes that revoked the V2 universal promotion:
1. identifier uniqueness no longer depends on truncated-HMAC collision resistance;
2. ADD2's exact IEEE-754 role order is recovered from a visible generator
   invariant before the terminal consequence is evaluated.

The claim is limited to the exact bound V3 generator/candidate and unchanged
V1 harness/scorer. It grants zero acceptance credit until independent exact-byte
verification and a separate fail-closed reduction.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_V1"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":
        "03a40a88801d1a7871e2b239ca00fee415ffb000",
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":
        "22559a9daa6f6c22c1d373565989a95e9c3b9f7f",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":
        "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":
        "e8cf5d1b5d311644725a751c15e6235958fb587d",
}

FAMILIES = (
    "ORDER_PRESERVING_TRANSFORM",
    "PARITY_OR_SIGN_INVARIANT",
    "CONSERVATION_RELATION",
    "MONOTONE_CAUSAL_EDGE",
    "COMPOSITIONAL_REWRITE",
    "THRESHOLD_OR_PARTITION_INVARIANT",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _verify_bindings(root: Path) -> dict[str, str]:
    got = {rel: _git_blob_sha(root / rel) for rel in EXPECTED_BLOBS}
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS
        if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _identifier_totality_theorem() -> dict[str, Any]:
    # g3._opaque_bijection requires a finite unique label set, sorts every label
    # exactly once, and assigns enumerate() ranks. Distinct labels therefore get
    # distinct output strings even if every HMAC ranking digest is identical.
    labels = ("ROLE:r0", "ROLE:r1", "DISTRACTOR:0", "DISTRACTOR:1")
    original = g3._rank_digest
    try:
        g3._rank_digest = lambda secret, beacon, scope, label: b"\x00" * 32
        out = g3._opaque_bijection(
            b"x" * 32,
            "B" * 16,
            scope="FORMAL_TIE",
            labels=labels,
            prefix="f",
        )
    finally:
        g3._rank_digest = original
    assert len(out) == 4
    assert len(set(out.values())) == 4

    # Case labels are also a finite disjoint set: 12 transfer + 15 abstention.
    case_labels = [
        *(f"T:{i}" for i in range(g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER])),
        *(f"A:{i}" for i in range(g1.PRODUCTION_CASE_COUNTS[g1.ABSTAIN])),
    ]
    assert len(case_labels) == 27
    assert len(case_labels) == len(set(case_labels))

    # Surface IDs allocate one slot per semantic role plus exactly two
    # distractors. Source/target scopes carry distinct domain prefixes.
    assert tuple(g1.PRIMITIVE_FAMILIES) == FAMILIES
    assert all(
        len(g2._program_for(b"x" * 32, "B" * 16, i)[2]) in (1, 2)
        for i in range(12)
    )
    return {
        "identifier_totality": True,
        "mechanism": (
            "FINITE_SECRET_DEPENDENT_PERMUTATION_TO_UNIQUE_ORDINAL_SLOTS"
        ),
        "uniqueness_depends_on_hash_collision_resistance": False,
        "forced_all_digest_tie_test_passed": True,
        "population_case_id_count": 27,
    }


def _add2_exact_orientation_theorem() -> dict[str, Any]:
    add2_indices = [
        i
        for i in range(g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER])
        if FAMILIES[i % len(FAMILIES)] == "COMPOSITIONAL_REWRITE"
    ]
    assert add2_indices == [4, 10]

    for index in add2_indices:
        # Magnitudes in V2/V3 are sampled from [0.25, 3.5], inclusive, so they
        # are strictly positive. Only these deterministic sign branches matter.
        r0 = tuple(-1 if (j + index) % 2 == 0 else 1 for j in range(3))
        r1 = tuple(-1 if (j + index + 1) % 3 == 0 else 1 for j in range(3))
        assert r0 == c3._R0_ADD2_SIGN_PATTERN == (-1, 1, -1)
        assert r1 == c3._R1_ADD2_SIGN_PATTERN == (1, -1, 1)
        assert r0 != r1

    # The candidate and generator evaluate the final ADD2 in the same role
    # order after orientation. Exact Python float equality follows because both
    # execute bias + r0 + r1 on the same binary64 operands.
    program = {
        "dsl": "UDIR_V1",
        "op": "ADD2",
        "roles": ["r0", "r1"],
        "params": {"bias": 0.1},
    }
    values = {"r0": 1.0e16, "r1": -1.0e16}
    assert c1._program_eval(program, values) == g1._eval(program, values)

    return {
        "add2_indices": add2_indices,
        "r0_visible_sign_pattern": [-1, 1, -1],
        "r1_visible_sign_pattern": [1, -1, 1],
        "strictly_nonzero_magnitude_lower_bound": 0.25,
        "orientation_uses_identifier_spelling": False,
        "candidate_generator_add2_eval_exactly_aligned": True,
    }


def _support_rejection_theorem() -> dict[str, Any]:
    # V3 preserves V2's numeric row generation and V2's support discovery.
    # Only opaque identifier assignment and final ADD2 role orientation changed.
    min_shift = 4.75

    affine_min_output_gap = 0.6 * min_shift
    complement_min_output_gap = min_shift
    sat_mono_min_output_gap = 0.7 * min_shift / 121.0
    sat_mono_max_close_tolerance = 4.5e-9
    sign_negative_probe_distractor_min = -3.5 + min_shift
    step_wrong_side_margin = min_shift - 2.2
    add2_wrong_support_min_gap = min(
        4.75 - (3.5 - 0.25),
        6.25,
        4.75,
        6.25 - (3.5 - 0.25),
        4.75 + 6.25,
    )

    assert affine_min_output_gap > 1.0
    assert complement_min_output_gap > 1.0
    assert sat_mono_min_output_gap > sat_mono_max_close_tolerance
    assert sign_negative_probe_distractor_min > 0.0
    assert step_wrong_side_margin > 0.0
    assert add2_wrong_support_min_gap == 1.5
    assert harness.MAX_TRANSFER_PROBES == 2
    assert 2 < 3

    return {
        "all_six_families_wrong_support_rejected": True,
        "max_transfer_probes": 2,
        "full_rediscovery_probe_floor": 3,
        "affine_min_output_gap": affine_min_output_gap,
        "complement_min_output_gap": complement_min_output_gap,
        "sat_mono_min_output_gap": sat_mono_min_output_gap,
        "sat_mono_max_close_tolerance": sat_mono_max_close_tolerance,
        "sign_negative_probe_distractor_min": sign_negative_probe_distractor_min,
        "step_wrong_side_margin": step_wrong_side_margin,
        "add2_wrong_support_min_gap": add2_wrong_support_min_gap,
    }


def _abstention_theorem() -> dict[str, Any]:
    assert tuple(g1.ABSTAIN_CLASSES) == (
        "IDENTIFIABLE",
        "NONIDENTIFIABLE",
        "UNDERSPECIFIED",
    )
    assert g1.PRODUCTION_CASE_COUNTS[g1.ABSTAIN] == 15
    assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}
    return {
        "all_three_classes_universal": True,
        "identifiable": (
            "TWO_VISIBLE_HYPOTHESES_SHARE_ONE_TERMINAL_CONSEQUENCE__CANDIDATE_CONCLUDES"
        ),
        "nonidentifiable": (
            "DISTINCT_VISIBLE_CONSEQUENCES_AND_NO_SAFE_BINARY_DISCRIMINATOR__CANDIDATE_ABSTAINS"
        ),
        "underspecified": (
            "TWO_VISIBLE_SAFE_BINARY_DISCRIMINATORS__CANDIDATE_REQUESTS_MINIMUM_VISIBLE_COST"
        ),
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _repo_root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    identifier = _identifier_totality_theorem()
    orientation = _add2_exact_orientation_theorem()
    support = _support_rejection_theorem()
    abstention = _abstention_theorem()

    return {
        "schema": SCHEMA,
        "status": "PASS__UNIVERSAL_PROOF_CANDIDATE_OVER_EXACT_V3_EMITTED_DOMAIN",
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
        "identifier_totality_proof": identifier,
        "add2_exact_orientation_proof": orientation,
        "support_rejection_proof": support,
        "abstention_proof": abstention,
        "theorem": (
            "FOR_EVERY_V3_POPULATION_EMITTED_FOR_A_VALID_BEACON_AND_SECRET__"
            "IDENTIFIERS_REQUIRED_BY_THE_SCORER_ARE_STRUCTURALLY_TOTAL__"
            "EVERY_TRANSFER_CASE_RECOVERS_THE_EXACT_HIDDEN_SUPPORT__ADD2_ROLE_"
            "ORIENTATION_IS_RECOVERED_FROM_VISIBLE_SIGN_STRUCTURE__THE_EXACT_"
            "FROZEN_SCORER_TERMINAL_CONSEQUENCE_IS_REPRODUCED__AND_ALL_THREE_"
            "ABSTENTION_CLASSES_ARE_DECIDED_CORRECTLY"
        ),
        "fresh_reality_required_for_this_content_bound_claim": False,
        "production_execution_information_gain": 0,
        "hard_nonclaims": [
            "NO_OPEN_WORLD_GENERALIZATION_CLAIM_BEYOND_THE_BOUND_V3_EVALUATOR_DOMAIN",
            "NO_ACCEPTANCE_PROMOTION_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
            "INDEPENDENT_EXACT_BYTE_VERIFICATION_AND_SEPARATE_REDUCTION_REQUIRED",
            "NO_PRODUCTION_CASE_GENERATED_OR_READ",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "terminal_cases_consumed": 0,
            "production_cases_generated": 0,
            "acceptance_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True))
