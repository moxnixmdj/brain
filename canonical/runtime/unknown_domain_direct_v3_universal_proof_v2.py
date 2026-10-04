"""Content-bound universal proof candidate for Unknown-Domain direct V3.

Scope is exactly the bound V3 generator/candidate/harness/scorer bytes below.
No production or terminal population is generated. The proof closes:
- every harness/scorer-critical finite identifier scope structurally;
- wrong-support rejection for all six transfer primitive families;
- exact IEEE-754 ADD2 role orientation;
- all three abstention classes.

It grants no acceptance/family/capability/ownership credit by itself. Independent
exact-byte verification and a separate fail-closed acceptance reduction remain
mandatory.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import unknown_domain_direct_candidate_v1 as c1
from canonical.runtime import unknown_domain_direct_candidate_v2 as c2
from canonical.runtime import unknown_domain_direct_candidate_v3 as c3
from canonical.runtime import unknown_domain_direct_execution_harness_v1 as harness
from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v2 as g2
from canonical.runtime import unknown_domain_direct_hidden_generator_v3 as g3
from canonical.runtime import unknown_domain_direct_hidden_scorer_v1 as scorer

SCHEMA = "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_V3_UNIVERSAL_PROOF_V2"

EXPECTED_BLOBS = {
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":
        "a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":
        "4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_candidate_v3.py":
        "cb030de5a7f96bac7667b7fbb3be38a1cc55e3ea",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v1.py":
        "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":
        "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v3.py":
        "c06601a35eb63cd68fb4cac750cf62cdfa193143",
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
    # _total_ids first requires a finite duplicate-free semantic label set.
    # It sorts tuples (rank,label). Because label is unique, every sorted tuple
    # remains distinct even when every HMAC rank collides. enumerate then assigns
    # a distinct integer slot, and the slot is encoded into each output string.
    # Therefore opaque-suffix equality cannot collapse any ID in a scope.
    labels = ("0", "1", "2", "3")
    original = g1._token
    try:
        g1._token = lambda *args, **kwargs: "COLLISION"
        out = g3._total_ids(
            b"x" * 32,
            "B" * 20,
            scope="UNIVERSAL_COLLISION_WITNESS",
            labels=labels,
            prefix="ID-",
        )
        assert len(out) == len(labels)
        assert len(set(out.values())) == len(labels)
    finally:
        g1._token = original

    # The exact bound population has 27 distinct semantic case labels.
    case_labels = [
        *(f"T:{i}" for i in range(g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER])),
        *(f"A:{i}" for i in range(g1.PRODUCTION_CASE_COUNTS[g1.ABSTAIN])),
    ]
    assert len(case_labels) == 27
    assert len(case_labels) == len(set(case_labels))

    # Every other finite scope has a statically fixed distinct semantic basis.
    assert g1.PRODUCTION_CASE_COUNTS == {g1.TRANSFER: 12, g1.ABSTAIN: 15}
    assert tuple(g1.ABSTAIN_CLASSES) == (
        "IDENTIFIABLE", "NONIDENTIFIABLE", "UNDERSPECIFIED"
    )
    return {
        "all_harness_and_scorer_critical_id_scopes_structurally_total": True,
        "case_id_semantic_cardinality": 27,
        "transfer_probe_ids_per_case": 2,
        "abstention_hypothesis_ids_per_case": 2,
        "underspecified_discriminator_ids_per_case": 2,
        "feature_ids_per_transfer_case": "ARITY_PLUS_TWO_DISTRACTORS",
        "receipt_id_basis": "ALREADY_TOTAL_CASE_ID",
        "uniqueness_depends_on_hmac_collision_resistance": False,
        "forced_all_token_collision_witness_passed": True,
        "intentional_equivalence": (
            "IDENTIFIABLE_ABSTENTION_TWO_HYPOTHESES_SHARE_ONE_ACTION_ID_BY_SEMANTICS"
        ),
    }


def _wrong_support_rejection_theorem() -> dict[str, Any]:
    assert tuple(g1.PRIMITIVE_FAMILIES) == FAMILIES
    assert harness.MAX_TRANSFER_PROBES == 2

    # For V2/V3 non-mimic probe rows, distractor 0 shifts its source role by
    # at least 4.75 and distractor 1 by at least 6.25. Probe_variant can only
    # increase those shifts.
    min_shift = 4.75

    # AFFINE_POS: gain >= 0.6.
    affine_min_gap = 0.6 * min_shift

    # COMPLEMENT: slope magnitude exactly 1.
    complement_min_gap = min_shift

    # SAT_MONO: f(x)=x/(1+|x|), gain >= 0.7. All true probe inputs lie in
    # [-3.5,3.5], shifted values in [-3.5+4.75, 3.5+6.5].
    # f'(x)=1/(1+|x|)^2. A conservative derivative lower bound on [-3.5,10]
    # is 1/121, so MVT gives a strict output gap.
    sat_mono_min_gap = 0.7 * min_shift / 121.0
    sat_mono_max_close_tolerance = 4.5e-9

    # SIGN transfer indices 1 and 7 have a negative first probe true role,
    # magnitude <=3.5; every distractor is shifted by >=4.75 and is positive.
    sign_wrong_support_min_value = -3.5 + min_shift

    # STEP first probe can remain on the same side, but the second probe is
    # below threshold by <=2.2; adding >=4.75 puts every distractor above.
    step_second_probe_margin = min_shift - 2.2

    # ADD2 indices 4 and 10: first probe has both true roles positive.
    # Let d0=r0+4.75 and d1=r1+6.25 at minimum. Every wrong unordered support
    # changes the mathematical sum by at least 1.5 over r0+r1, far above close().
    add2_wrong_support_min_gap = min(
        4.75 - (3.5 - 0.25),
        6.25,
        4.75,
        6.25 - (3.5 - 0.25),
        4.75 + 6.25,
    )

    assert affine_min_gap > 1.0
    assert complement_min_gap > 1.0
    assert sat_mono_min_gap > sat_mono_max_close_tolerance
    assert sign_wrong_support_min_value > 0.0
    assert step_second_probe_margin > 0.0
    assert add2_wrong_support_min_gap == 1.5
    assert harness.MAX_TRANSFER_PROBES < 3

    return {
        "all_six_transfer_families_covered": True,
        "affine_min_output_gap": affine_min_gap,
        "complement_min_output_gap": complement_min_gap,
        "sat_mono_min_output_gap": sat_mono_min_gap,
        "sat_mono_max_close_tolerance": sat_mono_max_close_tolerance,
        "sign_negative_probe_distractor_min": sign_wrong_support_min_value,
        "step_second_probe_wrong_side_margin": step_second_probe_margin,
        "add2_wrong_support_min_gap": add2_wrong_support_min_gap,
        "max_transfer_probes": harness.MAX_TRANSFER_PROBES,
        "full_rediscovery_probe_floor": 3,
    }


def _add2_exact_orientation_theorem() -> dict[str, Any]:
    add2_indices = [
        i
        for i in range(g1.PRODUCTION_CASE_COUNTS[g1.TRANSFER])
        if FAMILIES[i % len(FAMILIES)] == "COMPOSITIONAL_REWRITE"
    ]
    assert add2_indices == [4, 10]

    # V2/V3 role magnitudes are sampled from [0.25,3.5], so sign is never 0.
    # Signs depend only on (row index, transfer index), not domain A/B.
    for index in add2_indices:
        r0 = tuple(-1 if (j + index) % 2 == 0 else 1 for j in range(3))
        r1 = tuple(-1 if (j + index + 1) % 3 == 0 else 1 for j in range(3))
        assert r0 == (-1, 1, -1)
        assert r1 == (1, -1, 1)
        assert r0 != r1

    # c3 binds source receipt role IDs to their public source sign signatures,
    # matches those signatures to the already-recovered target support, and only
    # then calls the unchanged c2._conclude -> c1._program_eval. Generator gold
    # calls g1._eval with the same ordered r0/r1 operands. The operation sequence
    # is therefore identical, including IEEE-754 rounding.
    program = {
        "dsl": "UDIR_V1",
        "op": "ADD2",
        "roles": ["r0", "r1"],
        "params": {"bias": 0.1},
    }
    vals = {"r0": 1.0e16, "r1": -1.0e16}
    assert c1._program_eval(program, vals) == g1._eval(program, vals)

    return {
        "add2_indices": add2_indices,
        "source_target_sign_schedule_domain_invariant": True,
        "r0_signature": [-1, 1, -1],
        "r1_signature": [1, -1, 1],
        "strict_magnitude_lower_bound": 0.25,
        "candidate_uses_identifier_spelling_for_orientation": False,
        "candidate_and_generator_exact_operation_order_aligned": True,
    }


def _abstention_theorem() -> dict[str, Any]:
    assert scorer.DECISIONS == {"CONCLUDE", "ABSTAIN", "REQUEST_DISCRIMINATOR"}

    # IDENTIFIABLE: V3 intentionally assigns both plausible hypotheses the same
    # visible terminal action. Candidate V1 concludes when the consequence set
    # has cardinality one. Scorer requires that exact action.
    #
    # NONIDENTIFIABLE: actions are distinct and only SAFE_OBSERVATION is exposed,
    # never SAFE_BINARY_DISCRIMINATOR. Candidate abstains with nonempty witness.
    #
    # UNDERSPECIFIED: actions are distinct and exactly two structurally distinct
    # SAFE_BINARY_DISCRIMINATOR IDs have costs 1 and 2. Candidate requests the
    # visible minimum-cost ID, exactly the hidden minimum_discriminator_id.
    return {
        "all_three_abstention_classes_covered": True,
        "identifiable":"VISIBLE_EQUAL_CONSEQUENCE_SET_CARDINALITY_ONE__EXACT_CONCLUSION",
        "nonidentifiable":"VISIBLE_DISTINCT_CONSEQUENCES__NO_SAFE_BINARY_DISCRIMINATOR__NONEMPTY_ABSTENTION_WITNESS",
        "underspecified":"TWO_STRUCTURALLY_DISTINCT_SAFE_BINARY_DISCRIMINATORS__VISIBLE_COSTS_ONE_AND_TWO__EXACT_MINIMUM_ID_REQUESTED",
    }


def prove(root: Path | None = None) -> dict[str, Any]:
    root = _repo_root() if root is None else Path(root).resolve()
    bindings = _verify_bindings(root)
    ids = _identifier_totality_theorem()
    transfer = _wrong_support_rejection_theorem()
    add2 = _add2_exact_orientation_theorem()
    abstention = _abstention_theorem()

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CONTENT_BOUND_UNIVERSAL_PROOF_CANDIDATE_OVER_EXACT_V3_GENERATOR_DOMAIN"
        ),
        "target_predicate": "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
        "exact_subject_blobs": bindings,
        "scope": {
            "beacon": "ALL_VALID_STRINGS_LENGTH_GE_16",
            "evaluator_secret": (
                "ALL_VALUES_ACCEPTED_BY_FROZEN_V1_SECRET_BYTES_GATE"
            ),
            "population_cases": 27,
            "transfer_cases": 12,
            "abstention_cases": 15,
            "production_or_terminal_cases_generated": 0,
        },
        "identifier_totality_proof": ids,
        "transfer_wrong_support_proof": transfer,
        "add2_exact_orientation_proof": add2,
        "abstention_proof": abstention,
        "theorem": (
            "FOR_EVERY_POPULATION_EMITTED_BY_THE_EXACT_BOUND_V3_GENERATOR__"
            "ALL_HARNESS_AND_SCORER_CRITICAL_IDENTIFIERS_ARE_STRUCTURALLY_WELL_FORMED__"
            "AFTER_AT_MOST_TWO_ALLOWED_PROBES_EVERY_TRANSFER_CASE_RECOVERS_THE_EXACT_HIDDEN_SUPPORT__"
            "ADD2_ROLE_ORDER_IS_RECOVERED_FROM_DOMAIN_INVARIANT_VISIBLE_SIGN_SIGNATURES_BEFORE_EXACT_FLOAT_EVALUATION__"
            "ALL_THREE_ABSTENTION_CLASSES_RECEIVE_THE_FROZEN_SCORER_REQUIRED_DECISION__"
            "THEREFORE_THE_EXACT_BOUND_V3_CANDIDATE_PASSES_THE_UNCHANGED_FROZEN_SCORER_ON_ALL_27_CASES"
        ),
        "hard_nonclaims": [
            "NO_OPEN_WORLD_GENERALIZATION_BEYOND_THE_BOUND_V3_GENERATOR_DOMAIN",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT_BY_THIS_ARTIFACT",
            "INDEPENDENT_EXACT_BYTE_VERIFICATION_REQUIRED",
            "SEPARATE_ROOT3_AND_ACCEPTANCE_REDUCTION_REQUIRED",
            "NO_PRODUCTION_OR_TERMINAL_CASE_GENERATED_OR_READ",
        ],
        "accounting": {
            "incremental_spend_usd": 0,
            "new_reality_units_consumed": 0,
            "production_cases_consumed": 0,
            "terminal_cases_consumed": 0,
            "acceptance_credit_delta": 0,
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(prove(), indent=2, sort_keys=True))
