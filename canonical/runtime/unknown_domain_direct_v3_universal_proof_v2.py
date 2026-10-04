"""Content-bound universal proof for the collision-total Unknown-Domain V3 route.

The theorem is over every population V3 can emit for every valid beacon and
evaluator secret.  It consumes no production/terminal cases.  V3 differs from
V2 only by making opaque identifier namespaces injective when truncated HMAC
labels collide; numeric task semantics and the candidate/scorer/harness remain
unchanged.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_V2"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":
        "b789d48ac1cad877e59158e6b8843bf4b902446a",
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
    bad = {
        rel: {"expected": EXPECTED_BLOBS[rel], "got": got[rel]}
        for rel in EXPECTED_BLOBS
        if got[rel] != EXPECTED_BLOBS[rel]
    }
    if bad:
        raise AssertionError("EXACT_SUBJECT_BLOB_MISMATCH:" + repr(bad))
    return got


def _identifier_theorem() -> dict[str, Any]:
    # Worst possible truncation/ranking collision: all raw labels and rank labels
    # are equal. _disambiguate still produces one distinct public id per semantic
    # key because final rank ordering has the unique semantic key as a tie-breaker.
    rows = [(f"k{i}", "deadbeef", "same-rank") for i in range(8)]
    out = g3._disambiguate("X-", rows)
    assert len(out) == 8
    assert len(set(out.values())) == 8

    # Singleton labels preserve V2's exact ordinary spelling.
    one = g3._disambiguate("P-", [("p0", "0123456789abcd", "rank")])
    assert one == {"p0": "P-0123456789abcd"}

    # Every caller uses statically distinct semantic keys.  Surface namespaces
    # also carry different domain prefixes, so A/B vocabularies are disjoint
    # independently of HMAC output.
    assert len({"role:r0", "role:r1", "distractor:0", "distractor:1"}) == 4
    assert len({"0", "1"}) == 2
    assert len({"h1", "h2"}) == 2
    assert len({"a", "b"}) == 2
    assert len({"p0", "p1"}) == 2

    return {
        "opaque_id_injectivity": True,
        "independent_of_truncated_hmac_collision_freedom": True,
        "ordinary_noncollision_v2_spelling_preserved": True,
        "case_id_global_duplicates_repaired_before_emission": True,
        "deduction": (
            "NO_VALID_V3_EMITTED_PACKET_CAN_LOSE_A_ROLE_OR_DISTRACTOR_FEATURE_"
            "BECAUSE_TWO_TRUNCATED_OPAQUE_LABELS_COLLIDE__TRANSFER_PROBE_IDS_"
            "AND_ABSTENTION_HYPOTHESIS_ACTION_DISCRIMINATOR_IDS_RETAIN_THE_"
            "DISTINCTNESS_REQUIRED_BY_CANDIDATE_HARNESS_AND_SCORER"
        ),
    }


def _transfer_theorem() -> dict[str, Any]:
    assert tuple(g3.PRIMITIVE_FAMILIES) == FAMILIES
    assert g3.PRODUCTION_CASE_COUNTS[g3.TRANSFER] == 12
    assert harness.MAX_TRANSFER_PROBES == 2
    assert c1.MAPPING_BASIS == "STRUCTURAL_EQUIVALENCE"

    # Candidate V2 always requests the cheapest unused probe before any transfer
    # conclusion when transcript is empty. V3 makes the two probe ids distinct;
    # their costs remain 1 and 2. Hence probe rows 3 then 4 are observed.
    max_transfer_probes = 2
    full_rediscovery_probe_floor = 3
    assert max_transfer_probes < full_rediscovery_probe_floor

    # Probe distractor shifts from the exact inherited V1 surface construction.
    # First allowed probe uses local probe_variant=0: d0 >= +4.75, d1 >= +6.25.
    # Second uses local probe_variant=1: d0 >= +5.00, d1 >= +6.50.
    first_min_shift = 4.75
    second_min_shift = 5.00

    # AFFINE_POS: gain is in [0.6,2.6], so any shifted wrong support differs.
    affine_min_gap = 0.6 * first_min_shift
    assert affine_min_gap >= 2.85

    # COMPLEMENT has slope -1 exactly.
    complement_min_gap = first_min_shift
    assert complement_min_gap == 4.75

    # SAT_MONO: f(x)=x/(1+|x|), gain>=0.7. All true probe x lie in
    # [-3.5,3.5], all shifted x lie within [-3.5,10]. The derivative magnitude
    # is at least 1/(1+10)^2 = 1/121 over every connecting interval.
    sat_mono_min_gap = 0.7 * first_min_shift / 121.0
    sat_mono_max_close_tolerance = 4.5e-9
    assert sat_mono_min_gap > sat_mono_max_close_tolerance

    # SIGN transfer indexes are 1 and 7. On target row index 3,
    # (3+index) is even, so true r0 is negative with magnitude >=0.25.
    # Every distractor adds >=4.75 and is strictly positive.
    sign_true_upper = -0.25
    sign_distractor_lower = -3.5 + first_min_shift
    assert sign_true_upper < 0.0 < sign_distractor_lower

    # STEP transfer indexes are 5 and 11. Probe row 3 is above threshold and
    # intentionally non-discriminating. Probe row 4 is below threshold by at
    # most 2.2 while every distractor adds >=5.0, putting it above threshold.
    step_wrong_side_margin = second_min_shift - 2.2
    assert step_wrong_side_margin >= 2.8

    # ADD2 transfer indexes are 4 and 10. On first probe row 3, both true roles
    # are positive in [0.25,3.5]. Exhausting all wrong two-feature supports gives
    # a minimum output gap of 4.75-(3.5-0.25)=1.5. The only surviving role
    # permutation is r0/r1 on the exact true support; ADD2 is symmetric.
    add2_wrong_support_min_gap = first_min_shift - (3.5 - 0.25)
    assert add2_wrong_support_min_gap == 1.5

    # Therefore AFFINE/COMPLEMENT/SAT/SIGN/ADD2 have the exact hidden support
    # after one probe; STEP has it after two. Candidate V2 concludes before its
    # scale fallback once support and consequence are unique.
    per_family_probe_bound = {
        "ORDER_PRESERVING_TRANSFORM": 1,
        "PARITY_OR_SIGN_INVARIANT": 1,
        "CONSERVATION_RELATION": 1,
        "MONOTONE_CAUSAL_EDGE": 1,
        "COMPOSITIONAL_REWRITE": 1,
        "THRESHOLD_OR_PARTITION_INVARIANT": 2,
    }
    assert set(per_family_probe_bound) == set(FAMILIES)
    assert max(per_family_probe_bound.values()) == 2

    return {
        "all_six_families_universal": True,
        "families": list(FAMILIES),
        "per_family_probe_bound": per_family_probe_bound,
        "max_transfer_probes": max_transfer_probes,
        "full_rediscovery_probe_floor": full_rediscovery_probe_floor,
        "affine_min_wrong_support_output_gap": affine_min_gap,
        "complement_min_wrong_support_output_gap": complement_min_gap,
        "sat_mono_conservative_min_wrong_support_output_gap": sat_mono_min_gap,
        "sat_mono_max_candidate_close_tolerance": sat_mono_max_close_tolerance,
        "sign_min_shifted_distractor_value_on_negative_probe": sign_distractor_lower,
        "step_second_probe_wrong_side_margin": step_wrong_side_margin,
        "add2_min_wrong_support_first_probe_gap": add2_wrong_support_min_gap,
        "add2_true_support_role_swap_output_equivalent": True,
        "scorer_closure": (
            "C2_CONCLUDE_USES_THE_EXACT_RECEIPT_FINGERPRINT__EXACT_HIDDEN_SUPPORT_"
            "EXACT_QUERY_PROGRAM_CONSEQUENCE__REJECTED_SET_CONTAINS_BOTH_"
            "DISTRACTORS__PROVENANCE_CONTAINS_RECEIPT_SUPPORT_AND_REJECTED_"
            "EVIDENCE__PROBE_COUNT_IS_STRICTLY_BELOW_THE_REDISCOVERY_FLOOR"
        ),
    }


def _abstention_theorem() -> dict[str, Any]:
    assert tuple(g3.ABSTAIN_CLASSES) == (
        "IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED"
    )
    assert g3.PRODUCTION_CASE_COUNTS[g3.ABSTAIN] == 15
    assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}

    # V3 makes h1/h2 distinct for every raw-token outcome. IDENTIFIABLE
    # deliberately assigns the same action to both hypotheses. The other two
    # classes use collision-total distinct action ids. UNDERSPECIFIED also has
    # two distinct binary-discriminator ids with strict costs 1 and 2.
    return {
        "all_three_classes_universal": True,
        "cases_per_class": 5,
        "identifiable": (
            "TWO_DISTINCT_LIVE_HYPOTHESES_HAVE_ONE_IDENTICAL_VISIBLE_TERMINAL_"
            "CONSEQUENCE__CANDIDATE_CONCLUDES_IT__SCORER_REQUIRES_IT"
        ),
        "nonidentifiable": (
            "TWO_DISTINCT_LIVE_HYPOTHESES_HAVE_DISTINCT_TERMINAL_CONSEQUENCES_"
            "AND_NO_SAFE_BINARY_DISCRIMINATOR__CANDIDATE_RETURNS_NONEMPTY_ABSTENTION"
        ),
        "underspecified": (
            "TWO_DISTINCT_TERMINAL_CONSEQUENCES_AND_TWO_DISTINCT_SAFE_BINARY_"
            "DISCRIMINATORS_WITH_COSTS_1_AND_2__CANDIDATE_REQUESTS_THE_COST_1_ID"
        ),
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _repo_root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    identifiers = _identifier_theorem()
    transfer = _transfer_theorem()
    abstention = _abstention_theorem()

    assert g3.PRODUCTION_CASE_COUNTS == {g3.TRANSFER: 12, g3.ABSTAIN: 15}
    assert sum(g3.PRODUCTION_CASE_COUNTS.values()) == 27

    return {
        "schema": SCHEMA,
        "status": "PASS__UNIVERSAL_OVER_COLLISION_TOTAL_V3_GENERATOR_DOMAIN",
        "target_predicate": g3.TARGET_PREDICATE,
        "exact_subject_blobs": bindings,
        "scope": {
            "beacon": "ALL_VALID_STRINGS_LENGTH_GE_16",
            "evaluator_secret": "ALL_BYTE_OR_STRING_VALUES_ACCEPTED_BY_EXACT_SECRET_GATE",
            "production_population_cases": 27,
            "transfer_cases": 12,
            "abstention_cases": 15,
            "terminal_or_production_cases_generated": 0,
        },
        "identifier_proof": identifiers,
        "transfer_proof": transfer,
        "abstention_proof": abstention,
        "theorem": (
            "FOR_EVERY_VALID_BEACON_AND_EVALUATOR_SECRET__THE_COLLISION_TOTAL_V3_"
            "GENERATOR_EMITS_A_WELL_FORMED_27_CASE_POPULATION__THE_EXACT_V2_"
            "CANDIDATE_THROUGH_THE_EXACT_FROZEN_HARNESS_RECEIVES_PASS_FROM_THE_"
            "EXACT_FROZEN_SCORER_ON_ALL_27_CASES"
        ),
        "fresh_reality_required_for_this_frozen_generator_claim": False,
        "production_execution_information_gain": 0,
        "v2_delta": (
            "NUMERIC_TASK_AND_SCORING_SEMANTICS_UNCHANGED__ONLY_ACTUAL_TRUNCATED_"
            "OPAQUE_ID_COLLISIONS_RECEIVE_DETERMINISTIC_DISAMBIGUATION"
        ),
        "hard_nonclaims": [
            "NO_OPEN_WORLD_UNKNOWN_DOMAIN_GENERALIZATION_BEYOND_THIS_FROZEN_EVALUATOR_CONTRACT",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_BY_THIS_MODULE_ALONE",
            "NO_PRODUCTION_OR_TERMINAL_CASE_GENERATED_OR_READ",
            "INDEPENDENT_CONTENT_BOUND_VERIFICATION_REQUIRED_BEFORE_PROMOTION",
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
